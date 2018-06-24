"""HTTP Prefer header handling.

See https://tools.ietf.org/html/rfc7240 for foundational specification
and https://www.w3.org/TR/ldp/#prefer-parameters for LDP use.
"""

import logging


def _strip(s):
    """Strip whitespace from around s, or =, and zap empty param."""
    s = s.lstrip().rstrip()
    p = s.split('=', maxsplit=2)
    p[0] = p[0].rstrip(' ')
    if (len(p) == 2):
        p[1] = p[1].lstrip(' ')
        if (p[1] == '""'):
            p.pop()
    return '='.join(p)


def parse_prefer_header(header):
    """Parse a single Prefer header, return preference and params."""
    params = [_strip(s) for s in header.split(';')]
    pref = _strip(params.pop(0))
    return pref, params


def find_preference(prefer_headers, preference):
    """Look for specific preference in headers.

    Returns preference found, else nothing.
    """
    for header in prefer_headers:
        (pref, params) = parse_prefer_header(header)
        if (pref == preference):
            return params
    return()


def find_return_representation(prefer_headers):
    """Look for return=representation preference as used in LDP.

    Returns type ('omit' or 'include') and list of URIs, else
    (None, []).
    """
    params = find_preference(prefer_headers, 'return=representation')
    if (len(params) > 1):
        raise Exception("Bad paramaters for return=representation preference")
    elif (len(params) == 0):
        return(None, [])
    (ptype, quoted_uris) = params[0].split('=')
    if (ptype not in ['omit', 'include']):
        raise Exception("Bad type for return=representation preference")
    uris = quoted_uris.lstrip('"').rstrip('"').split(' ')
    return(ptype, uris)


_uri_to_name_map = {
    'http://www.w3.org/ns/ldp#PreferContainment': 'containment',
    'http://www.w3.org/ns/ldp#PreferMembership': 'membership',
    'http://www.w3.org/ns/ldp#PreferMinimalContainer': 'minimal',
    'http://www.w3.org/ns/ldp#PreferEmptyContainer': 'minimal'
}


def parse_prefer_return_representation(prefer_headers):
    """Return set of sections to omit in LDP response.

    Three sections are defined in LDP: 'minimal', 'membership', 'containment'
    where we here consider these to be three orthogonal sections that make
    up the response. Specification of include="..." for the LDP defined sections
    is treated as the opposite of omit="...". Note that LDP explicitly says that
    servers may choose not to implement it this way.

    Note that 'minimal' is defined https://www.w3.org/TR/ldp/#dfn-minimal-container-triples
    as all thr triples (server managed and client managed content) that would be
    returned if there were no members and no contained resources. It should include
    all the triples defining membership predicates etc..

    However, if the Prefer header has include="..." with some other preference
    not defined by LDP, and does not specify an LDP section then we will treat
    that as if all sections were included (i.e. omits = set() ).
    """
    omits = set()
    includes = set()
    try:
        (ptype, uris) = find_return_representation(prefer_headers)
        if (ptype == 'omit'):
            # For omit we recognize only LDP URIs
            for uri in uris:
                if (uri in _uri_to_name_map):
                    omits.add(_uri_to_name_map[uri])
        else:  # ptype == 'include'
            # For include we treat LDP and non-LDP URIs differently
            ldp_includes = set()
            for uri in uris:
                if (uri in _uri_to_name_map):
                    ldp_includes.add(_uri_to_name_map[uri])
                else:
                    includes.add(uri)
            if (len(ldp_includes) > 0):
                # Invert to get omits
                omits = set(_uri_to_name_map.values())
                for section in ldp_includes:
                    omits.remove(section)
    except (TypeError, StopIteration) as e:
        logging.debug("Ignored: " + str(e))
    return omits, includes
