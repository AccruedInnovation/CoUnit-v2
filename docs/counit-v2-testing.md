# CoUnit v2 testing for agents

For **CoUnit 2.1.0.7** installation, guarded/catalog/temporal APIs,
structured diagnostics and migration, use the [2.1 guide](2.1-upgrade.md) and its
examples. Confirm the exact installed provider and matched host route. Qualification
is bounded to the documented journeys; historical 2.0 examples below are not
a new .6 native qualification. Existing jobs keep their pins until deliberately
migrated. Disable **Qualified access only** if existing source uses the unqualified
`TEST` and `TEST_FINISHED` calls shown in those historical examples.

The source under `compatibility/1.2.0.3` is historical. Test Manager's `TM.Testcase` and TcUnit are different providers; do not substitute their lifecycle or assertion APIs. This consumer guide complements [framework qualification](../qualification/README.md), whose deliberately failing and internal fault-injection fixtures have different acceptance oracles.

## Runner ownership

Suite instances extend `CoUnit.FB_TestSuite` and register automatically during initialization. **CoUnit invokes the registered suites in its own execution context.**

- Declare only the selected suite instances in persistent program/FB storage. Omitting a direct call does not exclude an instantiated suite from registration.
- Call exactly one of `CoUnit.RUN()` or `CoUnit.RUN_IN_SEQUENCE()` cyclically from one task. Keep that choice unchanged through finalization and completion.
- Never also call `Suite()` from PRG_TEST or a task call entry. The suite body itself still calls its test methods.
- Do not use multiple test runners/tasks against the same CoUnit globals. The v2 run is owned by one task.
- Respect the installed capacity settings. The maintained release defaults to 32 registered suites and 2,048 tests per suite. Sequential mode does not bypass registration capacity; use separate native shards for a large inventory.

Minimal runner declaration (DEC):

```iecst
PROGRAM PRG_TEST
VAR_OUTPUT
	bTestComplete : BOOL;
END_VAR
VAR
	Suite : FB_Example_Test;
	Init : BOOL;
END_VAR
```

Runner implementation (IMP):

```iecst
IF NOT Init THEN
	// Replace this filename with the current run's unique report name.
	GVL_coUnit.xUnitFilePath := 'coUnit_xunit_testresults_CURRENT_RUN.xml';
	Init := TRUE;
END_IF
CoUnit.RUN();
bTestComplete := GVL_coUnit.coUnitRunner.AreAllTestSuitesFinished();
```

Set the report path before the first RUN call. Keep RUN executing while the host waits for the complete fresh report. A completion flag alone is not a passing result. For framework qualification, use `qualification/generate_native.py` and its generated PRG_Qualification. Consumer programs follow the runner pattern above.

An optional diagnostic JSON sidecar is available in the current version: set the library reference parameter `DiagnosticJsonEnablePublish` to `TRUE` before building and bind a distinct fresh run-specific path to `GVL_coUnit.DiagnosticJsonFilePath` before the first RUN call. The default is `FALSE`, so existing consumers continue to publish xUnit only. Observe the JSON publisher's own state, phase, file-error and cleanup-warning getters; XML publication success does not imply JSON success. Bind the requested path to the same exact run in the host completion record and capture it before runtime cleanup. See [report acceptance](../REPORTING.md) and [reporting qualification](../qualification/README.md).

## Test methods and isolation

Prefer `TEST_GUARDED` or catalog `BeginCase` for new cases. Call the chosen entry before assertions, and `TEST_FINISHED()` after the case's final required observation. Keep names stable and reconcile them against the selected inventory. Both positional names and `TEST(TestName := 'Name')` are accepted by the API; ensure your host inventory extractor handles the syntax you use.

`TEST()` is not a Structured Text control-flow guard. Discovery and later invocations can execute statements after it even when assertions are not being recorded. `RUN_IN_SEQUENCE()` does not make shared mutable fixtures safe. Give stateful cases independent suite-owned FBs, phase counters and observations; do not declare FB fixtures in method-local VAR storage. Use persistent fixture storage even where an older example shows a method-local FB; CODESYS SA0167 flags those temporary instances.

Reset fixtures through their supported public reset methods, check meaningful BOOL returns, and restore inputs/configuration needed by the next stimulus. Never clear an entire FB with SysMemSet, assign a constructor expression to reset it, or mutate CoUnit's private state in consumer tests. The documented internal hooks in framework qualification are deliberate, isolated exceptions and must not ship in the library. A product reset does not reset the framework's test registration. Preserve the terminal/cleanup behavior being tested instead of forcing private state to make a fixture resettable.

The suite body must continue calling its test methods on each framework invocation. Do not return early from that body because a custom `LifecycleComplete` flag is true. Individual methods may return while a multi-cycle case is unfinished. After the final stimulus, retain the observations and continue presenting its assertions/completion without repeating destructive work.

## Multi-cycle tests

Use a suite-owned phase machine to perform one intended step per invocation. This self-contained example supplies the FB_Example_Test used by the runner above; it needs only CoUnit and the CODESYS LTIME() builtin.

Suite declaration (DEC):

```iecst
FUNCTION_BLOCK FB_Example_Test EXTENDS CoUnit.FB_TestSuite
VAR
	_phase : UINT;
	_first : LTIME;
	_advanced : BOOL;
END_VAR
```

Suite implementation (IMP):

```iecst
ClockAcrossScans();
```

Child method declaration (DEC):

