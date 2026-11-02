"""Independent checks for streamed xUnit failure-body preservation."""
import tempfile
import unittest
from pathlib import Path

import verify_xunit as xml


class FailureBodyTests(unittest.TestCase):
    def test_mixed_fixture_preserves_escaped_failure_body(self):
        fixture = Path(__file__).parent / 'fixtures'
        summary = xml.summarize(fixture / 'mixed-results.xml')
        self.assertEqual(
            summary['suites'][0]['cases'][1]['failure'],
            {
                'type': 'Type_DINT',
                'message': 'expected <3 & 4> but got "5"',
                'body': 'Expected: 3 & <4>\nActual: "5"',
            },
        )
        self.assertEqual(
            [case['status'] for case in summary['suites'][0]['cases']],
            ['passed', 'failure', 'skipped', 'error'],
        )
        self.assertEqual(summary['suites'][0]['cases'][0]['assertions'], 2)
        self.assertNotIn('failure', summary['suites'][0]['cases'][2])
        self.assertEqual(summary['suites'][0]['cases'][3]['error'], {'message': 'task lookup failed'})

    def test_failure_body_oracle_keeps_string_array_and_long_values(self):
        expected = 'left <& "quoted"\t\n' + ('e' * 255)
        actual = 'right &> "quoted"\r' + ('a' * 255)
        body_text = f'Expected: {expected}\nActual: {actual}'
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / 'body.xml'
            escaped = (
                'Expected: left &lt;&amp; &quot;quoted&quot;&#9;&#10;' + ('e' * 255) +
                '&#10;Actual: right &amp;&gt; &quot;quoted&quot;&#13;' + ('a' * 255)
            )
            report.write_text(
                '<testsuites tests="2" failures="2" errors="0" skipped="0">'
                '<testsuite name="Publisher" tests="2" failures="2" errors="0" skipped="0">'
                '<testcase classname="Publisher" name="String mismatch" assertions="1">'
                '<failure type="Type_STRING" message="mismatch">' + escaped + '</failure></testcase>'
                '<testcase classname="Publisher" name="Array mismatch" assertions="1">'
                '<failure type="Type_Array_UINT" message="array mismatch">'
                'Expected: 4&#10;Actual: 5</failure></testcase>'
                '</testsuite></testsuites>',
                encoding='utf-8',
            )
            summary = xml.summarize(report)
            cases = summary['suites'][0]['cases']
            self.assertEqual(cases[0]['failure']['body'], body_text)
            self.assertEqual(cases[1]['failure']['type'], 'Type_Array_UINT')
            self.assertEqual(cases[1]['failure']['body'], 'Expected: 4\nActual: 5')

    def test_failure_body_must_be_text_not_nested_markup(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / 'nested.xml'
            report.write_text(
                '<testsuites tests="1" failures="1" errors="0" skipped="0">'
                '<testsuite name="Publisher" tests="1" failures="1" errors="0" skipped="0">'
                '<testcase name="Mismatch"><failure type="Type_BOOL"><expected>false</expected></failure></testcase>'
                '</testsuite></testsuites>',
                encoding='utf-8',
            )
            with self.assertRaises(xml.CheckError):
                xml.summarize(report)

    def test_publisher_streams_both_values_through_existing_xml_escaper(self):
        publisher = (
            Path(__file__).resolve().parents[1] /
            'PlaintextExport/Unit Test Framework for CODESYS/POUs/FB_xUnitXmlPublisher'
        )
        caller = (publisher / 'EmitTest/EmitTest.IMP.exp').read_text(encoding='utf-8')
        source = (publisher / 'EmitFailure/EmitFailure.IMP.exp').read_text(encoding='utf-8')
        self.assertIn('IF NOT EmitFailure(Test := Test) THEN RETURN; END_IF', caller)
        self.assertIn('AppendEscaped(Value := Test.FirstFailure.ExpectedText)', source)
        self.assertIn('AppendEscaped(Value := Test.FirstFailure.ActualText)', source)
        self.assertIn("AppendLiteral(Value := '&#10;Actual: ')", source)
        expected = source.index('AppendEscaped(Value := Test.FirstFailure.ExpectedText)')
        separator = source.index("AppendLiteral(Value := '&#10;Actual: ')")
        actual = source.index('AppendEscaped(Value := Test.FirstFailure.ActualText)')
        self.assertLess(expected, separator)
        self.assertLess(separator, actual)


if __name__ == '__main__':
    unittest.main()
