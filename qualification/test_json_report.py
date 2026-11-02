"""Independent schema and cross-publisher checks for JSON diagnostics."""
import copy
import importlib.util
import json
import re
import sys
import tempfile
import types
import unittest
import xml.sax.saxutils as sax
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import controlled_boot
import verify_json_report as json_report
import verify_xunit as xml_report


def _payload():
    expected = 'left <& "quoted"\t\nÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬'
    actual = 'right &> "quoted"\rvalue'
    return {
        'format_version': 1,
        'run_disposition': 'NORMAL',
        'tests': 4,
        'failures': 1,
        'errors': 1,
        'skipped': 1,
        'suites': [{
            'identity': 42,
            'name': 'Suite & <A>',
            'tests': 4,
            'failures': 1,
            'errors': 1,
            'skipped': 1,
            'cases': [
                {'classname': 'Suite & <A>', 'name': 'Passed', 'status': 'passed', 'assertions': 1},
                {
                    'classname': 'Suite & <A>', 'name': 'String mismatch', 'status': 'failure', 'assertions': 3,
                    'failure': {'type': 'Type_STRING', 'message': 'failed <& "quoted"', 'expected': expected, 'actual': actual},
                },
                {'classname': 'Suite & <A>', 'name': 'Skipped', 'status': 'skipped', 'assertions': 0},
                {'classname': 'Suite & <A>', 'name': 'Framework error', 'status': 'error', 'assertions': 0,
                 'error': {'message': 'Framework error'}},
            ],
        }],
    }


def _xml_text(value):
    return sax.escape(value).replace('\t', '&#9;').replace('\n', '&#10;').replace('\r', '&#13;')


def _xml_attr(value):
    return _xml_text(value).replace('"', '&quot;')


def _write_xml(payload, path):
    suite = payload['suites'][0]
    attrs = ' '.join(f'{key}="{value}"' for key, value in payload.items() if key in xml_report.COUNT_KEYS)
    xml = f'<testsuites {attrs} counit-run-disposition="{payload["run_disposition"]}">'
    suite_attrs = ' '.join(f'{key}="{suite[key]}"' for key in xml_report.COUNT_KEYS)
    xml += f'<testsuite id="{suite["identity"]}" name="{_xml_attr(suite["name"])}" {suite_attrs}>'
    for case in suite['cases']:
        case_attrs = (
            f'classname="{_xml_attr(case["classname"])}" '
            f'name="{_xml_attr(case["name"])}" assertions="{case["assertions"]}"'
        )
        if case['status'] == 'passed':
            xml += f'<testcase {case_attrs}/>'
        elif case['status'] == 'skipped':
            xml += f'<testcase {case_attrs}><skipped/></testcase>'
        elif case['status'] == 'error':
            message = case['error']['message']
            xml += f'<testcase {case_attrs}><error message="{_xml_attr(message)}"/></testcase>'
        else:
            failure = case['failure']
            body = f'Expected: {failure["expected"]}\nActual: {failure["actual"]}'
            xml += (
                f'<testcase {case_attrs}><failure type="{_xml_attr(failure["type"])}" '
                f'message="{_xml_attr(failure["message"])}">{_xml_text(body)}</failure></testcase>'
            )
    xml += '</testsuite></testsuites>'
    path.write_text(xml, encoding='utf-8')


def _manager_v2_error_fixture(*, disposition='FRAMEWORK_ERROR', assertions=1,
                              framework_version='2.1.0.1'):
    reason = 'later framework termination'
    error_message = 'Run aborted' if disposition == 'ABORTED' else 'Framework error'
    error = {'message': error_message}
    if disposition != 'NORMAL':
        error['termination_reason'] = reason
    first_failure = {
        'type': 'Type_BOOL', 'message': 'original assertion failed',
        'expected': 'TRUE', 'actual': 'FALSE',
    }
    if assertions:
        error['first_failure'] = first_failure
    case = {
        'classname': 'Suite', 'name': 'Case', 'case_id': 'case-id', 'row_key': 'row-a',
        'status': 'error', 'assertions': assertions, 'selected': True, 'started': True,
        'error': error,
    }
    payload = {
        'format_version': 2, 'schema_version': 2, 'framework_version': framework_version,
        'run_id': 'run-current', 'build_id': 'build-current', 'target_id': 'target-current',
        'generation': 1, 'clock_mode': 'MONOTONIC', 'run_disposition': disposition,
        'tests': 1, 'failures': 0, 'errors': 1, 'skipped': 0,
        'suites': [{
            'identity': 7, 'suite_id': 'suite-id', 'name': 'Suite',
            'tests': 1, 'failures': 0, 'errors': 1, 'skipped': 0, 'cases': [case],
        }],
    }
    if disposition != 'NORMAL':
        payload['termination_reason'] = reason
    attrs = (
        f'counit-run-disposition="{disposition}" counit-schema-version="2" '
        f'counit-framework-version="{framework_version}" counit-run-id="run-current" '
        'counit-build-id="build-current" counit-target-id="target-current" '
        'counit-generation="1" counit-clock-mode="MONOTONIC"'
    )
    if disposition != 'NORMAL':
        attrs += f' counit-termination-reason="{_xml_attr(reason)}"'
    root = f'<testsuites tests="1" failures="0" errors="1" skipped="0" {attrs}>'
    root += (
        '<testsuite id="7" name="Suite" counit-suite-id="suite-id" '
        'tests="1" failures="0" errors="1" skipped="0">'
        f'<testcase classname="Suite" name="Case" counit-case-id="case-id" '
        f'counit-row-key="row-a" counit-selected="TRUE" counit-started="TRUE" assertions="{assertions}">'
        f'<error message="{_xml_attr(error_message)}"'
    )
    if disposition != 'NORMAL':
        root += f' termination-reason="{_xml_attr(reason)}"'
    if assertions:
        root += (
            f' failure-type="{_xml_attr(first_failure["type"])}"'
            f' failure-message="{_xml_attr(first_failure["message"])}">'
            f'Expected: {first_failure["expected"]}&#10;Actual: {first_failure["actual"]}</error>'
        )
    else:
        root += '/>'
    root += '</testcase></testsuite></testsuites>'
    return payload, root


def _literal_case_map(source, result_name):
    """Read only literal CASE arms from the reachable byte-map implementation."""
    pattern = rf'^\s*16#([0-9A-Fa-f]+):\s*{re.escape(result_name)}\s*:=\s*16#([0-9A-Fa-f]+);'
    return {
        int(source_byte, 16): int(code_point, 16)
        for source_byte, code_point in re.findall(pattern, source, flags=re.MULTILINE)
    }


def _python_cp1252_reference(value):
    try:
        return ord(bytes([value]).decode('cp1252'))
    except UnicodeDecodeError:
        return 0xFFFD


