"""Compare actual PLC XML with a generated independent native-shard inventory.

The caller binds exact suite class paths from the imported project before launch.
This check does not prove freshness or publication commit; retain launch evidence.
"""
import argparse
import json
from pathlib import Path

from verify_xunit import summarize, require_disposition, CheckError

STATES = {'PASSED': 'passed', 'FAILED': 'failure', 'SKIPPED': 'skipped', 'ABORTED': 'error', 'ERROR': 'error'}


def check(report, expected, classes):
    actual = summarize(report)
    require_disposition(actual)
    if actual['run_disposition'] != expected['run_disposition']:
        raise CheckError('run disposition differs from independent native-shard expectation')
    suites = expected['suites']
    if len(classes) != len(suites):
        raise CheckError('bind exactly one --suite-class per expected suite before execution')
    if len(actual['suites']) != len(suites):
        raise CheckError('selected suite inventory does not match report')
    for index, (want, got, classname) in enumerate(zip(suites, actual['suites'], classes), 1):
        if got['name'] != classname or len(want) != len(got['cases']):
            raise CheckError(f'suite {index}: wrong class or selected case count')
        for expected_case, actual_case in zip(want, got['cases']):
            fields = {'name': expected_case['name'], 'classname': classname,
                      'status': STATES[expected_case['state']], 'assertions': expected_case['assertions']}
            for key, value in fields.items():
                if actual_case.get(key) != value:
                    raise CheckError(f"{expected_case['name']}: {key} expected {value!r}, observed {actual_case.get(key)!r}")
            if 'failure_type' in expected_case:
                failure = actual_case.get('failure', {})
                if failure.get('type') != expected_case['failure_type']:
                    raise CheckError(f"{expected_case['name']}: first-failure event differs")
                if 'message' in expected_case and failure.get('message') != expected_case['message']:
                    raise CheckError(f"{expected_case['name']}: first-failure message differs")
                if 'message_contains' in expected_case and expected_case['message_contains'] not in failure.get('message', ''):
                    raise CheckError(f"{expected_case['name']}: first-failure identifying message missing")
    return actual


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('expected', type=Path)
    parser.add_argument('--suite-class', action='append', default=[])
    args = parser.parse_args()
    try:
        check(args.report, json.loads(args.expected.read_text(encoding='utf-8')), args.suite_class)
    except (OSError, ValueError, CheckError) as exc:
        print(f'FAIL: {exc}')
        raise SystemExit(1)
    print('PASS: exact suite/case inventory, terminal outcomes, counts and first failures')
