"""Run standard native shards serially and independently check their reports."""
from pathlib import Path
import argparse
import json
import os
import shutil
import sys
import time

VERSION = Path(__file__).resolve().parents[1]
ROOT = VERSION if (VERSION / 'CIScripts').is_dir() else VERSION.parents[2]
ARTIFACTS = ROOT / 'LocalArtifacts/CoUnit2'
RUNTIME = Path.home() / 'AppData/Roaming/CODESYS/Simulation/PlcLogic/CoUnit2'
sys.path[:0] = [str(ROOT), str(VERSION / 'qualification')]
from CIScripts.mcp_client import Client
from check_report import check

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('shards', nargs='+')
    args = parser.parse_args()
    script = Path(os.environ['LOCALAPPDATA']) / 'AccruedInnovation/CODESYS-MCP-ScriptRunner/user_scripts/counit2_native_qualification.py'
    shutil.copyfile(VERSION / 'tools/native_qualification.py', script)
    client = Client()
    try:
        for name in args.shards:
            fixture = VERSION / 'qualification/generated' / name
            expected = json.loads((fixture / 'expected.json').read_text(encoding='utf-8'))
            if 'suite_count' in expected:
                cases = [{'name': expected['test_name_prefix'] + str(i),
                          'state': 'FAILED' if expected['failed'] else 'PASSED',
                          'assertions': expected['assertions_per_test']}
                         for i in range(expected['first_test_index'], expected['last_test_index'] + 1)]
                expected['suites'] = [cases for _ in range(expected['suite_count'])]
            declaration = (fixture / 'PRG_Qualification/POU.PRG_Qualification.DEC.exp').read_text(encoding='utf-8')
            index = 1
            while (ARTIFACTS / f'{name}-run{index}.json').exists() or (RUNTIME / f'{name}-{index}.xml').exists():
                index += 1
            report = ARTIFACTS / f'{name}-run{index}.json'
            xml = RUNTIME / f'{name}-{index}.xml'
            request = {
                'project': str(ARTIFACTS / 'qualification.project'), 'clear': False,
                'report': str(report), 'xmls': [str(fixture / 'qualification.xml')],
                'run': True, 'polls': 400 if name.startswith('aggregate_') else 160, 'report_path': f'CoUnit2/{xml.name}',
                'done': 'PRG_Qualification.Done',
                'report_state': 'GVL_coUnit.coUnitRunner.xUnitXmlPublisher._state',
                'observe': ['PRG_Qualification.Done', 'PRG_Qualification.OraclePass',
                            'PRG_Qualification.FailedCheck', 'PRG_Qualification.SnapshotBytes',
                            'GVL_coUnit.coUnitRunner.xUnitXmlPublisher._state',
                            'GVL_coUnit.coUnitRunner.xUnitXmlPublisher._lastError'],
                'bind': [f'PRG_Qualification._suite{i + 1}.InstancePath' for i in range(len(expected['suites']))],
            }
            if name.startswith('aggregate_'): request['drain_completed'] = True
            if 'FailedCheck' not in declaration:
                request['observe'].remove('PRG_Qualification.FailedCheck')
                request['observe'] += ['PRG_Qualification.ObservedTotal', 'PRG_Qualification.FirstBadSuite', 'PRG_Qualification.FirstBadTest']
            request['observe'] += ['GVL_coUnit.coUnitRunner.TestResults.TestSuiteResults.' + field
                for field in ('NumberOfTestCases', 'NumberOfSuccessfulTestCases', 'NumberOfFailedTestCases')]
            hooks = []
            if name in ('assertions_overflow', 'tests_overflow'):
                hooks += [('FB_TestSuite', 'ReadQualificationGuard'), ('FB_coUnitRunner', 'ReadQualificationBudget')]
                request['observe'] += ['PRG_Qualification._suite1.' + field for field in
                    ['GuardPass', 'CountBefore', 'CountAfter', 'OrderedBefore', 'OrderedAfter', 'CursorBefore', 'CursorAfter', 'BudgetBefore', 'BudgetAfter', 'LastBefore.CanonicalName', 'LastAfter.CanonicalName']]
            if name == 'suites_overflow':
                hooks += [('FB_coUnitRunner', 'RejectQualificationSuite')]
                request['observe'].append('PRG_Qualification.GuardPass')
            if name == 'cross_task': request['foreign_task'] = True
            request['test_hooks'] = [{'owner': owner, 'name': hook, 'directory': str(VERSION / 'qualification/test_hooks' / hook)} for owner, hook in hooks]
            (ARTIFACTS / f'{name}-request{index}.json').write_text(json.dumps(request, indent=2), encoding='utf-8')
            response = client.call('run_codesys_script', {'script_path': str(script), 'arguments': [],
                'trace': False, 'input_json': json.dumps(request), 'max_output_characters': 1000})
            if not report.exists():
                deadline = time.monotonic() + 60
                while not report.exists() and time.monotonic() < deadline: time.sleep(1)
            if not report.exists():
                raise RuntimeError(f'{name}: no native result: {response}')
            native = json.loads(report.read_text(encoding='utf-8'))
            if xml.exists(): shutil.copyfile(xml, ARTIFACTS / 'reports' / xml.name)
            last = native.get('observations', [{}])[-1]
            summary = {'shard': name, 'native': str(report), 'errors': native.get('errors'),
                       'completed': native.get('completed'), 'observed': last}
            if not native.get('ok') or not native.get('completed') or last.get('PRG_Qualification.OraclePass') != 'TRUE':
                summary['exception'] = native.get('exception')
                failed = last.get('PRG_Qualification.FailedCheck', 'UDINT#0').split('#')[-1]
                if failed.isdigit() and 0 < int(failed) <= len(expected.get('checks', [])):
                    summary['failed_check'] = expected['checks'][int(failed) - 1]
                print(json.dumps(summary), flush=True)
                raise SystemExit(1)
            classes = [native['bindings'][key].strip("'") for key in request['bind']]
            check(xml, expected, classes)
            summary['xml_inventory'] = 'PASS'
            print(json.dumps(summary), flush=True)
    finally:
        client.close()
