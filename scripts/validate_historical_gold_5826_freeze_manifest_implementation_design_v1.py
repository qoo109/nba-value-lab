#!/usr/bin/env python3
"""Validate Historical Gold 5,826 freeze-manifest implementation design v1."""
from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DESIGN_STATE = "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_IMPLEMENTATION_DESIGN_VALIDATED"
STATUS_STATE = "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_IMPLEMENTATION_DESIGN_VALIDATED_READY_FOR_SYNTHETIC_VALIDATION"
POLICY_STATE = "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_POLICY_VALIDATED_READY_FOR_IMPLEMENTATION_DESIGN"
RECOVERY_STATE = "HISTORICAL_SILVER_2023_24_TWO_GAME_OFFICIAL_CDN_PBP_RECOVERY_PASS_ARTIFACT_ADOPTED"
NEXT = "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_IMPLEMENTATION_READY_FOR_SYNTHETIC_VALIDATION"
POLICY_ID = "HISTORICAL-GOLD-5826-COMPLETE-CORPUS-FREEZE-POLICY-2026-07-23-001"
DESIGN_ID = "HISTORICAL-GOLD-5826-COMPLETE-CORPUS-FREEZE-MANIFEST-IMPLEMENTATION-DESIGN-2026-07-23-001"
ARTIFACT_DIGEST = "sha256:3ed2d28da3af58b8b72d805860a144541ac5f38106653cfbda593e16bbaa8e8d"
GOLD_SHA = "sha256:a4e94fab1681b53817f305d08c196995d406fa0566ab70d6083aa5cebfc52085"


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def validate(
    design: dict[str, Any],
    status: dict[str, Any],
    policy_status: dict[str, Any],
    recovery_status: dict[str, Any],
) -> dict[str, Any]:
    checks: dict[str, bool] = {}

    def add(name: str, condition: Any) -> None:
        checks[name] = bool(condition)

    add("design_schema", design.get("schema_version") == "historical-gold-5826-complete-corpus-freeze-manifest-implementation-design-v1")
    add("design_id", design.get("design_id") == DESIGN_ID)
    add("design_state", design.get("formal_state") == DESIGN_STATE)
    add("design_role", design.get("design_role") == "DESIGN_ONLY_NO_REAL_ARTIFACT_READ_NO_CORPUS_FREEZE")

    binding = design.get("policy_binding", {})
    add("policy_id_binding", binding.get("policy_id") == POLICY_ID)
    add("policy_pr", binding.get("policy_recording_pr") == 135)
    add("policy_merge", binding.get("policy_recording_merge_commit") == "b6edf9b8acaf51b1287d6976c6e42cac056dc726")
    add("policy_validation_run", binding.get("policy_validation_run_id") == 29978555275)
    add("policy_validation_artifact", binding.get("policy_validation_artifact_id") == 8552326235)
    add("policy_validation_digest", binding.get("policy_validation_artifact_digest") == "sha256:96fdcee4b39f6ca03b9597677aa01db2e47b15d6d8f780f2e4525be978dd3722")

    governed = design.get("governed_input", {})
    add("artifact_id", governed.get("artifact_id") == 8551587005)
    add("artifact_digest", governed.get("artifact_digest") == ARTIFACT_DIGEST)
    add("artifact_expiry", governed.get("artifact_expires_at") == "2026-08-06T03:14:00Z")
    add("gold_filename", governed.get("gold_filename") == "historical-gold-multiseason-recovered-v1.sqlite.gz")
    add("gold_bytes", governed.get("gold_compressed_bytes") == 5268851)
    add("gold_sha", governed.get("gold_compressed_sha256") == GOLD_SHA)
    add("matchup_rows", governed.get("expected_matchup_rows") == 5826)
    add("team_rows", governed.get("expected_team_rows") == 11652)
    add("pit_zero", governed.get("expected_point_in_time_violations") == 0)
    add("exceptions_zero", governed.get("expected_remaining_source_exceptions") == 0)
    add("season_set", governed.get("expected_seasons") == ["2019-20", "2020-21", "2021-22", "2022-23", "2023-24"])

    module = design.get("future_module_contract", {})
    add("module_path", module.get("module_path") == "scripts/build_historical_gold_5826_complete_corpus_freeze_manifest_v1.py")
    add("workflow_path", module.get("workflow_path") == ".github/workflows/build-historical-gold-5826-complete-corpus-freeze-manifest-v1.yml")
    add("manifest_name", module.get("manifest_output_path") == "historical-gold-5826-complete-corpus-freeze-manifest-v1.json")
    add("cli_exact", module.get("cli") == ["--gold-sqlite", "--policy", "--output"])
    add("stdlib_only", module.get("python_standard_library_only") is True)
    add("readonly_mode", module.get("database_open_mode") == "SQLITE_URI_MODE_RO_IMMUTABLE_QUERY_ONLY")
    add("no_db_writes", module.get("database_write_operations_allowed") is False)
    add("no_network", module.get("network_access_in_module_allowed") is False)
    add("no_raw_materialization", module.get("raw_row_materialization_allowed") is False)
    add("no_row_hash_output", module.get("row_level_hash_output_allowed") is False)
    add("no_temp_export", module.get("temporary_row_export_allowed") is False)

    readonly = design.get("read_only_database_contract", {})
    add("uri_template", readonly.get("uri_template") == "file:{path}?mode=ro&immutable=1")
    add("uri_flag", readonly.get("uri_flag_required") is True)
    add("query_only", readonly.get("pragma_query_only_required") is True)
    add("integrity_check", readonly.get("pragma_integrity_check_required") is True)
    add("transaction_readonly", readonly.get("transaction_mode") == "READ_ONLY_NO_SCHEMA_OR_DATA_MUTATION")
    add("pre_post_sha", readonly.get("pre_and_post_database_sha256_must_match") is True)
    add("compressed_sha", readonly.get("input_compressed_sha256_must_match_policy") is True)
    add("compressed_size", readonly.get("input_compressed_size_must_match_policy") is True)
    add("required_tables", readonly.get("required_tables") == ["gold_team_game_features", "gold_matchup_features", "gold_metadata"])

    semantic = design.get("semantic_identity_algorithm", {})
    add("sha256", semantic.get("digest_algorithm") == "SHA256")
    add("jsonl", semantic.get("stream_format") == "CANONICAL_JSON_LINES_WITH_TYPE_TAGGED_VALUES")
    encoding = semantic.get("json_encoding", {})
    add("sorted_keys", encoding.get("sort_keys") is True)
    add("compact_separators", encoding.get("separators") == [",", ":"])
    add("unicode", encoding.get("ensure_ascii") is False)
    add("nan_blocked", encoding.get("allow_nan") is False)
    add("lf", encoding.get("line_terminator") == "LF")
    value_encoding = semantic.get("value_encoding", {})
    add("null_tagged", value_encoding.get("null", {}).get("type") == "null")
    add("integer_tagged", value_encoding.get("integer", {}).get("value_format") == "BASE10_STRING")
    add("real_hex", value_encoding.get("real", {}).get("value_format") == "PYTHON_FLOAT_HEX_FINITE_ONLY")
    add("text_utf8", value_encoding.get("text", {}).get("value_format") == "UTF8_JSON_STRING")
    add("blob_forbidden", value_encoding.get("blob", {}).get("type") == "forbidden")
    add("pragma_schema", semantic.get("schema_introspection") == "PRAGMA_TABLE_INFO")
    add("policy_columns", semantic.get("stable_columns_source") == "POLICY_ALL_SCHEMA_COLUMNS_MINUS_EXPLICIT_POLICY_VOLATILE_COLUMNS")
    add("no_extra_exclusions", semantic.get("additional_runtime_column_exclusions_allowed") is False)
    add("team_order_policy", semantic.get("team_sort_order_source") == "POLICY_TEAM_TABLE_SORT_ORDER")
    add("matchup_order_policy", semantic.get("matchup_sort_order_source") == "POLICY_MATCHUP_TABLE_SORT_ORDER")
    add("metadata_order", semantic.get("metadata_sort_order") == ["key"])
    add("metadata_exclusions_policy", semantic.get("metadata_exclusions_source") == "POLICY_EXPLICIT_VOLATILE_METADATA_KEYS")
    add("table_incremental", semantic.get("table_digest_method") == "INCREMENTAL_SHA256_OVER_CANONICAL_ROW_LINES")
    add("schema_digest", semantic.get("schema_digest_method") == "SHA256_OVER_CANONICAL_INCLUDED_COLUMN_DESCRIPTORS")
    add("metadata_incremental", semantic.get("metadata_digest_method") == "INCREMENTAL_SHA256_OVER_CANONICAL_STABLE_METADATA_LINES")
    add("corpus_components", semantic.get("corpus_digest_components_in_order") == [
        "manifest_schema_version", "policy_id", "team_schema_sha256", "team_table_sha256",
        "team_row_count", "matchup_schema_sha256", "matchup_table_sha256", "matchup_row_count",
        "metadata_sha256", "metadata_entry_count", "season_set", "point_in_time_validation_state"
    ])

    gates = design.get("fail_closed_validation_gates", {})
    expected_true = (
        "required_table_set_exact", "unique_team_game_keys_required", "unique_matchup_game_keys_required",
        "two_team_rows_per_matchup_required", "season_set_exact"
    )
    for key in expected_true:
        add(f"gate_{key}", gates.get(key) is True)
    expected_false = (
        "blank_or_null_game_dates_allowed", "blank_or_null_game_ids_allowed", "blank_or_null_team_codes_allowed",
        "non_finite_real_values_allowed", "blob_values_allowed", "schema_drift_allowed",
        "undeclared_volatile_column_allowed", "partial_manifest_allowed"
    )
    for key in expected_false:
        add(f"gate_{key}", gates.get(key) is False)
    add("gate_team_count", gates.get("team_rows_exactly") == 11652)
    add("gate_matchup_count", gates.get("matchup_rows_exactly") == 5826)
    add("gate_pit", gates.get("point_in_time_violations_exactly") == 0)

    output = design.get("aggregate_manifest_contract", {})
    allowed = set(output.get("allowed_output_categories", []))
    required_allowed = {
        "schema_and_policy_identifiers", "governed_artifact_bindings", "aggregate_table_row_counts",
        "included_and_excluded_column_counts", "schema_sha256_digests", "table_sha256_digests",
        "metadata_sha256_digest_and_entry_count", "corpus_sha256_digest", "season_labels",
        "aggregate_validation_booleans", "scientific_boundaries", "formal_stake"
    }
    add("allowed_output_exact", allowed == required_allowed)
    forbidden = set(output.get("forbidden_output_categories", []))
    add("forbidden_output_exact", forbidden == {
        "game_ids", "game_dates", "team_codes", "feature_ids", "raw_rows", "sample_rows",
        "row_level_hashes", "individual_feature_values", "player_information", "market_prices"
    })
    add("output_size", output.get("maximum_output_bytes") == 1048576)
    add("output_stake", output.get("formal_stake") == 0)

    synthetic = design.get("synthetic_validation_plan", {})
    add("synthetic_no_real_read", synthetic.get("real_artifact_read_allowed") is False)
    add("synthetic_sqlite", synthetic.get("synthetic_sqlite_required") is True)
    required_tests = {
        "stable_digest_repeats_identically", "row_insertion_order_does_not_change_digest",
        "volatile_feature_generated_at_change_does_not_change_digest",
        "policy_excluded_metadata_change_does_not_change_digest",
        "stable_feature_change_changes_table_and_corpus_digest",
        "stable_metadata_change_changes_metadata_and_corpus_digest", "missing_required_table_blocks",
        "unexpected_schema_column_blocks", "missing_stable_schema_column_blocks", "wrong_row_count_blocks",
        "duplicate_team_game_key_blocks", "orphan_or_incomplete_matchup_blocks", "wrong_season_set_blocks",
        "blank_date_blocks", "non_finite_real_blocks", "blob_value_blocks", "database_write_attempt_blocks",
        "database_sha_change_blocks", "forbidden_output_key_blocks", "output_size_limit_blocks"
    }
    add("synthetic_tests_exact", set(synthetic.get("required_tests", [])) == required_tests)

    boundaries = design.get("implementation_stage_boundaries", {})
    add("design_only", boundaries.get("design_only") is True)
    for key in (
        "future_module_created", "future_workflow_created", "real_artifact_downloaded", "real_gold_database_read",
        "semantic_manifest_created", "corpus_frozen", "market_backtest_executed",
        "model_training_or_retraining_executed", "injury_candidate_activated", "betting_edge_claim"
    ):
        add(f"boundary_{key}", boundaries.get(key) is False)
    add("boundary_stake", boundaries.get("formal_stake") == 0)
    add("design_next", design.get("next_research_step") == NEXT)
    add("design_ready_synthetic", design.get("ready_for_synthetic_implementation") is True)
    add("design_not_ready_real", design.get("ready_for_real_artifact_execution") is False)
    add("design_not_ready_market", design.get("ready_for_market_backtest") is False)
    add("design_not_ready_retrain", design.get("ready_for_model_retraining") is False)
    add("design_stake", design.get("formal_stake") == 0)

    add("status_schema", status.get("schema_version") == "historical-gold-5826-complete-corpus-freeze-manifest-implementation-current-status-v1")
    add("status_state", status.get("formal_state") == STATUS_STATE)
    add("status_design_id", status.get("design_id") == DESIGN_ID)
    implementation = status.get("implementation_state", {})
    add("status_design_validated", implementation.get("design_validated") is True)
    for key in (
        "implementation_module_created", "synthetic_sqlite_tests_executed", "real_artifact_execution_workflow_created",
        "real_artifact_execution_approved", "semantic_manifest_created", "corpus_frozen", "repeat_execution_allowed"
    ):
        add(f"status_{key}", implementation.get(key) is False)
    add("status_execution_zero", implementation.get("real_artifact_execution_count") == 0)
    add("status_next", status.get("next_research_step") == NEXT)
    add("status_ready_synthetic", status.get("ready_for_synthetic_implementation") is True)
    add("status_not_ready_real", status.get("ready_for_real_artifact_execution") is False)
    add("status_not_ready_market", status.get("ready_for_market_backtest") is False)
    add("status_not_ready_retrain", status.get("ready_for_model_retraining") is False)
    add("status_stake", status.get("formal_stake") == 0)

    add("policy_status_state", policy_status.get("formal_state") == POLICY_STATE)
    add("policy_status_id", policy_status.get("policy_id") == POLICY_ID)
    add("policy_status_gold", policy_status.get("governed_corpus", {}).get("gold_matchup_features") == 5826)
    add("policy_status_exceptions", policy_status.get("governed_corpus", {}).get("remaining_source_exceptions") == 0)
    add("policy_status_not_frozen", policy_status.get("freeze_state", {}).get("corpus_frozen") is False)
    add("policy_status_ready_design", policy_status.get("ready_for_freeze_manifest_implementation_design") is True)
    add("policy_status_stake", policy_status.get("formal_stake") == 0)

    add("recovery_state", recovery_status.get("formal_state") == RECOVERY_STATE)
    add("recovery_gold", recovery_status.get("adoption", {}).get("new_gold_matchup_reference_count") == 5826)
    add("recovery_exceptions", recovery_status.get("source_exception_state", {}).get("remaining_documented_exception_count") == 0)
    add("recovery_artifact", recovery_status.get("execution_evidence", {}).get("artifact_id") == 8551587005)
    add("recovery_digest", recovery_status.get("execution_evidence", {}).get("artifact_archive_digest") == ARTIFACT_DIGEST)
    add("recovery_gold_sha", recovery_status.get("artifact_files", {}).get("historical_gold", {}).get("sha256") == GOLD_SHA)
    add("recovery_stake", recovery_status.get("formal_stake") == 0)

    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": "historical-gold-5826-freeze-manifest-implementation-design-validation-report-v1",
        "validated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "formal_state": "HISTORICAL_GOLD_5826_FREEZE_MANIFEST_IMPLEMENTATION_DESIGN_VALID" if not failed else "HISTORICAL_GOLD_5826_FREEZE_MANIFEST_IMPLEMENTATION_DESIGN_INVALID",
        "checks": checks,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "checks_failed": len(failed),
        "failed_checks": failed,
        "gold_matchups": 5826 if not failed else None,
        "gold_team_rows": 11652 if not failed else None,
        "remaining_exceptions": 0 if not failed else None,
        "design_only": True,
        "ready_for_synthetic_implementation": not failed,
        "ready_for_real_artifact_execution": False,
        "ready_for_market_backtest": False,
        "ready_for_model_retraining": False,
        "formal_stake": 0,
    }


