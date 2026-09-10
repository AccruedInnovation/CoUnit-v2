# PRD-COU-03 normative reporting and publication design

**Authority:** detailed-design refinement under R3 assignment `PRD-COU-03`.  
**Status:** normative for this PRD candidate. It closes architecture `OPEN-COU-003` at detailed-design level; target qualification remains future evidence.

## 1. Canonical final snapshot

Create private canonical types equivalent to:

```iecst
TYPE E_CoUnitReportState :
(
    DISABLED,
    PENDING,
    WRITING,
    WRITTEN,
    FAILED
);
END_TYPE

TYPE ST_CoUnitSnapshotTest :
STRUCT
    Name : T_MaxString;
    ClassName : T_MaxString;
    State : E_CoUnitTestState;
    NumberOfAsserts : UINT;
    FirstFailure : ST_CoUnitFirstFailure;
END_STRUCT
END_TYPE

TYPE ST_CoUnitSnapshotSuite :
STRUCT
    Name : T_MaxString;
    Identity : UINT;
    Total : UINT;
    Passed : UINT;
    Failed : UINT;
    Skipped : UINT;
    Errors : UINT;
    Tests : ARRAY[1..GVL_Param_coUnit.MaxNumberOfTestsForEachTestSuite] OF ST_CoUnitSnapshotTest;
END_STRUCT
END_TYPE

TYPE ST_CoUnitRunSnapshot :
STRUCT
    IsValid : BOOL;
    Disposition : E_CoUnitRunDisposition;
    SuiteCount : UINT;
    Total : UDINT;
    Passed : UDINT;
    Failed : UDINT;
    Skipped : UDINT;
    Errors : UDINT;
    Suites : ARRAY[1..GVL_Param_coUnit.MaxNumberOfTestSuites] OF ST_CoUnitSnapshotSuite;
END_STRUCT
END_TYPE
```

Equivalent names/field integer widths may follow repository convention if they preserve limits and public projection. `Errors` includes canonical `ABORTED` and `ERROR` test states.

### Snapshot build

- Build exactly once after runner enters `FINALIZING` and fixes disposition.
- Read canonical suite/test records only; never infer terminal truth from legacy result booleans.
- Validate every count/index before bounded copy.
- For each test require one terminal state. If a nonterminal test exists during finalization, convert it only according to PRD-01 abort/error rules before snapshot build; otherwise framework consistency error.
- Narrow `MaxAssertionsPerInvocation` to legacy `UINT` only after proving it is within `UINT` and the configured assertion bound.
- Compute suite counts from copied terminal states, then run counts by summing suite counts.
- Require `Total = Passed + Failed + Skipped + Errors` per suite and run before setting `IsValid=TRUE`.
- Set `IsValid=TRUE` last. After that the snapshot is immutable until reinitialization.

### Snapshot resource gate

The fixed-capacity layout preserves the R3 requirement that the finalized snapshot contain every registered suite/test. It is not assumed to be cheap. Before implementation acceptance, measure the compiled `SIZEOF(ST_CoUnitRunSnapshot)` (or exact equivalent) and the application's relevant static-memory use on the bound target/compiler. At architecture maxima the string fields alone imply at least 80 MiB of declared storage, so a target that cannot fit the full snapshot must stop for an architecture-owned representation decision. No implementation worker may silently lower cardinality or omit snapshot fields.

## 2. Legacy public result projection

Existing `I_TestResults`, `ST_TestSuiteResults`, `ST_TestSuiteResult`, and `ST_TestCaseResult` remain source-compatible.

Projection rules:

- `NumberOfTestSuites` = snapshot suite count.
- `NumberOfTestCases` = snapshot total.
- `NumberOfSuccessfulTestCases` = snapshot passed only.
- `NumberOfFailedTestCases` = snapshot failed only; aborted/error tests are not assertion failures.
- suite `NumberOfTests` = suite total; `NumberOfFailedTests` = suite failed only.
- test `TestIsFailed=TRUE` only for canonical `FAILED`.
- test `TestIsSkipped=TRUE` only for canonical `SKIPPED`.
- test `NumberOfAsserts` = snapshot max-per-single-invocation value unchanged.
- `FailureType`/`FailureMessage` are populated only from an assertion first-failure record. For `ABORTED`/`ERROR`, keep `FailureType=Type_UNDEFINED`; no public success flag exists in the legacy record, so new publishers must never infer pass from `NOT failed AND NOT skipped`.

