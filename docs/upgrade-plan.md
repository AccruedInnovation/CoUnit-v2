# Qualification and limitations

CoUnit 2.1.0.7 has a clean native build, read-back and bounded installed-consumer
runtime checks. See [scan tracing](scan-tracing.md) for those checks and the
untested sink-error and incomplete timeout-trace limitations.

For CoUnit 2.1.0.6, native source export/readback and
side-by-side installed-byte verification passed. Bounded legacy ALL and sequence
runs on CODESYS 3.5.22.20 and Linux Virtual Control SL 4.22 x64 passed with XML
and requested JSON, report identity checks and cleanup. The sequence observation
used the inherited TIME/TON millisecond clock domain. These observations do not
qualify every application, capacity, target or timing constraint.

Additional narrowly scoped installed-.6 observations covered catalog readiness,
selected case and suite execution, catalog listing, cancellation, first-failure
preservation through one scaled forced-abort fixture, and one two-run retained
session with an explicit warm application reset and separate reports. The reset
result does not qualify arbitrary warm reset, repeatability or uncertain-reset
recovery. One public controlled-exchange probe rejected a backward request after
configuration without body effects. This does not prove generic replay safety or
exactly-once execution. Detailed coherent live results and broader lifecycle
behavior remain unqualified.

Native UTF-8 compiler configuration, physical-controller deployment and online
change are not qualified. The full 2.0.0.0 Windows-1252 simulator matrix is
historical and does not automatically qualify 2.1. Earlier .5 setup-error and
resource-profile evidence remains specific to that version. Failed attempts are
not turned into passing evidence by a later successful run.

[Framework qualification](../qualification/README.md) documents the available
shards, independent oracles, runtime matrix and historical evidence archive.
Consumer checks must independently identify their application, provider, task,
selected inventory, fresh reports and cleanup. A source-only example, a completed
run or successful publication alone does not establish test success.
