#!/usr/bin/env python3
"""Validate Historical Gold 5,826 complete-corpus freeze policy v1."""
from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

POLICY_ID = "HISTORICAL-GOLD-5826-COMPLETE-CORPUS-FREEZE-POLICY-2026-07-23-001"
POLICY_STATE = "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_POLICY_DESIGN_VALIDATED"
STATUS_STATE = "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_POLICY_VALIDATED_READY_FOR_IMPLEMENTATION_DESIGN"
RECOVERY_STATE = "HISTORICAL_SILVER_2023_24_TWO_GAME_OFFICIAL_CDN_PBP_RECOVERY_PASS_ARTIFACT_ADOPTED"
NEXT = "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_IMPLEMENTATION_READY_FOR_DESIGN"
BASE_COMMIT = "f19282040fb8e45326133c9b77afc1ff45c13bb4"
RECOVERY_RESULT_SHA = "sha256:97d292d56f6ee8b6f0a2d4e4471990f7c953cca7c324eb64c129066695df7c30"
SOURCE_SHA = "sha256:33d49fefc809f73d5d6cbad6d1d6690e0df6c89fe2b5a4d814ecc9ea4df6101b"
ARTIFACT_DIGEST = "sha256:3ed2d28da3af58b8b72d805860a144541ac5f38106653cfbda593e16bbaa8e8d"
SILVER_SHA = "sha256:48c032339402d5f75e43d7aaf8e977784aee9eceff74c9e7da952af8e1680eb8"
GOLD_SHA = "sha256:a4e94fab1681b53817f305d08c196995d406fa0566ab70d6083aa5cebfc52085"
SEASONS = ["2019-20", "2020-21", "2021-22", "2022-23", "2023-24"]


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def validate(policy: dict[str, Any], status: dict[str, Any], recovery: dict[str, Any]) -> dict[str, Any]:
    checks: dict[str, bool] = {}

    def add(name: str, condition: Any) -> None:
        checks[name] = bool(condition)

    add("policy_schema", policy.get("schema_version") == "historical-gold-5826-complete-corpus-freeze-policy-v1")
    add("policy_id", policy.get("policy_id") == POLICY_ID)
    add("policy_state", policy.get("formal_state") == POLICY_STATE)
    add("policy_design_only", policy.get("policy_role") == "DESIGN_ONLY_NO_CORPUS_FREEZE_EXECUTION")

    scope = policy.get("governed_scope", {})
    add("scope_seasons", scope.get("seasons") == SEASONS)
    add("scope_silver_games", scope.get("silver_games") == 5826)
    add("scope_silver_team", scope.get("silver_team_game_features") == 11652)
    add("scope_gold_matchups", scope.get("gold_matchup_features") == 5826)
    add("scope_gold_team", scope.get("gold_team_game_features") == 11652)
    add("scope_no_gap", scope.get("missing_gold_for_silver") == 0)
    add("scope_no_exceptions", scope.get("documented_source_exceptions_remaining") == 0)
    add("scope_pit_zero", scope.get("gold_point_in_time_violations") == 0)
    add("scope_pit_pass", scope.get("gold_point_in_time_passed") is True)
    add("scope_complete", scope.get("corpus_complete_for_governed_scope") is True)
    add("scope_no_exclusions", scope.get("row_exclusions_allowed") is False)
    add("scope_no_partial", scope.get("partial_freeze_allowed") is False)

    bindings = policy.get("immutable_evidence_bindings", {})
    add("base_commit", bindings.get("policy_base_commit") == BASE_COMMIT)
    add("recovery_pr", bindings.get("recovery_recording_pr") == 133)
    add("recovery_merge", bindings.get("recovery_recording_merge_commit") == "98bcb2538070eb57bba2ce79920262262c0924ef")
    add("recovery_result_sha", bindings.get("recovery_result_sha256") == RECOVERY_RESULT_SHA)
    add("source_sha", bindings.get("source_archive_sha256") == SOURCE_SHA)
    add("source_bytes", bindings.get("source_archive_bytes") == 18598380)
    add("artifact_id", bindings.get("adopted_artifact_id") == 8551587005)
    add("artifact_digest", bindings.get("adopted_artifact_digest") == ARTIFACT_DIGEST)
    add("artifact_expiry", bindings.get("adopted_artifact_expires_at") == "2026-08-06T03:14:00Z")
    add("silver_sha", bindings.get("historical_silver_sha256") == SILVER_SHA)
    add("silver_bytes", bindings.get("historical_silver_bytes") == 369318173)
    add("gold_sha", bindings.get("historical_gold_sha256") == GOLD_SHA)
    add("gold_bytes", bindings.get("historical_gold_bytes") == 5268851)

    identity = policy.get("freeze_identity_design", {})
    add("binary_not_semantic_identity", identity.get("binary_artifact_hash_role") == "EXECUTION_INPUT_EVIDENCE_NOT_LONG_TERM_SEMANTIC_IDENTITY")
    add("volatile_reason", "feature_generated_at" in str(identity.get("reason_binary_hash_is_not_sufficient_alone", "")))
    add("manifest_type", identity.get("required_manifest_type") == "AGGREGATE_SEMANTIC_CORPUS_MANIFEST")
    add("required_tables", identity.get("required_tables") == ["gold_team_game_features", "gold_matchup_features", "gold_metadata"])
    add("team_rows", identity.get("team_table_expected_rows") == 11652)
    add("matchup_rows", identity.get("matchup_table_expected_rows") == 5826)
    add("team_sort", identity.get("team_table_sort_order") == ["season_label", "game_date", "game_id", "team_abbr"])
    add("matchup_sort", identity.get("matchup_table_sort_order") == ["game_date", "game_id"])
    add("only_generated_at_volatile", identity.get("volatile_columns_excluded_from_semantic_digest") == ["feature_generated_at"])
    add("only_metadata_generated_at_volatile", identity.get("volatile_metadata_keys_excluded_from_semantic_digest") == ["feature_generated_at"])
    add("required_metadata", identity.get("required_metadata_keys") == [
        "pipeline_name", "schema_version", "feature_version", "source_version",
        "point_in_time_rule", "same_day_games_policy", "season_history_policy", "season_labels"
    ])
    add("sha256_tables", identity.get("table_digest_algorithm") == "SHA256")
    add("sha256_metadata", identity.get("metadata_digest_algorithm") == "SHA256")
    add("sha256_corpus", identity.get("corpus_digest_algorithm") == "SHA256_OF_CANONICAL_AGGREGATE_MANIFEST")
    add("nonfinite_blocked", identity.get("nonfinite_numeric_values_allowed") is False)
    add("duplicates_blocked", identity.get("duplicate_primary_keys_allowed") is False)
    for key in ("row_level_values_emitted_in_public_manifest", "game_ids_emitted_in_public_manifest", "dates_emitted_in_public_manifest", "team_codes_emitted_in_public_manifest"):
        add(f"privacy_{key}", identity.get(key) is False)

    required_fields = policy.get("freeze_manifest_required_fields", {})
    add("all_manifest_fields_required", bool(required_fields) and all(value is True for value in required_fields.values()))

    access = policy.get("implementation_access_policy", {})
    add("preferred_exact_artifact", access.get("preferred_input_path") == "DOWNLOAD_ADOPTED_ARTIFACT_BEFORE_EXPIRY")
    add("artifact_download_allowed", access.get("artifact_download_allowed") is True)
    add("network_exact_only", access.get("network_access_allowed_only_for_exact_github_artifact") is True)
    add("other_network_blocked", access.get("other_network_access_allowed") is False)
    add("raw_archive_download_blocked", access.get("raw_source_archive_download_allowed") is False)
    add("db_read_only", access.get("database_read_allowed") is True and access.get("database_write_allowed") is False and access.get("database_mutation_allowed") is False)
    add("repo_db_commit_blocked", access.get("repository_database_commit_allowed") is False)
    add("raw_upload_blocked", access.get("raw_row_artifact_upload_allowed") is False)
    add("manifest_size", access.get("aggregate_manifest_max_bytes") == 1048576)
    add("workflow_dispatch_only", access.get("workflow_dispatch_only_for_real_artifact_execution") is True)
    add("no_auto_execution", access.get("automatic_real_artifact_execution_allowed") is False)
    add("one_execution", access.get("maximum_real_artifact_execution_count") == 1)
    add("no_repeat", access.get("repeat_execution_allowed") is False)
    add("expiry_fail_closed", access.get("artifact_expiry_fallback") == "BLOCK_AND_REQUIRE_NEW_GOVERNED_REBUILD_WITH_COMPLETE_SOURCE_HASH_MANIFEST")
    add("unbound_rebuild_blocked", access.get("unbound_rebuild_after_expiry_allowed") is False)

    invalidation = policy.get("freeze_invalidation_rules", {})
    add("invalidation_complete", all(key in invalidation for key in (
        "gold_binary_sha256_change", "gold_schema_version_change", "gold_feature_version_change",
        "source_version_change", "season_scope_change", "row_count_change",
        "semantic_table_digest_change", "point_in_time_violation_above_zero",
        "duplicate_primary_key_above_zero", "missing_required_metadata",
        "unexplained_missing_game_above_zero"
    )))
    add("pit_blocks", invalidation.get("point_in_time_violation_above_zero") == "FREEZE_BLOCKED")
    add("duplicate_blocks", invalidation.get("duplicate_primary_key_above_zero") == "FREEZE_BLOCKED")

    dependencies = policy.get("downstream_data_dependency_ledger", {})
    odds = dependencies.get("timestamped_bookmaker_odds", {})
    injury = dependencies.get("historical_multi_snapshot_injury_panel", {})
    ledger = dependencies.get("team_submission_completeness_ledger", {})
    add("gold_complete_dependency", dependencies.get("historical_silver_gold_corpus", {}).get("state") == "COMPLETE_FOR_GOVERNED_FIVE_SEASON_SCOPE")
    add("odds_missing", odds.get("state") == "MISSING_REAL_LEGAL_AUDITABLE_OBSERVED_AT_DATA")
    add("odds_blocks_market", odds.get("blocks_market_backtest") is True)
    add("odds_not_freeze_blocker", odds.get("blocks_freeze_policy") is False)
    add("injury_pilot_state", injury.get("state") == "PILOT_ONLY_BELOW_100_INDEPENDENT_GAME_ACTIVATION_GATE")
    add("injury_41", injury.get("independent_games_available") == 41)
    add("injury_31", injury.get("primary_t60_selected_games") == 31)
    add("injury_blocks_activation", injury.get("blocks_injury_model_activation") is True)
    add("injury_not_freeze_blocker", injury.get("blocks_freeze_policy") is False)
    add("submission_ledger_required", ledger.get("state") == "REQUIRED_BEFORE_FORMAL_INJURY_HOLDOUT")
    add("submission_blocks_holdout", ledger.get("blocks_formal_injury_holdout") is True)

    prohibited = policy.get("prohibited_interpretations", {})
    add("all_interpretations_false", bool(prohibited) and all(value is False for value in prohibited.values()))

    decision = policy.get("decision", {})
    add("policy_valid", decision.get("policy_design_valid") is True)
    add("not_frozen", decision.get("corpus_freeze_executed") is False)
    add("no_manifest_yet", decision.get("semantic_freeze_manifest_created") is False)
    add("ready_implementation_design", decision.get("ready_for_freeze_manifest_implementation_design") is True)
    add("not_ready_execution", decision.get("ready_for_real_artifact_freeze_execution") is False)
    add("not_ready_market", decision.get("ready_for_market_backtest") is False)
    add("not_ready_retrain", decision.get("ready_for_model_retraining") is False)
    add("next_step", decision.get("next_research_step") == NEXT)
    add("policy_stake_zero", decision.get("formal_stake") == 0)

    add("status_schema", status.get("schema_version") == "historical-gold-5826-complete-corpus-freeze-policy-current-status-v1")
    add("status_state", status.get("formal_state") == STATUS_STATE)
    add("status_policy_id", status.get("policy_id") == POLICY_ID)
    add("status_next", status.get("next_research_step") == NEXT)
    status_scope = status.get("governed_corpus", {})
    add("status_counts", status_scope.get("silver_games") == 5826 and status_scope.get("gold_matchup_features") == 5826 and status_scope.get("remaining_source_exceptions") == 0)
    add("status_pit", status_scope.get("point_in_time_violations") == 0 and status_scope.get("complete_for_governed_scope") is True)
    freeze_state = status.get("freeze_state", {})
    add("status_policy_valid", freeze_state.get("policy_design_validated") is True)
    add("status_not_implemented", freeze_state.get("implementation_created") is False)
    add("status_not_frozen", freeze_state.get("corpus_frozen") is False)
    add("status_zero_execution", freeze_state.get("real_artifact_execution_count") == 0)
    add("status_no_repeat", freeze_state.get("repeat_execution_allowed") is False)
    status_boundaries = status.get("boundaries", {})
    for key in ("corpus_freeze_executed", "database_downloaded_or_read_in_policy_stage", "database_modified", "raw_rows_emitted", "game_ids_emitted", "dates_emitted", "team_codes_emitted", "market_backtest_executed", "model_training_or_retraining_executed", "injury_candidate_activated", "betting_edge_claim"):
        add(f"status_boundary_{key}", status_boundaries.get(key) is False)
    add("status_stake_zero", status.get("formal_stake") == 0 and status_boundaries.get("formal_stake") == 0)
    add("status_market_blocked", status.get("ready_for_market_backtest") is False)
    add("status_retrain_blocked", status.get("ready_for_model_retraining") is False)

    add("recovery_state", recovery.get("formal_state") == RECOVERY_STATE)
    recovery_scope = recovery.get("adoption", {})
    add("recovery_5826", recovery_scope.get("new_gold_matchup_reference_count") == 5826)
    add("recovery_complete", recovery_scope.get("gold_complete_for_governed_five_season_scope") is True)
    add("recovery_zero_exceptions", recovery.get("source_exception_state", {}).get("remaining_documented_exception_count") == 0)
    add("recovery_artifact", recovery.get("execution_evidence", {}).get("artifact_id") == 8551587005)
    add("recovery_artifact_digest", recovery.get("execution_evidence", {}).get("artifact_archive_digest") == ARTIFACT_DIGEST)
    add("recovery_gold_sha", recovery.get("artifact_files", {}).get("historical_gold", {}).get("sha256") == GOLD_SHA)
    add("recovery_pit", recovery.get("artifact_files", {}).get("historical_gold", {}).get("point_in_time_violations") == 0)
    add("recovery_market_blocked", recovery.get("ready_for_market_backtest") is False)
    add("recovery_retrain_blocked", recovery.get("ready_for_model_retraining") is False)
    add("recovery_stake_zero", recovery.get("formal_stake") == 0)

    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": "historical-gold-5826-complete-corpus-freeze-policy-validation-report-v1",
        "validated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "formal_state": "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_POLICY_VALID" if not failed else "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_POLICY_INVALID",
        "policy_id": POLICY_ID,
        "checks": checks,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "checks_failed": len(failed),
        "failed_checks": failed,
        "silver_games": 5826 if not failed else None,
        "gold_matchups": 5826 if not failed else None,
        "remaining_exceptions": 0 if not failed else None,
        "corpus_freeze_executed": False,
        "ready_for_freeze_manifest_implementation_design": not failed,
        "ready_for_real_artifact_freeze_execution": False,
        "ready_for_market_backtest": False,
        "ready_for_model_retraining": False,
        "formal_stake": 0,
    }


