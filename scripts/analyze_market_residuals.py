#!/usr/bin/env python3
"""Analyze where an NBA model adds information beyond the closing moneyline market.

This module is forecast research only. It consumes closing-label-only prices, never
computes ROI or CLV, never writes joined game-level data, and activates no production
blend unless a forward holdout improves both Log Loss and Brier with adequate evidence.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

VERSION = "market-residual-analysis-v1"
EPS = 1e-8
WEIGHTS = tuple(round(value, 2) for value in np.linspace(0.0, 1.0, 21))
REQUIRED_PREDICTION_COLUMNS = {
    "test_season",
    "game_id",
    "game_date",
    "home_team_abbr",
    "away_team_abbr",
    "actual_home_win",
    "predicted_home_win_probability",
}
REQUIRED_CLOSING_COLUMNS = {
    "game_date",
    "home_team_abbr",
    "away_team_abbr",
    "fair_home_probability",
    "timestamp_quality",
    "source_id",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clipped(values: pd.Series | np.ndarray) -> np.ndarray:
    return np.clip(np.asarray(values, dtype=float), EPS, 1.0 - EPS)


def loss_arrays(
    actual: pd.Series | np.ndarray,
    probability: pd.Series | np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    y = np.asarray(actual, dtype=float)
    p = clipped(probability)
    log_loss = -(y * np.log(p) + (1.0 - y) * np.log(1.0 - p))
    brier = (p - y) ** 2
    return log_loss, brier


def metric_summary(
    actual: pd.Series | np.ndarray,
    probability: pd.Series | np.ndarray,
) -> dict[str, float]:
    y = np.asarray(actual, dtype=float)
    p = clipped(probability)
    log_loss, brier = loss_arrays(y, p)
    return {
        "log_loss": float(log_loss.mean()),
        "brier_score": float(brier.mean()),
        "accuracy": float(((p >= 0.5).astype(int) == y.astype(int)).mean()),
        "mean_probability": float(p.mean()),
        "actual_rate": float(y.mean()),
    }


def bootstrap_mean_interval(
    values: np.ndarray,
    seed: int = 20260717,
    samples: int = 2000,
) -> dict[str, float]:
    array = np.asarray(values, dtype=float)
    if len(array) < 2:
        value = float(array.mean()) if len(array) else float("nan")
        return {"mean": value, "low_95": value, "high_95": value, "samples": 0}
    rng = np.random.default_rng(seed)
    means = np.empty(samples, dtype=float)
    size = len(array)
    for index in range(samples):
        means[index] = array[rng.integers(0, size, size=size)].mean()
    return {
        "mean": float(array.mean()),
        "low_95": float(np.quantile(means, 0.025)),
        "high_95": float(np.quantile(means, 0.975)),
        "samples": samples,
    }


def prepare_joined(predictions_path: Path, closing_path: Path) -> pd.DataFrame:
    predictions = pd.read_csv(predictions_path)
    closing = pd.read_csv(closing_path)
    missing_predictions = sorted(REQUIRED_PREDICTION_COLUMNS - set(predictions.columns))
    missing_closing = sorted(REQUIRED_CLOSING_COLUMNS - set(closing.columns))
    if missing_predictions or missing_closing:
        raise ValueError(
            f"missing prediction columns={missing_predictions}; "
            f"closing columns={missing_closing}"
        )
    if (closing["timestamp_quality"].astype(str) != "closing_label_only").any():
        raise ValueError("market residual analysis only accepts closing_label_only archives")

    keys = ["game_date", "home_team_abbr", "away_team_abbr"]
    for frame in (predictions, closing):
        frame["game_date"] = pd.to_datetime(
            frame["game_date"], errors="raise"
        ).dt.date.astype(str)
        frame["home_team_abbr"] = frame["home_team_abbr"].astype(str).str.upper().str.strip()
        frame["away_team_abbr"] = frame["away_team_abbr"].astype(str).str.upper().str.strip()
    if predictions.duplicated(keys).any():
        raise ValueError("predictions contain duplicate schedule keys")
    if closing.duplicated(keys).any():
        raise ValueError("closing archive contains duplicate schedule keys")

    optional_closing = [
        column
        for column in [
            "home_price_decimal",
            "away_price_decimal",
            "overround",
        ]
        if column in closing.columns
    ]
    joined = predictions.merge(
        closing[
            keys
            + ["fair_home_probability", "source_id", "timestamp_quality"]
            + optional_closing
        ],
        on=keys,
        how="inner",
        validate="one_to_one",
    )
    if joined.empty:
        raise ValueError("no closing rows matched predictions")
    joined = joined.sort_values(["game_date", "game_id"]).reset_index(drop=True)
    joined["actual_home_win"] = joined["actual_home_win"].astype(int)
    joined["model_probability"] = clipped(
        joined["predicted_home_win_probability"]
    )
    joined["market_probability"] = clipped(joined["fair_home_probability"])
    joined["model_minus_market_probability"] = (
        joined["model_probability"] - joined["market_probability"]
    )
    model_log, model_brier = loss_arrays(
        joined["actual_home_win"], joined["model_probability"]
    )
    market_log, market_brier = loss_arrays(
        joined["actual_home_win"], joined["market_probability"]
    )
    joined["model_minus_market_log_loss"] = model_log - market_log
    joined["model_minus_market_brier"] = model_brier - market_brier
    joined["model_better_log_score"] = (
        joined["model_minus_market_log_loss"] < 0
    ).astype(int)
    return joined


def group_summary(group: pd.DataFrame) -> dict[str, Any]:
    model = metric_summary(group["actual_home_win"], group["model_probability"])
    market = metric_summary(group["actual_home_win"], group["market_probability"])
    log_delta = group["model_minus_market_log_loss"].to_numpy(dtype=float)
    brier_delta = group["model_minus_market_brier"].to_numpy(dtype=float)
    return {
        "games": int(len(group)),
        "actual_home_win_rate": float(group["actual_home_win"].mean()),
        "mean_model_probability": float(group["model_probability"].mean()),
        "mean_market_probability": float(group["market_probability"].mean()),
        "mean_signed_disagreement": float(
            group["model_minus_market_probability"].mean()
        ),
        "mean_absolute_disagreement": float(
            group["model_minus_market_probability"].abs().mean()
        ),
        "model": model,
        "closing_market": market,
        "model_minus_market_log_loss": float(log_delta.mean()),
        "model_minus_market_brier": float(brier_delta.mean()),
        "model_better_log_score_rate": float(group["model_better_log_score"].mean()),
        "bootstrap_log_loss_delta": bootstrap_mean_interval(log_delta),
        "bootstrap_brier_delta": bootstrap_mean_interval(
            brier_delta, seed=20260718
        ),
    }


def grouped_table(frame: pd.DataFrame, column: str) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for label, group in frame.groupby(column, observed=True, sort=True):
        if len(group):
            output.append({"segment": str(label), **group_summary(group)})
    return output


def add_segments(joined: pd.DataFrame) -> pd.DataFrame:
    frame = joined.copy()
    frame["market_probability_band"] = pd.cut(
        frame["market_probability"],
        bins=[0.0, 0.35, 0.45, 0.55, 0.65, 1.000001],
        labels=["0-35%", "35-45%", "45-55%", "55-65%", "65-100%"],
        include_lowest=True,
        right=False,
    )
    frame["signed_disagreement_band"] = pd.cut(
        frame["model_minus_market_probability"],
        bins=[-1.000001, -0.10, -0.05, -0.02, 0.02, 0.05, 0.10, 1.000001],
        labels=[
            "<=-10pp",
            "-10 to -5pp",
            "-5 to -2pp",
            "-2 to +2pp",
            "+2 to +5pp",
            "+5 to +10pp",
            ">=+10pp",
        ],
        include_lowest=True,
        right=False,
    )
    frame["absolute_disagreement_band"] = pd.cut(
        frame["model_minus_market_probability"].abs(),
        bins=[0.0, 0.02, 0.05, 0.10, 0.15, 1.000001],
        labels=["0-2pp", "2-5pp", "5-10pp", "10-15pp", "15pp+"],
        include_lowest=True,
        right=False,
    )
    frame["direction_relationship"] = np.where(
        (frame["model_probability"] >= 0.5)
        == (frame["market_probability"] >= 0.5),
        "same_side",
        "opposite_side",
    )
    return frame


def select_blend_weight(train: pd.DataFrame) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    actual = train["actual_home_win"].to_numpy(dtype=float)
    market = train["market_probability"].to_numpy(dtype=float)
    model = train["model_probability"].to_numpy(dtype=float)
    for weight in WEIGHTS:
        probability = market + weight * (model - market)
        metrics = metric_summary(actual, probability)
        candidates.append({"model_residual_weight": weight, **metrics})
    candidates.sort(
        key=lambda row: (
            row["log_loss"],
            row["brier_score"],
            row["model_residual_weight"],
        )
    )
    return {"selected": candidates[0], "candidates": candidates}


def forward_holdout_blend(joined: pd.DataFrame) -> dict[str, Any]:
    seasons = sorted(
        joined["test_season"].astype(str).unique().tolist(),
        key=lambda value: int(value.split("-")[0]),
    )
    if len(seasons) < 2:
        return {
            "available": False,
            "reason": "at least two matched seasons are required",
            "training_seasons": seasons,
            "holdout_season": None,
        }
    holdout_season = seasons[-1]
    training_seasons = seasons[:-1]
    train = joined[
        joined["test_season"].astype(str).isin(training_seasons)
    ].copy()
    holdout = joined[
        joined["test_season"].astype(str) == holdout_season
    ].copy()
    if len(train) < 500 or len(holdout) < 250:
        return {
            "available": False,
            "reason": "insufficient temporal train or holdout games",
            "training_seasons": training_seasons,
            "holdout_season": holdout_season,
            "train_games": int(len(train)),
            "holdout_games": int(len(holdout)),
        }

    selection = select_blend_weight(train)
    weight = float(selection["selected"]["model_residual_weight"])
    market_probability = holdout["market_probability"].to_numpy(dtype=float)
    model_probability = holdout["model_probability"].to_numpy(dtype=float)
    blend_probability = market_probability + weight * (
        model_probability - market_probability
    )
    actual = holdout["actual_home_win"].to_numpy(dtype=float)

    market_log, market_brier = loss_arrays(actual, market_probability)
    blend_log, blend_brier = loss_arrays(actual, blend_probability)
    log_delta = blend_log - market_log
    brier_delta = blend_brier - market_brier
    log_interval = bootstrap_mean_interval(log_delta, seed=20260719)
    brier_interval = bootstrap_mean_interval(brier_delta, seed=20260720)
    blend = metric_summary(actual, blend_probability)
    market = metric_summary(actual, market_probability)
    model = metric_summary(actual, model_probability)

    improves_point_estimates = (
        blend["log_loss"] < market["log_loss"]
        and blend["brier_score"] < market["brier_score"]
    )
    statistically_supported = (
        log_interval["high_95"] < 0.0
        and brier_interval["high_95"] < 0.0
    )
    activated = (
        weight > 0.0 and improves_point_estimates and statistically_supported
    )

    return {
        "available": True,
        "method": (
            "train_past_seasons_select_linear_residual_weight_"
            "test_latest_season"
        ),
        "training_seasons": training_seasons,
        "holdout_season": holdout_season,
        "train_games": int(len(train)),
        "holdout_games": int(len(holdout)),
        "selected_model_residual_weight": weight,
        "training_selection": selection,
        "holdout": {
            "closing_market": market,
            "raw_model": model,
            "market_plus_model_residual": blend,
            "blend_minus_market_log_loss": float(log_delta.mean()),
            "blend_minus_market_brier": float(brier_delta.mean()),
            "bootstrap_log_loss_delta": log_interval,
            "bootstrap_brier_delta": brier_interval,
        },
        "decision": {
            "improves_both_point_estimates": improves_point_estimates,
            "bootstrap_supports_both_improvements": statistically_supported,
            "blend_candidate_activated": activated,
        },
    }


def analyze(
    predictions_path: Path,
    closing_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    joined = add_segments(prepare_joined(predictions_path, closing_path))
    seasons = sorted(
        joined["test_season"].astype(str).unique().tolist(),
        key=lambda value: int(value.split("-")[0]),
    )
    overall = group_summary(joined)
    forward = forward_holdout_blend(joined)
    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "coverage": {
            "matched_games": int(len(joined)),
            "matched_seasons": len(seasons),
            "seasons": seasons,
            "source_ids": sorted(
                joined["source_id"].astype(str).unique().tolist()
            ),
        },
        "overall": overall,
        "segments": {
            "by_season": grouped_table(joined, "test_season"),
            "by_market_probability": grouped_table(
                joined, "market_probability_band"
            ),
            "by_signed_model_market_disagreement": grouped_table(
                joined, "signed_disagreement_band"
            ),
            "by_absolute_model_market_disagreement": grouped_table(
                joined, "absolute_disagreement_band"
            ),
            "by_direction_relationship": grouped_table(
                joined, "direction_relationship"
            ),
        },
        "forward_holdout_blend": forward,
        "guardrails": {
            "closing_archive_has_exact_observation_timestamp": False,
            "closing_prices_used_as_base_forecast_only": True,
            "segment_search_is_exploratory": True,
            "joined_game_rows_written_to_artifact": False,
            "roi_computed": False,
            "clv_computed": False,
            "betting_edge_claim_allowed": False,
        },
        "decision": {
            "market_residual_analysis_complete": True,
            "ready_for_market_residual_research": (
                len(joined) >= 1000 and len(seasons) >= 2
            ),
            "forward_holdout_complete": bool(forward.get("available")),
            "incremental_model_signal_detected": bool(
                forward.get("decision", {}).get(
                    "blend_candidate_activated", False
                )
            ),
            "ready_for_production_market_blend": False,
            "ready_for_point_in_time_roi_backtest": False,
            "ready_for_clv_analysis": False,
            "ready_for_betting_edge_claim": False,
        },
    }
    (output_dir / "market-residual-analysis-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )

    rows: list[dict[str, Any]] = []
    for category, entries in report["segments"].items():
        for entry in entries:
            rows.append(
                {
                    "category": category,
                    "segment": entry["segment"],
                    "games": entry["games"],
                    "model_log_loss": entry["model"]["log_loss"],
                    "market_log_loss": entry["closing_market"]["log_loss"],
                    "model_minus_market_log_loss": entry[
                        "model_minus_market_log_loss"
                    ],
                    "model_brier": entry["model"]["brier_score"],
                    "market_brier": entry["closing_market"]["brier_score"],
                    "model_minus_market_brier": entry[
                        "model_minus_market_brier"
                    ],
                    "model_better_log_score_rate": entry[
                        "model_better_log_score_rate"
                    ],
                    "mean_signed_disagreement": entry[
                        "mean_signed_disagreement"
                    ],
                    "mean_absolute_disagreement": entry[
                        "mean_absolute_disagreement"
                    ],
                }
            )
    pd.DataFrame(rows).to_csv(
        output_dir / "market-residual-segment-summary.csv", index=False
    )
    return report


def self_test(output_dir: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="nbavl-market-residual-") as temp_name:
        root = Path(temp_name)
        predictions = root / "predictions.csv"
        closing = root / "closing.csv"
        rows_predictions: list[dict[str, Any]] = []
        rows_closing: list[dict[str, Any]] = []
        rng = np.random.default_rng(42)
        game_id = 0
        for season, count in (("2021-22", 600), ("2022-23", 300)):
            for _ in range(count):
                game_id += 1
                market = float(rng.uniform(0.25, 0.75))
                model = float(
                    np.clip(market + rng.normal(0, 0.05), 0.05, 0.95)
                )
                actual = int(rng.random() < market)
                date = (
                    pd.Timestamp("2021-10-01")
                    + pd.Timedelta(days=game_id)
                ).date().isoformat()
                home = f"H{game_id:04d}"
                away = f"A{game_id:04d}"
                rows_predictions.append(
                    {
                        "test_season": season,
                        "game_id": str(game_id),
                        "game_date": date,
                        "home_team_abbr": home,
                        "away_team_abbr": away,
                        "actual_home_win": actual,
                        "predicted_home_win_probability": model,
                    }
                )
                rows_closing.append(
                    {
                        "game_date": date,
                        "home_team_abbr": home,
                        "away_team_abbr": away,
                        "fair_home_probability": market,
                        "home_price_decimal": 1.0 / market,
                        "away_price_decimal": 1.0 / (1.0 - market),
                        "overround": 0.0,
                        "timestamp_quality": "closing_label_only",
                        "source_id": "self_test",
                    }
                )
        pd.DataFrame(rows_predictions).to_csv(predictions, index=False)
        pd.DataFrame(rows_closing).to_csv(closing, index=False)
        report = analyze(predictions, closing, output_dir)
        assert report["coverage"]["matched_games"] == 900
        assert report["forward_holdout_blend"]["available"] is True
        assert report["guardrails"]["roi_computed"] is False
        assert report["decision"]["ready_for_betting_edge_claim"] is False
        assert not (output_dir / "joined.csv").exists()
        (output_dir / "self-test.json").write_text(
            '{"passed":true}\n', encoding="utf-8"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--closing-odds", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("market residual analysis self-test passed")
        return
    if not args.predictions or not args.closing_odds:
        parser.error(
            "--predictions and --closing-odds are required unless --self-test is used"
        )
    report = analyze(args.predictions, args.closing_odds, args.output_dir)
    print(json.dumps(report["decision"], indent=2))


if __name__ == "__main__":
    main()
