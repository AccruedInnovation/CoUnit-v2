# Checking completed CoUnit reports

The repository provides report validators. They inspect captured files; they do
not connect to a PLC, start tests, or establish report freshness by themselves.
Use your test environment to build and run the selected application and capture
fresh reports before cleanup.

For ordinary legacy xUnit success:

```powershell
python qualification/verify_xunit.py path/to/fresh-report.xml --require-success
```

Independently check the exact selected suite/case inventory and report path. For a
controlled catalog run, `tools/accept_run.py` also checks identities and an
independently prepared inventory. Supply actual captured values, not example IDs:

```powershell
python tools/accept_run.py --xml runs/run-001/report.xml `
  --json runs/run-001/report.json --inventory runs/run-001/inventory.json `
  --run-id RUN_ID --build-id BUILD_ID --target-id TARGET_ID `
  --framework-version 2.1.0.6
```

Omit `--json` only when JSON was not requested. A failed case, incomplete report,
identity mismatch or abnormal run disposition must not be reported as a pass.
The acceptor's catalog requirements do not turn legacy Selected/Started fields
into catalog evidence. See [report acceptance](../../REPORTING.md).
