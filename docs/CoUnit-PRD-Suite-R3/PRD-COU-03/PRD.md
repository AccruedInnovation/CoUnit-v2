# PRD-COU-03 — Results, Logging, and xUnit Publication

## 1. Status and decision summary

**Assignment:** `PRD-COU-03`  
**Architecture:** `COUNIT-ARCH-R3` / `2026-09-09-r3` — `APPROVED`.  
**PRD revision:** `PRD-COU-03-R3` / `2026-09-09`.  
**PRD status:** `PARTIAL`.  
**PRD approval:** `CANDIDATE`.  
**Implementation-ready:** **no**. Detailed reporting and publication design is closed, including `OPEN-COU-003`, but the active implementation repo/target is not bound, predecessor implementations do not exist, and fresh-context recipient review has not run. All slices remain `NOT_READY`.

**Outcome.** Build one immutable final result snapshot after execution stops, project it truthfully to legacy result types, emit useful Device Log output, and publish bounded streamed xUnit XML. A failed or partial publication must never become the externally current report. Test truth remains separate from report delivery.

**Target worker.** Conservative CODESYS worker profile: edit ST/library objects, follow exact state/file sequencing, run specified target tests, and make private helper-layout choices. It must not redefine result categories, assertion count meaning, current-report semantics, public result types, XML count meaning, or failure acceptance.

### Governing sources

R3 `ADR-COU-010..012`, `016..017`; `IF-COU-004/005`; `ISC-COU-003/004`; `SDE-COU-003`; requirements `REQ-COU-022..031`, `036` plus public compatibility contribution `REQ-COU-001`. `SRC-001` supplies current result/log/XML/file implementations as evidence. CODESYS SysFile documentation is supporting evidence only; PRD-04 qualifies actual release targets.

### Detailed decisions made here

| ID | Decision | Origin/status | Authority | Owner | Acceptance |
|---|---|---|---|---|---|
| `DD-COU03-001` | Close `OPEN-COU-003` with reserved sibling staging/backup protocol: `P.counit.tmp`, `P.counit.bak`; write/close staging, preserve existing current at backup, then stage->final rename is semantic commit; restore backup on failed commit where possible. | newly selected `ACTIVE_DELEGATED` | PRD-03 target publication mechanism delegation | PRD-03 | `VER-021/031`, `QAS-008/013`, `SCN-006` |
| `DD-COU03-002` | Stream XML through a bounded raw-byte chunk; every SysFile write checks both result and returned byte count. | derived/detail `ACTIVE_DERIVED` from `ADR-011`, `REQ-029/030` | inherited | PRD-03 | `VER-020/021` |
| `DD-COU03-003` | XML input decoding is bound to the project-wide CODESYS `STRING` encoding mode. UTF-8 projects validate/copy UTF-8 code points; legacy projects decode the exact legacy single-byte mode established at preflight. XML-forbidden code points or malformed input become U+FFFD before XML escaping. | newly selected `ACTIVE_DELEGATED`, corrected in R2 | XML code-point policy delegation | PRD-03 | `VER-019`, `QAS-006` |
| `DD-COU03-004` | `SysFileFlush` success is used when supported; exactly NOT_IMPLEMENTED/NOT_SUPPORTED is recorded and close remains mandatory; other flush errors fail publication. No power-loss durability claim is made. | newly selected `ACTIVE_DELEGATED` | target file mechanism | PRD-03 | `VER-021/025` |
| `DD-COU03-005` | Post-commit backup cleanup failure is a warning, not a rollback of `WRITTEN`, because semantic currentness has already moved to a complete final file. | newly selected `ACTIVE_DELEGATED` | publication-state detail | PRD-03 | commit fault matrix |
| `DD-COU03-006` | Companion-path admission uses stored byte length and a bounded byte append, not character-count `LEN()`. Overflow, truncation, missing terminator, or path aliasing fails before any filesystem effect. | derived repair `ACTIVE_DERIVED` | `T_MaxString` byte capacity + `REQ-030/036` + `IF-COU-005` | PRD-03 | `R14-path-byte-capacity`, PRD-04 S2 |

