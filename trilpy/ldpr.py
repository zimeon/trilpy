"""An LDPR - LDP Resource."""
import hashlib
from .namespace import LDP


class LDPR(object):
    """Generic LDPR, base class for all LDP resource types.

    See <https://www.w3.org/TR/ldp/#ldpr>.
    """

    type_label = 'LDPR'

    def __init__(self, uri=None):
        """Initialize LDPR."""
        self.uri = uri
        self.content = None
        self.contained_in = None
        self.member_of = None
        self.acl = None
        self._etag = None

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
            self._compute_etag()
        return(self._etag)

    def _compute_etag(self):
        """Compute and update stored ETag value."""
        h = hashlib.md5(self.content).hexdigest()
        self._etag = '"' + h + '"'
