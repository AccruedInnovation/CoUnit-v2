# Framework qualification

The [qualification summary](../docs/upgrade-plan.md) distinguishes the current
candidate's bounded observations from historical results. The fixtures and
independent oracles below include deliberate failures and internal hooks: these
are not ordinary consumer test patterns. `native-evidence.zip` and
`runtime-matrix.csv` preserve the historical 2.0.0.0 simulator evidence and its
limits; that matrix does not qualify the 2.1.0.6 candidate.

## Build and execute one isolated shard

From the repository root:

```powershell
python qualification/generate_native.py
python -m unittest discover -s qualification -p test_host_tools.py
python qualification/check_public_api.py
python generate_assertions.py --check
```

The generator emits complete split source and `generated/<shard>/qualification.xml`, using the repository PLCOpenXML writer. It never accesses CODESYS. Import exactly one shard into a clean disposable application alongside the 2.0.0 library source. Remove the previous shard's importable object tree first. Only `PRG_Qualification` belongs in the owner cyclic task. **Do not call suite instances manually**: this runner invokes its registered suites. These fixtures access internal diagnostics and therefore initially belong in the same native application as the imported library source. Installed-library consumer compatibility is a separate build.

The fixture outputs `Done`, `OraclePass`, and usually `FailedCheck` and `SnapshotBytes`. `Done` observes runner `COMPLETE`, including exceptional invalid-snapshot completion. A false `OraclePass` is a qualification failure. `generated/<shard>/expected.json` gives independently authored expectations and the one-based check expressions corresponding to `FailedCheck`. Assertions inside suites are deliberate stimuli to the library; snapshot comparisons outside those suites are the qualification oracle. An expected FAILED test is not a failed qualification if its exact count, family and first-failure event match.

Bind the output path to a run-owned disposable directory before launch, remove/archive the exact previous report, record the selected classes, and observe a fresh complete report under a finite host timeout. Completion, report availability, correct inventory, actual assertion truth, file currentness and cleanup are separate checks. Retain failures and partial output across retries. Use a sufficiently generous simulator task watchdog for the full-capacity snapshot; measure actual static memory and execution time rather than lowering the default 32/2048/2048 capacities.

## Shards

