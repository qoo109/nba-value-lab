#!/usr/bin/env python3
"""Validate the one-time Historical Gold/Silver real-reference request v1.

Policy-only validation: no network, no real reference reads, no execution.
"""
from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REQUEST_ID = "HISTORICAL-GOLD-SILVER-COVERAGE-RECONCILIATION-2026-07-21-001"
REQUEST_SCHEMA = "historical-gold-silver-coverage-real-reference-execution-request-v1"
IMPLEMENTATION_SCHEMA = "historical-gold-silver-coverage-reconciliation-implementation-v1"
RESULT_SCHEMA = "legacy-market-real-file-audit-retry-002-result-v1"
READY = "HISTORICAL_GOLD_SILVER_COVERAGE_RECONCILIATION_REQUEST_VALID_AWAITING_EXPLICIT_USER_APPROVAL"
BLOCKED = "HISTORICAL_GOLD_SILVER_COVERAGE_RECONCILIATION_REQUEST_STRUCTURAL_BLOCKED"
EXPECTED_YEARS = [2019, 2020, 2021, 2022, 2023]
EXPECTED_LABELS = ["2019-20", "2020-21", "2021-22", "2022-23", "2023-24"]
EXPECTED_CATEGORIES = [
    "missing_home_team_feature",
    "missing_away_team_feature",
    "missing_both_team_features",
    "silver_feature_pair_identity_mismatch",
    "gold_team_feature_transfer_mismatch",
    "gold_matchup_builder_omission",
    "silver_game_outside_gold_identity_contract",
    "unclassified",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def evaluate(request: dict[str, Any], implementation: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    checks: dict[str, bool] = {}

    def check(name: str, condition: Any) -> None:
        checks[name] = bool(condition)

    check("request_schema", request.get("schema_version") == REQUEST_SCHEMA)
    check("request_id", request.get("request_id") == REQUEST_ID)
    check("request_waiting", request.get("request_state") == "AWAITING_EXPLICIT_USER_APPROVAL")

    evidence = request.get("upstream_evidence", {})
    check("evidence_run", evidence.get("real_audit_workflow_run_id") == 29810347326)
    check("evidence_sha", evidence.get("real_audit_workflow_sha") == "78ac0931cd28b2315b6e24954dc9ad1af9caf4f0")
    check("evidence_outcome", evidence.get("real_audit_formal_outcome") == "USER_SUPPLIED_LEGACY_MARKET_ARCHIVE_CROSS_SOURCE_AUDIT_RESEARCH_BLOCKED")
    check("evidence_scientific_gates", evidence.get("all_scientific_gates_passed") is True)
    check("evidence_boundary", evidence.get("blocking_boundary") == "reference_missing_gold_for_silver")
    check("evidence_silver", evidence.get("silver_rows_in_scope") == 5826)
    check("evidence_gold", evidence.get("gold_matchup_rows") == 5824)
    check("evidence_gap", evidence.get("missing_gold_for_silver") == 2)
    check("evidence_implementation_commit", evidence.get("implementation_merge_commit") == "0d8d0134e05d00fb8e41220cc0621df24a275257")

    scope = request.get("frozen_reference_scope", {})
    check("scope_years", scope.get("season_start_years") == EXPECTED_YEARS)
    check("scope_labels", scope.get("season_labels") == EXPECTED_LABELS)
    check("scope_source", scope.get("reference_source_path") == "shufinskiy/nba_data")
    check("scope_identity", scope.get("identity_key") == "game_id")
    check("scope_unchanged", scope.get("reference_scope_change_allowed") is False)

    execution = request.get("one_time_execution_scope", {})
    check("one_time", execution.get("one_time_only") is True)
    check("maximum_one", execution.get("maximum_execution_count") == 1)
    check("dispatch_only", execution.get("workflow_dispatch_only") is True)
    check("no_push", execution.get("automatic_main_push_execution_allowed") is False)
    check("no_pr_execution", execution.get("pull_request_execution_allowed") is False)
    check("no_schedule", execution.get("scheduled_execution_allowed") is False)
    check("no_concurrency", execution.get("concurrent_execution_allowed") is False)
    check("candidate_not_required", execution.get("candidate_csv_required") is False)
    check("candidate_download_forbidden", execution.get("candidate_csv_download_allowed") is False)
    check("reference_download_after_approval", execution.get("temporary_reference_archive_download_allowed_after_approval") is True)
    check("reference_read_after_approval", execution.get("temporary_reference_rows_may_be_read_after_approval") is True)
    check("reference_rebuild_after_approval", execution.get("temporary_reference_rebuild_allowed_after_approval") is True)
    check("diagnostics_after_approval", execution.get("temporary_row_level_diagnostics_may_be_computed_after_approval") is True)
    check("no_builder_change", execution.get("gold_builder_code_change_during_execution_allowed") is False)
    check("no_replacement", execution.get("historical_silver_or_gold_replacement_allowed") is False)
    check("no_manual_override", execution.get("manual_row_insertion_or_override_allowed") is False)
    check("no_fuzzy", execution.get("fuzzy_matching_allowed") is False)
    check("no_score_repair", execution.get("score_assisted_identity_repair_allowed") is False)

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
    check("output_one", output.get("maximum_public_output_files") == 1)
    check("output_size", output.get("maximum_public_output_bytes") == 1048576)
    check("raw_rows_zero", output.get("raw_rows_emitted") == 0)
    check("raw_files_false", output.get("raw_files_emitted") is False)
    check("no_db_artifact", output.get("reference_databases_uploaded_as_artifact") is False)
    check("no_archive_artifact", output.get("source_archives_uploaded_as_artifact") is False)
    check("temporary_deleted", output.get("temporary_material_deleted_before_artifact_upload") is True)

    approval = request.get("approval_boundary", {})
    check("approval_required", approval.get("explicit_user_approval_required") is True)
    check("approval_not_granted", approval.get("approval_granted") is False)
    check("approval_identity_empty", approval.get("approved_by") is None and approval.get("approved_at") is None)
    check("approval_record_empty", approval.get("approval_record") is None)
    check("execution_disabled", approval.get("execution_enabled") is False)
    check("approval_template_request", REQUEST_ID in str(approval.get("approval_text_template", "")))
    check("approval_template_candidate_forbidden", "不得下載或讀取 candidate CSV" in str(approval.get("approval_text_template", "")))

    current = request.get("current_execution_boundary", {})
    check("network_zero", current.get("network_calls_made") == 0)
    check("reference_not_read", current.get("real_reference_rows_read") is False)
    check("not_executed", current.get("real_reconciliation_executed") is False)
    check("execution_count_zero", current.get("execution_count") == 0)
    check("current_disabled", current.get("execution_enabled") is False)
    check("role_unchanged", current.get("source_role_changed") is False)
    check("builder_change_not_ready", current.get("ready_for_gold_builder_change") is False)
    check("rerun_not_ready", current.get("ready_for_cross_source_audit_rerun") is False)
    check("market_not_ready", current.get("ready_for_market_backtest") is False)
    check("model_not_ready", current.get("ready_for_model_retraining") is False)
    check("edge_not_ready", current.get("ready_for_betting_edge_claim") is False)
    check("stake_zero", current.get("formal_stake") == 0)

    next_state = request.get("next_state_if_request_validation_passes", {})
    check("next_state", next_state.get("formal_state") == READY)
    check("next_user_approval", next_state.get("ready_for_user_approval") is True)
    check("next_not_execution", next_state.get("ready_for_execution") is False)
    check("next_not_executed", next_state.get("real_reconciliation_executed") is False)
    check("next_role_unchanged", next_state.get("source_role_changed") is False)
    check("next_stake_zero", next_state.get("formal_stake") == 0)

    check("implementation_schema", implementation.get("schema_version") == IMPLEMENTATION_SCHEMA)
    check("implementation_ready", implementation.get("formal_state") == "HISTORICAL_GOLD_SILVER_COVERAGE_RECONCILIATION_IMPLEMENTATION_READY_REAL_EXECUTION_DISABLED")
    check("implementation_analyzer", implementation.get("analyzer") == "scripts/analyze_historical_gold_silver_coverage_v1.py")
    check("implementation_synthetic", implementation.get("validation_mode", {}).get("synthetic_fixture_only") is True)
    check("implementation_no_network", implementation.get("validation_mode", {}).get("network_calls") is False)
    check("implementation_no_real_read", implementation.get("validation_mode", {}).get("real_reference_rows_read") is False)
    check("implementation_no_real_execution", implementation.get("validation_mode", {}).get("real_reconciliation_executed") is False)
    check("implementation_stake", implementation.get("downstream_permissions", {}).get("formal_stake") == 0)

    check("result_schema", result.get("schema_version") == RESULT_SCHEMA)
    check("result_request", result.get("request_id") == "LEGACY-MARKET-ARCHIVE-AUDIT-2026-07-21-002")
    check("result_run", result.get("workflow_run_id") == 29810347326)
    check("result_executed", result.get("real_file_audit_executed") is True)
    check("result_gates", result.get("all_scientific_gates_passed") is True)
    check("result_outcome", result.get("formal_outcome") == "USER_SUPPLIED_LEGACY_MARKET_ARCHIVE_CROSS_SOURCE_AUDIT_RESEARCH_BLOCKED")
    check("result_gap", result.get("reference_counts", {}).get("missing_gold_for_silver") == 2)
    check("result_consumed", result.get("request_consumed") is True)
    check("result_no_repeat", result.get("repeat_execution_allowed") is False)
    check("result_stake", result.get("boundaries", {}).get("formal_stake") == 0)

    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": "historical-gold-silver-coverage-real-reference-request-validation-report-v1",
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
            "real_reconciliation_executed": False,
            "raw_rows_emitted": 0,
            "raw_files_emitted": False,
            "execution_enabled": False,
            "source_role_changed": False,
            "formal_stake": 0,
        },
        "decision": {
            "ready_for_explicit_user_approval": not failed,
            "ready_for_execution": False,
            "ready_for_gold_builder_change": False,
            "ready_for_cross_source_audit_rerun": False,
            "ready_for_market_backtest": False,
            "ready_for_model_retraining": False,
            "ready_for_betting_edge_claim": False,
            "formal_stake": 0,
        },
    }


def self_test(request: dict[str, Any], implementation: dict[str, Any], result: dict[str, Any]) -> dict[str, bool]:
    baseline = evaluate(request, implementation, result)
    assert baseline["formal_state"] == READY, baseline
    tests = {"baseline_passes": True}
    cases = {
        "approval_granted_blocks": ("request", ["approval_boundary", "approval_granted"], True),
        "candidate_download_blocks": ("request", ["one_time_execution_scope", "candidate_csv_download_allowed"], True),
        "raw_output_blocks": ("request", ["output_boundary", "raw_files_emitted"], True),
        "builder_change_blocks": ("request", ["one_time_execution_scope", "gold_builder_code_change_during_execution_allowed"], True),
        "scope_drift_blocks": ("request", ["frozen_reference_scope", "season_start_years"], [2020, 2021, 2022, 2023]),
        "gap_drift_blocks": ("result", ["reference_counts", "missing_gold_for_silver"], 3),
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
        raise RuntimeError("validation report exceeds 1 MiB")
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
