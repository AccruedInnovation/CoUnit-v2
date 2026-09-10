# Supplemental lifecycle trace

Import `qualification.xml` into a clean isolated application containing the candidate source, replacing the other qualification shard. Call only `PRG_Qualification` from the owner cyclic task. No native run has been performed by this generator.

The fixture calls the existing internal `RunTestSuiteTestsInSequence(TimeBetweenTestSuitesExecution := T#100ms)` method. This is the same runner path used by `RUN_IN_SEQUENCE()`, but it supplies the test delay directly. The immutable production `GVL_Param_coUnit.TimeBetweenTestSuitesExecution` remains unchanged at `T#0MS`; no override or restoration is needed. This supplements the public-facade sequence shard rather than claiming a modified configuration was tested through that facade.

## Run and observe

1. Start the isolated application with `PRG_Qualification.Start = FALSE` (the default). Allow at least one owner-task invocation. Require `PrestartIdle = TRUE`, `ObservedState = IDLE`, `ObservedEpoch = 0`, `ObservedSuiteCount = 3`, and `ThirdRecordCount = 0`. `GVL_LifecycleTrace.Scan`, `EventCount`, all `Visits`, and `DisabledBodyVisits` must be zero. These are observations before the first `RUN`, after normal initialization registered the suites.
2. Set `PRG_Qualification.Start := TRUE`. Leave `HoldThird = FALSE`. Require `Done = TRUE`, `OraclePass = TRUE`, `FailedCheck = 0`. The check-number mapping is the ordered `checks` list in `expected.json`.
3. Inspect `GVL_LifecycleTrace.Order[1..3] = [1,2,3]`, `EntryMs`, `ExitMs`, `EntryScan`, `ExitScan`, and `Visits`. These counters/timestamps are written by fixture bodies independently of canonical CoUnit results. `RegistrationOrderObserved` separately compares registered pointers with the three declared instances.
4. Require `FirstGapMs >= 100` and `SecondGapMs >= 100`. These subtract the preceding fixture body's exit timestamp from the next body's entry timestamp using native `TIME()` milliseconds. There is no upper timing bound: scheduler delays are not a framework error. Avoid a trace spanning the native millisecond-clock rollover.
5. Require `EntryScan[1] = 1`, proving no initial delay, and `CompletedScan = ExitScan[3]`, proving execution completes in the final suite's scan without a trailing delay. Publication work may take additional time and is not a sequence delay.
6. Require `Visits[2] = 1` and `DisabledBodyVisits = 1`, alongside the final middle test state `SKIPPED` and zero assertion count. `TEST` does not suppress arbitrary caller statements: the disabled test's body-side counter intentionally increments once, while the terminal suite must never be revisited.

## Reset during an open test

Begin from a fresh native application initialization. Observe step 1, then set `HoldThird := TRUE` and `Start := TRUE`. Wait for `ThirdRecordAvailable = TRUE`, `ThirdRecordState = OPEN`, and `ObservedState = RUNNING`; record a positive `ObservedEpoch` and third-suite visit count. Perform the user-authorized simulator application reinitialization/reset and restart the owner task. Do not simulate reset by toggling `Start`.

After one task invocation, before setting `Start` again, require all step-1 observations, `Start = FALSE`, `HoldThird = FALSE`, `Done = FALSE`, `ThirdRecordAvailable = FALSE`, `GVL_LifecycleTrace.HoldThird = FALSE`, and all entry/exit timestamps and visit counts zero. Then set `Start := TRUE` for the clean second run and require the normal completion oracle. Record the exact native reset operation; ordinary stop/start is not assumed to reinitialize storage.

Useful monitor roots are `PRG_Qualification` and `GVL_LifecycleTrace`. `FirstRunMs` and `CompletedMs` preserve the overall trace endpoints. `SnapshotBytes` supports the existing qualification memory measurement. No CoUnit assertion acts as an oracle for CoUnit itself.

Regenerate locally with `python dependencies/CoUnit/2.0.0/qualification/lifecycle_trace/generate.py`. The generator only writes within this supplemental fixture directory and never calls native tools.
