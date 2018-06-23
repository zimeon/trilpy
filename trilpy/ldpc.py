"""An LDPC - LDP Container."""
from rdflib import URIRef

from .ldprs import LDPRS
from .namespace import LDP


class UnsupportedContainerType(Exception):
    """Exception to indicate an unsupported container type."""

    pass


class LDPC(LDPRS):
    """LDPC class supporting Basic, Direct and Indirect behaviors.

    See <https://www.w3.org/TR/ldp/#ldpc>.
    """

    def __init__(self, uri=None,
                 container_type=LDP.BasicContainer, **kwargs):
        """Initialize LDPC as subclass of LDPRS.

        container_type may be either a URIRef() or else one will be created from
        the string value.
        """
        super(LDPC, self).__init__(uri, **kwargs)
        self.container_type = container_type if isinstance(container_type, URIRef) else URIRef(container_type)
        if self.container_type not in (LDP.BasicContainer, LDP.DirectContainer, LDP.IndirectContainer):
            raise UnsupportedContainerType()
        self.contains = set()
        self.containment_predicate = LDP.contains
        self.members = set()
        self.membership_predicate = LDP.member
        self.type_label = 'LDPC'

    def add_server_managed_triples(self, graph, omits=None):
        """Add RDF triples from the server.

        The includes the type triples of a generic LDPRS add_server_managed_triples
        and also containement and membership triples.
        """
        self.add_type_triples(graph)
        if (self.container_type == LDP.DirectContainer):
            graph.add((self.uriref,
                       LDP.membershipResource,
                       self.uriref))
            graph.add((self.uriref,
                       LDP.hasMemberRelation,
                       self.membership_predicate))
            graph.add((self.uriref,
                      LDP.insertedContentRelation,
                      LDP.MemberSubject))
        if (omits is None or 'membership' not in omits):
            self.add_membership_triples(graph)
        if (omits is None or 'containment' not in omits):
            self.add_containment_triples(graph)

    def add_containment_triples(self, graph):
        """Add containment triples to graph."""
        for triple in self.containment_triples():
            graph.add(triple)

    def add_membership_triples(self, graph):
        """Add member triples to graph."""
        for triple in self.membership_triples():
            graph.add(triple)

    def containment_triples(self):
        """Generator for containment triples (rdflib style tuples)."""
        for contained in self.contains:
            yield((self.uriref,
                   self.containment_predicate,
                   URIRef(contained)))

    def membership_triples(self):
        """Generator for membership triples (rdflib style tuples)."""
        for member in self.members:
            yield((self.uriref,
                   self.membership_predicate,
                   URIRef(member)))

    @property
    def rdf_types(self):
        """List of RDF types for this container."""
        return([self.container_type, LDP.RDFSource, LDP.Resource])

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
