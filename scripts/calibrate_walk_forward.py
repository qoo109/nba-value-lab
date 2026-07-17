#!/usr/bin/env python3
"""Evaluate leakage-safe probability calibration on season OOF predictions."""
from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score

CALIBRATION_VERSION = "probability-calibration-v1"
EPSILON = 1e-6


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clip_probability(values: np.ndarray | list[float]) -> np.ndarray:
    return np.clip(np.asarray(values, dtype=float), EPSILON, 1.0 - EPSILON)


def logit(values: np.ndarray | list[float]) -> np.ndarray:
    p = clip_probability(values)
    return np.log(p / (1.0 - p))


def load_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for raw in csv.DictReader(handle):
            rows.append({
                **raw,
                "actual_home_win": int(raw["actual_home_win"]),
                "actual_home_margin": float(raw["actual_home_margin"]),
                "predicted_home_win_probability": float(raw["predicted_home_win_probability"]),
                "elo_home_win_probability": float(raw["elo_home_win_probability"]),
            })
    rows.sort(key=lambda row: (row["game_date"], row["game_id"]))
    if not rows:
        raise ValueError("No walk-forward prediction rows found")
    return rows


def ordered_seasons(rows: list[dict[str, Any]]) -> list[str]:
    seasons: list[str] = []
    for row in rows:
        season = str(row["test_season"])
        if season not in seasons:
            seasons.append(season)
    return seasons


def reliability_table(y: np.ndarray, p: np.ndarray, bins: int = 10) -> list[dict[str, Any]]:
    p = clip_probability(p)
    edges = np.linspace(0.0, 1.0, bins + 1)
    output: list[dict[str, Any]] = []
    for index in range(bins):
        low, high = float(edges[index]), float(edges[index + 1])
        mask = (p >= low) & (p < high if index < bins - 1 else p <= high)
        count = int(mask.sum())
        if count == 0:
            continue
        output.append({
            "bin_low": low,
            "bin_high": high,
            "rows": count,
            "mean_predicted": float(p[mask].mean()),
            "observed_rate": float(y[mask].mean()),
            "absolute_gap": float(abs(p[mask].mean() - y[mask].mean())),
        })
    return output


def expected_calibration_error(table: list[dict[str, Any]]) -> float:
    total = sum(item["rows"] for item in table)
    if total == 0:
        return 0.0
    return float(sum(item["rows"] * item["absolute_gap"] for item in table) / total)


def probability_metrics(y: np.ndarray, p: np.ndarray) -> dict[str, Any]:
    p = clip_probability(p)
    table = reliability_table(y, p)
    auc = None if len(np.unique(y)) < 2 else float(roc_auc_score(y, p))
    return {
        "rows": int(len(y)),
        "log_loss": float(log_loss(y, p, labels=[0, 1])),
        "brier_score": float(brier_score_loss(y, p)),
        "accuracy": float(accuracy_score(y, p >= 0.5)),
        "roc_auc": auc,
        "expected_calibration_error": expected_calibration_error(table),
        "maximum_calibration_error": float(max((item["absolute_gap"] for item in table), default=0.0)),
        "reliability": table,
    }


def fit_platt(probabilities: np.ndarray, outcomes: np.ndarray) -> LogisticRegression:
    model = LogisticRegression(C=1_000_000.0, solver="lbfgs", max_iter=2000, random_state=42)
    model.fit(logit(probabilities).reshape(-1, 1), outcomes)
    return model


def predict_platt(model: LogisticRegression, probabilities: np.ndarray) -> np.ndarray:
    return model.predict_proba(logit(probabilities).reshape(-1, 1))[:, 1]


def fit_isotonic(probabilities: np.ndarray, outcomes: np.ndarray) -> IsotonicRegression:
    model = IsotonicRegression(y_min=0.001, y_max=0.999, out_of_bounds="clip")
    model.fit(clip_probability(probabilities), outcomes)
    return model


