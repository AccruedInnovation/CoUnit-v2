#!/usr/bin/env python3
"""Accept a completed CoUnit 2.1 run from its required xUnit artifact.

The helper validates run identity and the complete pre-execution inventory,
then classifies the observed run. It does not invoke or control a PLC.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from qualification import verify_json_report, verify_xunit


EXIT_ACCEPTED = 0
EXIT_TEST_FAILED = 1
EXIT_INVALID_REQUEST = 2
EXIT_ABORTED = 6
EXIT_FRAMEWORK_ERROR = 7
EXIT_ACCEPTANCE_ERROR = 8
IDENTITY_LIMIT = 63
BUILD_ID_LIMIT = 64
FRAMEWORK_LIMIT = 15


class InputError(ValueError):
    """The request or prepared inventory is invalid."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise InputError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _identifier(value: Any, label: str, limit: int) -> str:
    if type(value) is not str or not value.strip():
        raise InputError(f"{label} must be a non-empty string")
    if len(value) > limit:
        raise InputError(f"{label} exceeds {limit} characters")
    return value


def load_inventory(path: Path) -> list[dict[str, Any]]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, InputError) as exc:
        raise InputError(f"inventory could not be read: {exc}") from exc
    if type(document) is not dict or set(document) != {"rows"} or type(document["rows"]) is not list:
        raise InputError("inventory must be an object containing only a rows array")

    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for index, raw in enumerate(document["rows"], 1):
        label = f"inventory.rows[{index}]"
        if type(raw) is not dict or set(raw) != {"suite_id", "case_id", "row_key", "selected", "disabled"}:
            raise InputError(f"{label} must contain suite_id, case_id, row_key, selected, and disabled")
        row = {
            "suite_id": _identifier(raw["suite_id"], f"{label}.suite_id", IDENTITY_LIMIT),
            "case_id": _identifier(raw["case_id"], f"{label}.case_id", IDENTITY_LIMIT),
            "row_key": _identifier(raw["row_key"], f"{label}.row_key", IDENTITY_LIMIT),
            "selected": raw["selected"],
            "disabled": raw["disabled"],
        }
        if type(row["selected"]) is not bool or type(row["disabled"]) is not bool:
            raise InputError(f"{label}.selected and disabled must be booleans")
        key = (row["suite_id"], row["case_id"], row["row_key"])
        if key in seen:
            raise InputError(f"{label} duplicates a suite_id/case_id/row_key identity")
        seen.add(key)
        rows.append(row)
    return rows


def _request_values(run_id: Any, build_id: Any, target_id: Any, framework_version: Any) -> dict[str, str]:
    return {
        "run_id": _identifier(run_id, "run_id", IDENTITY_LIMIT),
        "build_id": _identifier(build_id, "build_id", BUILD_ID_LIMIT),
        "target_id": _identifier(target_id, "target_id", IDENTITY_LIMIT),
        "framework_version": _identifier(framework_version, "framework_version", FRAMEWORK_LIMIT),
    }


def _metadata_errors(summary: dict[str, Any], expected: dict[str, str], label: str) -> list[str]:
    errors: list[str] = []
    if summary.get("schema_version") != 2:
        errors.append(f"{label} must carry schema_version 2")
    for key in ("run_id", "build_id", "target_id", "framework_version"):
        if summary.get(key) != expected[key]:
            errors.append(f"{label} {key} does not match the requested run")
    if summary.get("clock_mode") != "MONOTONIC":
        errors.append(f"{label} clock_mode must be MONOTONIC")
    if type(summary.get("generation")) is not int or summary["generation"] < 1:
        errors.append(f"{label} generation must be a positive integer")
    if summary.get("run_disposition") not in {"NORMAL", "ABORTED", "FRAMEWORK_ERROR"}:
        errors.append(f"{label} is missing a valid run disposition")
    return errors


def _key(suite_id: str, case_id: str, row_key: str) -> tuple[str, str, str]:
    return suite_id, case_id, row_key