```iecst
METHOD ClockAcrossScans
```

Child method implementation (IMP):

```iecst
IF CoUnit.TEST_GUARDED(TestName := 'ClockAcrossScans') THEN
IF _phase = 0 THEN
	_first := LTIME();
	_phase := 1;
	RETURN;
END_IF
IF _phase = 1 THEN
	_advanced := LTIME() > _first;
	_phase := 2;
END_IF
AssertTrue(Condition := _advanced, Message := 'time advances between task scans');
CoUnit.TEST_FINISHED();
END_IF
```

Use a nonzero cyclic task interval and a finite host timeout. This illustrates authoring; qualify the example in your selected consumer/compiler/runtime before treating it as native evidence. The phase and observations survive method calls, and completed invocations do not repeat the stimulus.

When the product samples LTIME() internally, exercise its actual-clock behavior across task invocations. If it exposes a deterministic duration override, that value is one call's elapsed interval and stays constant; only a monotonic timestamp override accumulates. Match TIME versus LTIME to the actual signature. Repeated FB calls in a FOR loop do not create PLC task scans or advance real timers.

Call the complete fixture dependency chain in its normal order: equipment/participants, endpoints, then the coordinator/controller being tested. A coordinator-only loop can leave its simulated equipment permanently unacknowledged. Explicitly verify that the intended starting state was reached before injecting the failure.

## Assertions

Use typed REAL/LREAL assertions with a contract-backed Delta. For BOOL assertions, the named argument is `Condition`, not `Actual`:

```iecst
_result := _fixture.SetConfig(Config := _config);
AssertTrue(Condition := _result, Message := 'valid configuration accepted');
```

Declare `_result : BOOL` in the method DEC. Materialize method/function results before BOOL assertions, especially calls with VAR_OUTPUT associations (`=>`). Keep generic ANY operands writable and of the expected type; do not rely on temporary pointer behavior observed in older libraries.

V2 preserves the first failure for each test while continuing assertion evaluation. Its assertion count is the maximum executable assertion-call count in any one invocation of that test body, not a sum over all scans. Do not use it as a count of unique source assertion sites or repeatedly executed checks.

## Native execution and acceptance

Follow [native qualification directions](../qualification/README.md) for framework work and the selected runtime authorization. For consumer regressions:

1. Confirm the disposable project, application, exact installed CoUnit version, task and selected suite/test inventory. Select simulator mode explicitly for simulator-only work.
2. Generate one PLCOpenXML containing the selected suites, runner and dependency closure using the existing XML tools. This repository provides `_tools/generate_plcopenxml.py` and `qualification/generate_native.py`; a consumer must include its own dependency closure. Clear the importable tree when replacing a shard, import once and reacquire handles. Do not create or replace bulk objects in a per-object ScriptEngine loop.
3. Capture a fresh complete native build. A transport success or script exit code does not override build errors. Classify a failed build as not run; do not silently omit it from the inventory.
4. Archive the exact prior xUnit report and the selected suite's filesystem fixtures before starting. Cold reset does not remove files. Identify the exact paths owned by the selected fixtures, including immutable snapshots and journals, and archive only those paths. In the Windows simulator, relative files normally resolve beneath `%APPDATA%/CODESYS/Simulation/PlcLogic`; confirm the actual runtime location. Never clear the runtime directory indiscriminately. Publication fault tests may intentionally precreate a prior report; follow their explicit setup instead.
5. Download/reset/start the authorized test application and poll from its current start with a finite deadline. Distinguish PLC exception, execution timeout, report timeout and assertion failure. Continue collecting known failures if report capture later fails.
6. Require a complete fresh parseable report, the exact selected cases, nonzero execution, no required skips or missing cases, and passing assertions. For ordinary assertion-based consumer tests, investigate zero-assertion cases. Require `counit-run-disposition="NORMAL"`; a v2 report missing the attribute cannot pass. See [report acceptance](../REPORTING.md). Framework qualification intentionally includes empty, skipped, failed and framework-error cases, which must match their independent expected oracles instead.
7. Stop/log out and restore the intended production import when finished. Retain earlier failing reports, diagnostics and timeout captures; a later pass does not erase them.

From the repository root, gate an ordinary consumer report with:

```powershell
python qualification/verify_xunit.py path/to/current-report.xml --require-success
```

The gate validates report semantics and normal success; separately verify freshness, the exact selected inventory and any required-skip policy. Do not point it at `.counit.tmp` or `.counit.bak`. See [REPORTING.md](../REPORTING.md) for publication versus test-truth distinctions.

## CODESYS library-state recovery

Malformed tokens inside an installed CoUnit library can be stale installation/language-model state. Preserve the exact diagnostics and compare with authoritative source before editing the library. The verified recovery uses the unchanged v2 release: unload/reinstall or reload the authoritative library as appropriate, Clean All, rebind namespace/version, and rebuild before rerunning. Do not silently downgrade to 1.x or distribute an unqualified repair candidate. See [CODESYS recovery directions](codesys-library-recovery.md).

Use ScriptEngine prompt handling for clean/reload operations. Export to a fresh destination or explicitly handle overwrite prompts; an unattended overwrite dialog can outlive the MCP timeout. A transport timeout does not prove the IDE script stopped, so resolve its state before issuing more mutations. Prefer MCP and files. If an IDE dialog cannot be handled through the supported scripting APIs, ask the user to resolve it manually; do not start another mutation while the first script may still be active.