def self_test(design: dict[str, Any], status: dict[str, Any], policy: dict[str, Any], recovery: dict[str, Any]) -> dict[str, bool]:
    baseline = validate(design, status, policy, recovery)
    assert baseline["checks_failed"] == 0, baseline
    tests: dict[str, bool] = {"baseline_passes": True}
    mutations = {
        "wrong_design_state_blocks": ("design", ("formal_state",), "WRONG"),
        "wrong_gold_count_blocks": ("design", ("governed_input", "expected_matchup_rows"), 5824),
        "wrong_artifact_blocks": ("design", ("governed_input", "artifact_id"), 1),
        "write_permission_blocks": ("design", ("future_module_contract", "database_write_operations_allowed"), True),
        "network_permission_blocks": ("design", ("future_module_contract", "network_access_in_module_allowed"), True),
        "extra_exclusion_blocks": ("design", ("semantic_identity_algorithm", "additional_runtime_column_exclusions_allowed"), True),
        "blob_allowed_blocks": ("design", ("fail_closed_validation_gates", "blob_values_allowed"), True),
        "missing_synthetic_test_blocks": ("design", ("synthetic_validation_plan", "required_tests"), []),
        "real_execution_ready_blocks": ("design", ("ready_for_real_artifact_execution",), True),
        "status_executed_blocks": ("status", ("implementation_state", "real_artifact_execution_count"), 1),
        "status_frozen_blocks": ("status", ("implementation_state", "corpus_frozen"), True),
        "policy_not_ready_blocks": ("policy", ("ready_for_freeze_manifest_implementation_design",), False),
        "recovery_gap_blocks": ("recovery", ("source_exception_state", "remaining_documented_exception_count"), 2),
        "nonzero_stake_blocks": ("status", ("formal_stake",), 1),
    }
    for name, (target, path, replacement) in mutations.items():
        d = copy.deepcopy(design)
        s = copy.deepcopy(status)
        p = copy.deepcopy(policy)
        r = copy.deepcopy(recovery)
        obj = {"design": d, "status": s, "policy": p, "recovery": r}[target]
        cursor = obj
        for key in path[:-1]:
            cursor = cursor[key]
        cursor[path[-1]] = replacement
        report = validate(d, s, p, r)
        tests[name] = report["checks_failed"] > 0
        assert tests[name], (name, report)
    return tests


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--design", required=True, type=Path)
    parser.add_argument("--current-status", required=True, type=Path)
    parser.add_argument("--policy-status", required=True, type=Path)
    parser.add_argument("--recovery-status", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    design = read_json(args.design)
    status = read_json(args.current_status)
    policy = read_json(args.policy_status)
    recovery = read_json(args.recovery_status)
    report = validate(design, status, policy, recovery)
    if args.self_test:
        report["self_test"] = self_test(design, status, policy, recovery)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["checks_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
