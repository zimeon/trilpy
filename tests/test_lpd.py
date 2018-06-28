"""LDP tests."""
import unittest
from trilpy.ldp import LDPNR_URI, LDPRS_URI, LDPC_URI, LDPBC_URI, LDPDC_URI, LDPIC_URI, is_ldp_same_or_sub_type


class TestAll(unittest.TestCase):
    """TestAll class to run tests."""

    def test01_constants(self):
        """Test constants, sanity check."""
        self.assertEqual(LDPNR_URI, 'http://www.w3.org/ns/ldp#NonRDFSource')
        self.assertEqual(LDPBC_URI, 'http://www.w3.org/ns/ldp#BasicContainer')

    def test01_is_ldp_same_or_sub_type(self):
        """Test is_ldp_same_or_sub_type."""
        self.assertTrue(is_ldp_same_or_sub_type(LDPNR_URI, LDPNR_URI))
        self.assertFalse(is_ldp_same_or_sub_type(LDPNR_URI, LDPRS_URI))
        self.assertFalse(is_ldp_same_or_sub_type(LDPRS_URI, LDPC_URI))
        self.assertFalse(is_ldp_same_or_sub_type(LDPC_URI, LDPBC_URI))
        self.assertTrue(is_ldp_same_or_sub_type(LDPBC_URI, LDPRS_URI))
        self.assertTrue(is_ldp_same_or_sub_type(LDPBC_URI, LDPC_URI))
        self.assertTrue(is_ldp_same_or_sub_type(LDPBC_URI, LDPBC_URI))
        self.assertFalse(is_ldp_same_or_sub_type(LDPBC_URI, 'unknown'))
        self.assertFalse(is_ldp_same_or_sub_type('unknown', LDPRS_URI))