def _inventory_errors(
    summary: dict[str, Any], rows: list[dict[str, Any]], *, allow_incomplete_run: bool
) -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    expected = {
        _key(row["suite_id"], row["case_id"], row["row_key"]): row
        for row in rows
    }
    actual: dict[tuple[str, str, str], dict[str, Any]] = {}
    actual_suite_ids: set[str] = set()
    for suite_index, suite in enumerate(summary.get("suites", []), 1):
        suite_id = suite.get("suite_id")
        if type(suite_id) is not str or not suite_id.strip():
            errors.append(f"report suite[{suite_index}] has no usable suite_id")
            continue
        actual_suite_ids.add(suite_id)
        for case_index, case in enumerate(suite.get("cases", []), 1):
            case_id, row_key = case.get("case_id"), case.get("row_key")
            if type(case_id) is not str or not case_id.strip() or type(row_key) is not str or not row_key.strip():
                errors.append(f"report suite[{suite_index}] case[{case_index}] has no usable identity")
                continue
            key = _key(suite_id, case_id, row_key)
            if key in actual:
                errors.append(f"report duplicates case identity {key!r}")
            else:
                actual[key] = case

    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    if missing:
        errors.append(f"report is missing {len(missing)} frozen inventory row(s): {missing[:5]!r}")
    if extra:
        errors.append(f"report contains {len(extra)} row(s) outside the frozen inventory: {extra[:5]!r}")
    expected_suites = {row["suite_id"] for row in rows}
    if actual_suite_ids != expected_suites:
        errors.append("report suite_id set does not match the frozen inventory")

    selected = sum(row["selected"] for row in rows)
    disabled = sum(row["disabled"] for row in rows)
    excluded = sum(not row["selected"] for row in rows)
    started = 0
    unstarted = 0
    for key in set(expected) & set(actual):
        row, case = expected[key], actual[key]
        if case.get("selected") is not row["selected"]:
            errors.append(f"report selection differs for case identity {key!r}")
            continue
        is_started = case.get("started")
        status = case.get("status")
        if type(is_started) is not bool:
            errors.append(f"report started flag is invalid for case identity {key!r}")
            continue
        if not row["selected"] or row["disabled"]:
            if status != "skipped" or is_started:
                errors.append(f"excluded/disabled row is not skipped and unstarted: {key!r}")
            continue
        fixture = case.get("fixture")
        if fixture is not None:
            if type(fixture) is not dict:
                errors.append(f"fixture summary is invalid for selected case {key!r}")
            else:
                primary_cause = fixture.get("primary_cause")
                cleanup_outcome = fixture.get("cleanup_outcome")
                if type(primary_cause) is not int or primary_cause not in range(5):
                    errors.append(f"fixture primary cause is invalid for selected case {key!r}")
                elif primary_cause != 0 and not allow_incomplete_run:
                    errors.append(f"fixture primary cause is nonzero for selected case {key!r}")
                if type(cleanup_outcome) is not int or cleanup_outcome not in range(5):
                    errors.append(f"fixture cleanup outcome is invalid for selected case {key!r}")
                elif cleanup_outcome in {1, 3, 4}:
                    errors.append(f"fixture cleanup is pending, failed, or incomplete for selected case {key!r}")
        if not is_started:
            unstarted += 1
            setup_error = (
                summary.get("run_disposition") == "FRAMEWORK_ERROR"
                and status == "error" and case.get("assertions") == 0
                and bool(summary.get("termination_reason"))
                and case.get("error", {}).get("termination_reason") == summary["termination_reason"]
            )
            if status != "skipped" and not setup_error:
                errors.append(f"selected unstarted row is not reported as skipped: {key!r}")
            elif not allow_incomplete_run:
                errors.append(f"selected row was not started in a NORMAL run: {key!r}")
            continue
        started += 1
        if status == "skipped":
            errors.append(f"selected active row was skipped: {key!r}")
        elif status not in {"passed", "failure", "error"}:
            errors.append(f"selected active row has an invalid terminal state: {key!r}")

    return errors, {
        "rows": len(rows),
        "selected": selected,
        "excluded": excluded,
        "disabled": disabled,
        "started": started,
        "unstarted": unstarted,
    }


