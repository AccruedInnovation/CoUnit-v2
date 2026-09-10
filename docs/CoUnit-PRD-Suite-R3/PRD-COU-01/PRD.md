# PRD-COU-01 — Execution Core and Lifecycle

## 1. Status and decision summary

**Assignment:** `PRD-COU-01`  
**Architecture:** `COUNIT-ARCH-R3` / `2026-09-09-r3` — `APPROVED`; architecture authoring status `READY_FOR_PRD`.  
**PRD revision:** `PRD-COU-01-R2` / `2026-09-09`.  
**PRD status:** `PARTIAL`.  
**PRD approval:** `CANDIDATE`; no implementation/release approval is implied.  
**Implementation-ready:** **no**. The detailed design is closed, but the mandatory fresh-context recipient review has not been obtained and `OPEN-COU-001` leaves the active implementation repository/baseline unbound. All slices are therefore `NOT_READY` for dispatch.

**Outcome.** Repair the CoUnit runner, suite registry, test lifecycle, ordering, finish/query behavior, abort/error finalization, and task binding while preserving the normal CoUnit test-authoring API. One runner owns execution; one task owns each run; all fixed storage is guarded before write; tests have stable canonical identity and explicit terminal states; zero/one/many suites terminate in normal and sequence modes; restart starts a fresh run. Target maturity remains `PRODUCTION_INTENDED` for test/development use, not production control.

**Target worker.** No exact model/tool profile was supplied. Dispatch assumes a conservative worker that can navigate the bound CoUnit repository, edit CODESYS Structured Text and related project objects, run the repository's declared CODESYS compile/test path, and make private coding choices. The worker must not redesign public APIs, lifecycle semantics, task ownership, acceptance rules, or cross-PRD contracts. Context must fit this PRD's slice packet plus its named contract/source objects; the worker need not load the full 423-section export.

### Governing sources and precedence

1. current user/architecture-owner approval `SRC-020` as recorded in R3;
2. `COUNIT-ARCH-R3`: `architecture-baseline.md`, `decisions.md`, `shared-contracts.md`, `verification-and-readiness.md`, and this PRD assignment;
3. exact source snapshot `SRC-001` at `../architecture/sources/CoUnitPlaintextExport.zip` as evidence of current CoUnit 1.2.0.3 behavior, not authority to override R3;
4. current CODESYS API documentation as supporting platform evidence; exact target qualification remains PRD-04 work.

### Fixed architecture

`ADR-COU-001..006`, `008`, `015`; `IF-COU-001/002`; `ISC-COU-001/004`; `SDE-COU-001/002`; allocated `REQ-COU-001..006`, `009..014`, `031`, `033`, `035`. PRD-02 owns assertion semantics and PRD-03 owns final result/publication semantics.

### Detailed decisions made here

| ID | Decision | Origin/status | Authority | Owner | Acceptance link |
|---|---|---|---|---|---|
| `DD-COU01-001` | A foreign task may only set one atomic `DWORD` cross-task violation latch with `TEST_AND_SET`; only the bound task mutates complex runner/test state or accepts the framework error. | newly selected, `ACTIVE_DELEGATED` | `DELEGATED_AUTHORITY`, PRD-01 private helper/task-binding delegation | PRD-01 | `VER-COU-022`, `QAS-COU-010` |
| `DD-COU01-002` | Canonical private run/test records and counters use explicit enums/state plus wide internal counters; legacy/global fields, when retained, are projections and never a second authority. | newly selected, `ACTIVE_DELEGATED` | same | PRD-01 | `VER-COU-001/002/004..007/029/030` |
| `DD-COU01-003` | Duplicate definition means the same canonical test appears twice in one accepted runner epoch; one occurrence in each later epoch is normal multi-scan continuation. | derived from `ADR-COU-005/006`, `ACTIVE_DERIVED` | inherited R3 authority | architecture owner | `VER-COU-028` |
| `DD-COU01-004` | Sequence delay applies only between terminal suite N and first invocation of suite N+1; never before suite 1 or after final suite. | newly selected, `ACTIVE_DELEGATED` | sequence elaboration | PRD-01 | `VER-COU-005`, `QAS-COU-003` |

Full normative behavior is in [`contracts/execution-core-contract.md`](contracts/execution-core-contract.md).

### Open items

