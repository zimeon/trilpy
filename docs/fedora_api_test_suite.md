# Running the Fedora API Test Suite

This page discusses running the [Fedora API Test Suite](https://github.com/fcrepo4-labs/Fedora-API-Test-Suite) against `trilpy` using stand-alone processes. See also notes about [running the Fedora API Test Suite from the integration tests](../README_secret.md#fedora-api-test-suite).

## Default URI for `trlipy`

Run `trilpy` with:

```
> trilpy_server.py -v
INFO:root:Running trilpy on http://localhost:9999
...
```

and then in a separate window run the test suite:

```
> java -jar target/testSuite-1.0-SNAPSHOT-shaded.jar --host http://localhost:9999
[TestNG] Running:
  Command line suite


===============================================
ldptest
Total tests run: 51, Failures: 47, Skips: 0
===============================================

Writing HTML results:
    /...some-path.../Fedora-API-Test-Suite/report/testsuite-execution-report.html
```

Success and failure summary in `report/testsuite-execution-report.html` and log data in `report/testsuite-execution.log`.

## Using a specific root container location

In order to use `http://localhost:8080/root` as the root container, run `trilpy.py` with:

```
> trilpy_server.py -v --port 8080 --root-container=root
```

and the correspondig setup for the test suite is:

```
> java -jar target/testSuite-1.0-SNAPSHOT-shaded.jar --host http://localhost:8080/root
```
