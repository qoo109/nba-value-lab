#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

SPEC = Path("data/research/training-free-prior-only-rotation-residual-audit-2025-26-v1-column-binding-amendment.json")
DOC = Path("docs/training-free-prior-only-rotation-residual-audit-2025-26-v1-column-binding-amendment.md")
OUT = Path("validation-output/training-free-prior-only-rotation-residual-audit-column-binding-v1.json")
VALID = "TRAINING_FREE_PRIOR_ONLY_ROTATION_RESIDUAL_AUDIT_2025_26_V1_COLUMN_BINDING_AMENDMENT_VALID"
NEXT = "IMPLEMENT_AND_EXECUTE_TRAINING_FREE_PRIOR_ONLY_ROTATION_RESIDUAL_AUDIT_2025_26_V1_USING_EXACT_COLUMN_BINDING"

EXPECTED_MAPPING = {
    "rotation_players_prior_5_diff": "diff_rotation_players_prior_5",
    "top5_minutes_share_prior_5_diff": "diff_top5_minutes_share_prior_5",
    "top8_minutes_share_prior_5_diff": "diff_top8_minutes_share_prior_5",
    "top8_minutes_share_prior_10_diff": "diff_top8_minutes_share_prior_10",
    "rotation_entropy_prior_5_diff": "diff_rotation_entropy_prior_5",
    "rotation_entropy_prior_10_diff": "diff_rotation_entropy_prior_10",
    "top8_set_continuity_prior_5_diff": "diff_top8_set_continuity_prior_5",
    "starter_set_continuity_prior_5_diff": "diff_starter_set_continuity_prior_5",
    "minutes_allocation_volatility_prior_5_diff": "diff_minutes_allocation_volatility_prior_5",
    "role_change_magnitude_prior_3_vs_10_diff": "diff_role_change_magnitude_prior_3_vs_10",
    "recent_return_players_count_diff": "diff_recent_return_players_count",
    "new_team_rotation_players_prior_5_diff": "diff_new_team_rotation_players_prior_5",
}

EXPECTED_IDENTITY = {
    "game_id": "target_game_id",
    "game_date_et": "target_game_date_et",
    "home_team": "home_team_abbr",
    "away_team": "away_team_abbr",
    "feature_ready_game": "feature_ready_game",
}

EXPECTED_STRESS = {
    "rotation_players_prior_5_diff": ("diff_rotation_players_prior_5", 1),
    "top8_set_continuity_prior_5_diff": ("diff_top8_set_continuity_prior_5", -1),
    "starter_set_continuity_prior_5_diff": ("diff_starter_set_continuity_prior_5", -1),
    "minutes_allocation_volatility_prior_5_diff": ("diff_minutes_allocation_volatility_prior_5", 1),
    "role_change_magnitude_prior_3_vs_10_diff": ("diff_role_change_magnitude_prior_3_vs_10", 1),
    "recent_return_players_count_diff": ("diff_recent_return_players_count", 1),
    "new_team_rotation_players_prior_5_diff": ("diff_new_team_rotation_players_prior_5", 1),
}


