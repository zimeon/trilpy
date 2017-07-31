#!/usr/bin/env python
"""Test trilpy by running on localhost."""
import trilpy.require_python3
import unittest
from urllib.parse import urljoin
from subprocess import Popen
import requests
import time

port = 9999
baseurl = 'http://localhost:' + str(port) + '/'


class TestAll(unittest.TestCase):
    """TestAll class to run tests."""

    LDPC_URI = baseurl

    def setUp(self):
        """Start trilpy."""
        self.proc = Popen(['/usr/bin/env', 'python', './trilpy.py',
                           '-v', '-p', str(port)])
        print("Started trilpy (pid=%d)" % (self.proc.pid))
        time.sleep(1)

    def tearDown(self):
        """Kill trilpy."""
        self.proc.kill()
        outs, errs = self.proc.communicate()
        print("Killed trilpy (%s, %s)" % (outs, errs))

    def test01_unknown_paths(self):
        """Expect 404 for bad path."""
        url = urljoin(baseurl, 'does_not_exist')
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
        r = requests.get(urljoin(baseurl, '/'))
        self.assertEqual(r.status_code, 200)

    def test03_delete_root_ldpc(self):
        """Delete the LDPC at /."""
        url = urljoin(baseurl, '/')
        r = requests.delete(url)
        self.assertEqual(r.status_code, 200)
        r = requests.get(url)
        self.assertEqual(r.status_code, 410)

    def test_ldp_4_2_4_5(self):
        """If-Match on ETag for PUT to replace."""
        url = urljoin(baseurl, '/test1')
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

    def test_fcrepo_3_1_1(self):
        """Resource creation SHOULD follow Link: rel='type' for LDP-NR.

        https://fcrepo.github.io/fcrepo-specification/#ldpnr-ixn-model
        """
        # POST Turtle object as LDR-NR
        r = requests.post(self.LDPC_URI,
                          headers={'Content-Type': 'text/turtle',
                                   'Link': '<http://www.w3.org/ns/ldp#NonRDFSource>; rel="type"'},
                          data='<http://ex.org/a> <http://ex.org/b> "123".')
        self.assertEqual(r.status_code, 201)
        uri = r.headers.get('Location')
        self.assertRegexpMatches(uri, baseurl)
        # HEAD to get etag
        r = requests.head(uri)
        etag = r.headers.get('etag')
        self.assertTrue(etag)
        self.assertEqual(r.headers.get('Content-Type'), 'text/turtle')
        # Must not be reported as am LDP-RS container...
        links = r.headers.get('Link')
        self.assertNotIn('http://www.w3.org/ns/ldp#RDFSource', links)
        self.assertNotIn('http://www.w3.org/ns/ldp#Container', links)
        self.assertNotIn('http://www.w3.org/ns/ldp#BasicContainer', links)
        self.assertNotIn('http://www.w3.org/ns/ldp#DirectContainer', links)
        self.assertNotIn('http://www.w3.org/ns/ldp#IndirectContainer', links)
        # As LDP-NR should be OK to replace with diff media type
        r = requests.put(uri,
                         headers={'If-Match': etag,
                                  'Content-Type': 'text/stuff'},
                         data='Hello there!')
        self.assertEqual(r.status_code, 204)

# If run from command line, do tests
if __name__ == '__main__':
    unittest.main(verbosity=2)
