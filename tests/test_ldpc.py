"""LDPC tests."""
import unittest
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF
from trilpy.ldpc import LDPC
from trilpy.namespace import LDP


class TestAll(unittest.TestCase):
    """TestAll class to run tests."""

    def test01_init(self):
        """Test initialization."""
        r = LDPC()
        self.assertEqual(len(r.content), 0)

    def test02_add_server_managed_triples(self):
        pass

    def test03_add_member_triples(self):
        pass 

    def test04_containment_triples(self):
        r = LDPC()
        ct = list(r.containment_triples())
        self.assertEqual(len(ct), 0)

    def test05_rdf_types(self):
        r = LDPC()
        self.assertIn(LDP.Resource, r.rdf_types)
        self.assertIn(LDP.RDFSource, r.rdf_types)
        self.assertIn(LDP.BasicContainer, r.rdf_types)

    def test10_add_del_contained(self):
        """Test addition and deletion of containement triples."""
        r = LDPC('uri:self')
        r.add_contained('uri:1')
        self.assertEqual(len(list(r.containment_triples())), 1)
        r.add_contained('uri:2')
        self.assertEqual(len(list(r.containment_triples())), 2)
        r.add_contained('uri:2')
        self.assertEqual(len(list(r.containment_triples())), 2)
        r.del_contained('uri:2')
        self.assertEqual(len(list(r.containment_triples())), 1)
        self.assertRaises(KeyError, r.del_contained, 'uri:2')
        r.add_contained('uri:3')
        ct = list(r.containment_triples())
        self.assertEqual(len(ct), 2)
        self.assertIn((URIRef('uri:self'), LDP.contains, URIRef('uri:1')), ct)
        self.assertIn((URIRef('uri:self'), LDP.contains, URIRef('uri:3')), ct)

    def test20_add_del_member(self):
        pass