The complete normative contract is [`contracts/reporting-contract.md`](contracts/reporting-contract.md).

### Open items

- `OPEN-COU-001`: active repository/project, exact target/toolchain and writable scope must be bound before dispatch.
- predecessor implementation outputs: accepted PRD-01 terminal state and PRD-02 failure/count semantics are required for implementation integration.
- `PRD03-REV-001`: fresh packet-only recipient review remains `NOT_RUN`.
- Target rename/flush/file-result behavior is **future qualification**, not an open semantic choice. A target that cannot satisfy the selected commit protocol is unsupported for xUnit publication until an architecture-approved alternative is supplied.

Architecture `OPEN-COU-003` is **closed by detailed design** in this PRD; it is not claimed implemented or runtime-qualified.

### Dispatch

`COU03-S1/S2/S3`: `NOT_READY`. Implementation acceptance: not established.

## 2. Repository discovery and current state

No active repository/path is supplied. Current implementation facts are from exact `SRC-001`.

### Observed result/log path

`FB_coUnitRunner` owns `FB_TestResults`, `FB_CdsTestResultLogger`, and `FB_xUnitXmlPublisher` and calls them continuously after suite execution work. `FB_TestResults` incrementally stores suite/general result data in legacy structs rather than building one immutable terminal snapshot.

The legacy structures are:

- `ST_TestCaseResult`: name, class, failed/skipped booleans, failure message/type, `NumberOfAsserts : UINT`;
- `ST_TestSuiteResult`: name/identity, number of tests/failed, fixed testcase array;
- `ST_TestSuiteResults`: suite count, testcase total, successful count, failed count, fixed suite array.

The current source does not copy the R3 assertion max metric because that architecture is new. Current successful count logic treats “not failed” too broadly for R3 skipped/error truth.

### Observed logging/XML/file defects

- `WRITE_DEVICE_LOG` returns immediately when `%s` is absent and emits long text tail before head.
- xUnit builds one whole document in `FB_XmlControl` using configured 1 MiB buffer in the supplied snapshot.
- root `tests` is currently written from successful count, not total.
- the current file flow deletes the configured final report and writes directly to it.
- `FB_FileControl.Write` passes a result pointer to `SysFileWrite` but does not capture/check the returned byte count.
- xUnit logs an exported-success banner after its helper call without requiring that helper to succeed.

### Platform evidence

Current CODESYS SysFile reference exposes checked open/write/flush/close/rename/delete calls; write returns a byte count, and flush may explicitly report unsupported/not implemented. The docs do not promise rename-over-existing behavior or cross-target atomicity. This PRD therefore avoids relying on overwrite-by-rename and treats target support as qualification evidence.

### Evidence table

| Claim | Evidence | Result/limit |
|---|---|---|
| current whole-buffer XML/direct-final write exists | `SRC-001/FB_xUnitXmlPublisher`, `FB_XmlControl`, `FB_FileControl` | observed source |
| current root tests uses successful count | xUnit publisher implementation | observed source |
| current write does not check returned byte count | `FB_FileControl/Write` | observed source |
| Device Log requires `%s` today | `WRITE_DEVICE_LOG.IMP.exp` | observed source |
| final result types are legacy fixed structs | result DUT declarations | observed source |
| `SysFileWrite` returns bytes-written + result | current CODESYS docs | supporting evidence; target execution not run |
| `SysFileRename`, `Flush`, `Close`, `Delete`, `Open` have result-bearing APIs | current docs | supporting evidence; exact target behavior later |
| active repo/target/filesystem path/version | none supplied | dispatch input missing |

Full source/platform notes are in `../review/`.

## 3. Outcome, scope, and non-goals

### Obligations

`U03 = {REQ-COU-001, REQ-COU-022..031, REQ-COU-036}`.

Local refinements:

- `L-COU03-001`: stage/backup companion names are reserved CoUnit-owned paths while xUnit is enabled;
- `L-COU03-002`: semantic commit is the successful stage->final rename after stage close;
- `L-COU03-003`: dynamic text uses one deterministic XML/UTF-8 policy bound to the project-wide CODESYS `STRING` encoding mode; no hard-coded single-byte transcode is used for UTF-8 projects;
- `L-COU03-004`: a complete successful write checks status **and** byte count;
- `L-COU03-005`: post-commit cleanup cannot revoke a valid already-current complete report;
- `L-COU03-006`: snapshot storage cost is measured on the bound compiler/target before implementation acceptance/support qualification; if the full R3 snapshot cannot fit the application memory budget, implementation stops for an architecture/storage decision rather than silently weakening the snapshot contract.
- `L-COU03-007`: report-path admission is byte-capacity based. `P`, staging and backup paths must be proven nontruncated, NUL-terminated and pairwise distinct before any filesystem effect; UTF-8 character count is not a substitute for byte length.

### Observable success

- Final snapshot appears only after run finalization and obeys total = passed+failed+skipped+errors.
- Legacy successful counts equal passed only; failed booleans mean assertion failure only; skipped booleans remain truthful; assertion count is copied unchanged from PRD-02 max-per-invocation.
- Plain log messages emit without `%s`; `LogExtendedResults=FALSE` hides only verbose detail.
- XML total/failure/error/skip counts reconcile and dynamic text cannot break XML syntax.
- A report much larger than the in-memory chunk writes fully and parses.
- Any required pre-commit file failure yields `FAILED`, never success banner, and cannot put partial stage bytes at the current final path.
- Restart while staging is partial restores/keeps prior complete final or no current report and cleans stale staging before the next publication.

### Scope

In: snapshot, legacy projection, Device Log function/logger, xUnit XML structure/escaping/streaming, file adapter, report state, stage/backup/currentness, restart cleanup.

Out: test execution/assertion semantics, durable power-fail filesystem guarantees, network CI transport, new result public fields, multi-process publisher coordination, automatic same-run retry, release support declaration.

### Actors/owners

PRD-01/02 are snapshot producers; snapshot is canonical reporting input; Device Log and xUnit are independent consumers. The configured final file is the CI/human file-consumer boundary. PRD-03 owns file publisher detail; architecture owner owns shared currentness meaning; PRD-04 owns final integrated qualification.

## 4. Interfaces and data contracts

Normative definitions: [`contracts/reporting-contract.md`](contracts/reporting-contract.md).

### Snapshot contract

One private native structured snapshot includes run disposition; total/pass/fail/skip/error counts; suite identities/counts; test canonical name/class/state/count/first-failure. `IsValid` commits last after all count invariants pass. No publisher reads canonical suite/test live state after this point.

### Legacy mapping

Legacy fields remain source-compatible and are projections only. In particular, a legacy test record with both booleans false is **not sufficient evidence of pass** because legacy representation cannot express abort/framework error. New publisher logic uses canonical `State`, never `NOT failed AND NOT skipped` inference.

### xUnit contract

Root attributes: `tests=Total`, `failures=Failed`, `errors=Errors`, `skipped=Skipped`. Each suite has the same four counts plus id/name. Each testcase has `name`/`classname` and may carry an `assertions` attribute; terminal state is represented only by exactly one of no result child (pass), `<failure/>`, `<skipped/>`, or `<error/>`. Do not emit a second `status` attribute that duplicates terminal state.

If a release's named external schema rejects the optional `assertions` attribute, omit that attribute for that compatibility profile; do not alter internal/legacy R3 count semantics.

### XML text

One escaper handles every dynamic string. Contract §5 binds the source `STRING` encoding mode, code-point validation/replacement, and entities. The exact compile option must be captured at repository/target preflight and later in the qualification row. Static XML tokens are constants and do not bypass syntax review.

### File/publication contract

`P` current; `P.counit.tmp` staging; `P.counit.bak` backup. Final path must be nonempty and its **stored content byte length** must be at most 244 under current `T_MaxString=STRING(255)` and 11-byte suffixes. Standard `LEN(P)` is not the admission check in UTF-8 mode. The bounded companion builder must prove both derived paths are NUL-terminated, exactly 11 bytes longer than `P`, and pairwise distinct before the first filesystem effect. These two companion names are owned by CoUnit while publication is enabled.