| Shard | Independent expected behavior |
|---|---|
| `families` | One deliberate failure for each of 44 public methods; exact enum, message and one assertion per case. |
| `values` | REAL/LREAL raw-bit NaN/Inf/bad delta outcomes; 280-byte STRING and 280-code-unit WSTRING; ANY mismatch and user representations. |
| `descriptors` | Ten raw descriptor cases: null, negative size, wrong primitive size, odd WSTRING size, missing terminators, valid controls and zero-length user representation. Requires the test-only injected hook described below. |
| `utf8_diagnostic` | Raw UTF-8 bytes force a diagnostic cut inside a multibyte sequence. The fixture forces the decoder branch after the first RUN encoding bind; this does not qualify a native UTF-8 compiler/runtime row. |
| `multiscan` | Branch A pass then B fail at ordinal one; A-first-failure companion; 10,000 invocations; zero and three assertion cases. |
| `integrated` | Two suites under RUN: delayed pass, repeated changing-value failure, disabled case and second-suite pass. |
| `ordered` | Disabled first/middle/last become SKIPPED; enabled successors finish. |
| `names` | Whitespace/disabled canonical names, duplicate suppression, finish B while A retains its two assertions. |
| `sequence` | Three separately registered suites finish in order. Repeat with a nonzero configured delay and capture timestamps. |
| `zero` | Empty registration reaches COMPLETE with zero counts. |
| `assertions_max` / `assertions_overflow` | 2048 calls accepted; 2049th produces framework error while stored count stays 2048. |
| `tests_max` / `tests_overflow` | 2048 named records remain intact; 2049th cannot commit a record. |
| `suites_max` / `suites_overflow` | Exactly 32 registrations; 33rd causes framework error without an extra suite. |
| `aggregate_65536` | All 32Ã—2048 tests run in sequence; total and passed equal 65536; every test record is checked. |
| `aggregate_65536_failed` | Same full capacity with one deliberate failure per test; total and failed equal 65536 and every test has one assertion. |
| `mode_switch` | Switching mode with an open test produces framework error and terminal ERROR, never success. |
| `abort` | Owner abort with an open test produces ABORTED and an error-category snapshot. |
| `cross_task` | Put `PRG_QualificationForeign` on a distinct bounded task; it waits for scalar owner-ready then calls once. Foreign name must never register; original test becomes ERROR. |
| `task_lookup` | Inject failed task lookup after ownership is established; clear injection; next owner call reports framework error without invalid dereference. |
| `initial_lookup` | Three failed task lookups before binding preserve IDLE, epoch zero and registration/test state. Diagnostic claim is one; a later healthy RUN completes normally. Capture exactly one matching diagnostic independently. |
| `platform_helpers` | Real successful task/project lookup, injected invalid result, then successful recovery. All six output booleans must be true. |
| `snapshot_failure` | One-shot snapshot failure reaches COMPLETE/FRAMEWORK_ERROR with invalid snapshot for repeated calls. No new report or success banner is permitted. |
| `seal_violation` | Inject immediately before snapshot seal. Both dispositions become FRAMEWORK_ERROR, the snapshot remains valid, and already-terminal pass/fail/skip records and counts remain intact. |
| `device_log` | Capture plain/substituted text, first-placeholder-only replacement, a complete 498-byte prefix/argument/suffix result, and raw UTF-8 at the 127-byte chunk boundary. |
| `timeout` | Deliberately leaves a test open. The finite external watchdog must classify EXECUTION_TIMEOUT, retain evidence, and stop/reinitialize the disposable application. |
| `reporting` | Six-case independently populated snapshot (pass, scalar/array failures, skip and error) drives XML plus an independently configured optional JSON publisher with controlled file failures/pauses. |

The complete 32-VER / eight-SCN map and residual observations are in [coverage.csv](coverage.csv). This map deliberately does not convert a generated fixture into a native PASS. Max-bound guards, disabled-body effects, registration timing, repeat-state memory use and platform diagnostics need observations beyond the final snapshot.

## Independent XML checks

For the direct publisher's six-case snapshot:

```powershell
python qualification/verify_xunit.py <fresh-report.xml> qualification/generated/reporting/expected.json --require-disposition
```

For ordinary native shards, bind the exact suite instance path from the imported project **before launch** and supply one class per registered suite:

```powershell
python qualification/check_report.py <fresh-report.xml> qualification/generated/multiscan/expected.json --suite-class <exact-suite-class>
```

`verify_xunit.py` checks XML structure, terminal children, counters, failure type/message/body text, and optional exact logical JSON. Its positive fixture and three intentional negative fixtures are preserved under `fixtures/`. `check_report.py` additionally requires the generated selected case inventory and externally bound class names. A self-consistent empty report cannot satisfy a nonempty expected inventory. Neither parser establishes launch identity or atomic publication by itself.

The optional JSON publisher is checked against that same logical expected file:

```powershell
python qualification/verify_json_report.py <fresh-report.json> qualification/generated/reporting/expected.json --require-disposition
```

The JSON oracle requires UTF-8, format version 1, closed object keys, consistent root/suite counts, unique JSON keys, terminal case states and exact first-failure details. It normalizes failure `expected` and `actual` into the same labeled body checked by the XML oracle. A requested sidecar must also be bound to the exact run by the external completion record and fresh run-specific path; parsing alone does not prove freshness. JSON is default-off and has independent state and file effects. One publisher may commit when the other fails, and a JSON failure does not change XML bytes, testcase truth or run disposition.

