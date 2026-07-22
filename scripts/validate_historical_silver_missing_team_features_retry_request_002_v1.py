#!/usr/bin/env python3
"""Validate Historical Silver missing-team-features retry request 002.

Policy-only: no network access, no source reads, and no execution.
"""
from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REQUEST_ID = "HISTORICAL-SILVER-2023-24-MISSING-BOTH-TEAM-FEATURES-ROOT-CAUSE-2026-07-22-002"
PREVIOUS_REQUEST_ID = "HISTORICAL-SILVER-2023-24-MISSING-BOTH-TEAM-FEATURES-ROOT-CAUSE-2026-07-21-001"
REQUEST_SCHEMA = "historical-silver-2023-24-missing-team-features-root-cause-retry-request-002-v1"
CURRENT_SCHEMA = "historical-silver-2023-24-missing-team-features-root-cause-current-status-v3"
READY = "HISTORICAL_SILVER_2023_24_MISSING_TEAM_FEATURES_ROOT_CAUSE_RETRY_002_REQUEST_VALID_AWAITING_EXPLICIT_USER_APPROVAL"
BLOCKED = "HISTORICAL_SILVER_2023_24_MISSING_TEAM_FEATURES_ROOT_CAUSE_RETRY_002_REQUEST_STRUCTURAL_BLOCKED"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def evaluate(request: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    checks: dict[str, bool] = {}

    def check(name: str, condition: Any) -> None:
        checks[name] = bool(condition)

    check("request_schema", request.get("schema_version") == REQUEST_SCHEMA)
    check("request_id", request.get("request_id") == REQUEST_ID)
    check("request_waiting", request.get("state") == "AWAITING_EXPLICIT_USER_APPROVAL")
    check("previous_request", request.get("previous_request_id") == PREVIOUS_REQUEST_ID)
    check("previous_run", request.get("previous_run_id") == 29888939524)
    check("previous_artifact", request.get("previous_artifact_id") == 8517546804)
    check("previous_digest", request.get("previous_artifact_digest") == "sha256:9dc05a526aec039bf02032e276a9c6c9b258e9a7368ba699c9935d7aff5e8db9")
    check("previous_result", request.get("previous_result") == "BLOCKED_BEFORE_RESULT")
    check("previous_error_type", request.get("previous_error_type") == "KeyError")
    check("previous_error_summary", request.get("previous_error_summary") == "team_inference_failures")
    check("incident_note", request.get("incident_note") == "docs/historical-silver-missing-team-features-run-29888939524-incident-v1.md")
    check("repair_commit", request.get("repair_commit") == "db5a7ea4ad38f5d3db763d6ea4457e5428292fb5")
    check("repair_summary", "sources.pbpstats_2023" in str(request.get("repair_summary", "")))
    check("scope_unchanged", request.get("scope_unchanged_from_request_001") is True)
    check("season", request.get("season_label") == "2023-24")
    check("silver_games", request.get("expected_silver_games") == 1230)
    check("missing_games", request.get("expected_games_without_team_features") == 2)
    check("source_path", request.get("reference_source_path") == "shufinskiy/nba_data")

    check("one_time", request.get("one_time_only") is True)
    check("max_one", request.get("maximum_execution_count") == 1)
    check("dispatch_only", request.get("workflow_dispatch_only") is True)
    check("approval_not_granted", request.get("approval_granted") is False)
    check("approved_by_empty", request.get("approved_by") is None)
    check("approved_at_empty", request.get("approved_at") is None)
    check("execution_disabled", request.get("execution_enabled") is False)
    check("execution_count_zero", request.get("execution_count") == 0)

    false_keys = (
        "candidate_csv_download_allowed",
        "gold_database_required",
        "gold_builder_execution_allowed",
        "silver_builder_code_change_during_execution_allowed",
        "manual_row_insertion_or_override_allowed",
        "fuzzy_matching_allowed",
        "score_assisted_identity_repair_allowed",
        "historical_silver_replacement_allowed",
        "historical_gold_replacement_allowed",
        "raw_files_emitted",
        "silver_database_uploaded_as_artifact",
        "source_archives_uploaded_as_artifact",
        "game_ids_emitted",
        "dates_emitted",
        "team_codes_emitted",
        "row_level_records_emitted",
        "row_key_hashes_emitted",
        "opening_or_closing_labels_authorized",
        "point_in_time_market_backtest_authorized",
        "clv_ev_roi_drawdown_authorized",
        "model_training_or_retraining_authorized",
        "betting_edge_claim_authorized",
    )
    for key in false_keys:
        check(f"false_{key}", request.get(key) is False)
    check("aggregate_only", request.get("aggregate_json_only") is True)
    check("one_output", request.get("maximum_public_output_files") == 1)
    check("output_size", request.get("maximum_public_output_bytes") == 1048576)
    check("raw_rows_zero", request.get("raw_rows_emitted") == 0)
    check("stake_zero", request.get("formal_stake") == 0)

    template = str(request.get("approval_text_template", ""))
    check("approval_template_request", REQUEST_ID in template)
    check("approval_template_retry_only", "只修正 request 001 的 runner 欄位路徑錯誤" in template)
    check("approval_template_no_candidate", "不得下載或讀取 candidate CSV" in template)
    check("approval_template_no_gold", "不得建立或修改 Gold" in template)
    check("approval_template_stake_zero", "非 0 Stake" in template)

    next_state = request.get("next_state_if_request_validation_passes", {})
    check("next_state", next_state.get("formal_state") == READY)
    check("next_user_approval", next_state.get("ready_for_user_approval") is True)
    check("next_execution_false", next_state.get("ready_for_execution") is False)
    check("next_repeat_false", next_state.get("ready_for_repeat_execution") is False)
    check("next_stake_zero", next_state.get("formal_stake") == 0)

    check("current_schema", current.get("schema_version") == CURRENT_SCHEMA)
    check("current_state", current.get("formal_state") == "HISTORICAL_SILVER_2023_24_MISSING_TEAM_FEATURES_ROOT_CAUSE_001_CONSUMED_BLOCKED_BY_RUNNER_BUG")
    check("current_request", current.get("request_id") == PREVIOUS_REQUEST_ID)
    check("current_run", current.get("execution_run_id") == 29888939524)
    check("current_artifact", current.get("execution_artifact_id") == 8517546804)
    check("current_consumed", current.get("request_consumed") is True)
    check("current_no_repeat", current.get("repeat_execution_allowed") is False)
    check("current_no_outcome", current.get("formal_outcome_produced") is False)
    check("current_blocked", current.get("blocked_before_result") is True)
    check("current_error", current.get("blocked_error_summary") == "team_inference_failures")
    check("current_next", current.get("next_research_step") == "HISTORICAL_SILVER_2023_24_MISSING_TEAM_FEATURES_ROOT_CAUSE_REPAIRED_RETRY_REQUEST_002_REQUIRED")
    check("current_stake_zero", current.get("formal_stake") == 0)

    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": "historical-silver-2023-24-missing-team-features-retry-request-002-validation-report-v1",
        "validated_at": utc_now(),
        "request_id": REQUEST_ID,
        "formal_state": READY if not failed else BLOCKED,
        "checks": checks,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "checks_failed": len(failed),
        "failed_checks": failed,
        "quality": {
            "network_calls_made": False,
            "real_reference_rows_read": False,
            "real_root_cause_audit_executed": False,
            "raw_rows_emitted": 0,
            "raw_files_emitted": False,
            "execution_enabled": False,
            "formal_stake": 0,
        },
        "decision": {
            "ready_for_explicit_user_approval": not failed,
            "ready_for_execution": False,
            "ready_for_repeat_execution": False,
            "ready_for_silver_builder_change": False,
            "ready_for_gold_rebuild": False,
            "ready_for_cross_source_audit_rerun": False,
            "ready_for_market_backtest": False,
            "ready_for_model_retraining": False,
            "ready_for_betting_edge_claim": False,
            "formal_stake": 0,
        },
    }


