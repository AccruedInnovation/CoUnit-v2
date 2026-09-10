#!/usr/bin/env python3
"""Independent host-side semantic checks for CoUnit xUnit output.

Usage:
  python verify_xunit.py report.xml [expected.json]

This checks the PRD-COU-03/R3 count, terminal-child, assertion-count and
failure/error-detail semantics. It does not replace native CODESYS tests or
prove publication currentness.
"""
from __future__ import annotations
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ALLOWED_CASE_CHILDREN = {"failure", "error", "skipped"}
COUNT_KEYS = ("tests", "failures", "errors", "skipped")

class CheckError(Exception):
    pass

def as_uint(elem: ET.Element, key: str, *, required: bool = True):
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
    return value

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
    return (child.tag if child is not None else "passed"), child

def summarize_case(case: ET.Element) -> dict:
    kind, child = classify_case(case)
    result = {
        "classname": case.get("classname", ""),
        "name": case.get("name", ""),
        "status": kind,
    }
    assertions = as_uint(case, "assertions", required=False)
    if assertions is not None:
        result["assertions"] = assertions
    if kind == "failure":
        result["failure"] = {
            "type": child.get("type", ""),
            "message": child.get("message", ""),
        }
    elif kind == "error":
        result["error"] = {"message": child.get("message", "")}
    return result

def summarize_suite(suite: ET.Element) -> dict:
    foreign = [c.tag for c in list(suite) if c.tag != "testcase"]
    if foreign:
        raise CheckError(f"testsuite {suite.get('name')!r} has unsupported child elements {foreign}")
    cases = [c for c in list(suite) if c.tag == "testcase"]
    named = [summarize_case(c) for c in cases]
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
    return {"name": suite.get("name", ""), **expected, "cases": named}

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
    summaries = [summarize_suite(s) for s in suites]
    calculated = {
        "tests": sum(s["tests"] for s in summaries),
        "failures": sum(s["failures"] for s in summaries),
        "errors": sum(s["errors"] for s in summaries),
        "skipped": sum(s["skipped"] for s in summaries),
    }
    declared = {k: as_uint(root, k) for k in COUNT_KEYS}
    if declared != calculated:
        raise CheckError(f"root count mismatch: declared={declared}, observed={calculated}")
    return {**calculated, "suites": summaries}

def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3):
        print(__doc__.strip(), file=sys.stderr)
        return 2
    report = Path(argv[1])
    try:
        summary = summarize(report)
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
