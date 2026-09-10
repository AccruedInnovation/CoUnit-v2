# PRD-COU-02 — Assertion Engine and Safe Comparison

## 1. Status and decision summary

**Assignment:** `PRD-COU-02`  
**Architecture:** `COUNIT-ARCH-R3` / `2026-09-09-r3` — `APPROVED`.  
**PRD revision:** `PRD-COU-02-R2` / `2026-09-09`.  
**PRD status:** `PARTIAL`.  
**PRD approval:** `CANDIDATE`.  
**Implementation-ready:** **no**. The in-scope detailed design is closed, but the active repository remains unbound, PRD-01 implementation output does not yet exist, and the required fresh-context recipient review has not been obtained. All implementation slices are `NOT_READY`.

**Outcome.** Preserve all 44 existing public assertion method signatures while replacing scan/cycle assertion-history tracking with one bounded transaction per executable assertion call. Each call is evaluated every time, the per-test count is the maximum executable calls in one invocation, only the first failure owns detailed failure fields/logging, REAL/LREAL special values are handled without unsafe arithmetic, and generic `ANY` validates descriptor type/size/pointers before any read or copy.

**Target worker.** Conservative profile: can edit CODESYS ST and native project objects, run declared compile/tests, and implement private helpers from fixed pseudocode. It must not choose assertion identity, count semantics, public signatures, float semantics, generic `ANY` meaning, failure precedence, or acceptance standards.

### Governing sources and precedence

1. R3 approved architecture and `SRC-020` authority;
2. `ADR-COU-017`, `IF-COU-003`, `ISC-COU-002`, allocated requirements and verification;
3. digest-bound `SRC-001` as existing implementation evidence;
4. CODESYS generic `ANY`/IEEE REAL documentation as supporting evidence for representation fields and value ranges; exact target/compiler behavior remains PRD-04 qualification.

### Detailed decisions made here

| ID | Decision | Origin/status | Authority | Owner | Acceptance |
|---|---|---|---|---|---|
| `DD-COU02-001` | Every public assertion call starts exactly one assertion transaction; internal dispatch may call only private comparators/reporters, never another public assertion wrapper. | newly selected `ACTIVE_DELEGATED` | `DELEGATED_AUTHORITY` under PRD-02 helper/decomposition scope | PRD-02 | `VER-003/008/009/014/032` |
| `DD-COU02-002` | First-failure fields are written while `IsSet=FALSE`, then `IsSet` commits last; later failures set failure truth but do not overwrite/log detailed fields. | derived/detail `ACTIVE_DERIVED` | `ADR-COU-017` | PRD-02 | `VER-014` |
| `DD-COU02-003` | Float comparator uses NaN/equality/non-finite guards and an opposite-sign comparison that avoids subtraction overflow solely to test tolerance. | newly selected `ACTIVE_DELEGATED` | float algorithm delegation under `ADR-COU-009` | PRD-02 | `VER-011`, `QAS-004` |
| `DD-COU02-004` | Generic STRING/WSTRING `ANY` values are compared in-place to a bounded terminator; capacities may differ. Known primitives require exact descriptor size before typed read; all remaining equal-type/equal-size values use bytewise representation equality. | newly selected `ACTIVE_DELEGATED` | `ADR-COU-013`, `REQ-020/021` | PRD-02 | `VER-012/013` |
| `DD-COU02-005` | Failure diagnostics are capped to `T_MaxString` and use suffix `...<truncated>`; array diagnostics contain shape or first mismatch only. | newly selected `ACTIVE_DELEGATED` | formatter-length delegation | PRD-02 | `VER-014`; memory bound |

Normative details: [`contracts/assertion-engine-contract.md`](contracts/assertion-engine-contract.md). Exact exported public signatures: [`contracts/assertion-family-map.csv`](contracts/assertion-family-map.csv).

### Open items

- `OPEN-COU-001`: bind active repository/toolchain before dispatch.
- predecessor gate: accepted PRD-01 active-context implementation is required before `COU02-S1` integration/dispatch; this is a planned implementation dependency, not missing architecture.
- `PRD02-REV-001`: mandatory fresh packet-only consumption review for each slice remains `NOT_RUN`.

