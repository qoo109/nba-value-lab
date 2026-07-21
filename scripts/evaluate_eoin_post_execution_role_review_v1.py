#!/usr/bin/env python3
"""Evaluate the frozen Eoin post-execution role review using aggregate evidence only."""
from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from validate_eoin_post_execution_role_review_policy_v1 import (
    READY_STATE as POLICY_READY_STATE,
    load_json,
    validate as validate_policy,
)

SCHEMA_VERSION = "eoin-post-execution-role-review-evaluation-report-v1"
MANIFEST_SCHEMA = "eoin-post-execution-role-review-evaluation-v1"
MANIFEST_STATE = "POST_EXECUTION_ROLE_REVIEW_EVALUATION_PREDECLARED"
CURRENT_ROLE = "ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE"
VALIDATED_ROLE = "ROLE_LIMITED_SECONDARY_QA_SOURCE_VALIDATED"
RETAIN_ROLE = "RETAIN_ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE"
BLOCKED = "POST_EXECUTION_ROLE_REVIEW_BLOCKED"
EXPECTED_OUTCOMES = {VALIDATED_ROLE, RETAIN_ROLE, BLOCKED}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def validate_manifest(manifest: dict[str, Any]) -> dict[str, bool]:
    checks: dict[str, bool] = {}
    checks["schema_version"] = manifest.get("schema_version") == MANIFEST_SCHEMA
    checks["source_id"] = manifest.get("source_id") == "kaggle_eoinamoore_historical_nba"
    checks["evaluation_state"] = manifest.get("evaluation_state") == MANIFEST_STATE
    checks["policy_path"] = manifest.get("policy") == "data/eoin-post-execution-role-review-policy-v1.json"
    checks["policy_state"] = manifest.get("policy_required_state") == POLICY_READY_STATE
    checks["current_role"] = manifest.get("current_formal_role") == CURRENT_ROLE
    checks["candidate_outcomes"] = set(manifest.get("candidate_outcomes") or []) == EXPECTED_OUTCOMES

    rules = manifest.get("outcome_rules") or {}
    checks["outcome_rules"] = (
        rules.get("policy_or_boundary_failure") == BLOCKED
        and rules.get("valid_policy_but_any_scientific_gate_failure") == RETAIN_ROLE
        and rules.get("valid_policy_and_all_scientific_gates_pass") == VALIDATED_ROLE
    )

    input_boundary = manifest.get("input_boundary") or {}
    checks["input_boundary"] = (
        input_boundary.get("policy_json_only") is True
        and input_boundary.get("embedded_aggregate_evidence_only") is True
        and input_boundary.get("network_calls_allowed") is False
        and input_boundary.get("new_bundle_execution_allowed") is False
        and input_boundary.get("raw_source_rows_read_allowed") is False
        and input_boundary.get("external_artifact_download_allowed") is False
    )

    output_boundary = manifest.get("output_boundary") or {}
    checks["output_boundary"] = (
        output_boundary.get("aggregate_report_only") is True
        and output_boundary.get("maximum_output_files") == 1
        and output_boundary.get("raw_rows_emitted") == 0
        and output_boundary.get("raw_files_emitted") is False
        and output_boundary.get("downloaded_archives_emitted") is False
        and output_boundary.get("derived_tables_emitted") is False
    )

    role_boundary = manifest.get("role_boundary") or {}
    false_keys = (
        "primary_source_allowed",
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
        "repeat_full_bundle_execution_allowed",
    )
    checks["role_boundary"] = (
        role_boundary.get("maximum_possible_role") == VALIDATED_ROLE
        and all(role_boundary.get(key) is False for key in false_keys)
        and role_boundary.get("formal_stake") == 0
    )

    expected = manifest.get("expected_result_for_frozen_evidence") or {}
    checks["expected_result"] = (
        expected.get("formal_outcome") == VALIDATED_ROLE
        and expected.get("all_scientific_gates_passed") is True
        and expected.get("current_role_superseded_for_qa_label_only") is True
        and expected.get("ready_for_primary_source_use") is False
        and expected.get("ready_for_silver_replacement") is False
        and expected.get("ready_for_gold_replacement") is False
        and expected.get("ready_for_player_stat_parity") is False
        and expected.get("ready_for_model_retraining") is False
        and expected.get("ready_for_market_backtest") is False
        and expected.get("ready_for_betting_edge_claim") is False
        and expected.get("formal_stake") == 0
    )
    return checks


