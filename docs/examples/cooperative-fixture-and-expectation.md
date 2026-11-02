# Cooperative fixture and temporal expectation helpers

These helpers advance one callback per PLC scan and keep test ownership in the caller's suite. They do not start runner tests or assert on the runner's behalf. A caller begins the logical test once, then calls `Observe` or `Execute` on each scan with a stable `ST_CoUnitFixtureKey`.

The key contains `RunId`, `SuiteId`, `CaseId`, `RowKey`, `AttemptId`, and `StepId` as `STRING(63)`. A suite-level check may use an empty `CaseId`; it must still provide stable run, suite, row, attempt, and step identity. A mismatched key is rejected without changing the active state.

## Temporal expectations

Call `FB_CoUnitExpectation.Start` while idle or after a terminal result, passing the key, mode, current monotonic `LTIME`, and duration. Call `Observe` every scan with that same key, the current `LTIME`, condition, and cancellation flag.

- `EVENTUALLY_TRUE` and `STEP` pass on the first true observation at or before the inclusive deadline. A true observation after the deadline fails.
- `REMAINS_TRUE` fails on any false observation, including at the deadline; it passes on the first matching observation at or after the deadline.
- `REMAINS_FALSE` fails on any true observation, including at the deadline; it passes on the first matching observation at or after the deadline.
- Cancellation resolves to `CANCELLED`. Terminal state remains stable. `Resolved` pulses once on the transition into a terminal state.
- Negative duration, negative or regressing time, unsupported mode, overflow, and stale identity are rejected. Rejection does not reset the active expectation. A completed key cannot be started again; use a fresh attempt or step identity.

Use a monotonic timestamp such as `LTIME()` in production. PLC scans can only observe a condition at scan boundaries, so a short-lived transition between scans cannot be detected. Deterministic tests should pass explicit `LTIME` values.

### Complete temporal suite example

This local example waits across three cyclic invocations. Create an FB with this
declaration and instantiate it in the persistent program calling `CoUnit.RUN()`:

```iecst
FUNCTION_BLOCK FB_WaitExample EXTENDS CoUnit.FB_TestSuite
VAR
	_expectation : CoUnit.FB_CoUnitExpectation;
	_key : CoUnit.ST_CoUnitFixtureKey;
	_state : CoUnit.E_CoUnitTemporalResult;
	_stateText : CoUnit.T_MaxString;
	_now : LTIME;
	_started : BOOL;
	_cycles : UINT;
	_phaseAccepted : BOOL;
END_VAR
```

Its implementation is:

```iecst
IF CoUnit.TEST_GUARDED(TestName := 'ReadyWithinOneSecond') THEN
	_phaseAccepted := ReportPhase(Phase := CoUnit.E_CoUnitFixturePhase.BODY,
		StepId := 'ready/await');
	AssertResult(Passed := _phaseAccepted, CheckId := 'progress/await',
		Message := 'Waiting progress accepted', ExpectedText := 'TRUE',
		ActualText := BOOL_TO_STRING(_phaseAccepted), Detail := 'Before observation');
	_now := LTIME();
	IF NOT _started THEN
		_key.RunId := 'example-run';
		_key.SuiteId := 'example.wait';
		_key.CaseId := 'ready';
		_key.RowKey := 'default';
		_key.AttemptId := 'attempt-1';
		_key.StepId := 'wait-ready';
		_started := _expectation.Start(Key := _key,
			Mode := CoUnit.E_CoUnitTemporalMode.EVENTUALLY_TRUE,
			Now := _now, Duration := LTIME#1s);
		IF NOT _started THEN
			AssertResult(Passed := _started, CheckId := 'ready/start',
				Message := 'Expectation start', ExpectedText := 'TRUE',
				ActualText := BOOL_TO_STRING(_started), Detail := 'Original start decision');
			CoUnit.TEST_FINISHED();
		END_IF
	END_IF
	IF _started THEN
		_cycles := _cycles + 1;
		_state := _expectation.Observe(Key := _key, Now := _now,
			Condition := _cycles >= 3, Cancel := CoUnit.COUNIT_CANCELLED());
		IF _state <> CoUnit.E_CoUnitTemporalResult.WAITING THEN
			CASE _state OF
				CoUnit.E_CoUnitTemporalResult.PASSED: _stateText := 'PASSED';
				CoUnit.E_CoUnitTemporalResult.FAILED: _stateText := 'FAILED';
				CoUnit.E_CoUnitTemporalResult.CANCELLED: _stateText := 'CANCELLED';
				CoUnit.E_CoUnitTemporalResult.REJECTED: _stateText := 'REJECTED';
			ELSE
				_stateText := 'Unexpected result';
			END_CASE
			AssertResult(Passed := _state = CoUnit.E_CoUnitTemporalResult.PASSED,
				CheckId := 'ready/within-deadline', Message := 'Ready within one second',
				ExpectedText := 'PASSED', ActualText := _stateText,
				Detail := 'Terminal observation after start');
			CoUnit.TEST_FINISHED();
		END_IF
	END_IF
END_IF
```

A rejected Start finishes immediately: observation and downstream readiness remain
untested. The captured `_state` is the terminal typed result; preserve the actual run and
fixture identity in real reports. Each invocation advances the expectation at most once.
Replace the cycle condition with the DUT observation. This example's fixed key
belongs to one fresh application; a CI fixture uses its actual run identity and
a new attempt/step key for a new attempt. Helpers and callback instances must
remain in suite storage across scans. The native helper oracle exercises the
underlying boundary semantics; this illustrative suite is not an additional
qualified target row.

## Cooperative fixtures

Implement `I_CoUnitFixture.Setup`, `Body`, and `Cleanup`. Each returns `PENDING`, `PASSED`, or `FAILED`; a pending callback gets another invocation on a later scan. `FB_CoUnitFixture.Start` accepts an absolute clock origin, per-phase timeout, and cleanup budget. `Execute` invokes at most one callback each scan.

Setup failure prevents body entry. Once setup has been entered, cleanup runs even if setup later fails or cancellation/timeout occurs. The first setup/body/cancel/timeout cause remains in `PrimaryCause`; `CleanupOutcome` independently reports pass, failure, or an incomplete cleanup budget. `Complete` becomes true only after cleanup resolves or its budget expires. Phase callbacks after their deadline are not invoked; cleanup callbacks after the cleanup deadline are skipped. Exact-deadline callback results are admissible. Start is rejected while active or for a previously completed key; starting with fresh identity is an explicit new attempt, not an implicit reset.

After `Observe` resolves or the fixture reaches `Complete`, the owning suite may submit exactly one `AssertResult` inside its `BeginCase` guard. Include the structured key fields in `CheckId`; report the temporal/fixture result as `Passed`, and pass expected, actual, and detail strings for the independent oracle.

See `qualification/upgrade_helpers.py` and its generated XML/expected JSON for a cyclic, deterministic helper qualification fixture. The JSON is an independent expected-outcome record; generated source alone is not native qualification.

The fixture copies the interface binding at Start; the callback object must outlive
the fixture. Rebinding the caller's interface variable cannot redirect an active
fixture. Invalid or null bindings are rejected. When cleanup is required, call
ReportFixture with PENDING after entering setup and again with the helper's
PrimaryCause/CleanupOutcome before TEST_FINISHED. This preserves cleanup failure
or incompleteness independently from the first assertion; finishing a case with
cleanup pending becomes an error. Use a separate suite-owned helper for a shared
suite fixture; setup must complete before any dependent case body is entered.
