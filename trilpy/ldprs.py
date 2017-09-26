"""An LDPRS - RDF Source."""
# import context_cache.for_rdflib_jsonld
import hashlib
import logging
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import RDF, NamespaceManager

from .ldpr import LDPR
from .namespace import LDP


class LDPRS(LDPR):
    """Generic LDPRS.

    See <https://www.w3.org/TR/ldp/#ldprs>.
    """

    mime_to_rdflib_type = {
        'text/turtle': 'turtle',
        'application/ld+json': 'json-ld'
    }

    type_label = 'LDPRS'

    def __init__(self, uri=None, **kwargs):
        """Initialize LDPRS as subclass of LDPR."""
        super(LDPRS, self).__init__(uri, **kwargs)
        self.content = Graph()

    def parse(self, content, content_type='text/turtle', context=None):
        """Parse RDF and add to this LDPRS.

        If specified, use context as a the base URI for interpretation
        of relative URIs in the RDF supplied.

        FIXME -- need to make this work with JSON-LD
        """
        if (context is not None and content_type == 'text/turtle'):
            base = (b'@base <%b> .\n' % (context.encode('utf-8')))
            content = base + content
        self.content.parse(
            format=self._mime_to_rdflib_type(content_type),
            data=content)

    def get_container_type(self, context, default=None):
        """Find LDP container type from data supplied.

        Returns the default type or None if there is no matching
        type information. Will throw and exception if there are
        conflicting container types specified.
        """
        types = self._get_types(context)
        count = 0
        last = None
        for ctype in (LDP.BasicContainer,
                      LDP.DirectContainer,
                      LDP.IndirectContainerin):
            if (ctype in types):
                last = ctype
                count += 1
        if (count > 1):
            raise Exception("Conflicting container types specified.")
        elif (count == 1):
            return(last)
        return(default)

    def _get_types(self, context):
        """Return rdf:type properties of context in content.

        FIXME - presumably can make this more efficient!
        """
        ctx = URIRef(context)
        types = set()
        for (s, p, o) in self.content:
            if (s == ctx and p == RDF.type):
                types.add(o)
                logging.debug("type: %s" % (str(o)))
        return(types)

    def get_containment_triples(self):
        """Return set of containment triples in content."""
        ctriples = Graph()
        for (s, p, o) in self.content:
            if (p == LDP.contains):
                ctriples.add((s, p, o))
        return(ctriples)

    def serialize(self, content_type='text/turtle', omits=None):
        """Serialize this resource in given format.

        We also add in certain server managed triples required
        by LDP and/or Fedora.

        If ptype is not None then apply the Prefer return=representation
        preference to select only a subset of triples.
        """
        graph = Graph()
        graph.bind('ldp', LDP)
        if (omits is None or 'content' not in omits):
            graph += self.content
        self.add_server_managed_triples(graph, omits)
        return(graph.serialize(
            format=self._mime_to_rdflib_type(content_type),
            context="",
            indent=2).decode('utf-8'))

    def add_server_managed_triples(self, graph, omits=None):
        """Add server managed RDF triples to graph."""
        self.add_type_triples(graph)

    def add_type_triples(self, graph):
        """Add rdf:type triples to graph."""
        for rdf_type in self.rdf_types:
            graph.add((URIRef(self.uri), RDF.type, URIRef(rdf_type)))

    def server_managed_triples(self):
        """Graph of RDF triples that would be added from the server."""
        g = Graph()
        self.add_server_managed_triples(g)
        return(g)

    @property
    def rdf_types(self):
        """List of RDF types for this RDF source."""
        return([LDP.RDFSource, LDP.Resource])

    def _mime_to_rdflib_type(self, content_type):
        """Get rdflib type from mime content type."""
        if (content_type in self.mime_to_rdflib_type):
            return(self.mime_to_rdflib_type[content_type])
        else:
            raise Exception("Unknown RDF content type")

    def _compute_etag(self):
        """Compute ETag value.

        Make an ETag that is fixed for the graph.

        FIXME - This is very slow and inefficient!

        FIXME - This probably doesn't work because unless bnodes are serialized with a
        consistent labeling then the hashing over them won't be consistent. Having said
        that, the test below with a bnode seems to give consistent results... so maybe
        the serialization is consistent if the graph isn't changed (though perhaps reading
        the same graph's triples in a different order would mess things up?)
        """
        s = b''
        for line in sorted(self.content.serialize(format='nt').splitlines()):
            if line:
                s += line + b'\n'
        h = hashlib.md5(s).hexdigest()
        return('W/"' + h + '"')
