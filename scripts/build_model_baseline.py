#!/usr/bin/env python3
"""Train point-in-time NBA baseline win-probability and margin models."""
from __future__ import annotations

import argparse, csv, gzip, json, math, shutil, sqlite3, tempfile
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, mean_absolute_error, mean_squared_error, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

MODEL_VERSION = "baseline-v1"
FEATURE_COLUMNS = [
    "net_rtg_last_5_diff", "net_rtg_last_10_diff", "net_rtg_last_20_diff",
    "pace_last_10_diff", "efg_pct_last_10_diff", "tov_pct_last_10_diff",
    "orb_pct_last_10_diff", "free_throw_rate_last_10_diff", "rest_days_diff",
    "evidence_coverage", "prior_games_min",
]


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ungzip(source, destination):
    with gzip.open(source, "rb") as src, open(destination, "wb") as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)


def load_rows(gold_db, silver_db):
    gold = sqlite3.connect(gold_db); silver = sqlite3.connect(silver_db)
    try:
        games = {r[0]: r[1:] for r in silver.execute(
            "SELECT game_id, home_score, away_score, season_label FROM games WHERE home_score IS NOT NULL AND away_score IS NOT NULL"
        )}
        cols = ["game_id", "game_date", "home_team_abbr", "away_team_abbr", *FEATURE_COLUMNS]
        query = f"SELECT {', '.join(cols)} FROM gold_matchup_features ORDER BY game_date, game_id"
        rows = []
        for values in gold.execute(query):
            row = dict(zip(cols, values)); target = games.get(str(row["game_id"]))
            if not target: continue
            home_score, away_score, season_label = target
            margin = int(home_score) - int(away_score)
            row.update(home_score=int(home_score), away_score=int(away_score), home_win=int(margin > 0), home_margin=margin, season_label=season_label)
            rows.append(row)
        return rows
    finally:
        gold.close(); silver.close()


def matrix(rows):
    return np.asarray([[r.get(c) for c in FEATURE_COLUMNS] for r in rows], dtype=float)


def split_points(n):
    if n < 100: raise ValueError(f"Need at least 100 completed games, got {n}")
    train_end = int(n * 0.70); validation_end = int(n * 0.85)
    return train_end, validation_end


