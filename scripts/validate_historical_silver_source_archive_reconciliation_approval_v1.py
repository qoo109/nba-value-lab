#!/usr/bin/env python3
"""Validate explicit approval for the 2023-24 source archive reconciliation."""
from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REQUEST_ID = "HISTORICAL-SILVER-2023-24-SOURCE-ARCHIVE-RECONCILIATION-2026-07-22-001"
READY = "HISTORICAL_SILVER_2023_24_SOURCE_ARCHIVE_RECONCILIATION_APPROVAL_VALID_READY_FOR_MANUAL_DISPATCH"
BLOCKED = "HISTORICAL_SILVER_2023_24_SOURCE_ARCHIVE_RECONCILIATION_APPROVAL_BLOCKED"
EXPECTED_RESPONSE = (
    "我核准 request HISTORICAL-SILVER-2023-24-SOURCE-ARCHIVE-RECONCILIATION-2026-07-22-001 "
    "執行一次 workflow_dispatch 的 aggregate-only 2023-24 Shufinskiy source archive reconciliation。\n\n"
    "核准範圍只包含在暫存空間下載並讀取 Shufinskiy NBA Stats／PBP Stats source archives、"
    "計算 archive manifest counts、coverage overlap counts 與 missing reason aggregate histogram，"
    "並輸出一份不超過 1 MiB 的彙總 JSON。\n\n"
    "不得下載或讀取 Chris Munch、Eoin 或任何 candidate CSV，不得建立、修改或上傳 Silver／Gold database，"
    "不得上傳來源 archive、raw rows、raw files、game IDs、日期、隊伍代碼、source file paths、"
    "source file hashes、逐列資料或 row-key hashes，不得修改 Silver builder、人工補列、模糊配對、"
    "以比分修補 identity、替換 Historical Silver／Gold、重跑 cross-source audit、開啟市場回測、"
    "模型重訓、betting edge 或非 0 Stake。"
)


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def validate(request, approval, design, result, current, registry, confirmation, event, ref):
    checks: dict[str, bool] = {}

    def add(name: str, value: Any) -> None:
        checks[name] = bool(value)

    add("request_schema", request.get("schema_version") == "historical-silver-2023-24-source-archive-reconciliation-request-v1")
    add("request_id", request.get("request_id") == REQUEST_ID)
    add("request_state", request.get("request_state") == "AWAITING_EXPLICIT_USER_APPROVAL")
    scope = request.get("frozen_scope", {})
    add("request_season", scope.get("season_label") == "2023-24" and scope.get("season_start_year") == 2023)
    add("request_source", scope.get("source_id") == "shufinskiy_nba_data")
    add("request_path", scope.get("reference_source_path") == "shufinskiy/nba_data")
    add("request_games", scope.get("expected_silver_games") == 1230)
    add("request_gap", scope.get("expected_games_without_team_features") == 2)
    add("request_reason", scope.get("expected_missing_reason") == "nbastats_game_present_pbpstats_game_absent")
    add("request_reason_count", scope.get("expected_missing_reason_count") == 2)
    for key in (
        "candidate_csv_download_allowed",
        "chris_munch_raw_csv_allowed",
        "eoin_raw_bundle_allowed",
        "gold_database_required",
        "gold_builder_execution_allowed",
    ):
        add(f"request_{key}", scope.get(key) is False)

    add("approval_schema", approval.get("schema_version") == "historical-silver-2023-24-source-archive-reconciliation-approval-v1")
    add("approval_id", approval.get("request_id") == REQUEST_ID)
    add("approval_state", approval.get("approval_state") == "EXPLICIT_USER_APPROVAL_GRANTED")
    add("approval_owner", approval.get("approved_by") == "qoo109")
    add("approval_response", approval.get("user_response") == EXPECTED_RESPONSE)
    context = approval.get("context_binding", {})
    add("context_request_commit", context.get("request_commit") == "f188b6263abcbba8291b511891026fb65840834b")
    add("context_request_validation_run", context.get("request_validation_workflow_run_id") == 29900088612)
    add("context_request_artifact", context.get("request_validation_artifact_id") == 8521512013)
    add("context_request_digest", context.get("request_validation_artifact_digest") == "sha256:bfe51b43dbf94864954f4ecf1a7159d53d33f322fc5cfe03caedaada46900695")
    add("context_design_run", context.get("design_validation_workflow_run_id") == 29896243732)
    add("context_result_run", context.get("root_cause_retry_002_run_id") == 29890527281)
    add("context_result_artifact", context.get("root_cause_retry_002_artifact_id") == 8518081820)
    add("context_result_digest", context.get("root_cause_retry_002_artifact_digest") == "sha256:a10b1c63b3edff65e4a3eeb86e5062f245fdc300e61b2e40ff0ba8cc4df98f40")

    auth = approval.get("execution_authorization", {})
    add("approval_one_time", auth.get("one_time_only") is True)
    add("approval_max_one", auth.get("maximum_execution_count") == 1)
    add("approval_prior_zero", auth.get("executions_recorded_before_approval") == 0)
    add("approval_dispatch_only", auth.get("workflow_dispatch_only") is True)
    add("approval_main", auth.get("approved_ref") == "refs/heads/main")
    add("approval_season", auth.get("season_label") == "2023-24" and auth.get("season_start_year") == 2023)
    add("approval_source", auth.get("source_id") == "shufinskiy_nba_data")
    add("approval_path", auth.get("reference_source_path") == "shufinskiy/nba_data")
    add("approval_expected", auth.get("expected_silver_games") == 1230 and auth.get("expected_games_without_team_features") == 2)
    add("approval_reason", auth.get("expected_missing_reason") == "nbastats_game_present_pbpstats_game_absent")
    add("approval_reason_count", auth.get("expected_missing_reason_count") == 2)
    add("approval_download", auth.get("temporary_shufinskiy_source_archive_download_allowed") is True)
    add("approval_read", auth.get("temporary_shufinskiy_source_archive_read_allowed") is True)
    add("approval_manifest_scan", auth.get("temporary_archive_manifest_scan_allowed") is True)
    add("approval_overlap", auth.get("temporary_coverage_overlap_count_allowed") is True)
    add("approval_aggregate", auth.get("aggregate_outputs_only") is True)
    add("approval_output_one", auth.get("maximum_public_output_files") == 1)
    add("approval_output_size", auth.get("maximum_public_output_bytes") == 1048576)
    add("approval_enabled", auth.get("execution_enabled_for_this_request") is True)

    ack = approval.get("acknowledgements", {})
    for key in (
        "chris_munch_csv_downloaded_or_read",
        "eoin_bundle_downloaded_or_read",
        "candidate_csv_downloaded_or_read",
        "gold_database_created_or_read",
        "silver_database_created_modified_or_uploaded",
        "gold_builder_execution_or_change",
        "silver_builder_code_change_during_execution",
        "manual_row_insertion_or_override",
        "fuzzy_matching",
        "score_assisted_identity_repair",
        "source_archives_uploaded",
        "raw_rows_or_raw_files_uploaded",
        "game_ids_emitted",
        "dates_emitted",
        "team_codes_emitted",
        "source_file_paths_emitted",
        "source_file_hashes_emitted",
        "row_level_records_emitted",
        "row_key_hashes_emitted",
        "historical_silver_replacement_authorized",
        "historical_gold_replacement_authorized",
        "cross_source_audit_rerun_authorized",
        "point_in_time_market_backtest_authorized",
        "clv_ev_roi_drawdown_authorized",
        "model_training_or_retraining_authorized",
        "betting_edge_claim_authorized",
    ):
        add(f"ack_{key}", ack.get(key) is False)
    add("ack_stake", ack.get("formal_stake") == 0)
    add("approval_confirmation", approval.get("required_confirmation_input") == REQUEST_ID)
    next_state = approval.get("next_state_if_approval_validation_passes", {})
    add("approval_next", next_state.get("formal_state") == READY)
    add("approval_ready_once", next_state.get("ready_for_one_time_aggregate_execution") is True)
    add("approval_no_repeat", next_state.get("ready_for_repeat_execution") is False)
    add("approval_no_chris", next_state.get("ready_for_chris_munch_data_execution") is False)
    add("approval_no_market", next_state.get("ready_for_market_backtest") is False)
    add("approval_next_stake", next_state.get("formal_stake") == 0)

    add("design_ready", design.get("formal_state") == "HISTORICAL_SILVER_2023_24_SOURCE_ARCHIVE_RECONCILIATION_DESIGN_READY")
    add("design_request_ready", design.get("downstream_permissions", {}).get("ready_for_source_archive_reconciliation_request") is True)
    add("design_no_data_execution", design.get("downstream_permissions", {}).get("ready_for_chris_munch_data_execution") is False)
    add("design_stake", design.get("downstream_permissions", {}).get("formal_stake") == 0)

    result_scope = result.get("scope", {})
    add("result_outcome", result.get("formal_outcome") == "HISTORICAL_SILVER_MISSING_TEAM_FEATURES_SOURCE_GAP_CONFIRMED")
    add("result_scope", result_scope.get("silver_games") == 1230 and result_scope.get("games_without_team_features") == 2)
    add("result_reason", result.get("root_cause", {}).get("missing_by_reason", {}).get("nbastats_game_present_pbpstats_game_absent") == 2)
    add("result_consumed", result.get("execution_receipt", {}).get("request_consumed") is True)
    add("result_no_repeat", result.get("execution_receipt", {}).get("repeat_execution_allowed") is False)
    add("result_boundary_stake", result.get("boundaries", {}).get("formal_stake") == 0)

    add("current_schema", current.get("schema_version") == "historical-silver-2023-24-source-archive-reconciliation-current-status-v1")
    add("current_state", current.get("formal_state") == READY)
    add("current_id", current.get("request_id") == REQUEST_ID)
    add("current_approved", current.get("approval_granted") is True)
    add("current_enabled", current.get("execution_enabled") is True)
    add("current_zero", current.get("execution_count") == 0)
    add("current_max_one", current.get("maximum_execution_count") == 1)
    add("current_dispatch_only", current.get("workflow_dispatch_only") is True)
    add("current_no_network", current.get("network_calls_made") == 0)
    add("current_no_archive_read", current.get("shufinskiy_source_archives_read") is False)
    add("current_no_chris", current.get("ready_for_chris_munch_data_execution") is False)
    add("current_next", current.get("next_research_step") == "HISTORICAL_SILVER_2023_24_SOURCE_ARCHIVE_RECONCILIATION_READY_FOR_MANUAL_DISPATCH")
    add("current_stake", current.get("formal_stake") == 0)

    sources = registry.get("sources", [])
    shufinskiy = next((source for source in sources if source.get("source_id") == "shufinskiy_nba_data"), {})
    policy = shufinskiy.get("source_archive_reconciliation_design", {})
    add("registry_state", policy.get("formal_state") == READY)
    add("registry_approval", policy.get("approval") == "data/research/historical-silver-2023-24-source-archive-reconciliation-approval-v1.json")
    add("registry_current", policy.get("current_status") == "data/research/historical-silver-2023-24-source-archive-reconciliation-current-status-v1.json")
    add("registry_manual_ready", policy.get("ready_for_manual_dispatch") is True)
    add("registry_enabled", policy.get("execution_enabled") is True)
    add("registry_count_zero", policy.get("execution_count") == 0)
    add("registry_max_one", policy.get("maximum_execution_count") == 1)
    add("registry_raw_zero", policy.get("raw_rows_emitted") == 0)
    add("registry_stake", policy.get("formal_stake") == 0)

    add("runtime_request", confirmation == REQUEST_ID)
    add("runtime_event", event == "workflow_dispatch")
    add("runtime_ref", ref == "refs/heads/main")

    failed = sorted(name for name, ok in checks.items() if not ok)
    return {
        "schema_version": "historical-silver-2023-24-source-archive-reconciliation-approval-validation-report-v1",
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
        "shufinskiy_source_archives_read": False,
        "candidate_csv_rows_read": False,
        "real_reconciliation_executed": False,
        "raw_rows_emitted": 0,
        "raw_files_emitted": False,
        "formal_stake": 0,
    }


