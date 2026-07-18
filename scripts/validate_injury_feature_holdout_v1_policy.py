#!/usr/bin/env python3
"""Validate the frozen Injury Feature Walk-forward Holdout v1 predeclaration.

This module validates governance and internal consistency only. It must not fit a
candidate, read game outcomes, or calculate holdout metrics.
"""
from __future__ import annotations

import argparse
import copy
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "injury-feature-walk-forward-holdout-policy-validation-v1"
POLICY_SCHEMA = "injury-feature-walk-forward-holdout-policy-v1"
EXPECTED_FEATURES = [
    "weighted_unavailable_minutes_home_minus_away",
    "weighted_absence_impact_positive_home_minus_away",
]
EXPECTED_STATES = [
    "STRUCTURAL_BLOCKED",
    "VALID_NEGATIVE_RESULT",
    "HOLDOUT_RESEARCH_PASS",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def parse_date(value: Any) -> date:
    return date.fromisoformat(str(value))


def check(condition: bool, name: str, failures: list[str]) -> None:
    if not condition:
        failures.append(name)


def validate(policy: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []

    check(policy.get("schema_version") == POLICY_SCHEMA, "schema_version", failures)
    check(policy.get("roadmap_parent") == "step-4-injury-feature-walk-forward-holdout", "roadmap_parent", failures)

    pre = policy.get("predeclaration", {})
    for field in (
        "policy_committed_before_holdout_implementation",
        "policy_committed_before_candidate_fit",
        "policy_committed_before_holdout_metrics",
    ):
        check(pre.get(field) is True, f"predeclaration.{field}", failures)
    check(pre.get("post_result_threshold_edits_allowed") is False, "no_post_result_threshold_edits", failures)
    check(pre.get("outcome_based_feature_selection_allowed") is False, "no_outcome_feature_selection", failures)
    check(pre.get("hyperparameter_search_allowed") is False, "no_hyperparameter_search", failures)

    upstream = policy.get("upstream_evidence", {})
    audit = upstream.get("expected_minutes_audit_v3", {})
    check(audit.get("source_pr") == 54, "upstream.audit_pr", failures)
    check(audit.get("formal_state") == "ACCURACY_PASS", "upstream.audit_pass", failures)
    check(audit.get("source_merge_commit") == upstream.get("base_main_commit"), "upstream.audit_merge_is_base", failures)
    baseline_source = upstream.get("baseline_oof", {})
    check(baseline_source.get("model_version") == "walk-forward-v2", "upstream.baseline_version", failures)
    check(baseline_source.get("source_run") == 29551715399, "upstream.baseline_run", failures)

    pop = policy.get("frozen_population", {})
    check(pop.get("combined_selected_independent_games") == 293, "population.games", failures)
    check(pop.get("wave_selected_games") == {"wave1": 91, "wave2": 85, "wave3": 117}, "population.wave_counts", failures)
    check(sum(pop.get("wave_selected_games", {}).values()) == 293, "population.wave_sum", failures)
    check(pop.get("selection_policy") == "latest_feature_ready_at_or_before_t60", "population.selection_policy", failures)
    check(pop.get("minimum_minutes_before_tip") == 60, "population.t60", failures)
    check(pop.get("fallback_allowed") is False, "population.no_fallback", failures)
    check(pop.get("deduplication_key") == "historical_game_id", "population.dedup_key", failures)
    check(pop.get("baseline_oof_join_required") == 293, "population.baseline_join", failures)
    check(pop.get("game_identity_mismatches_allowed") == 0, "population.identity_mismatch", failures)
    check(pop.get("matchup_snapshot_complete_required") is True, "population.complete_snapshot", failures)
    check(pop.get("matchup_feature_available_required") is True, "population.feature_available", failures)

    folds = policy.get("chronological_folds", [])
    check(len(folds) == 2, "folds.count", failures)
    expected_folds = [
        {
            "fold_id": "development_forward_1",
            "train_start": "2023-10-30",
            "train_end": "2024-01-31",
            "expected_train_games": 124,
            "test_start": "2024-02-01",
            "test_end": "2024-02-29",
            "expected_test_games": 65,
            "role": "development_forward_check",
        },
        {
            "fold_id": "final_untouched_holdout",
            "train_start": "2023-10-30",
            "train_end": "2024-02-29",
            "expected_train_games": 189,
            "test_start": "2024-03-01",
            "test_end": "2024-04-12",
            "expected_test_games": 104,
            "role": "primary_final_holdout",
        },
    ]
    check(folds == expected_folds, "folds.exact", failures)
    if len(folds) == 2:
        for index, fold in enumerate(folds):
            try:
                train_start = parse_date(fold["train_start"])
                train_end = parse_date(fold["train_end"])
                test_start = parse_date(fold["test_start"])
                test_end = parse_date(fold["test_end"])
                check(train_start <= train_end < test_start <= test_end, f"folds.{index}.chronology", failures)
            except Exception:
                failures.append(f"folds.{index}.dates")
    check(sum(int(f.get("expected_test_games", 0)) for f in folds) == 169, "folds.test_sum", failures)
    check(policy.get("combined_forward_test_games") == 169, "folds.combined_forward_count", failures)

    baseline = policy.get("baseline", {})
    check(baseline.get("probability_field") == "predicted_home_win_probability", "baseline.probability_field", failures)
    check(baseline.get("margin_field") == "predicted_home_margin", "baseline.margin_field", failures)
    check(baseline.get("raw_probability_selected_by_prior_calibration_gate") is True, "baseline.raw_selected", failures)
    check(baseline.get("recalibration_inside_holdout") is False, "baseline.no_recalibration", failures)
    check(baseline.get("market_odds_used") is False, "baseline.no_market", failures)

    candidate = policy.get("primary_candidate", {})
    check(candidate.get("name") == "bounded_injury_logit_offset_v1", "candidate.name", failures)
    check(candidate.get("features") == EXPECTED_FEATURES, "candidate.features", failures)
    prep = candidate.get("preprocessing", {})
    check(prep.get("standardization") == "training-fold mean and population standard deviation only", "candidate.train_only_scaling", failures)
    check(prep.get("test_fold_statistics_used") is False, "candidate.no_test_statistics", failures)
    check(prep.get("missing_feature_imputation") is False, "candidate.no_imputation", failures)
    check(prep.get("probability_clip") == [0.000001, 0.999999], "candidate.probability_clip", failures)
    fit = candidate.get("fit", {})
    check(fit.get("l2_alpha") == 0.05, "candidate.l2_alpha", failures)
    check(fit.get("intercept") is False, "candidate.no_intercept", failures)
    check(fit.get("baseline_logit_coefficient") == 1.0, "candidate.fixed_baseline_logit", failures)
    check(fit.get("coefficient_bounds") == [-0.5, 0.0], "candidate.bounds", failures)
    check(fit.get("optimizer") == "L-BFGS-B", "candidate.optimizer", failures)
    check(fit.get("initial_coefficients") == [0.0, 0.0], "candidate.initial_coefficients", failures)
    check(fit.get("maximum_iterations") == 2000, "candidate.max_iterations", failures)
    check(fit.get("tolerance") == 1e-09, "candidate.tolerance", failures)
    check(fit.get("random_seed") == 20260718, "candidate.seed", failures)
    check(fit.get("hyperparameter_tuning") is False, "candidate.no_tuning", failures)

    margin = policy.get("secondary_margin_candidate", {})
    check(margin.get("promotion_gate") is False, "margin.not_promotion_gate", failures)
    check(margin.get("features") == EXPECTED_FEATURES, "margin.features", failures)
    check(margin.get("coefficient_bounds") == [-6.0, 0.0], "margin.bounds", failures)

    structural = policy.get("structural_gates", {})
    exact_structural = {
        "required_population_games": 293,
        "required_baseline_join_games": 293,
        "required_unique_game_ids": 293,
        "required_combined_forward_test_games": 169,
        "required_final_holdout_games": 104,
        "duplicate_injury_games": 0,
        "duplicate_baseline_games": 0,
        "game_identity_mismatches": 0,
        "fold_overlap_games": 0,
        "test_rows_used_for_training": 0,
        "feature_rows_with_missing_values": 0,
        "snapshot_rows_before_t60_violations": 0,
        "strict_point_in_time_violations": 0,
        "target_game_labels_used_as_features": False,
        "market_odds_used": False,
        "random_shuffle_used": False,
        "fuzzy_identity_used": False,
        "fuzzy_schedule_matching_used": False,
    }
    check(structural == exact_structural, "structural_gates.exact", failures)

    check(policy.get("primary_metrics") == ["log_loss", "brier_score"], "metrics.primary", failures)
    bootstrap = policy.get("paired_bootstrap", {})
    check(bootstrap.get("unit") == "historical_game_id", "bootstrap.unit", failures)
    check(bootstrap.get("replicates") == 10000, "bootstrap.replicates", failures)
    check(bootstrap.get("seed") == 20260718, "bootstrap.seed", failures)
    check(bootstrap.get("reported_intervals") == [0.8, 0.95], "bootstrap.intervals", failures)

    promotion = policy.get("promotion_gates", {})
    exact_promotion = {
        "minimum_combined_forward_log_loss_gain": 0.002,
        "minimum_final_holdout_log_loss_gain": 0.0,
        "minimum_development_fold_log_loss_gain": -0.005,
        "minimum_combined_forward_brier_gain": 0.0005,
        "minimum_final_holdout_brier_gain": -0.001,
        "minimum_combined_bootstrap_probability_log_loss_gain_positive": 0.7,
        "minimum_final_holdout_bootstrap_probability_log_loss_gain_positive": 0.55,
        "maximum_average_absolute_probability_shift": 0.05,
        "maximum_single_game_absolute_probability_shift": 0.2,
        "maximum_monitored_subgroup_log_loss_degradation": 0.03,
        "required_primary_candidate_coefficients_non_positive": True,
    }
    check(promotion == exact_promotion, "promotion_gates.exact", failures)

    subgroups = policy.get("monitored_subgroups", {})
    check(subgroups.get("minimum_rows_for_safety_gate") == 30, "subgroups.minimum_rows", failures)
    check(subgroups.get("quartile_thresholds_learned_from_training_only") is True, "subgroups.train_only_quartiles", failures)

    check(policy.get("decision_states") == EXPECTED_STATES, "decision_states", failures)
    rules = policy.get("decision_rules", {})
    check(set(rules) == set(EXPECTED_STATES), "decision_rules.states", failures)
    permissions = policy.get("post_decision_permissions", {})
    check(permissions.get("STRUCTURAL_BLOCKED", {}).get("ready_for_timestamped_odds_predeclaration") is False, "permissions.structural_block", failures)
    check(permissions.get("VALID_NEGATIVE_RESULT", {}).get("ready_for_timestamped_odds_predeclaration") is True, "permissions.negative_market_path", failures)
    check(permissions.get("VALID_NEGATIVE_RESULT", {}).get("injury_candidate_research_ready") is False, "permissions.negative_reject_candidate", failures)
    check(permissions.get("HOLDOUT_RESEARCH_PASS", {}).get("ready_for_timestamped_odds_predeclaration") is True, "permissions.pass_market_path", failures)
    check(permissions.get("HOLDOUT_RESEARCH_PASS", {}).get("injury_candidate_research_ready") is True, "permissions.pass_candidate", failures)
    check(permissions.get("ready_for_timestamped_odds_execution") is False, "permissions.no_odds_execution", failures)
    check(permissions.get("ready_for_production_model_training") is False, "permissions.no_production_training", failures)
    check(permissions.get("ready_for_probability_adjustment") is False, "permissions.no_probability_adjustment", failures)
    check(permissions.get("ready_for_betting_edge_claim") is False, "permissions.no_betting_claim", failures)
    check(permissions.get("formal_stake") == 0, "permissions.stake_zero", failures)

    guard = policy.get("guardrails", {})
    for field in (
        "closing_market_used_for_feature_selection",
        "odds_used_for_training",
        "same_game_multiple_snapshots_are_independent_samples",
        "target_game_participation_used_as_prediction_feature",
        "target_game_minutes_used_as_prediction_feature",
        "missing_injury_values_imputed_as_zero",
        "post_result_candidate_changes_allowed",
        "secondary_metrics_can_override_primary_failure",
        "subgroup_results_can_override_primary_failure",
        "holdout_pass_directly_activates_model",
        "holdout_pass_directly_enables_betting",
    ):
        check(guard.get(field) is False, f"guardrails.{field}", failures)
    check(guard.get("valid_negative_result_must_be_retained") is True, "guardrails.retain_negative", failures)

    return {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "policy_schema_version": policy.get("schema_version"),
        "quality": {
            "validation_checks": 89,
            "failed_checks": sorted(set(failures)),
            "holdout_metrics_calculated": False,
            "candidate_fit_performed": False,
            "game_outcomes_read": False,
            "market_odds_read": False,
        },
        "decision": {
            "ready_for_injury_feature_holdout_v1_implementation": not failures,
            "ready_for_injury_feature_holdout_v1_execution": False,
            "ready_for_timestamped_odds_execution": False,
            "ready_for_production_model_training": False,
            "ready_for_probability_adjustment": False,
            "ready_for_betting_edge_claim": False,
            "formal_stake": 0,
        },
    }


def self_test(policy: dict[str, Any]) -> None:
    valid = validate(policy)
    assert valid["decision"]["ready_for_injury_feature_holdout_v1_implementation"] is True, valid
    assert valid["quality"]["holdout_metrics_calculated"] is False, valid

    mutated = copy.deepcopy(policy)
    mutated["promotion_gates"]["minimum_combined_forward_log_loss_gain"] = -1.0
    invalid = validate(mutated)
    assert invalid["decision"]["ready_for_injury_feature_holdout_v1_implementation"] is False, invalid
    assert "promotion_gates.exact" in invalid["quality"]["failed_checks"], invalid

    mutated = copy.deepcopy(policy)
    mutated["primary_candidate"]["fit"]["hyperparameter_tuning"] = True
    invalid = validate(mutated)
    assert "candidate.no_tuning" in invalid["quality"]["failed_checks"], invalid

    mutated = copy.deepcopy(policy)
    mutated["post_decision_permissions"]["ready_for_betting_edge_claim"] = True
    invalid = validate(mutated)
    assert "permissions.no_betting_claim" in invalid["quality"]["failed_checks"], invalid


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    policy = read_json(args.policy)
    if args.self_test:
        self_test(policy)
        print("Injury Feature holdout v1 policy self-test passed")
        return

    report = validate(policy)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["decision"], indent=2))
    if not report["decision"]["ready_for_injury_feature_holdout_v1_implementation"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