No shared assertion semantic decision remains open.

### Slice status

`COU02-S1`, `COU02-S2`, and `COU02-S3` are all `NOT_READY`. S1 waits on repository + accepted PRD-01 context; S2 waits on S1; S3 waits on S1/S2.

Implementation acceptance: **not established**.

## 2. Repository discovery and current state

The active implementation repository is not supplied. Existing-system observations use `SRC-001`, the exact CoUnit 1.2.0.3 plaintext source snapshot packaged with R3.

### Observed assertion implementation

- `FB_TestSuite` currently owns `AssertResults : FB_AssertResultStatic` and `AssertArrayResults : FB_AssertArrayResultStatic` plus public assertion methods.
- `FB_AssertResultStatic.ReportResult` uses runtime task cycle count and has `FoundOne`/`AdditionalIdenticalAssert` branches, but the supplied implementation does not assign those flags before deciding whether to add a result.
- scalar and array tracker add paths increment a total and index fixed arrays without the R3 pre-write limit rule.
- typed wrappers such as `AssertEquals_REAL` call the tracker before comparing and gate failure logging on `AlreadyReported`.
- `SetTestFailed` overwrites assertion type/message on each failure in the current source.
- generic `AssertEquals(ANY,ANY)` compares type/size, but for STRING/WSTRING performs `MEMCPY` using the argument `diSize` into fixed local 255-character buffers before proving that size fits; it dispatches standard types by copying and then calling public typed assertion wrappers, which would be incompatible with the new “one public call = one count” rule if left unchanged.
- 1-D arrays compare equal logical extents even when lower bounds differ, by offsetting each array from its own lower bound. This current behavior is retained.
- the source enum `E_AssertionType` contains generic, 21 scalar/string/time types, and 20 array types; `assertion-family-map.csv` records 44 public assertion methods.

### Evidence table

| Claim | Source | Baseline/result |
|---|---|---|
| 44 public assertion methods/signatures exist. | `SRC-001/Unit Test Framework for CODESYS/POUs/FB_TestSuite/Assert*/*.DEC.exp` | mechanically inventoried into `assertion-family-map.csv` — `PASS` |
| old tracker keeps cycle/assertion-history state. | `FB_AssertResultStatic`, `FB_AssertArrayResultStatic`, suite declaration | observed source |
| `ReportResult` search flags are not assigned in supplied scalar implementation. | `FB_AssertResultStatic/ReportResult/ReportResult.IMP.exp` | observed source; no runtime reproduction claimed |
| generic `ANY` exposes `TypeClass`, `pValue`, `diSize`; current source reads these. | current source + CODESYS generic `ANY` docs | representation supported; target compile later |
| current generic string path copies arbitrary `diSize` into 255-character locals. | `FB_TestSuite/AssertEquals/AssertEquals.IMP.exp` + `T_MaxString` | observed unsafe shape |
| array methods permit differing lower bounds when extents match. | e.g. `AssertArrayEquals_REAL.IMP.exp` | observed and retained |
| REAL/LREAL are IEEE-754 in current CODESYS docs and have documented finite maxima. | CODESYS docs, recorded by authoring review | supporting design evidence; exact target qualification later |
| active repo/build/test/compiler/runtime | not supplied | dispatch binding needed |

No current test project is assumed to exist merely because source methods include documentation examples.

## 3. Outcome, scope, and non-goals

### Obligations

`U02 = {REQ-COU-001, REQ-COU-004, REQ-COU-007, REQ-COU-008, REQ-COU-015..021, REQ-COU-034, REQ-COU-037}`.

Local refinements:

- `L-COU02-001`: one public assertion call must consume one count even when generic/array logic reuses private typed comparators;
- `L-COU02-002`: first-failure commit must prevent mixed fields on the sole owner task;
- `L-COU02-003`: diagnostic formatting must remain bounded and must not determine equality;
- `L-COU02-004`: generic string comparison must prove terminator access stays inside descriptor bounds.

