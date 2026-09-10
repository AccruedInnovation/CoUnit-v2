"""Generate supplemental lifecycle observations; never connects to CODESYS."""
from pathlib import Path
import json
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1] if (HERE.parents[1] / 'docs').is_dir() else HERE.parents[4]
sys.path.insert(0, str(REPO / '_tools'))
import generate_plcopenxml as plc


def obj(prefix, name, declaration, body=None):
    return plc.ObjectExport(prefix, name, declaration, body, ('LifecycleTrace',), HERE / name)


objects = [obj('GVL', 'GVL_LifecycleTrace', """{attribute 'qualified_only'}
VAR_GLOBAL
	Scan : UDINT;
	EventCount : UINT;
	Order : ARRAY[1..3] OF UINT;
	EntryMs : ARRAY[1..3] OF UDINT;
	ExitMs : ARRAY[1..3] OF UDINT;
	EntryScan : ARRAY[1..3] OF UDINT;
	ExitScan : ARRAY[1..3] OF UDINT;
	Visits : ARRAY[1..3] OF UDINT;
	DisabledBodyVisits : UDINT;
	HoldThird : BOOL;
END_VAR""")]

for index, suffix in [(1, 'First'), (2, 'Disabled'), (3, 'Third')]:
    name = 'FB_Lifecycle' + suffix
    body = f"""GVL_LifecycleTrace.Visits[{index}] := GVL_LifecycleTrace.Visits[{index}] + 1;
IF GVL_LifecycleTrace.Visits[{index}] = 1 THEN
	IF GVL_LifecycleTrace.EventCount < 3 THEN
		GVL_LifecycleTrace.EventCount := GVL_LifecycleTrace.EventCount + 1;
		GVL_LifecycleTrace.Order[GVL_LifecycleTrace.EventCount] := {index};
	END_IF
	GVL_LifecycleTrace.EntryMs[{index}] := TIME_TO_UDINT(TIME());
	GVL_LifecycleTrace.EntryScan[{index}] := GVL_LifecycleTrace.Scan;
END_IF
TEST('{'DISABLED_' if index == 2 else ''}{suffix}');
"""
    if index == 2:
        body += """(* TEST suppresses assertions, not arbitrary caller statements. *)
GVL_LifecycleTrace.DisabledBodyVisits := GVL_LifecycleTrace.DisabledBodyVisits + 1;
"""
    elif index == 3:
        body += "IF GVL_LifecycleTrace.HoldThird THEN RETURN; END_IF\nTEST_FINISHED();\n"
    else:
        body += 'TEST_FINISHED();\n'
    body += f"GVL_LifecycleTrace.ExitMs[{index}] := TIME_TO_UDINT(TIME());\nGVL_LifecycleTrace.ExitScan[{index}] := GVL_LifecycleTrace.Scan;"
    objects.append(obj('POU', name, f'FUNCTION_BLOCK {name} EXTENDS FB_TestSuite', body))

