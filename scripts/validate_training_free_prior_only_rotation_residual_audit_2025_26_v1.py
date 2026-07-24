#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

SPEC = Path("data/research/training-free-prior-only-rotation-residual-audit-2025-26-v1.json")
DOC = Path("docs/training-free-prior-only-rotation-residual-audit-2025-26-v1.md")
OUT = Path("validation-output/prior-only-player-rotation-residual-audit-2025-26-v1.json")
PREDECLARED = "TRAINING_FREE_PRIOR_ONLY_ROTATION_RESIDUAL_AUDIT_2025_26_V1_PREDECLARED"
VALID = "TRAINING_FREE_PRIOR_ONLY_ROTATION_RESIDUAL_AUDIT_2025_26_V1_DESIGN_VALID"
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
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")
    checks: dict[str, bool] = {}

    def check(name: str, value: bool) -> None:
        checks[name] = bool(value)

    binding = spec["binding_history"]
    inputs = spec["bound_private_inputs"]
    join = spec["join_policy"]
    populations = spec["populations"]
    residuals = spec["residual_definitions"]
    features = spec["feature_scope"]
    stress = spec["predeclared_rotation_stress_index"]
    hypotheses = spec["primary_hypotheses"]
    secondary = spec["secondary_tests"]
    robustness = spec["uncertainty_and_robustness"]
    gates = spec["validity_gates"]
    decision = spec["decision_policy"]
    public = spec["public_output_policy"]
    qualification = spec["qualification"]

    check("schema", spec["schema_version"] == "training-free-prior-only-rotation-residual-audit-2025-26-v1")
    check("predeclared_state", spec["formal_state"] == PREDECLARED)
    check("base_main", binding["base_main"] == "85821f7df6babce207dc5c39a24fbdcedd5ad165")
    check("binding_pr187", binding["binding_feature_pr"] == 187)
    check("binding_feature_result", binding["binding_feature_result"] == "PRIOR_ONLY_PLAYER_ROTATION_STATE_FEATURES_2025_26_RESULT_VALID")
    check("frozen_baseline_lock", binding["binding_prior_decision"] == "PRESERVE_FROZEN_BASELINE_AND_MARKET_BACKTEST_LOCK")
    check("design_mainline", binding["current_unique_mainline"] == "PREDECLARE_TRAINING_FREE_PRIOR_ONLY_ROTATION_RESIDUAL_AUDIT_2025_26_V1")

    expected_inputs = {
        "rotation_feature_artifact_id": 8603761824,
        "rotation_feature_artifact_digest": "sha256:e02cd15e9b3aa1d58d3cbee1f27f1caea461d7e2f8ec701389e6e5f969ba440a",
        "rotation_feature_head": "b1de9fa8616caff42f251d2db253e8ed2f80e42a",
        "rotation_matchup_rows": 1230,
        "rotation_feature_ready_games": 1075,
        "rotation_matchup_csv_sha256": "sha256:3e8ef30f3a9801fda92fc95a490228b73fa53603093c914207e884a933b2de02",
        "frozen_prediction_artifact_id": 8592208938,
        "frozen_prediction_artifact_digest": "sha256:3f509beac4a897a86baf3bdfceb0d37100e65b334c60162ef98effee5064f518",
        "frozen_prediction_csv_sha256": "sha256:c3764faf6eb3703374b12a5d8668c6ef889cd8f54070a2c6cf135b55559ca725",
        "private_model_market_join_csv_sha256": "sha256:fbd5b0133cd0ad58f3fe4dada53e79b0fd2ea6021d8179f648f727c76a96735b",
        "private_odds_main_csv_sha256": "sha256:8ce1f53a39f9dc3a0adf65f3f91ba9eb6024fccfabd5282a50eea00a1292a0b3",
        "private_odds_bundle_sha256": "sha256:346e69f9f4ad559422d55add1b0d2b5c1a2dc38e22ef4575e1fc8ec87bf0df43",
    }
    for key, expected in expected_inputs.items():
        check(f"bound_{key}", inputs[key] == expected)
    check("private_inputs_not_public", inputs["public_row_level_inputs_allowed"] is False)

    check("exact_game_id_join", join["identity_key"] == "exact governed game_id")
    check("no_fallback_identity", join["fallback_identity_allowed"] is False)
    check("no_fuzzy_identity", join["fuzzy_identity_allowed"] is False)
    check("no_nearest_name", join["nearest_name_guessing_allowed"] is False)
    check("duplicate_join_keys_zero", join["duplicate_join_keys_allowed"] == 0)
    check("missing_side_imputation_prohibited", join["missing_feature_side_imputation"] == "PROHIBITED")
    check("market_rule_frozen_to_pr180", "PR #180" in join["market_selection_rule"])
    check("market_no_vig", join["market_probability"] == "proportional_no_vig")
    check("provider_observed_at_unverified", join["provider_origin_observed_at_verified"] is False)
    check("strict_t60_unqualified", join["strict_t60_qualified"] is False)

    model_population = populations["primary_model_residual_population"]
    market_population = populations["primary_market_residual_population"]
    check("model_population_expected_1075", model_population["expected_rows"] == 1075)
    check("model_population_min_1000", model_population["minimum_rows"] == 1000)
    check("one_row_per_game", model_population["one_row_per_game"] is True)
    check("market_population_min_200", market_population["minimum_rows"] == 200)
    check("market_population_diagnostic_only", market_population["timing_semantics"] == "PRIVATE_ARCHIVE_BATCH_RELATIVE_DIAGNOSTIC_ONLY")
    sensitivity = populations["market_sensitivity_populations"]
    check("sensitivity_bands", [row["maximum_nominal_t60_batch_error_minutes"] for row in sensitivity] == [15, 30, 60])
    check("sensitivity_minimums", [row["minimum_rows"] for row in sensitivity] == [300, 400, 450])
    check("no_outcome_population_selection", populations["population_selection_after_outcome_review_allowed"] is False)

    check("model_residual_formula", residuals["model_home_residual"] == "actual_home_win - model_home_probability")
    check("market_residual_formula", residuals["market_home_residual"] == "actual_home_win - market_home_probability_no_vig")
    check("model_minus_market_logloss_defined", "binary_log_loss" in residuals["model_minus_market_log_loss_row"])
    check("model_minus_market_brier_defined", "squared_error" in residuals["model_minus_market_brier_row"])

    check("primary_features_differences_only", features["primary_features"] == "home-minus-away matchup differences only")
    check("feature_count_12", features["primary_feature_count"] == 12)
    check("feature_list_frozen", features["features"] == EXPECTED_FEATURES)
    check("raw_values_secondary", features["raw_home_and_away_values"] == "secondary descriptive only")
    check("no_post_outcome_transform", features["feature_transformation_after_outcome_review_allowed"] is False)
    check("no_outcome_feature_selection", features["outcome_based_feature_selection_allowed"] is False)

    components = stress["components"]
    check("stress_audit_only", stress["audit_only"] is True)
    check("stress_scaling_outcome_free", stress["scaling"].startswith("outcome-free"))
    check("stress_components_7", len(components) == 7)
    check("stress_components_unique", len({row["feature"] for row in components}) == 7)
    check("stress_component_signs", all(row["sign"] in {-1, 1} for row in components))
    check("stress_minimum_components_5", stress["minimum_components"] == 5)

    h1 = hypotheses["model_signed_residual"]
    h2 = hypotheses["market_relative_error"]
    check("h1_spearman", h1["test"].startswith("Spearman"))
    check("h1_direction_negative", h1["predeclared_direction"] == "negative")
    check("h2_spearman", h2["test"].startswith("Spearman"))
    check("h2_direction_positive", h2["predeclared_direction"] == "positive")

    check("secondary_fixed_12_model", "12 fixed" in secondary["individual_feature_signed_residual"])
    check("secondary_fixed_12_market", "12 fixed" in secondary["individual_feature_market_relative_error"])
    check("quartile_secondary", "quartile" in secondary["quartile_contrast"])
    check("brier_secondary", "brier" in secondary["brier_sensitivity"].lower())
    check("bh_fdr_q10", "Benjamini-Hochberg" in secondary["multiple_testing"] and "0.10" in secondary["multiple_testing"])
    check("secondary_diagnostic_only", secondary["secondary_results_are_diagnostic_only"] is True)

    check("bootstrap_5000", robustness["bootstrap_resamples"] == 5000)
    check("bootstrap_seed", robustness["bootstrap_seed"] == 20260725)
    check("bootstrap_independent_game", robustness["bootstrap_unit"] == "independent game")
    check("ci95", robustness["confidence_interval"] == 0.95)
    check("chronological_split_frozen", "first and second half" in robustness["chronological_split"])
    check("split_sign_required", robustness["primary_signal_requires_split_sign_consistency"] is True)
    check("monthly_four_of_six", "4 of the 6" in robustness["monthly_direction_check"])
    check("no_posthoc_threshold", robustness["post_hoc_threshold_tuning_allowed"] is False)
    check("no_best_band_selection", robustness["band_selection_by_best_result_allowed"] is False)

    zero_gate_keys = [
        "source_time_violations",
        "identity_ambiguities",
        "duplicate_game_keys",
        "non_finite_required_values",
        "public_private_boundary_violations",
        "model_fit_calls",
        "model_refit_calls",
        "calibration_changes",
        "market_features_added_to_model",
    ]
    check("model_rows_gate", gates["exact_feature_ready_model_rows_minimum"] == 1000)
    check("market_rows_gate", gates["primary_market_rows_minimum"] == 200)
    for key in zero_gate_keys:
        check(f"zero_gate_{key}", gates[key] == 0)

    check("decision_states_frozen", {
        decision["invalid"],
        decision["no_signal"],
        decision["inconclusive"],
        decision["diagnostic_signal"],
    } == {
        "AUDIT_INVALID_OR_UNDERPOWERED",
        "VALID_NO_PRIOR_ONLY_ROTATION_RESIDUAL_SIGNAL",
        "VALID_INCONCLUSIVE_PRIOR_ONLY_ROTATION_RESIDUAL_DIAGNOSTIC",
        "VALID_DIAGNOSTIC_PRIOR_ONLY_ROTATION_RESIDUAL_SIGNAL",
    })
    check("signal_requirements_5", len(decision["diagnostic_signal_requires"]) == 5)
    check("signal_no_training", decision["passing_signal_does_not_authorize_training"] is True)
    check("signal_no_feature_selection", decision["passing_signal_does_not_authorize_feature_selection"] is True)
    check("signal_no_promotion", decision["passing_signal_does_not_authorize_model_promotion"] is True)

    check("public_aggregate_only", public["aggregate_only"] is True)
    check("public_game_rows_zero", public["public_game_level_rows"] == 0)
    check("public_player_rows_zero", public["public_player_rows"] == 0)
    check("public_price_rows_zero", public["public_price_rows"] == 0)
    check("raw_private_artifacts_zero", public["raw_private_artifacts_committed"] == 0)

    check("non_goals_10", len(spec["explicit_non_goals"]) == 10)
    check("design_predeclared", qualification["design_predeclared"] is True)
    for key in [
        "real_residual_audit_executed",
        "model_training_authorized",
        "model_promotion_authorized",
        "strict_t60_qualified",
        "formal_market_backtest_allowed",
        "betting_edge_claim_allowed",
    ]:
        check(f"locked_{key}", qualification[key] is False)
    check("stake_zero", qualification["formal_stake"] == 0)
    check("next_mainline", spec["next_unique_mainline_after_design_validation"] == NEXT)

    for marker in [
        PREDECLARED,
        "source_game_date_et < target_game_date_et",
        "PRIVATE_ARCHIVE_BATCH_RELATIVE_DIAGNOSTIC_ONLY",
        "Spearman(signed rotation stress, model_home_residual) < 0",
        "Spearman(rotation stress gap magnitude,",
        "Benjamini–Hochberg",
        "Formal Stake: 0",
        NEXT,
    ]:
        check(f"doc_marker_{marker[:24]}", marker in doc)

    failed = sorted(name for name, passed in checks.items() if not passed)
    output = {
        "schema_version": 1,
        "formal_state": VALID if not failed else "TRAINING_FREE_PRIOR_ONLY_ROTATION_RESIDUAL_AUDIT_2025_26_V1_DESIGN_INVALID",
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
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
