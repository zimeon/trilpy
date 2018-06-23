"""An LDPR - LDP Resource."""
import hashlib
from .namespace import LDP


class LDPR(object):
    """Generic LDPR, base class for all LDP resource types.

    See <https://www.w3.org/TR/ldp/#ldpr>.
    """

    type_label = 'LDPR'

    def __init__(self, uri=None, content=b'', acl=None):
        """Initialize LDPR.

        uri is a URI expressed as a string (not a URIRef)

        content is expected to be in bytes not unicode
        """
        # LDP properties
        self.uri = uri
        self.content = content
        self.contained_in = None
        self.member_of = None
        self.acl = acl
        self.describes = None
        self.describedby = None
        # Fedora versioned resource properties
        self.timemap = None
        self.original = None
        # Cache values
        self._etag = None

    @property
    def is_ldprv(self):
        """True if this LDPR is an LDPRv, a versioned resource (Original Resource)."""
        return(self.timemap is not None and self.original is None)

    @property
    def is_ldprm(self):
        """True if this LDPR is an LDPRm, a Memento of a version resource (Memento)."""
        return(self.timemap is not None and self.original is not None)

    @property
    def is_ldpcv(self):
        """False, override in sub-class implementing LDPCv."""
        return(False)

    @property
    def rdf_type(self):
        """Primary RDF type for this LDP Resource."""
        return(self.rdf_types[0])

    @property
    def rdf_type_uri(self):
        """Primary RDF type URI for this LDP Resource."""
        return(str(self.rdf_type))

    @property
    def rdf_types(self):
        """List of rdflib RDF types for this LDP Resource.

        First must be the primary type returned by rdf_type.
        """
        return([LDP.Resource])

    @property
    def rdf_type_uris(self):
        """List of RDF type URIs for this LDP Resource."""
        return([str(x) for x in self.rdf_types])

    @property
    def etag(self):
        """ETag value, lazily computed."""
        if (self._etag is None):
            self._etag = self._compute_etag()
        return(self._etag)

    def _compute_etag(self):
        """Compute ETag value."""
        return('"' + hashlib.md5(self.content).hexdigest() + '"')
