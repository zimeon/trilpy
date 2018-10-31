#!/usr/bin/env python3
"""Test trilpy by running on localhost."""
import argparse
from base64 import b64encode
import unittest
import http.client
from urllib.parse import urljoin, urlparse
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
    rooturi = 'http://localhost:' + str(port)
    no_auth = False
    start_trilpy = True
    new_for_each_test = False
    run_ldp_tests = False
    skip_should = False
    trilpy_path = None
    ldp_test_suite_jar = None
    fedora_api_test_suite_jar = None
    digest = None

    root_webid = 'http://example.org/user/root'  # FIXME - last segment must match username, see https://github.com/fcrepo/Fedora-API-Test-Suite/issues/288
    root_user = 'root'
    root_pass = 'secret'
    other_webid = 'http://example.org/user/other'
    other_user = 'other'
    other_pass = 'tersec'

    @classmethod
    def _start_trilpy(cls):
        """Start trilpy."""
        options = ['-v', '-p', str(cls.port)]
        if (cls.no_auth):
            options.append('--no-auth')
        else:
            options.append('--user')
            options.append("%s=%s:%s" % (cls.root_webid, cls.root_user, cls.root_pass))
            options.append('--user')
            options.append("%s=%s:%s" % (cls.other_webid, cls.other_user, cls.other_pass))
            options.append('--root-webid')
            options.append(cls.root_webid)
            options.append('--default-acl-webid')
            options.append(cls.root_webid)
        if cls.__name__ == 'FedoraAPITestSuite':
            # FIXME - disable If-Match check until test suite issue
            # https://github.com/fcrepo4-labs/Fedora-API-Test-Suite/issues/88
            # is resolved
            options.append('--optional-if-match-etag')
        print("Starting trilpy with: " + ' '.join(options))
        cls.proc = Popen(['/usr/bin/env', 'python', cls.trilpy_path] + options)
        print("Started trilpy (pid=%d)" % (cls.proc.pid))
        for n in range(0, 20):
            time.sleep(1)
            try:
                if (cls.no_auth):
                    r = requests.head(cls.rooturi, timeout=0.5)
                else:
                    r = requests.head(cls.rooturi, auth=(cls.root_user, cls.root_pass), timeout=0.5)
                if (r.status_code == 200):
                    break
                else:
                    raise Exception("Server started but returns bad status code %d" % (r.status_code))
            except requests.exceptions.Timeout:
                pass
            print("Waiting on trilpy startup (%ds)..." % (n))

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
        if (link_header is None):
            return values
        for link in link_header.split(','):
            m = re.match(r'\s*<([^>]+)>\s*;\s*rel="([^"]+)"\s*', link)
            # print("## " + link + ' -- ' + str(m))
            if (m and m.group(2) == rel):
                values.append(m.group(1))
        return values

    def links_include(self, link_header, rel, value=None):
        """True if link_header includes link with given rel and value.

        If value is None then the value is not tested.
        """
        values = self.find_links(link_header, rel)
        if (value is None):
            return(len(values) > 0)
        if (value is 'ANY_CONTAINER'):
            return(('http://www.w3.org/ns/ldp#Container' in values) or
                   ('http://www.w3.org/ns/ldp#BasicContainer' in values) or
                   ('http://www.w3.org/ns/ldp#DirectContainer' in values) or
                   ('http://www.w3.org/ns/ldp#IndirectContainer' in values))
        else:
            return(value in values)

    def assert_link_types_include(self, r, link_types):
        """Response r include Link header with rel='type' for link_types (list)."""
        link_header = r.headers.get('link')
        type_links = self.find_links(link_header, 'type')
        for link_type in link_types:
            self.assertIn(link_type, type_links)

    def assert_link_types_do_not_include(self, r, link_types):
        """Response r does not include Link header with rel='type' for link_types (list)."""
        link_header = r.headers.get('link')
        type_links = self.find_links(link_header, 'type')
        for link_type in link_types:
            self.assertNotIn(link_type, type_links)

    def allows(self, r):
        """List of HTTP methods from Allow header."""
        allow = r.headers.get('allow')
        self.assertNotEqual(allow, None, "Includes Allow: header")
        return self.parse_comma_list(allow)

    def assert_allow_includes(self, r, methods):
        """Response r has Allow: header which includes methods (list)."""
        allows = self.allows(r)
        for method in (methods):
            self.assertIn(method, allows, "Allow header includes %s" % (method))

    def assert_4xx(self, status_code):
        """Assert status code is a 4xx code."""
        self.assertGreaterEqual(status_code, 400)
        self.assertLessEqual(status_code, 499)

    def assert_4xx_with_link_to_constraints(self, r, status_code=None):
        """Assert response has 4xx (or specified status) code with constrainedby link."""
        if (status_code is None):
            self.assert_4xx(r.status_code)
        else:
            self.assertEqual(r.status_code, status_code)
        self.assertTrue(self.links_include(r.headers.get('link'),
                                           'http://www.w3.org/ns/ldp#constrainedBy'))

    def request_and_parse_graph(self, uri, check_container=False):
        """Return RDF graph from uri."""
        r = self.get(uri)
        self.assertEqual(r.status_code, 200)
        link_header = r.headers.get('Link')
        if (check_container):
            self.assertTrue(self.links_include(link_header, 'type', 'ANY_CONTAINER'), "Is LDPC")
        g = Graph()
        g.parse(format='turtle', data=r.content)
        return g

    def assert_ldpc_contains(self, ldpc_uri, uri, msg=None):
        """Assert that LPC at ldpc_uri ldp:contains uri."""
        g = self.request_and_parse_graph(ldpc_uri)
        self.assertIn((URIRef(ldpc_uri),
                       URIRef("http://www.w3.org/ns/ldp#contains"),
                       URIRef(uri)),
                      g, msg)

    def assert_ldpc_does_not_contain(self, ldpc_uri, uri, msg=None):
        """Assert that LPC at ldpc_uri does not ldp:contains uri."""
        g = self.request_and_parse_graph(ldpc_uri)
        self.assertNotIn((URIRef(ldpc_uri),
                          URIRef("http://www.w3.org/ns/ldp#contains"),
                          URIRef(uri)),
                         g, msg)

    def parse_comma_list(self, header_str=None):
        """List of comma separated values in header_str."""
        if (header_str):
            return re.split(r'''\s*,\s*''', header_str)
        else:
            return []

    # Base HTTP methods from requests with auth added

    def head(self, uri, auth=None, **kwargs):
        """HEAD uri with auth."""
        if (auth is None):
            auth = (self.root_user, self.root_pass)
        return requests.head(uri, auth=auth, **kwargs)

    def get(self, uri, auth=None, **kwargs):
        """GET uri with auth."""
        if (auth is None):
            auth = (self.root_user, self.root_pass)
        return requests.get(uri, auth=auth, **kwargs)

    def options(self, uri, auth=None, **kwargs):
        """OPTIONS uri with auth."""
        if (auth is None):
            auth = (self.root_user, self.root_pass)
        return requests.options(uri, auth=auth, **kwargs)

    def post(self, uri, auth=None, **kwargs):
        """POST uri with auth."""
        if (auth is None):
            auth = (self.root_user, self.root_pass)
        return requests.post(uri, auth=auth, **kwargs)

    def put(self, uri, auth=None, **kwargs):
        """PUT uri with auth."""
        if (auth is None):
            auth = (self.root_user, self.root_pass)
        return requests.put(uri, auth=auth, **kwargs)

    def patch(self, uri, auth=None, **kwargs):
        """PATCH uri with auth."""
        if (auth is None):
            auth = (self.root_user, self.root_pass)
        return requests.patch(uri, auth=auth, **kwargs)

    def delete(self, uri, auth=None, **kwargs):
        """DELETE uri with auth."""
        if (auth is None):
            auth = (self.root_user, self.root_pass)
        return requests.delete(uri, auth=auth, **kwargs)

    # Frequently used methods with tests

    def post_ldpnr(self, uri=None, data='', content_type='text/plain'):
        """POST to create an LDPNR, return location."""
        if (uri is None):
            uri = self.rooturi
        r = self.post(uri,
                      headers={'Content-Type': content_type,
                               'Link': '<http://www.w3.org/ns/ldp#NonRDFSource>; rel="type"'},
                      data=data)
        self.assertEqual(r.status_code, 201)
        ldpnr_uri = r.headers.get('Location')
        self.assertTrue(ldpnr_uri)
        return(ldpnr_uri)

    def post_ldprv(self, uri=None, model='http://www.w3.org/ns/ldp#RDFSource',
                   data='', content_type='text/turtle'):
        """POST to create an LDPRv with model and data given.

        Returns:
            ldprv_uri - URI of LDPRv created
            ldpcv_uri - URI of LDPCv created for Mementos
        """
        if (uri is None):
            uri = self.rooturi
        r = self.post(uri,
                      headers={'Content-Type': content_type,
                               'Link': '<%s>; rel="type", '
                                       '<http://mementoweb.org/ns#OriginalResource>; rel="type"' % model},
                      data=data)
        self.assertEqual(r.status_code, 201)
        ldprv_uri = r.headers.get('Location')
        self.assertTrue(ldprv_uri)
        r = requests.head(ldprv_uri, auth=(self.root_user, self.root_pass))
        link_header = r.headers.get('link')
        ldpcv_uri = self.find_links(link_header, 'timemap')[0]
        return(ldprv_uri, ldpcv_uri)

    def get_parse_ldprs(self, uri, auth=None, **kwargs):
        """GET with get(...) method, then parse and return rdflib Graph."""
        if 'headers' not in kwargs:
            kwargs['headers'] = {}
        kwargs['headers']['Content-Type'] = 'text/turtle'
        r = self.get(uri, auth, **kwargs)
        g = Graph()
        g.parse(format='turtle', data=r.content)
        return g


