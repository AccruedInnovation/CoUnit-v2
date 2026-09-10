# Verification, Review and Readiness — R3

## 1. Product/architecture verification assertions

The methods below are future implementation/qualification obligations unless the R2/R3 review result column says an analytical or structural check was actually performed. No native CODESYS execution occurred in this review.

| ID | Claim | Method / semantic oracle | Expected evidence | Producing / acceptance owner |
|---|---|---|---|---|
| `VER-COU-001` | Suite capacity cannot overrun | max and max+1 boundary test | no invalid write; deterministic framework error | PRD-01 / PRD-04 |
| `VER-COU-002` | Test capacity cannot overrun | max and max+1 boundary test | no invalid write; deterministic framework error | PRD-01 / PRD-04 |
| `VER-COU-003` | Assertion invocation bookkeeping cannot overflow | execute the configured maximum assertion calls across one suite-body invocation, then attempt one more | max case records correctly; max+1 becomes framework error before either assertion counter or result state updates | PRD-02 / PRD-04 |
| `VER-COU-004` | Normal runner completes | zero/one/many suites, empty and multi-scan | terminal state and exact counts | PRD-01 / PRD-04 |
| `VER-COU-005` | Sequential runner completes | zero/one/many, final suite, nonzero delay | registration order, only intended delay, terminal state | PRD-01 / PRD-04 |
| `VER-COU-006` | Skipped ordered tests do not block | skipped first/middle/last | later enabled tests execute | PRD-01 / PRD-04 |
| `VER-COU-007` | Named finish cannot corrupt current test | A current, finish B, continue A | only B terminal; A context/count preserved | PRD-01 / PRD-04 |
| `VER-COU-008` | Multi-scan assertion state remains bounded | repeat an assertion with changing values for >=10,000 invocations | constant per-test bookkeeping; no assertion-history growth; correct truth | PRD-02 / PRD-04 |
| `VER-COU-009` | Scalar/array assertion type mappings are correct | one failing case per public family | exact `E_AssertionType` | PRD-02 / PRD-04 |
| `VER-COU-010` | STRING→REAL cannot reinterpret old union data | reproduce TcUnit #237 pattern | no runtime exception | PRD-02 / PRD-04 |
| `VER-COU-011` | REAL/LREAL special values are safe | NaN/Inf/NaN-delta/negative-delta matrix | defined outcome; no exception | PRD-02 / PRD-04 |
| `VER-COU-012` | Generic `ANY` string handling is bounded | long STRING/WSTRING and type/size mismatch | no overwrite; exact result | PRD-02 / PRD-04 |
| `VER-COU-013` | Generic user types use bounded representation equality | equal/different same-layout samples | stated bytewise contract | PRD-02 / PRD-04 |
| `VER-COU-014` | First failure is one coherent event | first fail then different later fail | all first-failure fields come from first event | PRD-02 / PRD-04 |
| `VER-COU-015` | Counts reconcile | pass/fail/skip/error mixtures | total equality at suite and run | PRD-03 / PRD-04 |
| `VER-COU-016` | Assertion counts reach result objects | tests with 0/1/many assertions per invocation plus branch-changing multi-scan case | final `NumberOfAsserts` equals maximum executable assertion calls in any single test-body invocation | PRD-03 / PRD-04 |
| `VER-COU-017` | Device Log keeps plain messages | plain and substituted log text | both complete messages appear | PRD-03 / PRD-04 |
| `VER-COU-018` | `LogExtendedResults` is honored | compare TRUE/FALSE | only optional verbosity changes | PRD-03 / PRD-04 |
| `VER-COU-019` | XML inserted text is safe | metacharacters + invalid-code-point policy | standards parser accepts; logical content decodes | PRD-03 / PRD-04 |
| `VER-COU-020` | Large XML streams | result larger than chunk buffer | complete parseable file and exact counts | PRD-03 / PRD-04 |
| `VER-COU-021` | I/O errors are truthful | fail delete/open/write/flush/close/commit where target permits | publication `FAILED`; no success banner; no test-truth rewrite | PRD-03 / PRD-04 |
| `VER-COU-022` | Cross-task misuse is contained | second task calls during active run | framework error; no cross-suite mutation | PRD-01 / PRD-04 |
| `VER-COU-023` | Existing public API source compiles | representative current CoUnit test projects | no normal test-source edits | PRD-04 |
| `VER-COU-024` | Inherited defects stay fixed | regression set from exact CoUnit source plus selected upstream defects | all applicable cases pass | PRD-04 |
| `VER-COU-025` | Runtime support claims are evidence-based | native qualification matrix | exact compiler/runtime versions and results | PRD-04 / release owner |
| `VER-COU-026` | Runner context is sole suite/test execution authority | invalid context and run-mode switch probes | deterministic error; unrelated state unchanged | PRD-01 / PRD-04 |
| `VER-COU-027` | Platform task/project failures cannot become bad dereferences | inject/mock failed lookups | bounded framework error/diagnostic; no dereference fault | PRD-01 / PRD-04 |
| `VER-COU-028` | Canonical names and duplicate rules are deterministic | whitespace, disabled case, duplicate/conflicting shape | one identity and required diagnostic/state | PRD-01 / PRD-04 |
| `VER-COU-029` | Abort/error finalization preserves truth | inject abort/error with open tests | no unfinished success; snapshot reconciles | PRD-01 + PRD-03 / PRD-04 |
| `VER-COU-030` | Reinit cannot resume partial run | interrupt open run, reinitialize, run again | new run begins `IDLE`; prior run state absent | PRD-01 / PRD-04 |
| `VER-COU-031` | External current report cannot become partial | start with complete prior report; fail new publish after bytes written and also reinitialize mid-write | current path/locator still names prior complete artifact or is absent; partial staging is non-current | PRD-03 / PRD-04 |
| `VER-COU-032` | Branch-dependent assertions cannot be suppressed by an old ordinal identity | scan 1: A at ordinal 1 passes; scan 2: different branch B at ordinal 1 fails | B is evaluated and becomes the first failure; no per-assertion identity entry exists; final assertion count is 1 | PRD-02 / PRD-04 |

