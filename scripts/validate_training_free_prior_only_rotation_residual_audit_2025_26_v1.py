#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

SPEC = Path("data/research/training-free-prior-only-rotation-residual-audit-2025-26-v1.json")
DOC = Path("docs/training-free-prior-only-rotation-residual-audit-2025-26-v1.md")
FORMAL_STATE = "TRAINING_FREE_PRIOR_ONLY_ROTATION_RESIDUAL_AUDIT_2025_26_V1_DESIGN_VALID"
PREDECLARED_STATE = "TRAINING_FREE_PRIOR_ONLY_ROTATION_RESIDUAL_AUDIT_2025_26_V1_PREDECLARED"
NEXT = "EXECUTE_TRAINING_FREE_PRIOR_ONLY_ROTATION_RESIDUAL_AUDIT_2025_26_V1_ON_BOUND_PRIVATE_ARTIFACTS"

EXPECTED_FEATURES = [
    "rotation_players_prior_5_diff",
    "top5_minutes_share_prior_5_diff",
    "top8_minutes_share_prior_5_diff",
    "top8_minutes_share_prior_10_diff",
    "rotation_entropy_prior_5_diff",
    "rotation_entropy_prior_10_diff",
    "top8_set_continuity_prior_5_diff",
    "starter_set_continuity_prior_5_diff",
    "minutes_allocation_volatility_prior_5_diff",
    "role_change_magnitude_prior_3_vs_10_diff",
    "recent_return_players_count_diff",
    "new_team_rotation_players_prior_5_diff",
]


