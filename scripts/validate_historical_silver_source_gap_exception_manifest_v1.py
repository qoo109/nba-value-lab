#!/usr/bin/env python3
"""Validate the privacy-safe Historical Silver 2023-24 source-gap exception manifest."""
from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MANIFEST_STATE = "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_MANIFEST_DESIGN_READY"
VALID_STATE = "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_MANIFEST_VALIDATED"
NEXT_STEP = "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_POLICY_READY_FOR_DESIGN"
RECONCILIATION_STATE = "HISTORICAL_SILVER_2023_24_SOURCE_ARCHIVE_RECONCILIATION_AGGREGATE_VALIDATION_PASS"
DIGEST = "sha256:2b42dca052d331bf94e31568b24492092beb00fef352405601fd812a8603b334"


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def validate(
    manifest: dict[str, Any],
    result: dict[str, Any],
    reconciliation_status: dict[str, Any],
    exception_status: dict[str, Any],
) -> dict[str, Any]:
    checks: dict[str, bool] = {}

    def add(name: str, value: Any) -> None:
        checks[name] = bool(value)

    add("manifest_schema", manifest.get("schema_version") == "historical-silver-2023-24-source-gap-exception-manifest-v1")
    add("manifest_state", manifest.get("formal_state") == MANIFEST_STATE)
    add("manifest_season", manifest.get("season_label") == "2023-24")
    add("manifest_source", manifest.get("source_id") == "shufinskiy_nba_data")

    trigger = manifest.get("triggering_reconciliation", {})
    add("trigger_result", trigger.get("result_record") == "data/research/historical-silver-2023-24-source-archive-reconciliation-result-v1.json")
    add("trigger_status", trigger.get("current_status_record") == "data/research/historical-silver-2023-24-source-archive-reconciliation-current-status-v2.json")
    add("trigger_run", trigger.get("workflow_run_id") == 29901869841)
    add("trigger_artifact", trigger.get("artifact_id") == 8522225397)
    add("trigger_digest", trigger.get("artifact_digest") == DIGEST)
    add("trigger_state", trigger.get("formal_state") == RECONCILIATION_STATE)
    add("trigger_decision", trigger.get("decision") == "SOURCE_ARCHIVE_GAP_STABLE")

    scope = manifest.get("aggregate_scope", {})
    add("scope_silver", scope.get("silver_games") == 1230)
    add("scope_feature_ready", scope.get("games_with_two_team_feature_rows") == 1228)
    add("scope_exceptions", scope.get("source_gap_exception_games") == 2)
    add("scope_unclassified", scope.get("unclassified_games") == 0)
    add("scope_sum", scope.get("silver_games") == scope.get("games_with_two_team_feature_rows", -1) + scope.get("source_gap_exception_games", -1))
    add("scope_reason", scope.get("missing_reason") == "nbastats_game_present_pbpstats_game_absent")
    add("scope_reason_count", scope.get("missing_reason_count") == 2)
    overlap = scope.get("coverage_overlap", {})
    add("scope_overlap", overlap == {
        "nbastats_game_count": 1230,
        "pbpstats_game_count": 1228,
        "overlap_game_count": 1228,
        "nbastats_only_game_count": 2,
        "pbpstats_only_game_count": 0,
    })
    add("scope_histogram", scope.get("team_feature_count_histogram") == {"0": 2, "2": 1228})

    exception = manifest.get("exception_class", {})
    add("exception_code", exception.get("exception_code") == "SOURCE_ARCHIVE_PBPSTATS_GAME_ABSENT")
    add("exception_stable", exception.get("upstream_gap_stable") is True)
    for key in ("silver_builder_defect", "gold_builder_defect", "identity_defect", "manual_repair_allowed"):
        add(f"exception_{key}", exception.get(key) is False)

    public = manifest.get("public_evidence_policy", {})
    add("public_aggregate", public.get("aggregate_only") is True)
    for key in (
        "game_ids_allowed", "dates_allowed", "team_codes_allowed", "source_file_paths_allowed",
        "source_file_hashes_allowed", "row_level_records_allowed", "row_key_hashes_allowed",
        "raw_rows_allowed", "raw_files_allowed",
    ):
        add(f"public_{key}", public.get(key) is False)
    add("public_size", public.get("maximum_public_output_bytes") == 1048576)

    handling = manifest.get("exception_handling_policy", {})
    add("handling_mode", handling.get("mode") == "DOCUMENTED_AGGREGATE_ONLY_NO_ROW_PATCH")
    add("handling_retain", handling.get("retain_existing_silver_game_rows") is True)
    for key in (
        "delete_silver_game_rows", "synthesize_team_feature_rows", "insert_manual_team_feature_rows",
        "impute_missing_features_as_zero", "copy_features_from_another_source", "override_builder_output",
        "historical_silver_replacement", "historical_gold_replacement", "runtime_identifiers_may_be_persisted_publicly",
    ):
        add(f"handling_{key}", handling.get(key) is False)
    add("handling_rule", handling.get("runtime_identification_rule") == "silver_game_present AND nbastats_game_present AND pbpstats_game_absent AND team_feature_row_count_equals_0")

    eligibility = manifest.get("downstream_eligibility", {})
    add("eligibility_identity", eligibility.get("silver_game_identity_retained") is True)
    for key in (
        "possession_derived_team_features_available", "gold_matchup_eligible_without_new_valid_source_rows",
        "model_training_eligible", "model_evaluation_eligible", "market_backtest_reference_eligible",
        "manual_override_eligible", "ready_for_silver_builder_change", "ready_for_silver_exception_patch",
        "ready_for_gold_rebuild", "ready_for_cross_source_audit_rerun", "ready_for_market_backtest",
        "ready_for_model_retraining", "ready_for_betting_edge_claim",
    ):
        add(f"eligibility_{key}", eligibility.get(key) is False)
    add("eligibility_stake", eligibility.get("formal_stake") == 0)

    boundaries = manifest.get("execution_boundary", {})
    add("boundary_design", boundaries.get("design_only") is True)
    for key in (
        "network_calls_made", "source_archives_read", "candidate_csv_downloaded_or_read",
        "chris_munch_data_execution", "eoin_bundle_execution", "silver_database_created_or_modified",
        "gold_database_created_or_read", "builder_execution", "raw_files_emitted",
    ):
        add(f"boundary_{key}", boundaries.get(key) is False)
    add("boundary_raw_rows", boundaries.get("raw_rows_emitted") == 0)
    add("boundary_stake", boundaries.get("formal_stake") == 0)

    next_state = manifest.get("next_state_if_valid", {})
    add("next_state", next_state.get("formal_state") == VALID_STATE)
    add("next_step", next_state.get("next_research_step") == NEXT_STEP)
    for key in (
        "ready_for_data_execution", "ready_for_silver_builder_change", "ready_for_gold_rebuild",
        "ready_for_cross_source_audit_rerun", "ready_for_market_backtest",
    ):
        add(f"next_{key}", next_state.get(key) is False)
    add("next_stake", next_state.get("formal_stake") == 0)

    add("result_state", result.get("formal_state") == RECONCILIATION_STATE)
    add("result_decision", result.get("decision", {}).get("decision") == "SOURCE_ARCHIVE_GAP_STABLE")
    add("result_gap", result.get("decision", {}).get("source_archive_gap_stable") is True)
    add("result_coverage", result.get("coverage_overlap_counts", {}).get("nbastats_only_game_count") == 2)
    add("result_reason", result.get("missing_reason_count_histogram", {}).get("nbastats_game_present_pbpstats_game_absent") == 2)
    add("result_consumed", result.get("execution_receipt", {}).get("request_consumed") is True)
    add("result_no_repeat", result.get("execution_receipt", {}).get("repeat_execution_allowed") is False)

    add("reconciliation_status_state", reconciliation_status.get("formal_state") == RECONCILIATION_STATE)
    add("reconciliation_status_decision", reconciliation_status.get("decision") == "SOURCE_ARCHIVE_GAP_STABLE")
    add("reconciliation_status_count", reconciliation_status.get("missing_reason_count") == 2)
    add("reconciliation_status_no_repair", reconciliation_status.get("silver_builder_repair_required") is False)
    add("reconciliation_status_no_repeat", reconciliation_status.get("repeat_execution_allowed") is False)

    add("exception_status_schema", exception_status.get("schema_version") == "historical-silver-2023-24-source-gap-exception-current-status-v1")
    add("exception_status_state", exception_status.get("formal_state") == VALID_STATE)
    add("exception_status_manifest", exception_status.get("manifest") == "data/research/historical-silver-2023-24-source-gap-exception-manifest-v1.json")
    add("exception_status_count", exception_status.get("exception_count") == 2 and exception_status.get("unclassified_count") == 0)
    add("exception_status_aggregate", exception_status.get("public_evidence_aggregate_only") is True)
    for key in (
        "game_ids_emitted", "dates_emitted", "team_codes_emitted", "row_level_records_emitted",
        "silver_builder_repair_required", "silver_builder_change_allowed", "silver_exception_patch_allowed",
        "gold_rebuild_allowed", "cross_source_audit_rerun_allowed", "model_training_allowed", "market_backtest_allowed",
    ):
        add(f"exception_status_{key}", exception_status.get(key) is False)
    add("exception_status_next", exception_status.get("next_research_step") == NEXT_STEP)
    add("exception_status_stake", exception_status.get("formal_stake") == 0)

    failed = sorted(name for name, ok in checks.items() if not ok)
    return {
        "schema_version": "historical-silver-2023-24-source-gap-exception-manifest-validation-report-v1",
        "validated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "formal_state": VALID_STATE if not failed else "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_MANIFEST_INVALID",
        "checks": checks,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "checks_failed": len(failed),
        "failed_checks": failed,
        "network_calls_made": False,
        "source_archives_read": False,
        "raw_rows_emitted": 0,
        "ready_for_data_execution": False,
        "ready_for_silver_builder_change": False,
        "ready_for_gold_rebuild": False,
        "ready_for_market_backtest": False,
        "next_research_step": NEXT_STEP,
        "formal_stake": 0,
    }