## 2. Requirement cross-reference

| Requirement | Verification | Producing contribution |
|---|---|---|
| `REQ-COU-001` | `VER-COU-023` | PRD-01 runner/test API; PRD-02 assertion API; PRD-03 result/config API |
| `REQ-COU-002` | `VER-COU-022` | PRD-01 |
| `REQ-COU-003` | `VER-COU-026` | PRD-01 |
| `REQ-COU-004` | `VER-COU-001..003`, `012`, `020`, `027` | PRD-01 suite/test; PRD-02 assertion/de-dup writes |
| `REQ-COU-005` | `VER-COU-001` | PRD-01 |
| `REQ-COU-006` | `VER-COU-002` | PRD-01 |
| `REQ-COU-007` | `VER-COU-003` | PRD-02 |
| `REQ-COU-008` | `VER-COU-008` | PRD-02 |
| `REQ-COU-009` | `VER-COU-007`, `028` | PRD-01 |
| `REQ-COU-010` | `VER-COU-028` | PRD-01 |
| `REQ-COU-011` | `VER-COU-006`, `028` | PRD-01 |
| `REQ-COU-012` | `VER-COU-007` | PRD-01 |
| `REQ-COU-013` | `VER-COU-004`, `005` | PRD-01 |
| `REQ-COU-014` | `VER-COU-029` | PRD-01 |
| `REQ-COU-015` | `VER-COU-008`, `010` | PRD-02 |
| `REQ-COU-016` | `VER-COU-009` | PRD-02 |
| `REQ-COU-017` | `VER-COU-014` | PRD-02 |
| `REQ-COU-018` | `VER-COU-009` | PRD-02 |
| `REQ-COU-019` | `VER-COU-011` | PRD-02 |
| `REQ-COU-020` | `VER-COU-012` | PRD-02 |
| `REQ-COU-021` | `VER-COU-013` | PRD-02 |
| `REQ-COU-022` | `VER-COU-015`, `029` | PRD-03 |
| `REQ-COU-023` | `VER-COU-015`, `023` | PRD-03 |
| `REQ-COU-024` | `VER-COU-016`, `032` | PRD-02 produces max-per-invocation count; PRD-03 projects it |
| `REQ-COU-025` | `VER-COU-017` | PRD-03 |
| `REQ-COU-026` | `VER-COU-018` | PRD-03 |
| `REQ-COU-027` | `VER-COU-019`, `020` | PRD-03 |
| `REQ-COU-028` | `VER-COU-015`, `020` | PRD-03 |
| `REQ-COU-029` | `VER-COU-020` | PRD-03 |
| `REQ-COU-030` | `VER-COU-021`, `031` | PRD-03 |
| `REQ-COU-031` | `VER-COU-027`, `021`, `031` | PRD-01 task/project; PRD-03 file/log |
| `REQ-COU-032` | `VER-COU-025` | PRD-04 |
| `REQ-COU-033` | `VER-COU-022`, `026`, `029` | PRD-01 |
| `REQ-COU-034` | `VER-COU-011..013` | PRD-02 |
| `REQ-COU-035` | `VER-COU-030` | PRD-01 |
| `REQ-COU-036` | `VER-COU-031` | PRD-03 |
| `REQ-COU-037` | `VER-COU-032` | PRD-02 under `ADR-COU-017` |

