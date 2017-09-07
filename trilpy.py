#!/usr/bin/env python
"""Trilpy - LDP & Fedora playpen."""

import sys
import logging
import optparse
from trilpy import Store, LDPC, ACLR, LDP, run

def main():
    """Command line handler."""
    parser = optparse.OptionParser()
    parser.add_option('--port', '-p', type='int', default=9999,
                      help="port to run on (default %default)")
    parser.add_option('--root-container', '-r', default='/',
                      help="define root container path (default %default)")
    parser.add_option('--container-type', '-c', default='basic',
                      help="root container type (default %default)")
    parser.add_option('--no-put', action='store_true',
                      help="do not support PUT method")
    parser.add_option('--no-delete', action='store_true',
                      help="do not support DELETE method")
    parser.add_option('--no-acl', action='store_true',
                      help="do not support Web Access Control ACLs")
    parser.add_option('--root-acl', default='/.acl',
                      help="define root ACL path (default %default)")
    parser.add_option('--default-acl', default='/default.acl',
                      help="define default ACL path (default %default)")
    parser.add_option('--verbose', '-v', action='store_true',
                      help="be verbose.")
    (opts, args) = parser.parse_args()
    if (opts.container_type == 'basic'):
        container_type = LDP.BasicContainer
    elif (opts.container_type == 'direct'):
        container_type = LDP.DirectContainer
    elif (opts.container_type == 'indirect'):
        container_type = LDP.IndirectContainer
    else:
        parser.error("Unrecognized container type '%s'" %
                     (opts.container_type))
    logging.basicConfig(level=logging.DEBUG if opts.verbose else logging.INFO)
    base_uri = 'http://localhost:%d' % (opts.port)  # FIXME
    store = Store(base_uri)
    container = LDPC(container_type=container_type)
    store.add(container, opts.root_container)
    if (not opts.no_acl):
        acl = ACLR(acl_for=opts.root_container)
        acl.add_public_read(inherit=True)
        acl_uri = store.add(acl, opts.root_acl)
        container.acl = acl_uri
        acl_default = ACLR(acl_for=opts.default_acl)  # for self hack
        acl_default.add_public_read(inherit=True)
        acl.acl_default = store.add(acl, opts.default_acl)
    run(opts.port, store,
        support_put=(not opts.no_put),
        support_delete=(not opts.no_delete),
        support_acl=(not opts.no_acl))

if __name__ == "__main__":
    main()
