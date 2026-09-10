# Shared Contracts and State–Decision–Effect Rules

## IF-COU-001 — Public test-authoring contract

**Owner:** CoUnit public API  
**Consumers:** all user test suites and test programs  
**Status:** `ACTIVE_ACCEPTED`, compatibility-preserving

### Operations

#### `RUN()`

- Called once per scan from the run's one bound test task.
- Selects `ALL_SUITES` mode on first accepted call.
- Invokes no already-terminal suite.
- After terminal test execution, subsequent calls are idempotent with respect to test state and may only service pending publication if the chosen implementation needs it.

#### `RUN_IN_SEQUENCE()`

- Same task/call rule as `RUN()`.
- Selects `IN_SEQUENCE` on first accepted call.
- Uses registration order.
- Honors configured inter-suite delay.
- A skipped/empty/completed suite never blocks the next suite.

#### `TEST(TestName)`

- Canonicalizes and registers the test if first seen.
- Makes it the active test for following assertions in the current suite-body invocation.
- For a terminal or skipped test, following assertions are suppressed through the active context.
- Duplicate same-epoch definition is diagnosed.

#### `TEST_ORDERED(TestName) : BOOL`

- Performs the same canonical registration.
- Returns `TRUE` only for the enabled open test at the ordered cursor.
- Returns `FALSE` for skipped, terminal or not-yet-selected ordered tests.
- Skipped terminal entries are advanced automatically.

#### `TEST_FINISHED() : BOOL`

- Finalizes the current open test.
- Idempotent for an already-terminal current test.
- Returns success only when a valid current test context exists.

#### `TEST_FINISHED_NAMED(TestName)`

- Resolves the supplied canonical name.
- Finalizes only that test.
- Does not replace or mutate another current test context.
- Unknown name is rejected with a bounded misuse diagnostic and no state change.

#### `IS_TEST_FINISHED(TestName) : BOOL`

- Resolves the canonical name in the active suite.
- Returns true for any terminal state (`PASSED`, `FAILED`, `SKIPPED`, `ABORTED`, `ERROR`).

### Invalid context

A test/assert/finish operation outside a runner-owned active suite context must not use stale global state. If a run is active and the missing/mismatched context makes its integrity uncertain, CoUnit fixes the run disposition as `FRAMEWORK_ERROR` and finalizes safely. A call made when no run is active is rejected with a bounded diagnostic and no stale-state mutation.

---

## IF-COU-002 — Runner ↔ suite contract

**Owner:** execution core  
**Provider:** `ELM-COU-02`  
**Consumer/provider counterpart:** `ELM-COU-03`

### Runner guarantees

Before suite invocation:

- active run exists;
- active task matches bound task;
- suite index/pointer are valid;
- runner epoch is fixed for this top-level call;
- active test is cleared.

After suite return:

- the runner clears transient active suite/test context;
- suite state remains canonical in the suite-owned record array.

### Suite guarantees

- test records are written only after capacity checks;
- canonical test identity is stable after first registration;
- `AreAllTestsFinished` is derived from terminal states and empty-suite observation, not from a second uninitialized loop;
- skipped tests count as terminal;
- all internal loops stop at the validated stored count.

### Empty suite

A suite becomes complete after it has been invoked under a valid runner epoch and has registered zero tests. It does not require a second task-cycle heuristic from a runtime API.

---

## IF-COU-003 — Assertion outcome contract

**Status:** `ACTIVE_ACCEPTED` under `ADR-COU-017` / `SRC-020`  
**Owner:** assertion engine; shared count semantics owned by the architecture baseline  
**Provider:** `ELM-COU-04`  
**Consumer:** `ELM-COU-03`

Each executable public assertion reports:

```text
RecordAssertion(
    test_index,
    invocation_ordinal,
    assertion_type,
    passed,
    message,
    expected_text_if_failed,
    actual_text_if_failed
)
```

`invocation_ordinal` is order within the current test-body segment of one suite-body invocation. It is not a persistent assertion identity. `suite_invocation_assertion_count` is reset once when the runner enters the suite body and preserves the existing `MaxNumberOfAssertsForEachTestSuite` configuration as a per-suite-body-invocation execution bound.

### Fixed guarantees

- reset `suite_invocation_assertion_count` at runner entry to each suite-body invocation and reset `invocation_ordinal` when an accepted current-test segment starts;
- before each assertion, require `suite_invocation_assertion_count < GVL_Param_coUnit.MaxNumberOfAssertsForEachTestSuite`; otherwise raise a framework error before increment or assertion-state write;
- after the guard, increment both counters once per executable assertion call;
- evaluate every executable assertion on every invocation;
- update `MaxAssertionsPerInvocation` from the largest valid ordinal seen for the test during the run;
- apply failure truth to the active test immediately;
- write the first-failure record atomically only on the transition from no failure to first failure;
- emit detailed assertion failure output only for that first-failure transition; later assertions still evaluate but do not require de-duplication state;
- retain no raw expected/actual history and no source/message/value/ordinal-derived call-site key;
- final `NumberOfAssertions`/`NumberOfAsserts` equals `MaxAssertionsPerInvocation` and is not described as a count of distinct source assertion statements;
- scan-dependent branch changes cannot make a later assertion "already reported" merely because another branch used the same ordinal.

