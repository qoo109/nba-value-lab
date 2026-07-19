#!/usr/bin/env python3
"""Validate the Eoin role-limited secondary adapter predeclaration.

The validator is policy-only: it does not download Kaggle data, inspect raw rows,
build derived tables, train models, calculate market metrics, or access secrets.
"""
from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "eoin-adapter-predeclaration-validation-v1"
POLICY_SCHEMA = "eoin-adapter-predeclaration-v1"
EVIDENCE_SCHEMA = "eoin-cross-source-audit-result-v1"
READY_STATE = "ROLE_LIMITED_ADAPTER_READY_FOR_IMPLEMENTATION"
BLOCKED_STATE = "ADAPTER_EXECUTION_BLOCKED"

EXPECTED_INPUTS = {
    "Games.csv",
    "TeamStatistics.csv",
    "PlayerStatistics.csv",
    "PlayByPlay.parquet",
}
EXPECTED_DOMAINS = {
    "game_identity_crosscheck",
    "final_score_crosscheck",
    "team_boxscore_score_crosscheck",
    "player_boxscore_candidate_coverage",
    "play_by_play_game_coverage",
    "aggregate_source_health",
}
FORBIDDEN_PUBLIC_OUTPUTS = {
    "small_derived_game_id_lists",
    "raw_game_rows",
    "raw_team_rows",
    "raw_player_rows",
    "raw_pbp_rows",
    "full_csv_or_parquet_files",
    "full_sqlite_or_duckdb_files",
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


def validate(policy: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []

    check(policy.get("schema_version") == POLICY_SCHEMA, "policy.schema_version", failures)
    check(policy.get("formal_state") == "ADAPTER_PREDECLARED_EXECUTION_NOT_STARTED", "policy.formal_state", failures)
    check(policy.get("source_id") == "kaggle_eoinamoore_historical_nba", "policy.source_id", failures)
    check(policy.get("adapter_version") == "eoin-role-limited-secondary-adapter-v1", "policy.adapter_version", failures)

    pre = policy.get("predeclaration", {})
    for key in (
        "policy_committed_after_cross_source_audit",
        "policy_committed_before_adapter_execution",
        "policy_committed_before_derived_data_import",
        "policy_committed_before_model_retraining",
    ):
        check(pre.get(key) is True, f"predeclaration.{key}", failures)
    for key in (
        "post_result_scope_or_gate_edits_allowed",
        "raw_source_commit_allowed",
        "raw_source_artifact_allowed",
    ):
        check(pre.get(key) is False, f"predeclaration.{key}", failures)

    upstream = policy.get("upstream_evidence", {})
    check(upstream.get("required_report") == "data/eoin-cross-source-audit-v1.json", "upstream.report", failures)
    check(upstream.get("required_schema_version") == EVIDENCE_SCHEMA, "upstream.schema_requirement", failures)
    check(upstream.get("required_formal_outcome") == "ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE", "upstream.outcome_requirement", failures)
    check(upstream.get("required_all_core_gates_passed") is True, "upstream.gates_requirement", failures)
    check(upstream.get("required_deterministic_matching_only") is True, "upstream.deterministic_requirement", failures)
    check(upstream.get("required_existing_silver_replacement") is False, "upstream.no_silver_replacement_requirement", failures)
    check(upstream.get("required_existing_gold_replacement") is False, "upstream.no_gold_replacement_requirement", failures)
    check(upstream.get("required_formal_stake") == 0, "upstream.stake_requirement", failures)

    check(evidence.get("schema_version") == upstream.get("required_schema_version"), "evidence.schema_version", failures)
    check(evidence.get("formal_outcome") == upstream.get("required_formal_outcome"), "evidence.formal_outcome", failures)
    check(evidence.get("all_core_gates_passed") is True, "evidence.all_core_gates_passed", failures)
    check(evidence.get("deterministic_matching_only") is True, "evidence.deterministic_only", failures)
    check(evidence.get("fuzzy_matching") is False, "evidence.no_fuzzy", failures)
    check(evidence.get("existing_silver_replacement") is False, "evidence.no_silver_replacement", failures)
    check(evidence.get("existing_gold_replacement") is False, "evidence.no_gold_replacement", failures)
    check(evidence.get("formal_stake") == 0, "evidence.formal_stake", failures)

    comparison = evidence.get("comparison", {})
    gates = policy.get("frozen_gates", {})
    check(comparison.get("reference_games", 0) >= gates.get("minimum_reference_games", 10**9), "gate.reference_games", failures)
    check(comparison.get("game_identity_match_rate", 0) >= gates.get("minimum_game_identity_match_rate", 1), "gate.game_identity", failures)
    check(comparison.get("final_score_match_rate", 0) >= gates.get("minimum_final_score_match_rate", 1), "gate.final_score", failures)
    check(comparison.get("team_boxscore_coverage_rate", 0) >= gates.get("minimum_team_boxscore_coverage", 1), "gate.team_coverage", failures)
    check(comparison.get("player_boxscore_candidate_coverage_rate", 0) >= gates.get("minimum_player_boxscore_candidate_coverage", 1), "gate.player_candidate_coverage", failures)
    check(comparison.get("pbp_game_coverage_rate", 0) >= gates.get("minimum_pbp_game_coverage_when_claimed", 1), "gate.pbp_coverage", failures)
    eoin_games = evidence.get("eoin_observed", {}).get("games", {})
    check(eoin_games.get("duplicate_game_id_groups") == gates.get("maximum_duplicate_eoin_game_id_groups"), "gate.duplicate_games", failures)
    check(gates.get("maximum_fuzzy_matches") == 0, "gate.no_fuzzy_matches", failures)
    check(gates.get("maximum_raw_rows_emitted") == 0, "gate.no_raw_rows", failures)

    contract = policy.get("required_input_contract", {})
    check(set(policy.get("allowed_input_files", [])) == EXPECTED_INPUTS, "inputs.expected_files", failures)
    check(contract.get("game_id_column") == "gameId", "contract.game_id_column", failures)
    check(contract.get("matching") == "deterministic_game_id_only", "contract.matching", failures)
    check(contract.get("fuzzy_matching") is False, "contract.no_fuzzy", failures)
    check(contract.get("pilot_season") == "2023-24", "contract.pilot_season", failures)
    check(contract.get("temporary_raw_files_only") is True, "contract.temp_only", failures)
    check(contract.get("read_only_source_access") is True, "contract.read_only", failures)

    check(set(policy.get("allowed_output_domains", [])) == EXPECTED_DOMAINS, "outputs.domains", failures)
    public = policy.get("allowed_public_outputs", {})
    for key in ("aggregate_json_reports", "schema_metadata", "row_counts", "coverage_rates", "hashes_and_file_sizes"):
        check(public.get(key) is True, f"public_outputs.{key}", failures)
    for key in FORBIDDEN_PUBLIC_OUTPUTS:
        check(public.get(key) is False, f"public_outputs.no_{key}", failures)

    outputs = policy.get("adapter_outputs_v1", {})
    check(outputs.get("aggregate_report") == "eoin-role-limited-secondary-adapter-v1-report.json", "adapter_outputs.report", failures)
    check(outputs.get("run_status") == "eoin-role-limited-secondary-adapter-v1-status.json", "adapter_outputs.status", failures)
    check(outputs.get("derived_tables_publicly_committed") == [], "adapter_outputs.no_public_tables", failures)
    check(outputs.get("raw_rows_emitted") == 0, "adapter_outputs.no_raw_rows", failures)

    role = policy.get("role_limits", {})
    check(role.get("secondary_source_only") is True, "role.secondary_only", failures)
    for key in (
        "historical_silver_replacement_allowed",
        "historical_gold_replacement_allowed",
        "model_training_input_allowed",
        "model_retraining_allowed",
        "market_backtest_allowed",
        "betting_decision_layer_allowed",
    ):
        check(role.get(key) is False, f"role.no_{key}", failures)
    check(role.get("formal_stake") == 0, "role.stake_zero", failures)

    player = policy.get("player_boxscore_boundary", {})
    check(player.get("coverage_only_in_v1") is True, "player.coverage_only", failures)
    check(player.get("player_stat_parity_approved") is False, "player.no_stat_parity", failures)
    check(player.get("independent_player_boxscore_reference_required_before_stats") is True, "player.requires_reference", failures)
    check(player.get("player_stat_feature_import_allowed") is False, "player.no_feature_import", failures)

    check(policy.get("decision_states") == [
        "ADAPTER_PREDECLARED_EXECUTION_NOT_STARTED",
        "ADAPTER_EXECUTION_BLOCKED",
        "ROLE_LIMITED_ADAPTER_READY_FOR_IMPLEMENTATION",
        "ROLE_LIMITED_ADAPTER_VALIDATED",
    ], "decision_states", failures)

    permissions = policy.get("post_decision_permissions", {})
    check(permissions.get("ready_for_adapter_implementation") is True, "permissions.implementation_ready", failures)
    for key in (
        "ready_for_adapter_execution",
        "ready_for_silver_replacement",
        "ready_for_gold_replacement",
        "ready_for_model_retraining",
        "ready_for_market_backtest",
        "ready_for_betting_edge_claim",
    ):
        check(permissions.get(key) is False, f"permissions.no_{key}", failures)
    check(permissions.get("formal_stake") == 0, "permissions.stake_zero", failures)

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
            "model_metrics_calculated": False,
            "market_metrics_calculated": False,
            "formal_stake": 0
        },
        "decision": {
            "ready_for_adapter_implementation": passed,
            "ready_for_adapter_execution": False,
            "ready_for_silver_replacement": False,
            "ready_for_gold_replacement": False,
            "ready_for_model_retraining": False,
            "ready_for_market_backtest": False,
            "ready_for_betting_edge_claim": False,
            "formal_stake": 0
        }
    }