| ID | Class | Owner / closure | Readiness effect |
|---|---|---|---|
| `OPEN-COU-001` | implementation-stage binding | implementation owner supplies active repository/path, storage form, branch/commit/local changes, CODESYS/compiler/library baseline and writable scope before dispatch | does not change design; all slices `NOT_READY` until closed |
| `PRD01-REV-001` | required review evidence | PRD owner obtains fresh-context packet-only consumption review for all slices after repository binding; repair any defects and recheck | keeps PRD `PARTIAL`; prevents implementation-ready claim |

No unresolved semantic decision remains within PRD-01 authority.

### Slice status

| Slice | Status | Decisive gate |
|---|---|---|
| `COU01-S1` runner/task ownership | `NOT_READY` | active repository/toolchain binding absent |
| `COU01-S2` test lifecycle | `NOT_READY` | repository absent; predecessor `S1` not accepted |
| `COU01-S3` integration | `NOT_READY` | repository absent; `S1/S2` not accepted |

Implementation acceptance: **not established**.

## 2. Repository discovery and current state

There is no active implementation repository/path in the supplied assignment. The authoritative existing-system evidence for authoring is the digest-bound CoUnit 1.2.0.3 plaintext export in R3. Its README states that it is a source-analysis snapshot and does not carry the complete native `.library` project settings/library references. The PRD therefore does not invent a Git commit, build command, writable directory, or currently installed CODESYS version.

### Current execution path observed in `SRC-001`

`RUN()`/`RUN_IN_SEQUENCE()` call methods on global `GVL_coUnit.coUnitRunner`; the runner reads global registered suite pointers, invokes suite FBs, asks each suite whether tests are finished, then continuously advances result/log/xUnit objects. Public `TEST*` functions rely on global current-suite/current-name state. `FB_TestSuite` stores fixed arrays of tests, duplicate/cycle bookkeeping, and assertion tracker FBs.

The baseline uses task cycle count inside test registration to decide whether a name was repeated “this cycle,” and `GetCurTaskInfo` obtains CmpIecTask data. R3 replaces runtime cycle count as semantic lifecycle identity with a runner-owned epoch. The current sequence runner and all-suites runner both derive completion using transient counters rather than explicit run state.

### Repository/source evidence

| Claim | Source kind | Source path/symbol | Baseline | Result / limit |
|---|---|---|---|---|
| Runner invokes registered suites and continuously progresses result/log/xUnit helpers. | existing source | `POUs/FB_coUnitRunner/RunTestSuiteTests/*.exp`, `RunTestSuiteTestsInSequence/*.exp` | `SRC-001` / CoUnit 1.2.0.3 | observed in source; no runtime execution performed |
| Suite has fixed test array, cycle-index duplicate tracking, assertion trackers and `FirstCycle`. | existing source | `POUs/FB_TestSuite/FB_TestSuite.DEC.exp` | same | observed |
| Name registration trims and detects leading `disabled_`; duplicate identity uses task cycle count. | existing source | `FB_TestSuite/AddTest/AddTest.IMP.exp` | same | observed |
| Named finish/current query traverse global/current suite state. | existing source | public `TEST_FINISHED_NAMED`, `IS_TEST_FINISHED`, `TEST`, `TEST_ORDERED` | same | observed; current pointer/error assumptions are part of repair |
| Current task helper can dereference task info after fallible calls. | existing source | `Support/POUs/GetCurTaskInfo/GetCurTaskInfo.IMP.exp` | same | observed; exact target API behavior remains qualification work |
| Configured limits are fixed at source level. | existing source | `GVLs/GVL_Param_coUnit/GVL_Param_coUnit.DEC.exp` | same | suite 32, tests 2048, assertions 2048 in snapshot |
| `TEST_AND_SET(DWORD)` is atomic across tasks/cores. | supporting platform docs | CODESYS operator docs, recorded in `../review/platform-api-evidence.md` | docs read 2026-09-09 | supports private latch mechanism; target compiler still must compile it |
| Active repo, compiler/runtime version, local changes, writable paths and native project form. | unknown implementation input | none supplied | n/a | must be bound before slice dispatch |

Full source observations: [`../review/source-observations.md`](../review/source-observations.md).

### Planned repository binding

At dispatch preflight, record without changing the PRD semantics:

