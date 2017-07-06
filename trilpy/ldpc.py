"""An LDPC - LDP Container."""
from trilpy.ldprs import LDPRS


class LDPC(LDPRS):
    """Generic LDPC.

    See <https://www.w3.org/TR/ldp/#ldpc>.
    """

    def __init__(self, uri=None):
        """Initialize LDPC."""
        super(LDPC, self).__init__(uri)

    @property
    def rdf_types(self):
        """List of RDF types for this container."""
        return(['http://www.w3.org/ns/ldp#BasicContainer'])