### Observable success

- Existing source still calls the same `Assert*` signatures.
- A 10,000-scan test does not grow assertion-history storage merely because scans repeat.
- Branch A can execute one passing assertion at ordinal 1 on one scan and branch B a different failing assertion at ordinal 1 later; B still evaluates and fails, and final `NumberOfAsserts=1` if each invocation contained one executable assertion.
- Exceeding the suite invocation assertion limit fails before incrementing a counter or writing test failure data for the rejected call.
- The first failure record is coherent and never replaced by later failures.
- Every typed public method produces the correct `E_AssertionType`.
- negative or NaN delta fails the current test locally; NaN operands are unequal; equal same-sign infinities pass; all other infinity combinations fail; no unsafe conversion is required.
- generic mismatched type is unequal, invalid descriptor sizes/pointers become local assertion-argument failures, long strings do not overflow fixed locals, and user-defined equal-type/equal-size values retain bytewise representation equality.

### Scope

In: all public assertion wrappers, private comparators, common begin/outcome reporting, assertion count/max state, first-failure state/log trigger, formatting bounds, removal/migration of old tracker canonical use.

Out: test/run lifecycle ownership (PRD-01), result snapshot and report files (PRD-03), new assertion APIs, explicit stable call-site IDs, duration reporting, protected/custom assertion extension API, runtime release matrix.

### Assumptions/gates

PRD-01 provides a valid active test segment, suite-body invocation reset point, owner-task validation and canonical test record. If its accepted interface differs from R3, this PRD must be rechecked before implementation. The active compiler must expose `ANY` descriptor semantics compatible with the public method declarations; a mismatch is a target qualification/compatibility issue, not permission to change generic semantics.

## 4. Interfaces and data contracts

The normative assertion contract is [`contracts/assertion-engine-contract.md`](contracts/assertion-engine-contract.md). `assertion-family-map.csv` is an author-generated projection of `SRC-001`, not a competing API source.

### Internal calls

```text
BeginAssertion(assertion_type, message)
  -> Execute : BOOL
  -> Ordinal : UDINT
  -> framework error via runner on capacity/context integrity failure

RecordAssertionOutcome(
  ordinal,
  assertion_type,
  passed,
  argument_error,
  message,
  expected_text,
  actual_text,
  diagnostic_suffix)
```

Exact ST method signatures may place outputs in `VAR_OUTPUT`, return type, or private record according to repo convention, but semantic inputs/outputs and one-transaction rule are fixed.

### Counter/state fields

| Field | Type/owner | Rule |
|---|---|---|
| `SuiteInvocationAssertionCount` | private `UDINT`, runner/suite invocation context | reset before suite body; guard `< configured max` before increment |
| `InvocationOrdinal` | `UDINT`, current canonical test record | reset on each accepted test segment; increment only executable assertion calls |
| `MaxAssertionsPerInvocation` | `UDINT`, test record | `MAX(previous, InvocationOrdinal)` after each accepted assertion |
| `HasFailure` | BOOL, test record | monotonic false→true during run |
| `FirstFailure` | first-failure struct | fields filled before `IsSet=TRUE`; never overwritten after commit |

No field uses ordinal as a persistent key.

### Public type map

The worker shall use the source enum values by semantic name. Scalars map to `Type_<suffix>`, arrays to exact `Type_Array_*`, 2-D/3-D float families to `Type_Array2D_*`/`Type_Array3D_*`, `AssertTrue/AssertFalse` to `Type_BOOL`, and generic `AssertEquals` to `Type_ANY`.

A mechanical test must compare all 44 methods against the map and fail if a method is missing or reports another family.

### Generic ANY contract

CODESYS `ANY` descriptors carry a type class, pointer and signed size. This PRD requires pointer/size validation before read/copy; typed primitive exact-size validation before local copy; bounded logical string termination; and bytewise fallback over exactly equal `diSize`. See supporting contract §7.

Unknown future type classes are not rejected merely because they lack a typed formatter: if descriptors are otherwise valid and type/size match, representation comparison is allowed. Diagnostic type remains `Type_ANY`.