### Floating point

The rules in `ADR-COU-009` are canonical: invalid negative/NaN delta fails locally without unsafe arithmetic; any NaN operand is unequal; same-sign infinities compare equal; other infinities do not; finite values use the defined absolute tolerance.

### Generic `ANY`

The rules in `ADR-COU-013` are canonical. STRING/WSTRING use bounded logical content comparison; other same-type/same-size unsupported values use bounded representation equality.

---

## IF-COU-004 — Final result contract

**Owner:** execution core/result snapshot  
**Consumers:** Device Log publisher, xUnit publisher, legacy result projection

### Acceptance point

Results become final only in `FINALIZING`, after the run disposition has been fixed as `NORMAL`, `ABORTED` or `FRAMEWORK_ERROR` and the snapshot has been built from canonical suite/test records.

### Invariants

- each known test has exactly one final category;
- total = passed + failed + skipped + error/aborted;
- suite counts sum to run counts;
- `PASSED` requires explicit test finish and zero failed assertions;
- `FAILED` requires explicit test finish and at least one failed assertion;
- `SKIPPED` is never counted as passed;
- unfinished tests on abort/error are never counted as passed;
- assertion count comes from the test record, not from a later path/name search.

### Legacy projection

Legacy public result types remain a projection. They cannot override canonical snapshot truth.

---

## IF-COU-005 — xUnit publication contract

**Owner:** xUnit publisher  
**Consumer:** CI/human file consumer

### Input

One immutable final result snapshot plus:

- enable flag;
- target path;
- bounded output chunk size.

### Output and status

- `DISABLED` when publication is disabled;
- `WRITTEN` only after the entire XML document has been emitted and file close succeeds;
- `FAILED` on any required file, XML-writer, or publication-commit failure.

### External currentness and semantic commit

The CI/human consumer is a file consumer and cannot be required to inspect an internal PLC enum before deciding whether the configured report artifact is current. Therefore:

1. output before commit is staging output and is not the externally current successful report;
2. the current successful report changes only after the full document is written, flushed/closed as required, and the chosen commit step succeeds;
3. on failure before commit, the prior complete current artifact remains current or the current artifact is absent; a partial artifact may remain only under a non-current staging identity;
4. restart/reinitialization must ignore or safely clean stale staging output before a later run publishes;
5. direct final-path writing is conforming only if the target/runtime and consumer protocol establish the same no-partial-current guarantee.

This invariant is `ADR-COU-016` / `REQ-COU-036`; the exact platform mechanism is `OPEN-COU-003` / `PRD-COU-03` detail.

### XML semantics

```xml
<testsuites tests="TOTAL" failures="FAILED" errors="ERRORS">
  <testsuite name="..." tests="..." failures="..." errors="..." skipped="...">
    <testcase name="..." classname="...">
      <failure .../>   <!-- assertion failure -->
      <skipped/>       <!-- skipped test -->
      <error .../>     <!-- framework/aborted test -->
    </testcase>
  </testsuite>
</testsuites>
```

Only the applicable child result appears for a testcase.

All dynamic text passes through one XML escaping function before writer insertion.

The chunk writer flushes before capacity exhaustion. Output size is bounded only by file/storage capacity and the result set, not by one in-memory XML document.

---

# ImplementationStructureContracts

## ISC-COU-001 — Execution core

### Fixed structure

- `FB_coUnitRunner` or its successor remains the run-state owner.
- suite registration is owned by the runner/registry, not open GVL mutation;
- a compact `ST_TestRecord` replaces canonical per-test FB state;
- runner epoch is persistent run state;
- active suite/test context is transient and cleared on return;
- one-task binding is enforced;
- all capacities fail closed before writes.

### Delegated detail

The PRD may choose exact DUT/FB names, enum numeric values and private helper layout. It may retain compatibility wrappers around old helper FBs.

It may not reintroduce value-based expected/actual assertion identity or a second completion owner.

## ISC-COU-002 — Assertion core

### Fixed structure

- typed public assertion wrappers;
- shared internal compare/report helpers;
- suite-body-invocation assertion counter, test-local invocation ordinal and per-test `MaxAssertionsPerInvocation`;
- hard suite-body-invocation guard using `MaxNumberOfAssertsForEachTestSuite` before either assertion counter or result state is updated;
- no persistent per-assertion de-duplication/identity table;
- atomic first-failure record, with detailed failure logging only on the first-failure transition;
- no raw expected/actual persistence for repeat suppression;
- safe `ANY` dispatch;
- one REAL/LREAL rule.

