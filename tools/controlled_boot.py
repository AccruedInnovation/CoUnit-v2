"""Prepare a selected catalog row with the matched offline CoUnit boot route.

This adapter does not talk to a PLC or provide a host-side exchange. It freezes
the requested suite/case/row/tag into the generated cyclic runner before the
an external offline build and boot-bundle route is invoked.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sys


MATCHED_BOOT = Path(os.environ.get("COUNIT_BOOT_HELPER", "external-host-helper/counit_boot.py"))
MATCHED_FIXTURE = MATCHED_BOOT.parent / "fixture"
SUPPORTED_UPGRADE_VERSIONS = ("2.1.0.1", "2.1.0.2", "2.1.0.3", "2.1.0.4", "2.1.0.5")
SUPPORTED_VERSION = "2.1.0.5"
TARGET_PROFILE = "linux-vcs-4.22-x64"
QUALIFICATION_BUDGET_SUITES = frozenset({
    "FB_UpgradeBudgetSmall16", "FB_UpgradeBudgetLarge2048", "FB_UpgradeBudgetOverCapacity17",
})
QUALIFICATION_BUDGET_PROFILES = {
    "FB_UpgradeBudgetSmall16": {"suite_count": 1, "tests_required": 16, "tests_target": 16, "asserts_target": 16},
    "FB_UpgradeBudgetLarge2048": {"suite_count": 1, "tests_required": 2048, "tests_target": 2048, "asserts_target": 2048},
    "FB_UpgradeBudgetOverCapacity17": {"suite_count": 1, "tests_required": 17, "tests_target": 16, "asserts_target": 16},
}
OWNED_RUNNER = Path(os.environ.get("COUNIT_ADAPTER_ROOT", "external-host-helper")) / "owned-runner"
REMOTE_MANAGER = os.environ.get("COUNIT_REMOTE_MANAGER", "/path/to/external/ci_runtime.py")
OWNED_FIXTURE = Path(os.environ.get("COUNIT_ADAPTER_ROOT", "external-host-helper")) / "owned-fixture"
DEFINE_CASE = re.compile(
    r"\bDefineCase\s*\(\s*CaseId\s*:=\s*'((?:[^']|'')*)'\s*,\s*"
    r"Name\s*:=\s*'((?:[^']|'')*)'\s*,\s*RowKey\s*:=\s*'((?:[^']|'')*)'\s*,\s*"
    r"Tags\s*:=\s*'((?:[^']|'')*)'\s*,\s*Disabled\s*:=\s*(TRUE|FALSE)\s*\)", re.I)
SET_ID = re.compile(r"\bSetCatalogIdentity\s*\(\s*SuiteId\s*:=\s*'((?:[^']|'')*)'\s*\)", re.I)
COMMENT = re.compile(r"\(\*.*?\*\)|//[^\r\n]*", re.S)
DEFINE_CALL = re.compile(r"\bDefineCase\s*\(", re.I)
SET_ID_CALL = re.compile(r"\bSetCatalogIdentity\s*\(", re.I)


def _prepare_owned_runner() -> None:
    """Use the existing paired, staged manager route; leave maintained files unchanged."""
    original = MATCHED_BOOT.parent / "runner"
    if not OWNED_RUNNER.exists():
        OWNED_RUNNER.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(original, OWNED_RUNNER, ignore=shutil.ignore_patterns("__pycache__"))
    source = (original / "ci_runtime.py").read_text(encoding="utf-8")

    def replace_once(old: str, new: str, label: str) -> None:
        nonlocal source
        if source.count(old) != 1:
            raise RuntimeError(f"Matched {label} changed")
        source = source.replace(old, new)

    upgrade_versions_literal = ", ".join(f'"{version}"' for version in SUPPORTED_UPGRADE_VERSIONS)
    replace_once('"diagnostic_json_path_template" in identity and counit_library_version != "2.0.1.0"',
                 '"diagnostic_json_path_template" in identity and counit_library_version not in '
                 f'("2.0.1.0", {upgrade_versions_literal})',
                 "diagnostic JSON manifest admission")
    replace_once('                    self._stop_runtime(state, "cleanup", deadline)',
                 '''                    try:
                        observed = self._verify_running_container(state["instance"], slot)
                        peak_text = self.bounded_run(["docker", "exec", observed["container_id"],
                            "cat", "/sys/fs/cgroup/memory.peak"], timeout=5).stdout.strip()
                        if not peak_text.isdecimal() or int(peak_text) <= 0:
                            raise RuntimeError("cgroup memory.peak is not a positive byte count")
                        state["resource_observation"] = {"status": "observed", "source": "cgroup-v2 memory.peak",
                            "peak_bytes": int(peak_text), "limit_bytes": self.memory_bytes(slot["memory_limit"]),
                            "container_id": observed["container_id"]}
                    except Exception as error:
                        state["resource_observation"] = {"status": "unavailable", "reason": str(error)}
                    self._stop_runtime(state, "cleanup", deadline)''',
                 "owned pre-stop resource observation")

    guard = 'counit_library_version not in ("2.0.0.0", "2.0.1.0")'
    if source.count(guard) != 1:
        raise RuntimeError("Matched runtime version guard changed")
    source = source.replace(
        guard, 'counit_library_version not in ("2.0.0.0", "2.0.1.0", ' + upgrade_versions_literal + ')')
    versioned_name = '"counit - a unittest framework for codesys, 2.0.1.0 (www.co5e.org)",'
    if versioned_name not in source:
        raise RuntimeError("Matched resolved-library guard changed")
    upgrade_library_names = "".join(
        f'\n                               "counit - a unittest framework for codesys, {version} (www.co5e.org)",'
        for version in SUPPORTED_UPGRADE_VERSIONS)
    source = source.replace(versioned_name, versioned_name + upgrade_library_names)
    # The report reader separately validates the resolved library's dialect.
    generic_versions = '"2.0.0.0": "counit_v2", "2.0.1.0": "counit_v2", "1.2.0.3": "counit_legacy"'
    if source.count(generic_versions) != 2:
        raise RuntimeError("Matched report dialect maps changed")
    upgrade_dialects = ", ".join(f'"{version}": "counit_v2"' for version in SUPPORTED_UPGRADE_VERSIONS)
    source = source.replace(generic_versions, generic_versions + ", " + upgrade_dialects)
    title_map = '"counit - a unittest framework for codesys, 2.0.1.0 (www.co5e.org)": {"2.0.1.0": "counit_v2"},'
    if source.count(title_map) != 1:
        raise RuntimeError("Matched report title map changed")
    upgrade_title_maps = "".join(
        f'\n            "counit - a unittest framework for codesys, {version} (www.co5e.org)": '
        f'{{"{version}": "counit_v2"}},' for version in SUPPORTED_UPGRADE_VERSIONS)
    source = source.replace(title_map, title_map + upgrade_title_maps)
    zero_assertion_guard = '''            if assertion_count <= 0 and (case_outcome != "skipped" or failure_node or error_node):
                raise RuntimeError(f"CoUnit testcase {case.get('name', '')} has no assertions")'''
    if source.count(zero_assertion_guard) != 1:
        raise RuntimeError("Matched zero-assertion guard changed")
    source = source.replace(zero_assertion_guard, '            canonical_error_without_assertions = (\n'
        '                root.get("counit-schema-version") == "2" and\n'
        '                root.get("counit-framework-version") in (' + upgrade_versions_literal + ') and\n'
        '                case_outcome == "error" and error_node and not failure_node and not skipped_node)\n'
        '            if assertion_count <= 0 and (case_outcome != "skipped" or failure_node or error_node):\n'
        '                if not canonical_error_without_assertions:\n'
        '                    raise RuntimeError(f"CoUnit testcase {case.get(\'name\', \'\')} has no assertions")')

    replace_once(
        '        return {"tests": len(cases), "failures": failures, "errors": errors, "skipped": skipped,\n',
        '        report_summary = {"tests": len(cases), "failures": failures, "errors": errors, "skipped": skipped,\n',
        "matched xUnit summary return",
    )
    replace_once(
        '                    "truncated": report_truncated,\n                }}\n\n    @staticmethod\n    def report_failure_reason',
        '                    "truncated": report_truncated,\n                }}\n'
        '        if "counit-termination-reason" in root.attrib:\n'
        '            report_summary["termination_reason"] = root.get("counit-termination-reason")\n'
        '        return report_summary\n\n    @staticmethod\n    def report_failure_reason',
        "matched xUnit termination summary",
    )
    replace_once(
        '                if case_outcome == "failure":\n                    record["assertion_callsite"] = "unavailable"',
        '                if case_outcome == "error" and result_node is not None:\n'
        '                    if "termination-reason" in result_node.attrib:\n'
        '                        record["termination_reason"] = result_node.get("termination-reason", "")\n'
        '                    if "failure-type" in result_node.attrib or "failure-message" in result_node.attrib:\n'
        '                        record["first_failure"] = {\n'
        '                            "type": result_node.get("failure-type", ""),\n'
        '                            "message": result_node.get("failure-message", ""),\n'
        '                            "body": bounded["body"],\n'
        '                            "body_truncated": bounded["body_truncated"],\n'
        '                            "omitted_body_characters": bounded["omitted_body_characters"],\n'
        '                        }\n'
        '                if case_outcome == "failure":\n                    record["assertion_callsite"] = "unavailable"',
        "matched xUnit error details",
    )

    replace_once(
        '        if not isinstance(document, dict) or type(document.get("format_version")) is not int or document["format_version"] != 1:\n'
        '            raise RuntimeError("diagnostic JSON report has an unsupported format_version")',
        '        if not isinstance(document, dict) or type(document.get("format_version")) is not int or document["format_version"] not in (1, 2):\n'
        '            raise RuntimeError("diagnostic JSON report has an unsupported format_version")\n'
        '        format_version = document["format_version"]\n'
        '        if format_version == 2:\n'
        '            if type(document.get("schema_version")) is not int or document["schema_version"] != 2:\n'
        '                raise RuntimeError("diagnostic JSON format 2 requires schema_version 2")\n'
        '            if document.get("framework_version") not in (' + upgrade_versions_literal + '):\n'
        '                raise RuntimeError("diagnostic JSON format 2 requires a supported 2.1 upgrade version")',
        "diagnostic JSON schema-version gate",
    )
    replace_once(
        '        if document["run_disposition"] != report_summary.get("run_disposition"):\n'
        '            raise RuntimeError("diagnostic JSON run disposition differs from xUnit")',
        '        if document["run_disposition"] != report_summary.get("run_disposition"):\n'
        '            raise RuntimeError("diagnostic JSON run disposition differs from xUnit")\n'
        '        if format_version == 2:\n'
        '            has_json_reason = "termination_reason" in document\n'
        '            has_xml_reason = "termination_reason" in report_summary\n'
        '            if has_json_reason != has_xml_reason:\n'
        '                raise RuntimeError("diagnostic JSON run termination reason differs from xUnit")\n'
        '            if has_json_reason and (type(document["termination_reason"]) is not str or\n'
        '                                    document["termination_reason"] != report_summary["termination_reason"]):\n'
        '                raise RuntimeError("diagnostic JSON run termination reason differs from xUnit")',
        "diagnostic JSON root termination comparison",
    )
    replace_once(
        '                if (type(assertions) is not int or assertions < 0 or\n'
        '                        (assertions == 0 and outcome != "skipped") or assertions != xunit_cases[key]["assertions"]):\n'
        '                    raise RuntimeError(f"diagnostic JSON assertions differ from xUnit for {classname}.{name}")',
        '                canonical_error_without_assertions = (\n'
        '                    format_version == 2 and document.get("schema_version") == 2 and\n'
        '                    document.get("framework_version") in (' + upgrade_versions_literal + ') and outcome == "error" and\n'
        '                    isinstance(case.get("error"), dict) and "failure" not in case)\n'
        '                if (type(assertions) is not int or assertions < 0 or\n'
        '                        (assertions == 0 and outcome != "skipped" and not canonical_error_without_assertions) or\n'
        '                        assertions != xunit_cases[key]["assertions"]):\n'
        '                    raise RuntimeError(f"diagnostic JSON assertions differ from xUnit for {classname}.{name}")',
        "diagnostic JSON canonical zero-assertion case",
    )
    replace_once(
        '                elif outcome == "error":\n'
        '                    error = case.get("error")\n'
        '                    if (not isinstance(error, dict) or not isinstance(error.get("message"), str) or\n'
        '                            len(error["message"]) > MAX_REPORT_FAILURE_TEXT_CHARS):\n'
        '                        raise RuntimeError(f"diagnostic JSON error detail is missing or exceeds the text bound for {classname}.{name}")\n'
        '                    xml_detail = xunit_details.get(key)\n'
        '                    if xml_detail is not None and error["message"] != xml_detail["message"]:\n'
        '                        raise RuntimeError(f"diagnostic JSON error message differs from xUnit for {classname}.{name}")',
        '                elif outcome == "error":\n'
        '                    error = case.get("error")\n'
        '                    if (not isinstance(error, dict) or not isinstance(error.get("message"), str) or\n'
        '                            len(error["message"]) > MAX_REPORT_FAILURE_TEXT_CHARS):\n'
        '                        raise RuntimeError(f"diagnostic JSON error detail is missing or exceeds the text bound for {classname}.{name}")\n'
        '                    xml_detail = xunit_details.get(key)\n'
        '                    if xml_detail is not None and error["message"] != xml_detail["message"]:\n'
        '                        raise RuntimeError(f"diagnostic JSON error message differs from xUnit for {classname}.{name}")\n'
        '                    if format_version == 2:\n'
        '                        allowed_error_keys = {"message", "termination_reason", "first_failure"}\n'
        '                        if not set(error) <= allowed_error_keys:\n'
        '                            raise RuntimeError(f"diagnostic JSON error keys are invalid for {classname}.{name}")\n'
        '                        json_has_reason = "termination_reason" in error\n'
        '                        xml_has_reason = xml_detail is not None and "termination_reason" in xml_detail\n'
        '                        if json_has_reason and type(error["termination_reason"]) is not str:\n'
        '                            raise RuntimeError(f"diagnostic JSON error termination reason is malformed for {classname}.{name}")\n'
        '                        if xml_detail is not None and (\n'
        '                                json_has_reason != xml_has_reason or\n'
        '                                (json_has_reason and error["termination_reason"] != xml_detail["termination_reason"])):\n'
        '                            raise RuntimeError(f"diagnostic JSON error termination reason differs from xUnit for {classname}.{name}")\n'
        '                        json_has_first_failure = "first_failure" in error\n'
        '                        xml_has_first_failure = xml_detail is not None and "first_failure" in xml_detail\n'
        '                        if xml_detail is not None and json_has_first_failure != xml_has_first_failure:\n'
        '                            raise RuntimeError(f"diagnostic JSON first failure presence differs from xUnit for {classname}.{name}")\n'
        '                        if json_has_first_failure:\n'
        '                            first_failure = error["first_failure"]\n'
        '                            fields = {"type", "message", "expected", "actual"}\n'
        '                            if type(first_failure) is not dict or set(first_failure) != fields:\n'
        '                                raise RuntimeError(f"diagnostic JSON first failure is malformed for {classname}.{name}")\n'
        '                            if any(type(first_failure[field]) is not str or\n'
        '                                   len(first_failure[field]) > MAX_REPORT_FAILURE_TEXT_CHARS\n'
        '                                   for field in fields):\n'
        '                                raise RuntimeError(f"diagnostic JSON first failure fields are malformed for {classname}.{name}")\n'
        '                            if xml_detail is not None and xml_has_first_failure:\n'
        '                                expected_body = f"Expected: {first_failure[\'expected\']}\\nActual: {first_failure[\'actual\']}"\n'
        '                                xml_first_failure = xml_detail["first_failure"]\n'
        '                                if (first_failure["type"] != xml_first_failure["type"] or\n'
        '                                        first_failure["message"] != xml_first_failure["message"] or\n'
        '                                        xml_first_failure["body"] != expected_body[:MAX_REPORT_FAILURE_TEXT_CHARS] or\n'
        '                                        xml_first_failure["omitted_body_characters"] !=\n'
        '                                        max(0, len(expected_body) - MAX_REPORT_FAILURE_TEXT_CHARS)):\n'
        '                                    raise RuntimeError(f"diagnostic JSON first failure differs from xUnit for {classname}.{name}")',
        "diagnostic JSON rich error reconciliation",
    )
    replace_once(
        '        return {"format_version": 1, "run_disposition": document["run_disposition"],\n',
        '        return {"format_version": format_version, "run_disposition": document["run_disposition"],\n',
        "diagnostic JSON format summary",
    )
    (OWNED_RUNNER / "ci_runtime.py").write_text(source, encoding="utf-8", newline="\n")
    script = (original / "run-bundle.ps1").read_text(encoding="utf-8-sig")
    old = "[string]$ManagerCommand = '/usr/local/sbin/codesys-ci-runtime'"
    if script.count(old) != 1 or script.count('[string]$ManagerSourcePath,') != 1:
        raise RuntimeError("Matched paired-manager parameters changed")
    script = script.replace(old, "[string]$ManagerCommand = '" + REMOTE_MANAGER + "'")
    script = script.replace('[string]$ManagerSourcePath,', "[string]$ManagerSourcePath = (Join-Path $PSScriptRoot 'ci_runtime.py'),")
    (OWNED_RUNNER / "run-bundle.ps1").write_text(script, encoding="utf-8")


def _literal(value: str) -> str:
    return value.replace("''", "'")


def extract_catalog(describe_source: str) -> dict:
    """Read literal Describe declarations; method bodies are never executed."""
    if "$'" in describe_source:
        raise ValueError("Describe uses unsupported IEC dollar-quote escapes")
    body = COMMENT.sub("", describe_source)
    suite_ids = SET_ID.findall(body)
    if len(suite_ids) != 1 or len(SET_ID_CALL.findall(body)) != 1:
        raise ValueError("Describe must set exactly one literal SuiteId")
    rows = []
    for case_id, name, row_key, tags, disabled in DEFINE_CASE.findall(body):
        declared_name = _literal(name)
        canonical_name = declared_name[9:] if declared_name[:9].casefold() == "disabled_" else declared_name
        rows.append({"case_id": _literal(case_id), "name": canonical_name,
                     "declared_name": declared_name,
                     "row_key": _literal(row_key), "tags": _literal(tags),
                     "disabled": disabled.upper() == "TRUE"})
    if not rows or len(DEFINE_CALL.findall(body)) != len(rows):
        raise ValueError("Every DefineCase call must use supported literal arguments")
    keys = [(row["case_id"], row["row_key"]) for row in rows]
    if len(set(keys)) != len(keys):
        raise ValueError("Describe contains duplicate case/row identities")
    return {"suite_id": _literal(suite_ids[0]), "cases": rows}


def select_catalog_rows(catalog: dict, *, case_id: str | None = None,
                        row_key: str | None = None, tag: str = "",
                        all_cases: bool = False) -> list[dict]:
    if all_cases:
        if case_id not in (None, "") or row_key not in (None, ""):
            raise ValueError("--all-cases cannot be combined with --case-id or --row-key")
        selected = [row for row in catalog["cases"]
                    if not tag or tag in row["tags"].split("|")]
        if not selected:
            raise ValueError("All-case selection matched no catalog rows")
        return selected
    if not case_id or not row_key:
        raise ValueError("One-row selection requires both --case-id and --row-key")
    selected = [row for row in catalog["cases"] if not row["disabled"]
                and row["case_id"] == case_id and row["row_key"] == row_key
                and (not tag or tag in row["tags"].split("|"))]
    if len(selected) != 1:
        raise ValueError("Selection must resolve to exactly one enabled catalog row")
    return selected


def select_catalog(catalog: dict, *, case_id: str, row_key: str, tag: str = "") -> dict:
    return select_catalog_rows(catalog, case_id=case_id, row_key=row_key, tag=tag)[0]


def validate_qualification_budget(*, suite_name: str, all_cases: bool,
                                   task_interval_ms: int) -> None:
    if suite_name not in QUALIFICATION_BUDGET_SUITES or not all_cases:
        raise ValueError("--qualification-budget requires --all-cases and an UpgradeBudget suite")
    if task_interval_ms != 10:
        raise ValueError("--qualification-budget requires a 10 ms task interval")
    profile = QUALIFICATION_BUDGET_PROFILES[suite_name]
    if profile["tests_required"] > profile["tests_target"]:
        raise ValueError("qualification catalog exceeds the configured CoUnit capacity; rejected before preparation")


def strict_inventory(catalog: dict, *, tag: str = "", case_id: str | None = None,
                     row_key: str | None = None, all_cases: bool = False) -> dict:
    selected_keys = {(row["case_id"], row["row_key"]) for row in
                     select_catalog_rows(catalog, case_id=case_id, row_key=row_key,
                                         tag=tag, all_cases=all_cases)}
    return {"rows": [
        {"suite_id": catalog["suite_id"], "case_id": row["case_id"],
         "row_key": row["row_key"],
         "selected": ((row["case_id"], row["row_key"]) in selected_keys),
         "disabled": row["disabled"]}
        for row in catalog["cases"]]}


def _load_matched_boot(*, qualification_budget: bool = False,
                       qualification_capacity: dict | None = None):
    if not MATCHED_BOOT.is_file():
        raise FileNotFoundError(f"Matched CoUnit boot helper is missing: {MATCHED_BOOT}")
    spec = importlib.util.spec_from_file_location("matched_counit_boot", MATCHED_BOOT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load matched CoUnit boot helper: {MATCHED_BOOT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    # This is a task-local adapter; the installed helper and package remain untouched.
    module.COUNIT_LIBRARY_VERSIONS = (*module.COUNIT_LIBRARY_VERSIONS, *SUPPORTED_UPGRADE_VERSIONS)
    module.COUNIT_LIBRARY_NAMES.update(
        f"counit - a unittest framework for codesys, {version} (www.co5e.org)"
        for version in SUPPORTED_UPGRADE_VERSIONS)
    original_validate = module.validate_counit_library_version

    def validate(version: str, *, diagnostic_json: bool = False) -> str:
        if version in SUPPORTED_UPGRADE_VERSIONS and type(diagnostic_json) is bool:
            return version
        return original_validate(version, diagnostic_json=diagnostic_json)

    module.validate_counit_library_version = validate
    if qualification_budget:
        original_capacity = module.selection_capacity

        def declared_capacity(suites, cases, declared):
            capacity = original_capacity(suites, cases, declared)
            if (len(suites) != qualification_capacity["suite_count"] or
                    max(len(cases[suite]) for suite in suites) != qualification_capacity["tests_required"]):
                raise ValueError("Literal catalog differs from the qualification capacity profile")
            capacity["tests_per_suite"] = {
                "required": qualification_capacity["tests_required"],
                "target": qualification_capacity["tests_target"],
            }
            return capacity

        module.selection_capacity = declared_capacity
    _prepare_owned_fixture(qualification_budget=qualification_budget,
                           qualification_capacity=qualification_capacity)
    _prepare_owned_runner()
    module.runner_sidecar_dir = lambda _repo_root: OWNED_RUNNER
    module.boot_fixture_root = lambda _repo_root: OWNED_FIXTURE
    return module


def _prepare_owned_fixture(*, qualification_budget: bool = False,
                           qualification_capacity: dict | None = None) -> None:
    """Freeze the matched fixture with explicit known candidate versions; default to active."""
    if not MATCHED_FIXTURE.is_dir():
        raise FileNotFoundError(f"Matched boot fixture is missing: {MATCHED_FIXTURE}")
    if not OWNED_FIXTURE.exists():
        OWNED_FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(MATCHED_FIXTURE, OWNED_FIXTURE)
    helper = OWNED_FIXTURE / "prepare_control_sl.py"
    source = (MATCHED_FIXTURE / "prepare_control_sl.py").read_text(encoding="utf-8")
    source = source.replace('SUPPORTED_COUNIT_LIBRARY_VERSIONS = ("2.0.0.0", "2.0.1.0")',
                            'SUPPORTED_COUNIT_LIBRARY_VERSIONS = ("2.1.0.1", "2.1.0.2", "2.1.0.3", "2.1.0.4", "2.1.0.5")')
    source = source.replace('EXPECTED_COUNIT_VERSION = "2.0.0.0"',
                            'EXPECTED_COUNIT_VERSION = "2.1.0.5"')
    source = source.replace("counit_library_version must be exactly 2.0.0.0 or 2.0.1.0",
                            "counit_library_version must be exactly 2.1.0.1, 2.1.0.2, 2.1.0.3, 2.1.0.4 or 2.1.0.5")
    source = source.replace('DEFAULT_COUNIT_LIBRARY_VERSION = EXPECTED_COUNIT_VERSION',
                            'DEFAULT_COUNIT_LIBRARY_VERSION = EXPECTED_COUNIT_VERSION')
    source = source.replace('EXPECTED_COUNIT_VERSION == "2.0.1.0"',
                            'EXPECTED_COUNIT_VERSION in ("2.0.1.0", "2.1.0.1", "2.1.0.2", "2.1.0.3", "2.1.0.4", "2.1.0.5")')
    source = source.replace('EXPECTED_COUNIT_VERSION != "2.0.1.0"',
                            'EXPECTED_COUNIT_VERSION not in ("2.0.1.0", "2.1.0.1", "2.1.0.2", "2.1.0.3", "2.1.0.4", "2.1.0.5")')
    guard = 'diagnostic_json_requested and counit_version != "2.0.1.0"'
    if source.count(guard) != 1:
        raise RuntimeError("Matched fixture JSON admission changed")
    source = source.replace(guard, 'diagnostic_json_requested and counit_version not in ("2.0.1.0", "2.1.0.1", "2.1.0.2", "2.1.0.3", "2.1.0.4", "2.1.0.5")')
    if qualification_budget:
        if not isinstance(qualification_capacity, dict):
            raise ValueError("qualification budget requires a fixed CoUnit capacity profile")
        capacity_anchor = '    wanted = _requested_suite_capacity(request)\n'
        if source.count(capacity_anchor) != 1:
            raise RuntimeError("Matched CoUnit capacity configuration shape changed")
        capacity_hook = '''    budget_profile = QUALIFICATION_BUDGET_PROFILE
    if budget_profile is not None:
        reference = _counit_reference(application)
        parameters = reference.parameters
        requested_parameters = {
            "MAXNUMBEROFTESTSUITES": budget_profile["suite_count"],
            "MAXNUMBEROFTESTSFOREACHTESTSUITE": budget_profile["tests_target"],
            "MAXNUMBEROFASSERTSFOREACHTESTSUITE": budget_profile["asserts_target"],
        }
        for parameter_name, requested_value in requested_parameters.items():
            _parameters, parameter_key, _before = _counit_parameter_value(reference, parameter_name)
            parameters[parameter_key] = str(requested_value)
            reference = _counit_reference(application)
            _parameters, _key, actual_value = _counit_parameter_value(reference, parameter_name)
            if actual_value != requested_value:
                raise RuntimeError("CoUnit %s readback differs from qualification profile" % parameter_name)
        result["qualification_capacity_profile"] = {
            "requested": requested_parameters,
            "readback": _counit_parameter_list(reference),
        }
    wanted = _requested_suite_capacity(request)
'''
        source = source.replace(capacity_anchor, capacity_hook, 1)
        profile_literal = repr({
            "suite_count": qualification_capacity["suite_count"],
            "tests_required": qualification_capacity["tests_required"],
            "tests_target": qualification_capacity["tests_target"],
            "asserts_target": qualification_capacity["asserts_target"],
        })
        module_anchor = 'SUPPORTED_COUNIT_LIBRARY_VERSIONS ='
        pos = source.find(module_anchor)
        if pos < 0:
            raise RuntimeError("Matched fixture version constants changed")
        source = source[:pos] + "QUALIFICATION_BUDGET_PROFILE = " + profile_literal + "\n" + source[pos:]
    if qualification_budget:
        task_anchor = ('    task.priority = "1"\n'
                       '    task.pous.add(ENTRY_PROGRAM, "Offline CoUnit VM bundle delegate")')
        task_config = ('    task.priority = "1"\n'
                       '    task.watchdog.enabled = True\n'
                       '    task.watchdog.time = "T#20ms"\n'
                       '    task.watchdog.time_unit = "ms"\n'
                       '    task.watchdog.sensitivity = "1"\n'
                       '    task.pous.add(ENTRY_PROGRAM, "Offline CoUnit VM bundle delegate")')
        if source.count(task_anchor) != 1:
            raise RuntimeError("Matched task configuration shape changed before watchdog qualification")
        source = source.replace(task_anchor, task_config, 1)
        task_record = ('    return {"guid": _guid(task.guid), "configuration_guid": _guid(config.guid),\n'
                       '            "name": str(task.name), "kind": str(task.kind_of_task), "interval": str(task.interval),\n'
                       '            "interval_ms": interval_ms, "priority": str(task.priority), "programs": [str(task.pous[0][0])]}')
        qualified_record = ('    watchdog = task.watchdog\n'
                            '    watchdog_enabled = str(watchdog.enabled).strip().lower() == "true"\n'
                            '    watchdog_time = str(watchdog.time)\n'
                            '    watchdog_time_normalized = watchdog_time.upper().replace("TIME#", "T#")\n'
                            '    watchdog_time_unit = str(watchdog.time_unit)\n'
                            '    watchdog_sensitivity = str(watchdog.sensitivity)\n'
                            '    if (not watchdog_enabled or watchdog_time_normalized != "T#20MS" or\n'
                            '            watchdog_time_unit != "ms" or watchdog_sensitivity != "1"):\n'
                            '        raise RuntimeError("qualification task watchdog readback differs from 20 ms / 1 ms sensitivity")\n'
                            '    return {"guid": _guid(task.guid), "configuration_guid": _guid(config.guid),\n'
                            '            "name": str(task.name), "kind": str(task.kind_of_task), "interval": str(task.interval),\n'
                            '            "interval_ms": interval_ms, "priority": str(task.priority),\n'
                            '            "watchdog_enabled": watchdog_enabled, "watchdog_time": watchdog_time,\n'
                            '            "watchdog_time_normalized": watchdog_time_normalized,\n'
                            '            "watchdog_time_unit": watchdog_time_unit, "watchdog_sensitivity": watchdog_sensitivity,\n'
                            '            "programs": [str(task.pous[0][0])]}')
        if source.count(task_record) != 1:
            raise RuntimeError("Matched task record shape changed before watchdog readback")
        source = source.replace(task_record, qualified_record, 1)
    helper.write_text(source, encoding="utf-8")


def _qualification_metrics_st(target_suite: str) -> str:
    lines = ["Qualification := '{\"max_ns\":[';"]
    for index in range(5):
        if index:
            lines.append("Qualification := CONCAT(Qualification, ',');")
        lines.append(f"Qualification := CONCAT(Qualification, ULINT_TO_STRING(_maxNs[{index}]));")
    lines.append("Qualification := CONCAT(Qualification, '],\"calls\":[');")
    for index in range(5):
        if index:
            lines.append("Qualification := CONCAT(Qualification, ',');")
        lines.append(f"Qualification := CONCAT(Qualification, ULINT_TO_STRING(_calls[{index}]));")
    lines.extend([
        "Qualification := CONCAT(Qualification, '],\"snapshot_bytes\":');",
        "Qualification := CONCAT(Qualification, UDINT_TO_STRING(SIZEOF(CoUnit.ST_CoUnitRunSnapshot)));",
        "Qualification := CONCAT(Qualification, ',\"suite_bytes\":');",
        f"Qualification := CONCAT(Qualification, UDINT_TO_STRING(SIZEOF({target_suite})));",
        "Qualification := CONCAT(Qualification, ',\"runner_bytes\":');",
        "Qualification := CONCAT(Qualification, UDINT_TO_STRING(SIZEOF(CoUnit.FB_coUnitRunner)));",
        "Qualification := CONCAT(Qualification, ',\"records_per_scan\":1}');",
    ])
    return "\n".join("\t" + line for line in lines)


def _patch_qualification_bundle(workspace: Path) -> None:
    adapter_dir = workspace / "PlaintextExport/Tests/VM_Boot/FB_VMRunBundle"
    declaration_path = adapter_dir / "POU.FB_VMRunBundle.DEC.exp"
    declaration = declaration_path.read_text(encoding="utf-8")
    variable = "\t_qualification : STRING(512);\n"
    if variable not in declaration:
        end = declaration.rfind("END_VAR")
        if end < 0:
            raise RuntimeError("Matched bundle declaration has no final VAR section")
        declaration = declaration[:end] + variable + declaration[end:]
    diagnostic_variable = "\t_qualificationDiagnostic : STRING(255);\n"
    if diagnostic_variable not in declaration:
        end = declaration.rfind("END_VAR")
        if end < 0:
            raise RuntimeError("Matched bundle declaration has no final VAR section")
        declaration = declaration[:end] + diagnostic_variable + declaration[end:]
    declaration_path.write_text(declaration, encoding="utf-8")
    (adapter_dir / "M.SetQualification.DEC.exp").write_text(
        "METHOD PUBLIC SetQualification\nVAR_INPUT\n\tValue : STRING(512);\nEND_VAR\n", encoding="utf-8")
    (adapter_dir / "M.SetQualification.IMP.exp").write_text(
        "_qualification := Value;\n", encoding="utf-8")
    (adapter_dir / "M.SetQualificationDiagnostic.DEC.exp").write_text(
        "METHOD PUBLIC SetQualificationDiagnostic\nVAR_INPUT\n\tValue : STRING(255);\nEND_VAR\n", encoding="utf-8")
    (adapter_dir / "M.SetQualificationDiagnostic.IMP.exp").write_text(
        "_qualificationDiagnostic := Value;\n", encoding="utf-8")

    implementation_path = adapter_dir / "M.TryPublishCompletion.IMP.exp"
    implementation = implementation_path.read_text(encoding="utf-8")
    append_declaration_path = adapter_dir / "M.AppendMarkerPiece.DEC.exp"
    append_declaration = append_declaration_path.read_text(encoding="utf-8")
    if "Piece : STRING(255);" not in append_declaration:
        raise RuntimeError("Matched marker append capacity changed before qualification insertion")
    append_declaration_path.write_text(
        append_declaration.replace("Piece : STRING(255);", "Piece : STRING(512);", 1), encoding="utf-8")
    anchor = "IF NOT AppendMarkerPiece(Buffer := _markerText, Piece := '$N}') THEN Invalid := TRUE; RETURN; END_IF"
    if implementation.count(anchor) != 1:
        raise RuntimeError("Matched completion marker close changed before qualification insertion")
    qualification = ("IF _qualification <> '' THEN\n"
                     "\tIF NOT AppendMarkerPiece(Buffer := _markerText, Piece := ',$N  \"qualification\":') THEN Invalid := TRUE; RETURN; END_IF\n"
                     "\tIF NOT AppendMarkerPiece(Buffer := _markerText, Piece := _qualification) THEN Invalid := TRUE; RETURN; END_IF\n"
                     "END_IF\n")
    diagnostic = ("IF _qualificationDiagnostic <> '' THEN\n"
                  "\tIF NOT AppendMarkerPiece(Buffer := _markerText, Piece := ',$N  \"qualification_diagnostic\":') THEN Invalid := TRUE; RETURN; END_IF\n"
                  "\tIF NOT AppendMarkerPiece(Buffer := _markerText, Piece := _qualificationDiagnostic) THEN Invalid := TRUE; RETURN; END_IF\n"
                  "END_IF\n")
    implementation_path.write_text(implementation.replace(anchor, qualification + diagnostic + anchor, 1), encoding="utf-8")


def _patch_qualification_outputs(declaration: str) -> str:
    variable = "\tQualification : STRING(512);\n"
    diagnostic = "\tQualificationDiagnostic : STRING(255);\n"
    if declaration.count("VAR_OUTPUT\n") != 1:
        raise RuntimeError("Generated selected runner must have one VAR_OUTPUT section")
    if variable not in declaration:
        declaration = declaration.replace("VAR_OUTPUT\n", "VAR_OUTPUT\n" + variable, 1)
    if diagnostic not in declaration:
        declaration = declaration.replace(variable, variable + diagnostic, 1)
    return declaration


def _qualification_diagnostic_st(suite_instance: str) -> str:
    return "\n".join((
        "QualificationDiagnostic := '{\"configure_ns\":';",
        "QualificationDiagnostic := CONCAT(QualificationDiagnostic, ULINT_TO_STRING(_diagNs[1]));",
        "QualificationDiagnostic := CONCAT(QualificationDiagnostic, ',\"select_ns\":');",
        "QualificationDiagnostic := CONCAT(QualificationDiagnostic, ULINT_TO_STRING(_diagNs[2]));",
        "QualificationDiagnostic := CONCAT(QualificationDiagnostic, ',\"start_ns\":');",
        "QualificationDiagnostic := CONCAT(QualificationDiagnostic, ULINT_TO_STRING(_diagNs[3]));",
        "QualificationDiagnostic := CONCAT(QualificationDiagnostic, ',\"describe_ns\":');",
        f"QualificationDiagnostic := CONCAT(QualificationDiagnostic, ULINT_TO_STRING({suite_instance}.DescribeNanoseconds));",
        "QualificationDiagnostic := CONCAT(QualificationDiagnostic, '}');",
    ))


def _render_controlled_program(*, suite_id: str, case_id: str, row_key: str, tag: str,
                               target_profile: str, expected_selected: int = 1,
                               target_suite: str = "", suite_instance: str = "",
                               qualification_budget: bool = False) -> str:
    """Create executable body text for the generated cyclic runner FB."""
    # All dynamic values are PLC string literals and are escaped before insertion.
    def st(value: str) -> str:
        return "'" + value.replace("'", "$'") + "'"

    run_call = "CoUnit.RUN_CONTROLLED(Exchange := Exchange);"
    if qualification_budget:
        run_call = '''IF NOT _recordsConfigured THEN
	CoUnit.GVL_CoUnitReporting.RecordsPerScan := 1;
	_recordsConfigured := TRUE;
END_IF
_priorState := TO_USINT(Exchange.Status.State);
_callStarted := LTIME();
CoUnit.RUN_CONTROLLED(Exchange := Exchange);
_elapsedNs := TO_ULINT(LTIME() - _callStarted);
IF _priorState <= 4 THEN
	_calls[_priorState] := _calls[_priorState] + 1;
	IF _elapsedNs > _maxNs[_priorState] THEN _maxNs[_priorState] := _elapsedNs; END_IF
END_IF'''
        run_call = run_call.replace(
            "CoUnit.RUN_CONTROLLED(Exchange := Exchange);",
            """IF (Exchange.RequestId <> Exchange.AckId) AND NOT _diagMeasuring THEN
	_diagRequest := Exchange.RequestId;
	_diagOperation := TO_USINT(Exchange.Operation);
	_diagStarted := LTIME();
	_diagMeasuring := TRUE;
