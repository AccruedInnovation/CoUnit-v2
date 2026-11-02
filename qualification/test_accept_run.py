"""Behavioral acceptance checks using the strict shipped XML/JSON parsers."""
from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
import xml.sax.saxutils as sax
from pathlib import Path

from tools import accept_run


IDS = {
    "schema_version": 2,
    "framework_version": "2.1.0.1",
    "run_id": "run-current",
    "build_id": "build-current",
    "target_id": "target-current",
    "generation": 1,
    "clock_mode": "MONOTONIC",
}


def _xml_attr(value: str) -> str:
    return sax.escape(value, {'"': "&quot;", "'": "&apos;"})


def _case(row_key: str, *, status: str = "passed", selected: bool = True, started: bool = True,
          fixture: dict | None = None) -> dict:
    case = {
        "classname": "Same display suite",
        "name": "Same display name",
        "case_id": "same-case-id",
        "row_key": row_key,
        "status": status,
        "assertions": 1,
        "selected": selected,
        "started": started,
    }
    if status == "failure":
        case["failure"] = {
            "type": "Type_BOOL",
            "message": "deliberate assertion failure",
            "expected": "TRUE",
            "actual": "FALSE",
        }
    elif status == "error":
        case["error"] = {"message": "unexpected test error"}
    if fixture is not None:
        case["fixture"] = fixture
    return case


def _counts(cases: list[dict]) -> dict[str, int]:
    return {
        "tests": len(cases),
        "failures": sum(case["status"] == "failure" for case in cases),
        "errors": sum(case["status"] == "error" for case in cases),
        "skipped": sum(case["status"] == "skipped" for case in cases),
    }


def _reports(directory: Path, cases: list[dict], *, disposition: str = "NORMAL", metadata: dict | None = None,
             root_reason: str | None = None) -> tuple[Path, Path]:
    identity = {**IDS, **(metadata or {})}
    counts = _counts(cases)
    suite = {
        "identity": 3,
        "name": "Same display suite",
        "suite_id": "suite-id",
        **counts,
        "cases": cases,
    }
    json_document = {
        "format_version": 2,
        **identity,
        "run_disposition": disposition,
        **counts,
        "suites": [suite] if cases else [],
    }
    xml_identity = (
        f'counit-schema-version="{identity["schema_version"]}" '
        f'counit-framework-version="{_xml_attr(identity["framework_version"])}" '
        f'counit-run-id="{_xml_attr(identity["run_id"])}" '
        f'counit-build-id="{_xml_attr(identity["build_id"])}" '
        f'counit-target-id="{_xml_attr(identity["target_id"])}" '
        f'counit-generation="{identity["generation"]}" '
        f'counit-clock-mode="{_xml_attr(identity["clock_mode"])}"'
    )
    root_reason_xml = f' counit-termination-reason="{_xml_attr(root_reason)}"' if root_reason is not None else ""
    root_reason_json = {"termination_reason": root_reason} if root_reason is not None else {}
    json_document.update(root_reason_json)
    xml_parts = [
        f'<testsuites tests="{counts["tests"]}" failures="{counts["failures"]}" '
        f'errors="{counts["errors"]}" skipped="{counts["skipped"]}" '
        f'counit-run-disposition="{disposition}"{root_reason_xml} {xml_identity}>'
    ]
    if cases:
        xml_parts.append(
            f'<testsuite id="3" name="Same display suite" counit-suite-id="suite-id" '
            f'tests="{counts["tests"]}" failures="{counts["failures"]}" '
            f'errors="{counts["errors"]}" skipped="{counts["skipped"]}">'
        )
        for case in cases:
            fixture = case.get("fixture")
            fixture_xml = ""
            if fixture is not None:
                fixture_xml = (
                    f' counit-fixture-cause="{fixture["primary_cause"]}"'
                    f' counit-cleanup-outcome="{fixture["cleanup_outcome"]}"'
                    f' counit-fixture-detail="{_xml_attr(fixture["detail"])}"'
                    f' counit-fixture-truncated="{"TRUE" if fixture["truncated"] else "FALSE"}"'
                )
            xml_parts.append(
                f'<testcase classname="{_xml_attr(case["classname"])}" name="{_xml_attr(case["name"])}" '
                f'counit-case-id="{_xml_attr(case["case_id"])}" counit-row-key="{_xml_attr(case["row_key"])}" '
                f'counit-selected="{"TRUE" if case["selected"] else "FALSE"}" '
                f'counit-started="{"TRUE" if case["started"] else "FALSE"}" assertions="{case["assertions"]}"'
                f'{fixture_xml}>'
            )
            if case["status"] == "failure":
                failure = case["failure"]
                body = f'Expected: {failure["expected"]}\nActual: {failure["actual"]}'
                xml_parts.append(
                    f'<failure type="{_xml_attr(failure["type"])}" message="{_xml_attr(failure["message"])}">'
                    f'{sax.escape(body)}</failure>'
                )
            elif case["status"] == "error":
                reason = case["error"].get("termination_reason")
                reason_xml = f' termination-reason="{_xml_attr(reason)}"' if reason is not None else ""
                xml_parts.append(f'<error message="{_xml_attr(case["error"]["message"])}"{reason_xml}/>')
            elif case["status"] == "skipped":
                xml_parts.append("<skipped/>")
            xml_parts.append("</testcase>")
        xml_parts.append("</testsuite>")
    xml_parts.append("</testsuites>")
    xml_path = directory / "report.xml"
    json_path = directory / "report.json"
    xml_path.write_text("".join(xml_parts), encoding="utf-8")
    json_path.write_text(json.dumps(json_document, ensure_ascii=False), encoding="utf-8")
    return xml_path, json_path