`PRD-COU-04` is final integrated verification owner for the committed set; it does not own production of the other PRDs' behavior.

## 3. Integrated acceptance scenarios

### `SCN-COU-001` — Multi-scan all-suite run
Two suites run under `RUN()`: delayed pass, failure, disabled case; one assertion repeats with changing values. Require bounded state, truthful terminal categories, reconciled final snapshot, and publisher agreement.

### `SCN-COU-002` — Ordered sequence with skip
Ordered A, disabled B, C, D. Require B terminal skipped, later tests eligible in order, and no out-of-range cursor.

### `SCN-COU-003` — Cross-suite sequence
Three suites under `RUN_IN_SEQUENCE()` with delay. Require one active suite body, delay only between suites, and final-suite completion without hidden cumulative completion counters.

### `SCN-COU-004` — Report failure
Run is complete, publication fails. Test truth remains complete; report fails; no success banner; file-consumer currentness follows `IF-COU-005`.

### `SCN-COU-005` — Branch-changing multi-scan assertions
Scan 1 executes assertion A as ordinal 1 and A passes. Scan 2 executes a different branch-B assertion as ordinal 1 and B fails. Under `ADR-COU-017`, B is evaluated and becomes the first failure; no assertion-identity lookup can suppress it. Final `NumberOfAsserts = 1` because the metric is maximum assertions executed in any single test-body invocation. A companion case with A failing first confirms that the first-failure record remains A while B still executes later.

### `SCN-COU-006` — Publication interrupted after bytes are written
Start with either no report or a known-complete report. Begin a new streamed publication, then inject write/close/commit failure or reinitialize before commit. External consumer must still see the prior complete report or no current report; staging may exist but cannot be current. A later run can recover without treating stale staging as current.

### `SCN-COU-007` — Reinitialization mid-run
Interrupt an open multi-scan test, reinitialize the application/library, then run again. The new run starts at `IDLE`; no prior suite/test/assertion state resumes. Filesystem artifacts follow their separate publication-currentness rules.

### `SCN-COU-008` — Capacity and cross-task containment
Exercise suite/test/assertion storage at max/max+1 and attempt a second-task call. Every bounded write is guarded; the second task cannot mutate active-run state; errors remain distinguishable from test failures.

## 4. Architecture author-time gates