- active CoUnit repository/project path and storage form;
- exact baseline identity plus local changes;
- CODESYS Development System/compiler/library versions needed to open and compile it;
- the repository's build/test entry point and evidence output location;
- mapping from the source-export object names in this PRD to actual repository objects/files;
- writable PRD-01-owned scope and read-only PRD-02/03/04 scope.

If the bound repository has changed shared public signatures/contracts since `SRC-001`, stop and route the contradiction to the architecture owner rather than silently adapting this PRD.

## 3. Outcome, scope, and non-goals

### Upstream obligations

`U01 = {REQ-COU-001..006, REQ-COU-009..014, REQ-COU-031, REQ-COU-033, REQ-COU-035}` with the contribution boundaries stated by R3. No new product requirement is introduced. Local design obligations are:

- `L-COU01-001`: foreign-task detection must not itself perform unsafe complex cross-task mutation;
- `L-COU01-002`: internal counters used before bounds/narrowing must not overflow the configured public limits;
- `L-COU01-003`: sequence delay has one deterministic placement rule.

These refine `REQ-COU-002/004/013/031/033`; they do not enlarge public scope.

### Observable success

- Existing normal CoUnit test source continues to call the same public run/test lifecycle functions.
- One run binds to one task. A call from another task cannot execute a suite or mutate test state; owner task finalizes a framework error.
- Registering the 33rd suite or 2049th test under the current constants changes neither bounded array contents nor committed count.
- A test repeatedly invoked across scans remains one test record; a duplicate declaration inside one accepted epoch is diagnosed once without corrupting peers.
- Disabled tests are terminal `SKIPPED` and never block ordered progress.
- `TEST_FINISHED_NAMED(A)` cannot finish B merely because B is current.
- Both run modes terminate for zero, one and many suites, and abort/framework-error finalization never calls unfinished work passed.
- Reinitialization starts a new `IDLE` run rather than resuming partial state.

### In-scope implementation responsibilities

- `FB_coUnitRunner` run state/disposition/mode/epoch, registry, suite invocation and finalization handoff;
- `FB_TestSuite` test registry/lifecycle/ordered cursor and active invocation context;
- public run/test lifecycle facades and their internal delegation;
- CmpIecTask/project-name/task-info adapter calls needed by these flows;
- execution-specific regression fixtures and handoff to PRD-02/03/04.

Exact repository file paths await `OPEN-COU-001`; exact object identities come from `SRC-001` and are fixed by the source map above.

### Non-goals

- no multi-task test execution model; a second task is a fault, not a second owner;
- no assertion comparator/ANY/REAL redesign (`PRD-COU-02`);
- no canonical result snapshot/xUnit implementation (`PRD-COU-03`);
- no runtime support claim or release acceptance (`PRD-COU-04`);
- no production-control task use, durable resume, host service, network service, database, or new public programming model;
- no requirement to retain old internal cycle/assertion tracking data when it is not public compatibility surface.

### Actors and changed boundaries

Test code is the caller; the public facade is the compatibility boundary; runner/suite state is internal authority; PRD-02 consumes active test identity/segment and runner assertion-budget reset; PRD-03 consumes terminal run/suite/test state; PRD-04 consumes exact integrated evidence. The CoUnit architecture owner owns shared contract change; this PRD owns private execution implementation.

## 4. Interfaces and data contracts

The shared public contract is architecture `IF-COU-001`; runner↔suite is `IF-COU-002`. This PRD does not create a new persisted/wire schema. Internal native types are supplied in [`contracts/execution-core-contract.md`](contracts/execution-core-contract.md) and are the machine-checkable/native representation appropriate to this CODESYS-local boundary.

### Public facade behavior

| Entry | Required precondition | Normal effect | Localized misuse | Context-integrity failure |
|---|---|---|---|---|
| `RUN()` | none for first call; same bound task/mode later | binds/progresses all-suites run one scan | n/a | task failure/mismatch or mode mismatch -> framework error path |
| `RUN_IN_SEQUENCE()` | same | binds/progresses sequence run one scan | n/a | same |
| `TEST(name)` | valid active suite invocation | register/find test; establish active test segment; execute only open enabled test | bad/empty name or conflicting redeclaration -> diagnostic/no unrelated mutation | invalid active run/task -> latch/framework error |
| `TEST_ORDERED(name)` | same | same plus order/cursor gate | same | same |
| `TEST_FINISHED()` | valid active test segment | terminalize active test as pass/fail | no executable current test -> no unrelated mutation | task/context integrity loss -> framework error path |
| `TEST_FINISHED_NAMED(name)` | valid active suite | terminalize only named test | unknown/bad name -> no state mutation | task/context integrity loss -> framework error path |
| `IS_TEST_FINISHED(name)` | valid suite to query | returns terminality | unknown/no suite -> `FALSE`, bounded diagnostic as needed | must never dereference invalid pointer |

