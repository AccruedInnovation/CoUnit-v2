# PRD-COU-01 normative execution-core design

**Authority:** detailed-design refinement under `COUNIT-ARCH-R3` assignment `PRD-COU-01`.  
**Status:** normative for this PRD candidate. Public API signatures remain governed by architecture `IF-COU-001`; names below are private implementation names and may change only where the PRD says they are local choices.

## 1. Canonical private types

The worker shall add equivalent private types. Numeric enum values may differ; semantic variants may not.

```iecst
TYPE E_CoUnitRunState :
(
    IDLE,
    RUNNING,
    BETWEEN_SUITES,
    FINALIZING,
    COMPLETE
);
END_TYPE

TYPE E_CoUnitRunDisposition :
(
    UNSET,
    NORMAL,
    ABORTED,
    FRAMEWORK_ERROR
);
END_TYPE

TYPE E_CoUnitRunMode :
(
    MODE_UNSET,
    ALL_SUITES,
    IN_SEQUENCE
);
END_TYPE

TYPE E_CoUnitTestState :
(
    OPEN,
    PASSED,
    FAILED,
    SKIPPED,
    ABORTED,
    ERROR
);
END_TYPE

TYPE ST_CoUnitFirstFailure :
STRUCT
    IsSet : BOOL;
    AssertionType : E_AssertionType;
    Message : T_MaxString;
    ExpectedText : T_MaxString;
    ActualText : T_MaxString;
END_STRUCT
END_TYPE

TYPE ST_CoUnitTestRecord :
STRUCT
    InUse : BOOL;
    CanonicalName : T_MaxString;
    DefinedDisabled : BOOL;
    IsOrdered : BOOL;
    OrderNumber : UINT;
    State : E_CoUnitTestState;
    HasFailure : BOOL;
    FirstSeenEpoch : ULINT;
    LastSeenEpoch : ULINT;
    DuplicateReportedEpoch : ULINT;
    InvocationOrdinal : UDINT;
    MaxAssertionsPerInvocation : UDINT;
    FirstFailure : ST_CoUnitFirstFailure;
END_STRUCT
END_TYPE
```

`InvocationOrdinal`, `MaxAssertionsPerInvocation`, and `FirstFailure` are written by PRD-02 but live in the canonical test record established here. `UDINT` prevents arithmetic from failing before the configured `UINT` assertion limit can be checked. PRD-03 narrows the final count only after proving it fits the legacy field.

## 2. Runner-owned state

`FB_coUnitRunner` is the sole mutable owner of:

- `RunState : E_CoUnitRunState := IDLE`
- `RunDisposition : E_CoUnitRunDisposition := UNSET`
- `RunMode : E_CoUnitRunMode := MODE_UNSET`
- `Epoch : ULINT := 0`
- `BoundTaskHandle : RTS_IEC_HANDLE` plus `BoundTaskValid : BOOL`
- bounded suite registry and `SuiteCount`
- active suite/test indices and `ShouldExecuteCurrentTest`
- sequence suite cursor and inter-suite timer state
- `SuiteInvocationAssertionCount : UDINT` (PRD-02 writes under runner authority)
- `CrossTaskViolationLatch : DWORD := 0`
- framework-error reason/code sufficient for one bounded diagnostic

All current-run state is non-retained and non-persistent. Library/application reinitialization reconstructs defaults and begins at `IDLE`.

The existing `GVL_coUnit` current-suite/current-test variables may remain during migration only as **compatibility/debug projections** written by the runner. Core logic must not read them as authority after slice `COU01-S2` completes.

## 3. Task ownership and cross-task fault latch

### 3.1 Normative rule

A foreign task must not write complex runner, suite, test, result, publisher, or global compatibility-projection state. It may only set `CrossTaskViolationLatch` by the CODESYS atomic operator:

```iecst
dwPrevious := TEST_AND_SET(CrossTaskViolationLatch);
RETURN;
```

The bound owner task checks the latch before and after every suite-body invocation and at the start of each public entry path that can mutate the run. If set, the owner task transitions to `FRAMEWORK_ERROR`, marks known open tests `ERROR` during finalization, and clears the latch only after the framework-error state has been accepted by the owner.

This is a one-way notification, not a lock. No foreign task waits for the owner and no semaphore protects shared execution.

### 3.2 Task identity helper

Create one private adapter with this semantic contract:

```text
TryGetCurrentTaskHandle() -> {ok, handle, error}
```

It shall use the installed CmpIecTask APIs available in the bound repository/target and check all fallible results/pointers before use. The current `GetCurTaskInfo` implementation is evidence, not a required helper shape.

- On the first valid top-level run call in `IDLE`, failure to obtain a current task handle prevents run start and emits a bounded diagnostic; no suite/test state changes.
- During an active run, identity lookup failure sets the atomic violation latch and returns without complex mutation. The next valid owner call converts it to `FRAMEWORK_ERROR`.
- If current handle differs from `BoundTaskHandle`, set the latch and return.
- If current handle matches, owner mutation may proceed.

## 4. Name canonicalization

One helper is authoritative for registration, lookup, named finish, `IS_TEST_FINISHED`, and results:

```text
CanonicalizeTestName(input) -> {valid, canonical_name, disabled}
```

Algorithm:

1. trim leading and trailing spaces using the same logical trim behavior as the existing source;
2. compare the **leading** characters case-insensitively with `DISABLED_`;
3. when present, set `disabled=TRUE` and remove exactly that prefix from the trimmed original-casing string;
4. trim again only if removal exposes spaces that were part of the prefix boundary;
5. reject an empty canonical name as localized misuse;
6. preserve case for the canonical stored name; normal names remain case-sensitive.

The helper never lowercases the stored identity.

## 5. Suite registration

`FB_TestSuite.FB_init` registers `THIS` through the runner. The runner performs:

```text
if state != IDLE: framework error or initialization rejection before registry mutation
if suite pointer invalid: reject before registry mutation
if suite_count >= MaxNumberOfTestSuites: framework error; no count or array write
index := suite_count + 1
registry[index] := suite pointer
suite_count := index
```

No array write may use a candidate index until the capacity check succeeds. The worker shall not maintain a second authoritative suite count.

## 6. Test registration and invocation

Each `FB_TestSuite` owns:

- `TestRecords[1..MaxNumberOfTestsForEachTestSuite]`
- `NumberOfTests : UINT`
- `NumberOfOrderedTests : UINT`
- `OrderedCursor : UDINT := 1`
- `HasBeenInvoked : BOOL`

### 6.1 `BeginTest`

Public `TEST` and `TEST_ORDERED` delegate to one runner/suite path. Normative algorithm:

1. validate owner task and active suite invocation context;
2. canonicalize the supplied name;
3. find an existing record by exact canonical name among `1..NumberOfTests`;
4. if absent:
   - check `NumberOfTests < MaxNumberOfTestsForEachTestSuite` **before** write;
   - if ordered, check `NumberOfOrderedTests < MaxNumberOfTestsForEachTestSuite` before increment;
   - initialize one complete record at `index := NumberOfTests + 1`;
   - if disabled, initialize `State := SKIPPED`; otherwise `State := OPEN`;
   - for ordered record assign `OrderNumber := NumberOfOrderedTests + 1`, then commit `NumberOfOrderedTests`;
   - commit `NumberOfTests := index` last;
   - if the newly committed record is ordered **and already terminal** (notably `SKIPPED`), run `AdvanceOrderedCursorPastTerminalRecords()` immediately before deciding `ShouldExecute`; this is a registration-time terminal case, not a later transition;
5. if present, require the call shape (`ordered` versus normal and disabled declaration) to match the first definition. A shape conflict is localized misuse: bounded diagnostic, `ShouldExecute=FALSE`, no record change;
6. if `LastSeenEpoch = runner.Epoch`, this is a duplicate definition in the same top-level invocation. Emit at most one bounded duplicate diagnostic for that record/epoch, set `ShouldExecute=FALSE`, and do not alter another test;
7. otherwise set `LastSeenEpoch := runner.Epoch`, reset `InvocationOrdinal := 0`, set active suite/test indices;
8. if state is terminal, `ShouldExecute=FALSE`;
9. for a normal open test, `ShouldExecute=TRUE`;
10. for an ordered open test, `ShouldExecute=(OrderNumber = OrderedCursor)`.

`TEST`/`TEST_ORDERED` return/control only whether the caller's test body should run; they do not create an assertion identity.

### 6.2 Duplicate meaning

`Epoch` increments once per accepted owner-task top-level call to `RUN` or `RUN_IN_SEQUENCE`. Therefore a test seen once on each scan is a normal repeated invocation; the same canonical test declared twice inside the same accepted suite invocation is a duplicate-definition misuse.

## 7. Finish/query behavior

### `TEST_FINISHED()`

- Requires valid owner-task, active-suite, active-test context.
- If the active record is terminal, it is idempotent and changes nothing.
- If `ShouldExecuteCurrentTest=FALSE`, it changes nothing except an optional localized diagnostic when the call itself is invalid.
- For an executable open record: set `FAILED` if `HasFailure`, otherwise `PASSED`.
- After terminalizing an ordered record, advance the ordered cursor as described below.
- Clear only the active-test transient context; never change another test.

### `TEST_FINISHED_NAMED(name)`

- Canonicalize and look up the supplied name within the active suite.
- Unknown/invalid name: localized misuse, bounded diagnostic, no test/run mutation.
- Known terminal record: idempotent.
- Known open record: set `FAILED` when `HasFailure`, else `PASSED`.
- Do **not** replace the current active-test identity, reset its assertion ordinal, or mark an unrelated current test finished.
- If the target is ordered, advance the cursor only through the now-terminal leading ordered records.

### `IS_TEST_FINISHED(name)`

- Validate the bound owner task **before** reading suite/test records. A foreign task may set only the PRD-01 atomic violation latch and returns `FALSE`; it must not read complex mutable suite/test state.
- No valid active suite: return `FALSE` and emit at most a bounded localized diagnostic; never dereference an invalid pointer.
- Unknown name: return `FALSE`.
- Known test: return `TRUE` for `PASSED`, `FAILED`, `SKIPPED`, `ABORTED`, or `ERROR`; `FALSE` for `OPEN`.

