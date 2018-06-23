"""LDPRS tests."""
import unittest
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF
from trilpy.ldprs import LDPRS, PatchFailed
from trilpy.namespace import LDP


class TestAll(unittest.TestCase):
    """TestAll class to run tests."""

    def test01_init(self):
        """Test initialization."""
        r = LDPRS()
        self.assertTrue(isinstance(r.content, Graph))
        r = LDPRS(content='abc')
        self.assertEqual(r.content, 'abc')

    def test02_len(self):
        """Test len for length of content."""
        r = LDPRS()
        self.assertEqual(len(r), 0)
        r.content.add((URIRef('s1'), URIRef('p1'), URIRef('o1')))
        self.assertEqual(len(r), 1)

    def test03_uriref(self):
        """Test uriref property."""
        r = LDPRS()
        self.assertEqual(r.uriref, URIRef(''))
        r = LDPRS('my-uri')
        self.assertEqual(r.uriref, URIRef('my-uri'))

    def test04_parse_turtle(self):
        """Parse turtle."""
        r = LDPRS()
        r.parse(b'<http://ex.org/a> <http://ex.org/b> "1".')
        self.assertEqual(len(r.content), 1)
        r = LDPRS()
        r.parse(b'<http://ex.org/a> <http://ex.org/b> "1".',
                content_type='text/turtle')
        self.assertEqual(len(r.content), 1)
        r = LDPRS()
        r.parse(b'<> <http://ex.org/a> "123".',
                context="http://x.y/a")
        self.assertEqual(len(r.content), 1)
        for (s, p, o) in r.content:
            self.assertEqual(str(s), 'http://x.y/a')
            self.assertEqual(str(p), 'http://ex.org/a')
            self.assertEqual(str(o), '123')

    def test05_parse_json_ld(self):
        """Parse JSON-LD."""
        r = LDPRS()
        r.parse(b'{ "@id": "http://ex.org/a", "http://ex.org/b": "123"}',
                content_type='application/ld+json')
        self.assertEqual(len(r.content), 1)

    def test06_patch(self):
        """Test PATCH update."""
        r = LDPRS()
        r.parse('''
            @prefix x: <http://example.org/> .
            x:simeon x:has x:pizza .
            ''')
        sparql_update = '''
            PREFIX x: <http://example.org/>
            DELETE { ?s x:has ?o . }
            INSERT { ?s x:ate ?o .
                     ?o x:was_eaten_by ?s . }
            WHERE { ?s x:has ?o . }
            '''
        self.assertEqual(len(r.content), 1)
        r.patch(sparql_update, 'application/sparql-update')
        self.assertEqual(len(r.content), 2)
        self.assertEqual(len(list(r.content.triples((None, URIRef('http://example.org/has'), None)))), 0)
        self.assertEqual(len(list(r.content.triples((None, URIRef('http://example.org/ate'), None)))), 1)
        self.assertEqual(len(list(r.content.triples((None, URIRef('http://example.org/was_eaten_by'), None)))), 1)
        # bad type
        self.assertRaises(PatchFailed, r.patch, sparql_update, 'bad/type')
        # bad update command
        self.assertRaises(PatchFailed, r.patch, 'update syntax error', 'application/sparql-update')
        # try update at attempts to change containment triples

    def test10_get_container_type(self):
        """Test extraction of container type."""
        r = LDPRS()
        self.assertEqual(r.get_container_type(context="http://ex.org/aa"), None)
        self.assertEqual(r.get_container_type(context="http://ex.org/aa", default=LDP.BasicContainer), LDP.BasicContainer)
        r.parse(b'<http://ex.org/aa> <http://ex.org/b> "1".')
        self.assertEqual(r.get_container_type(context="http://ex.org/aa"), None)
        r.parse(b'<http://ex.org/aa> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://ex.org/some_type>.')
        self.assertEqual(r.get_container_type(context="http://ex.org/aa"), None)
        r.parse(b'<http://ex.org/aa> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/ns/ldp#DirectContainer>.')
        self.assertEqual(r.get_container_type(context="http://ex.org/aa"), LDP.DirectContainer)
        r.parse(b'<http://ex.org/aa> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/ns/ldp#IndirectContainer>.')
        self.assertRaises(Exception, r.get_container_type, context="http://ex.org/aa")
        self.assertEqual(r.get_container_type(context="http://ex.org/NOT_aa"), None)

    def test11_extract_containement_triples(self):
        """Test extraction of containment triples."""
        uri = URIRef('http://ex.org/klm')
        c1 = (uri, LDP.contains, URIRef('http://ex.org/c1'))
        c2 = (uri, LDP.contains, URIRef('http://ex.org/c2'))
        g = Graph()
        g.add(c1)
        g.add(c2)
        g.add((uri, RDF.type, URIRef('http://ex.org/some_type')))
        r = LDPRS(content=g)
        cg = r.extract_containment_triples()
        self.assertEqual(len(r.content), 1)
        self.assertEqual(len(cg), 2)
        self.assertIn(c1, cg)
        self.assertIn(c2, cg)

    def test20_serialize(self):
        """Test some simple serialization cases."""
        uri = URIRef('http://ex.org/ldprs')
        g = Graph()
        g.add((uri, RDF.type, URIRef('http://ex.org/some_type')))
        g.add((URIRef('http://ex.org/a'), URIRef('http://ex.org/b'), Literal('LITERAL')))
        r = LDPRS(uri=uri, content=g)
        s = r.serialize()
        self.assertIn('@prefix ldp: <http://www.w3.org/ns/ldp#> .', s)
        self.assertIn('ldprs', s)  # might prefix or not
        self.assertIn('some_type', s)  # might prefix or not
        self.assertIn('ldp:RDFSource', s)
        self.assertIn('ldp:Resource', s)
        self.assertIn('"LITERAL"', s)
        # Test omits
        s = r.serialize(omits=['content'])
        self.assertIn('ldprs', s)  # might prefix or not
        self.assertNotIn('some_type', s)  # might prefix or not
        self.assertIn('ldp:RDFSource', s)
        self.assertIn('ldp:Resource', s)
        self.assertNotIn('"LITERAL"', s)
        self.assertNotIn('"Wombat"', s)
        # Test extra
        eg = Graph()
        eg.add((URIRef('info:Happy'), URIRef('info:Lazy'), Literal('Wombat')))
        s = r.serialize(extra=eg)
        self.assertIn('"Wombat"', s)

    def test30_add_server_managed_triples(self):
        """Test addition of server manages triples to graph."""
        # CURRENTLY SAME AS JUST ADDING TYPE TRIPLES
        r = LDPRS('http://ex.org/xyz')
        g = Graph()
        r.add_server_managed_triples(g)
        self.assertEqual(len(g), 2)

    def test31_add_type_triples(self):
        """Test addition of build in types to graph."""
        r = LDPRS('http://ex.org/abc')
        g = Graph()
        r.add_type_triples(g)
        self.assertEqual(len(g), 2)

    def test32_media_to_rdflib_type(self):
        """Test media_ lookup and conversion."""
        r = LDPRS()
        self.assertEqual(r._media_to_rdflib_type('text/turtle'), 'turtle')
        self.assertRaises(Exception, r._media_to_rdflib_type, 'elephants')

    def test33_server_managed_triples(self):
        """Test set of server managed triples."""
        r = LDPRS('http://ex.org/cde')
        g = r.server_managed_triples()
        self.assertEqual(len(g), 2)
        self.assertIn((URIRef('http://ex.org/cde'), RDF.type, LDP.RDFSource), g)
        self.assertIn((URIRef('http://ex.org/cde'), RDF.type, LDP.Resource), g)

    def test35_containment_triples(self):
        """Test null iterator for containment triples."""
        ct = list(LDPRS().containment_triples())
        self.assertEqual(ct, [])

    def test36_triples(self):
        """Test triples()."""
        r = LDPRS()
        g = list(r.triples((None, None, URIRef('info:aaa'))))
        self.assertEqual(len(g), 0)
        r.parse(b'<info:bbb> <info:bbb> <info:aaa>.')
        r.parse(b'<info:ccc> <info:ccc> "info:bbb".')  # not a URI ref!
        g = list(r.triples((None, None, URIRef('info:aaa'))))
        self.assertEqual(len(g), 1)
        self.assertEqual(g[0], (URIRef('info:bbb'), URIRef('info:bbb'), URIRef('info:aaa')))
        g = list(r.triples((None, None, URIRef('info:bbb'))))
        self.assertEqual(len(g), 0)
        r.parse(b'<http://ex.org/a> <http://ex.org/b> <info:bbb>.')
        g = list(r.triples((None, None, URIRef('info:bbb'))))
        self.assertEqual(len(g), 1)
        self.assertEqual(g[0], (URIRef('http://ex.org/a'), URIRef('http://ex.org/b'), URIRef('info:bbb')))

    def test40_compute_etag(self):
        """Test computation of etag."""
        r = LDPRS()
        self.assertEqual(r._compute_etag(), 'W/"d41d8cd98f00b204e9800998ecf8427e"')
        r.parse(b'<http://ex.org/a> <http://ex.org/b> <http://ex.org/c>.')
        self.assertEqual(r._compute_etag(), 'W/"d06b10aa24d65ebf1fc913ce2e8d23ff"')
        r.parse(b'<http://ex.org/a> <http://ex.org/b> "hello".')
        self.assertEqual(r._compute_etag(), 'W/"5777dd3a4bc5065c7ed42bb86655c83f"')
        r = LDPRS()
        r.parse(b'<http://ex.org/d> <http://ex.org/e> [ <http://ex.org/f> "111"; <http://ex.org/g> "222"].')
        self.assertEqual(r._compute_etag(), 'W/"afe90adc3b4a1778ee5c4bb32083b061"')
        # This graph is different from the previous one because
        # it has two BNodes instead of one, and ETag will differ
        r = LDPRS()
        r.parse(b'<http://ex.org/d> <http://ex.org/e1> [ <http://ex.org/f> "111" ].' +
                b'<http://ex.org/d> <http://ex.org/e2> [ <http://ex.org/g> "222" ].')
        self.assertEqual(r._compute_etag(), 'W/"f1c12772ce8d7e485155601c2c095d2b"')
        # This graph is different from the previous one but
        # will end up with the same ETag because BNodes are conflated
        r = LDPRS()
        r.parse(b'<http://ex.org/d> <http://ex.org/e2> [ <http://ex.org/f> "111" ].' +
                b'<http://ex.org/d> <http://ex.org/e1> [ <http://ex.org/g> "222" ].')
        self.assertEqual(r._compute_etag(), 'W/"f1c12772ce8d7e485155601c2c095d2b"')
