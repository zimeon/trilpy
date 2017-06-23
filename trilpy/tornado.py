"""Tornado app for trilpy.

NOTE - DEMOWARE: NO ATTEMPT AT AUTH OR PERSISTENCE.
"""
import logging
import os.path
import tornado.ioloop
import tornado.web
from trilpy.ldpnr import LDPNR

class HTTPError(tornado.web.HTTPError):

    pass

class LDPHandler(tornado.web.RequestHandler):

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
            self.write("LDPC")
        self.set_header("Content-Length", len(content))
        if (not is_head):
            self.write(content)

    def post(self):
        """HTTP POST."""
        path = self.request.path        
        self.set_header("Content-Type", "text/plain")
        if (path not in self.store.resources):
            if (path in self.store.deleted):
                raise HTTPError(410)
            raise HTTPError(404)
        self.write("You wrote " + self.get_body_argument("message"))

    def put(self):
        """HTTP PUT."""
        if (not self.support_put):
            raise HTTPError(405)
        path = self.request.path
        logging.debug("PUT %s" % (path))
        if (path in self.store.resources):
            self.store.delete(path)
        content_type = self.request_content_type()
        if (content_type in ['text/turtle', 'application/ld+json']):
            self.confirm("Create LDPRS")
        else:
            self.store.add(path, LDPNR(content=self.request.body,
                                       content_type=content_type))
            self.confirm("Created LDPNR")

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
        return(cts[0])

    def write_error(self, status_code, **kwargs):
        """Plain text error message (nice with curl)."""
        self.set_header('Content-Type', 'text/plain')
        self.finish(str(status_code) + ' - ' + self._reason + "\n")

    def confirm(self, txt, status_code=200):
        """Plain text confirmation message."""
        self.set_header("Content-Type", "text/plain")
        self.write(str(status_code) + ' - ' + txt + "\n")


class StatusHandler(tornado.web.RequestHandler):

    store = None

    def get(self):
        self.set_header("Content-Type", "text/plain")
        self.write("Store has\n")
        self.write("  * %d active resources\n" % (len(self.store.resources)))
        for name in sorted(self.store.resources):
            self.write("    * %s - %s\n" % (name, 'x'))
        self.write("  * %d deleted resources\n" % (len(self.store.deleted)))
        for name in sorted(self.store.deleted):
            self.write("    * %s - %s\n" % (name, 'x'))

def make_app():
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
