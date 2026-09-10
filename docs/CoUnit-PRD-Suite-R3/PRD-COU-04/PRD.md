# PRD-COU-04 — Regression, Compatibility, and Integrated Qualification

## 1. Status and decision summary

**Assignment:** `PRD-COU-04`  
**Architecture:** `COUNIT-ARCH-R3` / `2026-09-09-r3` — `APPROVED`.  
**PRD revision:** `PRD-COU-04-R3` / `2026-09-09`.  
**PRD status:** `PARTIAL`.  
**PRD approval:** `CANDIDATE`.  
**Implementation-ready:** **no**.

The detailed qualification design, fixtures, host XML oracle, runtime-matrix contract, defect-to-verification map, and worker slices are complete. This PRD remains `PARTIAL` because no active implementation repository/candidate or native CODESYS toolchain/target has been bound, no real downstream compatibility project has been supplied, and the mandatory fresh-context recipient-consumption review has not run. Those gaps do not reopen R3 product semantics, but they prevent dispatch and the required PRD-stage review gate.

**Outcome.** Provide repeatable evidence that the repaired CoUnit library preserves public source compatibility, fixes the inherited defects, obeys all R3 contracts through integrated scenarios, and claims runtime support only for exact compiler/runtime environments actually qualified. Target maturity is `PRODUCTION_INTENDED` for test/development use; no production-control validation or release approval is performed by this PRD.

**Territory contribution.** `CAP-COU-04`; allocated production requirement `REQ-COU-032`; final integrated verification owner for `REQ-COU-001..037` without taking their implementation ownership from PRD-01/02/03.

**Target worker.** Conservative implementation/qualification worker: can navigate declared files, author CODESYS tests, run a bound CODESYS toolchain and target, run supplied host checks where available, and record exact evidence. It may choose private fixture/test names and equivalent harness layout, but may not change expected semantics, weaken an oracle, infer support from an untested target, or grant release approval.

### Governing sources and precedence

1. `../architecture/` exact R3 package and its accepted decisions/contracts.
2. `../architecture/sources/CoUnitPlaintextExport.zip` (`SRC-001`, SHA-256 `458aab0070f01c7751f63bd7b0980ce7dc260a9607731646a900afedef1c6d48`) for existing-source observations.
3. Accepted implementation outputs of PRD-01/02/03 once they exist; code is evidence of the candidate, not authority to change R3.
4. This PRD's detailed qualification choices, within R3 delegation.
5. Supporting current CODESYS API documentation recorded in `../review/platform-api-evidence.md`; actual target behavior remains subject to native qualification.

### Detailed decisions made here

| ID | Decision | Origin/status | Authority basis | Owner | Acceptance |
|---|---|---|---|---|---|
| `DD-COU04-001` | Runtime support is recorded as exact candidate/compiler/runtime matrix rows; only rows whose required checks pass may be marked `SUPPORTED`. | newly selected `ACTIVE_DELEGATED` | R3 PRD-04 qualification-layout/runtime-matrix delegation | PRD-04 | `VER-COU-025` |
| `DD-COU04-002` | `VER-COU-023` needs at least one real downstream current CoUnit project compiled against the accepted candidate with no normal test-source edits; synthetic/generated projects are supplemental only. | newly selected `ACTIVE_DELEGATED` | R3 public-compatibility qualification delegation | PRD-04 | `REQ-COU-001`, `VER-COU-023` |
| `DD-COU04-003` | Host xUnit verification uses an independent standards XML parser plus separate expected logical results; the PLC publisher's own success flag is never its only oracle. | derived `ACTIVE_DERIVED` | `REQ-COU-027..030`, `VER-COU-019..021` | PRD-04 | supplied `verify_xunit.py` checks |
| `DD-COU04-004` | Final qualification is non-averaging: an applicable `FAIL` blocks its claim; `INCONCLUSIVE`/`NOT_RUN` leave it unqualified; local passes cannot override a failed integrated scenario. | derived `ACTIVE_DERIVED` | R3 verification/readiness rules | PRD-04 | final evidence report |
| `DD-COU04-005` | Existing-source surface inventory is an early drift detector, not proof of source compatibility. Native compilation of a real consumer remains the acceptance oracle. | newly selected `ACTIVE_DELEGATED` | qualification design delegation | PRD-04 | `VER-COU-023` |
| `DD-COU04-006` | A legacy single-byte support row binds an exact mapping identity and mapping-sensitive raw-byte oracle; the broad encoding-mode label alone cannot prove XML text correctness. | derived repair `ACTIVE_DERIVED` | PRD-03 `DD-COU03-003` + `REQ-027/032` | PRD-04 | `VER-COU-019/025`, `L-COU04-005` |

Normative detailed contract: [`contracts/qualification-contract.md`](contracts/qualification-contract.md).

### Open facts and gates