## 5. Canonical production and verification closure

### Producers/consumers

| Concept | Producer | Consumer | Check |
|---|---|---|---|
| executable assertion admission | `BeginAssertion` | all public wrappers | limit/context tests |
| invocation ordinal/max | `BeginAssertion` | PRD-03 final result | branch/max-count tests |
| comparison truth | one private comparator per logical family | `RecordAssertionOutcome` | independent expected-value fixtures |
| first-failure record | `RecordAssertionOutcome` first failing call | Device Log and PRD-03 snapshot | two-failure coherence test |
| test failure truth | outcome reporter | PRD-01 finish + PRD-03 snapshot | final test-state tests |

No producer success flag is accepted without testing observable state. The 10k-scan and branch-switch tests reject an implementation that accidentally reintroduces assertion-history/dedup logic. The 44-family type test rejects copy/paste enum errors without duplicating comparator internals.

### Recompute/invalidation

`InvocationOrdinal` recomputes from zero each accepted test segment; `SuiteInvocationAssertionCount` each suite body; `MaxAssertionsPerInvocation` and first-failure record persist only for the current non-retained run. Reinit discards all.

### Two-conforming-implementations test

Two implementations cannot differ on whether repeated assertions execute, what is counted, which failure owns detail, float special cases, array lower-bound treatment, or generic type/size representation rules. Private loop/helper layout may differ.

## 6. Bootstrap, staging, and migration

### A1 — bind accepted PRD-01 + repository

Verify exact PRD-01 candidate provides active test index, `ShouldExecute`, owner-task validation, suite-invocation reset hook and canonical test record. Bind active repository/toolchain.

### A2 — common assertion core (`COU02-S1`)

Add begin/count/max/first-failure path. Keep existing typed methods temporarily but route at least a small representative family through the new reporter. Disable/remove old trackers from canonical count/dedup use. Run 10k-scan, branch-change and capacity tests first.

### A3 — scalar + ANY (`COU02-S2`)

Migrate all non-array wrappers. Generic ANY uses private typed comparators, not public recursion. Run float and ANY adversarial cases.

### A4 — arrays + full family (`COU02-S3`)

Migrate all arrays, verify extent/offset behavior and exact enum types, then run all 44-family coverage and integration.

### Migration compatibility

Old tracker FBs/DUTs may stay in the library if public/source compatibility requires them, but there must be no canonical execution references. Do not keep them synchronized “just in case”; that would reintroduce storage and dual authority. Old `CalculateAndSetNumberOfAssertsForTest` may wrap the new max count only if an existing caller still needs it.

## 7. State, effects, transactions, and recovery

Assertion treatment is `CONTRACT` because failure state crosses PRD boundaries.

### Assertion transaction

| Phase | Guard/effect | Failure behavior |
|---|---|---|
| admission | owner/context + `ShouldExecute`; pre-write suite count guard | context integrity -> PRD-01 framework error; suppressed test -> no-op; capacity -> framework error before writes |
| count commit | increment suite count, ordinal, max | must complete before comparison; sole owner task |
| compare | read only validated inputs | local bad argument yields comparison failure, not runtime abort |
| outcome | set test failure; first failure fields then `IsSet` | later failure cannot mix/overwrite first record |
| diagnostic | one detailed first-failure log | log delivery failure must not rewrite test truth (PRD-03 platform rule) |

No filesystem/network/DB effect occurs in PRD-02. Diagnostic Device Log calls are external-ish platform effects but are non-authoritative; failure truth commits before logging and cannot be undone by log failure.

### Recovery

No assertion transaction is resumed after restart. The run state is non-retained. Because one owner task executes each call synchronously, there is no retry/idempotency key. Repeated scans are new assertion executions under a new per-invocation ordinal, not replays of a persistent assertion record.

## 8. Source, install, runtime, and platform closure

### Source objects to change

Repository mapping awaits `OPEN-COU-001`. Expected existing object families:

- 44 `FB_TestSuite.Assert*` methods;
- `FB_TestSuite` assertion tracker/current failure members;
- `FB_TestSuite.SetTestFailed`, count helper, message formatter path;
- `FB_AssertResultStatic`/`FB_AssertArrayResultStatic` and related DUTs/functions as removal/compatibility candidates;
- generic helper union/functions if no longer used;
- `E_AssertionType` should not need semantic change.

### Platform facts

CODESYS currently documents `ANY` as an internal descriptor with `typeclass`, `pvalue`, `diSize`, and REAL/LREAL as IEEE-754. Those docs support this PRD's private algorithm but do not establish support on every target/compiler. Do not add `FloatingPointUtils` merely for special-value classification unless the bound repo already requires it; the normative algorithm can use IEEE comparisons and documented type bounds.

### Build/install

No new external package/library is required by design. The implementation must compile with the repo's existing public library dependencies. Any proposed new library dependency requires a source/build/release impact review.

No product filesystem path applies.

## 9. Integration, invalidation, and requalification

### Upstream/downstream

- PRD-01 supplies current test segment and owner context.
- PRD-02 writes test record assertion fields.
- PRD-03 copies `MaxAssertionsPerInvocation` and first failure into the canonical snapshot without reinterpretation.
- PRD-04 verifies family coverage, branch behavior, resource bound, float/ANY safety and source compatibility.

### Invalidation

Change to PRD-01 segment boundaries/task ownership reopens count/context tests. Change to `ADR-COU-017`, assertion limit type, public signatures, `E_AssertionType`, generic `ANY` descriptor semantics, string encoding, or float target representation reopens relevant assertion design/evidence. A PRD-03 request to count “distinct source assertions” is a shared-contract contradiction and must return to architecture; PRD-02 must not add hidden call-site identity.

### Authoring boundary review

Analytical checks covered public wrapper→common reporter, PRD-01 context→assertion admission, and PRD-02 result→PRD-03 snapshot. A counterexample with public ANY dispatching through public typed wrappers exposed double-count risk; `DD-COU02-001` forbids it. A branch-switch trace confirms no persistent ordinal identity exists. Runtime checks remain future.

## 10. Test and evidence plan

| Requirement/VER | Case | Fixture/preconditions | Expected / prohibited | Evidence/method | Status |
|---|---|---|---|---|---|
| `REQ-007`, `VER-003` | `A01-assert-limit` | valid current test; exactly max assertions then one extra in one suite-body invocation | first max accepted; extra triggers framework error before suite/test count or failure write | CODESYS test/state snapshot | `NOT_RUN` |
| `REQ-008/015`, `VER-008` | `A02-10k-scans` | one test invoked 10,000 scans with same passing assertion | fixed test bookkeeping; max count 1; no assertion-history growth | memory/state inspection | `NOT_RUN` |
| `REQ-018`, `VER-009` | `A03-family-type-map` | one intentional failure per 44 public methods | first-failure type equals map for isolated test | generated cases from CSV + assertions | `NOT_RUN` |
| `REQ-034`, `VER-010` | `A04-type-transition-safety` | generic/string then typed REAL or source-regression shape | no stale union/copy runtime fault; correct local outcome | target regression | `NOT_RUN` |
| `REQ-019`, `VER-011` | `A05-float-matrix` | finite boundary; delta 0/equal; +/-Inf pairs; qNaN expected/actual/delta; sNaN raw-bit fixtures where preserved; negative delta; opposite-sign large values | exact contract result; bad delta local fail; no runtime exception; NaN classification occurs before FP operations | table-driven CODESYS test | `NOT_RUN` |
| `REQ-020`, `VER-012` | `A06-any-bounds` | long STRING/WSTRING capacities, type mismatch, primitive wrong size via safe harness, null/malformed descriptor when constructible | no fixed-buffer overrun/read; correct fail class; no unrelated state | instrumented test | `NOT_RUN` |
| `REQ-021`, `VER-013` | `A07-userdef-bytes` | two same-type structs same/different padding/representation bytes; size/type mismatch | equal iff exact representation for same type/size; mismatches fail before compare | independent byte fixtures | `NOT_RUN` |
| `REQ-017`, `VER-014` | `A08-first-failure` | test with first fail type/message A, second fail B | HasFailure true; detailed record/log remains A; B still evaluated | test state + log capture | `NOT_RUN` |
| `REQ-037`, `VER-032` | `A09-branch-ordinal` | scan1 branch A assertion passes at ordinal1; scan2 branch B different assertion fails at ordinal1 | B evaluated/fails; first failure B; max count 1 | state/result test | `NOT_RUN` |
| `REQ-016/018` | `A10-array-shape-offset` | equal values with different lower bounds but same extents; shape mismatch; first content mismatch | offset compare passes first; shape/content cases fail with correct array type | CODESYS arrays | `NOT_RUN` |
| `REQ-001` | `A11-public-signature-compile` | all 44 existing call shapes/representative real user source | compile with no call-site edits | PRD-04 | `NOT_RUN` |

