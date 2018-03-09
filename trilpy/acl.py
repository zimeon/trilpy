"""ACLR to implement Web Access Control.

Code to implement the Web Access Control (WAC)
<https://github.com/solid/web-access-control-spec>
in the context of the trilpy server.
"""
import hashlib
from rdflib import URIRef, Literal
from rdflib.namespace import RDF, FOAF
from .ldprs import LDPRS
from .namespace import LDP, ACL


class ACLR(LDPRS):
    """An ACL resource is an LDP RDF Source.

    Fedora: "The linked Access Control List Resource (ACL) for a controlled
    resource by a conforming server must itself be an LDPRS. This
    ACL resource should be located in the same server as the
    controlled resource."
    """

    type_label = 'ACLR'

    def __init__(self, uri=None, acl_for=None):
        """Initialize ACLR."""
        super(ACLR, self).__init__(uri)
        self._acl_for = acl_for

    def add_public_read(self, inherit=False):
        """Set this ACL to public access (read for anyone).

        Returns URIRef() for the auth block.
        """
        if (self._acl_for is None):
            raise Exception("Can't set ACL without target!")
        auth = self._get_new_hash_uriref()
        acl_for = URIRef(self._acl_for)
        # <#authorizationN>
        #    a acl:Authorization;
        #    acl:agentClass foaf:Agent;  # everyone
        #    acl:mode acl:Read;  # has Read-only access
        #    acl:accessTo <target>.
        self.content.add((auth, RDF.type, ACL.Authorization))
        self.content.add((auth, ACL.agentClass, FOAF.Agent))
        self.content.add((auth, ACL.mode, ACL.Read))
        self.content.add((auth, ACL.accessTo, acl_for))
        if (inherit):
            self.content.add((auth, ACL.defaultForNew, acl_for))
        return(auth)

    @property
    def authorizations(self):
        """Iterator over authorizations in this ACL."""
        return self.content.subjects(RDF.type, ACL.Authorization)

    @property
    def has_heritable_auths(self):
        """True if this ACL has heritable authorizations.

        The ACL Inheritance Algorithm algorithm requires following
        the containment hierarchy up until a resource with an
        ACL is found. This ACL is then checked for authorizations
        to inherit, as indicated by the ACL.default predicate.
        """
        for authz in self.authorizations:
            for s, p, o in self.content.triples((authz, ACL.default, None)):
                return(True)
        return(False)

    def _get_new_hash_uriref(self):
        """Return a new local hashuri for a new authorization block."""
        subjects = set(self.content.subjects())  # set of distinct subjects
        n = 0
        while (True):
            n += 1
            uri = URIRef("#authorization%d" % n)
            if (uri not in subjects):
                break
        return(uri)