def scientific_gate_results(policy: dict[str, Any]) -> dict[str, bool]:
    gates = policy.get("frozen_review_gates") or {}
    evidence = policy.get("evidence_anchors") or {}
    cross = evidence.get("cross_source_audit") or {}
    execution = evidence.get("one_time_full_adapter_execution") or {}

    return {
        "cross_source_matched_games": cross.get("matched_games", 0)
        >= gates.get("minimum_cross_source_matched_games", 10**9),
        "game_identity_match_rate": cross.get("game_identity_match_rate", 0)
        >= gates.get("minimum_game_identity_match_rate", 1.1),
        "final_score_match_rate": cross.get("final_score_match_rate", 0)
        >= gates.get("minimum_final_score_match_rate", 1.1),
        "cross_team_boxscore_coverage_rate": cross.get("team_boxscore_coverage_rate", 0)
        >= gates.get("minimum_team_boxscore_coverage_rate", 1.1),
        "cross_team_boxscore_score_match_rate": cross.get("team_boxscore_score_match_rate", 0)
        >= gates.get("minimum_team_boxscore_score_match_rate", 1.1),
        "cross_player_candidate_coverage_rate": cross.get("player_boxscore_candidate_coverage_rate", 0)
        >= gates.get("minimum_player_boxscore_candidate_coverage_rate", 1.1),
        "cross_pbp_game_coverage_rate": cross.get("pbp_game_coverage_rate", 0)
        >= gates.get("minimum_pbp_game_coverage_rate", 1.1),
        "full_bundle_games": execution.get("games", 0)
        >= gates.get("minimum_full_bundle_games", 10**9),
        "full_team_boxscore_coverage_rate": execution.get("team_boxscore_coverage_rate", 0)
        >= gates.get("minimum_team_boxscore_coverage_rate", 1.1),
        "full_team_boxscore_score_match_rate": execution.get("team_boxscore_score_match_rate", 0)
        >= gates.get("minimum_team_boxscore_score_match_rate", 1.1),
        "full_player_candidate_coverage_rate": execution.get("player_boxscore_candidate_coverage_rate", 0)
        >= gates.get("minimum_player_boxscore_candidate_coverage_rate", 1.1),
        "full_pbp_game_coverage_rate": execution.get("pbp_game_coverage_rate", 0)
        >= gates.get("minimum_pbp_game_coverage_rate", 1.1),
        "duplicate_game_id_groups": execution.get("duplicate_game_id_groups", 10**9)
        <= gates.get("maximum_duplicate_game_id_groups", -1),
        "request_consumed": execution.get("request_consumed")
        is gates.get("request_must_be_consumed"),
        "execution_count": execution.get("execution_count", 10**9)
        <= gates.get("maximum_execution_count", -1),
        "raw_rows_emitted": execution.get("raw_rows_emitted", 10**9)
        <= gates.get("maximum_raw_rows_emitted", -1),
        "raw_files_emitted": execution.get("raw_files_emitted")
        is gates.get("raw_files_emitted_allowed"),
    }


