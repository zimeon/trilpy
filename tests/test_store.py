"""tirlpy store tests."""
import unittest
from rdflib import URIRef
from trilpy.store import Store, KeyDeleted
from trilpy import LDPR, LDPRS, LDPC, ACLR


class TestAll(unittest.TestCase):
    """TestAll class to run tests."""

    def test01_create(self):
        """Check create."""
        s = Store('http://ex.org/')
        self.assertEqual(s.base_uri, 'http://ex.org/')
        self.assertRaises(TypeError, Store)

    def test02_add(self):
        """Test addition of resource."""
        s = Store('http://ex.org')
        # resource with known URI
        r1 = LDPR(content='abc')
        uri = s.add(r1, uri='http://a.b/')
        self.assertEqual(uri, 'http://a.b/')
        # resource with no URI
        r2 = LDPR(content='bcd')
        uri = s.add(r2)
        self.assertRegex(uri, r'''http://ex.org/''')
        # normalization of base_uri to form without trailing /
        uri3 = s.add(LDPR(), uri='http://ex.org/')
        self.assertEqual(uri3, 'http://ex.org')

    def test03_delete(self):
        """Test deletion of resource."""
        s = Store('http://ex.org/')
        uri = s.add(LDPR(content='def'))
        self.assertEqual(s[uri].content, 'def')
        s.delete(uri)
        self.assertRaises(KeyDeleted, s.__getitem__, uri)

    def test04_getitem(self):
        """Test getitem."""
        s = Store('http://ex.org/')
        self.assertRaises(KeyError, s.__getitem__, 'http://ex.org/')
        self.assertRaises(KeyError, s.__getitem__, 'http://ex.org/a-z')
        uri = s.add(LDPR(), uri='http://ex.org/bbb')
        self.assertTrue(s['http://ex.org/bbb'])
        s.delete('http://ex.org/bbb')
        self.assertRaises(KeyDeleted, s.__getitem__, 'http://ex.org/bbb')

    def test05_resources_access(self):
        """Test other functions providing access to resources dict from store."""
        s = Store('http://x.o/')
        s.add(LDPR())
        uri = s.add(LDPR())
        s.add(LDPR())
        self.assertEqual(len(s), 3)
        self.assertEqual(len(s.items()), 3)
        self.assertEqual(len(set(iter(s))), 3)
        self.assertTrue(uri in s)
        self.assertFalse('abc' in s)

    def test06_get_uri(self):
        """Test URI generation."""
        s = Store('http://x.o/')
        self.assertEqual(s._get_uri('http://x.o/a/', 'b'), 'http://x.o/a/b')
        self.assertEqual(s._get_uri('http://x.o/a/anything', 'b'), 'http://x.o/a/b')
        s.add(LDPR(), uri='http://x.o/a/c')
        self.assertNotEqual(s._get_uri('http://x.o/a/', 'c'), 'a/c')  # can't have same again
        # With no inputs we get a number on the base_uri
        uri1 = s._get_uri()
        s.add(LDPR(), uri=uri1)
        self.assertRegex(uri1, r'''\/(\d+)$''')
        uri2 = s._get_uri()
        self.assertRegex(uri2, r'''\/(\d+)$''')
        self.assertNotEqual(uri1, uri2)

    def test07_individual_acl(self):
        """Test access to individual resource ACL."""
        s = Store('http://x.o/')
        uri = s.add(LDPR(), uri='http://x.o/a/c')
        # no acl defined
        acl = s.individual_acl(uri)
        self.assertNotEqual(uri, acl)
        self.assertRegex(acl, uri + r'''\S+$''')
        # acl defined
        s[uri].acl = 'the_acl'
        self.assertEqual(s.individual_acl(uri), 'the_acl')

    def test08_acl(self):
        """Test location of effective ACL."""
        s = Store('http://x.o/')
        # resource has no acl
        uri = s.add(LDPR())
        self.assertEqual(s.acl(uri), s.acl_default)
        # resource has acl
        acl = s.add(ACLR('http://x.o/an_acl'))
        uri1 = s.add(LDPC(acl=acl))
        self.assertEqual(s.acl(uri1), acl)
        # sub-containers will inherit
        uri2 = s.add(LDPC(), context=uri1)
        self.assertEqual(s.acl(uri2), acl)
        uri3 = s.add(LDPC(), context=uri2)
        self.assertEqual(s.acl(uri3), acl)
        # set small inheritance limit
        s.acl_inheritance_limit = 1
        self.assertRaises(Exception, s.acl, uri3)
        s.acl_inheritance_limit = 2
        self.assertEqual(s.acl(uri3), acl)
