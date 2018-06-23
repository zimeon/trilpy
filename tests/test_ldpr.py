"""LDPR tests."""
import unittest
from unittest.mock import MagicMock
from trilpy.ldpr import LDPR
from trilpy.namespace import LDP


class TestAll(unittest.TestCase):
    """TestAll class to run tests."""

    def test01_create(self):
        """Parse turtle."""
        r = LDPR()
        self.assertEqual(len(r.content), 0)

    def test02_is_ldprv(self):
        """Test is_ldprv."""
        r = LDPR()
        self.assertFalse(r.is_ldprv)
        r.timemap = 1
        self.assertTrue(r.is_ldprv)
        r.original = 1
        self.assertFalse(r.is_ldprv)

    def test03_is_ldprm(self):
        """Test is_ldprm."""
        r = LDPR()
        self.assertFalse(r.is_ldprm)
        r.timemap = 1
        self.assertFalse(r.is_ldprm)
        r.original = 1
        self.assertTrue(r.is_ldprm)

    def test04_is_ldpcv(self):
        """Test is_ldpcv."""
        r = LDPR()
        self.assertFalse(r.is_ldpcv)

    def test05_rdf_type(self):
        """Test rdf_type."""
        r = LDPR()
        self.assertEqual(r.rdf_type, LDP.Resource)

    def test06_rdf_type_uri(self):
        """Test rdf_type_url."""
        r = LDPR()
        self.assertEqual(r.rdf_type_uri, 'http://www.w3.org/ns/ldp#Resource')

    def test07_rdf_types(self):
        """Test rdf_types."""
        r = LDPR()
        self.assertEqual(r.rdf_types, [LDP.Resource])

    def test08_rdf_type_uris(self):
        """est rdf_type_uris."""
        r = LDPR()
        self.assertEqual(r.rdf_type_uris, ['http://www.w3.org/ns/ldp#Resource'])

    def test20_etag(self):
        """Test etag."""
        r = LDPR(content=b'abc')
        self.assertEqual(r.etag, '"900150983cd24fb0d6963f7d28e17f72"')
        # Lazy behavior
        r._compute_etag = MagicMock(return_value='wrong')
        self.assertEqual(r.etag, '"900150983cd24fb0d6963f7d28e17f72"')

    def test21_compute_etag(self):
        """Test computation of etag."""
        r = LDPR()
        self.assertEqual(r._compute_etag(), '"d41d8cd98f00b204e9800998ecf8427e"')
        r.content = b'hello world, be nice to me!'
        self.assertEqual(r._compute_etag(), '"87bdb247e70d648d5782a4dd943cea76"')
