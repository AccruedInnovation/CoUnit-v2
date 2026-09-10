"""Serial simulator publisher boundaries; no log callback or native execution on import.

Raw $HH literals bind stored STRING bytes independently of compiler literal encoding.
TextMode selects the XML decoder, not the runtime's filesystem path encoding. A
R14 path capacity is checked through a disposable-project byte inspection hook:
244 bytes form distinct 255-byte companions, then an injected first probe fails;
245/246 bytes fail before any file effect. This makes no long-path OS promise.
Previous native attempts showed expanded relative Windows paths failing Open
with ERR_NO_OBJECT and absolute paths failing Probe with ERR_OPERATION_DENIED;
those historical evidence directories remain intact. Ordinary publication and
interruption cases still require actual SysFile publication. Interrupted files
are copied verbatim before each fresh import/download, including failed cases.
"""
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


def literal(raw):
    return "'" + ''.join('$%02X' % byte for byte in raw) + "'"


def native_integer(value):
    return int(str(value).split('#')[-1])


def expected(suite=None, message=None):
    result = json.loads((VERSION / 'qualification/generated/reporting/expected.json').read_text())
    if suite is not None:
        result['suites'][0]['name'] = suite
        for case in result['suites'][0]['cases']:
            case['classname'] = suite
    if message is not None:
        result['suites'][0]['cases'][1]['failure']['message'] = message
    return result


def unique(name):
    index = 1
    while True:
        stem = 'edge-%s-%d' % (name, index)
        if not (ARTIFACTS / stem).exists() and not list(RUNTIME.glob(stem + '*')):
            (ARTIFACTS / stem).mkdir(parents=True)
            return stem
        index += 1


def files(stem):
    # The ASCII prefix identifies raw UTF8 paths even when SysFile decodes them
    # using a legacy code page. Do not guess which Unicode filename Windows sees.
    return sorted(p for p in RUNTIME.glob(stem + '*') if p.is_file())


def capture(stem, folder):
    folder.mkdir(parents=True, exist_ok=False)
    result = []
    for index, path in enumerate(files(stem)):
        target = folder / ('%d.bin' % index)
        shutil.copyfile(path, target)
        result.append({'name': path.name, 'size': path.stat().st_size, 'bytes': str(target)})
    return result


def invoke(client, script, stem, label, raw_path, inputs, pause=False, capacity=False):
    folder = ARTIFACTS / stem
    assignments = {'Path': literal(raw_path), 'TextMode': 'E_CoUnitTextMode.WINDOWS1252'}
    assignments.update(inputs)
    request = {'project': str(ARTIFACTS / 'qualification.project'), 'clear': False,
               'report': str(folder / (label + '-native.json')),
               'xmls': [str(VERSION / 'qualification/generated/reporting/qualification.xml')],
               'fixture_inputs': ''.join('PRG_Qualification.%s := %s;\n' % item for item in assignments.items()),
               'run': True,
               # ReleasePause remains FALSE. Unlike Done it cannot finish phase8
               # early, so all interruption phases exercise the host timeout.
               'done': 'PRG_Qualification.ReleasePause' if pause else 'PRG_Qualification.Done',
               'runtime_timeout_seconds': 2 if pause else 10,
               'observe': ['PRG_Qualification.' + name for name in
                           ['Done', 'OraclePass', 'Phase', 'FileEffects', 'LastFileError', 'ReportState']]}
    owner = 'PRG_Qualification'
    if capacity:
        owner = 'PRG_TEST'
        request.pop('fixture_inputs')
        request['test_hooks'] = [{'owner': 'FB_xUnitXmlPublisher', 'name': 'ReadQualificationPaths',
                                 'directory': str(VERSION / 'qualification/test_hooks/ReadQualificationPaths')}]
        request['declaration'] = '''PROGRAM PRG_TEST
VAR
 _results : FB_TestResults;
 _publisher : FB_xUnitXmlPublisher(_results);
 _snapshot : ST_CoUnitRunSnapshot;
 _path : T_MaxString;
 _init : BOOL;
 _result : BOOL;
 Done : BOOL;
 OraclePass : BOOL;
 Phase : UINT;
 FileEffects : UDINT;
 LastFileError : UDINT;
 ReportState : E_CoUnitReportState;
 PathProof : BOOL;
 PathLength : UINT;
 StageLength : UINT;
 BackupLength : UINT;
 PrefixPreserved : BOOL;
 SuffixAndNul : BOOL;
 Distinct : BOOL;
END_VAR'''
        request['implementation'] = '''IF NOT _init THEN
 _path := %s;
 _snapshot.IsValid := TRUE;
 _snapshot.Disposition := E_CoUnitRunDisposition.NORMAL;
 _result := _publisher.ConfigureTest(Path := _path, Enabled := TRUE, ChunkLimit := 64,
  TextMode := E_CoUnitTextMode.UTF8, FaultOperation := E_CoUnitFileOperation.PROBE, FaultOccurrence := 1);
 _init := TRUE;
END_IF
_result := _publisher.ServiceSnapshot(Snapshot := _snapshot);
Phase := _publisher.GetPhase();
FileEffects := _publisher.GetFileEffectCount();
LastFileError := _publisher.GetLastFileError();
ReportState := _publisher.GetReportState();
PathProof := _publisher.ReadQualificationPaths(ExpectedPath := _path,
 PathLength => PathLength, StageLength => StageLength, BackupLength => BackupLength,
 PrefixPreserved => PrefixPreserved, SuffixAndNul => SuffixAndNul, Distinct => Distinct);
Done := ReportState = E_CoUnitReportState.FAILED;
OraclePass := Done;
''' % literal(raw_path)
        request['done'] = 'PRG_TEST.Done'
        request['observe'] = ['PRG_TEST.' + name for name in
                              ['Done', 'OraclePass', 'Phase', 'FileEffects', 'LastFileError', 'ReportState',
                               'PathProof', 'PathLength', 'StageLength', 'BackupLength',
                               'PrefixPreserved', 'SuffixAndNul', 'Distinct']]
    (folder / (label + '-request.json')).write_text(json.dumps(request, indent=2))
    evidence = {'label': label, 'stored_path_bytes': len(raw_path),
                'text_mode': 'E_CoUnitTextMode.UTF8' if capacity else assignments['TextMode']}
    try:
        client.call('run_codesys_script', {'script_path': str(script), 'arguments': [], 'trace': False,
                    'input_json': json.dumps(request), 'max_output_characters': 1000})
        native = json.loads(Path(request['report']).read_text())
        observation = native.get('observations', [{}])[-1]
        evidence.update(observed=observation, completed=native.get('completed'),
                        runtime_seconds=native.get('runtime_seconds'))
        assert native.get('ok') and not native.get('cleanup_exception'), native.get('exception', native.get('cleanup_exception'))
        assert native.get('completed') is (not pause), 'Unexpected completion/timeout'
        if pause:
            assert float(native['runtime_seconds']) >= 2, 'Stopped before requested interruption interval'
        evidence['admitted'] = native_integer(observation[owner + '.FileEffects']) > 0
    finally:
        evidence['files'] = capture(stem, folder / (label + '-files'))
        (folder / (label + '-evidence.json')).write_text(json.dumps(evidence, indent=2))
    return evidence


