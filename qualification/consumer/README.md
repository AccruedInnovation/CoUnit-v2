# Unchanged consumer compatibility

`consumer.xml` packages the original FB_MovingAverage and FB_MovingAverage_Test from the process-library repository without product/test-source edits. The runner invokes only CoUnit.RUN(), provides the existing PRG_TEST.TestLog method, and waits for publication. Library reference `qualified_only` must be FALSE because existing tests use unqualified TEST/TEST_FINISHED.

The installed 2.0.0.0 library compiled with zero errors and one existing UINT-to-INT warning in FB_MovingAverage. All eight cases passed, 30 assertions, NORMAL disposition, no skips. Native evidence: consumer-native6.json and reports/consumer-6.xml in ../native-evidence.zip.
