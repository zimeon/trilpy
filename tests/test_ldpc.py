"""LDPC tests."""
import unittest
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF
from trilpy.ldpc import LDPC, UnsupportedContainerType
from trilpy.namespace import LDP


class TestAll(unittest.TestCase):
    """TestAll class to run tests."""

    def test01_init(self):
        """Test initialization."""
        r = LDPC()
        self.assertEqual(len(r.content), 0)
        self.assertEqual(r.container_type, LDP.BasicContainer)
        # Explicit types
        self.assertEqual(r.container_type, LDP.BasicContainer)
        r = LDPC(container_type=LDP.DirectContainer)
        self.assertEqual(r.container_type, LDP.DirectContainer)
        r = LDPC(container_type=LDP.IndirectContainer)
        self.assertEqual(r.container_type, LDP.IndirectContainer)
        # Bad type
        self.assertRaises(UnsupportedContainerType, LDPC, container_type=LDP.UNKNOWNContainer)

    def test02_add_server_managed_triples(self):
        """Test addition of server managed triples to RDF."""
        pass

    def test03_add_containment_triples(self):
        """Test addition of containment triples to RDF."""
        r = LDPC('uri:self-act')
        g = Graph()
        r.add_containment_triples(g)
        self.assertEqual(len(g), 0)
        r.add_contained('uri:act1')
        r.add_contained('uri:act2')
        r.add_containment_triples(g)
        self.assertEqual(len(g), 2)
        self.assertIn((URIRef('uri:self-act'), LDP.contains, URIRef('uri:act1')), list(r.containment_triples()))

    def test04_add_membership_triples(self):
        """Test addition of member triples to RDF."""
        r = LDPC('uri:self-amt')
        g = Graph()
        r.add_membership_triples(g)
        self.assertEqual(len(g), 0)
        r.add_member('uri:mem1')
        r.add_contained('uri:act1')
        r.add_contained('uri:act2')
        r.add_membership_triples(g)
        self.assertEqual(len(g), 1)
        self.assertIn((URIRef('uri:self-amt'), LDP.member, URIRef('uri:mem1')), list(r.membership_triples()))

    def test05_containment_triples(self):
        """Test generation of containment triples."""
        r = LDPC()
        ct = list(r.containment_triples())
        self.assertEqual(len(ct), 0)
        r.add_contained('uri:c1')
        ct = list(r.containment_triples())
        self.assertEqual(len(ct), 1)

    def test06_membership_triples(self):
        """Test generation of membership triples."""
        r = LDPC()
        mt = list(r.membership_triples())
        self.assertEqual(len(mt), 0)

    def test07_rdf_types(self):
        """Test RDF types."""
        r = LDPC()
        self.assertIn(LDP.Resource, r.rdf_types)
        self.assertIn(LDP.RDFSource, r.rdf_types)
        self.assertIn(LDP.BasicContainer, r.rdf_types)

    def test10_add_del_contains(self):
        """Test addition and deletion of containment triples."""
        r = LDPC('uri:self-con')
        r.add_contained('uri:c1')
        self.assertEqual(len(list(r.containment_triples())), 1)
        r.add_contained('uri:c2')
        self.assertEqual(len(list(r.containment_triples())), 2)
        r.add_contained('uri:c2')
        self.assertEqual(len(list(r.containment_triples())), 2)
        r.del_contained('uri:c2')
        self.assertEqual(len(list(r.containment_triples())), 1)
        self.assertRaises(KeyError, r.del_contained, 'uri:c2')
        r.add_contained('uri:c3')
        ct = list(r.containment_triples())
        self.assertEqual(len(ct), 2)
        self.assertIn((URIRef('uri:self-con'), LDP.contains, URIRef('uri:c1')), ct)
        self.assertIn((URIRef('uri:self-con'), LDP.contains, URIRef('uri:c3')), ct)

    def test20_add_del_member(self):
        """Test addition and deletion of member triples."""
        r = LDPC('uri:self-mem')
        r.add_member('uri:m1')
        self.assertEqual(len(list(r.membership_triples())), 1)
        r.add_member('uri:m2')
        self.assertEqual(len(list(r.membership_triples())), 2)
        r.add_member('uri:m2')
        self.assertEqual(len(list(r.membership_triples())), 2)
        r.del_member('uri:m2')
        self.assertEqual(len(list(r.membership_triples())), 1)
        self.assertRaises(KeyError, r.del_member, 'uri:m2')
        r.add_member('uri:m3')
        mt = list(r.membership_triples())
        self.assertEqual(len(mt), 2)
        self.assertIn((URIRef('uri:self-mem'), LDP.member, URIRef('uri:m1')), mt)
        self.assertIn((URIRef('uri:self-mem'), LDP.member, URIRef('uri:m3')), mt)
