"""Tornado app for trilpy.

DEMOWARE ONLY: NO ATTEMPT AT AUTH, THREAD SAFETY, PERSISTENCE.
"""
import itertools
import logging
from negotiator2 import conneg_on_accept, memento_parse_datetime
import os.path
import requests.utils
import tornado.ioloop
import tornado.web
from urllib.parse import urljoin, urlsplit

from .digest import Digest, UnsupportedDigest, BadDigest
from .ldpc import LDPC
from .ldpcv import LDPCv
from .ldpnr import LDPNR
from .ldpr import LDPR
from .ldprs import LDPRS, PatchFailed, PatchIllegal
from .namespace import LDP
from .prefer_header import ldp_return_representation_omits
from .store import KeyDeleted


class HTTPError(tornado.web.HTTPError):
    """HTTP Error class for non-2xx responses."""

    pass


class LDPHandler(tornado.web.RequestHandler):
    """LDP and Fedora request handler."""

    store = None
    support_put = True
    support_patch = True
    support_delete = True
    support_acl = True
    support_versioning = True
    require_if_match_etag = True
    base_uri = 'BASE'
    rdf_media_types = LDPRS.rdf_media_types
    rdf_patch_types = LDPRS.rdf_patch_types
    ldp_container_types = [str(LDP.IndirectContainer),
                           str(LDP.DirectContainer),
                           str(LDP.BasicContainer),
                           str(LDP.Container)]
    ldp_rdf_source = str(LDP.RDFSource)
    ldp_nonrdf_source = str(LDP.NonRDFSource)
    constraints_path = '/constraints.txt'

    def initialize(self):
        """Set up place to accumulate links for Link header."""
        # request parsing
        self._request_links = None  # values extracted from Link: rel=".."
        # response building
        self._links = []  # accumulate links for Link header

    def head(self):
        """HEAD - GET with no body."""
        self.get(is_head=True)

    def get(self, is_head=False):
        """GET or HEAD if is_head set True."""
        path = self.request.path
        uri = self.path_to_uri(path)
        logging.debug("GET %s" % (path))
        want_digest = self.check_want_digest()
        resource = self.from_store(uri)
        if (isinstance(resource, LDPNR)):
            content_type = resource.content_type
            content = resource.content
            logging.debug("Non-RDF content, size=%dbytes" % (len(content)))
        else:
            content_type = conneg_on_accept(
                resource.rdf_media_types, self.request.headers.get("Accept"))
            # Is there a Prefer return=representation header?
            omits = ldp_return_representation_omits(
                self.request.headers.get_list('Prefer'))
            # logging.debug("Prefer: " + str(self.request.headers.get_list('Prefer')))
            logging.debug("Omits: " + str(omits))
            content = resource.serialize(content_type, omits)
            logging.debug("RDF content:\n" + content)
            if (len(omits) > 0):
                self.set_header("Preference-Applied",
                                "return=representation")
        self.add_links('type', resource.rdf_types)
        self.add_links('acl', [self.store.individual_acl(uri)])
        if (resource.is_ldprv):
            self.add_links('timemap', [resource.timemap])
            self.add_links('original timegate', [resource.uri])
            self.add_links('type', ['http://mementoweb.org/ns#TimeGate',
                                    'http://mementoweb.org/ns#OriginalResource'])
            self.set_header("Vary", 'Accept-Datetime')
        elif (resource.is_ldpcv):
            self.add_links('original timegate', [resource.original])  # FIXME - need this?
            self.add_links('type', ['http://mementoweb.org/ns#TimeMap'])
        elif (resource.is_ldprm):
            self.add_links('type', ['http://mementoweb.org/ns#Memento'])
        self.set_link_header()
        if (want_digest):
            self.set_header("Digest", want_digest.digest_value(content))
        self.set_header("Content-Type", content_type)
        self.set_header("Content-Length", len(content))
        self.set_header("Etag", resource.etag)
        self.set_allow(resource)
        if (not is_head):
            self.write(content)

    def post(self):
        """HTTP POST.

        Fedora: https://fcrepo.github.io/fcrepo-specification/#httpPOST
        LDP: https://www.w3.org/TR/ldp/#ldpr-HTTP_POST
        """
        path = self.request.path
        uri = self.path_to_uri(path)
        logging.debug("POST %s" % (path))
        resource = self.from_store(uri)
        if (resource.is_ldprm):
            raise HTTPError(405, "POST not supported on LDPRm/Memento")
        elif (not isinstance(resource, LDPC)):
            raise HTTPError(405, "Rejecting POST to non-LDPC (%s)" % (str(resource)))
        acl_uri = self.request_acl_uri()
        datetime = None
        if (resource.is_ldpcv):
            mdt_header = self.request.headers.get('Memento-Datetime')
            if (mdt_header):
                try:
                    datetime = memento_parse_datetime(mdt_header)
                except ValueError:
                    HTTPError(401, "Bad Memento-Datetime header")
        if (resource.is_ldpcv and not datetime):
            # Request to create LDPRm/Memento with copy of LDPRv content
            ldprv = self.store[resource.original]
            new_resource = type(ldprv)()
            new_resource.content = ldprv.content
            if (isinstance(ldprv, LDPNR)):
                new_resource.content_type = ldprv.content_type
        else:
            new_resource = self.put_post_resource(uri)
        slug = self.request.headers.get('Slug')
        if (resource.is_ldpcv):
            # Request to create LDPRm/Memento
            new_resource.original = resource.original
            new_resource.timemap = resource.uri
        new_uri = self.store.add(new_resource, context=uri, slug=slug)
        if (self.request_for_versioning()):
            tm = LDPCv(uri=None, original=new_uri)
            tm_uri = self.store.add(tm)  # no naming advice
            logging.debug("POST Versioned request, timemap=%s" % (tm.uri))
            new_resource.timemap = tm.uri
            self.store.update(new_resource)
        new_path = self.uri_to_path(new_uri)
        self.set_header("Content-Type", "text/plain")
        self.set_header("Location", new_uri)
        self.set_status(201)
        logging.debug("POST %s as %s in %s OK" %
                      (str(new_resource), new_uri, uri))

    def put(self):
        """HTTP PUT.

        Fedora: https://fcrepo.github.io/fcrepo-specification/#httpPUT
        LDP: https://www.w3.org/TR/ldp/#ldpr-HTTP_PUT
        HTTP: https://tools.ietf.org/html/rfc7231#section-4.3.4
        """
        if (not self.support_put):
            raise HTTPError(405, "PUT not supported")
        path = self.request.path
        uri = self.path_to_uri(path)
        logging.debug("PUT %s" % (path))
        # 5.2.4.2 LDP servers that allow LDPR creation via
        # PUT should not re-use URIs. => 409 if deleted
        if (uri in self.store.deleted):
            raise HTTPError(409, "Rejecting PUT to deleted URI")
        replace = False
        current_type = None
        if (uri in self.store):
            replace = True
            current_resource = self.store[uri]
            current_type = current_resource.rdf_type_uri
            if (current_resource.is_ldprm):
                raise HTTPError(405, "PUT not supported on LDPRm/Memento")
        resource = self.put_post_resource(uri, current_type)
        if (uri in self.store):
            # FIXME - What about versioning PUT to replace requests?
            #
            # 5.2.4.1 LDP servers SHOULD NOT allow HTTP PUT to
            # update an LDPC's containment triples; if the
            # server receives such a request, it SHOULD respond
            # with a 409 (Conflict) status code.
            logging.debug("PUT REPLACE: %s" % (str(resource)))
            current_resource = self.store[uri]
            self.check_replace_via_put(current_resource, resource)
            # OK, do replace of content only
            current_resource.content = resource.content
            self.store.update(current_resource)
        else:
            # New resource
            self.store.add(resource, uri)
            if (self.request_for_versioning()):
                tm = LDPCv(uri=None, original=r)
                tm_uri = self.store.add(tm)  # no naming advice
                logging.debug("PUT Versioned request, timemap=%s" % (tm.uri))
                resource.timemap = tm.uri
            self.store.update(resource)
        self.set_status(204 if replace else 201)
        logging.debug("PUT %s to %s OK" % (str(resource), uri))

    def check_replace_via_put(self, old_resource, new_resource):
        """Determine whether it is OK to repace with PUT.

        Will return if OK, raise HTTPError otherwise.
        """
        # Check ETags
        im = self.request.headers.get('If-Match')
        if (self.require_if_match_etag and im is None):
            raise HTTPError(428, "Missing If-Match header")
        elif (im is not None and im != old_resource.etag):
            raise HTTPError(412, "ETag mismatch: %s vs %s" % (im, old_resource.etag))
        # Check replacement details
        if (isinstance(old_resource, LDPNR) and
                isinstance(new_resource, LDPNR)):
            # OK to replace any binary with another
            content = old_resource.content
        elif (isinstance(old_resource, LDPC) and
              isinstance(new_resource, LDPC)):
            # Container triple checks - it is OK to repeat (or not)
            # any container triple present in the old resource, but
            # changes are not allowed.
            old_ctriples = old_resource.server_managed_triples()
            new_ctriples = new_resource.extract_containment_triples()
            if (len(new_ctriples + old_ctriples) != len(old_ctriples)):
                raise HTTPError(409, "Rejecting attempt to change containment triples")
        elif (isinstance(old_resource, LDPRS) and
              not isinstance(old_resource, LDPC) and
              isinstance(new_resource, LDPRS) and
              not isinstance(new_resource, LDPC)):
            # FIXME - RDF Source checks
            pass
        else:
            raise HTTPError(409, "Rejecting incompatible replace of %s with %s" %
                                 (str(old_resource), str(new_resource)))

    def put_post_resource(self, uri=None, current_type=None):
        """Create resource by pasring request data for PUT or POST.

        Handles both RDF and Non-RDF sources. Look first at the Link header
        to determine the requested LDP interaction model.

        Returns resource object or raises HTTPError.
        """
        if (self.request_for_versioning() and not self.support_versioning):
            raise HTTPError(400, "Versioning is not supported")
        model = self.request_ldp_type()
        content_type = self.request_content_type()
        content_type_is_rdf = content_type in self.rdf_media_types
        logging.warn("got-content-type " + content_type)
        if (current_type is not None):  # Replacements
            if (model is None):
                # Assume current type on replace where not model specified
                model = current_type
            else:
                # Check for incompatible replacements
                if (model != self.ldp_nonrdf_source and not content_type_is_rdf):
                    raise HTTPError(415, "Attempt to replace LDPRS (or subclass) with non-RDF type %s" % (content_type))
        elif (model is None):
            # Take default model (LDPRS or LDPNR) from content type
            model = self.ldp_rdf_source if content_type_is_rdf else self.ldp_nonrdf_source
        logging.warn('model ' + str(model))
        #
        # Now deal with the content
        #
        self.check_digest()
        if (model != self.ldp_nonrdf_source):
            if (not content_type_is_rdf):
                raise HTTPError(415, "Unsupported RDF type: %s" % (content_type))
            try:
                if (model in self.ldp_container_types):
                    r = LDPC(uri=uri, container_type=model)
                else:
                    r = LDPRS(uri=uri)
                r.parse(content=self.request.body,
                        content_type=content_type,
                        context=uri)
            except Exception as e:
                raise HTTPError(400, "Failed to parse/add RDF: %s" % (str(e)))
            logging.debug("RDF--- " + r.serialize())
        else:
            r = LDPNR(uri=uri, content=self.request.body, content_type=content_type)
        return(r)

    def patch(self):
        """HTTP PATCH."""
        if (not self.support_patch):
            raise HTTPError(405, "PATCH not supported")
        path = self.request.path
        uri = self.path_to_uri(path)
        logging.debug("PATCH %s" % (path))
        resource = self.from_store(uri)
        if (resource.is_ldprm):
            raise HTTPError(405, "PATCH not supported on LDPRm/Memento")
        if (not isinstance(resource, LDPRS)):
            raise HTTPError(405, "Rejecting PATCH to non-LDPRS (%s)" % (str(resource)))
        self.check_digest()
        content_type = self.request_content_type()
        if (content_type not in self.rdf_patch_types):
            raise HTTPError(415, "Unsupported RDF PATCH type: %s" % (content_type))
        try:
            resource.patch(patch=self.request.body.decode('utf-8'),
                           content_type=content_type)
        except PatchIllegal as e:
            raise HTTPError(409, "PATCH illegal: " + str(e))
        except PatchFailed as e:
            raise HTTPError(400, "PATCH failed: " + str(e))
        logging.debug("PATCH %s OK" % (uri))

    def delete(self):
        """HTTP DELETE.

        Optional in LDP <https://www.w3.org/TR/ldp/#ldpr-HTTP_DELETE>
        """
        if (not self.support_delete):
            raise HTTPError(405, "DELETE not supported")
        path = self.request.path
        uri = self.path_to_uri(path)
        logging.debug("DELETE %s" % (path))
        resource = self.from_store(uri)  # handles 404/410 if not present
        if (resource.is_ldpcv):
            # Remove versioning from original, remove Memento
            ldprv = self.store[resource.original]
            ldprv.timemap = None
            self.store.update(resource.original)
            for contained in resource.contains:
                # FIXME - What to do about any Mementos that might themselves be LDPC?
                self.store.delete(contained)
        self.store.delete(uri)
        self.confirm("Deleted")

    def options(self):
        """HTTP OPTIONS.

        Required in LDP
        <https://www.w3.org/TR/ldp/#ldpr-HTTP_OPTIONS>
        with extensions beyond
        <https://tools.ietf.org/html/rfc7231#section-4.3.7>
        """
        path = self.request.path
        uri = self.path_to_uri(path)
        logging.debug("OPTIONS %s" % (path))
        if (path == '*'):
            # Server-wide options per RFC7231
            pass
        else:
            # Specific resource
            resource = self.from_store(uri)
            self.add_links('type', resource.rdf_type_uris)
            self.set_link_header()
            self.set_allow(resource)
        self.confirm("Options returned")

    def request_content_type(self):
        """Return the request content type.

        400 if there are multiple headers specified.

        FIXME - Simply strips any charset information.
        """
        cts = self.request.headers.get_list('content-type')
        if (len(cts) > 1):
            raise HTTPError(400, "Multiple Content-Type headers")
        elif (len(cts) == 0):
            raise HTTPError(400, "No Content-Type header")
        content_type = cts[0].split(';')[0]
        logging.debug("Request content-type %s" % (content_type))
        return(content_type)

    @property
    def request_links(self):
        """Dict of lists of Link header url values keyed by rel.

        Saves all data from Link rel="..." headers to avoid
        parsing repeatedly. Note that per
        https://tools.ietf.org/html/rfc7230#section-3.2.2
        multiple Link headers are to be treated the same as additional
        comma separated link-value entries as described in
        https://tools.ietf.org/html/rfc5988#section-5
        """
        if (self._request_links is not None):
            return self._request_links
        self._request_links = dict()
        link_headers = self.request.headers.get_list('link')
        for link_header in link_headers:
            for link in requests.utils.parse_header_links(link_header):
                if ('rel' in link and 'url' in link):
                    rel = link['rel']
                    url = link['url']
                    if (rel not in self._request_links):
                        self._request_links[rel] = list()
                    if (link not in self._request_links[rel]):
                        self._request_links[rel].append(url)
        return self._request_links

    def request_links_rel(self, rel):
        """List (possibly empty) of Link rel="..." headers for given rel."""
        links = self.request_links
        return links[rel] if (rel in links) else []

    @property
    def request_types(self):
        """Type information from Link rel="type" headers, or empty set()."""
        return self.request_links_rel('type')

    def request_ldp_type(self):
        """LDP interaction model URI from request Link rel="type", else None."""
        types = self.request_types
        # Look for LDP types starting with most specific
        is_ldpnr = (self.ldp_nonrdf_source in types)
        is_rdf = None
        for rdf_type in itertools.chain(self.ldp_container_types,
                                        [self.ldp_rdf_source]):
            if (rdf_type in types):
                is_rdf = rdf_type
                break  # FIXME - ignoring possible container type conflicts
        # Error conditions
        if (is_ldpnr and is_rdf):
            raise HTTPError(400, "Conflicting LDP types in Link headers")
        elif (is_ldpnr):
            return(self.ldp_nonrdf_source)
        else:
            return(is_rdf)

    def request_acl_uri(self):
        """ACL URI in request header else None, must be local if specified."""
        acls = self.request_links_rel('acl')
        if (len(acls) == 0):
            return None
        if (len(acls) > 1):
            raise HTTPError(400, 'Multiple Link rel="acl" in request')
        acl_uri = acls[0]
        if (not acl_uri.startswith(self.base_uri)):  # FIXME - need better test
            raise HTTPError(400, 'Non-local acl rel="acl" specified')
        return acl_uri

    def request_for_versioning(self):
        """True if request specifies versioning through Link rel="type"."""
        types = self.request_types
        return('http://mementoweb.org/ns#OriginalResource' in types)

    def check_digest(self):
        """Check request Digest if present, raise 409 if bad, 400 if not supported.

        Follows https://tools.ietf.org/html/rfc3230. Will take the only the first
        Digest header if multiple are specified. Per the Fedora API specification,
        will report a 400 error if any digest type specified is not supported.
        """
        digest_header = self.request.headers.get("Digest")
        if (digest_header is None):
            return
        try:
            Digest(digest_header=digest_header).check(self.request.body)
        except UnsupportedDigest as e:
            raise HTTPError(409, str(e))
        except BadDigest as e:
            raise HTTPError(400, str(e))

    def check_want_digest(self):
        """Check to see whether a Want-Digest header is provided, check support.

        Will return empty(False) if there is not Want-Digest header, raise HTTPError
        if bad, else return Digest object with header.
        """
        want_digest_header = self.request.headers.get("Want-Digest")
        if (want_digest_header is None):
            return None
        try:
            return Digest(want_digest_header=want_digest_header)
        except UnsupportedDigest as e:
            raise HTTPError(409, str(e))
        except BadDigest as e:
            raise HTTPError(400, str(e))

    def conneg(self, supported_types):
        """Return content_type for response by conneg.

        Based on an update of the negotiate package from
        2013.
        """
        default_type = supported_types[0]
        accept_header = self.request.headers.get("Accept")
        if (accept_header is None):
            return(default_type)
        default_params = AcceptParameters(
            ContentType(default_type))
        acceptable = []
        for t in supported_types:
            acceptable.append(AcceptParameters(
                ContentType(t)))
        cn = ContentNegotiator(default_params, acceptable)
        acceptable = cn.negotiate(accept=accept_header)
        if (acceptable is None):
            return(default_type)
        return(acceptable.content_type.mimetype())

    def path_to_uri(self, path):
        """Resource URI from server path."""
        uri = urljoin(self.base_uri, path)
        # Normalize base_uri/ to base_uri
        if (uri == (self.base_uri + '/')):
            uri = self.base_uri
        return(uri)

    def from_store(self, uri):
        """Get resource from store, raise 404 or 410 if not present."""
        try:
            return self.store[uri]
        except KeyDeleted:
            raise HTTPError(410, "Resource has been deleted")
        except KeyError:
            raise HTTPError(404, "Resource not found")

    def uri_to_path(self, uri):
        """Resource local path (with /) from URI."""
        path = urlsplit(uri)[2]
        return(path if path != '' else '/')

    def set_allow(self, resource=None):
        """Add Allow header to current response."""
        methods = ['GET', 'HEAD', 'OPTIONS', 'PUT']
        if (self.support_delete):
            methods.append('DELETE')
        if (resource is not None):
            if (isinstance(resource, LDPRS)):
                # 4.2.7.1 LDP servers that support PATCH must include an
                # Accept-Patch HTTP response header [RFC5789] on HTTP
                # OPTIONS requests, listing patch document media type(s)
                # supported by the server.
                methods.append('PATCH')
                self.set_header('Accept-Patch', ', '.join(self.rdf_patch_types))
            if (isinstance(resource, LDPC)):
                # 5.2.3.13 LDP servers that support POST must include an
                # Accept-Post response header on HTTP OPTIONS responses,
                # listing POST request media type(s) supported by the
                # server.
                methods.append('POST')
                self.set_header('Accept-Post', ', '.join(self.rdf_media_types))
        self.set_header('Allow', ', '.join(methods))

    def add_links(self, rel, uris):
        """Add rel uris to list used for Link header.

        set_link_header() must be called after all links have been added
        to actually write out the header.
        """
        for uri in uris:
            self._links.append('<%s>; rel="%s"' % (uri, rel))

    def set_link_header(self):
        """Add Link header with set of rel uris."""
        logging.debug('Link: ' + ', '.join(self._links))
        self.set_header('Link', ', '.join(self._links))

    def set_links(self, rel, uris):
        """Add Link headers with set of rel uris."""
        links = []
        for uri in uris:
            links.append('<%s>; rel="%s"' % (uri, rel))
        self.set_header('Link', ', '.join(links))

    def write_error(self, status_code, **kwargs):
        """Plain text error message (nice with curl).

        Also adds a Link header for constraints that (might have)
        caused an error. Use defined in
        <https://www.w3.org/TR/ldp/#ldpr-gen-pubclireqs>
        and servers MAY add this header indescriminately.
        """
        self.set_links('http://www.w3.org/ns/ldp#constrainedBy',
                       [self.path_to_uri(self.constraints_path)])
        self.set_header('Content-Type', 'text/plain')
        self.finish(str(status_code) + ' - ' + self._reason + "\n")

    def confirm(self, txt, status_code=200):
        """Plain text confirmation message."""
        self.set_header("Content-Type", "text/plain")
        self.write(str(status_code) + ' - ' + txt + "\n")


