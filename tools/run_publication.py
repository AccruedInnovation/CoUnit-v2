"""Serial simulator publisher faults with independently checked on-disk currentness."""
from pathlib import Path
import json
import os
import shutil
import sys

VERSION = Path(__file__).resolve().parents[1]
ROOT = VERSION if (VERSION / 'CIScripts').is_dir() else VERSION.parents[2]
ARTIFACTS = ROOT / 'LocalArtifacts/CoUnit2'
RUNTIME = Path.home() / 'AppData/Roaming/CODESYS/Simulation/PlcLogic/CoUnit2'
sys.path[:0] = [str(ROOT), str(VERSION / 'qualification')]
from CIScripts.mcp_client import Client
from verify_xunit import summarize

def run(client, script, name, inputs, prior=False, stage=False, backup=False, written=False, restored=True):
    index = 1
    while (ARTIFACTS / f'publication-{name}-{index}.json').exists(): index += 1
    stem = f'publication-{name}-{index}'
    final = RUNTIME / (stem + '.xml')
    companions = [final, Path(str(final) + '.counit.tmp'), Path(str(final) + '.counit.bak')]
    if any(p.exists() for p in companions): raise ValueError('Refusing stale publication paths')
    old = b'<?xml version="1.0"?><prior-complete sentinel="' + stem.encode() + b'"/>'
    for exists, path, content in zip([prior, stage, backup], companions, [old, b'stale-stage-never-current', old]):
        if exists: path.write_bytes(content)
    assignments = {'Path': "'CoUnit2/" + final.name + "'", 'TextMode': 'E_CoUnitTextMode.WINDOWS1252',
                   'ExpectedState': 'E_CoUnitReportState.' + ('WRITTEN' if written else 'FAILED')}
    assignments.update(inputs)
    request = {'project': str(ARTIFACTS / 'qualification.project'), 'clear': False,
        'report': str(ARTIFACTS / (stem + '.json')),
        'xmls': [str(VERSION / 'qualification' / part) for part in ['generated/reporting/qualification.xml', 'log_capture/observer.xml', 'log_capture/wrapper.xml']],
        'declaration': 'PROGRAM PRG_TEST',
        'implementation': ''.join('PRG_Qualification.' + k + ' := ' + v + ';\n' for k, v in assignments.items()) + 'PRG_QualificationObserved();',
        'run': True, 'polls': 160, 'done': 'PRG_QualificationObserved.Done', 'capture_log': True,
        'observe': ['PRG_Qualification.' + n for n in ['Done', 'OraclePass', 'Phase', 'FileEffects', 'LastFileError', 'ReportState', 'SnapshotBytes']] + ['PRG_QualificationObserved.CaptureHealthy']}
    (ARTIFACTS / (stem + '-request.json')).write_text(json.dumps(request, indent=2))
    response = client.call('run_codesys_script', {'script_path': str(script), 'arguments': [], 'trace': False,
        'input_json': json.dumps(request), 'max_output_characters': 1000})
    native = json.loads(Path(request['report']).read_text())
    last = native.get('observations', [{}])[-1]
    evidence = {'case': name, 'native': request['report'], 'observed': last, 'files': {p.name: p.stat().st_size if p.exists() else None for p in companions}}
    try:
        assert native['ok'] and native['completed'] and last['PRG_Qualification.OraclePass'] == 'TRUE', native.get('exception', last)
        assert last['PRG_QualificationObserved.CaptureHealthy'] == 'TRUE', 'Incomplete native log capture'
        log = b''.join(bytes.fromhex(chunk) for chunk in native['log_hex'])
        assert (b'xUnit results exported:' in log) == written, 'Incorrect publication success log'
        if written:
            expected = json.loads((VERSION / 'qualification/generated/reporting/expected.json').read_text())
            assert summarize(final) == expected, 'Report semantics differ'
        elif (prior or backup) and restored:
            assert final.read_bytes() == old, 'Prior complete report lost or changed'
        else:
            assert not final.exists(), 'Failed publication exposed a current file'
            if prior and not restored: assert companions[2].read_bytes() == old, 'Recovery backup lost'
        evidence['result'] = 'PASS'
    except Exception as exc:
        evidence['result'], evidence['failure'] = 'FAIL', str(exc)
    for p in companions:
        if p.exists(): shutil.copyfile(p, ARTIFACTS / 'reports' / p.name)
    (ARTIFACTS / (stem + '-check.json')).write_text(json.dumps(evidence, indent=2))
    print(json.dumps(evidence), flush=True)
    if evidence['result'] != 'PASS': raise RuntimeError(evidence['failure'])

if __name__ == '__main__':
    script = Path(os.environ['LOCALAPPDATA']) / 'AccruedInnovation/CODESYS-MCP-ScriptRunner/user_scripts/counit2_native_qualification.py'
    shutil.copyfile(VERSION / 'tools/native_qualification.py', script)
    client = Client()
    try:
        cases = [('normal', {}, False, False, False, True, True)]
        for op in ['PROBE', 'OPEN', 'WRITE', 'FLUSH', 'CLOSE']:
            cases.append((op.lower(), {'FaultOperation':'E_CoUnitFileOperation.' + op,'FaultOccurrence':'1'}, True, False, False, False, True))
        cases += [
            ('short', {'FaultOperation':'E_CoUnitFileOperation.WRITE','FaultOccurrence':'1','ShortWrite':'TRUE'}, True, False, False, False, True),
            ('backup-rename', {'FaultOperation':'E_CoUnitFileOperation.RENAME','FaultOccurrence':'1'}, True, False, False, False, True),
            ('commit-rename', {'FaultOperation':'E_CoUnitFileOperation.RENAME','FaultOccurrence':'2'}, True, False, False, False, True),
            ('restore-rename', {'FaultOperation':'E_CoUnitFileOperation.RENAME','FaultOccurrence':'2','FaultOccurrence2':'3'}, True, False, False, False, False),
            ('stale-delete', {'FaultOperation':'E_CoUnitFileOperation.DELETE','FaultOccurrence':'1'}, True, True, False, False, True),
            ('cleanup-delete', {'FaultOperation':'E_CoUnitFileOperation.DELETE','FaultOccurrence':'1'}, True, False, False, True, True),
            ('flush-not-implemented', {'FaultOperation':'E_CoUnitFileOperation.FLUSH','FaultOccurrence':'1','FaultError':'16#C'}, False, False, False, True, True),
            ('flush-not-supported', {'FaultOperation':'E_CoUnitFileOperation.FLUSH','FaultOccurrence':'1','FaultError':'16#18'}, False, False, False, True, True),
            ('recover-backup', {}, False, True, True, True, True),
            ('recover-final-backup', {}, True, True, True, True, True),
            ('recover-stage-only', {}, False, True, False, True, True),
        ]
        selected = set(sys.argv[1:])
        for case in cases:
            if not selected or case[0] in selected: run(client, script, *case)
    finally: client.close()

