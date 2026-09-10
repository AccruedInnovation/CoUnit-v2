# PRD-COU-02 normative assertion-engine design

**Authority:** detailed-design refinement under R3 assignment `PRD-COU-02`.  
**Status:** normative for this PRD candidate. Public signatures are those enumerated in `assertion-family-map.csv` and remain unchanged.

## 1. One assertion transaction per public assertion call

Every executable public `Assert*` method performs exactly one assertion transaction:

```text
BeginAssertion(assertion_type, message) -> {execute, ordinal | framework_error}
if not execute: return
comparison := Compare...(inputs)
RecordAssertionOutcome(ordinal, assertion_type, comparison, message)
```

Public assertion methods shall **not** call another public assertion method internally. Generic `AssertEquals` and array assertions dispatch only to private comparators/reporters so one public call increments the counters once.

An assertion suppressed because the current test is terminal, skipped, out of ordered position, or otherwise `ShouldExecute=FALSE` performs no comparison and consumes no assertion count.

## 2. `BeginAssertion` and bounded counting

`BeginAssertion` uses the PRD-01 active suite/test context and bound-task validation.

1. validate owner task and active suite/test context;
2. if context is valid but `ShouldExecuteCurrentTest=FALSE`, return `execute=FALSE` without count or failure;
3. **before any counter write**, require `SuiteInvocationAssertionCount < GVL_Param_coUnit.MaxNumberOfAssertsForEachTestSuite`;
4. if the guard fails, request runner `FRAMEWORK_ERROR`, return without incrementing either counter or modifying test failure data;
5. increment `SuiteInvocationAssertionCount` by one;
6. increment current test `InvocationOrdinal` by one;
7. set `MaxAssertionsPerInvocation := MAX(MaxAssertionsPerInvocation, InvocationOrdinal)`;
8. return the current `InvocationOrdinal` as diagnostic context only.

`SuiteInvocationAssertionCount` is reset to zero immediately before each runner-owned suite-body invocation. `InvocationOrdinal` is reset to zero when PRD-01 begins a new accepted current-test segment. No ordinal persists as assertion identity.

The final public `NumberOfAssertions`/`NumberOfAsserts` is `MaxAssertionsPerInvocation`, narrowed only after proving it fits `UINT`. Under the current `UINT` configured assertion maximum, a conforming run cannot exceed that final type.

## 3. Outcome and first-failure commit

Comparison returns:

```text
ST_CoUnitComparisonResult
  Passed : BOOL
  ArgumentError : BOOL
  ExpectedText : T_MaxString
  ActualText : T_MaxString
  DiagnosticSuffix : T_MaxString
```

This is a private logical shape; exact record/helper names may differ.

`ArgumentError` means the assertion inputs are invalid but the fault is safely localizable, for example negative/NaN delta, invalid `ANY` descriptor, or malformed bounded string descriptor. It is recorded as a **failed assertion for the current test**, not as a run framework error.

`RecordAssertionOutcome`:

- if `Passed=TRUE`, does not touch failure fields;
- on failure, sets `HasFailure := TRUE`;
- if `FirstFailure.IsSet=FALSE`, fills **all** first-failure fields from this assertion, then sets `IsSet=TRUE` as the final commit step and emits one detailed failure message;
- if already set, leaves first-failure fields unchanged and emits no second detailed assertion-failure event;
- a later assertion still evaluates and remains part of run/test failure truth even though it does not replace the diagnostic record.

If a platform/language primitive cannot make the multi-field write literally atomic, “atomic” here means no public consumer may observe a mixed record: all fields are written while `IsSet=FALSE`, then `IsSet` is committed last on the sole owner task.

## 4. Diagnostic text bound

Equality is never decided from formatted strings. Expected/actual text is produced only after a failure is known, except when a small primitive conversion is required by an existing private helper.

`T_MaxString` is `STRING(255)`, whose declared size is **255 data bytes plus the terminating zero byte**, not 255 Unicode characters. Diagnostic construction must therefore enforce the destination byte capacity in the bound project's `STRING` encoding. If generated diagnostic text would exceed that byte capacity, keep the longest valid encoded prefix that leaves room for the exact marker:

```text
...<truncated>
```

The marker and terminator must fit inside the declared storage. In UTF-8 mode, truncation must not split a multi-byte sequence. Array diagnostic text records only shape information or the first mismatch; it never serializes the whole array.

## 5. Scalar typed comparisons

Every public typed assertion maps to the exact `E_AssertionType` matching its suffix. `AssertTrue` and `AssertFalse` use `Type_BOOL`. Generic `AssertEquals` uses `Type_ANY` as the public assertion family even when it dispatches to a primitive private comparer.

For BOOL/integer/bit/date/time/string/wstring exact typed methods, compare with the type's existing logical equality behavior. No raw value history is stored.

### REAL/LREAL tolerance — normative algorithm

The following semantics apply to scalar and array REAL/LREAL comparisons. CODESYS defines `REAL` and `LREAL` as IEEE-754 32-bit and 64-bit types. The implementation must classify their raw bit patterns **before any floating-point comparison or arithmetic** so a signaling or quiet NaN cannot reach an instruction that may raise an invalid-operation exception on a target.

Private classification may use `MEMCPY` of exactly `SIZEOF(REAL)`/`SIZEOF(LREAL)` into `DWORD`/`LWORD` and these IEEE-754 masks, or an already-qualified platform helper proven to have the same no-floating-operation classification behavior:

```text
REAL:  exponent=16#7F800000, fraction=16#007FFFFF, sign=16#80000000
LREAL: exponent=16#7FF0000000000000, fraction=16#000FFFFFFFFFFFFF,
       sign=16#8000000000000000
NaN:       exponent all ones AND fraction nonzero
Infinity:  exponent all ones AND fraction zero
Finite:    exponent not all ones
```

