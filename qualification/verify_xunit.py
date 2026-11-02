#!/usr/bin/env python3
"""Independent host-side semantic checks for CoUnit xUnit output.

Usage:
  python verify_xunit.py report.xml [expected.json] [--require-disposition] [--require-success]

This checks the PRD-COU-03/R3 count, terminal-child, assertion-count and
failure/error-detail semantics, including the streamed failure text body. It
does not replace native CODESYS tests or prove publication currentness.
"""
from __future__ import annotations
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ALLOWED_CASE_CHILDREN = {"failure", "error", "skipped"}
COUNT_KEYS = ("tests", "failures", "errors", "skipped")
DISPOSITIONS = {"NORMAL", "ABORTED", "FRAMEWORK_ERROR"}
ULINT_MAX = 0xFFFFFFFFFFFFFFFF
ROOT_IDENTITY_ATTRIBUTES = (
    "counit-schema-version", "counit-framework-version", "counit-run-id", "counit-build-id",
    "counit-target-id", "counit-generation", "counit-clock-mode",
)
CASE_IDENTITY_ATTRIBUTES = (
    "counit-case-id", "counit-row-key", "counit-selected", "counit-started",
)

class CheckError(Exception):
    pass

def as_uint(elem: ET.Element, key: str, *, required: bool = True, maximum: int | None = None):
    raw = elem.get(key)
    if raw is None:
        if required:
            raise CheckError(f"<{elem.tag}> missing required {key!r} attribute")
        return None
    try:
        value = int(raw, 10)
    except ValueError as exc:
        raise CheckError(f"<{elem.tag}> {key!r} is not an integer: {raw!r}") from exc
    if value < 0:
        raise CheckError(f"<{elem.tag}> {key!r} must be >= 0")
    if maximum is not None and value > maximum:
        raise CheckError(f"<{elem.tag}> {key!r} must be <= {maximum}")
    return value


def bounded_string(value: str, label: str, maximum: int) -> str:
    if len(value) > maximum:
        raise CheckError(f"{label} exceeds {maximum} characters")
    return value


def root_identity(root: ET.Element) -> dict | None:
    schema_raw = root.get("counit-schema-version")
    identity_attrs = ROOT_IDENTITY_ATTRIBUTES[1:]
    if schema_raw is None:
        if any(root.get(key) is not None for key in identity_attrs):
            raise CheckError("root identity metadata requires counit-schema-version")
        return None
    schema_version = as_uint(root, "counit-schema-version", maximum=0xFFFF)
    if schema_version != 2:
        raise CheckError("counit-schema-version must be 2")
    for key in identity_attrs:
        if root.get(key) is None:
            raise CheckError(f"<testsuites> missing required {key!r} attribute")
    return {
        "schema_version": schema_version,
        "framework_version": bounded_string(root.get("counit-framework-version", ""), "framework_version", 15),
        "run_id": bounded_string(root.get("counit-run-id", ""), "run_id", 63),
        "build_id": bounded_string(root.get("counit-build-id", ""), "build_id", 64),
        "target_id": bounded_string(root.get("counit-target-id", ""), "target_id", 63),
        "generation": as_uint(root, "counit-generation", maximum=ULINT_MAX),
        "clock_mode": bounded_string(root.get("counit-clock-mode", ""), "clock_mode", 15),
    }


def xml_bool(value: str, label: str) -> bool:
    if value == "TRUE":
        return True
    if value == "FALSE":
        return False
    raise CheckError(f"{label} must be TRUE or FALSE")

def classify_case(case: ET.Element):
    if case.get("status") is not None:
        raise CheckError(f"testcase {case.get('name')!r} must not duplicate terminal state in a status attribute")
    children = [c for c in list(case) if c.tag in ALLOWED_CASE_CHILDREN]
    foreign = [c.tag for c in list(case) if c.tag not in ALLOWED_CASE_CHILDREN]
    if foreign:
        raise CheckError(f"testcase {case.get('name')!r} has unsupported child elements {foreign}")
    if len(children) > 1:
        raise CheckError(f"testcase {case.get('name')!r} has multiple terminal result children")
    child = children[0] if children else None
    if child is not None and child.tag == "failure" and list(child):
        raise CheckError(f"failure for testcase {case.get('name')!r} must contain text only")
    return (child.tag if child is not None else "passed"), child

def summarize_case(case: ET.Element, *, require_identity: bool = False) -> dict:
    kind, child = classify_case(case)
    result = {
        "classname": case.get("classname", ""),
        "name": case.get("name", ""),
        "status": kind,
    }
    assertions = as_uint(case, "assertions", required=False)
    if assertions is not None:
        result["assertions"] = assertions
    present_identity = [key for key in CASE_IDENTITY_ATTRIBUTES if case.get(key) is not None]
    if require_identity and len(present_identity) != len(CASE_IDENTITY_ATTRIBUTES):
        raise CheckError(f"testcase {case.get('name')!r} is missing identity metadata")
    if present_identity:
        if len(present_identity) != len(CASE_IDENTITY_ATTRIBUTES):
            raise CheckError(f"testcase {case.get('name')!r} has incomplete identity metadata")
        result.update({
            "case_id": bounded_string(case.get("counit-case-id", ""), "case_id", 63),
            "row_key": bounded_string(case.get("counit-row-key", ""), "row_key", 63),
            "selected": xml_bool(case.get("counit-selected", ""), "counit-selected"),
            "started": xml_bool(case.get("counit-started", ""), "counit-started"),
        })
    fixture_attrs = ('counit-fixture-cause', 'counit-cleanup-outcome', 'counit-fixture-detail', 'counit-fixture-truncated')
    if any(case.get(key) is not None for key in fixture_attrs):
        if not all(case.get(key) is not None for key in fixture_attrs):
            raise CheckError('incomplete fixture metadata')
        result['fixture'] = {
            'primary_cause': as_uint(case, 'counit-fixture-cause', maximum=4),
            'cleanup_outcome': as_uint(case, 'counit-cleanup-outcome', maximum=4),
            'detail': bounded_string(case.get('counit-fixture-detail'), 'fixture.detail', 127),
            'truncated': xml_bool(case.get('counit-fixture-truncated'), 'fixture.truncated'),
        }
    if kind == "failure":
        result["failure"] = {
            "type": child.get("type", ""),
            "message": child.get("message", ""),
            "body": child.text or "",
        }
    elif kind == "error":
        error = {"message": child.get("message", "")}
        termination_reason = child.get("termination-reason")
        if termination_reason is not None:
            error["termination_reason"] = termination_reason
        failure_type = child.get("failure-type")
        failure_message = child.get("failure-message")
        if (failure_type is None) != (failure_message is None):
            raise CheckError(f"error for testcase {case.get('name')!r} must provide both failure-type and failure-message")
        body = child.text or ""
        if failure_type is not None:
            error["first_failure"] = {
                "type": failure_type,
                "message": failure_message,
                "body": body,
            }
        result["error"] = error
    return result

