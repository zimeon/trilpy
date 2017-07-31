"""Trilpy store for resources."""

import logging
from urllib.parse import urljoin


class Store(object):
    """Resource store."""

    def __init__(self, base_uri):
        """Initialize empty store with a base_uri."""
        self.base_uri = base_uri
        self.resources = {}
        self.deleted = set()

    def add(self, resource, uri=None, context=None, slug=None):
        """Add resource, optionally with specific uri."""
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
        self.resources[uri] = resource
        resource.uri = uri
        if (context):
            container = self.resources[context]
            # Add containment and contains relationships
            resource.contained_in = context
            container.add_contained(uri)
            # if (container.container_type == LDP.DirectContainer):
            #    resource.member_of = context
            #    container.add_member(uri)
        return(uri)

    def delete(self, uri):
        """Delete resource and record deletion.

        If the resource being deleted is recorded as being contained
        in a container then delete the entry from the container.
        """
        if (uri in self.resources):
            resource = self.resources[uri]
            if (resource.contained_in is not None):
                try:
                    # Delete containment and contains relationships
                    context = resource.contained_in
                    resource.contained_in = None
                    container = self.resources[context]
                    container.del_contained(uri)
                    if (container.container_type == LDP.DirectContainer):
                        resource.member_of = None
                        container.del_member(uri)
                except:
                    logging.warn("OOPS - failed to remove containment triple of %s from %s" %
                                 (uri, resource.contained_in))
            del self.resources[uri]
            self.deleted.add(uri)

    def _get_uri(self, context=None, slug=None):
        """Get URI for a new resource.

        Will first try to honor the slug but creating a new URI
        with slug as the final path element.
        """
        if (context is not None and slug is not None):
            uri = urljoin(context, slug)
            if (uri not in self.resources and
                    uri not in self.deleted):
                return(uri)
        # Otherwise consruct URI
        n = 1
        while (True):
            uri = urljoin(self.base_uri, '/' + str(n))
            if (uri not in self.resources and
                    uri not in self.deleted):
                return(uri)
            n += 1
