"""Trilpy store for resources."""

import logging
from urllib.parse import urljoin
from rdflib import Graph, URIRef

from .ldpc import LDPC
from .ldprs import LDPRS


class KeyDeleted(KeyError):
    """Class indicating key not present because it has been deleted."""

    pass


class Store(object):
    """Resource store.

    In general this acts like a dictionary of resource items with their
    URIs as the keys. But also records deleted items (raising KeyDeleted
    instead of KeyError on attemt to access) and handles generation of
    URIs for newly added resources.
    """

    acl_inheritance_limit = 100
    acl_default = '/missing.acl'
    acl_suffix = '.acl'

    def __init__(self, base_uri):
        """Initialize empty store with a base_uri."""
        self.base_uri = base_uri
        self._resources = {}
        self.deleted = set()

    def add(self, resource, uri=None, context=None, slug=None):
        """Add resource, optionally with specific uri.

        If uri is not None then the new resource should be added with
        that URI, possibly relaive to the repository base_uri.

        If context is not None then it is the URI of the container to which
        this resource is being added.

        If slug is not None then it is a hint at the client's preferred
        naming of the new resource (ignored if uri is set).
        """
        if (uri is None):
            uri = self._get_uri(context, slug)
        else:
            # Handle possible relative URI
            uri = urljoin(self.base_uri, uri)
            # Normalize base_uri/ to base_uri
            if (uri == (self.base_uri + '/')):
                uri = self.base_uri
        if (uri in self.deleted):
            self.deleted.discard(uri)
        self._resources[uri] = resource
        resource.uri = uri
        if (context):
            container = self._resources[context]
            # Add containment and contains relationships
            resource.contained_in = context
            container.add_contained(uri)
            # if (container.container_type == LDP.DirectContainer):
            #    resource.member_of = context
            #    container.add_member(uri)
        return(uri)

    def update(self, resource):
        """Update content of the resource at resource.uri in the store.

        In the case that resource is the same object as already stored at this location then
        update no-op in this model of an in-memory store. However, is resource is a different
        object then it will be replaced.
        """
        if resource.uri in self.deleted:
            raise KeyDeleted("Attempt to update deleted resource %s." % resource.uri)
        if resource.uri not in self._resources:
            raise KeyError("Attempt to update resource %s that does not exist." % resource.uri)
        # Retain containment link
        old_resource = self._resources[resource.uri]
        resource.contained_in = old_resource.contained_in
        self._resources[resource.uri] = resource

    def delete(self, uri):
        """Delete resource and record deletion. Return context of deleted resource.

        If the resource being deleted is recorded as being contained
        in a container then delete the entry from the container.
        """
        context = None
        if (uri in self._resources):
            resource = self._resources[uri]
            if (resource.contained_in is not None):
                context = resource.contained_in
                try:
                    # Delete containment and contains relationships
                    resource.contained_in = None
                    container = self._resources[context]
                    container.del_contained(uri)
                except KeyError:
                    logging.warn("OOPS - failed to remove containment of %s from %s" %
                                 (uri, context))
                # if (container.container_type == LDP.DirectContainer):
                #        resource.member_of = None
                #        container.del_member(uri)
            del self._resources[uri]
            self.deleted.add(uri)
        return context

    def object_references(self, uri):
        """Graph of triples in store that refer to object uri.

        These may come from two sources:
            1. Arbitrary triples in RDF then have uri as the object.
            2. Containment and membership relations for uri.

        FIXME - This is SPECTACULARLY inefficient! Does a simple
        search over all triples in all LDPRS objects looking for
        for object uri.
        """
        g = Graph()
        triple_pattern = (None, None, URIRef(uri))
        for r_uri, resource in self.items():
            if (isinstance(resource, LDPRS)):
                for (s, p, o) in resource.triples(triple_pattern):
                    g.add((s, p, o))
            if (isinstance(resource, LDPC)):
                if (uri in resource.contains):
                    g.add((URIRef(resource.uri),
                           resource.containment_predicate,
                           URIRef(uri)))
                if (uri in resource.members):
                    g.add((URIRef(resource.uri),
                           resource.membership_predicate,
                           URIRef(uri)))
        return g

    def contained_graph(self, uri, omits):
        """Graph of resource content for resources contained by uri.

        Simply iterates through the set of contained resources and adds
        the content (following omits rules) of any that are LDPRS to the
        graph.

        FIXME - this has the potential to get quite large, should there be a cutoff?
        """
        resource = self[uri]
        contained_graph = Graph()
        for contained_uri in resource.contains:
            contained_resource = self[contained_uri]
            if isinstance(contained_resource, LDPRS):
                contained_graph += contained_resource.graph(omits)
        return contained_graph

    def acl(self, uri, depth=0):
        """ACL URI for the ACL controlling access to uri.

        Note that this effective ACL is not necessarily the same as the
        individual_acl(uri) which may or may not exist. If it doesn't
        exist then we follow the containment hierarchy up looking for
        an individual ACL, or in the limit return the default acl.

        FIXME - How do we handle `control` type directives that apply to
        self in the case that uri is an ACL resource, see
        https://github.com/solid/web-access-control-spec#modes-of-access
        """
        resource = self._resources[uri]
        if (resource.acl is None):
            if (resource.contained_in is None):
                # This is not covered by WAC specification see:
                # https://github.com/fcrepo/fcrepo-specification/issues/163
                return(self.acl_default)
        elif (depth == 0 or
              self._resources[resource.acl].has_heritable_auths or
              resource.contained_in is None):
            return(resource.acl)
        # Go up inheritance hierarchy
        if (depth >= self.acl_inheritance_limit):
            raise Exception("Exceeded acl_inheritance_limit!")
        return(self.acl(resource.contained_in, depth=(depth + 1)))

    def individual_acl(self, uri):
        """ACL uri for the individual ACL for uri, which may or may not exist.

        Response headers are required to return the ACL URI for the individual
        ACL for the specified resource. That may or may not exist but the location
        will allow a client to create one in the right location.
        """
        resource = self._resources[uri]
        if (resource.acl is None):
            return(uri + self.acl_suffix)
        else:
            return(resource.acl)

    def _get_uri(self, context=None, slug=None):
        """Get URI for a new resource.

        Will first try to honor the slug but creating a new URI
        with slug as the final path element.
        """
        if (context is not None and slug is not None):
            # Add trailing slash to context just in case, // tidied by urljoin
            uri = urljoin(context + '/', slug)
            if (uri not in self._resources and
                    uri not in self.deleted):
                return(uri)
        # Otherwise consruct URI
        n = 1
        while (True):
            uri = urljoin(self.base_uri, '/' + str(n))
            if (uri not in self._resources and
                    uri not in self.deleted):
                return(uri)
            n += 1

    def __getitem__(self, uri):
        """Item access with [uri] as key.

        Raises KeyDeleted (a sub-class of KeyError) if the item used to exist but has
        been deleted, or KeyError if there is no record of it.
        """
        try:
            return self._resources[uri]
        except KeyError as e:
            if (uri in self.deleted):
                raise KeyDeleted(uri + " has been deleted")
            raise e

    def __contains__(self, uri):
        """Item presence test with uri as key."""
        return(uri in self._resources)

    def __len__(self):
        """Number of resources (excluding deleted resources)."""
        return(len(self._resources))

    def __iter__(self):
        """Iterator over resources (excluding deleted resources)."""
        return(iter(self._resources))

    def items(self):
        """Resource items in the store (excluding deleted resources)."""
        return(self._resources.items())
