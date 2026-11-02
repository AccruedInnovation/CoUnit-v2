# Report acceptance

CoUnit 2.1.0.6 publishes xUnit XML and, when enabled, an independent diagnostic
JSON report. Configure fresh writable paths before the first runner call. Keep the
runner executing until the requested publishers finish; a committed report and a
passing test run are separate facts.

## Accepting a run

Require the exact independently selected suite/case inventory, fresh complete
reports, a `NORMAL` run disposition, no unexpected failures, errors or skips,
and the expected assertion counts. A completed assertion-based case with zero
assertions is not behavioral evidence. The assertion count is the maximum in any
one invocation, not a total of unique checks over scans. Reconcile the intended
observations separately. Verify each requested publisher's state, file error and
cleanup warning; XML success does not imply JSON success. Never consume the
`.counit.tmp` or `.counit.bak` files as current reports.

For an ordinary xUnit report, from the repository root:

```powershell
python qualification/verify_xunit.py path/to/fresh-report.xml --require-success
```

The parser checks report semantics, not freshness, project identity or the
selected inventory. For controlled runs with independently captured identities
and inventory, use `tools/accept_run.py` as described in the
[report-checking example](docs/examples/host-acceptance.md).

## XML and JSON

Failures preserve the first assertion's bounded message, expected and actual
values. Later cleanup or termination information is separate and must not replace
that failure. XML encodes comparison details in the failure body. `AssertResult`
combines CheckId, Message and Detail into a bounded message; expected and actual
remain separate. Disclose any caller-side truncation before submission.

JSON is disabled by default. Set the `DiagnosticJsonEnablePublish` library
reference parameter to TRUE before building, and assign a distinct fresh
`CoUnit.GVL_coUnit.DiagnosticJsonFilePath` before startup. The current schema 2
carries run/build/target and generation when supplied, case/row identity for
catalog runs, selection, execution, results and fixture information. A configured
legacy run has run/build/target identity but not catalog identities or catalog
Selected/Started semantics. Unconfigured legacy runs do not supply those
identities. The parser also accepts historical format 1, which lacks the schema 2
identity and catalog fields. See [report identity](docs/2.1-upgrade.md#report-identity).

The publishers commit independently; one can succeed while the other fails.
Paths must be valid and distinct. JSON path validation uses canonical ASCII paths
of the same absolute or relative kind as XML; check the implementation's path
rules before integrating a host. Successful publication does not imply test PASS.

## Qualification

Historical 2.0.0 and 2.0.1 report results are version-specific and do not alone
qualify 2.1.0.6. See the [qualification record](docs/upgrade-plan.md) and
[framework qualification](qualification/README.md) for supported scope and gaps.
