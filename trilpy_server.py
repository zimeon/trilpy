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
    parser.add_argument('--no-auth', action='store_true',
                        help="do not support authentication")
    parser.add_argument('--optional-if-match-etag', action='store_true',
                        help="do not require an If-Match header for updates")
    parser.add_argument('--user', dest='users', action='append', default=['http://example.org/rootuser#i=root:secret'],
                        help='add user with webids, username and password (webid=user:pass)')
    parser.add_argument('--no-acl', action='store_true',
                        help="do not support Web Access Control ACLs")
    parser.add_argument('--root-acl', default='/.acl',
                        help="define root ACL path")
    parser.add_argument('--root-webid', default='http://example.org/rootuser#i',
                        help="webid that owns the root container")
    parser.add_argument('--default-acl', default='/default.acl',
                        help="define default ACL path")
    parser.add_argument('--default-acl-webid', default='http://example.org/rootuser#i',
                        help="webid that has ownership in default ACL")
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
    logging.error(args.users)
    base_uri = 'http://localhost:%d' % (args.port)  # FIXME

    # Set up store
    store = Store(base_uri)
    container = LDPC(container_type=container_type)
    store.add(container, args.root_container)
    if (not args.no_acl):
        acl = ACLR(acl_for=args.root_container)
        acl.add_public_read(inherit=True)
        acl.add_owner(webid=args.root_webid, inherit=True)
        acl_uri = store.add(acl, args.root_acl)
        container.acl = acl_uri
        acl_default = ACLR(acl_for=args.default_acl)  # for self hack
        acl_default.add_public_read(inherit=True)
        acl.add_owner(webid=args.default_acl_webid, inherit=True)
        acl.acl_default = store.add(acl, args.default_acl)

    # Set up users
    users = {}
    if len(args.users) > 1:
        # Throw away default if users have been specified
        args.users[1:]
    for user in args.users:
        webid, user_pass = user.split("=", 1)
        users[user_pass] = webid

    run(args.port, store,
        no_auth=(args.no_auth),
        support_put=(not args.no_put),
        support_delete=(not args.no_delete),
        require_if_match_etag=(not args.optional_if_match_etag),
        users=users,
        root_webid=args.root_webid,
        default_acl_webid=args.default_acl_webid)

if __name__ == "__main__":
    main()
