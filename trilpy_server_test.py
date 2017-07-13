#!/usr/bin/env python
"""Test trilpy by running on localhost."""
import unittest
from urllib.parse import urljoin
from subprocess import Popen
import re
import requests
import time


class TestAll(unittest.TestCase):
    """TestAll class to run tests."""

    port = 9999
    baseuri = 'http://localhost:' + str(port) + '/'
    rooturi = baseuri

    def setUp(self):
        """Start trilpy."""
        self.proc = Popen(['/usr/bin/env', 'python', './trilpy.py',
                           '-v', '-p', str(self.port)])
        print("Started trilpy (pid=%d)" % (self.proc.pid))
        time.sleep(2)

    def tearDown(self):
        """Kill trilpy."""
        self.proc.kill()
        outs, errs = self.proc.communicate()
        print("Killed trilpy (%s, %s)" % (outs, errs))

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
        url = urljoin(self.baseuri, 'does_not_exist')
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
        r = requests.get(urljoin(self.baseuri, '/'))
        self.assertEqual(r.status_code, 200)

    def test03_delete_root_ldpc(self):
        """Delete the LDPC at /."""
        url = urljoin(self.baseuri, '/')
        r = requests.delete(url)
        self.assertEqual(r.status_code, 200)
        r = requests.get(url)
        self.assertEqual(r.status_code, 410)

    def test_ldp_4_2_4_5(self):
        """If-Match on ETag for PUT to replace."""
        url = urljoin(self.baseuri, '/test1')
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
    unittest.main(verbosity=2)
