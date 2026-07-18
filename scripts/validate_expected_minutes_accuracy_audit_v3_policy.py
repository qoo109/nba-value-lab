#!/usr/bin/env python3
"""Validate that the v3 predeclaration preserves v1/v2 gates and does not execute accuracy."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

VERSION = "expected-minutes-accuracy-audit-v3-policy-validator-v1"

PRESERVED_STRUCTURAL_KEYS = [
    "minimum_games_with_evaluable_player_rows",
    "minimum_selected_player_snapshot_rows",
    "minimum_official_game_source_coverage",
    "minimum_identity_match_rate",
    "minimum_expected_minutes_coverage",
    "maximum_unknown_rate_for_matched_players",
    "maximum_source_missing_games",
    "minimum_conditional_role_rows",
    "minimum_actual_starter_rows",
    "minimum_actual_bench_rows",
    "minimum_long_history_rows",
    "minimum_complete_team_game_groups",
    "strict_prior_date_violations",
    "duplicate_selected_games",
    "duplicate_official_game_player_rows",
    "invalid_participation_labels",
    "invalid_minutes_label_combinations",
]

EXPECTED_COUNTS = {
    "successful_official_source_games": 293,
    "source_missing_games": 0,
    "official_player_rows": 10309,
    "selected_player_snapshot_rows": 3045,
    "identity_matched_rows": 3037,
    "official_participation_join_rows": 3022,
    "unknown_rows": 103,
    "games_with_evaluable_played_rows": 226,
    "conditional_played_rows": 516,
    "actual_starter_rows": 307,
    "actual_bench_rows": 209,
    "long_history_rows": 502,
    "complete_team_game_groups": 450,
    "recognized_roster_transition_rows": 1,
    "unrecognized_team_mismatches": 0,
}


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def validate(v2: dict[str, Any], v3: dict[str, Any]) -> dict[str, Any]:
    v2_structural = v2.get("structural_gates", {})
    v3_structural = v3.get("structural_gates", {})
    v2_accuracy = v2.get("primary_accuracy_gates", {})
    v3_accuracy = v3.get("primary_accuracy_gates", {})

    checks = {
        "schema_version": v3.get("schema_version")
        == "expected-minutes-accuracy-audit-policy-v3",
        "predeclared_before_execution": v3.get("predeclaration", {}).get(
            "policy_committed_before_v3_accuracy_execution"
        ) is True,
        "predeclared_before_result": v3.get("predeclaration", {}).get(
            "policy_committed_before_v3_accuracy_result"
        ) is True,
        "post_result_edits_forbidden": v3.get("predeclaration", {}).get(
            "post_result_threshold_edits_allowed"
        ) is False,
        "population_exact_293": v3.get("evaluation_population", {}).get(
            "combined_selected_independent_games"
        ) == 293,
        "wave_counts_exact": v3.get("evaluation_population", {}).get(
            "wave_selected_games"
        ) == {"wave1": 91, "wave2": 85, "wave3": 117},
        "selection_policy_preserved": v3.get("evaluation_population", {}).get(
            "selection_policy"
        ) == v2.get("evaluation_population", {}).get("selection_policy"),
        "minimum_t60_preserved": v3.get("evaluation_population", {}).get(
            "minimum_minutes_before_tip"
        ) == v2.get("evaluation_population", {}).get("minimum_minutes_before_tip"),
        "fallback_forbidden": v3.get("evaluation_population", {}).get(
            "fallback_allowed"
        ) is False,
        "target_labels_evaluation_only": v3.get("evaluation_population", {}).get(
            "target_game_labels_are_evaluation_only"
        ) is True,
        "frozen_counts_exact": v3.get("frozen_input_counts") == EXPECTED_COUNTS,
        "census_source_pr": v3.get("upstream_census", {}).get("source_pr") == 52,
        "census_merge_commit": v3.get("upstream_census", {}).get(
            "source_merge_commit"
        ) == "b2e07050e883cc62c35714406bdab606377d301c",
        "census_state_eligible": v3.get("upstream_census", {}).get("formal_state")
        == "CENSUS_READY_AUDIT_V3_ELIGIBLE",
        "census_accuracy_not_calculated": v3.get("upstream_census", {}).get(
            "accuracy_metrics_calculated_in_census"
        ) is False,
        "primary_estimand_preserved": v3.get("primary_estimand", {}).get("name")
        == v2.get("primary_estimand", {}).get("name"),
        "primary_prediction_preserved": v3.get("primary_estimand", {}).get(
            "prediction"
        ) == v2.get("primary_estimand", {}).get("prediction"),
        "primary_label_preserved": v3.get("primary_estimand", {}).get("label")
        == v2.get("primary_estimand", {}).get("label"),
        "accuracy_gates_exactly_preserved": v3_accuracy == v2_accuracy,
        "required_subgroups_exactly_preserved": v3.get("required_subgroups")
        == v2.get("required_subgroups"),
        "decision_states_exactly_preserved": v3.get("decision_states")
        == v2.get("decision_states"),
        "structural_sample_gates_preserved": all(
            v3_structural.get(key) == v2_structural.get(key)
            for key in PRESERVED_STRUCTURAL_KEYS
        ),
        "join_gate_not_lowered": float(
            v3_structural.get("minimum_participation_label_join_rate_for_matched_players", 0)
        ) >= float(
            v2_structural.get("minimum_participation_label_join_rate_for_matched_players", 0)
        ),
        "join_gate_matches_census_contract": v3_structural.get(
            "minimum_participation_label_join_rate_for_matched_players"
        ) == 0.99,
        "ambiguous_identity_zero": v3_structural.get("ambiguous_identity_rows") == 0,
        "fuzzy_identity_false": v3_structural.get("fuzzy_identity_used") is False,
        "unrecognized_team_mismatch_zero": v3_structural.get(
            "maximum_unrecognized_team_mismatches"
        ) == 0,
        "recognized_transition_exact_one": v3_structural.get(
            "required_recognized_roster_transition_rows"
        ) == 1,
        "duplicate_accuracy_rows_zero": v3_structural.get("duplicate_accuracy_rows") == 0,
        "privacy_retained_zero": v3_structural.get(
            "forbidden_player_level_files_retained"
        ) == 0,
        "raw_official_labels_unmodified": v3.get(
            "frozen_input_integrity_gates", {}
        ).get("require_raw_official_labels_unmodified") is True,
        "exact_input_counts_required": v3.get("frozen_input_integrity_gates", {}).get(
            "require_exact_frozen_input_counts"
        ) is True,
        "missing_not_zero": all([
            v3.get("participation_labels", {}).get("missing_player_row_is_zero_minutes")
            is False,
            v3.get("participation_labels", {}).get("unknown_label_is_zero_minutes")
            is False,
            v3.get("guardrails", {}).get("missing_actual_is_zero_minutes") is False,
            v3.get("guardrails", {}).get("missing_expected_minutes_is_zero_minutes")
            is False,
        ]),
        "secondary_estimands_nonpromotion": all(
            item.get("promotion_gate") is False
            for item in v3.get("secondary_estimands", [])
        ),
        "accuracy_pass_only_unlocks_design_predeclaration": v3.get(
            "post_decision_permissions", {}
        ).get("ACCURACY_PASS", {}).get(
            "ready_for_injury_feature_walk_forward_holdout_design_predeclaration"
        ) is True,
        "holdout_execution_still_false": v3.get("post_decision_permissions", {}).get(
            "ready_for_injury_feature_walk_forward_holdout_execution"
        ) is False,
        "model_activation_false": v3.get("post_decision_permissions", {}).get(
            "ready_for_model_training"
        ) is False,
        "probability_adjustment_false": v3.get("post_decision_permissions", {}).get(
            "ready_for_probability_adjustment"
        ) is False,
        "betting_claim_false": v3.get("post_decision_permissions", {}).get(
            "ready_for_betting_edge_claim"
        ) is False,
        "formal_stake_zero": v3.get("post_decision_permissions", {}).get(
            "formal_stake"
        ) == 0,
    }

    forbidden_result_keys = {
        "overall_mae",
        "overall_rmse",
        "overall_bias",
        "median_absolute_error",
        "starter_mae",
        "bench_mae",
        "accuracy_result",
        "audit_result",
    }
    top_level_keys = set(v3)
    checks["no_v3_accuracy_result_fields"] = not (top_level_keys & forbidden_result_keys)

    passed = all(checks.values())
    return {
        "schema_version": VERSION,
        "passed": passed,
        "checks": checks,
        "failed_checks": sorted(key for key, value in checks.items() if not value),
        "decision": {
            "ready_for_v3_predeclaration_merge": passed,
            "ready_for_v3_accuracy_execution": False,
            "ready_for_injury_holdout": False,
            "ready_for_model_training": False,
            "ready_for_betting_edge_claim": False,
            "formal_stake": 0,
        },
    }


def self_test() -> None:
    assert len(EXPECTED_COUNTS) == 15
    assert EXPECTED_COUNTS["conditional_played_rows"] >= 500
    assert EXPECTED_COUNTS["actual_bench_rows"] >= 200
    assert EXPECTED_COUNTS["long_history_rows"] >= 400


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v2-policy", type=Path)
    parser.add_argument("--v3-policy", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        print("Expected Minutes Accuracy Audit v3 policy validator self-test passed")
        return
    if args.v2_policy is None or args.v3_policy is None:
        parser.error("--v2-policy and --v3-policy are required")
    result = validate(read_json(args.v2_policy), read_json(args.v3_policy))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    if not result["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
