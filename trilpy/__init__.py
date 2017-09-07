"""Trilpy module.

Requires python 3.3 or greater.
"""
import sys
from .store import Store
from .ldpc import LDPC
from .acl import ACLR
from .tornado import run
from .namespace import LDP, ACL

if sys.version_info < (3, 3):
    raise Exception("Must use python 3.3 or greater (probably)!")