Checked semantic wrappers are `Probe`, `OpenWrite`, `WriteAll`, `FlushIfSupported`, `Close`, `Rename`, `DeleteIfPresent`. Private names may differ, semantics may not.

Compatibility/version skew: snapshot and publisher belong to the same library build. PRD-04 rejects mixed candidate evidence. There is no persisted snapshot version across restart.

## 5. Canonical production and verification closure

| Derived artifact/value | Producer | Inputs | Consumer | Independent check |
|---|---|---|---|---|
| final snapshot | result finalizer | terminal canonical records + disposition | legacy/log/xUnit | recompute counts in tests from fixture terminal states |
| legacy results | projection | final snapshot | existing public consumers | compare each projection field with snapshot oracle |
| Device Log summary | logger | final snapshot | engineering user/log | captured text expectations |
| XML byte stream | xUnit writer | final snapshot | staging file | host XML parser + expected counts/text |
| current report | commit protocol | complete closed stage + current/backup topology | file-only CI/human | fault tests + parse current file only |

No publisher sets snapshot/test truth. `WRITTEN` depends on the commit step, not merely stage file close. The verifier parses the **current final file**, not the publisher's internal buffer/success state.

### Admission/consistency

Publication admission requires one valid snapshot, same-run config values, publisher not already terminal, valid path/chunk size, and successful companion recovery. If snapshot/config/candidate changes before publication starts, start only from the new finalized run; no partial mixed snapshot exists because snapshot is immutable.

## 6. Bootstrap, staging, and migration

### R1 — bind repository + predecessors

Bind `OPEN-COU-001`; inspect actual accepted PRD-01/02 outputs. Confirm result structs/public interfaces still match R3 or route contradiction.

### R2 — snapshot/log (`COU03-S1`)

Build snapshot and legacy projection; fix Device Log behavior. Existing xUnit may temporarily consume legacy output only in a non-release intermediate build, but S2/S3 must consume canonical snapshot before PRD completion.

### R3 — XML stream (`COU03-S2`)

Replace whole-document buffer with stream writer/escaper and checked write count. During this stage write only to a disposable/test staging path; do not enable current-report replacement before S3.

### R4 — commit/recovery (`COU03-S3`)

Add companion path reconciliation and semantic commit protocol; run full fault matrix.

### Upgrade/mixed-version rules

- Existing `P` at first upgraded run is treated as the prior current artifact. The new publisher never edits it in place.
- Old whole-buffer helper types may remain unused for compatibility but cannot remain the xUnit producer.
- A stale `.counit.tmp` from the new protocol is never current and is deleted before new publication.
- `.counit.bak` is a protocol-owned prior-current copy. Recovery rules in contract §9 determine restoration/cleanup.
- Do not attempt to migrate partial in-memory publish state across reinit.

## 7. State, effects, transactions, and recovery

### Snapshot state

Mutable canonical test records -> `FINALIZING` -> snapshot build/check -> `IsValid=TRUE` -> immutable until reinit. Failure to reconcile canonical counts is a framework/report finalization defect and must not create a publishable snapshot.

### Publication state/effects

| State | Allowed effects | Exit |
|---|---|---|
| `DISABLED` | none | terminal for run |
| `PENDING` | probe/recover/delete stale companions | `WRITING` or `FAILED` |
| `WRITING` | create/write/flush/close stage; later rename current/backup/stage during commit | `WRITTEN` or `FAILED` |
| `WRITTEN` | optional backup cleanup warning only | terminal |
| `FAILED` | bounded diagnostic; stale stage may remain non-current | terminal |

### Transaction/commit point

The semantic commit is successful `Rename(stage,P)` after complete write and close. Before that, the external current report is the old `P` or absent. If old current exists, it is moved to backup only after stage is complete. Commit failure triggers one restore attempt.