### Float oracle

A table in the test code shall state expected booleans explicitly; it must not call the production comparator as its oracle. Include at minimum `+Inf/+Inf`, `-Inf/-Inf`, `+Inf/-Inf`, `Inf/finite`, quiet-NaN combinations, signaling-NaN bit patterns where the target preserves them, and large opposite-sign finite values with both insufficient and infinite delta. Construct NaN fixtures by copying raw IEEE bit patterns so fixture setup itself does not evaluate the NaN.

### ANY guard reachability

Do not count a test as proof of size/pointer guard when it first fails type mismatch. Build each negative fixture with matching type where needed so the target guard executes. If CODESYS syntax makes malformed raw `ANY` descriptors impossible through public calls, use a private test-only helper in the test project to call the private comparator with a descriptor record; do not expose such helper in library public API.

### Author-time results

- 44 public assertion methods mechanically inventoried: `PASS`.
- contract vs R3 semantic review: `PASS`.
- actual CODESYS compile/runtime: `NOT_RUN`.
- fresh recipient consumption: `NOT_RUN`.

## 11. Leaf implementation slices

Worker packets:

1. [`COU02-S1-count-outcome-core.md`](slices/COU02-S1-count-outcome-core.md)
2. [`COU02-S2-scalar-any.md`](slices/COU02-S2-scalar-any.md)
3. [`COU02-S3-arrays-integration.md`](slices/COU02-S3-arrays-integration.md)

### Reference availability

| Reference | Classification | Gate |
|---|---|---|
| R3 + `SRC-001` | `SUPPLIED_WITH_PRD` | present |
| assertion contract/map | `SUPPLIED_WITH_PRD` | present; CSV has 44 methods |
| active repo/toolchain | dispatch binding/open item | absent |
| accepted PRD-01 context implementation | `PRODUCED_BY_PREDECESSOR` | not available until accepted |
| S1 output | `PRODUCED_BY_PREDECESSOR` | S2/S3 wait |
| new comparators/tests | `CREATED_BY_THIS_SLICE` | acceptance fixed here |

### Context fit

S1 reads only common assertion bookkeeping + PRD-01 context; S2 reads scalar/ANY rows; S3 array rows. The CSV lets the worker retrieve exact method declarations without loading all 44 implementations at once. Exact model capacity is unknown; dispatch must verify the selected worker can hold each slice packet, the relevant contract section and changed source family plus work reserve.

### Fresh recipient gate

No fresh independent recipient exists in this session. Author-only packet reconstruction found no unstated semantic choice, but does not satisfy the mandatory review. This keeps the handoff row `PARTIAL` and PRD not implementation-ready.

### Coverage equality

`O02 = U02 ∪ {L-COU02-001..004}`. Sections 3/4/7/10 and the three slices cover all. PRD-04 owns final integrated acceptance, not PRD-02.

## 12. Risks, security, operations, and documentation

