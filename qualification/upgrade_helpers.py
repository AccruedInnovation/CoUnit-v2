"""Generate a standalone deterministic PLCOpenXML qualification fixture for upgrade helpers."""
from __future__ import annotations

import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / '_tools'))
import generate_plcopenxml as plc

OUT = Path(__file__).resolve().parent / 'generated' / 'upgrade_helpers'
BASE = Path('PlaintextExport/Unit Test Framework for CODESYS')


def obj(prefix, name, declaration, implementation=None, members=()):
    if prefix == 'POU' and name.startswith('FB_') and not (implementation or '').strip():
        implementation = '(* Execution through methods. *)'
    return plc.ObjectExport(prefix, name, declaration, implementation, ('UpgradeHelpers',), OUT / name, members=list(members))


def method(name, declaration, implementation):
    return plc.Member('M', name, declaration, implementation, OUT / name)


def source(relative):
    return (REPO / BASE / relative).read_text(encoding='utf-8')


def library_objects():
    objects = []
    for name in ('E_CoUnitTemporalMode', 'E_CoUnitTemporalResult', 'ST_CoUnitFixtureKey', 'E_CoUnitFixtureCallback', 'E_CoUnitFixturePhase', 'E_CoUnitFixtureCause', 'E_CoUnitFixtureOutcome'):
        path = f'DUTs/{name}/{name}.DEC.exp'
        objects.append(obj('DUT', name, source(path)))
    interface_methods = [
        method('Setup', source('ITFs/I_CoUnitFixture/Setup/Setup.DEC.exp'), 'Setup := E_CoUnitFixtureCallback.PENDING;'),
        method('Body', source('ITFs/I_CoUnitFixture/Body/Body.DEC.exp'), 'Body := E_CoUnitFixtureCallback.PENDING;'),
        method('Cleanup', source('ITFs/I_CoUnitFixture/Cleanup/Cleanup.DEC.exp'), 'Cleanup := E_CoUnitFixtureCallback.PENDING;'),
    ]
    objects.append(obj('I', 'I_CoUnitFixture', source('ITFs/I_CoUnitFixture/I_CoUnitFixture.DEC.exp'), members=interface_methods))
    for fb, methods in [('FB_CoUnitExpectation', ('Start', 'Observe')), ('FB_CoUnitFixture', ('Start', 'Execute'))]:
        members = [method(n, source(f'POUs/{fb}/{n}/{n}.DEC.exp'), source(f'POUs/{fb}/{n}/{n}.IMP.exp')) for n in methods]
        objects.append(obj('POU', fb, source(f'POUs/{fb}/{fb}.DEC.exp'), implementation='', members=members))
    return objects


