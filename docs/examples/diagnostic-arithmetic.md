# Guarded diagnostic arithmetic

The [source objects](diagnostic-arithmetic/) are executable example input targeting the current installed CoUnit. Create a suite extending
`CoUnit.FB_TestSuite`, add the following method, and call `DiagnosticArithmetic()`
from its suite body on each invocation. Instantiate only the selected suite in
the persistent runner, and call one CoUnit runner cyclically from one task.
This example has not yet been native qualified.

Method DEC:

```iecst
METHOD DiagnosticArithmetic
VAR
	_actual : DINT;
	_phaseAccepted : BOOL;
END_VAR
```

Method IMP:

```iecst
IF CoUnit.TEST_GUARDED(TestName := 'DiagnosticArithmetic') THEN
	_phaseAccepted := ReportPhase(Phase := CoUnit.E_CoUnitFixturePhase.BODY,
		StepId := 'arithmetic/observe');
	AssertResult(Passed := _phaseAccepted, CheckId := 'progress/admission',
		Message := 'Progress accepted in active test context',
		ExpectedText := 'TRUE', ActualText := BOOL_TO_STRING(_phaseAccepted),
		Detail := 'Before arithmetic observation');
	_actual := DINT#6 * DINT#7;
	AssertResult(Passed := _actual = DINT#42, CheckId := 'arithmetic/product',
		Message := 'Multiplication result', ExpectedText := '42',
		ActualText := DINT_TO_STRING(_actual), Detail := 'Sampled in this invocation');
	_phaseAccepted := ReportPhase(Phase := CoUnit.E_CoUnitFixturePhase.COMPLETE,
		StepId := 'arithmetic/complete');
	AssertResult(Passed := _phaseAccepted, CheckId := 'progress/complete',
		Message := 'Completion phase accepted', ExpectedText := 'TRUE',
		ActualText := BOOL_TO_STRING(_phaseAccepted), Detail := 'Before TEST_FINISHED');
	CoUnit.TEST_FINISHED();
END_IF
```

For bounded native qualification select exactly this case in a disposable
application with installed .6 and fresh XML/JSON paths. Expect one passing case
and three assertions. In a separately identified negative application, change
only the product comparison to `DINT#43` and ExpectedText to `'43'`; retain the
same CheckId and detail. Expect one failed case, expected 43 and actual 42 in
both raw reports. Do not include that negative variant in normal passing
selections. Preserve raw reports, exact inventory, identities, publisher outcomes
and exact resource cleanup. A source example or a completed report alone is not
native acceptance.
