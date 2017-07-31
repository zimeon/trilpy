"""Tornado server tests."""
import unittest
from unittest.mock import Mock
import tornado.web
from trilpy.tornado import HTTPError, LDPHandler


class TestAll(unittest.TestCase):
    """TestAll class to run tests."""

    def test01_create_LDPHandler(self):
        """Create LDPHandler object."""
        h = LDPHandler(tornado.web.Application(), Mock())
        self.assertTrue(h)

    def test20_request_ldp_type(self):
        """Test LDPHandler.request_ldp_type."""
        h = LDPHandler(tornado.web.Application(), Mock())
        h.request.headers = Mock()
        h.request.headers.get_list = Mock(return_value=[])
        self.assertEqual(h.request_ldp_type(), None)
        h.request.headers.get_list = Mock(return_value=['a', 'b'])
        self.assertRaises(HTTPError, h.request_ldp_type)
        h.request.headers.get_list = Mock(return_value=['a'])
        self.assertEqual(h.request_ldp_type(), None)
        h.request.headers.get_list = Mock(return_value=['<bb>; rel="type"'])
        self.assertEqual(h.request_ldp_type(), None)
        h.request.headers.get_list = Mock(return_value=['<http://www.w3.org/ns/ldp#NonRDFSource>; rel="type"'])
        self.assertEqual(h.request_ldp_type(), 'http://www.w3.org/ns/ldp#NonRDFSource')
        h.request.headers.get_list = Mock(return_value=['<http://www.w3.org/ns/ldp#NonRDFSource>; rel="type", <cc>; rel="type"'])
        self.assertEqual(h.request_ldp_type(), 'http://www.w3.org/ns/ldp#NonRDFSource')
        h.request.headers.get_list = Mock(return_value=['<dd>; rel="type", <http://www.w3.org/ns/ldp#NonRDFSource>; rel="type"'])
        self.assertEqual(h.request_ldp_type(), 'http://www.w3.org/ns/ldp#NonRDFSource')
        h.request.headers.get_list = Mock(return_value=['<http://www.w3.org/ns/ldp#RDFSource>; rel="type"'])
        self.assertEqual(h.request_ldp_type(), 'http://www.w3.org/ns/ldp#RDFSource')
        h.request.headers.get_list = Mock(return_value=['<http://www.w3.org/ns/ldp#RDFSource>; rel="type", '
                                                        '<http://www.w3.org/ns/ldp#NonRDFSource>; rel="type"'])
        self.assertRaises(HTTPError, h.request_ldp_type)
        h.request.headers.get_list = Mock(return_value=['<http://www.w3.org/ns/ldp#RDFSource>; rel="type", '
                                                        '<http://www.w3.org/ns/ldp#Container>; rel="type"'])
        self.assertEqual(h.request_ldp_type(), 'http://www.w3.org/ns/ldp#Container')
        h.request.headers.get_list = Mock(return_value=['<http://www.w3.org/ns/ldp#BasicContainer>; rel="type", '
                                                        '<http://www.w3.org/ns/ldp#Container>; rel="type"'])
        self.assertEqual(h.request_ldp_type(), 'http://www.w3.org/ns/ldp#BasicContainer')
        h.request.headers.get_list = Mock(return_value=['<http://www.w3.org/ns/ldp#Container>; rel="type", '
                                                        '<http://www.w3.org/ns/ldp#DirectContainer>; rel="type"'])
        self.assertEqual(h.request_ldp_type(), 'http://www.w3.org/ns/ldp#DirectContainer')
        # FIXME - Following should probably give HTTPError
        h.request.headers.get_list = Mock(return_value=['<http://www.w3.org/ns/ldp#BasicContainer>; rel="type", '
                                                        '<http://www.w3.org/ns/ldp#DirectContainer>; rel="type"'])
        self.assertEqual(h.request_ldp_type(), 'http://www.w3.org/ns/ldp#DirectContainer')
