"""Trilpy store for._resources."""

import logging
from urllib.parse import urljoin


class KeyDeleted(KeyError):
    """Class indicating key not present because it has been deleted."""

    pass


class Store(object):
    """Resource store.

    In general this acts like a dictionary of resource items with their
    URIs as the keys. But also records deleted items (raising KeyDeleted
    instead of KeyError on attemt to access) and handles generation of
    URIs for newly added._resources.
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

    def delete(self, uri):
        """Delete resource and record deletion.

        If the resource being deleted is recorded as being contained
        in a container then delete the entry from the container.
        """
        if (uri in self._resources):
            resource = self._resources[uri]
            if (resource.contained_in is not None):
                try:
                    # Delete containment and contains relationships
                    context = resource.contained_in
                    resource.contained_in = None
                    container = self._resources[context]
                    container.del_contained(uri)
                    if (container.container_type == LDP.DirectContainer):
                        resource.member_of = None
                        container.del_member(uri)
                except:
                    logging.warn("OOPS - failed to remove containment triple of %s from %s" %
                                 (uri, resource.contained_in))
            del self._resources[uri]
            self.deleted.add(uri)

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
              self._resources[resource.acl].has_heritable_auths() or
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
            uri = urljoin(context, slug)
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