END_IF
CoUnit.RUN_CONTROLLED(Exchange := Exchange);
IF _diagMeasuring AND (Exchange.AckId = _diagRequest) THEN
	_diagElapsed := TO_ULINT(LTIME() - _diagStarted);
	IF (_diagOperation >= 1) AND (_diagOperation <= 3) THEN
		IF _diagElapsed > _diagNs[_diagOperation] THEN _diagNs[_diagOperation] := _diagElapsed; END_IF
	END_IF
	_diagMeasuring := FALSE;
END_IF""")
        if target_suite not in QUALIFICATION_BUDGET_SUITES:
            raise ValueError("qualification metrics require an UpgradeBudget suite")
        if not suite_instance:
            raise ValueError("qualification diagnostics require the selected suite instance name")
    qualification_report = ""
    qualification_diagnostic = ""
    if qualification_budget:
        qualification_report = "\n" + _qualification_metrics_st(target_suite)
        qualification_diagnostic = "\n" + _qualification_diagnostic_st(suite_instance)
    return f'''IF NOT _waiting AND NOT _failed THEN
    CASE _step OF
        0:
            _request := _request + 1; Exchange.Operation := 1;
            Exchange.RunId := run_number; Exchange.BuildId := build_id;
            Exchange.TargetId := {st(target_profile)};
            Exchange.RunTimeout := _runTimeout; Exchange.CleanupTimeout := _cleanupTimeout;
            Exchange.RequestId := _request; _waiting := TRUE; _step := 1;
        1:
            IF Exchange.Accepted AND Exchange.Status.CatalogReady THEN
                _request := _request + 1; Exchange.Operation := 2;
                Exchange.RunId := run_number; Exchange.ExpectedGeneration := Exchange.Status.Generation;
                Exchange.SuiteId := {st(suite_id)}; Exchange.CaseId := {st(case_id)};
                Exchange.RowKey := {st(row_key)}; Exchange.Tag := {st(tag)};
                Exchange.RequestId := _request; _waiting := TRUE; _step := 2;
            ELSIF Exchange.AckId = _request AND NOT Exchange.Accepted THEN _failed := TRUE;
            END_IF
        2:
            IF Exchange.Accepted THEN
                _request := _request + 1; Exchange.Operation := 3;
                Exchange.RunId := run_number; Exchange.ExpectedGeneration := Exchange.Status.Generation;
                Exchange.ExpectedSelected := _expectedSelected;
                Exchange.RequestId := _request; _waiting := TRUE; _step := 3;
            ELSIF Exchange.AckId = _request THEN _failed := TRUE;
            END_IF
        3:
            IF Exchange.Status.ExecutionComplete THEN _step := 4;
            ELSIF Exchange.AckId = _request AND NOT Exchange.Accepted THEN _failed := TRUE;
            END_IF
        4:
            bTestComplete := TRUE;
    END_CASE
END_IF
IF _waiting AND (Exchange.AckId = _request) THEN _waiting := FALSE; END_IF
CoUnit.GVL_coUnit.xUnitFilePath := report_path;
{run_call}
IF Exchange.Status.ExecutionComplete THEN bTestComplete := TRUE; END_IF
{qualification_report}
{qualification_diagnostic}
'''


def _install_prepare_hook(boot, selection: dict, *, suite_id: str, case_id: str,
                          row_key: str, tag: str, target_profile: str, target_suite: str,
                          selected_rows: list[dict], all_cases: bool = False,
                          qualification_budget: bool = False) -> None:
    original = boot.prepare_source
    original_case_reader = boot.selected_suite_cases

    class DefineNames:
        def __init__(self, declaration_body):
            self.declaration_body = declaration_body

        def findall(self, body):
            return ([_literal(row[1]) for row in DEFINE_CASE.findall(body)]
                    if body.lstrip("\ufeff") == self.declaration_body else [])

    def catalog_cases(root, suite, tools_root=None, index=None):
        if suite != target_suite:
            return original_case_reader(root, suite, tools_root, index=index)
        index = index or boot.source_index(root, tools_root)
        records = index["symbols"].get(suite.casefold(), [])
        if len(records) != 1:
            raise ValueError("Catalog must resolve to one owned source object")
        paths = [path for path in records[0].files if path.name == "M.Describe.IMP.exp"]
        if len(paths) != 1 or extract_catalog(paths[0].read_text(encoding="utf-8-sig")) != selection:
            raise ValueError("Frozen catalog changed or has duplicate method sources")
        runners = index["runners"]
        test_re = runners.TEST_RE
        try:
            declaration_body = index["dependencies"].COMMENT_RE.sub(
                "", paths[0].read_text(encoding="utf-8-sig"))
            runners.TEST_RE = DefineNames(declaration_body)
            return original_case_reader(root, suite, tools_root, index=index)
        finally:
            runners.TEST_RE = test_re

    boot.selected_suite_cases = catalog_cases

    def prepare(repo_root, output, suite, *, diagnostic_json_requested=False):
        original_cases = boot.selected_suite_cases
        original_extra = boot.EXTRA_OBJECTS
        original_checked = boot.run_checked
        original_patch = boot.patch_standard_runner
        boot.EXTRA_OBJECTS = set(original_extra)

        def patch_runner(workspace, fixture_path, *, diagnostic_json_requested=False):
            original_patch(workspace, fixture_path,
                           diagnostic_json_requested=diagnostic_json_requested)
            delegate_path = workspace / "PlaintextExport/Tests/PRG_TEST/POU.PRG_TEST.IMP.exp"
            delegate = delegate_path.read_text(encoding="utf-8")
            old_call = "selectedRunner(run_number := _boot.RunId, report_path := _boot.RuntimeReportPath);"
            new_call = ("selectedRunner(run_number := _boot.RunId, build_id := _boot.GetBuildId(), "
                        "report_path := _boot.RuntimeReportPath);")
            if delegate.count(old_call) != 1:
                raise RuntimeError("Matched delegate call shape changed")
            delegate = delegate.replace(old_call, new_call)
            if qualification_budget:
                completion_call = "\t\t_boot.TryPublishCompletion();"
                qualification_call = ("\t\t_boot.SetQualification(Value := selectedRunner.Qualification);\n"
                                      "\t\t_boot.SetQualificationDiagnostic(Value := selectedRunner.QualificationDiagnostic);\n"
                                      + completion_call)
                if delegate.count(completion_call) != 1:
                    raise RuntimeError("Matched completion call shape changed before budget metrics bind")
                delegate = delegate.replace(completion_call, qualification_call, 1)
            delegate_path.write_text(delegate, encoding="utf-8")

        def checked(command):
            if len(command) > 1 and str(command[1]).endswith("generate_plcopenxml.py"):
                workspace = Path(command[command.index("--repo-root") + 1])
                object_list = Path(command[command.index("--object-list") + 1])
                xml_path = Path(command[command.index("--output") + 1])
                single = workspace / "PlaintextExport/Tests/PRG_TEST_SINGLE"
                decl_path = single / "POU.PRG_TEST_SINGLE.DEC.exp"
                decl = decl_path.read_text(encoding="utf-8")
                if "\tbuild_id : STRING(64);" not in decl:
                    decl = decl.replace("\treport_path : STRING(255);\n",
                                        "\treport_path : STRING(255);\n\tbuild_id : STRING(64);\n", 1)
                if qualification_budget:
                    decl = _patch_qualification_outputs(decl)
                state = ("\tExchange : CoUnit.ST_CoUnitExchange;\n"
                         "\t_step : UINT;\n\t_request : ULINT;\n"
                         f"\t_expectedSelected : UDINT := {len(selected_rows)};\n"
                         "\t_runTimeout : TIME := T#60s;\n\t_cleanupTimeout : TIME := T#5s;\n"
                         "\t_waiting : BOOL;\n\t_failed : BOOL;\n")
                if qualification_budget:
                    state += ("\t_recordsConfigured : BOOL;\n"
                              "\t_priorState : USINT;\n"
                              "\t_callStarted : LTIME;\n"
                              "\t_elapsedNs : ULINT;\n"
                              "\t_maxNs : ARRAY[0..4] OF ULINT;\n"
                              "\t_calls : ARRAY[0..4] OF ULINT;\n"
                              "\t_diagMeasuring : BOOL;\n"
                              "\t_diagRequest : ULINT;\n"
                              "\t_diagOperation : USINT;\n"
                              "\t_diagStarted : LTIME;\n"
                              "\t_diagElapsed : ULINT;\n"
                              "\t_diagNs : ARRAY[1..3] OF ULINT;\n")
                if "\tExchange : CoUnit.ST_CoUnitExchange;" not in decl:
                    end = decl.rfind("END_VAR")
                    if end < 0:
                        raise RuntimeError("Generated runner has no final VAR section")
                    decl = decl[:end] + state + decl[end:]
                decl_path.write_text(decl, encoding="utf-8")
                adapter_dir = workspace / "PlaintextExport/Tests/VM_Boot/FB_VMRunBundle"
                (adapter_dir / "M.GetBuildId.DEC.exp").write_text(
                    "METHOD PUBLIC GetBuildId : STRING(64)\n", encoding="utf-8")
                (adapter_dir / "M.GetBuildId.IMP.exp").write_text(
                    "GetBuildId := _buildId;\n", encoding="utf-8")
                if qualification_budget:
                    _patch_qualification_bundle(workspace)
                (single / "POU.PRG_TEST_SINGLE.IMP.exp").write_text(
                    _render_controlled_program(suite_id=suite_id, case_id=case_id,
                                               row_key=row_key, tag=tag,
                                               target_profile=target_profile,
                                               expected_selected=len(selected_rows),
                                               target_suite=target_suite,
                                               suite_instance=(boot.instance_name(target_suite)
                                                               if qualification_budget else ""),
                                               qualification_budget=qualification_budget), encoding="utf-8")
                writer_path = repo_root / "_tools/generate_plcopenxml.py"
                writer_spec = importlib.util.spec_from_file_location(
                    "controlled_plcopen_writer", writer_path)
                if writer_spec is None or writer_spec.loader is None:
                    raise RuntimeError("Cannot load the repository PLCOpenXML writer")
                writer = importlib.util.module_from_spec(writer_spec)
                sys.modules[writer_spec.name] = writer
                writer_spec.loader.exec_module(writer)
                objects = writer.discover_objects([
                    writer.RootSpec((workspace / "PlaintextExport").resolve(), (), "staged selected source")])
                requested = writer.read_object_list(object_list)
                selected_objects = writer.filter_objects(objects, requested)
                xml_path.parent.mkdir(parents=True, exist_ok=True)
                writer.build_xml(selected_objects, "Controlled CoUnit catalog run").write(
                    xml_path, encoding="utf-8", xml_declaration=True, short_empty_elements=True)
                return ""
            return original_checked(command)

        boot.patch_standard_runner = patch_runner
        boot.run_checked = checked
        try:
            result = original(
                repo_root, output, suite, diagnostic_json_requested=diagnostic_json_requested)
            inventory = strict_inventory(selection, tag=tag, case_id=case_id,
                                         row_key=row_key, all_cases=all_cases)
            (output / "expected-catalog.json").write_text(
                json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
            return result
        finally:
            boot.selected_suite_cases = original_cases
            boot.EXTRA_OBJECTS = original_extra
            boot.run_checked = original_checked
            boot.patch_standard_runner = original_patch

    boot.prepare_source = prepare


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite-source", type=Path, required=True,
                        help="Canonical generated suite source directory containing Describe/Describe.IMP.exp")
    parser.add_argument("--case-id", default="")
    parser.add_argument("--row-key", default="")
    parser.add_argument("--all-cases", action="store_true",
                        help="Select every matching catalog row; disabled bodies remain skipped")
    parser.add_argument("--qualification-budget", action="store_true",
                        help="Enable the bounded UpgradeBudget timing/watchdog qualification profile")
    parser.add_argument("--tag", default="")
    parser.add_argument("--target-profile", choices=[TARGET_PROFILE], default=TARGET_PROFILE)
    parser.add_argument("--inventory-output", type=Path,
                        help="Write the extracted static catalog inventory here and exit")
    parser.add_argument("--inventory-json", type=Path,
                        help="Frozen independent expected metadata used by the existing run acceptor")
    parser.add_argument("boot_args", nargs=argparse.REMAINDER,
                        help="Remaining arguments are passed to matched counit_boot.py")
    args = parser.parse_args(argv)
    if args.all_cases:
        if args.case_id not in (None, "") or args.row_key not in (None, ""):
            parser.error("--all-cases cannot be combined with --case-id or --row-key")
    elif not args.case_id or not args.row_key:
        parser.error("supply both --case-id and --row-key, or use --all-cases")
    describe_candidates = (args.suite_source / "M.Describe.IMP.exp",
                           args.suite_source / "Describe" / "M.Describe.IMP.exp",
                           args.suite_source / "Describe" / "Describe.IMP.exp")
    describe = next((path for path in describe_candidates if path.is_file()), describe_candidates[0])
    catalog = extract_catalog(describe.read_text(encoding="utf-8-sig"))
    try:
        selected_rows = select_catalog_rows(catalog, case_id=args.case_id,
                                            row_key=args.row_key, tag=args.tag,
                                            all_cases=args.all_cases)
    except ValueError as exc:
        parser.error(str(exc))
    selected = selected_rows if args.all_cases else selected_rows[0]
    if args.qualification_budget and (args.inventory_output or not args.boot_args):
        parser.error("--qualification-budget requires a matched boot run, not inventory-only mode")
    inventory = {"suite_source": str(args.suite_source.resolve()), "suite_id": catalog["suite_id"],
                 "cases": catalog["cases"], "selected": selected,
                 "all_cases": args.all_cases, "selected_count": len(selected_rows),
                 "target_profile": args.target_profile, "framework_version": SUPPORTED_VERSION,
                 "selection_source": "literal Describe metadata"}
    if args.inventory_output:
        args.inventory_output.parent.mkdir(parents=True, exist_ok=True)
        args.inventory_output.write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
        return 0
    if args.inventory_json:
        args.inventory_json.parent.mkdir(parents=True, exist_ok=True)
        inventory_rows = strict_inventory(catalog, tag=args.tag, case_id=args.case_id,
                                          row_key=args.row_key, all_cases=args.all_cases)
        args.inventory_json.write_text(json.dumps(inventory_rows, indent=2) + "\n", encoding="utf-8")
    if not args.boot_args:
        parser.error("supply matched boot arguments after --")
    boot_args = list(args.boot_args)
    if boot_args[:1] == ["--"]:
        boot_args.pop(0)
    def option_value(name: str) -> str | None:
        for index, value in enumerate(boot_args):
            if value == name and index + 1 < len(boot_args):
                return boot_args[index + 1]
            if value.startswith(name + "="):
                return value.split("=", 1)[1]
        return None
    if args.qualification_budget:
        try:
            validate_qualification_budget(
                suite_name=args.suite_source.name, all_cases=args.all_cases,
                task_interval_ms=int(option_value("--task-interval-ms") or "-1"))
        except ValueError as exc:
            parser.error(str(exc))
        if option_value("--suite") != args.suite_source.name:
            parser.error("--qualification-budget suite must match --suite-source")
    # Run control remains in the cyclic runner; the selected key is frozen in the prepared source.
    capacity_profile = (QUALIFICATION_BUDGET_PROFILES[args.suite_source.name]
                        if args.qualification_budget else None)
    boot = _load_matched_boot(qualification_budget=args.qualification_budget,
                              qualification_capacity=capacity_profile)
    _install_prepare_hook(boot, catalog, suite_id=catalog["suite_id"], case_id=args.case_id,
                          row_key=args.row_key, tag=args.tag, target_profile=args.target_profile,
                          target_suite=args.suite_source.name, selected_rows=selected_rows,
                          all_cases=args.all_cases, qualification_budget=args.qualification_budget)
    if "--counit-library-version" not in boot_args:
        boot_args.extend(["--counit-library-version", SUPPORTED_VERSION])
    return boot.main(boot_args)


if __name__ == "__main__":
    raise SystemExit(main())
