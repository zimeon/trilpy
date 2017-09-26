"""Digest tests."""
import unittest
from trilpy.digest import Digest, UnsupportedDigest, BadDigest

class TestAll(unittest.TestCase):
    """TestAll class to run tests."""

    def test01_create(self):
        """Create Digest object."""
        d = Digest()
        self.assertEqual(len(d.digests), 0)
        self.assertRaises(BadDigest, Digest, digest_header='bad-digest-header')
        self.assertRaises(UnsupportedDigest, Digest, want_digest_header='unknown-digest-header')

    def test02_parse_digest(self):
        """Test parse_digest."""
        d = Digest()
        d.parse_digest('md5=HUXZLQLMuI/KZ5KDcJPcOA==')
        self.assertEqual(d.digests['md5'], 'HUXZLQLMuI/KZ5KDcJPcOA==')
        d = Digest()
        d.parse_digest('SHA=thvDyvhfIqlvFe+A9MYgxAfm1q5=')
        self.assertEqual(d.digests['sha'], 'thvDyvhfIqlvFe+A9MYgxAfm1q5=')
        d = Digest()
        d.parse_digest('md5=HUXZLQLMuI/KZ5KDcJPcOA==,SHA=thvDyvhfIqlvFe+A9MYgxAfm1q5=')
        self.assertEqual(d.digests['md5'], 'HUXZLQLMuI/KZ5KDcJPcOA==')
        self.assertEqual(d.digests['sha'], 'thvDyvhfIqlvFe+A9MYgxAfm1q5=')
        # Error cases
        self.assertRaises(BadDigest, d.parse_digest, 'bad-digest-header')
        self.assertRaises(BadDigest, d.parse_digest, 'md5')
        self.assertRaises(BadDigest, d.parse_digest, 'MD5')
        self.assertRaises(UnsupportedDigest, d.parse_digest, 'unknown=aaa')
        self.assertRaises(UnsupportedDigest, d.parse_digest, 'md5=HUXZLQLMuI/KZ5KDcJPcOA==,uk=aa')

    def test03_parse_want_digest(self):
        """Test parse_want_digest."""
        d = Digest()
        d.parse_want_digest('md5')
        self.assertEqual(d.want_digest, 'md5')
        d.parse_want_digest('sha-256')
        self.assertEqual(d.want_digest, 'sha-256')
        d.parse_want_digest('MD5;q=0.3, sha;q=1')
        self.assertEqual(d.want_digest, 'sha')
        d.parse_want_digest('MD5;q=0.3,sha;q=1')
        self.assertEqual(d.want_digest, 'sha')
        d.parse_want_digest('md5, sha-999')
        self.assertEqual(d.want_digest, 'md5')
        # Error cases
        self.assertRaises(UnsupportedDigest, d.parse_want_digest, 'bad-digest-header')
        self.assertRaises(UnsupportedDigest, d.parse_want_digest, 'md, sha-999')
        self.assertRaises(UnsupportedDigest, d.parse_want_digest, 'md5;q=0.1, sha-999')
        self.assertRaises(BadDigest, d.parse_want_digest, 'md5;q=0.0, sha;q=0.0')
        self.assertRaises(BadDigest, d.parse_want_digest, 'md5;q=0..0')
        self.assertRaises(BadDigest, d.parse_want_digest, 'md5;q=2.0')
        self.assertRaises(BadDigest, d.parse_want_digest, ';')

    def test04_check(self):
        """Test check method."""
        d = Digest()
        d.digests = {'md5': 'XUFAKrxLKna5cZ2REBfFkg==', 'sha': 'qvTGHdzF6KLavt4PO0gs2a6pQ00='}
        d.check(b'hello')
        # Error cases
        d.digests = {'md5': 'bad-digest'}
        self.assertRaises(BadDigest, d.check, b'hello')
        d.digests = {'md99': 'aa'}
        self.assertRaises(UnsupportedDigest, d.check, b'hello')

