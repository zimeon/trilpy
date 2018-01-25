#!/usr/bin/env python3
"""Trilpy - LDP & Fedora playpen."""

import sys
import logging
import argparse
from trilpy import Store, LDPC, ACLR, LDP, run


def main():
    """Command line handler."""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--port', '-p', type=int, default=9999,
                        help="port to run on")
    parser.add_argument('--root-container', '-r', default='/',
                        help="define root container path")
    parser.add_argument('--container-type', '-c', default='basic',
                        help="root container type")
    parser.add_argument('--no-put', action='store_true',
                        help="do not support PUT method")
    parser.add_argument('--no-delete', action='store_true',
                        help="do not support DELETE method")
    parser.add_argument('--no-acl', action='store_true',
                        help="do not support Web Access Control ACLs")
    parser.add_argument('--root-acl', default='/.acl',
                        help="define root ACL path")
    parser.add_argument('--default-acl', default='/default.acl',
                        help="define default ACL path")
    parser.add_argument('--verbose', '-v', action='store_true',
                        help="be verbose.")
    args = parser.parse_args()
    if (args.container_type == 'basic'):
        container_type = LDP.BasicContainer
    elif (args.container_type == 'direct'):
        container_type = LDP.DirectContainer
    elif (args.container_type == 'indirect'):
        container_type = LDP.IndirectContainer
    else:
        parser.error("Unrecognized container type '%s'" %
                     (args.container_type))
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)
    base_uri = 'http://localhost:%d' % (args.port)  # FIXME
    store = Store(base_uri)
    container = LDPC(container_type=container_type)
    store.add(container, args.root_container)
    if (not args.no_acl):
        acl = ACLR(acl_for=args.root_container)
        acl.add_public_read(inherit=True)
        acl_uri = store.add(acl, args.root_acl)
        container.acl = acl_uri
        acl_default = ACLR(acl_for=args.default_acl)  # for self hack
        acl_default.add_public_read(inherit=True)
        acl.acl_default = store.add(acl, args.default_acl)
    run(args.port, store,
        support_put=(not args.no_put),
        support_delete=(not args.no_delete),
        support_acl=(not args.no_acl))

if __name__ == "__main__":
    main()