def _assert_reachable_json_decoder_contract(test, encoder, decoder, utf8, continuation):
    """Check decoder dataflow and bounds in the actual encoder call chain."""
    for source, required in (
        (encoder, '_cp := DecodeJsonCodePoint(Bytes := _p, Index := _i, TextMode := _textMode, Taken => _taken)'),
        (encoder, 'AppendJsonEscapedCodePoint(CodePoint := _cp)'),
        (decoder, '_cp := BYTE_TO_UDINT(Bytes[Index]);'),
        (decoder, 'IF TextMode = E_CoUnitTextMode.UTF8 AND _cp >= 16#80 THEN'),
        (decoder, 'ELSIF TextMode = E_CoUnitTextMode.WINDOWS1252 AND _cp >= 16#80 AND _cp <= 16#9F THEN'),
        (decoder, '_cp := MapWindows1252CodePoint(CodePoint := _cp);'),
        (decoder, 'ELSIF TextMode = E_CoUnitTextMode.WINDOWS1252 AND _cp >= 16#80 AND _cp <= 16#9F THEN\n\t_cp := MapWindows1252CodePoint(CodePoint := _cp);\nEND_IF\nDecodeJsonCodePoint := _cp;'),
        (decoder, '_cp := DecodeUtf8CodePoint(Bytes := Bytes, Index := Index, FirstByte := _cp, Taken => Taken);'),
        (decoder, 'DecodeJsonCodePoint := _cp;'),
        (utf8, '_cp := FirstByte AND _initialMask;'),
        (utf8, 'CodePoint := _cp, Taken => Taken)'),
        (utf8, 'DecodeUtf8CodePoint := _cp;'),
        (continuation, 'CodePoint := DWORD_TO_UDINT(SHL(UDINT_TO_DWORD(CodePoint), 6) OR UDINT_TO_DWORD(BYTE_TO_UDINT(Bytes[Index + _j] AND 16#3F)));'),
    ):
        test.assertIn(required, source)
    test.assertLess(encoder.index('AppendJsonEscapedCodePoint(CodePoint := _cp)'), encoder.index('_i := _i + _taken'))
    test.assertLess(decoder.index('_cp := BYTE_TO_UDINT(Bytes[Index]);'), decoder.index('DecodeJsonCodePoint := _cp;'))
    test.assertLess(utf8.index('_cp := FirstByte AND _initialMask;'), utf8.index('DecodeUtf8CodePoint := _cp;'))


def _assert_snapshot_index_source_contract(test, suite_handler, test_handler, validate_suite):
    suite_guard = re.compile(r'IF _suiteIndex = 0 OR _suiteIndex > Snapshot\.SuiteCount OR\s+'
                             r'_suiteIndex > GVL_Param_coUnit\.MaxNumberOfTestSuites THEN')
    test_guard = re.compile(r'IF _testIndex = 0 OR _testIndex > Snapshot\.Suites\[_suiteIndex\]\.Total OR\s+'
                            r'_testIndex > GVL_Param_coUnit\.MaxNumberOfTestsForEachTestSuite THEN')
    for source in (suite_handler, test_handler):
        match = suite_guard.search(source)
        test.assertIsNotNone(match)
        test.assertLess(match.start(), source.index('Snapshot.Suites[_suiteIndex]'))
    match = test_guard.search(test_handler)
    test.assertIsNotNone(match)
    test.assertLess(match.start(), test_handler.index('Snapshot.Suites[_suiteIndex].Tests[_testIndex]'))
    suite_index_guard = re.compile(r'IF SuiteIndex = 0 OR SuiteIndex > Snapshot\.SuiteCount OR\s+'
                                   r'SuiteIndex > GVL_Param_coUnit\.MaxNumberOfTestSuites THEN')
    match = suite_index_guard.search(validate_suite)
    test.assertIsNotNone(match)
    test.assertLess(match.start(), validate_suite.index('Snapshot.Suites[SuiteIndex]'))
    test_index_guard = re.compile(r'IF _testIndex = 0 OR _testIndex > Snapshot\.Suites\[SuiteIndex\]\.Total OR\s+'
                                  r'_testIndex > GVL_Param_coUnit\.MaxNumberOfTestsForEachTestSuite THEN')
    match = test_index_guard.search(validate_suite)
    test.assertIsNotNone(match)
    test.assertLess(match.start(), validate_suite.index('Snapshot.Suites[SuiteIndex].Tests[_testIndex]'))