def self_test(policy: dict[str, Any], evidence: dict[str, Any]) -> None:
    base = validate(policy, evidence)
    assert base["formal_state"] == READY_STATE, base

    mutated = copy.deepcopy(policy)
    mutated["role_limits"]["historical_silver_replacement_allowed"] = True
    blocked = validate(mutated, evidence)
    assert blocked["formal_state"] == BLOCKED_STATE, blocked
    assert "role.no_historical_silver_replacement_allowed" in blocked["quality"]["failed_checks"], blocked

    mutated = copy.deepcopy(policy)
    mutated["player_boxscore_boundary"]["player_stat_parity_approved"] = True
    blocked = validate(mutated, evidence)
    assert blocked["formal_state"] == BLOCKED_STATE, blocked
    assert "player.no_stat_parity" in blocked["quality"]["failed_checks"], blocked

    mutated_evidence = copy.deepcopy(evidence)
    mutated_evidence["formal_outcome"] = "SECONDARY_SOURCE_REJECTED"
    blocked = validate(policy, mutated_evidence)
    assert blocked["formal_state"] == BLOCKED_STATE, blocked
    assert "evidence.formal_outcome" in blocked["quality"]["failed_checks"], blocked


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, default=Path("data/eoin-adapter-predeclaration-v1.json"))
    parser.add_argument("--evidence", type=Path, default=Path("data/eoin-cross-source-audit-v1.json"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    policy = read_json(args.policy)
    evidence = read_json(args.evidence)
    if args.self_test:
        self_test(policy, evidence)
        print("eoin adapter predeclaration self-test passed")
        return 0

    report = validate(policy, evidence)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
