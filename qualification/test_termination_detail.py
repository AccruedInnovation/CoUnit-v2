"""Parser fixtures for assertion details retained on aborted/error cases."""
import json
import tempfile
import unittest
import xml.sax.saxutils as sax
from pathlib import Path

import verify_json_report as json_report
import verify_xunit as xml_report


ROOT_METADATA = {
    'schema_version': 2,
    'framework_version': '2.1.0.1',
    'run_id': 'run<&>1',
    'build_id': 'build&2',
    'target_id': 'target<3>',
    'generation': 1,
    'clock_mode': 'MONOTONIC',
}
SUITE_ID = 'suite<&>main'
CASE_ID = 'case<&>id'
ROW_KEY = 'row<&>key'


def _xml_attr(value):
    return sax.escape(value).replace('"', '&quot;')


def _xml_root_metadata():
    return (
        f'counit-schema-version="{ROOT_METADATA["schema_version"]}" '
        f'counit-framework-version="{_xml_attr(ROOT_METADATA["framework_version"])}" '
        f'counit-run-id="{_xml_attr(ROOT_METADATA["run_id"])}" '
        f'counit-build-id="{_xml_attr(ROOT_METADATA["build_id"])}" '
        f'counit-target-id="{_xml_attr(ROOT_METADATA["target_id"])}" '
        f'counit-generation="{ROOT_METADATA["generation"]}" '
        f'counit-clock-mode="{_xml_attr(ROOT_METADATA["clock_mode"])}"'
    )


def _reports(disposition, generic_message, termination_reason):
    suite_name = 'Termination suite'
    case_name = 'Assertion then termination'
    first_failure = {
        'type': 'Type_BOOL',
        'message': 'initial assertion detail...<truncated>',
        'expected': 'TRUE',
        'actual': 'FALSE',
    }
    json_payload = {
        'format_version': 2,
        **ROOT_METADATA,
        'run_disposition': disposition,
        'tests': 1,
        'failures': 0,
        'errors': 1,
        'skipped': 0,
        'suites': [{
            'identity': 7,
            'name': suite_name,
            'suite_id': SUITE_ID,
            'tests': 1,
            'failures': 0,
            'errors': 1,
            'skipped': 0,
            'cases': [{
                'classname': suite_name,
                'name': case_name,
                'case_id': CASE_ID,
                'row_key': ROW_KEY,
                'status': 'error',
                'assertions': 1,
                'selected': True,
                'started': True,
                'error': {
                    'message': generic_message,
                    'termination_reason': termination_reason,
                    'first_failure': first_failure,
                },
            }],
        }],
    }

    xml_escape = lambda value: sax.escape(value).replace('\n', '&#10;').replace('\r', '&#13;')
    body = f'Expected: {first_failure["expected"]}\nActual: {first_failure["actual"]}'
    xml_report_text = (
        f'<testsuites tests="1" failures="0" errors="1" skipped="0" '
        f'counit-run-disposition="{disposition}" {_xml_root_metadata()}>'
        f'<testsuite id="7" name="{_xml_attr(suite_name)}" '
        f'counit-suite-id="{_xml_attr(SUITE_ID)}" tests="1" failures="0" errors="1" skipped="0">'
        f'<testcase classname="{_xml_attr(suite_name)}" name="{_xml_attr(case_name)}" '
        f'counit-case-id="{_xml_attr(CASE_ID)}" counit-row-key="{_xml_attr(ROW_KEY)}" '
        'counit-selected="TRUE" counit-started="TRUE" assertions="1">'
        f'<error message="{_xml_attr(generic_message)}" '
        f'termination-reason="{_xml_attr(termination_reason)}" '
        f'failure-type="{_xml_attr(first_failure["type"])}" '
        f'failure-message="{_xml_attr(first_failure["message"])}">{xml_escape(body)}</error>'
        '</testcase></testsuite></testsuites>'
    )
    return json_payload, xml_report_text