def _observed(summary: dict[str, Any], report_format: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    details: dict[str, list[dict[str, Any]]] = {"failures": [], "errors": [], "fixture_issues": []}
    expected = {_key(row["suite_id"], row["case_id"], row["row_key"]): row for row in rows}
    for suite in summary.get("suites", []):
        for case in suite.get("cases", []):
            state = case.get("status")
            item = {
                "suite_id": suite.get("suite_id"),
                "case_id": case.get("case_id"),
                "row_key": case.get("row_key"),
                "classname": case.get("classname", ""),
                "name": case.get("name", ""),
            }
            if state in {"failure", "error"}:
                item["detail"] = case.get("failure" if state == "failure" else "error", {})
                if "fixture" in case:
                    item["fixture"] = case["fixture"]
                details["failures" if state == "failure" else "errors"].append(item)
            fixture = case.get("fixture")
            row_key = case.get("row_key")
            identity = _key(suite.get("suite_id", ""), case.get("case_id", ""), row_key if type(row_key) is str else "")
            expected_row = expected.get(identity)
            if expected_row is not None and expected_row["selected"] and not expected_row["disabled"] and fixture is not None:
                invalid_fixture = (
                    type(fixture) is not dict
                    or type(fixture.get("primary_cause")) is not int
                    or fixture.get("primary_cause") != 0
                    or type(fixture.get("cleanup_outcome")) is not int
                    or fixture.get("cleanup_outcome") in {1, 3, 4}
                )
                if invalid_fixture:
                    details["fixture_issues"].append({**item, "fixture": fixture})
    root_keys = (
        "schema_version", "framework_version", "run_id", "build_id", "target_id", "generation", "clock_mode",
        "run_disposition", "termination_reason", "tests", "failures", "errors", "skipped",
    )
    return {
        "format": report_format,
        "run": {key: summary[key] for key in root_keys if key in summary},
        **details,
    }


def _result(classification: str, exit_code: int, reason: str, **extra: Any) -> dict[str, Any]:
    return {"classification": classification, "exit_code": exit_code, "reason": reason, **extra}


def accept_run(
    *,
    xml_path: Path,
    inventory_path: Path,
    run_id: str,
    build_id: str,
    target_id: str,
    framework_version: str = "2.1.0.1",
    json_path: Path | None = None,
    allow_empty: bool = False,
    allow_all_skipped: bool = False,
) -> dict[str, Any]:
    capture: dict[str, str] = {"xml": "pending", "json": "not_requested" if json_path is None else "pending"}
    observed: list[dict[str, Any]] = []
    acceptance_errors: list[str] = []
    try:
        expected_ids = _request_values(run_id, build_id, target_id, framework_version)
        rows = load_inventory(inventory_path)
    except InputError as exc:
        return _result("invalid_request", EXIT_INVALID_REQUEST, str(exc), capture=capture, observed=observed)

    summaries: dict[str, dict[str, Any]] = {}
    try:
        summaries["xml"] = verify_xunit.summarize(xml_path)
        capture["xml"] = "present"
        observed.append(_observed(summaries["xml"], "xml", rows))
    except (OSError, verify_xunit.CheckError) as exc:
        capture["xml"] = "failed"
        acceptance_errors.append(f"xUnit capture failed: {exc}")

    if json_path is not None:
        try:
            summaries["json"] = verify_json_report.summarize(json_path)
            capture["json"] = "present"
            observed.append(_observed(summaries["json"], "json", rows))
        except (OSError, verify_json_report.CheckError) as exc:
            capture["json"] = "failed"
            acceptance_errors.append(f"JSON capture failed: {exc}")

    inventory_counts: dict[str, int] | None = None
    for report_format, summary in summaries.items():
        acceptance_errors.extend(_metadata_errors(summary, expected_ids, report_format))
        inventory_run_incomplete = summary.get("run_disposition") in {"ABORTED", "FRAMEWORK_ERROR"}
        inventory_errors, counts = _inventory_errors(summary, rows, allow_incomplete_run=inventory_run_incomplete)
        acceptance_errors.extend(f"{report_format}: {error}" for error in inventory_errors)
        if report_format == "xml":
            inventory_counts = counts
    if "xml" in summaries and "json" in summaries and summaries["xml"] != summaries["json"]:
        acceptance_errors.append("XML and JSON semantic summaries differ")

    if acceptance_errors:
        return _result(
            "report_error", EXIT_ACCEPTANCE_ERROR, acceptance_errors[0],
            capture=capture, inventory=inventory_counts, observed=observed, acceptance_errors=acceptance_errors,
        )

    summary = summaries["xml"]
    disposition = summary["run_disposition"]
    if disposition == "ABORTED":
        return _result(
            "aborted", EXIT_ABORTED, "run disposition is ABORTED",
            capture=capture, inventory=inventory_counts, observed=observed,
        )
    if disposition == "FRAMEWORK_ERROR":
        return _result(
            "framework_error", EXIT_FRAMEWORK_ERROR, "run disposition is FRAMEWORK_ERROR",
            capture=capture, inventory=inventory_counts, observed=observed,
        )
    if summary["failures"]:
        return _result(
            "test_failed", EXIT_TEST_FAILED, "one or more assertion failures were reported",
            capture=capture, inventory=inventory_counts, observed=observed,
        )
    if summary["errors"]:
        return _result(
            "report_error", EXIT_ACCEPTANCE_ERROR, "NORMAL run contains testcase errors",
            capture=capture, inventory=inventory_counts, observed=observed,
            acceptance_errors=["NORMAL run contains testcase errors"],
        )
    assert inventory_counts is not None
    if inventory_counts["rows"] == 0 and not allow_empty:
        return _result(
            "report_error", EXIT_ACCEPTANCE_ERROR, "empty inventory requires --allow-empty",
            capture=capture, inventory=inventory_counts, observed=observed,
            acceptance_errors=["empty inventory requires --allow-empty"],
        )
    active_expected = sum(row["selected"] and not row["disabled"] for row in rows)
    if inventory_counts["rows"] > 0 and active_expected == 0 and not allow_all_skipped:
        return _result(
            "report_error", EXIT_ACCEPTANCE_ERROR, "all-skipped inventory requires --allow-all-skipped",
            capture=capture, inventory=inventory_counts, observed=observed,
            acceptance_errors=["all-skipped inventory requires --allow-all-skipped"],
        )
    return _result(
        "accepted", EXIT_ACCEPTED, "NORMAL run matches the frozen inventory",
        capture=capture, inventory=inventory_counts, observed=observed,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Accept a completed CoUnit run from published reports.")
    parser.add_argument("--xml", required=True, type=Path, help="required current xUnit report")
    parser.add_argument("--json", dest="json_path", type=Path, help="required current JSON report when requested")
    parser.add_argument("--inventory", required=True, type=Path, help="pre-execution frozen inventory JSON")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--build-id", required=True)
    parser.add_argument("--target-id", required=True)
    parser.add_argument("--framework-version", default="2.1.0.1")
    parser.add_argument("--allow-empty", action="store_true", help="explicitly accept a NORMAL empty inventory")
    parser.add_argument("--allow-all-skipped", action="store_true", help="explicitly accept a NORMAL nonempty all-skipped inventory")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)
    result = accept_run(
        xml_path=args.xml,
        json_path=args.json_path,
        inventory_path=args.inventory,
        run_id=args.run_id,
        build_id=args.build_id,
        target_id=args.target_id,
        framework_version=args.framework_version,
        allow_empty=args.allow_empty,
        allow_all_skipped=args.allow_all_skipped,
    )
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return result["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
