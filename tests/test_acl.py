"""ACL tests."""
import unittest
from rdflib import URIRef
from trilpy.acl import ACLR
from trilpy.namespace import LDP, ACL


class TestAll(unittest.TestCase):
    """TestAll class to run tests."""

    def test01_create(self):
        """Check create."""
        r = ACLR()
        self.assertEqual(r.type_label, 'ACLR')

    def test02_get_new_hash_uriref(self):
        """Check _get_new_hash_uriref doesn't give dupes."""
        a = ACLR()
        # First new hash
        uriref1 = a._get_new_hash_uriref()
        self.assertTrue(str(uriref1).startswith('#'))
        a.content.add((uriref1, ACL.x, ACL.Y))
        # Second new hash
        uriref2 = a._get_new_hash_uriref()
        self.assertTrue(str(uriref2).startswith('#'))
        self.assertNotEqual(uriref1, uriref2)
        self.assertNotEqual(str(uriref1), str(uriref2))
        # Third new hash
        uriref3 = a._get_new_hash_uriref()
        self.assertTrue(str(uriref3).startswith('#'))
        self.assertNotEqual(uriref1, uriref3)
        self.assertNotEqual(str(uriref1), str(uriref3))

    def test03_add_public_read(self):
        """Check add_public_read."""
        a = ACLR()
        # Raise exception of no _acl_for
        self.assertRaises(Exception, a.add_public_read)
        a._acl_for = 'http://example.org/a'
        # Add public read (twice), check different
        uriref1 = a.add_public_read()
        uriref2 = a.add_public_read()
        self.assertNotEqual(uriref1, uriref2)