def evaluate(manifest: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    manifest_checks = validate_manifest(manifest)
    policy_report = validate_policy(policy)
    gates = scientific_gate_results(policy)

    manifest_failures = sorted(name for name, passed in manifest_checks.items() if not passed)
    boundary_valid = not manifest_failures and policy_report["formal_state"] == POLICY_READY_STATE
    all_scientific_gates_passed = all(gates.values())

    if not boundary_valid:
        outcome = BLOCKED
    elif all_scientific_gates_passed:
        outcome = VALIDATED_ROLE
    else:
        outcome = RETAIN_ROLE

    failed_scientific_gates = sorted(name for name, passed in gates.items() if not passed)
    return {
        "schema_version": SCHEMA_VERSION,
        "evaluated_at": utc_now(),
        "evaluation_state": "POST_EXECUTION_ROLE_REVIEW_EVALUATION_COMPLETE",
        "formal_outcome": outcome,
        "previous_formal_role": policy.get("current_formal_role"),
        "reviewed_formal_role": VALIDATED_ROLE if outcome == VALIDATED_ROLE else CURRENT_ROLE,
        "policy_validation": {
            "formal_state": policy_report["formal_state"],
            "checks_failed": policy_report["checks_failed"],
        },
        "manifest_checks": manifest_checks,
        "manifest_failures": manifest_failures,
        "scientific_gates": gates,
        "failed_scientific_gates": failed_scientific_gates,
        "all_scientific_gates_passed": all_scientific_gates_passed,
        "quality": {
            "network_calls_made": False,
            "new_bundle_execution_performed": False,
            "external_artifacts_downloaded": False,
            "raw_eoin_rows_read": False,
            "raw_rows_emitted": 0,
            "raw_files_emitted": False,
            "derived_tables_emitted": False,
            "formal_stake": 0,
        },
        "role_scope": {
            "secondary_qa_only": outcome == VALIDATED_ROLE,
            "game_identity_qa": outcome == VALIDATED_ROLE,
            "final_score_qa": outcome == VALIDATED_ROLE,
            "team_boxscore_qa": outcome == VALIDATED_ROLE,
            "player_boxscore_candidate_coverage_only": outcome == VALIDATED_ROLE,
            "pbp_game_coverage_qa": outcome == VALIDATED_ROLE,
            "independent_player_stat_parity": False,
        },
        "downstream_permissions": {
            "ready_for_primary_source_use": False,
            "ready_for_silver_replacement": False,
            "ready_for_gold_replacement": False,
            "ready_for_player_stat_parity": False,
            "ready_for_player_feature_import": False,
            "ready_for_model_retraining": False,
            "ready_for_market_backtest": False,
            "ready_for_clv_ev_roi_drawdown": False,
            "ready_for_betting_edge_claim": False,
            "ready_for_repeat_full_bundle_execution": False,
            "formal_stake": 0,
        },
    }


def self_test(manifest: dict[str, Any], policy: dict[str, Any]) -> None:
    report = evaluate(manifest, policy)
    assert report["formal_outcome"] == VALIDATED_ROLE, report
    assert report["all_scientific_gates_passed"] is True, report

    mutated_policy = copy.deepcopy(policy)
    mutated_policy["evidence_anchors"]["cross_source_audit"]["final_score_match_rate"] = 0.97
    report = evaluate(manifest, mutated_policy)
    assert report["formal_outcome"] == RETAIN_ROLE, report
    assert "final_score_match_rate" in report["failed_scientific_gates"], report

    mutated_manifest = copy.deepcopy(manifest)
    mutated_manifest["role_boundary"]["primary_source_allowed"] = True
    report = evaluate(mutated_manifest, policy)
    assert report["formal_outcome"] == BLOCKED, report

    mutated_policy = copy.deepcopy(policy)
    mutated_policy["review_scope"]["raw_rows_emitted"] = 1
    report = evaluate(manifest, mutated_policy)
    assert report["formal_outcome"] == BLOCKED, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/eoin-post-execution-role-review-evaluation-v1.json"),
    )
    parser.add_argument(
        "--policy",
        type=Path,
        default=Path("data/eoin-post-execution-role-review-policy-v1.json"),
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    manifest = load_json(args.manifest)
    policy = load_json(args.policy)
    if args.self_test:
        self_test(manifest, policy)

    report = evaluate(manifest, policy)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "formal_outcome": report["formal_outcome"],
                "all_scientific_gates_passed": report["all_scientific_gates_passed"],
                "failed_scientific_gates": report["failed_scientific_gates"],
            },
            indent=2,
        )
    )
    return 0 if report["formal_outcome"] != BLOCKED else 1


if __name__ == "__main__":
    raise SystemExit(main())