### Crash/restart traces

1. crash during stage write: old final remains; restart deletes stage.
2. crash after stage close before current->backup: old final remains; restart deletes stage.
3. crash after current->backup before stage->final: final missing, backup complete, stage complete; restart restores backup then deletes stage.
4. crash after stage->final before backup delete: final complete new, backup complete old; restart keeps final and deletes backup.
5. first-ever publish with no old final, crash before commit: only stage; restart deletes it and current remains absent.

No compensating action claims to “undo” bytes already written to staging; staging is simply non-current.

### Concurrent publication

None by architecture: one run/one task and one publisher instance owns the configured report. A second concurrent process writing the same companion/current paths is outside scope and must be prevented operationally. If the product later permits multiple CoUnit publishers to the same path, shared coordination becomes a new architecture decision.

## 8. Source, install, runtime, and platform closure

### Source objects expected to change

- `FB_TestResults` and result mapping helpers/DUTs (private canonical snapshot additions; public legacy DUTs retained);
- `FB_CdsTestResultLogger`;
- `WRITE_DEVICE_LOG`;
- `FB_xUnitXmlPublisher`;
- `FB_XmlControl` may be replaced/unused for xUnit streaming;
- `FB_FileControl` extended/replaced with checked wrappers including byte count, flush, probe, rename;
- configuration docs for final path and reserved companions.

Actual repository files/objects are mapped at dispatch.

### SysFile binding

Current docs establish semantic signatures, but release target versions are unknown. Implementation shall bind exact installed namespace/types/result constants. `SysFileWrite` byte count and result both matter. `Probe` must distinguish missing from real error (for example through `SysFileGetSize` plus result), not treat all failures as missing.

### Path rules

Use the configured path exactly under CODESYS runtime path semantics; SysFile docs accept relative or absolute names and forward slash separators. This PRD does not invent a separate path sandbox because the file target is already an explicit user configuration. It reserves the two suffix paths and validates the stored byte length before any bounded append. Character-count `LEN()` cannot prove UTF-8 storage capacity; the path helper must reject overflow/truncation and companion aliasing before any filesystem effect.

Symlink/junction semantics are target filesystem behavior and not security isolation in this test library. Qualification must use the same filesystem class as the supported runtime profile.

### Install/runtime

No external host service is required. The actual library build/install/test path is unknown until repository binding. Installed-artifact tests must ensure the target test project loads the repaired library artifact rather than stale workspace source.

### Snapshot memory budget

The full fixed R3 snapshot is intentionally large. At the architecture maxima, `32 * 2048 = 65,536` test slots exist. Each snapshot test carries at least five `T_MaxString=STRING(255)`-sized text fields across name/class/first-failure data, so the declared string storage alone is at least `65,536 * 5 * 256 = 83,886,080` bytes (80 MiB) before test state/count fields, suite metadata, alignment, live canonical test state, and legacy-result projections. This is a **design estimate from declared capacities**, not a measured compiled size.

Before PRD-03 implementation acceptance and each release support claim, record `SIZEOF(ST_CoUnitRunSnapshot)` (or exact equivalent) and the relevant application/static-memory figures from the bound compiler/target. The integration/release owner must confirm that the full application fits its actual memory budget. A failure stops the affected release path and returns to the architecture owner for an authorized storage-representation decision; the worker must not reduce cardinality, omit required fields, or change snapshot truth to make it fit.

## 9. Integration, invalidation, and requalification

### Integrations

- PRD-01 terminal records/disposition -> snapshot.
- PRD-02 first failure + max assertion count -> snapshot.
- snapshot -> Device Log/xUnit.
- xUnit stage/commit -> runtime filesystem -> external XML parser/CI.
- PRD-04 owns end-to-end report/currentness qualification.

### Invalidation map

