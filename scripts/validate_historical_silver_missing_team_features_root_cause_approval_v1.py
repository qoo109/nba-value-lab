#!/usr/bin/env python3
"""Validate explicit approval for the one-time 2023-24 Silver root-cause audit."""
from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REQUEST_ID = "HISTORICAL-SILVER-2023-24-MISSING-BOTH-TEAM-FEATURES-ROOT-CAUSE-2026-07-21-001"
READY = "HISTORICAL_SILVER_2023_24_MISSING_TEAM_FEATURES_ROOT_CAUSE_APPROVAL_VALID_READY_FOR_MANUAL_DISPATCH"
BLOCKED = "HISTORICAL_SILVER_2023_24_MISSING_TEAM_FEATURES_ROOT_CAUSE_APPROVAL_BLOCKED"
EXPECTED_RESPONSE = "我核准 request HISTORICAL-SILVER-2023-24-MISSING-BOTH-TEAM-FEATURES-ROOT-CAUSE-2026-07-21-001 執行一次 workflow_dispatch 的 aggregate-only 2023-24 Historical Silver missing-team-features root-cause audit。核准範圍只包含在暫存空間下載並重建 2023-24 Historical Silver、讀取暫存 games／possessions／team_game_features rows、分類兩場零 team features 的根本原因並輸出彙總 JSON；不得下載或讀取 candidate CSV，不得建立或修改 Gold，不得上傳原始資料、Silver database、來源 archive、game IDs、日期、隊伍代碼、逐場資料或 row-key hashes，不得修改 Silver builder、人工補列、模糊配對或以比分修補 identity，不得解鎖 Opening／Closing、PIT market backtest、CLV、EV、ROI、Drawdown、模型重訓、betting edge 或非 0 Stake。"


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def validate(request, approval, implementation, result, current, confirmation, event, ref):
    checks: dict[str, bool] = {}
    def add(name: str, value: Any) -> None:
        checks[name] = bool(value)

    add("request_id", request.get("request_id") == REQUEST_ID)
    add("request_state", request.get("request_state") == "AWAITING_EXPLICIT_USER_APPROVAL")
    add("request_one_time", request.get("one_time_execution_scope", {}).get("one_time_only") is True)
    add("request_max_one", request.get("one_time_execution_scope", {}).get("maximum_execution_count") == 1)
    add("request_dispatch_only", request.get("one_time_execution_scope", {}).get("workflow_dispatch_only") is True)
    add("request_candidate_forbidden", request.get("frozen_scope", {}).get("candidate_csv_download_allowed") is False)
    add("request_gold_forbidden", request.get("frozen_scope", {}).get("gold_builder_execution_allowed") is False)
    add("request_expected_games", request.get("frozen_scope", {}).get("expected_silver_games") == 1230)
    add("request_expected_gap", request.get("frozen_scope", {}).get("expected_games_without_team_features") == 2)
    add("request_not_approved", request.get("approval_boundary", {}).get("approval_granted") is False)
    add("request_disabled", request.get("approval_boundary", {}).get("execution_enabled") is False)
    add("request_stake", request.get("current_execution_boundary", {}).get("formal_stake") == 0)

    add("approval_id", approval.get("request_id") == REQUEST_ID)
    add("approval_state", approval.get("approval_state") == "EXPLICIT_USER_APPROVAL_GRANTED")
    add("approval_owner", approval.get("approved_by") == "qoo109")
    add("approval_response", approval.get("user_response") == EXPECTED_RESPONSE)
    auth = approval.get("execution_authorization", {})
    add("approval_one_time", auth.get("one_time_only") is True)
    add("approval_max_one", auth.get("maximum_execution_count") == 1)
    add("approval_prior_zero", auth.get("executions_recorded_before_approval") == 0)
    add("approval_dispatch_only", auth.get("workflow_dispatch_only") is True)
    add("approval_main", auth.get("approved_ref") == "refs/heads/main")
    add("approval_season", auth.get("season_label") == "2023-24" and auth.get("season_start_year") == 2023)
    add("approval_expected", auth.get("expected_silver_games") == 1230 and auth.get("expected_games_without_team_features") == 2)
    add("approval_aggregate", auth.get("aggregate_outputs_only") is True)
    add("approval_output_one", auth.get("maximum_public_output_files") == 1)
    add("approval_output_size", auth.get("maximum_public_output_bytes") == 1048576)
    add("approval_enabled", auth.get("execution_enabled_for_this_request") is True)
    ack = approval.get("acknowledgements", {})
    forbidden = [
        "candidate_csv_downloaded_or_read", "gold_database_created_or_read", "gold_builder_execution_or_change",
        "silver_builder_code_change_during_execution", "manual_row_insertion_or_override", "fuzzy_matching",
        "score_assisted_identity_repair", "raw_rows_or_raw_files_uploaded", "silver_database_uploaded",
        "source_archives_uploaded", "game_ids_emitted", "dates_emitted", "team_codes_emitted",
        "row_level_records_emitted", "row_key_hashes_emitted", "historical_silver_replacement_authorized",
        "historical_gold_replacement_authorized", "opening_or_closing_labels_authorized",
        "point_in_time_market_backtest_authorized", "clv_ev_roi_drawdown_authorized",
        "model_training_or_retraining_authorized", "betting_edge_claim_authorized",
    ]
    for key in forbidden:
        add(f"ack_{key}", ack.get(key) is False)
    add("ack_stake", ack.get("formal_stake") == 0)
    add("approval_confirmation", approval.get("required_confirmation_input") == REQUEST_ID)
    next_state = approval.get("next_state_if_approval_validation_passes", {})
    add("approval_next", next_state.get("formal_state") == READY)
    add("approval_ready_once", next_state.get("ready_for_one_time_aggregate_execution") is True)
    add("approval_no_repeat", next_state.get("ready_for_repeat_execution") is False)
    add("approval_no_builder", next_state.get("ready_for_silver_builder_change") is False)
    add("approval_no_gold", next_state.get("ready_for_gold_rebuild") is False)
    add("approval_no_rerun", next_state.get("ready_for_cross_source_audit_rerun") is False)
    add("approval_next_stake", next_state.get("formal_stake") == 0)

    add("implementation_state", implementation.get("formal_state") == "HISTORICAL_SILVER_2023_24_MISSING_TEAM_FEATURES_ROOT_CAUSE_IMPLEMENTATION_READY_REAL_EXECUTION_DISABLED")
    add("implementation_season", implementation.get("observed_gap", {}).get("season_label") == "2023-24")
    add("implementation_gap", implementation.get("observed_gap", {}).get("games_without_team_features") == 2)
    add("implementation_no_real", implementation.get("validation_mode", {}).get("real_root_cause_audit_executed") is False)
    add("implementation_stake", implementation.get("downstream_permissions", {}).get("formal_stake") == 0)

    add("result_run", result.get("workflow_run_id") == 29819457942)
    add("result_outcome", result.get("formal_outcome") == "HISTORICAL_GOLD_SILVER_COVERAGE_RECONCILIATION_SOURCE_DATA_GAP_CONFIRMED")
    add("result_gap", result.get("missing_season") == "2023-24" and result.get("missing_both_team_features") == 2)
    add("result_no_candidate", result.get("candidate_csv_downloaded_or_read") is False)
    add("result_stake", result.get("formal_stake") == 0)

    add("current_state", current.get("formal_state") == "HISTORICAL_SILVER_2023_24_MISSING_TEAM_FEATURES_ROOT_CAUSE_REQUEST_VALID_AWAITING_EXPLICIT_USER_APPROVAL")
    add("current_id", current.get("request_id") == REQUEST_ID)
    add("current_unapproved", current.get("approval_granted") is False)
    add("current_disabled", current.get("execution_enabled") is False)
    add("current_zero", current.get("execution_count") == 0)
    add("current_stake", current.get("formal_stake") == 0)

    add("runtime_request", confirmation == REQUEST_ID)
    add("runtime_event", event == "workflow_dispatch")
    add("runtime_ref", ref == "refs/heads/main")

    failed = sorted(k for k, v in checks.items() if not v)
    return {
        "schema_version": "historical-silver-2023-24-missing-team-features-root-cause-approval-validation-report-v1",
        "validated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
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
        "real_reference_rows_read": False,
        "real_root_cause_audit_executed": False,
        "raw_rows_emitted": 0,
        "raw_files_emitted": False,
        "formal_stake": 0,
    }


