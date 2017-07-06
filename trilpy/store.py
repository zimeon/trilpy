"""Trilpy store for resources."""

from urllib.parse import urljoin


class Store(object):
    """Resource store."""

    def __init__(self, base_uri):
        """Initialize empty store with a base_uri."""
        self.base_uri = base_uri
        self.resources = {}
        self.deleted = set()

    def add(self, resource, uri=None, context=None, slug=None):
        """Add resource, optionally with uri."""
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
        return(uri)

    def delete(self, uri):
        """Delete resource and record deletion."""
        if (uri in self.resources):
            del self.resources[uri]
            self.deleted.add(uri)

    def _get_uri(self, context=None, slug=None):
        """Get URI for a new resource.

        FIXME - ignores context and slug.
        """
        n = 1
        while (True):
            uri = urljoin(self.base_uri, '/' + str(n))
            if (uri not in self.resources and
                    uri not in self.deleted):
                return(uri)
            n += 1
