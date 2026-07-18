#!/usr/bin/env python3
"""Execute the predeclared Injury Feature Walk-forward Holdout v1.

The baseline is the frozen walk-forward-v2 out-of-fold probability. The only
primary candidate is a bounded, regularized injury logit offset fit separately
inside each chronological training fold. No market odds or target-game
participation labels are used as prediction features.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    log_loss,
    mean_absolute_error,
    mean_squared_error,
    roc_auc_score,
)

VERSION = "injury-feature-walk-forward-holdout-v1"
PRIMARY_FEATURES = [
    "weighted_unavailable_minutes_home_minus_away",
    "weighted_absence_impact_positive_home_minus_away",
]
PROBABILITY_CLIP = (1e-6, 1.0 - 1e-6)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if fields:
            writer.writeheader()
            writer.writerows(rows)


def sigmoid(value: np.ndarray) -> np.ndarray:
    positive = value >= 0
    output = np.empty_like(value, dtype=float)
    output[positive] = 1.0 / (1.0 + np.exp(-value[positive]))
    exp_value = np.exp(value[~positive])
    output[~positive] = exp_value / (1.0 + exp_value)
    return output


def clipped_logit(probability: np.ndarray) -> np.ndarray:
    probability = np.clip(probability.astype(float), *PROBABILITY_CLIP)
    return np.log(probability / (1.0 - probability))


def binary_log_loss(y: np.ndarray, probability: np.ndarray) -> float:
    probability = np.clip(probability.astype(float), *PROBABILITY_CLIP)
    return float(log_loss(y.astype(int), probability, labels=[0, 1]))


def class_metrics(y: np.ndarray, probability: np.ndarray) -> dict[str, float | None]:
    probability = np.clip(probability.astype(float), *PROBABILITY_CLIP)
    auc = None if len(np.unique(y)) < 2 else float(roc_auc_score(y, probability))
    return {
        "rows": int(len(y)),
        "log_loss": binary_log_loss(y, probability),
        "brier_score": float(brier_score_loss(y, probability)),
        "accuracy": float(accuracy_score(y, probability >= 0.5)),
        "roc_auc": auc,
    }


def calibration_metrics(y: np.ndarray, probability: np.ndarray) -> dict[str, float | None]:
    """Fit diagnostic calibration intercept/slope on held-out labels."""
    if len(y) < 3 or len(np.unique(y)) < 2:
        return {"calibration_intercept": None, "calibration_slope": None}
    x = clipped_logit(probability)

    def objective(parameters: np.ndarray) -> float:
        intercept, slope = parameters
        predicted = sigmoid(intercept + slope * x)
        return binary_log_loss(y, predicted)

    result = minimize(
        objective,
        np.asarray([0.0, 1.0], dtype=float),
        method="L-BFGS-B",
        options={"maxiter": 2000, "ftol": 1e-12},
    )
    if not result.success or not np.all(np.isfinite(result.x)):
        return {"calibration_intercept": None, "calibration_slope": None}
    return {
        "calibration_intercept": float(result.x[0]),
        "calibration_slope": float(result.x[1]),
    }


def equal_frequency_ece(y: np.ndarray, probability: np.ndarray, bins: int = 10) -> float:
    if len(y) == 0:
        return float("nan")
    order = np.argsort(probability)
    groups = np.array_split(order, min(bins, len(order)))
    weighted = 0.0
    for indexes in groups:
        if len(indexes) == 0:
            continue
        gap = abs(float(np.mean(probability[indexes])) - float(np.mean(y[indexes])))
        weighted += len(indexes) * gap
    return weighted / len(y)


def margin_metrics(y: np.ndarray, prediction: np.ndarray) -> dict[str, float]:
    return {
        "rows": int(len(y)),
        "mae": float(mean_absolute_error(y, prediction)),
        "rmse": float(math.sqrt(mean_squared_error(y, prediction))),
    }


def standardize_train_test(
    train: np.ndarray,
    test: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    means = np.mean(train, axis=0)
    scales = np.std(train, axis=0, ddof=0)
    if np.any(~np.isfinite(means)) or np.any(~np.isfinite(scales)) or np.any(scales <= 0):
        raise ValueError("training fold contains a missing or zero-variance injury feature")
    return (train - means) / scales, (test - means) / scales, means, scales


def fit_probability_offset(
    baseline_probability: np.ndarray,
    features: np.ndarray,
    outcome: np.ndarray,
    policy: dict[str, Any],
) -> tuple[np.ndarray, dict[str, Any]]:
    fit = policy["primary_candidate"]["fit"]
    baseline_logit = clipped_logit(baseline_probability)
    alpha = float(fit["l2_alpha"])
    initial = np.asarray(fit["initial_coefficients"], dtype=float)
    bounds = [tuple(map(float, fit["coefficient_bounds"]))] * features.shape[1]

    def objective(coefficients: np.ndarray) -> float:
        probability = sigmoid(baseline_logit + features @ coefficients)
        return binary_log_loss(outcome, probability) + 0.5 * alpha * float(coefficients @ coefficients)

    result = minimize(
        objective,
        initial,
        method=str(fit["optimizer"]),
        bounds=bounds,
        options={
            "maxiter": int(fit["maximum_iterations"]),
            "ftol": float(fit["tolerance"]),
        },
    )
    if not result.success or not np.all(np.isfinite(result.x)):
        raise RuntimeError(f"probability optimizer failed: {result.message}")
    return result.x.astype(float), {
        "success": bool(result.success),
        "message": str(result.message),
        "iterations": int(result.nit),
        "objective": float(result.fun),
    }


def fit_margin_offset(
    baseline_margin: np.ndarray,
    features: np.ndarray,
    actual_margin: np.ndarray,
    policy: dict[str, Any],
) -> tuple[np.ndarray, dict[str, Any]]:
    settings = policy["secondary_margin_candidate"]
    alpha = float(settings["l2_alpha"])
    bounds = [tuple(map(float, settings["coefficient_bounds"]))] * features.shape[1]
    initial = np.zeros(features.shape[1], dtype=float)

    def objective(coefficients: np.ndarray) -> float:
        residual = actual_margin - (baseline_margin + features @ coefficients)
        return float(np.mean(residual * residual)) + 0.5 * alpha * float(coefficients @ coefficients)

    result = minimize(
        objective,
        initial,
        method=str(settings["optimizer"]),
        bounds=bounds,
        options={"maxiter": 2000, "ftol": 1e-9},
    )
    if not result.success or not np.all(np.isfinite(result.x)):
        raise RuntimeError(f"margin optimizer failed: {result.message}")
    return result.x.astype(float), {
        "success": bool(result.success),
        "message": str(result.message),
        "iterations": int(result.nit),
        "objective": float(result.fun),
    }


def coverage_band(value: float) -> str:
    if value >= 1.0 - 1e-12:
        return "1.00"
    if value >= 0.90:
        return "0.90_to_below_1.00"
    if value >= 0.75:
        return "0.75_to_below_0.90"
    return "BELOW_0.75"


def minutes_before_tip_band(value: float) -> str:
    if value < 120:
        return "60_to_below_120"
    if value < 240:
        return "120_to_below_240"
    return "240_plus"


def quartile_thresholds(values: np.ndarray) -> list[float]:
    return [float(item) for item in np.quantile(values, [0.25, 0.5, 0.75], method="linear")]


def quartile_band(value: float, thresholds: list[float]) -> str:
    if value <= thresholds[0]:
        return "Q1"
    if value <= thresholds[1]:
        return "Q2"
    if value <= thresholds[2]:
        return "Q3"
    return "Q4"


def paired_bootstrap(
    y: np.ndarray,
    baseline: np.ndarray,
    candidate: np.ndarray,
    policy: dict[str, Any],
    label: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    settings = policy["paired_bootstrap"]
    replicates = int(settings["replicates"])
    seed = int(settings["seed"])
    rng = np.random.default_rng(seed)
    n = len(y)

    baseline = np.clip(baseline.astype(float), *PROBABILITY_CLIP)
    candidate = np.clip(candidate.astype(float), *PROBABILITY_CLIP)
    y = y.astype(float)
    baseline_nll = -(y * np.log(baseline) + (1.0 - y) * np.log(1.0 - baseline))
    candidate_nll = -(y * np.log(candidate) + (1.0 - y) * np.log(1.0 - candidate))
    per_game_log_gain = baseline_nll - candidate_nll
    per_game_brier_gain = (y - baseline) ** 2 - (y - candidate) ** 2

    log_gains = np.empty(replicates, dtype=float)
    brier_gains = np.empty(replicates, dtype=float)
    batch_size = 1000
    for start_index in range(0, replicates, batch_size):
        stop_index = min(start_index + batch_size, replicates)
        indexes = rng.integers(0, n, size=(stop_index - start_index, n))
        log_gains[start_index:stop_index] = np.mean(per_game_log_gain[indexes], axis=1)
        brier_gains[start_index:stop_index] = np.mean(per_game_brier_gain[indexes], axis=1)

    def summary(values: np.ndarray, metric: str) -> dict[str, Any]:
        return {
            "sample": label,
            "metric": metric,
            "replicates": replicates,
            "seed": seed,
            "mean_gain": float(np.mean(values)),
            "probability_gain_positive": float(np.mean(values > 0)),
            "interval_80_lower": float(np.quantile(values, 0.10)),
            "interval_80_upper": float(np.quantile(values, 0.90)),
            "interval_95_lower": float(np.quantile(values, 0.025)),
            "interval_95_upper": float(np.quantile(values, 0.975)),
        }

    rows = [summary(log_gains, "log_loss_gain"), summary(brier_gains, "brier_gain")]
    return {
        "log_loss_gain": rows[0],
        "brier_gain": rows[1],
    }, rows


def subgroup_rows(frame: pd.DataFrame, minimum_rows: int) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    dimensions = [
        "source_wave",
        "test_fold",
        "minimum_expected_minutes_coverage_band",
        "minutes_before_tip_band",
        "training_fold_absolute_weighted_unavailable_minutes_quartile",
    ]
    for dimension in dimensions:
        for value, group in frame.groupby(dimension, dropna=False):
            y = group["actual_home_win"].to_numpy(dtype=int)
            baseline = group["baseline_probability"].to_numpy(dtype=float)
            candidate = group["candidate_probability"].to_numpy(dtype=float)
            baseline_loss = binary_log_loss(y, baseline)
            candidate_loss = binary_log_loss(y, candidate)
            results.append({
                "dimension": dimension,
                "value": str(value),
                "rows": int(len(group)),
                "baseline_log_loss": baseline_loss,
                "candidate_log_loss": candidate_loss,
                "log_loss_gain": baseline_loss - candidate_loss,
                "candidate_log_loss_degradation": candidate_loss - baseline_loss,
                "safety_gate_monitored": bool(len(group) >= minimum_rows),
            })
    return results


def decision_from_gates(structural: list[dict[str, Any]], promotion: list[dict[str, Any]]) -> str:
    if not all(bool(row["passed"]) for row in structural):
        return "STRUCTURAL_BLOCKED"
    if not all(bool(row["passed"]) for row in promotion):
        return "VALID_NEGATIVE_RESULT"
    return "HOLDOUT_RESEARCH_PASS"


def prepare_join(
    injury_path: Path,
    baseline_path: Path,
    policy: dict[str, Any],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    injury = pd.read_csv(injury_path, dtype={"historical_game_id": str})
    baseline = pd.read_csv(baseline_path, dtype={"game_id": str})

    required_injury = {
        "historical_game_id",
        "game_date",
        "observed_at",
        "commence_time",
        "minutes_before_tip",
        "home_team_abbr",
        "away_team_abbr",
        "matchup_snapshot_complete",
        "matchup_feature_available",
        "minimum_expected_minutes_coverage",
        "selection_policy",
        "selection_minimum_minutes_before_tip",
        "selection_fallback_used",
        "source_wave",
        *PRIMARY_FEATURES,
    }
    required_baseline = {
        "game_id",
        "game_date",
        "home_team_abbr",
        "away_team_abbr",
        "actual_home_win",
        "actual_home_margin",
        "predicted_home_win_probability",
        "predicted_home_margin",
    }
    missing_injury = sorted(required_injury - set(injury.columns))
    missing_baseline = sorted(required_baseline - set(baseline.columns))
    if missing_injury or missing_baseline:
        raise ValueError(f"missing columns injury={missing_injury} baseline={missing_baseline}")

    duplicate_injury = int(injury["historical_game_id"].duplicated().sum())
    duplicate_baseline = int(baseline["game_id"].duplicated().sum())
    joined = injury.merge(
        baseline,
        left_on="historical_game_id",
        right_on="game_id",
        how="left",
        suffixes=("_injury", "_baseline"),
        validate="one_to_one",
    )
    joined["game_date"] = joined["game_date_injury"].astype(str)
    joined["date_match"] = joined["game_date_injury"].astype(str) == joined["game_date_baseline"].astype(str)
    joined["home_team_match"] = joined["home_team_abbr_injury"].astype(str) == joined["home_team_abbr_baseline"].astype(str)
    joined["away_team_match"] = joined["away_team_abbr_injury"].astype(str) == joined["away_team_abbr_baseline"].astype(str)
    identity_mismatches = int((~joined["date_match"] | ~joined["home_team_match"] | ~joined["away_team_match"]).sum())
    joined["game_date_dt"] = pd.to_datetime(joined["game_date"], format="%Y-%m-%d")
    joined["observed_at_dt"] = pd.to_datetime(joined["observed_at"], utc=True, errors="coerce")
    joined["commence_time_dt"] = pd.to_datetime(joined["commence_time"], utc=True, errors="coerce")
    timestamp_parse_errors = int(
        joined["observed_at_dt"].isna().sum() + joined["commence_time_dt"].isna().sum()
    )
    strict_point_in_time_violations = int(
        (
            joined["observed_at_dt"].notna()
            & joined["commence_time_dt"].notna()
            & (joined["observed_at_dt"] >= joined["commence_time_dt"])
        ).sum()
    )
    joined = joined.sort_values(["game_date_dt", "historical_game_id"]).reset_index(drop=True)

    structural_observations = {
        "injury_rows": int(len(injury)),
        "unique_injury_games": int(injury["historical_game_id"].nunique()),
        "baseline_rows": int(len(baseline)),
        "baseline_join_rows": int(joined["game_id"].notna().sum()),
        "duplicate_injury_games": duplicate_injury,
        "duplicate_baseline_games": duplicate_baseline,
        "game_identity_mismatches": identity_mismatches,
        "missing_feature_rows": int(joined[PRIMARY_FEATURES].isna().any(axis=1).sum()),
        "complete_snapshot_rows": int((joined["matchup_snapshot_complete"] == 1).sum()),
        "feature_available_rows": int((joined["matchup_feature_available"] == 1).sum()),
        "selection_policy_mismatches": int(
            (joined["selection_policy"] != policy["frozen_population"]["selection_policy"]).sum()
        ),
        "selection_t60_mismatches": int(
            (joined["selection_minimum_minutes_before_tip"] != policy["frozen_population"]["minimum_minutes_before_tip"]).sum()
        ),
        "fallback_rows": int((joined["selection_fallback_used"] != 0).sum()),
        "before_t60_violations": int(
            (joined["minutes_before_tip"] < policy["frozen_population"]["minimum_minutes_before_tip"]).sum()
        ),
        "timestamp_parse_errors": timestamp_parse_errors,
        "strict_point_in_time_violations": strict_point_in_time_violations,
        "date_start": str(joined["game_date"].min()) if len(joined) else "",
        "date_end": str(joined["game_date"].max()) if len(joined) else "",
        "wave_counts": dict(sorted(Counter(joined["source_wave"].astype(str)).items())),
    }
    return joined, structural_observations


def run(
    injury_path: Path,
    baseline_path: Path,
    policy: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    joined, observations = prepare_join(injury_path, baseline_path, policy)
    population = policy["frozen_population"]

    structural_gates: list[dict[str, Any]] = []

    def structural(name: str, observed: Any, expected: Any, passed: bool) -> None:
        structural_gates.append({
            "name": name,
            "observed": observed,
            "expected": expected,
            "passed": bool(passed),
        })

    structural("population_games", observations["injury_rows"], population["combined_selected_independent_games"], observations["injury_rows"] == population["combined_selected_independent_games"])
    structural("unique_game_ids", observations["unique_injury_games"], population["combined_selected_independent_games"], observations["unique_injury_games"] == population["combined_selected_independent_games"])
    structural("baseline_join_games", observations["baseline_join_rows"], population["baseline_oof_join_required"], observations["baseline_join_rows"] == population["baseline_oof_join_required"])
    structural("duplicate_injury_games", observations["duplicate_injury_games"], 0, observations["duplicate_injury_games"] == 0)
    structural("duplicate_baseline_games", observations["duplicate_baseline_games"], 0, observations["duplicate_baseline_games"] == 0)
    structural("game_identity_mismatches", observations["game_identity_mismatches"], 0, observations["game_identity_mismatches"] == 0)
    structural("feature_missing_rows", observations["missing_feature_rows"], 0, observations["missing_feature_rows"] == 0)
    structural("complete_snapshot_rows", observations["complete_snapshot_rows"], population["combined_selected_independent_games"], observations["complete_snapshot_rows"] == population["combined_selected_independent_games"])
    structural("feature_available_rows", observations["feature_available_rows"], population["combined_selected_independent_games"], observations["feature_available_rows"] == population["combined_selected_independent_games"])
    structural("selection_policy_mismatches", observations["selection_policy_mismatches"], 0, observations["selection_policy_mismatches"] == 0)
    structural("selection_t60_mismatches", observations["selection_t60_mismatches"], 0, observations["selection_t60_mismatches"] == 0)
    structural("fallback_rows", observations["fallback_rows"], 0, observations["fallback_rows"] == 0)
    structural("snapshot_before_t60_violations", observations["before_t60_violations"], 0, observations["before_t60_violations"] == 0)
    structural("timestamp_parse_errors", observations["timestamp_parse_errors"], 0, observations["timestamp_parse_errors"] == 0)
    structural("strict_point_in_time_violations", observations["strict_point_in_time_violations"], 0, observations["strict_point_in_time_violations"] == 0)
    structural("date_start", observations["date_start"], population["game_date_start"], observations["date_start"] == population["game_date_start"])
    structural("date_end", observations["date_end"], population["game_date_end"], observations["date_end"] == population["game_date_end"])
    structural("wave_counts", observations["wave_counts"], population["wave_selected_games"], observations["wave_counts"] == population["wave_selected_games"])

    if not all(row["passed"] for row in structural_gates):
        report = {
            "schema_version": VERSION,
            "generated_at": utc_now(),
            "decision_state": "STRUCTURAL_BLOCKED",
            "coverage": observations,
            "structural_gates": structural_gates,
            "promotion_gates": [],
            "folds": [],
            "combined_forward": None,
            "final_holdout": None,
            "bootstrap": None,
            "quality": {
                "test_rows_used_for_training": 0,
                "strict_point_in_time_violations": observations["strict_point_in_time_violations"],
                "target_game_labels_used_as_features": False,
                "market_odds_used": False,
                "random_shuffle_used": False,
                "fuzzy_identity_used": False,
                "fuzzy_schedule_matching_used": False,
            },
            "decision": {
                "injury_candidate_research_ready": False,
                "ready_for_timestamped_odds_predeclaration": False,
                "ready_for_timestamped_odds_execution": False,
                "ready_for_production_model_training": False,
                "ready_for_probability_adjustment": False,
                "ready_for_betting_edge_claim": False,
                "formal_stake": 0,
            },
        }
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "injury-feature-holdout-v1-report.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        return report

    fold_rows: list[dict[str, Any]] = []
    game_outputs: list[pd.DataFrame] = []
    fold_boundaries: list[dict[str, Any]] = []

    for fold in policy["chronological_folds"]:
        train_start = pd.Timestamp(fold["train_start"])
        train_end = pd.Timestamp(fold["train_end"])
        test_start = pd.Timestamp(fold["test_start"])
        test_end = pd.Timestamp(fold["test_end"])
        train = joined[(joined["game_date_dt"] >= train_start) & (joined["game_date_dt"] <= train_end)].copy()
        test = joined[(joined["game_date_dt"] >= test_start) & (joined["game_date_dt"] <= test_end)].copy()

        train_test_overlap = len(
            set(train["historical_game_id"].astype(str))
            & set(test["historical_game_id"].astype(str))
        )
        structural(f"{fold['fold_id']}.train_games", len(train), fold["expected_train_games"], len(train) == fold["expected_train_games"])
        structural(f"{fold['fold_id']}.test_games", len(test), fold["expected_test_games"], len(test) == fold["expected_test_games"])
        structural(f"{fold['fold_id']}.train_test_overlap", train_test_overlap, 0, train_test_overlap == 0)
        structural(f"{fold['fold_id']}.chronology", int(train["game_date_dt"].max() < test["game_date_dt"].min()), 1, bool(train["game_date_dt"].max() < test["game_date_dt"].min()))

        x_train_raw = train[PRIMARY_FEATURES].to_numpy(dtype=float)
        x_test_raw = test[PRIMARY_FEATURES].to_numpy(dtype=float)
        try:
            x_train, x_test, means, scales = standardize_train_test(x_train_raw, x_test_raw)
        except Exception as exc:
            structural(f"{fold['fold_id']}.feature_standardization", str(exc), "finite nonzero training scales", False)
            continue

        y_train = train["actual_home_win"].to_numpy(dtype=int)
        y_test = test["actual_home_win"].to_numpy(dtype=int)
        p_train = train["predicted_home_win_probability"].to_numpy(dtype=float)
        p_test = test["predicted_home_win_probability"].to_numpy(dtype=float)
        m_train = train["predicted_home_margin"].to_numpy(dtype=float)
        m_test = test["predicted_home_margin"].to_numpy(dtype=float)
        actual_margin_train = train["actual_home_margin"].to_numpy(dtype=float)
        actual_margin_test = test["actual_home_margin"].to_numpy(dtype=float)

        beta, probability_optimizer = fit_probability_offset(p_train, x_train, y_train, policy)
        gamma, margin_optimizer = fit_margin_offset(m_train, x_train, actual_margin_train, policy)

        candidate_test = sigmoid(clipped_logit(p_test) + x_test @ beta)
        candidate_margin = m_test + x_test @ gamma

        baseline_metrics = class_metrics(y_test, p_test)
        candidate_metrics = class_metrics(y_test, candidate_test)
        baseline_calibration = calibration_metrics(y_test, p_test)
        candidate_calibration = calibration_metrics(y_test, candidate_test)
        baseline_margin_metrics = margin_metrics(actual_margin_test, m_test)
        candidate_margin_metrics = margin_metrics(actual_margin_test, candidate_margin)

        fold_row = {
            "fold_id": fold["fold_id"],
            "role": fold["role"],
            "train_games": int(len(train)),
            "test_games": int(len(test)),
            "train_start": fold["train_start"],
            "train_end": fold["train_end"],
            "test_start": fold["test_start"],
            "test_end": fold["test_end"],
            "baseline_log_loss": baseline_metrics["log_loss"],
            "candidate_log_loss": candidate_metrics["log_loss"],
            "log_loss_gain": baseline_metrics["log_loss"] - candidate_metrics["log_loss"],
            "baseline_brier": baseline_metrics["brier_score"],
            "candidate_brier": candidate_metrics["brier_score"],
            "brier_gain": baseline_metrics["brier_score"] - candidate_metrics["brier_score"],
            "baseline_auc": baseline_metrics["roc_auc"],
            "candidate_auc": candidate_metrics["roc_auc"],
            "baseline_accuracy": baseline_metrics["accuracy"],
            "candidate_accuracy": candidate_metrics["accuracy"],
            "baseline_calibration_intercept": baseline_calibration["calibration_intercept"],
            "baseline_calibration_slope": baseline_calibration["calibration_slope"],
            "candidate_calibration_intercept": candidate_calibration["calibration_intercept"],
            "candidate_calibration_slope": candidate_calibration["calibration_slope"],
            "baseline_ece": equal_frequency_ece(y_test, p_test),
            "candidate_ece": equal_frequency_ece(y_test, candidate_test),
            "average_absolute_probability_shift": float(np.mean(np.abs(candidate_test - p_test))),
            "maximum_absolute_probability_shift": float(np.max(np.abs(candidate_test - p_test))),
            "baseline_margin_mae": baseline_margin_metrics["mae"],
            "candidate_margin_mae": candidate_margin_metrics["mae"],
            "baseline_margin_rmse": baseline_margin_metrics["rmse"],
            "candidate_margin_rmse": candidate_margin_metrics["rmse"],
            "beta_weighted_unavailable_minutes": float(beta[0]),
            "beta_positive_absence_impact": float(beta[1]),
            "gamma_weighted_unavailable_minutes": float(gamma[0]),
            "gamma_positive_absence_impact": float(gamma[1]),
            "feature_mean_weighted_unavailable_minutes": float(means[0]),
            "feature_mean_positive_absence_impact": float(means[1]),
            "feature_scale_weighted_unavailable_minutes": float(scales[0]),
            "feature_scale_positive_absence_impact": float(scales[1]),
            "probability_optimizer_success": probability_optimizer["success"],
            "margin_optimizer_success": margin_optimizer["success"],
        }
        fold_rows.append(fold_row)

        threshold_values = quartile_thresholds(np.abs(x_train_raw[:, 0]))
        fold_boundaries.append({
            "fold_id": fold["fold_id"],
            "q25": threshold_values[0],
            "q50": threshold_values[1],
            "q75": threshold_values[2],
        })
        output = test[[
            "historical_game_id",
            "game_date",
            "source_wave",
            "minutes_before_tip",
            "minimum_expected_minutes_coverage",
            "actual_home_win",
            "actual_home_margin",
        ]].copy()
        output["test_fold"] = fold["fold_id"]
        output["baseline_probability"] = p_test
        output["candidate_probability"] = candidate_test
        output["baseline_margin"] = m_test
        output["candidate_margin"] = candidate_margin
        output["minimum_expected_minutes_coverage_band"] = output["minimum_expected_minutes_coverage"].map(coverage_band)
        output["minutes_before_tip_band"] = output["minutes_before_tip"].map(minutes_before_tip_band)
        output["training_fold_absolute_weighted_unavailable_minutes_quartile"] = [
            quartile_band(value, threshold_values)
            for value in np.abs(x_test_raw[:, 0])
        ]
        game_outputs.append(output)

    if len(fold_rows) != len(policy["chronological_folds"]):
        structural("all_folds_fit", len(fold_rows), len(policy["chronological_folds"]), False)

    forward = pd.concat(game_outputs, ignore_index=True) if game_outputs else pd.DataFrame()
    duplicate_forward_games = int(forward["historical_game_id"].duplicated().sum()) if len(forward) else 0
    structural("combined_forward_test_games", len(forward), policy["combined_forward_test_games"], len(forward) == policy["combined_forward_test_games"])
    structural("fold_overlap_games", duplicate_forward_games, 0, duplicate_forward_games == 0)
    final_rows = forward[forward["test_fold"] == "final_untouched_holdout"].copy() if len(forward) else pd.DataFrame()
    structural("final_holdout_games", len(final_rows), policy["structural_gates"]["required_final_holdout_games"], len(final_rows) == policy["structural_gates"]["required_final_holdout_games"])

    if not all(row["passed"] for row in structural_gates):
        decision_state = "STRUCTURAL_BLOCKED"
        promotion_gates: list[dict[str, Any]] = []
        combined_summary = None
        final_summary = None
        bootstrap_summary = None
        subgroup_output: list[dict[str, Any]] = []
        bootstrap_rows: list[dict[str, Any]] = []
    else:
        y_forward = forward["actual_home_win"].to_numpy(dtype=int)
        base_forward = forward["baseline_probability"].to_numpy(dtype=float)
        cand_forward = forward["candidate_probability"].to_numpy(dtype=float)
        y_final = final_rows["actual_home_win"].to_numpy(dtype=int)
        base_final = final_rows["baseline_probability"].to_numpy(dtype=float)
        cand_final = final_rows["candidate_probability"].to_numpy(dtype=float)

        base_combined_metrics = class_metrics(y_forward, base_forward)
        cand_combined_metrics = class_metrics(y_forward, cand_forward)
        base_final_metrics = class_metrics(y_final, base_final)
        cand_final_metrics = class_metrics(y_final, cand_final)

        combined_bootstrap, combined_bootstrap_rows = paired_bootstrap(
            y_forward, base_forward, cand_forward, policy, "combined_forward"
        )
        final_bootstrap, final_bootstrap_rows = paired_bootstrap(
            y_final, base_final, cand_final, policy, "final_holdout"
        )
        bootstrap_rows = combined_bootstrap_rows + final_bootstrap_rows
        bootstrap_summary = {
            "combined_forward": combined_bootstrap,
            "final_holdout": final_bootstrap,
        }

        combined_summary = {
            "rows": int(len(forward)),
            "baseline": base_combined_metrics,
            "candidate": cand_combined_metrics,
            "log_loss_gain": base_combined_metrics["log_loss"] - cand_combined_metrics["log_loss"],
            "brier_gain": base_combined_metrics["brier_score"] - cand_combined_metrics["brier_score"],
            "average_absolute_probability_shift": float(np.mean(np.abs(cand_forward - base_forward))),
            "maximum_absolute_probability_shift": float(np.max(np.abs(cand_forward - base_forward))),
        }
        final_summary = {
            "rows": int(len(final_rows)),
            "baseline": base_final_metrics,
            "candidate": cand_final_metrics,
            "log_loss_gain": base_final_metrics["log_loss"] - cand_final_metrics["log_loss"],
            "brier_gain": base_final_metrics["brier_score"] - cand_final_metrics["brier_score"],
            "average_absolute_probability_shift": float(np.mean(np.abs(cand_final - base_final))),
            "maximum_absolute_probability_shift": float(np.max(np.abs(cand_final - base_final))),
        }

        minimum_subgroup_rows = int(policy["monitored_subgroups"]["minimum_rows_for_safety_gate"])
        subgroup_output = subgroup_rows(forward, minimum_subgroup_rows)
        monitored = [row for row in subgroup_output if row["safety_gate_monitored"]]
        worst_subgroup_degradation = max(
            (float(row["candidate_log_loss_degradation"]) for row in monitored),
            default=0.0,
        )

        fold_index = {row["fold_id"]: row for row in fold_rows}
        development_gain = float(fold_index["development_forward_1"]["log_loss_gain"])
        all_beta_nonpositive = all(
            row["beta_weighted_unavailable_minutes"] <= 1e-12
            and row["beta_positive_absence_impact"] <= 1e-12
            for row in fold_rows
        )
        gates = policy["promotion_gates"]
        promotion_gates = []

        def promotion(name: str, observed: Any, operator: str, threshold: Any, passed: bool) -> None:
            promotion_gates.append({
                "name": name,
                "observed": observed,
                "operator": operator,
                "threshold": threshold,
                "passed": bool(passed),
            })

        promotion("combined_forward_log_loss_gain", combined_summary["log_loss_gain"], ">=", gates["minimum_combined_forward_log_loss_gain"], combined_summary["log_loss_gain"] >= gates["minimum_combined_forward_log_loss_gain"])
        promotion("final_holdout_log_loss_gain", final_summary["log_loss_gain"], ">", gates["minimum_final_holdout_log_loss_gain"], final_summary["log_loss_gain"] > gates["minimum_final_holdout_log_loss_gain"])
        promotion("development_fold_log_loss_gain", development_gain, ">=", gates["minimum_development_fold_log_loss_gain"], development_gain >= gates["minimum_development_fold_log_loss_gain"])
        promotion("combined_forward_brier_gain", combined_summary["brier_gain"], ">=", gates["minimum_combined_forward_brier_gain"], combined_summary["brier_gain"] >= gates["minimum_combined_forward_brier_gain"])
        promotion("final_holdout_brier_gain", final_summary["brier_gain"], ">=", gates["minimum_final_holdout_brier_gain"], final_summary["brier_gain"] >= gates["minimum_final_holdout_brier_gain"])
        promotion("combined_bootstrap_probability_log_loss_gain_positive", combined_bootstrap["log_loss_gain"]["probability_gain_positive"], ">=", gates["minimum_combined_bootstrap_probability_log_loss_gain_positive"], combined_bootstrap["log_loss_gain"]["probability_gain_positive"] >= gates["minimum_combined_bootstrap_probability_log_loss_gain_positive"])
        promotion("final_bootstrap_probability_log_loss_gain_positive", final_bootstrap["log_loss_gain"]["probability_gain_positive"], ">=", gates["minimum_final_holdout_bootstrap_probability_log_loss_gain_positive"], final_bootstrap["log_loss_gain"]["probability_gain_positive"] >= gates["minimum_final_holdout_bootstrap_probability_log_loss_gain_positive"])
        promotion("average_absolute_probability_shift", combined_summary["average_absolute_probability_shift"], "<=", gates["maximum_average_absolute_probability_shift"], combined_summary["average_absolute_probability_shift"] <= gates["maximum_average_absolute_probability_shift"])
        promotion("maximum_single_game_probability_shift", combined_summary["maximum_absolute_probability_shift"], "<=", gates["maximum_single_game_absolute_probability_shift"], combined_summary["maximum_absolute_probability_shift"] <= gates["maximum_single_game_absolute_probability_shift"])
        promotion("worst_monitored_subgroup_log_loss_degradation", worst_subgroup_degradation, "<=", gates["maximum_monitored_subgroup_log_loss_degradation"], worst_subgroup_degradation <= gates["maximum_monitored_subgroup_log_loss_degradation"])
        promotion("candidate_coefficients_non_positive", all_beta_nonpositive, "is", True, all_beta_nonpositive)

        decision_state = decision_from_gates(structural_gates, promotion_gates)

    structurally_valid = decision_state != "STRUCTURAL_BLOCKED"
    candidate_ready = decision_state == "HOLDOUT_RESEARCH_PASS"
    ready_for_odds_predeclaration = decision_state in {
        "VALID_NEGATIVE_RESULT",
        "HOLDOUT_RESEARCH_PASS",
    }

    quality = {
        "test_rows_used_for_training": 0,
        "strict_point_in_time_violations": observations["strict_point_in_time_violations"],
        "target_game_labels_used_as_features": False,
        "target_game_minutes_used_as_features": False,
        "market_odds_used": False,
        "random_shuffle_used": False,
        "fuzzy_identity_used": False,
        "fuzzy_schedule_matching_used": False,
        "missing_injury_values_imputed_as_zero": False,
        "post_result_feature_selection_performed": False,
        "hyperparameter_search_performed": False,
        "training_fold_scaling_only": True,
        "structural_blockers": [row["name"] for row in structural_gates if not row["passed"]],
        "promotion_blockers": [row["name"] for row in promotion_gates if not row["passed"]],
    }
    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "policy_schema_version": policy.get("schema_version"),
        "decision_state": decision_state,
        "coverage": observations,
        "fold_boundaries": fold_boundaries,
        "folds": fold_rows,
        "combined_forward": combined_summary,
        "final_holdout": final_summary,
        "bootstrap": bootstrap_summary,
        "structural_gates": structural_gates,
        "promotion_gates": promotion_gates,
        "quality": quality,
        "decision": {
            "structurally_valid_holdout_result": structurally_valid,
            "injury_candidate_research_ready": candidate_ready,
            "market_research_model_path": (
                "baseline_and_injury_candidate_compared_separately"
                if candidate_ready
                else "frozen_baseline_only"
                if decision_state == "VALID_NEGATIVE_RESULT"
                else "blocked"
            ),
            "ready_for_timestamped_odds_predeclaration": ready_for_odds_predeclaration,
            "ready_for_timestamped_odds_execution": False,
            "ready_for_production_model_training": False,
            "ready_for_probability_adjustment": False,
            "ready_for_betting_edge_claim": False,
            "formal_stake": 0,
        },
        "guardrails": policy["guardrails"],
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "injury-feature-holdout-v1-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    write_csv(output_dir / "injury-feature-holdout-v1-folds.csv", fold_rows)
    write_csv(output_dir / "injury-feature-holdout-v1-subgroups.csv", subgroup_output)
    write_csv(output_dir / "injury-feature-holdout-v1-bootstrap.csv", bootstrap_rows)
    if len(forward):
        forward.to_csv(output_dir / "injury-feature-holdout-v1-game-rows.csv", index=False)
    return report


def self_test(output_dir: Path) -> None:
    assert decision_from_gates(
        [{"name": "s", "passed": True}],
        [{"name": "p", "passed": True}],
    ) == "HOLDOUT_RESEARCH_PASS"
    assert decision_from_gates(
        [{"name": "s", "passed": True}],
        [{"name": "p", "passed": False}],
    ) == "VALID_NEGATIVE_RESULT"
    assert decision_from_gates(
        [{"name": "s", "passed": False}],
        [{"name": "p", "passed": True}],
    ) == "STRUCTURAL_BLOCKED"

    rng = np.random.default_rng(20260718)
    n = 200
    baseline = np.full(n, 0.55)
    raw = rng.normal(size=(n, 2))
    standardized, _, _, _ = standardize_train_test(raw, raw.copy())
    truth = sigmoid(clipped_logit(baseline) + standardized @ np.asarray([-0.35, -0.15]))
    outcome = rng.binomial(1, truth)
    policy = {
        "primary_candidate": {
            "fit": {
                "l2_alpha": 0.05,
                "initial_coefficients": [0.0, 0.0],
                "coefficient_bounds": [-0.5, 0.0],
                "optimizer": "L-BFGS-B",
                "maximum_iterations": 2000,
                "tolerance": 1e-9,
            }
        }
    }
    coefficients, optimizer = fit_probability_offset(baseline, standardized, outcome, policy)
    assert optimizer["success"] is True, optimizer
    assert np.all(coefficients <= 1e-12), coefficients
    assert np.all(coefficients >= -0.5 - 1e-12), coefficients

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "self-test.json").write_text(
        json.dumps({
            "coefficients": coefficients.tolist(),
            "decision_pass": "HOLDOUT_RESEARCH_PASS",
            "decision_negative": "VALID_NEGATIVE_RESULT",
            "decision_structural": "STRUCTURAL_BLOCKED",
        }, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--injury-panel", type=Path)
    parser.add_argument("--baseline-predictions", type=Path)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test(args.output_dir)
        print("Injury Feature holdout v1 self-test passed")
        return
    if not args.injury_panel or not args.baseline_predictions or not args.policy:
        parser.error("--injury-panel, --baseline-predictions, and --policy are required")

    report = run(
        args.injury_panel,
        args.baseline_predictions,
        read_json(args.policy),
        args.output_dir,
    )
    print(json.dumps({
        "decision_state": report["decision_state"],
        **report["decision"],
    }, indent=2))
    if report["decision_state"] == "STRUCTURAL_BLOCKED":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
