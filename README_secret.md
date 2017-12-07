# trilpy - the secret readme, shhhh!

## Tests

To run unit tests:

```
> python setup.py test
```

To run integration tests:

```
> python trilpy_server_test.py
```

The integration tests by default start a `trilpy` instance on port 9999 (can be controlled with `--port` option). They include the [LDP Test Suite](https://w3c.github.io/ldp-testsuite/) which is included pre-compiled for Java 8 in the `vendor` directory.

## Implementation status

### [LDP](https://www.w3.org/TR/ldp/)

Mostly done, requires more work around containers. Currently passes the [LDP Test Suite](https://w3c.github.io/ldp-testsuite/) with options `--includedGroups MUST SHOULD --excludedGroups MANUAL --basic`. Can run from `trilpy_server_test.py` with the following:

```
> python trilpy_server_test.py LDPTestSuite
...
===============================================
LDP Test Suite
Total tests run: 78, Failures: 0, Skips: 21
===============================================
...
```

### 3. [Resource Management](https://fcrepo.github.io/fcrepo-specification/#resource-management)

Simple implementation of PATCH.

Does not add all server managed triples to the output representations of LDPRS.

Only BasicContainer implemented to any degree or included in testing.

### 4. [Resource Versioning](https://fcrepo.github.io/fcrepo-specification/#resource-versioning)

Have implemented client managed version creation.

May later implement server managed version creation as a configuration option (memento created for every update of a versioned resource). There seems to be no problem with this existing at the same time as client managed version creation, which is anyway necessary in order to import previously versioned data as might be needed in a migration.

### 5. [Resource Authorization](https://fcrepo.github.io/fcrepo-specification/#resource-authorization)

Some implementation but out of data with spec draft, needs reworking. 

### 6. [Notifications](https://fcrepo.github.io/fcrepo-specification/#notifications)

Not implemented at all.

Since all interactions with stored data happen through `trilpy.store`, hooks to generate notifications likely go in there.

### 7. [Binary Fixity](https://fcrepo.github.io/fcrepo-specification/#binary-fixity)

Done. Implements `Digest` for transmission fixity, `Want-Digest` for persistence fixity. Supports `md5`, `sha` (and alias `sha1` used by Fedora4, see [fcrepo#235](https://github.com/fcrepo/fcrepo-specification/issues/235).

Current implementation does this for all LDPR, not just LDPNR.
