"""LDPR tests."""
import unittest
from trilpy.ldpr import LDPR


class TestAll(unittest.TestCase):
    """TestAll class to run tests."""

    def test01_create(self):
        """Parse turtle."""
        r = LDPR()
        self.assertEqual(len(r.content), 0)

    def test10_compute_etag(self):
        """Test computation of etag."""
        r = LDPR()
        self.assertEqual(r._compute_etag(), '"d41d8cd98f00b204e9800998ecf8427e"')
        r.content = b'hello world, be nice to me!'
        self.assertEqual(r._compute_etag(), '"87bdb247e70d648d5782a4dd943cea76"')