def main() -> int:
    payload = json.loads(SPEC.read_text(encoding="utf-8"))
    document = DOC.read_text(encoding="utf-8")
    checks: dict[str, bool] = {}

    def check(name: str, condition: bool) -> None:
        checks[name] = bool(condition)

    check("schema", payload.get("schema_version") == "training-free-prior-only-rotation-residual-audit-2025-26-v1")
    check("predeclared_state", payload.get("formal_state") == PREDECLARED_STATE)
    binding = payload.get("binding_history", {})
    check("base_main", binding.get("base_main") == "85821f7df6babce207dc5c39a24fbdcedd5ad165")
    check("binding_pr", binding.get("binding_feature_pr") == 187)
    check("binding_result", binding.get("binding_feature_result") == "PRIOR_ONLY_PLAYER_ROTATION_STATE_FEATURES_2025_26_RESULT_VALID")
    check("frozen_baseline_lock", binding.get("binding_prior_decision") == "PRESERVE_FROZEN_BASELINE_AND_MARKET_BACKTEST_LOCK")
    check("current_mainline", binding.get("current_unique_mainline") == "PREDECLARE_TRAINING_FREE_PRIOR_ONLY_ROTATION_RESIDUAL_AUDIT_2025_26_V1")

    inputs = payload.get("bound_private_inputs", {})
    check("feature_artifact", inputs.get("rotation_feature_artifact_id") == 8603761824)
    check("feature_artifact_digest", inputs.get("rotation_feature_artifact_digest") == "sha256:e02cd15e9b3aa1d58d3cbee1f27f1caea461d7e2f8ec701389e6e5f969ba440a")
    check("feature_head", inputs.get("rotation_feature_head") == "b1de9fa8616caff42f251d2db253e8ed2f80e42a")
    check("feature_rows", inputs.get("rotation_matchup_rows") == 1230)
    check("ready_games", inputs.get("rotation_feature_ready_games") == 1075)
    check("matchup_digest", inputs.get("rotation_matchup_csv_sha256") == "sha256:3e8ef30f3a9801fda92fc95a490228b73fa53603093c914207e884a933b2de02")
    check("prediction_artifact", inputs.get("frozen_prediction_artifact_id") == 8592208938)
    check("prediction_artifact_digest", inputs.get("frozen_prediction_artifact_digest") == "sha256:3f509beac4a897a86baf3bdfceb0d37100e65b334c60162ef98effee5064f518")
    check("prediction_digest", inputs.get("frozen_prediction_csv_sha256") == "sha256:c3764faf6eb3703374b12a5d8668c6ef889cd8f54070a2c6cf135b55559ca725")
    check("private_join_digest", inputs.get("private_model_market_join_csv_sha256") == "sha256:fbd5b0133cd0ad58f3fe4dada53e79b0fd2ea6021d8179f648f727c76a96735b")
    check("private_odds_digest", inputs.get("private_odds_main_csv_sha256") == "sha256:8ce1f53a39f9dc3a0adf65f3f91ba9eb6024fccfabd5282a50eea00a1292a0b3")
    check("private_bundle_digest", inputs.get("private_odds_bundle_sha256") == "sha256:346e69f9f4ad559422d55add1b0d2b5c1a2dc38e22ef4575e1fc8ec87bf0df43")
    check("no_public_inputs", inputs.get("public_row_level_inputs_allowed") is False)

    join = payload.get("join_policy", {})
    check("exact_game_id", join.get("identity_key") == "exact governed game_id")
    check("no_identity_fallback", join.get("fallback_identity_allowed") is False)
    check("no_fuzzy", join.get("fuzzy_identity_allowed") is False)
    check("no_nearest_name", join.get("nearest_name_guessing_allowed") is False)
    check("no_duplicate_join", join.get("duplicate_join_keys_allowed") == 0)
    check("no_missing_impute", join.get("missing_feature_side_imputation") == "PROHIBITED")
    check("frozen_market_selection", "PR #180" in join.get("market_selection_rule", ""))
    check("no_provider_observed_at", join.get("provider_origin_observed_at_verified") is False)
    check("strict_t60_false", join.get("strict_t60_qualified") is False)

    populations = payload.get("populations", {})
    model_population = populations.get("primary_model_residual_population", {})
    market_population = populations.get("primary_market_residual_population", {})
    check("model_expected_1075", model_population.get("expected_rows") == 1075)
    check("model_min_1000", model_population.get("minimum_rows") == 1000)
    check("one_row_game", model_population.get("one_row_per_game") is True)
    check("market_min_200", market_population.get("minimum_rows") == 200)
    check("market_diagnostic_only", market_population.get("timing_semantics") == "PRIVATE_ARCHIVE_BATCH_RELATIVE_DIAGNOSTIC_ONLY")
    sensitivity = populations.get("market_sensitivity_populations", [])
    check("sensitivity_bands", [item.get("maximum_nominal_t60_batch_error_minutes") for item in sensitivity] == [15, 30, 60])
    check("sensitivity_minimums", [item.get("minimum_rows") for item in sensitivity] == [300, 400, 450])
    check("no_outcome_population_selection", populations.get("population_selection_after_outcome_review_allowed") is False)

    residuals = payload.get("residual_definitions", {})
    check("model_residual_direction", residuals.get("model_home_residual") == "actual_home_win - model_home_probability")
    check("market_residual_direction", residuals.get("market_home_residual") == "actual_home_win - market_home_probability_no_vig")
    check("positive_meaning", "better" in residuals.get("positive_signed_residual_meaning", ""))
    check("negative_meaning", "worse" in residuals.get("negative_signed_residual_meaning", ""))
    check("positive_market_error_meaning", "model is worse" in residuals.get("positive_model_minus_market_error_meaning", ""))

    feature_scope = payload.get("feature_scope", {})
    check("difference_only_primary", feature_scope.get("primary_features") == "home-minus-away matchup differences only")
    check("feature_count_12", feature_scope.get("primary_feature_count") == 12)
    check("exact_feature_list", feature_scope.get("features") == EXPECTED_FEATURES)
    check("home_away_secondary", feature_scope.get("raw_home_and_away_values") == "secondary descriptive only")
    check("no_outcome_transform", feature_scope.get("feature_transformation_after_outcome_review_allowed") is False)
    check("no_outcome_feature_selection", feature_scope.get("outcome_based_feature_selection_allowed") is False)

    stress = payload.get("predeclared_rotation_stress_index", {})
    check("stress_audit_only", stress.get("audit_only") is True)
    check("stress_outcome_free_scaling", "outcome-free" in stress.get("scaling", ""))
    components = stress.get("components", [])
    check("stress_components_7", len(components) == 7)
    check("stress_component_names_unique", len({item.get("feature") for item in components}) == 7)
    check("stress_component_signs", all(item.get("sign") in {-1, 1} for item in components))
    check("stress_min_components", stress.get("minimum_components") == 5)
    check("stress_gap_absolute", "absolute" in stress.get("stress_gap_magnitude", ""))

    hypotheses = payload.get("primary_hypotheses", {})
    h1 = hypotheses.get("model_signed_residual", {})
    h2 = hypotheses.get("market_relative_error", {})
    check("h1_spearman", "Spearman" in h1.get("test", ""))
    check("h1_negative", h1.get("predeclared_direction") == "negative")
    check("h2_spearman", "Spearman" in h2.get("test", ""))
    check("h2_positive", h2.get("predeclared_direction") == "positive")

    secondary = payload.get("secondary_tests", {})
    check("secondary_12_features", "12" in secondary.get("individual_feature_signed_residual", ""))
    check("secondary_market_12", "12" in secondary.get("individual_feature_market_relative_error", ""))
    check("quartile_contrast", "quartile" in secondary.get("quartile_contrast", ""))
    check("brier_secondary", "Brier" in secondary.get("brier_sensitivity", ""))
    check("bh_fdr", "Benjamini-Hochberg" in secondary.get("multiple_testing", "") and "0.10" in secondary.get("multiple_testing", ""))
    check("secondary_diagnostic_only", secondary.get("secondary_results_are_diagnostic_only") is True)

    robustness = payload.get("uncertainty_and_robustness", {})
    check("bootstrap_5000", robustness.get("bootstrap_resamples") == 5000)
    check("seed_fixed", robustness.get("bootstrap_seed") == 20260725)
    check("game_bootstrap", robustness.get("bootstrap_unit") == "independent game")
    check("ci95", robustness.get("confidence_interval") == 0.95)
    check("chronological_split", "first and second half" in robustness.get("chronological_split", ""))
    check("split_sign_consistency", robustness.get("primary_signal_requires_split_sign_consistency") is True)
    check("four_months", "4 of the 6" in robustness.get("monthly_direction_check", ""))
    check("no_threshold_tuning", robustness.get("post_hoc_threshold_tuning_allowed") is False)
    check("no_best_band", robustness.get("band_selection_by_best_result_allowed") is False)

    gates = payload.get("validity_gates", {})
    check("gate_model_rows", gates.get("exact_feature_ready_model_rows_minimum") == 1000)
    check("gate_market_rows", gates.get("primary_market_rows_minimum") == 200)
    for key in (
        "source_time_violations",
        "identity_ambiguities",
        "duplicate_game_keys",
        "non_finite_required_values",
        "public_private_boundary_violations",
        "model_fit_calls",
        "model_refit_calls",
        "calibration_changes",
        "market_features_added_to_model",
    ):
        check(f"zero_gate_{key}", gates.get(key) == 0)

    decision = payload.get("decision_policy", {})
    check("decision_invalid", decision.get("invalid") == "AUDIT_INVALID_OR_UNDERPOWERED")
    check("decision_no_signal", decision.get("no_signal") == "VALID_NO_PRIOR_ONLY_ROTATION_RESIDUAL_SIGNAL")
    check("decision_inconclusive", decision.get("inconclusive") == "VALID_INCONCLUSIVE_PRIOR_ONLY_ROTATION_RESIDUAL_DIAGNOSTIC")
    check("decision_signal", decision.get("diagnostic_signal") == "VALID_DIAGNOSTIC_PRIOR_ONLY_ROTATION_RESIDUAL_SIGNAL")
    check("signal_requirements_5", len(decision.get("diagnostic_signal_requires", [])) == 5)
    check("no_training_from_signal", decision.get("passing_signal_does_not_authorize_training") is True)
    check("no_selection_from_signal", decision.get("passing_signal_does_not_authorize_feature_selection") is True)
    check("no_promotion_from_signal", decision.get("passing_signal_does_not_authorize_model_promotion") is True)

    public = payload.get("public_output_policy", {})
    check("aggregate_only", public.get("aggregate_only") is True)
    check("public_game_rows_zero", public.get("public_game_level_rows") == 0)
    check("public_player_rows_zero", public.get("public_player_rows") == 0)
    check("public_price_rows_zero", public.get("public_price_rows") == 0)
    check("raw_artifacts_zero", public.get("raw_private_artifacts_committed") == 0)
    check("allowed_outputs_aggregate", len(public.get("allowed_public_outputs", [])) == 5)

    check("non_goals_10", len(payload.get("explicit_non_goals", [])) == 10)
    qualification = payload.get("qualification", {})
    check("design_true", qualification.get("design_predeclared") is True)
    for key in (
        "real_residual_audit_executed",
        "model_training_authorized",
        "model_promotion_authorized",
        "strict_t60_qualified",
        "formal_market_backtest_allowed",
        "betting_edge_claim_allowed",
    ):
        check(f"qualification_{key}_false", qualification.get(key) is False)
    check("formal_stake_zero", qualification.get("formal_stake") == 0)
    check("next_mainline", payload.get("next_unique_mainline_after_design_validation") == NEXT)

    for text, name in (
        (PREDECLARED_STATE, "doc_state"),
        ("source_game_date_et", "doc_pit_context"),
        ("PRIVATE_ARCHIVE_BATCH_RELATIVE_DIAGNOSTIC_ONLY", "doc_market_boundary"),
        ("Spearman(signed rotation stress", "doc_h1"),
        ("Spearman(rotation stress gap magnitude", "doc_h2"),
        ("Benjamini–Hochberg", "doc_fdr"),
        ("Formal Stake: 0", "doc_stake"),
        (NEXT, "doc_next"),
    ):
        check(name, text in document)

    failed = sorted(name for name, passed in checks.items() if not passed)
    output = {
        "schema_version": 1,
        "formal_state": FORMAL_STATE if not failed else "TRAINING_FREE_PRIOR_ONLY_ROTATION_RESIDUAL_AUDIT_2025_26_V1_DESIGN_INVALID",
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "checks_failed": len(failed),
        "failed_checks": failed,
        "real_residual_audit_executed": False,
        "model_training_authorized": False,
        "model_promotion_authorized": False,
        "strict_t60_qualified": False,
        "formal_market_backtest_allowed": False,
        "betting_edge_claim_allowed": False,
        "formal_stake": 0,
        "next_unique_mainline": NEXT,
    }
    out = Path("validation-output/training-free-prior-only-rotation-residual-audit-2025-26-v1.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
