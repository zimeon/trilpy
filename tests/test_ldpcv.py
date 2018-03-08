"""LDPCv tests."""
import unittest
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF
from trilpy.ldpcv import LDPCv
from trilpy.namespace import LDP


class TestAll(unittest.TestCase):
    """TestAll class to run tests."""

    def test05_timemap_object(self):
        """Test timemap_object property."""
        r = LDPCv('info:ldpcv')
        r.original = 'info:orig'
        tm = r.timemap_object
        self.assertEqual(tm.timegate, 'info:orig')
        self.assertEqual(tm.timemap, 'info:ldpcv')

    def test06_serialize(self):
        """Test some simple serialization cases."""
        uri = URIRef('http://ex.org/an_ldpcv')
        g = Graph()
        g.add((uri, RDF.type, URIRef('http://ex.org/some_type')))
        g.add((URIRef('http://ex.org/a'), URIRef('http://ex.org/b'), Literal('Denali')))
        r = LDPCv(uri=uri, content=g)
        s = r.serialize(omits=None, extra=None)
        self.assertIn('@prefix ldp: <http://www.w3.org/ns/ldp#> .', s)
        self.assertIn('an_ldpcv', s)  # might prefix or not
        self.assertIn('some_type', s)  # might prefix or not
        self.assertIn('ldp:RDFSource', s)
        self.assertIn('ldp:Resource', s)
        self.assertIn('"Denali"', s)
        # Now specify timemap, first bad data
        self.assertRaises(Exception, r.serialize, content_type='application/link-format')
        # and then good data
        r.original = 'info:the_orig'
        tm = r.serialize(content_type='application/link-format')
        self.assertIn('<http://ex.org/an_ldpcv>', tm)
        self.assertIn('<info:the_orig', tm)
