#!/usr/bin/env python3
"""Audit whether injury burden aligns with out-of-fold model residuals.

This is a diagnostic-only script. It does not fit a model, adjust probabilities, or claim causal
or betting value. Small samples are explicitly blocked from activation.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

VERSION = "injury-feature-residual-audit-v1"
FEATURES = [
    "weighted_unavailable_minutes_home_minus_away",
    "weighted_absence_impact_signed_home_minus_away",
    "weighted_absence_impact_positive_home_minus_away",
    "weighted_absence_impact_absolute_home_minus_away",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_corr(x: pd.Series, y: pd.Series) -> dict[str, Any]:
    frame = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(frame) < 3 or frame["x"].nunique() < 2 or frame["y"].nunique() < 2:
        return {"n": len(frame), "rho": None, "p_value": None}
    result = spearmanr(frame["x"], frame["y"])
    rho = float(result.statistic)
    p_value = float(result.pvalue)
    return {
        "n": len(frame),
        "rho": round(rho, 6) if np.isfinite(rho) else None,
        "p_value": round(p_value, 6) if np.isfinite(p_value) else None,
    }


def audit(predictions_path: Path, injury_path: Path, output_dir: Path) -> dict[str, Any]:
    predictions = pd.read_csv(predictions_path, dtype={"game_id": str})
    injury = pd.read_csv(injury_path, dtype={"historical_game_id": str})

    required_predictions = {
        "game_id", "game_date", "home_team_abbr", "away_team_abbr",
        "actual_home_win", "actual_home_margin", "predicted_home_win_probability",
        "predicted_home_margin",
    }
    required_injury = {
        "historical_game_id", "game_date", "home_team_abbr", "away_team_abbr",
        "matchup_snapshot_complete", "matchup_feature_available", *FEATURES,
    }
    missing_pred = sorted(required_predictions - set(predictions.columns))
    missing_injury = sorted(required_injury - set(injury.columns))
    if missing_pred or missing_injury:
        raise ValueError(f"missing columns: predictions={missing_pred}, injury={missing_injury}")

    joined = predictions.merge(
        injury,
        left_on="game_id",
        right_on="historical_game_id",
        how="inner",
        suffixes=("_prediction", "_injury"),
        validate="one_to_one",
    )
    joined["date_match"] = joined["game_date_prediction"] == joined["game_date_injury"]
    joined["home_team_match"] = (
        joined["home_team_abbr_prediction"] == joined["home_team_abbr_injury"]
    )
    joined["away_team_match"] = (
        joined["away_team_abbr_prediction"] == joined["away_team_abbr_injury"]
    )
    identity_mismatches = int(
        (~joined["date_match"] | ~joined["home_team_match"] | ~joined["away_team_match"]).sum()
    )
    if identity_mismatches:
        raise ValueError(f"joined rows contain {identity_mismatches} game identity mismatches")

    joined["home_win_probability_residual"] = (
        joined["actual_home_win"] - joined["predicted_home_win_probability"]
    )
    joined["home_margin_residual"] = (
        joined["actual_home_margin"] - joined["predicted_home_margin"]
    )
    eligible = joined[joined["matchup_feature_available"] == 1].copy()

    feature_results = {}
    for feature in FEATURES:
        feature_results[feature] = {
            "probability_residual": safe_corr(
                eligible[feature], eligible["home_win_probability_residual"]
            ),
            "margin_residual": safe_corr(
                eligible[feature], eligible["home_margin_residual"]
            ),
            "expected_direction": "negative",
            "direction_matches_probability_residual": None,
            "direction_matches_margin_residual": None,
        }
        probability_rho = feature_results[feature]["probability_residual"]["rho"]
        margin_rho = feature_results[feature]["margin_residual"]["rho"]
        if probability_rho is not None:
            feature_results[feature]["direction_matches_probability_residual"] = probability_rho < 0
        if margin_rho is not None:
            feature_results[feature]["direction_matches_margin_residual"] = margin_rho < 0

    joined_output = joined[
        [
            "game_id", "game_date_prediction", "home_team_abbr_prediction",
            "away_team_abbr_prediction", "matchup_snapshot_complete",
            "matchup_feature_available", "actual_home_win", "actual_home_margin",
            "predicted_home_win_probability", "predicted_home_margin",
            "home_win_probability_residual", "home_margin_residual", *FEATURES,
        ]
    ].rename(
        columns={
            "game_date_prediction": "game_date",
            "home_team_abbr_prediction": "home_team_abbr",
            "away_team_abbr_prediction": "away_team_abbr",
        }
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    joined_output.to_csv(output_dir / "injury-residual-audit-rows.csv", index=False)

    eligible_rows = len(eligible)
    minimum_activation_rows = 100
    all_probability_directions = all(
        item["direction_matches_probability_residual"] is True
        for item in feature_results.values()
    )
    all_margin_directions = all(
        item["direction_matches_margin_residual"] is True
        for item in feature_results.values()
    )
    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "coverage": {
            "prediction_rows": len(predictions),
            "injury_matchup_rows": len(injury),
            "joined_rows": len(joined),
            "complete_snapshot_rows": int((joined["matchup_snapshot_complete"] == 1).sum()),
            "feature_ready_rows": eligible_rows,
            "minimum_rows_for_activation": minimum_activation_rows,
        },
        "quality": {
            "duplicate_prediction_game_ids": int(predictions["game_id"].duplicated().sum()),
            "duplicate_injury_game_ids": int(injury["historical_game_id"].duplicated().sum()),
            "game_identity_mismatches": identity_mismatches,
            "all_feature_ready_rows_have_complete_snapshots": bool(
                (eligible["matchup_snapshot_complete"] == 1).all()
            ),
            "all_probability_residual_directions_negative": all_probability_directions,
            "all_margin_residual_directions_negative": all_margin_directions,
        },
        "feature_results": feature_results,
        "decision": {
            "directional_signal_detected_in_pilot": (
                all_probability_directions and all_margin_directions and eligible_rows >= 5
            ),
            "ready_for_injury_feature_model_training": False,
            "ready_for_probability_adjustment": False,
            "ready_for_betting_edge_claim": False,
            "reason": (
                f"Only {eligible_rows} feature-ready games are available; at least "
                f"{minimum_activation_rows} independent point-in-time games are required before "
                "any activation experiment."
            ),
        },
        "guardrails": {
            "model_refit_performed": False,
            "probabilities_modified": False,
            "causal_claim_made": False,
            "statistical_significance_required_for_directional_pilot": False,
            "small_sample_activation_blocked": eligible_rows < minimum_activation_rows,
            "positive_injury_difference_means_more_home_burden": True,
            "expected_residual_direction": "negative",
        },
    }
    (output_dir / "injury-residual-audit-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def self_test(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    predictions = pd.DataFrame(
        {
            "game_id": ["1", "2", "3"],
            "game_date": ["2023-01-01", "2023-01-02", "2023-01-03"],
            "home_team_abbr": ["AAA", "BBB", "CCC"],
            "away_team_abbr": ["DDD", "EEE", "FFF"],
            "actual_home_win": [1, 0, 0],
            "actual_home_margin": [5, -4, -12],
            "predicted_home_win_probability": [0.6, 0.6, 0.6],
            "predicted_home_margin": [2, 2, 2],
        }
    )
    injury = pd.DataFrame(
        {
            "historical_game_id": ["1", "2", "3"],
            "game_date": predictions["game_date"],
            "home_team_abbr": predictions["home_team_abbr"],
            "away_team_abbr": predictions["away_team_abbr"],
            "matchup_snapshot_complete": [1, 1, 1],
            "matchup_feature_available": [1, 1, 1],
            "weighted_unavailable_minutes_home_minus_away": [-10, 0, 10],
            "weighted_absence_impact_signed_home_minus_away": [-1, 0, 1],
            "weighted_absence_impact_positive_home_minus_away": [-1, 0, 1],
            "weighted_absence_impact_absolute_home_minus_away": [-1, 0, 1],
        }
    )
    pred_path = output_dir / "predictions.csv"
    injury_path = output_dir / "injury.csv"
    predictions.to_csv(pred_path, index=False)
    injury.to_csv(injury_path, index=False)
    report = audit(pred_path, injury_path, output_dir / "result")
    assert report["decision"]["directional_signal_detected_in_pilot"] is True, report
    assert report["decision"]["ready_for_injury_feature_model_training"] is False, report
    assert report["guardrails"]["small_sample_activation_blocked"] is True, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--injury-matchups", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("injury feature residual audit self-test passed")
        return
    if not args.predictions or not args.injury_matchups:
        parser.error("--predictions and --injury-matchups are required")
    report = audit(args.predictions, args.injury_matchups, args.output_dir)
    print(json.dumps(report["decision"], indent=2))


if __name__ == "__main__":
    main()
