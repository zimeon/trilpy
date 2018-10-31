"""HTTP Basic Authentication.

Should abstract/generalize
This code based on https://gist.github.com/notsobad/5771635
and https://pypi.python.org/pypi/tornado-http-auth
"""

import base64
import hashlib


def get_user_password(auth_header):
    """Get user:password from request header value.

    @return user:password string else raise Exception
    """
    if auth_header is None:
        raise Exception('No Authorization header')
    auth_data = auth_header.split()
    if len(auth_data) < 2 or auth_data[0] != 'Basic':
        raise Exception('Authorization header not for HTTP Basic')
    return base64.b64decode(auth_data[1]).decode('ascii')

def get_user(auth_header, users):
    """Get user webid from request headers authz in users dict, None is no auth or bad credentials.

    users dict has form {'user:password': 'webid', ...}
    """
    try:
        user_password = get_user_password(auth_header)
        if user_password in users:
            return users[user_password]
    except:
        # Any exception means no auth
        pass
    return None