| Change | Required rechecks |
|---|---|
| test terminal state/count semantics | snapshot invariants, legacy mapping, XML counts, log summary |
| assertion count/first failure | snapshot projection, XML attribute if enabled, failure message/type tests |
| public result DUT/interface | source compatibility + all projection consumers |
| XML schema/text policy | parser/metachar/consumer tests |
| chunk size/buffer writer | small-buffer + large-document + byte-count tests |
| final path/byte-capacity helper/companion naming/commit order | path-boundary cases + full failure/restart currentness matrix |
| SysFile component/runtime/filesystem | file adapter and PRD-04 target matrix |

A changed shared currentness contract returns to architecture. A different target-specific mechanism may replace the one here only after proving the same R3 invariant and updating PRD-04 fault tests.

### Authoring boundary/integrated probes

A file-only consumer cannot consult PLC `FAILED`; therefore direct final-path write was rejected. The chosen protocol was traced across all crash points before/after each rename. The key property holds analytically: no partial stage path is ever named `P`; failure either preserves/restores prior complete `P` or leaves `P` absent. Actual filesystem behavior remains `NOT_RUN`.

## 10. Test and evidence plan

| Requirement/VER | Case | Fixture/preconditions | Expected/prohibited | Method/evidence | Status |
|---|---|---|---|---|---|
| `REQ-022/023`, `VER-015` | `R01-mixed-counts` | suite with PASS, FAIL, SKIP, ERROR/ABORT | exact suite/root invariant; legacy success=PASS only; failed bool only assertion FAIL | CODESYS snapshot/projection assertions | `NOT_RUN` |
| `REQ-024`, `VER-016` | `R02-assert-count-copy` | test invocations with counts 1,4,2 + branch case | final/legacy `NumberOfAsserts=4`; branch-only example=1 | snapshot test | `NOT_RUN` |
| `REQ-025`, `VER-017` | `R03-log-plain-format` | no `%s`, one `%s`, long message | all emitted; substitution first occurrence; long chunks left-to-right | log capture | `NOT_RUN` |
| `REQ-026`, `VER-018` | `R04-log-extended` | flag true/false mixed result | false suppresses verbose only; failure/framework/summary/report failure remain | log capture | `NOT_RUN` |
| `REQ-027`, `VER-019` | `R05-xml-escape` | names/messages containing `& < > " '`; UTF-8 non-ASCII; legacy non-ASCII for claimed legacy profile; malformed UTF-8 where constructible | parser-valid UTF-8; text round-trips under the bound source encoding; malformed/forbidden code points become U+FFFD | current/stage XML + independent parser; record encoding mode | `NOT_RUN` target; host fixture tool supplied |
| `REQ-029`, `VER-020` | `R06-large-stream` | report > 3x configured chunk | full parser-valid XML, exact last testcase/count | target write + host parser | `NOT_RUN` |
| `REQ-030`, `VER-021` | `R07-file-faults` | fail open/write/short-write/flush-error/close | `FAILED`, no success log, no test-truth change | fault injection | `NOT_RUN` |
| `REQ-031` | `R08-invalid-handle-result` | invalid handle/result path | no invalid use; bounded FAILED/log | target/platform harness | `NOT_RUN` |
| `REQ-028` | `R09-count-reconcile-xml` | mixed multi-suite snapshot | root/suite attrs exactly snapshot | independent parser oracle | `NOT_RUN` |
| `REQ-036`, `VER-031` | `R10-currentness-commit` | prior valid `P`; inject at every commit/recovery step | current always prior complete/new complete/absent; never partial; stage ignored | target filesystem observation + parse | `NOT_RUN` |
| `QAS-013` | `R11-restart-topology` | restart at five crash points §7 | recovery topology exactly as stated | target restart test | `NOT_RUN` |
| `REQ-001` | `R12-public-result-compat` | current callers of `I_TestResults`/legacy DUTs | compile without source edits; meanings as documented | PRD-04 cohort | `NOT_RUN` |
| `L-COU03-006` | `R13-snapshot-memory` | accepted snapshot implementation on bound compiler/target at configured maxima | record compiled snapshot `SIZEOF` + relevant application/static memory; full application fits target budget; no silent capacity/field reduction | compiler/memory report + PRD-04 support evidence | `NOT_RUN` |
| `L-COU03-007`, `REQ-030/036` | `R14-path-byte-capacity` | ASCII `P` of 244/245 bytes; UTF-8 `P` of 122/123 × U+00E9 (244/246 bytes) | 244-byte paths produce distinct 255-byte companions; 245/246-byte paths fail before any `Probe/Open/Rename/Delete`; no truncation or aliasing | native path-helper tests + effect spy/fault harness | `NOT_RUN` |

