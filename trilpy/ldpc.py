"""An LDPC - LDP Container."""
from rdflib import URIRef

from .ldprs import LDPRS
from .namespace import LDP


class LDPC(LDPRS):
    """Generic LDPC.

    See <https://www.w3.org/TR/ldp/#ldpc>.
    """

    def __init__(self, uri=None, content=None,
                 container_type=LDP.BasicContainer):
        """Initialize LDPC."""
        super(LDPC, self).__init__(uri)
        if (content is not None):
            self.content = content
        self.container_type = container_type
        self.members = set()
        self.membership_predicate = URIRef('http://www.w3.org/ns/ldp#member')
        self.contains = set()
        self.containment_predicate = URIRef('http://www.w3.org/ns/ldp#contains')

    def add_server_managed_triples(self, graph, omits=None):
        """Add RDF triples from the server.

        The includes the type triples of a generic LDPRS add_server_managed_triples
        and also containement triples.
        """
        self.add_type_triples(graph)
        if (self.container_type == LDP.DirectContainer):
            graph.add((URIRef(self.uri),
                       LDP.membershipResource,
                       URIRef(self.uri)))
            graph.add((URIRef(self.uri),
                       LDP.hasMemberRelation,
                       self.membership_predicate))
            graph.add((URIRef(self.uri),
                      LDP.insertedContentRelation,
                      LDP.MemberSubject))
        if (omits is None or 'membership' not in omits):
            self.add_member_triples(graph)
        if (omits is None or 'containment' not in omits):
            self.add_containment_triples(graph)

    def add_member_triples(self, graph):
        """Add member triples to graph."""
        for member in self.members:
            graph.add((URIRef(self.uri),
                       self.membership_predicate,
                       URIRef(member)))

    def add_containment_triples(self, graph):
        """Add containment triples to graph."""
        for contained in self.contains:
            graph.add((URIRef(self.uri),
                       self.containment_predicate,
                       URIRef(contained)))

    @property
    def rdf_types(self):
        """List of RDF types for this container."""
        return([self.container_type, LDP.Resource])

    def add_contained(self, uri):
        """Add uri as contained resource."""
        self.contains.add(uri)

    def del_contained(self, uri):
        """Delete uri as contained resource."""
        self.contains.remove(uri)

    def add_member(self, uri):
        """Add uri as member resource."""
        self.members.add(uri)

    def del_member(self, uri):
        """Delete uri as member resource."""
        self.members.remove(uri)
