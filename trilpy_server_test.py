#!/usr/bin/env python
"""Test trilpy by running on localhost."""
import argparse
import unittest
from urllib.parse import urljoin
from subprocess import Popen, run
from rdflib import Graph, URIRef, Literal
import re
import requests
import sys
import time
import uuid


class TCaseWithSetup(unittest.TestCase):
    """Derivative TestCase class with setup to start/stop server and utility methods.

    This class is named TCaseWithSetup (instead of TestCaseWithSetup) in order that unittest
    doesn't pick it up, instantiate and run as part of the discovery process.
    """

    port = 9999
    rooturi = 'http://localhost:' + str(port) + '/'
    LDPC_URI = rooturi
    start_trilpy = True
    new_for_each_test = False
    run_ldp_tests = False
    digest = None

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

    def post_ldpnr(self, uri=None, data='', content_type='text/plain'):
        """POST to create a LDPNR, return location."""
        if (uri is None):
            uri = self.rooturi
        r = requests.post(uri,
                          headers={'Content-Type': content_type,
                                   'Link': '<http://www.w3.org/ns/ldp#NonRDFSource>; rel="type"'},
                          data=data)
        self.assertEqual(r.status_code, 201)
        ldpnr_uri = r.headers.get('Location')
        self.assertTrue(ldpnr_uri)
        return(ldpnr_uri)


class TestLDPSuite(TCaseWithSetup):
    """TestLDPSuite class to run the Java LDP testsuite."""

    def test_ldp_testsuite(self):
        """Run the standard LDP testsuite.

        The exit codes from the testsuite seem to be done with a bitmask, see e.g.
        https://github.com/apache/marmotta/blob/develop/platform/marmotta-ldp/src/test/java/org/apache/marmotta/platform/ldp/LdpSuiteTest.java#L116
        So: 
            1 - failure
            2 - skipped
            8 - no tests
        thus we allow 2 only to allow skips
        """
        base_uri = 'http://localhost:' + str(self.port)
        p = run('java -jar vendor/ldp-testsuite-0.2.0-SNAPSHOT-shaded.jar --server %s '
                '--includedGroups MUST SHOULD --excludedGroups MANUAL --basic'
                % (base_uri), shell=True)
        self.assertEqual(p.returncode | 2, 2)  # allow skipped tests


class TestLDP(TCaseWithSetup):
    """TestLDP class to run LDP tests."""

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