def qualification_objects():
    adapter_methods = [
        method('Setup', 'METHOD Setup : E_CoUnitFixtureCallback\nVAR_INPUT\n\tKey : ST_CoUnitFixtureKey;\n\tNow : LTIME;\nEND_VAR', '''SetupCalls := SetupCalls + 1;
IF SetupCalls = SetupFailOn THEN
	Setup := E_CoUnitFixtureCallback.FAILED;
ELSIF SetupCalls < SetupPassOn THEN
	Setup := E_CoUnitFixtureCallback.PENDING;
ELSE
	Setup := E_CoUnitFixtureCallback.PASSED;
END_IF'''),
        method('Body', 'METHOD Body : E_CoUnitFixtureCallback\nVAR_INPUT\n\tKey : ST_CoUnitFixtureKey;\n\tNow : LTIME;\nEND_VAR', '''BodyCalls := BodyCalls + 1;
Body := BodyResult;'''),
        method('Cleanup', 'METHOD Cleanup : E_CoUnitFixtureCallback\nVAR_INPUT\n\tKey : ST_CoUnitFixtureKey;\n\tNow : LTIME;\nEND_VAR', '''CleanupCalls := CleanupCalls + 1;
Cleanup := CleanupResult;'''),
    ]
    adapter = obj('POU', 'FB_UpgradeCallback', '''FUNCTION_BLOCK FB_UpgradeCallback IMPLEMENTS I_CoUnitFixture
VAR_INPUT
	SetupCalls : UINT;
	BodyCalls : UINT;
	CleanupCalls : UINT;
	SetupFailOn : UINT := 0;
	SetupPassOn : UINT := 1;
	BodyResult : E_CoUnitFixtureCallback := E_CoUnitFixtureCallback.PASSED;
	CleanupResult : E_CoUnitFixtureCallback := E_CoUnitFixtureCallback.PASSED;
END_VAR''', members=adapter_methods)
    decl = '''PROGRAM PRG_Qualification
VAR_OUTPUT
	Done : BOOL;
	OraclePass : BOOL;
	FailedCheck : UINT;
END_VAR
VAR
	_stage : UINT;
	_now : LTIME;
	_key : ST_CoUnitFixtureKey;
	_staleKey : ST_CoUnitFixtureKey;
	_temporal : FB_CoUnitExpectation;
	_temporalResult : E_CoUnitTemporalResult;
	_fixture : FB_CoUnitFixture;
	_fixtureKey : ST_CoUnitFixtureKey;
	_callback : FB_UpgradeCallback;
	_temporalBoundary : BOOL;
	_staleRejected : BOOL;
	_pulseOnce : BOOL;
	_stableTerminal : BOOL;
	_holdFalseStarted : BOOL;
	_holdViolationAtDeadline : BOOL;
	_holdTrueBoundary : BOOL;
	_stepPass : BOOL;
	_lateEventuallyFails : BOOL;
	_sameKeyRestartRejected : BOOL;
	_cancelled : BOOL;
	_setupFailureSuppressedBody : BOOL;
	_partialSetupCleaned : BOOL;
	_primaryCausePreserved : BOOL;
	_cleanupTimeoutVisible : BOOL;
	_sameFixtureRestartRejected : BOOL;
	_lateSetupCallbackSkipped : BOOL;
	_lateCleanupSkipped : BOOL;
	_exactPhaseBoundary : BOOL;
	_holdTrueOvershoot : BOOL;
	_holdFalseOvershoot : BOOL;
	_binding : I_CoUnitFixture;
	_invalidBinding : REFERENCE TO I_CoUnitFixture;
	_otherCallback : FB_UpgradeCallback;
	_fixtureBindingStable : BOOL;
	_nullBindingRejected : BOOL;
	_invalidBindingRejected : BOOL;
END_VAR'''
    body = '''CASE _stage OF
0:
	_key.RunId := 'run-A'; _key.SuiteId := 'suite-A'; _key.CaseId := 'case-A'; _key.RowKey := 'row-A'; _key.AttemptId := 'attempt-A'; _key.StepId := 'eventually';
	_staleKey := _key; _staleKey.StepId := 'stale';
	_temporalBoundary := _temporal.Start(Key := _key, Mode := E_CoUnitTemporalMode.EVENTUALLY_TRUE, Now := LTIME#0ns, Duration := LTIME#10ns);
	_stage := 1;
1:
	_temporalResult := _temporal.Observe(Key := _key, Now := LTIME#5ns, Condition := FALSE, Cancel := FALSE);
	_stage := 2;
2:
	_temporalResult := _temporal.Observe(Key := _key, Now := LTIME#10ns, Condition := TRUE, Cancel := FALSE);
	_temporalBoundary := _temporalBoundary AND (_temporalResult = E_CoUnitTemporalResult.PASSED) AND _temporal.Resolved;
	_pulseOnce := _temporal.Resolved;
	_stage := 3;
3:
	_sameKeyRestartRejected := NOT _temporal.Start(Key := _key, Mode := E_CoUnitTemporalMode.EVENTUALLY_TRUE, Now := LTIME#11ns, Duration := LTIME#1ns);
	_temporalResult := _temporal.Observe(Key := _staleKey, Now := LTIME#11ns, Condition := FALSE, Cancel := FALSE);
	_staleRejected := (_temporalResult = E_CoUnitTemporalResult.REJECTED) AND (_temporal.State = E_CoUnitTemporalResult.PASSED) AND _temporal.Resolved;
	_temporalResult := _temporal.Observe(Key := _key, Now := LTIME#11ns, Condition := FALSE, Cancel := FALSE);
	_stableTerminal := (_temporalResult = E_CoUnitTemporalResult.PASSED) AND NOT _temporal.Resolved;
	_stage := 4;
4:
	_key.StepId := 'hold-false';
	_holdFalseStarted := _temporal.Start(Key := _key, Mode := E_CoUnitTemporalMode.REMAINS_FALSE, Now := LTIME#20ns, Duration := LTIME#5ns);
	_stage := 5;
5:
	_temporalResult := _temporal.Observe(Key := _key, Now := LTIME#25ns, Condition := TRUE, Cancel := FALSE);
	_holdViolationAtDeadline := _holdFalseStarted AND (_temporalResult = E_CoUnitTemporalResult.FAILED) AND _temporal.Resolved;
	_key.StepId := 'hold-true';
	_holdTrueBoundary := _temporal.Start(Key := _key, Mode := E_CoUnitTemporalMode.REMAINS_TRUE, Now := LTIME#30ns, Duration := LTIME#3ns);
	_temporalResult := _temporal.Observe(Key := _key, Now := LTIME#33ns, Condition := TRUE, Cancel := FALSE);
	_holdTrueBoundary := _holdTrueBoundary AND (_temporalResult = E_CoUnitTemporalResult.PASSED) AND _temporal.Resolved;
	_key.StepId := 'named-step';
	_stepPass := _temporal.Start(Key := _key, Mode := E_CoUnitTemporalMode.STEP, Now := LTIME#34ns, Duration := LTIME#5ns);
	_temporalResult := _temporal.Observe(Key := _key, Now := LTIME#35ns, Condition := TRUE, Cancel := FALSE);
	_stepPass := _stepPass AND (_temporalResult = E_CoUnitTemporalResult.PASSED);
	_key.StepId := 'late-eventually';
	_lateEventuallyFails := _temporal.Start(Key := _key, Mode := E_CoUnitTemporalMode.EVENTUALLY_TRUE, Now := LTIME#36ns, Duration := LTIME#5ns);
	_temporalResult := _temporal.Observe(Key := _key, Now := LTIME#42ns, Condition := TRUE, Cancel := FALSE);
	_lateEventuallyFails := _lateEventuallyFails AND (_temporalResult = E_CoUnitTemporalResult.FAILED);
	_stage := 6;
6:
	_key.StepId := 'cancel';
	_cancelled := _temporal.Start(Key := _key, Mode := E_CoUnitTemporalMode.STEP, Now := LTIME#43ns, Duration := LTIME#50ns);
	_temporalResult := _temporal.Observe(Key := _key, Now := LTIME#44ns, Condition := FALSE, Cancel := TRUE);
	_cancelled := _cancelled AND (_temporalResult = E_CoUnitTemporalResult.CANCELLED);
	_fixtureKey := _key; _fixtureKey.StepId := 'setup-fail-cleanup';
	_callback.SetupCalls := 0; _callback.BodyCalls := 0; _callback.CleanupCalls := 0;
	_callback.SetupFailOn := 2; _callback.SetupPassOn := 99;
	_callback.CleanupResult := E_CoUnitFixtureCallback.PASSED;
	_binding := _callback;
	_setupFailureSuppressedBody := _fixture.Start(Key := _fixtureKey, Fixture := _binding, Now := LTIME#0ns, PhaseTimeout := LTIME#10ns, CleanupBudget := LTIME#10ns);
	_stage := 7;
7:
	_fixture.Execute(Key := _fixtureKey, Now := LTIME#1ns, Cancel := FALSE);
	_stage := 8;
8:
	_fixture.Execute(Key := _fixtureKey, Now := LTIME#2ns, Cancel := FALSE);
	_stage := 9;
9:
	_fixture.Execute(Key := _fixtureKey, Now := LTIME#3ns, Cancel := FALSE);
	_setupFailureSuppressedBody := _setupFailureSuppressedBody AND (_callback.BodyCalls = 0) AND (_fixture.PrimaryCause = E_CoUnitFixtureCause.SETUP_FAILED);
	_partialSetupCleaned := _fixture.Complete AND (_fixture.CleanupOutcome = E_CoUnitFixtureOutcome.PASSED) AND (_callback.CleanupCalls = 1);
	_binding := _callback;
	_sameFixtureRestartRejected := NOT _fixture.Start(Key := _fixtureKey, Fixture := _binding, Now := LTIME#4ns, PhaseTimeout := LTIME#10ns, CleanupBudget := LTIME#10ns);
	_fixtureKey.StepId := 'body-fail';
	_callback.SetupCalls := 0; _callback.BodyCalls := 0; _callback.CleanupCalls := 0;
	_callback.SetupFailOn := 0; _callback.SetupPassOn := 1;
	_callback.BodyResult := E_CoUnitFixtureCallback.FAILED; _callback.CleanupResult := E_CoUnitFixtureCallback.FAILED;
	_binding := _callback;
	_primaryCausePreserved := _fixture.Start(Key := _fixtureKey, Fixture := _binding, Now := LTIME#10ns, PhaseTimeout := LTIME#10ns, CleanupBudget := LTIME#10ns);
	_stage := 10;
10:
	_fixture.Execute(Key := _fixtureKey, Now := LTIME#11ns, Cancel := FALSE);
	_stage := 11;
11:
	_fixture.Execute(Key := _fixtureKey, Now := LTIME#12ns, Cancel := FALSE);
	_stage := 12;
12:
	_fixture.Execute(Key := _fixtureKey, Now := LTIME#13ns, Cancel := FALSE);
	_primaryCausePreserved := _primaryCausePreserved AND _fixture.Complete AND (_fixture.PrimaryCause = E_CoUnitFixtureCause.BODY_FAILED) AND (_fixture.CleanupOutcome = E_CoUnitFixtureOutcome.FAILED);
	_fixtureKey.StepId := 'cleanup-budget';
	_callback.SetupCalls := 0; _callback.BodyCalls := 0; _callback.CleanupCalls := 0;
	_callback.SetupFailOn := 0; _callback.SetupPassOn := 1;
	_callback.BodyResult := E_CoUnitFixtureCallback.PASSED; _callback.CleanupResult := E_CoUnitFixtureCallback.PENDING;
	_binding := _callback;
	_cleanupTimeoutVisible := _fixture.Start(Key := _fixtureKey, Fixture := _binding, Now := LTIME#20ns, PhaseTimeout := LTIME#10ns, CleanupBudget := LTIME#2ns);
	_stage := 13;
13:
	_fixture.Execute(Key := _fixtureKey, Now := LTIME#21ns, Cancel := FALSE);
	_stage := 14;
14:
	_fixture.Execute(Key := _fixtureKey, Now := LTIME#22ns, Cancel := FALSE);
	_stage := 15;
15:
	_fixture.Execute(Key := _fixtureKey, Now := LTIME#23ns, Cancel := FALSE);
	_stage := 16;
16:
	_fixture.Execute(Key := _fixtureKey, Now := LTIME#25ns, Cancel := FALSE);
	_cleanupTimeoutVisible := _cleanupTimeoutVisible AND _fixture.Complete AND (_fixture.CleanupOutcome = E_CoUnitFixtureOutcome.INCOMPLETE);
	_fixtureKey.StepId := 'late-setup';
	_callback.SetupCalls := 0; _callback.BodyCalls := 0; _callback.CleanupCalls := 0;
	_callback.SetupFailOn := 0; _callback.SetupPassOn := 2; _callback.CleanupResult := E_CoUnitFixtureCallback.PASSED;
	_binding := _callback;
	_lateSetupCallbackSkipped := _fixture.Start(Key := _fixtureKey, Fixture := _binding, Now := LTIME#30ns, PhaseTimeout := LTIME#2ns, CleanupBudget := LTIME#2ns);
	_stage := 17;
17:
	_fixture.Execute(Key := _fixtureKey, Now := LTIME#31ns, Cancel := FALSE);
	_stage := 18;
18:
	_fixture.Execute(Key := _fixtureKey, Now := LTIME#33ns, Cancel := FALSE);
	_lateSetupCallbackSkipped := _lateSetupCallbackSkipped AND (_callback.SetupCalls = 1) AND (_fixture.PrimaryCause = E_CoUnitFixtureCause.PHASE_TIMEOUT) AND (_fixture.Phase = E_CoUnitFixturePhase.CLEANUP);
	_stage := 19;
19:
	_fixture.Execute(Key := _fixtureKey, Now := LTIME#34ns, Cancel := FALSE);
	_lateSetupCallbackSkipped := _lateSetupCallbackSkipped AND _fixture.Complete AND (_fixture.CleanupOutcome = E_CoUnitFixtureOutcome.PASSED);
	_fixtureKey.StepId := 'late-cleanup';
	_callback.SetupCalls := 0; _callback.BodyCalls := 0; _callback.CleanupCalls := 0;
	_callback.SetupPassOn := 1; _callback.BodyResult := E_CoUnitFixtureCallback.PASSED; _callback.CleanupResult := E_CoUnitFixtureCallback.PASSED;
	_binding := _callback;
	_lateCleanupSkipped := _fixture.Start(Key := _fixtureKey, Fixture := _binding, Now := LTIME#40ns, PhaseTimeout := LTIME#10ns, CleanupBudget := LTIME#2ns);
	_stage := 20;
20:
	_fixture.Execute(Key := _fixtureKey, Now := LTIME#41ns, Cancel := FALSE);
	_stage := 21;
21:
	_fixture.Execute(Key := _fixtureKey, Now := LTIME#42ns, Cancel := FALSE);
	_stage := 22;
22:
	_fixture.Execute(Key := _fixtureKey, Now := LTIME#45ns, Cancel := FALSE);
	_lateCleanupSkipped := _lateCleanupSkipped AND _fixture.Complete AND (_fixture.CleanupOutcome = E_CoUnitFixtureOutcome.INCOMPLETE) AND (_callback.CleanupCalls = 0);
	_fixtureKey.StepId := 'exact-phase-deadline';
	_callback.SetupCalls := 0; _callback.BodyCalls := 0; _callback.CleanupCalls := 0;
	_callback.SetupPassOn := 1; _callback.BodyResult := E_CoUnitFixtureCallback.PASSED; _callback.CleanupResult := E_CoUnitFixtureCallback.PASSED;
	_binding := _callback;
	_exactPhaseBoundary := _fixture.Start(Key := _fixtureKey, Fixture := _binding, Now := LTIME#60ns, PhaseTimeout := LTIME#1ns, CleanupBudget := LTIME#2ns);
	_stage := 23;
23:
	_fixture.Execute(Key := _fixtureKey, Now := LTIME#61ns, Cancel := FALSE);
	_exactPhaseBoundary := _exactPhaseBoundary AND (_callback.SetupCalls = 1) AND (_fixture.Phase = E_CoUnitFixturePhase.BODY);
	_stage := 24;
24:
	_fixture.Execute(Key := _fixtureKey, Now := LTIME#62ns, Cancel := FALSE);
	_stage := 25;
25:
	_fixture.Execute(Key := _fixtureKey, Now := LTIME#63ns, Cancel := FALSE);
	_exactPhaseBoundary := _exactPhaseBoundary AND _fixture.Complete AND (_fixture.CleanupOutcome = E_CoUnitFixtureOutcome.PASSED);
	_stage := 26;
26:
	_key.StepId := 'hold-true-overshoot';
	_holdTrueOvershoot := _temporal.Start(Key := _key, Mode := E_CoUnitTemporalMode.REMAINS_TRUE, Now := LTIME#0ms, Duration := LTIME#15ms);
	_temporalResult := _temporal.Observe(Key := _key, Now := LTIME#0ms, Condition := TRUE, Cancel := FALSE);
	_stage := 27;
27:
	_temporalResult := _temporal.Observe(Key := _key, Now := LTIME#10ms, Condition := TRUE, Cancel := FALSE);
	_stage := 28;
28:
	_temporalResult := _temporal.Observe(Key := _key, Now := LTIME#20ms, Condition := TRUE, Cancel := FALSE);
	_holdTrueOvershoot := _holdTrueOvershoot AND (_temporalResult = E_CoUnitTemporalResult.PASSED);
	_key.StepId := 'hold-false-overshoot';
	_holdFalseOvershoot := _temporal.Start(Key := _key, Mode := E_CoUnitTemporalMode.REMAINS_FALSE, Now := LTIME#0ms, Duration := LTIME#15ms);
	_stage := 29;
29:
	_temporalResult := _temporal.Observe(Key := _key, Now := LTIME#0ms, Condition := FALSE, Cancel := FALSE);
	_stage := 30;
30:
	_temporalResult := _temporal.Observe(Key := _key, Now := LTIME#10ms, Condition := FALSE, Cancel := FALSE);
	_stage := 31;
31:
	_temporalResult := _temporal.Observe(Key := _key, Now := LTIME#20ms, Condition := FALSE, Cancel := FALSE);
	_holdFalseOvershoot := _holdFalseOvershoot AND (_temporalResult = E_CoUnitTemporalResult.PASSED);
	_fixtureKey.StepId := 'stable-binding';
	_callback.SetupCalls := 0; _callback.SetupPassOn := 1; _callback.SetupFailOn := 0;
	_otherCallback.SetupCalls := 0; _binding := _callback;
	_fixtureBindingStable := _fixture.Start(Key := _fixtureKey, Fixture := _binding, Now := LTIME#0ns, PhaseTimeout := LTIME#10ns, CleanupBudget := LTIME#10ns);
	_binding := _otherCallback;
	_stage := 32;
32:
	_fixture.Execute(Key := _fixtureKey, Now := LTIME#1ns, Cancel := FALSE);
	_fixtureBindingStable := _fixtureBindingStable AND (_callback.SetupCalls = 1) AND (_otherCallback.SetupCalls = 0);
	_stage := 33;
33:
	_fixture.Execute(Key := _fixtureKey, Now := LTIME#2ns, Cancel := FALSE);
	_stage := 34;
34:
	_fixture.Execute(Key := _fixtureKey, Now := LTIME#3ns, Cancel := FALSE);
	_binding := 0; _fixtureKey.StepId := 'null-binding';
	_nullBindingRejected := NOT _fixture.Start(Key := _fixtureKey, Fixture := _binding, Now := LTIME#4ns, PhaseTimeout := LTIME#10ns, CleanupBudget := LTIME#10ns);
	_invalidBindingRejected := NOT _fixture.Start(Key := _fixtureKey, Fixture := _invalidBinding, Now := LTIME#4ns, PhaseTimeout := LTIME#10ns, CleanupBudget := LTIME#10ns);
	OraclePass := _temporalBoundary AND _staleRejected AND _pulseOnce AND _stableTerminal AND _sameKeyRestartRejected AND _holdViolationAtDeadline AND _holdTrueBoundary AND _stepPass AND _lateEventuallyFails AND _cancelled AND _setupFailureSuppressedBody AND _partialSetupCleaned AND _primaryCausePreserved AND _cleanupTimeoutVisible AND _sameFixtureRestartRejected AND _lateSetupCallbackSkipped AND _lateCleanupSkipped AND _exactPhaseBoundary AND _holdTrueOvershoot AND _holdFalseOvershoot AND _fixtureBindingStable AND _nullBindingRejected AND _invalidBindingRejected;
	FailedCheck := 0;
	IF NOT _temporalBoundary THEN FailedCheck := 1; ELSIF NOT _staleRejected THEN FailedCheck := 2; ELSIF NOT _pulseOnce THEN FailedCheck := 3; ELSIF NOT _stableTerminal THEN FailedCheck := 4; ELSIF NOT _sameKeyRestartRejected THEN FailedCheck := 5; ELSIF NOT _holdViolationAtDeadline THEN FailedCheck := 6; ELSIF NOT _holdTrueBoundary THEN FailedCheck := 7; ELSIF NOT _stepPass THEN FailedCheck := 8; ELSIF NOT _lateEventuallyFails THEN FailedCheck := 9; ELSIF NOT _cancelled THEN FailedCheck := 10; ELSIF NOT _setupFailureSuppressedBody THEN FailedCheck := 11; ELSIF NOT _partialSetupCleaned THEN FailedCheck := 12; ELSIF NOT _primaryCausePreserved THEN FailedCheck := 13; ELSIF NOT _cleanupTimeoutVisible THEN FailedCheck := 14; ELSIF NOT _sameFixtureRestartRejected THEN FailedCheck := 15; ELSIF NOT _lateSetupCallbackSkipped THEN FailedCheck := 16; ELSIF NOT _lateCleanupSkipped THEN FailedCheck := 17; ELSIF NOT _exactPhaseBoundary THEN FailedCheck := 18; ELSIF NOT _holdTrueOvershoot THEN FailedCheck := 19; ELSIF NOT _holdFalseOvershoot THEN FailedCheck := 20; ELSIF NOT _fixtureBindingStable THEN FailedCheck := 21; ELSIF NOT _nullBindingRejected THEN FailedCheck := 22; ELSIF NOT _invalidBindingRejected THEN FailedCheck := 23; END_IF
	Done := TRUE;
END_CASE'''
    return [adapter, obj('POU', 'PRG_Qualification', decl, body)]