- `OPEN-COU-001` — exact writable implementation repository/path, candidate revision, local changes, CODESYS toolchain and target. Owner: implementation/integration owner. Closure: bind before any slice dispatch. Design effect: none unless actual repo contradicts a fixed assumption; dispatch effect: blocking.
- `OPEN-COU-002` — exact release runtime/compiler matrix. Owner: PRD-04 qualification plus release owner. Closure: execute `VER-COU-025` on accepted candidate. Release effect: blocking for support claims; PRD design effect: none.
- `PRD04-OPEN-001` — at least one real downstream project for `VER-COU-023`. Owner: qualification/release owner. Closure: bind exact project/revision and compile without normal test-source edits. Dispatch effect: COU04-S2/S3 not ready.
- `PRD04-REV-001` — fresh packet-only recipient review for all three slices. Owner: PRD review owner. `NOT_RUN`; PRD readiness effect: keeps overall status `PARTIAL`.

`OPEN-COU-003` was closed by PRD-COU-03 detailed design and is not reopened here.

### Dispatch and acceptance

- `COU04-S1`: `NOT_READY` — waits for accepted candidate/repo/toolchain and fresh recipient review.
- `COU04-S2`: `NOT_READY` — also waits for real downstream compile cohort.
- `COU04-S3`: `NOT_READY` — waits for accepted S1/S2 evidence and actual target matrix access.
- Implementation accepted: **not established**.

## 2. Repository discovery and current state

No active implementation repository or native CODESYS project is supplied. The exact authoring baseline is the R3-packaged plaintext export, which its own README identifies as a source-analysis snapshot rather than a complete `.library` project with all project settings and library references. This is enough to ground existing-source behavior and public declarations, but not to prove current repository layout, native compilation, installation, runtime behavior, or downstream consumer compatibility.

### Existing-source evidence

Observed current baseline facts are recorded in [`../review/source-observations.md`](../review/source-observations.md). Material points for this PRD:

- 423 exported source sections plus the source README are present in `SRC-001`.
- public lifecycle façade includes `RUN`, `RUN_IN_SEQUENCE`, `TEST`, `TEST_FINISHED`, `TEST_FINISHED_NAMED`, and `IS_TEST_FINISHED`;
- 44 public `FB_TestSuite.Assert*` methods exist in the supplied source;
- current runner/assertion/result/xUnit/file paths contain the defect classes R3 assigns to PRD-01/02/03;
- `T_MaxString = STRING(255)` and current configured fixed limits are 32 suites, 2048 tests/suite, and 2048 assertions/suite invocation;
- no real downstream user test project is present in `SRC-001`;
- exact Development System, compiler, controller/runtime, SysFile and CmpIecTask versions for a release target are not supplied.

### Author-supplied current-state projections

- [`qualification/public-api-surface.csv`](qualification/public-api-surface.csv): 60 declaration records mechanically recovered from exact `SRC-001` for the R3-preserved compatibility surface (7 lifecycle/test façade functions, 44 assertion methods, `FB_TestSuite`, `I_TestResults` + 2 methods, 3 legacy result DUTs, `E_AssertionType`, and `GVL_Param_coUnit`), with source-relative paths and SHA-256 values.
- [`qualification/defect-to-verification-map.csv`](qualification/defect-to-verification-map.csv): known source defect/risk classes to R3 VER IDs.

These projections do not replace the source archive or R3 verification inventory.

### Planned implementation locations

The final CODESYS qualification project path is **planned and late-bound at dispatch**, because no active repository is supplied. The worker may create a qualification subtree under the integration owner's chosen test area only after ownership is bound. Planned host-side materials may be copied from this packet into that test area without changing their semantics.

### Evidence table

| Claim | Source kind | Location | Baseline/environment | Result/uncertainty |
|---|---|---|---|---|
| exact architecture and source are available | supplied | `../architecture/` | R3 | verified by package construction/review |
| 60 R3-preserved public compatibility declarations inventoried | derived from source | `qualification/public-api-surface.csv` | exact `SRC-001` | author-time generated; native compile not implied |
| static xUnit parser can accept valid fixture | executed observation | `tools/verify_xunit.py`, `fixtures/xunit/mixed-results.*` | Python host in authoring environment | `PASS`; evidence in `evidence/xunit-positive.txt` |
| parser rejects deliberate semantic defects | executed observation | `fixtures/xunit/bad-count.xml`, `bad-terminal.xml`, `bad-assertions.xml` | same host | all three expected rejections observed for their intended reasons |
| active repo/candidate | unknown future dispatch input | none | none | not bound |
| real downstream compatibility project | unknown future qualification input | none | none | not supplied |
| native target support | future qualification | `qualification/runtime-matrix.csv` | unbound | `NOT_RUN` |

## 3. Outcome, scope, and non-goals

### Obligations

`U04 = {REQ-COU-032}` plus the assigned final-verification contribution for all `REQ-COU-001..037`.

Local obligations introduced within delegation:

- `L-COU04-001` — every runtime/support observation binds exact candidate, contract, toolchain, target, fixture, configuration and evidence.
- `L-COU04-002` — public source compatibility cannot pass without at least one real current downstream consumer compile; source-surface comparison alone is insufficient.
- `L-COU04-003` — qualification status is non-averaging; no failed/inconclusive/unrun required check may be represented as passing support.
- `L-COU04-004` — xUnit semantic acceptance must use an independent parser/oracle that can reject a plausible wrong report.
- `L-COU04-005` — a support row for legacy single-byte `STRING` mode must bind the exact byte-to-Unicode mapping and prove it with a mapping-sensitive raw-byte XML case; the broad mode label alone cannot qualify text semantics.

### Observable success

1. Every `VER-COU-001..032` has an exact semantic test/evidence route and final honest disposition.
2. All `SCN-COU-001..008` are assessed using compatible candidate/contract assumptions.
3. A real downstream current CoUnit project compiles against the candidate without routine call-site edits.
4. xUnit generated by the PLC parses independently, has exact terminal counts/content, and file-currentness faults preserve prior current or absence as specified.
5. Runtime support is stated only for exact matrix rows with evidence; unsupported or unqualified rows remain visible.
6. Final evidence lets the CoUnit release/architecture owner make the acceptance decision without inventing semantics or reconstructing missing bindings.

### In scope

Qualification project/tests, defect-to-VER mapping, static/source API inventory, real-consumer compile cohort, independent report parser/oracles, report/currentness fault harness, runtime/compiler matrix, integrated evidence assembly, support recommendation.

### Non-goals

- implementing PRD-01/02/03 product behavior;
- changing public API or R3 semantics to fit observed code;
- granting release approval;
- proving production-control safety;
- network/distributed CI transport;
- broad filesystem durability under power loss beyond PRD-03's defined semantic commit;
- qualifying unspecified compiler/runtime variants by similarity alone.

### Ownership and boundaries

PRD-01/02/03 own product behavior and local evidence contributions. PRD-04 owns qualification assembly and its own `REQ-COU-032`. The CoUnit release/architecture owner owns final acceptance/support policy. Actual CODESYS target and downstream projects are external qualification inputs, not semantic authorities.

### Fixed versus local choices

Fixed: all R3 requirements/contracts, expected outcomes, report currentness, assertion semantics, task ownership, error categories, compatibility promise, acceptance ownership. Local worker choices: private test-suite names, harness helper layout, fault-injection implementation supported by the bound target, evidence directory names, and equivalent independent XML parser when the supplied Python tool cannot run. Any change to an expected product result or public surface goes to the architecture owner.

## 4. Interfaces and data contracts

Normative qualification contract: [`contracts/qualification-contract.md`](contracts/qualification-contract.md).

### Runtime matrix

Canonical projection: [`qualification/runtime-matrix.csv`](qualification/runtime-matrix.csv). Contract: [`qualification/runtime-matrix-schema.md`](qualification/runtime-matrix-schema.md).

Required fields bind row identity, implementation candidate/hash, Development System/compiler, runtime/controller, OS/architecture, SysFile/CmpIecTask versions, project-wide `STRING` encoding mode, exact legacy byte-mapping identity when that mode applies, fixture/project, the six focused qualification groups, public compatibility, aggregate all-VER coverage, integrated scenarios, support disposition, evidence path and notes. Empty or `UNBOUND` proof-relevant values prohibit a support claim. `legacy_mapping_id` is `N/A` for UTF-8 rows, `UNBOUND` until a legacy mapping is proven, or a stable evidence-backed mapping identifier for a `LEGACY_SINGLE_BYTE` row. Status values are `PASS`, `FAIL`, `INCONCLUSIVE`, `NOT_RUN`; disposition is `SUPPORTED`, `UNSUPPORTED`, `UNQUALIFIED`. `SUPPORTED` is valid only when every required row status is `PASS` and the encoding/mapping identity is valid for that row.

Unknown extra CSV columns may be retained by tooling but cannot override canonical fields. Duplicate row IDs are invalid. A later run on the same environment receives a new unique row or an explicit superseding evidence record; historical failures are not deleted.

### Public API surface inventory

[`qualification/public-api-surface.csv`](qualification/public-api-surface.csv) fields: `symbol`, `kind`, `source_path`, `sha256`, `normalized_declaration`. It is source-evidence only and covers the R3-preserved compatibility surface rather than claiming every exported declaration. Validation checks the required symbol/kind set explicitly, so a missing `TEST_ORDERED` or legacy-result/interface surface cannot be hidden by a matching row count. A declaration text/hash difference triggers review; acceptance remains semantic source compatibility and real native consumer compilation.

### Defect-to-verification projection

[`qualification/defect-to-verification-map.csv`](qualification/defect-to-verification-map.csv) maps source/risk classes to R3 VER IDs, producer and final owner. Architecture verification records remain canonical if any projection disagrees.

### Host xUnit oracle

`tools/verify_xunit.py REPORT [EXPECTED_JSON]`:

- precondition: readable XML file; optional readable JSON expected summary;
- success exit `0`: XML parses, root/suite declared counts equal observed testcase terminal elements, testcase terminal form is valid, and optional expected logical summary matches;
- failure exit `1`: parse, semantic count/terminal or expected-summary mismatch;
- usage exit `2`: bad command syntax;
- no mutation of the input report;
- it does not prove XML schema compatibility beyond parsed structure, publication commit/currentness, filesystem durability, or PLC test truth by itself.

Python availability is not assumed for worker dispatch. A substitute independent parser must preserve these rules and be recorded.

### Real compatibility cohort

A cohort entry is `project identity/revision + candidate identity + Development System/compiler + project/library refs + compile result/log + source-edit declaration`. `PASS` requires no normal test-source edits to satisfy current public calls. Project business/customer data may be redacted from retained evidence, but call-site compile failures and tool versions must remain assessable.

## 5. Canonical production and verification closure

### Producers and consumers

| Artifact/value | Canonical producer | Inputs | Consumer/check | Invalidation |
|---|---|---|---|---|
| candidate product behavior | PRD-01/02/03 implementation | R3 + accepted PRDs | qualification project | any affected semantic/product change |
| architecture expected semantics | R3 | accepted architecture sources | all qualification oracles | authorized architecture successor |
| public source inventory | PRD-04 authoring derivation | exact `SRC-001` | drift check | source baseline change |
| runtime row | COU04-S3 | exact candidate + environment + executed evidence | release owner | candidate/environment binding change |
| xUnit semantic summary | independent host parser | final XML | report acceptance | parser/oracle change or report change |
| final qualification report | COU04-S3 | all compatible evidence | release/architecture owner | any included evidence invalidation |

### Closure rules

- Product code never establishes its own acceptance merely by returning success.
- Expected values/states come from R3/PRDs or separate fixtures, not from a second copy of the implementation algorithm.
- The host xUnit parser independently derives count/result semantics from XML structure.
- Public API source inventory plus a real native consumer compile guards two different compatibility failure modes.
- Runtime support is derived only from exact rows; no unknown target receives support by inference.
- Final integrated report checks compatible candidate/contract bindings before joining local evidence.

No immutable multi-artifact admission system is added. A frozen candidate identity, explicit evidence bindings and pre-execution binding checks are sufficient for this bounded library qualification.

## 6. Bootstrap, staging, and migration

### Stage Q0 — Bind implementation and environment

Prerequisites: active repo/path, accepted PRD-01/02/03 candidate or planned implementation sequence, actual CODESYS tooling, writable test area. Output: exact candidate/toolchain records and qualification-project location. Rollback: none; no product effects. Gate: no `UNBOUND` entry facts needed for the next slice.

### Stage Q1 — Build regression project (`COU04-S1`)

Prerequisite: accepted product candidate and compiler. Output: native test project/suites covering runner/assertion/result-facing semantic cases. Gate: project builds and each planned test maps to R3 VER IDs. A pre-fix product failure is allowed while creating tests if harness validity is independently shown; accepted qualification requires candidate passes later.

### Stage Q2 — Reporting/currentness and compatibility (`COU04-S2`)

Prerequisite: PRD-03 candidate and safe filesystem test area; real downstream project. Outputs: actual xUnit parser runs, currentness fault evidence, compile-cohort evidence. Gate: real project compile status known; host oracle can catch deliberate bad count; fault cases have honest statuses.

### Stage Q3 — Native runtime rows/integrated assembly (`COU04-S3`)

Prerequisite: accepted Q1/Q2 outputs and actual target access. Output: completed matrix rows + final evidence report. Gate: all applicable VER/SCN dispositions explicit and evidence-bound. Release owner then accepts/rejects separately.

### Non-circular bootstrap

The source/architecture and host parser fixtures exist before candidate qualification. The new native regression suite does not qualify itself solely by its own result: harness construction uses R3 semantic oracles, selected deliberate precondition/negative cases, native compiler behavior, and independent report parsing. Final product acceptance waits until actual candidate execution.

No data migration is required. Existing downstream source projects are compile inputs only and must not be bulk rewritten as a compatibility step.

## 7. State, effects, transactions, and recovery

PRD-04 introduces no production runtime state machine. Qualification execution has these operational states:

`UNBOUND -> READY_TO_RUN -> RUNNING -> {PASS, FAIL, INCONCLUSIVE}` per check; `NOT_RUN` describes no execution. A runtime matrix row remains `UNQUALIFIED` until required checks pass.

### Effects

- native compile/import/build effects inside an authorized development/test workspace;
- controller download/start/reinitialize only when explicit test-target permission exists;
- filesystem create/write/delete/rename fault tests only in the designated disposable xUnit test root;
- reading real downstream consumer source/project for compile qualification;
- writing evidence files in the qualification output root.

No production deployment, external messages, purchases, release publication, or production-control effects are authorized by this PRD.

### Fault test containment

