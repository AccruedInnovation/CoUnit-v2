"""Generate installed-CoUnit upgrade consumers and their frozen expected outcomes.

This writes only the task-owned sparse consumer folders. The expected outcome
JSON is authored from the fixture contract before any native execution and is
never inferred from a report.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys
import tempfile


REPO = Path(__file__).resolve().parents[1]
DEFAULT_CONSUMER = Path(r"D:\aib-work\counit-upgrade-2100\consumer")
sys.path.insert(0, str(REPO / "_tools"))
SUITES = {
    "lifecycle": ("FB_UpgradeLifecycle", "upgrade.lifecycle"),
    "helper": ("FB_UpgradeHelperOracle", "upgrade.helper-oracle"),
    "memory": ("FB_UpgradeMemory", "upgrade.memory"),
    "assertions": ("FB_UpgradeAssertions", "upgrade-assertions"),
    "budget_small16": ("FB_UpgradeBudgetSmall16", "upgrade.budget.small16"),
    "budget_large2048": ("FB_UpgradeBudgetLarge2048", "upgrade.budget.large2048"),
    "budget_overcapacity17": ("FB_UpgradeBudgetOverCapacity17", "upgrade.budget.overcapacity17"),
    "catalog_timeout": ("FB_UpgradeCatalogTimeout", "upgrade.catalog-timeout"),
    "catalog_overstep": ("FB_UpgradeCatalogOverstep", "upgrade.catalog-overstep"),
    "catalog_recursive": ("FB_UpgradeCatalogRecursive", "upgrade.catalog-recursive"),
    "catalog_duplicate": ("FB_UpgradeCatalogDuplicate", "upgrade.catalog-duplicate"),
    "catalog_missing_identity": ("FB_UpgradeCatalogMissingIdentity", "upgrade.catalog-missing-identity"),
    "catalog_conflicting_identity": ("FB_UpgradeCatalogConflictingIdentity", "upgrade.catalog-conflicting-identity"),
}

STRICT_CATALOG_REASONS = {
    "catalog_duplicate": "Duplicate stable case and parameter row",
    "catalog_missing_identity": "Catalog suite omitted stable identity",
    "catalog_conflicting_identity": "Invalid or duplicate stable suite identity",
}


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _object(prefix: str, name: str, declaration: str, implementation: str | None = None,
            members: list | None = None):
    import generate_plcopenxml as plc
    return plc.ObjectExport(prefix, name, declaration, implementation,
                            ("Tests", "Upgrade"), REPO / "qualification" / name,
                            members=members or [])


def _member(name: str, declaration: str, implementation: str | None):
    import generate_plcopenxml as plc
    return plc.Member("M", name, declaration, implementation,
                      REPO / "qualification" / name)


def _write_object(root: Path, item) -> None:
    folder = root / item.name
    folder.mkdir(parents=True, exist_ok=True)
    prefix = "POU" if item.prefix == "POU" else item.prefix
    (folder / f"{prefix}.{item.name}.DEC.exp").write_text(item.declaration.rstrip() + "\n", encoding="utf-8")
    if item.implementation is not None:
        (folder / f"{prefix}.{item.name}.IMP.exp").write_text(item.implementation.rstrip() + "\n", encoding="utf-8")
    for member in item.members:
        declaration = member.declaration.rstrip() + "\n"
        implementation = member.implementation.rstrip() + "\n" if member.implementation is not None else None
        # One canonical flat method source, consumed by both adapter and writer.
        (folder / f"M.{member.name}.DEC.exp").write_text(declaration, encoding="utf-8")
        if member.implementation is not None:
            (folder / f"M.{member.name}.IMP.exp").write_text(implementation, encoding="utf-8")



def _lifecycle_objects():
    lifecycle_rows = [
        ("late-error", "LateError", "run", False),
        ("assert-then-error", "AssertThenError", "run", False),
        ("cleanup-failure", "CleanupFailure", "run", False),
        ("cleanup-incomplete", "CleanupIncomplete", "run", False),
        ("cancel-timeout", "CancelTimeout", "run", False),
    ]
    declaration = """\t_handleLate : UINT;
\t_handleAssertError : UINT;
\t_handleCleanupFailure : UINT;
\t_handleCleanupIncomplete : UINT;
\t_handleCancelTimeout : UINT;
\t_fixture : CoUnit.FB_CoUnitFixture;
\t_fixtureCallback : FB_UpgradeLifecycleCallback;
\t_fixtureBinding : CoUnit.I_CoUnitFixture;
\t_fixtureKey : CoUnit.ST_CoUnitFixtureKey;
\t_fixtureStarted : BOOL;
\t_bodyAssertionRecorded : BOOL;
\t_fixtureMode : UINT;
\t_lastPhase : CoUnit.E_CoUnitFixturePhase;
\t_lateRan : BOOL;
\t_assertErrorRan : BOOL;"""
    implementation = r"""IF BeginCase(Handle := _handleLate) THEN
	IF NOT _lateRan THEN
		_lateRan := TRUE;
		AssertResult(Passed := TRUE, CheckId := 'upgrade/lifecycle/late-error/pass', Message := 'Passing case closes before a late assertion', ExpectedText := 'passed', ActualText := 'passed', Detail := 'late framework error must not rewrite a closed case');
		CoUnit.TEST_FINISHED();
		AssertResult(Passed := FALSE, CheckId := 'upgrade/lifecycle/late-error/unbound', Message := 'Unbound assertion after case close', ExpectedText := 'no open case', ActualText := 'unbound', Detail := 'expected run-only FRAMEWORK_ERROR');
	END_IF