| Risk | Trigger | Prevention/detection | Response | Gate |
|---|---|---|---|---|
| history growth/exhaustion | multi-scan tests | no tracker/identity storage; 10k scan test | reject implementation if memory/count grows | `VER-008` |
| branch alias false pass | changing control flow | evaluate all calls; no persistent ordinal key | branch test | `VER-032` |
| buffer overwrite | generic long string/large ANY | descriptor-first bounded reads, no arbitrary fixed-buffer copy | local assertion failure | `VER-012` |
| FP runtime fault/wrong result | NaN/Inf/negative delta/large opposite signs | guarded algorithm + explicit oracle | local failure or correct bool, never crash | `VER-011` |
| wrong failure metadata | copy/paste wrapper | family map + one isolated fail each | block integration | `VER-009` |
| first failure overwritten | multiple fails | commit-once first-failure record | block result/log integration | `VER-014` |
| dependency growth | adding utility library | default no new library; review any addition | reject unnecessary dependency | build review |

Security/privacy: assertions operate on caller memory through CODESYS generic descriptors. The relevant security property is bounded valid access; the PRD neither persists arbitrary expected/actual content nor sends it over network. Diagnostic values may contain application test data; existing Device Log exposure policy applies and PRD-03 should not expand retention.

Documentation must state the R3 count meaning clearly: `NumberOfAsserts` is max executable calls in one invocation, not distinct source sites. Generic unsupported values use representation equality. FIRST failure owns detailed diagnostic.

## 13. Implementability matrix

| Dimension | Status | Evidence/section | Remaining gap and owner |
|---|---|---|---|
| Repository or new-project evidence, baseline, and current-state discovery | `PARTIAL` | §2, source snapshot | active repo/toolchain absent |
| Architecture binding, allocated scope, delegated design, and approval gates | `PASS` | §1 | None |
| Target maturity, operating limits, and permitted claims | `PASS` | §§1,3 | None |
| Source precedence, design authority, and decision closure | `PASS` | §1 | None |
| Outcome, scope, non-goals, and ownership | `PASS` | §3 | None |
| Target worker, context fit, and bounded local choices | `PARTIAL` | §§1,11 | worker/access/capacity unbound |
| Interfaces and field-level data contracts | `PASS` | §4 + assertion contract/map | None |
| Canonical producer/recomputation/verifier closure | `PASS` | §5 | None |
| Cross-artifact admission and consistency where required | `PASS` | §§5,9 | None — assertion state is in-memory and candidate binding is explicit |
| Non-circular bootstrap, staging, and migration | `PASS` | §6 | implementation waits on predecessor/repo but path is defined |
| State/effect/transaction/recovery semantics | `PASS` | §7 | None |
| Source/build/install/runtime/platform closure | `PARTIAL` | §8 | active compiler/repo/build path absent |
| Observed capabilities and filesystem boundaries | `PASS` | §§2,8 | no product filesystem effect; platform claims deferred to qualification |
| Integration invalidation and requalification | `PASS` | §9 | None |
| Author-set acceptance rules and schema-valid adversarial cases | `PASS` | §10 | runtime execution future |
| Supplied artifacts, reference availability, and author-time validation | `PASS` | §§2,4,10,11 | map/contract present and checked |
| Leaf slices, file ownership, sequencing, and dispatch gates | `PARTIAL` | §11 | active repository mapping and predecessor absent; all `NOT_READY` |
| Worker-facing handoffs and fresh-context recipient review | `PARTIAL` | §11 | fresh review unavailable |
| Set-equal allocated/local obligation coverage and cross-PRD acceptance ownership | `PASS` | §§3,10,11 | None |
| Open facts, decisions, assumptions, and late-bound values | `PASS` | §1 | open inputs are explicit dispatch/qualification bindings, not semantic choices |
| Security, operations, rollout, and documentation | `PASS` | §12 | None |

**Overall:** `PARTIAL`. Detailed assertion design is complete within delegated authority; missing active-repository/predecessor bindings affect dispatch, and missing fresh-recipient evidence prevents overall `PASS`.

**Implementation-ready: no.** PRD approval is `CANDIDATE`; architecture remains approved. No slice may dispatch yet. Implementation correctness, runtime safety, and release acceptance are not established.