Before each report-currentness case, create a known complete final sentinel in the disposable test root and record its bytes/hash. Inject one defined failure. After the case, inspect publisher state, current final bytes/existence, staging/backup names, logs and test truth. Cleanup occurs only after evidence capture. A harness failure that prevents observing the intended fault produces `INCONCLUSIVE`, not a product pass/fail.

### Crash/restart qualification

For `VER-COU-030/031`, stop/reinitialize only the authorized test application/runtime. Capture pre-state and report files first. After restart, verify CoUnit execution begins fresh and report recovery follows PRD-03. Do not infer a power-loss guarantee from an application reinitialize test.

For PRD-03 resource qualification, record the bound project's `UTF8 Encoding for STRING` mode, compiled `SIZEOF` of the final snapshot type, and relevant application/static-memory use. A support row cannot claim xUnit/report support if the required snapshot does not fit the tested application/target memory budget.

## 8. Source, install, runtime, and platform closure

### Supplied files

This packet supplies qualification design, static fixtures, a host verifier and empty runtime-matrix template. It does **not** contain the future repaired CODESYS library, active project, native test project, or a qualified runtime result.

### Native path to prove

`accepted source candidate -> project/library build/import -> downstream/qualification project compile -> target download/run -> canonical CoUnit final state -> Device Log/xUnit final artifact -> independent checks -> evidence report`.

Each executed runtime row records Development System/compiler/controller/runtime/OS-CPU plus SysFile and CmpIecTask versions where available. A missing component version that matters to the tested behavior leaves that support detail unqualified rather than guessed.

### Platform boundaries

PRD-01 uses task APIs/atomic latch; PRD-03 uses SysFile primitives. Supporting docs show needed API shapes, but `VER-COU-025` must establish actual release-target behavior. PRD-04 does not claim rename atomicity or task-call behavior on an untested target.

### Host tool

`verify_xunit.py` needs a normal Python 3 standard library only. Its availability is checked at dispatch; if absent, use a bound independent XML parser with the same oracle. No package installation is required by the supplied script.

### CI/release

CI integration is optional until a project-specific CI path is bound. The required behavior is the same: run qualified native tests, archive exact evidence, independently parse xUnit, and fail the candidate on any required failed check. Release notes must list qualified exact environments and any unqualified/unsupported rows.

## 9. Integration, invalidation, and requalification

Material boundaries under this PRD:

- public caller ↔ CoUnit façade (`IF-COU-001`);
- runner ↔ suite/test state (`IF-COU-002`);
- suite/test ↔ assertion engine (`IF-COU-003`);
- execution ↔ final result/log publishers (`IF-COU-004`);
- publisher ↔ filesystem/external report consumer (`IF-COU-005`);
- CoUnit ↔ CODESYS task/project/file/log platform adapter (`ISC-COU-004`).

Qualification must inspect both sides of each boundary under the same accepted candidate. Provider-local passes cannot supply a missing consumer or currentness result.

### Change map

`CON-COU04-001 §8` is normative. In short:

- PRD-01 semantic/public changes re-run lifecycle/capacity/task cases and affected integrated scenarios;
- PRD-02 changes re-run assertion cases, branch/count/first-failure and any result projections touched;
- PRD-03 changes re-run snapshot/log/XML/file/currentness plus report/restart scenarios;
- compiler/runtime/platform changes create/re-run target rows, including the APIs they affect;
- public declaration changes always reopen source-compatibility qualification;
- evidence-format-only edits do not invalidate product tests when source/candidate/contracts remain identical.

### Integration order and final ownership

PRD-01 and PRD-02 may implement independently where their fixed contract permits; PRD-03 consumes their accepted state/count outputs. PRD-04 qualification uses actual accepted outputs from all three. PRD-04 owns evidence assembly; CoUnit release/architecture owner owns final integrated acceptance.

Mixed-revision evidence is rejected unless an explicit unaffected-scope argument proves the observed property is identical under the final candidate.

## 10. Test and evidence plan

Architecture `verification-and-readiness.md` defines the exact semantic oracle for `VER-COU-001..032`; this PRD fixes execution grouping, evidence binding and qualification ownership without weakening them.