CoUnit 2.0 candidate reports must include root attribute `counit-run-disposition="NORMAL|ABORTED|FRAMEWORK_ERROR"`. The qualification parser preserves it as `run_disposition`, allowing deliberate ABORTED/FRAMEWORK_ERROR fixtures to match their expected outcomes without changing terminal test counts. `check_report.py` always requires and compares it; the generic XML parser requires it with `--require-disposition` so original legacy controls remain usable. `--require-success` is a separate release-success gate requiring NORMAL, at least one test, zero failed assertions and zero error cases. Expected-negative qualification fixtures must not use that success gate.

Generic JUnit consumers that ignore this additive root attribute can still misclassify a framework-error run whose tests were already terminal. CI consumers must apply the disposition gate before declaring success; XML schema/consumer compatibility with the additive attribute is a separate downstream qualification obligation. Original 1.2.0.3 reports may lack it; absence cannot establish a CoUnit 2.0 report claim.

Array and argument-error messages may include the contract-permitted diagnostic suffix/prefix. Their oracles require the exact assertion family and preserved identifying message; the dedicated first-failure BOOL cases still require exact complete message equality. This prevents formatting choices from replacing the semantic first-failure oracle.

For `descriptors`, inject `test_hooks/CompareAnyForQualification/CompareAnyForQualification.{DEC,IMP}.exp` as a method of the candidate `FB_TestSuite` **in the disposable qualification project only**. The hook is not shipping library code. It delegates to the same private comparator with explicitly supplied pointer/size/type descriptors. Every pointer except the deliberate null case names valid sentinel-backed storage; all bytes are checked unchanged afterward. These tests qualify the comparator guard, alongside public ANY transport cases in `values`.

For `utf8_diagnostic`, the first suite invocation only registers an open test. After that first RUN performs native encoding binding, the program sets `GVL_coUnit.StringIsUtf8=TRUE`; the second invocation exercises the decoder branch. Native expected values are byte-array constants, avoiding compiler-dependent string literal encoding. This is a controlled decoder test, **not evidence of a native UTF-8 compiler/runtime support row**. Efficiently capture `DiagnosticHex[1]` through `[4]` after Done; each STRING(128) holds 64 raw bytes, in order. Save `{"hex_chunks":[four strings]}` and run `check_utf8_diagnostic.py <capture.json> generated/utf8_diagnostic/expected.json`. A JSON list of all 256 `DiagnosticBytes` values is also accepted. The host uses a strict Unicode decoder and independent encoded expected bytes to reject missing terminators, split multibyte sequences, wrong truncation markers and non-maximal prefixes. Merely reading a formatted diagnostic string through a monitoring UI may conceal invalid bytes and is insufficient.

For `device_log`, `generated/device_log/expected.json` defines five independently expected complete messages. The long format and argument are each 250 bytes and must produce all 498 bytes, including distinct `QLONG-BEGIN`, `QARG-BEGIN`, `QARG-END` and `QLONG-TAIL` markers. The UTF-8 case places the first byte of `Ã©` at offset 126 so a naive 127-byte split would corrupt the character. Capture ordered chunks for each call, grouped as a JSON object by `plain`, `substitution`, `first_only`, `long`, and `utf8_boundary`; each chunk can be a string or `{"hex":"raw bytes"}`. Run `check_device_log.py <capture.json> generated/device_log/expected.json`. It rejects lost suffixes, wrong substitution, reordered content, chunks over 127 bytes and split UTF-8. Prefer raw bytes when the native monitor uses a legacy STRING decoder. The separate `log_capture/` observer, when available, must start before the first fixture call and stop after completion; its overflow/error flags are additional acceptance checks.

## Publication and currentness controls

For `reporting`, set `TextMode` to the actual bound project encoding: `UTF8`, `LATIN1`, or `WINDOWS1252`. `UNKNOWN` deliberately fails preflight. `Path` must be inside the disposable directory. Its default is only a proposed relative path; create/bind the directory in the native launcher. `ChunkLimit=64` makes the six-case XML report exceed several chunks and streams labeled expected/actual failure bodies. Keep `ExpectedState=WRITTEN` for normal publication, or use `FAILED` for precommit failures. `Configured` alone is not acceptance.

