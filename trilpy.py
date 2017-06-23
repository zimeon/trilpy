#!/usr/bin/env python
"""Trilpy - LDP & Fedora playpen."""

import logging
import optparse
from trilpy.store import Store
from trilpy.ldpc import LDPC
from trilpy.tornado import run

def main():
    """Command line handler."""
    parser = optparse.OptionParser()
    parser.add_option('--port', '-p', type='int', default=9999,
                      help="port to run on (default %default)")
    parser.add_option('--root-container', '-c', default='/',
                      help="define root container (default %default)")
    parser.add_option('--no-put', action='store_true',
                      help="do not support PUT method")
    parser.add_option('--no-delete', action='store_true',
                      help="do not support DELETE method")
    parser.add_option('--verbose', '-v', action='store_true',
                      help="be verbose.")
    (opts, args) = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if opts.verbose else logging.INFO)
    store = Store()
    store.add(opts.root_container, LDPC())
    run(opts.port, store,
        support_put = (not opts.no_put),
        support_delete = (not opts.no_delete))

if __name__ == "__main__":
    main()