def report(stem, want):
    current = [p for p in files(stem) if not p.name.endswith(('.counit.tmp', '.counit.bak'))]
    assert len(current) == 1, 'Expected exactly one current report'
    assert summarize(current[0]) == want, 'Report semantic mismatch'
    return current[0]


def basic(client, script, name, inputs, reject=False, size=None, utf8_path=False, want=None):
    stem = unique(name)
    if not reject and size is None:
        (ARTIFACTS / stem / 'expected.json').write_text(json.dumps(want or expected(), indent=2))
    raw = ('CoUnit2/' + stem).encode('ascii')
    if size is None:
        raw += b'.xml'
    else:
        raw = (b'\xc3\xa9' * (size // 2) + b'x' * (size % 2)) if utf8_path else b'x' * size
        assert len(raw) == size
    inputs = dict(inputs, ExpectedState='E_CoUnitReportState.' + ('FAILED' if reject else 'WRITTEN'))
    evidence = invoke(client, script, stem, 'run', raw, inputs, capacity=size is not None)
    if size is not None:
        observed = evidence['observed']
        assert observed['PRG_TEST.OraclePass'] == 'TRUE', observed
        assert native_integer(observed['PRG_TEST.FileEffects']) == (1 if size == 244 else 0), observed
        assert not files(stem), 'Capacity-only fixture created files'
        if size == 244:
            for key in ['PathProof', 'PrefixPreserved', 'SuffixAndNul', 'Distinct']:
                assert observed['PRG_TEST.' + key] == 'TRUE', observed
            for key, value in [('PathLength', 244), ('StageLength', 255), ('BackupLength', 255)]:
                assert native_integer(observed['PRG_TEST.' + key]) == value, observed
        return stem
    assert evidence['observed']['PRG_Qualification.OraclePass'] == 'TRUE', evidence['observed']
    if reject:
        assert not evidence['admitted'] and not files(stem), 'Rejected input caused file effects'
    else:
        assert evidence['admitted'], 'Valid input rejected before file access'
        current = report(stem, want or expected())
        if name == 'utf8':
            data = current.read_bytes()
            for escape in (b'&#9;', b'&#10;', b'&#13;'):
                assert escape in data, 'Missing XML attribute whitespace escape: %r' % escape
    return stem


def interrupted(client, script, phase):
    stem = unique('pause%d' % phase)
    final = RUNTIME / (stem + '.xml')
    stage, backup = Path(str(final) + '.counit.tmp'), Path(str(final) + '.counit.bak')
    old = ('<prior-complete sentinel="%s"/>' % stem).encode('ascii')
    final.write_bytes(old)
    raw = ('CoUnit2/' + final.name).encode('ascii')
    marker = 'interrupted-' + stem
    (ARTIFACTS / stem / 'interrupted-expected.json').write_text(json.dumps(expected(suite=marker), indent=2))
    (ARTIFACTS / stem / 'recovered-expected.json').write_text(json.dumps(expected(suite='recovered-new'), indent=2))
    first = invoke(client, script, stem, 'interrupted', raw,
                   {'PauseAfterPhase': str(phase), 'SuiteName': literal(marker.encode())}, pause=True)
    assert native_integer(first['observed']['PRG_Qualification.Phase']) == phase, first['observed']
    if phase == 6:
        assert final.read_bytes() == old and not backup.exists()
        assert summarize(stage) == expected(suite=marker)
    elif phase == 7:
        assert not final.exists() and backup.read_bytes() == old
        assert summarize(stage) == expected(suite=marker)
    else:
        assert not stage.exists() and backup.read_bytes() == old
        report(stem, expected(suite=marker))
    retained = final.read_bytes() if phase == 8 else old
    # Fresh import/download resets the fixture. Pause immediately after recovery
    # and opening a NEW empty stage, before any new report serialization.
    recovered = invoke(client, script, stem, 'recovered-before-write', raw,
                       {'PauseAfterPhase': '1', 'SuiteName': literal(b'recovered-new')}, pause=True)
    assert native_integer(recovered['observed']['PRG_Qualification.Phase']) == 1, recovered['observed']
    assert final.read_bytes() == retained, 'Recovery promoted the interrupted staging report'
    assert not backup.exists() and stage.read_bytes() == b'', 'Recovery retained stale staging/backup bytes'
    complete = invoke(client, script, stem, 'recovered-complete', raw,
                      {'SuiteName': literal(b'recovered-new')})
    assert complete['observed']['PRG_Qualification.OraclePass'] == 'TRUE', complete['observed']
    report(stem, expected(suite='recovered-new'))
    assert not stage.exists() and not backup.exists(), 'Successful recovery left transaction files'
    return stem


def main():
    RUNTIME.mkdir(parents=True, exist_ok=True)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    script = Path(os.environ['LOCALAPPDATA']) / 'AccruedInnovation/CODESYS-MCP-ScriptRunner/user_scripts/counit2_native_qualification.py'
    shutil.copyfile(VERSION / 'tools/native_qualification.py', script)
    cases = [('chunk%d' % n, dict(inputs={'ChunkLimit': str(n)}, reject=True)) for n in range(16)]
    cases.append(('unknown', dict(inputs={'TextMode': 'E_CoUnitTextMode.UNKNOWN'}, reject=True)))
    for raw_utf8 in (False, True):
        for size in (244, 245, 246):
            cases.append(('%s%d' % ('path-utf8' if raw_utf8 else 'path-ascii', size),
                          dict(inputs={}, size=size, utf8_path=raw_utf8, reject=size > 244)))
    # Explicit expected Unicode, not Python's decoder implementation under test.
    vectors = [('cp1252', 'WINDOWS1252', b'\x80\xe9\x81\x01', '\u20ac\u00e9\ufffd\ufffd'),
               ('latin1', 'LATIN1', b'\x80\xe9', '\u0080\u00e9'),
               ('utf8', 'UTF8', b'\xc2\xa2\xe2\x82\xac\xf0\x9f\x98\x80\xff\xc0\xaf\t\n\r&<>"',
                '\u00a2\u20ac\U0001f600\ufffd\ufffd\ufffd\t\n\r&<>"')]
    for name, mode, raw, decoded in vectors:
        cases.append((name, dict(inputs={'TextMode': 'E_CoUnitTextMode.' + mode,
                                       'SuiteName': literal(raw), 'FailureMessage': literal(raw)},
                                want=expected(suite=decoded, message=decoded))))
    selected = set(sys.argv[1:])
    known = {name for name, _ in cases} | {'pause6', 'pause7', 'pause8'}
    if selected - known:
        raise ValueError('Unknown cases: ' + ', '.join(sorted(selected - known)))
    batch = ARTIFACTS / unique('batch')
    client, failed, results = Client(), False, []
    try:
        for name, options in cases + [('pause%d' % phase, phase) for phase in (6, 7, 8)]:
            if selected and name not in selected:
                continue
            result = {'case': name}
            try:
                stem = interrupted(client, script, options) if isinstance(options, int) else basic(client, script, name, **options)
                result.update(result='PASS', evidence=str(ARTIFACTS / stem))
            except Exception as exc:
                failed = True
                result.update(result='FAIL', failure=str(exc))
            results.append(result)
            (batch / 'results.json').write_text(json.dumps(results, indent=2))
            print(json.dumps(result), flush=True)
    finally:
        client.close()
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
