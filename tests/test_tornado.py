"""Tornado server tests."""
import unittest
from unittest.mock import Mock, MagicMock
import tornado.web
from trilpy.tornado import HTTPError, LDPHandler


class TestAll(unittest.TestCase):
    """TestAll class to run tests."""

    def test01_create_LDPHandler(self):
        """Create LDPHandler object."""
        h = LDPHandler(tornado.web.Application(), Mock())
        self.assertTrue(h)

    def test20_request_types(self):
        """Test LDPHandler.request_types property."""
        h = LDPHandler(tornado.web.Application(), Mock())
        h.request.headers = Mock()
        h.request.headers.get_list = Mock(return_value=[])
        self.assertEqual(h.request_types, [])
        h._request_links = None
        h.request.headers.get_list = Mock(return_value=['a'])
        self.assertEqual(h.request_types, [])
        h._request_links = None
        h.request.headers.get_list = Mock(return_value=['<bb>; rel="type"'])
        self.assertEqual(h.request_types, ['bb'])
        h._request_links = None
        h.request.headers.get_list = Mock(return_value=['<cc>; rel="type", <dd>; rel="type", <ee>; rel="other", <ff>; rel="type"'])
        self.assertEqual(h.request_types, ['cc', 'dd', 'ff'])

    def test21_request_ldp_type(self):
        """Test LDPHandler.request_ldp_type() method."""
        h = LDPHandler(tornado.web.Application(), Mock())
        h._request_links = {'type': ['bb']}
        self.assertEqual(h.request_ldp_type(), None)
        h._request_links = {'type': ['http://www.w3.org/ns/ldp#NonRDFSource']}
        self.assertEqual(h.request_ldp_type(), 'http://www.w3.org/ns/ldp#NonRDFSource')
        h._request_links = {'type': ['http://www.w3.org/ns/ldp#NonRDFSource', 'cc']}
        self.assertEqual(h.request_ldp_type(), 'http://www.w3.org/ns/ldp#NonRDFSource')
        h._request_links = {'type': ['dd', 'http://www.w3.org/ns/ldp#NonRDFSource']}
        self.assertEqual(h.request_ldp_type(), 'http://www.w3.org/ns/ldp#NonRDFSource')
        h._request_links = {'type': ['http://www.w3.org/ns/ldp#RDFSource']}
        self.assertEqual(h.request_ldp_type(), 'http://www.w3.org/ns/ldp#RDFSource')
        h._request_links = {'type': ['http://www.w3.org/ns/ldp#RDFSource',
                                     'http://www.w3.org/ns/ldp#NonRDFSource']}
        self.assertRaises(HTTPError, h.request_ldp_type)
        h._request_links = {'type': ['http://www.w3.org/ns/ldp#RDFSource',
                                     'http://www.w3.org/ns/ldp#Container']}
        self.assertEqual(h.request_ldp_type(), 'http://www.w3.org/ns/ldp#Container')
        h._request_links = {'type': ['http://www.w3.org/ns/ldp#BasicContainer',
                                     'http://www.w3.org/ns/ldp#Container']}
        self.assertEqual(h.request_ldp_type(), 'http://www.w3.org/ns/ldp#BasicContainer')
        h._request_links = {'type': ['http://www.w3.org/ns/ldp#Container',
                                     'http://www.w3.org/ns/ldp#DirectContainer']}
        self.assertEqual(h.request_ldp_type(), 'http://www.w3.org/ns/ldp#DirectContainer')
        # FIXME - Following should probably give HTTPError
        h._request_links = {'type': ['http://www.w3.org/ns/ldp#BasicContainer',
                                     'http://www.w3.org/ns/ldp#DirectContainer']}
        self.assertEqual(h.request_ldp_type(), 'http://www.w3.org/ns/ldp#DirectContainer')

    def test50_confirm(self):
        """Test confirm method."""
        h = LDPHandler(tornado.web.Application(), Mock())
        m = Mock()
        h.write = MagicMock()
        h.set_header = MagicMock()
        h.confirm("blah!", 987)
        h.write.assert_called_with('987 - blah!\n')
        h.set_header.assert_called_with('Content-Type', 'text/plain')
