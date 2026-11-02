"""Generate the bounded application-owned CoUnit callback consumer fixture.

Model/effort: gpt-6-luna/high; the ABI and guard behavior are fixed by
AIRouter/docs/counit-live-contract.md. No native execution or layout claim is
made here; the bridge owner supplies measured binding and runtime evidence.

Owning-task order: latch each new nonzero Command.RequestId, copy the completed
payload and invoke TrySubmitCoUnit once, then run RUN_CONTROLLED once and copy
Publication. The producer writes RequestId last and holds the payload through
ACK. The callback never runs CoUnit or retries a rejected/busy deposit.
Before test execution, the consumer host must bind CoUnit's xUnit report path
to an agent-owned runtime path; Configure alone leaves that unset and runs no tests.
The five-object XML stays application-only. A native project importing the full
fixture must also include the existing FB_UpgradeLifecycle and
FB_UpgradeLifecycleCallback application sources from Tests/Upgrade, plus the
installed CoUnit 2.1.0.6 library. expected-guard.json covers FB_UpgradeGuard;
lifecycle outcomes remain in Tests/Upgrade/FB_UpgradeLifecycle/expected-outcomes.json.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "_tools"))


def objects():
    import generate_plcopenxml as plc

    command = plc.ObjectExport(
        "DUT", "ST_CoUnitCommand", """TYPE ST_CoUnitCommand :
STRUCT
	RequestId : ULINT;
	Operation : UINT;
	RunId : STRING(63);
	BuildId : STRING(64);
	TargetId : STRING(63);
	ExpectedGeneration : ULINT;
	SuiteId : STRING(63);
	CaseId : STRING(63);
	RowKey : STRING(63);
	Tag : STRING(63);
	SuiteIndex : UINT;
	CaseIndex : UINT;
	ExpectedSelected : UDINT;
	AllowEmpty : BOOL;
	RunTimeout : TIME;
	CleanupTimeout : TIME;
END_STRUCT
END_TYPE""", None, ("Tests", "UpgradeLive"), REPO / "qualification" / "upgrade_live_consumer.py",
    )
    publication = plc.ObjectExport(
        "DUT", "ST_CoUnitPublication", """TYPE ST_CoUnitPublication :
STRUCT
	RequestId : ULINT;
	AckId : ULINT;
	Accepted : BOOL;
	Rejection : CoUnit.T_MaxString;
	Status : CoUnit.ST_CoUnitPublicStatus;
	Page : CoUnit.ST_CoUnitPublicCase;
	SubmissionCount : UDINT;
	LastDepositedRequestId : ULINT;
END_STRUCT
END_TYPE""", None, ("Tests", "UpgradeLive"), REPO / "qualification" / "upgrade_live_consumer.py",
    )
    bridge = plc.ObjectExport(
        "POU", "FB_CoUnitPublicBridge", """FUNCTION_BLOCK FB_CoUnitPublicBridge
VAR_INPUT
	Command : ST_CoUnitCommand;
END_VAR
VAR_OUTPUT
	Publication : ST_CoUnitPublication;
END_VAR
VAR
	_exchange : CoUnit.ST_CoUnitExchange;
	_observedRequestId : ULINT;
	_lastObservedRequestId : ULINT;
	_commandSnapshot : ST_CoUnitCommand;
	_submissionResult : USINT;
END_VAR""", """(* A completed producer payload is committed by RequestId last and held through ACK.
   Latch before submission: a rejected or busy deposit is never retried cyclically. *)
_observedRequestId := Command.RequestId;
IF (_observedRequestId <> 0) AND (_observedRequestId <> _lastObservedRequestId) THEN
	_lastObservedRequestId := _observedRequestId;
	_commandSnapshot := Command;
	IF (_commandSnapshot.RequestId = _observedRequestId) AND (Command.RequestId = _observedRequestId) THEN
		_submissionResult := TrySubmitCoUnit(Value := _commandSnapshot);
	ELSE
		_submissionResult := 2;
	END_IF
END_IF
CoUnit.RUN_CONTROLLED(Exchange := _exchange);
Publication.RequestId := _exchange.RequestId;
Publication.AckId := _exchange.AckId;
Publication.Accepted := _exchange.Accepted;
Publication.Rejection := _exchange.Rejection;
Publication.Status := _exchange.Status;
Publication.Page := _exchange.Page;""", ("Tests", "UpgradeLive"), REPO / "qualification" / "upgrade_live_consumer.py",
        members=[
            plc.Member("M", "TrySubmitCoUnit", """METHOD PUBLIC TrySubmitCoUnit : USINT
VAR_INPUT
	Value : ST_CoUnitCommand;