Compatibility rule: signatures remain byte/source-level as present in the accepted implementation baseline unless the bound repo already contains an approved compatible successor. Unknown extra internal fields are not a compatibility requirement.

### Internal data rules

- `Epoch`: `ULINT`, increment once per accepted owner-task top-level run call, no wrap; first-seen/last-seen test epochs are framework identity only.
- suite/test counts: existing public/config `UINT`, but calculate candidate indices in a wider private type or explicit checked arithmetic before narrowing.
- test state: one semantic enum, mutually exclusive; no independent “finished/skipped/failed” booleans may decide canonical truth.
- active context: valid only inside the runner-owned suite call; cleared on every return/error path.
- first-failure/assertion fields exist in the canonical record but PRD-02 owns writes and semantics.
- task handle is opaque and compared only through supported runtime type/API; never dereference a result pointer before checking it.

### Error precedence

Framework/context integrity outranks abort; abort outranks new test work; localized test misuse never escalates solely because it is a bad name/unknown named finish. Detailed order is normative contract §12.

### Two-conforming-implementations closure

Provider and consumer cannot differ on terminality, canonical name, task ownership, or duplicate meaning because those rules are fixed above. Private helper names and enum numeric values may differ without changing observable behavior.

## 5. Canonical production and verification closure

### Canonical producers

| Value/state | Producer | Inputs | Consumer | Invalidated by |
|---|---|---|---|---|
| bound run task | runner on first valid top-level call | checked current task handle | every mutating facade/helper | reinit/new run |
| run epoch | runner | accepted owner-task top-level call | test duplicate/invocation logic; PRD-02 segment setup | next accepted call increments it |
| suite registry/count | runner registration | valid suite instance + capacity | run modes/result finalization | reinit only |
| canonical test record/name | suite `BeginTest` path | public name + order/disabled form + epoch | finish/query/assert/result | reinit/new library instance |
| ordered cursor | suite terminal transition | ordered records/states | `TEST_ORDERED` | any ordered terminal transition |
| run state/disposition | runner | execution completion, abort or framework error | PRD-03 finalization | terminal only until reinit |
| cross-task violation latch | foreign caller only via atomic set; owner consumes | task mismatch/identity failure | owner-run validation | owner acceptance clears after transition |

No alternate producer may write canonical test state through `GVL_coUnit` compatibility fields.

### Verification independence

Bounds checks use canary/snapshot comparisons around arrays and committed counts, not a producer “success” bit. Cross-task tests verify both the foreign-call immediate state and owner-consumed final state. Completion tests assert terminal state from observable run/suite/test APIs/result handoff rather than repeat the state transition implementation as oracle.

### Closure

Every canonical value above has one producer and a named consumer. No verification method requires the future repaired implementation to certify itself before first compile: the current CODESYS compiler plus source-level/static inspection and external test programs supply the initial checks. PRD-04 owns final integrated qualification.

## 6. Bootstrap, staging, and migration

### Stage E1 — bind implementation baseline

**Prerequisite:** user/implementation owner supplies `OPEN-COU-001`.  
**Output:** exact repo/project path, identity/local changes, CODESYS/toolchain/library baseline, object-path map, writable ownership.  
**Gate:** source/shared-contract comparison finds no unapproved conflict.  
**Rollback:** none; read-only discovery.

### Stage E2 — runner/task core (`COU01-S1`)

Add private states, registry rules, owner task binding, latch, run modes and error/abort transitions while preserving public entry signatures. Existing result/assertion internals may remain temporarily, but they must not be allowed to become alternate lifecycle authority.

**Exit:** execution-core local tests pass; exact active-context interface is recorded for S2/PRD-02.

### Stage E3 — suite/test lifecycle (`COU01-S2`)

Replace cycle-count/parallel-boolean test identity with canonical records, name helper, terminal skip, ordered cursor and target-safe finish/query. Remove core reads of old global current-test authority.

**Exit:** name/registration/order/finish tests pass and active context is stable.

### Stage E4 — execution integration (`COU01-S3`)

