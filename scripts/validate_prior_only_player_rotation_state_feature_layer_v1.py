#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

SPEC = Path("data/research/prior-only-player-rotation-state-feature-layer-v1.json")
DOC = Path("docs/prior-only-player-rotation-state-feature-layer-v1.md")
FORMAL_STATE = "PRIOR_ONLY_PLAYER_ROTATION_STATE_FEATURE_LAYER_V1_DESIGN_VALID"


def main() -> int:
    payload = json.loads(SPEC.read_text(encoding="utf-8"))
    document = DOC.read_text(encoding="utf-8")
    tests = 0

    def check(condition: bool, message: str) -> None:
        nonlocal tests
        if not condition:
            raise AssertionError(message)
        tests += 1

    check(payload["schema_version"] == "prior-only-player-rotation-state-feature-layer-v1", "schema")
    check(payload["formal_state"] == "PRIOR_ONLY_PLAYER_ROTATION_STATE_FEATURE_LAYER_V1_PREDECLARED", "state")
    check(payload["source_of_truth"]["base_main"] == "d572632a798e2453ea577318af34f811847c8f28", "base main")
    check(payload["source_of_truth"]["binding_prior_pr"] == 181, "prior PR")
    check(payload["source_of_truth"]["binding_prior_decision"] == "PRESERVE_FROZEN_BASELINE_AND_MARKET_BACKTEST_LOCK", "prior decision")
    check(payload["source_of_truth"]["binding_prior_next"] == "PREDECLARE_PRIOR_ONLY_PLAYER_ROTATION_STATE_FEATURE_LAYER_V1", "prior next")

    scope = payload["primary_scope"]
    check(scope["target_season"] == "2025-26", "season")
    check(scope["target_games"] == 1230, "target games")
    check(scope["target_team_rows"] == 2460, "team rows")
    for key in (
        "market_data_allowed_as_feature",
        "target_game_boxscore_allowed",
        "target_game_starters_allowed",
        "target_game_minutes_allowed",
        "target_game_participation_allowed",
        "target_game_outcome_allowed",
    ):
        check(scope[key] is False, key)

    pit = payload["point_in_time_policy"]
    check(pit["required_order"] == "source_game_end_time_utc < target_analysis_cutoff_utc < target_tipoff_utc", "PIT order")
    check(pit["primary_cutoff"] == "target scheduled tipoff UTC", "cutoff")
    check("strictly earlier" in pit["same_day_date_only_fallback"], "date fallback")
    check(pit["unknown_source_end_time"] == "exclude and flag", "unknown time")
    check(pit["source_time_violations_allowed"] == 0, "PIT violations")

    source = payload["source_qualification"]
    check(source["player_identity"] == "deterministic official person ID only", "identity")
    check(source["fuzzy_identity_allowed"] is False, "no fuzzy")
    check(source["nearest_name_guessing_allowed"] is False, "no guessing")
    check(source["public_raw_player_rows"] == 0, "no public player rows")
    check(len(source["source_requirements"]) >= 9, "provenance requirements")
    check("do not bypass" in source["http_403_or_access_control"], "no bypass")

    season = payload["season_boundary_policy"]
    check(season["primary_features"] == "current-season completed games only", "current season")
    check(season["minimum_games_for_primary_rotation_features"] == 3, "minimum games")
    check(season["prior_season_carry_in_primary"] is False, "no primary carry")
    check("null" in season["early_season_missingness"], "early missing")

    player_names = {item["name"] for item in payload["player_state_features"]}
    check(len(player_names) == 10, "player feature count")
    for required in (
        "minutes_avg_prior_3",
        "minutes_avg_prior_5",
        "minutes_avg_prior_10",
        "minutes_trend_prior_3_vs_10",
        "start_rate_prior_5",
        "start_rate_prior_10",
        "appearance_rate_prior_10",
        "days_since_last_appearance",
        "recent_return_state",
        "role_rank_prior_5",
    ):
        check(required in player_names, required)

    team_names = {item["name"] for item in payload["team_state_features"]}
    check(len(team_names) == 12, "team feature count")
    for required in (
        "rotation_players_prior_5",
        "top5_minutes_share_prior_5",
        "top8_minutes_share_prior_5",
        "top8_minutes_share_prior_10",
        "rotation_entropy_prior_5",
        "rotation_entropy_prior_10",
        "top8_set_continuity_prior_5",
        "starter_set_continuity_prior_5",
        "minutes_allocation_volatility_prior_5",
        "role_change_magnitude_prior_3_vs_10",
        "recent_return_players_count",
        "new_team_rotation_players_prior_5",
    ):
        check(required in team_names, required)

    matchup = payload["matchup_features"]
    check(matchup["rule"] == "home value minus away value", "matchup rule")
    check(matchup["include_team_values"] is True, "team values")
    check(matchup["include_differences"] is True, "diffs")
    check("null" in matchup["missing_side"], "missing side")

    starter = payload["starter_proxy_policy"]
    check(starter["official_flag_primary"] is True, "official starter")
    check(starter["minutes_based_inference_primary"] is False, "no inferred primary")
    check(starter["minutes_based_inference_optional_name"] == "starter_proxy_by_prior_minutes_v1", "proxy name")
    check(starter["proxy_must_be_separate"] is True, "proxy separate")
    check(starter["proxy_cannot_be_described_as_confirmed_lineup"] is True, "not confirmed")

    trade = payload["trade_and_roster_policy"]
    check(trade["minutes_windows_are_team_specific"] is True, "team specific")
    check(trade["prior_minutes_from_other_team_in_primary_role_state"] is False, "no other team")
    check("unknown" in trade["roster_absence_without_source_row"], "unknown absence")
    check("never target-game" in trade["player_removed_from_rotation"], "no target removal")

    missing = payload["missingness"]
    check("null" in missing["missing_minutes"], "minutes null")
    check("null" in missing["missing_starter_flag"], "starter null")
    check("null" in missing["insufficient_history"], "history null")
    check("never converted" in missing["not_yet_observed"], "not observed")

    qa = payload["qa_gates"]
    check(qa["unique_target_team_rows"] == 2460, "QA team rows")
    check(qa["exactly_two_team_rows_per_game"] is True, "two rows")
    for key in (
        "duplicate_target_game_team_keys",
        "target_game_source_rows_used",
        "same_or_future_source_rows_used",
        "fuzzy_identity_rows",
        "non_finite_feature_values",
        "negative_minutes",
        "public_player_names",
        "public_game_level_feature_rows",
    ):
        check(qa[key] == 0, key)
    for key in ("bounded_share_features", "bounded_jaccard_features", "bounded_entropy_features"):
        check(qa[key] == "0 to 1", key)
    check("overtime" in qa["source_minutes_team_total_check"], "OT validation")

    diagnostic = payload["diagnostic_plan"]
    check("coverage" in diagnostic["phase_1"], "phase 1")
    check("residual" in diagnostic["phase_2"], "phase 2")
    check("walk-forward" in diagnostic["phase_3"], "phase 3")
    check("<=5 minutes" in diagnostic["primary_residual_population"], "primary residual")
    check(diagnostic["secondary_sensitivity_bands"] == [15, 30, 60], "secondary bands")
    check(diagnostic["outcome_based_feature_selection_allowed"] is False, "no outcome selection")
    check(diagnostic["post_hoc_threshold_tuning_allowed"] is False, "no threshold tuning")
    check(diagnostic["model_retraining_in_this_design"] is False, "no retraining")

    activation = payload["activation_gates"]
    check(activation["minimum_feature_ready_games"] == 1000, "minimum ready")
    check(activation["minimum_months_covered"] == 5, "months")
    check(activation["minimum_teams_with_feature_ready_rows"] == 30, "teams")
    check(activation["source_time_violations"] == 0, "activation PIT")
    check(activation["identity_ambiguities"] == 0, "ambiguities")
    check(activation["feature_ready_rate_minimum"] == 0.8, "ready rate")
    check(activation["missingness_subgroup_audit_required"] is True, "missing audit")
    check(activation["residual_direction_must_be_predeclared"] is True, "residual direction")
    check(activation["passing_coverage_does_not_authorize_training"] is True, "coverage not training")

    check(len(payload["explicit_non_goals"]) == 7, "non-goals")
    qualification = payload["qualification"]
    check(qualification["design_predeclared"] is True, "design predeclared")
    for key in (
        "source_qualified",
        "real_feature_build_executed",
        "residual_audit_executed",
        "model_training_authorized",
        "strict_t60_qualified",
        "formal_market_backtest_allowed",
        "betting_edge_claim_allowed",
    ):
        check(qualification[key] is False, key)
    check(qualification["formal_stake"] == 0, "stake")
    check(payload["next_unique_mainline"] == "QUALIFY_AND_BUILD_PRIOR_ONLY_PLAYER_ROTATION_STATE_SOURCE_V1_WITHOUT_MODEL_RETRAINING", "next")

    check("source_game_end_time_utc < target_analysis_cutoff_utc < target_tipoff_utc" in document, "doc PIT")
    check("1,000 feature-ready" in document, "doc sample gate")
    check("Formal Stake: 0" in document, "doc stake")

    output = {
        "schema_version": 1,
        "formal_state": FORMAL_STATE,
        "all_contract_tests_passed": True,
        "contract_tests": tests,
        "design": {
            "player_features": len(player_names),
            "team_features": len(team_names),
            "target_games": 1230,
            "target_team_rows": 2460,
            "minimum_feature_ready_games": 1000
        },
        "preserved_locks": {
            "real_feature_build_executed": False,
            "model_training_authorized": False,
            "strict_t60_qualified": False,
            "formal_market_backtest_allowed": False,
            "betting_edge_claim_allowed": False,
            "formal_stake": 0
        },
        "next_unique_mainline": payload["next_unique_mainline"]
    }
    path = Path("artifacts/prior-only-player-rotation-state-feature-layer-v1-validation.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
