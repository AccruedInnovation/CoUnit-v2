# Scan-trace qualification cases

These are test suite sources, not a new runner or native evidence. Build against
the candidate installed CoUnit package with the existing selected-suite workflow.
Use fresh output paths and a disposable runtime. The qualification host must
capture raw standard INFO log entries and independently check names, scan numbers,
sequence numbers, part counts and reconstructed payloads.

- `FB_ScanTraceWait_Test`: two invocations, the first returns early after a
  nonterminal EXIT; the second ends and checks five assertions and helper Reset.
  Run the entire selected case again after the supported application/framework
  reset with fresh report and log capture; product/helper Reset alone is not a
  second CoUnit run.
- `FB_ScanTraceProtocol_Test`: verify an unrepresentable payload is rejected,
  trace completeness stays false, and Reset clears the closed status. This does
  not exercise a failing sink.
- `FB_ScanTraceFailure_Test`: select separately. Expect one failed case with
  original `trace/expected-failure` and a terminal trace, not a passing run.
- `FB_ScanTraceTimeout_Test`: select alone with a finite host watchdog. Expect an
  unfinished case and waiting scan records, then exact runtime/IDE cleanup. This
  deliberately has no terminal record and is not passing test evidence.

A real sink failure must be exercised with a qualified fault route; no fake sink
success or unverified logger mutation is supplied by these fixtures. Preserve raw
logs and report exact allocation/IDE cleanup before claiming qualification.