Do not add public fields without a separate compatibility review.

## 3. Device Log

### `WRITE_DEVICE_LOG`

Required behavior:

1. if `MsgFmtStr` contains `%s`, replace the **first** occurrence with `StrArg` using current source-compatible substitution behavior;
2. if no `%s` exists, emit `MsgFmtStr` unchanged; do not return silently;
3. emit long logical text left-to-right in bounded chunks no larger than the adapter's supported per-entry size; never emit the right tail first;
4. logging failure never changes canonical test/result truth.

### Result logger levels

Always emit:

- detailed first assertion failure events already committed by PRD-02;
- framework errors;
- one final summary with total/passed/failed/skipped/errors;
- xUnit publication failure.

When `GVL_Param_coUnit.LogExtendedResults=TRUE`, also emit per-suite/per-test detail. When false, suppress only that optional detail.

## 4. XML logical schema

The streamed XML uses this semantic structure:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<testsuites tests="TOTAL" failures="FAILED" errors="ERRORS" skipped="SKIPPED">
  <testsuite id="1" name="..." tests="..." failures="..." errors="..." skipped="...">
    <testcase name="..." classname="..." assertions="..."/>
    <testcase name="..." classname="..." assertions="...">
      <failure type="..." message="..."/>
    </testcase>
    <testcase ...><skipped/></testcase>
    <testcase ...><error message="..."/></testcase>
  </testsuite>
</testsuites>
```

`assertions` is permitted as an additive xUnit attribute and, when emitted, shall contain the R3 max-per-single-invocation metric as a nonnegative decimal integer. If a named downstream schema used by the release rejects this attribute, omit the attribute rather than change the metric; parser/consumer meaning still comes from the snapshot and legacy result. PRD-04 records schema-specific compatibility separately.

Terminal state is represented by the child result element only; do **not** emit a separate `status` attribute that can disagree with it. Only one child state element appears for a testcase. `PASSED` has no child result element. `FAILED` uses `<failure type="..." message="...">` (empty values allowed when the canonical first-failure record lacks text). `SKIPPED` uses `<skipped/>`. `ABORTED` and `ERROR` use `<error message="...">`.

## 5. XML dynamic-text encoding and escaping

All report dynamic text is `STRING`/`T_MaxString`. CODESYS can interpret `STRING` project-wide as UTF-8 or as its legacy single-byte encoding depending on the compiler option. The publisher always writes UTF-8 XML, so the repository/target preflight must bind the active `STRING` encoding mode before this slice is dispatched and PRD-04 must record that mode with qualification evidence. Do not assume Windows-1252 for a UTF-8 project.

### Conversion policy

Use one of two bound source modes:

- `UTF8`: source bytes are already UTF-8. Decode bounded code-point sequences without reading past the terminating zero or declared `STRING` byte capacity. Valid XML characters retain their Unicode value; malformed UTF-8 sequences and XML-forbidden code points become U+FFFD. Re-emit the resulting code points as UTF-8. Never reinterpret each source byte as a legacy code page.
- `LEGACY_SINGLE_BYTE`: bind the exact CODESYS legacy single-byte mapping used by the project's compiler/runtime configuration. Decode each nonzero byte through that mapping; XML-forbidden control values and unmappable/invalid values become U+FFFD; emit the resulting code points as UTF-8. CODESYS documentation describes the disabled project-wide UTF-8 setting as the legacy Latin-1/Windows-1252 mode, so exact target behavior must be captured rather than guessed by the library.

For both modes, `0x00` terminates the bounded input. No decoder may read beyond the declared string byte capacity. A malformed UTF-8 tail at the bound is one malformed sequence and becomes U+FFFD; it is not read past the bound.

For XML attribute syntax, escape after code-point decoding/validation:

- `&` -> `&amp;`
- `<` -> `&lt;`
- `>` -> `&gt;`
- `"` -> `&quot;`
- `'` -> `&apos;`

