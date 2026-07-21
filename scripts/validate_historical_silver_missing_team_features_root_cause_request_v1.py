#!/usr/bin/env python3
"""Validate the one-time 2023-24 Silver missing-feature root-cause request.

Policy-only: no network access, no real reference reads, and no execution.
"""
from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REQUEST_ID = "HISTORICAL-SILVER-2023-24-MISSING-BOTH-TEAM-FEATURES-ROOT-CAUSE-2026-07-21-001"
REQUEST_SCHEMA = "historical-silver-2023-24-missing-team-features-root-cause-real-execution-request-v1"
IMPLEMENTATION_SCHEMA = "historical-silver-2023-24-missing-team-features-root-cause-implementation-v1"
RESULT_SCHEMA = "historical-gold-silver-coverage-real-reference-result-v1"
READY = "HISTORICAL_SILVER_2023_24_MISSING_TEAM_FEATURES_ROOT_CAUSE_REQUEST_VALID_AWAITING_EXPLICIT_USER_APPROVAL"
BLOCKED = "HISTORICAL_SILVER_2023_24_MISSING_TEAM_FEATURES_ROOT_CAUSE_REQUEST_STRUCTURAL_BLOCKED"
EXPECTED_CATEGORIES = [
    "nbastats_game_present_pbpstats_game_absent",
    "no_event_or_possession_source_rows",
    "pbpstats_possessions_all_offense_unresolved",
    "pbpstats_single_expected_offense_team_coverage",
    "pbpstats_offense_team_identity_mismatch",
    "possession_metadata_count_mismatch",
    "feature_aggregation_omission_after_valid_possessions",
    "silver_game_identity_unresolved",
    "unclassified",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def evaluate(
    request: dict[str, Any],
    implementation: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    checks: dict[str, bool] = {}

    def check(name: str, condition: Any) -> None:
        checks[name] = bool(condition)

    check("request_schema", request.get("schema_version") == REQUEST_SCHEMA)
    check("request_id", request.get("request_id") == REQUEST_ID)
    check("request_waiting", request.get("request_state") == "AWAITING_EXPLICIT_USER_APPROVAL")

    evidence = request.get("upstream_evidence", {})
    check("evidence_result", evidence.get("coverage_result") == "data/research/historical-gold-silver-coverage-real-reference-result-v1.json")
    check("evidence_run", evidence.get("coverage_workflow_run_id") == 29819457942)
    check("evidence_outcome", evidence.get("coverage_formal_outcome") == "HISTORICAL_GOLD_SILVER_COVERAGE_RECONCILIATION_SOURCE_DATA_GAP_CONFIRMED")
    check("evidence_implementation", evidence.get("implementation") == "data/research/historical-silver-2023-24-missing-team-features-root-cause-implementation-v1.json")
    check("evidence_commit", evidence.get("implementation_merge_commit") == "be61b82d74ba17f500787d2685275e572f209b1d")
    check("evidence_validation_run", evidence.get("implementation_validation_workflow_run_id") == 29821350899)
    check("evidence_artifact", evidence.get("implementation_validation_artifact_id") == 8491472454)
    check("evidence_digest", evidence.get("implementation_validation_artifact_digest") == "sha256:c61d635a0af8f676ae0fb7bd7378cccf2073313bc652fe4561ae7b1f0c37efe2")

    scope = request.get("frozen_scope", {})
    check("scope_label", scope.get("season_label") == "2023-24")
    check("scope_year", scope.get("season_start_year") == 2023)
    check("scope_source", scope.get("reference_source_path") == "shufinskiy/nba_data")
    check("scope_games", scope.get("expected_silver_games") == 1230)
    check("scope_missing", scope.get("expected_games_without_team_features") == 2)
    check("scope_no_candidate", scope.get("candidate_csv_required") is False)
    check("scope_candidate_forbidden", scope.get("candidate_csv_download_allowed") is False)
    check("scope_no_gold", scope.get("gold_database_required") is False)
    check("scope_gold_builder_forbidden", scope.get("gold_builder_execution_allowed") is False)

    execution = request.get("one_time_execution_scope", {})
    check("one_time", execution.get("one_time_only") is True)
    check("max_one", execution.get("maximum_execution_count") == 1)
    check("dispatch_only", execution.get("workflow_dispatch_only") is True)
    check("no_push", execution.get("automatic_main_push_execution_allowed") is False)
    check("no_pr", execution.get("pull_request_execution_allowed") is False)
    check("no_schedule", execution.get("scheduled_execution_allowed") is False)
    check("no_concurrent", execution.get("concurrent_execution_allowed") is False)
    check("reference_download_after_approval", execution.get("temporary_reference_archive_download_allowed_after_approval") is True)
    check("reference_read_after_approval", execution.get("temporary_reference_rows_may_be_read_after_approval") is True)
    check("silver_rebuild_after_approval", execution.get("temporary_2023_24_silver_rebuild_allowed_after_approval") is True)
    check("diagnostics_after_approval", execution.get("temporary_root_cause_diagnostics_allowed_after_approval") is True)
    check("no_builder_change", execution.get("silver_builder_code_change_during_execution_allowed") is False)
    check("no_manual_override", execution.get("manual_row_insertion_or_override_allowed") is False)
    check("no_fuzzy", execution.get("fuzzy_matching_allowed") is False)
    check("no_score_repair", execution.get("score_assisted_identity_repair_allowed") is False)
    check("no_silver_replacement", execution.get("historical_silver_replacement_allowed") is False)
    check("no_gold_replacement", execution.get("historical_gold_replacement_allowed") is False)

    diagnostic = request.get("diagnostic_contract", {})
    check("categories", diagnostic.get("classification_categories") == EXPECTED_CATEGORIES)
    for key in (
        "individual_game_ids_may_be_emitted",
        "individual_dates_may_be_emitted",
        "individual_team_codes_may_be_emitted",
        "row_level_records_may_be_emitted",
        "row_key_hashes_may_be_emitted",
    ):
        check(f"diagnostic_{key}", diagnostic.get(key) is False)

    output = request.get("output_boundary", {})
    check("aggregate_only", output.get("aggregate_json_only") is True)
    check("one_output", output.get("maximum_public_output_files") == 1)
    check("output_size", output.get("maximum_public_output_bytes") == 1048576)
    check("raw_rows_zero", output.get("raw_rows_emitted") == 0)
    check("raw_files_false", output.get("raw_files_emitted") is False)
    check("no_silver_artifact", output.get("silver_database_uploaded_as_artifact") is False)
    check("no_archive_artifact", output.get("source_archives_uploaded_as_artifact") is False)
    check("temporary_deleted", output.get("temporary_material_deleted_before_artifact_upload") is True)

    approval = request.get("approval_boundary", {})
    check("approval_required", approval.get("explicit_user_approval_required") is True)
    check("approval_not_granted", approval.get("approval_granted") is False)
    check("approval_identity_empty", approval.get("approved_by") is None and approval.get("approved_at") is None)
    check("approval_record_empty", approval.get("approval_record") is None)
    check("execution_disabled", approval.get("execution_enabled") is False)
    template = str(approval.get("approval_text_template", ""))
    check("approval_template_request", REQUEST_ID in template)
    check("approval_template_candidate_forbidden", "不得下載或讀取 candidate CSV" in template)
    check("approval_template_no_gold", "不得建立或修改 Gold" in template)

    current = request.get("current_execution_boundary", {})
    check("network_zero", current.get("network_calls_made") == 0)
    check("reference_not_read", current.get("real_reference_rows_read") is False)
    check("not_executed", current.get("real_root_cause_audit_executed") is False)
    check("count_zero", current.get("execution_count") == 0)
    check("current_disabled", current.get("execution_enabled") is False)
    check("role_unchanged", current.get("source_role_changed") is False)
    check("builder_not_ready", current.get("ready_for_silver_builder_change") is False)
    check("gold_not_ready", current.get("ready_for_gold_rebuild") is False)
    check("rerun_not_ready", current.get("ready_for_cross_source_audit_rerun") is False)
    check("market_not_ready", current.get("ready_for_market_backtest") is False)
    check("model_not_ready", current.get("ready_for_model_retraining") is False)
    check("edge_not_ready", current.get("ready_for_betting_edge_claim") is False)
    check("stake_zero", current.get("formal_stake") == 0)

    next_state = request.get("next_state_if_request_validation_passes", {})
    check("next_state", next_state.get("formal_state") == READY)
    check("next_user_approval", next_state.get("ready_for_user_approval") is True)
    check("next_not_execution", next_state.get("ready_for_execution") is False)
    check("next_not_executed", next_state.get("real_root_cause_audit_executed") is False)
    check("next_role_unchanged", next_state.get("source_role_changed") is False)
    check("next_stake_zero", next_state.get("formal_stake") == 0)

    check("implementation_schema", implementation.get("schema_version") == IMPLEMENTATION_SCHEMA)
    check("implementation_ready", implementation.get("formal_state") == "HISTORICAL_SILVER_2023_24_MISSING_TEAM_FEATURES_ROOT_CAUSE_IMPLEMENTATION_READY_REAL_EXECUTION_DISABLED")
    check("implementation_analyzer", implementation.get("analyzer") == "scripts/analyze_historical_silver_missing_team_features_root_cause_v1.py")
    check("implementation_synthetic", implementation.get("validation_mode", {}).get("synthetic_fixture_only") is True)
    check("implementation_no_network", implementation.get("validation_mode", {}).get("network_calls") is False)
    check("implementation_no_real_read", implementation.get("validation_mode", {}).get("real_reference_rows_read") is False)
    check("implementation_no_real_execution", implementation.get("validation_mode", {}).get("real_root_cause_audit_executed") is False)
    check("implementation_stake", implementation.get("downstream_permissions", {}).get("formal_stake") == 0)

    check("result_schema", result.get("schema_version") == RESULT_SCHEMA)
    check("result_run", result.get("workflow_run_id") == 29819457942)
    check("result_outcome", result.get("formal_outcome") == "HISTORICAL_GOLD_SILVER_COVERAGE_RECONCILIATION_SOURCE_DATA_GAP_CONFIRMED")
    check("result_silver", result.get("silver_game_rows") == 5826)
    check("result_gold", result.get("gold_matchup_rows") == 5824)
    check("result_gap", result.get("missing_gold_for_silver") == 2)
    check("result_season", result.get("missing_season") == "2023-24")
    check("result_missing_both", result.get("missing_both_team_features") == 2)
    check("result_builder_false", result.get("builder_repair_required") is False)
    check("result_source_true", result.get("source_data_reconciliation_required") is True)
    check("result_consumed", result.get("request_consumed") is True)
    check("result_no_repeat", result.get("repeat_execution_allowed") is False)
    check("result_stake", result.get("formal_stake") == 0)

    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": "historical-silver-2023-24-missing-team-features-root-cause-request-validation-report-v1",
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
            "source_role_changed": False,
            "formal_stake": 0,
        },
        "decision": {
            "ready_for_explicit_user_approval": not failed,
            "ready_for_execution": False,
            "ready_for_silver_builder_change": False,
            "ready_for_gold_rebuild": False,
            "ready_for_cross_source_audit_rerun": False,
            "ready_for_market_backtest": False,
            "ready_for_model_retraining": False,
            "ready_for_betting_edge_claim": False,
            "formal_stake": 0,
        },
    }


