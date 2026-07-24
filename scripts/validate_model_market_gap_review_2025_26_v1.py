#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "data" / "research" / "model-market-gap-review-2025-26-v1.json"
DOC = ROOT / "docs" / "model-market-gap-review-2025-26-v1.md"
ANALYZER = ROOT / "scripts" / "review_model_market_gap_2025_26_v1.py"


def main() -> int:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    document = DOC.read_text(encoding="utf-8")
    analyzer = ANALYZER.read_text(encoding="utf-8")
    tests = 0

    def check(condition: bool, message: str) -> None:
        nonlocal tests
        assert condition, message
        tests += 1

    check(result["formal_state"] == "MODEL_MARKET_GAP_REVIEW_2025_26_VALID_RECORDED", "formal state")
    check(result["scope"] == "PRIVATE_AGGREGATE_DIAGNOSTIC_ONLY", "scope")
    source = result["source_evidence"]
    check(source["main_before_review"] == "d464bd0973974c9075e9a9bee9a14bb5fb2ac2d1", "prior main")
    check(source["private_sensitivity_pr"] == 180, "source PR")
    check(source["private_join_rows"] == 1110, "private joins")
    check(source["forward_gold_rows"] == 1230, "forward Gold")
    check(source["network_requests"] == 0, "network")
    check(source["provider_api_requests"] == 0, "provider API")
    check(source["public_game_level_rows"] == 0, "public games")
    check(source["public_price_rows"] == 0, "public prices")

    population = result["primary_population"]
    check(population["rows"] == 310, "primary rows")
    check("<= 5 minutes" in population["definition"], "primary definition")
    check(population["strict_t60_qualified"] is False, "strict T60")
    check(population["provider_origin_quote_time_verified"] is False, "provider time")
    check(population["quote_level_exact_observed_at_verified"] is False, "quote time")

    metrics = result["primary_metrics"]
    model = metrics["model"]
    market = metrics["market_no_vig"]
    differences = metrics["model_minus_market"]
    check(model["rows"] == 310, "model rows")
    check(market["rows"] == 310, "market rows")
    check(abs(model["log_loss"] - 0.6253827387181812) < 1e-12, "model log loss")
    check(abs(market["log_loss"] - 0.6024162935120525) < 1e-12, "market log loss")
    check(abs(model["brier_score"] - 0.21740226957261513) < 1e-12, "model Brier")
    check(abs(market["brier_score"] - 0.2085980001061601) < 1e-12, "market Brier")
    check(abs(model["accuracy"] - 0.6548387096774193) < 1e-12, "model accuracy")
    check(abs(market["accuracy"] - 0.6580645161290323) < 1e-12, "market accuracy")
    check(abs(model["roc_auc"] - 0.6995193312434691) < 1e-12, "model AUC")
    check(abs(market["roc_auc"] - 0.7292163009404389) < 1e-12, "market AUC")
    check(differences["log_loss"] > 0, "market better log loss")
    check(differences["brier_score"] > 0, "market better Brier")
    check(differences["accuracy"] < 0, "market better accuracy")
    check(differences["roc_auc"] < 0, "market better AUC")

    calibration = metrics["calibration"]
    check(calibration["model"]["ece_10_equal_frequency_bins"] > calibration["market_no_vig"]["ece_10_equal_frequency_bins"], "ECE ordering")
    check(0 < calibration["model"]["slope"] < 2, "model slope")
    check(0 < calibration["market_no_vig"]["slope"] < 2, "market slope")
    check(abs(calibration["model"]["intercept"]) < 1, "model intercept")
    check(abs(calibration["market_no_vig"]["intercept"]) < 1, "market intercept")

    slices = result["fixed_diagnostic_slices"]
    check(len(slices["side_agreement"]) == 2, "agreement groups")
    check(sum(row["rows"] for row in slices["side_agreement"]) == 310, "agreement total")
    check(len(slices["absolute_probability_gap"]) == 4, "gap groups")
    check(sum(row["rows"] for row in slices["absolute_probability_gap"]) == 310, "gap total")
    check(len(slices["model_selected_probability"]) == 6, "model confidence groups")
    check(sum(row["rows"] for row in slices["model_selected_probability"]) == 310, "model confidence total")
    check(len(slices["market_selected_probability"]) == 6, "market confidence groups")
    check(sum(row["rows"] for row in slices["market_selected_probability"]) == 310, "market confidence total")
    check(len(slices["prior_games_min"]) == 4, "prior games groups")
    check(sum(row["rows"] for row in slices["prior_games_min"]) == 310, "prior games total")
    check(len(slices["season_phase"]) == 3, "season groups")
    check(sum(row["rows"] for row in slices["season_phase"]) == 310, "season total")

    gap = {row["group"]: row for row in slices["absolute_probability_gap"]}
    check(gap["10pp+"]["rows"] == 92, "large gap rows")
    check(abs(gap["10pp+"]["model_minus_market"]["log_loss"] - 0.06312530457077015) < 1e-12, "large gap log loss")
    check(gap["10pp+"]["model_minus_market"]["brier_score"] > 0, "large gap Brier")
    check(gap["5-10pp"]["rows"] == 96, "medium gap rows")
    check(gap["5-10pp"]["model_minus_market"]["log_loss"] < 0, "descriptive medium gap")
    check(result["findings"]["no_subgroup_promotion_authorized"] is True, "no subgroup promotion")

    correlations = result["existing_gold_feature_residual_correlations"]
    check(correlations["method"] == "Spearman", "correlation method")
    check(correlations["features_predeclared_as_all_existing_matchup_features"] is True, "all features")
    check(len(correlations["results"]) == 11, "correlation count")
    check(correlations["results"][0]["feature"] == "orb_pct_last_10_diff", "top correlation")
    check(abs(correlations["results"][0]["spearman_rho"] - 0.2569608523710654) < 1e-12, "top rho")
    check(all(row["rows"] in {306, 310} for row in correlations["results"]), "correlation rows")

    findings = result["findings"]
    check(findings["market_better_overall_primary_band"] is True, "market better")
    check(findings["model_ece_higher_than_market_ece"] is True, "model ECE")
    check(findings["largest_descriptive_gap_bin"] == "10pp+", "largest gap")
    check(findings["largest_gap_bin_rows"] == 92, "largest gap count")
    check(findings["injury_two_feature_candidate_already_valid_negative"] is True, "injury negative preserved")
    check(findings["current_gold_features_alone_do_not_close_market_gap"] is True, "Gold gap preserved")

    decision = result["decision"]
    check(decision["formal_interpretation"] == "PRESERVE_FROZEN_BASELINE_AND_MARKET_BACKTEST_LOCK", "decision")
    check(decision["model_retraining_authorized"] is False, "no retraining")
    check(decision["existing_injury_candidate_retuning_authorized"] is False, "no injury retune")
    check(decision["market_residual_blend_activation_authorized"] is False, "no blend")
    check(decision["next_research_design"] == "PREDECLARE_PRIOR_ONLY_PLAYER_ROTATION_STATE_FEATURE_LAYER_V1", "next design")

    locks = result["preserved_locks"]
    for key in (
        "strict_t60_qualified",
        "formal_point_in_time_market_backtest_allowed",
        "ev_allowed",
        "roi_allowed",
        "clv_allowed",
        "drawdown_allowed",
        "betting_edge_claim_allowed",
    ):
        check(locks[key] is False, f"lock {key}")
    check(locks["formal_stake"] == 0, "stake")

    check("VALID_NEGATIVE_RESULT" in document, "document injury result")
    check("PREDECLARE_PRIOR_ONLY_PLAYER_ROTATION_STATE_FEATURE_LAYER_V1" in document, "document next")
    check("This is diagnostic, not a post-hoc betting filter." in document, "document subgroup warning")
    check("Formal Stake: 0" in document, "document stake")
    check("never writes game-level rows or prices" in analyzer, "analyzer private boundary")
    check("provider-origin observed_at" in analyzer, "analyzer timestamp warning")
    check("expected 1,110 private joins" in analyzer, "analyzer population")
    check("expected 310 primary rows" in analyzer, "analyzer primary")
    check("public_game_level_rows" in analyzer, "analyzer public lock")
    check("model_retraining_authorized" in analyzer, "analyzer retraining lock")

    validation = {
        "schema_version": 1,
        "formal_state": "MODEL_MARKET_GAP_REVIEW_2025_26_RESULT_VALID",
        "all_contract_tests_passed": True,
        "contract_tests": tests,
        "validated_population": {
            "private_join_rows": 1110,
            "forward_gold_rows": 1230,
            "primary_rows": 310,
        },
        "formal_interpretation": decision["formal_interpretation"],
        "next_research_design": decision["next_research_design"],
        "preserved_locks": locks,
    }
    output = ROOT / "artifacts" / "model-market-gap-review-2025-26-validation-v1.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(validation, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
