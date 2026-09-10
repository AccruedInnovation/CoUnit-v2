# Report acceptance in CoUnit 2.0.0

Every 2.0.0 report includes `counit-run-disposition` on `<testsuites>`, with exactly `NORMAL`, `ABORTED`, or `FRAMEWORK_ERROR`. This describes the run's integrity separately from individual testcase results. A late framework error can therefore leave all already-finished tests passed while the run disposition is `FRAMEWORK_ERROR`. Root and suite counts continue to equal the actual terminal testcase categories; no synthetic testcase or extra error count is introduced.

A successful file publication (`WRITTEN`) means that a complete report committed to the configured path. It does not mean the test run passed. CI success requires a `NORMAL` run disposition in addition to the consumer's existing testcase/count/freshness checks. The qualification parser preserves a non-normal disposition as observed data so deliberately failed-run fixtures can be checked; its separate success gate must reject such a run.

The originating process-library repository's `CIScripts/ci_receipt.py` and `parse_xunit.py` reject any present disposition other than `NORMAL`, including empty or unknown values. They preserve compatibility with older reports that lack the attribute. A report known to be produced by 2.0.0 must also pass the version-specific attribute-presence check in the 2.0.0 qualification tooling; accepting an unmarked legacy report does not qualify a 2.0.0 report.

Generic xUnit/JUnit consumers may ignore this CoUnit attribute. Use the run-success gate before publishing results to such consumers; an all-green testcase display alone is not evidence of a successful CoUnit run. No claim is made that the new attribute is accepted by an external XSD until that schema has been explicitly qualified. The existing legacy `CodesysRunUnitTests.py` parser also requires its own R3 migration before it can consume 2.0.0 reports; this change does not migrate that runner.

Only the configured final path is current. `.counit.tmp` and `.counit.bak` companions belong to CoUnit and must not be used as independent files or ingested as current reports. Failed precommit publication retains/restores the previous complete report or leaves no current report, so consumers must retain their existing run-freshness checks.

This standalone distribution uses `qualification/verify_xunit.py --require-success` as its v2-specific gate. The originating repository adapters remain there and are not dependencies of this distribution.
