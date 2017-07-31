"""Import to require python 3."""
import sys

if sys.version_info < (3, 3):
    raise Exception("Must use python 3.3 or greater (probably)!")
