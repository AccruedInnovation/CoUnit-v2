"""Host oracle controls; these do not claim native CoUnit correctness."""
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import check_public_api as api
import verify_xunit as xml
import check_runtime_matrix as matrix
import generate_native as native
import check_utf8_diagnostic as utf8
import check_device_log as log
import check_report as report_check
import json


class PublicSurfaceTests(unittest.TestCase):
    def test_private_storage_allowed(self):
        before = 'METHOD PUBLIC F : BOOL\nVAR_INPUT\nX : UINT;\nEND_VAR\nVAR\nOld : INT;\nEND_VAR'
        after = before.replace('Old : INT;', 'New : STRING(255);')
        self.assertEqual(api.signature(before, 'interface_method'), api.signature(after, 'interface_method'))

    def test_input_direction_type_and_return_drift(self):
        before = 'METHOD PUBLIC F : BOOL\nVAR_INPUT\nX : UINT;\nEND_VAR'
        for after in (before.replace('VAR_INPUT', 'VAR_IN_OUT'), before.replace('UINT', 'UDINT'), before.replace(': BOOL', ': UINT')):
            self.assertNotEqual(api.signature(before, 'interface_method'), api.signature(after, 'interface_method'))

    def test_struct_and_config_not_ignored(self):
        for kind, text in [('type', 'TYPE X : STRUCT Field : UINT; END_STRUCT END_TYPE'), ('global_constants', 'VAR_GLOBAL CONSTANT Limit : UINT := 32; END_VAR')]:
            self.assertNotEqual(api.signature(text, kind), api.signature(text.replace('UINT', 'UDINT'), kind))

    def test_comment_tokens_inside_strings(self):
        self.assertIn("'//(*x*)'", api.uncomment("A := '//(*x*)'; // remove\n(* remove *)"))


