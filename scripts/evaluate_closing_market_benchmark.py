#!/usr/bin/env python3
"""Compare walk-forward NBA probabilities with closing-only moneyline archives."""
from __future__ import annotations

import argparse
import json
import math
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

VERSION = "closing-market-benchmark-v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clip(values: pd.Series) -> pd.Series:
    return values.astype(float).clip(1e-8, 1 - 1e-8)


def metrics(actual: pd.Series, probability: pd.Series) -> dict[str, float]:
    y = actual.astype(float)
    p = clip(probability)
    return {
        "log_loss": float((-(y * p.map(math.log) + (1 - y) * (1 - p).map(math.log))).mean()),
        "brier_score": float(((p - y) ** 2).mean()),
        "accuracy": float(((p >= 0.5).astype(int) == y.astype(int)).mean()),
        "mean_probability": float(p.mean()),
        "actual_rate": float(y.mean()),
    }


def evaluate(predictions_path: Path, closing_path: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    predictions = pd.read_csv(predictions_path)
    closing = pd.read_csv(closing_path)
    required_predictions = {
        "test_season", "game_id", "game_date", "home_team_abbr", "away_team_abbr",
        "actual_home_win", "predicted_home_win_probability",
    }
    required_closing = {
        "game_date", "home_team_abbr", "away_team_abbr", "fair_home_probability",
        "timestamp_quality", "source_id",
    }
    missing_p = sorted(required_predictions - set(predictions.columns))
    missing_c = sorted(required_closing - set(closing.columns))
    if missing_p or missing_c:
        raise ValueError(f"missing prediction columns={missing_p}; closing columns={missing_c}")
    if (closing["timestamp_quality"] != "closing_label_only").any():
        raise ValueError("this evaluator only accepts closing_label_only archives")
    keys = ["game_date", "home_team_abbr", "away_team_abbr"]
    predictions = predictions.copy()
    closing = closing.copy()
    for frame in (predictions, closing):
        frame["game_date"] = frame["game_date"].astype(str)
        frame["home_team_abbr"] = frame["home_team_abbr"].astype(str).str.upper().str.strip()
        frame["away_team_abbr"] = frame["away_team_abbr"].astype(str).str.upper().str.strip()
    if closing.duplicated(keys).any():
        raise ValueError("closing archive contains duplicate game keys")
    joined = predictions.merge(closing, on=keys, how="inner", validate="one_to_one")
    if joined.empty:
        raise ValueError("no closing archive rows matched walk-forward predictions")
    joined = joined.sort_values(["game_date", "game_id"]).reset_index(drop=True)
    joined.to_csv(output_dir / "closing-benchmark-joined.csv", index=False)

    aggregate_model = metrics(joined["actual_home_win"], joined["predicted_home_win_probability"])
    aggregate_market = metrics(joined["actual_home_win"], joined["fair_home_probability"])
    per_season: list[dict[str, Any]] = []
    for season, group in joined.groupby("test_season", sort=True):
        model = metrics(group["actual_home_win"], group["predicted_home_win_probability"])
        market = metrics(group["actual_home_win"], group["fair_home_probability"])
        per_season.append({
            "season": str(season),
            "games": int(len(group)),
            "model": model,
            "closing_market": market,
            "model_minus_market_log_loss": model["log_loss"] - market["log_loss"],
            "model_minus_market_brier": model["brier_score"] - market["brier_score"],
        })
    coverage = len(joined) / len(predictions) if len(predictions) else 0.0
    season_count = int(joined["test_season"].nunique())
    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "coverage": {
            "prediction_games": int(len(predictions)),
            "matched_games": int(len(joined)),
            "match_rate": coverage,
            "matched_seasons": season_count,
            "source_ids": sorted(set(joined["source_id"].astype(str))),
        },
        "aggregate": {
            "model": aggregate_model,
            "closing_market": aggregate_market,
            "model_minus_market_log_loss": aggregate_model["log_loss"] - aggregate_market["log_loss"],
            "model_minus_market_brier": aggregate_model["brier_score"] - aggregate_market["brier_score"],
        },
        "per_season": per_season,
        "guardrails": {
            "archive_has_exact_observation_timestamp": False,
            "closing_odds_used_as_model_features": False,
            "roi_computed": False,
            "clv_computed": False,
            "result_is_forecast_benchmark_only": True,
        },
        "decision": {
            "closing_benchmark_evaluation_complete": True,
            "ready_for_market_accuracy_comparison": len(joined) >= 500 and season_count >= 3 and coverage >= 0.70,
            "ready_for_point_in_time_roi_backtest": False,
            "ready_for_clv_analysis": False,
            "ready_for_betting_edge_claim": False,
        },
    }
    (output_dir / "closing-benchmark-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def self_test(output_dir: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="nbavl-closing-benchmark-") as temp_name:
        root = Path(temp_name)
        p = root / "predictions.csv"
        c = root / "closing.csv"
        pd.DataFrame([
            {"test_season": "2022-23", "game_id": "1", "game_date": "2022-10-18", "home_team_abbr": "BOS", "away_team_abbr": "PHI", "actual_home_win": 1, "predicted_home_win_probability": 0.62},
            {"test_season": "2022-23", "game_id": "2", "game_date": "2022-10-19", "home_team_abbr": "PHX", "away_team_abbr": "DAL", "actual_home_win": 0, "predicted_home_win_probability": 0.54},
        ]).to_csv(p, index=False)
        pd.DataFrame([
            {"game_date": "2022-10-18", "home_team_abbr": "BOS", "away_team_abbr": "PHI", "fair_home_probability": 0.58, "timestamp_quality": "closing_label_only", "source_id": "self_test"},
            {"game_date": "2022-10-19", "home_team_abbr": "PHX", "away_team_abbr": "DAL", "fair_home_probability": 0.51, "timestamp_quality": "closing_label_only", "source_id": "self_test"},
        ]).to_csv(c, index=False)
        report = evaluate(p, c, output_dir)
        assert report["coverage"]["matched_games"] == 2
        assert report["guardrails"]["roi_computed"] is False
        (output_dir / "self-test.json").write_text('{"passed":true}\n', encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--closing-odds", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("closing market benchmark self-test passed")
        return
    if not args.predictions or not args.closing_odds:
        parser.error("--predictions and --closing-odds are required unless --self-test is used")
    report = evaluate(args.predictions, args.closing_odds, args.output_dir)
    print(json.dumps(report["decision"], indent=2))


if __name__ == "__main__":
    main()
