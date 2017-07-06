"""An LDPRS - RDF Source."""
import context_cache.for_rdflib_jsonld
import hashlib
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF, NamespaceManager

from .ldpr import LDPR
from .namespace import LDP


class LDPRS(LDPR):
    """Generic LDPRS.

    See <https://www.w3.org/TR/ldp/#ldprs>.
    """

    mime_to_rdflib_type = {
        'text/turtle': 'turtle',
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
        self.content.bind('ldp', LDP)
        self.add_server_managed_triples(graph)
        return(graph.serialize(
            format=self._mime_to_rdflib_type(content_type),
            context="",
            indent=2).decode('utf-8'))

    def add_server_managed_triples(self, graph):
        """Add RDF triples from the server."""
        for rdf_type in self.rdf_types:
            graph.add((URIRef(self.uri), RDF.type, URIRef(rdf_type)))

    @property
    def rdf_types(self):
        """List of RDF types for this RDF source."""
        return([LDP.RDFSource, LDP.Resource])

    def _mime_to_rdflib_type(self, content_type):
        """Get rdflib type from mime content type."""
        if (content_type in self.mime_to_rdflib_type):
            return(self.mime_to_rdflib_type[content_type])
        else:
            raise Exception("Unknown RDF content type")

    def _compute_etag(self):
        """Compute and update stored ETag value.

        Make an ETag that is fixed for the graph. This is very slow
        and inefficient!
        """
        s = b''
        for line in sorted(self.content.serialize(format='nt').splitlines()):
            if line:
                s += line + b'\n'
        h = hashlib.md5(s).hexdigest()
        self._etag = 'W/"' + h + '"'