checks = [
    'PrestartIdleObserved',
    'RegistrationOrderObserved',
    'GVL_LifecycleTrace.EventCount = 3',
    'GVL_LifecycleTrace.Order[1] = 1 AND GVL_LifecycleTrace.Order[2] = 2 AND GVL_LifecycleTrace.Order[3] = 3',
    'GVL_LifecycleTrace.EntryScan[1] = 1',
    'FirstGapMs >= 100',
    'SecondGapMs >= 100',
    'GVL_LifecycleTrace.Visits[1] = 1',
    'GVL_LifecycleTrace.Visits[2] = 1',
    'GVL_LifecycleTrace.DisabledBodyVisits = 1',
    'GVL_LifecycleTrace.Visits[3] >= 1',
    'CompletedScan = GVL_LifecycleTrace.ExitScan[3]',
    'BetweenSuitesObserved',
    '_snapshot.IsValid',
    '_snapshot.Disposition = E_CoUnitRunDisposition.NORMAL',
    '_snapshot.Total = 3 AND _snapshot.Passed = 2 AND _snapshot.Skipped = 1',
    '_snapshot.Failed = 0 AND _snapshot.Errors = 0',
    '_snapshot.Suites[2].Tests[1].State = E_CoUnitTestState.SKIPPED',
]
declaration = """PROGRAM PRG_Qualification
VAR_INPUT
	Start : BOOL := FALSE;
	HoldThird : BOOL := FALSE;
END_VAR
VAR_OUTPUT
	Done : BOOL;
	OraclePass : BOOL;
	FailedCheck : UDINT;
	SnapshotBytes : UDINT;
	PrestartIdle : BOOL;
	PrestartIdleObserved : BOOL;
	RegistrationOrderObserved : BOOL;
	BetweenSuitesObserved : BOOL;
	ObservedState : E_CoUnitRunState;
	ObservedEpoch : ULINT;
	ObservedSuiteCount : UINT;
	ThirdRecordCount : UINT;
	ThirdRecordState : E_CoUnitTestState;
	ThirdRecordAvailable : BOOL;
	FirstGapMs : UDINT;
	SecondGapMs : UDINT;
	CompletedScan : UDINT;
	CompletedMs : UDINT;
	FirstRunMs : UDINT;
END_VAR
VAR
	_first : FB_LifecycleFirst;
	_disabled : FB_LifecycleDisabled;
	_third : FB_LifecycleThird;
	_snapshot : REFERENCE TO ST_CoUnitRunSnapshot;
	_record : ST_CoUnitTestRecord;
END_VAR"""
body = """SnapshotBytes := SIZEOF(ST_CoUnitRunSnapshot);
ObservedState := GVL_coUnit.coUnitRunner.GetRunState();
ObservedEpoch := GVL_coUnit.coUnitRunner.GetEpoch();
ObservedSuiteCount := GVL_coUnit.coUnitRunner.GetSuiteCount();
ThirdRecordCount := _third.GetNumberOfTests();
IF NOT Start THEN
	PrestartIdle := ObservedState = E_CoUnitRunState.IDLE AND ObservedEpoch = 0 AND
		ObservedSuiteCount = 3 AND ThirdRecordCount = 0 AND GVL_LifecycleTrace.EventCount = 0 AND
		GVL_LifecycleTrace.DisabledBodyVisits = 0 AND GVL_LifecycleTrace.Scan = 0;
	PrestartIdleObserved := PrestartIdleObserved OR PrestartIdle;
	RETURN;
END_IF
GVL_LifecycleTrace.HoldThird := HoldThird;
GVL_LifecycleTrace.Scan := GVL_LifecycleTrace.Scan + 1;
IF GVL_LifecycleTrace.Scan = 1 THEN FirstRunMs := TIME_TO_UDINT(TIME()); END_IF
(* Same internal path as RUN_IN_SEQUENCE, with explicit test delay instead of a constant override. *)
GVL_coUnit.coUnitRunner.RunTestSuiteTestsInSequence(TimeBetweenTestSuitesExecution := T#100ms);
ObservedState := GVL_coUnit.coUnitRunner.GetRunState();
ObservedEpoch := GVL_coUnit.coUnitRunner.GetEpoch();
RegistrationOrderObserved := GVL_coUnit.coUnitRunner.GetSuite(Index := 1) = ADR(_first) AND
	GVL_coUnit.coUnitRunner.GetSuite(Index := 2) = ADR(_disabled) AND
	GVL_coUnit.coUnitRunner.GetSuite(Index := 3) = ADR(_third);
BetweenSuitesObserved := BetweenSuitesObserved OR ObservedState = E_CoUnitRunState.BETWEEN_SUITES;
ThirdRecordCount := _third.GetNumberOfTests();
ThirdRecordAvailable := _third.GetCanonicalRecord(Index := 1, Record => _record);
IF ThirdRecordAvailable THEN ThirdRecordState := _record.State; END_IF
_snapshot REF= GVL_coUnit.coUnitRunner.GetSnapshot();
IF ObservedState = E_CoUnitRunState.COMPLETE AND NOT Done THEN
	CompletedScan := GVL_LifecycleTrace.Scan;
	CompletedMs := TIME_TO_UDINT(TIME());
	FirstGapMs := GVL_LifecycleTrace.EntryMs[2] - GVL_LifecycleTrace.ExitMs[1];
	SecondGapMs := GVL_LifecycleTrace.EntryMs[3] - GVL_LifecycleTrace.ExitMs[2];
	OraclePass := TRUE;
"""
for index, check in enumerate(checks, 1):
    body += f'\tIF NOT ({check}) THEN\n\t\tOraclePass := FALSE;\n\t\tIF FailedCheck = 0 THEN FailedCheck := {index}; END_IF\n\tEND_IF\n'
body += '\tDone := TRUE;\nEND_IF'
objects.append(obj('POU', 'PRG_Qualification', declaration, body))

for item in objects:
    folder = HERE / item.name
    folder.mkdir(exist_ok=True)
    (folder / f'{item.prefix}.{item.name}.DEC.exp').write_text(item.declaration + '\n', encoding='utf-8')
    if item.implementation is not None:
        (folder / f'{item.prefix}.{item.name}.IMP.exp').write_text(item.implementation + '\n', encoding='utf-8')
plc.build_xml(objects, 'CoUnit supplemental lifecycle trace').write(str(HERE / 'qualification.xml'), encoding='utf-8', xml_declaration=True)
(HERE / 'expected.json').write_text(json.dumps({'checks': checks, 'suites': [
    [{'name': 'First', 'state': 'PASSED', 'assertions': 0}],
    [{'name': 'Disabled', 'state': 'SKIPPED', 'assertions': 0}],
    [{'name': 'Third', 'state': 'PASSED', 'assertions': 0}],
]}, indent=2) + '\n', encoding='utf-8')
print('Generated three-suite 100 ms lifecycle trace with gated initial/reset observations')
