# Scan tracing — 2.1.0.7 candidate

The candidate has a clean native library build and read-back, but is not a released
or runtime-qualified library.
A suite owns one `CoUnit.FB_TestScanTrace` per case. Calling its methods does not
change the test runner, assertions, scheduling, clocks, deadlines or product calls.
Only the caller knows the source and sampling time of its observations.

Inside an executing test guard, call `BeginScan(Name, Stage)` once for each
invocation, `Emit(Payload)` for each captured observation, and `EndScan(Terminal)`
before *every* return from that invocation. Use `Terminal := TRUE` only on the
final invocation. Captured values must be sampled before calling Emit. Label them
`current`, `prior` or `unknown`, and identify fixture, deadline and wall-clock
time explicitly when relevant; the tracer does not read or convert a clock.
Do not call the tracer during discovery or inactive replay. Do not use its BOOL
returns to skip production calls or change test completion: retain them and
inspect trace status independently.

`Scan` counts begun invocations; `Sequence` counts sink entries across all record
kinds for this instance. Records are printable ASCII with a stable name of 1–32
non-space characters; payloads may contain spaces. Control bytes and non-ASCII bytes are rejected; the rejection latches `Incomplete`
and increments `ProtocolErrors`. Percent signs are accepted as logger text. Text passed into
`Emit` is `STRING(255)`; a caller that truncates before the call must disclose it.
Each logical record is emitted in chunks of at most 48 payload bytes with scan,
sequence and part/total fields; every sink entry is at most 122 characters.
A reader groups by instance name and scan, checks the per-instance sequence and
part counts, and concatenates parts. Trace names must uniquely identify active
instances within the collected log.

`LastResult` is the last actual CmpLog sink result and is meaningful only when
`HaveSinkResult` is TRUE. `Errors` counts failed sink calls; `ProtocolErrors`
counts invalid calls/data or exhausted counters. Both saturate. `Incomplete` is
latched on either kind of failure. `Ended` means terminal close was attempted;
`Complete` means it ended with no recorded failure. These flags cannot detect a
caller that stopped invoking the FB before closing a scan: host evidence must also
require a fresh complete BEGIN/ENTER/EXIT/END sequence and expected case inventory.
A sink return is not proof that a host received or retained an entry.

`Reset()` permits a new trace after terminal close, or before the first scan. It
rejects an open or unfinished trace so incomplete evidence is not silently erased.
Capture the first run's status and logs before reset. Do not reset framework globals
or zero the FB's memory. An application reset gives ordinary non-retained FB state
its normal runtime semantics; verify that for the actual target.

The sink uses the standard logger and the component registered by CoUnit's existing
support component, with symbolic INFO. It does not alter `WRITE_DEVICE_LOG` or its
named destination. The package must include its own CmpLog, CmpErrors and component
references; source text alone does not prove that native dependency closure.
