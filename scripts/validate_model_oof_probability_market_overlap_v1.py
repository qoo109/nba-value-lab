#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "data" / "research" / "model-oof-probability-market-overlap-diagnostic-v1.json"
ANALYZER = ROOT / "scripts" / "analyze_model_oof_probability_market_overlap_v1.py"
DOC = ROOT / "docs" / "model-oof-probability-market-overlap-diagnostic-v1.md"


def close(actual: float, expected: float, tolerance: float = 1e-12) -> bool:
    return abs(actual - expected) <= tolerance


def recursive_keys(value: Any) -> list[str]:
    keys: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            keys.append(str(key))
            keys.extend(recursive_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.extend(recursive_keys(child))
    return keys


def main() -> int:
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    analyzer_text = ANALYZER.read_text(encoding="utf-8")
    document = DOC.read_text(encoding="utf-8")
    tests = 0

    def check(condition: bool, message: str) -> None:
        nonlocal tests
        assert condition, message
        tests += 1

    check(
        record["formal_state"]
        == "MODEL_OOF_PROBABILITY_DIAGNOSTIC_VALID_MARKET_JOIN_BLOCKED_NO_SEASON_OVERLAP",
        "formal state",
    )
    check(record["inputs"]["model_artifact_run"] == 29551715399, "model run")
    check(record["inputs"]["model_artifact_id"] == 8396002523, "model artifact")
    check(
        record["inputs"]["model_artifact_digest"]
        == "sha256:6063adac9851b47d339a93e35935115008b736a16925548d36a8c54a0353b41b",
        "model artifact digest",
    )
    check(record["inputs"]["prediction_rows"] == 3688, "prediction rows")
    check(
        record["inputs"]["prediction_test_seasons"]
        == ["2021-22", "2022-23", "2023-24"],
        "prediction seasons",
    )
    check(record["inputs"]["odds"]["seasons"] == ["2025-26"], "odds season")
    check(record["inputs"]["odds"]["unique_regular_events"] == 1112, "odds events")
    check(record["inputs"]["odds"]["rows"] == 8153, "odds rows")
    check(record["inputs"]["raw_predictions_committed"] is False, "no raw predictions")
    check(record["inputs"]["raw_odds_committed"] is False, "no raw odds")

    model = record["model_only_oof"]["model"]
    elo = record["model_only_oof"]["elo_benchmark"]
    check(record["model_only_oof"]["selected_probability_method"] == "raw_logistic_elo", "selected method")
    check(close(model["log_loss"], 0.6313055505091826), "model log loss")
    check(close(model["brier_score"], 0.2205666108266445), "model brier")
    check(close(model["accuracy"], 0.6385574837310195), "model accuracy")
    check(close(model["roc_auc"], 0.6870991607711363), "model AUC")
    check(close(elo["log_loss"], 0.6343010509609447), "Elo log loss")
    check(close(elo["brier_score"], 0.22194937399955977), "Elo brier")
    check(record["model_only_oof"]["model_minus_elo"]["log_loss"] < 0, "model log loss better")
    check(record["model_only_oof"]["model_minus_elo"]["brier_score"] < 0, "model brier better")
    check(record["model_only_oof"]["model_minus_elo"]["accuracy"] < 0, "model accuracy slightly lower")
    check(record["model_only_oof"]["model_minus_elo"]["roc_auc"] > 0, "model AUC higher")

    reliability = record["model_only_oof"]["reliability"]
    check(close(reliability["ece"], 0.014239421393709352), "ECE")
    check(len(reliability["bins"]) == 10, "reliability bin count")
    check(reliability["bins"][-1]["rows"] == 4, "sparse highest bin")

    thresholds = record["model_only_oof"]["confidence_thresholds"]
    threshold_map = {
        row["minimum_selected_side_probability"]: row for row in thresholds
    }
    check(threshold_map[0.60]["rows"] == 2260, "60 percent rows")
    check(close(threshold_map[0.60]["accuracy"], 0.7), "60 percent accuracy")
    check(threshold_map[0.70]["rows"] == 1091, "70 percent rows")
    check(close(threshold_map[0.70]["accuracy"], 0.772685609532539), "70 percent accuracy")
    check(threshold_map[0.80]["rows"] == 281, "80 percent rows")
    check(close(threshold_map[0.80]["accuracy"], 0.8256227758007118), "80 percent accuracy")

    bootstrap = record["model_only_oof"]["paired_game_bootstrap_vs_elo"]
    check(bootstrap["resamples"] == 5000, "bootstrap resamples")
    check(bootstrap["seed"] == 20260724, "bootstrap seed")
    check(
        bootstrap["model_minus_elo_log_loss"]["ci95"][0] < 0
        < bootstrap["model_minus_elo_log_loss"]["ci95"][1],
        "log loss interval crosses zero",
    )
    check(
        bootstrap["model_minus_elo_brier"]["ci95"][0] < 0
        < bootstrap["model_minus_elo_brier"]["ci95"][1],
        "brier interval crosses zero",
    )

    overlap = record["market_overlap_gate"]
    check(overlap["overlap_seasons"] == [], "no season overlap")
    check(overlap["market_sensitivity_executed"] is False, "no market sensitivity")
    check(overlap["strict_t60_qualified"] is False, "strict T60 locked")

    readiness = record["forward_scoring_readiness_2025_26"]
    check(readiness["trained_model_artifact_available"] is True, "model artifact available")
    check(readiness["ready_to_score_2025_26"] is False, "2025-26 scoring blocked")
    check(len(readiness["blockers"]) == 3, "three forward blockers")
    check(
        "MISSING_GOVERNED_2024_25_SEASON_STATE" in readiness["blockers"],
        "2024-25 state blocker",
    )

    qualification = record["qualification"]
    check(qualification["model_probability_quality_analysis_allowed"] is True, "model analysis allowed")
    check(qualification["model_vs_market_same_game_comparison_allowed"] is False, "same-game comparison blocked")
    check(qualification["market_backtest_allowed"] is False, "market backtest locked")
    check(qualification["clv_allowed"] is False, "CLV locked")
    check(qualification["roi_allowed"] is False, "ROI locked")
    check(qualification["betting_edge_claim_allowed"] is False, "edge claim locked")
    check(qualification["formal_stake"] == 0, "stake zero")

    keys = {key.lower() for key in recursive_keys(record)}
    check("team1_moneyline" not in keys, "no moneyline field committed")
    check("team2_moneyline" not in keys, "no opposing moneyline field committed")
    check("game_link" not in keys, "no provider link committed")
    check("urllib" not in analyzer_text and "requests" not in analyzer_text, "analyzer offline")
    check("Market Backtest: locked" in document, "document backtest lock")
    check("Formal Stake: 0" in document, "document stake lock")

    prediction_headers = [
        "test_season",
        "game_id",
        "game_date",
        "home_team_abbr",
        "away_team_abbr",
        "actual_home_win",
        "predicted_home_win_probability",
        "elo_home_win_probability",
    ]
    odds_headers = [
        "status",
        "official_schedule_row_id",
        "official_game_id",
        "scheduled_tipoff_utc",
    ]
    synthetic_predictions = [
        {
            "test_season": "2023-24",
            "game_id": str(index),
            "game_date": f"2024-01-{index:02d}",
            "home_team_abbr": "HOM",
            "away_team_abbr": "AWY",
            "actual_home_win": str(index % 2),
            "predicted_home_win_probability": str(0.35 + 0.03 * index),
            "elo_home_win_probability": str(0.37 + 0.025 * index),
        }
        for index in range(1, 13)
    ]
    synthetic_odds = [
        {
            "status": "MATCHED_HIGH_CONFIDENCE_REGULAR_SEASON",
            "official_schedule_row_id": "nba-published-synthetic",
            "official_game_id": "",
            "scheduled_tipoff_utc": "2025-10-21T23:30:00Z",
        }
    ]
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        predictions_path = root / "predictions.csv"
        odds_path = root / "odds.csv"
        output_path = root / "output.json"
        with predictions_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=prediction_headers)
            writer.writeheader()
            writer.writerows(synthetic_predictions)
        with odds_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=odds_headers)
            writer.writeheader()
            writer.writerows(synthetic_odds)
        subprocess.run(
            [
                sys.executable,
                str(ANALYZER),
                "--predictions",
                str(predictions_path),
                "--odds-main",
                str(odds_path),
                "--output",
                str(output_path),
            ],
            check=True,
        )
        synthetic = json.loads(output_path.read_text(encoding="utf-8"))
        check(synthetic["market_overlap_gate"]["overlap_seasons"] == [], "synthetic no overlap")
        check(synthetic["market_overlap_gate"]["market_sensitivity_executed"] is False, "synthetic market lock")
        check(synthetic["qualification"]["formal_stake"] == 0, "synthetic stake")

    qa = {
        "schema_version": 1,
        "formal_state": "MODEL_OOF_PROBABILITY_MARKET_OVERLAP_DIAGNOSTIC_VALID",
        "real_oof_rows": 3688,
        "selected_probability_method": "raw_logistic_elo",
        "model_probability_diagnostic_valid": True,
        "odds_season_overlap": False,
        "market_sensitivity_executed": False,
        "model_retraining_executed": False,
        "raw_predictions_committed": False,
        "raw_odds_committed": False,
        "strict_t60_qualified": False,
        "market_backtest_unlocked": False,
        "contract_tests": tests,
        "formal_stake": 0,
    }
    output = ROOT / "artifacts" / "model-oof-probability-market-overlap-validation-v1.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
