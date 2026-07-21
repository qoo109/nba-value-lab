#!/usr/bin/env python3
"""Validate explicit approval for the one-time Legacy Market Archive audit.

Policy-only validator. It performs no network calls, reads no candidate/reference rows,
and never executes the audit.
"""
from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REQUEST_ID = "LEGACY-MARKET-ARCHIVE-AUDIT-2026-07-21-001"
REQUEST_SCHEMA = "user-supplied-legacy-market-archive-real-file-audit-execution-request-v1"
APPROVAL_SCHEMA = "user-supplied-legacy-market-archive-real-file-audit-approval-v1"
READY = "LEGACY_MARKET_ARCHIVE_REAL_FILE_AUDIT_APPROVAL_VALID_READY_FOR_MANUAL_DISPATCH"
BLOCKED = "LEGACY_MARKET_ARCHIVE_REAL_FILE_AUDIT_APPROVAL_BLOCKED"
SOURCE_ID = "kaggle_cviaxmiwnptr_nba_betting_data_user_supplied"
EXPECTED_DATASET = "cviaxmiwnptr/nba-betting-data-october-2007-to-june-2024"
EXPECTED_FILE = "nba_2008-2026.csv"
EXPECTED_BYTES = 2493308
EXPECTED_SHA256 = "729eb2ead85c14affbb81ae9a4c611fee9790b8dd3d1d7824e1ddba14410a8c4"
EXPECTED_YEARS = [2019, 2020, 2021, 2022, 2023]
EXPECTED_USER_RESPONSE = (
    "我核准 request LEGACY-MARKET-ARCHIVE-AUDIT-2026-07-21-001 執行一次 workflow_dispatch 的 "
    "aggregate-only Legacy Market Archive 真實檔案 cross-source audit。核准範圍包含在暫存空間下載已確認的 "
    "Kaggle candidate、重建五季 Historical Silver／Gold、讀取暫存資料列並依 frozen deterministic gates 稽核；"
    "不得上傳原始 CSV、資料庫、來源 archive 或逐場資料，不得解鎖 Opening／Closing、PIT market backtest、"
    "CLV、EV、ROI、Drawdown、模型重訓、betting edge 或非 0 Stake。"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain one JSON object")
    return value


def validate_approval(
    request: dict[str, Any],
    approval: dict[str, Any],
    implementation: dict[str, Any],
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
    check("request_source", request.get("source_id") == SOURCE_ID)
    check("request_waiting_state", request.get("request_state") == "AWAITING_EXPLICIT_USER_APPROVAL")
    check("request_not_preapproved", request.get("approval_boundary", {}).get("approval_granted") is False)
    check("request_execution_disabled", request.get("approval_boundary", {}).get("execution_enabled") is False)
    scope = request.get("one_time_execution_scope", {})
    check("request_one_time", scope.get("one_time_only") is True)
    check("request_dispatch_only", scope.get("workflow_dispatch_only") is True)
    check("request_no_push", scope.get("automatic_main_push_execution_allowed") is False)
    check("request_no_pr_execution", scope.get("pull_request_execution_allowed") is False)
    check("request_no_schedule", scope.get("scheduled_execution_allowed") is False)
    check("request_max_execution_one", scope.get("maximum_execution_count") == 1)
    check("request_no_prior_execution", request.get("current_execution_boundary", {}).get("real_file_execution_count") == 0)
    check("request_no_prior_candidate_read", request.get("current_execution_boundary", {}).get("candidate_rows_read") is False)
    check("request_no_prior_reference_read", request.get("current_execution_boundary", {}).get("reference_rows_read") is False)
    check("request_stake_zero", request.get("current_execution_boundary", {}).get("formal_stake") == 0)

    candidate = request.get("frozen_candidate_identity", {})
    check("request_dataset", candidate.get("dataset_handle") == EXPECTED_DATASET)
    check("request_file", candidate.get("file_name") == EXPECTED_FILE)
    check("request_bytes", candidate.get("file_bytes") == EXPECTED_BYTES)
    check("request_sha256", candidate.get("file_sha256") == EXPECTED_SHA256)
    check("request_exact_identity", candidate.get("exact_identity_required") is True)
    check("request_no_derived_substitution", candidate.get("cleaned_or_derived_substitution_allowed") is False)
    check("request_reference_years", request.get("frozen_reference_scope", {}).get("season_start_years") == EXPECTED_YEARS)

    check("approval_schema", approval.get("schema_version") == APPROVAL_SCHEMA)
    check("approval_id", approval.get("request_id") == REQUEST_ID)
    check("approval_state", approval.get("approval_state") == "EXPLICIT_USER_APPROVAL_GRANTED")
    check("approval_owner", approval.get("approved_by") == "qoo109")
    check("approval_owner_role", approval.get("approved_by_role") == "repository_owner_user")
    check("approval_channel", approval.get("approval_channel") == "ChatGPT project conversation")
    check("approval_exact_user_response", approval.get("user_response") == EXPECTED_USER_RESPONSE)
    context = approval.get("context_binding", {})
    check("approval_request_packet", context.get("request_packet") == "data/research/user-supplied-legacy-market-archive-real-file-audit-execution-request-v1.json")
    check("approval_request_state", context.get("request_packet_state") == "AWAITING_EXPLICIT_USER_APPROVAL")
    check("approval_request_pr", context.get("request_packet_merge_pr") == 109)
    check("approval_request_commit", context.get("request_packet_main_commit") == "0a30b2c1ca77cd2856f69265c3fc9f875af2a587")
    check("approval_validation_run", context.get("request_validation_workflow_run_id") == 29799732000)
    check("approval_validation_artifact", context.get("request_validation_artifact_id") == 8483294031)
    check(
        "approval_validation_digest",
        context.get("request_validation_artifact_digest")
        == "sha256:fd739cde2d628db33ca74a53e0b9d7d69c20209bfb789cf76184f19854b95c1c",
    )

    authorization = approval.get("execution_authorization", {})
    check("approval_one_time", authorization.get("one_time_only") is True)
    check("approval_max_execution_one", authorization.get("maximum_execution_count") == 1)
    check("approval_no_prior_execution", authorization.get("executions_recorded_before_approval") == 0)
    check("approval_dispatch_only", authorization.get("workflow_dispatch_only") is True)
    check("approval_main_ref", authorization.get("approved_ref") == "refs/heads/main")
    check("approval_dataset", authorization.get("dataset_handle") == EXPECTED_DATASET)
    check("approval_file", authorization.get("exact_candidate_file") == EXPECTED_FILE)
    check("approval_bytes", authorization.get("candidate_file_bytes") == EXPECTED_BYTES)
    check("approval_sha256", authorization.get("candidate_file_sha256") == EXPECTED_SHA256)
    check("approval_years", authorization.get("reference_season_start_years") == EXPECTED_YEARS)
    check("approval_network", authorization.get("temporary_network_download_allowed") is True)
    check("approval_candidate_read", authorization.get("temporary_candidate_rows_may_be_read") is True)
    check("approval_reference_read", authorization.get("temporary_reference_rows_may_be_read") is True)
    check("approval_reference_rebuild", authorization.get("temporary_reference_rebuild_allowed") is True)
    check("approval_aggregate_only", authorization.get("aggregate_outputs_only") is True)
    check("approval_output_files", authorization.get("maximum_public_output_files") == 1)
    check("approval_output_bytes", authorization.get("maximum_public_output_bytes") == 1048576)
    check("approval_execution_enabled", authorization.get("execution_enabled_for_this_request") is True)
    check("approval_confirmation", approval.get("required_confirmation_input") == REQUEST_ID)

    acknowledgements = approval.get("acknowledgements", {})
    for key in (
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
        check(f"approval_no_{key}", acknowledgements.get(key) is False)
    check("approval_stake_zero", acknowledgements.get("formal_stake") == 0)

    next_state = approval.get("next_state_if_approval_validation_passes", {})
    check("approval_next_state", next_state.get("formal_state") == READY)
    check("approval_ready_once", next_state.get("ready_for_one_time_aggregate_execution") is True)
    check("approval_no_repeat", next_state.get("ready_for_repeat_execution") is False)
    check("approval_no_market", next_state.get("ready_for_point_in_time_market_backtest") is False)
    check("approval_no_model", next_state.get("ready_for_model_retraining") is False)
    check("approval_no_edge", next_state.get("ready_for_betting_edge_claim") is False)
    check("approval_next_stake_zero", next_state.get("formal_stake") == 0)

    check("runtime_request_id", confirmation_request_id == REQUEST_ID)
    check("runtime_dispatch", workflow_event == "workflow_dispatch")
    check("runtime_main", workflow_ref == "refs/heads/main")

    check("implementation_source", implementation.get("source_id") == SOURCE_ID)
    check(
        "implementation_request_ready",
        implementation.get("next_state_if_validation_passes", {}).get("ready_for_separate_real_file_execution_request") is True,
    )
    check("implementation_not_executed", implementation.get("validation_mode", {}).get("real_file_audit_executed") is False)
    check("implementation_no_model", implementation.get("downstream_permissions", {}).get("ready_for_model_retraining") is False)
    check("implementation_stake_zero", implementation.get("downstream_permissions", {}).get("formal_stake") == 0)

    check("current_source", current.get("source_id") == SOURCE_ID)
    check("current_role", current.get("current_formal_outcome") == "ROLE_LIMITED_LEGACY_MARKET_ARCHIVE_ELIGIBLE")
    check("current_not_executed", current.get("real_cross_source_audit_executed") is False)
    check("current_stake_zero", current.get("formal_stake") == 0)

    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": "user-supplied-legacy-market-archive-real-file-audit-approval-validation-v1",
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


def self_test(
    request: dict[str, Any],
    approval: dict[str, Any],
    implementation: dict[str, Any],
    current: dict[str, Any],
) -> dict[str, bool]:
    baseline = validate_approval(
        request, approval, implementation, current, REQUEST_ID, "workflow_dispatch", "refs/heads/main"
    )
    assert baseline["formal_state"] == READY, baseline
    cases = {
        "wrong_request_id_blocks": ("runtime_request_id", lambda a: a),
        "wrong_event_blocks": ("runtime_event", lambda a: a),
        "wrong_ref_blocks": ("runtime_ref", lambda a: a),
        "approval_revocation_blocks": ("approval", lambda a: a),
        "repeat_count_blocks": ("repeat", lambda a: a),
        "raw_artifact_permission_blocks": ("raw", lambda a: a),
        "nonzero_stake_blocks": ("stake", lambda a: a),
    }
    results = {"baseline_passes": True}
    for name, (kind, _) in cases.items():
        approval_copy = copy.deepcopy(approval)
        confirmation = REQUEST_ID
        event = "workflow_dispatch"
        ref = "refs/heads/main"
        if kind == "runtime_request_id":
            confirmation = "WRONG"
        elif kind == "runtime_event":
            event = "push"
        elif kind == "runtime_ref":
            ref = "refs/heads/dev"
        elif kind == "approval":
            approval_copy["approval_state"] = "REVOKED"
        elif kind == "repeat":
            approval_copy["execution_authorization"]["maximum_execution_count"] = 2
        elif kind == "raw":
            approval_copy["acknowledgements"]["candidate_csv_may_be_uploaded_as_artifact"] = True
        elif kind == "stake":
            approval_copy["acknowledgements"]["formal_stake"] = 1
        report = validate_approval(
            request, approval_copy, implementation, current, confirmation, event, ref
        )
        results[name] = report["formal_state"] == BLOCKED
    assert all(results.values()), results
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--implementation", type=Path, required=True)
    parser.add_argument("--current-status", type=Path, required=True)
    parser.add_argument("--confirmation-request-id", default="")
    parser.add_argument("--workflow-event", default="")
    parser.add_argument("--workflow-ref", default="")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    request = load_json(args.request)
    approval = load_json(args.approval)
    implementation = load_json(args.implementation)
    current = load_json(args.current_status)
    confirmation = args.confirmation_request_id or (REQUEST_ID if args.self_test else "")
    event = args.workflow_event or ("workflow_dispatch" if args.self_test else "")
    ref = args.workflow_ref or ("refs/heads/main" if args.self_test else "")
    report = validate_approval(request, approval, implementation, current, confirmation, event, ref)
    if args.self_test:
        report["self_tests"] = self_test(request, approval, implementation, current)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if len(payload.encode("utf-8")) > 1048576:
        raise RuntimeError("approval validation report exceeds 1 MiB")
    args.output.write_text(payload, encoding="utf-8")
    print(json.dumps({
        "formal_state": report["formal_state"],
        "checks_passed": report["checks_passed"],
        "checks_total": report["checks_total"],
        "ready_for_one_time_aggregate_execution": report["ready_for_one_time_aggregate_execution"],
        "formal_stake": report["formal_stake"],
    }, indent=2))
    return 0 if report["formal_state"] == READY else 1


if __name__ == "__main__":
    raise SystemExit(main())
