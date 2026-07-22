#!/usr/bin/env python3
"""Validate explicit approval for one aggregate-only real-reference validation.

This validator reads only the request, request status, approval record, and
transformer source bytes needed for immutable SHA-256 binding. It does not read
real-reference inputs and does not execute the transformer.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

REQUEST_ID = (
    "HISTORICAL-SILVER-2023-24-SOURCE-GAP-EXCEPTION-INTEGRATION-"
    "REAL-REFERENCE-VALIDATION-2026-07-22-001"
)
REQUEST_SCHEMA = (
    "historical-silver-2023-24-source-gap-exception-integration-"
    "real-reference-validation-request-v1"
)
APPROVAL_SCHEMA = (
    "historical-silver-2023-24-source-gap-exception-integration-"
    "real-reference-validation-approval-v1"
)
REQUEST_READY_STATE = (
    "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_"
    "REAL_REFERENCE_VALIDATION_REQUEST_VALID_AWAITING_EXPLICIT_USER_APPROVAL"
)
APPROVAL_READY_STATE = (
    "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_"
    "REAL_REFERENCE_VALIDATION_APPROVAL_VALID"
)
BLOCKED_STATE = (
    "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_"
    "REAL_REFERENCE_VALIDATION_APPROVAL_STRUCTURAL_BLOCKED"
)
EXPECTED_REQUEST_SHA256 = (
    "sha256:192a06862fe830027686d149d36572b4ad76ea609f489c6a3d540b7ea4b27e97"
)
EXPECTED_IMPLEMENTATION_SHA256 = (
    "sha256:c4bd7ccb05bcf78747a7210e0eefad083d599de2ca8b0d44c9c455006f084cbc"
)
EXPECTED_ARTIFACT_DIGEST = (
    "sha256:63f5ca853727d2530cff9bc9bf1b6eb92b3a1841f90668ecdcfb0a01018b9200"
)
EXPECTED_ALLOWED_INPUTS = {
    "aggregate_coverage_report": (
        "data/research/historical-gold-silver-coverage-real-reference-result-v1.json"
    ),
    "exception_manifest": (
        "data/research/historical-silver-2023-24-source-gap-exception-manifest-v1.json"
    ),
    "integration_policy": (
        "data/research/historical-silver-2023-24-source-gap-exception-"
        "integration-policy-v1.json"
    ),
}
EXPECTED_PROHIBITED_FIELDS = [
    "game_id",
    "game_date",
    "home_team_abbr",
    "away_team_abbr",
    "team_code",
    "source_file_path",
    "source_file_hash",
    "row_level_record",
    "row_key_hash",
]


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate(
    request: dict[str, Any],
    request_status: dict[str, Any],
    approval: dict[str, Any],
    request_sha256: str,
    implementation_sha256: str,
) -> dict[str, Any]:
    checks: dict[str, bool] = {}

    def check(name: str, value: Any) -> None:
        checks[name] = bool(value)

    check("request_schema", request.get("schema_version") == REQUEST_SCHEMA)
    check("request_id", request.get("request_id") == REQUEST_ID)
    check("request_role", request.get("request_role") == "ONE_TIME_AGGREGATE_ONLY_REAL_REFERENCE_VALIDATION_REQUEST")
    check("request_status_state", request_status.get("formal_state") == REQUEST_READY_STATE)
    check("request_status_id", request_status.get("request_id") == REQUEST_ID)
    check("request_status_approval_false", request_status.get("approval_granted") is False)
    check("request_status_execution_false", request_status.get("execution_enabled") is False)
    check("request_status_count_zero", request_status.get("execution_count") == 0)
    check("request_status_max_one", request_status.get("maximum_execution_count") == 1)

    control = request.get("execution_control", {})
    check("request_count_zero", control.get("execution_count") == 0)
    check("request_max_one", control.get("maximum_execution_count") == 1)
    check("request_not_consumed", control.get("request_consumed") is False)
    check("request_no_repeat", control.get("repeat_execution_allowed") is False)
    check("request_dispatch_only", control.get("workflow_dispatch_only") is True)
    check("request_no_auto_dispatch", control.get("automatic_dispatch_allowed") is False)
    check("request_approval_required", control.get("explicit_user_approval_required") is True)
    check("request_does_not_grant_approval", control.get("approval_granted") is False)
    check("request_execution_disabled", control.get("execution_enabled") is False)
    check("request_workflow_absent", control.get("execution_workflow_created") is False)
    check("request_not_executed", control.get("real_reference_validation_executed") is False)

    allowed = request.get("allowed_committed_inputs", {})
    for key, expected in EXPECTED_ALLOWED_INPUTS.items():
        check(f"request_input_{key}", allowed.get(key) == expected)
    for key in (
        "additional_input_paths_allowed",
        "database_files_allowed",
        "source_archives_allowed",
        "raw_csv_allowed",
        "raw_rows_allowed",
        "network_download_allowed",
        "temporary_reference_rebuild_allowed",
    ):
        check(f"request_forbids_{key}", allowed.get(key) is False)

    check("approval_schema", approval.get("schema_version") == APPROVAL_SCHEMA)
    check("approval_request_id", approval.get("request_id") == REQUEST_ID)
    check("approval_state", approval.get("approval_state") == "EXPLICIT_USER_APPROVAL_GRANTED")
    check("approved_by", approval.get("approved_by") == "qoo109")
    check("approved_by_role", approval.get("approved_by_role") == "repository_owner_user")
    check("approval_channel", approval.get("approval_channel") == "ChatGPT project conversation")
    check("user_response", approval.get("user_response_exact") == "好的繼續")

    context = approval.get("approval_context", {})
    check(
        "approval_context",
        context.get("immediately_preceding_request")
        == "我批准 Request 001 依已驗證的 Request SHA-256 與 Transformer SHA-256，建立單次 aggregate-only real-reference validation 執行流程；最大執行次數 1，Stake 維持 0。",
    )
    check(
        "approval_interpretation",
        context.get("interpretation")
        == "EXPLICIT_AFFIRMATION_OF_IMMEDIATELY_PRECEDING_APPROVAL_REQUEST",
    )
    check("approval_no_scope_expansion", context.get("scope_expansion_allowed") is False)

    bindings = approval.get("immutable_bindings", {})
    check("binding_request_file", bindings.get("request_file") == "data/research/historical-silver-2023-24-source-gap-exception-integration-real-reference-validation-request-v1.json")
    check("binding_request_hash_declared", bindings.get("request_file_sha256") == EXPECTED_REQUEST_SHA256)
    check("binding_request_hash_computed", request_sha256 == EXPECTED_REQUEST_SHA256)
    check("binding_implementation_file", bindings.get("implementation_file") == "scripts/integrate_historical_silver_source_gap_exception_v1.py")
    check("binding_implementation_hash_declared", bindings.get("implementation_file_sha256") == EXPECTED_IMPLEMENTATION_SHA256)
    check("binding_implementation_hash_computed", implementation_sha256 == EXPECTED_IMPLEMENTATION_SHA256)
    check("binding_run", bindings.get("request_validation_workflow_run_id") == 29913352533)
    check("binding_artifact", bindings.get("request_validation_artifact_id") == 8526880141)
    check("binding_artifact_digest", bindings.get("request_validation_artifact_digest") == EXPECTED_ARTIFACT_DIGEST)
    check("binding_pr", bindings.get("request_merge_pr") == 127)
    check("binding_commit", bindings.get("request_main_commit") == "5b29843a5cb3c7b680e049206d6eb9c6fd994ea0")
    check("binding_mutations", bindings.get("mutation_tests_passed") == 15)

    auth = approval.get("execution_authorization", {})
    check("approval_one_time", auth.get("one_time_only") is True)
    check("approval_max_one", auth.get("maximum_execution_count") == 1)
    check("approval_count_zero", auth.get("executions_recorded_before_approval") == 0)
    check("approval_dispatch_only", auth.get("workflow_dispatch_only") is True)
    check("approval_no_auto_dispatch", auth.get("automatic_dispatch_allowed") is False)
    check("approval_main_ref", auth.get("approved_ref") == "refs/heads/main")
    check("approval_workflow_creation", auth.get("approved_to_create_one_time_execution_workflow") is True)
    check("approval_execution_still_disabled", auth.get("real_reference_validation_execution_enabled_now") is False)
    check("approval_workflow_not_created", auth.get("execution_workflow_created_now") is False)
    check("approval_not_consumed", auth.get("request_consumed_now") is False)
    check("approval_no_repeat", auth.get("repeat_execution_allowed") is False)

    approval_inputs = approval.get("allowed_committed_inputs", {})
    for key, expected in EXPECTED_ALLOWED_INPUTS.items():
        check(f"approval_input_{key}", approval_inputs.get(key) == expected)
    for key in (
        "additional_input_paths_allowed",
        "database_files_allowed",
        "source_archives_allowed",
        "raw_csv_allowed",
        "raw_rows_allowed",
        "network_download_allowed",
        "temporary_reference_rebuild_allowed",
    ):
        check(f"approval_forbids_{key}", approval_inputs.get(key) is False)

    output = approval.get("output_authorization", {})
    check("output_single", output.get("single_json_artifact_only") is True)
    check("output_aggregate", output.get("aggregate_only") is True)
    check("output_size", output.get("maximum_output_bytes") == 1048576)
    check("output_no_rows", output.get("raw_rows_emitted") == 0)
    check("output_no_files", output.get("raw_files_emitted") is False)
    check("output_prohibited_fields", output.get("prohibited_fields") == EXPECTED_PROHIBITED_FIELDS)

    nonauth = approval.get("non_authorizations", {})
    for key in (
        "coverage_analyzer_replacement",
        "coverage_analyzer_modification",
        "transformer_modification",
        "silver_builder_change",
        "gold_builder_change",
        "silver_or_gold_database_write",
        "historical_silver_replacement",
        "historical_gold_replacement",
        "source_gap_row_patch",
        "manual_row_insertion",
        "cross_source_audit_rerun",
        "market_backtest",
        "opening_or_closing_semantics",
        "clv_ev_roi_drawdown",
        "model_training_or_retraining",
        "betting_edge_claim",
        "formal_stake_above_zero",
    ):
        check(f"nonauth_{key}", nonauth.get(key) is False)

    next_state = approval.get("next_state_if_approval_validation_passes", {})
    check("next_state", next_state.get("formal_state") == APPROVAL_READY_STATE)
    check("next_workflow_implementation", next_state.get("ready_for_one_time_execution_workflow_implementation") is True)
    check("next_execution_still_false", next_state.get("ready_for_real_reference_validation_execution") is False)
    check("next_no_repeat", next_state.get("ready_for_repeat_execution") is False)
    check("next_stake_zero", next_state.get("formal_stake") == 0)
    check("approval_stake_zero", approval.get("formal_stake") == 0)

    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": "historical-silver-2023-24-source-gap-exception-integration-real-reference-validation-approval-validation-report-v1",
        "request_id": REQUEST_ID,
        "formal_state": APPROVAL_READY_STATE if not failed else BLOCKED_STATE,
        "approval_valid": not failed,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "checks_failed": len(failed),
        "failed_checks": failed,
        "request_file_sha256": request_sha256,
        "implementation_file_sha256": implementation_sha256,
        "approval_granted": not failed,
        "execution_count": 0,
        "maximum_execution_count": 1,
        "execution_workflow_created": False,
        "execution_enabled": False,
        "real_reference_validation_executed": False,
        "ready_for_one_time_execution_workflow_implementation": not failed,
        "ready_for_real_reference_validation_execution": False,
        "aggregate_only": True,
        "database_access": False,
        "network_access": False,
        "source_archive_access": False,
        "real_reference_inputs_read": False,
        "transformer_executed": False,
        "raw_rows_read": False,
        "raw_rows_emitted": 0,
        "formal_stake": 0,
    }


def run_mutation_tests(
    request: dict[str, Any],
    request_status: dict[str, Any],
    approval: dict[str, Any],
    request_sha256: str,
    implementation_sha256: str,
) -> dict[str, bool]:
    baseline = evaluate(request, request_status, approval, request_sha256, implementation_sha256)
    if not baseline["approval_valid"]:
        raise AssertionError(baseline)

    tests: dict[str, bool] = {"baseline_passes": True}

    def mutated(name: str, mutate) -> None:
        req = copy.deepcopy(request)
        status = copy.deepcopy(request_status)
        app = copy.deepcopy(approval)
        req_hash = request_sha256
        impl_hash = implementation_sha256
        req, status, app, req_hash, impl_hash = mutate(req, status, app, req_hash, impl_hash)
        report = evaluate(req, status, app, req_hash, impl_hash)
        tests[name] = report["approval_valid"] is False

    mutated("wrong_request_id_blocks", lambda r, s, a, rh, ih: (r, s, {**a, "request_id": "WRONG"}, rh, ih))
    mutated("wrong_user_blocks", lambda r, s, a, rh, ih: (r, s, {**a, "approved_by": "other"}, rh, ih))
    mutated("wrong_response_blocks", lambda r, s, a, rh, ih: (r, s, {**a, "user_response_exact": "continue"}, rh, ih))
    mutated("wrong_request_hash_blocks", lambda r, s, a, rh, ih: (r, s, a, "sha256:wrong", ih))
    mutated("wrong_implementation_hash_blocks", lambda r, s, a, rh, ih: (r, s, a, rh, "sha256:wrong"))

    def change_auth(field: str, value: Any):
        def apply(r, s, a, rh, ih):
            a["execution_authorization"][field] = value
            return r, s, a, rh, ih
        return apply

    mutated("max_two_blocks", change_auth("maximum_execution_count", 2))
    mutated("count_one_blocks", change_auth("executions_recorded_before_approval", 1))
    mutated("automatic_dispatch_blocks", change_auth("automatic_dispatch_allowed", True))
    mutated("wrong_ref_blocks", change_auth("approved_ref", "refs/heads/dev"))
    mutated("premature_execution_enable_blocks", change_auth("real_reference_validation_execution_enabled_now", True))
    mutated("premature_workflow_blocks", change_auth("execution_workflow_created_now", True))

    def change_input(field: str, value: Any):
        def apply(r, s, a, rh, ih):
            a["allowed_committed_inputs"][field] = value
            return r, s, a, rh, ih
        return apply

    mutated("network_access_blocks", change_input("network_download_allowed", True))
    mutated("database_access_blocks", change_input("database_files_allowed", True))
    mutated("raw_rows_blocks", change_input("raw_rows_allowed", True))

    def nonzero_stake(r, s, a, rh, ih):
        a["formal_stake"] = 1
        return r, s, a, rh, ih

    mutated("nonzero_stake_blocks", nonzero_stake)

    if not all(tests.values()):
        raise AssertionError(tests)
    return tests


def write_json(path: Path, value: dict[str, Any]) -> None:
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if len(payload.encode("utf-8")) > 1048576:
        raise RuntimeError("approval validation report exceeds 1 MiB")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--request-status", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--implementation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    request = read_json(args.request)
    request_status = read_json(args.request_status)
    approval = read_json(args.approval)
    request_sha256 = sha256_file(args.request)
    implementation_sha256 = sha256_file(args.implementation)

    report = evaluate(
        request,
        request_status,
        approval,
        request_sha256,
        implementation_sha256,
    )
    tests = run_mutation_tests(
        request,
        request_status,
        approval,
        request_sha256,
        implementation_sha256,
    )
    report["mutation_tests"] = tests
    report["mutation_tests_passed"] = sum(1 for value in tests.values() if value)
    write_json(args.output, report)
    print(
        json.dumps(
            {
                "formal_state": report["formal_state"],
                "checks_failed": report["checks_failed"],
                "mutation_tests_passed": report["mutation_tests_passed"],
                "formal_stake": 0,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["approval_valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
