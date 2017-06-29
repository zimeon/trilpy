"""An LDPC - LDP Container."""
from trilpy.ldprs import LDPRS


class LDPC(LDPRS):
    """Generic LDPC.

    See <https://www.w3.org/TR/ldp/#ldpc>.
    """

    def __init__(self):
        """Initialize LDPC."""
        super(LDPC, self).__init__()
