"""An LDPR."""

class LDPR(object):
    """Generic LDPR.

    See <https://www.w3.org/TR/ldp/#ldpr>.
    """

    def __init__(self):
        """Initialize LDPR."""
        self.admin = None
        self.content = None
