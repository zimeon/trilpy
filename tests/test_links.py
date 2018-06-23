"""Links tests."""
import unittest

from trilpy.links import RequestLinks, ResponseLinks, HTTPError


class TestRequestLinks(unittest.TestCase):
    """TestAll class to run tests."""

    def test01_init(self):
        """Test RequestLinks creation."""
        rl = RequestLinks()
        self.assertEqual(rl.links, None)
        rl = RequestLinks(link_headers=['<a>; rel="b"'])
        self.assertEqual(len(rl.links), 1)
        rl = RequestLinks(link_dict={'a': ['b'], 'c': ['d']})
        self.assertEqual(len(rl.links), 2)

    def test02_parse(self):
        """Test parse method."""
        rl = RequestLinks()
        self.assertEqual(rl.parse([]), {})
        # Result same for single or multiple headers
        self.assertEqual(rl.parse(['<b>; rel="a"', '<d>; rel="c"', '<e>; rel="a"']),
                         {'a': ['b', 'e'], 'c': ['d']})
        self.assertEqual(rl.parse(['<b>;rel="a",<d>; rel="c",<e>; rel="a"']),
                         {'a': ['b', 'e'], 'c': ['d']})

    def test03_rel(self):
        """Test rel method to extract links with given relation."""
        rl = RequestLinks(link_dict={'a': ['b1', 'b2'], 'c': ['d']})
        self.assertEqual(rl.rel('a'), ['b1', 'b2'])
        self.assertEqual(rl.rel('c'), ['d'])

    def test04_types(self):
        """Test types property."""
        rl = RequestLinks(link_headers=[])
        self.assertEqual(rl.types, [])
        rl = RequestLinks(link_headers=['a'])
        self.assertEqual(rl.types, [])
        rl = RequestLinks(link_headers=['<bb>; rel="type"'])
        self.assertEqual(rl.types, ['bb'])
        rl = RequestLinks(link_headers=['<cc>; rel="type", <dd>; rel="type", <ee>; rel="other", <ff>; rel="type"'])
        self.assertEqual(rl.types, ['cc', 'dd', 'ff'])

    def test05_ldp_type(self):
        """Test ldp_type property."""
        rl = RequestLinks(link_dict={'type': ['bb']})
        self.assertEqual(rl.ldp_type, None)
        rl = RequestLinks(link_dict={'type': ['http://www.w3.org/ns/ldp#NonRDFSource']})
        self.assertEqual(rl.ldp_type, 'http://www.w3.org/ns/ldp#NonRDFSource')
        rl = RequestLinks(link_dict={'type': ['http://www.w3.org/ns/ldp#NonRDFSource', 'cc']})
        self.assertEqual(rl.ldp_type, 'http://www.w3.org/ns/ldp#NonRDFSource')
        rl = RequestLinks(link_dict={'type': ['dd', 'http://www.w3.org/ns/ldp#NonRDFSource']})
        self.assertEqual(rl.ldp_type, 'http://www.w3.org/ns/ldp#NonRDFSource')
        rl = RequestLinks(link_dict={'type': ['http://www.w3.org/ns/ldp#RDFSource']})
        self.assertEqual(rl.ldp_type, 'http://www.w3.org/ns/ldp#RDFSource')
        # Incompatible LDPRS and LDPNR
        rl = RequestLinks(link_dict={'type': ['http://www.w3.org/ns/ldp#RDFSource',
                                              'http://www.w3.org/ns/ldp#NonRDFSource']})
        self.assertRaises(HTTPError, lambda: rl.ldp_type)
        rl = RequestLinks(link_dict={'type': ['http://www.w3.org/ns/ldp#RDFSource',
                                              'http://www.w3.org/ns/ldp#BasicContainer']})
        self.assertEqual(rl.ldp_type, 'http://www.w3.org/ns/ldp#BasicContainer')
        rl = RequestLinks(link_dict={'type': ['http://www.w3.org/ns/ldp#BasicContainer']})
        self.assertEqual(rl.ldp_type, 'http://www.w3.org/ns/ldp#BasicContainer')
        rl = RequestLinks(link_dict={'type': ['http://www.w3.org/ns/ldp#DirectContainer']})
        self.assertEqual(rl.ldp_type, 'http://www.w3.org/ns/ldp#DirectContainer')
        # Incompatible container types
        rl = RequestLinks(link_dict={'type': ['http://www.w3.org/ns/ldp#BasicContainer',
                                              'http://www.w3.org/ns/ldp#DirectContainer']})
        self.assertRaises(HTTPError, lambda: rl.ldp_type)

    def test06_acl_uri(self):
        """Test acl_uri method."""
        # none
        rl = RequestLinks(link_headers=['<bb>; rel="type"'])
        self.assertEqual(rl.acl_uri(), None)
        self.assertEqual(rl.acl_uri("base:uri"), None)
        # multiple
        rl = RequestLinks(link_headers=['<http://example.org/acl1>; rel="acl"',
                                        '<http://example.org/acl2>; rel="acl"'])
        self.assertRaises(HTTPError, rl.acl_uri, 'http://example.org/')
        # one (with and without good baseuri)
        rl = RequestLinks(link_headers=['<http://example.org/acl1>; rel="acl"'])
        self.assertEqual(rl.acl_uri('http://example.org/'), 'http://example.org/acl1')
        self.assertRaises(HTTPError, rl.acl_uri, 'http://not-example.org/')


class TestResponseLinks(unittest.TestCase):
    """TestAll class to run tests."""

    def test01_init_and_len(self):
        """Test ResponseLinks creation and len method."""
        rl = ResponseLinks()
        self.assertEqual(rl.links, [])
        self.assertEqual(len(rl), 0)

    def test02_add_and_header(self):
        """Test add method and header property."""
        rl = ResponseLinks()
        rl.add('a', [])
        self.assertEqual(len(rl), 0)
        self.assertEqual(rl.header, '')
        rl.add('a', ['b', 'b', 'c'])
        self.assertEqual(len(rl), 2)
        self.assertEqual(rl.header, '<b>; rel="a", <c>; rel="a"')
        rl.add('a', ['b', 'b', 'c'])
        self.assertEqual(len(rl), 2)
        rl.add('d', ['e'])
        self.assertEqual(len(rl), 3)
        self.assertEqual(rl.header, '<b>; rel="a", <c>; rel="a", <e>; rel="d"')
