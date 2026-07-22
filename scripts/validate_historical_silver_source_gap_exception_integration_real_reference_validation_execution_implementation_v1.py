#!/usr/bin/env python3
"""Validate the one-time execution implementation without reading real inputs."""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import run_historical_silver_source_gap_exception_integration_real_reference_validation_once_v1 as runner

READY = (
    "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_"
    "REAL_REFERENCE_VALIDATION_ONE_TIME_EXECUTION_WORKFLOW_IMPLEMENTATION_VALIDATED_NOT_EXECUTED"
)
BLOCKED = (
    "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_"
    "REAL_REFERENCE_VALIDATION_EXECUTION_IMPLEMENTATION_BLOCKED"
)
STATUS_SCHEMA = (
    "historical-silver-2023-24-source-gap-exception-integration-"
    "real-reference-validation-execution-implementation-current-status-v1"
)
RUNNER_PATH = "scripts/run_historical_silver_source_gap_exception_integration_real_reference_validation_once_v1.py"
WORKFLOW_PATH = ".github/workflows/run-approved-historical-silver-source-gap-exception-integration-real-reference-validation-once-v1.yml"

RUNNER_REQUIRED = (
    'REQUEST_SHA256 = "sha256:192a06862fe830027686d149d36572b4ad76ea609f489c6a3d540b7ea4b27e97"',
    'IMPLEMENTATION_SHA256 = "sha256:c4bd7ccb05bcf78747a7210e0eefad083d599de2ca8b0d44c9c455006f084cbc"',
    "def validate_admission(",
    "def adapt_coverage_record(",
    "def evaluate_result(",
    "def self_test(",
    "integrate_documented_source_gap(raw_report, manifest, policy)",
    '"execution_count_for_request": 1',
    '"request_consumed": True',
    '"repeat_execution_allowed": False',
    '"database_access": False',
    '"network_access": False',
    '"formal_stake": 0',
)
WORKFLOW_REQUIRED = (
    "workflow_dispatch:",
    "github.ref == 'refs/heads/main'",
    "github.run_attempt == 1",
    runner.REQUEST_ID,
    "--execution-count-before 0",
    "--validate-only",
    "--coverage data/research/historical-gold-silver-coverage-real-reference-result-v1.json",
    "--manifest data/research/historical-silver-2023-24-source-gap-exception-manifest-v1.json",
    "--policy data/research/historical-silver-2023-24-source-gap-exception-integration-policy-v1.json",
    "historical-silver-source-gap-exception-integration-real-reference-validation-execution-v1",
    "if-no-files-found: error",
)
RUNNER_FORBIDDEN = (
    "import requests",
    "from requests",
    "import sqlite3",
    "import socket",
    "import urllib",
    "subprocess.",
    "os.system",
    "curl ",
    "wget ",
)
WORKFLOW_FORBIDDEN = (
    "schedule:",
    "push:",
    "pull_request:",
    "curl ",
    "wget ",
    "pip install",
    "git push",
)


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def checks_for(runner_text: str, workflow_text: str, status: dict[str, Any]) -> dict[str, bool]:
    checks: dict[str, bool] = {}
    for index, fragment in enumerate(RUNNER_REQUIRED):
        checks[f"runner_required_{index}"] = fragment in runner_text
    for index, fragment in enumerate(WORKFLOW_REQUIRED):
        checks[f"workflow_required_{index}"] = fragment in workflow_text
    for index, fragment in enumerate(RUNNER_FORBIDDEN):
        checks[f"runner_forbidden_{index}"] = fragment not in runner_text
    for index, fragment in enumerate(WORKFLOW_FORBIDDEN):
        checks[f"workflow_forbidden_{index}"] = fragment not in workflow_text
    checks.update({
        "status_schema": status.get("schema_version") == STATUS_SCHEMA,
        "status_state": status.get("formal_state") == READY,
        "status_request": status.get("request_id") == runner.REQUEST_ID,
        "status_runner": status.get("runner") == RUNNER_PATH,
        "status_workflow": status.get("manual_workflow") == WORKFLOW_PATH,
        "approval_granted": status.get("approval_granted") is True,
        "workflow_created": status.get("execution_workflow_created") is True,
        "execution_enabled": status.get("execution_enabled") is True,
        "count_zero": status.get("execution_count") == 0,
        "maximum_one": status.get("maximum_execution_count") == 1,
        "not_consumed": status.get("request_consumed") is False,
        "no_repeat": status.get("repeat_execution_allowed") is False,
        "manual_only": status.get("workflow_dispatch_only") is True,
        "no_automatic_dispatch": status.get("automatic_dispatch_allowed") is False,
        "not_executed": status.get("real_reference_validation_executed") is False,
        "ready_manual": status.get("ready_for_manual_dispatch") is True,
        "aggregate_only": status.get("committed_aggregate_inputs_only") is True,
        "no_database": status.get("database_access_allowed") is False,
        "no_network": status.get("network_access_allowed") is False,
        "no_archive": status.get("source_archive_access_allowed") is False,
        "no_rows": status.get("raw_rows_allowed") is False,
        "stake_zero": status.get("formal_stake") == 0,
    })
    return checks


