"""An LDPRS - RDF Source."""
from trilpy.ldpr import LDPR
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF
import context_cache.for_rdflib_jsonld


class LDPRS(LDPR):
    """Generic LDPRS.

    See <https://www.w3.org/TR/ldp/#ldprs>.
    """

    mime_to_rdflib_type = {
        'text/turtle': 'nt',
        'application/ld+json': 'json-ld'
    }

    def __init__(self, uri=None):
        """Initialize LDPRS."""
        super(LDPRS, self).__init__(uri)
        self.content = Graph()

    def parse(self, content, content_type='text/turtle'):
        """Parse RDF and add to this LDPRS."""
        self.content.parse(
            format=self._mime_to_rdflib_type(content_type),
            data=content)

    def serialize(self, content_type='text/turtle'):
        """Serialize this resource in given format.

        We also add in certain server managed triples required
        by LDP and/or Fedora.
        """
        graph = Graph() + self.content
        for rdf_type in self.rdf_types:
            graph.add((URIRef(self.uri), RDF.type, URIRef(rdf_type)))
        return(graph.serialize(
            format=self._mime_to_rdflib_type(content_type),
            context="http://json-ld.org/contexts/person.jsonld",
            indent=2).decode('utf-8'))

    @property
    def rdf_types(self):
        """List of RDF types for this RDF source."""
        return(['http://www.w3.org/ns/ldp#BasicContainer'])

    def _mime_to_rdflib_type(self, content_type):
        """Get rdflib type from mime content type."""
        if (content_type in self.mime_to_rdflib_type):
            return(self.mime_to_rdflib_type[content_type])
        else:
            raise Exception("Unknown RDF content type")
