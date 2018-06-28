"""HTTP Link header handling for requests and responses.

Include some Tornado and LDP specific code in order to be
able to move more code out of the tornado.web.RequestHandler.
"""
import logging
import requests.utils
from tornado.web import HTTPError

from .ldp import LDPNR_URI, LDPRS_URI, LDPC_URI, LDPBC_URI, LDPDC_URI, LDPIC_URI, LDP_CONTAINER_TYPE_URIS
from .namespace import LDP


class RequestLinks(object):
    """Class to handle parsing an access to HTTP request links."""

    def __init__(self, link_headers=None, link_dict=None):
        """Initialize RequestLinks object.

        Will parse link_headers if provided.

        The link_dict parameter offers a convenient setup for test code
        for related methods.
        """
        self.links = link_dict
        if link_headers is not None:
            self.parse(link_headers)

    def parse(self, link_headers):
        """Parse Link header(s) in links.

        Note that per https://tools.ietf.org/html/rfc7230#section-3.2.2
        multiple Link headers are to be treated the same as additional
        comma separated link-value entries as described in
        https://tools.ietf.org/html/rfc5988#section-5

        Designed to parse link_headers as provided by Tornado with
        something like:

        handler = tornado.web.RequestHandler()
        rh = RequestLinks(handler.request.headers.get_list('link'))
        """
        self.links = dict()
        for link_header in link_headers:
            logging.debug("Request Link: " + link_header)
            for link in requests.utils.parse_header_links(link_header):
                if ('rel' in link and 'url' in link):
                    rel = link['rel']
                    url = link['url']
                    if (rel not in self.links):
                        self.links[rel] = list()
                    if (link not in self.links[rel]):
                        self.links[rel].append(url)
        return self.links

    def rel(self, rel):
        """List (possibly empty) of Link rel="..." headers for given rel."""
        return self.links[rel] if (rel in self.links) else []

    @property
    def types(self):
        """Type information from Link rel="type" headers, or empty list()."""
        return self.rel('type')

    @property
    def ldp_type(self):
        """LDP interaction model URI string from request Link rel="type", else None."""
        types = self.types
        # Look for LDP types starting with most specific
        is_ldpnr = LDPNR_URI in types
        rdf_type = LDPRS_URI if LDPRS_URI in types else None
        generic_container_type = LDPC_URI if LDPC_URI in types else None
        container_types = []
        for ctype in LDP_CONTAINER_TYPE_URIS:
            if ctype in types:
                container_types.append(ctype)
        # Work out type and deal with error conditions
        if len(container_types) > 1:
            raise HTTPError(400, "Conflicting LDP container types specified")
        elif len(container_types) == 1:
            # container type overrides an RDF Source which is a compatible superclass
            rdf_type = container_types[0]
        elif generic_container_type:
            # generic container overrides an RDF Source which is a compatible superclass
            rdf_type = generic_container_type
        # Either RDF type or LDPNR...
        if (is_ldpnr and rdf_type):
            raise HTTPError(400, "Conflicting LDP types in Link headers")
        elif (is_ldpnr):
            return(LDPNR_URI)
        else:
            return(rdf_type)

    def acl_uri(self, base_uri=None):
        """ACL URI in request header else None, must be local if base_uri specified."""
        acls = self.rel('acl')
        if len(acls) == 0:
            return None
        if len(acls) > 1:
            raise HTTPError(400, 'Multiple Link rel="acl" in request')
        acl_uri = acls[0]
        if base_uri and not acl_uri.startswith(base_uri):  # FIXME - need better test
            raise HTTPError(400, 'Non-local acl rel="acl" specified')
        return acl_uri


class ResponseLinks(object):
    """Class to handle building of HTTP response links."""

    def __init__(self):
        """Initialize ResponseLinks object."""
        self.links = []

    def __len__(self):
        """Length is number of links."""
        return len(self.links)

    def add(self, rel, uris):
        """Add link to uris with relation rel to list of Link headers to write.

        Does a check to avoid duplication of links with same relation and
        uri as that has no change in meaning.
        """
        for uri in uris:
            link = '<%s>; rel="%s"' % (uri, rel)
            if link not in self.links:
                self.links.append(link)

    @property
    def header(self):
        """Link: header content string property."""
        return ', '.join(self.links)