Normative comparison:

```text
classify Delta, Expected, Actual from raw bits
if Delta is NaN or (Delta is negative and not zero):
    argument-error failure
else if Expected is NaN or Actual is NaN:
    fail
else if Expected and Actual are infinities:
    pass iff their signs match
else if exactly one of Expected/Actual is infinite:
    fail
else if Delta is +Inf:
    pass                 // both operands are finite here
else if Expected = Actual:
    pass                 // finite equality, including +0/-0
else if Expected and Actual have opposite signs:
    a := ABS(Expected)
    b := ABS(Actual)
    if Delta < a:
        fail
    else:
        pass iff b <= (Delta - a)
else:
    pass iff ABS(Expected - Actual) <= Delta
```

Negative zero is not an invalid delta. `Delta=+Inf` is allowed by the upstream contract. Once raw classification has excluded NaN/infinite operands from the finite arithmetic path, the opposite-sign branch avoids overflowing a subtraction solely to test tolerance.

Qualification must include quiet-NaN bit patterns and, where the bound compiler/runtime preserves them, signaling-NaN bit patterns constructed through raw bits rather than floating-point arithmetic. If a target cannot preserve a signaling-NaN fixture, that subcase is `INCONCLUSIVE`; it must not be reported as executed evidence.

## 6. Array comparison

One array method call is one assertion.

- Compare extent in every dimension, not absolute lower-bound identity.
- Equal extents with different lower bounds are compared by corresponding offset from each lower bound, preserving current source behavior.
- Shape mismatch fails before element reads outside the shared valid shape.
- Equal shape: iterate in deterministic dimension order and stop equality work at the first mismatch.
- REAL/LREAL elements use the exact scalar floating rule above.
- Diagnostic expected/actual text states either all relevant extents or the first mismatching pair of logical offsets/values. No array content history is retained.

## 7. Generic `AssertEquals(ANY, ANY)`

CODESYS represents an `ANY` argument using type class, `pValue`, and `diSize`. The implementation must validate descriptors before any read/copy.

### Validation/order

1. `pValue` for both descriptors must be non-null; otherwise local argument-error failure.
2. `diSize` for both must be `>= 0`; otherwise local argument-error failure.
3. Type classes unequal -> ordinary assertion failure; do not reinterpret bytes.
4. `STRING`/`WSTRING` use logical bounded string comparison below and do **not** require equal storage sizes.
5. Other known primitive types require `diSize = SIZEOF(type)` on both sides before copy/dereference; bad size -> local argument-error failure.
6. For any remaining same-type values, require equal `diSize`; unequal size -> ordinary assertion failure. Equal size -> representation equality over exactly `diSize` bytes. Zero-size equal representations compare equal.

### STRING

Do not `MEMCPY` arbitrary `diSize` into `T_MaxString`.

- Treat the descriptor as a bounded sequence of bytes in the target's CODESYS `STRING` encoding.
- Search for the first zero terminator without reading at or beyond `diSize`.
- Missing terminator inside the descriptor bound -> local argument-error failure.
- Compare byte values up to the terminator; declared capacities may differ.

### WSTRING

- Require `diSize` to be a nonnegative multiple of `SIZEOF(WCHAR/WORD-equivalent code unit)` used by the bound compiler.
- Search bounded code units for the zero terminator.
- Missing terminator -> local argument-error failure.
- Compare logical code units up to the terminator; capacities may differ.
- Bind the exact native code-unit type at repository/compiler preflight; do not assume host-language UTF representation.

### Known primitive dispatch

After exact descriptor size validation, copy exactly `SIZEOF(type)` to local typed values or use an equivalent safely aligned read, then call a **private** type comparator. This must not invoke the public wrapper and must not increment count again.

Known primitives include the existing CoUnit scalar assertion types: BOOL, BYTE, WORD, DWORD, LWORD, SINT, INT, DINT, LINT, USINT, UINT, UDINT, ULINT, REAL, LREAL, TIME, LTIME, DATE, DATE_AND_TIME, TIME_OF_DAY. Generic STRING/WSTRING follow the logical path above.

### Unsupported/user-defined values

After equal type and size checks, compare `pValue[i]` for each byte `i = 0 .. diSize-1`. This is explicitly **representation equality**, not domain-semantic equality. It covers `TYPE_USERDEF` and other unsupported same-type values without a fixed union buffer.

No generic comparison may use `U_ExpectedOrActual`, copy an arbitrary object into a fixed-size union/string, or retain expected/actual bytes after the call returns.

## 8. Obsolete tracker migration

The canonical path shall no longer read/write `FB_AssertResultStatic`, `FB_AssertArrayResultStatic`, `ST_AssertResult*`, `ST_AssertArrayResult*`, or cycle-detection counts for assertion repeat suppression.

Implementation choices:

- delete them if repository/public compatibility permits; or
- keep them as unused compatibility objects with no references from the execution path.

`CalculateAndSetNumberOfAssertsForTest` shall not calculate from tracker history. It may become a compatibility wrapper that copies the canonical max count, or be removed if non-public/internal use allows.

## 9. Failure classification

- assertion capacity guard failure -> `FRAMEWORK_ERROR`, no assertion count/failure record update for the rejected call;
- invalid assertion argument that can be localized -> current test failure, `ArgumentError=TRUE`, no run abort;
- ordinary unequal values -> current test failure;
- invalid owner task/active context -> PRD-01 framework/context rule;
- skipped/terminal/non-current ordered test -> assertion suppressed, no count/comparison/failure.
