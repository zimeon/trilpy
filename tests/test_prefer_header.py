"""prefer_header tests."""
import unittest
from trilpy.prefer_header import parse_prefer_header, find_preference, find_return_representation, parse_prefer_return_representation


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

    def test03_find_preference(self):
        """Extract particular preference."""
        params = find_preference(['foo; bar'], 'foo')
        self.assertEqual(params, ['bar'])
        params = find_preference(['foo; bar; baz'], 'foo')
        self.assertEqual(params, ['bar', 'baz'])
        params = find_preference(['foo; bar; baz'], 'bar')
        self.assertEqual(params, ())

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
        # Empty
        (ptype, uris) = find_return_representation([])
        self.assertEqual(ptype, None)
        (ptype, uris) = find_return_representation(['a; b="c"'])
        self.assertEqual(ptype, None)
        # Error
        self.assertRaises(Exception, find_return_representation,
                          ['return=representation; omit="a"; include="b"'])
        self.assertRaises(Exception, find_return_representation,
                          ['return=representation; foo'])
        self.assertRaises(Exception, find_return_representation,
                          ['return=representation;foo = bar'])

    def test05_ldp_return_representation_omits(self):
        """Get set of omits."""
        omits, includes = parse_prefer_return_representation([])
        self.assertEqual(omits, set())
        self.assertEqual(includes, set())
        omits, includes = parse_prefer_return_representation([
            'return=representation; include="http://www.w3.org/ns/ldp#PreferMinimalContainer"'])
        self.assertEqual(omits, set(['membership', 'containment']))
        self.assertEqual(includes, set())
        omits, includes = parse_prefer_return_representation([
            'return = representation; omit ="http://www.w3.org/ns/ldp#PreferMembership http://www.w3.org/ns/ldp#PreferContainment"'])
        self.assertEqual(omits, set(['membership', 'containment']))
        self.assertEqual(includes, set())
        omits, includes = parse_prefer_return_representation([
            'return = representation; include="http://www.w3.org/ns/ldp#PreferMembership http://www.w3.org/ns/ldp#PreferContainment"'])
        self.assertEqual(omits, set(['content']))
        self.assertEqual(includes, set())
        omits, includes = parse_prefer_return_representation([
            'return=representation; include="http://example.org/other/include"'])
        self.assertEqual(omits, set())
        self.assertEqual(includes, set(['http://example.org/other/include']))
        omits, includes = parse_prefer_return_representation([
            'return=representation; include="http://example.org/other/include1 http://example.org/other/include2"'])
        self.assertEqual(omits, set())
        self.assertEqual(includes, set(['http://example.org/other/include1', 'http://example.org/other/include2']))
        # Junk data
        omits, includes = parse_prefer_return_representation(['aaa', 'foo=bar'])
        self.assertEqual(omits, set())
        self.assertEqual(includes, set())
        omits, includes = parse_prefer_return_representation(1)
        self.assertEqual(omits, set())
        self.assertEqual(includes, set())
