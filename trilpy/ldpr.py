"""An LDPR - LDP Resource."""


class LDPR(object):
    """Generic LDPR, base class for all LDP resource types.

    See <https://www.w3.org/TR/ldp/#ldpr>.
    """

    def __init__(self):
        """Initialize LDPR."""
        self.admin = None
        self.content = None