No dynamic text bypasses this one escaper. Integer attributes are produced from bounded integer conversion and can use the same append path.

## 6. Bounded chunk writer

Replace whole-document buffering with one reusable byte chunk of configured size.

### Preconditions

- xUnit publishing disabled -> state `DISABLED`, no file effect.
- final snapshot must be `IsValid=TRUE` before `PENDING`.
- configured current path must be non-empty.
- `xUnitBufferSize` must be at least 16 bytes; smaller -> `FAILED` before file effect.
- the current path plus reserved suffix must fit the library path string type **by stored byte count**, not character count. `T_MaxString=STRING(255)` reserves 255 content bytes and each reserved suffix below is 11 ASCII bytes, so require `PathByteLength(finalPath) <= 244`; otherwise `FAILED` before any filesystem probe/open/rename/delete. `PathByteLength` means the number of nonzero bytes before the first `0x00`, bounded by the declared `STRING` content capacity. Standard `LEN()` is not a valid capacity check in UTF-8 mode because it reports characters while `STRING(n)` capacity is byte-based.
- derive `stage` and `backup` with a bounded byte append that proves each result is NUL-terminated, has exactly `PathByteLength(finalPath)+11` content bytes, and is distinct from `finalPath` and from the other companion. Any overflow, truncation, missing terminator, or alias result is `FAILED` before filesystem effect. A direct `CONCAT` is acceptable only if the bound toolchain proves these same byte-capacity and non-truncation properties.

### Writer rule

`AppendBytes(bytes)` repeats:

1. if no space for the next byte/token, flush current occupied bytes;
2. append only when `used < capacity`;
3. never rely on a C-style terminator inside the file buffer;
4. `Flush` is a no-op if `used=0`;
5. one SysFile write must report both result success and returned byte count exactly equal to `used`; otherwise publication fails;
6. reset `used=0` only after successful full write.

Escaped tokens may span flush boundaries, but their byte sequence remains in correct order. There is no document-size limit other than result cardinality, filesystem/runtime limits and successful writes.

## 7. Publication paths and ownership

Given configured final path `P`, reserve two sibling paths exclusively for CoUnit publication:

```text
stage  = P + '.counit.tmp'
backup = P + '.counit.bak'
```

Enabling xUnit publishing grants CoUnit ownership of these two companion paths. Documentation must warn users not to use them for independent files. No other temp naming scheme is accepted without rechecking restart/currentness semantics.

`P` is the only externally current report identity. Consumers must ignore companion paths.

### Companion-path derivation

`PathByteLength` and the companion builder are part of publication admission, not filesystem recovery:

1. scan only within the declared `T_MaxString` content capacity and stop at the first `0x00`;
2. reject a non-terminated value or any `P` whose content byte count exceeds 244;
3. append the 11 ASCII suffix bytes with a bounded builder; do not append by character count;
4. require `ByteLen(stage)=ByteLen(P)+11` and `ByteLen(backup)=ByteLen(P)+11`;
5. require `stage <> P`, `backup <> P`, and `stage <> backup` by byte comparison;
6. complete all checks before the first `Probe`, `OpenWrite`, `Rename`, or `DeleteIfPresent`.

For the UTF-8 boundary fixture, 122 repetitions of U+00E9 encode to 244 bytes and are admissible; 123 repetitions encode to 246 bytes and must be rejected before file effect even though a character-count `LEN` result is only 123.

## 8. File adapter contract

Provide private checked wrappers with these semantic results:

