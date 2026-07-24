#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

FORMAL_STATE = "PRIVATE_MODEL_MARKET_GAP_DECOMPOSITION_2025_26_RESULT_VALID"
EXPECTED_BAND_ROWS = {"5": 310, "15": 493, "30": 612, "60": 697}
EXPECTED_DISAGREEMENTS = {"5": 47, "15": 75, "30": 85, "60": 93}
EXPECTED_MODEL_SIDE_WINS = {"5": 23, "15": 32, "30": 36, "60": 43}
EXPECTED_GAP_ROWS = {
    "LT_2PP": 119,
    "2_TO_LT_5PP": 172,
    "5_TO_LT_10PP": 208,
    "GE_10PP": 198,
}
EXPECTED_GAP_LL = {
    "LT_2PP": 0.003309080111402185,
    "2_TO_LT_5PP": 0.008426367496714993,
    "5_TO_LT_10PP": 0.02501107259951163,
    "GE_10PP": 0.05161809436272313,
}
EXPECTED_RHO = {
    "5": 0.054751516307583833,
    "15": 0.00831830631032415,
    "30": -0.010394954860041144,
    "60": 0.006724097829716217,
}
FORBIDDEN_TEXT = (
    "away_odds_decimal",
    "home_odds_decimal",
    "collector_batch_timestamp_utc_assumed",
    "official_schedule_row_id",
    "pinnacle.com",
)


def close(left: float, right: float, tolerance: float = 1e-12) -> bool:
    return abs(float(left) - float(right)) <= tolerance


