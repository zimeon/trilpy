"""prefer_header tests."""
import unittest
from trilpy.prefer_header import parse_prefer_header, find_return_representation, ldp_return_representation_omits


class TestAll(unittest.TestCase):
    """TestAll class to run tests."""

    def test01_parse_prefer_header(self):
        """Parse prefer headers."""
        (pref, params) = parse_prefer_header('foo; bar')
        self.assertEqual(pref, 'foo')
        self.assertEqual(params, ['bar'])
        (pref, params) = parse_prefer_header('foo; bar=""')
        self.assertEqual(pref, 'foo')
        self.assertEqual(params, ['bar'])
        (pref, params) = parse_prefer_header('foo=""; bar')
        self.assertEqual(pref, 'foo')
        self.assertEqual(params, ['bar'])

    def test02_parse_prefer_header_ldp(self):
        """Parse prefer headers from LDP spec."""
        (pref, params) = parse_prefer_header(
            'return=representation; include="http://www.w3.org/ns/ldp#PreferMinimalContainer"')
        self.assertEqual(pref, 'return=representation')
        self.assertEqual(params, ['include="http://www.w3.org/ns/ldp#PreferMinimalContainer"'])
        (pref, params) = parse_prefer_header(
            'return = representation ; omit = "http://www.w3.org/ns/ldp#PreferMembership http://www.w3.org/ns/ldp#PreferContainment"')
        self.assertEqual(pref, 'return=representation')
        self.assertEqual(params, ['omit="http://www.w3.org/ns/ldp#PreferMembership http://www.w3.org/ns/ldp#PreferContainment"'])

    def test04_find_return_representation(self):
        """Get return=representation prefernce."""
        (ptype, uris) = find_return_representation([
            'foo; bar',
            'return=representation; include="http://www.w3.org/ns/ldp#PreferMinimalContainer"'])
        self.assertEqual(ptype, 'include')
        self.assertEqual(uris, ['http://www.w3.org/ns/ldp#PreferMinimalContainer'])
        (ptype, uris) = find_return_representation([
            'foo; bar',
            'return = representation; omit ="http://www.w3.org/ns/ldp#PreferMembership http://www.w3.org/ns/ldp#PreferContainment"',
            'something-else'])
        self.assertEqual(ptype, 'omit')
        self.assertEqual(uris, ['http://www.w3.org/ns/ldp#PreferMembership',
                                'http://www.w3.org/ns/ldp#PreferContainment'])

    def test05_ldp_return_representation_omits(self):
        """Get set of omits."""
        omits = ldp_return_representation_omits([])
        self.assertEqual(omits, set())
        omits = ldp_return_representation_omits([
            'return=representation; include="http://www.w3.org/ns/ldp#PreferMinimalContainer"'])
        self.assertEqual(omits, set(['membership', 'containment']))
        omits = ldp_return_representation_omits([
            'return = representation; omit ="http://www.w3.org/ns/ldp#PreferMembership http://www.w3.org/ns/ldp#PreferContainment"'])
        self.assertEqual(omits, set(['membership', 'containment']))
