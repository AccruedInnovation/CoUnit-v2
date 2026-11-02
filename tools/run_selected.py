"""Run one prepared controlled CoUnit selection and strictly accept its reports."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from pathlib import PurePosixPath
import re
import secrets
import shutil
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import accept_run, controlled_boot


EXIT_ACCEPTED = 0
EXIT_TEST_FAILED = 1
EXIT_ABORTED = 2
EXIT_FRAMEWORK_ERROR = 3
EXIT_INFRASTRUCTURE = 4
EXIT_ACCEPTANCE_ERROR = 5
EXIT_BUILD_FAILED = 6
EXIT_TIMEOUT = 7
EXIT_INVALID_REQUEST = 8
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,47}$")
RUNTIME_PROFILE = "virtual_control_sl"
TARGET_DEVICE = {"type": "4096", "id": "0000 1007", "version": "4.22.0.0"}


def fresh_run_id() -> str:
    return f"ci-{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-{secrets.token_hex(4)}"


def _last_json_object(text: str) -> dict[str, Any] | None:
    for line in reversed(text.splitlines()):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if type(value) is dict:
            return value
    return None


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _parse_runner_output(text: str) -> dict[str, str]:
    fields = {}
    for line in text.splitlines():
        key, separator, value = line.partition("=")
        if separator and key in {"RunId", "Results", "ExceptionPositions", "ExitCode"}:
            fields[key] = value
    return fields


def _find_run_json(results_path: Path, run_id: str) -> Path | None:
    candidates = [
        results_path / "results" / run_id / "run.json",
        results_path / run_id / "run.json",
        results_path / "run.json",
    ]
    return next((path for path in candidates if path.is_file()), None)


def _run_health(run: dict[str, Any] | None, *, run_id: str,
                identity: dict[str, Any]) -> dict[str, Any]:
    if run is None:
        return {"status": "unknown", "reason": "run.json was not captured", "cleanup": None}
    cleanup = run.get("cleanup")
    log_summary = run.get("runtime_log_summary")
    errors = []
    if run.get("run_id") != run_id:
        errors.append(f"run.json run_id={run.get('run_id')!r} does not match requested run")
    if run.get("build_identity") != identity or run.get("build_id") != identity.get("build_id"):
        errors.append("run.json build identity does not match the prepared bundle")
    if run.get("mode") != "boot" or run.get("profile") != RUNTIME_PROFILE:
        errors.append("run.json mode/profile does not match the qualified boot target")
    if type(run.get("build_identity")) is dict and run["build_identity"].get("target_device") != TARGET_DEVICE:
        errors.append("run.json target device does not match Control SL 4.22")
    if run.get("status") != "complete":
        errors.append(f"runtime status={run.get('status')!r}")
    if run.get("outcome") == "infrastructure_error":
        errors.append("runtime outcome=infrastructure_error")
    if type(log_summary) is dict:
        count = log_summary.get("error_or_exception_records")
        if type(count) is not int or count != 0:
            errors.append(f"runtime error/exception records={count!r}")
    else:
        errors.append("runtime log summary is missing")
    if type(run.get("exception_positions")) is list and run["exception_positions"]:
        errors.append(f"runtime exception positions={len(run['exception_positions'])}")
    if run.get("instance_delete_completed") is not True:
        errors.append("runtime instance deletion is not confirmed")
    postboot = run.get("postboot_application_state")
    if type(postboot) is not dict or postboot.get("application_unchanged") is not True:
        errors.append("postboot application identity is not confirmed unchanged")
    if type(cleanup) is not dict:
        errors.append("cleanup record is missing")
    elif cleanup.get("status") != "passed" or cleanup.get("errors") != []:
        errors.append(f"cleanup status={cleanup.get('status')!r}, errors={cleanup.get('errors')!r}")
    return {"status": "passed" if not errors else "failed", "errors": errors,
            "runtime_status": run.get("status"), "runtime_outcome": run.get("outcome"),
            "cleanup": cleanup, "instance_delete_completed": run.get("instance_delete_completed"),
            "runtime_log_summary": log_summary}


def _manager_selection_error(selection: Any) -> str | None:
    """Require manager evidence to match the currently paired staged runner."""
    if type(selection) is not dict:
        return "manager-selection evidence is missing or invalid"
    expected_command = controlled_boot.REMOTE_MANAGER
    expected_source = (controlled_boot.OWNED_RUNNER / "ci_runtime.py").resolve()
    expected_candidate = PurePosixPath(expected_command).parent.name
    expected_digest = _paired_manager_digest(expected_source)
    if expected_digest is None:
        return "paired manager source is unavailable"
    source_path = selection.get("source_path")
    try:
        source_matches = type(source_path) is str and Path(source_path).resolve() == expected_source
    except OSError:
        source_matches = False
    source_digest = selection.get("source_sha256")
    remote_digest = selection.get("remote_sha256")
    if (selection.get("selection") != "staged_candidate" or
            selection.get("verification") != "matched" or
            selection.get("manager_command") != expected_command or
            selection.get("candidate_id") != expected_candidate or
            not source_matches or
            type(source_digest) is not str or re.fullmatch(r"[0-9a-f]{64}", source_digest) is None or
            source_digest != remote_digest or source_digest != expected_digest):
        return "manager-selection proof does not match the staged manager command, source, candidate, and digest"
    return None


def _paired_manager_digest(source: Path) -> str | None:
    try:
        return hashlib.sha256(source.read_bytes()).hexdigest()
    except OSError:
        return None


def _helper_result(stdout: str, preparation: Path) -> dict[str, Any] | None:
    result = _last_json_object(stdout)
    if result is not None:
        return result
    path = preparation / "helper-result.json"
    if path.is_file():
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return value if type(value) is dict else None
    return None


def _prepare(args, run_root: Path, run_id: str) -> tuple[dict[str, Any], int]:
    preparation = args.state_root.expanduser().resolve() / args.alias / "boot-bundles" / run_id
    command = [
        sys.executable, str(ROOT / "tools/controlled_boot.py"),
        "--suite-source", str(args.suite_source), "--case-id", getattr(args, "case_id", None) or "",
        "--row-key", getattr(args, "row_key", None) or "", "--tag", args.tag,
        "--target-profile", args.target_id, "--",
        "--alias", args.alias, "--state-root", str(args.state_root),
        "--suite", args.suite, "--repo-root", str(args.repo_root),
        "--output", str(preparation), "--poll-timeout", str(args.poll_timeout),
        "--task-interval-ms", str(getattr(args, "task_interval_ms", 10)), "--check", "all",
    ]
    if getattr(args, "all_cases", False):
        command.insert(command.index("--tag"), "--all-cases")
    if getattr(args, "qualification_budget", False):
        command.insert(command.index("--tag"), "--qualification-budget")
    if getattr(args, "diagnostic_json", False):
        command.append("--diagnostic-json")
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    (run_root / "prepare.stdout.log").write_text(completed.stdout, encoding="utf-8")
    (run_root / "prepare.stderr.log").write_text(completed.stderr, encoding="utf-8")
    result = _helper_result(completed.stdout, preparation)
    metadata = {"process_exit_code": completed.returncode, "result": result,
                "preparation_path": str(preparation),
                "result_path": str(preparation / "helper-result.json")}
    if completed.returncode != 0 or result is None or result.get("status") != "BOOT_BUNDLE_READY":
        metadata["status"] = "failed"
        metadata["primary_failure"] = ((result or {}).get("message") or (result or {}).get("status")
                                       or completed.stderr.strip() or "preparation did not return BOOT_BUNDLE_READY")
        status = (result or {}).get("status")
        if status == "BLOCKED" or (completed.returncode == 2 and result is None and
                                   completed.stderr.lstrip().startswith("usage:")):
            metadata["failure_kind"] = "invalid_preparation_request"
            return metadata, EXIT_INVALID_REQUEST
        if status == "OUTCOME_UNKNOWN" or "timeout" in str(metadata["primary_failure"]).casefold():
            metadata["failure_kind"] = "preparation_timeout_or_unknown"
            return metadata, EXIT_TIMEOUT
        if type((result or {}).get("native_failure")) is dict:
            metadata["failure_kind"] = "native_build_or_export_failure"
            return metadata, EXIT_BUILD_FAILED
        metadata["failure_kind"] = "preparation_infrastructure_failure"
        return metadata, EXIT_INFRASTRUCTURE
    metadata["status"] = "ready"
    return metadata, EXIT_ACCEPTED


def _validated_run_command(helper: dict[str, Any], run_id: str, runtime_output: Path) -> list[str]:
    command = helper.get("run_command")
    if type(command) is not dict or command.get("executable") != "pwsh":
        raise ValueError("helper result has no supported PowerShell run_command")
    arguments = command.get("arguments")
    if type(arguments) is not list or any(type(value) is not str for value in arguments):
        raise ValueError("helper run_command arguments are invalid")
    try:
        script_index = arguments.index("-File") + 1
        bundle_index = arguments.index("-BundlePath") + 1
    except (ValueError, IndexError) as exc:
        raise ValueError("helper run_command omits -File or -BundlePath") from exc
    script = Path(arguments[script_index]).resolve()
    expected_script = (controlled_boot.OWNED_RUNNER / "run-bundle.ps1").resolve()
    bundle = Path(arguments[bundle_index]).resolve()
    expected_bundle = Path(str(helper.get("bundle_path", ""))).resolve()
    if script != expected_script or bundle != expected_bundle or not (bundle / "build_identity.json").is_file():
        raise ValueError("helper run_command does not match the matched runner and prepared bundle")
    values = list(arguments)
    values.extend(["-RunId", run_id, "-OutputRoot", str(runtime_output)])
    executable = shutil.which(command["executable"])
    if executable is None:
        raise FileNotFoundError(f"Required executable is unavailable: {command['executable']}")
    return [executable, *values]


def run_selected(args) -> tuple[dict[str, Any], int]:
    run_root = args.output.resolve()
    if run_root.exists():
        raise FileExistsError(f"Output directory already exists: {run_root}")
    run_root.mkdir(parents=True)
    run_id = args.run_id or fresh_run_id()
    if not RUN_ID_RE.fullmatch(run_id):
        raise ValueError("run-id must use 1-48 letters, digits, underscores, or hyphens")
    result: dict[str, Any] = {"status": "preparing", "run_id": run_id,
                              "output_path": str(run_root), "primary_failure": None,
                              "preparation": None, "runtime_transport": None,
                              "runtime_health": None, "test_acceptance": None}
    preparation, prep_code = _prepare(args, run_root, run_id)
    result["preparation"] = preparation
    if prep_code != EXIT_ACCEPTED:
        result["status"] = preparation.get("failure_kind", "preparation_failed")
        result["primary_failure"] = preparation["primary_failure"]
        _write_json(run_root / "orchestration.json", result)
        return result, prep_code

    helper = preparation["result"]
    identity_path = Path(helper["bundle_path"]) / "build_identity.json"
    identity = json.loads(identity_path.read_text(encoding="utf-8"))
    runtime_output = run_root / "runtime-runs"
    try:
        command = _validated_run_command(helper, run_id, runtime_output)
    except (ValueError, OSError, KeyError) as exc:
        result["status"] = "infrastructure_failed"
        result["primary_failure"] = f"run command validation failed: {exc}"
        result["runtime_transport"] = {"status": "not_started"}
        _write_json(run_root / "orchestration.json", result)
        return result, EXIT_INFRASTRUCTURE
    run_process = subprocess.run(command, text=True, capture_output=True, check=False)
    (run_root / "run.stdout.log").write_text(run_process.stdout, encoding="utf-8")
    (run_root / "run.stderr.log").write_text(run_process.stderr, encoding="utf-8")
    fields = _parse_runner_output(run_process.stdout)
    reported_path = Path(fields["Results"]).resolve() if fields.get("Results") else runtime_output / run_id
    run_json_path = _find_run_json(reported_path, run_id)
    run_record = None
    if run_json_path is not None:
        try:
            run_record = json.loads(run_json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            run_record = None
    manager_failure = reported_path / "manager-selection.json"
    failure_path = reported_path / "failure.json"
    manager_selection = None
    manager_selection_error = None
    if manager_failure.is_file():
        try:
            manager_selection = json.loads(manager_failure.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            manager_selection_error = f"manager-selection evidence could not be read: {exc}"
    if failure_path.is_file():
        try:
            failure = json.loads(failure_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            failure = {}
    elif run_record is None and manager_failure.is_file():
        try:
            failure = json.loads(manager_failure.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            failure = {}
    else:
        failure = {}
    result["runtime_transport"] = {
        "status": "run_record_captured" if run_record is not None else "not_confirmed",
        "process_exit_code": run_process.returncode, "reported_run_id": fields.get("RunId"),
        "results_path": str(reported_path), "run_json_path": str(run_json_path) if run_json_path else None,
        "failure": failure or None, "manager_selection_path": str(manager_failure),
        "manager_selection": manager_selection, "manager_selection_error": manager_selection_error,
    }
    result["runtime_health"] = _run_health(run_record, run_id=run_id, identity=identity)
    if run_record is None:
        result["runtime_health"]["failure"] = failure.get("reason") or failure.get("failure")

    acceptance = None
    inventory_path = Path(preparation["preparation_path"]) / "expected-catalog.json"
    candidate_xml = [reported_path / "results" / run_id / "raw/counit-xunit.xml",
                     reported_path / "results" / run_id / "junit.xml"]
    xml_path = next((path for path in candidate_xml if path.is_file()), candidate_xml[0])
    candidate_json = reported_path / "results" / run_id / "raw/counit-diagnostic.json"
    target_id = args.target_id
    framework_version = str(identity.get("counit_library_version", helper.get("counit_library_version", "")))
    if inventory_path.is_file():
        diagnostic_requested = ((run_record or {}).get("diagnostic_json_requested") is True or
                                "diagnostic_json_path_template" in identity)
        acceptance = accept_run.accept_run(
            xml_path=xml_path, json_path=candidate_json if diagnostic_requested else None,
            inventory_path=inventory_path, run_id=run_id,
            build_id=str(identity.get("build_id", "")), target_id=target_id,
            framework_version=framework_version,
            allow_empty=args.allow_empty, allow_all_skipped=args.allow_all_skipped,
        )
    else:
        acceptance = {"classification": "not_run", "exit_code": EXIT_ACCEPTANCE_ERROR,
                      "reason": "strict inventory or xUnit report is missing",
                      "inventory_path": str(inventory_path), "xml_path": str(xml_path)}
    result["test_acceptance"] = {**acceptance, "xml_path": str(xml_path),
                                 "json_path": str(candidate_json) if candidate_json.is_file() else None,
                                 "inventory_path": str(inventory_path)}

    expected_exit = {"passed": 0, "test_failed": 1, "aborted": 2, "framework_error": 3}
    exit_matches_run = (run_record is not None and
                        expected_exit.get(str(run_record.get("outcome"))) == run_process.returncode)
    timeout_detected = (
        (run_process.returncode == EXIT_ABORTED and failure.get("outcome") == "supervisor_timeout") or
        (run_record is not None and run_record.get("status") in {"starting", "running", "interrupted"}) or
        (run_record is not None and run_record.get("outcome") in {
            "timeout", "supervisor_timeout", "readiness_timeout", "execution_timeout"})
    )
    manager_identity_error = manager_selection_error or _manager_selection_error(manager_selection)
    result["runtime_transport"]["manager_selection_error"] = manager_identity_error
    manager_identity_failed = manager_identity_error is not None
    runtime_failed = (manager_identity_failed or timeout_detected or
                      result["runtime_health"]["status"] != "passed" or
                      not exit_matches_run or run_record is None)
    if runtime_failed:
        failure_text = json.dumps(failure, ensure_ascii=False).casefold()
        timed_out = timeout_detected or (run_record is None and "timeout" in failure_text)
        result["status"] = "runtime_timeout_or_unknown" if timed_out else "runtime_infrastructure_failed"
        cleanup = result["runtime_health"].get("cleanup")
        if type(cleanup) is dict and (cleanup.get("status") != "passed" or cleanup.get("errors") != []):
            result["primary_failure"] = f"cleanup failed: {cleanup}"
        else:
            result["primary_failure"] = (result["runtime_health"].get("errors") or
                                          [failure.get("reason") or
                                           (manager_selection or {}).get("failure") or
                                           manager_identity_error or
                                           (run_record or {}).get("reason") or
                                           "runtime health/transport was not confirmed"])[0]
        exit_code = EXIT_TIMEOUT if timed_out else EXIT_INFRASTRUCTURE
    elif acceptance["classification"] == "accepted":
        result["status"] = "accepted"
        exit_code = EXIT_ACCEPTED
    elif acceptance["classification"] == "test_failed":
        result["status"] = "test_failed"
        result["primary_failure"] = acceptance["reason"]
        exit_code = EXIT_TEST_FAILED
    elif acceptance["classification"] == "aborted":
        result["status"] = "aborted"
        result["primary_failure"] = acceptance["reason"]
        exit_code = EXIT_ABORTED
    elif acceptance["classification"] == "framework_error":
        result["status"] = "framework_error"
        result["primary_failure"] = acceptance["reason"]
        exit_code = EXIT_FRAMEWORK_ERROR
    else:
        result["status"] = "acceptance_failed"
        result["primary_failure"] = acceptance["reason"]
        exit_code = (EXIT_INVALID_REQUEST if acceptance["classification"] == "invalid_request"
                     else EXIT_ACCEPTANCE_ERROR)
    result["exit_code"] = exit_code
    _write_json(run_root / "orchestration.json", result)
    return result, exit_code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--suite-source", type=Path, required=True)
    parser.add_argument("--suite", required=True)
    parser.add_argument("--case-id")
    parser.add_argument("--row-key")
    parser.add_argument("--all-cases", action="store_true",
                        help="Select every matching catalog row; disabled bodies remain skipped")
    parser.add_argument("--qualification-budget", action="store_true",
                        help="Enable the bounded UpgradeBudget timing/watchdog qualification profile")
    parser.add_argument("--tag", default="")
    parser.add_argument("--target-id", choices=[controlled_boot.TARGET_PROFILE],
                        default=controlled_boot.TARGET_PROFILE)
    parser.add_argument("--alias", required=True)
    parser.add_argument("--state-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True,
                        help="Fresh root for preparation, run evidence, and orchestration.json")
    parser.add_argument("--run-id")
    parser.add_argument("--poll-timeout", type=int, default=1200)
    parser.add_argument("--task-interval-ms", type=int, default=10)
    parser.add_argument("--allow-empty", action="store_true")
    parser.add_argument("--allow-all-skipped", action="store_true")
    parser.add_argument("--diagnostic-json", action="store_true")
    try:
        args = parser.parse_args(argv)
        if args.all_cases:
            if args.case_id not in (None, "") or args.row_key not in (None, ""):
                parser.error("--all-cases cannot be combined with --case-id or --row-key")
        elif not args.case_id or not args.row_key:
            parser.error("supply both --case-id and --row-key, or use --all-cases")
        if args.qualification_budget:
            try:
                controlled_boot.validate_qualification_budget(
                    suite_name=args.suite, all_cases=args.all_cases,
                    task_interval_ms=args.task_interval_ms)
            except ValueError as exc:
                parser.error(str(exc))
            if args.suite_source.name != args.suite:
                parser.error("--qualification-budget suite must match --suite-source")
    except SystemExit as exc:
        return 0 if exc.code == 0 else EXIT_INVALID_REQUEST
    output_preexisting = args.output.exists()
    args.run_id = args.run_id or fresh_run_id()
    try:
        result, code = run_selected(args)
    except Exception as exc:
        invalid = isinstance(exc, (ValueError, FileExistsError))
        exit_code = EXIT_INVALID_REQUEST if invalid else EXIT_INFRASTRUCTURE
        failure = {"status": "invalid_request" if invalid else "infrastructure_failed",
                   "exit_code": exit_code,
                   "primary_failure": str(exc), "phase": "orchestration",
                   "output_path": str(args.output.resolve()),
                   "preparation_path": str(args.state_root.expanduser().resolve() / args.alias /
                                            "boot-bundles" / args.run_id),
                   "runtime_output_path": str(args.output.resolve() / "runtime-runs")}
        if not output_preexisting and args.output.is_dir():
            try:
                _write_json(args.output.resolve() / "orchestration.json", failure)
            except OSError:
                pass
        print(json.dumps(failure, ensure_ascii=False))
        return exit_code
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