Run all execution `VER` contributions on the integrated local candidate. Package exact candidate/evidence for PRD-02/03. Old cycle bookkeeping may be deleted when no accepted public/internal consumer remains.

### Migration rules

- Do not change public call sites in user test source.
- During intermediate buildable states, wrappers may translate old globals/`FB_Test` projections to canonical records; remove translator authority once the canonical path exists.
- No old partial run is migrated. Reinit starts fresh.
- A changed active repo with already-implemented successor behavior requires comparison, not blind overwrite.
- No PRD-02/03 slice may bind to PRD-01 output until S3 acceptance identifies the actual candidate.

## 7. State, effects, transactions, and recovery

The architecture SDE treatment is `CONTRACT`; full state semantics are in the supporting normative contract.

### Run transitions

| From | Trigger/guard | To | Effect/commit | Illegal/failure handling |
|---|---|---|---|---|
| `IDLE` | valid first RUN/sequence + current task | `RUNNING` | bind task/mode, epoch++, begin work | task lookup failure: remain IDLE, diagnostic |
| `RUNNING` | same task/mode next call | `RUNNING` or `BETWEEN_SUITES`/`FINALIZING` | epoch++, invoke allowed suite(s) | mismatch/latch -> `FINALIZING` with framework error |
| `BETWEEN_SUITES` | delay complete, same owner | `RUNNING` | next sequence suite may start | mismatch -> framework error |
| `RUNNING`/`BETWEEN_SUITES` | owner abort | `FINALIZING` | disposition ABORTED; open tests -> ABORTED | framework error already accepted wins |
| any active | owner accepts integrity defect | `FINALIZING` | disposition FRAMEWORK_ERROR; open tests -> ERROR | terminal; no resume |
| `FINALIZING` | result finalization complete | `COMPLETE` | PRD-03 owns snapshot/publisher handoff | publisher failure never changes test truth |
| `COMPLETE` | later run call in same instance | `COMPLETE` | no suite invocation | rerun requires explicit reinit/new instance; no hidden reset |

### Test transitions

`OPEN -> PASSED|FAILED|ABORTED|ERROR`; disabled first registration -> `SKIPPED`. All terminal states are terminal. No transition out of terminal state in a current run.

### Effects and authority

Execution effects are in-memory library state plus diagnostic log calls. No file/network/deployment effect belongs to this PRD. The atomic foreign-task latch is the only cross-task write allowed on the error path. If the owner never runs again after a foreign violation, CoUnit cannot safely finalize from the foreign task; state remains nonterminal until owner execution or application restart. This is the bounded failure mode, preferable to corrupting complex state.

### Recovery

There is no current-run recovery/resume. Application/library reinitialization reconstructs `IDLE`. Diagnostics from a failed run may be lost on reinit; final report persistence is PRD-03. A worker must not add RETAIN/PERSISTENT to “improve” recovery without architecture approval.

## 8. Source, install, runtime, and platform closure

### Required source changes

Exact source-export object families are known; repository paths are not. Once bound, map and edit only the active equivalents of:

- `FB_coUnitRunner` + run/sequence/abort/completion methods;
- `FB_TestSuite` + init/registration/completion/finish/query helpers;
- public `RUN`, `RUN_IN_SEQUENCE`, `TEST`, `TEST_ORDERED`, `TEST_FINISHED`, `TEST_FINISHED_NAMED`, `IS_TEST_FINISHED` implementations as needed to delegate;
- `FB_Test` only as required for compatibility projection;
- `GVL_coUnit` only for runner-owned/projection changes;
- current task helper/platform adapter.

Private DUTs/helpers may be created inside the existing CoUnit library's internal object namespace/folder once repository conventions are known.

### Toolchain/runtime

No exact supported CODESYS/compiler/runtime version is asserted by this PRD. The source snapshot came from CoUnit 1.2.0.3. Target support depends on PRD-04. The worker must bind library namespaces/component versions already used by the repo; do not upgrade dependencies as part of this repair unless required and separately reviewed.

`TEST_AND_SET` is selected because current CODESYS documentation defines an atomic `DWORD` operation across multicore tasks. This PRD does not claim that every historical compiler targeted by CoUnit supports it. If the required release compiler lacks it, stop and route a platform-design issue; do not replace it with a non-atomic Boolean.

### Build/install/runtime path

