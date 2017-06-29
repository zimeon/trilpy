"""Trilpy store for resources."""


class Store(object):
    """Resource store."""

    def __init__(self):
        """Initialize empty store."""
        self.resources = {}
        self.deleted = set()

    def add(self, resource, name=None, context=None, slug=None):
        """Add resource, optionally with name."""
        if (name is None):
            name = self._get_name(context, slug)
        elif (name in self.deleted):
            self.deleted.discard(name)
        self.resources[name] = resource
        return(name)

    def delete(self, name):
        """Delete resource and record deletion."""
        if (name in self.resources):
            del self.resources[name]
            self.deleted.add(name)

    def _get_name(self, context=None, slug=None):
        """Create a new resource name.

        FIXME - ignores context and slug.
        """
        n = 1
        while (('/' + str(n)) in self.resources):
            n += 1
        return('/' + str(n))
