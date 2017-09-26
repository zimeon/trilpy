"""Digest handling per rfc3230.

IANA registry of digest names:
https://www.iana.org/assignments/http-dig-alg/http-dig-alg.xhtml
"""
from base64 import b64encode
from collections import OrderedDict
import hashlib
import re


class UnsupportedDigest(Exception):
    """Exception to indicate an unsupported digest type."""

    pass


class BadDigest(Exception):
    """Exception to indicate a bad digest comparison."""

    pass


class Digest(object):
    """Digest class."""

    # Digest names are case insensitive, use lowercase as canonical
    # Values in hash are the hashlib functions to generate hash
    #
    # FIXME - F4 uses 'sha1' but IANA has 'sha', include both here. See
    # FIXME - https://github.com/fcrepo/fcrepo-specification/issues/235
    supported_digests = {'md5': hashlib.md5, 'sha': hashlib.sha1,
                         'sha1': hashlib.sha1,
                         'sha-256': hashlib.sha256, 'sha-512': hashlib.sha512}

    def __init__(self, digest_header=None, want_digest_header=None):
        """Initialize Digest object with optional HTTP header parsing."""
        self.digests = {}
        self.want_digest = None
        if (digest_header is not None):
            self.parse_digest(digest_header)
        if (want_digest_header is not None):
            self.parse_want_digest(want_digest_header)

    def parse_digest(self, digest_header):
        """Parse HTTP Digest header.

        Records the set of digests specified in self.digests, raises a
        BadDigest exception if an unsupported type is encountered.
        """
        for instance_digest in digest_header.split(','):
            try:
                digest_type, digest = instance_digest.split('=', 1)
            except ValueError:
                raise BadDigest("Bad digest specification " + instance_digest)
            digest_type = digest_type.lower()
            if (digest_type not in self.supported_digests):
                raise UnsupportedDigest("Unsupported digest type " + digest_type)
            self.digests[digest_type] = digest

    def parse_want_digest(self, want_digest_header):
        """Parse HTTP Want-Digest header.

        Records the preferred supported digest type in self.want_digest, will
        raise an BadDigest exception if no supported digest is specified
        with non-zero q value.
        """
        self.want_digest = None
        digests = OrderedDict()  # so we'll pick the first specified if multiple with same q are supported
        highest_q = 0.0
        for digest_spec in want_digest_header.split(','):
            digest_spec = digest_spec.lstrip(' ')
            m = re.match(r'''([\w\-]+)(;q=([\d\.]+))?$''', digest_spec)
            if (m):
                digest_type = m.group(1).lower()
                try:
                    q = float(m.group(3)) if m.group(3) else 1.0
                except ValueError:
                    raise BadDigest("Bad q value for digest type " + digest_type)
                if (q > 1.0):
                    raise BadDigest("Bad q value (>1.0) for digest type " + digest_type)
                digests[digest_type] = q
                if (q > highest_q):
                    highest_q = q
            else:
                raise BadDigest("Bad Want-Digest specifiation " + digest_spec)
        # Have read all, get set with highest q, see if one is supported
        if (highest_q == 0.0):
            raise BadDigest("Bad Want-Digest specifiation, no type with q>0.0")
        digest_types = [t for t, q in digests.items() if q == highest_q]
        for digest_type in digest_types:
            if (digest_type in self.supported_digests):
                self.want_digest = digest_type
                return
        raise UnsupportedDigest("No supported digest type for q=%f (got %s)" % (highest_q, ','.join(digest_types)))

    def check(self, content):
        """Check content against the stored digests, raise BadDigest if bad."""
        for (digest_type, digest) in self.digests.items():
            cdigest = self._calculate_digest(digest_type, content)
            if (cdigest != digest):
                raise BadDigest("Digest type %s doesn't match: got %s, expected %s" % (digest_type, cdigest, digest))

    def digest_value(self, content):
        """Create digest value for response header with the content supplied, accordintg parsed Want-Digest."""
        return(self.want_digest + '=' + self._calculate_digest(self.want_digest, content))

    def _calculate_digest(self, digest_type, content):
        """Calculate digest string for given digest_type over byte content."""
        try:
            digest_func = self.supported_digests[digest_type]
        except KeyError:
            raise UnsupportedDigest("Unsupported digest type %s requested")
        return(b64encode(digest_func(content).digest()).decode('utf-8'))
