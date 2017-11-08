"""Tornado app for trilpy.

DEMOWARE ONLY: NO ATTEMPT AT AUTH, THREAD SAFETY, PERSISTENCE.
"""
import itertools
import logging
from negotiator2 import conneg_on_accept
import os.path
import requests.utils
import tornado.ioloop
import tornado.web
from urllib.parse import urljoin, urlsplit

from .digest import Digest, UnsupportedDigest, BadDigest
from .ldpnr import LDPNR
from .ldprs import LDPRS, PatchFailed, PatchIllegal
from .ldpc import LDPC
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
        self._types = None  # values extracted from Link: rel="type"
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
                self.rdf_media_types, self.request.headers.get("Accept"))
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
        if (not isinstance(resource, LDPC)):
            logging.debug("Rejecting POST to non-LDPC (%s)" %
                          (str(resource)))
            raise HTTPError(405)
        new_resource = self.put_post_resource(uri)
        slug = self.request.headers.get('Slug')
        new_uri = self.store.add(new_resource, context=uri, slug=slug)
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
            raise HTTPError(405)
        path = self.request.path
        uri = self.path_to_uri(path)
        logging.debug("PUT %s" % (path))
        # 5.2.4.2 LDP servers that allow LDPR creation via
        # PUT should not re-use URIs. => 409 if deleted
        if (uri in self.store.deleted):
            logging.debug("Rejecting PUT to deleted URI")
            raise HTTPError(409)
        replace = False
        current_type = None
        if (uri in self.store):
            replace = True
            current_type = self.store[uri].rdf_type_uri
        resource = self.put_post_resource(uri, current_type)
        if (uri in self.store):
            # 5.2.4.1 LDP servers SHOULD NOT allow HTTP PUT to
            # update an LDPC's containment triples; if the
            # server receives such a request, it SHOULD respond
            # with a 409 (Conflict) status code.
            logging.debug("PUT REPLACE: %s" % (str(resource)))
            current_resource = self.store[uri]
            self.check_replace_via_put(current_resource, resource)
            # OK, do replace of content only
            current_resource.content = resource.content
        else:
            # New resource
            self.store.add(resource, uri)
        self.set_status(204 if replace else 201)
        logging.debug("PUT %s to %s OK" % (str(resource), uri))

    def check_replace_via_put(self, old_resource, new_resource):
        """Determine whether it is OK to repace with PUT.

        Will return if OK, raise HTTPError otherwise.
        """
        # Check ETags
        im = self.request.headers.get('If-Match')
        if (self.require_if_match_etag and im is None):
            logging.debug("Missing If-Match header")
            raise HTTPError(428)
        elif (im is not None and im != old_resource.etag):
            logging.debug("ETag mismatch: %s vs %s" %
                          (im, old_resource.etag))
            raise HTTPError(412)
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
                logging.debug("Rejecting attempt to change containment triples.")
                raise HTTPError(409)
        elif (isinstance(old_resource, LDPRS) and
              not isinstance(old_resource, LDPC) and
              isinstance(new_resource, LDPRS) and
              not isinstance(new_resource, LDPC)):
            # FIXME - RDF Source checks
            pass
        else:
            logging.debug("Rejecting incompatible replace of %s with %s" %
                          (str(old_resource), str(new_resource)))
            raise HTTPError(409)

    def put_post_resource(self, uri=None, current_type=None):
        """Parse request data for PUT or POST.

        Handles both RDF and Non-RDF sources. Look first at the Link header
        to determine the requested LDP interaction model.
        """
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
                    logging.warn("Attempt to replace LDPRS (or subclass) with non-RDF type %s" % (content_type))
                    raise HTTPError(415)
        elif (model is None):
            # Take default model (LDPRS or LDPNR) from content type
            model = self.ldp_rdf_source if content_type_is_rdf else self.ldp_nonrdf_source
        logging.warn('model ' + str(model))
        self.check_digest()
        if (model != self.ldp_nonrdf_source):
            if (not content_type_is_rdf):
                logging.warn("Unsupported RDF type: %s" % (content_type))
                raise HTTPError(415)
            try:
                if (model in self.ldp_container_types):
                    rs = LDPC(uri, container_type=model)
                else:
                    rs = LDPRS(uri)
                rs.parse(content=self.request.body,
                         content_type=content_type,
                         context=uri)
            except Exception as e:
                logging.warn("Failed to parse/add RDF: %s" % (str(e)))
                raise HTTPError(400)
            logging.debug("RDF--- " + rs.serialize())
            return(rs)
        else:
            return(LDPNR(uri=uri,
                         content=self.request.body,
                         content_type=content_type))

    def patch(self):
        """HTTP PATCH."""
        if (not self.support_patch):
            raise HTTPError(405)
        path = self.request.path
        uri = self.path_to_uri(path)
        logging.debug("PATCH %s" % (path))
        resource = self.from_store(uri)
        if (not isinstance(resource, LDPRS)):
            logging.debug("Rejecting PATCH to non-LDPRS (%s)" %
                          (str(resource)))
            raise HTTPError(405)
        self.check_digest()
        content_type = self.request_content_type()
        if (content_type not in self.rdf_patch_types):
            logging.warn("Unsupported RDF PATCH type: %s" % (content_type))
            raise HTTPError(415)
        try:
            resource.patch(patch=self.request.body.decode('utf-8'),
                           content_type=content_type)
        except PatchIllegal as e:
            logging.warn("Patch illegal: " + str(e))
            raise HTTPError(409, str(e))
        except PatchFailed as e:
            logging.warn("Patch failed: " + str(e))
            raise HTTPError(400, str(e))
        logging.debug("PATCH %s OK" % (uri))

    def delete(self):
        """HTTP DELETE.

        Optional in LDP <https://www.w3.org/TR/ldp/#ldpr-HTTP_DELETE>
        """
        if (not self.support_delete):
            logging.debug("DELETE not supported")
            raise HTTPError(405)
        path = self.request.path
        uri = self.path_to_uri(path)
        logging.debug("DELETE %s" % (path))
        self.from_store(uri)  # handles 404/410 if not present
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
    def request_types(self):
        """Type imformation from Link Link rel="type" headers.

        Save all type names/URIS to self._types so we don't have
        to work through this mulitple times if called more than
        once.
        """
        if (self._types is not None):
            return self._types
        self._types = set()
        links = self.request.headers.get_list('link')
        if (len(links) > 1):
            raise HTTPError(400, "Multiple Link headers")
        elif (len(links) == 1):
            # Extra set of types specified
            for link in requests.utils.parse_header_links(links[0]):
                if ('rel' in link and link['rel'] == 'type' and 'url' in link):
                    self._types.add(link['url'])
        return self._types

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
            logging.debug("Gone")
            raise HTTPError(410)
        except KeyError:
            logging.debug("Not found")
            raise HTTPError(404)

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
