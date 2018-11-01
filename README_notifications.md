# Notifications

Have experimented with [Apache ActiveMQ](http://activemq.apache.org/version-5-run-broker.html) using Stomp to send messages from Python and then the tcp transport which is used by the Fedora-API-TestSuite.

  * http://activemq.apache.org/tcp-transport-reference.html

2018-10-31 - homebrew install didn't work on MacOSX, perhaps something transient to do with release of 5.15.7 when only 5.15.6 available from mirrors.

## Writing from Python

Have done very simple test using `stomp.py` library, test code:

```
from stomp import *
from stomp.exception import ConnectFailedException

try:
    c = Connection12([('127.0.0.1', 61613)])
    c.start()
    c.connect('admin', 'admin', wait=True)
    c.send('/queue/fedora', '''{
      "@context": "https://www.w3.org/ns/activitystreams",
      "id": "urn:uuid:3c834a8f-5638-4412-aa4b-35ea80416a18",
      "type": "Create",
      "name": "Resource Creation",
      "actor": "http://example.org/agent/fedoraAdmin",
      "object": {
        "id": "http://example.org/fcrepo/rest/resource/path",
        "type": [ "ldp:Container", "ldp:RDFSource" ]
      }
    }''')
    c.disconnect()
except ConnectFailedException as e:
    print(str(e))
```

seems to work fine sending to ActiveMQ.

