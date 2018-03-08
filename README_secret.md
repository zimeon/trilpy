# trilpy - the secret readme, shhhh!

## Implementation status

### [LDP](https://www.w3.org/TR/ldp/) and the LDP Test Suite

Mostly done, requires more work around containers. Currently passes the [LDP Test Suite](https://w3c.github.io/ldp-testsuite/) with options `--includedGroups MUST SHOULD --excludedGroups MANUAL --basic`. Can run from `trilpy_tests.py` with the following:

```
> python trilpy_tests.py LDPTestSuite
...
===============================================
LDP Test Suite
Total tests run: 78, Failures: 0, Skips: 21
===============================================
...
```

This relies up a Java 8 compiled copy of the LDP Test Suite in the [`vendor`](vendor) directory, and the location may be overridden with with `--ldp-test-suite-jar` option.

### Fedora API Section 3. [Resource Management](https://fcrepo.github.io/fcrepo-specification/#resource-management)

3.1.1 - Only BasicContainer implemented to any degree or included in testing.

3.2 - LDP - Does not add all server managed triples to the output representations of LDPRS.

3.2.1 - Supports `Prefer: http://fedora.info/definitions/fcrepo#PreferInboundReferences` albeit very inefficiently. Does not support `Prefer: http://www.w3.org/ns/oa#PreferContainedDescriptions`.

3.7 - Simple implementation of PATCH.

### Fedora API Section 4. [Resource Versioning](https://fcrepo.github.io/fcrepo-specification/#resource-versioning)

Have implemented client managed version creation.

May later implement server managed version creation as a configuration option (memento created for every update of a versioned resource). There seems to be no problem with this existing at the same time as client managed version creation, which is anyway necessary in order to import previously versioned data as might be needed in a migration.

### Fedora API Section 5. [Resource Authorization](https://fcrepo.github.io/fcrepo-specification/#resource-authorization)

Some implementation but out of data with spec draft, needs reworking. 

### Fedora API Section 6. [Notifications](https://fcrepo.github.io/fcrepo-specification/#notifications)

Not implemented at all.

Since all interactions with stored data happen through `trilpy.store`, hooks to generate notifications could likely be added in there.

### Fedora API Section 7. [Binary Fixity](https://fcrepo.github.io/fcrepo-specification/#binary-fixity)

Done. Implements `Digest` for transmission fixity, `Want-Digest` for persistence fixity. Supports `md5`, `sha` (and alias `sha1` used by Fedora4, see [fcrepo#235](https://github.com/fcrepo/fcrepo-specification/issues/235).

Current implementation does this for all LDPR, not just LDPNR.

## To run

`trilpy` is wriiten to run with Python 3 (currently tested with 3.5 and 3.6), you can check your python with:

```
> python --version
Python 3.5.3
```

After downloading from github, from the `trilpy` root directory install dependencies and code with:

```
> python setup.py install
```

and then run with:

```
> trilpy_server.py
INFO:root:Running trilpy on http://localhost:9999
``` 

where the output will be a log of accesses. From another window one can test by requesting the root container:

```
> curl http://localhost:9999
@prefix ldp: <http://www.w3.org/ns/ldp#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xml: <http://www.w3.org/XML/1998/namespace> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<http://localhost:9999> a ldp:BasicContainer,
        ldp:RDFSource,
        ldp:Resource .
```

See `trilpy_server.py -h` for help with possible options such as port, path to root container, and `-v` for more verbose logging.

**As currently implemented, `trilpy_server.py` simply stores resources in memory for the time it is running. Everything is lost on exit and attempts to store large resources might exhaust memory. It is merely a test implementation.**

## Tests

To run unit tests:

```
> python setup.py test
```

To run integration tests:

```
> ./trilpy_tests.py
```

The integration tests by default start a `trilpy` instance on port 9999 (can be controlled with `--port` option). By default, tests include the [LDP Test Suite](https://w3c.github.io/ldp-testsuite/) (see below), a local LDP test, and as set of local Fedora API tests.

To run just the local Fedora API tests use:

```
> ./trilpy_tests.py TestFedora
```

or to run a specific test use the `Class.mathod` form (see methods in `trilpy_tests.py`), e.g.:

```
> ./trilpy_tests.py TestFedora.test_fedora_3_7
```

### LDP Test Suite

The integration tests normally run the  [LDP Test Suite](https://w3c.github.io/ldp-testsuite/). A version compiled for Java 8 is included in the [`vendor`](vendor) directory. This suite can be run on its own with:

```
> ./trilpy_tests.py LDPTestSuite
```

### Fedora API Test Suite

The integration tests include support for running the [Fedora API Test Suite](https://github.com/fcrepo4-labs/Fedora-API-Test-Suite). A version compiled for Java 8 is included in the [`vendor`](vendor) directory. The normal set of integration tests skips this test suite because `trilpy` is quite some way from passing! This test suite can be run on its own with the following (the `--failing` flag avoids skipping it):

```
> ./trilpy_tests.py --failing FedoraAPITestSuite
```

An alternate jar file may be specified with:

```
> ./trilpy_tests.py --failing --fedora-api-test-suite-jar some-path/testSuite-1.0-SNAPSHOT-shaded.jar FedoraAPITestSuite
```

See also notes about [running the Fedora API Test Suite stand-alone](docs/fedora_api_test_suite.md).

## Related work

  * https://w3c.github.io/ldp-testsuite/ - LDP Test Suite
  * https://github.com/fcrepo4-labs/Fedora-API-Test-Suite - Fedora API Test Suite that exercises the requirements in the Fedora API Specification indicating the degree of a server’s compliance with the specification.
  * https://github.com/rotated8/fedora-spec-testing - Test suite for Fedora5 implementation. Assumes a number of implementation specific behaviors (like assumption of `Content-Type` for POST so it is not specified in request, removal of assumed `fcr:tombstone` resources).