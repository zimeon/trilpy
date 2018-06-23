"""Tornado server tests."""
import unittest
from unittest.mock import Mock, MagicMock
from tornado.testing import AsyncHTTPTestCase
from tornado.web import Application, HTTPError
from tornado.httpserver import HTTPRequest
from tornado.httputil import HTTPHeaders

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

    def zztest50_confirm(self):
        """Test confirm method."""
        h = LDPHandler(Application(), Mock())
        h.write = MagicMock()
        h.set_header = MagicMock()
        h.confirm("blah!", 987)
        h.write.assert_called_with('987 - blah!\n')
        h.set_header.assert_called_with('Content-Type', 'text/plain')


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
        store = Store('http://localhost/')
        LDPHandler.store = store
        LDPHandler.base_uri = store.base_uri
        StatusHandler.store = store
        return make_app()

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
