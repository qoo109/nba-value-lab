#!/usr/bin/env python3
"""Validate the Eoin full adapter execution preflight policy.

This validator is aggregate-only. It reads policy JSON and an adapter self-test
report, but it does not download Kaggle data, inspect raw rows, build derived
tables, train models, calculate market metrics, or access secrets.
"""
from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "eoin-full-adapter-execution-preflight-validation-v1"
POLICY_SCHEMA = "eoin-full-adapter-execution-preflight-v1"
POLICY_STATE = "FULL_ADAPTER_PREFLIGHT_DECLARED_EXECUTION_DISABLED"
READY_STATE = "FULL_ADAPTER_EXECUTION_PREFLIGHT_READY_BUT_DISABLED"
BLOCKED_STATE = "FULL_ADAPTER_EXECUTION_PREFLIGHT_BLOCKED"
CROSS_SOURCE_SCHEMA = "eoin-cross-source-audit-result-v1"
CROSS_SOURCE_OUTCOME = "ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE"
PREDECLARATION_SCHEMA = "eoin-adapter-predeclaration-v1"
PREDECLARATION_STATE = "ADAPTER_PREDECLARED_EXECUTION_NOT_STARTED"
SELF_TEST_STATE = "ROLE_LIMITED_ADAPTER_SELF_TEST_PASS"

