#!/usr/bin/env python3
"""Validate explicit approval for Legacy Market Archive retry request 002.

Policy-only validator: no network, no real candidate/reference reads, no execution.
"""
from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REQUEST_ID = "LEGACY-MARKET-ARCHIVE-AUDIT-2026-07-21-002"
REQUEST_SCHEMA = "legacy-market-real-file-audit-retry-request-002-v1"
APPROVAL_SCHEMA = "legacy-market-real-file-audit-retry-002-approval-v1"
READY = "LEGACY_MARKET_ARCHIVE_REAL_FILE_AUDIT_RETRY_002_APPROVAL_VALID_READY_FOR_MANUAL_DISPATCH"
BLOCKED = "LEGACY_MARKET_ARCHIVE_REAL_FILE_AUDIT_RETRY_002_APPROVAL_BLOCKED"
SOURCE_ID = "kaggle_cviaxmiwnptr_nba_betting_data_user_supplied"
EXPECTED_DATASET = "cviaxmiwnptr/nba-betting-data-october-2007-to-june-2024"
EXPECTED_FILE = "nba_2008-2026.csv"
EXPECTED_BYTES = 2493308
EXPECTED_SHA256 = "729eb2ead85c14affbb81ae9a4c611fee9790b8dd3d1d7824e1ddba14410a8c4"
EXPECTED_YEARS = [2019, 2020, 2021, 2022, 2023]
EXPECTED_RESPONSE = (
    "我核准 request LEGACY-MARKET-ARCHIVE-AUDIT-2026-07-21-002 執行一次修復後的 workflow_dispatch "
    "aggregate-only Legacy Market Archive 真實檔案 cross-source audit。此重試只修正暫存 reference 目錄建立問題；"
    "candidate identity、五季 Historical Silver／Gold 範圍、deterministic join、frozen gates 與 aggregate-only 邊界不得改變。"
    "不得上傳原始 CSV、資料庫、來源 archive、逐場資料、unmatched keys 或 game IDs；不得解鎖 Opening／Closing、"
    "PIT market backtest、CLV、EV、ROI、Drawdown、模型重訓、betting edge 或非 0 Stake。"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def validate(
    request: dict[str, Any],
    approval: dict[str, Any],
    implementation: dict[str, Any],
    policy: dict[str, Any],
    current: dict[str, Any],
    confirmation_request_id: str,
    workflow_event: str,
    workflow_ref: str,
) -> dict[str, Any]:
    checks: dict[str, bool] = {}

    def check(name: str, condition: Any) -> None:
        checks[name] = bool(condition)

    check("request_schema", request.get("schema_version") == REQUEST_SCHEMA)
    check("request_id", request.get("request_id") == REQUEST_ID)
    check("request_state", request.get("state") == "AWAITING_EXPLICIT_USER_APPROVAL")
    check("request_previous_id", request.get("previous_request_id") == "LEGACY-MARKET-ARCHIVE-AUDIT-2026-07-21-001")
    check("request_previous_run", request.get("previous_run_id") == 29804975869)
    check("request_previous_blocked", request.get("previous_result") == "BLOCKED_BEFORE_SCIENTIFIC_RESULT")
    check("request_repair_commit", request.get("repair_commit") == "613ce3a6232780c486d899b02dd7a99e799b0a27")
    check("request_repair_entrypoint", request.get("repair_entrypoint") == "scripts/run_user_supplied_legacy_market_archive_real_file_audit_once_v1_1.py")
    check("request_one_time", request.get("one_time_only") is True)
    check("request_max_one", request.get("maximum_execution_count") == 1)
    check("request_dispatch_only", request.get("workflow_dispatch_only") is True)
    check("request_not_preapproved", request.get("approval_granted") is False)
    check("request_execution_disabled", request.get("execution_enabled") is False)
    check("request_execution_zero", request.get("execution_count") == 0)
    for key in (
        "candidate_identity_changed",
        "reference_scope_changed",
        "scientific_contract_changed",
        "frozen_gates_changed",
        "output_boundary_changed",
        "raw_files_uploaded",
    ):
        check(f"request_{key}_false", request.get(key) is False)
    check("request_raw_rows_zero", request.get("raw_rows_emitted") == 0)
    check("request_stake_zero", request.get("formal_stake") == 0)

    check("approval_schema", approval.get("schema_version") == APPROVAL_SCHEMA)
    check("approval_id", approval.get("request_id") == REQUEST_ID)
    check("approval_state", approval.get("approval_state") == "EXPLICIT_USER_APPROVAL_GRANTED")
    check("approval_owner", approval.get("approved_by") == "qoo109")
    check("approval_owner_role", approval.get("approved_by_role") == "repository_owner_user")
    check("approval_channel", approval.get("approval_channel") == "ChatGPT project conversation")
    check("approval_exact_response", approval.get("user_response") == EXPECTED_RESPONSE)

    context = approval.get("context_binding", {})
    check("approval_request_packet", context.get("request_packet") == "data/research/legacy-market-real-file-audit-retry-request-002-v1.json")
    check("approval_request_state", context.get("request_packet_state") == "AWAITING_EXPLICIT_USER_APPROVAL")
    check("approval_request_pr", context.get("request_packet_merge_pr") == 112)
    check("approval_request_commit", context.get("request_packet_main_commit") == "3805bfb6ccc6fe13bd46c40e523eb225fd7ee506")
    check("approval_validation_run", context.get("request_validation_workflow_run_id") == 29807027441)
    check("approval_validation_job", context.get("request_validation_job_id") == 88559621609)
    check("approval_repair_pr", context.get("repair_pr") == 111)
    check("approval_repair_commit", context.get("repair_commit") == "613ce3a6232780c486d899b02dd7a99e799b0a27")
    check("approval_previous_run", context.get("previous_run_id") == 29804975869)

    authorization = approval.get("execution_authorization", {})
    check("approval_one_time", authorization.get("one_time_only") is True)
    check("approval_max_one", authorization.get("maximum_execution_count") == 1)
    check("approval_prior_zero", authorization.get("executions_recorded_before_approval") == 0)
    check("approval_dispatch_only", authorization.get("workflow_dispatch_only") is True)
    check("approval_main_ref", authorization.get("approved_ref") == "refs/heads/main")
    check("approval_dataset", authorization.get("dataset_handle") == EXPECTED_DATASET)
    check("approval_file", authorization.get("exact_candidate_file") == EXPECTED_FILE)
    check("approval_bytes", authorization.get("candidate_file_bytes") == EXPECTED_BYTES)
    check("approval_sha", authorization.get("candidate_file_sha256") == EXPECTED_SHA256)
    check("approval_years", authorization.get("reference_season_start_years") == EXPECTED_YEARS)
    check("approval_network", authorization.get("temporary_network_download_allowed") is True)
    check("approval_candidate_read", authorization.get("temporary_candidate_rows_may_be_read") is True)
    check("approval_reference_read", authorization.get("temporary_reference_rows_may_be_read") is True)
    check("approval_rebuild", authorization.get("temporary_reference_rebuild_allowed") is True)
    check("approval_aggregate", authorization.get("aggregate_outputs_only") is True)
    check("approval_output_one", authorization.get("maximum_public_output_files") == 1)
    check("approval_output_size", authorization.get("maximum_public_output_bytes") == 1048576)
    check("approval_execution_enabled", authorization.get("execution_enabled_for_this_request") is True)
    check("approval_confirmation", approval.get("required_confirmation_input") == REQUEST_ID)

    acknowledgements = approval.get("acknowledgements", {})
    for key in (
        "candidate_identity_changed",
        "reference_scope_changed",
        "scientific_contract_changed",
        "frozen_gates_changed",
        "output_boundary_changed",
        "raw_rows_or_raw_files_may_be_uploaded_as_artifact",
        "candidate_csv_may_be_uploaded_as_artifact",
        "historical_silver_database_may_be_uploaded_as_artifact",
        "historical_gold_database_may_be_uploaded_as_artifact",
        "source_archives_may_be_uploaded_as_artifact",
        "unmatched_keys_or_game_ids_may_be_emitted",
        "opening_or_closing_labels_authorized",
        "point_in_time_market_backtest_authorized",
        "clv_ev_roi_drawdown_authorized",
        "historical_silver_replacement_authorized",
        "historical_gold_replacement_authorized",
        "model_training_or_retraining_authorized",
        "betting_edge_claim_authorized",
        "betting_decision_layer_authorized",
    ):
        check(f"approval_{key}_false", acknowledgements.get(key) is False)
    check("approval_stake_zero", acknowledgements.get("formal_stake") == 0)

    next_state = approval.get("next_state_if_approval_validation_passes", {})
    check("approval_next_state", next_state.get("formal_state") == READY)
    check("approval_ready_once", next_state.get("ready_for_one_time_aggregate_execution") is True)
    check("approval_no_repeat", next_state.get("ready_for_repeat_execution") is False)
    check("approval_no_market", next_state.get("ready_for_point_in_time_market_backtest") is False)
    check("approval_no_model", next_state.get("ready_for_model_retraining") is False)
    check("approval_no_edge", next_state.get("ready_for_betting_edge_claim") is False)
    check("approval_next_stake_zero", next_state.get("formal_stake") == 0)

    candidate = implementation.get("candidate_input", {})
    check("implementation_source", implementation.get("source_id") == SOURCE_ID)
    check("implementation_file", candidate.get("file_name") == EXPECTED_FILE)
    check("implementation_bytes", candidate.get("file_bytes") == EXPECTED_BYTES)
    check("implementation_sha", candidate.get("file_sha256") == EXPECTED_SHA256)
    check("implementation_no_derived", candidate.get("cleaned_or_derived_file_substitution_allowed") is False)
    check("implementation_not_executed", implementation.get("validation_mode", {}).get("real_file_audit_executed") is False)
    check("implementation_stake_zero", implementation.get("downstream_permissions", {}).get("formal_stake") == 0)

    source = policy.get("candidate_source", {})
    check("policy_source", source.get("source_id") == SOURCE_ID)
    check("policy_dataset", source.get("dataset_handle") == EXPECTED_DATASET)
    check("policy_file", source.get("file_name") == EXPECTED_FILE)
    check("policy_bytes", source.get("file_bytes") == EXPECTED_BYTES)
    check("policy_sha", source.get("file_sha256") == EXPECTED_SHA256)
    check("policy_join", policy.get("deterministic_join_contract", {}).get("join_key") == ["game_date", "home_team_abbr", "away_team_abbr"])
    check("policy_no_fuzzy", policy.get("deterministic_join_contract", {}).get("fuzzy_matching_allowed") is False)

    retry = current.get("retry_request", {})
    check("current_source", current.get("source_id") == SOURCE_ID)
    check("current_role", current.get("current_formal_outcome") == "ROLE_LIMITED_LEGACY_MARKET_ARCHIVE_ELIGIBLE")
    check("current_retry_id", retry.get("request_id") == REQUEST_ID)
    check("current_retry_waiting", retry.get("state") == "AWAITING_EXPLICIT_USER_APPROVAL")
    check("current_retry_not_approved", retry.get("approval_granted") is False)
    check("current_retry_disabled", retry.get("execution_enabled") is False)
    check("current_retry_count_zero", retry.get("execution_count") == 0)
    check("current_real_not_executed", current.get("real_cross_source_audit_executed") is False)
    check("current_stake_zero", current.get("formal_stake") == 0)

    check("runtime_request", confirmation_request_id == REQUEST_ID)
    check("runtime_event", workflow_event == "workflow_dispatch")
    check("runtime_ref", workflow_ref == "refs/heads/main")

    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": "legacy-market-real-file-audit-retry-002-approval-validation-report-v1",
        "validated_at": utc_now(),
        "request_id": REQUEST_ID,
        "formal_state": READY if not failed else BLOCKED,
        "checks": checks,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "checks_failed": len(failed),
        "failed_checks": failed,
        "ready_for_one_time_aggregate_execution": not failed,
        "ready_for_repeat_execution": False,
        "network_calls_made": False,
        "real_candidate_csv_read": False,
        "real_reference_database_read": False,
        "raw_rows_emitted": 0,
        "raw_files_emitted": False,
        "ready_for_point_in_time_market_backtest": False,
        "ready_for_model_retraining": False,
        "ready_for_betting_edge_claim": False,
        "formal_stake": 0,
    }