def _root_reason_reports(with_passed_case):
    reason = 'late framework failure after case closure'
    suites = []
    if with_passed_case:
        suites.append({
            'identity': 0,
            'name': 'Completed suite',
            'suite_id': SUITE_ID,
            'tests': 1,
            'failures': 0,
            'errors': 0,
            'skipped': 0,
            'cases': [{
                'classname': 'Completed suite',
                'name': 'Completed case',
                'case_id': CASE_ID,
                'row_key': ROW_KEY,
                'status': 'passed',
                'assertions': 2,
                'selected': True,
                'started': True,
            }],
        })
    total = sum(suite['tests'] for suite in suites)
    json_payload = {
        'format_version': 2,
        **ROOT_METADATA,
        'run_disposition': 'FRAMEWORK_ERROR',
        'termination_reason': reason,
        'tests': total,
        'failures': 0,
        'errors': 0,
        'skipped': 0,
        'suites': suites,
    }
    xml_text = (
        f'<testsuites tests="{total}" failures="0" errors="0" skipped="0" '
        f'counit-run-disposition="FRAMEWORK_ERROR" '
        f'counit-termination-reason="{reason}" {_xml_root_metadata()}>'
    )
    for suite in suites:
        xml_text += (
            f'<testsuite id="{suite["identity"]}" name="{suite["name"]}" '
            f'counit-suite-id="{_xml_attr(suite["suite_id"])}" '
            'tests="1" failures="0" errors="0" skipped="0">'
            f'<testcase classname="{suite["name"]}" name="Completed case" '
            f'counit-case-id="{_xml_attr(CASE_ID)}" counit-row-key="{_xml_attr(ROW_KEY)}" '
            'counit-selected="TRUE" counit-started="TRUE" assertions="2"/>'
            '</testsuite>'
        )
    xml_text += '</testsuites>'
    return json_payload, xml_text, reason


