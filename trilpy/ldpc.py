"""An LDPC - LDP Container."""
from rdflib import URIRef

from .ldprs import LDPRS
from .namespace import LDP


class LDPC(LDPRS):
    """Generic LDPC.

    See <https://www.w3.org/TR/ldp/#ldpc>.
    """

    def __init__(self, uri=None):
        """Initialize LDPC."""
        super(LDPC, self).__init__(uri)
        self.members = set()
        self.membership_predicate = URIRef('http://www.w3.org/ns/ldp#member')

    def add_server_managed_triples(self, graph):
        """Add RDF triples from the server.

        The includes the type triples of a generic LDPRS add_server_managed_triples
        and also containement triples.
        """
        super(LDPC, self).add_server_managed_triples(graph)
        for member in self.members:
            graph.add((URIRef(self.uri),
                       self.membership_predicate,
                       URIRef(member)))

    @property
    def rdf_types(self):
        """List of RDF types for this container."""
        return([LDP.BasicContainer, LDP.Resource])

    def add_member(self, uri):
        """Add uri as member resource."""
        self.members.add(uri)

    def del_member(self, uri):
        """Delete uri as member resource."""
        self.members.remove(uri)
