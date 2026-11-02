"""Emit installed-.6 legacy context oracles for the maintained ALL/sequence route.

Expected outcomes are authored before execution. No provider or runner is changed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from upgrade_native_consumers import _member, _object, _write_object


def generate(root: Path, *, timing_probe: bool = False, timing_report_probe: bool = False) -> None:
    folder = root / "PlaintextExport/Tests/UpgradeLegacy6"
    expectations = {}
    for suffix, sequential in (("All", False), ("Sequence", True)):
        shared = "GVL_Legacy6" + suffix
        first = "FB_Legacy6A" + suffix
        second = "FB_Legacy6Z" + suffix
        runner = "PRG_TEST_LEGACY6_" + suffix.upper()
        instrument = sequential and (timing_probe or timing_report_probe)
        extra_tick = "\n\tFirstTick : TIME;" if sequential else ""
        items = [_object("GVL", shared, "VAR_GLOBAL\n\tFirstDone : BOOL;\n\tFirstFinishedAt : LTIME;" + extra_tick + "\nEND_VAR")]
        first_sample = f"\n\t\t{shared}.FirstTick := TIME();" if sequential else ""
        items.append(_object("POU", first,
            f"FUNCTION_BLOCK {first} EXTENDS CoUnit.FB_TestSuite\nVAR\n\t_scans : UINT;\n\t_accepted : BOOL;\nEND_VAR",
            "ContextImmutable();", [_member("ContextImmutable", "METHOD PRIVATE ContextImmutable",
            f"""CoUnit.TEST(TestName := 'ContextImmutable');
IF NOT CoUnit.IS_TEST_FINISHED(TestName := 'ContextImmutable') THEN
	_scans := _scans + 1;
	IF _scans = 3 THEN
		_accepted := CoUnit.CONFIGURE_LEGACY_RUN(RunId := 'replacement', BuildId := 'replacement', TargetId := 'replacement', InSequence := FALSE);
		AssertFalse(Condition := _accepted, Message := 'running context rejects replacement');
		_accepted := CoUnit.CONFIGURE_LEGACY_RUN(RunId := '', BuildId := '', TargetId := '', InSequence := TRUE);
		AssertFalse(Condition := _accepted, Message := 'empty identities reject');
		AssertTrue(Condition := _scans = 3, Message := 'legacy body completed across three invocations');
		{shared}.FirstDone := TRUE;
		{shared}.FirstFinishedAt := LTIME();{first_sample}
		CoUnit.TEST_FINISHED();
	END_IF