| Gate | Required input | Pass condition | Current R3 observation | Effect |
|---|---|---|---|---|
| `GATE-COU-001` | exact `SRC-001` + operative architecture approval | digest-matched source is package-accessible; approval covers the R3 shared decisions and PRD authoring | **PASS**: packaged `SRC-001` digest matches; `SRC-020` accepts R2 and `ADR-COU-017` | PRD authoring allowed |
| `GATE-COU-002` | authorized successor to `ADR-COU-007` | assertion evaluation, repeat-log and final count semantics are fixed in contract/requirements/allocations/checks | **PASS**: `ADR-COU-017`, `IF-COU-003`, `REQ-COU-024/037`, `VER-COU-032` | PRD-02/03/04 authoring allowed |
| `GATE-COU-003` | accepted predecessor implementations | dependent implementation/integration uses actual accepted outputs and matching contracts | `NOT_RUN` — future implementation gate | does not block PRD authoring |
| `GATE-COU-004` | native compiler/runtime evidence | all claimed support rows pass on exact candidate or claims are bounded to passing rows | `NOT_RUN` — future release gate | limits release claims, not PRD authoring |

## 5. Review performed against unchanged R1

### Candidate binding

- Subject: uploaded `CoUnit-Architecture-Rebaseline-R1(1).zip`.
- Archive SHA-256: `0d99336a7ee38de212be1f5af222716f700d05008fdbfeba31077d155bd6b84a`.
- R1 claim: package `COMPLETE`, approval `CANDIDATE`, all four PRDs `READY_FOR_PRD`.
- Review mode: `REVIEW_AND_REVISE`; document/archive changes only. No production code, deployment, credentials or physical effects.

### Checks actually run

| Check | Result | Binding / limit |
|---|---|---|
| ZIP path/symlink safety and separate extraction | `PASS` | unchanged uploaded R1 archive |
| R1 YAML parsing | `PASS` | `package-manifest.yaml`, `prd-authoring-handoff.yaml` |
| 18 canonical handoff field presence | `PASS` | all four YAML assignments have all 18 keys; field content still had defects |
| Exact `SRC-001` availability | `FAIL` | no package-relative file; File Library search by exact filename/hash did not recover it |
| Exact project assignment/delegation availability | `FAIL` | R1 contains only a generic claim that the user requested architecture; no source/locator/scope for delegation |
| Governing authoring edition | `PASS` | v4 synthesizer recovered as `SRC-019`; byte identity with R1 `SRC-017` not claimed |
| R1 assertion-position identity probe | `FAIL` | analytical counterexample `SCN-COU-005`: two distinct branch-dependent assertions alias `(test, ordinal)` |
| R1 xUnit external-currentness probe | `FAIL` | direct final-path write can expose partial bytes while internal state says `FAILED`; file-only consumer has no required internal-state channel |
| R1 spanning-allocation review | `FAIL` | PRD-02 could change assertion API/bounds without owning `REQ-COU-001/004`; PRD-03 could change file/log platform calls without owning `REQ-COU-031`; `ELM-COU-08` had no ISC split |
| R1 YAML exact-reference/dependency semantics | `FAIL` | bare fixed IDs lacked file/revision/authority; dependencies omitted contract/gate; PRD-04 YAML omitted `QAS-COU-011` while prose said all QAS |

### Strong rebuttals tested

- **Source identity rebuttal:** filename + SHA is enough. Rejected for readiness because identity does not provide the required authoring bytes or an accessible locator.
- **Authority rebuttal:** a candidate package can contain delegated choices without approval. Correct in principle, but R1 still must bind the delegation's source/scope before calling those choices settled for `READY_FOR_PRD`.
- **Assertion identity rebuttal:** ordinal is stable if every scan executes the same assertion call shape. Correct under that extra constraint, but R1 neither states nor proves such a constraint and preserving the public test-authoring model permits ordinary scan-dependent ST control flow. The architecture therefore cannot call ordinal a stable logical position.
- **Publication rebuttal:** internal `FAILED` state tells the consumer the file is bad. Rejected because `IF-COU-005` names CI/human **file consumer**; no channel requiring that consumer to query PLC publication state exists.
- **Allocation rebuttal:** final PRD-04 compatibility tests would catch drift. Rejected as an allocation defense: a late test can detect a defect but does not assign the producer-side obligation to the PRD that can introduce it.