def self_test(request: dict[str, Any], current: dict[str, Any]) -> dict[str, bool]:
    baseline = evaluate(request, current)
    assert baseline["formal_state"] == READY, baseline
    tests = {"baseline_passes": True}
    cases = {
        "wrong_request_blocks": ("request", ["request_id"], "WRONG"),
        "approval_granted_blocks": ("request", ["approval_granted"], True),
        "execution_enabled_blocks": ("request", ["execution_enabled"], True),
        "candidate_download_blocks": ("request", ["candidate_csv_download_allowed"], True),
        "gold_execution_blocks": ("request", ["gold_builder_execution_allowed"], True),
        "raw_artifact_blocks": ("request", ["raw_files_emitted"], True),
        "nonzero_stake_blocks": ("request", ["formal_stake"], 1),
        "unconsumed_001_blocks": ("current", ["request_consumed"], False),
    }
    for name, (target_name, path, value) in cases.items():
        req = copy.deepcopy(request)
        cur = copy.deepcopy(current)
        target = {"request": req, "current": cur}[target_name]
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        report = evaluate(req, cur)
        tests[name] = report["formal_state"] == BLOCKED
    assert all(tests.values()), tests
    return tests


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--current-status", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    request = read_json(args.request)
    current = read_json(args.current_status)
    report = evaluate(request, current)
    if args.self_test:
        report["self_tests"] = self_test(request, current)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if len(payload.encode("utf-8")) > 1048576:
        raise RuntimeError("request validation report exceeds 1 MiB")
    args.output.write_text(payload, encoding="utf-8")
    print(json.dumps({
        "formal_state": report["formal_state"],
        "checks_passed": report["checks_passed"],
        "checks_total": report["checks_total"],
        "formal_stake": report["quality"]["formal_stake"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["formal_state"] == READY else 1


if __name__ == "__main__":
    raise SystemExit(main())
