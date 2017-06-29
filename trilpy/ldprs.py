"""An LDPRS - RDF Source."""
from trilpy.ldpr import LDPR
from rdflib import Graph
import context_cache.for_rdflib_jsonld


class LDPRS(LDPR):
    """Generic LDPRS.

    See <https://www.w3.org/TR/ldp/#ldprs>.
    """

    mime_to_rdflib_type = {
        'text/turtle': 'nt',
        'application/ld+json': 'json-ld'
    }

    def __init__(self):
        """Initialize LDPRS."""
        super(LDPRS, self).__init__()
        self.content = Graph()

    def parse(self, content, content_type='text/turtle'):
        """Parse RDF and add to this LDPRS."""
        self.content.parse(
            format=self._mime_to_rdflib_type(content_type),
            data=content)

    def serialize(self, content_type='text/turtle'):
        """Serialize this resource in given format."""
        return(self.content.serialize(
            format=self._mime_to_rdflib_type(content_type),
            context="http://json-ld.org/contexts/person.jsonld",
            indent=2).decode('utf-8'))

    def _mime_to_rdflib_type(self, content_type):
        """Get rdflib type from mime content type."""
        if (content_type in self.mime_to_rdflib_type):
            return(self.mime_to_rdflib_type[content_type])
        else:
            raise Exception("Unknown RDF content type")