```text
Probe(path) -> EXISTS(size) | MISSING | ERROR(code)
OpenWrite(path) -> HANDLE | ERROR
WriteAll(handle, bytes) -> OK | ERROR       // checks pResult + exact byte count
FlushIfSupported(handle) -> OK | UNSUPPORTED | ERROR
Close(handle) -> OK | ERROR
Rename(old,new) -> OK | ERROR
DeleteIfPresent(path) -> OK | ERROR
```

`Probe` may use `SysFileGetSize(path,pResult)` or an equivalent existing SysFile call that distinguishes missing from other error. Map the target's exact CmpErrors constant during repository/target binding. Never treat every error as “missing.”

`FlushIfSupported`:

- `ERR_OK` -> `OK`;
- exactly `ERR_NOTIMPLEMENTED` or `ERR_NOT_SUPPORTED` -> `UNSUPPORTED` and continue to close; PRD-04 records this target condition;
- any other result -> `ERROR`.

Close success remains mandatory. PRD-04 must include at least one target read/parse test after a close and before release support claim; lack of explicit flush does not grant power-loss durability and no such claim is made.

## 9. Startup/restart recovery

Before a new publication starts, reconcile companion files using `Probe`:

1. If final `P` is missing and backup exists, attempt `Rename(backup,P)`. Failure -> publisher `FAILED`; do not start a new write.
2. If final exists and backup exists, the only conforming prior-protocol state is “commit succeeded, cleanup did not run.” Delete backup; deletion failure -> `FAILED` before new publication (do not risk overwriting an unknown companion).
3. If stage exists, delete stage. Failure -> `FAILED` before new publication.
4. If final and backup are both missing, that is valid “no current report.”
5. Any probe error other than MISSING -> `FAILED`.

After this reconciliation, stage and backup are absent and final is either a complete prior report or absent.

## 10. Write and semantic commit protocol

### Write phase

1. enter `PENDING` after valid snapshot/config;
2. run startup reconciliation;
3. `OpenWrite(stage)` only; never open `P` for write;
4. enter `WRITING`;
5. stream document in deterministic suite/test registration order;
6. require every `WriteAll` success;
7. flush remaining chunk;
8. call `FlushIfSupported`; fail on real flush error, record unsupported condition otherwise;
9. close stage; close failure -> `FAILED`;
10. optionally/where cheap, `Probe(stage)` and require byte size equal the writer's total emitted byte count; mismatch -> `FAILED`.

At this point stage is complete but still **not current**.

### Commit phase

1. `Probe(P)`.
2. If current final exists:
   - require backup absent after reconciliation;
   - `Rename(P,backup)`. If this fails, set `FAILED`; stage may remain for later cleanup, final remains current.
3. If final was missing, skip backup move.
4. `Rename(stage,P)`.
5. If step 4 succeeds, semantic commit occurs at that instant. Set `WRITTEN`; emit success message only now. Then `DeleteIfPresent(backup)` as post-commit cleanup. Cleanup failure emits a warning but **does not change `WRITTEN`**, because the current report is already the complete newly committed file and backup is non-current.
6. If step 4 fails:
   - if an old final was moved to backup, try `Rename(backup,P)` once;
   - regardless of restore outcome, set `FAILED`, emit publication error, never success;
   - if restore succeeds, prior complete report is current; if restore fails, current report is absent; stage remains non-current and will be cleaned next initialization/publication.

The protocol does not depend on rename-over-existing support and never deletes current before securing it at backup.

## 11. Publication state

- `DISABLED`: no publication requested/effects.
- `PENDING`: valid snapshot/config; no stage handle open yet.
- `WRITING`: stage file may be partial; never current.
- `WRITTEN`: complete stage was closed and successful stage->final rename committed it.
- `FAILED`: required write/close/reconciliation/commit step failed before semantic success.

Publication failure never alters snapshot/test truth.

## 12. Idempotency/retry

One finalized run attempts publication once by default. `FAILED` does not automatically retry in the same run, because repeated filesystem side effects can obscure the primary fault. A new application/library initialization or explicit later approved retry feature starts with the recovery procedure above.

Calling the publisher again after `WRITTEN`, `FAILED`, or `DISABLED` is side-effect free for that run.