## 6. R2 repair and successor recheck

| Finding | R2 repair | Recheck result |
|---|---|---|
| `RF-COU-001` | source register, gates, assignments and status now expose `OPEN-COU-006`; all affected readiness lowered | structural `PASS`; source remains unavailable, so blocker remains open |
| `RF-COU-002` | R1 authority claims preserved as history but not relied on; `OPEN-COU-007`; decision ledger and permission fields corrected | structural `PASS`; authority still unresolved |
| `RF-COU-003` | `ADR-COU-007` marked `CONTRADICTED`; `IF-COU-003` fixes non-aliasing semantic constraint and explicitly blocks mechanism/count selection | analytical counterexample no longer falsely passes; blocker remains open by design |
| `RF-COU-004` | `ADR-COU-016`, `REQ-COU-036`, strengthened `IF-COU-005`/`SDE-COU-003`, `SCN-COU-006`, `VER-COU-031` | analytical recheck `PASS`: a conforming R2 design may not make failed staging current; runtime proof remains future |
| `RF-COU-005` | spanning allocations fixed; `ISC-COU-004`; PRD-01/02/03 contribution boundaries made explicit | structural/semantic cross-reference recheck `PASS` |
| `RF-COU-006` | exact package-relative fixed-ref semantics, gate-bearing dependencies, concrete routes, all QAS/SCN refs and readiness projection corrected | YAML/reference/read-route recheck `PASS` subject to open source/authority blockers |

## 6A. R3 closure and requalification

| Closure | Evidence | R3 result |
|---|---|---|
| `OPEN-COU-006` / `RF-COU-001` | Exact `SRC-001` source is supplied package-relative, has the expected SHA-256, and passed safe archive/source-inventory inspection. | `FIXED_AND_RECHECKED` |
| `OPEN-COU-007` / `RF-COU-002` | `SRC-020` explicitly approves the R2 basis and the recommended assertion-semantics closure. | `FIXED_AND_RECHECKED`; R3 operative decisions use `EXPLICIT_APPROVAL` |
| `OPEN-COU-008` / `RF-COU-003` | Source inspection found no public call-site identity input; `ADR-COU-017` removes persistent assertion identity and fixes max-per-invocation count plus first-failure semantics. Branch-switch counterexamples were re-run against the new contract. | `FIXED_AND_RECHECKED` analytically; runtime checks remain future `VER` work |
| Source defect fidelity | inspected `FB_AssertResultStatic.ReportResult`: declared `FoundOne`/`AdditionalIdenticalAssert` are never assigned in the implementation; `AddAssertResult` increments/indexes without capacity check; final assignment refreshes `CurrentCycleCount`, not stored `CycleCount` | `PASS` for source-observation fidelity; does not claim runtime reproduction |
| Handoff requalification | all four assignments now bind R3, packaged source, accepted assertion semantics, and nonblocking later-stage items only | `READY_FOR_PRD` for all four |

R3 also corrected one R2 source-reading assumption: the packaged plaintext archive does **not** contain a `JUnitv5.xsd` file. PRD-03/04 must treat `SRC-016` as separate supporting material when schema-specific checking is needed rather than expect that schema inside `SRC-001`. This does not block PRD authoring because the shared XML meaning and parser-based acceptance rules are already fixed.

## 7. PRD-author consumption self-check

No fresh independent recipient was available. This reviewer had already seen the package/history, so the following is a same-context consumption check and **not independence**.