END_IF""")]))
        order_check = "_callsBeforeFirst = 0" if sequential else "_callsBeforeFirst > 0"
        timing_check = (f"\n\t(* The inherited TON uses TIME milliseconds; do not assert a nanosecond wall-clock minimum. *)\n\tAssertTrue(Condition := (TIME() - {shared}.FirstTick) >= CoUnit.GVL_Param_coUnit.TimeBetweenTestSuitesExecution, Message := 'sequence delay preserved in TIME milliseconds');" if sequential else "")
        method_decl = "METHOD PRIVATE DispatchPreserved"
        if instrument:
            method_decl += "\nVAR\n\t_sampleAt : LTIME;\n\t_sampleTick : TIME;\n\t_elapsed : LTIME;\n\t_threshold : LTIME;\n\t_tickDelta : TIME;\n\t_timingOk : BOOL;\n\t_message : STRING(255);\n\t_logResult : DINT;\nEND_VAR"
            timing_check = f"""
	_sampleAt := LTIME();
	_sampleTick := TIME();
	_elapsed := _sampleAt - {shared}.FirstFinishedAt;
	_threshold := TIME_TO_LTIME(CoUnit.GVL_Param_coUnit.TimeBetweenTestSuitesExecution);
	_tickDelta := _sampleTick - {shared}.FirstTick;
	_timingOk := _elapsed >= _threshold;
	_message := CONCAT('LC6 f=', ULINT_TO_STRING(LTIME_TO_ULINT({shared}.FirstFinishedAt)));
	_message := CONCAT(CONCAT(_message, ' s='), ULINT_TO_STRING(LTIME_TO_ULINT(_sampleAt)));
	_message := CONCAT(CONCAT(_message, ' d='), ULINT_TO_STRING(LTIME_TO_ULINT(_elapsed)));
	_message := CONCAT(CONCAT(_message, ' p='), UDINT_TO_STRING(TIME_TO_UDINT(CoUnit.GVL_Param_coUnit.TimeBetweenTestSuitesExecution)));
	_message := CONCAT(CONCAT(_message, ' q='), ULINT_TO_STRING(LTIME_TO_ULINT(_threshold)));
	_message := CONCAT(CONCAT(_message, ' a='), UDINT_TO_STRING(TIME_TO_UDINT({shared}.FirstTick)));
	_message := CONCAT(CONCAT(_message, ' b='), UDINT_TO_STRING(TIME_TO_UDINT(_sampleTick)));
	_message := CONCAT(CONCAT(_message, ' t='), UDINT_TO_STRING(TIME_TO_UDINT(_tickDelta)));
	_message := CONCAT(CONCAT(_message, ' c='), BOOL_TO_STRING(_timingOk));
	AssertTrue(Condition := _timingOk, Message := _message);
	(* LOG_INFO=16#1; existing CmpLog interface, no added dependency. *)
	IF LEN(_message) <= 127 THEN
		_logResult := CoUnit.WRITE_DEVICE_LOG(msgCtrlMask := DWORD#16#1, msgFmtStr := _message, strArg := '');
	ELSE
		_logResult := CoUnit.WRITE_DEVICE_LOG(msgCtrlMask := DWORD#16#1, msgFmtStr := 'LC6 OVERFLOW', strArg := '');
	END_IF"""
            if timing_report_probe:
                method_decl = method_decl.replace("\n\t_logResult : DINT;", "")
                timing_check = timing_check.split("\n\t(* LOG_INFO=", 1)[0]
                timing_check += "\n\t(* Intentional diagnostic failure captures LC6 on either timing outcome. *)\n\tAssertTrue(Condition := FALSE, Message := _message);"
        items.append(_object("POU", second,
            f"FUNCTION_BLOCK {second} EXTENDS CoUnit.FB_TestSuite\nVAR\n\t_callsBeforeFirst : UINT;\n\t_accepted : BOOL;\nEND_VAR",
            "DispatchPreserved();", [_member("DispatchPreserved", method_decl,
            f"""CoUnit.TEST(TestName := 'DispatchPreserved');
IF NOT {shared}.FirstDone THEN
	_callsBeforeFirst := _callsBeforeFirst + 1;
	RETURN;
END_IF
IF NOT CoUnit.IS_TEST_FINISHED(TestName := 'DispatchPreserved') THEN
	AssertTrue(Condition := {order_check}, Message := 'legacy dispatch mode preserved');
	_accepted := CoUnit.CONFIGURE_LEGACY_RUN(RunId := 'second-suite-replacement', BuildId := 'replacement', TargetId := 'replacement', InSequence := {'FALSE' if sequential else 'TRUE'});
	AssertFalse(Condition := _accepted, Message := 'second suite cannot replace run context');{timing_check}
	CoUnit.TEST_FINISHED();
END_IF""")]))
        dispatch = "CoUnit.RUN_IN_SEQUENCE();" if sequential else "CoUnit.RUN();"
        items.append(_object("POU", runner,
            f"PROGRAM {runner}\nVAR\n\tfbFirst : {first};\n\tfbSecond : {second};\nEND_VAR", dispatch))
        for item in items:
            _write_object(folder, item)
        expectations[runner] = {
            "expectations_authored_before_execution": True,
            "framework_version": "2.1.0.6", "run_disposition": "NORMAL", "generation": 1,
            "run_mode": "IN_SEQUENCE" if sequential else "ALL_SUITES",
            "tests": 2, "failures": 0, "errors": 0, "skipped": 0,
            "TimeBetweenTestSuitesExecution": "TIME#100ms" if sequential else "TIME#0ms",
            "cases": [{"suite": first, "name": "ContextImmutable", "status": "passed", "assertions": 3},
                      {"suite": second, "name": "DispatchPreserved", "status": "passed", "assertions": 3 if sequential else 2}],
            "embedded_identity": "exact host-bound run/build/target; no legacy catalog identity or flag inference",
        }
        if instrument:
            expectations[runner]["diagnostic_capture"] = "Require complete LC6 INFO record in raw codesyscontrol.log; missing/overflow is INCONCLUSIVE. Original 100ms predicate and six assertions unchanged."
        if sequential and timing_report_probe:
            expectations[runner]["failures"] = 1
            expectations[runner]["cases"][1].update(status="failure", assertions=4)
            expectations[runner]["diagnostic_capture"] = "Intentional negative: require complete matching LC6 in XML/JSON first failure; two cases/seven assertions/one failed case. Original six assertions and 100ms predicate remain. This cannot be a qualification PASS."
    inventory_path = root / "_tools/library_ownership.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8-sig"))
    owner = next(row for row in inventory["owners"] if row["name"] == "Integration.Tests")
    owned_path = "PlaintextExport/Tests/UpgradeLegacy6/**"
    if owned_path not in owner["include"]:
        owner["include"].append(owned_path)
        inventory_path.write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    (folder / "expected.json").write_text(json.dumps(expectations, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"source_root": str(root), "expected": str(folder / "expected.json"), "native_status": "NOT_RUN"}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_root", type=Path)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--timing-probe", action="store_true", help="Add one bounded clock-observation log; do not change the sequence predicate or assertion count")
    modes.add_argument("--timing-report-probe", action="store_true", help="Preserve the timing check and add one intentional failure to capture clocks in the existing report")
    args = parser.parse_args()
    generate(args.source_root.resolve(), timing_probe=args.timing_probe, timing_report_probe=args.timing_report_probe)
