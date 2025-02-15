"""An LDPRS - RDF Source."""
# import context_cache.for_rdflib_jsonld
from collections import OrderedDict
import hashlib
import logging
import pyparsing
from rdflib import Graph, URIRef, Literal, BNode
from rdflib.namespace import RDF, NamespaceManager
import re

from .ldpr import LDPR
from .namespace import LDP


class PatchFailed(Exception):
    """Patch failure exception."""

    pass


class PatchIllegal(PatchFailed):
    """Patch failure because of illegal change."""

    pass


class LDPRS(LDPR):
    """Generic LDPRS.

    See <https://www.w3.org/TR/ldp/#ldprs>.

    This is the base class for objects that have RDF content and thus
    includes routines for parsing and output. The class properties
    expose types that can be handled:

    rdf_types - Media types for RDF supported (content type)

    rdf_patch_types - Media types for HTTP PATCH method
    """

    type_label = 'LDPRS'

    media_to_rdflib_type = OrderedDict([
        ('text/turtle', 'turtle'),   # default - must be first
        ('application/ld+json', 'json-ld')
    ])

    rdf_media_types = list(media_to_rdflib_type.keys())

    rdf_patch_types = ['application/sparql-update']

    def __init__(self, uri=None, content=None, describes=None, **kwargs):
        """Initialize LDPRS as subclass of LDPR.

        Initial content may optionally be specified via an
        rdflib.Graph object.

        If this LDPRS describes and LDPNR then the URI of the LDPNR
        SHOULD be specified in the `describes` parameter.
        """
        super(LDPRS, self).__init__(uri, **kwargs)
        self.content = Graph() if (content is None) else content
        self.describes = describes

    def __len__(self):
        """Number of content triples."""
        return len(self.content)

    @property
    def uriref(self):
        """URIRef object for self.uri, safe if self.uri is None."""
        return URIRef('' if self.uri is None else self.uri)

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
            format=self._media_to_rdflib_type(content_type),
            data=content)

    def patch(self, patch, content_type):
        """Update this object with specifed patch that has given content_type.

        Will raise PatchFailed (or subclass) and make no changed to the stored
        data if the patch cannot be applied. Otherwise updates this
        object's content.

        patch is expected to be a string rather than bytes object.

        Definition of 'application/sparql-update' at:
        https://www.w3.org/TR/sparql11-update/#mediaType
        """
        if (content_type != 'application/sparql-update'):
            raise PatchFailed("Unrecognized PATCH content type")
        g = Graph() + self.content
        try:
            g.update(patch)
        except pyparsing.ParseException as e:
            raise PatchFailed("Failed to apply patch (bad patch data)")
        # check result and raise PatchIllegal if bad
        self.patch_result_prune_check(g)
        # success
        self.content = g

    def patch_result_prune_check(self, g):
        """Noop implementation of PATCH result pruning and check.

        This method will be overriden in LDPC.
        """
        pass

    def get_container_type(self, context, default=None):
        """Find LDP container type from data supplied.

        Returns the default type provided (or None if not
        specified) if there is no matching type information.
        Will throw and exception if there are conflicting
        container types specified.
        """
        types = self._get_types(context)
        count = 0
        last = None
        for ctype in (LDP.BasicContainer,
                      LDP.DirectContainer,
                      LDP.IndirectContainer):
            if (ctype in types):
                last = ctype
                count += 1
        if (count > 1):
            raise Exception("Conflicting container types specified.")
        elif (count == 1):
            return last
        return default

    def _get_types(self, context):
        """Set of rdf:type properties of context resource.

        Search through data in the content of this resource and
        pull out all rdf:type statements associated with the
        context resource.
        """
        types = set()
        for (s, p, o) in self.content.triples((URIRef(context), RDF.type, None)):
            types.add(o)
            logging.debug("type: %s" % (str(o)))
        return types

    def graph(self, omits, extra=None):
        """RDF graph representation with given omits, extra.

        Adds in certain server managed triples required by LDP and/or Fedora.

        The add_server_managed_triples() method should be overridden in subclasses
        such as those implementing LDPCs.

        The preferences don't make much sense for LDPRS as opposed to LDPC. There
        are no 'container' or 'membership' triples so 'minimal' in omits just turns
        off the whole server managed and content output.
        """
        graph = Graph()
        graph.bind('ldp', LDP)
        if 'minimal' not in omits:
            graph += self.content
        if extra is not None:
            graph += extra
        self.add_server_managed_triples(graph, omits)
        return graph

    def serialize(self, content_type='text/turtle', omits=None, extra=None):
        """Serialize this resource in given format.

        Build graph and then serialize according to the requested content_type.
        """
        if omits is None:
            omits = set()
        return self.graph(omits, extra).serialize(
            format=self._media_to_rdflib_type(content_type),
            context="",
            indent=2).decode('utf-8')

    def add_server_managed_triples(self, graph, omits):
        """Add server managed RDF triples to graph."""
        if 'minimal' not in omits:
            self.add_type_triples(graph)

    def add_type_triples(self, graph):
        """Add rdf:type triples to graph."""
        for rdf_type in self.rdf_types:
            graph.add((URIRef(self.uri), RDF.type, URIRef(rdf_type)))

    def server_managed_triples(self):
        """Graph of RDF triples that would be added from the server."""
        g = Graph()
        self.add_server_managed_triples(g, [])
        return g

    def triples(self, triple_pattern):
        """Iterator over triples in LDPRS content matching triple pattern.

        Provides interface to rdflib Graph.triples() method over the RDF
        content of this LDPRS.
        """
        return self.content.triples(triple_pattern)

    @property
    def rdf_types(self):
        """List of RDF types for this RDF source."""
        return [LDP.RDFSource, LDP.Resource]

    def _media_to_rdflib_type(self, content_type):
        """Get rdflib type from mime/media content_type."""
        try:
            return self.media_to_rdflib_type[content_type]
        except:
            raise Exception("Unknown RDF content type " + content_type)

    def _compute_etag(self):
        """Compute ETag value.

        Make an ETag that is fixed for the graph. In order to use this tag for 
        an If-Match pre-condition it must be a stong tag and thus suitable for
        the stong comparison per https://tools.ietf.org/html/rfc7232#section-2.3.2.

        The strong ETag requirement is rather awkward. It is supposed to indicate byte
        equivalent responses in order to support byte-range requests. In order to support
        use with the If-Match header for PUT and PATCH we need "strong" only is the sense
        that the internal state of the resource is identical

        FIXME - Even at the level or RDF-match this implementation doesn't work properly
        because unless bnodes are serialized with a consistent labeling then the hashing
        over them won't be consistent. Having said that, the test below with a bnode seems
        to give consistent results... so maybe the serialization is consistent if the graph
        isn't changed (though perhaps reading the same graph's triples in a different order
        would mess things up?)
        """
        lines = []
        for (s, p, o) in self.content:
            # Change any bnodes to a fixed sting. This is wrong
            # because it means non-isomorphic graphs will end up
            # with the same etag. However, in practice it is very
            # likely that the ETag will change with changes in graph.
            lines.append(("_:BNODE" if isinstance(s, BNode) else s.n3()) +
                         ' ' + p.n3() + ' ' +
                         ("_:BNODE" if isinstance(o, BNode) else o.n3()))
        s = '\n'.join(sorted(lines))
        h = hashlib.md5(s.encode('utf-8')).hexdigest()
        return '"' + h + '"'
