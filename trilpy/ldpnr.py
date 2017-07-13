"""An LDPNR - LDP Non-RDF Source."""
from trilpy.ldpr import LDPR


class LDPNR(LDPR):
    """LDPNR - A binary object.

    An LDPR whose state is not represented in RDF. For example,
    these can be binary or text documents that do not have useful
    RDF representations.

    See <https://www.w3.org/TR/ldp/#ldpnr>.
    """

    type_label = 'LDPNR'

    def __init__(self, uri=None, content=None, content_type=None):
        """Initialize LDPNR."""
        super(LDPNR, self).__init__(uri)
        self.content = content
        self.content_type = content_type