| IDs | Exact input/precondition | Expected result / prohibited effect | Method/evidence | Owner | Current status |
|---|---|---|---|---|---|
| `VER-001..003` | configured max and max+1 suite/test/assertion operations | max works; max+1 framework error before bounded write/count mutation | native capacity suites; state snapshots | S1 / PRD-04 | `NOT_RUN` |
| `VER-004..007` | zero/one/many runners, sequence+delay, skipped positions, named-finish mismatch | finite truthful termination; no skipped block; no current-test corruption | native lifecycle suites | S1 | `NOT_RUN` |
| `VER-008` | >=10,000 accepted test invocations with changing assertion values | constant bookkeeping, no history growth, correct truth | native long-run suite + state observation | S1 | `NOT_RUN` |
| `VER-009` | one failing case per public assertion family | exact `E_AssertionType` | native assertion matrix from public map | S1 | `NOT_RUN` |
| `VER-010` | STRING→REAL TcUnit #237-style sequence | no stale union reinterpretation/runtime exception | native regression | S1 | `NOT_RUN` |
| `VER-011` | REAL/LREAL NaN/Inf/negative/NaN delta matrix | PRD-02 defined outcomes; no unsafe exception | native values constructed on target | S1 | `NOT_RUN` |
| `VER-012` | long STRING/WSTRING + ANY mismatch/null/size cases | bounded compare/rejection; no overwrite/deref fault | native guarded fixtures | S1 | `NOT_RUN` |
| `VER-013` | same-type/equal-size user-defined samples equal/different | exact bytewise representation contract | native representation fixtures | S1 | `NOT_RUN` |
| `VER-014` | first fail then distinct later fail | all stored first-failure fields remain first event; later assertion executes | native two-failure case | S1 | `NOT_RUN` |
| `VER-015/016` | pass/fail/skip/error mixture; 0/1/many plus branch-changing scans | reconciled totals; max-per-single-invocation count | native run + final snapshot + report compare | S1/S2 | `NOT_RUN` |
| `VER-017/018` | plain/substituted logs; extended TRUE/FALSE | full plain text retained; only optional verbosity changes | Device Log capture | S2 | `NOT_RUN` |
| `VER-019` | dynamic XML metachars, invalid-byte policy, and mapping-sensitive legacy raw bytes | parser accepts; decoded logical content matches an external mapping oracle; a legacy row proves at least one mapping-sensitive byte and records the exact mapping ID | PLC output + independent parser + retained mapping evidence | S2 | static parser fixture `PASS`; PLC output `NOT_RUN` |
| `VER-020` | XML larger than configured chunk | complete parseable file, exact counts, no truncation | native large run + parser | S2 | `NOT_RUN` |
| `VER-021` | one controlled file failure at each target-supported pre-commit point | publisher `FAILED`; no success banner; test truth unchanged; no partial current | disposable filesystem fault harness | S2 | `NOT_RUN` |
| `L-COU03-007` | path byte-capacity boundary: ASCII 244/245 bytes and UTF-8 122/123 × U+00E9 | 244-byte path accepted with exact distinct 255-byte companions; over-limit paths rejected before any filesystem effect | native path-helper/effect-spy case | S2 | `NOT_RUN` |
| `VER-022` | foreign task call during active owner run | framework error observed by owner; no foreign complex-state mutation | two-task native project | S1 | `NOT_RUN` |
| `VER-023` | real current downstream CoUnit project + accepted candidate | compiles with no normal test-source edits | native compiler; retained log | S2 | `NOT_RUN` |
| `VER-024` | exact-source inherited regression set | all applicable cases pass | S1/S2 regression corpus | S1/S2 | `NOT_RUN` |
| `VER-025` | exact candidate on exact compiler/runtime rows | only evidence-complete passing rows become `SUPPORTED` | runtime matrix | S3/release owner | `NOT_RUN` |
| `VER-026` | invalid runner context/run-mode switch | deterministic framework error; unrelated state unchanged | native lifecycle suite | S1 | `NOT_RUN` |
| `VER-027` | failed/null task/project lookups through controllable seam or target-supported fault | bounded error; no bad dereference | native platform case | S1 | `NOT_RUN` |
| `VER-028` | whitespace/disabled case/duplicate/conflicting names | one canonical identity and required diagnostics/state | native name table | S1 | `NOT_RUN` |
| `VER-029` | abort/framework error while tests remain open | unfinished tests not successful; final snapshot reconciles | native fault-finalization case | S1/S2 | `NOT_RUN` |
| `VER-030` | interrupt open run then application/library reinitialize | new execution begins fresh at `IDLE`; prior run state absent | native restart case | S1 | `NOT_RUN` |
| `VER-031` | prior complete report; fail after stage bytes; reinitialize mid-write | prior complete current or no current; partial staging never current | S2 currentness harness | S2 | `NOT_RUN` |
| `VER-032` | scan1 A ordinal1 pass; scan2 branch B ordinal1 fail | B executes/fails; no identity entry; final count=1 | native branch fixture | S1 | `NOT_RUN` |

### Local-obligation evidence

- `L-COU04-001`: matrix/evidence binding checks in S3.
- `L-COU04-002`: real project cohort in S2 / `VER-023`.
- `L-COU04-003`: final report status computation in S3 / `VER-025`.
- `L-COU04-004`: supplied independent parser positive control plus deliberate bad-count, multiple-terminal, and negative-assertion-count rejections; actual PLC reports later in S2.
- `L-COU04-005`: S2/S3 bind `legacy_mapping_id`; a legacy-support row must include mapping-sensitive raw-byte evidence whose expected Unicode value comes from retained compiler/runtime mapping evidence, not from the PLC converter.

### Author-time executed checks

From package root:

```text
python PRD-COU-04/tools/verify_xunit.py PRD-COU-04/fixtures/xunit/mixed-results.xml PRD-COU-04/fixtures/xunit/mixed-results.expected.json
```