class LDPTestSuite(TCaseWithSetup):
    """LDPTestSuite class to run the Java LDP testsuite."""

    no_auth = True

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
        p = run('java -jar %s --server %s --includedGroups MUST SHOULD --excludedGroups MANUAL --basic'
                % (self.ldp_test_suite_jar, self.rooturi), shell=True)
        self.assertEqual(p.returncode | 2, 2)  # allow skipped tests


class FedoraAPITestSuite(TCaseWithSetup):
    """FedoraAPITestSuite class to run the Java Fedora API testsuite.

    See: https://github.com/fcrepo4-labs/Fedora-API-Test-Suite
    """

    no_auth = True

    def test_fedora_api_testsuite(self):
        """Run the Fedora API testsuite.

        Relies on a custom set of test excludes in vendor/testng-passing.xml
        as trilpy is still some way from passing all tests.
        """
        cmd = ['java', '-jar', self.fedora_api_test_suite_jar]
        if not self.failing:
            print("Skipping known failing tests in Fedora API test suite (use --failing to run)")
            cmd += ['--testngxml', 'vendor/testng-passing.xml']
        cmd += ['--rooturl', self.rooturi,
                '--root-controller-user-webid', self.root_webid,
                '--root-controller-user-password', self.root_pass,
                '--permissionless-user-webid', self.other_webid,
                '--permissionless-user-password', self.other_pass,
                '--broker-url', 'tcp://overtherainbow:61616',
                '--queue-name', 'fedora']
        print("Starting Fedora-API-Test-Suite with: " + ' '.join(cmd))
        p = run(' '.join(cmd), shell=True)
        self.assertEqual(p.returncode, 0,  # FIXME - seems to always give 0
                         "Expected zero return code, got %s" % p.returncode)


class TestLDP(TCaseWithSetup):
    """TestLDP class to run LDP tests."""

    def test_ldp_4_2_4_5(self):
        """If-Match on ETag for PUT to replace."""
        url = urljoin(self.rooturi, '/' + str(uuid.uuid1()))
        # PUT object
        r = self.put(url,
                     headers={'Content-Type': 'text/turtle'},
                     data='<http://ex.org/a> <http://ex.org/b> "1".')
        self.assertEqual(r.status_code, 201)
        # Match
        r = self.get(url)
        self.assertEqual(r.status_code, 200)
        etag = r.headers.get('etag')
        self.assertTrue(etag)
        r = self.put(url,
                     headers={'If-Match': etag,
                              'Content-Type': 'text/turtle'},
                     data='<http://ex.org/a> <http://ex.org/b> "2".')
        self.assertEqual(r.status_code, 204)
        # Now mismatch
        r = self.get(url)
        self.assertEqual(r.status_code, 200)
        etag = r.headers.get('etag')
        self.assertTrue(etag)
        r = self.put(url,
                     headers={'If-Match': etag + 'XXX',
                              'Content-Type': 'text/turtle'},
                     data='<http://ex.org/a> <http://ex.org/b> "3".')
        self.assertEqual(r.status_code, 412)
        # Cleanup
        self.delete(url, auth=(self.root_user, self.root_pass))

    def test_ldp_5_3_2_7(self):
        """Test <> in POST body.

        https://www.w3.org/TR/ldp/#ldpc-post-rdfnullrel
        LDP servers creating a LDP-RS via POST must interpret the null relative URI for
        the subject of triples in the LDP-RS representation in the request entity body
        as identifying the entity in the request body. Commonly, that entity is the model
        for the "to be created" LDPR, so triples whose subject is the null relative URI
        result in triples in the created resource whose subject is the created resource.
        """
        r = self.post(self.rooturi,
                      headers={'Content-Type': 'text/turtle',
                               'Link': '<http://www.w3.org/ns/ldp#RDFSource>; rel="type"'},
                      data='<> <http://ex.org/b> "xyz".')
        self.assertEqual(r.status_code, 201)
        uri = r.headers.get('Location')
        self.assertTrue(uri)
        g = self.get_parse_ldprs(uri)
        self.assertIn((URIRef(uri), URIRef('http://ex.org/b'), Literal('xyz')), g)


