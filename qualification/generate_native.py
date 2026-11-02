"""Generate isolated native CoUnit 2.0 qualification shards and independent oracles.

Only emits source/XML under qualification/generated. It never touches CODESYS.
Import one shard into a clean application containing the candidate library objects.
Call only PRG_Qualification from a cyclic task; RUN invokes the suite bodies.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent if (HERE.parent / 'docs').is_dir() else HERE.parents[3]
sys.path.insert(0, str(REPO / '_tools'))
import generate_plcopenxml as plc


def obj(prefix, name, declaration, implementation=None, members=None):
    return plc.ObjectExport(prefix, name, declaration, implementation, ('Qualification',), HERE / 'generated' / name, members=members or [])


def method(name, declaration, body):
    return plc.Member('M', name, declaration, body, HERE / 'generated' / name)


def case(name, body, declarations='', state='PASSED', count=1, failure_type=None, message=None, exact_message=True):
    wrapped = f"TEST('{name}');\nIF NOT IS_TEST_FINISHED('{name}') THEN\n" + '\n'.join('\t' + line for line in body.splitlines()) + '\nEND_IF'
    member = method(name, f'METHOD {name}\n' + (f'VAR\n{declarations}\nEND_VAR' if declarations else ''), wrapped)
    expected = {'name': name, 'state': state, 'assertions': count}
    if failure_type:
        expected.update(failure_type=failure_type)
        expected['message' if exact_message else 'message_contains'] = message or name
    return member, expected


def suite(name, cases, variables=''):
    return obj('POU', name, f'FUNCTION_BLOCK {name} EXTENDS FB_TestSuite\nVAR\n{variables}\nEND_VAR', '\n'.join(f'{m.name}();' for m, _ in cases), [m for m, _ in cases])


def runner(suites, expectations, sequence=False, extra_vars='', extra_body='', disposition='NORMAL'):
    checks = ['_snapshot.IsValid', f'_snapshot.Disposition = E_CoUnitRunDisposition.{disposition}', f'_snapshot.SuiteCount = UINT#{len(suites)}', f'_snapshot.Total = UDINT#{sum(len(c) for c in expectations)}']
    states = [case['state'] for cases in expectations for case in cases]
    for state, field in [('PASSED', 'Passed'), ('FAILED', 'Failed'), ('SKIPPED', 'Skipped')]:
        checks.append(f'_snapshot.{field} = UDINT#{states.count(state)}')
    checks.append(f'_snapshot.Errors = UDINT#{states.count("ERROR") + states.count("ABORTED")}')
    for si, cases in enumerate(expectations, 1):
        checks.append(f'_snapshot.Suites[{si}].Total = UINT#{len(cases)}')
        for ti, expected in enumerate(cases, 1):
            record = f'_snapshot.Suites[{si}].Tests[{ti}]'
            checks += [f"{record}.Name = '{expected['name']}'", f"{record}.State = E_CoUnitTestState.{expected['state']}", f"{record}.NumberOfAsserts = UINT#{expected['assertions']}"]
            if 'failure_type' in expected:
                checks += [f'{record}.FirstFailure.IsSet', f"{record}.FirstFailure.AssertionType = E_AssertionType.{expected['failure_type']}"]
                checks.append(f"{record}.FirstFailure.Message = '{expected['message']}'" if 'message' in expected else f"FIND({record}.FirstFailure.Message, '{expected['message_contains']}') > 0")
    body = f"SnapshotBytes := SIZEOF(ST_CoUnitRunSnapshot);\n{'RUN_IN_SEQUENCE' if sequence else 'RUN'}();\n_snapshot REF= GVL_coUnit.coUnitRunner.GetSnapshot();\nIF (GVL_coUnit.coUnitRunner.GetRunState() = E_CoUnitRunState.COMPLETE) AND NOT Done THEN\n\tOraclePass := TRUE;\n"
    if suites and suites[0].name == 'FB_QualificationMultiscan':
        checks += ["_snapshot.Suites[1].Tests[2].FirstFailure.ExpectedText = 'TRUE'", "_snapshot.Suites[1].Tests[2].FirstFailure.ActualText = 'FALSE'", '_suite1.LaterFailureExecuted']
    if suites and suites[0].name == 'FB_QualificationNames':
        checks += ['_suite1.ShapePreserved']
    if suites and suites[0].name in ('FB_QualificationAssertionLimit', 'FB_QualificationTestLimit') and disposition == 'FRAMEWORK_ERROR':
        checks += ['_suite1.GuardPass']
    for i, check in enumerate(checks, 1):
        body += f'\tIF NOT ({check}) THEN\n\t\tOraclePass := FALSE;\n\t\tIF FailedCheck = 0 THEN FailedCheck := {i}; END_IF\n\tEND_IF\n'
    body += '\tDone := TRUE;\nEND_IF\n' + extra_body
    declaration = 'PROGRAM PRG_Qualification\nVAR_OUTPUT\n\tDone : BOOL;\n\tOraclePass : BOOL;\n\tFailedCheck : UDINT;\n\tSnapshotBytes : UDINT;\nEND_VAR\nVAR\n'
    declaration += '\n'.join(f'\t_suite{i} : {s.name};' for i, s in enumerate(suites, 1))
    declaration += '\n\t_snapshot : REFERENCE TO ST_CoUnitRunSnapshot;\n' + extra_vars + '\nEND_VAR'
    return obj('POU', 'PRG_Qualification', declaration, body), checks


def assertions():
    with (REPO / 'docs/CoUnit-PRD-Suite-R3/PRD-COU-02/contracts/assertion-family-map.csv').open(newline='', encoding='utf-8') as stream:
        rows = list(csv.DictReader(stream))
    cases, variables = [], []
    values = {'BOOL': ('TRUE', 'FALSE'), 'STRING': ("'expected'", "'actual'"), 'WSTRING': ('"expected"', '"actual"'), 'DATE': ('D#2020-01-01', 'D#2020-01-02'), 'DATE_AND_TIME': ('DT#2020-01-01-00:00:00', 'DT#2020-01-02-00:00:00'), 'TIME_OF_DAY': ('TOD#01:00:00', 'TOD#02:00:00'), 'TIME': ('T#1ms', 'T#2ms'), 'LTIME': ('LTIME#1ns', 'LTIME#2ns')}
    for i, row in enumerate(rows):
        name = row['method']
        typ = name.removeprefix('AssertEquals_') if name.startswith('AssertEquals_') else name.rsplit('_', 1)[-1] if '_' in name else 'BOOL' if name in ('AssertTrue', 'AssertFalse') else 'UINT'
        x, y = values.get(typ, ('1', '2'))
        array = 'Array' in name
        dims = 3 if '3d' in name else 2 if '2d' in name else 1
        vartype = 'T_MaxString' if typ == 'STRING' else 'WSTRING(255)' if typ == 'WSTRING' else typ
        variable = f'_v{i}'
        if array:
            variables += [f'\t{variable}e : ARRAY[{", ".join(["1..2"] * dims)}] OF {vartype};', f'\t{variable}a : ARRAY[{", ".join(["1..2"] * dims)}] OF {vartype};']
            index = ', '.join(['1'] * dims)
            body = f'{variable}e[{index}] := {x};\n{variable}a[{index}] := {y};\n{name}(Expecteds := {variable}e, Actuals := {variable}a, '
            etype = f'Type_Array{str(dims) + "D" if dims > 1 else ""}_{typ}'
        elif name in ('AssertTrue', 'AssertFalse'):
            body = f'{name}(Condition := {"FALSE" if name == "AssertTrue" else "TRUE"}, '
            etype = 'Type_BOOL'
        else:
            variables += [f'\t{variable}e : {vartype} := {x};', f'\t{variable}a : {vartype} := {y};']
            body = f'{name}(Expected := {variable}e, Actual := {variable}a, '
            etype = 'Type_ANY' if name == 'AssertEquals' else f'Type_{typ}'
        if typ in ('REAL', 'LREAL'):
            body += 'Delta := 0.0, '
        testname = f'F{i:02}_{name}'
        body += f"Message := '{testname}');\nTEST_FINISHED();"
        cases.append(case(testname, body, state='FAILED', failure_type=etype, exact_message=not array and typ not in ('STRING', 'WSTRING', 'REAL', 'LREAL')))
    return [suite('FB_QualificationFamilies', cases, '\n'.join(variables))], [[expected for _, expected in cases]]


def multiscan():
    cases = [
        case('BranchPassThenFail', "_branch := _branch + 1;\nIF _branch = 1 THEN\n\tAssertTrue(Condition := TRUE, Message := 'A');\nELSE\n\tAssertFalse(Condition := TRUE, Message := 'B');\n\tTEST_FINISHED();\nEND_IF", state='FAILED', failure_type='Type_BOOL', message='B'),
        case('FirstFailureCoherent', "_first := _first + 1;\nIF _first = 1 THEN\n\tAssertTrue(Condition := FALSE, Message := 'first-A');\nELSE\n\tAssertFalse(Condition := TRUE, Message := 'later-B');\n\tTEST_FINISHED();\nEND_IF", state='FAILED', failure_type='Type_BOOL', message='first-A'),
        case('TenThousandInvocations', "_long := _long + 1;\n_good := _long < 10000;\nAssertTrue(Condition := _good, Message := 'last-invocation');\nIF _long >= 10000 THEN TEST_FINISHED(); END_IF", state='FAILED', failure_type='Type_BOOL', message='last-invocation'),
        case('ZeroAssertions', 'TEST_FINISHED();', count=0),
        case('ThreeAssertions', "AssertTrue(Condition := TRUE, Message := 'one');\nAssertTrue(Condition := TRUE, Message := 'two');\nAssertTrue(Condition := TRUE, Message := 'three');\nTEST_FINISHED();", count=3),
    ]
    result = suite('FB_QualificationMultiscan', cases, '\t_branch : UDINT;\n\t_first : UDINT;\n\t_long : UDINT;\n\t_good : BOOL;')
    result.declaration = result.declaration.replace('\nVAR\n', '\nVAR_OUTPUT\n\tLaterFailureExecuted : BOOL;\nEND_VAR\nVAR\n', 1)
    result.implementation += '\nLaterFailureExecuted := _first >= 2;'
    return [result], [[e for _, e in cases]]


def ordered():
    members, expected = [], []
    for i, name in enumerate(('DISABLED_First', 'EnabledA', 'DISABLED_Middle', 'EnabledB', 'DISABLED_Last')):
        disabled = name.startswith('DISABLED_')
        supplied = name
        body = f"IF TEST_ORDERED('{supplied}') THEN\n\t_bodyVisits := _bodyVisits + 1;\n\tTEST_FINISHED();\nEND_IF"
        members.append(method(f'T{i}', f'METHOD T{i}', body))
        expected.append({'name': supplied.removeprefix('DISABLED_'), 'state': 'SKIPPED' if disabled else 'PASSED', 'assertions': 0})
    s = obj('POU', 'FB_QualificationOrdered', 'FUNCTION_BLOCK FB_QualificationOrdered EXTENDS FB_TestSuite\nVAR\n\t_bodyVisits : UINT;\nEND_VAR', '\n'.join(f'{m.name}();' for m in members), members)
    return [s], [expected]


def names_and_finish():
    cases = [case('NamedB', '// Remain open until NamedA finishes this known target.', count=0),
             case('NamedA', "AssertTrue(Condition := TRUE, Message := 'before-B');\nTEST_FINISHED_NAMED('NamedB');\nAssertTrue(Condition := TRUE, Message := 'after-B');\nTEST_FINISHED();", count=2)]
    cases.append((method('Whitespace', 'METHOD Whitespace', "TEST('  Trimmed  ');\nIF NOT IS_TEST_FINISHED('Trimmed') THEN\n\tTEST_FINISHED();\nEND_IF"), {'name': 'Trimmed', 'state': 'PASSED', 'assertions': 0}))
    cases.append((method('DisabledCase', 'METHOD DisabledCase', "TEST('  dIsAbLeD_  Hidden  ');"), {'name': 'Hidden', 'state': 'SKIPPED', 'assertions': 0}))
    cases.append((method('Duplicate', 'METHOD Duplicate', "TEST('Duplicate');\nAssertTrue(Condition := TRUE, Message := 'first-definition');\nTEST_FINISHED();\nTEST('Duplicate');\nAssertTrue(Condition := FALSE, Message := 'must-be-suppressed');\nTEST_FINISHED();"), {'name': 'Duplicate', 'state': 'PASSED', 'assertions': 1}))
    cases.append((method('ConflictingShape', 'METHOD ConflictingShape', "TEST('Shape');\nAssertTrue(Condition := TRUE, Message := 'original-shape');\nTEST_FINISHED();\nTEST_ORDERED('Shape');\nAssertTrue(Condition := FALSE, Message := 'conflicting-shape-must-be-suppressed');\nTEST_FINISHED();"), {'name': 'Shape', 'state': 'PASSED', 'assertions': 1}))
    result = suite('FB_QualificationNames', cases, '\t_shape : ST_CoUnitTestRecord;\n\t_found : BOOL;')
    result.declaration = result.declaration.replace('\nVAR\n', '\nVAR_OUTPUT\n\tShapePreserved : BOOL;\nEND_VAR\nVAR\n', 1)
    result.implementation += "\n_found := GetCanonicalRecord(Index := 6, Record => _shape);\nShapePreserved := _found AND NOT _shape.IsOrdered AND (_shape.OrderNumber = 0) AND (_shape.CanonicalName = 'Shape') AND (_shape.State = E_CoUnitTestState.PASSED);"
    return [result], [[e for _, e in cases]]


def integrated():
    first = [case('DelayedPass', "_passScan := _passScan + 1;\nAssertTrue(Condition := TRUE, Message := 'delayed-pass');\nIF _passScan = 3 THEN TEST_FINISHED(); END_IF"),
             case('ChangingFailure', "_failScan := _failScan + 1;\n_good := _failScan < 3;\nAssertTrue(Condition := _good, Message := 'third-scan-failure');\nIF _failScan = 3 THEN TEST_FINISHED(); END_IF", state='FAILED', failure_type='Type_BOOL', message='third-scan-failure')]
    second = [(method('Disabled', 'METHOD Disabled', "TEST('DISABLED_NotExecuted');"), {'name': 'NotExecuted', 'state': 'SKIPPED', 'assertions': 0}),
              case('OtherSuitePass', 'TEST_FINISHED();', count=0)]
    return [suite('FB_QualificationIntegratedA', first, '\t_passScan : UINT;\n\t_failScan : UINT;\n\t_good : BOOL;'), suite('FB_QualificationIntegratedB', second)], [[e for _, e in first], [e for _, e in second]]


def floating_and_any():
    cases = []
    variables = []
    # Values are constructed through integer storage; no FP calculation creates NaNs.
    matrices = [('EqualFinite', '3F800000', '3F800000', '00000000', True),
                ('UnequalFinite', '3F800000', '40000000', '00000000', False),
                ('QuietNaN', '7FC00001', '3F800000', '00000000', False),
                ('SignalNaN', '7F800001', '3F800000', '00000000', False),
                ('PositiveInfinityEqual', '7F800000', '7F800000', '00000000', True),
                ('OppositeInfinity', '7F800000', 'FF800000', '00000000', False),
                ('InfinityFinite', '7F800000', '3F800000', '00000000', False),
                ('NaNDelta', '3F800000', '3F800000', '7FC00001', False),
                ('NegativeDelta', '3F800000', '3F800000', 'BF800000', False)]
    wide = {'3F800000': '3FF0000000000000', '40000000': '4000000000000000', '00000000': '0000000000000000', '7FC00001': '7FF8000000000001', '7F800001': '7FF0000000000001', '7F800000': '7FF0000000000000', 'FF800000': 'FFF0000000000000', 'BF800000': 'BFF0000000000000'}
    for typ in ('REAL', 'LREAL'):
        for index, (label, a, b, d, passed) in enumerate(matrices):
            prefix = f'_f{typ}{index}'
            inttype = 'DWORD' if typ == 'REAL' else 'LWORD'
            bits = [a, b, d] if typ == 'REAL' else [wide[a], wide[b], wide[d]]
            for suffix, value in zip(('a', 'b', 'd'), bits):
                variables.append(f'\t{prefix}{suffix} : {inttype} := {inttype}#16#{value};')
            declaration = '\n'.join(f'\t_p{s} : POINTER TO {typ};' for s in ('a', 'b', 'd'))
            name = typ + label
            body = '\n'.join(f'_p{s} := ADR({prefix}{s});' for s in ('a', 'b', 'd'))
            body += f"\nAssertEquals_{typ}(Expected := _pa^, Actual := _pb^, Delta := _pd^, Message := '{name}');\nTEST_FINISHED();"
            cases.append(case(name, body, declaration, 'PASSED' if passed else 'FAILED', failure_type=None if passed else f'Type_{typ}', exact_message=False))
    variables += ['\t_longE : STRING(300);', '\t_longA : STRING(300);', '\t_wideE : WSTRING(300);', '\t_wideA : WSTRING(300);', '\t_uint : UINT := 1;', '\t_udint : UDINT := 1;', '\t_userE : ST_QualificationRepresentation;', '\t_userA : ST_QualificationRepresentation;', '\t_regressionScan : UINT;', '\t_arrayE : ARRAY[1..2] OF UINT;', '\t_arrayA : ARRAY[4..5] OF UINT;', '\t_arrayLong : ARRAY[4..6] OF UINT;']
    long_value = 'x' * 280
    cases += [case('AnyLongString', f"_longE := '{long_value}';\n_longA := '{long_value}';\nAssertEquals(Expected := _longE, Actual := _longA, Message := 'long-string');\nTEST_FINISHED();"),
              case('AnyLongWString', f'_wideE := "{long_value}";\n_wideA := "{long_value}";\nAssertEquals(Expected := _wideE, Actual := _wideA, Message := \'long-wstring\');\nTEST_FINISHED();'),
              case('AnyTypeMismatch', "AssertEquals(Expected := _uint, Actual := _udint, Message := 'AnyTypeMismatch');\nTEST_FINISHED();", state='FAILED', failure_type='Type_ANY'),
              case('AnyRepresentationEqual', "_userE.A := 1;\n_userE.B := 2;\n_userA := _userE;\nAssertEquals(Expected := _userE, Actual := _userA, Message := 'same-representation');\nTEST_FINISHED();"),
              case('AnyRepresentationDifferent', "_userE.A := 1;\n_userE.B := 2;\n_userA := _userE;\n_userA.B := 3;\nAssertEquals(Expected := _userE, Actual := _userA, Message := 'AnyRepresentationDifferent');\nTEST_FINISHED();", state='FAILED', failure_type='Type_ANY', exact_message=False),
              case('StringThenReal', "_regressionScan := _regressionScan + 1;\nIF _regressionScan = 1 THEN\n\tAssertEquals_STRING(Expected := 'text-first', Actual := 'different', Message := 'first-string');\nELSE\n\tAssertEquals_REAL(Expected := 1.0, Actual := 2.0, Delta := 0.0, Message := 'later-real');\n\tTEST_FINISHED();\nEND_IF", state='FAILED', failure_type='Type_STRING', message='first-string'),
              case('ArrayDifferentLowerBounds', "AssertArrayEquals_UINT(Expecteds := _arrayE, Actuals := _arrayA, Message := 'lower-bounds');\nTEST_FINISHED();"),
              case('ArrayDifferentLengths', "AssertArrayEquals_UINT(Expecteds := _arrayE, Actuals := _arrayLong, Message := 'ArrayDifferentLengths');\nTEST_FINISHED();", state='FAILED', failure_type='Type_Array_UINT', exact_message=False)]
    dut = obj('DUT', 'ST_QualificationRepresentation', 'TYPE ST_QualificationRepresentation :\nSTRUCT\n\tA : UDINT;\n\tB : UDINT;\nEND_STRUCT\nEND_TYPE')
    return [suite('FB_QualificationValues', cases, '\n'.join(variables))], [[e for _, e in cases]], [dut]


def capacity(kind, overflow):
    if kind == 'assertions':
        n = 2048 + int(overflow)
        cases = [case('AssertionLimit', f"FOR _index := 1 TO {n} DO\n\tAssertTrue(Condition := TRUE, Message := 'bounded-call');\nEND_FOR\nTEST_FINISHED();", state='ERROR' if overflow else 'PASSED', count=2048)]
        result = suite('FB_QualificationAssertionLimit', cases, '\t_index : UINT;')
        if overflow:
            capacity_guard(result, result.members[0], "AssertTrue(Condition := TRUE, Message := 'bounded-call');", 1)
        return [result], [[e for _, e in cases]]
    if kind == 'tests':
        n = 2048 + int(overflow)
        body = f"FOR _index := 1 TO {n} DO\n\t_name := CONCAT('Test', UINT_TO_STRING(_index));\n\tTEST(_name);\n\tTEST_FINISHED();\nEND_FOR"
        s = obj('POU', 'FB_QualificationTestLimit', 'FUNCTION_BLOCK FB_QualificationTestLimit EXTENDS FB_TestSuite\nVAR\n\t_index : UINT;\n\t_name : T_MaxString;\nEND_VAR', body)
        if overflow:
            capacity_guard(s, s, 'TEST(_name);', 2048)
        return [s], [[{'name': f'Test{i}', 'state': 'PASSED', 'assertions': 0} for i in range(1, 2049)]]
    suites, expectations = [], []
    for i in range(32):
        cases = [case(f'Suite{i}', 'TEST_FINISHED();', count=0)]
        suites.append(suite(f'FB_QualificationSuite{i}', cases))
        expectations.append([e for _, e in cases])
    return suites, expectations


def capacity_guard(s, target, stimulus, expected_count):
    fields = '\tGuardPass : BOOL;\n'
    for suffix in ('Before', 'After'):
        fields += f'\tCount{suffix} : UINT;\n\tOrdered{suffix} : UINT;\n\tCursor{suffix} : UDINT;\n\tBudget{suffix} : UDINT;\n\tLast{suffix} : ST_CoUnitTestRecord;\n'
    s.declaration = s.declaration.replace('\nVAR\n', '\nVAR_OUTPUT\n' + fields + 'END_VAR\nVAR\n', 1)
    def capture(suffix):
        return f'ReadQualificationGuard(Count => Count{suffix}, OrderedCount => Ordered{suffix}, Cursor => Cursor{suffix}, LastRecord => Last{suffix});\nBudget{suffix} := GVL_coUnit.coUnitRunner.ReadQualificationBudget();'
    invariant = [f'CountBefore = {expected_count}', 'CountAfter = CountBefore', 'OrderedAfter = OrderedBefore', 'CursorAfter = CursorBefore', f'BudgetBefore = {2048 if expected_count == 1 else 0}', 'BudgetAfter = BudgetBefore', 'LastAfter.FirstFailure.IsSet = LastBefore.FirstFailure.IsSet']
    invariant += [f'LastAfter.{field} = LastBefore.{field}' for field in ('CanonicalName', 'InUse', 'IsOrdered', 'OrderNumber', 'DefinedDisabled', 'InvocationOrdinal', 'MaxAssertionsPerInvocation', 'HasFailure')]
    # ERROR terminalization is permitted; declaration identity and assertion bookkeeping are not.
    replacement = 'IF _index = 2049 THEN\n' + capture('Before') + '\nEND_IF\n' + stimulus + '\nIF _index = 2049 THEN\n' + capture('After') + '\nGuardPass := ' + ' AND '.join(invariant) + ';\nEND_IF'
    pattern = r'(?m)^(\t*)' + re.escape(stimulus) + '$'
    target.implementation = re.sub(pattern, lambda match: '\n'.join(match[1] + line for line in replacement.splitlines()), target.implementation, count=1)


def emit(name, suites, expectations, sequence=False, extras=None, disposition='NORMAL', runner_mode=None):
    root = HERE / 'generated' / name
    root.mkdir(parents=True, exist_ok=True)
    prg, checks = runner(suites, expectations, sequence, disposition=disposition)
    if runner_mode == 'suites_overflow':
        prg.declaration = prg.declaration.replace('\nVAR\n', '\nVAR\n\t_overflowSuite : FB_QualificationEmpty;\n', 1)
    if runner_mode == 'cross_task':
        prg.implementation = prg.implementation.replace('RUN();', 'RUN();\nGVL_Qualification.OwnerReady := TRUE;', 1)
    if runner_mode == 'task_lookup':
        prg.declaration = prg.declaration.replace('\nVAR\n', '\nVAR\n\t_injected : BOOL;\n', 1)
        prg.implementation = prg.implementation.replace('RUN();', "RUN();\nIF NOT _injected THEN\n\tGVL_coUnit.InjectTaskLookupFailure := TRUE;\n\tTEST('LookupMustNotRegister');\n\tGVL_coUnit.InjectTaskLookupFailure := FALSE;\n\t_injected := TRUE;\nEND_IF", 1)
    if runner_mode == 'seal_violation':
        prg.declaration = prg.declaration.replace('\tSnapshotBytes : UDINT;', '\tSnapshotBytes : UDINT;\n\tRunDisposition : E_CoUnitRunDisposition;\n\tSnapshotDisposition : E_CoUnitRunDisposition;\n\tSealInjectionConsumed : BOOL;')
        prg.declaration = prg.declaration.replace('\nVAR\n', '\nVAR\n\t_sealInjected : BOOL;\n', 1)
        prg.implementation = prg.implementation.replace('RUN();', 'IF NOT _sealInjected THEN\n\tGVL_CoUnitReporting.InjectSnapshotSealViolation := TRUE;\n\t_sealInjected := TRUE;\nEND_IF\nRUN();', 1)
        prg.implementation += '\nRunDisposition := GVL_coUnit.coUnitRunner.GetDisposition();\nSnapshotDisposition := _snapshot.Disposition;\nSealInjectionConsumed := NOT GVL_CoUnitReporting.InjectSnapshotSealViolation;\nIF Done THEN OraclePass := OraclePass AND SealInjectionConsumed AND (RunDisposition = SnapshotDisposition); END_IF'
    if runner_mode in ('mode_switch', 'abort'):
        prg.declaration = prg.declaration.replace('\nVAR\n', '\nVAR\n\t_epoch : UDINT;\n', 1)
        service = 'IF _epoch = 0 THEN\n\tRUN();\nELSE\n'
        service += '\tRUN_IN_SEQUENCE();\n' if runner_mode == 'mode_switch' else '\tGVL_coUnit.coUnitRunner.AbortRunningTestSuiteTests();\n\tRUN();\n'
        service += 'END_IF\n_epoch := _epoch + 1;'
        prg.implementation = prg.implementation.replace('RUN();', service, 1)
    objects = (extras or []) + suites + [prg]
    for item in objects:
        folder = root / item.name
        folder.mkdir(exist_ok=True)
        (folder / f'{item.prefix}.{item.name}.DEC.exp').write_text(item.declaration + '\n', encoding='utf-8')
        if item.implementation is not None:
            (folder / f'{item.prefix}.{item.name}.IMP.exp').write_text(item.implementation + '\n', encoding='utf-8')
        for member in item.members:
            (folder / f'M.{member.name}.DEC.exp').write_text(member.declaration + '\n', encoding='utf-8')
            (folder / f'M.{member.name}.IMP.exp').write_text(member.implementation + '\n', encoding='utf-8')
    plc.build_xml(objects, f'CoUnit qualification {name}').write(str(root / 'qualification.xml'), encoding='utf-8', xml_declaration=True)
    expected_record = {'shard': name, 'native_status': 'NOT_RUN', 'run_disposition': disposition, 'suites': expectations, 'checks': checks}
    if name == 'names':
        expected_record['required_log_occurrences'] = {'Conflicting test declaration shape': 1, 'Duplicate test declaration in runner epoch': 1}
    if runner_mode == 'timeout':
        expected_record = {'shard': name, 'native_status': 'NOT_RUN', 'Done': False, 'expected_host_outcome': 'EXECUTION_TIMEOUT', 'report': 'No fresh completed report', 'recovery': 'Stop/reinitialize disposable application; preserve timeout evidence'}
    (root / 'expected.json').write_text(json.dumps(expected_record, indent=2) + '\n', encoding='utf-8')
    print(f'{name}: {len(objects)} native objects, {len(checks)} independent checks')


def reporting():
    declaration = '''PROGRAM PRG_Qualification
VAR_INPUT
	Path : T_MaxString := 'counit_qualification/report.xml';
	JsonPath : T_MaxString := 'counit_qualification/report.json';
	TextMode : E_CoUnitTextMode := E_CoUnitTextMode.UNKNOWN;
	ChunkLimit : UDINT := 64;
	FaultOperation : E_CoUnitFileOperation := E_CoUnitFileOperation.NONE;
	FaultOccurrence : UDINT := 0;
	FaultOccurrence2 : UDINT := 0;
	FaultError : UDINT := 16#FFFF0001;
	ShortWrite : BOOL;
	PauseAfterPhase : UINT;
	ExpectedState : E_CoUnitReportState := E_CoUnitReportState.WRITTEN;
	JsonEnabled : BOOL := FALSE;
	JsonExpectedState : E_CoUnitReportState := E_CoUnitReportState.DISABLED;
	JsonFaultOperation : E_CoUnitFileOperation := E_CoUnitFileOperation.NONE;
	JsonFaultOccurrence : UDINT := 0;
	JsonFaultOccurrence2 : UDINT := 0;
	JsonFaultError : UDINT := 16#FFFF0001;
	JsonShortWrite : BOOL;
	JsonPauseAfterPhase : UINT;
	ReleasePause : BOOL;
	SuiteName : T_MaxString := 'Suite & <A>';
	FailureMessage : T_MaxString := 'expected <3 & 4> but got "5"';
END_VAR
VAR_OUTPUT
	Done : BOOL;
	OraclePass : BOOL;
	Configured : BOOL;
	Phase : UINT;
	FileEffects : UDINT;
	LastFileError : UDINT;
	ReportState : E_CoUnitReportState;
	JsonConfigured : BOOL;
	JsonPhase : UINT;
	JsonFileEffects : UDINT;
	JsonLastFileError : UDINT;
	JsonReportState : E_CoUnitReportState;
	JsonCleanupWarning : BOOL;
	JsonFlushUnsupported : BOOL;
	SnapshotBytes : UDINT;
	JsonPublisherBytes : UDINT;
END_VAR
VAR
	_snapshot : ST_CoUnitRunSnapshot;
	_backing : ARRAY[1..6] OF ST_CoUnitTestRecord;
	_fixtureIndex : UINT;
	_results : FB_TestResults;
	_publisher : FB_xUnitXmlPublisher(_results);
	_jsonPublisher : FB_JsonDiagnosticPublisher;
	_result : BOOL;
	_jsonResult : BOOL;
	Init : BOOL;
END_VAR'''
    body = '''SnapshotBytes := SIZEOF(ST_CoUnitRunSnapshot);
JsonPublisherBytes := SIZEOF(_jsonPublisher);
IF NOT Init THEN
	FOR _fixtureIndex := 1 TO 6 DO
		_snapshot.Suites[1].Tests[_fixtureIndex].Name REF= _backing[_fixtureIndex].CanonicalName;
		_snapshot.Suites[1].Tests[_fixtureIndex].ClassName REF= _snapshot.Suites[1].Name;
		_snapshot.Suites[1].Tests[_fixtureIndex].LaterDetail REF= _backing[_fixtureIndex].LaterDetail;
		_snapshot.Suites[1].Tests[_fixtureIndex].FirstFailure REF= _backing[_fixtureIndex].FirstFailure;
	END_FOR
	_snapshot.Disposition := E_CoUnitRunDisposition.NORMAL;
	_snapshot.SuiteCount := 1;
	_snapshot.Total := 6;
	_snapshot.Passed := 1;
	_snapshot.Failed := 3;
	_snapshot.Skipped := 1;
	_snapshot.Errors := 1;
	_snapshot.Suites[1].Name := SuiteName;
	_snapshot.Suites[1].Identity := 0;
	_snapshot.Suites[1].Total := 6;
	_snapshot.Suites[1].Passed := 1;
	_snapshot.Suites[1].Failed := 3;
	_snapshot.Suites[1].Skipped := 1;
	_snapshot.Suites[1].Errors := 1;
	_snapshot.Suites[1].Tests[1].Name := 'Pass "quoted"';
	_snapshot.Suites[1].Tests[1].ClassName := SuiteName;
	_snapshot.Suites[1].Tests[1].State := E_CoUnitTestState.PASSED;
	_snapshot.Suites[1].Tests[1].NumberOfAsserts := 2;
	_snapshot.Suites[1].Tests[2].Name := 'Fail & compare';
	_snapshot.Suites[1].Tests[2].ClassName := SuiteName;
	_snapshot.Suites[1].Tests[2].State := E_CoUnitTestState.FAILED;
	_snapshot.Suites[1].Tests[2].NumberOfAsserts := 3;
	_snapshot.Suites[1].Tests[2].FirstFailure.IsSet := TRUE;
	_snapshot.Suites[1].Tests[2].FirstFailure.AssertionType := E_AssertionType.Type_DINT;
	_snapshot.Suites[1].Tests[2].FirstFailure.Message := FailureMessage;
	_snapshot.Suites[1].Tests[2].FirstFailure.ExpectedText := '3';
	_snapshot.Suites[1].Tests[2].FirstFailure.ActualText := '5';
	_snapshot.Suites[1].Tests[3].Name := 'String scalar mismatch';
	_snapshot.Suites[1].Tests[3].ClassName := SuiteName;
	_snapshot.Suites[1].Tests[3].State := E_CoUnitTestState.FAILED;
	_snapshot.Suites[1].Tests[3].NumberOfAsserts := 1;
	_snapshot.Suites[1].Tests[3].FirstFailure.IsSet := TRUE;
	_snapshot.Suites[1].Tests[3].FirstFailure.AssertionType := E_AssertionType.Type_STRING;
	_snapshot.Suites[1].Tests[3].FirstFailure.Message := 'string mismatch';
	_snapshot.Suites[1].Tests[3].FirstFailure.ExpectedText := 'left <& "quoted"';
	_snapshot.Suites[1].Tests[3].FirstFailure.ActualText := 'right &> "quoted"';
	_snapshot.Suites[1].Tests[4].Name := 'Array mismatch';
	_snapshot.Suites[1].Tests[4].ClassName := SuiteName;
	_snapshot.Suites[1].Tests[4].State := E_CoUnitTestState.FAILED;
	_snapshot.Suites[1].Tests[4].NumberOfAsserts := 2;
	_snapshot.Suites[1].Tests[4].FirstFailure.IsSet := TRUE;
	_snapshot.Suites[1].Tests[4].FirstFailure.AssertionType := E_AssertionType.Type_Array_UINT;
	_snapshot.Suites[1].Tests[4].FirstFailure.Message := 'array mismatch';
	_snapshot.Suites[1].Tests[4].FirstFailure.ExpectedText := '4';
	_snapshot.Suites[1].Tests[4].FirstFailure.ActualText := '5';
	_snapshot.Suites[1].Tests[5].Name := 'Disabled';
	_snapshot.Suites[1].Tests[5].ClassName := SuiteName;
	_snapshot.Suites[1].Tests[5].State := E_CoUnitTestState.SKIPPED;
	_snapshot.Suites[1].Tests[5].NumberOfAsserts := 0;
	_snapshot.Suites[1].Tests[6].Name := 'Framework error';
	_snapshot.Suites[1].Tests[6].ClassName := SuiteName;
	_snapshot.Suites[1].Tests[6].State := E_CoUnitTestState.ERROR;
	_snapshot.IsValid := TRUE;
	GVL_coUnit.xUnitFilePath := Path;
	Configured := _publisher.ConfigureTest(Path := Path, Enabled := TRUE, ChunkLimit := ChunkLimit, TextMode := TextMode, FaultOperation := FaultOperation, FaultOccurrence := FaultOccurrence, FaultOccurrence2 := FaultOccurrence2, FaultError := FaultError, ShortWrite := ShortWrite, PauseAfterPhase := PauseAfterPhase);
	JsonConfigured := _jsonPublisher.ConfigureTest(Path := JsonPath, Enabled := JsonEnabled, TextMode := TextMode,
		FaultOperation := JsonFaultOperation, FaultOccurrence := JsonFaultOccurrence, FaultOccurrence2 := JsonFaultOccurrence2,
		FaultError := JsonFaultError, ShortWrite := JsonShortWrite, PauseAfterPhase := JsonPauseAfterPhase);
	Init := TRUE;
END_IF
IF ReleasePause THEN
	_result := _publisher.Resume();
	_jsonResult := _jsonPublisher.Resume();
END_IF
_result := _publisher.ServiceSnapshot(Snapshot := _snapshot);
_jsonResult := _jsonPublisher.ServiceSnapshot(Snapshot := _snapshot);
Phase := _publisher.GetPhase();
ReportState := _publisher.GetReportState();
FileEffects := _publisher.GetFileEffectCount();
LastFileError := _publisher.GetLastFileError();
JsonPhase := _jsonPublisher.GetPhase();
JsonReportState := _jsonPublisher.GetReportState();
JsonFileEffects := _jsonPublisher.GetFileEffectCount();
JsonLastFileError := _jsonPublisher.GetLastFileError();
JsonCleanupWarning := _jsonPublisher.GetCleanupWarning();
JsonFlushUnsupported := _jsonPublisher.GetFlushUnsupported();
Done := ((ReportState = E_CoUnitReportState.WRITTEN) OR (ReportState = E_CoUnitReportState.FAILED)) AND
	((JsonReportState = E_CoUnitReportState.WRITTEN) OR (JsonReportState = E_CoUnitReportState.FAILED) OR (JsonReportState = E_CoUnitReportState.DISABLED));
OraclePass := Done AND (ReportState = ExpectedState) AND (JsonReportState = JsonExpectedState) AND _snapshot.IsValid AND
	(_snapshot.Total = 6) AND (_snapshot.Passed = 1) AND (_snapshot.Failed = 3) AND (_snapshot.Skipped = 1) AND (_snapshot.Errors = 1) AND
	((JsonEnabled) OR (JsonFileEffects = 0));
'''
    root = HERE / 'generated/reporting'
    root.mkdir(parents=True, exist_ok=True)
    item = obj('POU', 'PRG_Qualification', declaration, body)
    for section, content in [('DEC', declaration), ('IMP', body)]:
        (root / f'POU.PRG_Qualification.{section}.exp').write_text(content, encoding='utf-8')
    plc.build_xml([item], 'CoUnit publication qualification').write(str(root / 'qualification.xml'), encoding='utf-8', xml_declaration=True)
    expected = json.loads((HERE / 'fixtures/mixed-results.expected.json').read_text(encoding='utf-8'))
    expected['run_disposition'] = 'NORMAL'
    suite = expected['suites'][0]
    suite.update(identity=0, tests=6, failures=3)
    suite['cases'][1]['failure']['body'] = 'Expected: 3\nActual: 5'
    suite['cases'].insert(2, {
        'classname': 'Suite & <A>', 'name': 'String scalar mismatch', 'status': 'failure', 'assertions': 1,
        'failure': {
            'type': 'Type_STRING', 'message': 'string mismatch',
            'body': 'Expected: left <& "quoted"\nActual: right &> "quoted"',
        },
    })
    suite['cases'].insert(3, {
        'classname': 'Suite & <A>', 'name': 'Array mismatch', 'status': 'failure', 'assertions': 2,
        'failure': {
            'type': 'Type_Array_UINT', 'message': 'array mismatch',
            'body': 'Expected: 4\nActual: 5',
        },
    })
    suite['cases'][5]['error']['message'] = 'Framework error'
    expected.update(tests=6, failures=3)
    (root / 'expected.json').write_text(json.dumps(expected, indent=2) + '\n', encoding='utf-8')
    print('reporting: independent six-case snapshot and parameterized fault/phase controls')


def platform_helpers():
    decl = '''PROGRAM PRG_Qualification
VAR_OUTPUT
	Done : BOOL;
	OraclePass : BOOL;
	ProjectBefore : BOOL;
	ProjectRejected : BOOL;
	ProjectRecovered : BOOL;
	TaskBefore : BOOL;
	TaskRejected : BOOL;
	TaskRecovered : BOOL;
END_VAR
VAR
	_project : GetCurProjInfo;
	_task : GetCurTaskInfo;
END_VAR'''
    body = '''IF NOT Done THEN
	_project();
	ProjectBefore := _project.Valid;
	_task();
	TaskBefore := _task.Valid;
	GVL_coUnit.InjectProjectLookupFailure := TRUE;
	_project();
	ProjectRejected := NOT _project.Valid;
	GVL_coUnit.InjectProjectLookupFailure := FALSE;
	_project();
	ProjectRecovered := _project.Valid;
	GVL_coUnit.InjectTaskLookupFailure := TRUE;
	_task();
	TaskRejected := NOT _task.Valid;
	GVL_coUnit.InjectTaskLookupFailure := FALSE;
	_task();
	TaskRecovered := _task.Valid;
	OraclePass := ProjectBefore AND ProjectRejected AND ProjectRecovered AND TaskBefore AND TaskRejected AND TaskRecovered;
	Done := TRUE;
END_IF'''
    root = HERE / 'generated/platform_helpers'
    root.mkdir(parents=True, exist_ok=True)
    for section, content in [('DEC', decl), ('IMP', body)]:
        (root / f'POU.PRG_Qualification.{section}.exp').write_text(content + '\n', encoding='utf-8')
    plc.build_xml([obj('POU', 'PRG_Qualification', decl, body)], 'CoUnit task project failures').write(str(root / 'qualification.xml'), encoding='utf-8', xml_declaration=True)
    (root / 'expected.json').write_text(json.dumps({'native_status': 'NOT_RUN', 'Done': True, 'OraclePass': True, 'ProjectBefore': True, 'ProjectRejected': True, 'ProjectRecovered': True, 'TaskBefore': True, 'TaskRejected': True, 'TaskRecovered': True}, indent=2) + '\n', encoding='utf-8')


def aggregate_boundary(fail_all=False):
    name = 'aggregate_65536_failed' if fail_all else 'aggregate_65536'
    root = HERE / 'generated' / name
    root.mkdir(parents=True, exist_ok=True)
    suites, _ = capacity('tests', False)
    if fail_all:
        suites[0].implementation = suites[0].implementation.replace('\tTEST_FINISHED();', "\tAssertTrue(Condition := FALSE, Message := 'aggregate-failure');\n\tTEST_FINISHED();")
    declaration = '''PROGRAM PRG_Qualification
VAR_OUTPUT
	Done : BOOL;
	OraclePass : BOOL;
	ObservedTotal : UDINT;
	SnapshotBytes : UDINT;
	FirstBadSuite : UINT;
	FirstBadTest : UINT;
END_VAR
VAR
'''
    declaration += '\n'.join(f'\t_suite{i} : FB_QualificationTestLimit;' for i in range(1, 33))
    declaration += '''
	_snapshot : REFERENCE TO ST_CoUnitRunSnapshot;
	_suiteIndex : UINT;
	_testIndex : UINT;
	_expectedName : T_MaxString;
END_VAR'''
    body = '''SnapshotBytes := SIZEOF(ST_CoUnitRunSnapshot);
RUN_IN_SEQUENCE();
_snapshot REF= GVL_coUnit.coUnitRunner.GetSnapshot();
IF (GVL_coUnit.coUnitRunner.GetRunState() = E_CoUnitRunState.COMPLETE) AND NOT Done THEN
	ObservedTotal := _snapshot.Total;
	OraclePass := _snapshot.IsValid AND (_snapshot.Disposition = E_CoUnitRunDisposition.NORMAL) AND (_snapshot.SuiteCount = 32) AND (_snapshot.Total = UDINT#65536) AND (_snapshot.Passed = UDINT#65536) AND (_snapshot.Failed = 0) AND (_snapshot.Errors = 0) AND (_snapshot.Skipped = 0);
	FOR _suiteIndex := 1 TO 32 DO
		IF _snapshot.Suites[_suiteIndex].Total <> 2048 THEN OraclePass := FALSE; END_IF
		FOR _testIndex := 1 TO 2048 DO
			_expectedName := CONCAT('Test', UINT_TO_STRING(_testIndex));
			IF (_snapshot.Suites[_suiteIndex].Tests[_testIndex].Name <> _expectedName) OR (_snapshot.Suites[_suiteIndex].Tests[_testIndex].State <> E_CoUnitTestState.PASSED) OR (_snapshot.Suites[_suiteIndex].Tests[_testIndex].NumberOfAsserts <> 0) THEN
				OraclePass := FALSE;
				IF FirstBadSuite = 0 THEN FirstBadSuite := _suiteIndex; FirstBadTest := _testIndex; END_IF
			END_IF
		END_FOR
	END_FOR
	Done := TRUE;
END_IF'''
    if fail_all:
        body = body.replace('_snapshot.Passed = UDINT#65536', '_snapshot.Passed = 0').replace('_snapshot.Failed = 0', '_snapshot.Failed = UDINT#65536').replace('.State <> E_CoUnitTestState.PASSED', '.State <> E_CoUnitTestState.FAILED').replace('.NumberOfAsserts <> 0', '.NumberOfAsserts <> 1')
    objects = suites + [obj('POU', 'PRG_Qualification', declaration, body)]
    for item in objects:
        folder = root / item.name
        folder.mkdir(exist_ok=True)
        (folder / f'POU.{item.name}.DEC.exp').write_text(item.declaration + '\n', encoding='utf-8')
        (folder / f'POU.{item.name}.IMP.exp').write_text(item.implementation + '\n', encoding='utf-8')
    plc.build_xml(objects, 'CoUnit 65536 aggregate boundary').write(str(root / 'qualification.xml'), encoding='utf-8', xml_declaration=True)
    (root / 'expected.json').write_text(json.dumps({'native_status': 'NOT_RUN', 'run_disposition': 'NORMAL', 'suite_count': 32, 'tests_per_suite': 2048, 'total': 65536, 'passed': 0 if fail_all else 65536, 'failed': 65536 if fail_all else 0, 'errors': 0, 'skipped': 0, 'test_name_prefix': 'Test', 'first_test_index': 1, 'last_test_index': 2048, 'assertions_per_test': int(fail_all)}, indent=2) + '\n', encoding='utf-8')
    print(f'{name}: exact 32 x 2048 sequence, all test records checked')


def snapshot_failure():
    root = HERE / 'generated/snapshot_failure'
    root.mkdir(parents=True, exist_ok=True)
    decl = '''PROGRAM PRG_Qualification
VAR_OUTPUT
	Done : BOOL;
	OraclePass : BOOL;
	SnapshotValid : BOOL;
	Disposition : E_CoUnitRunDisposition;
	SettledCalls : UDINT;
END_VAR
VAR
	_snapshot : REFERENCE TO ST_CoUnitRunSnapshot;
	Init : BOOL;
END_VAR'''
    body = '''IF NOT Init THEN
	GVL_CoUnitReporting.InjectSnapshotBuildFailure := TRUE;
	Init := TRUE;
END_IF
RUN();
_snapshot REF= GVL_coUnit.coUnitRunner.GetSnapshot();
SnapshotValid := _snapshot.IsValid;
Disposition := GVL_coUnit.coUnitRunner.GetDisposition();
IF GVL_coUnit.coUnitRunner.GetRunState() = E_CoUnitRunState.COMPLETE THEN
	SettledCalls := SettledCalls + 1;
	Done := SettledCalls >= 3;
	OraclePass := Done AND NOT SnapshotValid AND (Disposition = E_CoUnitRunDisposition.FRAMEWORK_ERROR) AND NOT GVL_CoUnitReporting.InjectSnapshotBuildFailure;
END_IF'''
    for section, content in [('DEC', decl), ('IMP', body)]:
        (root / f'POU.PRG_Qualification.{section}.exp').write_text(content + '\n', encoding='utf-8')
    plc.build_xml([obj('POU', 'PRG_Qualification', decl, body)], 'CoUnit final snapshot failure').write(str(root / 'qualification.xml'), encoding='utf-8', xml_declaration=True)
    (root / 'expected.json').write_text(json.dumps({'native_status': 'NOT_RUN', 'Done': True, 'OraclePass': True, 'SnapshotValid': False, 'Disposition': 'FRAMEWORK_ERROR', 'report': 'No new current report; preserve prior sentinel or absence', 'log': 'No successful publication banner'}, indent=2) + '\n', encoding='utf-8')


def device_log():
    root = HERE / 'generated/device_log'
    root.mkdir(parents=True, exist_ok=True)
    declaration = '''PROGRAM PRG_Qualification
VAR_OUTPUT
	Done : BOOL;
	OraclePass : BOOL;
	PlainResult : DINT;
	SubstitutionResult : DINT;
	LongResult : DINT;
	FirstOnlyResult : DINT;
	Utf8Result : DINT;
END_VAR
VAR
	_longFormat : T_MaxString;
	_longArgument : T_MaxString;
	_utf8Format : T_MaxString;
	_bytes : POINTER TO BYTE;
END_VAR'''
    prefix = 'QLONG-BEGIN|' + 'p' * 108
    suffix = 's' * (250 - len(prefix) - 2 - len('|QLONG-TAIL')) + '|QLONG-TAIL'
    long_format = prefix + '%s' + suffix
    long_argument = 'QARG-BEGIN|' + 'a' * (250 - len('QARG-BEGIN|') - len('|QARG-END')) + '|QARG-END'
    utf8_prefix = 'QUTF8-BEGIN|' + 'u' * (126 - len('QUTF8-BEGIN|'))
    utf8_text = utf8_prefix + '\u00e9|QUTF8-TAIL'
    body = '''IF NOT Done THEN
	PlainResult := WRITE_DEVICE_LOG(UDINT_TO_DWORD(CmpLog.LogClass.LOG_INFO), 'CoUnit qualification plain message', 'unused');
	SubstitutionResult := WRITE_DEVICE_LOG(UDINT_TO_DWORD(CmpLog.LogClass.LOG_INFO), 'CoUnit qualification value=%s', 'sentinel-42');
	FirstOnlyResult := WRITE_DEVICE_LOG(UDINT_TO_DWORD(CmpLog.LogClass.LOG_INFO), 'QFIRST-BEGIN|%s|SECOND=%s|QFIRST-TAIL', 'ARG-ONLY');
	OraclePass := (PlainResult = 0) AND (SubstitutionResult = 0) AND (FirstOnlyResult = 0);
	Done := TRUE;
END_IF'''
    extra = f"\t_longFormat := '{long_format}';\n\t_longArgument := '{long_argument}';\n\tLongResult := WRITE_DEVICE_LOG(UDINT_TO_DWORD(CmpLog.LogClass.LOG_INFO), _longFormat, _longArgument);\n\t_bytes := ADR(_utf8Format);\n"
    extra += '\n'.join(f'\t_bytes[{index}] := {byte};' for index, byte in enumerate(utf8_text.encode('utf-8') + b'\0'))
    extra += "\n\tUtf8Result := WRITE_DEVICE_LOG(UDINT_TO_DWORD(CmpLog.LogClass.LOG_INFO), _utf8Format, 'unused');\n\tOraclePass := OraclePass AND (LongResult = 0) AND (Utf8Result = 0);\n"
    body = body.replace('\tDone := TRUE;', extra + '\tDone := TRUE;')
    for section, content in [('DEC', declaration), ('IMP', body)]:
        (root / f'POU.PRG_Qualification.{section}.exp').write_text(content + '\n', encoding='utf-8')
    plc.build_xml([obj('POU', 'PRG_Qualification', declaration, body)], 'CoUnit log text qualification').write(str(root / 'qualification.xml'), encoding='utf-8', xml_declaration=True)
    messages = {'plain': 'CoUnit qualification plain message', 'substitution': 'CoUnit qualification value=sentinel-42', 'first_only': 'QFIRST-BEGIN|ARG-ONLY|SECOND=%s|QFIRST-TAIL', 'long': prefix + long_argument + suffix, 'utf8_boundary': utf8_text}
    (root / 'expected.json').write_text(json.dumps({'native_status': 'NOT_RUN', 'max_chunk_bytes': 127, 'format_bytes': len(long_format), 'argument_bytes': len(long_argument), 'long_result_bytes': len(messages['long']), 'messages': {name: {'text': text, 'hex': text.encode('utf-8').hex()} for name, text in messages.items()}, 'OraclePass_is_supplemental': 'API success does not prove log content; capture all exact messages/chunks independently'}, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def descriptors():
    root = HERE / 'generated/descriptors'
    root.mkdir(parents=True, exist_ok=True)
    declaration = '''PROGRAM PRG_Qualification
VAR_OUTPUT
	Done : BOOL;
	OraclePass : BOOL;
	GuardIntact : BOOL;
	CasePassed : ARRAY[1..10] OF BOOL;
	ObservedPassed : ARRAY[1..10] OF BOOL;
	ObservedArgumentError : ARRAY[1..10] OF BOOL;
END_VAR
VAR
	_underTest : FB_TestSuite;
	_bytes : ARRAY[0..6] OF BYTE := [16#AA, 65, 66, 67, 68, 0, 16#BB];
	_comparison : ST_CoUnitComparisonResult;
	_i : UINT;
END_VAR'''
    cases = [('valid_byte', 'ADR(_bytes[1])', 1, 1, 'BYTE', 'BYTE', True, False),
             ('null_pointer', '0', 1, 1, 'BYTE', 'BYTE', False, True),
             ('negative_size', 'ADR(_bytes[1])', -1, 1, 'BYTE', 'BYTE', False, True),
             ('wrong_primitive_size', 'ADR(_bytes[1])', 1, 1, 'DINT', 'DINT', False, True),
             ('odd_wstring_size', 'ADR(_bytes[1])', 3, 3, 'WSTRING', 'WSTRING', False, True),
             ('unterminated_string', 'ADR(_bytes[1])', 4, 4, 'STRING', 'STRING', False, True),
             ('empty_user_representation', 'ADR(_bytes[1])', 0, 0, 'USERDEF', 'USERDEF', True, False),
             ('bounded_terminated_string', 'ADR(_bytes[1])', 5, 5, 'STRING', 'STRING', True, False),
             ('type_mismatch', 'ADR(_bytes[1])', 1, 1, 'BYTE', 'WORD', False, False),
             ('unterminated_wstring', 'ADR(_bytes[1])', 4, 4, 'WSTRING', 'WSTRING', False, True)]
    body = 'IF NOT Done THEN\n'
    expected = []
    for index, (name, pointer, esize, asize, eclass, aclass, passed, error) in enumerate(cases, 1):
        body += f'\t_comparison := _underTest.CompareAnyForQualification(ExpectedData := {pointer}, ActualData := ADR(_bytes[1]), ExpectedSize := {esize}, ActualSize := {asize}, ExpectedClass := TO_DINT(IBaseLibrary.TypeClass.TYPE_{eclass}), ActualClass := TO_DINT(IBaseLibrary.TypeClass.TYPE_{aclass}));\n'
        body += f'\tObservedPassed[{index}] := _comparison.Passed;\n\tObservedArgumentError[{index}] := _comparison.ArgumentError;\n'
        body += f'\tCasePassed[{index}] := (_comparison.Passed = {str(passed).upper()}) AND (_comparison.ArgumentError = {str(error).upper()});\n'
        if error:
            body += f'\tCasePassed[{index}] := CasePassed[{index}] AND (LEN(_comparison.DiagnosticSuffix) > 0);\n'
        expected.append({'name': name, 'Passed': passed, 'ArgumentError': error})
    body += '''	GuardIntact := (_bytes[0] = 16#AA) AND (_bytes[1] = 65) AND (_bytes[2] = 66) AND (_bytes[3] = 67) AND (_bytes[4] = 68) AND (_bytes[5] = 0) AND (_bytes[6] = 16#BB);
	OraclePass := GuardIntact;
	FOR _i := 1 TO 10 DO OraclePass := OraclePass AND CasePassed[_i]; END_FOR
	Done := TRUE;
END_IF'''
    for section, content in [('DEC', declaration), ('IMP', body)]:
        (root / f'POU.PRG_Qualification.{section}.exp').write_text(content + '\n', encoding='utf-8')
    plc.build_xml([obj('POU', 'PRG_Qualification', declaration, body)], 'CoUnit descriptor negative matrix').write(str(root / 'qualification.xml'), encoding='utf-8', xml_declaration=True)
    (root / 'expected.json').write_text(json.dumps({'native_status': 'NOT_RUN', 'required_hook': 'Inject test_hooks/CompareAnyForQualification into FB_TestSuite in disposable project only', 'cases': expected, 'GuardIntact': True, 'Done': True, 'OraclePass': True}, indent=2) + '\n', encoding='utf-8')
    print('descriptors: 10 direct native descriptor cases with valid backing storage and guard checks')


def utf8_diagnostic():
    # Independent Unicode encoder is the oracle for the raw-byte implementation.
    message = 'A' + '\u00e9' * 124
    diagnostic = 'Invalid assertion argument: ' + message
    marker = '...<truncated>'
    limit = 255 - len(marker.encode('ascii'))
    expected_message = diagnostic.encode('utf-8')[:limit].decode('utf-8', errors='ignore') + marker
    case_body = '''_scans := _scans + 1;
IF _scans = 1 THEN RETURN; END_IF
_bytes := ADR(_message);
_bytes[0] := 65;
FOR _i := 0 TO 123 DO
	_bytes[1 + 2 * _i] := 16#C3;
	_bytes[2 + 2 * _i] := 16#A9;
END_FOR
_bytes[249] := 0;
AssertEquals_REAL(Expected := 1.0, Actual := 1.0, Delta := -1.0, Message := _message);
TEST_FINISHED();'''
    cases = [case('Utf8Diagnostic', case_body, state='FAILED', failure_type='Type_REAL', message='A', exact_message=False)]
    s = suite('FB_QualificationUtf8', cases, '\t_message : T_MaxString;\n\t_bytes : POINTER TO BYTE;\n\t_i : UINT;\n\t_scans : UINT;')
    prg, checks = runner([s], [[e for _, e in cases]])
    expected_bytes = expected_message.encode('utf-8') + b'\0'
    prg.declaration = prg.declaration.replace('\tSnapshotBytes : UDINT;', '\tSnapshotBytes : UDINT;\n\tDecoderBranchForced : BOOL;\n\tDiagnosticByteCount : UINT;\n\tDiagnosticBytes : ARRAY[0..255] OF BYTE;\n\tDiagnosticHex : ARRAY[1..4] OF STRING(128);')
    prg.declaration = prg.declaration.replace('\t_snapshot : REFERENCE', '\t_byteIndex : UINT;\n\t_bytes : POINTER TO BYTE;\n\t_snapshot : REFERENCE')
    prg.declaration = prg.declaration.replace('\t_byteIndex : UINT;', f'\t_expectedBytes : ARRAY[0..{len(expected_bytes)-1}] OF BYTE := [{", ".join(map(str, expected_bytes))}];\n\t_byteIndex : UINT;')
    prg.declaration = prg.declaration.replace('\t_byteIndex : UINT;', "\t_hexDigits : STRING(16) := '0123456789abcdef';\n\t_hexDigitsPointer : POINTER TO BYTE;\n\t_hexOutput : POINTER TO BYTE;\n\t_hexBlock : UINT;\n\t_hexIndex : UINT;\n\t_hexValue : UINT;\n\t_byteIndex : UINT;")
    prg.implementation = prg.implementation.replace('RUN();', 'RUN();\n// Force only after RUN has completed its native encoding bind.\nGVL_coUnit.StringIsUtf8 := TRUE;\nDecoderBranchForced := TRUE;', 1)
    prg.implementation += '''
IF Done THEN
	_bytes := ADR(_snapshot.Suites[1].Tests[1].FirstFailure.Message);
	DiagnosticByteCount := 0;
	FOR _byteIndex := 0 TO 255 DO
		DiagnosticBytes[_byteIndex] := _bytes[_byteIndex];
		IF (_bytes[_byteIndex] <> 0) AND (DiagnosticByteCount = _byteIndex) THEN DiagnosticByteCount := DiagnosticByteCount + 1; END_IF
	END_FOR
END_IF'''
    prg.implementation += f'\nIF Done THEN\n\tFOR _byteIndex := 0 TO {len(expected_bytes)-1} DO\n\t\tIF DiagnosticBytes[_byteIndex] <> _expectedBytes[_byteIndex] THEN OraclePass := FALSE; END_IF\n\tEND_FOR\nEND_IF'
    prg.implementation += '''
IF Done THEN
	_hexDigitsPointer := ADR(_hexDigits);
	FOR _hexBlock := 1 TO 4 DO
		_hexOutput := ADR(DiagnosticHex[_hexBlock]);
		FOR _hexIndex := 0 TO 63 DO
			_hexValue := BYTE_TO_UINT(DiagnosticBytes[(_hexBlock - 1) * 64 + _hexIndex]);
			_hexOutput[2 * _hexIndex] := _hexDigitsPointer[_hexValue / 16];
			_hexOutput[2 * _hexIndex + 1] := _hexDigitsPointer[_hexValue MOD 16];
		END_FOR
		_hexOutput[128] := 0;
	END_FOR
END_IF'''
    root = HERE / 'generated/utf8_diagnostic'
    root.mkdir(parents=True, exist_ok=True)
    for item in [s, prg]:
        folder = root / item.name
        folder.mkdir(exist_ok=True)
        (folder / f'POU.{item.name}.DEC.exp').write_text(item.declaration + '\n', encoding='utf-8')
        (folder / f'POU.{item.name}.IMP.exp').write_text(item.implementation + '\n', encoding='utf-8')
        for member in item.members:
            (folder / f'M.{member.name}.DEC.exp').write_text(member.declaration + '\n', encoding='utf-8')
            (folder / f'M.{member.name}.IMP.exp').write_text(member.implementation + '\n', encoding='utf-8')
    plc.build_xml([s, prg], 'CoUnit UTF8 byte truncation').write(str(root / 'qualification.xml'), encoding='utf-8', xml_declaration=True)
    (root / 'expected.json').write_text(json.dumps({'native_status': 'NOT_RUN', 'run_disposition': 'NORMAL', 'scope': 'Forced UTF8 decoder branch after native RUN bind; does not qualify a native UTF8 compiler/runtime row', 'suites': [[e for _, e in cases]], 'checks': checks, 'diagnostic_byte_count': len(expected_message.encode('utf-8')), 'diagnostic_hex': expected_message.encode('utf-8').hex(), 'diagnostic_text': expected_message}, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print('utf8_diagnostic: raw multi-byte boundary input and independent strict UTF8 output bytes')


def initial_lookup():
    root = HERE / 'generated/initial_lookup'
    root.mkdir(parents=True, exist_ok=True)
    cases = [case('LookupRecovered', 'TEST_FINISHED();', count=0)]
    s = suite('FB_QualificationInitialLookup', cases)
    declaration = '''PROGRAM PRG_Qualification
VAR_OUTPUT
	Done : BOOL;
	OraclePass : BOOL;
	FailedCalls : UINT;
	DiagnosticClaim : DWORD;
	IdlePreserved : BOOL := TRUE;
	EpochPreserved : BOOL := TRUE;
	SuiteAndTestsPreserved : BOOL := TRUE;
	RecoveryComplete : BOOL;
	SnapshotDisposition : E_CoUnitRunDisposition;
END_VAR
VAR
	_suite : FB_QualificationInitialLookup;
	_snapshot : REFERENCE TO ST_CoUnitRunSnapshot;
END_VAR'''
    body = '''IF FailedCalls < 3 THEN
	GVL_coUnit.InjectTaskLookupFailure := TRUE;
	RUN();
	GVL_coUnit.InjectTaskLookupFailure := FALSE;
	FailedCalls := FailedCalls + 1;
	DiagnosticClaim := GVL_coUnit.coUnitRunner.GetInitialLookupDiagnosticClaim();
	IdlePreserved := IdlePreserved AND (GVL_coUnit.coUnitRunner.GetRunState() = E_CoUnitRunState.IDLE);
	EpochPreserved := EpochPreserved AND (GVL_coUnit.coUnitRunner.GetEpoch() = 0);
	SuiteAndTestsPreserved := SuiteAndTestsPreserved AND (GVL_coUnit.coUnitRunner.GetSuiteCount() = 1) AND (_suite.GetNumberOfTests() = 0);
ELSE
	RUN();
	_snapshot REF= GVL_coUnit.coUnitRunner.GetSnapshot();
	SnapshotDisposition := _snapshot.Disposition;
	Done := GVL_coUnit.coUnitRunner.GetRunState() = E_CoUnitRunState.COMPLETE;
	RecoveryComplete := Done AND _snapshot.IsValid AND (_snapshot.Disposition = E_CoUnitRunDisposition.NORMAL) AND (_snapshot.SuiteCount = 1) AND (_snapshot.Total = 1) AND (_snapshot.Passed = 1) AND (_snapshot.Failed = 0) AND (_snapshot.Errors = 0) AND (_snapshot.Skipped = 0);
	OraclePass := RecoveryComplete AND IdlePreserved AND EpochPreserved AND SuiteAndTestsPreserved AND (DiagnosticClaim = 1);
END_IF'''
    for item in [s, obj('POU', 'PRG_Qualification', declaration, body)]:
        folder = root / item.name
        folder.mkdir(exist_ok=True)
        (folder / f'POU.{item.name}.DEC.exp').write_text(item.declaration + '\n', encoding='utf-8')
        (folder / f'POU.{item.name}.IMP.exp').write_text(item.implementation + '\n', encoding='utf-8')
        for member in item.members:
            (folder / f'M.{member.name}.DEC.exp').write_text(member.declaration + '\n', encoding='utf-8')
            (folder / f'M.{member.name}.IMP.exp').write_text(member.implementation + '\n', encoding='utf-8')
    plc.build_xml([s, obj('POU', 'PRG_Qualification', declaration, body)], 'CoUnit initial task lookup failure').write(str(root / 'qualification.xml'), encoding='utf-8', xml_declaration=True)
    (root / 'expected.json').write_text(json.dumps({'native_status': 'NOT_RUN', 'run_disposition': 'NORMAL', 'suites': [[e for _, e in cases]], 'FailedCalls': 3, 'DiagnosticClaim': 1, 'IdlePreserved': True, 'EpochPreserved': True, 'SuiteAndTestsPreserved': True, 'RecoveryComplete': True, 'Done': True, 'OraclePass': True, 'SnapshotDisposition': 'NORMAL', 'diagnostic_contains': 'Current task lookup failed before run start', 'diagnostic_occurrences': 1}, indent=2) + '\n', encoding='utf-8')
    print('initial_lookup: three rejected prebind calls, one diagnostic claim, clean recovery')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    names = ['families', 'values', 'multiscan', 'integrated', 'ordered', 'names', 'sequence', 'zero', 'mode_switch', 'abort', 'cross_task', 'task_lookup', 'timeout', 'seal_violation', 'assertions_max', 'assertions_overflow', 'tests_max', 'tests_overflow', 'suites_max', 'suites_overflow']
    parser.add_argument('--shard', choices=['all', 'reporting', 'platform_helpers', 'aggregate_65536', 'aggregate_65536_failed', 'snapshot_failure', 'device_log', 'descriptors', 'utf8_diagnostic', 'initial_lookup'] + names, default='all')
    args = parser.parse_args()
    if args.shard in ('all', 'reporting'):
        reporting()
    if args.shard in ('all', 'platform_helpers'):
        platform_helpers()
    if args.shard in ('all', 'aggregate_65536'):
        aggregate_boundary()
    if args.shard in ('all', 'aggregate_65536_failed'):
        aggregate_boundary(True)
    if args.shard in ('all', 'snapshot_failure'):
        snapshot_failure()
    if args.shard in ('all', 'device_log'):
        device_log()
    if args.shard in ('all', 'descriptors'):
        descriptors()
    if args.shard in ('all', 'utf8_diagnostic'):
        utf8_diagnostic()
    if args.shard in ('all', 'initial_lookup'):
        initial_lookup()
    for name in names:
        if args.shard not in ('all', name):
            continue
        extras = []
        if name == 'suites_overflow':
            # 33 instances of one empty FB: rejected registration cannot create test records.
            suites = [obj('POU', 'FB_QualificationEmpty', 'FUNCTION_BLOCK FB_QualificationEmpty EXTENDS FB_TestSuite', '')]
            expected = [[]] * 32
            # runner() needs 32 instance declarations, but XML needs only one FB definition.
            root = HERE / 'generated' / name
            root.mkdir(parents=True, exist_ok=True)
            prg, checks = runner(suites * 32, expected, disposition='FRAMEWORK_ERROR', extra_vars='\t_guardMeasured : BOOL;\n\tGuardPass : BOOL;')
            prg.implementation = prg.implementation.replace('RUN();', 'IF NOT _guardMeasured THEN\n\tGuardPass := GVL_coUnit.coUnitRunner.RejectQualificationSuite();\n\t_guardMeasured := TRUE;\nEND_IF\nRUN();', 1)
            prg.implementation += '\nIF Done THEN OraclePass := OraclePass AND GuardPass; END_IF'
            for item in suites + [prg]:
                folder = root / item.name
                folder.mkdir(exist_ok=True)
                (folder / f'POU.{item.name}.DEC.exp').write_text(item.declaration + '\n', encoding='utf-8')
                (folder / f'POU.{item.name}.IMP.exp').write_text(item.implementation + '\n', encoding='utf-8')
            plc.build_xml(suites + [prg], 'CoUnit suite overflow').write(str(root / 'qualification.xml'), encoding='utf-8', xml_declaration=True)
            (root / 'expected.json').write_text(json.dumps({'shard': name, 'native_status': 'NOT_RUN', 'run_disposition': 'FRAMEWORK_ERROR', 'suites': expected, 'checks': checks}, indent=2) + '\n', encoding='utf-8')
            print(f'{name}: 32 suite instances, guarded 33rd registration attempt')
            continue
        elif name == 'seal_violation':
            cases = [case('TerminalPass', 'TEST_FINISHED();', count=0), case('TerminalFailure', "AssertTrue(Condition := FALSE, Message := 'sealed-first-failure');\nTEST_FINISHED();", state='FAILED', failure_type='Type_BOOL', message='sealed-first-failure'), (method('TerminalSkip', 'METHOD TerminalSkip', "TEST('DISABLED_TerminalSkip');"), {'name': 'TerminalSkip', 'state': 'SKIPPED', 'assertions': 0})]
            suites, expected = [suite('FB_QualificationSealViolation', cases)], [[e for _, e in cases]]
        elif name.endswith(('_max', '_overflow')):
            suites, expected = capacity(name.split('_')[0], name.endswith('_overflow'))
        elif name in ('mode_switch', 'abort', 'cross_task', 'task_lookup', 'timeout'):
            cases = [case('OpenTest', "AssertTrue(Condition := TRUE, Message := 'open');", state='ABORTED' if name == 'abort' else 'ERROR')]
            suites, expected = [suite('FB_QualificationOpen', cases)], [[e for _, e in cases]]
            if name == 'cross_task':
                extras = [obj('GVL', 'GVL_Qualification', "{attribute 'qualified_only'}\nVAR_GLOBAL\n\tOwnerReady : BOOL;\n\tForeignCalled : BOOL;\nEND_VAR"),
                          obj('POU', 'PRG_QualificationForeign', 'PROGRAM PRG_QualificationForeign', "IF GVL_Qualification.OwnerReady AND NOT GVL_Qualification.ForeignCalled THEN\n\tTEST('ForeignMustNotRegister');\n\tGVL_Qualification.ForeignCalled := TRUE;\nEND_IF")]
        elif name == 'families':
            suites, expected = assertions()
        elif name == 'values':
            suites, expected, extras = floating_and_any()
        elif name == 'multiscan':
            suites, expected = multiscan()
        elif name == 'integrated':
            suites, expected = integrated()
        elif name == 'ordered':
            suites, expected = ordered()
        elif name == 'names':
            suites, expected = names_and_finish()
        elif name == 'sequence':
            suites, expected = [], []
            for i in range(3):
                cases = [case(f'Sequence{i}', 'TEST_FINISHED();', count=0)]
                suites.append(suite(f'FB_QualificationSequence{i}', cases))
                expected.append([e for _, e in cases])
        else:
            suites, expected = [], []
        disposition = 'ABORTED' if name == 'abort' else 'FRAMEWORK_ERROR' if name.endswith('_overflow') or name in ('mode_switch', 'cross_task', 'task_lookup', 'seal_violation') else 'NORMAL'
        emit(name, suites, expected, sequence=name == 'sequence', extras=extras, disposition=disposition, runner_mode=name)


if __name__ == '__main__':
    main()
