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
