"""HTTP Basic Authentication.

Should abstract/generalize
This code based on https://gist.github.com/notsobad/5771635
and https://pypi.python.org/pypi/tornado-http-auth
"""

import base64
import hashlib


def get_user_and_password(auth_header):
    """Get user and password from request header value.

    @return [user, password] else raise Exception
    """
    if auth_header is None:
        raise Exception('No Authorization header')
    auth_data = auth_header.split()
    if len(auth_data) < 2 or auth_data[0] != 'Basic':
        raise Exception('Authorization header not for HTTP Basic')
    return base64.b64decode(auth_data[1]).decode('ascii').split(':', 1)


def get_user(auth_header, users):
    """Get user from request headers authz in users dict, None is no auth or bad credentials."""
    try:
        user, password = get_user_and_password(auth_header)
        if (user in users and users[user] == password):
            return user
    except:
        # Any exception means no auth
        pass
    return None
