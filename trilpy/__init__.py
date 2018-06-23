"""Trilpy module.

Requires python 3.3 or greater.
"""
import sys
from .store import Store, KeyDeleted
from .ldpr import LDPR
from .ldprs import LDPRS
from .ldpc import LDPC
from .acl import ACLR
from .tornado import run
from .namespace import LDP, ACL

__version__ = '0.0.3'

if sys.version_info < (3, 3):  # pragma: no cover
    raise Exception("Must use python 3.3 or greater (probably)!")
