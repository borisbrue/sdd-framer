#!/bin/sh
cat <<'XML'
<testsuite name="shell">
  <testcase classname="app" name="test_FR-01_startet"/>
  <testcase classname="app" name="test_FR-02_stoppt"><failure message="exit 1"/></testcase>
</testsuite>
XML