def mutation_tests(runner_text: str, workflow_text: str, status: dict[str, Any]) -> dict[str, bool]:
    tests: dict[str, bool] = {}
    baseline = checks_for(runner_text, workflow_text, status)
    assert all(baseline.values()), baseline

    for index, fragment in enumerate(RUNNER_REQUIRED):
        mutated = runner_text.replace(fragment, f"REMOVED_RUNNER_{index}", 1)
        tests[f"remove_runner_required_{index}_blocks"] = not all(checks_for(mutated, workflow_text, status).values())
    for index, fragment in enumerate(WORKFLOW_REQUIRED):
        mutated = workflow_text.replace(fragment, f"REMOVED_WORKFLOW_{index}", 1)
        tests[f"remove_workflow_required_{index}_blocks"] = not all(checks_for(runner_text, mutated, status).values())

    for index, fragment in enumerate(("import requests", "import sqlite3", "import socket")):
        mutated = runner_text + "\n" + fragment + "\n"
        tests[f"forbidden_runner_{index}_blocks"] = not all(checks_for(mutated, workflow_text, status).values())
    for index, fragment in enumerate(("schedule:", "push:", "curl https://example.invalid")):
        mutated = workflow_text + "\n" + fragment + "\n"
        tests[f"forbidden_workflow_{index}_blocks"] = not all(checks_for(runner_text, mutated, status).values())

    for key, value in (
        ("approval_granted", False),
        ("execution_workflow_created", False),
        ("execution_enabled", False),
        ("execution_count", 1),
        ("request_consumed", True),
        ("automatic_dispatch_allowed", True),
        ("real_reference_validation_executed", True),
        ("formal_stake", 1),
    ):
        mutated_status = copy.deepcopy(status)
        mutated_status[key] = value
        tests[f"status_{key}_mutation_blocks"] = not all(checks_for(runner_text, workflow_text, mutated_status).values())
    return tests


def write_json(path: Path, value: dict[str, Any]) -> None:
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if len(payload.encode("utf-8")) > 1_048_576:
        raise RuntimeError("validation output exceeds 1 MiB")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", type=Path, required=True)
    parser.add_argument("--manual-workflow", type=Path, required=True)
    parser.add_argument("--status", type=Path, required=True)
    parser.add_argument("--self-test-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    runner_text = args.runner.read_text(encoding="utf-8")
    workflow_text = args.manual_workflow.read_text(encoding="utf-8")
    status = read_json(args.status)
    checks = checks_for(runner_text, workflow_text, status)
    mutations = mutation_tests(runner_text, workflow_text, status)
    synthetic = runner.self_test()

    write_json(args.self_test_output, {
        "schema_version": "historical-silver-source-gap-exception-real-reference-validation-runner-self-test-v1",
        "formal_state": "SELF_TEST_PASS" if all(synthetic.values()) else "SELF_TEST_FAIL",
        "tests_run": len(synthetic),
        "tests_passed": sum(synthetic.values()),
        "tests": synthetic,
        "real_reference_inputs_read": False,
        "formal_stake": 0,
    })

    failed_checks = sorted(name for name, passed in checks.items() if not passed)
    failed_mutations = sorted(name for name, passed in mutations.items() if not passed)
    valid = not failed_checks and not failed_mutations and all(synthetic.values())
    report = {
        "schema_version": "historical-silver-source-gap-exception-real-reference-validation-execution-implementation-validation-v1",
        "formal_state": READY if valid else BLOCKED,
        "implementation_valid": valid,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed_checks),
        "checks_failed": len(failed_checks),
        "failed_checks": failed_checks,
        "mutation_tests_run": len(mutations),
        "mutation_tests_passed": len(mutations) - len(failed_mutations),
        "failed_mutation_tests": failed_mutations,
        "synthetic_tests_run": len(synthetic),
        "synthetic_tests_passed": sum(synthetic.values()),
        "approval_granted": True,
        "execution_workflow_created": True,
        "execution_enabled": True,
        "execution_count": 0,
        "maximum_execution_count": 1,
        "request_consumed": False,
        "workflow_dispatch_only": True,
        "automatic_dispatch_allowed": False,
        "real_reference_validation_executed": False,
        "real_reference_inputs_read": False,
        "database_access": False,
        "network_access": False,
        "source_archive_access": False,
        "raw_rows_read": False,
        "raw_rows_emitted": 0,
        "ready_for_manual_dispatch": valid,
        "formal_stake": 0,
    }
    write_json(args.output, report)
    print(json.dumps({
        "formal_state": report["formal_state"],
        "checks_failed": report["checks_failed"],
        "mutation_tests_passed": report["mutation_tests_passed"],
        "synthetic_tests_passed": report["synthetic_tests_passed"],
        "formal_stake": 0,
    }, ensure_ascii=False, indent=2))
    return 0 if valid else 2


if __name__ == "__main__":
    raise SystemExit(main())
