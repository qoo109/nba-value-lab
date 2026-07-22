#!/usr/bin/env python3
"""Validate the admission-state fix without reading governed aggregate inputs."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

import run_historical_silver_source_gap_exception_integration_real_reference_validation_once_v2 as runner

READY = (
    "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_"
    "REAL_REFERENCE_VALIDATION_ADMISSION_FIX_VALIDATED_READY_FOR_MANUAL_RETRY"
)
BLOCKED = (
    "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_"
    "REAL_REFERENCE_VALIDATION_ADMISSION_FIX_BLOCKED"
)
STATUS_SCHEMA = (
    "historical-silver-2023-24-source-gap-exception-integration-"
    "real-reference-validation-execution-implementation-current-status-v2"
)
WRAPPER_PATH = (
    "scripts/run_historical_silver_source_gap_exception_integration_"
    "real_reference_validation_once_v2.py"
)
WORKFLOW_PATH = (
    ".github/workflows/run-approved-historical-silver-source-gap-exception-"
    "integration-real-reference-validation-once-v1.yml"
)


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def admission(
    request: dict[str, Any],
    approval: dict[str, Any],
    approval_status: dict[str, Any],
    request_hash: str,
    implementation_hash: str,
    confirmation: str = runner.REQUEST_ID,
    event: str = "workflow_dispatch",
    ref: str = "refs/heads/main",
    count: int = 0,
) -> dict[str, Any]:
    return runner.validate_admission(
        request=request,
        approval=approval,
        approval_status=approval_status,
        request_sha256=request_hash,
        implementation_sha256=implementation_hash,
        confirmation_request_id=confirmation,
        workflow_event=event,
        workflow_ref=ref,
        execution_count_before=count,
    )


def evaluate(
    request: dict[str, Any],
    approval: dict[str, Any],
    approval_status: dict[str, Any],
    status: dict[str, Any],
    request_hash: str,
    implementation_hash: str,
    wrapper_text: str,
    workflow_text: str,
) -> tuple[dict[str, bool], dict[str, Any]]:
    report = admission(
        request,
        approval,
        approval_status,
        request_hash,
        implementation_hash,
    )
    checks = {
        "admission_passes": report.get("formal_state") == runner.ADMISSION_STATE,
        "admission_checks_zero": report.get("checks_failed") == 0,
        "approval_status_exact": (
            approval_status.get("formal_state") == runner.APPROVAL_CURRENT_STATUS_STATE
        ),
        "request_hash_exact": request_hash == runner.REQUEST_SHA256,
        "implementation_hash_exact": implementation_hash == runner.IMPLEMENTATION_SHA256,
        "wrapper_state_binding_present": "core.READY_STATE = APPROVAL_CURRENT_STATUS_STATE" in wrapper_text,
        "wrapper_v1_delegate_present": (
            "run_historical_silver_source_gap_exception_integration_real_reference_validation_once_v1"
            in wrapper_text
        ),
        "workflow_uses_v2_validate": (
            "run_historical_silver_source_gap_exception_integration_real_reference_validation_once_v2.py"
            in workflow_text
        ),
        "workflow_uses_v2_twice": (
            workflow_text.count(
                "run_historical_silver_source_gap_exception_integration_real_reference_validation_once_v2.py"
            ) >= 3
        ),
        "workflow_manual_only": "workflow_dispatch:" in workflow_text,
        "workflow_main_only": "github.ref == 'refs/heads/main'" in workflow_text,
        "workflow_first_attempt_only": "github.run_attempt == 1" in workflow_text,
        "workflow_no_schedule": "schedule:" not in workflow_text,
        "workflow_no_push": "\n  push:" not in workflow_text,
        "workflow_no_pull_request": "pull_request:" not in workflow_text,
        "workflow_no_network": all(token not in workflow_text for token in ("curl ", "wget ", "pip install")),
        "status_schema": status.get("schema_version") == STATUS_SCHEMA,
        "status_state": status.get("formal_state") == READY,
        "status_request": status.get("request_id") == runner.REQUEST_ID,
        "status_wrapper": status.get("runner") == WRAPPER_PATH,
        "status_workflow": status.get("manual_workflow") == WORKFLOW_PATH,
        "status_failure_before_execution": status.get("failed_dispatch_reached_execution_step") is False,
        "status_governed_inputs_read_false": status.get("failed_dispatch_governed_inputs_read") is False,
        "status_request_not_consumed": status.get("request_consumed") is False,
        "status_execution_count_zero": status.get("execution_count") == 0,
        "status_maximum_one": status.get("maximum_execution_count") == 1,
        "status_ready_retry": status.get("ready_for_manual_retry") is True,
        "status_repeat_false": status.get("repeat_execution_allowed") is False,
        "status_automatic_false": status.get("automatic_dispatch_allowed") is False,
        "status_stake_zero": status.get("formal_stake") == 0,
    }
    return checks, report


def mutation_tests(
    request: dict[str, Any],
    approval: dict[str, Any],
    approval_status: dict[str, Any],
    request_hash: str,
    implementation_hash: str,
) -> dict[str, bool]:
    tests: dict[str, bool] = {}

    def blocked(
        req: dict[str, Any] | None = None,
        app: dict[str, Any] | None = None,
        app_status: dict[str, Any] | None = None,
        req_hash: str | None = None,
        impl_hash: str | None = None,
        confirmation: str = runner.REQUEST_ID,
        event: str = "workflow_dispatch",
        ref: str = "refs/heads/main",
        count: int = 0,
    ) -> bool:
        result = admission(
            req or request,
            app or approval,
            app_status or approval_status,
            req_hash or request_hash,
            impl_hash or implementation_hash,
            confirmation,
            event,
            ref,
            count,
        )
        return result.get("formal_state") != runner.ADMISSION_STATE

    bad_status = copy.deepcopy(approval_status)
    bad_status["formal_state"] = (
        "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_"
        "REAL_REFERENCE_VALIDATION_APPROVAL_VALID"
    )
    tests["wrong_approval_lifecycle_state_blocks"] = blocked(app_status=bad_status)
    tests["wrong_request_hash_blocks"] = blocked(req_hash="sha256:wrong")
    tests["wrong_implementation_hash_blocks"] = blocked(impl_hash="sha256:wrong")
    tests["wrong_confirmation_blocks"] = blocked(confirmation="WRONG")
    tests["wrong_event_blocks"] = blocked(event="push")
    tests["wrong_ref_blocks"] = blocked(ref="refs/heads/dev")
    tests["nonzero_execution_count_blocks"] = blocked(count=1)

    bad_approval = copy.deepcopy(approval)
    bad_approval["approved_by"] = "other"
    tests["wrong_owner_blocks"] = blocked(app=bad_approval)

    bad_approval = copy.deepcopy(approval)
    bad_approval["execution_authorization"]["maximum_execution_count"] = 2
    tests["maximum_two_blocks"] = blocked(app=bad_approval)

    bad_approval = copy.deepcopy(approval)
    bad_approval["execution_authorization"]["automatic_dispatch_allowed"] = True
    tests["automatic_dispatch_blocks"] = blocked(app=bad_approval)

    bad_approval = copy.deepcopy(approval)
    bad_approval["formal_stake"] = 1
    tests["nonzero_approval_stake_blocks"] = blocked(app=bad_approval)

    bad_request = copy.deepcopy(request)
    bad_request["formal_stake"] = 1
    tests["nonzero_request_stake_blocks"] = blocked(req=bad_request)

    bad_status = copy.deepcopy(approval_status)
    bad_status["approval_granted"] = False
    tests["approval_not_granted_blocks"] = blocked(app_status=bad_status)

    bad_status = copy.deepcopy(approval_status)
    bad_status["formal_stake"] = 1
    tests["nonzero_status_stake_blocks"] = blocked(app_status=bad_status)

    return tests


def write_json(path: Path, value: dict[str, Any]) -> None:
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if len(payload.encode("utf-8")) > 1_048_576:
        raise RuntimeError("validation report exceeds 1 MiB")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--approval-status", type=Path, required=True)
    parser.add_argument("--implementation", type=Path, required=True)
    parser.add_argument("--runner", type=Path, required=True)
    parser.add_argument("--manual-workflow", type=Path, required=True)
    parser.add_argument("--status", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    request = read_json(args.request)
    approval = read_json(args.approval)
    approval_status = read_json(args.approval_status)
    status = read_json(args.status)
    request_hash = runner.sha256_file(args.request)
    implementation_hash = runner.sha256_file(args.implementation)
    wrapper_text = args.runner.read_text(encoding="utf-8")
    workflow_text = args.manual_workflow.read_text(encoding="utf-8")

    checks, admission_report = evaluate(
        request,
        approval,
        approval_status,
        status,
        request_hash,
        implementation_hash,
        wrapper_text,
        workflow_text,
    )
    mutations = mutation_tests(
        request,
        approval,
        approval_status,
        request_hash,
        implementation_hash,
    )
    failed_checks = sorted(name for name, passed in checks.items() if not passed)
    failed_mutations = sorted(name for name, passed in mutations.items() if not passed)
    valid = not failed_checks and not failed_mutations

    report = {
        "schema_version": "historical-silver-source-gap-exception-real-reference-validation-admission-fix-validation-v1",
        "formal_state": READY if valid else BLOCKED,
        "admission_fix_valid": valid,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed_checks),
        "checks_failed": len(failed_checks),
        "failed_checks": failed_checks,
        "mutation_tests_run": len(mutations),
        "mutation_tests_passed": len(mutations) - len(failed_mutations),
        "failed_mutation_tests": failed_mutations,
        "admission_report": admission_report,
        "failed_dispatch_reached_execution_step": False,
        "failed_dispatch_governed_inputs_read": False,
        "execution_count": 0,
        "maximum_execution_count": 1,
        "request_consumed": False,
        "ready_for_manual_retry": valid,
        "real_reference_validation_executed": False,
        "database_access": False,
        "network_access": False,
        "source_archive_access": False,
        "raw_rows_read": False,
        "raw_rows_emitted": 0,
        "formal_stake": 0,
    }
    write_json(args.output, report)
    print(json.dumps({
        "formal_state": report["formal_state"],
        "checks_failed": report["checks_failed"],
        "mutation_tests_passed": report["mutation_tests_passed"],
        "request_consumed": report["request_consumed"],
        "formal_stake": 0,
    }, ensure_ascii=False, indent=2))
    return 0 if valid else 2


if __name__ == "__main__":
    raise SystemExit(main())
