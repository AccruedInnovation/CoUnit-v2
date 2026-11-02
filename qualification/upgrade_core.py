"""Emit isolated PLCOpenXML upgrade examples and core qualification fixtures."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / '_tools'))
import generate_plcopenxml as plc

OUT = Path(__file__).resolve().parent / 'generated'


def member(name, declaration, implementation):
    return plc.Member('M', name, declaration, implementation, OUT / name)


def obj(prefix, name, declaration, implementation='', members=()):
    if prefix == 'POU' and name.startswith('FB_') and not (implementation or '').strip():
        implementation = '(* Execution through methods. *)'
    return plc.ObjectExport(prefix, name, declaration, implementation, ('UpgradeCore',), OUT / name, members=list(members))


def emit_package(name, objects, expected):
    root = OUT / name
    if root.exists():
        out_real = OUT.resolve()
        root_real = root.resolve()
        if root.is_symlink() or root_real == out_real or not root_real.is_relative_to(out_real):
            raise ValueError(f'refusing to clear generated package outside output root: {root}')
        shutil.rmtree(root_real)
    root.mkdir(parents=True, exist_ok=True)
    for item in objects:
        folder = root / item.name
        folder.mkdir(parents=True, exist_ok=True)
        filename = f'{item.name}.DEC.exp' if item.prefix == 'I' else f'{item.prefix}.{item.name}.DEC.exp'
        (folder / filename).write_text(item.declaration + '\n', encoding='utf-8')
        if item.implementation is not None:
            imp = f'{item.name}.IMP.exp' if item.prefix == 'I' else f'{item.prefix}.{item.name}.IMP.exp'
            (folder / imp).write_text(item.implementation + '\n', encoding='utf-8')
        for m in item.members:
            method_folder = folder / m.name
            method_folder.mkdir(exist_ok=True)
            (method_folder / f'{m.name}.DEC.exp').write_text(m.declaration + '\n', encoding='utf-8')
            if m.implementation is not None:
                (method_folder / f'{m.name}.IMP.exp').write_text(m.implementation + '\n', encoding='utf-8')
    plc.build_xml(objects, f'CoUnit upgrade qualification: {name}').write(root / 'qualification.xml', encoding='utf-8', xml_declaration=True)
    (root / 'expected.json').write_text(json.dumps(expected, indent=2) + '\n', encoding='utf-8')


def catalog():
    describe = member('Describe', 'METHOD Describe\nVAR\n\t_identityOk : BOOL;\n\t_unusedHandle : UINT;\nEND_VAR', '''_identityOk := SetCatalogIdentity(SuiteId := 'upgrade');
_handleA := DefineCase(CaseId := 'row', Name := 'RowA', RowKey := 'a', Tags := 'upgrade', Disabled := FALSE);
_handleB := DefineCase(CaseId := 'row', Name := 'RowB', RowKey := 'b', Tags := 'upgrade', Disabled := FALSE);
_handleDisabled := DefineCase(CaseId := 'row', Name := 'DISABLED_Off', RowKey := 'disabled', Tags := 'upgrade', Disabled := TRUE);''')
    suite = obj('POU', 'FB_UpgradeCatalog', '''FUNCTION_BLOCK FB_UpgradeCatalog EXTENDS FB_TestSuite
VAR_OUTPUT
	RowAEffects : UINT;
	RowBEffects : UINT;
	DisabledEffects : UINT;
	RowBScans : UINT;
END_VAR
VAR
	_handleA : UINT;
	_handleB : UINT;
	_handleDisabled : UINT;
END_VAR''', '''IF BeginCase(Handle := _handleA) THEN
	RowAEffects := RowAEffects + 1;
	AssertResult(Passed := TRUE, CheckId := 'upgrade/row/a', Message := 'Row A', ExpectedText := 'unused', ActualText := 'unused', Detail := 'A must remain unselected');
	TEST_FINISHED();
END_IF
IF BeginCase(Handle := _handleB) THEN
	RowBEffects := RowBEffects + 1;
	RowBScans := RowBScans + 1;
	AssertResult(Passed := (RowAEffects = 0) AND (DisabledEffects = 0) AND (RowBEffects = RowBScans) AND (RowBScans <= 3), CheckId := 'upgrade/row/b', Message := 'Only the selected row may produce effects', ExpectedText := 'RowA=0; disabled=0; RowB=scan', ActualText := CONCAT(CONCAT(UINT_TO_STRING(RowAEffects), '/'), CONCAT(UINT_TO_STRING(DisabledEffects), CONCAT('/', UINT_TO_STRING(RowBEffects)))), Detail := 'three cyclic invocations');
	IF RowBScans >= 3 THEN
		TEST_FINISHED();
	END_IF
END_IF
IF BeginCase(Handle := _handleDisabled) THEN
	DisabledEffects := DisabledEffects + 1;
	TEST_FINISHED();
END_IF''', [describe])
    prg_decl = '''PROGRAM PRG_Qualification
VAR_OUTPUT
	Done : BOOL;
	OraclePass : BOOL;
	FailedCheck : UINT;
	SnapshotBytes : UDINT;
END_VAR
VAR
	Exchange : ST_CoUnitExchange;
	Suite : FB_UpgradeCatalog;
	_step : UINT;
	_request : ULINT;
	_waiting : BOOL;
	_configured : BOOL;
	_listA : BOOL;
	_listB : BOOL;
	_listDisabled : BOOL;
	_selected : BOOL;
	_started : BOOL;
	_rowAResult : BOOL;
	_rowBResult : BOOL;
	_disabledResult : BOOL;
	_cancelRejected : BOOL;
	_finalStatus : BOOL;
	_epochBeforeCancel : ULINT;
END_VAR'''
    prg_body = '''SnapshotBytes := SIZEOF(ST_CoUnitRunSnapshot);
IF NOT _waiting THEN
	CASE _step OF
	0:
		_request := _request + 1; Exchange.Operation := 1; Exchange.RunId := 'upgrade-run-1'; Exchange.BuildId := 'upgrade-build-1'; Exchange.TargetId := 'qualified-simulator';
		Exchange.RunTimeout := T#10s; Exchange.CleanupTimeout := T#2s; Exchange.RequestId := _request; _waiting := TRUE;
	1:
		IF Exchange.Status.CatalogReady THEN
			_request := _request + 1; Exchange.Operation := 5; Exchange.SuiteIndex := 1; Exchange.CaseIndex := 1; Exchange.RequestId := _request; _waiting := TRUE;
		END_IF
	2:
		_request := _request + 1; Exchange.Operation := 5; Exchange.SuiteIndex := 1; Exchange.CaseIndex := 2; Exchange.RequestId := _request; _waiting := TRUE;
	3:
		_request := _request + 1; Exchange.Operation := 5; Exchange.SuiteIndex := 1; Exchange.CaseIndex := 3; Exchange.RequestId := _request; _waiting := TRUE;
	4:
		_request := _request + 1; Exchange.Operation := 2; Exchange.RunId := 'upgrade-run-1'; Exchange.ExpectedGeneration := 1; Exchange.SuiteId := 'upgrade'; Exchange.CaseId := 'row'; Exchange.RowKey := 'b'; Exchange.RequestId := _request; _waiting := TRUE;
	5:
		_request := _request + 1; Exchange.Operation := 3; Exchange.RunId := 'upgrade-run-1'; Exchange.ExpectedGeneration := 1; Exchange.ExpectedSelected := 1; Exchange.RequestId := _request; _waiting := TRUE;
	6:
		IF Exchange.Status.ExecutionComplete AND Exchange.Status.ResultsAvailable THEN
			_request := _request + 1; Exchange.Operation := 5; Exchange.RunId := 'upgrade-run-1'; Exchange.ExpectedGeneration := 1; Exchange.SuiteIndex := 1; Exchange.CaseIndex := 1; Exchange.RequestId := _request; _waiting := TRUE; _step := 7;
		ELSE _started := _started OR Exchange.Status.SelectionFrozen; END_IF
	8:
		_request := _request + 1; Exchange.Operation := 5; Exchange.RunId := 'upgrade-run-1'; Exchange.ExpectedGeneration := 1; Exchange.SuiteIndex := 1; Exchange.CaseIndex := 2; Exchange.RequestId := _request; _waiting := TRUE;
	9:
		_request := _request + 1; Exchange.Operation := 5; Exchange.RunId := 'upgrade-run-1'; Exchange.ExpectedGeneration := 1; Exchange.SuiteIndex := 1; Exchange.CaseIndex := 3; Exchange.RequestId := _request; _waiting := TRUE;
	10:
		_epochBeforeCancel := Exchange.Status.ProgressEpoch;
		_request := _request + 1; Exchange.Operation := 4; Exchange.RunId := 'stale-run'; Exchange.ExpectedGeneration := 99; Exchange.RequestId := _request; _waiting := TRUE;
	11:
		_finalStatus := Exchange.Status.ExecutionComplete AND Exchange.Status.ResultsAvailable AND (Exchange.Status.Disposition = E_CoUnitRunDisposition.NORMAL) AND (Exchange.Status.RunId = 'upgrade-run-1') AND (Exchange.Status.Generation = 1) AND Exchange.Status.SelectionFrozen;
		OraclePass := _configured AND _listA AND _listB AND _listDisabled AND _selected AND _started AND _rowAResult AND _rowBResult AND _disabledResult AND _cancelRejected AND _finalStatus AND (Suite.RowAEffects = 0) AND (Suite.RowBEffects = 3) AND (Suite.DisabledEffects = 0) AND (Suite.RowBScans = 3);
		FailedCheck := 0;
		IF NOT _configured THEN FailedCheck := 1; ELSIF NOT _listA THEN FailedCheck := 2; ELSIF NOT _listB THEN FailedCheck := 3; ELSIF NOT _listDisabled THEN FailedCheck := 4; ELSIF NOT _selected THEN FailedCheck := 5; ELSIF NOT _started THEN FailedCheck := 6; ELSIF NOT _rowAResult THEN FailedCheck := 7; ELSIF NOT _rowBResult THEN FailedCheck := 8; ELSIF NOT _disabledResult THEN FailedCheck := 9; ELSIF NOT _cancelRejected THEN FailedCheck := 10; ELSIF NOT _finalStatus THEN FailedCheck := 11; ELSIF Suite.RowAEffects <> 0 THEN FailedCheck := 12; ELSIF Suite.RowBEffects <> 3 THEN FailedCheck := 13; ELSIF Suite.DisabledEffects <> 0 THEN FailedCheck := 14; ELSIF Suite.RowBScans <> 3 THEN FailedCheck := 15; END_IF
		Done := TRUE;
	END_CASE
ELSE
	IF Exchange.AckId = _request THEN
		_waiting := FALSE;
		CASE _step OF
		0: _configured := Exchange.Accepted AND (Exchange.Status.Generation = 1); _step := 1;
		1: _listA := Exchange.Accepted AND (Exchange.Page.RunId = 'upgrade-run-1') AND (Exchange.Page.Generation = 1) AND (Exchange.Page.SuiteId = 'upgrade') AND (Exchange.Page.CaseId = 'row') AND (Exchange.Page.RowKey = 'a') AND (Exchange.Page.Name = 'RowA') AND Exchange.Page.Selected AND NOT Exchange.Page.Disabled AND (Suite.RowAEffects = 0); _step := 2;
		2: _listB := Exchange.Accepted AND (Exchange.Page.CaseId = 'row') AND (Exchange.Page.RowKey = 'b') AND (Exchange.Page.Name = 'RowB') AND Exchange.Page.Selected AND NOT Exchange.Page.Disabled AND (Suite.RowBEffects = 0); _step := 3;
		3: _listDisabled := Exchange.Accepted AND (Exchange.Page.CaseId = 'row') AND (Exchange.Page.RowKey = 'disabled') AND (Exchange.Page.Name = 'Off') AND Exchange.Page.Selected AND Exchange.Page.Disabled AND (Suite.DisabledEffects = 0); _step := 4;
		4: _selected := Exchange.Accepted AND (Exchange.Status.SelectedCount = 1); _step := 5;
		5: _started := _started OR (Exchange.Accepted AND Exchange.Status.SelectionFrozen); _step := 6;
		7: _rowAResult := Exchange.Accepted AND NOT Exchange.Page.Selected AND NOT Exchange.Page.Started AND (Exchange.Page.State = E_CoUnitTestState.SKIPPED) AND (Suite.RowAEffects = 0); _step := 8;
		8: _rowBResult := Exchange.Accepted AND Exchange.Page.Selected AND Exchange.Page.Started AND (Exchange.Page.State = E_CoUnitTestState.PASSED) AND (Exchange.Page.MaxAssertionsPerInvocation = 1) AND (Suite.RowBEffects = 3) AND (Suite.RowBScans = 3); _step := 9;
		9: _disabledResult := Exchange.Accepted AND NOT Exchange.Page.Selected AND Exchange.Page.Disabled AND NOT Exchange.Page.Started AND (Exchange.Page.State = E_CoUnitTestState.SKIPPED) AND (Suite.DisabledEffects = 0); _step := 10;
		10: _cancelRejected := NOT Exchange.Accepted AND Exchange.Status.ExecutionComplete AND (Exchange.Status.Disposition = E_CoUnitRunDisposition.NORMAL) AND (Exchange.Status.ProgressEpoch = _epochBeforeCancel) AND (Exchange.Status.RunId = 'upgrade-run-1') AND (Exchange.Status.Generation = 1); _step := 11;
		END_CASE
	END_IF
END_IF
RUN_CONTROLLED(Exchange := Exchange);'''
    program = obj('POU', 'PRG_Qualification', prg_decl, prg_body)
    expected = {'native_status': 'NOT_RUN', 'done': True, 'oracle_pass': True, 'failed_check': 0,
                'public_contract': {'run_id': 'upgrade-run-1', 'generation': 1, 'suite_id': 'upgrade', 'case_id': 'row',
                                    'rows': {'a': {'name': 'RowA', 'selected': False, 'started': False, 'state': 'OPEN'},
                                             'b': {'name': 'RowB', 'selected': True, 'started': True, 'state': 'PASSED', 'max_assertions_per_invocation': 1},
                                             'disabled': {'name': 'Off', 'selected': False, 'disabled': True, 'started': False, 'state': 'SKIPPED'}},
                                    'effects': {'row_a': 0, 'row_b': 3, 'disabled': 0}, 'stale_cancel_accepted': False,
                                    'final_disposition': 'NORMAL'}}
    emit_package('upgrade_catalog', [suite, program], expected)


def legacy_guarded():
    disabled = member('Disabled', 'METHOD Disabled', '''IF TEST_GUARDED('DISABLED_GuardedOff') THEN
	DisabledEffects := DisabledEffects + 1;
	AssertResult(Passed := TRUE, CheckId := 'legacy/disabled', Message := 'unreachable', ExpectedText := '', ActualText := '', Detail := '');
	TEST_FINISHED();
END_IF''')
    active = member('Active', 'METHOD Active', '''IF TEST_GUARDED('GuardedActive') THEN
	ActiveEffects := ActiveEffects + 1;
	AssertResult(Passed := TRUE, CheckId := 'legacy/active', Message := 'guarded active', ExpectedText := 'one visit', ActualText := 'one visit', Detail := '');
	ActiveCompleted := TRUE;
	TEST_FINISHED();
END_IF''')
    suite = obj('POU', 'FB_UpgradeLegacyGuarded', '''FUNCTION_BLOCK FB_UpgradeLegacyGuarded EXTENDS FB_TestSuite
VAR_OUTPUT
	DisabledEffects : UINT;
	ActiveEffects : UINT;
	ActiveCompleted : BOOL;
END_VAR''', 'Disabled();\nActive();', [disabled, active])
    program = obj('POU', 'PRG_Qualification', '''PROGRAM PRG_Qualification
VAR_OUTPUT
	Done : BOOL;
	OraclePass : BOOL;
	FailedCheck : UINT;
END_VAR
VAR
	Suite : FB_UpgradeLegacyGuarded;
END_VAR''', '''RUN();
IF Suite.ActiveCompleted THEN
	Done := TRUE;
	OraclePass := (Suite.DisabledEffects = 0) AND (Suite.ActiveEffects = 1);
	IF NOT OraclePass THEN FailedCheck := 1; END_IF
END_IF''')
    emit_package('upgrade_legacy', [suite, program], {'native_status': 'NOT_RUN', 'done': True, 'oracle_pass': True,
                                                       'effects': {'disabled': 0, 'active': 1},
                                                       'cases': [{'name': 'GuardedOff', 'state': 'SKIPPED', 'assertions': 0},
                                                                 {'name': 'GuardedActive', 'state': 'PASSED', 'assertions': 1}]})


def strict_fixture(kind):
    if kind == 'empty':
        describe_body = "_h1 := DefineCase(CaseId := 'partial', Name := 'Defined before invalid suite identity', RowKey := '', Tags := '', Disabled := FALSE);"
        suite_body = ''
        expected_selected, allow_empty = 0, 'TRUE'
        expected_reason = 'Catalog suite omitted stable identity'
    elif kind == 'duplicate':
        describe_body = "_ok := SetCatalogIdentity(SuiteId := 'strict-duplicate');\n_h1 := DefineCase(CaseId := 'case', Name := 'Same', RowKey := 'row', Tags := '', Disabled := FALSE);\n_h2 := DefineCase(CaseId := 'case', Name := 'SameAgain', RowKey := 'row', Tags := '', Disabled := FALSE);"
        suite_body = ''
        expected_selected, allow_empty = 0, 'FALSE'
        expected_reason = 'Duplicate stable case and parameter row'
    else:
        describe_body = "_ok := SetCatalogIdentity(SuiteId := 'strict-unbound');\n_h1 := DefineCase(CaseId := 'declared', Name := 'Declared', RowKey := '', Tags := '', Disabled := FALSE);"
        suite_body = "TEST('Unexpected');\nTEST_FINISHED();"
        expected_selected, allow_empty = 1, 'FALSE'
        expected_reason = 'Dynamic TEST cannot mutate a frozen catalog'
    describe = member('Describe', 'METHOD Describe\nVAR\n\t_ok : BOOL;\n\t_h1 : UINT;\n\t_h2 : UINT;\nEND_VAR', describe_body)
    suite = obj('POU', 'FB_UpgradeStrict', '''FUNCTION_BLOCK FB_UpgradeStrict EXTENDS FB_TestSuite''', suite_body, [describe])
    program = obj('POU', 'PRG_Qualification', '''PROGRAM PRG_Qualification
VAR_OUTPUT
	Done : BOOL;
	OraclePass : BOOL;
	FailedCheck : UINT;
END_VAR
VAR
	Exchange : ST_CoUnitExchange;
	Suite : FB_UpgradeStrict;
	_step : UINT;
	_request : ULINT;
	_waiting : BOOL;
	_configAccepted : BOOL;
	_startAccepted : BOOL;
END_VAR''', f'''IF NOT _waiting THEN
	CASE _step OF
	0:
		_request := _request + 1; Exchange.Operation := 1; Exchange.RunId := 'strict-{kind}-run'; Exchange.BuildId := 'strict-build'; Exchange.TargetId := 'qualified-simulator'; Exchange.RunTimeout := T#10s; Exchange.CleanupTimeout := T#2s; Exchange.RequestId := _request; _waiting := TRUE;
	1:
		IF Exchange.Status.CatalogReady THEN
			_request := _request + 1; Exchange.Operation := 3; Exchange.RunId := 'strict-{kind}-run'; Exchange.ExpectedGeneration := 1; Exchange.ExpectedSelected := {expected_selected}; Exchange.AllowEmpty := {allow_empty}; Exchange.RequestId := _request; _waiting := TRUE;
		ELSIF Exchange.Status.ExecutionComplete AND (Exchange.Status.Disposition = E_CoUnitRunDisposition.FRAMEWORK_ERROR) THEN
			Done := TRUE; OraclePass := (Exchange.Status.Reason = '{expected_reason}') AND (Exchange.Status.TotalCount = 1) AND (Exchange.Status.ErrorCount = 1); IF NOT OraclePass THEN FailedCheck := 1; END_IF
		END_IF
	2:
		IF Exchange.Status.ExecutionComplete AND (Exchange.Status.Disposition = E_CoUnitRunDisposition.FRAMEWORK_ERROR) THEN
			Done := TRUE; OraclePass := _startAccepted AND (Exchange.Status.Reason = '{expected_reason}'); IF NOT OraclePass THEN FailedCheck := 2; END_IF
		END_IF
	END_CASE
ELSE
	IF Exchange.AckId = _request THEN
		_waiting := FALSE;
		IF _step = 0 THEN _configAccepted := Exchange.Accepted; _step := 1;
		ELSIF _step = 1 THEN _startAccepted := Exchange.Accepted; _step := 2;
		END_IF
	END_IF
END_IF
RUN_CONTROLLED(Exchange := Exchange);''')
    emit_package(f'upgrade_strict_{kind}', [suite, program], {'native_status': 'NOT_RUN', 'done': True, 'oracle_pass': True,
                                                             'disposition': 'FRAMEWORK_ERROR', 'reason': expected_reason,
                                                             'configuration_accepted': kind not in ('duplicate', 'empty'),
                                                             'start_accepted': kind not in ('duplicate', 'empty')})


def assertions():
    suite = obj('POU', 'FB_UpgradeAssertions', '''FUNCTION_BLOCK FB_UpgradeAssertions EXTENDS FB_TestSuite
VAR_OUTPUT
	CustomEffects : UINT;
	FloatEffects : UINT;
	StringEffects : UINT;
END_VAR
VAR
	_hCustom : UINT;
	_hFloat : UINT;
	_hString : UINT;
	_expectedBits : DWORD := DWORD#16#3F800000;
	_actualBits : DWORD := DWORD#16#3F800001;
	_expectedFloat : REAL;
	_actualFloat : REAL;
	_expected : STRING(300);
	_actual : STRING(300);
	_expectedPtr : POINTER TO BYTE;
	_actualPtr : POINTER TO BYTE;
	_i : UINT;
END_VAR''', '''IF BeginCase(Handle := _hCustom) THEN
	CustomEffects := CustomEffects + 1;
	AssertResult(Passed := FALSE, CheckId := 'domain/limit', Message := 'custom failure', ExpectedText := 'limit=10', ActualText := 'limit=12', Detail := 'first failed custom assertion');
	TEST_FINISHED();
END_IF
IF BeginCase(Handle := _hFloat) THEN
	FloatEffects := FloatEffects + 1;
	MEMCPY(destAddr := ADR(_expectedFloat), srcAddr := ADR(_expectedBits), n := SIZEOF(_expectedFloat));
	MEMCPY(destAddr := ADR(_actualFloat), srcAddr := ADR(_actualBits), n := SIZEOF(_actualFloat));
	AssertEquals_REAL(Expected := _expectedFloat, Actual := _actualFloat, Delta := 0.0, Message := 'adjacent finite REAL values');
	TEST_FINISHED();
END_IF
IF BeginCase(Handle := _hString) THEN
	_expectedPtr := ADR(_expected); _actualPtr := ADR(_actual);
	FOR _i := 0 TO 299 DO _expectedPtr[_i] := BYTE#16#41; _actualPtr[_i] := BYTE#16#41; END_FOR
	_expectedPtr[300] := 0; _actualPtr[300] := 0; _actualPtr[299] := BYTE#16#42;
	StringEffects := StringEffects + 1;
	AssertEquals(Expected := _expected, Actual := _actual, Message := 'late long string mismatch');
	TEST_FINISHED();
END_IF''', [member('Describe', 'METHOD Describe\nVAR\n\t_ok : BOOL;\nEND_VAR', "_ok := SetCatalogIdentity(SuiteId := 'upgrade-assertions');\n_hCustom := DefineCase(CaseId := 'assertion', Name := 'Custom', RowKey := 'custom', Tags := '', Disabled := FALSE);\n_hFloat := DefineCase(CaseId := 'assertion', Name := 'FloatNear', RowKey := 'float', Tags := '', Disabled := FALSE);\n_hString := DefineCase(CaseId := 'assertion', Name := 'LongString', RowKey := 'string', Tags := '', Disabled := FALSE);")])
    program = obj('POU', 'PRG_Qualification', '''PROGRAM PRG_Qualification
VAR_OUTPUT
	Done : BOOL;
	OraclePass : BOOL;
	FailedCheck : UINT;
END_VAR
VAR
	Exchange : ST_CoUnitExchange;
	Suite : FB_UpgradeAssertions;
	_step : UINT;
	_request : ULINT;
	_waiting : BOOL;
	_configured : BOOL;
	_started : BOOL;
	_customObserved : BOOL;
	_floatObserved : BOOL;
	_stringObserved : BOOL;
END_VAR''', '''IF NOT _started THEN
IF NOT _waiting THEN
	CASE _step OF
	0: _request := _request + 1; Exchange.Operation := 1; Exchange.RunId := 'assertions-run'; Exchange.BuildId := 'assertions-build'; Exchange.TargetId := 'qualified-simulator'; Exchange.RunTimeout := T#10s; Exchange.CleanupTimeout := T#2s; Exchange.RequestId := _request; _waiting := TRUE; _step := 1;
	2: IF Exchange.Status.CatalogReady THEN _request := _request + 1; Exchange.Operation := 3; Exchange.RunId := 'assertions-run'; Exchange.ExpectedGeneration := 1; Exchange.ExpectedSelected := 3; Exchange.RequestId := _request; _waiting := TRUE; _step := 3; END_IF
	4: IF Exchange.Status.ExecutionComplete THEN _request := _request + 1; Exchange.Operation := 5; Exchange.RunId := 'assertions-run'; Exchange.ExpectedGeneration := 1; Exchange.SuiteIndex := 1; Exchange.CaseIndex := 1; Exchange.RequestId := _request; _waiting := TRUE; _step := 5; END_IF
	6: _request := _request + 1; Exchange.Operation := 5; Exchange.RunId := 'assertions-run'; Exchange.ExpectedGeneration := 1; Exchange.SuiteIndex := 1; Exchange.CaseIndex := 2; Exchange.RequestId := _request; _waiting := TRUE; _step := 7;
	8: _request := _request + 1; Exchange.Operation := 5; Exchange.RunId := 'assertions-run'; Exchange.ExpectedGeneration := 1; Exchange.SuiteIndex := 1; Exchange.CaseIndex := 3; Exchange.RequestId := _request; _waiting := TRUE; _step := 9;
	10:
		OraclePass := _configured AND _started AND _customObserved AND _floatObserved AND _stringObserved AND (Exchange.Status.Disposition = E_CoUnitRunDisposition.NORMAL) AND (Suite.CustomEffects = 1) AND (Suite.FloatEffects = 1) AND (Suite.StringEffects = 1);
		IF NOT OraclePass THEN FailedCheck := 1; END_IF Done := TRUE;
	END_CASE
ELSE
	IF Exchange.AckId = _request THEN
		_waiting := FALSE;
		CASE _step OF
		1: _configured := Exchange.Accepted AND Exchange.Status.CatalogReady; _step := 2;
		3: _started := Exchange.Accepted AND Exchange.Status.SelectionFrozen; _step := 4;
		5: _customObserved := Exchange.Accepted AND (Exchange.Page.State = E_CoUnitTestState.FAILED) AND Exchange.Page.FirstFailure.IsSet AND (Exchange.Page.FirstFailure.AssertionType = E_AssertionType.Type_BOOL) AND (Exchange.Page.FirstFailure.ExpectedText = 'limit=10') AND (Exchange.Page.FirstFailure.ActualText = 'limit=12') AND (FIND(Exchange.Page.FirstFailure.Message, 'domain/limit') > 0);
		   _step := 6;
		7: _floatObserved := Exchange.Accepted AND (Exchange.Page.State = E_CoUnitTestState.FAILED) AND Exchange.Page.FirstFailure.IsSet AND (Exchange.Page.FirstFailure.ExpectedText <> Exchange.Page.FirstFailure.ActualText) AND (FIND(Exchange.Page.FirstFailure.ExpectedText, '16#3F800000') > 0) AND (FIND(Exchange.Page.FirstFailure.ActualText, '16#3F800001') > 0) AND (FIND(Exchange.Page.FirstFailure.Message, 'Delta=') > 0) AND (FIND(Exchange.Page.FirstFailure.Message, '16#00000000') > 0); _step := 8;
		9: _stringObserved := Exchange.Accepted AND (Exchange.Page.State = E_CoUnitTestState.FAILED) AND Exchange.Page.FirstFailure.IsSet AND (Exchange.Page.FirstFailure.AssertionType = E_AssertionType.Type_ANY) AND (Exchange.Page.FirstFailure.ExpectedText = 'code units=300') AND (Exchange.Page.FirstFailure.ActualText = 'code units=300') AND (FIND(Exchange.Page.FirstFailure.Message, 'offset=299') > 0); _step := 10;
		END_CASE
	END_IF
END_IF
RUN_CONTROLLED(Exchange := Exchange);''')
    emit_package('upgrade_assertions', [suite, program], {'native_status': 'NOT_RUN', 'done': True, 'oracle_pass': True,
                                                         'effects': {'custom': 1, 'float': 1, 'string': 1},
                                                         'cases': [{'name': 'Custom', 'state': 'FAILED', 'assertions': 1, 'check_id': 'domain/limit'},
                                                                   {'name': 'FloatNear', 'state': 'FAILED', 'assertions': 1,
                                                                    'expected_raw_bits': '3F800000', 'actual_raw_bits': '3F800001', 'applied_delta_raw_bits': '00000000'},
                                                                   {'name': 'LongString', 'state': 'FAILED', 'assertions': 1, 'expected_code_units': 300, 'actual_code_units': 300, 'mismatch_offset': 299}]})


def main():
    catalog()
    legacy_guarded()
    for scenario in ('empty', 'duplicate', 'unbound'):
        strict_fixture(scenario)
    assertions()
    print('Generated upgrade catalog, strict-definition, guarded, and assertion packages')


if __name__ == '__main__':
    main()
