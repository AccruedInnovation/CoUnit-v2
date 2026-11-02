"""Offline checks for selected and bounded qualification source generation."""
import shutil
import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from tools import controlled_boot as boot
from tools import run_selected as selected
from qualification import upgrade_native_consumers as budget_fixtures


def catalog():
    return {"suite_id": "upgrade", "cases": [
        {"case_id": "row", "row_key": "a", "tags": "small|fast", "disabled": False},
        {"case_id": "row", "row_key": "b", "tags": "large", "disabled": False},
        {"case_id": "row", "row_key": "off", "tags": "small", "disabled": True},
    ]}


class ControlledSelectionTests(unittest.TestCase):
    def test_budget_fixture_describe_timer_preserves_all_catalog_rows(self):
        suites = budget_fixtures._budget_objects()
        self.assertEqual([suite.name for suite in suites], [
            "FB_UpgradeBudgetSmall16", "FB_UpgradeBudgetLarge2048", "FB_UpgradeBudgetOverCapacity17"])
        large = suites[1]
        describe = next(member for member in large.members if member.name == "Describe")
        rows = [line for line in describe.implementation.splitlines() if "DefineCase(" in line]
        self.assertEqual(len(rows), 2048)
        self.assertEqual(rows[0], "_handles[1] := DefineCase(CaseId := 'budget', Name := 'Budget0001', RowKey := 'row0001', Tags := 'upgrade|budget', Disabled := FALSE);")
        self.assertEqual(rows[-1], "_handles[2048] := DefineCase(CaseId := 'budget', Name := 'Budget2048', RowKey := 'row2048', Tags := 'upgrade|budget', Disabled := FALSE);")
        self.assertTrue(describe.implementation.startswith("_describeStarted := LTIME();\n"))
        self.assertTrue(describe.implementation.endswith("DescribeNanoseconds := TO_ULINT(LTIME() - _describeStarted);"))
        self.assertIn("DescribeNanoseconds : ULINT;", large.declaration)

    def test_incremental_budget_inventory_matches_literal_legacy_inventory(self):
        for suite in budget_fixtures._budget_objects():
            describe = next(member for member in suite.members if member.name == "Describe")
            incremental = next(member for member in suite.members if member.name == "DescribeNext")
            self.assertEqual(boot.extract_catalog(incremental.implementation),
                             boot.extract_catalog(describe.implementation))

    def test_all_cases_and_strict_inventory_preserve_disabled_rows(self):
        rows = boot.select_catalog_rows(catalog(), all_cases=True, tag="small")
        self.assertEqual([row["row_key"] for row in rows], ["a", "off"])
        inventory = boot.strict_inventory(catalog(), all_cases=True, tag="small")
        self.assertEqual([row["selected"] for row in inventory["rows"]], [True, False, True])
        self.assertEqual([row["disabled"] for row in inventory["rows"]], [False, False, True])
        self.assertEqual(sum(row["selected"] and not row["disabled"] for row in inventory["rows"]), 1)

    def test_all_cases_rejects_mixed_identity_and_empty_selection(self):
        with self.assertRaises(ValueError):
            boot.select_catalog_rows(catalog(), all_cases=True, case_id="row")
        with self.assertRaises(ValueError):
            boot.select_catalog_rows(catalog(), all_cases=True, tag="missing")

    def test_plain_runner_has_no_qualification_only_branch(self):
        source = boot._render_controlled_program(
            suite_id="upgrade", case_id="row", row_key="a", tag="",
            target_profile=boot.TARGET_PROFILE)
        self.assertEqual(source.count("CoUnit.RUN_CONTROLLED("), 1)
        self.assertIn("IF Exchange.Status.ExecutionComplete THEN bTestComplete := TRUE; END_IF", source)
        self.assertNotIn("Qualification :=", source)
        self.assertNotIn("GVL_CoUnitReporting.RecordsPerScan", source)

    def test_qualification_runner_measures_every_run_and_refreshes_output(self):
        source = boot._render_controlled_program(
            suite_id="upgrade", case_id="", row_key="", tag="",
            target_profile=boot.TARGET_PROFILE, expected_selected=16,
            target_suite="FB_UpgradeBudgetSmall16", suite_instance="fbUpgradeBudgetSmall16",
            qualification_budget=True)
        self.assertEqual(source.count("CoUnit.RUN_CONTROLLED("), 1)
        self.assertIn("GVL_CoUnitReporting.RecordsPerScan := 1", source)
        self.assertIn("CaseId := '';", source)
        self.assertIn("RowKey := '';", source)
        self.assertIn("_calls[_priorState] := _calls[_priorState] + 1", source)
        self.assertIn("Qualification := CONCAT(Qualification", source)
        self.assertNotIn("_qualificationFormatted", source)
        self.assertIn("Qualification := CONCAT(Qualification, ',\"records_per_scan\":1}');", source)
        self.assertTrue(source.rstrip().endswith("QualificationDiagnostic := CONCAT(QualificationDiagnostic, '}');"))
        self.assertIn("_diagOperation := TO_USINT(Exchange.Operation)", source)
        self.assertIn("_diagElapsed > _diagNs[_diagOperation]", source)
        self.assertIn("_diagNs[_diagOperation] := _diagElapsed", source)
        self.assertIn("fbUpgradeBudgetSmall16.DescribeNanoseconds", source)
        diag = {"configure_ns": 18446744073709551615, "select_ns": 18446744073709551615,
                "start_ns": 18446744073709551615, "describe_ns": 18446744073709551615}
        self.assertLess(len(json.dumps(diag, separators=(",", ":"))), 255)
        # Full completion schema, not just the added objects. Bounds cover the
        # 20 ms watchdog and 1200 s host deadline at the fixed 10 ms task.
        qualification = {"max_ns": [20000000] * 5, "calls": [120000] * 5,
                         "snapshot_bytes": 8388608, "suite_bytes": 8388608,
                         "runner_bytes": 8388608, "records_per_scan": 1}
        run_id = "r" * 48
        marker = {"run_id": run_id, "build_id": "b" * 64,
                  "report_path": "PlcLogic/ci/report-" + run_id + ".xml",
                  "xunit_status": "WRITTEN", "xunit_phase": 9,
                  "xunit_last_file_error": 0, "xunit_cleanup_warning": False,
                  "diagnostic_json_requested": True,
                  "diagnostic_json_path": "PlcLogic/ci/report-" + run_id + ".json",
                  "diagnostic_json_status": "WRITTEN", "diagnostic_json_phase": 9,
                  "diagnostic_json_last_file_error": 0, "diagnostic_json_cleanup_warning": False,
                  "qualification": qualification,
                  "qualification_diagnostic": {key: 20000000 for key in diag}}
        rendered = "{\n  " + ",\n  ".join(
            json.dumps(key) + ": " + json.dumps(value, separators=(",", ":"))
            for key, value in marker.items()) + "\n}\n"
        self.assertLess(len(rendered.encode("utf-8")), 1023)

    def test_budget_profile_patch_is_nested_watchdog_and_fixed_capacity(self):
        with tempfile.TemporaryDirectory() as temp:
            owned = Path(temp) / "fixture"
            with mock.patch.object(boot, "OWNED_FIXTURE", owned):
                boot._prepare_owned_fixture(
                    qualification_budget=True,
                    qualification_capacity=boot.QUALIFICATION_BUDGET_PROFILES["FB_UpgradeBudgetSmall16"])
            source = (owned / "prepare_control_sl.py").read_text(encoding="utf-8")
            compile(source, "prepare_control_sl.py", "exec")
            self.assertIn("task.watchdog.enabled = True", source)
            self.assertIn('task.watchdog.time = "T#20ms"', source)
            self.assertIn("watchdog = task.watchdog", source)
            self.assertIn('watchdog_time_normalized != "T#20MS"', source)
            self.assertIn('"MAXNUMBEROFASSERTSFOREACHTESTSUITE": budget_profile["asserts_target"]', source)
            self.assertIn("'tests_required': 16, 'tests_target': 16", source)
            self.assertNotIn("task.watchdog_time =", source)

    def test_overcapacity_is_rejected_before_preparation(self):
        with self.assertRaisesRegex(ValueError, "rejected before preparation"):
            boot.validate_qualification_budget(
                suite_name="FB_UpgradeBudgetOverCapacity17", all_cases=True,
                task_interval_ms=10)

    def test_completion_marker_accepts_bounded_qualification_payload(self):
        source_adapter = boot.MATCHED_FIXTURE / "adapter"
        with tempfile.TemporaryDirectory() as temp:
            adapter = Path(temp) / "PlaintextExport/Tests/VM_Boot/FB_VMRunBundle"
            adapter.mkdir(parents=True)
            for name in ("POU.FB_VMRunBundle.DEC.exp", "M.AppendMarkerPiece.DEC.exp",
                         "M.TryPublishCompletion.IMP.exp"):
                shutil.copy2(source_adapter / name, adapter / name)
            boot._patch_qualification_bundle(Path(temp))
            self.assertIn("_qualification : STRING(512);",
                          (adapter / "POU.FB_VMRunBundle.DEC.exp").read_text(encoding="utf-8"))
            self.assertIn("Piece : STRING(512);",
                          (adapter / "M.AppendMarkerPiece.DEC.exp").read_text(encoding="utf-8"))
            self.assertIn('"qualification":',
                          (adapter / "M.TryPublishCompletion.IMP.exp").read_text(encoding="utf-8"))
            self.assertIn('"qualification_diagnostic":',
                          (adapter / "M.TryPublishCompletion.IMP.exp").read_text(encoding="utf-8"))
            self.assertTrue((adapter / "M.SetQualificationDiagnostic.IMP.exp").is_file())

    def test_invalid_capacity_is_invalid_request_before_preparation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            argv = ["--repo-root", str(root), "--suite-source", str(root / "FB_UpgradeBudgetOverCapacity17"),
                    "--suite", "FB_UpgradeBudgetOverCapacity17", "--all-cases", "--qualification-budget",
                    "--alias", "unused", "--state-root", str(root / "state"), "--output", str(root / "out")]
            with mock.patch.object(selected, "_prepare") as prepare, contextlib.redirect_stderr(io.StringIO()):
                code = selected.main(argv)
            self.assertEqual(code, selected.EXIT_INVALID_REQUEST)
            prepare.assert_not_called()
            self.assertFalse((root / "out").exists())

    def test_profile_capacity_is_declared_before_native_request_freeze(self):
        with tempfile.TemporaryDirectory() as temp:
            with mock.patch.object(boot, "OWNED_FIXTURE", Path(temp) / "fixture"), \
                    mock.patch.object(boot, "OWNED_RUNNER", Path(temp) / "runner"):
                module = boot._load_matched_boot(
                    qualification_budget=True,
                    qualification_capacity=boot.QUALIFICATION_BUDGET_PROFILES["FB_UpgradeBudgetSmall16"])
            capacity = module.selection_capacity(["Budget"], {"Budget": [str(i) for i in range(16)]}, None)
            self.assertEqual(module.native_capacity_request({"capacity": capacity}),
                             {"required": 1, "target": 1, "tests_required": 16, "tests_target": 16})
            fixture = (Path(temp) / "fixture/prepare_control_sl.py").read_text(encoding="utf-8")
            self.assertNotIn('request["counit_suite_capacity"] =', fixture)
            receipt = {"counit_suite_capacity": {"tests_per_suite": {
                "before": 16, "after_set": 16, "after_build": 16,
                "required": 16, "target": 16, "changed": False}}}
            with self.assertRaisesRegex(RuntimeError, "request did not name"):
                module.check_tests_per_suite(receipt, {"required": 1, "target": 1})
            module.check_tests_per_suite(receipt, module.native_capacity_request({"capacity": capacity}))

    def test_direct_all_cases_cli_supplies_empty_selection_filters(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "Describe").mkdir()
            (root / "Describe/Describe.IMP.exp").write_text(
                "SetCatalogIdentity(SuiteId := 's');\n"
                "DefineCase(CaseId := 'c', Name := 'C', RowKey := 'r', Tags := '', Disabled := FALSE);",
                encoding="utf-8")
            module = SimpleNamespace(main=lambda argv: 0)
            with mock.patch.object(boot, "_load_matched_boot", return_value=module), \
                    mock.patch.object(boot, "_install_prepare_hook") as install:
                self.assertEqual(boot.main(["--suite-source", str(root), "--all-cases", "--", "--alias", "owned"]), 0)
            self.assertEqual(install.call_args.kwargs["case_id"], "")
            self.assertEqual(install.call_args.kwargs["row_key"], "")

    def test_orchestrator_forwards_all_case_budget_profile(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_root = root / "run"
            run_root.mkdir()
            args = SimpleNamespace(
                state_root=root / "state", alias="owned", case_id=None, row_key=None,
                tag="", target_id=boot.TARGET_PROFILE, suite="FB_UpgradeBudgetSmall16",
                suite_source=root / "FB_UpgradeBudgetSmall16", repo_root=root,
                poll_timeout=1200, task_interval_ms=10, all_cases=True,
                qualification_budget=True, diagnostic_json=False)
            completed = subprocess.CompletedProcess([], 0, json.dumps({"status": "BOOT_BUNDLE_READY"}), "")
            with mock.patch.object(selected.subprocess, "run", return_value=completed) as run:
                metadata, code = selected._prepare(args, run_root, "run-1")
            command = run.call_args.args[0]
            self.assertIn("--all-cases", command)
            self.assertIn("--qualification-budget", command)
            self.assertEqual(command[command.index("--task-interval-ms") + 1], "10")
            self.assertEqual(code, selected.EXIT_ACCEPTED)
            self.assertEqual(metadata["status"], "ready")


if __name__ == "__main__":
    unittest.main()
