#!/usr/bin/env python
"""Test trilpy by running on localhost."""
import argparse
import unittest
from urllib.parse import urljoin
from subprocess import Popen
import re
import requests
import sys
import time
import uuid


class TestAll(unittest.TestCase):
    """TestAll class to run tests."""

    port = 9999
    rooturi = 'http://localhost:' + str(port) + '/'
    start_trilpy = True
    new_for_each_test = False

    @classmethod
    def _start_trilpy(cls):
        """Start trilpy."""
        cls.proc = Popen(['/usr/bin/env', 'python', './trilpy.py',
                          '-v', '-p', str(cls.port)])
        print("Started trilpy (pid=%d)" % (cls.proc.pid))
        time.sleep(2)

    @classmethod
    def _stop_trilpy(cls):
        """Kill trilpy."""
        cls.proc.kill()
        outs, errs = cls.proc.communicate()
        print("Killed trilpy (%s, %s)" % (outs, errs))

    @classmethod
    def setUpClass(cls):
        """Setup for class."""
        if (cls.start_trilpy and not cls.new_for_each_test):
            cls._start_trilpy()

    @classmethod
    def tearDownClass(cls):
        """Teardown for class."""
        if (cls.start_trilpy and not cls.new_for_each_test):
            cls._stop_trilpy()

    def setUp(self):
        """Setup for each test."""
        if (self.start_trilpy and self.new_for_each_test):
            self._start_trilpy()

    def tearDown(self):
        """Teardown for each test."""
        if (self.start_trilpy and self.new_for_each_test):
            self._stop_trilpy()

    def find_links(self, link_header, rel):
        """Find list of link values with given rel."""
        values = []
        for link in link_header.split(','):
            m = re.match(r'\s*<([^>]+)>\s*;\s*rel="([^"]+)"\s*', link)
            # print("## " + link + ' -- ' + str(m))
            if (m and m.group(2) == rel):
                values.append(m.group(1))
        return(values)

    def links_include(self, link_header, rel, value=None):
        """True if link_header include link with given rel and value.

        If value is None then the value is not tested.
        """
        values = self.find_links(link_header, rel)
        if (value is None):
            return(len(values) > 0)
        else:
            return(value in values)

    def test01_unknown_paths(self):
        """Expect 404 for bad path."""
        url = urljoin(self.rooturi, 'does_not_exist')
        r = requests.get(url)
        self.assertEqual(r.status_code, 404)
        r = requests.head(url)
        self.assertEqual(r.status_code, 404)
        r = requests.post(url)
        self.assertEqual(r.status_code, 404)
        r = requests.delete(url)
        self.assertEqual(r.status_code, 404)

    def test02_b(self):
        """Another test."""
        r = requests.get(urljoin(self.rooturi, '/'))
        self.assertEqual(r.status_code, 200)

