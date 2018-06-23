"""Tornado server tests."""
import unittest
from unittest.mock import Mock, MagicMock
import tornado.web
from trilpy.links import RequestLinks
from trilpy.tornado import HTTPError, LDPHandler


class TestAll(unittest.TestCase):
    """TestAll class to run tests."""

    def test01_create_LDPHandler(self):
        """Create LDPHandler object."""
        h = LDPHandler(tornado.web.Application(), Mock())
        self.assertTrue(h)

    def test50_confirm(self):
        """Test confirm method."""
        h = LDPHandler(tornado.web.Application(), Mock())
        h.write = MagicMock()
        h.set_header = MagicMock()
        h.confirm("blah!", 987)
        h.write.assert_called_with('987 - blah!\n')
        h.set_header.assert_called_with('Content-Type', 'text/plain')