### Delegated detail

Exact helper names, counter types large enough to guard the configured limit before narrowing to legacy `UINT`, formatter decomposition, and migration/removal of the old `FB_AssertResultStatic`/`FB_AssertArrayResultStatic` trackers are local PRD choices. A new call-site identity registry is outside this assignment unless a later approved architecture change reopens `ADR-COU-017`.

## ISC-COU-003 — Reporting

### Fixed structure

- canonical final snapshot first;
- legacy result projection second;
- Device Log and xUnit consume final state;
- XML escape is writer-owned;
- output is streamed/chunked;
- publish state is explicit;
- external currentness changes only at the `IF-COU-005` semantic commit;
- file failure cannot emit success or replace the current complete artifact with partial staging.

### Delegated detail

The PRD owns the exact portable file replacement strategy and chunk size implementation, subject to the above semantics.

---

## ISC-COU-004 — CODESYS platform adapter

**Outcome:** runtime-specific calls fail in the correct semantic domain without invalid pointer access or duplicated platform policy.

**Fixed structure:**

- `ELM-COU-08` is the canonical platform-boundary responsibility inside the CoUnit library; it need not be one source file.
- `PRD-COU-01` contributes task/project lookup and task-binding checks.
- `PRD-COU-03` contributes file/log calls used by publication and diagnostics.
- all fallible pointer/result-returning APIs are checked before dereference/use;
- task/context lookup failure that destroys execution-context integrity becomes a framework error;
- xUnit file failure changes publication state, not test truth, and obeys `IF-COU-005`;
- a log API failure must not mutate test truth or be reported as successful logging;
- both PRDs must use the same failure classification and may not create competing platform state authorities.

**Delegated detail:** helper/function names, grouping into one or several private adapter POUs, and target-specific call wrappers may vary if the shared semantics stay intact.

**Verification:** `VER-COU-027` covers task/project lookups; `VER-COU-021` and `VER-COU-031` cover file/publication behavior.

---

# State–Decision–Effect contracts

## SDE-COU-001 — Run lifecycle

| State | Observation | Decision | Effect |
|---|---|---|---|
| `IDLE` | top-level call | bind task and mode if valid | enter `RUNNING`, epoch +1 |
| `RUNNING` | suite(s) open | choose eligible suite(s) by mode | invoke under context |
| `RUNNING` | all applicable suites terminal | normal execution complete | set disposition `NORMAL`; enter `FINALIZING` |
| `RUNNING` | abort flag | stop new suite effects | set disposition `ABORTED`; mark open tests aborted; enter `FINALIZING` |
| any active | framework invariant violation | state unreliable | set disposition `FRAMEWORK_ERROR`; stop new suite effects; mark open tests error; enter `FINALIZING` |
| `BETWEEN_SUITES` | delay expires | next suite may run | enter `RUNNING` |
| `FINALIZING` | canonical snapshot built | execution result committed | enter `COMPLETE` |
| any state | application/library reinitialization | prior run is not resumable | non-retained framework state starts again at `IDLE` |

No suite call occurs after an `ABORTED` or `FRAMEWORK_ERROR` disposition has been fixed.

## SDE-COU-002 — Test lifecycle

| State | Event | Result |
|---|---|---|
| unseen | first enabled `TEST*` | `OPEN` |
| unseen | first disabled `TEST*` | `SKIPPED` |
| `OPEN` | failed assertion | remain `OPEN`, set `HasFailure` |
| `OPEN` | `TEST_FINISHED*` with no failure | `PASSED` |
| `OPEN` | `TEST_FINISHED*` with failure | `FAILED` |
| `OPEN` | run abort | `ABORTED` |
| `OPEN` | framework integrity loss | `ERROR` |
| terminal | repeated finish | no state change |

## SDE-COU-003 — Report publication

| State | Event | Result |
|---|---|---|
| `PENDING` | publication disabled | `DISABLED` |
| `PENDING` | valid final snapshot + enabled | open/start writer, `WRITING` |
| `WRITING` | chunk full | flush successful chunk, remain `WRITING` |
| `WRITING` | final bytes are written/closed and the external-currentness commit succeeds | `WRITTEN`; complete artifact becomes current |
| `WRITING` | required file/writer/commit operation fails | `FAILED`; prior current artifact remains current or absent; staging is non-current |
| `FAILED` | later runner scan | no false success; retry only if an explicit future policy is added |
| any non-retained publication state | application/library reinitialization | new run starts fresh; stale staging must not become current |

Publication failure or restart never rewrites test pass/fail truth. A file consumer may treat only a semantic-commit artifact as current successful output; partial staging is never a semantic commit.