def summarize_suite(suite: ET.Element, *, require_identity: bool = False) -> dict:
    foreign = [c.tag for c in list(suite) if c.tag != "testcase"]
    if foreign:
        raise CheckError(f"testsuite {suite.get('name')!r} has unsupported child elements {foreign}")
    suite_id = suite.get("counit-suite-id")
    if require_identity and suite_id is None:
        raise CheckError(f"testsuite {suite.get('name')!r} is missing counit-suite-id")
    cases = [c for c in list(suite) if c.tag == "testcase"]
    named = [summarize_case(c, require_identity=require_identity) for c in cases]
    status = {"passed": 0, "failure": 0, "error": 0, "skipped": 0}
    for case in named:
        status[case["status"]] += 1
    expected = {
        "tests": len(cases),
        "failures": status["failure"],
        "errors": status["error"],
        "skipped": status["skipped"],
    }
    declared = {k: as_uint(suite, k) for k in COUNT_KEYS}
    if declared != expected:
        raise CheckError(f"suite {suite.get('name')!r} count mismatch: declared={declared}, observed={expected}")
    result = {"name": suite.get("name", ""), **expected, "cases": named}
    identity = as_uint(suite, "id", required=False)
    if identity is not None:
        result["identity"] = identity
    if suite_id is not None:
        result["suite_id"] = bounded_string(suite_id, "suite_id", 63)
    return result

def summarize(path: Path) -> dict:
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        raise CheckError(f"XML parse failed: {exc}") from exc
    root = tree.getroot()
    if root.tag != "testsuites":
        raise CheckError(f"root must be <testsuites>, got <{root.tag}>")
    suites = [c for c in list(root) if c.tag == "testsuite"]
    foreign = [c.tag for c in list(root) if c.tag != "testsuite"]
    if foreign:
        raise CheckError(f"<testsuites> contains unsupported child elements {foreign}")
    root_meta = root_identity(root)
    summaries = [summarize_suite(s, require_identity=root_meta is not None) for s in suites]
    calculated = {
        "tests": sum(s["tests"] for s in summaries),
        "failures": sum(s["failures"] for s in summaries),
        "errors": sum(s["errors"] for s in summaries),
        "skipped": sum(s["skipped"] for s in summaries),
    }
    declared = {k: as_uint(root, k) for k in COUNT_KEYS}
    if declared != calculated:
        raise CheckError(f"root count mismatch: declared={declared}, observed={calculated}")
    result = {**calculated, "suites": summaries}
    if root_meta is not None:
        result.update(root_meta)
    disposition = root.get('counit-run-disposition')
    if disposition is not None:
        if disposition not in DISPOSITIONS:
            raise CheckError(f'unknown counit-run-disposition: {disposition!r}')
        result['run_disposition'] = disposition
    termination_reason = root.get('counit-termination-reason')
    if termination_reason is not None:
        result['termination_reason'] = termination_reason
    return result


def require_disposition(summary: dict, *, success: bool = False):
    if summary.get('run_disposition') not in DISPOSITIONS:
        raise CheckError('CoUnit 2.0 report requires counit-run-disposition')
    if success and (summary['run_disposition'] != 'NORMAL' or summary['failures'] != 0 or summary['errors'] != 0 or summary['tests'] == 0):
        raise CheckError('release-success gate requires NORMAL, nonempty inventory, zero failures and zero errors')

def main(argv: list[str]) -> int:
    allowed_flags = {'--require-disposition', '--require-success'}
    flags = {value for value in argv[1:] if value.startswith('--')}
    if not flags <= allowed_flags:
        print('unknown option', file=sys.stderr)
        return 2
    argv = [value for value in argv if value not in allowed_flags]
    if len(argv) not in (2, 3):
        print(__doc__.strip(), file=sys.stderr)
        return 2
    report = Path(argv[1])
    try:
        summary = summarize(report)
        if flags:
            require_disposition(summary, success='--require-success' in flags)
        if len(argv) == 3:
            expected = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
            if summary != expected:
                raise CheckError("semantic summary does not match expected JSON\n"
                                 f"expected={json.dumps(expected, sort_keys=True)}\n"
                                 f"actual={json.dumps(summary, sort_keys=True)}")
    except (OSError, json.JSONDecodeError, CheckError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("PASS: xUnit XML parses and count/result/detail semantics match")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