Observed `PASS` in this authoring environment; output is `evidence/xunit-positive.txt`.

Negative controls:

```text
python PRD-COU-04/tools/verify_xunit.py PRD-COU-04/fixtures/xunit/bad-count.xml
python PRD-COU-04/tools/verify_xunit.py PRD-COU-04/fixtures/xunit/bad-terminal.xml
python PRD-COU-04/tools/verify_xunit.py PRD-COU-04/fixtures/xunit/bad-assertions.xml
```

A nonzero exit was observed for each: root count mismatch, multiple terminal result children, and negative `assertions`, respectively. This establishes the supplied host oracle can reject those three plausible defects. It does not prove future PLC output.

Native commands cannot be fixed until repository/toolchain binding. The worker must record the exact command or IDE action, working directory/project, tool version, target, allowed effects and log path before execution rather than inventing a generic CLI.

## 11. Leaf implementation slices

Detailed worker packets:

1. [`slices/COU04-S1-qualification-project.md`](slices/COU04-S1-qualification-project.md) — native regression project/corpus.
2. [`slices/COU04-S2-report-compatibility.md`](slices/COU04-S2-report-compatibility.md) — report/currentness harness + real compatibility cohort.
3. [`slices/COU04-S3-runtime-integrated-acceptance.md`](slices/COU04-S3-runtime-integrated-acceptance.md) — target matrix + integrated evidence assembly.

### Reference availability

| Reference | Class | Availability/gate |
|---|---|---|
| R3 package, exact source | `SUPPLIED_WITH_PRD` | present under `../architecture`; source identity already checked upstream |
| qualification contract/map/matrix/host fixtures | `SUPPLIED_WITH_PRD` | present; host fixtures author-time checked |
| accepted repaired CoUnit candidate | `PRODUCED_BY_PREDECESSOR` | not available until PRD-01/02/03 implementation acceptance/integration |
| native qualification project | `CREATED_BY_THIS_SLICE` | S1 output |
| actual PLC xUnit/fault evidence | `CREATED_BY_THIS_SLICE` | S2 output after candidate/target binding |
| real downstream compatibility project | `EXISTING` | must be bound before S2 acceptance; currently unavailable |
| completed runtime rows/final evidence report | `CREATED_BY_THIS_SLICE` | S3 output |
| CODESYS tools/targets | external provision | must be bound with exact version/access before dispatch |

### Context fit

Each slice packet is intended to be read with one local contract and exact R3 verification sections, not the whole source/archive at once. Read-now material is roughly one worker packet + relevant PRD sections + one producer contract. Source/export details are retrieve-for-check. Historical architecture review is background. No model context capacity is supplied, so dispatch must verify the selected worker can hold its read-now set plus code/test output reserve; no invented token limit is claimed.

### Dispatch gates

All three are currently `NOT_READY`. The packet's design is conditional and complete enough to assess, but implementation dispatch needs the missing repository/toolchain/access and fresh recipient gate. S2 also needs a real consumer; S3 needs accepted S1/S2 outputs.

### Traceability set equality

`O04 = {REQ-COU-032, L-COU04-001, L-COU04-002, L-COU04-003, L-COU04-004, L-COU04-005}` for this PRD's own production/local obligations, plus its assigned final-verification contribution over `REQ-COU-001..037`.

Coverage:

- `REQ-COU-032` -> `VER-COU-025` -> S3 -> runtime matrix -> release-owner gate.
- `L-COU04-001` -> S3 binding validation -> final evidence report.
- `L-COU04-002` -> `VER-COU-023` -> S2 compile evidence.
- `L-COU04-003` -> S3 non-averaging disposition -> final report/release recommendation.
- `L-COU04-004` -> S2 independent parser -> actual xUnit evidence; author-time static positive/negative control supplied.
- `L-COU04-005` -> S2 mapping-sensitive raw-byte case + S3 mapping-bound runtime row -> `VER-019/025` support evidence.

All architecture requirements `REQ-COU-001..037` retain their producing PRD ownership and map to `VER-COU-001..032` in the canonical architecture verification record; S1/S2/S3 cover the final qualification contribution without redefining those requirements.

## 12. Risks, security, operations, and documentation