class XmlOracleTests(unittest.TestCase):
    def test_positive_exact_inventory(self):
        fixture = Path(__file__).parent / 'fixtures'
        self.assertEqual(xml.main(['verify', str(fixture / 'mixed-results.xml'), str(fixture / 'mixed-results.expected.json')]), 0)

    def test_negative_controls(self):
        fixture = Path(__file__).parent / 'fixtures'
        for name in ('bad-count.xml', 'bad-terminal.xml', 'bad-assertions.xml'):
            self.assertEqual(xml.main(['verify', str(fixture / name)]), 1)

    def test_well_formed_omitted_inventory_fails_expected(self):
        fixture = Path(__file__).parent / 'fixtures'
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'empty.xml'
            path.write_text('<testsuites tests="0" failures="0" errors="0" skipped="0"/>')
            self.assertEqual(xml.main(['verify', str(path), str(fixture / 'mixed-results.expected.json')]), 1)

    def test_framework_disposition_preserved_but_not_release_success(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'framework.xml'
            path.write_text('<testsuites counit-run-disposition="FRAMEWORK_ERROR" tests="1" failures="0" errors="0" skipped="0"><testsuite name="Suite" tests="1" failures="0" errors="0" skipped="0"><testcase classname="Suite" name="Pass" assertions="0"/></testsuite></testsuites>')
            summary = xml.summarize(path)
            self.assertEqual(summary['run_disposition'], 'FRAMEWORK_ERROR')
            xml.require_disposition(summary)
            with self.assertRaises(xml.CheckError):
                xml.require_disposition(summary, success=True)
            report_check.check(path, {'run_disposition': 'FRAMEWORK_ERROR', 'suites': [[{'name': 'Pass', 'state': 'PASSED', 'assertions': 0}]]}, ['Suite'])
            path.write_text(path.read_text().replace('FRAMEWORK_ERROR', 'NORMAL'))
            xml.require_disposition(xml.summarize(path), success=True)

    def test_candidate_requires_disposition_and_rejects_unknown(self):
        legacy = xml.summarize(Path(__file__).parent / 'fixtures/mixed-results.xml')
        with self.assertRaises(xml.CheckError):
            xml.require_disposition(legacy)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'unknown.xml'
            path.write_text('<testsuites counit-run-disposition="UNKNOWN" tests="0" failures="0" errors="0" skipped="0"/>')
            with self.assertRaises(xml.CheckError):
                xml.summarize(path)


class RuntimeDispositionTests(unittest.TestCase):
    def test_supported_requires_bound_identity(self):
        row = {key: 'PASS' for key in matrix.STATUSES}
        row.update(row_id='test', support_disposition='SUPPORTED', string_encoding_mode='UTF8', legacy_mapping_id='N/A', snapshot_size_bytes='1', application_static_memory_bytes='1')
        self.assertTrue(matrix.check([row]))

    def test_failure_cannot_be_unqualified(self):
        row = {key: 'NOT_RUN' for key in matrix.STATUSES}
        row.update(row_id='test', compile_status='FAIL', support_disposition='UNQUALIFIED')
        self.assertIn('test: status values require UNSUPPORTED', matrix.check([row]))


class NativeGeneratorTests(unittest.TestCase):
    def test_all_public_families_and_compound_type_suffixes(self):
        suites, expected = native.assertions()
        self.assertEqual(len(expected[0]), 44)
        self.assertEqual(len({case['name'] for case in expected[0]}), 44)
        declaration = suites[0].declaration
        self.assertIn(': DATE_AND_TIME := DT#', declaration)
        self.assertIn(': TIME_OF_DAY := TOD#', declaration)
        self.assertNotIn(': DAY', declaration)

    def test_disabled_names_expect_canonical_identity(self):
        _, expected = native.ordered()
        self.assertEqual([case['name'] for case in expected[0]], ['First', 'EnabledA', 'Middle', 'EnabledB', 'Last'])
        self.assertEqual([case['state'] for case in expected[0]], ['SKIPPED', 'PASSED', 'SKIPPED', 'PASSED', 'SKIPPED'])

    def test_runner_terminates_on_invalid_snapshot(self):
        runner, checks = native.runner([], [])
        self.assertIn('GetRunState() = E_CoUnitRunState.COMPLETE', runner.implementation)
        self.assertEqual(checks[0], '_snapshot.IsValid')

    def test_generated_xml_has_unique_program_and_objects(self):
        paths = list((Path(__file__).parent / 'generated').glob('*/qualification.xml'))
        self.assertGreaterEqual(len(paths), 24)
        ns = {'p': native.plc.PLCOPEN}
        for path in paths:
            root = ET.parse(path).getroot()
            pous = root.findall('./p:types/p:pous/p:pou', ns)
            names = [pou.get('name') for pou in pous]
            self.assertEqual(len(names), len(set(names)), str(path))
            self.assertEqual(names.count('PRG_Qualification'), 1, str(path))

    def test_utf8_oracle_rejects_split_sequence(self):
        expected = json.loads((Path(__file__).parent / 'generated/utf8_diagnostic/expected.json').read_text(encoding='utf-8'))
        raw = bytes.fromhex(expected['diagnostic_hex'])
        capture = list(raw + bytes(256 - len(raw)))
        utf8.check(capture, expected)
        encoded = bytes(capture).hex()
        utf8.check({'hex_chunks': [encoded[index:index + 128] for index in range(0, 512, 128)]}, expected)
        damaged = capture.copy()
        damaged[expected['diagnostic_byte_count'] - 15] = 0xC3
        with self.assertRaises(ValueError):
            utf8.check(damaged, expected)

    def test_utf8_decoder_override_follows_binding(self):
        root = Path(__file__).parent / 'generated/utf8_diagnostic'
        program = (root / 'PRG_Qualification/POU.PRG_Qualification.IMP.exp').read_text()
        self.assertLess(program.index('RUN();'), program.index('GVL_coUnit.StringIsUtf8 := TRUE;'))
        method = (root / 'FB_QualificationUtf8/M.Utf8Diagnostic.IMP.exp').read_text()
        self.assertIn('IF _scans = 1 THEN RETURN; END_IF', method)


class DeviceLogTests(unittest.TestCase):
    def setUp(self):
        self.expected = json.loads((Path(__file__).parent / 'generated/device_log/expected.json').read_text(encoding='utf-8'))
        self.capture = {}
        for name, oracle in self.expected['messages'].items():
            text = oracle['text']
            if name == 'utf8_boundary':
                self.capture[name] = [text[:126], text[126:]]
            else:
                self.capture[name] = [text[index:index + 127] for index in range(0, len(text), 127)]

    def test_long_complete_and_first_placeholder_only(self):
        self.assertEqual((self.expected['format_bytes'], self.expected['argument_bytes'], self.expected['long_result_bytes']), (250, 250, 498))
        log.check(self.capture, self.expected)

    def test_lost_suffix_rejected(self):
        self.capture['long'][-1] = self.capture['long'][-1][:-1]
        with self.assertRaises(ValueError):
            log.check(self.capture, self.expected)

    def test_split_utf8_rejected(self):
        raw = bytes.fromhex(self.expected['messages']['utf8_boundary']['hex'])
        self.capture['utf8_boundary'] = [{'hex': raw[:127].hex()}, {'hex': raw[127:].hex()}]
        with self.assertRaises(ValueError):
            log.check(self.capture, self.expected)


if __name__ == '__main__':
    unittest.main()