class TestFedora(TCaseWithSetup):
    """TestFedora class to run Fedora specific tests."""

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
        self.assertRegex(uri, self.rooturi)
        # HEAD to get etag and test type
        r = requests.head(uri)
        etag = r.headers.get('etag')
        self.assertTrue(etag)
        self.assertEqual(r.headers.get('Content-Type'), 'text/turtle')
        # Must not be reported as an LDP-RS or container...
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

    def test_fedore_3_1_2(self):
        """Check Implementations MUST support creation and management of containers."""
        # Should be able to create different container types and get back
        # their type in link header
        for container_type in ['http://www.w3.org/ns/ldp#BasicContainer',
                               'http://www.w3.org/ns/ldp#DirectContainer',
                               'http://www.w3.org/ns/ldp#IndirectContainer']:
            r = requests.post(self.LDPC_URI,
                              headers={'Content-Type': 'text/turtle',
                                       'Link': '<' + container_type + '>; rel="type"'},
                              data='<http://ex.org/a> <http://ex.org/b> "xyz".')
            self.assertEqual(r.status_code, 201)
            uri = r.headers.get('Location')
            self.assertTrue(uri)
            r = requests.head(uri)
            links = r.headers.get('Link')
            self.assertIn(container_type, links)

    def test_fedora_3_3_1(self):
        """Check handling of Digest header."""
        if (not self.digest):
            return()
        r = requests.post(self.rooturi,
                          headers={'Content-Type': 'text/plain',
                                   'Link': '<http://www.w3.org/ns/ldp#NonRDFSource>; rel="type"',
                                   'Digest': 'SURELY-NOT-SUPPORTED-TYPE'},  # FIXME - Digest syntax??
                          data='stuff')
        self.assertEqual(r.status_code, 400)
        # FIXME - Add invalid digest for valid type
        # FIXME - Add valid digest for valid type

    def test_fedora_3_4(self):
        """Check PUT and content model handling."""
        # LDPNR cannot be replaced with LDPRS, or LDPC types
        uri = self.post_ldpnr(data=b'I am an LDPNR, can only be replace with same')
        r = requests.head(uri)
        etag = r.headers.get('etag')
        for model in ['http://www.w3.org/ns/ldp#RDFSource',
                      'http://www.w3.org/ns/ldp#Container',
                      'http://www.w3.org/ns/ldp#BasicContainer',
                      'http://www.w3.org/ns/ldp#DirectContainer',
                      'http://www.w3.org/ns/ldp#IndirectContainer']:
            r = requests.put(uri,
                             headers={'Content-Type': 'text/turtle',
                                      'If-Match': etag,
                                      'Link': '<http://www.w3.org/ns/ldp#RDFSource>; rel="type"'},
                             data='<http://ex.org/a> <http://ex.org/b> "xyz".')
            self.assertEqual(r.status_code, 409)
        # LDPRS or LDPS types cannot be replaced with LDPRS
        for model in ['http://www.w3.org/ns/ldp#RDFSource',
                      'http://www.w3.org/ns/ldp#Container',
                      'http://www.w3.org/ns/ldp#BasicContainer',
                      'http://www.w3.org/ns/ldp#DirectContainer',
                      'http://www.w3.org/ns/ldp#IndirectContainer']:
            r = requests.post(self.rooturi,
                              headers={'Content-Type': 'text/turtle',
                                       'Link': '<' + model + '>; rel="type"'},
                              data='<http://ex.org/a> <http://ex.org/b> "xyz".')
            self.assertEqual(r.status_code, 201)
            uri = r.headers.get('Location')
            self.assertTrue(uri)
            r = requests.head(uri)
            etag = r.headers.get('etag')
            r = requests.put(uri,
                             headers={'Content-Type': 'text/plain',
                                      'If-Match': etag,
                                      'Link': '<http://www.w3.org/ns/ldp#NonRDFSource>; rel="type"'},
                             data='Not RDF')
            self.assertEqual(r.status_code, 409)
        # FIXME - Alsmot check incompatible LDPRS replacements

    def test_fedore_3_4_1(self):
        """Check PUT to LDPRS to update triples."""
        r = requests.post(self.rooturi,
                          headers={'Content-Type': 'text/turtle',
                                   'Link': '<http://www.w3.org/ns/ldp#RDFSource>; rel="type"'},
                          data='<http://ex.org/a> <http://ex.org/b> "xyz".')
        self.assertEqual(r.status_code, 201)
        uri = r.headers.get('Location')
        self.assertTrue(uri)
        r = requests.head(uri)
        etag = r.headers.get('etag')
        r = requests.put(uri,
                         headers={'Content-Type': 'text/turtle',
                                  'If-Match': etag,
                                  'Link': '<http://www.w3.org/ns/ldp#RDFSource>; rel="type"'},
                         data='<http://ex.org/a> <http://ex.org/b> "ZYX".')
        self.assertEqual(r.status_code, 204)
        r = requests.get(uri)
        g = Graph()
        g.parse(format='turtle', data=r.content)
        self.assertNotIn(Literal('xyz'), g.objects())
        self.assertIn(Literal('ZYX'), g.objects())

    def test_fedora_3_4_2(self):
        """Check LDPNR MUST support PUT to replace content."""
        uri = self.post_ldpnr(data=b'original data here')
        r = requests.head(uri)
        etag = r.headers.get('etag')
        new_data = b'WOW! NEW DATA'
        r = requests.put(uri,
                         headers={'Content-Type': 'text/plain',
                                  'If-Match': etag,
                                  'Link': '<http://www.w3.org/ns/ldp#NonRDFSource>; rel="type"'},
                         data=new_data)
        self.assertEqual(r.status_code, 204)
        r = requests.get(uri)
        self.assertEqual(r.content, new_data)

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
        # POST LDR-NR under root, expect to get new ACL
        child_uri = self.post_ldpnr(uri=self.rooturi, data='stuff')
        self.assertTrue(child_uri)
        r = requests.head(child_uri)
        self.assertEqual(r.status_code, 200)
        acls = self.find_links(r.headers.get('link'), 'acl')
        self.assertEqual(len(acls), 1)
        self.assertNotEqual(acls[0], root_acl)
        self.assertNotEqual(acls[0], child_uri)
        # Cleanup
        r = requests.delete(child_uri)
        # Try two level POST
        r = requests.post(self.rooturi,
                          headers={'Content-Type': 'text/turtle',
                                   'Link': '<http://www.w3.org/ns/ldp#BasicContainer>; rel="type"'})
        self.assertEqual(r.status_code, 201)
        child_uri = r.headers.get('Location')
        self.assertTrue(child_uri)
        r = requests.post(child_uri,
                          headers={'Content-Type': 'text/turtle',
                                   'Link': '<http://www.w3.org/ns/ldp#BasicContainer>; rel="type"'})
        self.assertEqual(r.status_code, 201)
        grandchild_uri = r.headers.get('Location')
        self.assertTrue(grandchild_uri)
        r = requests.head(grandchild_uri)
        self.assertEqual(r.status_code, 200)
        acls = self.find_links(r.headers.get('link'), 'acl')
        self.assertEqual(len(acls), 1)
        self.assertNotEqual(acls[0], root_acl)
        self.assertNotEqual(acls[0], child_uri)
        #
        # FIXME - Add check of skipping over intermediate containment resource
        # FIXME - that has no heritable auths
        #
        # Cleanup
        r = requests.delete(child_uri)
        r = requests.delete(grandchild_uri)


# If run from command line, do tests
if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=False,
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--rooturi', action='store', default=None,
                        help="Use LDP at given rooturi rather than running trilpy")
    parser.add_argument('--fresh', action='store_true',
                        help="Start trilpy fresh for each test (slow)")
    parser.add_argument('--port', type=int, default=9999,
                        help="Start trilpy on port")
    parser.add_argument('--digest', action='store', default='sha1',
                        help="Digest type to test.")
    parser.add_argument('--VeryVerbose', '-V', action='store_true',
                        help="be verbose.")
    parser.add_argument('--help', '-h', action='store_true',
                        help="show this help message and exit")
    (opts, args) = parser.parse_known_args()
    TCaseWithSetup.port = opts.port
    TCaseWithSetup.digest = opts.digest
    if (opts.rooturi):
        TCaseWithSetup.start_trilpy = False
        TCaseWithSetup.rooturi = opts.rooturi
    else:
        TCaseWithSetup.new_for_each_test = opts.fresh
    if (opts.help):
        # Show my help and then pass on to unittest, wish there were just a way
        # to pass in the parser object (but I don't see one)
        parser.print_help()
        args.append('--help')
        print('\nand see also arguments from unittest:\n')
    # Remaining args go to unittest
    unittest.main(verbosity=(2 if opts.VeryVerbose else 1),
                  argv=sys.argv[:1] + args)