def validate(result_path: Path) -> dict[str, Any]:
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    tests = 0

    def check(condition: bool, message: str) -> None:
        nonlocal tests
        if not condition:
            raise AssertionError(message)
        tests += 1

    check(payload["schema_version"] == "private-model-market-gap-decomposition-2025-26-result-v1", "schema")
    check(payload["formal_state"] == "PRIVATE_MODEL_MARKET_GAP_DECOMPOSITION_2025_26_VALID_RECORDED", "record state")
    check(payload["inputs"]["private_join_rows"] == 1110, "private rows")
    check(payload["inputs"]["unique_games"] == 1110, "unique games")
    check(payload["inputs"]["gold_feature_join_rows"] == 1110, "gold join")
    check(payload["inputs"]["private_join_sha256"].startswith("sha256:"), "join hash")
    check(payload["inputs"]["forward_gold_sha256"].startswith("sha256:"), "gold hash")

    design = payload["predeclared_design"]
    check(design["time_bands_minutes"] == [5, 15, 30, 60], "bands fixed")
    check(design["primary_feature_diagnostic_band"] == "T60_ABSOLUTE_ERROR_LE_60_MINUTES", "primary band")
    check(len(design["gap_bins"]) == 4, "gap bins")
    check(len(design["features"]) == 11, "feature list")
    check(design["profitability_based_selection"] is False, "no profitability selection")
    check(design["feature_promotion_allowed"] is False, "no feature promotion")

    for band, rows in EXPECTED_BAND_ROWS.items():
        item = payload["time_bands"][band]
        incremental = item["incremental_signal"]
        check(item["rows"] == rows, f"band {band} rows")
        check(item["model_minus_market"]["log_loss"] > 0, f"band {band} market ll")
        check(item["model_minus_market"]["brier_score"] > 0, f"band {band} market brier")
        check(close(incremental["delta_vs_market_residual_spearman"]["coefficient"], EXPECTED_RHO[band]), f"band {band} rho")
        check(abs(incremental["delta_vs_market_residual_spearman"]["coefficient"]) < 0.06, f"band {band} rho small")
        check(incremental["disagreement_games"] == EXPECTED_DISAGREEMENTS[band], f"band {band} disagreements")
        check(incremental["disagreement_model_side_wins"] == EXPECTED_MODEL_SIDE_WINS[band], f"band {band} model wins")
        check(incremental["disagreement_market_side_wins"] + incremental["disagreement_model_side_wins"] == incremental["disagreement_games"], f"band {band} disagreement total")
        check(incremental["disagreement_model_side_win_rate"] <= 0.5, f"band {band} no majority")
        check(incremental["bootstrap"]["resamples"] == 5000, f"band {band} bootstrap")
        check(incremental["bootstrap"]["spearman_ci95"][0] < 0 < incremental["bootstrap"]["spearman_ci95"][1], f"band {band} rho CI crosses zero")
        check(incremental["bootstrap"]["covariance_ci95"][0] < 0 < incremental["bootstrap"]["covariance_ci95"][1], f"band {band} covariance CI crosses zero")

    for label, rows in EXPECTED_GAP_ROWS.items():
        item = payload["gap_magnitude_primary_band"][label]
        check(item["rows"] == rows, f"gap {label} rows")
        check(close(item["model_minus_market"]["log_loss"], EXPECTED_GAP_LL[label]), f"gap {label} ll")
        check(item["model_minus_market"]["log_loss"] > 0, f"gap {label} market better")

    check(
        payload["gap_magnitude_primary_band"]["LT_2PP"]["model_minus_market"]["log_loss"]
        < payload["gap_magnitude_primary_band"]["2_TO_LT_5PP"]["model_minus_market"]["log_loss"]
        < payload["gap_magnitude_primary_band"]["5_TO_LT_10PP"]["model_minus_market"]["log_loss"]
        < payload["gap_magnitude_primary_band"]["GE_10PP"]["model_minus_market"]["log_loss"],
        "gap cost monotonic",
    )

    directions = payload["agreement_direction_primary_band"]
    check(directions["AGREE"]["rows"] == 604, "agree rows")
    check(directions["MODEL_HOME_MARKET_AWAY"]["rows"] == 45, "model home rows")
    check(directions["MODEL_AWAY_MARKET_HOME"]["rows"] == 48, "model away rows")
    check(sum(item["rows"] for item in directions.values()) == 697, "direction population")

    feature_associations = payload["governed_feature_associations_primary_band"]
    check(set(feature_associations) == set(design["features"]), "feature keys")
    for feature, item in feature_associations.items():
        check(item["rows"] >= 692, f"feature {feature} coverage")
        check(abs(item["feature_vs_market_residual_spearman"]["coefficient"]) < 0.06, f"feature {feature} residual correlation")

    findings = payload["aggregate_findings"]
    check(findings["incremental_signal_demonstrated"] is False, "no incremental signal")
    check(findings["all_band_delta_residual_spearman_absolute_below_0_06"] is True, "all rho small")
    check(findings["model_side_wins_majority_of_disagreements_in_any_band"] is False, "no disagreement majority")
    check(findings["model_log_loss_worse_than_market_in_every_gap_bin"] is True, "market wins bins")
    check(close(findings["largest_gap_bin_model_minus_market_log_loss"], EXPECTED_GAP_LL["GE_10PP"]), "largest gap loss")

    research = payload["research_direction"]
    check(research["validated_new_feature"] is None, "no promoted feature")
    check(research["priority_candidates_not_yet_validated"] == [
        "point_in_time_injury_availability",
        "expected_minutes_changes",
        "confirmed_starting_lineup",
        "rotation_and_role_change",
    ], "candidate priorities")
    check(research["next_unique_sub_mainline"] == "BUILD_2025_26_POINT_IN_TIME_INJURY_LINEUP_ROLE_FEATURE_DIAGNOSTIC_WITHOUT_MODEL_RETRAINING_OR_MARKET_BACKTEST_PROMOTION", "next")

    execution = payload["execution_boundaries"]
    for key in ("network_requests", "provider_api_requests"):
        check(execution[key] == 0, key)
    for key in (
        "model_retraining_executed",
        "model_refit_executed",
        "calibration_change_executed",
        "market_data_used_as_model_feature",
        "bet_selection_executed",
        "ev_calculated",
        "roi_calculated",
        "clv_calculated",
        "drawdown_calculated",
    ):
        check(execution[key] is False, key)

    boundary = payload["public_private_boundary"]
    check(boundary["public_game_level_rows"] == 0, "no public games")
    check(boundary["public_price_rows"] == 0, "no public prices")
    check(boundary["private_augmented_rows"] == 1110, "private augmented rows")
    check(boundary["raw_odds_archive_committed"] is False, "no archive")

    qualification = payload["qualification"]
    check(qualification["aggregate_gap_decomposition_valid"] is True, "diagnostic valid")
    check(qualification["strict_t60_qualified"] is False, "T60 locked")
    check(qualification["formal_point_in_time_market_backtest_allowed"] is False, "backtest locked")
    check(qualification["model_retraining_authorized"] is False, "retraining locked")
    check(qualification["betting_edge_claim_allowed"] is False, "edge locked")
    check(qualification["formal_stake"] == 0, "stake")

    rendered = result_path.read_text(encoding="utf-8").lower()
    for token in FORBIDDEN_TEXT:
        check(token.lower() not in rendered, f"forbidden public token: {token}")

    return {
        "schema_version": 1,
        "formal_state": FORMAL_STATE,
        "all_contract_tests_passed": True,
        "contract_tests": tests,
        "validated_population": {
            "private_join_rows": 1110,
            "gold_feature_join_rows": 1110,
            "primary_band_rows": 697,
        },
        "finding": "NO_INCREMENTAL_INFORMATION_SIGNAL_DEMONSTRATED",
        "preserved_locks": {
            "strict_t60_qualified": False,
            "formal_point_in_time_market_backtest_allowed": False,
            "model_retraining_authorized": False,
            "betting_edge_claim_allowed": False,
            "formal_stake": 0,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--result",
        type=Path,
        default=Path("data/research/private-model-market-gap-decomposition-2025-26-result-v1.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/private-model-market-gap-decomposition-2025-26-result-validation-v1.json"),
    )
    args = parser.parse_args()
    output = validate(args.result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
