#!/usr/bin/env python3
"""Train multi-season walk-forward NBA baseline models with point-in-time Elo."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import shutil
import sqlite3
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    log_loss,
    mean_absolute_error,
    mean_squared_error,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

MODEL_VERSION = "walk-forward-v2"
ELO_HOME_ADVANTAGE = 65.0
ELO_K = 20.0
ELO_OFFSEASON_RETENTION = 0.75
BASE_FEATURE_COLUMNS = [
    "net_rtg_last_5_diff",
    "net_rtg_last_10_diff",
    "net_rtg_last_20_diff",
    "pace_last_10_diff",
    "efg_pct_last_10_diff",
    "tov_pct_last_10_diff",
    "orb_pct_last_10_diff",
    "free_throw_rate_last_10_diff",
    "rest_days_diff",
    "evidence_coverage",
    "prior_games_min",
]
FEATURE_COLUMNS = BASE_FEATURE_COLUMNS + [
    "elo_rating_diff",
    "elo_home_win_probability",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ungzip(source: Path, destination: Path) -> None:
    with gzip.open(source, "rb") as src, destination.open("wb") as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)


def load_rows(gold_db: Path, silver_db: Path) -> list[dict[str, Any]]:
    gold = sqlite3.connect(gold_db)
    silver = sqlite3.connect(silver_db)
    try:
        games = {
            str(row[0]): row[1:]
            for row in silver.execute(
                "SELECT game_id, home_score, away_score, season_label FROM games "
                "WHERE home_score IS NOT NULL AND away_score IS NOT NULL"
            )
        }
        columns = [
            "game_id", "game_date", "home_team_abbr", "away_team_abbr",
            *BASE_FEATURE_COLUMNS,
        ]
        query = f"SELECT {', '.join(columns)} FROM gold_matchup_features ORDER BY game_date, game_id"
        rows: list[dict[str, Any]] = []
        for values in gold.execute(query):
            row = dict(zip(columns, values))
            target = games.get(str(row["game_id"]))
            if not target:
                continue
            home_score, away_score, season_label = target
            margin = int(home_score) - int(away_score)
            row.update(
                home_score=int(home_score),
                away_score=int(away_score),
                home_win=int(margin > 0),
                home_margin=margin,
                season_label=str(season_label),
            )
            rows.append(row)
        rows.sort(key=lambda item: (item["game_date"], item["game_id"]))
        return rows
    finally:
        gold.close()
        silver.close()


def add_point_in_time_elo(rows: list[dict[str, Any]]) -> None:
    ratings: dict[str, float] = {}
    current_season: str | None = None
    for row in rows:
        season = str(row["season_label"])
        if current_season is not None and season != current_season:
            ratings = {
                team: 1500.0 + ELO_OFFSEASON_RETENTION * (rating - 1500.0)
                for team, rating in ratings.items()
            }
        current_season = season

        home = str(row["home_team_abbr"])
        away = str(row["away_team_abbr"])
        home_rating = ratings.get(home, 1500.0)
        away_rating = ratings.get(away, 1500.0)
        rating_diff = (home_rating + ELO_HOME_ADVANTAGE) - away_rating
        probability = 1.0 / (1.0 + 10.0 ** (-rating_diff / 400.0))
        row["elo_rating_diff"] = round(rating_diff, 6)
        row["elo_home_win_probability"] = round(probability, 9)

        outcome = float(row["home_win"])
        adjustment = ELO_K * (outcome - probability)
        ratings[home] = home_rating + adjustment
        ratings[away] = away_rating - adjustment


def ordered_seasons(rows: list[dict[str, Any]]) -> list[str]:
    first_date: dict[str, str] = {}
    for row in rows:
        season = str(row["season_label"])
        first_date.setdefault(season, str(row["game_date"]))
    return sorted(first_date, key=lambda season: first_date[season])


def matrix(rows: list[dict[str, Any]]) -> np.ndarray:
    return np.asarray([[row.get(column) for column in FEATURE_COLUMNS] for row in rows], dtype=float)


def class_metrics(y_true: np.ndarray, probability: np.ndarray) -> dict[str, float | None]:
    probability = np.clip(probability, 1e-6, 1 - 1e-6)
    auc = None if len(np.unique(y_true)) < 2 else float(roc_auc_score(y_true, probability))
    return {
        "log_loss": float(log_loss(y_true, probability, labels=[0, 1])),
        "brier_score": float(brier_score_loss(y_true, probability)),
        "accuracy": float(accuracy_score(y_true, probability >= 0.5)),
        "roc_auc": auc,
    }


def reg_metrics(y_true: np.ndarray, prediction: np.ndarray) -> dict[str, float]:
    corr = 0.0
    if len(y_true) > 1 and float(np.std(prediction)) > 0 and float(np.std(y_true)) > 0:
        corr = float(np.corrcoef(y_true, prediction)[0, 1])
    return {
        "mae": float(mean_absolute_error(y_true, prediction)),
        "rmse": float(math.sqrt(mean_squared_error(y_true, prediction))),
        "correlation": corr,
    }


def calibration(y_true: np.ndarray, probability: np.ndarray) -> list[dict[str, float]]:
    observed, predicted = calibration_curve(y_true, probability, n_bins=10, strategy="quantile")
    return [
        {"mean_predicted": float(pred), "observed_rate": float(obs)}
        for pred, obs in zip(predicted, observed)
    ]


def create_models() -> tuple[Pipeline, Pipeline, DummyClassifier, DummyRegressor]:
    classifier = Pipeline([
        ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(max_iter=3000, C=0.5, random_state=42)),
    ])
    regressor = Pipeline([
        ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
        ("scaler", StandardScaler()),
        ("model", Ridge(alpha=15.0)),
    ])
    return classifier, regressor, DummyClassifier(strategy="prior"), DummyRegressor(strategy="mean")


def fit_models(rows: list[dict[str, Any]]) -> tuple[Pipeline, Pipeline, DummyClassifier, DummyRegressor]:
    X = matrix(rows)
    y_win = np.asarray([row["home_win"] for row in rows], dtype=int)
    y_margin = np.asarray([row["home_margin"] for row in rows], dtype=float)
    classifier, regressor, dummy_classifier, dummy_regressor = create_models()
    classifier.fit(X, y_win)
    regressor.fit(X, y_margin)
    dummy_classifier.fit(X, y_win)
    dummy_regressor.fit(X, y_margin)
    return classifier, regressor, dummy_classifier, dummy_regressor


def evaluate_fold(
    train_rows: list[dict[str, Any]],
    test_rows: list[dict[str, Any]],
    test_season: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    classifier, regressor, dummy_classifier, dummy_regressor = fit_models(train_rows)
    X = matrix(test_rows)
    y_win = np.asarray([row["home_win"] for row in test_rows], dtype=int)
    y_margin = np.asarray([row["home_margin"] for row in test_rows], dtype=float)
    probability = classifier.predict_proba(X)[:, 1]
    dummy_probability = dummy_classifier.predict_proba(X)[:, 1]
    elo_probability = np.asarray([row["elo_home_win_probability"] for row in test_rows], dtype=float)
    margin_prediction = regressor.predict(X)
    dummy_margin = dummy_regressor.predict(X)

    logistic_metrics = class_metrics(y_win, probability)
    elo_metrics = class_metrics(y_win, elo_probability)
    fold = {
        "test_season": test_season,
        "train_seasons": ordered_seasons(train_rows),
        "train_rows": len(train_rows),
        "test_rows": len(test_rows),
        "test_start_date": test_rows[0]["game_date"],
        "test_end_date": test_rows[-1]["game_date"],
        "logistic_elo": logistic_metrics,
        "elo_benchmark": elo_metrics,
        "dummy_probability": class_metrics(y_win, dummy_probability),
        "ridge_margin": reg_metrics(y_margin, margin_prediction),
        "dummy_margin": reg_metrics(y_margin, dummy_margin),
        "calibration": calibration(y_win, probability),
        "log_loss_gain_vs_elo": float(elo_metrics["log_loss"] - logistic_metrics["log_loss"]),
    }

    predictions: list[dict[str, Any]] = []
    for row, prob, elo_prob, dummy_prob, margin, baseline_margin in zip(
        test_rows,
        probability,
        elo_probability,
        dummy_probability,
        margin_prediction,
        dummy_margin,
    ):
        predictions.append({
            "test_season": test_season,
            "game_id": row["game_id"],
            "game_date": row["game_date"],
            "home_team_abbr": row["home_team_abbr"],
            "away_team_abbr": row["away_team_abbr"],
            "actual_home_win": row["home_win"],
            "actual_home_margin": row["home_margin"],
            "predicted_home_win_probability": round(float(prob), 8),
            "elo_home_win_probability": round(float(elo_prob), 8),
            "dummy_home_win_probability": round(float(dummy_prob), 8),
            "predicted_home_margin": round(float(margin), 6),
            "dummy_home_margin": round(float(baseline_margin), 6),
        })
    return fold, predictions


def aggregate_oof(predictions: list[dict[str, Any]]) -> dict[str, Any]:
    y_win = np.asarray([row["actual_home_win"] for row in predictions], dtype=int)
    logistic = np.asarray([row["predicted_home_win_probability"] for row in predictions], dtype=float)
    elo = np.asarray([row["elo_home_win_probability"] for row in predictions], dtype=float)
    dummy = np.asarray([row["dummy_home_win_probability"] for row in predictions], dtype=float)
    y_margin = np.asarray([row["actual_home_margin"] for row in predictions], dtype=float)
    ridge = np.asarray([row["predicted_home_margin"] for row in predictions], dtype=float)
    dummy_margin = np.asarray([row["dummy_home_margin"] for row in predictions], dtype=float)
    logistic_metrics = class_metrics(y_win, logistic)
    elo_metrics = class_metrics(y_win, elo)
    return {
        "rows": len(predictions),
        "logistic_elo": logistic_metrics,
        "elo_benchmark": elo_metrics,
        "dummy_probability": class_metrics(y_win, dummy),
        "ridge_margin": reg_metrics(y_margin, ridge),
        "dummy_margin": reg_metrics(y_margin, dummy_margin),
        "calibration": calibration(y_win, logistic),
        "log_loss_gain_vs_elo": float(elo_metrics["log_loss"] - logistic_metrics["log_loss"]),
    }


def train_walk_forward(rows: list[dict[str, Any]], output_dir: Path) -> dict[str, Any]:
    if not rows:
        raise ValueError("No completed matchup rows available")
    add_point_in_time_elo(rows)
    seasons = ordered_seasons(rows)
    if len(seasons) < 3:
        raise ValueError(f"Walk-forward training requires at least 3 seasons, got {seasons}")

    folds: list[dict[str, Any]] = []
    predictions: list[dict[str, Any]] = []
    # Require two complete prior seasons before a season becomes an OOF test fold.
    for test_index in range(2, len(seasons)):
        test_season = seasons[test_index]
        train_season_set = set(seasons[:test_index])
        train_rows = [row for row in rows if row["season_label"] in train_season_set]
        test_rows = [row for row in rows if row["season_label"] == test_season]
        fold, fold_predictions = evaluate_fold(train_rows, test_rows, test_season)
        folds.append(fold)
        predictions.extend(fold_predictions)

    output_dir.mkdir(parents=True, exist_ok=True)
    final_classifier, final_regressor, _, _ = fit_models(rows)
    model_metadata = {
        "features": FEATURE_COLUMNS,
        "version": MODEL_VERSION,
        "training_seasons": seasons,
        "elo": {
            "home_advantage": ELO_HOME_ADVANTAGE,
            "k": ELO_K,
            "offseason_retention": ELO_OFFSEASON_RETENTION,
        },
    }
    joblib.dump(
        {"model": final_classifier, **model_metadata},
        output_dir / "home-win-logistic-elo-v2.joblib",
    )
    joblib.dump(
        {"model": final_regressor, **model_metadata},
        output_dir / "home-margin-ridge-elo-v2.joblib",
    )

    with (output_dir / "walk-forward-predictions.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(predictions[0]))
        writer.writeheader()
        writer.writerows(predictions)

    aggregate = aggregate_oof(predictions)
    latest = folds[-1]
    report = {
        "model_version": MODEL_VERSION,
        "generated_at": utc_now(),
        "dataset": {
            "rows": len(rows),
            "seasons": seasons,
            "season_count": len(seasons),
            "features": FEATURE_COLUMNS,
            "walk_forward_fold_count": len(folds),
            "first_game_date": rows[0]["game_date"],
            "last_game_date": rows[-1]["game_date"],
        },
        "elo_policy": {
            "home_advantage": ELO_HOME_ADVANTAGE,
            "k": ELO_K,
            "offseason_retention": ELO_OFFSEASON_RETENTION,
            "point_in_time": True,
        },
        "walk_forward": {
            "minimum_prior_seasons": 2,
            "folds": folds,
            "aggregate_oof": aggregate,
            "latest_season_test": latest,
        },
        "guardrails": {
            "season_ordered_walk_forward": True,
            "random_shuffle": False,
            "gold_point_in_time_features_only": True,
            "elo_updated_after_each_completed_game": True,
            "rolling_features_reset_each_season": True,
            "odds_used_for_training": False,
        },
        "decision": {
            "ready_for_calibration_pilot": (
                len(seasons) >= 5
                and aggregate["logistic_elo"]["log_loss"] < aggregate["dummy_probability"]["log_loss"]
            ),
            "incremental_value_over_elo_detected": aggregate["log_loss_gain_vs_elo"] > 0,
            "ready_for_market_odds_backtest": False,
            "reason": "Market backtesting remains blocked until point-in-time odds and closing-line data are joined.",
        },
    }
    (output_dir / "walk-forward-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def synthetic_rows() -> list[dict[str, Any]]:
    rng = np.random.default_rng(42)
    teams = [f"T{index:02d}" for index in range(12)]
    base_strength = {team: float(rng.normal(0, 1)) for team in teams}
    rows: list[dict[str, Any]] = []
    for season_start in range(2019, 2024):
        season = f"{season_start}-{str(season_start + 1)[-2:]}"
        season_strength = {
            team: 0.7 * base_strength[team] + float(rng.normal(0, 0.5))
            for team in teams
        }
        start = date(season_start, 10, 1)
        for index in range(180):
            home = teams[index % len(teams)]
            away = teams[(index * 5 + 1) % len(teams)]
            if away == home:
                away = teams[(teams.index(away) + 1) % len(teams)]
            signal = season_strength[home] - season_strength[away] + 0.35
            margin = int(round(7.0 * signal + rng.normal(0, 10)))
            game_day = start + timedelta(days=index // 6)
            row = {column: float(rng.normal()) for column in BASE_FEATURE_COLUMNS}
            row["net_rtg_last_5_diff"] = 5.0 * signal + float(rng.normal(0, 2))
            row["net_rtg_last_10_diff"] = 6.0 * signal + float(rng.normal(0, 1.5))
            row["net_rtg_last_20_diff"] = 6.5 * signal + float(rng.normal(0, 1.2))
            row["evidence_coverage"] = min(1.0, index / 60.0)
            row["prior_games_min"] = min(20, index // 6)
            row.update({
                "game_id": f"{season_start}-g{index:04d}",
                "game_date": game_day.isoformat(),
                "home_team_abbr": home,
                "away_team_abbr": away,
                "home_win": int(margin > 0),
                "home_margin": margin,
                "season_label": season,
            })
            rows.append(row)
    rows.sort(key=lambda item: (item["game_date"], item["game_id"]))
    return rows


def self_test(output_dir: Path) -> None:
    report = train_walk_forward(synthetic_rows(), output_dir)
    assert report["dataset"]["season_count"] == 5
    assert report["dataset"]["walk_forward_fold_count"] == 3
    assert report["walk_forward"]["aggregate_oof"]["rows"] == 540
    assert (output_dir / "home-win-logistic-elo-v2.joblib").exists()
    assert (output_dir / "home-margin-ridge-elo-v2.joblib").exists()
    (output_dir / "self-test.json").write_text('{"passed":true}\n', encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold-db", type=Path)
    parser.add_argument("--silver-db", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("walk-forward model self-test passed")
        return
    if not args.gold_db or not args.silver_db:
        parser.error("--gold-db and --silver-db are required unless --self-test is used")

    with tempfile.TemporaryDirectory(prefix="nbavl-walk-forward-") as temp_name:
        temp = Path(temp_name)
        gold = temp / "gold.sqlite"
        silver = temp / "silver.sqlite"
        ungzip(args.gold_db, gold)
        ungzip(args.silver_db, silver)
        report = train_walk_forward(load_rows(gold, silver), args.output_dir)
    print(json.dumps(report["decision"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
