#!/usr/bin/env python
"""Test trilpy by running on localhost."""
import unittest
from urllib.parse import urljoin
from subprocess import Popen
import requests
import time

port = 9999
baseurl = 'http://localhost:' + str(port) + '/'


class TestAll(unittest.TestCase):
    """TestAll class to run tests."""

    def setUp(self):
        """Start trilpy."""
        self.proc = Popen(['/usr/bin/env', 'python', './trilpy.py', '-p', str(port)])
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


# If run from command line, do tests
if __name__ == '__main__':
    unittest.main(verbosity=2)