def self_test(policy: dict[str, Any], status: dict[str, Any], recovery: dict[str, Any]) -> dict[str, bool]:
    baseline = validate(policy, status, recovery)
    assert baseline["checks_failed"] == 0, baseline
    mutations: dict[str, tuple[str, tuple[str, ...], Any]] = {
        "wrong_gold_count_blocks": ("policy", ("governed_scope", "gold_matchup_features"), 5824),
        "remaining_gap_blocks": ("policy", ("governed_scope", "missing_gold_for_silver"), 2),
        "remaining_exception_blocks": ("policy", ("governed_scope", "documented_source_exceptions_remaining"), 2),
        "wrong_gold_hash_blocks": ("policy", ("immutable_evidence_bindings", "historical_gold_sha256"), "sha256:wrong"),
        "partial_freeze_blocks": ("policy", ("governed_scope", "partial_freeze_allowed"), True),
        "extra_volatile_column_blocks": ("policy", ("freeze_identity_design", "volatile_columns_excluded_from_semantic_digest"), ["feature_generated_at", "quality_flags"]),
        "row_ids_public_blocks": ("policy", ("freeze_identity_design", "game_ids_emitted_in_public_manifest"), True),
        "automatic_execution_blocks": ("policy", ("implementation_access_policy", "automatic_real_artifact_execution_allowed"), True),
        "repeat_execution_blocks": ("policy", ("implementation_access_policy", "repeat_execution_allowed"), True),
        "unbound_rebuild_blocks": ("policy", ("implementation_access_policy", "unbound_rebuild_after_expiry_allowed"), True),
        "odds_false_ready_blocks": ("policy", ("downstream_data_dependency_ledger", "timestamped_bookmaker_odds", "state"), "COMPLETE"),
        "injury_false_ready_blocks": ("policy", ("downstream_data_dependency_ledger", "historical_multi_snapshot_injury_panel", "state"), "READY"),
        "market_ready_blocks": ("policy", ("decision", "ready_for_market_backtest"), True),
        "nonzero_stake_blocks": ("policy", ("decision", "formal_stake"), 1),
        "status_frozen_blocks": ("status", ("freeze_state", "corpus_frozen"), True),
        "recovery_drift_blocks": ("recovery", ("adoption", "new_gold_matchup_reference_count"), 5824),
    }
    results: dict[str, bool] = {"baseline_passes": True}
    for name, (target, path, replacement) in mutations.items():
        p, s, r = copy.deepcopy(policy), copy.deepcopy(status), copy.deepcopy(recovery)
        root = {"policy": p, "status": s, "recovery": r}[target]
        cursor = root
        for key in path[:-1]:
            cursor = cursor[key]
        cursor[path[-1]] = replacement
        report = validate(p, s, r)
        results[name] = report["checks_failed"] > 0
        assert results[name], (name, report)
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--current-status", type=Path, required=True)
    parser.add_argument("--recovery-status", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    policy = read_json(args.policy)
    status = read_json(args.current_status)
    recovery = read_json(args.recovery_status)
    report = validate(policy, status, recovery)
    if args.self_test:
        report["self_test"] = self_test(policy, status, recovery)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["checks_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