class JsonReportTests(unittest.TestCase):
    def _load_derived_manager(self, root):
        runner = root / 'runner'
        with mock.patch.object(controlled_boot, 'OWNED_RUNNER', runner):
            controlled_boot._prepare_owned_runner()
        manager_path = runner / 'ci_runtime.py'
        source = manager_path.read_text(encoding='utf-8')
        compile(source, str(manager_path), 'exec')
        spec = importlib.util.spec_from_file_location('derived_counit_runtime_manager', manager_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        manager = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(manager)
        return manager

    def _load_owned_fixture(self, root):
        with mock.patch.object(controlled_boot, 'OWNED_RUNNER', root / 'runner'), \
                mock.patch.object(controlled_boot, 'OWNED_FIXTURE', root / 'fixture'):
            controlled_boot._load_matched_boot()
        fixture_path = root / 'fixture' / 'prepare_control_sl.py'
        system = types.ModuleType('System')
        system.AppDomain = object()
        diagnostics = types.ModuleType('System.Diagnostics')
        diagnostics.Process = object
        scriptengine = types.ModuleType('scriptengine')

        class ImportReporter:
            pass

        for name in ('ConflictResolve', 'KindOfTask', 'librarymanager', 'online', 'projects', 'system'):
            setattr(scriptengine, name, object())
        scriptengine.ImportReporter = ImportReporter
        stubs = {'System': system, 'System.Diagnostics': diagnostics, 'scriptengine': scriptengine}
        with mock.patch.dict(sys.modules, stubs):
            spec = importlib.util.spec_from_file_location('owned_counit_fixture', fixture_path)
            self.assertIsNotNone(spec)
            self.assertIsNotNone(spec.loader)
            fixture = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(fixture)
        return fixture

    def _valid_manager_manifest(self, manager, root, version):
        bundle = root / ('bundle-' + version)
        app_dir = bundle / 'PlcLogic' / 'Application'
        app_dir.mkdir(parents=True)
        (app_dir / 'App.app').write_bytes(b'app')
        (app_dir / 'App.crc').write_bytes(b'crc')
        identity = {
            'source_identity': {'tree_sha256': 'a' * 64},
            'compiler': '3.5.22.20',
            'target_device': {'type': '4096', 'id': '00001007', 'version': '4.22.0.0'},
            'resolved_libraries': [{
                'name': f'counit - a unittest framework for codesys, {version} (www.co5e.org)',
                'version': version,
            }],
            'build_options': {},
            'runtime_compatibility': {'runtime_version': '4.22.0.0', 'runtime_sdk': '4.22.0.0'},
            'application_name': 'App',
            'expected_tests': [{'suite': 'Suite', 'name': 'Case'}],
            'ready_path_template': 'PlcLogic/ci/ready-{run_id}.json',
            'completion_path_template': 'PlcLogic/ci/report-{run_id}.complete.json',
            'report_path_template': 'PlcLogic/ci/report-{run_id}.xml',
            'diagnostic_json_path_template': 'PlcLogic/ci/report-{run_id}.json',
            'counit_library_version': version,
        }
        identity['build_id'] = manager.RuntimeManager.build_identity_id(identity)
        (bundle / 'build_identity.json').write_text(json.dumps(identity), encoding='utf-8')
        instance = manager.RuntimeManager.__new__(manager.RuntimeManager)
        instance.codesys = {
            'virtual_control_sl': '4.22.0.0', 'development_system': '3.5.22.20',
            'runtime_sdk': '4.22.0.0',
        }
        return instance.validate_manifest(bundle, 'run-current')

    def _check_manager_pair(self, manager, directory, payload, xml):
        json_path = directory / 'diagnostic.json'
        xml_path = directory / 'report.xml'
        json_path.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
        xml_path.write_text(xml, encoding='utf-8')
        summary = manager.RuntimeManager.parse_report(
            xml_path, [{'suite': 'Suite', 'name': 'Case'}], dialect='counit_v2')
        return manager.RuntimeManager.parse_diagnostic_json(json_path, summary)

    def test_helper_accepts_active_2105_and_preserves_legacy_json_version(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.object(controlled_boot, 'OWNED_RUNNER', Path(directory) / 'runner'), \
                    mock.patch.object(controlled_boot, 'OWNED_FIXTURE', Path(directory) / 'fixture'):
                helper = controlled_boot._load_matched_boot()
            self.assertEqual(helper.validate_counit_library_version('2.1.0.5', diagnostic_json=True), '2.1.0.5')
            self.assertEqual(helper.validate_counit_library_version('2.1.0.4', diagnostic_json=True), '2.1.0.4')
            self.assertEqual(helper.validate_counit_library_version('2.1.0.3', diagnostic_json=True), '2.1.0.3')
            self.assertEqual(helper.validate_counit_library_version('2.1.0.2', diagnostic_json=True), '2.1.0.2')
            self.assertEqual(helper.validate_counit_library_version('2.1.0.2', diagnostic_json=False), '2.1.0.2')
            self.assertEqual(helper.validate_counit_library_version('2.1.0.1', diagnostic_json=True), '2.1.0.1')
            self.assertEqual(helper.validate_counit_library_version('2.0.1.0', diagnostic_json=True), '2.0.1.0')
            self.assertEqual(helper.validate_counit_library_version('2.0.0.0', diagnostic_json=False), '2.0.0.0')
            with self.assertRaises(ValueError):
                helper.validate_counit_library_version('2.0.0.0', diagnostic_json=True)
            with self.assertRaises(ValueError):
                helper.validate_counit_library_version('2.1.0.2', diagnostic_json=1)
            with self.assertRaises(ValueError):
                helper.validate_counit_library_version('2.1.0.6', diagnostic_json=True)

    def test_owned_fixture_defaults_to_2105_and_preserves_2010_json_getters(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = self._load_owned_fixture(Path(directory))
            self.assertEqual(fixture._requested_counit_library_version({}), '2.1.0.5')
            for version in ('2.1.0.1', '2.1.0.2', '2.1.0.3', '2.1.0.4', '2.1.0.5'):
                with self.subTest(version=version):
                    self.assertEqual(fixture._requested_counit_library_version(
                        {'counit_library_version': version}), version)
            with self.assertRaises(RuntimeError):
                fixture._requested_counit_library_version({'counit_library_version': '2.1.0.6'})

            request = {
                'expected_pid': 1, 'expected_process_start_utc': 'start',
                'expected_bridge_module_version_id': 'bridge', 'expected_project_path': 'project',
                'expected_scripts_root': 'scripts', 'expected_script_path': 'script',
                'xml_path': 'source.xml', 'output_directory': 'output',
                'output_app_path': 'App.app', 'expected_device_guid': 'device',
                'counit_library_version': '2.1.0.2', 'diagnostic_json_requested': True,
            }
            fixture.mcp_input_json = json.dumps(request)
            self.assertEqual(fixture._read_request()['counit_library_version'], '2.1.0.2')

            for version in ('2.0.1.0', '2.1.0.2'):
                with self.subTest(json_getter_version=version):
                    fixture.EXPECTED_COUNIT_VERSION = version
                    reference = types.SimpleNamespace(parameters={'DIAGNOSTICJSONENABLEPUBLISH': 'FALSE'})
                    with mock.patch.object(fixture, '_counit_reference', return_value=reference):
                        result = fixture._apply_counit_diagnostic_json_parameter(
                            application=object(), requested=True)
                    self.assertIsNotNone(result)
                    self.assertTrue(result['after_set'])
                    self.assertEqual(reference.parameters['DIAGNOSTICJSONENABLEPUBLISH'], 'TRUE')

    def test_derived_manager_reconciles_v2_error_and_zero_assertion_abort(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = self._load_derived_manager(Path(directory))
            for framework_version, disposition, assertions in (
                    ('2.1.0.1', 'FRAMEWORK_ERROR', 1), ('2.1.0.2', 'FRAMEWORK_ERROR', 1),
                    ('2.1.0.2', 'ABORTED', 0), ('2.1.0.3', 'FRAMEWORK_ERROR', 1),
                    ('2.1.0.3', 'ABORTED', 0), ('2.1.0.4', 'FRAMEWORK_ERROR', 1),
                    ('2.1.0.4', 'ABORTED', 0), ('2.1.0.5', 'FRAMEWORK_ERROR', 1),
                    ('2.1.0.5', 'ABORTED', 0)):
                with self.subTest(framework_version=framework_version, disposition=disposition, assertions=assertions):
                    payload, xml = _manager_v2_error_fixture(
                        disposition=disposition, assertions=assertions, framework_version=framework_version)
                    summary = self._check_manager_pair(manager, Path(directory), payload, xml)
                    self.assertEqual(summary['format_version'], 2)
                    self.assertEqual(summary['errors'], 1)
                    if assertions:
                        self.assertEqual(summary['run_disposition'], 'FRAMEWORK_ERROR')

    def test_derived_manager_keeps_v1_acceptance_and_rejects_v2_mismatches(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = self._load_derived_manager(Path(directory))
            v1 = {
                'format_version': 1, 'run_disposition': 'NORMAL',
                'tests': 1, 'failures': 0, 'errors': 0, 'skipped': 0,
                'suites': [{
                    'identity': 7, 'name': 'Suite',
                    'tests': 1, 'failures': 0, 'errors': 0, 'skipped': 0,
                    'cases': [{
                        'classname': 'Suite', 'name': 'Case', 'status': 'passed', 'assertions': 1,
                    }],
                }],
            }
            legacy_xml = (
                '<testsuites tests="1" failures="0" errors="0" skipped="0" '
                'counit-run-disposition="NORMAL"><testsuite id="7" name="Suite" '
                'tests="1" failures="0" errors="0" skipped="0"><testcase '
                'classname="Suite" name="Case" assertions="1"/></testsuite></testsuites>')
            self.assertEqual(
                self._check_manager_pair(manager, Path(directory), v1, legacy_xml)['format_version'], 1)

            payload, xml = _manager_v2_error_fixture(disposition='FRAMEWORK_ERROR', assertions=1)
            bad_documents = []
            bad_schema = copy.deepcopy(payload)
            bad_schema['schema_version'] = 1
            bad_documents.append((bad_schema, xml))
            bad_framework = copy.deepcopy(payload)
            bad_framework['framework_version'] = '2.1.0.6'
            bad_documents.append((bad_framework, xml))
            bad_reason = copy.deepcopy(payload)
            bad_reason['termination_reason'] = 'different run cause'
            bad_documents.append((bad_reason, xml))
            bad_failure = copy.deepcopy(payload)
            bad_failure['suites'][0]['cases'][0]['error']['first_failure']['actual'] = 'TRUE'
            bad_documents.append((bad_failure, xml))
            bad_inventory = copy.deepcopy(payload)
            bad_inventory['suites'][0]['cases'][0]['name'] = 'Stale Case'
            bad_documents.append((bad_inventory, xml))
            bad_count = copy.deepcopy(payload)
            bad_count['tests'] = 2
            bad_documents.append((bad_count, xml))
            for index, (document, report) in enumerate(bad_documents):
                with self.subTest(mismatch=index):
                    with self.assertRaises(RuntimeError):
                        self._check_manager_pair(manager, Path(directory), document, report)

            no_first_failure = copy.deepcopy(payload)
            del no_first_failure['suites'][0]['cases'][0]['error']['first_failure']
            with self.assertRaises(RuntimeError):
                self._check_manager_pair(manager, Path(directory), no_first_failure, xml)

            noncanonical_zero = copy.deepcopy(payload)
            noncanonical_zero['suites'][0]['cases'][0]['assertions'] = 0
            noncanonical_zero['suites'][0]['cases'][0]['failure'] = {
                'type': 'Type_BOOL', 'message': 'conflicting result',
                'expected': 'TRUE', 'actual': 'FALSE',
            }
            zero_xml = xml.replace('assertions="1"', 'assertions="0"')
            with self.assertRaises(RuntimeError):
                self._check_manager_pair(manager, Path(directory), noncanonical_zero, zero_xml)

    def test_derived_manager_admits_json_manifests_only_for_qualified_versions(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = self._load_derived_manager(Path(directory))
            for version in ('2.0.1.0', '2.1.0.1', '2.1.0.2', '2.1.0.3', '2.1.0.4', '2.1.0.5'):
                with self.subTest(version=version):
                    identity, _digest, paths = self._valid_manager_manifest(
                        manager, Path(directory), version)
                    self.assertEqual(identity['counit_library_version'], version)
                    self.assertIn('diagnostic_json_path_template', paths)
            with self.assertRaisesRegex(ValueError, 'counit_library_version'):
                self._valid_manager_manifest(manager, Path(directory), '2.1.0.6')

    def test_json_and_xml_match_one_complete_snapshot(self):
        payload = _payload()
        with tempfile.TemporaryDirectory() as directory:
            json_path = Path(directory) / 'diagnostic.json'
            xml_path = Path(directory) / 'report.xml'
            json_path.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
            _write_xml(payload, xml_path)
            json_summary = json_report.summarize(json_path)
            xml_summary = xml_report.summarize(xml_path)
            self.assertEqual(json_summary, xml_summary)
            self.assertEqual(json_summary['suites'][0]['identity'], 42)
            self.assertIn('Expected: left <& "quoted"\t\nÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬', json_summary['suites'][0]['cases'][1]['failure']['body'])

    def test_closed_keys_and_count_consistency(self):
        payload = _payload()
        mutations = []
        extra_root = copy.deepcopy(payload)
        extra_root['run_id'] = 'invented'
        mutations.append(extra_root)
        extra_failure = copy.deepcopy(payload)
        extra_failure['suites'][0]['cases'][1]['failure']['assertion_ordinal'] = 1
        mutations.append(extra_failure)
        bad_suite_count = copy.deepcopy(payload)
        bad_suite_count['suites'][0]['tests'] += 1
        mutations.append(bad_suite_count)
        bad_root_count = copy.deepcopy(payload)
        bad_root_count['failures'] = 0
        mutations.append(bad_root_count)
        for value in mutations:
            with self.subTest(value=value):
                with self.assertRaises(json_report.CheckError):
                    json_report.summarize_value(value)

    def test_terminal_shape_and_types_are_checked(self):
        payload = _payload()
        bad_status = copy.deepcopy(payload)
        bad_status['suites'][0]['cases'][0]['status'] = 'PASSED'
        with self.assertRaises(json_report.CheckError):
            json_report.summarize_value(bad_status)
        boolean_count = copy.deepcopy(payload)
        boolean_count['suites'][0]['cases'][0]['assertions'] = True
        with self.assertRaises(json_report.CheckError):
            json_report.summarize_value(boolean_count)
        extra_success_result = copy.deepcopy(payload)
        extra_success_result['suites'][0]['cases'][0]['failure'] = {
            'type': 'Type_BOOL', 'message': 'x', 'expected': 'TRUE', 'actual': 'FALSE'
        }
        with self.assertRaises(json_report.CheckError):
            json_report.summarize_value(extra_success_result)

    def test_duplicate_keys_truncation_and_invalid_utf8_are_refused(self):
        samples = (
            '{"format_version":1,"format_version":1}',
            '{"format_version":1',
        )
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / 'bad.json'
            for sample in samples:
                report.write_text(sample, encoding='utf-8')
                with self.assertRaises(json_report.CheckError):
                    json_report.summarize(report)
            report.write_bytes(b'{"bad":"\xff"}')
            with self.assertRaises(json_report.CheckError):
                json_report.summarize(report)

    def test_success_gate_requires_normal_nonempty_and_no_failures(self):
        summary = json_report.summarize_value(_payload())
        with self.assertRaises(json_report.CheckError):
            json_report.require_disposition(summary, success=True)
        empty = {
            'format_version': 1, 'run_disposition': 'NORMAL', 'tests': 0, 'failures': 0,
            'errors': 0, 'skipped': 0, 'suites': [],
        }
        empty_summary = json_report.summarize_value(empty)
        with self.assertRaises(json_report.CheckError):
            json_report.require_disposition(empty_summary, success=True)

    def test_json_encoder_uses_configured_decoder_and_fixed_chunk_source(self):
        """Source-contract checks only; IEC UTF-8/1252 execution oracles remain outstanding."""
        source_root = Path(__file__).resolve().parents[1] / 'PlaintextExport/Unit Test Framework for CODESYS/POUs/FB_JsonDiagnosticPublisher'
        encoder = (source_root / 'AppendJsonString/AppendJsonString.IMP.exp').read_text(encoding='utf-8')
        self.assertIn('DecodeJsonCodePoint(Bytes := _p, Index := _i, TextMode := _textMode, Taken => _taken)', encoder)
        self.assertIn('AppendJsonEscapedCodePoint(CodePoint := _cp)', encoder)
        self.assertLess(encoder.index('AppendJsonEscapedCodePoint(CodePoint := _cp)'), encoder.index('_i := _i + _taken'))
        self.assertIn('WHILE _i < 255 DO', encoder)
        self.assertIn('IF _p[255] <> 0 THEN', encoder)

        decoder = (source_root / 'DecodeJsonCodePoint/DecodeJsonCodePoint.IMP.exp').read_text(encoding='utf-8')
        utf8 = (source_root / 'DecodeUtf8CodePoint/DecodeUtf8CodePoint.IMP.exp').read_text(encoding='utf-8')
        continuation = (source_root / 'AccumulateUtf8Continuation/AccumulateUtf8Continuation.IMP.exp').read_text(encoding='utf-8')
        _assert_reachable_json_decoder_contract(self, encoder, decoder, utf8, continuation)

        cp1252_guard = 'ELSIF TextMode = E_CoUnitTextMode.WINDOWS1252 AND _cp >= 16#80 AND _cp <= 16#9F THEN'
        no_cp1252_range = decoder.replace(cp1252_guard, 'ELSIF TextMode = E_CoUnitTextMode.WINDOWS1252 THEN', 1)
        self.assertNotEqual(no_cp1252_range, decoder)
        with self.assertRaises(AssertionError):
            _assert_reachable_json_decoder_contract(self, encoder, no_cp1252_range, utf8, continuation)
        utf8_merge = 'CodePoint := DWORD_TO_UDINT(SHL(UDINT_TO_DWORD(CodePoint), 6) OR UDINT_TO_DWORD(BYTE_TO_UDINT(Bytes[Index + _j] AND 16#3F)));'
        no_utf8_merge = continuation.replace(utf8_merge, 'CodePoint := 0;', 1)
        self.assertNotEqual(no_utf8_merge, continuation)
        with self.assertRaises(AssertionError):
            _assert_reachable_json_decoder_contract(self, encoder, decoder, utf8, no_utf8_merge)

        for required in (
            'DecodeUtf8CodePoint := 16#FFFD;', 'Taken := 1;',
            'FirstByte >= 16#C2 AND FirstByte <= 16#DF', '_initialMask := 16#1F', '_minimum := 16#80',
            'FirstByte >= 16#E0 AND FirstByte <= 16#EF', '_initialMask := 16#0F', '_minimum := 16#800',
            'FirstByte >= 16#F0 AND FirstByte <= 16#F4', '_initialMask := 16#07', '_minimum := 16#10000',
            'AccumulateUtf8Continuation(Bytes := Bytes, Index := Index, Required := _required',
            'IsValidUnicodeScalar(CodePoint := _cp, Minimum := _minimum)',
        ):
            self.assertIn(required, utf8)
        self.assertIn('IF Index + _j >= 255 THEN RETURN; END_IF', continuation)
        self.assertIn('IF Bytes[Index + _j] = 0 THEN RETURN; END_IF', continuation)
        self.assertIn('(Bytes[Index + _j] AND 16#C0) <> 16#80', continuation)
        self.assertLess(continuation.index('Index + _j >= 255'), continuation.index('Bytes[Index + _j] = 0'))
        self.assertIn('Taken := Taken + 1;', continuation)
        scalar = (source_root / 'IsValidUnicodeScalar/IsValidUnicodeScalar.IMP.exp').read_text(encoding='utf-8')
        self.assertIn('(CodePoint >= Minimum) AND (CodePoint <= 16#10FFFF)', scalar)
        self.assertIn('NOT (CodePoint >= 16#D800 AND CodePoint <= 16#DFFF)', scalar)

        escape = (source_root / 'AppendJsonEscapedCodePoint/AppendJsonEscapedCodePoint.IMP.exp').read_text(encoding='utf-8')
        for required in (
            "AppendLiteral(Value := '\\b')", "AppendLiteral(Value := '\\t')",
            "AppendLiteral(Value := '\\n')", "AppendLiteral(Value := '\\f')",
            "AppendLiteral(Value := '\\r')", "AppendLiteral(Value := '\\\"')",
            "AppendLiteral(Value := '\\\\')", "AppendLiteral(Value := '\\u00')",
            '16#FFFD', 'AppendCodePoint(Value := _cp)',
        ):
            self.assertIn(required, escape)
        self.assertIn('(_cp >= 16#D800 AND _cp <= 16#DFFF)', escape)
        self.assertIn('_cp = 16#FFFE OR _cp = 16#FFFF OR _cp > 16#10FFFF', escape)

        json_map = (source_root / 'MapWindows1252CodePoint/MapWindows1252CodePoint.IMP.exp').read_text(encoding='utf-8')
        json_cases = _literal_case_map(json_map, 'MapWindows1252CodePoint')
        self.assertIn('ELSE MapWindows1252CodePoint := 16#FFFD;', json_map)
        xml_escaper = (Path(__file__).resolve().parents[1] / 'PlaintextExport/Unit Test Framework for CODESYS/POUs/FB_xUnitXmlPublisher/AppendEscaped/AppendEscaped.IMP.exp').read_text(encoding='utf-8')
        xml_cases = _literal_case_map(xml_escaper, '_cp')
        for value in range(0x80, 0x100):
            expected = _python_cp1252_reference(value)
            if 0x80 <= value <= 0x9F:
                self.assertEqual(json_cases.get(value, 0xFFFD), expected, f'JSON Windows-1252 byte {value:#04x}')
                self.assertEqual(xml_cases.get(value, 0xFFFD), expected, f'XML Windows-1252 byte {value:#04x}')
            else:
                self.assertEqual(value, expected)
        self.assertEqual(json_cases, xml_cases)

        self.assertIn('E_CoUnitTextMode.LATIN1', (source_root / 'ServicePhasePrepare/ServicePhasePrepare.IMP.exp').read_text(encoding='utf-8'))
        declaration = (source_root / 'FB_JsonDiagnosticPublisher.DEC.exp').read_text(encoding='utf-8')
        self.assertIn('ARRAY[0..255] OF BYTE', declaration)
        self.assertNotIn('ST_CoUnitRunSnapshot;', declaration)

    def test_default_off_and_path_preflight_source_contract(self):
        repo = Path(__file__).resolve().parents[1]
        params = (repo / 'PlaintextExport/Unit Test Framework for CODESYS/GVLs/GVL_Param_coUnit/GVL_Param_coUnit.DEC.exp').read_text(encoding='utf-8')
        self.assertIn('DiagnosticJsonEnablePublish : BOOL := FALSE;', params)

        source_root = repo / 'PlaintextExport/Unit Test Framework for CODESYS/POUs/FB_JsonDiagnosticPublisher'
        service = (source_root / 'ServiceSnapshotWork/ServiceSnapshotWork.IMP.exp').read_text(encoding='utf-8')
        self.assertLess(service.index('IF NOT _enabled THEN _state := E_CoUnitReportState.DISABLED; RETURN; END_IF'), service.index('CASE _phase OF'))
        self.assertLess(service.index('IF NOT _enabled THEN _state := E_CoUnitReportState.DISABLED; RETURN; END_IF'), service.index('IF NOT Snapshot.IsValid THEN RETURN; END_IF'))
        self.assertNotIn('GVL_coUnit.xUnitFilePath :=', service)
        phase_prepare = (source_root / 'ServicePhasePrepare/ServicePhasePrepare.IMP.exp').read_text(encoding='utf-8')
        self.assertLess(phase_prepare.index('IF NOT BuildPaths()'), phase_prepare.index('ValidateSnapshot(Snapshot := Snapshot)'))
        self.assertLess(phase_prepare.index('ValidateSnapshot(Snapshot := Snapshot)'), phase_prepare.index('IF NOT Recover()'))
        self.assertLess(phase_prepare.index('IF NOT Recover()'), phase_prepare.index('_file.OpenWrite(Path := _stage)'))
        self.assertIn('BuildPaths := FALSE;', (source_root / 'BuildPaths/BuildPaths.IMP.exp').read_text(encoding='utf-8'))

        build_paths = (source_root / 'BuildPaths/BuildPaths.IMP.exp').read_text(encoding='utf-8')
        path_pairs = (
            ('_path', '_xmlPath'), ('_path', '_xmlStage'), ('_path', '_xmlBackup'),
            ('_stage', '_xmlPath'), ('_stage', '_xmlStage'), ('_stage', '_xmlBackup'),
            ('_backup', '_xmlPath'), ('_backup', '_xmlStage'), ('_backup', '_xmlBackup'),
        )
        for left, right in path_pairs:
            with self.subTest(left=left, right=right):
                self.assertIn(f'PathsConflict(LeftPath := {left}, RightPath := {right})', build_paths)
        self.assertIn('IF _jsonPathKind <> _xmlPathKind THEN RETURN; END_IF', build_paths)
        validate_path = (source_root / 'ValidateCanonicalPath/ValidateCanonicalPath.IMP.exp').read_text(encoding='utf-8')
        self.assertIn('ValidateCanonicalPath := FALSE;', validate_path)
        self.assertIn('IF _p[0] = 0 THEN RETURN; END_IF', validate_path)
        self.assertIn('FOR _length := 0 TO 244 DO', validate_path)
        self.assertIn('ValidatePathRoot(PathBytes := _p, Length := _length, PathKind => PathKind, Separator => _separator,', validate_path)
        self.assertIn('ValidatePathPart(PathBytes := _p, Position := _i, CurrentByte := _byte,', validate_path)
        self.assertIn('ValidateCanonicalPath := TRUE;', validate_path)

        root = (source_root / 'ValidatePathRoot/ValidatePathRoot.IMP.exp').read_text(encoding='utf-8')
        for required in (
            'ValidatePathRoot := FALSE;', 'PathKind := 0;',
            'IF PathBytes[0] = 16#2F THEN', 'PathKind := 2;',
            'ELSIF PathBytes[0] = 16#5C THEN', 'RETURN;',
            'ELSIF Length >= 2 AND PathBytes[1] = 16#3A THEN',
            '_isLetter := (PathBytes[0] >= 16#41 AND PathBytes[0] <= 16#5A) OR (PathBytes[0] >= 16#61 AND PathBytes[0] <= 16#7A);',
            'IF NOT _isLetter OR Length < 3 OR (PathBytes[2] <> 16#2F AND PathBytes[2] <> 16#5C) THEN RETURN; END_IF',
            'PathKind := 3;', 'ELSE\n\tPathKind := 1;', 'ValidatePathRoot := TRUE;',
        ):
            self.assertIn(required, root)

        part = (source_root / 'ValidatePathPart/ValidatePathPart.IMP.exp').read_text(encoding='utf-8')
        self.assertIn('ValidatePathPart := FALSE;', part)
        self.assertIn('IF CurrentByte = 16#2F OR CurrentByte = 16#5C OR CurrentByte = 0 THEN', part)
        self.assertIn('IF Separator = 0 THEN Separator := CurrentByte; END_IF', part)
        self.assertIn('ValidatePathSegment(PathBytes := PathBytes, Start := SegmentStart, Length := _segmentLength)', part)
        self.assertIn('IF Separator <> CurrentByte THEN RETURN; END_IF', part)
        self.assertIn('SegmentStart := Position + 1;', part)
        self.assertIn('ValidatePathPart := ValidatePathByte(Value := CurrentByte);', part)
        byte = (source_root / 'ValidatePathByte/ValidatePathByte.IMP.exp').read_text(encoding='utf-8')
        self.assertIn('ValidatePathByte := FALSE;', byte)
        self.assertIn('IF Value > 16#7F THEN RETURN; END_IF', byte)
        for allowed in ('16#41 AND Value <= 16#5A', '16#61 AND Value <= 16#7A', '16#30 AND Value <= 16#39', 'Value = 16#2D', 'Value = 16#5F', 'Value = 16#2E'):
            self.assertIn(allowed, byte)
        segment = (source_root / 'ValidatePathSegment/ValidatePathSegment.IMP.exp').read_text(encoding='utf-8')
        for required in (
            'ValidatePathSegment := FALSE;', 'IF Length = 0 THEN RETURN; END_IF',
            'IF Length = 1 AND PathBytes[Start] = 16#2E THEN RETURN; END_IF',
            'IF Length = 2 AND PathBytes[Start] = 16#2E AND PathBytes[Start + 1] = 16#2E THEN RETURN; END_IF',
            'IF PathBytes[Start + Length - 1] = 16#2E THEN RETURN; END_IF',
            'IsReservedPathSegment(PathBytes := PathBytes, Start := Start, Length := Length)',
            'ValidatePathSegment := TRUE;',
        ):
            self.assertIn(required, segment)
        reserved = (source_root / 'IsReservedPathSegment/IsReservedPathSegment.IMP.exp').read_text(encoding='utf-8')
        self.assertIn('UpperAsciiByte(Value := PathBytes[Start])', reserved)
        self.assertIn('IF PathBytes[Start + _i] = 16#2E THEN _baseLength := _i; EXIT; END_IF', reserved)
        for device_rule in (
            '16#43: IsReservedPathSegment := _second = 16#4F AND _third = 16#4E;',
            '16#50: IsReservedPathSegment := _second = 16#52 AND _third = 16#4E;',
            '16#41: IsReservedPathSegment := _second = 16#55 AND _third = 16#58;',
            '16#4E: IsReservedPathSegment := _second = 16#55 AND _third = 16#4C;',
            '16#43: IsReservedPathSegment := _second = 16#4F AND _third = 16#4D AND _fourth >= 16#31 AND _fourth <= 16#39;',
            '16#4C: IsReservedPathSegment := _second = 16#50 AND _third = 16#54 AND _fourth >= 16#31 AND _fourth <= 16#39;',
        ):
            self.assertIn(device_rule, reserved)
        self.assertIn('Value >= 16#61 AND Value <= 16#7A', (source_root / 'UpperAsciiByte/UpperAsciiByte.IMP.exp').read_text(encoding='utf-8'))

        one_path = (source_root / 'BuildOnePath/BuildOnePath.IMP.exp').read_text(encoding='utf-8')
        self.assertIn('FOR _length := 0 TO 244 DO', one_path)
        self.assertIn('FOR _i := 0 TO 10 DO', one_path)
        self.assertIn('_s[_i] := _p[_i];', one_path)
        self.assertIn('_b[_i] := _p[_i];', one_path)
        self.assertIn('_s[_length + _i] := _ss[_i];', one_path)
        self.assertIn('_b[_length + _i] := _sb[_i];', one_path)
        self.assertIn('_s[_length + 11] := 0;', one_path)
        self.assertIn('_b[_length + 11] := 0;', one_path)
        self.assertIn('IF _s[_length + 11] <> 0 OR _b[_length + 11] <> 0 THEN RETURN; END_IF', one_path)
        self.assertIn("_suffixS : T_MaxString := '.counit.tmp';", (source_root / 'BuildOnePath/BuildOnePath.DEC.exp').read_text(encoding='utf-8'))
        self.assertIn("_suffixB : T_MaxString := '.counit.bak';", (source_root / 'BuildOnePath/BuildOnePath.DEC.exp').read_text(encoding='utf-8'))

    def test_json_service_phases_and_snapshot_bounds_source_contract(self):
        """Source contracts and boundary probes only; this does not execute IEC code."""
        repo = Path(__file__).resolve().parents[1]
        source_root = repo / 'PlaintextExport/Unit Test Framework for CODESYS/POUs/FB_JsonDiagnosticPublisher'
        work = (source_root / 'ServiceSnapshotWork/ServiceSnapshotWork.IMP.exp').read_text(encoding='utf-8')
        dispatch = (
            ('0:', 'ServicePhasePrepare(Snapshot := Snapshot)'),
            ('1:', 'ServicePhaseHeader(Snapshot := Snapshot)'),
            ('2:', 'ServicePhaseSuite(Snapshot := Snapshot)'),
            ('3, 4:', 'ServicePhaseTest(Snapshot := Snapshot)'),
            ('5:', 'ServicePhaseAdvanceSuite()'),
            ('6:', 'ServicePhasePreserveCurrent()'),
            ('7:', 'ServicePhaseCommit()'),
            ('8:', 'ServicePhaseCleanup()'),
        )
        for phase, handler in dispatch:
            with self.subTest(phase=phase):
                self.assertIn(phase + ' IF NOT ' + handler + ' THEN RETURN; END_IF', work)
                self.assertEqual(work.count(handler), 1)
        self.assertNotIn('_phase :=', work)
        self.assertIn("Fail(Operation := 'invalid JSON publication phase');", work)

        compat = (source_root / 'ServiceSnapshot/ServiceSnapshot.IMP.exp').read_text(encoding='utf-8')
        self.assertIn('ServiceSnapshot := FALSE;', compat)
        self.assertIn('ServiceSnapshotWork(Snapshot := Snapshot);', compat)
        self.assertIn('ServiceSnapshot := _state = E_CoUnitReportState.WRITTEN;', compat)
        compat_dec = (source_root / 'ServiceSnapshot/ServiceSnapshot.DEC.exp').read_text(encoding='utf-8')
        self.assertIn('VAR_IN_OUT\n\tSnapshot : ST_CoUnitRunSnapshot;', compat_dec)

        publication_dec = (source_root / 'ServicePublication/ServicePublication.DEC.exp').read_text(encoding='utf-8')
        publication = (source_root / 'ServicePublication/ServicePublication.IMP.exp').read_text(encoding='utf-8')
        self.assertIn('METHOD PUBLIC ServicePublication\n', publication_dec)
        self.assertNotIn('METHOD PUBLIC ServicePublication :', publication_dec)
        self.assertLess(publication.index('_snapshot REF='), publication.index('__ISVALIDREF(_snapshot)'))
        self.assertLess(publication.index('__ISVALIDREF(_snapshot)'), publication.index('ServiceSnapshotWork(Snapshot := _snapshot)'))
        logger = (source_root / 'LogTestSuiteResults/LogTestSuiteResults.IMP.exp').read_text(encoding='utf-8')
        self.assertIn('LogTestSuiteResults := FALSE;', logger)
        self.assertLess(logger.index('_snapshot REF='), logger.index('__ISVALIDREF(_snapshot)'))
        self.assertLess(logger.index('__ISVALIDREF(_snapshot)'), logger.index('ServiceSnapshot(Snapshot := _snapshot)'))

        prepare = (source_root / 'ServicePhasePrepare/ServicePhasePrepare.IMP.exp').read_text(encoding='utf-8')
        for earlier, later in (
            ('BuildPaths()', 'ValidateSnapshot(Snapshot := Snapshot)'),
            ('ValidateSnapshot(Snapshot := Snapshot)', 'Recover()'),
            ('Recover()', '_file.OpenWrite(Path := _stage)'),
        ):
            self.assertLess(prepare.index(earlier), prepare.index(later))
        validate = (source_root / 'ValidateSnapshot/ValidateSnapshot.IMP.exp').read_text(encoding='utf-8')
        validate_suite = (source_root / 'ValidateSnapshotSuite/ValidateSnapshotSuite.IMP.exp').read_text(encoding='utf-8')
        self.assertNotIn('_file.', validate)
        self.assertNotIn('_file.', validate_suite)
        self.assertIn('ValidateSnapshot := FALSE;', validate)
        self.assertIn('FOR _s := 1 TO GVL_Param_coUnit.MaxNumberOfTestSuites DO', validate)
        self.assertIn('IF _s > Snapshot.SuiteCount THEN EXIT; END_IF', validate)
        self.assertIn('ValidateSnapshotSuite(Snapshot := Snapshot, SuiteIndex := _s', validate)
        self.assertIn('IF _s = Snapshot.SuiteCount THEN EXIT; END_IF', validate)
        self.assertLess(validate.index('ValidateSnapshotSuite(Snapshot := Snapshot, SuiteIndex := _s'),
                        validate.index('IF _s = Snapshot.SuiteCount THEN EXIT; END_IF'))
        self.assertLess(validate.index('IF _s = Snapshot.SuiteCount THEN EXIT; END_IF'), validate.index('END_FOR'))
        self.assertIn('IF _testIndex = Snapshot.Suites[SuiteIndex].Total THEN EXIT; END_IF', validate_suite)
        self.assertLess(validate_suite.index('END_CASE'),
                        validate_suite.index('IF _testIndex = Snapshot.Suites[SuiteIndex].Total THEN EXIT; END_IF'))
        self.assertLess(validate_suite.index('IF _testIndex = Snapshot.Suites[SuiteIndex].Total THEN EXIT; END_IF'),
                        validate_suite.index('END_FOR'))

        suite_handler = (source_root / 'ServicePhaseSuite/ServicePhaseSuite.IMP.exp').read_text(encoding='utf-8')
        test_handler = (source_root / 'ServicePhaseTest/ServicePhaseTest.IMP.exp').read_text(encoding='utf-8')
        _assert_snapshot_index_source_contract(self, suite_handler, test_handler, validate_suite)
        bad_suite_guard = suite_handler.replace('OR\n\t\t_suiteIndex > GVL_Param_coUnit.MaxNumberOfTestSuites', '', 1)
        self.assertNotEqual(bad_suite_guard, suite_handler)
        with self.assertRaises(AssertionError):
            _assert_snapshot_index_source_contract(self, bad_suite_guard, test_handler, validate_suite)
        bad_test_guard = test_handler.replace('OR\n\t\t_testIndex > GVL_Param_coUnit.MaxNumberOfTestsForEachTestSuite', '', 1)
        self.assertIn('GVL_Param_coUnit.MaxNumberOfTestsForEachTestSuite THEN', test_handler)
        self.assertNotEqual(bad_test_guard, test_handler)
        with self.assertRaises(AssertionError):
            _assert_snapshot_index_source_contract(self, suite_handler, bad_test_guard, validate_suite)

        params = (repo / 'PlaintextExport/Unit Test Framework for CODESYS/GVLs/GVL_Param_coUnit/GVL_Param_coUnit.DEC.exp').read_text(encoding='utf-8')
        for parameter in ('MaxNumberOfTestSuites', 'MaxNumberOfTestsForEachTestSuite'):
            capacity_match = re.search(rf'^\s*{parameter}\s*:\s*UINT\s*:=\s*(\d+);', params, flags=re.MULTILINE)
            self.assertIsNotNone(capacity_match)
            capacity = int(capacity_match.group(1))
            for count in (0, 1, capacity):
                probes = ((0, False), (1, count >= 1), (count, count >= 1),
                          (count + 1, False), (capacity, capacity <= count), (capacity + 1, False))
                for index, expected_safe in probes:
                    with self.subTest(parameter=parameter, count=count, index=index):
                        self.assertEqual(index >= 1 and index <= count and index <= capacity, expected_safe)

        commit = (source_root / 'ServicePhaseCommit/ServicePhaseCommit.IMP.exp').read_text(encoding='utf-8')
        cleanup = (source_root / 'ServicePhaseCleanup/ServicePhaseCleanup.IMP.exp').read_text(encoding='utf-8')
        self.assertIn('_state := E_CoUnitReportState.WRITTEN;\n_phase := 8;', commit)
        self.assertIn('IF _pauseAfter <> 8 THEN\n\tIF NOT ServicePhaseCleanup() THEN RETURN; END_IF\nEND_IF', commit)
        self.assertLess(commit.index('_phase := 8;'), commit.index('IF _pauseAfter <> 8 THEN'))
        self.assertLess(commit.index('IF _pauseAfter <> 8 THEN'), commit.index('ServicePhaseCleanup()'))
        self.assertLess(commit.index('ServicePhaseCleanup()'), commit.index('ServicePhaseCommit := TRUE;'))
        self.assertIn('8: IF NOT ServicePhaseCleanup() THEN RETURN; END_IF', work)
        self.assertIn('_phase := 9;', cleanup)
        self.assertIn('IF _pauseAfter <> 0 AND _phase = _pauseAfter THEN _paused := TRUE; END_IF', work)
        self.assertIn('_state = E_CoUnitReportState.WRITTEN AND _phase <> 8', work)
        resume = (source_root / 'Resume/Resume.IMP.exp').read_text(encoding='utf-8')
        self.assertIn('_paused := FALSE;', resume)
        self.assertIn('_pauseAfter := 0;', resume)

        preserve = (source_root / 'ServicePhasePreserveCurrent/ServicePhasePreserveCurrent.IMP.exp').read_text(encoding='utf-8')
        self.assertIn('_file.Probe(Path := _path, Size => _currentSize)', preserve)
        self.assertIn('FailRecoveryArtifact(Size := _currentSize, Operation :=', preserve)
        self.assertIn('SHR(UDINT_TO_DWORD(_cp), 4)', (source_root / 'AppendJsonEscapedCodePoint/AppendJsonEscapedCodePoint.IMP.exp').read_text(encoding='utf-8'))
        self.assertNotIn('_p : POINTER TO BYTE;', (source_root / 'IsReservedPathSegment/IsReservedPathSegment.DEC.exp').read_text(encoding='utf-8'))
        self.assertIn('E_CoUnitRunDisposition.UNSET:', (source_root / 'ServicePhaseHeader/ServicePhaseHeader.IMP.exp').read_text(encoding='utf-8'))
        self.assertIn('ELSE\n\tFail(Operation := \'invalid JSON publication phase\');', work)

        log_sources = (
            (source_root / 'Fail/Fail.IMP.exp').read_text(encoding='utf-8'), commit, cleanup,
        )
        self.assertEqual(sum(source.count('WRITE_DEVICE_LOG(') for source in log_sources), 5)
        for source in log_sources:
            self.assertNotRegex(source, r'\w+\s*:=\s*WRITE_DEVICE_LOG\s*\(')


if __name__ == '__main__':
    unittest.main()