The source snapshot does not reveal a complete native build/install pipeline. At dispatch, the implementation owner must record the actual path: open/compile the library/project in its current storage form, run the dedicated test application on the qualified target/simulator, and verify downstream source compatibility. PRD-04 owns the release matrix. No workspace-only compile is accepted as proof of installed library behavior if the repository has a packaging/install step.

### Filesystem concerns

None — PRD-01 performs no product filesystem effects. Repository edits occur only inside the implementation workspace granted at dispatch.

## 9. Integration, invalidation, and requalification

### Integration boundaries

- PRD-01 -> PRD-02: active suite/test indices, `ShouldExecuteCurrentTest`, per-segment start that resets invocation ordinal, owner-task validation, suite invocation assertion-budget reset point.
- PRD-01 -> PRD-03: immutable-enough terminal suite/test/run state after execution stops; run disposition distinguishes normal/aborted/framework error.
- PRD-01 -> PRD-04: candidate binding plus execution verification evidence.

### Change invalidation

| Change | Recheck |
|---|---|
| public lifecycle signature/meaning | architecture owner + source compatibility `VER-COU-023` + all PRD consumers |
| task identity/latch mechanism | `VER-COU-022/027`, `QAS-COU-010`, counterpart active-context checks |
| epoch/duplicate/name semantics | `VER-COU-028`, PRD-02 invocation reset, result identity tests |
| suite/test storage layout | bounds tests, PRD-02/03 consumers, final snapshot mapping |
| run terminal/error mapping | normal/sequence/abort/restart integrated tests and PRD-03 final result mapping |
| config limits/type | max/cap+1 tests and any narrowing checks |

Evidence is reusable only when the candidate, R3 contracts, relevant configuration limits, compiler/runtime and platform adapter binding are unchanged for the claim.

### Boundary checks performed at authoring

Analytical review checked public facade↔runner, runner↔suite, and foreign-task↔owner boundaries against R3. The latch design resolves the key cross-task race: two conforming implementations cannot allow a foreign task to write the canonical complex state. Runtime behavior is `NOT_RUN` until implementation.

## 10. Test and evidence plan

The following rows refine upstream `VER` obligations; exact CODESYS test-object paths will be chosen inside the bound repository by PRD-04 conventions. Expected semantics are fixed now.

| Obligation | Case | Input/precondition | Expected / prohibited effect | Method / planned evidence | Owner/status |
|---|---|---|---|---|---|
| `VER-COU-001`, `REQ-004/005` | `T01-suite-cap-plus-one` | register exactly max suites, snapshot registry/count/canaries, attempt one more | framework error; registry/count/canaries unchanged by extra attempt | CODESYS regression test + state snapshot | PRD-01 impl; `NOT_RUN` |
| `VER-COU-002`, `REQ-004/006` | `T02-test-cap-plus-one` | one suite registers max distinct tests then extra | extra test not written/count unchanged; framework error | same | `NOT_RUN` |
| `VER-COU-004`, `REQ-013` | `T03-normal-0-1-many` | zero, one empty/nonempty, several suites incl multi-scan | each reaches `COMPLETE`; each nonterminal suite invoked at most once/top-level call | state trace | `NOT_RUN` |
| `VER-COU-005` | `T04-sequence-0-1-many` | configured 0 and nonzero inter-suite delay | stable order; delay only between terminal suites; final suite completes | trace/time observation | `NOT_RUN` |
| `VER-COU-006` | `T05-ordered-skip` | disabled first/middle/last ordered tests | skipped is terminal; cursor advances; later enabled test runs | test result trace | `NOT_RUN` |
| `VER-COU-007` | `T06-named-finish` | A exists; B current; finish A; then unknown name | A terminal; B unchanged by A/unknown call; no abort | state assertions | `NOT_RUN` |
| `VER-COU-022`, `REQ-002` | `T07-cross-task` | active run bound to task A; invoke facade from B | B performs only atomic latch write; no suite/test mutation; A later finalizes framework error | two-task CODESYS test | `NOT_RUN` |
| `VER-COU-026` | `T08-run-mode-switch` | start ALL, then sequence before terminal | framework error; no further suite invocation | trace | `NOT_RUN` |
| `VER-COU-027`, `REQ-031` | `T09-task-api-failure` | fault/stub supported task lookup failure | no invalid dereference; no unsafe complex mutation; bounded error path | target/platform fault harness | `NOT_RUN` |
| `VER-COU-028` | `T10-name-duplicate` | trim/prefix/case cases; same canonical name twice same epoch; once next epoch | exact name rules; duplicate only same epoch; later epoch normal | CODESYS tests | `NOT_RUN` |
| `VER-COU-029`, `REQ-014/033` | `T11-abort-framework-error` | abort with open tests; separate integrity error with open tests | open -> ABORTED or ERROR, never PASS; framework error precedence | state/result integration | `NOT_RUN` |
| `VER-COU-030`, `REQ-035` | `T12-reinit` | run partially, reinitialize app/library | new state IDLE, no stale active context/epoch resume | target restart test | `NOT_RUN` |
| `REQ-001` contribution | `T13-public-lifecycle-compile` | representative existing source using lifecycle facade | compile without source edits | PRD-04 compatibility cohort | `NOT_RUN` |