class TerminationDetailTests(unittest.TestCase):
    def test_abort_and_framework_error_keep_first_failure_and_later_reason(self):
        cases = (
            ('ABORTED', 'Run aborted', 'operator abort after assertion'),
            ('FRAMEWORK_ERROR', 'Framework error', 'later framework boundary failure'),
        )
        with tempfile.TemporaryDirectory() as directory:
            for index, (disposition, generic_message, reason) in enumerate(cases):
                with self.subTest(disposition=disposition):
                    json_path = Path(directory) / f'{index}.json'
                    xml_path = Path(directory) / f'{index}.xml'
                    payload, xml_text = _reports(disposition, generic_message, reason)
                    json_path.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
                    xml_path.write_text(xml_text, encoding='utf-8')

                    json_summary = json_report.summarize(json_path)
                    xml_summary = xml_report.summarize(xml_path)
                    self.assertEqual(json_summary, xml_summary)
                    case = json_summary['suites'][0]['cases'][0]
                    self.assertEqual(case['status'], 'error')
                    self.assertEqual(json_summary['errors'], 1)
                    self.assertEqual(case['error']['message'], generic_message)
                    self.assertEqual(case['error']['termination_reason'], reason)
                    self.assertEqual(case['error']['first_failure'], {
                        'type': 'Type_BOOL',
                        'message': 'initial assertion detail...<truncated>',
                        'body': 'Expected: TRUE\nActual: FALSE',
                    })
                    self.assertNotIn(reason, case['error']['first_failure']['message'])
                    self.assertEqual(json_summary['schema_version'], 2)
                    self.assertEqual(json_summary['run_id'], ROOT_METADATA['run_id'])
                    self.assertEqual(json_summary['build_id'], ROOT_METADATA['build_id'])
                    self.assertEqual(json_summary['target_id'], ROOT_METADATA['target_id'])
                    self.assertEqual(json_summary['generation'], ROOT_METADATA['generation'])
                    suite = json_summary['suites'][0]
                    self.assertEqual(suite['suite_id'], SUITE_ID)
                    self.assertEqual(case['case_id'], CASE_ID)
                    self.assertEqual(case['row_key'], ROW_KEY)
                    self.assertTrue(case['selected'])
                    self.assertTrue(case['started'])

    def test_empty_and_completed_reports_keep_run_only_framework_error(self):
        with tempfile.TemporaryDirectory() as directory:
            for index, has_passed_case in enumerate((False, True)):
                with self.subTest(has_passed_case=has_passed_case):
                    json_path = Path(directory) / f'root-{index}.json'
                    xml_path = Path(directory) / f'root-{index}.xml'
                    payload, xml_text, reason = _root_reason_reports(has_passed_case)
                    json_path.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
                    xml_path.write_text(xml_text, encoding='utf-8')

                    json_summary = json_report.summarize(json_path)
                    xml_summary = xml_report.summarize(xml_path)
                    self.assertEqual(json_summary, xml_summary)
                    self.assertEqual(json_summary['run_disposition'], 'FRAMEWORK_ERROR')
                    self.assertEqual(json_summary['termination_reason'], reason)
                    self.assertEqual(json_summary['tests'], int(has_passed_case))
                    self.assertEqual(json_summary['errors'], 0)
                    cases = [case for suite in json_summary['suites'] for case in suite['cases']]
                    self.assertEqual(len(cases), int(has_passed_case))
                    if has_passed_case:
                        self.assertEqual(cases[0]['status'], 'passed')

    def test_same_display_name_preserves_distinct_rows_and_selection(self):
        rows = (
            {'case_id': 'mix', 'row_key': 'A<&>', 'selected': False, 'started': False, 'status': 'skipped'},
            {'case_id': 'mix', 'row_key': 'B<&>', 'selected': True, 'started': False, 'status': 'skipped'},
            {'case_id': 'mix', 'row_key': 'C<&>', 'selected': True, 'started': True, 'status': 'passed'},
        )
        cases = [{
            'classname': 'Catalog suite',
            'name': 'Same display name',
            'assertions': 0,
            **row,
        } for row in rows]
        payload = {
            'format_version': 2,
            **ROOT_METADATA,
            'run_disposition': 'NORMAL',
            'tests': 3,
            'failures': 0,
            'errors': 0,
            'skipped': 2,
            'suites': [{
                'identity': 0,
                'name': 'Catalog suite',
                'suite_id': 'catalog<&>',
                'tests': 3,
                'failures': 0,
                'errors': 0,
                'skipped': 2,
                'cases': cases,
            }],
        }
        xml_text = (
            '<testsuites tests="3" failures="0" errors="0" skipped="2" '
            f'counit-run-disposition="NORMAL" {_xml_root_metadata()}>'
            '<testsuite id="0" name="Catalog suite" counit-suite-id="catalog&lt;&amp;&gt;" '
            'tests="3" failures="0" errors="0" skipped="2">'
        )
        for row in rows:
            xml_status = 'TRUE' if row['selected'] else 'FALSE'
            xml_started = 'TRUE' if row['started'] else 'FALSE'
            child = '<skipped/>' if row['status'] == 'skipped' else ''
            xml_text += (
                '<testcase classname="Catalog suite" name="Same display name" '
                f'counit-case-id="{row["case_id"]}" counit-row-key="{_xml_attr(row["row_key"])}" '
                f'counit-selected="{xml_status}" counit-started="{xml_started}" assertions="0">'
                f'{child}</testcase>'
            )
        xml_text += '</testsuite></testsuites>'

        with tempfile.TemporaryDirectory() as directory:
            json_path = Path(directory) / 'identity.json'
            xml_path = Path(directory) / 'identity.xml'
            json_path.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
            xml_path.write_text(xml_text, encoding='utf-8')
            summary = json_report.summarize(json_path)
            self.assertEqual(summary, xml_report.summarize(xml_path))
            parsed = summary['suites'][0]['cases']
            self.assertEqual([case['name'] for case in parsed], ['Same display name'] * 3)
            self.assertEqual([(case['case_id'], case['row_key']) for case in parsed], [
                ('mix', 'A<&>'), ('mix', 'B<&>'), ('mix', 'C<&>'),
            ])
            self.assertEqual([case['selected'] for case in parsed], [False, True, True])
            self.assertEqual([case['started'] for case in parsed], [False, False, True])
            self.assertEqual([case['status'] for case in parsed], ['skipped', 'skipped', 'passed'])

if __name__ == '__main__':
    unittest.main()
