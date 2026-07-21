#!/usr/bin/env python3
"""Validate one explicit Gold/Silver real-reference reconciliation approval."""
from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import validate_historical_gold_silver_coverage_real_reference_request_v1 as request_gate

REQUEST_ID = "HISTORICAL-GOLD-SILVER-COVERAGE-RECONCILIATION-2026-07-21-001"
APPROVAL_SCHEMA = "historical-gold-silver-coverage-real-reference-approval-v1"
READY = "HISTORICAL_GOLD_SILVER_COVERAGE_RECONCILIATION_APPROVAL_VALID_READY_FOR_MANUAL_DISPATCH"
BLOCKED = "HISTORICAL_GOLD_SILVER_COVERAGE_RECONCILIATION_APPROVAL_STRUCTURAL_BLOCKED"
EXPECTED_TEXT = "我核准 request HISTORICAL-GOLD-SILVER-COVERAGE-RECONCILIATION-2026-07-21-001 執行一次 workflow_dispatch 的 aggregate-only Historical Gold／Silver coverage reconciliation。核准範圍只包含在暫存空間重建 2019-20 至 2023-24 Historical Silver／Gold、讀取暫存 reference rows、診斷 Silver 5,826 場與 Gold 5,824 場之間缺少 2 場的原因並輸出按賽季與原因分類的彙總 JSON；不得下載或讀取 candidate CSV，不得上傳原始資料、資料庫、來源 archive、game IDs、日期、隊伍代碼、逐場資料或 row-key hashes，不得在診斷執行中修改 Gold builder、人工補列、模糊配對或以比分修補 identity，不得解鎖 Opening／Closing、PIT market backtest、CLV、EV、ROI、Drawdown、模型重訓、betting edge 或非 0 Stake。"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def evaluate(request, approval, implementation, result, confirmation, event, ref):
    checks: dict[str, bool] = {}
    def check(name: str, value: Any) -> None:
        checks[name] = bool(value)

    request_report = request_gate.evaluate(request, implementation, result)
    check("request_valid", request_report["formal_state"] == request_gate.READY)
    check("request_checks_pass", request_report["checks_failed"] == 0)
    check("approval_schema", approval.get("schema_version") == APPROVAL_SCHEMA)
    check("approval_request", approval.get("request_id") == REQUEST_ID)
    check("approval_state", approval.get("approval_state") == "EXPLICIT_USER_APPROVAL_GRANTED")
    check("approved_by", approval.get("approved_by") == "qoo109")
    check("approval_channel", approval.get("approval_channel") == "ChatGPT project conversation")
    check("approval_text", approval.get("user_response") == EXPECTED_TEXT)

    binding = approval.get("context_binding", {})
    check("binding_pr", binding.get("request_packet_merge_pr") == 115)
    check("binding_commit", binding.get("request_packet_main_commit") == "6b082b110cea0328fd777ccbcd8f5798bc935be7")
    check("binding_validation_run", binding.get("request_validation_workflow_run_id") == 29813766706)
    check("binding_artifact", binding.get("request_validation_artifact_id") == 8488470628)
    check("binding_trigger_run", binding.get("triggering_audit_workflow_run_id") == 29810347326)

    auth = approval.get("execution_authorization", {})
    check("one_time", auth.get("one_time_only") is True)
    check("maximum_one", auth.get("maximum_execution_count") == 1)
    check("count_zero", auth.get("executions_recorded_before_approval") == 0)
    check("dispatch_only", auth.get("workflow_dispatch_only") is True)
    check("approved_ref", auth.get("approved_ref") == "refs/heads/main")
    check("years", auth.get("reference_season_start_years") == request_gate.EXPECTED_YEARS)
    check("candidate_not_required", auth.get("candidate_csv_required") is False)
    check("candidate_forbidden", auth.get("candidate_csv_download_allowed") is False)
    check("reference_network", auth.get("temporary_network_reference_download_allowed") is True)
    check("reference_read", auth.get("temporary_reference_rows_may_be_read") is True)
    check("reference_rebuild", auth.get("temporary_reference_rebuild_allowed") is True)
    check("diagnostics", auth.get("temporary_row_level_diagnostics_may_be_computed") is True)
    check("aggregate_only", auth.get("aggregate_outputs_only") is True)
    check("one_output", auth.get("maximum_public_output_files") == 1)
    check("output_size", auth.get("maximum_public_output_bytes") == 1048576)
    check("execution_enabled", auth.get("execution_enabled_for_this_request") is True)

    ack = approval.get("acknowledgements", {})
    for key in (
        "candidate_csv_may_be_downloaded_or_read",
        "raw_rows_or_raw_files_may_be_uploaded_as_artifact",
        "historical_silver_database_may_be_uploaded_as_artifact",
        "historical_gold_database_may_be_uploaded_as_artifact",
        "source_archives_may_be_uploaded_as_artifact",
        "game_ids_dates_team_codes_or_row_key_hashes_may_be_emitted",
        "gold_builder_change_during_execution_authorized",
        "manual_row_insertion_or_override_authorized",
        "fuzzy_matching_authorized",
        "score_assisted_identity_repair_authorized",
        "historical_silver_replacement_authorized",
        "historical_gold_replacement_authorized",
        "opening_or_closing_labels_authorized",
        "point_in_time_market_backtest_authorized",
        "clv_ev_roi_drawdown_authorized",
        "model_training_or_retraining_authorized",
        "betting_edge_claim_authorized",
    ):
        check(f"ack_{key}", ack.get(key) is False)
    check("stake_zero", ack.get("formal_stake") == 0)

    check("confirmation", confirmation == REQUEST_ID)
    check("event", event == "workflow_dispatch")
    check("ref", ref == "refs/heads/main")
    check("required_confirmation", approval.get("required_confirmation_input") == REQUEST_ID)
    next_state = approval.get("next_state_if_approval_validation_passes", {})
    check("next_state", next_state.get("formal_state") == READY)
    check("next_ready_once", next_state.get("ready_for_one_time_aggregate_execution") is True)
    check("next_no_repeat", next_state.get("ready_for_repeat_execution") is False)
    check("next_no_builder", next_state.get("ready_for_gold_builder_change") is False)
    check("next_no_rerun", next_state.get("ready_for_cross_source_audit_rerun") is False)
    check("next_no_market", next_state.get("ready_for_market_backtest") is False)
    check("next_no_model", next_state.get("ready_for_model_retraining") is False)
    check("next_no_edge", next_state.get("ready_for_betting_edge_claim") is False)
    check("next_stake", next_state.get("formal_stake") == 0)

    failed = sorted(key for key, passed in checks.items() if not passed)
    return {
        "schema_version": "historical-gold-silver-coverage-real-reference-approval-validation-report-v1",
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
        "real_reference_rows_read": False,
        "real_reconciliation_executed": False,
        "raw_rows_emitted": 0,
        "raw_files_emitted": False,
        "source_role_changed": False,
        "formal_stake": 0,
    }


