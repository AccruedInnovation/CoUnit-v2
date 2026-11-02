#!/usr/bin/env python3
"""Strict host-side checks for CoUnit v2 JSON diagnostic reports.

The JSON summary deliberately has the same logical shape as verify_xunit.py,
so both outputs can be compared against one exact expected snapshot.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


COUNT_KEYS = ("tests", "failures", "errors", "skipped")
DISPOSITIONS = {"NORMAL", "ABORTED", "FRAMEWORK_ERROR"}
TERMINAL_STATES = {"passed", "failure", "error", "skipped"}
ULINT_MAX = 0xFFFFFFFFFFFFFFFF
ROOT_IDENTITY_KEYS = {
    "schema_version", "framework_version", "run_id", "build_id", "target_id", "generation", "clock_mode",
}
SUITE_IDENTITY_KEYS = {"suite_id"}
CASE_IDENTITY_KEYS = {"case_id", "row_key", "selected", "started"}


class CheckError(Exception):
    pass


def _object(value, expected: set[str], label: str) -> dict:
    if type(value) is not dict:
        raise CheckError(f"{label} must be an object")
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise CheckError(f"{label} keys differ: missing={missing}, unknown={unknown}")
    return value


def _uint(value, label: str, maximum: int = 0xFFFFFFFF) -> int:
    if type(value) is not int or value < 0 or value > maximum:
        raise CheckError(f"{label} must be an unsigned integer <= {maximum}")
    return value


def _string(value, label: str) -> str:
    if type(value) is not str:
        raise CheckError(f"{label} must be a string")
    if any(0xD800 <= ord(char) <= 0xDFFF for char in value):
        raise CheckError(f"{label} contains an unpaired surrogate")
    return value


def _bounded_string(value, label: str, maximum: int) -> str:
    text = _string(value, label)
    if len(text) > maximum:
        raise CheckError(f"{label} exceeds {maximum} characters")
    return text


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CheckError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def summarize_value(document: object) -> dict:
    if type(document) is not dict:
        raise CheckError("JSON root must be an object")
    format_version = _uint(document.get("format_version"), "format_version")
    if format_version not in (1, 2):
        raise CheckError("format_version must be 1 or 2")
    root_keys = {"format_version", "run_disposition", *COUNT_KEYS, "suites"}
    if format_version == 2:
        root_keys.update(ROOT_IDENTITY_KEYS)
        if "termination_reason" in document:
            root_keys.add("termination_reason")
    root = _object(
        document,
        root_keys,
        "JSON root",
    )
    disposition = _string(root["run_disposition"], "run_disposition")
    if disposition not in DISPOSITIONS:
        raise CheckError(f"unknown run_disposition: {disposition!r}")
    declared_root = {key: _uint(root[key], f"root {key}") for key in COUNT_KEYS}
    if type(root["suites"]) is not list:
        raise CheckError("suites must be an array")

    suites = []
    observed_root = dict.fromkeys(COUNT_KEYS, 0)
    for suite_index, raw_suite in enumerate(root["suites"], 1):
        suite_keys = {"identity", "name", *COUNT_KEYS, "cases"}
        if format_version == 2:
            suite_keys.update(SUITE_IDENTITY_KEYS)
        suite = _object(
            raw_suite,
            suite_keys,
            f"suite[{suite_index}]",
        )
        identity = _uint(suite["identity"], f"suite[{suite_index}].identity", 0xFFFF)
        name = _string(suite["name"], f"suite[{suite_index}].name")
        suite_id = _bounded_string(suite["suite_id"], f"suite[{suite_index}].suite_id", 63) if format_version == 2 else None
        declared_suite = {
            key: _uint(suite[key], f"suite[{suite_index}] {key}") for key in COUNT_KEYS
        }
        if type(suite["cases"]) is not list:
            raise CheckError(f"suite[{suite_index}].cases must be an array")

        cases = []
        observed_suite = dict.fromkeys(COUNT_KEYS, 0)
        for case_index, raw_case in enumerate(suite["cases"], 1):
            label = f"suite[{suite_index}].cases[{case_index}]"
            if type(raw_case) is not dict:
                raise CheckError(f"{label} must be an object")
            state = _string(raw_case.get("status"), f"{label}.status")
            expected_case_keys = {"classname", "name", "status", "assertions"}
            if format_version == 2:
                expected_case_keys.update(CASE_IDENTITY_KEYS)
            if state == "failure":
                expected_case_keys.add("failure")
            elif state == "error":
                expected_case_keys.add("error")
            elif state not in ("passed", "skipped"):
                raise CheckError(f"{label}.status is not terminal: {state!r}")
            if format_version == 2 and 'fixture' in raw_case:
                expected_case_keys.add('fixture')
            case = _object(raw_case, expected_case_keys, label)
            classname = _string(case["classname"], f"{label}.classname")
            case_name = _string(case["name"], f"{label}.name")
            assertions = _uint(case["assertions"], f"{label}.assertions", 0xFFFF)
            result = {
                "classname": classname,
                "name": case_name,
                "status": state,
                "assertions": assertions,
            }
            if format_version == 2:
                result.update({
                    "case_id": _bounded_string(case["case_id"], f"{label}.case_id", 63),
                    "row_key": _bounded_string(case["row_key"], f"{label}.row_key", 63),
                })
                for key in ("selected", "started"):
                    if type(case[key]) is not bool:
                        raise CheckError(f"{label}.{key} must be a boolean")
                    result[key] = case[key]
            if 'fixture' in case:
                fixture = _object(case['fixture'], {'primary_cause', 'cleanup_outcome', 'detail', 'truncated'}, label + '.fixture')
                if type(fixture['truncated']) is not bool:
                    raise CheckError(label + '.fixture.truncated must be a boolean')
                result['fixture'] = {
                    'primary_cause': _uint(fixture['primary_cause'], label + '.fixture.primary_cause', 4),
                    'cleanup_outcome': _uint(fixture['cleanup_outcome'], label + '.fixture.cleanup_outcome', 4),
                    'detail': _bounded_string(fixture['detail'], label + '.fixture.detail', 127),
                    'truncated': fixture['truncated'],
                }
            observed_suite["tests"] += 1
            if state == "failure":
                failure = _object(case["failure"], {"type", "message", "expected", "actual"}, f"{label}.failure")
                failure_type = _string(failure["type"], f"{label}.failure.type")
                message = _string(failure["message"], f"{label}.failure.message")
                expected = _string(failure["expected"], f"{label}.failure.expected")
                actual = _string(failure["actual"], f"{label}.failure.actual")
                result["failure"] = {
                    "type": failure_type,
                    "message": message,
                    "body": f"Expected: {expected}\nActual: {actual}",
                }
                observed_suite["failures"] += 1
            elif state == "error":
                if format_version == 1:
                    error = _object(case["error"], {"message"}, f"{label}.error")
                else:
                    raw_error = case["error"]
                    if type(raw_error) is not dict:
                        raise CheckError(f"{label}.error must be an object")
                    allowed_error_keys = {"message", "termination_reason", "first_failure"}
                    if "message" not in raw_error or not set(raw_error) <= allowed_error_keys:
                        raise CheckError(f"{label}.error keys are invalid")
                    error = raw_error
                error_result = {"message": _string(error["message"], f"{label}.error.message")}
                if "termination_reason" in error:
                    error_result["termination_reason"] = _string(
                        error["termination_reason"], f"{label}.error.termination_reason"
                    )
                if "first_failure" in error:
                    failure = _object(
                        error["first_failure"],
                        {"type", "message", "expected", "actual"},
                        f"{label}.error.first_failure",
                    )
                    failure_type = _string(failure["type"], f"{label}.error.first_failure.type")
                    failure_message = _string(failure["message"], f"{label}.error.first_failure.message")
                    expected = _string(failure["expected"], f"{label}.error.first_failure.expected")
                    actual = _string(failure["actual"], f"{label}.error.first_failure.actual")
                    error_result["first_failure"] = {
                        "type": failure_type,
                        "message": failure_message,
                        "body": f"Expected: {expected}\nActual: {actual}",
                    }
                result["error"] = error_result
                observed_suite["errors"] += 1
            elif state == "skipped":
                observed_suite["skipped"] += 1
            cases.append(result)

        if declared_suite != observed_suite:
            raise CheckError(
                f"suite[{suite_index}] counts differ: declared={declared_suite}, observed={observed_suite}"
            )
        for key in COUNT_KEYS:
            observed_root[key] += observed_suite[key]
        suite_summary = {"name": name, **observed_suite, "cases": cases, "identity": identity}
        if format_version == 2:
            suite_summary["suite_id"] = suite_id
        suites.append(suite_summary)

    if declared_root != observed_root:
        raise CheckError(f"root counts differ: declared={declared_root}, observed={observed_root}")
    result = {**observed_root, "suites": suites, "run_disposition": disposition}
    if "termination_reason" in root:
        result["termination_reason"] = _string(root["termination_reason"], "termination_reason")
    if format_version == 2:
        schema_version = _uint(root["schema_version"], "schema_version", 0xFFFF)
        if schema_version != 2:
            raise CheckError("schema_version must be 2")
        result.update({
            "schema_version": schema_version,
            "framework_version": _bounded_string(root["framework_version"], "framework_version", 15),
            "run_id": _bounded_string(root["run_id"], "run_id", 63),
            "build_id": _bounded_string(root["build_id"], "build_id", 64),
            "target_id": _bounded_string(root["target_id"], "target_id", 63),
            "generation": _uint(root["generation"], "generation", ULINT_MAX),
            "clock_mode": _bounded_string(root["clock_mode"], "clock_mode", 15),
        })
    return result


def summarize(path: Path) -> dict:
    try:
        document = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, CheckError) as exc:
        raise CheckError(f"JSON parse failed: {exc}") from exc
    return summarize_value(document)


def require_disposition(summary: dict, *, success: bool = False):
    if summary.get("run_disposition") not in DISPOSITIONS:
        raise CheckError("CoUnit v2 JSON requires run_disposition")
    if success and (
        summary["run_disposition"] != "NORMAL"
        or summary["failures"] != 0
        or summary["errors"] != 0
        or summary["tests"] == 0
    ):
        raise CheckError("release-success gate requires NORMAL, nonempty inventory, zero failures and zero errors")


def main(argv: list[str]) -> int:
    allowed_flags = {"--require-disposition", "--require-success"}
    flags = {value for value in argv[1:] if value.startswith("--")}
    if not flags <= allowed_flags:
        print("unknown option", file=sys.stderr)
        return 2
    argv = [value for value in argv if value not in allowed_flags]
    if len(argv) not in (2, 3):
        print(__doc__.strip(), file=sys.stderr)
        return 2
    report = Path(argv[1])
    try:
        summary = summarize(report)
        if flags:
            require_disposition(summary, success="--require-success" in flags)
        if len(argv) == 3:
            expected = json.loads(Path(argv[2]).read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
            if summary != expected:
                raise CheckError(
                    "logical summary does not match expected JSON\n"
                    f"expected={json.dumps(expected, sort_keys=True)}\n"
                    f"actual={json.dumps(summary, sort_keys=True)}"
                )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, CheckError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("PASS: JSON report parses and count/result/detail semantics match")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