Negative cases must satisfy unrelated preconditions so the intended guard is reached. For example, the cap+1 cases first establish a valid owner task/run and valid distinct names; cross-task case first establishes a healthy owner run.

### Author-time checks completed

- source-object existence and current behavior inspected from digest-bound `SRC-001` — `PASS` for source discovery;
- normative state/contract review against R3 — `PASS` analytically;
- target compile/runtime checks — `NOT_RUN`;
- fresh recipient consumption — `NOT_RUN` and required before `PASS`.

## 11. Leaf implementation slices

Canonical worker packets:

1. [`COU01-S1-runner-state.md`](slices/COU01-S1-runner-state.md) — runner state, registry, task ownership/latch.
2. [`COU01-S2-test-lifecycle.md`](slices/COU01-S2-test-lifecycle.md) — test identity/order/finish/query.
3. [`COU01-S3-execution-integration.md`](slices/COU01-S3-execution-integration.md) — integration tests and evidence handoff.

### Reference inventory

| Reference | Class | Availability / gate |
|---|---|---|
| R3 architecture package under `../architecture/` | `SUPPLIED_WITH_PRD` | present, exact accepted baseline |
| R3 source archive | `SUPPLIED_WITH_PRD` | present and digest-bound by architecture validation |
| normative execution contract | `SUPPLIED_WITH_PRD` | present; author-time structural review complete |
| active CoUnit repository/project | external implementation binding; equivalent to architecture `OPEN-COU-001` | absent; required before any slice dispatch |
| accepted `COU01-S1` output | `PRODUCED_BY_PREDECESSOR` | needed for S2; not available yet |
| accepted `COU01-S2` output | `PRODUCED_BY_PREDECESSOR` | needed for S3/PRD-02 integration; not available yet |
| slice-created source/tests | `CREATED_BY_THIS_SLICE` | definitions and acceptance are in slice + §§4/7/10 |

### Context fit

Each implementation slice reads its own packet, the cited subsections of the normative contract/architecture, and a small object family from the source/repo. No slice requires the full PRD suite or entire source export simultaneously. Exact target model capacity is unknown; preflight must verify that the worker can hold the required read-now packet plus retrieved source and working/output reserve. If it cannot, split the **review/retrieval task**, not the runner architecture, unless the owner approves a scope change.

### Mandatory recipient review

No fresh recipient tool/session is available in this authoring context. I performed an author-only reconstruction of all three packets, but it is not valid fresh-context evidence. Before dispatch, a fresh recipient must answer the eight consumption questions from the governing PRD prompt using only each packet and declared repository access. Any substantive repair invalidates freshness for the repaired scope and needs a fresh affected recheck.

### Traceability equality

`O01 = U01 ∪ {L-COU01-001..003}`. Sections 3, 4, 7, 10 and slice packets cover every member. No unrelated architecture requirement is claimed. PRD-04 remains final integrated acceptance owner.

## 12. Risks, security, operations, and documentation