def self_test(request, approval, design, result, current, registry):
    base = validate(request, approval, design, result, current, registry, REQUEST_ID, "workflow_dispatch", "refs/heads/main")
    assert base["formal_state"] == READY, base
    tests = {"baseline_passes": True}
    cases = {
        "wrong_request_blocks": ("runtime", "WRONG"),
        "wrong_ref_blocks": ("ref", "refs/heads/dev"),
        "revoked_approval_blocks": ("approval", "REVOKED"),
        "repeat_permission_blocks": ("repeat", 2),
        "candidate_permission_blocks": ("candidate", True),
        "file_hash_output_blocks": ("file_hash", True),
        "nonzero_stake_blocks": ("stake", 1),
        "registry_execution_count_blocks": ("registry_count", 1),
    }
    for name, (kind, value) in cases.items():
        app = copy.deepcopy(approval)
        cur = copy.deepcopy(current)
        reg = copy.deepcopy(registry)
        confirmation, event, ref = REQUEST_ID, "workflow_dispatch", "refs/heads/main"
        if kind == "runtime":
            confirmation = value
        elif kind == "ref":
            ref = value
        elif kind == "approval":
            app["approval_state"] = value
        elif kind == "repeat":
            app["execution_authorization"]["maximum_execution_count"] = value
        elif kind == "candidate":
            app["acknowledgements"]["candidate_csv_downloaded_or_read"] = value
        elif kind == "file_hash":
            app["acknowledgements"]["source_file_hashes_emitted"] = value
        elif kind == "stake":
            app["acknowledgements"]["formal_stake"] = value
        elif kind == "registry_count":
            source = next(item for item in reg["sources"] if item.get("source_id") == "shufinskiy_nba_data")
            source["source_archive_reconciliation_design"]["execution_count"] = value
        report = validate(request, app, design, result, cur, reg, confirmation, event, ref)
        tests[name] = report["formal_state"] == BLOCKED
    assert all(tests.values()), tests
    return tests


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--design", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--current-status", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--confirmation-request-id", default=REQUEST_ID)
    parser.add_argument("--workflow-event", default="workflow_dispatch")
    parser.add_argument("--workflow-ref", default="refs/heads/main")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    request = read_json(args.request)
    approval = read_json(args.approval)
    design = read_json(args.design)
    result = read_json(args.result)
    current = read_json(args.current_status)
    registry = read_json(args.registry)
    report = validate(
        request, approval, design, result, current, registry,
        args.confirmation_request_id, args.workflow_event, args.workflow_ref,
    )
    if args.self_test:
        report["self_tests"] = self_test(request, approval, design, result, current, registry)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if len(payload.encode("utf-8")) > 1048576:
        raise RuntimeError("approval report exceeds 1 MiB")
    args.output.write_text(payload, encoding="utf-8")
    print(json.dumps({
        "formal_state": report["formal_state"],
        "checks_passed": report["checks_passed"],
        "checks_total": report["checks_total"],
        "formal_stake": 0,
    }, ensure_ascii=False, indent=2))
    return 0 if report["formal_state"] == READY else 1


if __name__ == "__main__":
    raise SystemExit(main())