def _inventory(directory: Path, rows: list[dict] | None = None) -> Path:
    path = directory / "inventory.json"
    path.write_text(json.dumps({"rows": rows or []}, ensure_ascii=False), encoding="utf-8")
    return path


def _accept(directory: Path, xml_path: Path, json_path: Path | None, rows: list[dict], **options) -> dict:
    return accept_run.accept_run(
        xml_path=xml_path,
        json_path=json_path,
        inventory_path=_inventory(directory, rows),
        run_id=IDS["run_id"],
        build_id=IDS["build_id"],
        target_id=IDS["target_id"],
        **options,
    )


def _row(row_key: str, *, selected: bool = True, disabled: bool = False) -> dict:
    return {
        "suite_id": "suite-id",
        "case_id": "same-case-id",
        "row_key": row_key,
        "selected": selected,
        "disabled": disabled,
    }


class AcceptRunTests(unittest.TestCase):
    def test_prestart_framework_error_keeps_its_classification_with_complete_inventory(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            reason = "Duplicate stable case and parameter row"
            case = _case("row-a", status="error", started=False)
            case["assertions"] = 0
            case["error"]["termination_reason"] = reason
            xml_path, json_path = _reports(directory, [case], disposition="FRAMEWORK_ERROR", root_reason=reason)
            result = _accept(directory, xml_path, json_path, [_row("row-a")])
            self.assertEqual(result["classification"], "framework_error")
            self.assertEqual(result["exit_code"], 7)
            self.assertEqual(result["inventory"]["unstarted"], 1)
            for disposition, root_reason, assertions in (
                    ("NORMAL", reason, 0), ("ABORTED", reason, 0),
                    ("FRAMEWORK_ERROR", "different root cause", 0),
                    ("FRAMEWORK_ERROR", None, 0), ("FRAMEWORK_ERROR", reason, 1)):
                with self.subTest(disposition=disposition, root_reason=root_reason, assertions=assertions):
                    case["assertions"] = assertions
                    xml_path, json_path = _reports(directory, [case], disposition=disposition, root_reason=root_reason)
                    result = _accept(directory, xml_path, json_path, [_row("row-a")])
                    self.assertEqual(result["exit_code"], 8)

    def test_accepts_schema2_reports_against_distinct_row_keys_with_same_display_name(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            xml_path, json_path = _reports(directory, [_case("row-a"), _case("row-b")])
            result = _accept(directory, xml_path, json_path, [_row("row-a"), _row("row-b")])
            self.assertEqual(result["exit_code"], 0)
            self.assertEqual(result["inventory"]["started"], 2)
            self.assertEqual(result["observed"][0]["run"]["run_id"], IDS["run_id"])

    def test_wrong_run_build_target_and_inventory_are_acceptance_errors(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            rows = [_row("row-a")]
            for key, wrong in (
                ("run_id", "stale-run"),
                ("build_id", "other-build"),
                ("target_id", "other-target"),
                ("framework_version", "2.0.1.0"),
                ("clock_mode", "SYSTEM"),
            ):
                with self.subTest(identity=key):
                    xml_path, json_path = _reports(directory, [_case("row-a")], metadata={key: wrong})
                    result = _accept(directory, xml_path, json_path, rows)
                    self.assertEqual(result["exit_code"], 8)
                    self.assertTrue(any(key in error for error in result["acceptance_errors"]))

            xml_path, json_path = _reports(directory, [_case("extra-row")])
            result = _accept(directory, xml_path, json_path, rows)
            self.assertEqual(result["exit_code"], 8)
            self.assertTrue(any("missing" in error or "outside" in error for error in result["acceptance_errors"]))

    def test_64_character_build_id_matches_report_parser_bound(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            build_id = "b" * 64
            xml_path, json_path = _reports(directory, [_case("row-a")], metadata={"build_id": build_id})
            result = accept_run.accept_run(
                xml_path=xml_path,
                json_path=json_path,
                inventory_path=_inventory(directory, [_row("row-a")]),
                run_id=IDS["run_id"],
                build_id=build_id,
                target_id=IDS["target_id"],
            )
            self.assertEqual(result["exit_code"], 0)

    def test_stale_json_fails_but_keeps_xml_failure_details(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            xml_path, json_path = _reports(directory, [_case("row-a", status="failure")])
            document = json.loads(json_path.read_text(encoding="utf-8"))
            document["run_id"] = "previous-run"
            json_path.write_text(json.dumps(document), encoding="utf-8")
            result = _accept(directory, xml_path, json_path, [_row("row-a")])
            self.assertEqual(result["exit_code"], 8)
            self.assertEqual(result["observed"][0]["failures"][0]["detail"], {
                "type": "Type_BOOL",
                "message": "deliberate assertion failure",
                "body": "Expected: TRUE\nActual: FALSE",
            })

    def test_late_framework_error_with_all_cases_passed_is_exit_seven_without_synthetic_counts(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            reason = "late failure after final case closure"
            xml_path, json_path = _reports(directory, [_case("row-a")], disposition="FRAMEWORK_ERROR", root_reason=reason)
            result = _accept(directory, xml_path, json_path, [_row("row-a")])
            self.assertEqual(result["exit_code"], 7)
            self.assertEqual(result["observed"][0]["run"]["tests"], 1)
            self.assertEqual(result["observed"][0]["run"]["errors"], 0)
            self.assertEqual(result["observed"][0]["run"]["termination_reason"], reason)

    def test_cancelled_fixture_before_first_assertion_is_aborted_and_retains_cleanup(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            fixture = {"primary_cause": 3, "cleanup_outcome": 2,
                       "detail": "cancel cleanup released resource", "truncated": False}
            case = _case("row-a", status="error", fixture=fixture)
            case["assertions"] = 0
            xml_path, json_path = _reports(directory, [case], disposition="ABORTED")
            result = _accept(directory, xml_path, json_path, [_row("row-a")])
            self.assertEqual(result["classification"], "aborted")
            self.assertEqual(result["exit_code"], 6)
            self.assertTrue(result["observed"][0]["fixture_issues"])

    def test_empty_and_nonempty_all_skipped_require_explicit_policy(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            xml_path, json_path = _reports(directory, [])
            result = _accept(directory, xml_path, json_path, [])
            self.assertEqual(result["exit_code"], 8)
            result = _accept(directory, xml_path, json_path, [], allow_empty=True)
            self.assertEqual(result["exit_code"], 0)

            cases = [
                _case("excluded", status="skipped", selected=False, started=False),
                _case("disabled", status="skipped", selected=True, started=False),
            ]
            xml_path, json_path = _reports(directory, cases)
            rows = [_row("excluded", selected=False), _row("disabled", disabled=True)]
            result = _accept(directory, xml_path, json_path, rows)
            self.assertEqual(result["exit_code"], 8)
            result = _accept(directory, xml_path, json_path, rows, allow_all_skipped=True)
            self.assertEqual(result["exit_code"], 0)
            self.assertEqual(result["inventory"]["excluded"], 1)
            self.assertEqual(result["inventory"]["disabled"], 1)

    def test_selected_enabled_case_is_not_all_skipped_when_disabled_row_is_excluded(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            cases = [
                _case("active"),
                _case("excluded-disabled", status="skipped", selected=False, started=False),
            ]
            rows = [
                _row("active"),
                _row("excluded-disabled", selected=False, disabled=True),
            ]
            xml_path, json_path = _reports(directory, cases)
            result = _accept(directory, xml_path, json_path, rows)
            self.assertEqual(result["exit_code"], 0)
            self.assertEqual(result["classification"], "accepted")
            self.assertEqual(result["inventory"]["selected"], 1)
            self.assertEqual(result["inventory"]["disabled"], 1)
            self.assertEqual(result["inventory"]["excluded"], 1)

            xml_path, json_path = _reports(
                directory,
                [_case("excluded-disabled", status="skipped", selected=False, started=False)],
            )
            no_active_rows = [_row("excluded-disabled", selected=False, disabled=True)]
            result = _accept(directory, xml_path, json_path, no_active_rows)
            self.assertEqual(result["exit_code"], 8)
            self.assertEqual(result["classification"], "report_error")
            result = _accept(directory, xml_path, json_path, no_active_rows, allow_all_skipped=True)
            self.assertEqual(result["exit_code"], 0)

    def test_normal_selected_unstarted_is_acceptance_error_but_abort_is_classified(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            unstarted = _case("row-a", status="skipped", started=False)
            xml_path, json_path = _reports(directory, [unstarted])
            result = _accept(directory, xml_path, json_path, [_row("row-a")])
            self.assertEqual(result["exit_code"], 8)
            self.assertTrue(any("not started" in error for error in result["acceptance_errors"]))

            xml_path, json_path = _reports(directory, [unstarted], disposition="ABORTED")
            result = _accept(directory, xml_path, json_path, [_row("row-a")])
            self.assertEqual(result["exit_code"], 6)
            self.assertEqual(result["inventory"]["unstarted"], 1)

    def test_normal_assertion_failure_is_exit_one_with_original_detail(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            xml_path, json_path = _reports(directory, [_case("row-a", status="failure")])
            result = _accept(directory, xml_path, json_path, [_row("row-a")])
            self.assertEqual(result["exit_code"], 1)
            self.assertEqual(result["classification"], "test_failed")
            self.assertEqual(result["observed"][0]["failures"][0]["detail"]["message"], "deliberate assertion failure")

    def test_selected_fixture_failures_and_uncertain_cleanup_reject_normal_run(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            bad_fixtures = (
                {"primary_cause": 1, "cleanup_outcome": 0, "detail": "setup failed", "truncated": False},
                {"primary_cause": 0, "cleanup_outcome": 1, "detail": "still pending", "truncated": False},
                {"primary_cause": 0, "cleanup_outcome": 3, "detail": "cleanup failed", "truncated": False},
                {"primary_cause": 0, "cleanup_outcome": 4, "detail": "cleanup incomplete", "truncated": False},
            )
            for fixture in bad_fixtures:
                with self.subTest(fixture=fixture):
                    xml_path, json_path = _reports(directory, [_case("row-a", fixture=fixture)])
                    result = _accept(directory, xml_path, json_path, [_row("row-a")])
                    self.assertEqual(result["exit_code"], 8)
                    self.assertTrue(result["observed"][0]["fixture_issues"])

            not_run_is_valid_for_a_pure_test = {
                "primary_cause": 0,
                "cleanup_outcome": 0,
                "detail": "",
                "truncated": False,
            }
            xml_path, json_path = _reports(directory, [_case("row-a", fixture=not_run_is_valid_for_a_pure_test)])
            result = _accept(directory, xml_path, json_path, [_row("row-a")])
            self.assertEqual(result["exit_code"], 0)

    def test_disabled_and_excluded_rows_do_not_fail_acceptance_on_fixture_outcomes(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            fixture_failure = {"primary_cause": 1, "cleanup_outcome": 4, "detail": "ignored row", "truncated": False}
            cases = [
                _case("excluded", status="skipped", selected=False, started=False, fixture=fixture_failure),
                _case("disabled", status="skipped", selected=True, started=False, fixture=fixture_failure),
                _case("excluded-disabled", status="skipped", selected=False, started=False, fixture=fixture_failure),
            ]
            xml_path, json_path = _reports(directory, cases)
            rows = [_row("excluded", selected=False), _row("disabled", disabled=True), _row("excluded-disabled", selected=False, disabled=True)]
            result = _accept(directory, xml_path, json_path, rows, allow_all_skipped=True)
            self.assertEqual(result["exit_code"], 0)

    def test_missing_requested_json_is_exit_eight_and_preserves_prior_xml_capture(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            xml_path, _ = _reports(directory, [_case("row-a", status="failure")])
            missing_json = directory / "not-published.json"
            result = _accept(directory, xml_path, missing_json, [_row("row-a")])
            self.assertEqual(result["exit_code"], 8)
            self.assertEqual(result["capture"]["json"], "failed")
            self.assertEqual(result["observed"][0]["failures"][0]["detail"]["type"], "Type_BOOL")

    def test_invalid_inventory_is_exit_two(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            xml_path, json_path = _reports(directory, [_case("row-a")])
            inventory_path = directory / "inventory.json"
            inventory_path.write_text('{"rows":[{"suite_id":"s","case_id":"c","row_key":"r","selected":"false","disabled":true}]}', encoding="utf-8")
            result = accept_run.accept_run(
                xml_path=xml_path,
                json_path=json_path,
                inventory_path=inventory_path,
                run_id=IDS["run_id"],
                build_id=IDS["build_id"],
                target_id=IDS["target_id"],
            )
            self.assertEqual(result["exit_code"], 2)
            self.assertEqual(result["classification"], "invalid_request")

    def test_cli_emits_one_compact_json_summary(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            xml_path, json_path = _reports(directory, [_case("row-a")])
            inventory_path = _inventory(directory, [_row("row-a")])
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                exit_code = accept_run.main([
                    "--xml", str(xml_path), "--json", str(json_path), "--inventory", str(inventory_path),
                    "--run-id", IDS["run_id"], "--build-id", IDS["build_id"], "--target-id", IDS["target_id"],
                ])
            self.assertEqual(exit_code, 0)
            parsed = json.loads(output.getvalue())
            self.assertEqual(parsed["classification"], "accepted")
            self.assertNotIn("\n", output.getvalue().strip())


if __name__ == "__main__":
    unittest.main()
