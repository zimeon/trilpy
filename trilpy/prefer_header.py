"""HTTP Prefer header handling.

See:  https://tools.ietf.org/html/rfc7240
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
    return('='.join(p))


def parse_prefer_header(header):
    """Parse a single Prefer header, return preference and params."""
    params = [_strip(s) for s in header.split(';')]
    pref = _strip(params.pop(0))
    return(pref, params)


def find_preference(prefer_headers, preference):
    """Look for specific preference in headers.

    Returns preference found, else nothing.
    """
    for header in prefer_headers:
        (pref, params) = parse_prefer_header(header)
        if (pref == preference):
            return(params)
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
    'http://www.w3.org/ns/ldp#PreferMinimalContainer': 'content',
    'http://www.w3.org/ns/ldp#PreferEmptyContainer': 'content'
}


def ldp_return_representation_omits(prefer_headers):
    """Return set of sections to omit in LDP respose.

    Three possible sections: 'content', 'membership', 'containment'
    where we three the include and omit as opposites with these
    three portions completing the response. Note that LDP explicitly
    says that servers may choose not to implement it this way.
    """
    omits = set()
    try:
        (ptype, uris) = find_return_representation(prefer_headers)
        for uri in uris:
            if (uri in _uri_to_name_map):
                omits.add(_uri_to_name_map[uri])
        if (ptype == 'include'):
            # Invert to get omits
            includes = omits
            omits = set(_uri_to_name_map.values())
            for section in includes:
                omits.remove(section)
    except StopIteration as e:
        logging.debug("Ignored: " + str(e))
    return(omits)
