echo "Assuming server is running on port 9999"
java -jar vendor/ldp-testsuite-0.2.0-SNAPSHOT-shaded.jar --server http://localhost:9999 --includedGroups MUST SHOULD --excludedGroups MANUAL --basic $@
