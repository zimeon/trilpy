"""An LDPCv - LDP Version Container."""
from rdflib import URIRef

from .ldpc import LDPC
from .namespace import LDP


class LDPCv(LDPC):
    """An LDPCv."""

    def __init__(self, uri=None, original=None,
                 **kwargs):
        """Initialize LDPCv as subclass of LDPC."""
        super(LDPCv, self).__init__(uri, **kwargs)
        self.original = original
        self.type_label = 'LDPCv'

    @property
    def is_ldpcv(self):
        """True, this object is an LDPCv."""
        return(True)