| Risk | Trigger | Prevention/detection | Response | Owner/evidence gate |
|---|---|---|---|---|
| cross-task corruption | public call from second task | checked handle + atomic latch only; two-task test | owner finalizes framework error | PRD-01 / `VER-022` |
| out-of-bounds suite/test write | capacity exhausted | pre-write guards + count commit last + cap+1 tests | framework error/no extra mutation | PRD-01 / `VER-001/002` |
| hang due to completion heuristic | zero/empty/final sequence suite, skip | explicit state/terminal tests | fix lifecycle, never counter workaround | PRD-01 / `VER-004..006` |
| wrong test mutated | duplicate/named finish/current globals | canonical index/name, target-specific finish | localized diagnostic; no unrelated mutation | PRD-01 / `VER-007/028` |
| stale run after restart | app reinit mid-run | no retained current-run state | fresh IDLE | PRD-01/04 / `VER-030` |
| source compatibility regression | facade signature changed | compile cohort | stop release; route compatibility change | PRD-04 / `VER-023` |
| platform API mismatch | older compiler/runtime lacks chosen primitive | bind toolchain before dispatch; PRD-04 matrix | no support claim; route platform issue | PRD-04 |

Diagnostics shall include enough context to identify framework error, test/suite name when safe, and task mismatch reason, but no new unbounded log/event history is required. Existing device-log formatting implementation is PRD-03; PRD-01 only requests bounded diagnostics through that interface.

Documentation changes: update CoUnit internal/developer docs for lifecycle semantics and public docs only where old behavior descriptions conflict (skip, duplicate, named finish, one-task rule, restart). Do not document private enum names as public API.

Security/privacy: no credentials, network data, or personal data are introduced. Correctness and memory/task isolation are the main concerns.

## 13. Implementability matrix

| Dimension | Status | Evidence/section | Remaining gap and owner |
|---|---|---|---|
| Repository or new-project evidence, baseline, and current-state discovery | `PARTIAL` | §2 + digest-bound `SRC-001` source observations | active implementation repo/toolchain/local changes absent — implementation owner |
| Architecture binding, allocated scope, delegated design, and approval gates | `PASS` | §1, R3 assignment | None — R3 approved and scope bound |
| Target maturity, operating limits, and permitted claims | `PASS` | §§1,3 | None — test/development only; no support/release claim |
| Source precedence, design authority, and decision closure | `PASS` | §1 decisions | None — all in-scope semantic choices closed |
| Outcome, scope, non-goals, and ownership | `PASS` | §3 | None |
| Target worker, context fit, and bounded local choices | `PARTIAL` | §§1,11 | exact worker/access/capacity not yet bound; dispatch preflight owner |
| Interfaces and field-level data contracts | `PASS` | §4 + normative contract | None for PRD-01-owned boundaries |
| Canonical producer/recomputation/verifier closure | `PASS` | §5 | runtime evidence is future implementation evidence, not design gap |
| Cross-artifact admission and consistency where required | `PASS` | §5, §9 | None — no multi-file admission effect in this PRD; candidate/evidence binding specified |
| Non-circular bootstrap, staging, and migration | `PASS` | §6 | first dispatch waits on repo binding but path is non-circular |
| State/effect/transaction/recovery semantics | `PASS` | §7 + contract | None |
| Source/build/install/runtime/platform closure | `PARTIAL` | §8 | actual repo build/install path and exact platform versions absent |
| Observed capabilities and filesystem boundaries | `PASS` | §§2,8 | no product filesystem effects; `TEST_AND_SET` support still a dispatch/qualification check |
| Integration invalidation and requalification | `PASS` | §9 | None |
| Author-set acceptance rules and schema-valid adversarial cases | `PASS` | §10 | native tests remain future execution |
| Supplied artifacts, reference availability, and author-time validation | `PASS` | §§2,10,11 | architecture/source/contract/slices present |
| Leaf slices, file ownership, sequencing, and dispatch gates | `PARTIAL` | §11 | repo file mapping absent; all slices `NOT_READY` |
| Worker-facing handoffs and fresh-context recipient review | `PARTIAL` | §11 | mandatory fresh recipient review not available in this session — PRD owner |
| Set-equal allocated/local obligation coverage and cross-PRD acceptance ownership | `PASS` | §§3,10,11 | None; PRD-04 final owner retained |
| Open facts, decisions, assumptions, and late-bound values | `PASS` | §1 | remaining repo/worker bindings are explicit dispatch inputs, not design choices |
| Security, operations, rollout, and documentation | `PASS` | §12 | None at design stage |

**Overall:** `PARTIAL` because required repository-specific author-time/dispatch binding and fresh recipient-consumption evidence are missing. No design-critical shared decision remains.

**Implementation-ready: no.** Architecture approval remains `APPROVED`; this PRD is a `CANDIDATE`. No slice is dispatch-ready. Implementation acceptance, CODESYS runtime correctness, and release support are not established.
