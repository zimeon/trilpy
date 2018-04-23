# Running the Fedora API Test Suite

This page discusses running the [Fedora API Test Suite](https://github.com/fcrepo4-labs/Fedora-API-Test-Suite) against `trilpy` using stand-alone processes. See also notes about [running the Fedora API Test Suite from the integration tests](../README_secret.md#fedora-api-test-suite).

## Default URI for `trilpy`

Run `trilpy` with:

```
> trilpy_server.py -v
INFO:root:Running trilpy on http://localhost:9999
...
```

and then in a separate window run the test suite:

```
> java -jar target/testSuite-1.0-SNAPSHOT-shaded.jar --baseurl http://localhost:9999
[TestNG] Running:
  Command line suite


===============================================
ldptest
Total tests run: 63, Failures: 59, Skips: 0
===============================================

Writing HTML results:
    /...some-path.../Fedora-API-Test-Suite/report/testsuite-execution-report.html
```

Success and failure summary in `report/testsuite-execution-report.html` and log data in `report/testsuite-execution.log`.

### Running a subset of the tests

Use `--requirements MUST` or such (see `-h` for help):

```
> java -jar vendor/testSuite-1.0-SNAPSHOT-shaded.jar --baseurl http://localhost:9999 --requirements MUST
```

### Running a specific test

Running a specific test or a custom subset of tests requires the creation of a [TestNG XML file](http://testng.org/doc/documentation-main.html) and specification of that file with the `--testngxml` option. There are comments in the master [`testng.xml`](https://github.com/fcrepo4-labs/Fedora-API-Test-Suite/blob/master/src/main/resources/testng.xml) which show how to select a specific test -- the method name for the test must be placed within the scope of the appropriate class however.

## Using a specific root container location

In order to use `http://localhost:8080/root` as the root container, run `trilpy.py` with:

```
> trilpy_server.py -v --port 8080 --root-container=root
INFO:root:Running trilpy on http://localhost:8080
...
```

and the correspondig setup for the test suite is:

```
> java -jar target/testSuite-1.0-SNAPSHOT-shaded.jar --baseurl http://localhost:8080/root
...
```