def main() -> int:
    payload = json.loads(SPEC.read_text(encoding="utf-8"))
    document = DOC.read_text(encoding="utf-8")
    checks: dict[str, bool] = {}

    def check(name: str, value: bool) -> None:
        checks[name] = bool(value)

    check("schema", payload["schema_version"] == "training-free-prior-only-rotation-residual-audit-2025-26-v1-column-binding-amendment")
    check("state", payload["formal_state"] == "TRAINING_FREE_PRIOR_ONLY_ROTATION_RESIDUAL_AUDIT_2025_26_V1_COLUMN_BINDING_AMENDMENT_PREDECLARED")

    binding = payload["binding_history"]
    check("base_main", binding["base_main"] == "ca7eedc794f5dbba2a28d96cfd98386125a1d539")
    check("design_pr", binding["binding_design_pr"] == 188)
    check("design_state", binding["binding_design_state"] == "TRAINING_FREE_PRIOR_ONLY_ROTATION_RESIDUAL_AUDIT_2025_26_V1_DESIGN_VALID")
    check("feature_pr", binding["binding_feature_pr"] == 187)
    check("feature_artifact", binding["feature_artifact_id"] == 8603761824)
    check("feature_artifact_digest", binding["feature_artifact_digest"] == "sha256:e02cd15e9b3aa1d58d3cbee1f27f1caea461d7e2f8ec701389e6e5f969ba440a")
    check("matchup_digest", binding["matchup_csv_sha256"] == "sha256:3e8ef30f3a9801fda92fc95a490228b73fa53603093c914207e884a933b2de02")
    check("header_digest", binding["matchup_header_sha256"] == "sha256:81bbe7ab22a5e7892207b4eb765a084dc88c059407664532672ea93d9f51146d")

    status = payload["execution_status_at_amendment"]
    for key in (
        "private_residual_join_executed",
        "residual_statistics_computed",
        "outcomes_inspected_for_amendment",
        "market_results_inspected_for_amendment",
        "feature_set_changed",
        "hypotheses_changed",
        "population_gates_changed",
        "decision_policy_changed",
    ):
        check(f"status_{key}_false", status[key] is False)

    mapping = payload["canonical_to_physical_column_mapping"]
    check("exact_mapping", mapping == EXPECTED_MAPPING)
    check("mapping_count", len(mapping) == 12)
    check("canonical_unique", len(set(mapping)) == 12)
    check("physical_unique", len(set(mapping.values())) == 12)
    check("all_physical_diff_prefix", all(value.startswith("diff_") for value in mapping.values()))
    check("identity_mapping", payload["identity_and_readiness_columns"] == EXPECTED_IDENTITY)

    stress_rows = payload["stress_index_physical_components"]
    stress_map = {
        row["canonical"]: (row["physical"], row["sign"])
        for row in stress_rows
    }
    check("stress_count", len(stress_rows) == 7)
    check("stress_mapping", stress_map == EXPECTED_STRESS)
    check("stress_unique_physical", len({row["physical"] for row in stress_rows}) == 7)

    rules = payload["mapping_rules"]
    check("one_to_one", rules["mapping_cardinality"] == "ONE_TO_ONE")
    check("canonical_count_12", rules["canonical_feature_count"] == 12)
    check("physical_count_12", rules["physical_feature_count"] == 12)
    for key in (
        "duplicate_canonical_names_allowed",
        "duplicate_physical_columns_allowed",
        "unmapped_primary_features_allowed",
        "extra_primary_physical_columns_allowed",
    ):
        check(f"rule_{key}_zero", rules[key] == 0)
    for key in (
        "runtime_column_guessing_allowed",
        "prefix_or_suffix_inference_allowed",
        "case_insensitive_fallback_allowed",
        "fuzzy_column_matching_allowed",
    ):
        check(f"rule_{key}_false", rules[key] is False)

    design = payload["preserved_design"]
    check("expected_rows_1075", design["primary_model_population_expected_rows"] == 1075)
    check("minimum_rows_1000", design["primary_model_population_minimum_rows"] == 1000)
    check("market_minimum_200", design["primary_market_population_minimum_rows"] == 200)
    check("bands_15_30_60", design["market_sensitivity_bands_minutes"] == [15, 30, 60])
    check("bootstrap_5000", design["bootstrap_resamples"] == 5000)
    check("seed_20260725", design["bootstrap_seed"] == 20260725)
    check("h1_negative", design["primary_h1_direction"] == "negative")
    check("h2_positive", design["primary_h2_direction"] == "positive")
    check("bh_q10", design["multiple_testing"] == "Benjamini-Hochberg q <= 0.10")
    check("aggregate_only", design["public_output"] == "AGGREGATE_ONLY")

    locks = payload["preserved_locks"]
    for key in (
        "model_training_authorized",
        "model_promotion_authorized",
        "strict_t60_qualified",
        "formal_market_backtest_allowed",
        "betting_edge_claim_allowed",
    ):
        check(f"lock_{key}_false", locks[key] is False)
    check("stake_zero", locks["formal_stake"] == 0)
    check("next_mainline", payload["next_unique_mainline_after_amendment_validation"] == NEXT)

    for marker in (
        "COLUMN_BINDING_AMENDMENT_PREDECLARED",
        "diff_rotation_players_prior_5",
        "diff_new_team_rotation_players_prior_5",
        "Mapping cardinality: ONE_TO_ONE",
        "Private residual join executed: false",
        "Formal Stake: 0",
        NEXT,
    ):
        check(f"doc_{marker[:24]}", marker in document)

    failed = sorted(name for name, passed in checks.items() if not passed)
    output = {
        "schema_version": 1,
        "formal_state": VALID if not failed else "TRAINING_FREE_PRIOR_ONLY_ROTATION_RESIDUAL_AUDIT_2025_26_V1_COLUMN_BINDING_AMENDMENT_INVALID",
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "checks_failed": len(failed),
        "failed_checks": failed,
        "private_residual_join_executed": False,
        "residual_statistics_computed": False,
        "model_training_authorized": False,
        "model_promotion_authorized": False,
        "strict_t60_qualified": False,
        "formal_market_backtest_allowed": False,
        "formal_stake": 0,
        "next_unique_mainline": NEXT,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