END_VAR""", """TrySubmitCoUnit := 2;
IF (Value.Operation < 1) OR (Value.Operation > 5) OR (Value.RequestId = 0) THEN RETURN; END_IF
IF Value.RequestId <= Publication.LastDepositedRequestId THEN RETURN; END_IF
IF _exchange.RequestId <> _exchange.AckId THEN RETURN; END_IF
_exchange.Operation := Value.Operation;
_exchange.RunId := Value.RunId;
_exchange.BuildId := Value.BuildId;
_exchange.TargetId := Value.TargetId;
_exchange.ExpectedGeneration := Value.ExpectedGeneration;
_exchange.SuiteId := Value.SuiteId;
_exchange.CaseId := Value.CaseId;
_exchange.RowKey := Value.RowKey;
_exchange.Tag := Value.Tag;
_exchange.SuiteIndex := Value.SuiteIndex;
_exchange.CaseIndex := Value.CaseIndex;
_exchange.ExpectedSelected := Value.ExpectedSelected;
_exchange.AllowEmpty := Value.AllowEmpty;
_exchange.RunTimeout := Value.RunTimeout;
_exchange.CleanupTimeout := Value.CleanupTimeout;
Command := Value;
_exchange.RequestId := Value.RequestId;
Publication.SubmissionCount := Publication.SubmissionCount + 1;
Publication.LastDepositedRequestId := Value.RequestId;
TrySubmitCoUnit := 1;""", REPO / "qualification" / "upgrade_live_consumer.py"),
        ],
    )
    guard = plc.ObjectExport(
        "POU", "FB_UpgradeGuard", """FUNCTION_BLOCK FB_UpgradeGuard EXTENDS CoUnit.FB_TestSuite
VAR
	_handleComplete : UINT;
	_handleActive : UINT;
	_handleDisabled : UINT;
	_completeEffects : UDINT;
	_activeScans : UDINT;
	_disabledEffects : UDINT;
	_describeCursor : UINT := 1;
	_describeStarted : LTIME;
	_describeWaiting : BOOL;
END_VAR""", """IF BeginCase(Handle := _handleComplete) THEN
	CompleteCaseBody();
END_IF
IF BeginCase(Handle := _handleActive) THEN
	ActiveCaseBody();
END_IF
IF BeginCase(Handle := _handleDisabled) THEN
	DisabledCaseBody();
END_IF""", ("Tests", "UpgradeLive"), REPO / "qualification" / "upgrade_live_consumer.py",
        members=[
            plc.Member("M", "CompleteCaseBody", "METHOD PRIVATE CompleteCaseBody", """_completeEffects := _completeEffects + 1;
AssertTrue(Condition := _completeEffects = 1, Message := 'complete body runs once');
CoUnit.TEST_FINISHED();""", REPO / "qualification" / "upgrade_live_consumer.py"),
            plc.Member("M", "ActiveCaseBody", "METHOD PRIVATE ActiveCaseBody", """_activeScans := _activeScans + 1;
IF _activeScans = 3 THEN
	AssertTrue(Condition := (_completeEffects = 1) AND (_activeScans = 3) AND (_disabledEffects = 0), Message := 'complete then active then disabled guard ordering');
	CoUnit.TEST_FINISHED();
END_IF""", REPO / "qualification" / "upgrade_live_consumer.py"),
            plc.Member("M", "DisabledCaseBody", "METHOD PRIVATE DisabledCaseBody", """_disabledEffects := _disabledEffects + 1;
AssertTrue(Condition := FALSE, Message := 'disabled case body must never run');
CoUnit.TEST_FINISHED();""", REPO / "qualification" / "upgrade_live_consumer.py"),
            plc.Member("M", "Describe", """METHOD Describe
VAR
	_identityOk : BOOL;
END_VAR""", """_identityOk := SetCatalogIdentity(SuiteId := 'upgrade.guard-progress');
_handleComplete := DefineCase(CaseId := 'complete-once', Name := 'CompleteOnce', RowKey := 'complete', Tags := 'upgrade', Disabled := FALSE);
_handleActive := DefineCase(CaseId := 'active-three', Name := 'ActiveThree', RowKey := 'active', Tags := 'upgrade', Disabled := FALSE);
_handleDisabled := DefineCase(CaseId := 'disabled-never', Name := 'DISABLED_Never', RowKey := 'disabled', Tags := 'upgrade', Disabled := TRUE);""", REPO / "qualification" / "upgrade_live_consumer.py"),
            plc.Member("M", "DescribeNext", """METHOD DescribeNext : BOOL
VAR
	_identityOk : BOOL;
END_VAR""", """DescribeNext := FALSE;
(* Qualification-only pending window for observing ACK versus readiness and cancellation. *)
IF NOT _describeWaiting THEN
	_identityOk := SetCatalogIdentity(SuiteId := 'upgrade.guard-progress');
	_describeStarted := LTIME();
	_describeWaiting := TRUE;
	RETURN;
END_IF
IF LTIME() - _describeStarted < LTIME#5s THEN RETURN; END_IF
CASE _describeCursor OF
	1: _handleComplete := DefineCase(CaseId := 'complete-once', Name := 'CompleteOnce', RowKey := 'complete', Tags := 'upgrade', Disabled := FALSE);
	2: _handleActive := DefineCase(CaseId := 'active-three', Name := 'ActiveThree', RowKey := 'active', Tags := 'upgrade', Disabled := FALSE);
	3: _handleDisabled := DefineCase(CaseId := 'disabled-never', Name := 'DISABLED_Never', RowKey := 'disabled', Tags := 'upgrade', Disabled := TRUE);