def self_test(manifest: dict[str, Any], result: dict[str, Any], reconciliation_status: dict[str, Any], exception_status: dict[str, Any]) -> dict[str, bool]:
    baseline = validate(manifest, result, reconciliation_status, exception_status)
    assert baseline["checks_failed"] == 0, baseline
    tests = {"baseline_passes": True}
    cases = {
        "count_change_blocks": ("manifest", ("aggregate_scope", "source_gap_exception_games"), 3),
        "identifier_output_blocks": ("manifest", ("public_evidence_policy", "game_ids_allowed"), True),
        "manual_patch_blocks": ("manifest", ("exception_handling_policy", "insert_manual_team_feature_rows"), True),
        "model_activation_blocks": ("manifest", ("downstream_eligibility", "model_training_eligible"), True),
        "nonzero_stake_blocks": ("status", ("formal_stake",), 1),
    }
    for name, (target, path, value) in cases.items():
        mutated_manifest = copy.deepcopy(manifest)
        mutated_status = copy.deepcopy(exception_status)
        obj = mutated_manifest if target == "manifest" else mutated_status
        cursor: dict[str, Any] = obj
        for key in path[:-1]:
            cursor = cursor[key]
        cursor[path[-1]] = value
        report = validate(mutated_manifest, result, reconciliation_status, mutated_status)
        assert report["checks_failed"] > 0, (name, report)
        tests[name] = True
    return tests


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--reconciliation-status", required=True, type=Path)
    parser.add_argument("--exception-status", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    manifest = read_json(args.manifest)
    result = read_json(args.result)
    reconciliation_status = read_json(args.reconciliation_status)
    exception_status = read_json(args.exception_status)
    report = validate(manifest, result, reconciliation_status, exception_status)
    if args.self_test:
        report["self_test"] = self_test(manifest, result, reconciliation_status, exception_status)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["checks_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