| PRD | Outcome/allocation found | Fixed/shared behavior found | First substantive authoring action | Lookup/dependency result | R3 consumption result |
|---|---|---|---|---|---|
| `PRD-COU-01` | yes | yes | map packaged runner/suite/test/task-helper objects to R3 state contracts | source resolves package-relative; authority fixed by `SRC-020` | `READY_FOR_PRD` |
| `PRD-COU-02` | yes | yes, including complete `IF-COU-003` | map 44 assertion families and implement `ADR-COU-017` bookkeeping/first-failure semantics | packaged source and accepted contract resolve without a shared choice | `READY_FOR_PRD` |
| `PRD-COU-03` | yes | yes, including external publication-currentness and max-per-invocation assertion count | map result/log/XML/file objects and bind target publication commit design | packaged source resolves; publication mechanism remains bounded delegated detail | `READY_FOR_PRD` |
| `PRD-COU-04` | yes | yes | build exact defect-to-test/source-compatibility map against packaged source | authoring input resolves; native runtime matrix remains a later qualification gate | `READY_FOR_PRD` |

The same-context consumer can now recover every shared input needed for PRD authoring without inventing source, authority or assertion semantics. This is not a fresh independent recipient test; each PRD still requires its downstream fresh worker-consumption review.

## 8. Context fit

The R3 core package is intended for package-first reading. The largest common read-now set is README + one PRD assignment + the relevant architecture/contracts/decision/verification sections; source implementation objects are check-specific retrieval. No target model capacity was supplied, so recipient fit remains an estimate rather than measured model evidence. `SRC-001` is now package-accessible and should be retrieved by object family rather than loaded wholesale. After the final files are produced, package word counts are recorded in `architecture-review.md`.

## 9. Readiness

| PRD | R2 status | R3 supported status | Basis |
|---|---|---|---|
| `PRD-COU-01` | `BLOCKED` | `READY_FOR_PRD` | exact packaged source + `SRC-020` approval; lifecycle shared contracts settled |
| `PRD-COU-02` | `BLOCKED` | `READY_FOR_PRD` | exact packaged source + approval + accepted `ADR-COU-017`/`IF-COU-003` |
| `PRD-COU-03` | `BLOCKED` | `READY_FOR_PRD` | exact packaged source + approval + fixed assertion-count and report-currentness semantics |
| `PRD-COU-04` | `BLOCKED` | `READY_FOR_PRD` | exact source/test baseline available and all architecture-stage shared semantics settled; native runtime execution remains later qualification |

**Package completeness:** `COMPLETE`.  
**Approval:** `APPROVED` by `SRC-020`.  
**Implementation/release acceptance:** not claimed.

## 10. Open items and residual uncertainty

| ID | Class | Exact item | Owner / closure | Effect |
|---|---|---|---|---|
| `OPEN-COU-001` | delegated PRD/implementation detail | Active repository/path for implementing the repair is not supplied. | PRD/implementation owner records exact baseline before worker dispatch. | Does not block PRD authoring; required before worker dispatch/implementation. |
| `OPEN-COU-002` | future qualification | Exact CODESYS compiler/runtime compatibility matrix for release. | PRD-04 executes `VER-COU-025` on the accepted candidate. | Future release gate only. |
| `OPEN-COU-003` | delegated PRD detail | Target-specific method that enforces xUnit semantic commit/currentness. | PRD-03 selects and proves a mechanism satisfying `IF-COU-005`/`VER-COU-031`. | Nonblocking bounded PRD detail. |
| `OPEN-COU-004` | independent deferred scope | Duration reporting and extra long date/time assertions. | Future architecture decision if requested. | Out of current delivery. |
| `OPEN-COU-005` | independent deferred scope | Protected/custom assertion extension API. | Future architecture decision if requested. | Out of current delivery. |

Closed authoring gates: `OPEN-COU-006` (source), `OPEN-COU-007` (authority), and `OPEN-COU-008` (assertion semantics) are `FIXED_AND_RECHECKED`; see §6A.