### Host parser fixtures

PRD-04 supplies `tools/verify_xunit.py` and static fixtures so the XML oracle does not trust the PLC writer. PRD-03 implementation tests must parse file bytes from the actual stage/final artifact, not an in-memory string.

### Fault injection rules

A write fault must include both explicit error and a **short write with otherwise nonfatal status** if the target/harness can simulate it; the latter proves the byte-count guard. A commit failure test must fail `stage->P` after a successful `P->backup` and verify restore behavior.

### Author-time results

Contract/source review: `PASS`. The R3 author-time analytical path fixture confirms 122 × U+00E9 is 244 UTF-8 bytes and 123 × U+00E9 is 246 bytes, exposing why character-count `LEN()` cannot be the path-capacity guard. SysFile documentation semantics checked: `PASS` as supporting evidence. Actual target path helper/file semantics, CODESYS compile/runtime, and fresh recipient review: `NOT_RUN`.

## 11. Leaf implementation slices

1. [`COU03-S1-snapshot-log.md`](slices/COU03-S1-snapshot-log.md)
2. [`COU03-S2-xml-stream.md`](slices/COU03-S2-xml-stream.md)
3. [`COU03-S3-publication-commit.md`](slices/COU03-S3-publication-commit.md)

### Reference availability

| Reference | Class | Status/gate |
|---|---|---|
| R3 architecture/source | `SUPPLIED_WITH_PRD` | present |
| reporting contract | `SUPPLIED_WITH_PRD` | present |
| active repo/target filesystem | dispatch binding | absent |
| accepted PRD-01/02 implementations | `PRODUCED_BY_PREDECESSOR` | unavailable until accepted |
| S1/S2 outputs | `PRODUCED_BY_PREDECESSOR` | later slices wait |
| canonical snapshot/writer/tests | `CREATED_BY_THIS_SLICE` | exact semantics defined here |
| PRD-04 host parser | same suite supplied artifact, qualification-owned | supplied with this PRD suite; target dispatch must confirm Python/tool access or use equivalent independent parser without changing expected results |

### Context fit

S1 needs result/log objects; S2 XML/writer objects; S3 file adapter/currentness only. The worker should not load assertion internals or execution lifecycle source unless a specific boundary check needs it. Exact model capacity unknown; dispatch fit check required.

### Fresh recipient review

Unavailable in this session. Author-only reconstruction covered all three packets and crash traces but cannot satisfy mandatory freshness. Any fresh reviewer must identify the semantic commit and explain all five restart topologies without author coaching.

### Coverage equality

`O03 = U03 ∪ {L-COU03-001..007}`; covered by §§3–10 and slice packets. PRD-04 owns final integrated acceptance.

## 12. Risks, security, operations, and documentation

| Risk | Trigger | Prevention/detection | Response | Owner/gate |
|---|---|---|---|---|
| false current report | write/commit/restart failure | stage/backup protocol + file-only fault tests | retain/restore prior or absent; FAILED | PRD-03/04 `VER-031` |
| silent truncated report | whole buffer or short write | bounded streaming + exact bytes-written guard + parser | FAILED/block release | `VER-020/021` |
| malformed XML or wrong text | metachar/control/encoding mismatch | one encoding-bound decode+escape path; external parser | fix writer; no schema weakening | `VER-019` |
| snapshot does not fit target memory | large fixed maxima + full diagnostic snapshot | compile-time `SIZEOF` + application memory gate | stop affected release/dispatch and return storage representation to architecture owner | `L-COU03-006`, PRD-04 |
| false successful count | legacy inference | canonical terminal-state snapshot | block release | `VER-015` |
| lost diagnostics due verbose flag | flag false | mandatory vs optional log classes | regression test | `VER-018` |
| companion path overflow/alias | UTF-8 path has few characters but too many bytes, or append truncates | byte-count admission + bounded append + pairwise-distinct checks | fail before filesystem effect | `L-COU03-007`, PRD-04 |
| companion file collision | user creates reserved suffix path | docs reserve suffixes; startup treats errors conservatively | publication FAILED rather than overwrite unknown state | PRD-03 |
| filesystem target variation | rename/flush semantics differ | exact PRD-04 matrix/fault tests | no support claim on failing profile | PRD-04 |
| sensitive test values in logs/XML | test data may include secrets | existing user-controlled test environment; first-failure-only detail and no raw history | document exposure; caller avoids secrets | release docs |