def self_test(request, approval, implementation, result):
    baseline = evaluate(request, approval, implementation, result, REQUEST_ID, "workflow_dispatch", "refs/heads/main")
    assert baseline["formal_state"] == READY, baseline
    tests = {"baseline_passes": True}
    cases = {
        "wrong_confirmation_blocks": ("confirmation", "WRONG"),
        "wrong_event_blocks": ("event", "push"),
        "wrong_ref_blocks": ("ref", "refs/heads/dev"),
        "repeat_blocks": ("executions_recorded_before_approval", 1),
        "candidate_blocks": ("candidate_csv_download_allowed", True),
        "nonzero_stake_blocks": ("formal_stake", 1),
    }
    for name, (field, value) in cases.items():
        app = copy.deepcopy(approval)
        confirmation, event, ref = REQUEST_ID, "workflow_dispatch", "refs/heads/main"
        if field == "confirmation": confirmation = value
        elif field == "event": event = value
        elif field == "ref": ref = value
        elif field == "formal_stake": app["acknowledgements"][field] = value
        else: app["execution_authorization"][field] = value
        report = evaluate(request, app, implementation, result, confirmation, event, ref)
        tests[name] = report["formal_state"] == BLOCKED
    assert all(tests.values()), tests
    return tests


def write_json(path: Path, value: dict[str, Any]) -> None:
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if len(payload.encode("utf-8")) > 1048576:
        raise RuntimeError("aggregate report exceeds 1 MiB")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--implementation", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--confirmation-request-id", default="")
    parser.add_argument("--workflow-event", default="")
    parser.add_argument("--workflow-ref", default="")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    request, approval = read_json(args.request), read_json(args.approval)
    implementation, result = read_json(args.implementation), read_json(args.result)
    confirmation = args.confirmation_request_id or (REQUEST_ID if args.self_test else "")
    event = args.workflow_event or ("workflow_dispatch" if args.self_test else "")
    ref = args.workflow_ref or ("refs/heads/main" if args.self_test else "")
    report = evaluate(request, approval, implementation, result, confirmation, event, ref)
    if args.self_test:
        report["self_tests"] = self_test(request, approval, implementation, result)
    write_json(args.output, report)
    print(json.dumps({"formal_state": report["formal_state"], "checks_failed": report["checks_failed"], "formal_stake": 0}, ensure_ascii=False, indent=2))
    return 0 if report["formal_state"] == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
