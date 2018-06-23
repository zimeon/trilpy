"""Tornado server tests."""
import unittest
from unittest.mock import Mock, MagicMock, call
from tornado.testing import AsyncHTTPTestCase
from tornado.web import Application, HTTPError
from tornado.httpserver import HTTPRequest
from tornado.httputil import HTTPHeaders

from trilpy.ldpc import LDPC
from trilpy.ldpnr import LDPNR
from trilpy.ldprs import LDPRS
from trilpy.links import RequestLinks, ResponseLinks
from trilpy.store import Store
from trilpy.tornado import make_app, HTTPError, LDPHandler, StatusHandler


def mockedLDPHandler(method='GET', uri='/test', headers=None, body=None):
    """LDPHandler with appropriate Application and HTTPRequest mocking."""
    if headers is not None:
        headers = HTTPHeaders(headers)
    request = HTTPRequest(method=method, uri=uri, headers=headers, body=body,
                          connection=Mock())
    return LDPHandler(Application(), request)


class TestLDPHandler(unittest.TestCase):
    """TestLDPHandler class to run tests on LDPHandler.

    These tests synchrononously call methods in LDPHandler without setting
    up the Tornado ioloop or application context.
    """

    def test01_create_and_initialize(self):
        """Create LDPHandler object, initialize call automatically."""
        h = mockedLDPHandler()
        self.assertTrue(h)
        self.assertEqual(h._request_links, None)
        self.assertTrue(isinstance(h.response_links, ResponseLinks))

    def test02_get_current_user(self):
        """Test get_current_user method."""
        # auth disabled
        LDPHandler.no_auth = True
        h = mockedLDPHandler()
        self.assertEqual(h.get_current_user(), 'fedoraAdmin')
        # auth enabled
        LDPHandler.no_auth = False
        h = mockedLDPHandler()
        self.assertEqual(h.get_current_user(), None)
        h = mockedLDPHandler(headers={'Authorization': 'Basic ZmVkb3JhQWRtaW46c2VjcmV0'})
        self.assertEqual(h.get_current_user(), 'fedoraAdmin')
        h = mockedLDPHandler(headers={'Authorization': 'Basic YS11c2VyOmEtcGFzc3dvcmQ='})
        self.assertEqual(h.get_current_user(), None)

    def test34_request_content_type(self):
        """Test request_content_type method."""
        # no header -> 400
        h = mockedLDPHandler()
        self.assertRaises(HTTPError, h.request_content_type)
        # one ...
        h = mockedLDPHandler(headers={'Content-Type': 'a/b; charset="wierdo"'})
        self.assertEqual(h.request_content_type(), 'a/b')
        h = mockedLDPHandler(headers={'Content-Type': 'c/d'})
        self.assertEqual(h.request_content_type(), 'c/d')
        # multiple -> 400
        hh = HTTPHeaders()
        hh.add('Content-Type', 'a/b')
        hh.add('Content-Type', 'c/d')
        h = mockedLDPHandler(headers=hh)
        self.assertRaises(HTTPError, h.request_content_type)

    def test36_is_request_for_versioning(self):
        """Test is_request_for_versioning property."""
        # no header -> False
        h = mockedLDPHandler()
        self.assertFalse(h.is_request_for_versioning)
        # other links
        h = mockedLDPHandler(headers={'Link': '<a>; rel="type", <http://mementoweb.org/ns#OriginalResource>; rel="other"'})
        self.assertFalse(h.is_request_for_versioning)
        # yes
        h = mockedLDPHandler(headers={'Link': '<a>; rel="other", <http://mementoweb.org/ns#OriginalResource>; rel="type"'})
        self.assertTrue(h.is_request_for_versioning)

    def test37_check_digest(self):
        """Test check_digest method."""
        # no header -> None
        h = mockedLDPHandler()
        self.assertEqual(h.check_digest(), None)
        # header with good digest
        h = mockedLDPHandler(headers={'Digest': 'md5=XUFAKrxLKna5cZ2REBfFkg=='}, body=b'hello')
        self.assertEqual(h.check_digest(), None)
        # header with bad digest
        h = mockedLDPHandler(headers={'Digest': 'md5=not-right'}, body=b'hello')
        self.assertRaises(HTTPError, h.check_digest)
        # header with unsupported digest
        h = mockedLDPHandler(headers={'Digest': 'unsupported=whatever'}, body=b'hello')
        self.assertRaises(HTTPError, h.check_digest)

    def test38_check_want_digest(self):
        """Test check_want_digest method."""
        # no header -> None
        h = mockedLDPHandler()
        self.assertEqual(h.check_want_digest(), None)
        # header with good digest request
        h = mockedLDPHandler(headers={'Want-Digest': 'md5'})
        self.assertEqual(h.check_want_digest().want_digest, 'md5')
        # header with unsuppported digest and bad request header
        h = mockedLDPHandler(headers={'Want-Digest': 'special'})
        self.assertRaises(HTTPError, h.check_want_digest)
        h = mockedLDPHandler(headers={'Want-Digest': ';'})
        self.assertRaises(HTTPError, h.check_want_digest)

    def test40_check_authz(self):
        """Test check_authz method (just a stub)."""
        # auth disabled
        LDPHandler.no_auth = True
        h = mockedLDPHandler()
        h.check_authz(None, 'write')
        # auth enabled, no admin
        LDPHandler.no_auth = False
        h = mockedLDPHandler()
        self.assertRaises(HTTPError, h.check_authz, LDPRS('uri:a'), 'write')

    def test43_from_store(self):
        """Test from_store method."""
        h = mockedLDPHandler()
        h.store = Store('http://localhost/')
        self.assertRaises(HTTPError, h.from_store, 'uri:abc')
        r = LDPNR(content=b'hello')
        h.store.add(r, uri='uri:abc')
        self.assertEqual(h.from_store('uri:abc'), r)
        h.store.delete(uri='uri:abc')
        self.assertRaises(HTTPError, h.from_store, 'uri:abc')

    def test44_path_to_uri(self):
        """Test uri_to_path method."""
        h = mockedLDPHandler()
        h.base_uri = 'http://localhost:8000'
        self.assertEqual(h.path_to_uri(''), 'http://localhost:8000')
        self.assertEqual(h.path_to_uri('/'), 'http://localhost:8000')
        self.assertEqual(h.path_to_uri('/abc'), 'http://localhost:8000/abc')

    def test45_uri_to_path(self):
        """Test uri_to_path method."""
        h = mockedLDPHandler()
        self.assertEqual(h.uri_to_path('http://localhost:8000'), '/')
        self.assertEqual(h.uri_to_path('http://localhost:8000/'), '/')
        self.assertEqual(h.uri_to_path('http://localhost:8000/abc'), '/abc')
        self.assertEqual(h.uri_to_path('http://localhost:8000/abc/'), '/abc/')

    def test46_set_allow(self):
        """Test set_allow method."""
        h = mockedLDPHandler()
        h.support_delete = False
        h.set_header = MagicMock()
        h.set_allow()
        h.set_header.assert_called_with('Allow', 'GET, HEAD, OPTIONS, PUT')
        h.support_delete = True
        h.set_header = MagicMock()
        h.set_allow()
        h.set_header.assert_called_with('Allow', 'GET, HEAD, OPTIONS, PUT, DELETE')
        # add different resources
        h.set_header = MagicMock()
        h.set_allow(LDPRS())
        h.set_header.assert_has_calls([call('Accept-Patch', 'application/sparql-update'),
                                       call('Allow', 'GET, HEAD, OPTIONS, PUT, DELETE, PATCH')])
        h.set_header = MagicMock()
        h.set_allow(LDPC())
        h.set_header.assert_has_calls([call('Accept-Patch', 'application/sparql-update'),
                                       call('Accept-Post', 'text/turtle, application/ld+json'),
                                       call('Allow', 'GET, HEAD, OPTIONS, PUT, DELETE, PATCH, POST')])

    def test50_confirm(self):
        """Test confirm method."""
        h = mockedLDPHandler()
        h.write = MagicMock()
        h.set_header = MagicMock()
        h.confirm("blah!", 987)
        h.write.assert_called_with('987 - blah!\n')
        h.set_header.assert_called_with('Content-Type', 'text/plain')


