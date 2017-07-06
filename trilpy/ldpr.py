"""An LDPR - LDP Resource."""


class LDPR(object):
    """Generic LDPR, base class for all LDP resource types.

    See <https://www.w3.org/TR/ldp/#ldpr>.
    """

    def __init__(self, uri=None):
        """Initialize LDPR."""
        self.uri = uri
        self.admin = None
        self.content = None

    @property
    def rdf_types(self):
        """List of RDF types for this LDP Resource."""
        return(['http://www.w3.org/ns/ldp#Resource'])