## 8. Ordered cursor

`OrderedCursor` is a `UDINT`, not a constrained `UINT`, and may hold `NumberOfOrderedTests + 1` as the exhausted sentinel.

Run `AdvanceOrderedCursorPastTerminalRecords()` both (a) after any later transition of an ordered test to a terminal state and (b) immediately after registration commits an ordered record that is already terminal:

```text
while OrderedCursor <= NumberOfOrderedTests:
    find record whose OrderNumber = OrderedCursor
    if missing: framework error (internal consistency defect)
    if record.State is terminal: OrderedCursor++
    else: break
```

A disabled ordered test therefore advances the cursor during its first registration call when it occupies the current ordered position; it cannot leave the following ordered test permanently blocked.

## 9. Suite completion

A suite sets `HasBeenInvoked=TRUE` immediately before or at the start of its first valid runner-owned body invocation. `AreAllTestsFinished` is pure with respect to test state:

```text
if not HasBeenInvoked: FALSE
if NumberOfTests = 0: TRUE
for i in 1..NumberOfTests:
    if not terminal(TestRecords[i].State): FALSE
TRUE
```

No `FirstCycle` heuristic, task-cycle count, temporary finished count, or capped-loop fallback is used.

## 10. Run lifecycle

### 10.1 Top-level call acceptance

`RUN()` requests mode `ALL_SUITES`; `RUN_IN_SEQUENCE()` requests `IN_SEQUENCE`.

- `IDLE`: validate task; bind `BoundTaskHandle`; set mode; set disposition `UNSET`; increment `Epoch`; enter `RUNNING`.
- `RUNNING`/`BETWEEN_SUITES`: owner task + same mode -> increment `Epoch` once and progress one scan of work.
- mode mismatch after binding -> `FRAMEWORK_ERROR`.
- `FINALIZING`: no suite invocation; only finalization may progress.
- `COMPLETE`: no suite invocation. PRD-03 may progress an enabled publisher if its contract allows calls after completion.

Epoch overflow is a framework error before wrap. A release shall not silently wrap `ULINT` epoch identity.

### 10.2 All-suites mode

Within one accepted top-level call:

1. check violation latch;
2. if no registered suites, set disposition `NORMAL` and enter `FINALIZING`;
3. visit registered suites in stable registration order;
4. skip suites already terminal;
5. before each nonterminal suite invocation, establish active suite context, `HasBeenInvoked`, and reset PRD-02's `SuiteInvocationAssertionCount`;
6. call the suite body once;
7. clear transient suite/test context on return even when the suite remains open;
8. check violation latch again and stop further suite calls if set;
9. after the loop, if every suite is terminal, set disposition `NORMAL` and enter `FINALIZING`.

### 10.3 Sequence mode

- `SequenceSuiteIndex` begins at `1`.
- Skip terminal suites, including empty suites that became terminal after their valid invocation.
- Invoke only `SequenceSuiteIndex` while it is nonterminal.
- When it becomes terminal, advance to the next suite. If there is another suite and configured delay is nonzero, enter `BETWEEN_SUITES`; otherwise continue on a later top-level invocation without extra delay.
- The delay is between completed suite N and first invocation of suite N+1 only. It is not required before suite 1 or after the final suite.
- When the cursor exceeds `SuiteCount`, set disposition `NORMAL` and enter `FINALIZING`.

No temporary “number finished this call” counter determines terminal state.

## 11. Abort and framework error

Abort request from the bound owner task:

1. set disposition `ABORTED`;
2. convert every known `OPEN` test to `ABORTED`;
3. leave `PASSED`, `FAILED`, `SKIPPED`, and already-error tests unchanged;
4. stop suite invocation and enter `FINALIZING`.

Framework error accepted by owner task:

1. preserve the first framework-error reason;
2. set disposition `FRAMEWORK_ERROR`;
3. convert every known `OPEN` test to `ERROR`;
4. leave other terminal states unchanged;
5. stop suite invocation and enter `FINALIZING`.

These states are not assertion failures. PRD-03 maps them to result/error output.

## 12. Error precedence

Within one owner-task call, precedence is:

1. already-latched cross-task/context-integrity failure;
2. current task-identity failure/mismatch;
3. run-mode mismatch or internal invariant failure;
4. explicit abort request;
5. bounded localized test misuse;
6. ordinary test/assertion result.

Once `FRAMEWORK_ERROR` is accepted, later abort/test outcomes cannot downgrade it. Once `ABORTED` is accepted, later test calls cannot resume execution.

## 13. Compatibility surface

The following public call shapes remain unchanged: `RUN`, `RUN_IN_SEQUENCE`, `TEST`, `TEST_ORDERED`, `TEST_FINISHED`, `TEST_FINISHED_NAMED`, `IS_TEST_FINISHED`, `FB_TestSuite` inheritance, and all assertion method signatures. Internal globals/fields may be retained for binary/source compatibility only when the active repository requires it; any such field must be a projection and must not become a second state authority.
