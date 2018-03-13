"""HTTP Basic Auth test."""
import unittest
from trilpy.auth_basic import get_user_and_password, get_user


class TestAll(unittest.TestCase):
    """TestAll class to run tests."""

    def test01_get_user_and_password(self):
        """Test Authorization header parsing."""
        # No or bad auth
        self.assertRaises(Exception, get_user_and_password)
        self.assertRaises(Exception, get_user_and_password, '')
        self.assertRaises(Exception, get_user_and_password, 'Basic')
        self.assertRaises(Exception, get_user_and_password, 'Basic ')
        self.assertRaises(Exception, get_user_and_password, 'Basic XXX')
        self.assertRaises(Exception, get_user_and_password, 'Digest QWxhZGRpbjpvcGVuIHNlc2FtZQ==')
        # Example from https://tools.ietf.org/html/rfc2617#section-2
        self.assertEqual(get_user_and_password('Basic QWxhZGRpbjpvcGVuIHNlc2FtZQ=='),
                         ['Aladdin', 'open sesame'])
        # Simple example
        self.assertEqual(get_user_and_password('Basic dGVzdHVzZXI6dGVzdHBhc3M='),
                         ['testuser', 'testpass'])