END_IF
IF BeginCase(Handle := _handleAssertError) THEN
	IF NOT _assertErrorRan THEN
		_assertErrorRan := TRUE;
		AssertResult(Passed := FALSE, CheckId := 'upgrade/lifecycle/original', Message := 'Original assertion before later registration error', ExpectedText := 'expected-value', ActualText := 'actual-value', Detail := 'preserve this first failure');
		CoUnit.TEST('undeclared');
	END_IF
END_IF
IF BeginCase(Handle := _handleCleanupFailure) THEN
	_fixtureMode := 1;
	ServiceFixture(Mode := _fixtureMode, CaseId := 'cleanup-failure');
END_IF
IF BeginCase(Handle := _handleCleanupIncomplete) THEN
	_fixtureMode := 2;
	ServiceFixture(Mode := _fixtureMode, CaseId := 'cleanup-incomplete');
END_IF
IF BeginCase(Handle := _handleCancelTimeout) THEN
	_fixtureMode := 3;
	ServiceFixture(Mode := _fixtureMode, CaseId := 'cancel-timeout');
END_IF"""
    service_dec = """METHOD PRIVATE ServiceFixture
VAR_INPUT
	Mode : UINT;
	CaseId : CoUnit.T_MaxString;
END_VAR
VAR
	_now : LTIME;
	_phase : CoUnit.E_CoUnitFixturePhase;
	_cleanupDetail : CoUnit.T_MaxString;
END_VAR"""
    service_imp = r"""_now := LTIME();