For JSON cases, set `JsonEnabled=TRUE`, give `JsonPath` a distinct fresh sibling filename, and select `JsonExpectedState` independently. JSON and XML paths must be canonical ASCII paths with the same relative/absolute kind and base interpretation; the adapter's `PlcLogic/ci/report-{run_id}.json` relative sibling path is supported. Preflight rejects non-ASCII bytes, repeated or mixed separators, `.`/`..` components, trailing dots, reserved Windows device names and unresolved macro forms. The publisher uses a fixed 256-byte chunk and cursor rather than a snapshot/report copy. Its companion paths use the same `.counit.tmp` and `.counit.bak` suffixes and 244-byte final/255-byte companion bounds; preflight checks the JSON final/stage/backup against all three XML paths before any JSON file operation, folding ASCII case and normalizing separator direction. An invalid or colliding JSON path fails only the JSON publisher. Test OPEN, WRITE, FLUSH, CLOSE, RENAME/commit and cleanup faults separately for each publisher, including a known prior file and reinitialization at phases 6, 7 and 8. Capture `JsonPublisherBytes` and `SnapshotBytes` from the generated fixture on the qualified target; source `SIZEOF` declarations are not a measured memory result. Verify the final JSON with the command above. Windows-1252 byte mapping and raw UTF-8 decoding are separate qualification cases; do not infer native UTF-8 runtime support from the decoder fixture.

`SuiteName` and `FailureMessage` are writable pre-start inputs for encoding probes. Prepare the expected decoded text separately before applying raw bytes; update the independent expected JSON accordingly. The default six-case JSON applies only to the default text inputs.

Each run starts from a new application instance. Precreate a known prior complete file with unique sentinel bytes and compare those exact bytes after faults. File operation occurrences are counted only within the selected operation class. Operations occur in this order, with conditional recovery operations depending on initial files:

Every `DeleteIfPresent` first performs an additional PROBE. A missing path succeeds without an actual DELETE, so DELETE occurrences count existing-file deletions only. Include these extra probes when targeting PROBE faults; a fresh publication with no backup performs no cleanup DELETE.

1. Probe final, backup, stage; recover or remove stale companions as specified.
2. Open stage; write chunks; flush; close; probe stage size.
3. Probe final; rename final to backup if present; rename stage to final.
4. Delete backup after commit.

| Stimulus | Expected independent observation |
|---|---|
| Fail PROBE/OPEN/WRITE/FLUSH/CLOSE at the selected occurrence | FAILED, no success banner, unchanged snapshot, prior complete final or absence. |
| WRITE with `ShortWrite=TRUE` | Actual stage bytes exist, exact short count causes failure; final remains prior complete/absent. |
| Prior final + RENAME occurrence 1 | Backup preparation fails before commit; previous final remains. |
| Prior final + RENAME occurrence 2 | Commit fails and restore succeeds; previous final restored. |
| Prior final + RENAME occurrences 2 and 3 | Commit and restore fail; final absent, prior complete backup retained; no partial current. |
| Stale stage + DELETE occurrence 1 | Startup cleanup failure is precommit failure. |
| Prior final + DELETE occurrence 1 with no stale companions | Postcommit backup cleanup warning; state remains WRITTEN and new final is complete. |
| PauseAfterPhase 6 | Closed complete stage exists; reinit must not promote stale stage to current. |
| PauseAfterPhase 7 | Prior final moved to backup; reinit restores/reconciles according to startup rules. |
| PauseAfterPhase 8 | New complete report already committed; cleanup failure/reinit cannot revert semantic success. |

Set `ReleasePause=TRUE` to resume the same publication; use full application reinitialization for interruption/recovery tests. The host must watch actual bytes during the pause, not just after the final state. Precommit faults must preserve a known assertion failure in the canonical snapshot.

