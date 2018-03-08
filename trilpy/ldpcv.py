"""An LDPCv - LDP Version Container."""
from rdflib import URIRef
from negotiator2 import TimeMap

from .ldpc import LDPC
from .namespace import LDP


class LDPCv(LDPC):
    """An LDPCv."""

    rdf_media_types = list(LDPC.media_to_rdflib_type.keys())
    rdf_media_types.append('application/link-format')

    def __init__(self, uri=None, original=None,
                 **kwargs):
        """Initialize LDPCv as subclass of LDPC."""
        super(LDPCv, self).__init__(uri, **kwargs)
        self.original = original
        self.type_label = 'LDPCv'

    @property
    def is_ldpcv(self):
        """True, this object is an LDPCv."""
        return True

    @property
    def timemap_object(self):
        """TimeMap object for this LDPCv."""
        tm = TimeMap(original=self.original, timegate=self.original, timemap=self.uri)
        for contained in self.contains:
            datetime = 'Tue, 20 Jun 9999 10:11:12 GMT'  # FIXME - need datetime for Mementos
            tm.add_memento(contained, datetime)
        return tm

    def serialize(self, content_type='text/turtle', omits=None, extra=None):
        """Serialize this resource in given format.

        Adds understanding of content_type 'application/link-format'
        else passes superclass method.
        """
        if (content_type == 'application/link-format'):
            return self.timemap_object.serialize_link_format()
        else:
            return super(LDPCv, self).serialize(content_type, omits, extra)
