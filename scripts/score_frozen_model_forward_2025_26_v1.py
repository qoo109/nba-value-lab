#!/usr/bin/env python3
"""Build 2025-26 forward Gold and score the frozen walk-forward-v2 model.

No fitting, calibration, threshold selection, or market data is allowed here.
The script preserves the exact frozen classifier, reconstructs the model's Elo
state through the original 5,824-game training population, carries state through
2024-25, builds strictly pre-game 2025-26 Gold rows, and scores each 2025-26
regular-season game before updating Elo with that game's outcome.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import shutil
import sqlite3
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score

from build_historical_gold import build_matchups, insert_dicts, load_rows, load_silver
from build_historical_gold_multiseason import (
    build_team_features,
    source_version,
    validate_point_in_time,
)
from historical_gold_schema import (
    GOLD_FEATURE_VERSION,
    GOLD_SCHEMA_VERSION,
    create_gold_schema,
)

FORMAL_PASS = "FROZEN_MODEL_FORWARD_SCORE_2025_26_PASS"
FORMAL_BLOCKED = "FROZEN_MODEL_FORWARD_SCORE_2025_26_BLOCKED"
EXPECTED_FEATURES = [
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
    "elo_rating_diff",
    "elo_home_win_probability",
]
BASE_FEATURES = EXPECTED_FEATURES[:-2]
ELO_HOME_ADVANTAGE = 65.0
ELO_K = 20.0
ELO_OFFSEASON_RETENTION = 0.75
FROZEN_TRAINING_EXCLUSIONS = {"22301177", "22301195"}
EXPECTED_MODEL_SHA256 = "007ce32cc5a80df3b87554d13847d388e2ca6cbf6122f00df2d4e87d5b49a343"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def ungzip(source: Path, destination: Path) -> None:
    with gzip.open(source, "rb") as src, destination.open("wb") as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)


def load_completed_games(
    source: Path,
    working_dir: Path,
    name: str,
    exclusions: set[str] | None = None,
) -> list[dict[str, Any]]:
    sqlite_path = working_dir / f"{name}.sqlite"
    ungzip(source, sqlite_path)
    db = sqlite3.connect(sqlite_path)
    db.row_factory = sqlite3.Row
    rows = []
    try:
        for row in db.execute(
            """
            SELECT game_id, game_date, season_label, home_team_abbr,
                   away_team_abbr, home_score, away_score
            FROM games
            WHERE game_date IS NOT NULL
              AND home_team_abbr IS NOT NULL
              AND away_team_abbr IS NOT NULL
              AND home_score IS NOT NULL
              AND away_score IS NOT NULL
            ORDER BY game_date, game_id
            """
        ):
            item = dict(row)
            if exclusions and str(item["game_id"]) in exclusions:
                continue
            item["home_score"] = int(item["home_score"])
            item["away_score"] = int(item["away_score"])
            item["home_win"] = int(item["home_score"] > item["away_score"])
            rows.append(item)
    finally:
        db.close()
    return rows


def build_forward_gold(
    silver_2025_26: Path,
    output_dir: Path,
    working_dir: Path,
) -> tuple[Path, list[dict[str, Any]], dict[str, Any]]:
    silver_path = load_silver(silver_2025_26, working_dir)
    silver = sqlite3.connect(silver_path)
    try:
        source_ver = source_version(silver)
        silver_rows, games = load_rows(silver)
    finally:
        silver.close()
    if len(games) != 1230 or len(silver_rows) != 2460:
        raise RuntimeError(
            f"unexpected 2025-26 Silver population: games={len(games)}, team_rows={len(silver_rows)}"
        )
    generated_at = utc_now()
    team_rows = build_team_features(silver_rows, generated_at, source_ver)
    matchup_rows = build_matchups(team_rows, games, generated_at, source_ver)
    point_in_time = validate_point_in_time(team_rows, silver_rows)
    if not point_in_time["passed"]:
        raise RuntimeError(f"forward Gold point-in-time validation failed: {point_in_time}")
    if len(team_rows) != 2460 or len(matchup_rows) != 1230:
        raise RuntimeError(
            f"unexpected forward Gold population: team={len(team_rows)}, matchup={len(matchup_rows)}"
        )

    gold_path = output_dir / "forward-gold-2025-26.sqlite"
    gold = sqlite3.connect(gold_path)
    create_gold_schema(gold)
    insert_dicts(gold, "gold_team_game_features", team_rows)
    insert_dicts(gold, "gold_matchup_features", matchup_rows)
    gold.executemany(
        "INSERT INTO gold_metadata VALUES (?,?)",
        {
            "pipeline_name": "NBA Value Lab frozen-model forward Gold 2025-26",
            "schema_version": GOLD_SCHEMA_VERSION,
            "feature_version": GOLD_FEATURE_VERSION,
            "source_version": source_ver,
            "feature_generated_at": generated_at,
            "point_in_time_rule": "same_season_source_game_date_less_than_target_game_date",
            "same_day_games_policy": "excluded_from_each_other",
            "season_history_policy": "rolling_features_reset_for_2025_26",
            "season_labels": "2025-26",
            "model_retraining_executed": "false",
            "market_data_used": "false",
        }.items(),
    )
    gold.commit()
    gold.execute("VACUUM")
    gold.close()

    gzip_path = output_dir / "forward-gold-2025-26.sqlite.gz"
    with gold_path.open("rb") as src, gzip.open(gzip_path, "wb", compresslevel=6) as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)
    gold_path.unlink()
    gold_report = {
        "team_rows": len(team_rows),
        "matchup_rows": len(matchup_rows),
        "point_in_time": point_in_time,
        "mature_matchups_prior_20_both_sides": sum(
            int(row["prior_games_min"]) >= 20 for row in matchup_rows
        ),
        "low_evidence_matchups": sum(float(row["evidence_coverage"]) < 0.25 for row in matchup_rows),
        "source_version": source_ver,
        "database_gzip_bytes": gzip_path.stat().st_size,
        "database_gzip_sha256": sha256_file(gzip_path),
    }
    return gzip_path, matchup_rows, gold_report


def add_forward_elo(
    historical_rows: list[dict[str, Any]],
    season_2024_25_rows: list[dict[str, Any]],
    season_2025_26_rows: list[dict[str, Any]],
) -> dict[str, dict[str, float]]:
    all_rows = historical_rows + season_2024_25_rows + season_2025_26_rows
    all_rows.sort(key=lambda row: (str(row["game_date"]), str(row["game_id"])))
    ratings: dict[str, float] = {}
    current_season: str | None = None
    forward: dict[str, dict[str, float]] = {}
    season_counts = defaultdict(int)

    for row in all_rows:
        season = str(row["season_label"])
        if current_season is not None and season != current_season:
            ratings = {
                team: 1500.0 + ELO_OFFSEASON_RETENTION * (rating - 1500.0)
                for team, rating in ratings.items()
            }
        current_season = season
        season_counts[season] += 1
        home = str(row["home_team_abbr"])
        away = str(row["away_team_abbr"])
        home_rating = ratings.get(home, 1500.0)
        away_rating = ratings.get(away, 1500.0)
        rating_diff = (home_rating + ELO_HOME_ADVANTAGE) - away_rating
        probability = 1.0 / (1.0 + 10.0 ** (-rating_diff / 400.0))
        if season == "2025-26":
            forward[str(row["game_id"])] = {
                "elo_home_rating": round(home_rating, 6),
                "elo_away_rating": round(away_rating, 6),
                "elo_rating_diff": round(rating_diff, 6),
                "elo_home_win_probability": round(probability, 9),
            }
        adjustment = ELO_K * (float(row["home_win"]) - probability)
        ratings[home] = home_rating + adjustment
        ratings[away] = away_rating - adjustment

    expected_counts = {
        "2019-20": 1056,
        "2020-21": 1080,
        "2021-22": 1230,
        "2022-23": 1230,
        "2023-24": 1228,
        "2024-25": 1230,
        "2025-26": 1230,
    }
    if dict(season_counts) != expected_counts:
        raise RuntimeError(f"frozen Elo population mismatch: {dict(season_counts)}")
    if len(forward) != 1230:
        raise RuntimeError(f"expected 1,230 forward Elo rows, found {len(forward)}")
    return forward


def class_metrics(y_true: np.ndarray, probability: np.ndarray) -> dict[str, float]:
    probability = np.clip(probability, 1e-6, 1 - 1e-6)
    return {
        "log_loss": float(log_loss(y_true, probability, labels=[0, 1])),
        "brier_score": float(brier_score_loss(y_true, probability)),
        "accuracy": float(accuracy_score(y_true, probability >= 0.5)),
        "roc_auc": float(roc_auc_score(y_true, probability)),
    }


def reliability(y_true: np.ndarray, probability: np.ndarray) -> dict[str, Any]:
    bins = []
    weighted_gap = 0.0
    max_gap = 0.0
    for index in range(10):
        lower = index / 10
        upper = (index + 1) / 10
        mask = (probability >= lower) & (probability < upper if index < 9 else probability <= upper)
        count = int(mask.sum())
        if count == 0:
            continue
        mean_probability = float(probability[mask].mean())
        observed = float(y_true[mask].mean())
        gap = abs(mean_probability - observed)
        weighted_gap += count * gap
        max_gap = max(max_gap, gap)
        bins.append({
            "lower": lower,
            "upper": upper,
            "rows": count,
            "mean_predicted": mean_probability,
            "observed_rate": observed,
            "absolute_gap": gap,
        })
    return {
        "binning": "equal_width_10",
        "ece": weighted_gap / len(y_true),
        "mce": max_gap,
        "bins": bins,
    }


def confidence_thresholds(y_true: np.ndarray, probability: np.ndarray) -> list[dict[str, Any]]:
    selected_probability = np.maximum(probability, 1.0 - probability)
    selected_correct = np.where(probability >= 0.5, y_true == 1, y_true == 0)
    output = []
    for threshold in (0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80):
        mask = selected_probability >= threshold
        rows = int(mask.sum())
        output.append({
            "minimum_selected_side_probability": threshold,
            "rows": rows,
            "coverage": rows / len(y_true),
            "accuracy": float(selected_correct[mask].mean()) if rows else None,
            "mean_selected_side_probability": float(selected_probability[mask].mean()) if rows else None,
        })
    return output


def paired_bootstrap(
    y_true: np.ndarray,
    model_probability: np.ndarray,
    elo_probability: np.ndarray,
    resamples: int = 5000,
    seed: int = 20260724,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    logloss_diff = []
    brier_diff = []
    accuracy_diff = []
    n = len(y_true)
    for _ in range(resamples):
        index = rng.integers(0, n, size=n)
        y = y_true[index]
        model = np.clip(model_probability[index], 1e-6, 1 - 1e-6)
        elo = np.clip(elo_probability[index], 1e-6, 1 - 1e-6)
        logloss_diff.append(float(log_loss(y, model, labels=[0, 1]) - log_loss(y, elo, labels=[0, 1])))
        brier_diff.append(float(brier_score_loss(y, model) - brier_score_loss(y, elo)))
        accuracy_diff.append(float(accuracy_score(y, model >= 0.5) - accuracy_score(y, elo >= 0.5)))

    def summarize(values: list[float], lower_is_better: bool) -> dict[str, Any]:
        array = np.asarray(values)
        return {
            "mean": float(array.mean()),
            "ci95": [float(np.quantile(array, 0.025)), float(np.quantile(array, 0.975))],
            "probability_model_better": float((array < 0).mean() if lower_is_better else (array > 0).mean()),
        }

    return {
        "resamples": resamples,
        "seed": seed,
        "model_minus_elo_log_loss": summarize(logloss_diff, True),
        "model_minus_elo_brier": summarize(brier_diff, True),
        "model_minus_elo_accuracy": summarize(accuracy_diff, False),
    }


def score(
    historical_silver: Path,
    silver_2024_25: Path,
    silver_2025_26: Path,
    model_dir: Path,
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="nbavl-forward-score-") as temp_name:
        temp = Path(temp_name)
        gold_gzip, matchup_rows, gold_report = build_forward_gold(silver_2025_26, output_dir, temp)
        historical_rows = load_completed_games(
            historical_silver, temp, "historical-2019-24", FROZEN_TRAINING_EXCLUSIONS
        )
        rows_2024 = load_completed_games(silver_2024_25, temp, "silver-2024-25")
        rows_2025 = load_completed_games(silver_2025_26, temp, "silver-2025-26")
        if len(historical_rows) != 5824 or len(rows_2024) != 1230 or len(rows_2025) != 1230:
            raise RuntimeError(
                f"unexpected Silver populations: historical={len(historical_rows)}, "
                f"2024-25={len(rows_2024)}, 2025-26={len(rows_2025)}"
            )
        forward_elo = add_forward_elo(historical_rows, rows_2024, rows_2025)
        outcomes = {str(row["game_id"]): row for row in rows_2025}

        model_path = model_dir / "home-win-logistic-elo-v2.joblib"
        model_sha256 = sha256_file(model_path)
        if model_sha256 != EXPECTED_MODEL_SHA256:
            raise RuntimeError(f"frozen model hash mismatch: {model_sha256}")
        artifact = joblib.load(model_path)
        if artifact["version"] != "walk-forward-v2":
            raise RuntimeError(f"unexpected model version: {artifact['version']}")
        if artifact["features"] != EXPECTED_FEATURES:
            raise RuntimeError(f"frozen feature contract changed: {artifact['features']}")
        if artifact["training_seasons"] != ["2019-20", "2020-21", "2021-22", "2022-23", "2023-24"]:
            raise RuntimeError(f"unexpected frozen training seasons: {artifact['training_seasons']}")
        if artifact["elo"] != {
            "home_advantage": ELO_HOME_ADVANTAGE,
            "k": ELO_K,
            "offseason_retention": ELO_OFFSEASON_RETENTION,
        }:
            raise RuntimeError(f"frozen Elo contract changed: {artifact['elo']}")

        rows = []
        for matchup in sorted(matchup_rows, key=lambda item: (item["game_date"], item["game_id"])):
            game_id = str(matchup["game_id"])
            outcome = outcomes.get(game_id)
            elo = forward_elo.get(game_id)
            if not outcome or not elo:
                raise RuntimeError(f"forward join failed for game {game_id}")
            row = {
                "season_label": "2025-26",
                "game_id": game_id,
                "game_date": matchup["game_date"],
                "home_team_abbr": matchup["home_team_abbr"],
                "away_team_abbr": matchup["away_team_abbr"],
                **{column: matchup.get(column) for column in BASE_FEATURES},
                **elo,
                "actual_home_win": int(outcome["home_win"]),
                "actual_home_margin": int(outcome["home_score"] - outcome["away_score"]),
            }
            rows.append(row)

        X = np.asarray([[row.get(column) for column in EXPECTED_FEATURES] for row in rows], dtype=float)
        probability = artifact["model"].predict_proba(X)[:, 1]
        elo_probability = np.asarray([row["elo_home_win_probability"] for row in rows], dtype=float)
        y_true = np.asarray([row["actual_home_win"] for row in rows], dtype=int)
        for row, prob in zip(rows, probability):
            row["predicted_home_win_probability"] = round(float(prob), 9)
            row["predicted_away_win_probability"] = round(float(1.0 - prob), 9)
            row["selected_side"] = row["home_team_abbr"] if prob >= 0.5 else row["away_team_abbr"]
            row["selected_side_probability"] = round(float(max(prob, 1.0 - prob)), 9)
            row["selected_side_correct"] = int((prob >= 0.5) == bool(row["actual_home_win"]))

        predictions_path = output_dir / "frozen-model-forward-predictions-2025-26.csv"
        public_fields = [
            "season_label", "game_id", "game_date", "home_team_abbr", "away_team_abbr",
            "predicted_home_win_probability", "predicted_away_win_probability",
            "elo_home_win_probability", "selected_side", "selected_side_probability",
            "actual_home_win", "actual_home_margin", "selected_side_correct",
        ]
        with predictions_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=public_fields)
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row[field] for field in public_fields})

        model_metrics = class_metrics(y_true, probability)
        elo_metrics = class_metrics(y_true, elo_probability)
        report = {
            "schema_version": "frozen-model-forward-score-2025-26-v1",
            "formal_state": FORMAL_PASS,
            "generated_at_utc": utc_now(),
            "season_label": "2025-26",
            "frozen_model": {
                "artifact_file": "home-win-logistic-elo-v2.joblib",
                "sha256": model_sha256,
                "version": artifact["version"],
                "training_seasons": artifact["training_seasons"],
                "feature_columns": artifact["features"],
                "fit_or_refit_calls_executed": 0,
                "calibration_applied": False,
                "selected_probability_method": "raw_logistic_elo",
            },
            "population": {
                "frozen_training_elo_games": len(historical_rows),
                "frozen_training_exclusions": sorted(FROZEN_TRAINING_EXCLUSIONS),
                "state_update_games_2024_25": len(rows_2024),
                "forward_scored_games_2025_26": len(rows),
                "first_game_date": rows[0]["game_date"],
                "last_game_date": rows[-1]["game_date"],
            },
            "forward_gold": gold_report,
            "probability_quality": {
                "model": model_metrics,
                "elo_benchmark": elo_metrics,
                "model_minus_elo": {
                    "log_loss": model_metrics["log_loss"] - elo_metrics["log_loss"],
                    "brier_score": model_metrics["brier_score"] - elo_metrics["brier_score"],
                    "accuracy": model_metrics["accuracy"] - elo_metrics["accuracy"],
                    "roc_auc": model_metrics["roc_auc"] - elo_metrics["roc_auc"],
                },
                "reliability": reliability(y_true, probability),
                "confidence_thresholds": confidence_thresholds(y_true, probability),
                "paired_game_bootstrap_vs_elo": paired_bootstrap(y_true, probability, elo_probability),
            },
            "outputs": {
                "forward_gold_sqlite_gzip": gold_gzip.name,
                "forward_gold_sqlite_gzip_sha256": sha256_file(gold_gzip),
                "predictions_csv": predictions_path.name,
                "predictions_csv_sha256": sha256_file(predictions_path),
                "prediction_rows": len(rows),
                "raw_source_rows_emitted": 0,
                "odds_rows_emitted": 0,
            },
            "qualification": {
                "model_only_forward_probability_diagnostic_valid": True,
                "ready_for_private_same_game_odds_sensitivity_join": True,
                "strict_t60_qualified": False,
                "market_backtest_allowed": False,
                "clv_allowed": False,
                "roi_allowed": False,
                "betting_edge_claim_allowed": False,
                "formal_stake": 0,
            },
            "execution": {
                "model_retraining_executed": False,
                "model_refit_executed": False,
                "market_data_used_as_model_feature": False,
                "odds_join_executed": False,
                "provider_api_requests": 0,
            },
            "next_unique_sub_mainline": "JOIN_2025_26_FORWARD_PROBABILITIES_TO_PRIVATE_ALIGNED_ODDS_FOR_TIME_BANDED_SENSITIVITY_ONLY",
        }
        report_path = output_dir / "frozen-model-forward-score-2025-26-report-v1.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return report


def self_test(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    y = np.asarray([0, 1, 1, 0], dtype=int)
    p = np.asarray([0.2, 0.8, 0.6, 0.4], dtype=float)
    metrics = class_metrics(y, p)
    checks = {
        "perfect_accuracy": metrics["accuracy"] == 1.0,
        "confidence_rows": confidence_thresholds(y, p)[0]["rows"] == 4,
        "reliability_rows": sum(row["rows"] for row in reliability(y, p)["bins"]) == 4,
    }
    if not all(checks.values()):
        raise AssertionError(checks)
    (output_dir / "self-test.json").write_text(json.dumps({"passed": True, "checks": checks}, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--historical-silver", type=Path)
    parser.add_argument("--silver-2024-25", type=Path)
    parser.add_argument("--silver-2025-26", type=Path)
    parser.add_argument("--model-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("frozen forward scoring self-test passed")
        return 0
    required = [args.historical_silver, args.silver_2024_25, args.silver_2025_26, args.model_dir]
    if any(value is None for value in required):
        parser.error("all Silver inputs and --model-dir are required")
    report = score(
        args.historical_silver,
        args.silver_2024_25,
        args.silver_2025_26,
        args.model_dir,
        args.output_dir,
    )
    print(json.dumps(report["probability_quality"], ensure_ascii=False, indent=2))
    return 0 if report["formal_state"] == FORMAL_PASS else 2


if __name__ == "__main__":
    raise SystemExit(main())