def mockedStatusHandler(method='GET', uri='/status', headers=None, body=None):
    """StatsusHandler with appropriate Application and HTTPRequest mocking."""
    if headers is not None:
        headers = HTTPHeaders(headers)
    request = HTTPRequest(method=method, uri=uri, headers=headers, body=body,
                          connection=Mock())
    return StatusHandler(Application(), request)


class TestStatusHandler(unittest.TestCase):
    """TestStatusHandler class to run tests on StatusHandler."""

    def test01_create_and_initialize(self):
        """Create StatusHandler object."""
        h = mockedStatusHandler()
        self.assertTrue(h)

    def test02_get(self):
        """Test with data in store."""
        h = mockedStatusHandler()
        h.store = Store('uri:')
        r = LDPNR(content=b'hello')
        h.store.add(r, uri='uri:abc1')
        h.store.delete(uri='uri:abc1')
        h.store.add(r, uri='uri:abc2')
        h.store.add(Exception(), uri='uri:abc3')  # Exception does not have type_label property
        h.write = MagicMock()
        h.get()
        h.write.assert_has_calls([call('Store has\n'),
                                  call('  * 2 active resources\n'),
                                  call('    * uri:abc2 - LDPNR\n'),
                                  call("    * uri:abc3 - <class 'Exception'>\n"),
                                  call('  * 1 deleted resources\n'),
                                  call('    * uri:abc1 - deleted\n')])


class TestApp(AsyncHTTPTestCase):
    """TestApp class to run tests on a running server.

    See http://www.tornadoweb.org/en/stable/testing.html#tornado.testing.AsyncHTTPTestCase

    The AsyncHTTPTestCase and the get_app() method provide a framework to run
    the Tornado application and then make calls that mimic HTTP calls and
    return a response object that can then be examined. The tests here
    check that server functions are connect to the right HTTP paths etc..
    """

    def get_app(self):
        """Get trilpy application with some basic config."""
        return make_app(store=Store('http://localhost/'), no_auth=True)

    def test01_ldphandler(self):
        """Test LDPHandler."""
        response = self.fetch('/')
        self.assertEqual(response.code, 404)
        response = self.fetch('/', method="HEAD")
        self.assertEqual(response.code, 404)

    def test02_status(self):
        """Test StatusHandler."""
        response = self.fetch('/status')
        self.assertEqual(response.code, 200)
        self.assertIn(b'Store has', response.body)

    def test03_favicon(self):
        """Test static file for favicon."""
        response = self.fetch('/favicon.ico')
        self.assertEqual(response.code, 200)
        self.assertEqual(len(response.body), 1150)

    def test04_constraints(self):
        """Test static file for constraints.txt."""
        response = self.fetch('/constraints.txt')
        self.assertEqual(response.code, 200)
        self.assertIn(b'Constraints document', response.body)
