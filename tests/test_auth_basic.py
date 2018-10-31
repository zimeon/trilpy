"""HTTP Basic Auth test."""
import unittest
from trilpy.auth_basic import get_user_password, get_user


class TestAll(unittest.TestCase):
    """TestAll class to run tests."""

    def test01_get_user_and_password(self):
        """Test Authorization header parsing."""
        # No or bad auth
        self.assertRaises(Exception, get_user_password)
        self.assertRaises(Exception, get_user_password, '')
        self.assertRaises(Exception, get_user_password, 'Basic')
        self.assertRaises(Exception, get_user_password, 'Basic ')
        self.assertRaises(Exception, get_user_password, 'Basic XXX')
        self.assertRaises(Exception, get_user_password, 'Digest QWxhZGRpbjpvcGVuIHNlc2FtZQ==')
        # Example from https://tools.ietf.org/html/rfc2617#section-2
        self.assertEqual(get_user_password('Basic QWxhZGRpbjpvcGVuIHNlc2FtZQ=='),
                         'Aladdin:open sesame')
        # Simple example
        self.assertEqual(get_user_password('Basic dGVzdHVzZXI6dGVzdHBhc3M='),
                         'testuser:testpass')

    def test02_get_user(self):
        """Test get_user method."""
        users = {'a-user:a-password': 'http://example.org/a-user#1',
                 'fedoraAdmin:secret': 'http://example.org/admin'}
        self.assertEqual(get_user('Basic dGVzdHVzZXI6dGVzdHBhc3M=', users), None)
        self.assertEqual(get_user('Basic ZmVkb3JhQWRtaW46c2VjcmV0', users), 'http://example.org/admin')
        self.assertEqual(get_user('Basic YS11c2VyOmEtcGFzc3dvcmQ=', users), 'http://example.org/a-user#1')