#    def test03_delete_root_ldpc(self):
#        """Delete the LDPC at /."""
#        url = urljoin(self.rooturi, '/')
#        r = requests.delete(url)
#        self.assertEqual(r.status_code, 200)
#        r = requests.get(url)
#        self.assertEqual(r.status_code, 410)

    def test_ldp_4_2_4_5(self):
        """If-Match on ETag for PUT to replace."""
        url = urljoin(self.rooturi, '/' + str(uuid.uuid1()))
        # PUT object
        r = requests.put(url,
                         headers={'Content-Type': 'text/turtle'},
                         data='<http://ex.org/a> <http://ex.org/b> "1".')
        self.assertEqual(r.status_code, 201)
        # Match
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        etag = r.headers.get('etag')
        self.assertTrue(etag)
        r = requests.put(url,
                         headers={'If-Match': etag,
                                  'Content-Type': 'text/turtle'},
                         data='<http://ex.org/a> <http://ex.org/b> "2".')
        self.assertEqual(r.status_code, 204)
        # Now mismatch
        r = requests.get(url)
        self.assertEqual(r.status_code, 200)
        etag = r.headers.get('etag')
        self.assertTrue(etag)
        r = requests.put(url,
                         headers={'If-Match': etag + 'XXX',
                                  'Content-Type': 'text/turtle'},
                         data='<http://ex.org/a> <http://ex.org/b> "3".')
        self.assertEqual(r.status_code, 412)
        # Cleanup
        r = requests.delete(url)

    def test_fedora_5_1(self):
        """Check ACLs are LDP RDF Sources."""
        r = requests.head(self.rooturi)
        self.assertEqual(r.status_code, 200)
        acls = self.find_links(r.headers.get('link'), 'acl')
        self.assertEqual(len(acls), 1)
        r = requests.head(acls[0])
        self.assertEqual(r.status_code, 200)
        self.assertTrue(self.links_include(
            r.headers.get('link'),
            'type', 'http://www.w3.org/ns/ldp#RDFSource'))

    def test_fedora_5_2(self):
        """Check ACLs are discoverable via Link Headers."""
        r = requests.head(self.rooturi)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(self.links_include(r.headers.get('link'), 'acl'))
        r = requests.get(self.rooturi)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(self.links_include(r.headers.get('link'), 'acl'))

    def test_fedora_5_3(self):
        """Check ACL inheritance."""
        # ACL for root
        r = requests.head(self.rooturi)
        self.assertEqual(r.status_code, 200)
        acls = self.find_links(r.headers.get('link'), 'acl')
        self.assertEqual(len(acls), 1)
        root_acl = acls[0]
        # POST LDR-NR under root, expect to get same ACL
        r = requests.post(self.rooturi,
                          headers={'Content-Type': 'text/plain',
                                   'Link': '<http://www.w3.org/ns/ldp#NonRDFSource>; rel="type"'},
                          data='stuff')
        self.assertEqual(r.status_code, 201)
        child_uri = r.headers.get('Location')
        self.assertTrue(child_uri)
        r = requests.head(child_uri)
        self.assertEqual(r.status_code, 200)
        acls = self.find_links(r.headers.get('link'), 'acl')
        self.assertEqual(len(acls), 1)
        self.assertEqual(acls[0], root_acl)
        # Cleanup
        r = requests.delete(child_uri)
        # Try two level POST
        # FIXME - currently needs data to determine type, should use Link
        r = requests.post(self.rooturi,
                          headers={'Content-Type': 'text/turtle',
                                   'Link': '<http://www.w3.org/ns/ldp#BasicContainer>; rel="type"'},
                          data='<> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/ns/ldp#BasicContainer> .')
        self.assertEqual(r.status_code, 201)
        child_uri = r.headers.get('Location')
        self.assertTrue(child_uri)
        r = requests.post(child_uri,
                          headers={'Content-Type': 'text/turtle',
                                   'Link': '<http://www.w3.org/ns/ldp#BasicContainer>; rel="type"'},
                          data='<> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <http://www.w3.org/ns/ldp#BasicContainer> .')
        self.assertEqual(r.status_code, 201)
        grandchild_uri = r.headers.get('Location')
        self.assertTrue(grandchild_uri)
        r = requests.head(grandchild_uri)
        self.assertEqual(r.status_code, 200)
        acls = self.find_links(r.headers.get('link'), 'acl')
        self.assertEqual(len(acls), 1)
        self.assertEqual(acls[0], root_acl)
        #
        # FIXME - Add check of skipping over intermediate containment resource
        # FIXME - that has no heritable auths
        #
        # Cleanup
        r = requests.delete(child_uri)
        r = requests.delete(grandchild_uri)

# If run from command line, do tests
if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--rooturi', '-r', action='store', default='',
                        help="Use LDP at given rooturi rather than running trilpy")
    parser.add_argument('--fresh', action='store_true',
                        help="Start trilpy fresh for each test (slow)")
    parser.add_argument('--port', '-p', type=int, default=9999,
                        help="Start trilp on port (default %default)")
    parser.add_argument('--VeryVerbose', '-V', action='store_true',
                        help="be verbose.")
    (opts, args) = parser.parse_known_args()
    TestAll.port = opts.port
    if (opts.rooturi):
        TestAll.start_trilpy = False
        TestAll.rooturi = opts.rooturi
    else:
        TestAll.new_for_each_test = opts.fresh
    # Remaining args go to unittest
    unittest.main(verbosity=(2 if opts.VeryVerbose else 1),
                  argv=sys.argv[:1] + args)