| Risk | Trigger | Prevention/detection | Response | Owner/evidence |
|---|---|---|---|---|
| false support claim | passing one environment and generalizing | exact runtime rows; non-averaging rule | bound claim to passing row; mark others unqualified | S3 / release owner |
| compatibility false positive | synthetic test compiles but real project breaks | mandatory real downstream cohort | fail `VER-023`; route public change | S2 / architecture owner |
| harness proves itself | product success flag used as oracle | independent expected states/parser/negative controls | `INCONCLUSIVE` until independent oracle exists | PRD-04 |
| fault test damages real data | wrong report root/target | disposable test root + explicit permission + sentinel prestate | stop, preserve evidence, restore authorized test state | S2 |
| mixed candidate evidence | code changes between runs | bind candidate hash/revision per evidence | invalidate affected set and rerun | S3 |
| unsupported platform API behavior | rename/flush/task APIs differ | native matrix/fault checks | mark row unsupported/unqualified; architecture change only if support is required | PRD-04/release owner |
| hidden test-source edits | compatibility project patched to compile | source-edit declaration + diff/revision evidence | fail compatibility claim | S2 |
| stale staged report mistaken current | restart/fault path defect | final-path sentinel + file inspection | fail `VER-031`; no release | S2 |
| UTF-8 path overflow aliases/truncates companions | character count used as byte-capacity proof | PRD-03 byte-boundary fixtures + no-effect spy | fail reporting/currentness qualification | S2 |
| wrong legacy XML mapping passes broad-mode test | `LEGACY_SINGLE_BYTE` recorded without exact mapping-sensitive proof | bind mapping ID + external mapping evidence + raw-byte case | row remains `UNQUALIFIED`; fix converter/evidence | S2/S3 |

Qualification logs may contain source/project paths and test names. Do not put credentials or unrelated customer data into evidence. Redact business content where needed while retaining technical facts needed to reproduce the result. Retention follows the repository/release policy bound at dispatch; none is invented here.

Required docs at implementation close: updated CoUnit release notes, supported runtime matrix, compatibility notes when any source surface changed, and troubleshooting for xUnit publication failures/recovery. Product docs remain owned by the integration/release owner.

No new permanent service, registry, database, or workflow engine is introduced.

## 13. Implementability matrix

| Dimension | Status | Evidence/section | Remaining gap and owner |
|---|---|---|---|
| Repository or new-project evidence, baseline, and current-state discovery | PARTIAL | §2; exact source snapshot inspected | active implementation repo/candidate/toolchain unbound — integration owner |
| Architecture binding, allocated scope, delegated design, and approval gates | PASS | §§1,3; R3 assignment | None — R3 approved and delegation explicit |
| Target maturity, operating limits, and permitted claims | PASS | §§1,3,8 | None — release claims remain evidence-bound |
| Source precedence, design authority, and decision closure | PASS | §1 | None — no shared semantic decision left open |
| Outcome, scope, non-goals, and ownership | PASS | §3 | None |
| Target worker, context fit, and bounded local choices | PARTIAL | §§1,11 | worker/tool capacity/access not yet bound — dispatch owner |
| Interfaces and field-level data contracts | PASS | §4; `CON-COU04-001` | None |
| Canonical producer/recomputation/verifier closure | PASS | §5 | None at design stage |
| Cross-artifact admission and consistency where required | PASS | §§5,9 | None — exact binding/check rule supplied; no larger mechanism required |
| Non-circular bootstrap, staging, and migration | PASS | §6 | None — execution waits on real prerequisites |
| State/effect/transaction/recovery semantics | PASS | §7 | None for qualification effects; native results are future tests |
| Source/build/install/runtime/platform closure | PARTIAL | §8 | actual repository/install/runtime route not bound — integration owner |
| Observed capabilities and filesystem boundaries | PARTIAL | §§2,7,8 | target SysFile/task behavior not yet observed — S2/S3 |
| Integration invalidation and requalification | PASS | §9; contract §8 | None |
| Author-set acceptance rules and schema-valid adversarial cases | PASS | §10; positive oracle + three deliberate negative controls + R3 VER oracles | native product executions are future implementation checks, not missing design |
| Supplied artifacts, reference availability, and author-time validation | PASS | §§2,4,10,11 | supplied host artifacts validated; predecessor/target inputs correctly classified future |
| Leaf slices, file ownership, sequencing, and dispatch gates | PASS | §11 + slice files | all currently `NOT_READY` by explicit entry gates |
| Worker-facing handoffs and fresh-context recipient review | PARTIAL | §11; top-level author-only review | mandatory fresh packet-only review `NOT_RUN` — PRD review owner |
| Set-equal allocated/local obligation coverage and cross-PRD acceptance ownership | PASS | §§3,10,11 | None |
| Open facts, decisions, assumptions, and late-bound values | PASS | §1, §§4,11 | open items classified with gates; none changes completed semantic design |
| Security, operations, rollout, and documentation | PASS | §12 | None at design stage; execution permissions remain external gate |

**Overall: `PARTIAL`.**

**Implementation-ready: no.** The qualification design itself is complete within R3 authority, but the PRD cannot be `PASS` until the active candidate/repository/toolchain and worker access are bound and every slice receives the required fresh-context recipient-consumption review. Native runtime evidence, a real downstream compile cohort, and target matrix results are implementation/qualification outputs rather than evidence that can exist at authoring time; their absence keeps slices `NOT_READY` and prevents release acceptance, not the semantic design from being specified.

**Approval:** `CANDIDATE`; R3 architecture is `APPROVED`.  
**Dispatch:** S1/S2/S3 `NOT_READY`.  
**Implementation acceptance:** not established.  
**Release/runtime support:** not established.