EXPECTED_ALLOWED_CHECKS = {
    "validate_cross_source_aggregate_report",
    "validate_adapter_predeclaration_policy",
    "validate_role_limited_adapter_self_test_report",
    "validate_full_execution_boundaries",
    "validate_public_artifact_allowlist",
    "validate_no_raw_row_or_raw_file_public_outputs",
}
EXPECTED_RUNTIME_INPUTS = {
    "Games.csv",
    "TeamStatistics.csv",
    "PlayerStatistics.csv",
    "PlayByPlay.parquet",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def check(condition: bool, name: str, failures: list[str]) -> None:
    if not condition:
        failures.append(name)


def validate(
    policy: dict[str, Any],
    cross_source: dict[str, Any],
    predeclaration: dict[str, Any],
    self_test_report: dict[str, Any],
) -> dict[str, Any]:
    failures: list[str] = []

    check(policy.get("schema_version") == POLICY_SCHEMA, "policy.schema_version", failures)
    check(policy.get("formal_state") == POLICY_STATE, "policy.formal_state", failures)
    check(policy.get("source_id") == "kaggle_eoinamoore_historical_nba", "policy.source_id", failures)
    check(policy.get("adapter_version") == "eoin-role-limited-secondary-adapter-v1", "policy.adapter_version", failures)
    check(policy.get("preflight_version") == POLICY_SCHEMA, "policy.preflight_version", failures)

    upstream = policy.get("upstream_requirements", {})
    check(upstream.get("cross_source_report") == "data/eoin-cross-source-audit-v1.json", "upstream.cross_source_report", failures)
    check(upstream.get("cross_source_required_outcome") == CROSS_SOURCE_OUTCOME, "upstream.cross_source_outcome", failures)
    check(upstream.get("adapter_predeclaration") == "data/eoin-adapter-predeclaration-v1.json", "upstream.predeclaration", failures)
    check(upstream.get("adapter_predeclaration_required_state") == PREDECLARATION_STATE, "upstream.predeclaration_state", failures)
    check(upstream.get("adapter_self_test_workflow") == ".github/workflows/validate-eoin-role-limited-adapter-v1.yml", "upstream.self_test_workflow", failures)
    check(upstream.get("adapter_self_test_required_state") == SELF_TEST_STATE, "upstream.self_test_state", failures)
    check(upstream.get("adapter_self_test_artifact_required_before_execution") is True, "upstream.self_test_artifact_required", failures)
    check(upstream.get("adapter_self_test_ci_conclusion_required") == "success", "upstream.ci_success_required", failures)

    check(cross_source.get("schema_version") == CROSS_SOURCE_SCHEMA, "cross_source.schema_version", failures)
    check(cross_source.get("formal_outcome") == CROSS_SOURCE_OUTCOME, "cross_source.formal_outcome", failures)
    check(cross_source.get("all_core_gates_passed") is True, "cross_source.all_core_gates_passed", failures)
    check(cross_source.get("deterministic_matching_only") is True, "cross_source.deterministic_only", failures)
    check(cross_source.get("fuzzy_matching") is False, "cross_source.no_fuzzy", failures)
    check(cross_source.get("existing_silver_replacement") is False, "cross_source.no_silver_replacement", failures)
    check(cross_source.get("existing_gold_replacement") is False, "cross_source.no_gold_replacement", failures)
    check(cross_source.get("formal_stake") == 0, "cross_source.formal_stake", failures)

    check(predeclaration.get("schema_version") == PREDECLARATION_SCHEMA, "predeclaration.schema_version", failures)
    check(predeclaration.get("formal_state") == PREDECLARATION_STATE, "predeclaration.formal_state", failures)
    permissions = predeclaration.get("post_decision_permissions", {})
    check(permissions.get("ready_for_adapter_implementation") is True, "predeclaration.implementation_ready", failures)
    check(permissions.get("ready_for_adapter_execution") is False, "predeclaration.execution_disabled", failures)
    check(permissions.get("ready_for_silver_replacement") is False, "predeclaration.no_silver_replacement", failures)
    check(permissions.get("ready_for_gold_replacement") is False, "predeclaration.no_gold_replacement", failures)
    check(permissions.get("ready_for_model_retraining") is False, "predeclaration.no_model_retraining", failures)
    check(permissions.get("ready_for_market_backtest") is False, "predeclaration.no_market_backtest", failures)
    check(permissions.get("ready_for_betting_edge_claim") is False, "predeclaration.no_betting_edge", failures)
    check(permissions.get("formal_stake") == 0, "predeclaration.stake_zero", failures)

    check(set(policy.get("allowed_preflight_checks", [])) == EXPECTED_ALLOWED_CHECKS, "policy.allowed_preflight_checks", failures)

    full = policy.get("full_execution_boundary", {})
    check(full.get("full_eoin_bundle_execution_enabled") is False, "boundary.full_execution_disabled", failures)
    check(full.get("full_eoin_bundle_execution_requires_separate_user_action") is True, "boundary.requires_user_action", failures)
    check(full.get("workflow_dispatch_only_when_later_enabled") is True, "boundary.workflow_dispatch_only", failures)
    check(full.get("requires_explicit_local_or_actions_dataset_path") is True, "boundary.requires_dataset_path", failures)
    check(full.get("requires_successful_preflight_report") is True, "boundary.requires_preflight_report", failures)
    check(full.get("requires_self_test_ci_run_id") is True, "boundary.requires_ci_run_id", failures)
    check(full.get("requires_self_test_artifact_id_or_digest") is True, "boundary.requires_artifact_digest", failures)
    check(full.get("requires_private_temporary_storage_only") is True, "boundary.private_temp_only", failures)
    check(full.get("read_only_source_access") is True, "boundary.read_only", failures)
    check(full.get("safe_extract_required") is True, "boundary.safe_extract", failures)
    check(full.get("deterministic_game_id_only") is True, "boundary.deterministic_game_id_only", failures)
    check(full.get("fuzzy_matching_allowed") is False, "boundary.no_fuzzy", failures)

    runtime_inputs = policy.get("allowed_runtime_inputs_when_later_enabled", {})
    check(set(runtime_inputs) == EXPECTED_RUNTIME_INPUTS | {"other_files"}, "runtime_inputs.keys", failures)
    for key in EXPECTED_RUNTIME_INPUTS:
        check(runtime_inputs.get(key) is True, f"runtime_inputs.{key}", failures)
    check(runtime_inputs.get("other_files") is False, "runtime_inputs.no_other_files", failures)

    public = policy.get("allowed_public_outputs_when_later_enabled", {})
    for key in ("aggregate_json_reports", "schema_metadata", "row_counts", "coverage_rates", "hashes_and_file_sizes"):
        check(public.get(key) is True, f"public_outputs.{key}", failures)
    for key in (
        "raw_game_rows",
        "raw_team_rows",
        "raw_player_rows",
        "raw_pbp_rows",
        "derived_game_id_lists",
        "full_csv_or_parquet_files",
        "full_sqlite_or_duckdb_files",
    ):
        check(public.get(key) is False, f"public_outputs.no_{key}", failures)

    forbidden = policy.get("forbidden_promotions", {})
    for key in (
        "historical_silver_replacement_allowed",
        "historical_gold_replacement_allowed",
        "player_stat_parity_claim_allowed",
        "player_stat_feature_import_allowed",
        "model_training_input_allowed",
        "model_retraining_allowed",
        "market_backtest_allowed",
        "clv_ev_roi_drawdown_allowed",
        "betting_decision_layer_allowed",
        "betting_edge_claim_allowed",
    ):
        check(forbidden.get(key) is False, f"forbidden.{key}", failures)
    check(forbidden.get("formal_stake") == 0, "forbidden.stake_zero", failures)

    check(self_test_report.get("formal_state") == SELF_TEST_STATE, "self_test.formal_state", failures)
    check(self_test_report.get("all_adapter_gates_passed") is True, "self_test.all_adapter_gates_passed", failures)
    check(self_test_report.get("fixture_only") is True, "self_test.fixture_only", failures)
    check(self_test_report.get("full_eoin_bundle_execution") is False, "self_test.full_execution_disabled", failures)
    check(self_test_report.get("deterministic_matching_only") is True, "self_test.deterministic_only", failures)
    check(self_test_report.get("fuzzy_matching") is False, "self_test.no_fuzzy", failures)
    self_boundaries = self_test_report.get("boundaries", {})
    check(self_boundaries.get("raw_eoin_rows_read") is False, "self_test.no_raw_rows_read", failures)
    check(self_boundaries.get("raw_rows_emitted") == 0, "self_test.no_raw_rows_emitted", failures)
    check(self_boundaries.get("raw_files_emitted") is False, "self_test.no_raw_files_emitted", failures)
    check(self_boundaries.get("existing_silver_replacement") is False, "self_test.no_silver_replacement", failures)
    check(self_boundaries.get("existing_gold_replacement") is False, "self_test.no_gold_replacement", failures)
    check(self_boundaries.get("model_retraining") is False, "self_test.no_model_retraining", failures)
    check(self_boundaries.get("market_metrics") is False, "self_test.no_market_metrics", failures)
    check(self_boundaries.get("betting_decision_layer") is False, "self_test.no_betting_layer", failures)
    check(self_boundaries.get("formal_stake") == 0, "self_test.stake_zero", failures)
    self_permissions = self_test_report.get("permissions", {})
    check(self_permissions.get("ready_for_full_adapter_execution") is False, "self_test.execution_still_disabled", failures)
    check(self_permissions.get("ready_for_silver_replacement") is False, "self_test.no_silver_permission", failures)
    check(self_permissions.get("ready_for_gold_replacement") is False, "self_test.no_gold_permission", failures)
    check(self_permissions.get("ready_for_model_retraining") is False, "self_test.no_model_permission", failures)
    check(self_permissions.get("ready_for_market_backtest") is False, "self_test.no_market_permission", failures)
    check(self_permissions.get("ready_for_betting_edge_claim") is False, "self_test.no_edge_permission", failures)
    check(self_permissions.get("formal_stake") == 0, "self_test.permission_stake_zero", failures)

    next_state = policy.get("next_state_if_preflight_passes", {})
    check(next_state.get("formal_state") == READY_STATE, "next_state.formal_state", failures)
    check(next_state.get("ready_for_full_adapter_execution_policy") is True, "next_state.execution_policy_ready", failures)
    for key in (
        "ready_for_full_adapter_execution",
        "ready_for_silver_replacement",
        "ready_for_gold_replacement",
        "ready_for_model_retraining",
        "ready_for_market_backtest",
        "ready_for_betting_edge_claim",
    ):
        check(next_state.get(key) is False, f"next_state.no_{key}", failures)
    check(next_state.get("formal_stake") == 0, "next_state.stake_zero", failures)

    check(policy.get("decision_states") == [
        POLICY_STATE,
        BLOCKED_STATE,
        READY_STATE,
    ], "decision_states", failures)

    passed = not failures
    return {
        "schema_version": VERSION,
        "validated_at": utc_now(),
        "formal_state": READY_STATE if passed else BLOCKED_STATE,
        "quality": {
            "checks_failed": len(failures),
            "failed_checks": failures,
            "network_calls_made": False,
            "raw_rows_read": False,
            "raw_rows_emitted": 0,
            "raw_files_emitted": False,
            "model_metrics_calculated": False,
            "market_metrics_calculated": False,
            "formal_stake": 0,
        },
        "decision": {
            "ready_for_full_adapter_execution_policy": passed,
            "ready_for_full_adapter_execution": False,
            "ready_for_silver_replacement": False,
            "ready_for_gold_replacement": False,
            "ready_for_model_retraining": False,
            "ready_for_market_backtest": False,
            "ready_for_betting_edge_claim": False,
            "formal_stake": 0,
        },
    }


def self_test(
    policy: dict[str, Any],
    cross_source: dict[str, Any],
    predeclaration: dict[str, Any],
    self_test_report: dict[str, Any],
) -> None:
    base = validate(policy, cross_source, predeclaration, self_test_report)
    assert base["formal_state"] == READY_STATE, base

    mutated = copy.deepcopy(policy)
    mutated["full_execution_boundary"]["full_eoin_bundle_execution_enabled"] = True
    blocked = validate(mutated, cross_source, predeclaration, self_test_report)
    assert blocked["formal_state"] == BLOCKED_STATE, blocked
    assert "boundary.full_execution_disabled" in blocked["quality"]["failed_checks"], blocked

    mutated = copy.deepcopy(policy)
    mutated["forbidden_promotions"]["market_backtest_allowed"] = True
    blocked = validate(mutated, cross_source, predeclaration, self_test_report)
    assert blocked["formal_state"] == BLOCKED_STATE, blocked
    assert "forbidden.market_backtest_allowed" in blocked["quality"]["failed_checks"], blocked

    mutated_report = copy.deepcopy(self_test_report)
    mutated_report["boundaries"]["raw_rows_emitted"] = 1
    blocked = validate(policy, cross_source, predeclaration, mutated_report)
    assert blocked["formal_state"] == BLOCKED_STATE, blocked
    assert "self_test.no_raw_rows_emitted" in blocked["quality"]["failed_checks"], blocked


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, default=Path("data/eoin-full-adapter-preflight-v1.json"))
    parser.add_argument("--cross-source", type=Path, default=Path("data/eoin-cross-source-audit-v1.json"))
    parser.add_argument("--predeclaration", type=Path, default=Path("data/eoin-adapter-predeclaration-v1.json"))
    parser.add_argument("--adapter-self-test-report", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    policy = read_json(args.policy)
    cross_source = read_json(args.cross_source)
    predeclaration = read_json(args.predeclaration)
    self_test_report = read_json(args.adapter_self_test_report)

    if args.self_test:
        self_test(policy, cross_source, predeclaration, self_test_report)
        print("eoin full adapter preflight validator self-test passed")
        return 0

    report = validate(policy, cross_source, predeclaration, self_test_report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