class StatusHandler(tornado.web.RequestHandler):
    """Server status report handler."""

    store = None

    def get(self):
        """HTTP GET for status report."""
        self.set_header("Content-Type", "text/plain")
        self.write("Store has\n")
        self.write("  * %d active resources\n" % (len(self.store)))
        for (name, resource) in sorted(self.store.items()):
            try:
                t = resource.type_label
            except:
                t = str(type(resource))
            self.write("    * %s - %s\n" % (name, t))
        self.write("  * %d deleted resources\n" % (len(self.store.deleted)))
        for name in sorted(self.store.deleted):
            self.write("    * %s - %s\n" % (name, 'deleted'))


def make_app():
    """Create Trilpy Tornado application."""
    static_path = os.path.join(os.path.dirname(__file__), 'static')
    return tornado.web.Application([
        (r"/(favicon\.ico|constraints.txt)",
            tornado.web.StaticFileHandler,
            {'path': static_path}),
        (r"/status", StatusHandler),
        (r".*", LDPHandler),
    ])


def run(port, store, support_put=True, support_delete=True, support_acl=True):
    """Run LDP server on port with given store and options."""
    LDPHandler.store = store
    LDPHandler.support_put = support_put
    LDPHandler.support_delete = support_delete
    LDPHandler.support_acl = support_acl
    LDPHandler.base_uri = store.base_uri
    StatusHandler.store = store
    app = make_app()
    logging.info("Running trilpy on http://localhost:%d" % (port))
    app.listen(port)
    try:
        tornado.ioloop.IOLoop.current().start()
    except KeyboardInterrupt as e:
        logging.warn("KeyboardInterrupt, exiting.")