def main():
    objects = library_objects() + qualification_objects()
    OUT.mkdir(parents=True, exist_ok=True)
    for old_method in OUT.rglob('M.*.DEC.exp'):
        old_method.unlink()
    for old_method in OUT.rglob('M.*.IMP.exp'):
        old_method.unlink()
    for item in objects:
        for member in item.members:
            for extension in ('DEC', 'IMP'):
                stale_flat = OUT / item.name / f'{member.name}.{extension}.exp'
                if stale_flat.exists():
                    stale_flat.unlink()
    for item in objects:
        folder = OUT / item.name
        folder.mkdir(parents=True, exist_ok=True)
        ext = f'{item.name}.DEC.exp' if item.prefix == 'I' else f'{item.prefix}.{item.name}.DEC.exp'
        (folder / ext).write_text(item.declaration.rstrip('\r\n') + '\n', encoding='utf-8')
        if item.implementation is not None:
            (folder / f'{item.prefix}.{item.name}.IMP.exp').write_text(item.implementation.rstrip('\r\n') + '\n', encoding='utf-8')
        for member in item.members:
            member_folder = folder / member.name
            member_folder.mkdir(parents=True, exist_ok=True)
            (member_folder / f'{member.name}.DEC.exp').write_text(member.declaration.rstrip('\r\n') + '\n', encoding='utf-8')
            if member.implementation is not None:
                (member_folder / f'{member.name}.IMP.exp').write_text(member.implementation.rstrip('\r\n') + '\n', encoding='utf-8')
    plc.build_xml(objects, 'CoUnit cooperative fixture and temporal expectation helpers').write(OUT / 'qualification.xml', encoding='utf-8', xml_declaration=True)
    (OUT / 'expected.json').write_text(json.dumps({
        'native_status': 'NOT_RUN', 'done': True, 'oracle_pass': True,
        'checks': {'temporal_boundary_pass': True, 'stale_key_rejected_without_state_change': True,
                   'resolved_pulse_once': True, 'terminal_state_stable': True,
                   'completed_key_restart_rejected': True,
                   'hold_violation_at_deadline_fails': True, 'hold_true_passes_at_deadline': True,
                   'named_step_passes_on_true': True, 'late_eventual_true_fails': True, 'hold_true_overshoot_passes': True, 'hold_false_overshoot_passes': True, 'fixture_binding_stable': True, 'null_binding_rejected': True, 'invalid_binding_rejected': True,
                   'cancel_resolves_cancelled': True,
                   'setup_failure_suppresses_body': True, 'partial_setup_runs_cleanup': True,
                   'primary_body_failure_survives_cleanup_failure': True,
                   'cleanup_budget_reports_incomplete': True,
                   'completed_fixture_key_restart_rejected': True,
                   'late_setup_success_not_invoked': True,
                   'late_cleanup_success_not_invoked': True,
                   'exact_phase_deadline_success_allowed': True},
        'failed_check': 0,
    }, indent=2) + '\n', encoding='utf-8')
    print(f'Generated {len(objects)} PLCOpenXML objects at {OUT}')


if __name__ == '__main__':
    main()