def class_metrics(y, p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    auc = None if len(np.unique(y)) < 2 else float(roc_auc_score(y, p))
    return {"log_loss": float(log_loss(y, p, labels=[0, 1])), "brier_score": float(brier_score_loss(y, p)), "accuracy": float(accuracy_score(y, p >= 0.5)), "roc_auc": auc}


def reg_metrics(y, p):
    corr = float(np.corrcoef(y, p)[0, 1]) if len(y) > 1 else 0.0
    return {"mae": float(mean_absolute_error(y, p)), "rmse": float(math.sqrt(mean_squared_error(y, p))), "correlation": corr}


def elo_probabilities(rows, home_advantage=65.0, k=20.0):
    ratings = {}; probs = []
    for row in rows:
        home, away = str(row["home_team_abbr"]), str(row["away_team_abbr"])
        hr, ar = ratings.get(home, 1500.0), ratings.get(away, 1500.0)
        p = 1.0 / (1.0 + 10 ** (-((hr + home_advantage) - ar) / 400.0)); probs.append(p)
        outcome = float(row["home_win"])
        ratings[home] = hr + k * (outcome - p); ratings[away] = ar - k * (outcome - p)
    return np.asarray(probs)


def calibration(y, p):
    observed, predicted = calibration_curve(y, p, n_bins=10, strategy="quantile")
    return [{"mean_predicted": float(a), "observed_rate": float(b)} for a, b in zip(predicted, observed)]


def train(rows, output_dir):
    train_end, validation_end = split_points(len(rows))
    X = matrix(rows); y_win = np.asarray([r["home_win"] for r in rows]); y_margin = np.asarray([r["home_margin"] for r in rows], dtype=float)
    train_slice = slice(0, train_end)
    clf = Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler()), ("model", LogisticRegression(max_iter=2000, random_state=42))])
    reg = Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler()), ("model", Ridge(alpha=10.0))])
    dummy_clf = DummyClassifier(strategy="prior"); dummy_reg = DummyRegressor(strategy="mean")
    clf.fit(X[train_slice], y_win[train_slice]); reg.fit(X[train_slice], y_margin[train_slice])
    dummy_clf.fit(X[train_slice], y_win[train_slice]); dummy_reg.fit(X[train_slice], y_margin[train_slice])
    elo = elo_probabilities(rows); evaluation = {}; predictions = []
    for name, slc in {"validation": slice(train_end, validation_end), "test": slice(validation_end, len(rows))}.items():
        p = clf.predict_proba(X[slc])[:, 1]; dp = dummy_clf.predict_proba(X[slc])[:, 1]
        margin = reg.predict(X[slc]); dmargin = dummy_reg.predict(X[slc])
        evaluation[name] = {
            "logistic_regression": class_metrics(y_win[slc], p), "dummy_probability": class_metrics(y_win[slc], dp), "elo": class_metrics(y_win[slc], elo[slc]),
            "ridge_margin": reg_metrics(y_margin[slc], margin), "dummy_margin": reg_metrics(y_margin[slc], dmargin), "calibration": calibration(y_win[slc], p),
        }
        for idx, pp, ep, mp in zip(range(*slc.indices(len(rows))), p, elo[slc], margin):
            row = rows[idx]; predictions.append({"split": name, "game_id": row["game_id"], "game_date": row["game_date"], "home_team_abbr": row["home_team_abbr"], "away_team_abbr": row["away_team_abbr"], "actual_home_win": row["home_win"], "actual_home_margin": row["home_margin"], "predicted_home_win_probability": round(float(pp), 6), "elo_home_win_probability": round(float(ep), 6), "predicted_home_margin": round(float(mp), 4)})
    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": clf, "features": FEATURE_COLUMNS, "version": MODEL_VERSION}, output_dir / "home-win-logistic.joblib")
    joblib.dump({"model": reg, "features": FEATURE_COLUMNS, "version": MODEL_VERSION}, output_dir / "home-margin-ridge.joblib")
    with (output_dir / "baseline-predictions.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(predictions[0])); writer.writeheader(); writer.writerows(predictions)
    seasons = sorted({str(r["season_label"]) for r in rows})
    report = {
        "model_version": MODEL_VERSION, "generated_at": utc_now(),
        "dataset": {"rows": len(rows), "features": FEATURE_COLUMNS, "train_rows": train_end, "validation_rows": validation_end - train_end, "test_rows": len(rows) - validation_end, "train_end_date": rows[train_end - 1]["game_date"], "validation_end_date": rows[validation_end - 1]["game_date"], "test_end_date": rows[-1]["game_date"], "seasons": seasons},
        "evaluation": evaluation,
        "guardrails": {"chronological_split": True, "random_shuffle": False, "gold_point_in_time_features_only": True, "odds_used_for_training": False},
        "decision": {"ready_for_baseline_review": True, "ready_for_betting_backtest": len(seasons) >= 3, "note": "Single-season results are a pilot, not evidence of durable betting edge."},
    }
    (output_dir / "baseline-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def self_test(output_dir):
    rng = np.random.default_rng(42); rows = []
    for i in range(240):
        signal = float(rng.normal()); margin = int(round(5 * signal + rng.normal(0, 8)))
        row = {c: float(rng.normal()) for c in FEATURE_COLUMNS}; row["net_rtg_last_10_diff"] = signal * 8
        row.update(game_id=f"g{i:04d}", game_date=f"2025-{1 + i // 28:02d}-{1 + i % 28:02d}", home_team_abbr=f"H{i % 8}", away_team_abbr=f"A{i % 8}", home_win=int(margin > 0), home_margin=margin, season_label="synthetic")
        rows.append(row)
    report = train(rows, output_dir)
    assert report["dataset"]["rows"] == 240
    (output_dir / "self-test.json").write_text(json.dumps({"passed": True}, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--gold-db", type=Path); parser.add_argument("--silver-db", type=Path); parser.add_argument("--output-dir", type=Path, required=True); parser.add_argument("--self-test", action="store_true"); args = parser.parse_args()
    if args.self_test: self_test(args.output_dir); return
    if not args.gold_db or not args.silver_db: parser.error("--gold-db and --silver-db are required unless --self-test is used")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp); gold = tmp / "gold.sqlite"; silver = tmp / "silver.sqlite"; ungzip(args.gold_db, gold); ungzip(args.silver_db, silver)
        report = train(load_rows(gold, silver), args.output_dir); print(json.dumps(report["decision"], indent=2))

if __name__ == "__main__": main()