def self_test(
    request: dict[str, Any],
    implementation: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, bool]:
    baseline = evaluate(request, implementation, result)
    assert baseline["formal_state"] == READY, baseline
    tests = {"baseline_passes": True}
    cases = {
        "approval_granted_blocks": ("request", ["approval_boundary", "approval_granted"], True),
        "candidate_download_blocks": ("request", ["frozen_scope", "candidate_csv_download_allowed"], True),
        "gold_execution_blocks": ("request", ["frozen_scope", "gold_builder_execution_allowed"], True),
        "raw_output_blocks": ("request", ["output_boundary", "raw_files_emitted"], True),
        "builder_change_blocks": ("request", ["one_time_execution_scope", "silver_builder_code_change_during_execution_allowed"], True),
        "scope_drift_blocks": ("request", ["frozen_scope", "season_start_year"], 2022),
        "gap_drift_blocks": ("result", ["missing_both_team_features"], 3),
        "nonzero_stake_blocks": ("request", ["current_execution_boundary", "formal_stake"], 1),
    }
    for name, (target_name, path, value) in cases.items():
        req = copy.deepcopy(request)
        impl = copy.deepcopy(implementation)
        res = copy.deepcopy(result)
        target = {"request": req, "implementation": impl, "result": res}[target_name]
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        report = evaluate(req, impl, res)
        tests[name] = report["formal_state"] == BLOCKED
    assert all(tests.values()), tests
    return tests


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--implementation", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    request = read_json(args.request)
    implementation = read_json(args.implementation)
    result = read_json(args.result)
    report = evaluate(request, implementation, result)
    if args.self_test:
        report["self_tests"] = self_test(request, implementation, result)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if len(payload.encode("utf-8")) > 1048576:
        raise RuntimeError("request validation report exceeds 1 MiB")
    args.output.write_text(payload, encoding="utf-8")
    print(json.dumps({
        "formal_state": report["formal_state"],
        "checks_passed": report["checks_passed"],
        "checks_total": report["checks_total"],
        "ready_for_explicit_user_approval": report["decision"]["ready_for_explicit_user_approval"],
        "formal_stake": report["decision"]["formal_stake"],
    }, ensure_ascii=False, indent=2))
    return 0 if report["formal_state"] == READY else 1


if __name__ == "__main__":
    raise SystemExit(main())
