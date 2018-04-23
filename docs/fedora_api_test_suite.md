# Running the Fedora API Test Suite

This page discusses running the [Fedora API Test Suite](https://github.com/fcrepo4-labs/Fedora-API-Test-Suite) against `trilpy` using stand-alone processes. See also notes about [running the Fedora API Test Suite from the integration tests](../README_secret.md#fedora-api-test-suite).

## Default URI for `trilpy`

Run `trilpy` with authentication turned off:

```
> trilpy_server.py -v --no-auth
INFO:root:Running trilpy on http://localhost:9999
...
```

and then in a separate window run the test suite:

```
> java -jar vendor/testSuite-1.0-SNAPSHOT-shaded.jar --baseurl http://localhost:9999
[TestNG] Running:
  Default testng.xml

===============================================
Fedora API Specification Test Suite
Total tests run: 63, Failures: 28, Skips: 0
===============================================

Writing HTML results:
	/...some...path.../report/testsuite-execution-report.html
```

Success and failure summary in `report/testsuite-execution-report.html` and log data in `report/testsuite-execution.log`.

### Running a subset of the tests

Use `--requirements MUST` or such (see `-h` for help):

```
> java -jar vendor/testSuite-1.0-SNAPSHOT-shaded.jar --baseurl http://localhost:9999 --requirements MUST
```

### Running a specific test

Running a specific test or a custom subset of tests requires the creation of a [TestNG XML file](http://testng.org/doc/documentation-main.html) and specification of that file with the `--testngxml` option. There are comments in the master [`testng.xml`](https://github.com/fcrepo4-labs/Fedora-API-Test-Suite/blob/master/src/main/resources/testng.xml) which show how to select a specific test -- the method name for the test must be placed within the scope of the appropriate class however. The easiest way to find out what the methd name is and what class it is part of is to follow the **(Code)** links on the [Test Compatibility Suite Verification page] (https://wiki.duraspace.org/display/FF/Test+Compatibility+Suite+Verification). For example, for the first test `Container-3.1.1-A` the [code link](https://github.com/fcrepo4-labs/Fedora-API-Test-Suite/blob/master/src/main/java/com/ibr/fedora/testsuite/Container.java) takes us to the `com.ibr.fedora.testsuite.Container` class and we find that the method name is `createLDPC`. Thus a copy of `testng.xml` with the following:

```
    <classes>
      <class name="com.ibr.fedora.testsuite.SetUpSuite"/>
      <class name="com.ibr.fedora.testsuite.Container">
        <methods>
          <include name="createLDPC"/>
        </methods>
      </class>
    </classes>
```

will run just test `Container-3.1.1-A`:

```
> java -jar vendor/testSuite-1.0-SNAPSHOT-shaded.jar --baseurl http://localhost:9999 --testngxml testng.xml
[TestNG] Running:
  testng.xml

===============================================
Fedora API Specification Test Suite
Total tests run: 1, Failures: 0, Skips: 0
===============================================
```

## Using a specific root container location

In order to use `http://localhost:8080/root` as the root container, run `trilpy.py` (again with no authentication) with:

```
> trilpy_server.py -v --no-auth --port 8080 --root-container=root
INFO:root:Running trilpy on http://localhost:8080
...
```

and the correspondig setup for the test suite is:

```
> java -jar target/testSuite-1.0-SNAPSHOT-shaded.jar --baseurl http://localhost:8080/root
...
```
