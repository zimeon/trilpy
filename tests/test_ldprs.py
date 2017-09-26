"""LDPRS tests."""
import unittest
from trilpy.ldprs import LDPRS


class TestAll(unittest.TestCase):
    """TestAll class to run tests."""

    def test01_parse_turtle(self):
        """Parse turtle."""
        r = LDPRS()
        r.parse(b'<http://ex.org/a> <http://ex.org/b> "1".')
        self.assertEqual(len(r.content), 1)
        r = LDPRS()
        r.parse(b'<> <http://ex.org/a> "123".',
                context="http://x.y/a")
        self.assertEqual(len(r.content), 1)
        for (s, p, o) in r.content:
            self.assertEqual(str(s), 'http://x.y/a')
            self.assertEqual(str(p), 'http://ex.org/a')
            self.assertEqual(str(o), '123')

    def test10_compute_etag(self):
        """Test computation of etag."""
        r = LDPRS()
        self.assertEqual(r._compute_etag(), 'W/"d41d8cd98f00b204e9800998ecf8427e"')
        r.parse(b'<http://ex.org/a> <http://ex.org/b> <http://ex.org/c>.')
        self.assertEqual(r._compute_etag(), 'W/"3a56c2ec3f10bd6805c05fdd10d51955"')
        r.parse(b'<http://ex.org/a> <http://ex.org/b> "hello".')
        self.assertEqual(r._compute_etag(), 'W/"0f54b80f79677177774f22e45485f7d9"')
        r.parse(b'<http://ex.org/d> <http://ex.org/e> [ <http://ex.org/f> "111"; <http://ex.org/g> "222"].')
        self.assertEqual(r._compute_etag(), 'W/"296fc3fdd0a0fd9e718687c73696ff60"')