def self_test(request, approval, implementation, policy, current) -> dict[str, bool]:
    baseline = validate(request, approval, implementation, policy, current, REQUEST_ID, "workflow_dispatch", "refs/heads/main")
    assert baseline["formal_state"] == READY, baseline
    tests = {"baseline_passes": True}
    cases = {
        "wrong_request_blocks": ("runtime", "WRONG"),
        "wrong_ref_blocks": ("ref", "refs/heads/dev"),
        "approval_revocation_blocks": ("approval", "REVOKED"),
        "repeat_permission_blocks": ("repeat", 2),
        "raw_artifact_permission_blocks": ("raw", True),
        "nonzero_stake_blocks": ("stake", 1),
        "repair_commit_drift_blocks": ("repair", "0" * 40),
    }
    for name, (kind, value) in cases.items():
        req = copy.deepcopy(request)
        app = copy.deepcopy(approval)
        confirmation = REQUEST_ID
        event = "workflow_dispatch"
        ref = "refs/heads/main"
        if kind == "runtime": confirmation = value
        elif kind == "ref": ref = value
        elif kind == "approval": app["approval_state"] = value
        elif kind == "repeat": app["execution_authorization"]["maximum_execution_count"] = value
        elif kind == "raw": app["acknowledgements"]["candidate_csv_may_be_uploaded_as_artifact"] = value
        elif kind == "stake": app["acknowledgements"]["formal_stake"] = value
        elif kind == "repair": req["repair_commit"] = value
        result = validate(req, app, implementation, policy, current, confirmation, event, ref)
        tests[name] = result["formal_state"] == BLOCKED
    assert all(tests.values()), tests
    return tests


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--implementation", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--current-status", type=Path, required=True)
    parser.add_argument("--confirmation-request-id", default=REQUEST_ID)
    parser.add_argument("--workflow-event", default="workflow_dispatch")
    parser.add_argument("--workflow-ref", default="refs/heads/main")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    request = read_json(args.request)
    approval = read_json(args.approval)
    implementation = read_json(args.implementation)
    policy = read_json(args.policy)
    current = read_json(args.current_status)
    report = validate(
        request, approval, implementation, policy, current,
        args.confirmation_request_id, args.workflow_event, args.workflow_ref,
    )
    if args.self_test:
        report["self_tests"] = self_test(request, approval, implementation, policy, current)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if len(payload.encode("utf-8")) > 1048576:
        raise RuntimeError("approval report exceeds 1 MiB")
    args.output.write_text(payload, encoding="utf-8")
    print(json.dumps({
        "formal_state": report["formal_state"],
        "checks_passed": report["checks_passed"],
        "checks_total": report["checks_total"],
        "formal_stake": report["formal_stake"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["formal_state"] == READY else 1


if __name__ == "__main__":
    raise SystemExit(main())
