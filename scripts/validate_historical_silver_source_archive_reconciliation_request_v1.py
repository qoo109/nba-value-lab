#!/usr/bin/env python3
"""Validate the 2023-24 Historical Silver source archive reconciliation request.

Policy-only: no network access, no source archive reads, and no execution.
"""
from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REQUEST_ID = "HISTORICAL-SILVER-2023-24-SOURCE-ARCHIVE-RECONCILIATION-2026-07-22-001"
REQUEST_SCHEMA = "historical-silver-2023-24-source-archive-reconciliation-request-v1"
DESIGN_SCHEMA = "historical-silver-2023-24-source-archive-reconciliation-design-v1"
RESULT_SCHEMA = "historical-silver-2023-24-missing-team-features-root-cause-retry-002-result-v1"
READY = "HISTORICAL_SILVER_2023_24_SOURCE_ARCHIVE_RECONCILIATION_REQUEST_VALID_AWAITING_EXPLICIT_USER_APPROVAL"
BLOCKED = "HISTORICAL_SILVER_2023_24_SOURCE_ARCHIVE_RECONCILIATION_REQUEST_STRUCTURAL_BLOCKED"
EXPECTED_SECTIONS = [
    "archive_manifest_counts",
    "nbastats_game_coverage_counts",
    "pbpstats_game_coverage_counts",
    "coverage_overlap_counts",
    "missing_reason_count_histogram",
    "decision_summary",
]
EXPECTED_DECISIONS = [
    "SOURCE_ARCHIVE_GAP_STABLE",
    "SOURCE_ARCHIVE_GAP_NOT_CONFIRMED",
    "RECONCILIATION_BLOCKED",
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
    design: dict[str, Any],
    result: dict[str, Any],
    registry: dict[str, Any],
) -> dict[str, Any]:
    checks: dict[str, bool] = {}

    def check(name: str, condition: Any) -> None:
        checks[name] = bool(condition)

    check("request_schema", request.get("schema_version") == REQUEST_SCHEMA)
    check("request_id", request.get("request_id") == REQUEST_ID)
    check("request_waiting", request.get("request_state") == "AWAITING_EXPLICIT_USER_APPROVAL")
    check("purpose_mentions_aggregate", "aggregate-only" in str(request.get("purpose", "")))

    evidence = request.get("upstream_evidence", {})
    check("evidence_design", evidence.get("design") == "data/research/historical-silver-2023-24-source-archive-reconciliation-design-v1.json")
    check("evidence_design_state", evidence.get("design_formal_state") == "HISTORICAL_SILVER_2023_24_SOURCE_ARCHIVE_RECONCILIATION_DESIGN_READY")
    check("evidence_design_run", evidence.get("design_validation_workflow_run_id") == 29896243732)
    check("evidence_design_artifact", evidence.get("design_validation_artifact_id") == 8520078485)
    check("evidence_design_digest", evidence.get("design_validation_artifact_digest") == "sha256:48726113ae5662bbb62549f11b7ccff89b6aece952a959d456ec48c26fea7e54")
    check("evidence_triggering_result", evidence.get("triggering_result") == "data/research/historical-silver-2023-24-missing-team-features-root-cause-retry-002-result-v1.json")
    check("evidence_triggering_run", evidence.get("triggering_workflow_run_id") == 29890527281)
    check("evidence_triggering_artifact", evidence.get("triggering_artifact_id") == 8518081820)
    check("evidence_triggering_digest", evidence.get("triggering_artifact_digest") == "sha256:a10b1c63b3edff65e4a3eeb86e5062f245fdc300e61b2e40ff0ba8cc4df98f40")
    check("evidence_triggering_outcome", evidence.get("triggering_formal_outcome") == "HISTORICAL_SILVER_MISSING_TEAM_FEATURES_SOURCE_GAP_CONFIRMED")

    scope = request.get("frozen_scope", {})
    check("scope_label", scope.get("season_label") == "2023-24")
    check("scope_year", scope.get("season_start_year") == 2023)
    check("scope_source_id", scope.get("source_id") == "shufinskiy_nba_data")
    check("scope_source_path", scope.get("reference_source_path") == "shufinskiy/nba_data")
    check("scope_games", scope.get("expected_silver_games") == 1230)
    check("scope_zero_features", scope.get("expected_games_without_team_features") == 2)
    check("scope_classified", scope.get("expected_classified_missing_games") == 2)
    check("scope_unclassified", scope.get("expected_unclassified_missing_games") == 0)
    check("scope_reason", scope.get("expected_missing_reason") == "nbastats_game_present_pbpstats_game_absent")
    check("scope_reason_count", scope.get("expected_missing_reason_count") == 2)
    for key in (
        "candidate_csv_required",
        "candidate_csv_download_allowed",
        "chris_munch_raw_csv_allowed",
        "eoin_raw_bundle_allowed",
        "gold_database_required",
        "gold_builder_execution_allowed",
    ):
        check(f"scope_{key}", scope.get(key) is False)

    execution = request.get("one_time_execution_scope", {})
    check("one_time", execution.get("one_time_only") is True)
    check("max_one", execution.get("maximum_execution_count") == 1)
    check("dispatch_only", execution.get("workflow_dispatch_only") is True)
    for key in (
        "automatic_main_push_execution_allowed",
        "pull_request_execution_allowed",
        "scheduled_execution_allowed",
        "concurrent_execution_allowed",
    ):
        check(f"execution_{key}", execution.get(key) is False)
    for key in (
        "temporary_shufinskiy_source_archive_download_allowed_after_approval",
        "temporary_shufinskiy_source_archive_read_allowed_after_approval",
        "temporary_archive_manifest_scan_allowed_after_approval",
        "temporary_archive_file_inventory_allowed_after_approval",
        "temporary_coverage_overlap_count_allowed_after_approval",
        "temporary_2023_24_silver_reference_read_allowed_after_approval",
    ):
        check(f"execution_{key}", execution.get(key) is True)
    for key in (
        "silver_builder_code_change_during_execution_allowed",
        "manual_row_insertion_or_override_allowed",
        "fuzzy_matching_allowed",
        "score_assisted_identity_repair_allowed",
        "historical_silver_replacement_allowed",
        "historical_gold_replacement_allowed",
        "candidate_source_download_allowed",
    ):
        check(f"execution_{key}", execution.get(key) is False)

    contract = request.get("reconciliation_contract", {})
    check("contract_sections", contract.get("allowed_aggregate_sections") == EXPECTED_SECTIONS)
    check("contract_decisions", contract.get("required_decision_values") == EXPECTED_DECISIONS)
    for key in (
        "individual_game_ids_may_be_emitted",
        "individual_dates_may_be_emitted",
        "individual_team_codes_may_be_emitted",
        "row_level_records_may_be_emitted",
        "row_key_hashes_may_be_emitted",
        "source_file_paths_may_be_emitted",
        "source_file_hashes_may_be_emitted",
    ):
        check(f"contract_{key}", contract.get(key) is False)

    output = request.get("output_boundary", {})
    check("aggregate_only", output.get("aggregate_json_only") is True)
    check("one_output", output.get("maximum_public_output_files") == 1)
    check("output_size", output.get("maximum_public_output_bytes") == 1048576)
    check("raw_rows_zero", output.get("raw_rows_emitted") == 0)
    for key in (
        "raw_files_emitted",
        "silver_database_uploaded_as_artifact",
        "gold_database_uploaded_as_artifact",
        "source_archives_uploaded_as_artifact",
        "candidate_csv_uploaded_as_artifact",
    ):
        check(f"output_{key}", output.get(key) is False)
    check("temporary_deleted", output.get("temporary_material_deleted_before_artifact_upload") is True)

    approval = request.get("approval_boundary", {})
    check("approval_required", approval.get("explicit_user_approval_required") is True)
    check("approval_not_granted", approval.get("approval_granted") is False)
    check("approval_identity_empty", approval.get("approved_by") is None and approval.get("approved_at") is None)
    check("approval_record_empty", approval.get("approval_record") is None)
    check("execution_disabled", approval.get("execution_enabled") is False)
    template = str(approval.get("approval_text_template", ""))
    check("approval_template_request", REQUEST_ID in template)
    check("approval_template_no_candidate", "不得下載或讀取 Chris Munch" in template)
    check("approval_template_no_file_hash", "source file hashes" in template)
    check("approval_template_no_gold", "Silver／Gold" in template)
    check("approval_template_stake", "非 0 Stake" in template)

    current = request.get("current_execution_boundary", {})
    check("network_zero", current.get("network_calls_made") == 0)
    check("archives_not_read", current.get("shufinskiy_source_archives_read") is False)
    check("candidate_not_read", current.get("candidate_csv_rows_read") is False)
    check("not_executed", current.get("real_reconciliation_executed") is False)
    check("count_zero", current.get("execution_count") == 0)
    check("current_disabled", current.get("execution_enabled") is False)
    for key in (
        "source_role_changed",
        "ready_for_silver_builder_change",
        "ready_for_silver_exception_patch",
        "ready_for_gold_rebuild",
        "ready_for_cross_source_audit_rerun",
        "ready_for_chris_munch_data_execution",
        "ready_for_market_backtest",
        "ready_for_model_retraining",
        "ready_for_betting_edge_claim",
    ):
        check(f"current_{key}", current.get(key) is False)
    check("stake_zero", current.get("formal_stake") == 0)

    next_state = request.get("next_state_if_request_validation_passes", {})
    check("next_state", next_state.get("formal_state") == READY)
    check("next_user_approval", next_state.get("ready_for_user_approval") is True)
    check("next_not_execution", next_state.get("ready_for_execution") is False)
    check("next_not_executed", next_state.get("real_reconciliation_executed") is False)
    check("next_role_unchanged", next_state.get("source_role_changed") is False)
    check("next_stake_zero", next_state.get("formal_stake") == 0)

    check("design_schema", design.get("schema_version") == DESIGN_SCHEMA)
    check("design_ready", design.get("formal_state") == "HISTORICAL_SILVER_2023_24_SOURCE_ARCHIVE_RECONCILIATION_DESIGN_READY")
    check("design_trigger_result", design.get("triggering_result") == evidence.get("triggering_result"))
    check("design_trigger_run", design.get("triggering_workflow_run_id") == evidence.get("triggering_workflow_run_id"))
    check("design_reason", design.get("observed_gap", {}).get("missing_reason") == scope.get("expected_missing_reason"))
    check("design_reason_count", design.get("observed_gap", {}).get("missing_reason_count") == scope.get("expected_missing_reason_count"))
    check("design_request_ready", design.get("downstream_permissions", {}).get("ready_for_source_archive_reconciliation_request") is True)
    check("design_no_data", design.get("output_boundary", {}).get("shufinskiy_raw_rows_read") is False)
    check("design_stake", design.get("downstream_permissions", {}).get("formal_stake") == 0)

    check("result_schema", result.get("schema_version") == RESULT_SCHEMA)
    check("result_run", result.get("workflow_run_id") == evidence.get("triggering_workflow_run_id"))
    check("result_artifact", result.get("artifact_id") == evidence.get("triggering_artifact_id"))
    check("result_digest", result.get("artifact_digest") == evidence.get("triggering_artifact_digest"))
    check("result_outcome", result.get("formal_outcome") == "HISTORICAL_SILVER_MISSING_TEAM_FEATURES_SOURCE_GAP_CONFIRMED")
    result_scope = result.get("scope", {})
    check("result_silver_games", result_scope.get("silver_games") == scope.get("expected_silver_games"))
    check("result_missing", result_scope.get("games_without_team_features") == scope.get("expected_games_without_team_features"))
    check("result_classified", result_scope.get("classified_missing_games") == scope.get("expected_classified_missing_games"))
    check("result_unclassified", result_scope.get("unclassified_missing_games") == scope.get("expected_unclassified_missing_games"))
    histogram = result.get("root_cause", {}).get("missing_by_reason", {})
    check("result_reason_count", histogram.get(scope.get("expected_missing_reason")) == scope.get("expected_missing_reason_count"))
    receipt = result.get("execution_receipt", {})
    decision = result.get("decision", {})
    check("result_consumed", receipt.get("request_consumed") is True)
    check("result_no_repeat", receipt.get("repeat_execution_allowed") is False)
    check("result_source_archive_required", decision.get("source_archive_reconciliation_required") is True)
    check("result_no_builder_repair", decision.get("silver_builder_repair_required") is False)
    check("result_stake", decision.get("formal_stake") == 0)

    sources = registry.get("sources", [])
    shufinskiy = next((source for source in sources if source.get("source_id") == "shufinskiy_nba_data"), {})
    policy = shufinskiy.get("source_archive_reconciliation_design", {})
    check("registry_shufinskiy_policy", policy.get("formal_state") == "HISTORICAL_SILVER_2023_24_SOURCE_ARCHIVE_RECONCILIATION_REQUEST_VALID_AWAITING_EXPLICIT_USER_APPROVAL")
    check("registry_request", policy.get("request") == "data/research/historical-silver-2023-24-source-archive-reconciliation-request-v1.json")
    check("registry_execution_not_approved", policy.get("execution_approved") is False)
    check("registry_execution_disabled", policy.get("execution_enabled") is False)
    check("registry_raw_zero", policy.get("raw_rows_emitted") == 0)
    check("registry_stake", policy.get("formal_stake") == 0)

    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": "historical-silver-2023-24-source-archive-reconciliation-request-validation-report-v1",
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
            "shufinskiy_source_archives_read": False,
            "candidate_csv_rows_read": False,
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
            "ready_for_silver_builder_change": False,
            "ready_for_silver_exception_patch": False,
            "ready_for_gold_rebuild": False,
            "ready_for_cross_source_audit_rerun": False,
            "ready_for_chris_munch_data_execution": False,
            "ready_for_market_backtest": False,
            "ready_for_model_retraining": False,
            "ready_for_betting_edge_claim": False,
            "formal_stake": 0,
        },
    }