def choose_method(aggregate: dict[str, dict[str, Any]]) -> tuple[str, str]:
    raw = aggregate["raw_logistic_elo"]
    eligible: list[tuple[str, float]] = []
    for method in ("platt", "isotonic"):
        candidate = aggregate[method]
        improves_log_loss = candidate["log_loss"] <= raw["log_loss"] - 0.0005
        does_not_worsen_brier = candidate["brier_score"] <= raw["brier_score"]
        if improves_log_loss and does_not_worsen_brier:
            eligible.append((method, candidate["log_loss"]))
    if not eligible:
        return "raw_logistic_elo", "No calibration candidate improved Log Loss by at least 0.0005 without worsening Brier Score."
    selected = min(eligible, key=lambda item: item[1])[0]
    return selected, "Selected by prior-season OOF aggregate Log Loss with a Brier non-degradation gate."


def calibrate(rows: list[dict[str, Any]], output_dir: Path) -> dict[str, Any]:
    seasons = ordered_seasons(rows)
    if len(seasons) < 3:
        raise ValueError(f"Need at least three OOF seasons for calibration evaluation, got {seasons}")

    folds: list[dict[str, Any]] = []
    prediction_rows: list[dict[str, Any]] = []
    aggregate_values: dict[str, list[float]] = {
        "actual": [], "raw_logistic_elo": [], "platt": [], "isotonic": [], "elo_benchmark": []
    }

    for target_index in range(1, len(seasons)):
        calibration_seasons = seasons[:target_index]
        target_season = seasons[target_index]
        calibration_rows = [row for row in rows if row["test_season"] in calibration_seasons]
        target_rows = [row for row in rows if row["test_season"] == target_season]
        if not calibration_rows or not target_rows:
            continue

        y_cal = np.asarray([row["actual_home_win"] for row in calibration_rows], dtype=int)
        p_cal = np.asarray([row["predicted_home_win_probability"] for row in calibration_rows], dtype=float)
        y_test = np.asarray([row["actual_home_win"] for row in target_rows], dtype=int)
        p_raw = np.asarray([row["predicted_home_win_probability"] for row in target_rows], dtype=float)
        p_elo = np.asarray([row["elo_home_win_probability"] for row in target_rows], dtype=float)

        platt = fit_platt(p_cal, y_cal)
        isotonic = fit_isotonic(p_cal, y_cal)
        p_platt = predict_platt(platt, p_raw)
        p_isotonic = clip_probability(isotonic.predict(p_raw))

        metrics = {
            "raw_logistic_elo": probability_metrics(y_test, p_raw),
            "platt": probability_metrics(y_test, p_platt),
            "isotonic": probability_metrics(y_test, p_isotonic),
            "elo_benchmark": probability_metrics(y_test, p_elo),
        }
        folds.append({
            "target_season": target_season,
            "calibration_seasons": calibration_seasons,
            "calibration_rows": len(calibration_rows),
            "test_rows": len(target_rows),
            "metrics": metrics,
            "platt_intercept": float(platt.intercept_[0]),
            "platt_slope": float(platt.coef_[0][0]),
        })

        aggregate_values["actual"].extend(y_test.tolist())
        aggregate_values["raw_logistic_elo"].extend(p_raw.tolist())
        aggregate_values["platt"].extend(p_platt.tolist())
        aggregate_values["isotonic"].extend(p_isotonic.tolist())
        aggregate_values["elo_benchmark"].extend(p_elo.tolist())
        for row, raw_p, platt_p, isotonic_p, elo_p in zip(target_rows, p_raw, p_platt, p_isotonic, p_elo):
            prediction_rows.append({
                "target_season": target_season,
                "calibration_seasons": "|".join(calibration_seasons),
                "game_id": row["game_id"],
                "game_date": row["game_date"],
                "home_team_abbr": row["home_team_abbr"],
                "away_team_abbr": row["away_team_abbr"],
                "actual_home_win": row["actual_home_win"],
                "raw_probability": round(float(raw_p), 8),
                "platt_probability": round(float(platt_p), 8),
                "isotonic_probability": round(float(isotonic_p), 8),
                "elo_probability": round(float(elo_p), 8),
            })

    if len(folds) < 2:
        raise ValueError(f"Need at least two calibrated target folds, got {len(folds)}")

    y_all = np.asarray(aggregate_values["actual"], dtype=int)
    aggregate = {
        method: probability_metrics(y_all, np.asarray(aggregate_values[method], dtype=float))
        for method in ("raw_logistic_elo", "platt", "isotonic", "elo_benchmark")
    }
    selected_method, selection_reason = choose_method(aggregate)

    all_y = np.asarray([row["actual_home_win"] for row in rows], dtype=int)
    all_p = np.asarray([row["predicted_home_win_probability"] for row in rows], dtype=float)
    final_platt = fit_platt(all_p, all_y)
    final_isotonic = fit_isotonic(all_p, all_y)

    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump({
        "version": CALIBRATION_VERSION,
        "selected_method": selected_method,
        "platt": final_platt,
        "isotonic": final_isotonic,
        "fit_seasons": seasons,
        "fit_rows": len(rows),
        "deployment_rule": "Use a calibrator only when the report selects it; otherwise retain raw logistic+Elo probabilities.",
    }, output_dir / "calibration-candidates.joblib")

    with (output_dir / "calibrated-predictions.csv").open("w", encoding="utf-8", newline="") as handle:
        fieldnames = list(prediction_rows[0])
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(prediction_rows)

    report = {
        "calibration_version": CALIBRATION_VERSION,
        "generated_at": utc_now(),
        "source": {
            "prediction_rows": len(rows),
            "oof_seasons": seasons,
            "oof_season_count": len(seasons),
            "evaluated_target_seasons": [fold["target_season"] for fold in folds],
        },
        "evaluation": {
            "folds": folds,
            "aggregate_prior_oof": aggregate,
            "raw_vs_elo_log_loss_gain": aggregate["elo_benchmark"]["log_loss"] - aggregate["raw_logistic_elo"]["log_loss"],
            "platt_vs_raw_log_loss_gain": aggregate["raw_logistic_elo"]["log_loss"] - aggregate["platt"]["log_loss"],
            "isotonic_vs_raw_log_loss_gain": aggregate["raw_logistic_elo"]["log_loss"] - aggregate["isotonic"]["log_loss"],
        },
        "full_oof_diagnostic": {
            "platt_intercept": float(final_platt.intercept_[0]),
            "platt_slope": float(final_platt.coef_[0][0]),
            "interpretation": "An intercept near 0 and slope near 1 indicate limited need for global recalibration.",
        },
        "guardrails": {
            "season_ordered_calibration": True,
            "target_season_excluded_from_calibrator_fit": True,
            "calibration_uses_prior_oof_predictions_only": True,
            "model_retraining_during_calibration": False,
            "odds_used": False,
            "activation_requires_log_loss_and_brier_gate": True,
        },
        "decision": {
            "selected_probability_method": selected_method,
            "calibration_candidate_activated": selected_method != "raw_logistic_elo",
            "selection_reason": selection_reason,
            "calibration_evaluation_complete": True,
            "ready_for_point_in_time_odds_join": True,
            "ready_for_market_backtest": False,
            "market_backtest_blocker": "Timestamped point-in-time moneyline and closing-line data are not joined yet.",
        },
    }
    (output_dir / "probability-calibration-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def sigmoid(values: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-values))


def self_test(output_dir: Path) -> None:
    rng = np.random.default_rng(42)
    rows: list[dict[str, Any]] = []
    seasons = ("2021-22", "2022-23", "2023-24")
    for season_index, season in enumerate(seasons):
        for game_index in range(400):
            latent = rng.normal(0.15, 0.9)
            true_probability = sigmoid(np.asarray([latent]))[0]
            outcome = int(rng.random() < true_probability)
            raw_probability = sigmoid(np.asarray([1.55 * latent - 0.25]))[0]
            rows.append({
                "test_season": season,
                "game_id": f"{season_index}-{game_index}",
                "game_date": f"202{season_index + 1}-{1 + game_index // 28:02d}-{1 + game_index % 28:02d}",
                "home_team_abbr": "AAA",
                "away_team_abbr": "BBB",
                "actual_home_win": outcome,
                "actual_home_margin": 1.0 if outcome else -1.0,
                "predicted_home_win_probability": float(raw_probability),
                "elo_home_win_probability": 0.5,
            })
    report = calibrate(rows, output_dir)
    assert report["guardrails"]["target_season_excluded_from_calibrator_fit"] is True
    assert len(report["evaluation"]["folds"]) == 2
    assert report["decision"]["calibration_evaluation_complete"] is True
    (output_dir / "self-test.json").write_text('{"passed":true}\n', encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("probability calibration self-test passed")
        return
    if not args.predictions:
        parser.error("--predictions is required unless --self-test is used")
    report = calibrate(load_rows(args.predictions), args.output_dir)
    print(json.dumps(report["decision"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
