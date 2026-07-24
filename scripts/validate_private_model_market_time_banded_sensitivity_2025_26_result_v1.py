#!/usr/bin/env python3
"""Validate the recorded aggregate-only 2025-26 model/market sensitivity result.

This validator never reads or emits game-level predictions, bookmaker prices, or
private joined rows. It validates only the committed aggregate result and the
preserved research locks.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

EXPECTED_STATE = "PRIVATE_MODEL_MARKET_TIME_BANDED_SENSITIVITY_2025_26_VALID_RECORDED"
VALID_STATE = "PRIVATE_MODEL_MARKET_TIME_BANDED_SENSITIVITY_2025_26_RESULT_VALID"
EXPECTED_NEXT = (
    "REVIEW_MODEL_MARKET_GAP_AND_PRESERVE_MARKET_BACKTEST_LOCK_"
    "WHILE_AWAITING_EXACT_PROVIDER_OBSERVED_AT"
)
EXPECTED_BAND_ROWS = {"5": 310, "15": 493, "30": 612, "60": 697}


def require(condition: bool, label: str, checks: list[str]) -> None:
    if not condition:
        raise AssertionError(label)
    checks.append(label)


def validate(payload: dict[str, Any]) -> dict[str, Any]:
    checks: list[str] = []

    require(payload["formal_state"] == EXPECTED_STATE, "formal_state", checks)
    require(
        payload["schema_version"]
        == "private-model-market-time-banded-sensitivity-2025-26-result-v1",
        "schema_version",
        checks,
    )

    evidence = payload["execution_evidence"]
    require(evidence["execution_mode"] == "LOCAL_PRIVATE_OFFLINE", "offline_execution", checks)
    require(evidence["network_requests"] == 0, "zero_network_requests", checks)
    require(evidence["provider_api_requests"] == 0, "zero_provider_requests", checks)
    require(evidence["aggregate_report_inspected"] is True, "aggregate_report_inspected", checks)
    require(
        evidence["private_join_inspected_aggregate_only"] is True,
        "private_join_aggregate_only_inspection",
        checks,
    )
    for key in (
        "local_execution_script_sha256",
        "aggregate_report_sha256",
        "private_join_csv_sha256",
        "private_bundle_sha256",
    ):
        require(str(evidence[key]).startswith("sha256:"), f"evidence_digest_{key}", checks)

    inputs = payload["inputs"]
    require(inputs["prediction_rows"] == 1230, "prediction_rows_1230", checks)
    require(inputs["odds_rows"] == 8153, "odds_rows_8153", checks)
    require(inputs["regular_season_aligned_events"] == 1112, "aligned_events_1112", checks)
    require(inputs["source_scope"] == "PRIVATE_DIAGNOSTIC_ONLY", "private_scope", checks)

    join = payload["join"]
    require(join["exact_same_game_matches_before_moneyline_filter"] == 1111, "same_game_1111", checks)
    require(join["valid_two_way_pretip_moneyline_matches"] == 1110, "moneyline_matches_1110", checks)
    require(join["unique_prediction_games_joined"] == 1110, "unique_prediction_games_1110", checks)
    require(join["unique_schedule_rows_joined"] == 1110, "unique_schedule_rows_1110", checks)
    require(sum(join["join_methods"].values()) == 1110, "join_method_total_1110", checks)
    require(sum(join["alignment_status_counts"].values()) == 1110, "alignment_status_total_1110", checks)
    require(join["orientation_mismatches"] == 0, "zero_orientation_mismatches", checks)
    require(join["duplicate_join_keys"] == 0, "zero_duplicate_join_keys", checks)
    require(len(join["exclusions"]) == 2, "two_documented_exclusions", checks)

    selection = payload["selection_rule"]
    require(selection["market"] == "two_way_moneyline", "moneyline_only", checks)
    require(selection["time_bands_minutes"] == [5, 15, 30, 60], "predeclared_bands", checks)
    require(selection["bands_are_nested"] is True, "nested_bands", checks)
    require(selection["bands_predeclared_before_metric_review"] is True, "bands_predeclared", checks)
    require(selection["profitability_based_band_selection"] is False, "no_profitability_band_selection", checks)

    timing = payload["timing_authority"]
    require(timing["provider_origin_quote_time_verified"] is False, "provider_time_not_verified", checks)
    require(timing["quote_level_exact_observed_at_verified"] is False, "exact_observed_at_not_verified", checks)
    require(timing["strict_t60_qualified"] is False, "strict_t60_locked", checks)

    bands = payload["time_bands"]
    require(set(bands) == set(EXPECTED_BAND_ROWS), "exact_band_keys", checks)
    previous_rows = 0
    for key in ("5", "15", "30", "60"):
        band = bands[key]
        require(band["rows"] == EXPECTED_BAND_ROWS[key], f"band_{key}_row_count", checks)
        require(band["rows"] >= previous_rows, f"band_{key}_nested_row_count", checks)
        previous_rows = band["rows"]
        require(
            band["market_no_vig"]["log_loss"] < band["model"]["log_loss"],
            f"band_{key}_market_log_loss_better",
            checks,
        )
        require(
            band["market_no_vig"]["brier_score"] < band["model"]["brier_score"],
            f"band_{key}_market_brier_better",
            checks,
        )
        require(
            band["market_no_vig"]["accuracy"] >= band["model"]["accuracy"],
            f"band_{key}_market_accuracy_not_worse",
            checks,
        )
        bootstrap = band["paired_bootstrap"]
        require(bootstrap["resamples"] == 5000, f"band_{key}_bootstrap_5000", checks)
        require(
            bootstrap["model_minus_market_log_loss_ci95"][0] > 0,
            f"band_{key}_log_loss_ci_excludes_zero",
            checks,
        )
        if key != "5":
            require(
                bootstrap["model_minus_market_brier_ci95"][0] > 0,
                f"band_{key}_brier_ci_excludes_zero",
                checks,
            )

    findings = payload["cross_band_findings"]
    require(findings["market_log_loss_better_than_model_in_all_bands"] is True, "market_ll_all_bands", checks)
    require(findings["market_brier_better_than_model_in_all_bands"] is True, "market_brier_all_bands", checks)
    require(findings["model_accuracy_better_than_market_in_any_band"] is False, "model_accuracy_no_band_win", checks)

    private_outputs = payload["private_outputs"]
    require(private_outputs["joined_rows"] == 1110, "private_joined_rows_1110", checks)
    require(private_outputs["public_join_rows_committed"] == 0, "zero_public_join_rows", checks)
    require(private_outputs["public_price_rows_committed"] == 0, "zero_public_price_rows", checks)

    execution = payload["execution_boundaries"]
    for key in (
        "model_retraining_executed",
        "model_refit_executed",
        "market_data_used_as_model_feature",
        "bet_selection_executed",
        "ev_calculated",
        "roi_calculated",
        "clv_calculated",
        "drawdown_calculated",
    ):
        require(execution[key] is False, f"lock_{key}", checks)
    require(execution["provider_api_requests"] == 0, "execution_zero_provider_requests", checks)

    qualification = payload["qualification"]
    require(qualification["private_time_banded_sensitivity_valid"] is True, "private_diagnostic_valid", checks)
    require(
        qualification["formal_point_in_time_market_backtest_allowed"] is False,
        "formal_market_backtest_locked",
        checks,
    )
    require(qualification["strict_t60_qualified"] is False, "qualification_t60_locked", checks)
    require(qualification["betting_edge_claim_allowed"] is False, "betting_edge_locked", checks)
    require(qualification["formal_stake"] == 0, "formal_stake_zero", checks)
    require(payload["next_unique_sub_mainline"] == EXPECTED_NEXT, "next_unique_sub_mainline", checks)

    return {
        "formal_state": VALID_STATE,
        "validated_record_state": payload["formal_state"],
        "contract_tests": len(checks),
        "all_contract_tests_passed": True,
        "validated_population": {
            "prediction_rows": inputs["prediction_rows"],
            "regular_season_aligned_events": inputs["regular_season_aligned_events"],
            "valid_two_way_pretip_moneyline_matches": join["valid_two_way_pretip_moneyline_matches"],
            "time_band_rows": EXPECTED_BAND_ROWS,
        },
        "preserved_locks": {
            "strict_t60_qualified": False,
            "formal_point_in_time_market_backtest_allowed": False,
            "betting_edge_claim_allowed": False,
            "ev_roi_clv_drawdown_calculated": False,
            "formal_stake": 0,
        },
        "next_unique_sub_mainline": EXPECTED_NEXT,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = json.loads(args.result.read_text(encoding="utf-8"))
    validation = validate(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(validation, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