IF NOT _fixtureStarted THEN
	_fixtureKey.RunId := 'native-upgrade';
	_fixtureKey.SuiteId := 'upgrade.lifecycle';
	_fixtureKey.CaseId := CaseId;
	_fixtureKey.RowKey := 'run';
	_fixtureKey.AttemptId := 'attempt-1';
	_fixtureKey.StepId := 'body-and-cleanup';
	_fixtureCallback.Configure(Mode := Mode);
	_fixtureBinding := _fixtureCallback;
	_fixtureStarted := _fixture.Start(Key := _fixtureKey, Fixture := _fixtureBinding, Now := _now, PhaseTimeout := LTIME#600s, CleanupBudget := LTIME#5s);
	_lastPhase := CoUnit.E_CoUnitFixturePhase.SETUP;
	ReportPhase(Phase := CoUnit.E_CoUnitFixturePhase.SETUP, StepId := 'setup');
	ReportFixture(PrimaryCause := CoUnit.E_CoUnitFixtureCause.NONE, CleanupOutcome := CoUnit.E_CoUnitFixtureOutcome.PENDING, Detail := 'fixture acquired test-owned resource');
	RETURN;
END_IF
IF _fixture.Phase = CoUnit.E_CoUnitFixturePhase.BODY AND NOT _bodyAssertionRecorded AND Mode <> 3 THEN
	_bodyAssertionRecorded := TRUE;
	AssertResult(Passed := FALSE, CheckId := CONCAT('upgrade/lifecycle/', CaseId), Message := 'Body assertion is the immutable first failure', ExpectedText := 'body succeeds', ActualText := 'body assertion failed', Detail := 'later cleanup outcome is recorded separately');
END_IF
_fixture.Execute(Key := _fixtureKey, Now := _now, Cancel := CoUnit.COUNIT_CANCELLED());
_phase := _fixture.Phase;
_lastPhase := _phase;
(* Repeated same phase/step reports must be idempotent public progress. *)
IF _phase = CoUnit.E_CoUnitFixturePhase.BODY THEN
	ReportPhase(Phase := _phase, StepId := 'body');
ELSIF _phase = CoUnit.E_CoUnitFixturePhase.CLEANUP THEN
	ReportPhase(Phase := _phase, StepId := 'cleanup');
END_IF
IF _fixture.Complete THEN
	IF _fixture.CleanupOutcome = CoUnit.E_CoUnitFixtureOutcome.FAILED THEN _cleanupDetail := 'callback cleanup failed; acquired remains TRUE';
	ELSIF _fixture.CleanupOutcome = CoUnit.E_CoUnitFixtureOutcome.INCOMPLETE THEN _cleanupDetail := 'cleanup remained pending through its finite budget';
	ELSE _cleanupDetail := 'cancel cleanup released test-owned resource'; END_IF
	ReportFixture(PrimaryCause := _fixture.PrimaryCause, CleanupOutcome := _fixture.CleanupOutcome, Detail := _cleanupDetail);
	ReportPhase(Phase := CoUnit.E_CoUnitFixturePhase.COMPLETE, StepId := 'complete');
	CoUnit.TEST_FINISHED();
ELSE
	ReportFixture(PrimaryCause := _fixture.PrimaryCause, CleanupOutcome := CoUnit.E_CoUnitFixtureOutcome.PENDING, Detail := 'fixture callback is still pending');
END_IF"""
    service = _member("ServiceFixture", service_dec, service_imp)
    describe_dec = "METHOD Describe\nVAR\n\t_identityOk : BOOL;\nEND_VAR"
    describe_imp = """_identityOk := SetCatalogIdentity(SuiteId := 'upgrade.lifecycle');
_handleLate := DefineCase(CaseId := 'late-error', Name := 'LateError', RowKey := 'run', Tags := 'upgrade', Disabled := FALSE);
_handleAssertError := DefineCase(CaseId := 'assert-then-error', Name := 'AssertThenError', RowKey := 'run', Tags := 'upgrade', Disabled := FALSE);
_handleCleanupFailure := DefineCase(CaseId := 'cleanup-failure', Name := 'CleanupFailure', RowKey := 'run', Tags := 'upgrade', Disabled := FALSE);
_handleCleanupIncomplete := DefineCase(CaseId := 'cleanup-incomplete', Name := 'CleanupIncomplete', RowKey := 'run', Tags := 'upgrade', Disabled := FALSE);
_handleCancelTimeout := DefineCase(CaseId := 'cancel-timeout', Name := 'CancelTimeout', RowKey := 'run', Tags := 'upgrade', Disabled := FALSE);"""
    import generate_plcopenxml as plc
    item = _object("POU", "FB_UpgradeLifecycle",
                   "FUNCTION_BLOCK FB_UpgradeLifecycle EXTENDS CoUnit.FB_TestSuite\nVAR\n" + declaration + "\nEND_VAR",
                   implementation,
                   [_member("Describe", describe_dec, describe_imp), service])
    callback_methods = [
        _member("Configure", "METHOD PUBLIC Configure\nVAR_INPUT\n\tMode : UINT;\nEND_VAR", "_mode := Mode;"),
        _member("Setup", "METHOD Setup : CoUnit.E_CoUnitFixtureCallback\nVAR_INPUT\n\tKey : CoUnit.ST_CoUnitFixtureKey;\n\tNow : LTIME;\nEND_VAR", "Acquired := TRUE;\nSetup := CoUnit.E_CoUnitFixtureCallback.PASSED;"),
        _member("Body", "METHOD Body : CoUnit.E_CoUnitFixtureCallback\nVAR_INPUT\n\tKey : CoUnit.ST_CoUnitFixtureKey;\n\tNow : LTIME;\nEND_VAR", "IF _mode = 3 THEN\n\tBody := CoUnit.E_CoUnitFixtureCallback.PENDING;\nELSE\n\tBody := CoUnit.E_CoUnitFixtureCallback.FAILED;\nEND_IF"),
        _member("Cleanup", "METHOD Cleanup : CoUnit.E_CoUnitFixtureCallback\nVAR_INPUT\n\tKey : CoUnit.ST_CoUnitFixtureKey;\n\tNow : LTIME;\nEND_VAR", "IF _mode = 1 THEN\n\tCleanup := CoUnit.E_CoUnitFixtureCallback.FAILED;\nELSIF _mode = 2 THEN\n\tCleanup := CoUnit.E_CoUnitFixtureCallback.PENDING;\nELSE\n\tAcquired := FALSE;\n\tCleanup := CoUnit.E_CoUnitFixtureCallback.PASSED;\nEND_IF"),
    ]
    callback = _object("POU", "FB_UpgradeLifecycleCallback",
                       "FUNCTION_BLOCK FB_UpgradeLifecycleCallback IMPLEMENTS CoUnit.I_CoUnitFixture\nVAR\n\t_mode : UINT;\n\tAcquired : BOOL;\nEND_VAR", "(* Lifecycle callbacks execute through the fixture interface. *)", callback_methods)
    return [item, callback]


def _qualified_helper_objects():
    helper = _load_module("upgrade_helpers_for_native_consumer", REPO / "qualification" / "upgrade_helpers.py")
    adapter, program = helper.qualification_objects()
    names = (
        "I_CoUnitFixture", "E_CoUnitFixtureCallback", "ST_CoUnitFixtureKey",
        "E_CoUnitFixturePhase", "E_CoUnitFixtureCause", "E_CoUnitFixtureOutcome",
        "E_CoUnitTemporalMode", "E_CoUnitTemporalResult", "FB_CoUnitExpectation",
        "FB_CoUnitFixture",
    )
    def qualify(text: str | None) -> str | None:
        if text is None:
            return None
        for value in names:
            text = re.sub(rf"(?<![\w.]){value}\b", f"CoUnit.{value}", text)
        text = text.replace("PROGRAM PRG_Qualification", "FUNCTION_BLOCK FB_HelperOracle")
        text = text.replace("FB_UpgradeCallback", "FB_UpgradeCallback")
        return text
    adapter.declaration = qualify(adapter.declaration)
    adapter.implementation = "(* Helper callbacks execute through the fixture interface. *)"
    for member in adapter.members:
        member.declaration = qualify(member.declaration)
        member.implementation = qualify(member.implementation)
    program.name = "FB_HelperOracle"
    program.declaration = qualify(program.declaration)
    program.implementation = qualify(program.implementation)
    program.declaration = program.declaration.replace("FUNCTION_BLOCK FB_HelperOracle", "FUNCTION_BLOCK FB_HelperOracle")
    return [program, adapter]


def _helper_suite_objects():
    rows = [("helper-oracle", "HelperOracle", "oracle", False)]
    declaration = "\t_handle : UINT;\n\t_helperOracle : FB_HelperOracle;\n\t_finished : BOOL;"
    implementation = r"""IF BeginCase(Handle := _handle) THEN
	IF NOT _finished THEN
		_helperOracle();
		IF _helperOracle.Done THEN
			AssertResult(Passed := _helperOracle.OraclePass, CheckId := 'upgrade/helper-oracle', Message := 'Installed temporal and fixture helper oracle', ExpectedText := 'all deterministic checks pass', ActualText := BOOL_TO_STRING(_helperOracle.OraclePass), Detail := CONCAT('FailedCheck=', UINT_TO_STRING(_helperOracle.FailedCheck)));
			_finished := TRUE;
			CoUnit.TEST_FINISHED();
		END_IF
	END_IF
END_IF"""
    describe_dec = "METHOD Describe\nVAR\n\t_identityOk : BOOL;\nEND_VAR"
    describe_imp = """_identityOk := SetCatalogIdentity(SuiteId := 'upgrade.helper-oracle');
_handle := DefineCase(CaseId := 'helper-oracle', Name := 'HelperOracle', RowKey := 'oracle', Tags := 'upgrade', Disabled := FALSE);"""
    suite = _object("POU", "FB_UpgradeHelperOracle",
                    "FUNCTION_BLOCK FB_UpgradeHelperOracle EXTENDS CoUnit.FB_TestSuite\nVAR\n" + declaration + "\nEND_VAR",
                    implementation, [_member("Describe", describe_dec, describe_imp)])
    return [suite]


def _memory_objects():
    rows = [("memory-profile", "MemoryProfile", "size", False)]
    declaration = "\t_handle : UINT;\n\t_actual : CoUnit.T_MaxString;"
    implementation = r"""IF BeginCase(Handle := _handle) THEN
	_actual := CONCAT(CONCAT(CONCAT('snapshot=', UDINT_TO_STRING(SIZEOF(CoUnit.ST_CoUnitRunSnapshot))), CONCAT(';suite=', UDINT_TO_STRING(SIZEOF(CoUnit.FB_TestSuite)))), CONCAT(';runner=', UDINT_TO_STRING(SIZEOF(CoUnit.FB_coUnitRunner))));
	AssertResult(Passed := FALSE, CheckId := 'upgrade/memory/native-sizes', Message := 'Native installed-profile size diagnostic is intentionally failing', ExpectedText := 'Linux Virtual Control SL / CoUnit 2.1.0.5; record native sizes', ActualText := _actual, Detail := 'The host qualification oracle compares the three nonzero SIZEOF measurements.');
	CoUnit.TEST_FINISHED();
END_IF"""
    describe_dec = "METHOD Describe\nVAR\n\t_identityOk : BOOL;\nEND_VAR"
    describe_imp = """_identityOk := SetCatalogIdentity(SuiteId := 'upgrade.memory');
_handle := DefineCase(CaseId := 'memory-profile', Name := 'MemoryProfile', RowKey := 'size', Tags := 'upgrade', Disabled := FALSE);"""
    suite = _object("POU", "FB_UpgradeMemory",
                    "FUNCTION_BLOCK FB_UpgradeMemory EXTENDS CoUnit.FB_TestSuite\nVAR\n" + declaration + "\nEND_VAR",
                    implementation, [_member("Describe", describe_dec, describe_imp)])
    return [suite]


def _budget_objects():
    objects = []
    for name, suite_id, case_count in (
        ("FB_UpgradeBudgetSmall16", "upgrade.budget.small16", 16),
        ("FB_UpgradeBudgetLarge2048", "upgrade.budget.large2048", 2048),
        ("FB_UpgradeBudgetOverCapacity17", "upgrade.budget.overcapacity17", 17),
    ):
        handles = f"\t_handles : ARRAY[1..{case_count}] OF UINT;\n"
        describe_dec = "METHOD Describe\nVAR\n\t_identityOk : BOOL;\n\t_describeStarted : LTIME;\nEND_VAR"
        rows = [f"_handles[{index}] := DefineCase(CaseId := 'budget', Name := 'Budget{index:04d}', RowKey := 'row{index:04d}', Tags := 'upgrade|budget', Disabled := FALSE);"
                for index in range(1, case_count + 1)]
        describe_body = "_identityOk := SetCatalogIdentity(SuiteId := '" + suite_id + "');\n" + "\n".join(rows)
        describe_imp = ("_describeStarted := LTIME();\n" + describe_body +
                        "\nDescribeNanoseconds := TO_ULINT(LTIME() - _describeStarted);")
        next_rows = "\n".join(f"\t{index}:\n\t\t{row}" for index, row in enumerate(rows, 1))
        describe_next = ("DescribeNext := FALSE;\n_describeStarted := LTIME();\n"
                         "IF _describeCursor = 1 THEN\n\t_identityOk := SetCatalogIdentity(SuiteId := '"
                         + suite_id + "');\nEND_IF\nCASE _describeCursor OF\n" + next_rows +
                         f"\nEND_CASE\nIF _describeCursor <= {case_count} THEN\n"
                         "\t_describeCursor := _describeCursor + 1;\nEND_IF\n"
                         f"DescribeNext := _describeCursor > {case_count};\n"
                         "DescribeNanoseconds := MAX(DescribeNanoseconds, TO_ULINT(LTIME() - _describeStarted));")
        declaration = (f"FUNCTION_BLOCK {name} EXTENDS CoUnit.FB_TestSuite\n"
                       "VAR_OUTPUT\n"
                       "\tSnapshotBytes : UDINT;\n"
                       "\tSuiteBytes : UDINT;\n"
                       "\tRunnerBytes : UDINT;\n"
                       "\tDescribeNanoseconds : ULINT;\n"
                       "END_VAR\nVAR\n"
                       + handles + "\t_nextCase : UINT := 1;\n\t_describeCursor : UINT := 1;\nEND_VAR")
        implementation = f"""SnapshotBytes := SIZEOF(CoUnit.ST_CoUnitRunSnapshot);
SuiteBytes := SIZEOF({name});
RunnerBytes := SIZEOF(CoUnit.FB_coUnitRunner);
IF _nextCase <= {case_count} THEN
	IF BeginCase(Handle := _handles[_nextCase]) THEN
		AssertResult(Passed := FALSE, CheckId := 'budget/allfail', Message := 'Every budget row intentionally fails', ExpectedText := 'pass', ActualText := 'fail', Detail := 'one terminal record per scan');
		CoUnit.TEST_FINISHED();
		_nextCase := _nextCase + 1;
	END_IF
END_IF"""
        suite = _object("POU", name, declaration, implementation,
                        [_member("Describe", describe_dec, describe_imp),
                         _member("DescribeNext", describe_dec.replace("METHOD Describe", "METHOD DescribeNext : BOOL", 1), describe_next)])
        objects.append(suite)
    return objects


def _catalog_negative_objects():
    """Existing boot control drives finite setup failure; bodies must never run."""
    result = []
    for name, suite_id, mode in (
            ("FB_UpgradeCatalogTimeout", "upgrade.catalog-timeout", "timeout"),
            ("FB_UpgradeCatalogOverstep", "upgrade.catalog-overstep", "overstep"),
            ("FB_UpgradeCatalogRecursive", "upgrade.catalog-recursive", "recursive")):
        overstep = mode == "overstep"
        rows = ["_first := DefineCase(CaseId := 'setup', Name := 'First', RowKey := 'first', Tags := 'upgrade', Disabled := FALSE);"]
        if overstep:
            rows.append("_second := DefineCase(CaseId := 'setup', Name := 'Second', RowKey := 'second', Tags := 'upgrade', Disabled := FALSE);")
        identity = f"_ok := SetCatalogIdentity(SuiteId := '{suite_id}');"
        describe = _member("Describe", "METHOD Describe\nVAR\n\t_ok : BOOL;\nEND_VAR",
                           identity + "\n" + "\n".join(rows))
        next_body = ("DescribeNext := FALSE;\nIF NOT _identitySet THEN\n\t" + identity +
                     "\n\t_identitySet := TRUE;\nEND_IF")
        if overstep:
            next_body += "\n" + "\n".join(rows) + "\nDescribeNext := TRUE;"
        elif mode == "recursive":
            next_body += "\nCoUnit.RUN_CONTROLLED(Exchange := _nestedExchange);"
        incremental = _member("DescribeNext", "METHOD DescribeNext : BOOL\nVAR\n\t_ok : BOOL;\nEND_VAR", next_body)
        result.append(_object("POU", name,
                              f"FUNCTION_BLOCK {name} EXTENDS CoUnit.FB_TestSuite\nVAR\n\t_first : UINT;\n\t_second : UINT;\n\t_identitySet : BOOL;\n\t_nestedExchange : CoUnit.ST_CoUnitExchange;\nEND_VAR",
                              "IF BeginCase(Handle := _first) THEN\n\tAssertTrue(Condition := FALSE, Message := 'Setup failure must prevent body entry');\n\tCoUnit.TEST_FINISHED();\nEND_IF",
                              [describe, incremental]))
    return result


def _strict_definition_objects():
    """Literal Describe is the independent inventory; malformed DescribeNext must fail."""
    result = []
    row = "_first := DefineCase(CaseId := 'setup', Name := 'First', RowKey := 'first', Tags := 'upgrade', Disabled := FALSE);"
    for mode in STRICT_CATALOG_REASONS:
        name, suite_id = SUITES[mode]
        identity = f"_ok := SetCatalogIdentity(SuiteId := '{suite_id}');"
        describe = _member("Describe", "METHOD Describe\nVAR\n\t_ok : BOOL;\nEND_VAR",
                           identity + "\n" + row)
        if mode == "catalog_missing_identity":
            next_body = "DescribeNext := TRUE;\n" + row
        else:
            later = (row if mode == "catalog_duplicate" else
                     "_ok := SetCatalogIdentity(SuiteId := 'conflicting-suite');")
            next_body = ("DescribeNext := FALSE;\nIF NOT _identitySet THEN\n\t" + identity +
                         "\n\t" + row + "\n\t_identitySet := TRUE;\nELSE\n\t" + later +
                         "\n\tDescribeNext := TRUE;\nEND_IF")
        incremental = _member("DescribeNext", "METHOD DescribeNext : BOOL\nVAR\n\t_ok : BOOL;\nEND_VAR", next_body)
        result.append(_object("POU", name,
                              f"FUNCTION_BLOCK {name} EXTENDS CoUnit.FB_TestSuite\nVAR\n\t_first : UINT;\n\t_identitySet : BOOL;\nEND_VAR",
                              "IF BeginCase(Handle := _first) THEN\n\tAssertTrue(Condition := FALSE, Message := 'Invalid catalog must prevent body entry');\n\tCoUnit.TEST_FINISHED();\nEND_IF",
                              [describe, incremental]))
    return result


def _write_strict_expected(root: Path) -> None:
    for mode, reason in STRICT_CATALOG_REASONS.items():
        path = root / "PlaintextExport/Tests/Upgrade" / SUITES[mode][0] / "expected-outcomes.json"
        path.write_text(json.dumps({"framework_version": "2.1.0.5", "expectations_authored_before_execution": True,
                                    "run_disposition": "FRAMEWORK_ERROR", "tests": 1, "errors": 1,
                                    "failures": 0, "assertions": 0, "started": 0, "termination_reason": reason,
                                    "consumer_acceptance": "must reject non-NORMAL run"}, indent=2) + "\n", encoding="utf-8")


def _assertion_objects(name="FB_UpgradeAssertions", group="upgrade_assertions"):
    """Wrap an existing canonical qualification suite for installed-CoUnit use."""
    source = REPO / "qualification" / "generated" / group / name
    declaration = (source / f"POU.{name}.DEC.exp").read_text(encoding="utf-8")
    implementation = (source / f"POU.{name}.IMP.exp").read_text(encoding="utf-8")
    describe = source / "Describe"
    describe_declaration = (describe / "Describe.DEC.exp").read_text(encoding="utf-8")
    describe_implementation = (describe / "Describe.IMP.exp").read_text(encoding="utf-8")

    def qualify(text: str) -> str:
        for name, qualified in (
            ("FB_TestSuite", "CoUnit.FB_TestSuite"),
            ("TEST_FINISHED", "CoUnit.TEST_FINISHED"),
            ("MEMCPY", "CoUnit.MEMCPY"),
        ):
            text = re.sub(rf"\b{re.escape(name)}\b", qualified, text)
        return text

    item = _object(
        "POU", name, qualify(declaration), qualify(implementation),
        [_member("Describe", qualify(describe_declaration), qualify(describe_implementation))],
    )
    return [item]


EXPECTED = {
    "schema_version": 1,
    "framework_version": "2.1.0.5",
    "expectations_authored_before_execution": True,
    "cases": [
        {"suite_id": "upgrade.lifecycle", "case_id": "late-error", "row_key": "run",
         "run_disposition": "FRAMEWORK_ERROR", "termination_reason": "nonempty",
         "testcase_state": "PASSED", "failures": 0, "errors": 0,
         "first_failure": None},
        {"suite_id": "upgrade.lifecycle", "case_id": "assert-then-error", "row_key": "run",
         "run_disposition": "FRAMEWORK_ERROR", "termination_reason": "nonempty",
         "testcase_state": "ERROR", "failures": 0, "errors": 1,
         "first_failure": {"type": "BOOL", "check_id": "upgrade/lifecycle/original",
                            "message_contains": "Original assertion before registration error",
                            "expected": "expected-value", "actual": "actual-value"}},
        {"suite_id": "upgrade.lifecycle", "case_id": "cleanup-failure", "row_key": "run",
         "run_disposition": "NORMAL", "testcase_state": "ERROR", "failures": 0, "errors": 1,
         "first_failure": {"type": "BOOL", "check_id": "upgrade/lifecycle/cleanup-failure",
                            "message_contains": "Body assertion is the immutable first failure",
                            "expected": "body succeeds", "actual": "body assertion failed"},
         "fixture": {"primary_cause": "BODY_FAILED", "cleanup_outcome": "FAILED",
                     "primary_cause_code": 2, "cleanup_outcome_code": 3,
                     "cleanup_detail_contains": "callback cleanup failed"}},
        {"suite_id": "upgrade.lifecycle", "case_id": "cleanup-incomplete", "row_key": "run",
         "run_disposition": "NORMAL", "testcase_state": "ERROR", "failures": 0, "errors": 1,
         "first_failure": {"type": "BOOL", "check_id": "upgrade/lifecycle/cleanup-incomplete",
                            "message_contains": "Body assertion is the immutable first failure",
                            "expected": "body succeeds", "actual": "body assertion failed"},
         "fixture": {"primary_cause": "BODY_FAILED", "cleanup_outcome": "INCOMPLETE",
                     "primary_cause_code": 2, "cleanup_outcome_code": 4,
                     "cleanup_detail_contains": "cleanup remained pending"}},
        {"suite_id": "upgrade.lifecycle", "case_id": "cancel-timeout", "row_key": "run",
         "run_disposition": "ABORTED", "termination_reason": "nonempty",
         "testcase_state": "ABORTED", "failures": 0, "errors": 0,
         "first_failure": None,
         "fixture": {"primary_cause": "CANCELLED", "cleanup_outcome": "PASSED",
                     "primary_cause_code": 3, "cleanup_outcome_code": 2,
                     "cleanup_detail_contains": "resource"}},
        {"suite_id": "upgrade.helper-oracle", "case_id": "helper-oracle", "row_key": "oracle",
         "run_disposition": "NORMAL", "testcase_state": "PASSED", "failures": 0,
         "errors": 0, "first_failure": None, "oracle_pass": True, "failed_check": 0},
        {"suite_id": "upgrade.memory", "case_id": "memory-profile", "row_key": "size",
         "run_disposition": "NORMAL", "testcase_state": "FAILED", "failures": 1,
         "errors": 0, "first_failure": {"type": "BOOL", "check_id": "upgrade/memory/native-sizes",
                                          "expected": "Linux Virtual Control SL / CoUnit 2.1.0.5; record native sizes",
                                          "actual_pattern": "snapshot=[1-9][0-9]*;suite=[1-9][0-9]*;runner=[1-9][0-9]*"},
         "native_measurements": "independent host oracle must verify nonzero values"},
        {"suite_id": "upgrade-assertions", "case_id": "assertion", "row_key": "custom",
         "run_disposition": "NORMAL", "testcase_state": "FAILED", "failures": 1, "errors": 0,
         "first_failure": {"type": "Type_BOOL", "check_id": "domain/limit",
                            "expected": "limit=10", "actual": "limit=12"}},
        {"suite_id": "upgrade-assertions", "case_id": "assertion", "row_key": "float",
         "run_disposition": "NORMAL", "testcase_state": "FAILED", "failures": 1, "errors": 0,
         "first_failure": {"type": "Type_REAL", "expected_raw_bits": "3F800000",
                            "actual_raw_bits": "3F800001", "applied_delta_raw_bits": "00000000"}},
        {"suite_id": "upgrade-assertions", "case_id": "assertion", "row_key": "string",
         "run_disposition": "NORMAL", "testcase_state": "FAILED", "failures": 1, "errors": 0,
         "first_failure": {"type": "Type_ANY", "expected_code_units": 300,
                            "actual_code_units": 300, "mismatch_offset": 299}},
    ],
    "capacity_scenarios": [
        {"suite": "FB_UpgradeBudgetSmall16", "suite_id": "upgrade.budget.small16",
         "case_count": 16, "max_tests_per_suite": 16, "records_per_scan": 1,
         "configuration": "accepted", "run_disposition": "NORMAL", "failed": 16,
         "first_failure": {"check_id": "budget/allfail", "expected": "pass", "actual": "fail"}},
        {"suite": "FB_UpgradeBudgetLarge2048", "suite_id": "upgrade.budget.large2048",
         "case_count": 2048, "max_tests_per_suite": 2048, "records_per_scan": 1,
         "configuration": "accepted", "run_disposition": "NORMAL", "failed": 2048,
         "first_failure": {"check_id": "budget/allfail", "expected": "pass", "actual": "fail"}},
        {"suite": "FB_UpgradeBudgetOverCapacity17", "suite_id": "upgrade.budget.overcapacity17",
         "case_count": 17, "max_tests_per_suite": 16, "records_per_scan": 1,
         "configuration": "rejected", "framework_error": True, "run_started": False},
    ],
}


def _write_expected(root: Path) -> None:
    by_suite = {
        "FB_UpgradeLifecycle": EXPECTED["cases"][:5],
        "FB_UpgradeHelperOracle": EXPECTED["cases"][5:6],
        "FB_UpgradeMemory": EXPECTED["cases"][6:7],
        "FB_UpgradeAssertions": EXPECTED["cases"][7:10],
    }
    for suite_name, cases in by_suite.items():
        path = root / "PlaintextExport" / "Tests" / "Upgrade" / suite_name / "expected-outcomes.json"
        path.write_text(json.dumps({"schema_version": 1, "framework_version": "2.1.0.5",
                                    "expectations_authored_before_execution": True,
                                    "cases": cases}, indent=2) + "\n", encoding="utf-8")
    for suite_name, tests, errors, reason in (
            ("FB_UpgradeCatalogTimeout", 0, 0, "Catalog preparation deadline expired"),
            ("FB_UpgradeCatalogOverstep", 1, 1, "Incremental catalog step declared more than one case"),
            ("FB_UpgradeCatalogRecursive", 0, 0, "Recursive top-level runner invocation")):
        path = root / "PlaintextExport/Tests/Upgrade" / suite_name / "expected-outcomes.json"
        path.write_text(json.dumps({"framework_version": "2.1.0.5", "expectations_authored_before_execution": True,
                                    "run_disposition": "FRAMEWORK_ERROR", "tests": tests, "errors": errors,
                                    "failures": 0, "started": 0, "termination_reason": reason,
                                    "consumer_acceptance": "must reject incomplete frozen inventory"}, indent=2) + "\n", encoding="utf-8")


def _write_budget_expected(root: Path) -> None:
    for scenario in EXPECTED["capacity_scenarios"]:
        suite_name = scenario["suite"]
        case_count = scenario["case_count"]
        rows = [{"suite_id": scenario["suite_id"], "case_id": "budget",
                 "row_key": f"row{index:04d}", "selected": True, "disabled": False}
                for index in range(1, case_count + 1)]
        folder = root / "PlaintextExport" / "Tests" / "Upgrade" / suite_name
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "expected-catalog.json").write_text(
            json.dumps({"rows": rows}, indent=2) + "\n", encoding="utf-8")
        outcome = {"schema_version": 1, "framework_version": "2.1.0.5",
                   "expectations_authored_before_execution": True,
                   "scenario": scenario, "catalog": rows}
        if scenario["configuration"] == "accepted":
            outcome["expected_case"] = {"state": "FAILED", "assertions": 1,
                                         "first_failure": {"type": "BOOL", **scenario["first_failure"]}}
            outcome["expected_summary"] = {"selected": case_count, "failed": case_count,
                                           "passed": 0, "errors": 0, "skipped": 0,
                                           "records_per_scan": 1,
                                           "finalization_spans_multiple_scans": case_count > 1,
                                           "size_metrics": ["SnapshotBytes", "SuiteBytes", "RunnerBytes"]}
        else:
            outcome["expected_configuration"] = {"accepted": False,
                                                  "framework_error": True,
                                                  "run_started": False,
                                                  "message": "nonempty capacity diagnostic"}
        (folder / "expected-outcomes.json").write_text(
            json.dumps(outcome, indent=2) + "\n", encoding="utf-8")


def _check_catalog_adapter(root: Path, items: list, suite_names: set[str] | None = None) -> dict:
    adapter = _load_module("controlled_boot_for_native_consumer",
                           REPO / "tools" / "controlled_boot.py")
    output = {}
    for suite_name, suite_id in SUITES.values():
        if suite_names is not None and suite_name not in suite_names:
            continue
        folder = root / "PlaintextExport" / "Tests" / "Upgrade" / suite_name
        describe = folder / "M.Describe.IMP.exp"
        catalog = adapter.extract_catalog(describe.read_text(encoding="utf-8"))
        if catalog["suite_id"] != suite_id:
            raise RuntimeError(f"{suite_name}: literal catalog identity changed")
        output[suite_id] = catalog
    return output


def _build_xml(root: Path, output: Path, *, budget_only: bool = False) -> int:
    sys.path.insert(0, str(REPO / "_tools"))
    import generate_plcopenxml as plc
    folder_root = root / "PlaintextExport" / "Tests" / "Upgrade"
    names = ["FB_UpgradeBudgetSmall16", "FB_UpgradeBudgetLarge2048", "FB_UpgradeBudgetOverCapacity17"] if budget_only else ["FB_UpgradeLifecycle", "FB_UpgradeLifecycleCallback", "FB_UpgradeHelperOracle",
             "FB_HelperOracle", "FB_UpgradeCallback", "FB_UpgradeMemory", "FB_UpgradeAssertions",
             "FB_UpgradeCatalog", "FB_UpgradeBudgetSmall16", "FB_UpgradeBudgetLarge2048",
             "FB_UpgradeBudgetOverCapacity17", "FB_UpgradeCatalogTimeout", "FB_UpgradeCatalogOverstep", "FB_UpgradeCatalogRecursive"]
    if not budget_only:
        names += [SUITES[mode][0] for mode in STRICT_CATALOG_REASONS]
    roots = [plc.RootSpec(folder_root / name, ("Tests", "Upgrade"), f"task-owned {name}")
             for name in names]
    objects = plc.discover_objects(roots)
    requested = {("pou", name.casefold()) for name in names}
    selected = plc.filter_objects(objects, requested)
    output.parent.mkdir(parents=True, exist_ok=True)
    plc.build_xml(selected, "Installed CoUnit upgrade native consumers").write(
        output, encoding="utf-8", xml_declaration=True, short_empty_elements=True)
    return len(selected)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--consumer-root", type=Path, default=DEFAULT_CONSUMER)
    parser.add_argument("--xml-output", type=Path,
                        help="Optional offline PLCOpenXML import package for these consumer POUs")
    parser.add_argument("--budget-only", action="store_true",
                        help="Generate only the three task-owned capacity consumers and expectations")
    args = parser.parse_args(argv)
    consumer = args.consumer_root.resolve()
    upgrade = consumer / "PlaintextExport" / "Tests" / "Upgrade"
    if not (consumer / "_tools" / "library_ownership.json").is_file():
        parser.error(f"Not a sparse consumer checkout: {consumer}")
    if args.budget_only:
        items = _budget_objects()
        budget_names = {item.name for item in items}
        _write_budget_expected(consumer)
    else:
        items = (_lifecycle_objects() + _qualified_helper_objects() + _helper_suite_objects() + _catalog_negative_objects() + _strict_definition_objects()
                 + _memory_objects() + _budget_objects() + _assertion_objects()
                 + _assertion_objects("FB_UpgradeCatalog", "upgrade_catalog"))
        budget_names = None
    for item in items:
        _write_object(upgrade, item)
    if not args.budget_only:
        _write_expected(consumer)
        _write_strict_expected(consumer)
        expected_path = upgrade / "expected-native-consumers.json"
        expected_path.write_text(json.dumps(EXPECTED, indent=2) + "\n", encoding="utf-8")
    else:
        expected_path = upgrade / "FB_UpgradeBudgetSmall16" / "expected-outcomes.json"
    catalogs = _check_catalog_adapter(consumer, items, budget_names)
    xml_count = None
    if args.xml_output:
        xml_count = _build_xml(consumer, args.xml_output.resolve(), budget_only=args.budget_only)
    print(json.dumps({"consumer_root": str(consumer), "expected_json": str(expected_path),
                      "suite_catalogs": {key: len(value["cases"]) for key, value in catalogs.items()},
                      "xml_object_count": xml_count}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
