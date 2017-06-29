"""Tornado app for trilpy.

DEMOWARE ONLY: NO ATTEMPT AT AUTH, THREAD SAFETY, PERSISTENCE.
"""
import logging
from negotiator import ContentNegotiator, AcceptParameters, ContentType, Language
import os.path
import tornado.ioloop
import tornado.web
from .ldpnr import LDPNR
from .ldprs import LDPRS
from .ldpc import LDPC


class HTTPError(tornado.web.HTTPError):
    """HTTP Error class for non-2xx responses."""

    pass


class LDPHandler(tornado.web.RequestHandler):
    """LDP and Fedora request handler."""

    store = None
    support_put = True
    support_delete = True

    def head(self):
        """HEAD - GET with no body."""
        self.get(is_head=True)

    def get(self, is_head=False):
        """GET or HEAD if is_head set True."""
        path = self.request.path
        logging.debug("GET %s" % (path))
        if (path not in self.store.resources):
            if (path in self.store.deleted):
                raise HTTPError(410)
            logging.debug("Not found")
            raise HTTPError(404)
        resource = self.store.resources[path]
        if (isinstance(resource, LDPNR)):
            content = resource.content
        else:
            content_type = self.conneg(['text/turtle', 'application/ld+json'])
            content = resource.serialize(content_type)
        self.set_header("Content-Length", len(content))
        self.set_options()
        if (not is_head):
            self.write(content)

    def post(self):
        """HTTP POST.

        FIXME - ignores Slug.
        """
        path = self.request.path
        self.set_header("Content-Type", "text/plain")
        if (path not in self.store.resources):
            if (path in self.store.deleted):
                raise HTTPError(410)
            raise HTTPError(404)
        resource = self.store.resources[path]
        if (not isinstance(resource, LDPC)):
            raise HTTPError()
        resource = self.put_post_resource()
        path = self.store.add(resource)
        self.set_header("Location", path)
        self.set_status(201)

    def put(self):
        """HTTP PUT.

        Fedora: https://fcrepo.github.io/fcrepo-specification/#httpPUT
        LDP: https://www.w3.org/TR/ldp/#ldpr-HTTP_PUT
        HTTP: https://tools.ietf.org/html/rfc7231#section-4.3.4
        """
        if (not self.support_put):
            raise HTTPError(405)
        path = self.request.path
        logging.debug("PUT %s" % (path))
        replace = False
        if (path in self.store.resources):
            self.store.delete(path)
            replace = True
        resource = self.put_post_resource()
        self.store.add(resource, path)
        self.set_status(204 if replace else 201)

    def put_post_resource(self):
        """Parse request data for PUT or POST."""
        content_type = self.request_content_type()
        if (content_type in ['text/turtle', 'application/ld+json']):
            try:
                rs = LDPRS()
                rs.parse(content=self.request.body,
                         content_type=content_type)
            except Exception as e:
                logging.warn("Failed to add LDPRS: %s" % (str(e)))
                raise HTTPError(400)
            return(rs)
        else:
            return(self.request.body)

    def delete(self):
        """HTTP DELETE.

        Optional in LDP <https://www.w3.org/TR/ldp/#ldpr-HTTP_DELETE>
        """
        if (not self.support_delete):
            raise HTTPError(405)
        path = self.request.path
        logging.debug("DELETE %s" % (path))
        if (path not in self.store.resources):
            logging.debug("Not found")
            raise HTTPError(404)
        self.store.delete(path)
        self.confirm("Deleted")

    def request_content_type(self):
        """Return the request content type.

        400 if there are multiple headers specified.
        """
        cts = self.request.headers.get_list('content-type')
        if (len(cts) > 1):
            raise HTTPError(400, "Multiple Content-Type headers")
        elif (len(cts) == 0):
            raise HTTPError(400, "No Content-Type header")
        logging.debug("Request content-type %s" % (cts[0]))
        return(cts[0])

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

    def set_options(self):
        """Add options header to current response."""
        opts = ['GET', 'HEAD', 'OPTIONS']
        if (self.support_delete):
            opts.append('DELETE')
        self.set_header("Options", ', '.join(opts))

    def write_error(self, status_code, **kwargs):
        """Plain text error message (nice with curl)."""
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
        self.write("  * %d active resources\n" % (len(self.store.resources)))
        for name in sorted(self.store.resources.keys()):
            self.write("    * %s - %s\n" % (name, 'x'))
        self.write("  * %d deleted resources\n" % (len(self.store.deleted)))
        for name in sorted(self.store.deleted):
            self.write("    * %s - %s\n" % (name, 'x'))


def make_app():
    """Create Trilpy Tornado application."""
    static_path = os.path.join(os.path.dirname(__file__), 'static')
    return tornado.web.Application([
        (r"/(favicon\.ico)", tornado.web.StaticFileHandler,
            {'path': static_path}),
        (r"/status", StatusHandler),
        (r".*", LDPHandler),
    ])


def run(port, store, support_put=True, support_delete=True):
    """Run LDP server on port with given store and options."""
    LDPHandler.store = store
    LDPHandler.support_put = support_put
    LDPHandler.support_delete = support_delete
    StatusHandler.store = store
    app = make_app()
    logging.info("Running trilpy on http://localhost:%d" % (port))
    app.listen(port)
    try:
        tornado.ioloop.IOLoop.current().start()
    except KeyboardInterrupt as e:
        logging.warn("KeyboardInterrupt, exiting.")
