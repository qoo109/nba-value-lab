#!/usr/bin/env python3
"""Leakage-safe NBA schedule and travel context experiment.

Consumes point-in-time Gold team-game rows and out-of-fold walk-forward predictions.
The latest OOF season is held out once; no game outcomes are used to construct context.
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import shutil
import sqlite3
import tempfile
from collections import Counter, defaultdict
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, mean_absolute_error, mean_squared_error, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

VERSION = "feature-expansion-v3-context-pilot"
EPSILON = 1e-6
CLASSIFIER_CANDIDATES = (0.02, 0.05, 0.1, 0.25, 0.5, 1.0)
RIDGE_ALPHA_CANDIDATES = (1.0, 5.0, 15.0, 30.0, 60.0)
SCHEDULE_FEATURES = [
    "home_rest_days_capped", "away_rest_days_capped", "context_rest_days_diff",
    "home_is_back_to_back", "away_is_back_to_back", "back_to_back_diff",
    "home_games_last_3_days", "away_games_last_3_days", "games_last_3_days_diff",
    "home_games_last_7_days", "away_games_last_7_days", "games_last_7_days_diff",
    "home_three_in_four", "away_three_in_four", "three_in_four_diff",
    "home_four_in_six", "away_four_in_six", "four_in_six_diff",
    "home_five_in_eight", "away_five_in_eight", "five_in_eight_diff",
]
TRAVEL_FEATURES = [
    "home_travel_km_since_previous", "away_travel_km_since_previous", "travel_km_since_previous_diff",
    "home_travel_km_last_7_days", "away_travel_km_last_7_days", "travel_km_last_7_days_diff",
    "home_timezone_shift_hours", "away_timezone_shift_hours", "timezone_shift_hours_diff",
    "home_abs_timezone_shift_hours", "away_abs_timezone_shift_hours", "abs_timezone_shift_hours_diff",
    "home_eastward_shift_hours", "away_eastward_shift_hours", "eastward_shift_hours_diff",
    "home_westward_shift_hours", "away_westward_shift_hours", "westward_shift_hours_diff",
    "home_altitude_gain_m", "away_altitude_gain_m", "altitude_gain_m_diff",
    "home_road_trip_game_number", "away_road_trip_game_number", "road_trip_game_number_diff",
    "home_same_venue_streak", "away_same_venue_streak", "same_venue_streak_diff",
    "home_back_to_back_travel_km", "away_back_to_back_travel_km", "back_to_back_travel_km_diff",
]
FEATURE_GROUPS = {
    "recalibration_only": [],
    "schedule_context": SCHEDULE_FEATURES,
    "travel_context": TRAVEL_FEATURES,
    "schedule_plus_travel": SCHEDULE_FEATURES + TRAVEL_FEATURES,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_date(value: Any) -> date:
    return date.fromisoformat(str(value).strip()[:10])


def load_venue_config(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    venues = payload.get("venues")
    if not isinstance(venues, dict) or not venues:
        raise ValueError("venue config must contain a non-empty venues object")
    required = {"latitude", "longitude", "timezone", "elevation_m"}
    for key, value in venues.items():
        missing = required - set(value)
        if missing:
            raise ValueError(f"venue {key} missing {sorted(missing)}")
        ZoneInfo(str(value["timezone"]))
    return venues


def haversine_km(left: dict[str, Any], right: dict[str, Any]) -> float:
    radius = 6371.0088
    lat1, lat2 = math.radians(float(left["latitude"])), math.radians(float(right["latitude"]))
    dlat = lat2 - lat1
    dlon = math.radians(float(right["longitude"]) - float(left["longitude"]))
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return round(2 * radius * math.asin(math.sqrt(a)), 3)


def utc_offset_hours(venue: dict[str, Any], game_day: date) -> float:
    local = datetime.combine(game_day, time(hour=12), tzinfo=ZoneInfo(str(venue["timezone"])))
    offset = local.utcoffset()
    if offset is None:
        raise ValueError("timezone offset unavailable")
    return offset.total_seconds() / 3600


def venue_for_game(season: str, game_day: date, home_team: str) -> tuple[str, str]:
    if season == "2019-20" and game_day >= date(2020, 7, 30):
        return "ORLANDO_BUBBLE", "major_override_orlando_bubble"
    if season == "2020-21" and home_team == "TOR":
        return "TORONTO_TAMPA", "major_override_toronto_tampa"
    return home_team, "team_home_venue_proxy"


def load_gold_team_rows(source: Path) -> pd.DataFrame:
    with tempfile.TemporaryDirectory(prefix="nbavl-context-gold-") as temp_name:
        db_path = source
        if source.suffix == ".gz":
            db_path = Path(temp_name) / "historical-gold.sqlite"
            with gzip.open(source, "rb") as src, db_path.open("wb") as dst:
                shutil.copyfileobj(src, dst, length=1024 * 1024)
        db = sqlite3.connect(db_path)
        try:
            frame = pd.read_sql_query(
                """SELECT game_id, game_date, season_label, team_abbr, opponent_abbr,
                          is_home, days_rest, is_back_to_back,
                          games_last_3_days, games_last_7_days
                   FROM gold_team_game_features
                   ORDER BY season_label, game_date, game_id, team_abbr""",
                db,
            )
        finally:
            db.close()
    if frame.empty:
        raise ValueError("Gold database has no team-game feature rows")
    frame["game_id"] = frame["game_id"].astype(str)
    frame["game_date"] = pd.to_datetime(frame["game_date"], errors="raise").dt.date.astype(str)
    return frame


def count_prior_within(history: list[dict[str, Any]], game_day: date, days: int) -> int:
    return sum(0 < (game_day - item["game_day"]).days <= days for item in history)


def consecutive(history: list[dict[str, Any]], predicate) -> int:
    count = 0
    for item in reversed(history):
        if not predicate(item):
            break
        count += 1
    return count


def team_context(
    is_home: int,
    gold_row: dict[str, Any],
    game_day: date,
    venue_key: str,
    venue_quality: str,
    history: list[dict[str, Any]],
    venues: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    current = venues[venue_key]
    previous = history[-1] if history else None
    if previous is None:
        travel_km = timezone_shift = altitude_gain = 0.0
        previous_missing = 1
    else:
        prior_venue = venues[previous["venue_key"]]
        travel_km = haversine_km(prior_venue, current)
        timezone_shift = utc_offset_hours(current, game_day) - utc_offset_hours(prior_venue, game_day)
        altitude_gain = float(current["elevation_m"]) - float(prior_venue["elevation_m"])
        previous_missing = 0
    prior_travel_7 = sum(
        float(item["travel_km_to_game"])
        for item in history
        if 0 < (game_day - item["game_day"]).days <= 7
    )
    neutral = venue_quality != "team_home_venue_proxy"
    road_trip_number = 0
    if not is_home and not neutral:
        road_trip_number = 1 + consecutive(
            history,
            lambda item: item["is_home"] == 0 and item["venue_quality"] == "team_home_venue_proxy",
        )
    same_venue_streak = 1 + consecutive(history, lambda item: item["venue_key"] == venue_key)
    days_rest = gold_row.get("days_rest")
    days_rest = None if pd.isna(days_rest) else int(days_rest)
    games_3 = int(gold_row.get("games_last_3_days") or 0)
    games_7 = int(gold_row.get("games_last_7_days") or 0)
    b2b = int(gold_row.get("is_back_to_back") or 0)
    return {
        "previous_venue_missing": previous_missing,
        "rest_days_capped": None if days_rest is None else min(days_rest, 7),
        "is_back_to_back": b2b,
        "games_last_3_days": games_3,
        "games_last_7_days": games_7,
        "three_in_four": int(games_3 >= 2),
        "four_in_six": int(count_prior_within(history, game_day, 5) >= 3),
        "five_in_eight": int(count_prior_within(history, game_day, 7) >= 4),
        "travel_km_since_previous": travel_km,
        "travel_km_last_7_days": round(prior_travel_7 + travel_km, 3),
        "timezone_shift_hours": round(timezone_shift, 3),
        "abs_timezone_shift_hours": round(abs(timezone_shift), 3),
        "eastward_shift_hours": round(max(timezone_shift, 0.0), 3),
        "westward_shift_hours": round(max(-timezone_shift, 0.0), 3),
        "altitude_gain_m": round(altitude_gain, 3),
        "road_trip_game_number": road_trip_number,
        "same_venue_streak": same_venue_streak,
        "back_to_back_travel_km": travel_km if b2b else 0.0,
        "history_record": {
            "game_day": game_day,
            "venue_key": venue_key,
            "is_home": int(is_home),
            "venue_quality": venue_quality,
            "travel_km_to_game": travel_km,
        },
    }


def put_side(output: dict[str, Any], prefix: str, context: dict[str, Any]) -> None:
    for key in (
        "rest_days_capped", "is_back_to_back", "games_last_3_days", "games_last_7_days",
        "three_in_four", "four_in_six", "five_in_eight", "travel_km_since_previous",
        "travel_km_last_7_days", "timezone_shift_hours", "abs_timezone_shift_hours",
        "eastward_shift_hours", "westward_shift_hours", "altitude_gain_m",
        "road_trip_game_number", "same_venue_streak", "back_to_back_travel_km",
    ):
        output[f"{prefix}_{key}"] = context[key]


def add_diff(output: dict[str, Any], suffix: str, target: str) -> None:
    left, right = output.get(f"home_{suffix}"), output.get(f"away_{suffix}")
    output[target] = None if left is None or right is None else round(float(left) - float(right), 6)


def build_context_matchups(team_rows: pd.DataFrame, venues: dict[str, dict[str, Any]]) -> tuple[pd.DataFrame, dict[str, Any]]:
    missing_venues = sorted(set(team_rows["team_abbr"].astype(str)) - set(venues))
    if missing_venues:
        raise ValueError(f"venue config missing teams: {missing_venues}")
    games = []
    for game_id, sides in team_rows.groupby("game_id", sort=False):
        home, away = sides[sides["is_home"] == 1], sides[sides["is_home"] == 0]
        if len(home) != 1 or len(away) != 1:
            continue
        h, a = home.iloc[0].to_dict(), away.iloc[0].to_dict()
        games.append({
            "game_id": str(game_id), "game_date": str(h["game_date"]), "season_label": str(h["season_label"]),
            "home_team_abbr": str(h["team_abbr"]), "away_team_abbr": str(a["team_abbr"]),
            "home_gold": h, "away_gold": a,
        })
    games.sort(key=lambda item: (item["season_label"], item["game_date"], item["game_id"]))
    rows, quality_counts, previous_missing = [], Counter(), 0
    for season in sorted({item["season_label"] for item in games}):
        history: dict[str, list[dict[str, Any]]] = defaultdict(list)
        grouped: dict[date, list[dict[str, Any]]] = defaultdict(list)
        for item in games:
            if item["season_label"] == season:
                grouped[parse_date(item["game_date"])].append(item)
        for game_day in sorted(grouped):
            updates = []
            for item in grouped[game_day]:
                venue_key, venue_quality = venue_for_game(season, game_day, item["home_team_abbr"])
                quality_counts[venue_quality] += 1
                hc = team_context(1, item["home_gold"], game_day, venue_key, venue_quality, history[item["home_team_abbr"]], venues)
                ac = team_context(0, item["away_gold"], game_day, venue_key, venue_quality, history[item["away_team_abbr"]], venues)
                previous_missing += hc["previous_venue_missing"] + ac["previous_venue_missing"]
                output = {
                    "game_id": item["game_id"], "game_date": item["game_date"], "season_label": season,
                    "home_team_abbr": item["home_team_abbr"], "away_team_abbr": item["away_team_abbr"],
                    "venue_key": venue_key, "venue_quality": venue_quality,
                }
                put_side(output, "home", hc)
                put_side(output, "away", ac)
                for suffix, target in (
                    ("rest_days_capped", "context_rest_days_diff"),
                    ("is_back_to_back", "back_to_back_diff"),
                    ("games_last_3_days", "games_last_3_days_diff"),
                    ("games_last_7_days", "games_last_7_days_diff"),
                    ("three_in_four", "three_in_four_diff"),
                    ("four_in_six", "four_in_six_diff"),
                    ("five_in_eight", "five_in_eight_diff"),
                    ("travel_km_since_previous", "travel_km_since_previous_diff"),
                    ("travel_km_last_7_days", "travel_km_last_7_days_diff"),
                    ("timezone_shift_hours", "timezone_shift_hours_diff"),
                    ("abs_timezone_shift_hours", "abs_timezone_shift_hours_diff"),
                    ("eastward_shift_hours", "eastward_shift_hours_diff"),
                    ("westward_shift_hours", "westward_shift_hours_diff"),
                    ("altitude_gain_m", "altitude_gain_m_diff"),
                    ("road_trip_game_number", "road_trip_game_number_diff"),
                    ("same_venue_streak", "same_venue_streak_diff"),
                    ("back_to_back_travel_km", "back_to_back_travel_km_diff"),
                ):
                    add_diff(output, suffix, target)
                rows.append(output)
                updates.extend([
                    (item["home_team_abbr"], hc["history_record"]),
                    (item["away_team_abbr"], ac["history_record"]),
                ])
            for team, record in updates:
                history[team].append(record)
    frame = pd.DataFrame(rows)
    if frame.empty or frame["game_id"].duplicated().any():
        raise ValueError("invalid matchup context output")
    return frame, {
        "matchup_rows": int(len(frame)),
        "season_count": int(frame["season_label"].nunique()),
        "venue_quality_counts": dict(sorted(quality_counts.items())),
        "previous_venue_missing_team_rows": int(previous_missing),
        "strict_same_date_boundary": True,
        "travel_assumption": "direct_previous_game_venue_to_current_game_venue",
    }


def clip_probability(values: np.ndarray) -> np.ndarray:
    return np.clip(values.astype(float), EPSILON, 1 - EPSILON)


def logits(values: np.ndarray) -> np.ndarray:
    values = clip_probability(values)
    return np.log(values / (1 - values))


def classification_metrics(y_true: np.ndarray, probability: np.ndarray) -> dict[str, float | None]:
    probability = clip_probability(probability)
    return {
        "log_loss": float(log_loss(y_true, probability, labels=[0, 1])),
        "brier_score": float(brier_score_loss(y_true, probability)),
        "accuracy": float(accuracy_score(y_true, probability >= 0.5)),
        "roc_auc": None if len(np.unique(y_true)) < 2 else float(roc_auc_score(y_true, probability)),
    }


def margin_metrics(y_true: np.ndarray, prediction: np.ndarray) -> dict[str, float]:
    return {
        "mae": float(mean_absolute_error(y_true, prediction)),
        "rmse": float(math.sqrt(mean_squared_error(y_true, prediction))),
        "correlation": float(np.corrcoef(y_true, prediction)[0, 1]) if len(y_true) > 1 and np.std(y_true) > 0 and np.std(prediction) > 0 else 0.0,
    }


def classifier_pipeline(c_value: float) -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(C=c_value, max_iter=4000, random_state=42)),
    ])


def ridge_pipeline(alpha: float) -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
        ("scaler", StandardScaler()),
        ("model", Ridge(alpha=alpha)),
    ])


def design(frame: pd.DataFrame, group: str, baseline_column: str, probability: bool) -> tuple[np.ndarray, list[str]]:
    features = FEATURE_GROUPS[group]
    baseline = frame[baseline_column].to_numpy(dtype=float)
    baseline_name = baseline_column
    if probability:
        baseline, baseline_name = logits(baseline), "baseline_probability_logit"
    pieces = [baseline.reshape(-1, 1)]
    if features:
        pieces.append(frame[features].to_numpy(dtype=float))
    return np.column_stack(pieces), [baseline_name, *features]


def select_classifier(dev: pd.DataFrame, validation: pd.DataFrame) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    y_dev, y_val = dev["actual_home_win"].to_numpy(dtype=int), validation["actual_home_win"].to_numpy(dtype=int)
    candidates = []
    for group in FEATURE_GROUPS:
        x_dev, columns = design(dev, group, "predicted_home_win_probability", True)
        x_val, _ = design(validation, group, "predicted_home_win_probability", True)
        for c_value in CLASSIFIER_CANDIDATES:
            model = classifier_pipeline(c_value)
            model.fit(x_dev, y_dev)
            candidates.append({
                "feature_group": group, "c": c_value, "feature_count": len(columns),
                **classification_metrics(y_val, model.predict_proba(x_val)[:, 1]),
            })
    candidates.sort(key=lambda item: (item["log_loss"], item["brier_score"], item["feature_count"], item["c"]))
    return candidates[0], candidates


def select_ridge(dev: pd.DataFrame, validation: pd.DataFrame) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    y_dev, y_val = dev["actual_home_margin"].to_numpy(dtype=float), validation["actual_home_margin"].to_numpy(dtype=float)
    candidates = []
    for group in FEATURE_GROUPS:
        x_dev, columns = design(dev, group, "predicted_home_margin", False)
        x_val, _ = design(validation, group, "predicted_home_margin", False)
        for alpha in RIDGE_ALPHA_CANDIDATES:
            model = ridge_pipeline(alpha)
            model.fit(x_dev, y_dev)
            candidates.append({
                "feature_group": group, "alpha": alpha, "feature_count": len(columns),
                **margin_metrics(y_val, model.predict(x_val)),
            })
    candidates.sort(key=lambda item: (item["mae"], item["rmse"], item["feature_count"], item["alpha"]))
    return candidates[0], candidates


def paired_bootstrap(differences: np.ndarray, seed: int, iterations: int = 5000) -> dict[str, Any]:
    values = np.asarray(differences, dtype=float)
    rng, means = np.random.default_rng(seed), np.empty(iterations, dtype=float)
    for index in range(iterations):
        means[index] = float(np.mean(values[rng.integers(0, len(values), size=len(values))]))
    return {
        "mean_delta": float(np.mean(values)),
        "ci95_low": float(np.quantile(means, 0.025)),
        "ci95_high": float(np.quantile(means, 0.975)),
        "bootstrap_probability_improvement": float(np.mean(means < 0)),
        "iterations": iterations,
    }


def coefficient_rows(model: Pipeline, columns: list[str], group: str, model_type: str) -> list[dict[str, Any]]:
    values = np.ravel(model.named_steps["model"].coef_)
    names = list(columns) + [f"missing_indicator_{index}" for index in range(max(0, len(values) - len(columns)))]
    return [
        {"model_type": model_type, "feature_group": group, "feature": names[index], "standardized_coefficient": float(value)}
        for index, value in enumerate(values)
    ]


def join_predictions(context: pd.DataFrame, predictions: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    pred = pd.read_csv(predictions)
    required = {
        "test_season", "game_id", "game_date", "home_team_abbr", "away_team_abbr",
        "actual_home_win", "actual_home_margin", "predicted_home_win_probability", "predicted_home_margin",
    }
    missing = sorted(required - set(pred.columns))
    if missing:
        raise ValueError(f"walk-forward predictions missing columns: {missing}")
    pred["game_id"] = pred["game_id"].astype(str)
    joined = pred.merge(context, on="game_id", how="inner", suffixes=("_prediction", "_context"), validate="one_to_one")
    mismatched = joined[
        (joined["game_date_prediction"].astype(str) != joined["game_date_context"].astype(str))
        | (joined["home_team_abbr_prediction"].astype(str) != joined["home_team_abbr_context"].astype(str))
        | (joined["away_team_abbr_prediction"].astype(str) != joined["away_team_abbr_context"].astype(str))
    ]
    if not mismatched.empty:
        raise ValueError(f"prediction/context schedule mismatches: {len(mismatched)}")
    joined = joined.rename(columns={
        "game_date_prediction": "game_date", "home_team_abbr_prediction": "home_team_abbr",
        "away_team_abbr_prediction": "away_team_abbr",
    }).drop(columns=["game_date_context", "home_team_abbr_context", "away_team_abbr_context", "season_label"])
    if len(joined) != len(pred):
        raise ValueError(f"context coverage incomplete: predictions={len(pred)} matched={len(joined)}")
    return joined, {"prediction_rows": int(len(pred)), "matched_rows": int(len(joined)), "match_rate": float(len(joined) / len(pred)), "schedule_mismatches": 0}


def run_experiment(joined: pd.DataFrame, output_dir: Path, context_qa: dict[str, Any]) -> dict[str, Any]:
    seasons = list(dict.fromkeys(joined.sort_values(["game_date", "game_id"])["test_season"].astype(str)))
    if len(seasons) < 3:
        raise ValueError(f"requires at least three OOF seasons, got {seasons}")
    dev_season, validation_season, holdout_season = seasons[-3:]
    dev = joined[joined["test_season"] == dev_season].copy()
    validation = joined[joined["test_season"] == validation_season].copy()
    holdout = joined[joined["test_season"] == holdout_season].copy()
    if min(len(dev), len(validation), len(holdout)) < 500:
        raise ValueError("each experiment season must have at least 500 games")

    selected_class, class_candidates = select_classifier(dev, validation)
    train = pd.concat([dev, validation], ignore_index=True)
    x_train, class_columns = design(train, selected_class["feature_group"], "predicted_home_win_probability", True)
    x_holdout, _ = design(holdout, selected_class["feature_group"], "predicted_home_win_probability", True)
    classifier = classifier_pipeline(float(selected_class["c"]))
    classifier.fit(x_train, train["actual_home_win"].to_numpy(dtype=int))
    corrected_prob = classifier.predict_proba(x_holdout)[:, 1]
    baseline_prob = holdout["predicted_home_win_probability"].to_numpy(dtype=float)
    y = holdout["actual_home_win"].to_numpy(dtype=int)
    base_class, corrected_class = classification_metrics(y, baseline_prob), classification_metrics(y, corrected_prob)
    base_losses = -(y * np.log(clip_probability(baseline_prob)) + (1 - y) * np.log(clip_probability(1 - baseline_prob)))
    corrected_losses = -(y * np.log(clip_probability(corrected_prob)) + (1 - y) * np.log(clip_probability(1 - corrected_prob)))
    logloss_boot = paired_bootstrap(corrected_losses - base_losses, 20260717)
    brier_boot = paired_bootstrap((corrected_prob - y) ** 2 - (baseline_prob - y) ** 2, 20260718)

    selected_margin, margin_candidates = select_ridge(dev, validation)
    x_m_train, margin_columns = design(train, selected_margin["feature_group"], "predicted_home_margin", False)
    x_m_holdout, _ = design(holdout, selected_margin["feature_group"], "predicted_home_margin", False)
    ridge = ridge_pipeline(float(selected_margin["alpha"]))
    ridge.fit(x_m_train, train["actual_home_margin"].to_numpy(dtype=float))
    corrected_margin = ridge.predict(x_m_holdout)
    baseline_margin = holdout["predicted_home_margin"].to_numpy(dtype=float)
    y_margin = holdout["actual_home_margin"].to_numpy(dtype=float)
    base_margin, corrected_margin_metrics = margin_metrics(y_margin, baseline_margin), margin_metrics(y_margin, corrected_margin)
    mae_boot = paired_bootstrap(np.abs(corrected_margin - y_margin) - np.abs(baseline_margin - y_margin), 20260719)

    probability_signal = (
        selected_class["feature_group"] != "recalibration_only"
        and corrected_class["log_loss"] < base_class["log_loss"]
        and corrected_class["brier_score"] < base_class["brier_score"]
        and logloss_boot["ci95_high"] < 0 and brier_boot["ci95_high"] < 0
    )
    recalibration_signal = (
        selected_class["feature_group"] == "recalibration_only"
        and corrected_class["log_loss"] < base_class["log_loss"]
        and corrected_class["brier_score"] < base_class["brier_score"]
        and logloss_boot["ci95_high"] < 0 and brier_boot["ci95_high"] < 0
    )
    margin_signal = (
        selected_margin["feature_group"] != "recalibration_only"
        and corrected_margin_metrics["mae"] < base_margin["mae"]
        and corrected_margin_metrics["rmse"] < base_margin["rmse"]
        and mae_boot["ci95_high"] < 0
    )
    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "method": {
            "probability_model": "logistic correction around OOF baseline logit",
            "margin_model": "ridge correction around OOF baseline margin",
            "model_selection": f"{dev_season} fit, {validation_season} validation",
            "untouched_holdout": holdout_season,
            "feature_groups": FEATURE_GROUPS,
            "classifier_c_grid": list(CLASSIFIER_CANDIDATES),
            "ridge_alpha_grid": list(RIDGE_ALPHA_CANDIDATES),
        },
        "coverage": {
            "matched_games": int(len(joined)), "matched_seasons": seasons,
            "development_rows": int(len(dev)), "validation_rows": int(len(validation)), "holdout_rows": int(len(holdout)),
            "context_qa": context_qa,
        },
        "probability_experiment": {
            "selected_on_validation": selected_class, "validation_candidates": class_candidates,
            "holdout_baseline": base_class, "holdout_corrected": corrected_class,
            "holdout_delta_corrected_minus_baseline": {
                key: None if corrected_class[key] is None or base_class[key] is None else float(corrected_class[key] - base_class[key])
                for key in base_class
            },
            "paired_bootstrap_log_loss": logloss_boot, "paired_bootstrap_brier": brier_boot,
        },
        "margin_experiment": {
            "selected_on_validation": selected_margin, "validation_candidates": margin_candidates,
            "holdout_baseline": base_margin, "holdout_corrected": corrected_margin_metrics,
            "holdout_delta_corrected_minus_baseline": {key: float(corrected_margin_metrics[key] - base_margin[key]) for key in base_margin},
            "paired_bootstrap_mae": mae_boot,
        },
        "decision": {
            "context_probability_signal_detected": bool(probability_signal),
            "recalibration_only_signal_detected": bool(recalibration_signal),
            "context_margin_signal_detected": bool(margin_signal),
            "ready_to_promote_context_features_to_gold_v2_pilot": bool(probability_signal or margin_signal),
            "ready_for_production_model": False,
            "ready_for_betting_edge_claim": False,
            "next_step": "add injury and lineup snapshot schema after context holdout review",
        },
        "guardrails": {
            "uses_only_point_in_time_schedule_history": True,
            "same_date_games_excluded_from_history": True,
            "uses_market_odds": False,
            "uses_future_games": False,
            "uses_game_outcomes_for_feature_construction": False,
            "travel_is_venue_proxy": True,
            "neutral_sites_fully_enumerated": False,
            "injury_or_lineup_data_included": False,
            "game_level_predictions_uploaded": False,
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "feature-expansion-v3-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    pd.DataFrame(
        [{"model_type": "probability", **item} for item in class_candidates]
        + [{"model_type": "margin", **item} for item in margin_candidates]
    ).to_csv(output_dir / "feature-expansion-v3-candidate-summary.csv", index=False)
    pd.DataFrame(
        coefficient_rows(classifier, class_columns, selected_class["feature_group"], "probability")
        + coefficient_rows(ridge, margin_columns, selected_margin["feature_group"], "margin")
    ).to_csv(output_dir / "feature-expansion-v3-coefficients.csv", index=False)
    return report


def run(gold: Path, predictions: Path, venue_config: Path, output_dir: Path) -> dict[str, Any]:
    context, context_qa = build_context_matchups(load_gold_team_rows(gold), load_venue_config(venue_config))
    joined, join_qa = join_predictions(context, predictions)
    context_qa["prediction_join"] = join_qa
    report = run_experiment(joined, output_dir, context_qa)
    status = {
        "schema_version": VERSION, "generated_at": utc_now(), "feature_expansion_complete": True,
        "matched_games": report["coverage"]["matched_games"], "holdout_season": report["method"]["untouched_holdout"],
        "context_probability_signal_detected": report["decision"]["context_probability_signal_detected"],
        "context_margin_signal_detected": report["decision"]["context_margin_signal_detected"],
        "game_level_rows_written": False,
    }
    (output_dir / "feature-expansion-v3-run-status.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    return status


def self_test(output_dir: Path, venue_config: Path) -> None:
    rng, teams = np.random.default_rng(42), ["ATL", "BOS", "DEN", "LAL"]
    team_rows, predictions, game_number = [], [], 0
    for season_index, season in enumerate(["2021-22", "2022-23", "2023-24"]):
        start = date(2021 + season_index, 10, 15)
        team_dates: dict[str, list[date]] = defaultdict(list)
        for index in range(600):
            game_number += 1
            game_day = date.fromordinal(start.toordinal() + index // 4)
            home, away = teams[(index + season_index) % 4], teams[(index + 1 + 2 * season_index) % 4]
            if home == away:
                away = teams[(teams.index(away) + 1) % 4]
            game_id = f"synthetic-{game_number}"
            for team, opponent, is_home in ((home, away, 1), (away, home, 0)):
                prior = team_dates[team]
                gap = (game_day - prior[-1]).days if prior else None
                team_rows.append({
                    "game_id": game_id, "game_date": game_day.isoformat(), "season_label": season,
                    "team_abbr": team, "opponent_abbr": opponent, "is_home": is_home,
                    "days_rest": None if gap is None else max(gap - 1, 0),
                    "is_back_to_back": int(gap == 1) if gap is not None else 0,
                    "games_last_3_days": sum(0 < (game_day - value).days <= 3 for value in prior),
                    "games_last_7_days": sum(0 < (game_day - value).days <= 7 for value in prior),
                })
            team_dates[home].append(game_day)
            team_dates[away].append(game_day)
            base_logit = 0.25 + (0.4 if home == "DEN" else 0) - (0.25 if away == "DEN" else 0)
            probability = 1 / (1 + math.exp(-base_logit))
            actual, margin = int(rng.random() < probability), float(rng.normal((probability - 0.5) * 24, 12))
            predictions.append({
                "test_season": season, "game_id": game_id, "game_date": game_day.isoformat(),
                "home_team_abbr": home, "away_team_abbr": away, "actual_home_win": actual,
                "actual_home_margin": margin,
                "predicted_home_win_probability": min(max(probability + rng.normal(0, 0.03), 0.05), 0.95),
                "predicted_home_margin": margin + rng.normal(0, 10),
            })
    context, qa = build_context_matchups(pd.DataFrame(team_rows), load_venue_config(venue_config))
    with tempfile.TemporaryDirectory(prefix="nbavl-context-self-test-") as temp_name:
        prediction_path = Path(temp_name) / "predictions.csv"
        pd.DataFrame(predictions).to_csv(prediction_path, index=False)
        joined, join_qa = join_predictions(context, prediction_path)
        qa["prediction_join"] = join_qa
        report = run_experiment(joined, output_dir, qa)
    assert report["coverage"]["matched_games"] == 1800
    assert report["guardrails"]["uses_market_odds"] is False
    assert report["decision"]["ready_for_production_model"] is False
    (output_dir / "self-test.json").write_text('{"passed":true}\n', encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold", type=Path)
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--venue-config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir, args.venue_config)
        print("Feature Expansion v3 self-test passed")
        return
    if not args.gold or not args.predictions:
        parser.error("--gold and --predictions are required unless --self-test is used")
    print(json.dumps(run(args.gold, args.predictions, args.venue_config, args.output_dir), indent=2))


if __name__ == "__main__":
    main()
