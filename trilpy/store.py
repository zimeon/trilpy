"""Trilpy store for resources."""

class Store(object):

    def __init__(self):
        """Initialize empty store."""
        self.resources = {}
        self.deleted = set()

    def add(self, name, resource):
        """Add resource with name."""
        if (name in self.deleted):
            self.deleted.discard(name)
        self.resources[name] = resource

    def delete(self, name):
        """Delete resource and record deletion."""
        if (name in self.resources):
            del self.resources[name]
            self.deleted.add(name)