def self_test(
    request: dict[str, Any],
    design: dict[str, Any],
    result: dict[str, Any],
    registry: dict[str, Any],
) -> dict[str, bool]:
    baseline = evaluate(request, design, result, registry)
    assert baseline["formal_state"] == READY, baseline
    tests = {"baseline_passes": True}
    cases = {
        "approval_granted_blocks": ("request", ["approval_boundary", "approval_granted"], True),
        "candidate_download_blocks": ("request", ["frozen_scope", "candidate_csv_download_allowed"], True),
        "raw_output_blocks": ("request", ["output_boundary", "raw_files_emitted"], True),
        "source_hash_output_blocks": ("request", ["reconciliation_contract", "source_file_hashes_may_be_emitted"], True),
        "builder_change_blocks": ("request", ["one_time_execution_scope", "silver_builder_code_change_during_execution_allowed"], True),
        "scope_drift_blocks": ("request", ["frozen_scope", "expected_games_without_team_features"], 3),
        "result_drift_blocks": ("result", ["scope", "games_without_team_features"], 3),
        "registry_execution_blocks": ("registry", ["sources", "shufinskiy_nba_data", "source_archive_reconciliation_design", "execution_enabled"], True),
        "nonzero_stake_blocks": ("request", ["current_execution_boundary", "formal_stake"], 1),
    }
    for name, (target_name, path, value) in cases.items():
        req = copy.deepcopy(request)
        des = copy.deepcopy(design)
        res = copy.deepcopy(result)
        reg = copy.deepcopy(registry)
        target: Any = {"request": req, "design": des, "result": res, "registry": reg}[target_name]
        if target_name == "registry" and path[0] == "sources":
            target = next(source for source in target["sources"] if source.get("source_id") == path[1])
            path = path[2:]
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        report = evaluate(req, des, res, reg)
        tests[name] = report["formal_state"] == BLOCKED
    assert all(tests.values()), tests
    return tests


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--design", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    request = read_json(args.request)
    design = read_json(args.design)
    result = read_json(args.result)
    registry = read_json(args.registry)
    report = evaluate(request, design, result, registry)
    if args.self_test:
        report["self_tests"] = self_test(request, design, result, registry)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["checks_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