END_CASE
IF _describeCursor <= 3 THEN _describeCursor := _describeCursor + 1; END_IF
DescribeNext := _describeCursor > 3;""", REPO / "qualification" / "upgrade_live_consumer.py"),
        ],
    )
    program = plc.ObjectExport(
        "POU", "PRG_CoUnitLive", """PROGRAM PRG_CoUnitLive
VAR
	guardSuite : FB_UpgradeGuard;
	lifecycleSuite : FB_UpgradeLifecycle;
	Bridge : FB_CoUnitPublicBridge;
END_VAR""", "Bridge();", ("Tests", "UpgradeLive"), REPO / "qualification" / "upgrade_live_consumer.py",
    )
    return [command, publication, bridge, guard, program]


EXPECTED_GUARD = {
    "schema_version": 1,
    "framework_version": "2.1.0.6",
    "expectations_authored_before_execution": True,
    "fixture_suite": "FB_UpgradeGuard",
    "suite_id": "upgrade.guard-progress",
    "lifecycle_fixture_suite": "FB_UpgradeLifecycle",
    "lifecycle_expected_outcomes_path": "PlaintextExport/Tests/Upgrade/FB_UpgradeLifecycle/expected-outcomes.json",
    "catalog": [
        {"case_id": "complete-once", "name": "CompleteOnce", "declared_name": "CompleteOnce",
         "row_key": "complete", "tags": "upgrade", "disabled": False},
        {"case_id": "active-three", "name": "ActiveThree", "declared_name": "ActiveThree",
         "row_key": "active", "tags": "upgrade", "disabled": False},
        {"case_id": "disabled-never", "name": "Never", "declared_name": "DISABLED_Never",
         "row_key": "disabled", "tags": "upgrade", "disabled": True},
    ],
    "cases": [
        {"case_id": "complete-once", "row_key": "complete", "state": "PASSED", "failures": 0, "errors": 0,
         "first_failure": None, "body_effects": 1},
        {"case_id": "active-three", "row_key": "active", "state": "PASSED", "failures": 0, "errors": 0,
         "first_failure": None, "body_scans": 3, "complete_effects": 1, "disabled_effects": 0},
        {"case_id": "disabled-never", "row_key": "disabled", "state": "SKIPPED", "failures": 0, "errors": 0,
         "first_failure": None, "body_effects": 0},
    ],
}


def write_objects(consumer: Path, items) -> None:
    root = consumer / "PlaintextExport" / "Tests" / "UpgradeLive"
    for item in items:
        folder = root / item.name
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{item.prefix}.{item.name}.DEC.exp").write_text(
            item.declaration.rstrip() + "\n", encoding="utf-8")
        if item.implementation is not None:
            (folder / f"{item.prefix}.{item.name}.IMP.exp").write_text(
                item.implementation.rstrip() + "\n", encoding="utf-8")
        for member in item.members:
            (folder / f"M.{member.name}.DEC.exp").write_text(
                member.declaration.rstrip() + "\n", encoding="utf-8")
            if member.implementation is not None:
                (folder / f"M.{member.name}.IMP.exp").write_text(
                    member.implementation.rstrip() + "\n", encoding="utf-8")
    (root / "expected-guard.json").write_text(
        json.dumps(EXPECTED_GUARD, indent=2) + "\n", encoding="utf-8")


def build_xml(consumer: Path, output: Path) -> int:
    import generate_plcopenxml as plc

    root = consumer / "PlaintextExport" / "Tests" / "UpgradeLive"
    specs = [plc.RootSpec(root / item.name, ("Tests", "UpgradeLive"), f"task-owned {item.name}")
             for item in objects()]
    discovered = plc.discover_objects(specs)
    selected = plc.filter_objects(discovered, {(item.prefix.casefold(), item.name.casefold())
                                                for item in objects()})
    output.parent.mkdir(parents=True, exist_ok=True)
    plc.build_xml(selected, "CoUnit public callback application consumer").write(
        output, encoding="utf-8", xml_declaration=True, short_empty_elements=True)
    return len(selected)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--consumer-root", type=Path, required=True)
    parser.add_argument("--xml-output", type=Path, help="Optional offline PLCOpenXML package")
    args = parser.parse_args(argv)
    consumer = args.consumer_root.resolve()
    if not (consumer / "_tools" / "library_ownership.json").is_file():
        parser.error(f"Not a sparse consumer checkout: {consumer}")
    items = objects()
    write_objects(consumer, items)
    xml_count = build_xml(consumer, args.xml_output.resolve()) if args.xml_output else None
    print({"consumer_root": str(consumer), "object_count": len(items), "xml_object_count": xml_count})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