Path-capacity variants require 244 stored bytes accepted and 245/246 rejected before any `FileEffects`: ASCII 244/245 and UTF-8 122/123Ã—U+00E9. The accepted staging/backup paths are exactly 11 bytes longer and pairwise distinct. Full paths include directory bytes; account for the bound directory rather than assuming 244 characters fit. Legacy mapping cases must inject raw 0x80/0xE9 and compare to an independently established code-page mapping. A project encoding label alone is insufficient evidence.

## Compatibility and support

`check_public_api.py` compares all 60 R3 declarations to 1.2.0.3. It excludes private/local variable blocks and comments from callable signatures, while preserving input/output/in-out types and names, returns, result structures and configuration values. The only approved public exception is `ST_TestSuiteResults.NumberOfTestCases`, `NumberOfSuccessfulTestCases`, and `NumberOfFailedTestCases`: UINTâ†’UDINT, approved by the user for 65536 aggregate capacity. Any other drift fails. A real current consumer must still compile against installed 2.0.0 without normal test-source edits; runner/library binding changes are recorded separately. Bounded installed CoUnit 2.0.1.0 consumer and JSON-on checks do not replace the historical 2.0.0.0 framework matrix or establish 2.1.0.6 compatibility.


For the aggregate native runs, also capture the legacy result projection: `GVL_coUnit.coUnitRunner.TestResults.TestSuiteResults.NumberOfTestCases`, `NumberOfSuccessfulTestCases`, and `NumberOfFailedTestCases`. The pass variant expects 65536/65536/0; the failed variant expects 65536/0/65536. These are private diagnostic monitor paths, not new public API calls. The suite source checks the canonical snapshot; the legacy capture independently detects projection narrowing.

Use `check_runtime_matrix.py <matrix.csv>` to enforce exact dispositions and missing binding checks beyond the packet authoring validator. Record candidate identity once after edits/tests settle, exact compiler/runtime/library/OS/CPU versions, STRING mode/mapping, actual snapshot SIZEOF and application static memory, all 32 VER outcomes and eight integrated SCN outcomes. Required FAIL means UNSUPPORTED; missing/inconclusive evidence means UNQUALIFIED. Only an exact completely qualified simulator row may become SUPPORTED. The release owner retains final acceptance.

## Standalone native environment and packaging

The repository contains the required source generators and MCP bridge client; CODESYS and its licensed extensions are external prerequisites. Create a disposable project with a simulation-capable device and `Application`, save it as `LocalArtifacts/CoUnit2/qualification.project`, and make it primary before running the native launch tools. The tools reject other project names and verify the simulator build before login. The large workstation project and vendor-managed libraries are intentionally not redistributed. `tools/run_native.py` accepts a ScriptEngine file and an explicit JSON argument file; `tools/native_qualification.py` documents the supported operations in its source. Source fixtures can instead be imported manually into an equivalent disposable simulator application. Do not import qualification hooks into the shipped library.

Pass `source`, `tools` and `dependency_template` (a secondary copy of the packaged library) for source qualification, plus the chosen XML, report path, finite polling limit and observation variables. `run_shards.py`, `run_publication.py` and `run_publisher_edges.py` encode the tested selections and oracles. Use unique report names; no prior XML is admissible as a new run result.

`native_qualification.py` scopes `LogPrompts`, prompt detail logging and explicit Yes answers to its authorized disposable-project operation, then restores them. Verified keys include `CleanAll_Query`, `CleanActiveApplication_Query`, `QueryProgramChanged` and `QueryCreateApplication`. Unknown prompts use the logged native default rather than opening a blocking modal dialog; inspect their results.

The first installed-library builds exposed stale native language-model declarations despite exact text read-back. A clean consumer rebuild removed stale method diagnostics; recreating the isolated candidate's GVL_coUnit object and resynchronizing its exact declaration removed the remaining declaration corruption. The final saved library passes installed consumer compilation and all eight tests. `consumer-native1` through `consumer-native5` preserve failures; `consumer-native6` is the accepted run.

The archive retains original absolute launch paths as evidence, not as active source dependencies. Current generators work from this standalone repository. The archived original-project restoration receipt also records a final 599-section source comparison.
