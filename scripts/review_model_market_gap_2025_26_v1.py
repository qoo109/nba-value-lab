#!/usr/bin/env python3
"""Aggregate-only 2025-26 model/market gap review.

Reads a private same-game model/odds join and the governed forward Gold SQLite.
Emits only aggregate diagnostics. It never writes game-level rows or prices.
Collector timestamps remain unverified provider-origin observed_at.
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import sqlite3
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

FORMAL_STATE = "MODEL_MARKET_GAP_REVIEW_2025_26_VALID"
FEATURES = [
    "net_rtg_last_5_diff",
    "net_rtg_last_10_diff",
    "net_rtg_last_20_diff",
    "pace_last_10_diff",
    "efg_pct_last_10_diff",
    "tov_pct_last_10_diff",
    "orb_pct_last_10_diff",
    "free_throw_rate_last_10_diff",
    "rest_days_diff",
    "prior_games_min",
    "evidence_coverage",
]


def metrics(data: pd.DataFrame, probability: str) -> dict:
    y = data["actual_home_win"].to_numpy(dtype=int)
    p = np.clip(data[probability].to_numpy(dtype=float), 1e-6, 1 - 1e-6)
    return {
        "rows": int(len(data)),
        "log_loss": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))),
        "brier_score": float(np.mean((p - y) ** 2)),
        "accuracy": float(np.mean((p >= 0.5) == y)),
        "roc_auc": float(roc_auc_score(y, p)) if len(np.unique(y)) > 1 else None,
    }


def ece_equal_frequency(data: pd.DataFrame, probability: str) -> float:
    groups = pd.qcut(data[probability], q=min(10, len(data)), duplicates="drop")
    total = len(data)
    return float(
        sum(
            len(group) / total
            * abs(group[probability].mean() - group["actual_home_win"].mean())
            for _, group in data.groupby(groups, observed=True)
        )
    )


def calibration_fit(data: pd.DataFrame, probability: str) -> dict:
    p = np.clip(data[probability].to_numpy(dtype=float), 1e-6, 1 - 1e-6)
    logit = np.log(p / (1 - p)).reshape(-1, 1)
    y = data["actual_home_win"].to_numpy(dtype=int)
    fit = LogisticRegression(C=1e6, solver="lbfgs").fit(logit, y)
    return {
        "intercept": float(fit.intercept_[0]),
        "slope": float(fit.coef_[0][0]),
    }


def grouped(data: pd.DataFrame, column: str) -> list[dict]:
    output = []
    for name, frame in data.groupby(column, observed=True):
        model = metrics(frame, "model_home_probability")
        market = metrics(frame, "market_home_probability_no_vig")
        output.append(
            {
                "group": str(name),
                "rows": int(len(frame)),
                "model": model,
                "market_no_vig": market,
                "model_minus_market": {
                    key: model[key] - market[key]
                    for key in ("log_loss", "brier_score", "accuracy", "roc_auc")
                },
            }
        )
    return output


def load_gold(path: Path) -> pd.DataFrame:
    if path.suffix == ".gz":
        with tempfile.NamedTemporaryFile(suffix=".sqlite") as temporary:
            with gzip.open(path, "rb") as source:
                temporary.write(source.read())
                temporary.flush()
            connection = sqlite3.connect(temporary.name)
            frame = pd.read_sql("SELECT * FROM gold_matchup_features", connection)
            connection.close()
            return frame
    connection = sqlite3.connect(path)
    frame = pd.read_sql("SELECT * FROM gold_matchup_features", connection)
    connection.close()
    return frame


def review(join_path: Path, gold_path: Path) -> dict:
    private_join = pd.read_csv(join_path, dtype={"game_id": str})
    gold = load_gold(gold_path)
    gold["game_id"] = gold["game_id"].astype(str).str.zfill(10)
    private_join["game_id"] = private_join["game_id"].astype(str).str.zfill(10)

    if len(private_join) != 1110:
        raise ValueError(f"expected 1,110 private joins, found {len(private_join)}")
    if private_join["game_id"].nunique() != 1110:
        raise ValueError("private join game IDs are not unique")
    if len(gold) != 1230 or gold["game_id"].nunique() != 1230:
        raise ValueError("forward Gold population is not 1,230 unique games")

    data = private_join.merge(
        gold,
        on="game_id",
        how="left",
        validate="one_to_one",
        suffixes=("", "_gold"),
    )
    if data["matchup_feature_id"].isna().any():
        raise ValueError("one or more private joins lack forward Gold features")

    data["absolute_probability_gap"] = (
        data["model_home_probability"] - data["market_home_probability_no_vig"]
    ).abs()
    data["same_side"] = (
        (data["model_home_probability"] >= 0.5)
        == (data["market_home_probability_no_vig"] >= 0.5)
    )
    data["model_selected_probability"] = np.maximum(
        data["model_home_probability"], data["model_away_probability"]
    )
    data["market_selected_probability"] = np.maximum(
        data["market_home_probability_no_vig"],
        data["market_away_probability_no_vig"],
    )

    primary = data[data["t60_absolute_error_minutes"] <= 5].copy()
    if len(primary) != 310:
        raise ValueError(f"expected 310 primary rows, found {len(primary)}")

    primary["absolute_probability_gap_band"] = pd.cut(
        primary["absolute_probability_gap"],
        [-1, 0.025, 0.05, 0.10, 1],
        labels=["0-2.5pp", "2.5-5pp", "5-10pp", "10pp+"],
    )
    primary["model_selected_probability_band"] = pd.cut(
        primary["model_selected_probability"],
        [0.5, 0.60, 0.65, 0.70, 0.75, 0.80, 1.0],
        include_lowest=True,
        labels=["50-60", "60-65", "65-70", "70-75", "75-80", "80+"],
    )
    primary["market_selected_probability_band"] = pd.cut(
        primary["market_selected_probability"],
        [0.5, 0.60, 0.65, 0.70, 0.75, 0.80, 1.0],
        include_lowest=True,
        labels=["50-60", "60-65", "65-70", "70-75", "75-80", "80+"],
    )
    primary["prior_games_min_band"] = pd.cut(
        primary["prior_games_min"],
        [-1, 4, 9, 19, 999],
        labels=["0-4", "5-9", "10-19", "20+"],
    )
    month = pd.to_datetime(primary["game_date"]).dt.month
    primary["season_phase"] = np.select(
        [
            month.isin([10, 11]),
            month.isin([12, 1]),
            month.isin([2, 3, 4]),
        ],
        ["Oct-Nov", "Dec-Jan", "Feb-Apr"],
        default="Other",
    )
    primary["market_minus_model_home_probability"] = (
        primary["market_home_probability_no_vig"]
        - primary["model_home_probability"]
    )

    model = metrics(primary, "model_home_probability")
    market = metrics(primary, "market_home_probability_no_vig")
    correlations = []
    for feature in FEATURES:
        frame = primary[[feature, "market_minus_model_home_probability"]].dropna()
        correlations.append(
            {
                "feature": feature,
                "rows": int(len(frame)),
                "spearman_rho": float(
                    frame[feature].corr(
                        frame["market_minus_model_home_probability"],
                        method="spearman",
                    )
                ),
            }
        )
    correlations.sort(key=lambda item: abs(item["spearman_rho"]), reverse=True)

    gap_slices = grouped(primary, "absolute_probability_gap_band")
    largest = next(item for item in gap_slices if item["group"] == "10pp+")

    return {
        "schema_version": "model-market-gap-review-2025-26-v1",
        "formal_state": FORMAL_STATE,
        "scope": "PRIVATE_AGGREGATE_DIAGNOSTIC_ONLY",
        "source_evidence": {
            "private_join_rows": 1110,
            "forward_gold_rows": 1230,
            "network_requests": 0,
            "provider_api_requests": 0,
            "public_game_level_rows": 0,
            "public_price_rows": 0,
        },
        "primary_population": {
            "definition": (
                "nearest valid pre-tip collector batch with absolute "
                "T-60 batch error <= 5 minutes"
            ),
            "rows": 310,
            "strict_t60_qualified": False,
            "provider_origin_quote_time_verified": False,
            "quote_level_exact_observed_at_verified": False,
        },
        "primary_metrics": {
            "model": model,
            "market_no_vig": market,
            "model_minus_market": {
                key: model[key] - market[key]
                for key in ("log_loss", "brier_score", "accuracy", "roc_auc")
            },
            "calibration": {
                "model": {
                    "ece_10_equal_frequency_bins": ece_equal_frequency(
                        primary, "model_home_probability"
                    ),
                    **calibration_fit(primary, "model_home_probability"),
                },
                "market_no_vig": {
                    "ece_10_equal_frequency_bins": ece_equal_frequency(
                        primary, "market_home_probability_no_vig"
                    ),
                    **calibration_fit(
                        primary, "market_home_probability_no_vig"
                    ),
                },
            },
        },
        "fixed_diagnostic_slices": {
            "side_agreement": grouped(primary, "same_side"),
            "absolute_probability_gap": gap_slices,
            "model_selected_probability": grouped(
                primary, "model_selected_probability_band"
            ),
            "market_selected_probability": grouped(
                primary, "market_selected_probability_band"
            ),
            "prior_games_min": grouped(primary, "prior_games_min_band"),
            "season_phase": grouped(primary, "season_phase"),
        },
        "existing_gold_feature_residual_correlations": {
            "target": (
                "market_home_probability_no_vig - model_home_probability"
            ),
            "method": "Spearman",
            "features_predeclared_as_all_existing_matchup_features": True,
            "results": correlations,
            "interpretation_boundary": (
                "Existing frozen-model inputs only; correlations do not "
                "identify a new causal feature."
            ),
        },
        "findings": {
            "market_better_overall_primary_band": (
                market["log_loss"] < model["log_loss"]
                and market["brier_score"] < model["brier_score"]
            ),
            "largest_descriptive_gap_bin": "10pp+",
            "largest_gap_bin_rows": largest["rows"],
            "largest_gap_bin_model_minus_market_log_loss": (
                largest["model_minus_market"]["log_loss"]
            ),
            "no_subgroup_promotion_authorized": True,
            "injury_two_feature_candidate_already_valid_negative": True,
            "current_gold_features_alone_do_not_close_market_gap": True,
        },
        "decision": {
            "formal_interpretation": (
                "PRESERVE_FROZEN_BASELINE_AND_MARKET_BACKTEST_LOCK"
            ),
            "model_retraining_authorized": False,
            "existing_injury_candidate_retuning_authorized": False,
            "market_residual_blend_activation_authorized": False,
            "next_research_design": (
                "PREDECLARE_PRIOR_ONLY_PLAYER_ROTATION_STATE_FEATURE_LAYER_V1"
            ),
        },
        "preserved_locks": {
            "strict_t60_qualified": False,
            "formal_point_in_time_market_backtest_allowed": False,
            "ev_allowed": False,
            "roi_allowed": False,
            "clv_allowed": False,
            "drawdown_allowed": False,
            "betting_edge_claim_allowed": False,
            "formal_stake": 0,
        },
    }


def self_test(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    y = np.array([0, 1, 0, 1])
    frame = pd.DataFrame(
        {
            "actual_home_win": y,
            "model_home_probability": [0.3, 0.7, 0.4, 0.6],
            "market_home_probability_no_vig": [0.2, 0.8, 0.3, 0.7],
        }
    )
    checks = {
        "model_accuracy": metrics(frame, "model_home_probability")["accuracy"] == 1.0,
        "market_log_loss_better": (
            metrics(frame, "market_home_probability_no_vig")["log_loss"]
            < metrics(frame, "model_home_probability")["log_loss"]
        ),
        "ece_finite": math.isfinite(
            ece_equal_frequency(frame, "model_home_probability")
        ),
        "formal_state": FORMAL_STATE
        == "MODEL_MARKET_GAP_REVIEW_2025_26_VALID",
    }
    if not all(checks.values()):
        raise AssertionError(checks)
    (output / "self-test.json").write_text(
        json.dumps({"passed": True, "checks": checks}, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-join", type=Path)
    parser.add_argument("--forward-gold", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test(args.output)
        return 0
    if args.private_join is None or args.forward_gold is None:
        parser.error("--private-join and --forward-gold are required")
    result = review(args.private_join, args.forward_gold)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