Operations: xUnit failure must be visible in Device Log. A leftover stage/backup topology should be diagnosable with path + operation/error code, but log content stays bounded. No new background service or cleanup daemon is added.

Docs: publish count definitions, report states, reserved companion paths, max final-path **byte** length under current type, no same-run automatic retry, project-bound `STRING` encoding/UTF-8 XML policy, `LogExtendedResults` semantics, snapshot memory requirement, and target support matrix once qualified.

## 13. Implementability matrix

| Dimension | Status | Evidence/section | Remaining gap and owner |
|---|---|---|---|
| Repository or new-project evidence, baseline, and current-state discovery | `PARTIAL` | §2 `SRC-001` | active repo/target absent |
| Architecture binding, allocated scope, delegated design, and approval gates | `PASS` | §1 | `OPEN-COU-003` closed as delegated design |
| Target maturity, operating limits, and permitted claims | `PASS` | §§1,3,8 | no power-loss/release claim |
| Source precedence, design authority, and decision closure | `PASS` | §1 | None |
| Outcome, scope, non-goals, and ownership | `PASS` | §3 | None |
| Target worker, context fit, and bounded local choices | `PARTIAL` | §§1,11 | exact worker/access/capacity absent |
| Interfaces and field-level data contracts | `PASS` | §4 + reporting contract | None |
| Canonical producer/recomputation/verifier closure | `PASS` | §5 | None |
| Cross-artifact admission and consistency where required | `PASS` | §§5,7 | snapshot validity + file topology/commit rules fixed |
| Non-circular bootstrap, staging, and migration | `PASS` | §6 | waits on predecessors/repo but no design cycle |
| State/effect/transaction/recovery semantics | `PASS` | §7 + contract | None |
| Source/build/install/runtime/platform closure | `PARTIAL` | §8 | actual repo/tool/runtime/filesystem qualification absent |
| Observed capabilities and filesystem boundaries | `PARTIAL` | §§2,8 | APIs documented; target behavior untested |
| Integration invalidation and requalification | `PASS` | §9 | None |
| Author-set acceptance rules and schema-valid adversarial cases | `PASS` | §10 | execution future |
| Supplied artifacts, reference availability, and author-time validation | `PASS` | §§2,4,10,11 | architecture/source/contract present |
| Leaf slices, file ownership, sequencing, and dispatch gates | `PARTIAL` | §11 | active repo/predecessors absent; all `NOT_READY` |
| Worker-facing handoffs and fresh-context recipient review | `PARTIAL` | §11 | fresh review unavailable |
| Set-equal allocated/local obligation coverage and cross-PRD acceptance ownership | `PASS` | §§3,10,11 | PRD-04 final owner retained |
| Open facts, decisions, assumptions, and late-bound values | `PASS` | §1 | no open semantic choice; target/repo are explicit gates |
| Security, operations, rollout, and documentation | `PASS` | §12 | None at design stage |

**Overall:** `PARTIAL`. The reporting/currentness design is complete, but repo/target-specific evidence and mandatory fresh-recipient review remain absent.

**Implementation-ready: no.** PRD is `CANDIDATE`; architecture is approved. All slices are `NOT_READY`. No target xUnit support, implementation correctness, or release acceptance has been established.