class TestFedora(TCaseWithSetup):
    """TestFedora class to run Fedora specific tests."""

    def test_fedora_3_1_1(self):
        """Check Implementations MUST support creation and management of containers.

        https://fedora.info/spec/#ldpc
        """
        # Should be able to create different container types and get back
        # their type in link header
        for container_type in ['http://www.w3.org/ns/ldp#BasicContainer',
                               'http://www.w3.org/ns/ldp#DirectContainer',
                               'http://www.w3.org/ns/ldp#IndirectContainer']:
            r = self.post(self.rooturi,
                          headers={'Content-Type': 'text/turtle',
                                   'Link': '<' + container_type + '>; rel="type"'},
                          data='<http://ex.org/a> <http://ex.org/b> "xyz".')
            self.assertEqual(r.status_code, 201)
            uri = r.headers.get('Location')
            self.assertTrue(uri)
            r = self.head(uri)
            links = r.headers.get('Link')
            self.assertIn(container_type, links)
            self.assertNotIn('http://www.w3.org/ns/ldp#NonRDFSource', links)

    def test_fedora_3_1_2(self):
        """Resource creation SHOULD follow Link: rel='type' for LDP-NR.

        https://fedora.info/spec/#ldpnr-ixn-model
        """
        # POST Turtle object as LDR-NR
        r = self.post(self.rooturi,
                      headers={'Content-Type': 'text/turtle',
                               'Link': '<http://www.w3.org/ns/ldp#NonRDFSource>; rel="type"'},
                      data='<http://ex.org/a> <http://ex.org/b> "123".')
        self.assertEqual(r.status_code, 201)
        uri = r.headers.get('Location')
        self.assertRegex(uri, self.rooturi)
        # HEAD to get etag and test type
        r = self.head(uri)
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
        r = self.put(uri,
                     headers={'If-Match': etag,
                              'Content-Type': 'text/stuff'},
                     data='Hello there!')
        self.assertEqual(r.status_code, 204)

    def test_fedora_3_1_3(self):
        """Test link to constraints document on failure.

        https://fedora.info/spec/#constraints-document
        """
        if self.skip_should:
            return
        r = self.post(self.rooturi,
                      headers={'Content-Type': 'text/yoda-triples-unsupported',
                               'Link': '<http://www.w3.org/ns/ldp#RDFSource>; rel="type"'},
                      data='"xyz" <http://ex.org/b> <http://ex.org/a>.')
        self.assert_4xx_with_link_to_constraints(r)

    def test_fedora_3_2_1(self):
        """Test additional PreferInboundReferences value of Prefer: return=representation.

        https://fedora.info/spec/#additional-prefer-values
        """
        if self.skip_should:
            return
        pir = 'http://fedora.info/definitions/fcrepo#PreferInboundReferences'
        # Make new resource with reference to rooturi
        r = self.post(self.rooturi,
                      headers={'Content-Type': 'text/turtle',
                               'Link': '<http://www.w3.org/ns/ldp#RDFSource>; rel="type"'},
                      data='<http://ex.org/adf> <http://ex.org/bnm> <' + self.rooturi + '>.')
        self.assertEqual(r.status_code, 201)
        # Request rooturi with inbound references
        r = self.get(self.rooturi,
                     headers={'Prefer': 'return=representation; include="%s"' % pir})
        g = Graph()
        g.parse(format='turtle', data=r.content)
        self.assertIn((URIRef('http://ex.org/adf'), URIRef('http://ex.org/bnm'), URIRef(self.rooturi)), g)
        # Note that the requests package may combine header with commas:
        # http://docs.python-requests.org/en/master/user/quickstart/#response-headers
        pa_headers = (r.headers.get('Preference-Applied') or '').split(',')
        self.assertIn('return=representation', pa_headers)

    def test_fedora_3_5_a(self):
        """Check LDPC support for POST.

        https://fedora.info/spec/#http-post
        """
        for resource_type in ['http://www.w3.org/ns/ldp#RDFSource',
                              'http://www.w3.org/ns/ldp#NonRDFSource',
                              'http://www.w3.org/ns/ldp#BasicContainer']:
            r = self.post(self.rooturi,
                          headers={'Content-Type': 'text/turtle',
                                   'Link': '<' + resource_type + '>; rel="type"'},
                          data='<http://ex.org/aaa> <http://ex.org/bbb> "zeebee".')
            self.assertEqual(r.status_code, 201)
            uri = r.headers.get('Location')
            self.assertTrue(uri)
            r = self.head(uri)
            self.assertEqual(r.status_code, 200)

    # 3_5_b - untestable
    #
    # The default interaction model that will be assigned when there is no
    # explicit Link header in the request must be recorded in the constraints
    # document referenced in the Link: rel="http://www.w3.org/ns/ldp#constrainedBy"
    # header ([LDP] 4.2.1.6 clarification).

    def test_fedora_3_5_1_a(self):
        """Check creation of associated LDPRS on POST to create LDPNR.

        LDP: 5.2.3.12 ...may...
        If a LDP server creates this associated LDP-RS, it MUST indicate its location
        in the response by adding a HTTP Link header with a context URI identifying
        the newly created LDP-NR (instead of the effective request URI), a link relation
        value of describedby, and a target URI identifying the associated LDP-RS resource
        [RFC5988].
        """
        r = self.post(self.rooturi,
                      headers={'Content-Type': "text/plain",
                               'Link': '<http://www.w3.org/ns/ldp#NonRDFSource>; rel="type"'},
                      data="I am an LDPNR, must be describedby...")
        self.assertEqual(r.status_code, 201)
        ldpnr_uri = r.headers.get('Location')
        self.assertTrue(ldpnr_uri)
        link_header = r.headers.get('Link')
        db_links = self.find_links(link_header, 'describedby')
        self.assertGreaterEqual(len(db_links), 1)
        # Same links from HEAD
        r = self.head(ldpnr_uri)
        link_header2 = r.headers.get('Link')
        db_links2 = self.find_links(link_header, 'describedby')
        self.assertEqual(db_links, db_links2)

    def test_fedora_3_5_1_b(self):
        """Check handling of Digest header on POST.

        https://fedora.info/spec/#http-post-ldpnr
        """
        if (not self.digest):
            return()
        # Unsupported digest type
        r = self.post(self.rooturi,
                      headers={'Content-Type': 'text/plain',
                               'Link': '<http://www.w3.org/ns/ldp#NonRDFSource>; rel="type"',
                               'Digest': 'XXX=SURELY-NOT-SUPPORTED-TYPE'},
                      data='stuff')
        self.assertEqual(r.status_code, 400)
        # Supported digest with invalid value
        r = self.post(self.rooturi,
                      headers={'Content-Type': 'text/plain',
                               'Link': '<http://www.w3.org/ns/ldp#NonRDFSource>; rel="type"',
                               'Digest': 'SHA=zzzDyvhfIqlvFe+A9MYgxAfm1q5='},
                      data='stuff')
        self.assertEqual(r.status_code, 409)
        # Supported digest with valid value
        r = self.post(self.rooturi,
                      headers={'Content-Type': 'text/plain',
                               'Link': '<http://www.w3.org/ns/ldp#NonRDFSource>; rel="type"',
                               'Digest': 'md5=XUFAKrxLKna5cZ2REBfFkg=='},
                      data='hello')
        self.assertEqual(r.status_code, 201)

    def test_fedora_3_6(self):
        """Check PUT and content model handling.

        Implementations may allow the interaction model of an existing resource to be changed by
        specification of a new LDP type in a rel="type" link in the HTTP Link header. If supported,
        requests should be rejected with a 409 (Conflict) response unless the new LDP type specified
        is a subtype of the resource's current type.

        https://fedora.info/spec/#http-put
        """
        # LDPNR cannot be replaced with LDPRS, or LDPC types
        uri = self.post_ldpnr(data=b'I am an LDPNR, can only be replaced with another LDPNR')
        r = self.head(uri)
        etag = r.headers.get('etag')
        for model in ('http://www.w3.org/ns/ldp#RDFSource',
                      'http://www.w3.org/ns/ldp#Container',
                      'http://www.w3.org/ns/ldp#BasicContainer',
                      'http://www.w3.org/ns/ldp#DirectContainer',
                      'http://www.w3.org/ns/ldp#IndirectContainer'):
            r = self.put(uri,
                         headers={'Content-Type': 'text/turtle',
                                  'If-Match': etag,
                                  'Link': '<http://www.w3.org/ns/ldp#RDFSource>; rel="type"'},
                         data='<http://ex.org/a> <http://ex.org/b> "xyz".')
            self.assert_4xx_with_link_to_constraints(r, 409)
        self.delete(uri)
        # LDPRS or LDPC types cannot be replaced with LDPNS
        for model in ('http://www.w3.org/ns/ldp#RDFSource',
                      'http://www.w3.org/ns/ldp#Container',
                      'http://www.w3.org/ns/ldp#BasicContainer',
                      'http://www.w3.org/ns/ldp#DirectContainer',
                      'http://www.w3.org/ns/ldp#IndirectContainer'):
            r = self.post(self.rooturi,
                          headers={'Content-Type': 'text/turtle',
                                   'Link': '<' + model + '>; rel="type"'},
                          data='<http://ex.org/a> <http://ex.org/b> "xyz-a".')
            self.assertEqual(r.status_code, 201)
            uri = r.headers.get('Location')
            self.assertTrue(uri)
            r = self.head(uri)
            etag = r.headers.get('etag')
            r = self.put(uri,
                         headers={'Content-Type': 'text/plain',
                                  'If-Match': etag,
                                  'Link': '<http://www.w3.org/ns/ldp#NonRDFSource>; rel="type"'},
                         data='Not RDF')
            self.assert_4xx_with_link_to_constraints(r, 409)
        self.delete(uri)
        # LDPC types cannot be replaced with other LDPC types or LDPRS
        for model in ('http://www.w3.org/ns/ldp#BasicContainer',
                      'http://www.w3.org/ns/ldp#DirectContainer',
                      'http://www.w3.org/ns/ldp#IndirectContainer'):
            r = self.post(self.rooturi,
                          headers={'Content-Type': 'text/turtle',
                                   'Link': '<' + model + '>; rel="type"'},
                          data='<http://ex.org/a> <http://ex.org/b> "xyz-' + model + '" .')
            self.assertEqual(r.status_code, 201)
            uri = r.headers.get('Location')
            self.assertTrue(uri)
            r = self.head(uri)
            etag = r.headers.get('etag')
            for model2 in ('http://www.w3.org/ns/ldp#RDFSource',
                           'http://www.w3.org/ns/ldp#Container',
                           'http://www.w3.org/ns/ldp#BasicContainer',
                           'http://www.w3.org/ns/ldp#DirectContainer',
                           'http://www.w3.org/ns/ldp#IndirectContainer'):
                if model != model2:
                    r = self.put(uri,
                                 headers={'Content-Type': 'text/turtle',
                                          'If-Match': etag,
                                          'Link': '<' + model2 + '>; rel="type"'},
                                 data='<http://ex.org/a> <http://ex.org/b> "xyz-c".')
                    self.assert_4xx_with_link_to_constraints(r, 409)
            self.delete(uri)

    def test_fedore_3_6_1_a(self):
        """Check PUT to LDPRS to update triples.

        https://fedora.info/spec/#http-put-ldprs
        """
        r = self.post(self.rooturi,
                      headers={'Content-Type': 'text/turtle',
                               'Link': '<http://www.w3.org/ns/ldp#RDFSource>; rel="type"'},
                      data='<http://ex.org/a> <http://ex.org/b> "xyz".')
        self.assertEqual(r.status_code, 201)
        uri = r.headers.get('Location')
        self.assertTrue(uri)
        r = self.head(uri)
        etag = r.headers.get('etag')
        r = self.put(uri,
                     headers={'Content-Type': 'text/turtle',
                              'If-Match': etag,
                              'Link': '<http://www.w3.org/ns/ldp#RDFSource>; rel="type"'},
                     data='<http://ex.org/a> <http://ex.org/b> "ZYX".')
        self.assertEqual(r.status_code, 204)
        g = self.get_parse_ldprs(uri)
        self.assertNotIn(Literal('xyz'), g.objects())
        self.assertIn(Literal('ZYX'), g.objects())

    def test_fedore_3_6_1_b(self):
        """Check PUT to replace LDPBC disallows for conflicting triples and explanation.

        https://fedora.info/spec/#http-put-ldprs
        """
        r = self.post(self.rooturi,
                      headers={'Content-Type': 'text/turtle',
                               'Link': '<http://www.w3.org/ns/ldp#BasicContainer>; rel="type"'},
                      data='<http://ex.org/a> <http://ex.org/b> "xyz".')
        self.assertEqual(r.status_code, 201)
        uri = r.headers.get('Location')
        self.assertTrue(uri)
        r = self.head(uri)
        etag = r.headers.get('etag')
        r = self.put(uri,
                     headers={'Content-Type': 'text/turtle',
                              'If-Match': etag,
                              'Link': '<http://www.w3.org/ns/ldp#BasicContainer>; rel="type"'},
                     data='<> <http://www.w3.org/ns/ldp#contains> <http://ex.org/conflicting-thing>.')
        self.assertEqual(r.status_code, 409)
        # Explanation should contain these strings in whatever serialization of the
        # RDF might be used (with any prefix strategy)
        self.assertIn(b'contains', r.content)
        self.assertIn(b'conflicting-thing', r.content)

    def test_fedora_3_6_2(self):
        """Check LDPNR MUST support PUT to replace content.

        https://fedora.info/spec/#http-put-ldpnr
        """
        uri = self.post_ldpnr(data=b'original data here')
        r = self.head(uri)
        etag = r.headers.get('etag')
        new_data = b'WOW! NEW DATA'
        r = self.put(uri,
                     headers={'Content-Type': 'text/plain',
                              'If-Match': etag,
                              'Link': '<http://www.w3.org/ns/ldp#NonRDFSource>; rel="type"'},
                     data=new_data)
        self.assertEqual(r.status_code, 204)
        r = self.get(uri)
        self.assertEqual(r.content, new_data)

    def test_fedora_3_7(self):
        """Check implementations MUST support PATCH.

        https://fedora.info/spec/#http-patch
        """
        r = self.post(self.rooturi,
                      headers={'Content-Type': 'text/turtle',
                               'Link': '<http://www.w3.org/ns/ldp#BasicContainer>; rel="type"'},
                      data='''
                           @prefix x: <http://example.org/> .
                           x:simeon x:has x:pizza .
                           ''')
        self.assertEqual(r.status_code, 201)
        uri = r.headers.get('Location')
        self.assertTrue(uri)
        # Any LDP-RS MUST support PATCH
        r = self.head(uri)
        self.assertIn('PATCH', self.allows(r))
        self.assertIn('application/sparql-update', self.parse_comma_list(r.headers.get('Accept-Patch')))
        patch_data = '''
                     PREFIX x: <http://example.org/>
                     DELETE { ?s x:has ?o . }
                     INSERT { ?s x:ate ?o . }
                     WHERE { ?s x:has ?o . }
                     '''
        # Reject unsupported PATCH content type
        r = self.patch(uri,
                       headers={'Content-Type': 'bad-type/for-patch'},
                       data=patch_data)
        self.assertEqual(r.status_code, 415)
        # Accept valid patch
        r = self.patch(uri,
                       headers={'Content-Type': 'application/sparql-update'},
                       data=patch_data)
        self.assertEqual(r.status_code, 200)
        # Check result
        g = self.get_parse_ldprs(uri)
        self.assertIn((URIRef('http://example.org/simeon'),
                       URIRef('http://example.org/ate'),
                       URIRef('http://example.org/pizza')),
                      g)
        # Attempt to change containment triples (currently none, add one)
        r = self.patch(uri,
                       headers={'Content-Type': 'application/sparql-update'},
                       data='''
                            PREFIX ldp: <http://www.w3.org/ns/ldp#>
                            INSERT DATA { <%s> ldp:contains ldp:stuff . }
                            ''' % (uri))
        self.assert_4xx_with_link_to_constraints(r, 409)

    def test_fedora_4_1_1_and_4(self):
        """Check request to create versioned resource.

        Should be able to create a versioned resource for all types supported.
        We use a little block of turtle as the data for all types, in the case
        of the LDPNR this will not be parsed.
        """
        for ldpr_type in ('http://www.w3.org/ns/ldp#RDFSource',
                          'http://www.w3.org/ns/ldp#BasicContainer',
                          'http://www.w3.org/ns/ldp#NonRDFSource'):
            r = self.post(self.rooturi,
                          headers={'Content-Type': 'text/turtle',
                                   'Link': '<%s>; rel="type", '
                                           '<http://mementoweb.org/ns#OriginalResource>; rel="type"'
                                           % ldpr_type},
                          data='<http://ex.org/i> <http://ex.org/am_a> "%s".' % ldpr_type)
            self.assertEqual(r.status_code, 201)
            uri = r.headers.get('Location')
            self.assertTrue(uri)
            for method in (self.head, self.get):
                r = method(uri)
                self.assertEqual(r.status_code, 200)
                link_header = r.headers.get('link')
                self.assertTrue(self.links_include(link_header,
                                                   'type', ldpr_type), "Type %s as requested" % ldpr_type)
                # it MUST be created as an LDPRv ... 4.1.1 GET on LDPRv
                self.assertTrue(self.links_include(link_header,
                                                   'original timegate', uri), "Is original and timegate")
                self.assertTrue(self.links_include(link_header,
                                                   'type', 'http://mementoweb.org/ns#TimeGate'), "Is TimeGate")
                self.assertTrue(self.links_include(link_header,
                                                   'type', 'http://mementoweb.org/ns#OriginalResource'), "Is OriginalResource")
                timemaps = self.find_links(link_header, 'timemap')
                self.assertGreaterEqual(len(timemaps), 1, "At least one timemap link")
                tm_uri = timemaps[0]
                self.assertEqual(r.headers.get('vary'), 'Accept-Datetime')
            # and a version container LDPCv MUST be created ... 4.3.1 GET on LDPCv
            for method in (self.head, self.get):
                r = method(tm_uri)
                self.assertEqual(r.status_code, 200)
                link_header = r.headers.get('link')
                self.assertTrue(self.links_include(link_header,
                                                   'type', 'http://www.w3.org/ns/ldp#RDFSource'), "Is LDP-RS")
                self.assertTrue(self.links_include(link_header,
                                                   'type', 'ANY_CONTAINER'), "Is LDPC")
                self.assertTrue(self.links_include(link_header,
                                                   'type', 'http://mementoweb.org/ns#TimeMap'), "Is TimeMap")
                self.assert_allow_includes(r, ('GET', 'HEAD', 'OPTIONS'))

    def test_fedora_4_1_1_multiple_link_headers(self):
        """Check support for single or combined Link headers.

        Multiple Link header values are required in order to support creation
        of LDPRv. Following https://tools.ietf.org/html/rfc7230#section-3.2.2
        multiple Link headers are to be treated the same as additional
        comma separated link-value entries as described in
        https://tools.ietf.org/html/rfc5988#section-5
        """
        # In spite of old comments suggesting a way to send a list of tuples,
        # or some other class supporting items() that then provides tuples, I
        # do not think there is currently any way to coerce the requests module
        # into sending multiple headers of the same name. It also seems hard
        # (or perhaps impossible) to do with current urllib.request so here
        # I use the low-level interface to http.client where the putheader()
        # allows multiple headers to be sent.
        link1 = '<http://www.w3.org/ns/ldp#NonRDFSource>; rel="type"'
        link2 = '<http://mementoweb.org/ns#OriginalResource>; rel="type"'
        for headers in [[('Content-Type', 'text/plain'), ('Link', link1 + ',' + link2)],
                        [('Content-Type', 'text/plain'), ('Link', link1), ('Link', link2)],
                        [('Content-Type', 'text/plain'), ('Link', link2), ('Link', link1)]]:
            u = urlparse(self.rooturi)
            conn = http.client.HTTPConnection(u.netloc)
            conn.connect()
            conn.putrequest("POST", u.path)
            for (name, value) in headers:
                conn.putheader(name, value)
            # Add auth header
            if self.root_user and self.root_pass:
                up = b64encode(b':'.join((self.root_user.encode(), self.root_pass.encode())))
                conn.putheader('Authorization', 'Basic ' + up.decode())
            conn.endheaders()
            conn.send(b'some-data')
            response = conn.getresponse()
            ldprv_uri = response.info()['Location']
            conn.close()
            self.assertTrue(ldprv_uri)
            r = self.head(ldprv_uri)
            self.assert_link_types_include(r, ['http://mementoweb.org/ns#OriginalResource',
                                               'http://www.w3.org/ns/ldp#NonRDFSource'])

    def test_fedora_4_1_2(self):
        """LDPRv: An implementation must support PUT, as is the case for any LDPR.

        https://fedora.info/spec/#ldprv-put
        """
        for ldpr_type in ('http://www.w3.org/ns/ldp#RDFSource',
                          'http://www.w3.org/ns/ldp#BasicContainer',
                          'http://www.w3.org/ns/ldp#NonRDFSource'):
            r = self.post(self.rooturi,
                          headers={'Content-Type': 'text/turtle',
                                   'Link': '<%s>; rel="type", '
                                           '<http://mementoweb.org/ns#OriginalResource>; rel="type"'
                                           % ldpr_type},
                          data='<http://ex.org/4_1_2_i> <http://ex.org/am_a> "%s".' % ldpr_type)
            self.assertEqual(r.status_code, 201)
            uri = r.headers.get('Location')
            self.assertTrue(uri)
            r = self.head(uri)
            etag = r.headers.get('etag')
            self.assertTrue(etag)
            r = self.put(uri,
                         headers={'If-Match': etag,
                                  'Content-Type': 'text/turtle',
                                  'Link': '<%s>; rel="type"' % ldpr_type},
                         data='<http://ex.org/4_1_2_i> <http://ex.org/am_still_a> "%s".' % ldpr_type)
            self.assertEqual(r.status_code, 204)
            r = self.get(uri)
            self.assertIn(b'am_still_a', r.content)  # sloppy check on updated content

    def test_fedora_4_2_immutability(self):
        """An LDPRm may be deleted; however, it must not be modified once created.

        FIXME - test based on assumption that one can explicity create LDPRm via POST
        to the LDPCv.
        """
        for ldpr_type in ('http://www.w3.org/ns/ldp#RDFSource',
                          'http://www.w3.org/ns/ldp#BasicContainer',
                          'http://www.w3.org/ns/ldp#NonRDFSource'):
            r = self.post(self.rooturi,
                          headers={'Content-Type': 'text/turtle',
                                   'Link': '<%s>; rel="type", '
                                           '<http://mementoweb.org/ns#OriginalResource>; rel="type"'
                                           % ldpr_type},
                          data='<http://ex.org/4_2_x_i> <http://ex.org/am_a> "%s".' % ldpr_type)
            self.assertEqual(r.status_code, 201)
            uri = r.headers.get('Location')
            self.assertTrue(uri)
            r = self.head(uri)
            link_header = r.headers.get('link')
            tm_uri = self.find_links(link_header, 'timemap')[0]
            # Create LDPRm by POST to LPRCv/timemap
            r = self.post(tm_uri,
                          headers={'Content-Type': 'text/turtle',
                                   'Link': '<%s>; rel="type"' % ldpr_type,
                                   'Memento-Datetime': 'Tue, 20 Jun 2000 10:11:12 GMT'},
                          data='<http://ex.org/4_2_x_i> <http://ex.org/am_a_memento> "%s".' % ldpr_type)
            self.assertEqual(r.status_code, 201)
            ldprm_uri = r.headers.get('Location')
            # 4.2.1 response to a GET request (and HEAD implied too) MUST include a
            # Link: <http://mementoweb.org/ns#Memento>; rel="type" header
            for method in (self.head, self.get):
                r = method(ldprm_uri)
                self.assertEqual(r.status_code, 200)
                self.assert_link_types_include(r, ['http://mementoweb.org/ns#Memento'])
            # 4.2.2 response to an OPTIONS request MUST include Allow: GET, HEAD, OPTIONS
            r = self.options(ldprm_uri)
            self.assertEqual(r.status_code, 200)
            self.assert_allow_includes(r, ('GET', 'HEAD', 'OPTIONS'))
            supports_ldprm_delete = 'DELETE' in self.allows(r)
            # 4.2.3 implementation MUST NOT support POST for LDPRms
            r = self.post(ldprm_uri,
                          headers={'Content-Type': 'text/turtle',
                                   'Link': '<http://www.w3.org/ns/ldp#RDFSource>; rel="type"'},
                          data='<http://ex.org/4_2_3_i> <http://ex.org/am> "something".')
            self.assert_4xx(r.status_code)
            # 4.2.4 implementation MUST NOT support PATCH for LDPRms
            r = self.patch(ldprm_uri,
                           headers={'Content-Type': 'text/turtle',
                                    'Link': '<%s>; rel="type"' % ldpr_type},
                           data='<http://ex.org/4_2_4_i> <http://ex.org/am> "something".')
            self.assert_4xx(r.status_code)
            # 4.2.5 implementation MUST NOT support PUT for LDPRms
            r = self.patch(ldprm_uri,
                           headers={'Content-Type': 'text/turtle',
                                    'Link': '<%s>; rel="type"' % ldpr_type},
                           data='<http://ex.org/4_2_5_i> <http://ex.org/am> "something".')
            self.assert_4xx(r.status_code)
            # 4.2.6 implementation MAY support DELETE for LDPRms. If DELETE is supported,
            # the server is responsible for all behaviors implied by the LDP-containment
            # of the LDPRm.
            if (supports_ldprm_delete):
                r = self.delete(ldprm_uri)
                self.assertEqual(r.status_code, 200)
                # Check no longer included in LDPCv/TimeMap
                g = self.get_parse_ldprs(tm_uri)
                self.assertNotIn(URIRef(ldprm_uri), g.objects())

    def test_fedora_4_3(self):
        """LDPCv general tests."""
        # 4.3 An implementation must not allow the creation of an LDPCv that is
        # LDP-contained by its associated LDPRv.
        pass  # FIXME - how can this be tested?

    def test_fedora_4_3_1(self):
        """LDPCv GET and HEAD.

        https://fedora.info/spec/#ldpcv-get
        """
        (ldprv_uri, ldpcv_uri) = self.post_ldprv(data='<http://ex.org/4_3_1> <http://ex.org/a> "OPTIONS Test".')
        # 4.3.1 GET on LDPCv
        for method in (self.head, self.get):
            # An LDPCv must respond to GET Accept: application/link-format as indicated
            # in [RFC7089] section 5 and specified in [RFC6690] section 7.3
            # --> test this and Turtle
            for content_type in ('text/turtle', 'application/link-format'):
                r = method(ldpcv_uri,
                           headers={'Accept': content_type})
                self.assertEqual(r.status_code, 200)
                link_header = r.headers.get('link')
                self.assertTrue(self.links_include(link_header,
                                                   'type', 'http://www.w3.org/ns/ldp#RDFSource'), "Is LDP-RS")
                self.assertTrue(self.links_include(link_header,
                                                   'type', 'ANY_CONTAINER'), "Is LDPC")
                self.assertTrue(self.links_include(link_header,
                                                   'type', 'http://mementoweb.org/ns#TimeMap'), "Is TimeMap")
                # An implementation must include the Allow header as outlined
                # in 4.3.2 HTTP OPTIONS.
                self.assert_allow_includes(r, ('GET', 'HEAD', 'OPTIONS'))
                if ('POST' in self.allows(r)):
                    # If an LDPCv supports POST, then it must include the Accept-Post header
                    accept_post = r.headers.get('Accept-Post')
                    self.assertNotEqual(accept_post, None, 'Accept-Post required if POST supported')
                    self.assertIn('text/turtle', self.parse_comma_list(accept_post))
                if ('PATCH' in self.allows(r)):
                    # If an LDPCv supports PATCH, then it must include the Accept-Patch header
                    accept_patch = r.headers.get('Accept-Patch')
                    self.assertNotEqual(accept_patch, None, 'Accept-Patch required if PATCH supported')
                    self.assertIn('application/sparql-update', self.parse_comma_list(accept_patch))
                if (method == self.get and content_type == 'application/link-format'):
                    # FIXME - need more tests for response format
                    self.assertRegex(r.content.decode('utf-8'),
                                     r'''^<''' + ldprv_uri + r'''>\s*;\s*rel="original''')
                    self.assertRegex(r.content.decode('utf-8'),
                                     r'''<''' + ldpcv_uri + r'''>\s*;\s*rel="self"''')

    def test_fedora_4_3_2(self):
        """LDPCv OPTIONS."""
        # 4.3.2 ... MUST Allow: GET, HEAD, OPTIONS
        (ldprv_uri, ldpcv_uri) = self.post_ldprv(data='<http://ex.org/4_3_2> <http://ex.org/a> "OPTIONS Test".')
        r = self.options(ldpcv_uri)
        self.assert_allow_includes(r, ('GET', 'HEAD', 'OPTIONS'))

    def test_fedora_4_3_3(self):
        """LDPCv POST, if supported."""
        ldprv_data = '<http://ex.org/4_3_3> <http://ex.org/a> "POST Test".'
        (ldprv_uri, ldpcv_uri) = self.post_ldprv(data=ldprv_data)
        r = self.options(ldpcv_uri)
        if ('POST' not in self.allows(r)):
            self.skipTest("Implementation doesn't support POST to LDPCv")
        # a POST that does not contain a Memento-Datetime header should be understood
        # to create a new LDPRm contained by the LDPCv, reflecting the state of the
        # LDPRv at the time of the POST. Any request body must be ignored
        r = self.post(ldpcv_uri,
                      headers={'Content-Type': 'text/turtle',
                               'Link': '<http://www.w3.org/ns/ldp#RDFSource>; rel="type"'},
                      data='<http://ex.org/4_3_3a> <http://ex.org/a> "IGNORE_ME".')
        # may be 4xx for not supported, else create with Location, ignore body
        if (r.status_code == 201):
            loc = r.headers.get('Location')
            r = self.get(loc)
            self.assertEqual(r.status_code, 200)
            content_str = r.content.decode('utf-8')
            self.assertIn('"POST Test"', content_str)  # LDPRv data
            self.assertNotIn('"IGNORE_ME"', content_str)  # POST data ignored
            self.assert_ldpc_contains(ldpcv_uri, loc, "POSTed Memento is in LDPCv")
        else:
            self.assert_4xx_with_link_to_constraints(r)
        # a POST with a Memento-Datetime header should be understood to create a new
        # LDPRm contained by the LDPCv, with the state given in the request body and
        # the datetime given in the Memento-Datetime request header
        r = self.post(ldpcv_uri,
                      headers={'Content-Type': 'text/turtle',
                               'Link': '<http://www.w3.org/ns/ldp#RDFSource>; rel="type"',
                               'Memento-Datetime': 'Fri, 7 Dec 2017 15:05:00 GMT'},
                      data='<http://ex.org/4_3_3b> <http://ex.org/a> "USE_ME".')
        # may be 4xx for not supported, else create with Location, ignore body
        if (r.status_code == 201):
            loc = r.headers.get('Location')
            r = self.get(loc)
            self.assertEqual(r.status_code, 200)
            content_str = r.content.decode('utf-8')
            self.assertNotIn('"POST Test"', content_str)  # LDPRv data overwritten
            self.assertIn('"USE_ME"', content_str)  # POST data used
            self.assert_ldpc_contains(ldpcv_uri, loc, "POSTed Memento is in LDPCv")
        else:
            self.assert_4xx_with_link_to_constraints(r)

    def test_fedora_4_3_6(self):
        """LDPCv DELETE, if supported."""
        ldprv_data = '<http://ex.org/4_3_3> <http://ex.org/a> "DELETE Test".'
        (ldprv_uri, ldpcv_uri) = self.post_ldprv(data=ldprv_data)
        r = self.options(ldpcv_uri)
        if ('DELETE' not in self.allows(r)):
            self.skipTest("Implementation doesn't support DELETE to LDPCv")
        r = self.head(ldprv_uri)
        self.assert_link_types_include(r, ['http://mementoweb.org/ns#OriginalResource',
                                           'http://mementoweb.org/ns#TimeGate'])
        r = self.delete(ldpcv_uri)
        self.assertIn(r.status_code, (200, 204))
        r = self.head(ldpcv_uri)
        self.assertIn(r.status_code, (404, 410))  # FIXME - tighter than LDP spec
        if (not self.skip_should):
            r = self.head(ldprv_uri)
            self.assert_link_types_do_not_include(r, ['http://mementoweb.org/ns#OriginalResource',
                                                      'http://mementoweb.org/ns#TimeGate'])

    def test_fedora_5_1(self):
        """Check ACLs are LDP RDF Sources.

        https://fedora.info/spec/#solid-ldp-acls
        """
        r = self.head(self.rooturi)
        self.assertEqual(r.status_code, 200)
        acls = self.find_links(r.headers.get('link'), 'acl')
        self.assertEqual(len(acls), 1)
        r = self.head(acls[0])
        self.assertEqual(r.status_code, 200)
        self.assert_link_types_include(r, ['http://www.w3.org/ns/ldp#RDFSource'])

    def test_fedora_5_3(self):
        """Check ACLs are discoverable via Link Headers."""
        # Check root has an ACL
        r = self.get(self.rooturi)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(self.links_include(r.headers.get('link'), 'acl'))
        # Since the individual acl URI MUST be expressed for each resource, whether
        # or not it exists, we can test that the acl headers for two newly created
        # resources are different.
        acl_uris = []
        for n in (1, 2):
            ldpnr_uri = self.post_ldpnr()
            r = self.head(ldpnr_uri)
            acls = self.find_links(r.headers.get('link'), 'acl')
            self.assertEqual(len(acls), 1, "Expect one ACL URI in Link header")
            acl_uris.append(acls[0])
            # Cleanup
            self.delete(ldpnr_uri)
        self.assertNotEqual(acl_uris[0], acl_uris[1])

    def test_fedora_5_4(self):
        """Test ACL linking on resource creation.

        A client HTTP POST or PUT request to create a new LDPR may include a Link: 
        rel="acl" header referencing an existing LDP-RS to use as the ACL for the new
        LDPR. The server must reject the request and respond with a 4xx or 5xx range
        status code, such as 409 (Conflict) if it isn't able to create the LDPR
        with the specified LDP-RS as the ACL. In that response, the restrictions
        causing the request to fail must be described in a resource indicated by
        a Link: rel="http://www.w3.org/ns/ldp#constrainedBy" response header,
        following the pattern of [LDP] 4.2.1.6.

        https://fedora.info/spec/#link-acl-on-create
        """
        # Create an ACL resource
        r = self.post(self.rooturi,
                      headers={'Content-Type': 'text/turtle',
                               'Link': '<http://www.w3.org/ns/ldp#RDFSource>; rel="type"'},
                      data="""
                           @prefix acl: <http://www.w3.org/ns/auth/acl#> .
                           @prefix foaf: <http://xmlns.com/foaf/0.1/> .
                           @prefix ldp: <http://www.w3.org/ns/ldp#> .

                           <#authorization_1> a acl:Authorization ;
                               acl:agentClass foaf:Agent ;
                               acl:accessToClass ldp:Resource ;
                               acl:default <https://example.org/root/> ;
                               acl:mode acl:Read .
                           """)
        self.assertEqual(r.status_code, 201)
        acl_uri = r.headers.get('Location')
        self.assertTrue(acl_uri)
        # Now create a resource with ACL resource as the ACL
        r = self.post(self.rooturi,
                      headers={'Content-Type': 'text/turtle',
                               'Link': '<http://www.w3.org/ns/ldp#RDFSource>; rel="type", '
                                     + '<' + acl_uri + '>; rel="acl"'},
                      data="<uri:a> <uri:b> <uri:c>.")
        if (r.status_code == 201):
            # Success, must have ACL recorded and presented in Link on GET/HEAD
            child_uri = r.headers.get('Location')
            self.assertTrue(child_uri)    
            r = self.head(child_uri)
            acls = self.find_links(r.headers.get('link'), 'acl')
            self.assertEqual(len(acls), 1)
            self.assertEqual(acls[0], acl_uri)                
        else:
            # Rejects, must have 4xx and constraints
            self.assert_4xx_with_link_to_constraints(r)

    def test_fedora_5_5(self):
        """Cross domain ACLs MAY be rejected, if so MUST be 4xx and constraints."""
        r = self.post(self.rooturi,
                      headers={'Content-Type': 'text/turtle',
                               'Link': '<http://www.w3.org/ns/ldp#NonRDFSource>; rel="type",'
                                       '<http://example.org/external-acl>; rel="acl"'},
                      data='')
        if r.status_code == 201:
            child_uri = r.headers.get('Location')
            r = self.head(child_uri)
            acls = self.find_links(r.headers.get('link'), 'acl')
            self.assertEqual(len(acls), 1)
            self.assertEqual(acls[0], 'http://example.org/external-acl')
            # Cleanup
            self.delete(child_uri)
        else:
            self.assert_4xx_with_link_to_constraints(r)

    def test_fedora_5_9(self):
        """Check ACL inheritance.

        https://fedora.info/spec/#inheritance
        """
        # ACL for root
        r = self.head(self.rooturi)
        self.assertEqual(r.status_code, 200)
        acls = self.find_links(r.headers.get('link'), 'acl')
        self.assertEqual(len(acls), 1)
        root_acl = acls[0]
        # POST LDR-NR under root, expect to get new ACL
        child_uri = self.post_ldpnr(uri=self.rooturi, data='stuff')
        self.assertTrue(child_uri)
        r = self.head(child_uri)
        self.assertEqual(r.status_code, 200)
        acls = self.find_links(r.headers.get('link'), 'acl')
        self.assertEqual(len(acls), 1)
        self.assertNotEqual(acls[0], root_acl)
        self.assertNotEqual(acls[0], child_uri)
        # Cleanup
        r = self.delete(child_uri)
        # Try two level POST
        r = self.post(self.rooturi,
                      headers={'Content-Type': 'text/turtle',
                               'Link': '<http://www.w3.org/ns/ldp#BasicContainer>; rel="type"'})
        self.assertEqual(r.status_code, 201)
        child_uri = r.headers.get('Location')
        self.assertTrue(child_uri)
        r = self.post(child_uri,
                      headers={'Content-Type': 'text/turtle',
                               'Link': '<http://www.w3.org/ns/ldp#BasicContainer>; rel="type"'})
        self.assertEqual(r.status_code, 201)
        grandchild_uri = r.headers.get('Location')
        self.assertTrue(grandchild_uri)
        r = self.head(grandchild_uri)
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
        r = self.delete(child_uri)
        r = self.delete(grandchild_uri)

    def test_fedora_7_1(self):
        """Test transmission fixity."""
        r = self.post(self.rooturi,
                      headers={'Content-Type': 'text/plain',
                               'Link': '<http://www.w3.org/ns/ldp#NonRDFSource>; rel="type"',
                               'Digest': 'sha=no-match'},
                      data='hello')
        self.assertEqual(r.status_code, 409)
        r = self.post(self.rooturi,
                      headers={'Content-Type': 'text/plain',
                               'Link': '<http://www.w3.org/ns/ldp#NonRDFSource>; rel="type"',
                               'Digest': 'unknown=no-match'},
                      data='hello')
        self.assertEqual(r.status_code, 400)
        r = self.post(self.rooturi,
                      headers={'Content-Type': 'text/plain',
                               'Link': '<http://www.w3.org/ns/ldp#NonRDFSource>; rel="type"',
                               'Digest': 'sha=qvTGHdzF6KLavt4PO0gs2a6pQ00='},
                      data='hello')
        self.assertEqual(r.status_code, 201)
        uri = r.headers.get('Location')
        r = self.put(uri,
                     headers={'Content-Type': 'text/plain',
                              'Link': '<http://www.w3.org/ns/ldp#NonRDFSource>; rel="type"',
                              'Digest': 'md5=afqrYmg1ApVVDefVh7wyPQ=='},
                     data='goodbye')

    def test_fedora_7_2(self):
        """Test persistence fixity.

        https://fedora.info/spec/#persistence-fixity
        """
        r = self.post(self.rooturi,
                      headers={'Content-Type': 'text/plain',
                               'Link': '<http://www.w3.org/ns/ldp#NonRDFSource>; rel="type"'},
                      data='hello')
        self.assertEqual(r.status_code, 201)
        uri = r.headers.get('Location')
        # Can we get digest back?
        r = self.head(uri, headers={'Want-Digest': 'sha'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers.get('Digest'), 'sha=qvTGHdzF6KLavt4PO0gs2a6pQ00=')
        r = self.get(uri, headers={'Want-Digest': 'sha'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers.get('Digest'), 'sha=qvTGHdzF6KLavt4PO0gs2a6pQ00=')
        r = self.head(uri, headers={'Want-Digest': 'sha;q=0.1, md5;q=1.0, special1;q=1.0, special2'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers.get('Digest'), 'md5=XUFAKrxLKna5cZ2REBfFkg==')
        # Error cases
        r = self.head(uri, headers={'Want-Digest': 'sha;q=2.0'})
        self.assertEqual(r.status_code, 400)
        r = self.head(uri, headers={'Want-Digest': 'sha;q=0.1, md5;q=0.6, special1;q=1.0, special2'})
        self.assertEqual(r.status_code, 409)


class TestTrilpy(TCaseWithSetup):
    """TestTrilpy class to run miscellaneous or trilpy specific tests."""

    def test01_unknown_paths(self):
        """Expect 404 for bad path."""
        url = urljoin(self.rooturi, 'does_not_exist')
        r = self.get(url)
        self.assertEqual(r.status_code, 404)
        r = self.head(url)
        self.assertEqual(r.status_code, 404)
        r = self.post(url)
        self.assertEqual(r.status_code, 404)
        r = self.delete(url)
        self.assertEqual(r.status_code, 404)

    def test02_root_container(self):
        """Root container."""
        r = self.get(urljoin(self.rooturi, '/'))
        self.assertEqual(r.status_code, 200)

    def test03_delete_resource_get_gone(self):
        """Delete the LDPC at /."""
        uri = self.post_ldpnr(data=b'text')
        r = self.head(uri)
        self.assertEqual(r.status_code, 200)
        r = self.delete(uri)
        self.assertEqual(r.status_code, 200)
        # ... gives 410 on uri noe
        r = self.head(uri)
        self.assertEqual(r.status_code, 410)
        r = self.get(uri)
        self.assertEqual(r.status_code, 410)
        r = self.post(uri, data='')
        self.assertEqual(r.status_code, 410)

    def test_trilpy_4_3_3(self):
        """LDPCv POST is supported by trilpy."""
        ldprv_data = '<http://ex.org/4_3_3> <http://ex.org/a> "POST Test".'
        (ldprv_uri, ldpcv_uri) = self.post_ldprv(data=ldprv_data)
        r = self.options(ldpcv_uri)
        # a POST that does not contain a Memento-Datetime header should be understood
        # to create a new LDPRm contained by the LDPCv, reflecting the state of the
        # LDPRv at the time of the POST. Any request body must be ignored
        r = self.post(ldpcv_uri,
                      headers={'Content-Type': 'text/turtle',
                               'Link': '<http://www.w3.org/ns/ldp#RDFSource>; rel="type"'},
                      data='<http://ex.org/4_3_3a> <http://ex.org/a> "IGNORE_ME".')
        self.assertEqual(r.status_code, 201)
        loc = r.headers.get('Location')
        r = self.get(loc)
        self.assertEqual(r.status_code, 200)
        content_str = r.content.decode('utf-8')
        self.assertIn('"POST Test"', content_str)  # LDPRv data
        self.assertNotIn('"IGNORE_ME"', content_str)  # POST data ignored
        self.assert_ldpc_contains(ldpcv_uri, loc, "POSTed Memento is in LDPCv")
        # a POST with a Memento-Datetime header should be understood to create a new
        # LDPRm contained by the LDPCv, with the state given in the request body and
        # the datetime given in the Memento-Datetime request header
        r = self.post(ldpcv_uri,
                      headers={'Content-Type': 'text/turtle',
                               'Link': '<http://www.w3.org/ns/ldp#RDFSource>; rel="type"',
                               'Memento-Datetime': 'Fri, 7 Dec 2017 15:05:00 GMT'},
                      data='<http://ex.org/4_3_3b> <http://ex.org/a> "USE_ME".')
        # may be 4xx for not supported, else create with Location, ignore body
        self.assertEqual(r.status_code, 201)
        loc = r.headers.get('Location')
        r = self.get(loc)
        self.assertEqual(r.status_code, 200)
        content_str = r.content.decode('utf-8')
        self.assertNotIn('"POST Test"', content_str)  # LDPRv data overwritten
        self.assertIn('"USE_ME"', content_str)  # POST data used
        self.assert_ldpc_contains(ldpcv_uri, loc, "POSTed Memento is in LDPCv")

    def test_trilpy_5_5(self):
        """Cross domain ACLs not allowed => MUST be rejected with 4xx and constraints."""
        r = self.post(self.rooturi,
                      headers={'Content-Type': 'text/turtle',
                               'Link': '<http://www.w3.org/ns/ldp#NonRDFSource>; rel="type",'
                                       '<http://example.org/external-acl>; rel="acl"'},
                      data='')
        self.assert_4xx_with_link_to_constraints(r)


# If run from command line, do tests
if __name__ == '__main__':
    parser = argparse.ArgumentParser(add_help=False,
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--rooturi', action='store', default=None,
                        help="Use Fedora/LDP instance at given rooturi rather than running trilpy")
    parser.add_argument('--fresh', action='store_true',
                        help="Start trilpy fresh for each test (slow)")
    parser.add_argument('--port', type=int, default=9999,
                        help="Start trilpy on port")
    parser.add_argument('--user', action='store', default='fedoraAdmin',
                        help="User name for authentication tests.")
    parser.add_argument('--password', action='store', default='secret',
                        help="Password to got with --user for authentication tests.")
    parser.add_argument('--digest', action='store', default='sha1',
                        help="Digest type to test.")
    parser.add_argument('--skip-should', action='store_true',
                        help="Skip tests marked as SHOULD in TestLDP and TestFedora")
    parser.add_argument('--failing', action='store_true',
                        help="Include known failing tests which would otherwise be skipped")
    parser.add_argument('--trilpy-path', default='./trilpy_server.py',
                        help="Path to trilpy server executable")
    parser.add_argument('--ldp-test-suite-jar',
                        default='./vendor/ldp-testsuite-0.2.0-SNAPSHOT-shaded.jar',
                        help="Specify jar file for LDPTestSuite")
    parser.add_argument('--fedora-api-test-suite-jar',
                        default='./vendor/testSuite-1.0-SNAPSHOT-shaded.jar',
                        help="Specify jar file for Fedora-API-Test-Suite")
    parser.add_argument('--VeryVerbose', '-V', action='store_true',
                        help="be verbose.")
    parser.add_argument('--help', '-h', action='store_true',
                        help="show this help message and exit")
    (opts, args) = parser.parse_known_args()
    TCaseWithSetup.port = opts.port
    TCaseWithSetup.user = opts.user
    TCaseWithSetup.password = opts.password
    TCaseWithSetup.digest = opts.digest
    TCaseWithSetup.skip_should = opts.skip_should
    TCaseWithSetup.failing = opts.failing
    TCaseWithSetup.trilpy_path = opts.trilpy_path
    TCaseWithSetup.ldp_test_suite_jar = opts.ldp_test_suite_jar
    TCaseWithSetup.fedora_api_test_suite_jar = opts.fedora_api_test_suite_jar
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
