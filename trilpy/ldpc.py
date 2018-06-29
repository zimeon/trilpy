"""An LDPC - LDP Container."""
from rdflib import Graph, URIRef

from .ldprs import LDPRS, PatchIllegal
from .namespace import LDP


class UnsupportedContainerType(Exception):
    """Exception to indicate an unsupported container type."""

    pass


class DataConflict(Exception):
    """Data provided to create or update this LDPC is in conflict."""

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
        self.container_type = container_type if isinstance(container_type, URIRef) else URIRef(container_type)
        if self.container_type not in (LDP.BasicContainer, LDP.DirectContainer, LDP.IndirectContainer):
            raise UnsupportedContainerType()
        super(LDPC, self).__init__(uri, **kwargs)
        self.contains = set()
        self.containment_predicate = LDP.contains
        self.members = set()
        self.membership_predicate = LDP.member
        self._membership_constant = None
        self._inserted_content_rel = None
        self.type_label = 'LDPC'

    @property
    def membership_constant(self):
        """Member constant URIRef, either uriref or set from _member_constant."""
        return self.uriref if self._membership_constant is None else self._membership_constant

    @property
    def inserted_content_rel(self):
        """Inserted content relation defaults to ldp:MemberSubject."""
        return LDP.MemberSubject if self._inserted_content_rel is None else self._inserted_content_rel

    def parse(self, content, content_type='text/turtle', context=None):
        """Parse RDF and add to this LDPC.

        Uses LDPRS.parse() then extracts LDPC-specific information.
        """
        super(LDPC, self).parse(content, content_type=content_type, context=context)
        if self.container_type in (LDP.DirectContainer, LDP.IndirectContainer):
            self.extract_membership_config_triples()

    def _extract_property(self, predicate, remove=True):
        """Extract and return one property with the given predicate.

        Throws a DataConflict error if there is more than one matching property.
        """
        triples = list(self.content.triples((self.uriref, predicate, None)))
        if len(triples) > 1:
            raise DataConflict("Multiple %s properties given" % str(predicate))
        elif len(triples) == 1:
            triple = triples[0]
            if remove:
                self.content.remove(triple)
            return triple[2]

    def extract_membership_config_triples(self):
        """Extract membership configuration triples.

        Sets instance configuration variables.
        """
        # ldp:hasMemberRelation
        # FIXME - what about ldp:isMemberRelationOf
        # see: https://github.com/fcrepo/fcrepo-specification/issues/387
        mp = self._extract_property(LDP.hasMemberRelation)
        if mp:
            if mp == LDP.contains:
                raise DataConflict("Use of ldp:contains as membership relation not supported")
            self.membership_predicate = mp
        # ldp:membershipResource
        self._membership_constant = self._extract_property(LDP.membershipResource)
        #
        if self.container_type == LDP.IndirectContainer:
            # ldp:insertedContentRelation
            self._inserted_content_rel = self._extract_property(LDP.insertedContentRelation)

    def patch_result_prune_check(self, graph):
        """Prune containment triples from result of PATCH graph and check for illegal modifications.

        Check for attempt to modify containment triples. It is OK if the result of PATCH
        doesn't include the containment triples because they will be preserved anyway.
        However, it is illegal to add any new containment triples.

        SIDE EFFECT - graph is modified to remove the containment triples
        """
        patch_ct = self.extract_containment_triples(graph, remove=True)
        existing_ct = Graph()
        for triple in self.containment_triples():
            existing_ct.add(triple)
        if (len(existing_ct + patch_ct) != len(existing_ct)):
            raise PatchIllegal("Attempt to modify containment triples")

    def extract_containment_triples(self, content=None, remove=True):
        """Extract graph of containment triples from content.

        If content is not specified then modify self.content.

        We store containment triples as server managed so we do
        not want these duplicated in the content.
        """
        ctriples = Graph()
        if content is None:
            content = self.content
        # FIXME - Should we test for s == self.uriref ? Or should any triple with
        # the containment_predicate be rejected? For now reject any as otherwise
        # we fail the FedoraAPITestSuite 3.7.1 test.
        for (s, p, o) in content.triples((None, self.containment_predicate, None)):
            ctriples.add((s, p, o))
            if remove:
                content.remove((s, p, o))
        return ctriples

    def add_server_managed_triples(self, graph, omits):
        """Add RDF triples from the server.

        The includes the type triples of a generic LDPRS add_server_managed_triples
        and also containement and membership triples.
        """
        self.add_type_triples(graph)
        if self.container_type == LDP.BasicContainer:
            # For BasicContainers we have only ldp:contains triples
            if 'containment' not in omits:
                self.add_containment_triples(graph)
        else:
            # Direct and Indirect containers have membership information and
            # we do not serialize the ldp:contains triples
            # FIXME - where in the specs does it say we don't serialize ldp:contains?
            if 'membership' not in omits:
                self.add_membership_triples(graph)
                graph.add((self.uriref,
                           LDP.membershipResource,
                           self.membership_constant))
                graph.add((self.uriref,
                           LDP.hasMemberRelation,
                           self.membership_predicate))
                graph.add((self.uriref,
                           LDP.insertedContentRelation,
                           self.inserted_content_rel))

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