def self_test(request, approval, implementation, result, current):
    base = validate(request, approval, implementation, result, current, REQUEST_ID, "workflow_dispatch", "refs/heads/main")
    assert base["formal_state"] == READY, base
    tests = {"baseline_passes": True}
    mutations = {
        "wrong_request_blocks": ("runtime", "WRONG"),
        "wrong_ref_blocks": ("ref", "refs/heads/dev"),
        "revoked_approval_blocks": ("approval", "REVOKED"),
        "repeat_permission_blocks": ("repeat", 2),
        "candidate_permission_blocks": ("candidate", True),
        "nonzero_stake_blocks": ("stake", 1),
    }
    for name, (kind, value) in mutations.items():
        app = copy.deepcopy(approval)
        confirmation, event, ref = REQUEST_ID, "workflow_dispatch", "refs/heads/main"
        if kind == "runtime": confirmation = value
        elif kind == "ref": ref = value
        elif kind == "approval": app["approval_state"] = value
        elif kind == "repeat": app["execution_authorization"]["maximum_execution_count"] = value
        elif kind == "candidate": app["acknowledgements"]["candidate_csv_downloaded_or_read"] = value
        elif kind == "stake": app["acknowledgements"]["formal_stake"] = value
        report = validate(request, app, implementation, result, current, confirmation, event, ref)
        tests[name] = report["formal_state"] == BLOCKED
    assert all(tests.values()), tests
    return tests


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--implementation", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--current-status", type=Path, required=True)
    parser.add_argument("--confirmation-request-id", default=REQUEST_ID)
    parser.add_argument("--workflow-event", default="workflow_dispatch")
    parser.add_argument("--workflow-ref", default="refs/heads/main")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    request, approval = read_json(args.request), read_json(args.approval)
    implementation, result, current = read_json(args.implementation), read_json(args.result), read_json(args.current_status)
    report = validate(request, approval, implementation, result, current, args.confirmation_request_id, args.workflow_event, args.workflow_ref)
    if args.self_test:
        report["self_tests"] = self_test(request, approval, implementation, result, current)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if len(payload.encode("utf-8")) > 1048576:
        raise RuntimeError("approval report exceeds 1 MiB")
    args.output.write_text(payload, encoding="utf-8")
    print(json.dumps({"formal_state": report["formal_state"], "checks_passed": report["checks_passed"], "checks_total": report["checks_total"], "formal_stake": 0}, ensure_ascii=False, indent=2))
    return 0 if report["formal_state"] == READY else 1


if __name__ == "__main__":
    raise SystemExit(main())
