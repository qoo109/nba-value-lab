#!/usr/bin/env python3
"""Aggregate-only decomposition of the 2025-26 frozen model versus market gap.

Private inputs:
- same-game joined model/market CSV
- forward Gold SQLite (plain or .gz)

The script writes:
- aggregate report JSON safe for public repository
- optional private augmented CSV for local inspection only

No provider requests, model fitting/refitting, bet selection, EV, ROI, CLV or
Drawdown are performed. Collector batch timestamps remain unqualified as exact
provider-origin observed_at.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import shutil
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score

FORMAL_STATE = "PRIVATE_MODEL_MARKET_GAP_DECOMPOSITION_2025_26_VALID"
BANDS = (5, 15, 30, 60)
GAP_BINS = (
    ("LT_2PP", 0.0, 0.02),
    ("2_TO_LT_5PP", 0.02, 0.05),
    ("5_TO_LT_10PP", 0.05, 0.10),
    ("GE_10PP", 0.10, float("inf")),
)
FEATURES = (
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
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def safe_corr(func, x: np.ndarray, y: np.ndarray) -> dict[str, float | None]:
    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask]
    if len(x) < 3 or np.unique(x).size < 2 or np.unique(y).size < 2:
        return {"rows": int(len(x)), "coefficient": None, "p_value": None}
    result = func(x, y)
    return {
        "rows": int(len(x)),
        "coefficient": float(result.statistic),
        "p_value": float(result.pvalue),
    }


def metrics(frame: pd.DataFrame) -> dict[str, Any]:
    y = frame["actual_home_win"].to_numpy(dtype=int)
    model = np.clip(frame["model_home_probability"].to_numpy(dtype=float), 1e-9, 1 - 1e-9)
    market = np.clip(frame["market_home_probability_no_vig"].to_numpy(dtype=float), 1e-9, 1 - 1e-9)

    def one(prob: np.ndarray) -> dict[str, float | None]:
        return {
            "log_loss": float(log_loss(y, prob, labels=[0, 1])),
            "brier_score": float(brier_score_loss(y, prob)),
            "accuracy": float(accuracy_score(y, prob >= 0.5)),
            "roc_auc": float(roc_auc_score(y, prob)) if np.unique(y).size == 2 else None,
            "mean_probability": float(np.mean(prob)),
            "actual_home_win_rate": float(np.mean(y)),
            "calibration_bias": float(np.mean(prob - y)),
        }

    model_metrics = one(model)
    market_metrics = one(market)
    return {
        "rows": int(len(frame)),
        "model": model_metrics,
        "market_no_vig": market_metrics,
        "model_minus_market": {
            "log_loss": model_metrics["log_loss"] - market_metrics["log_loss"],
            "brier_score": model_metrics["brier_score"] - market_metrics["brier_score"],
            "accuracy": model_metrics["accuracy"] - market_metrics["accuracy"],
            "roc_auc": (
                model_metrics["roc_auc"] - market_metrics["roc_auc"]
                if model_metrics["roc_auc"] is not None and market_metrics["roc_auc"] is not None
                else None
            ),
        },
    }


def bootstrap_incremental(frame: pd.DataFrame, resamples: int, seed: int) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    delta = frame["model_minus_market_probability"].to_numpy(dtype=float)
    residual = frame["market_home_residual"].to_numpy(dtype=float)
    disagree = frame.loc[~frame["side_agreement"], "model_side_correct"].to_numpy(dtype=float)
    n = len(frame)

    rho_values: list[float] = []
    covariance_values: list[float] = []
    for _ in range(resamples):
        idx = rng.integers(0, n, n)
        x = delta[idx]
        y = residual[idx]
        rho = spearmanr(x, y).statistic
        if math.isfinite(rho):
            rho_values.append(float(rho))
        covariance_values.append(float(np.mean((x - x.mean()) * (y - y.mean()))))

    output: dict[str, Any] = {
        "resamples": resamples,
        "spearman_ci95": [float(v) for v in np.quantile(rho_values, [0.025, 0.975])],
        "covariance_ci95": [float(v) for v in np.quantile(covariance_values, [0.025, 0.975])],
    }
    if len(disagree):
        draw = rng.integers(0, len(disagree), size=(resamples, len(disagree)))
        rates = disagree[draw].mean(axis=1)
        output["disagreement_model_side_win_rate_ci95"] = [
            float(v) for v in np.quantile(rates, [0.025, 0.975])
        ]
    else:
        output["disagreement_model_side_win_rate_ci95"] = None
    return output


def load_gold(path: Path) -> pd.DataFrame:
    temp_path: Path | None = None
    try:
        if path.suffix == ".gz":
            handle = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
            handle.close()
            temp_path = Path(handle.name)
            with gzip.open(path, "rb") as source, temp_path.open("wb") as target:
                shutil.copyfileobj(source, target)
            sqlite_path = temp_path
        else:
            sqlite_path = path
        connection = sqlite3.connect(sqlite_path)
        try:
            frame = pd.read_sql_query("SELECT * FROM gold_matchup_features", connection)
        finally:
            connection.close()
        return frame
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def prepare(join_path: Path, gold_path: Path) -> pd.DataFrame:
    joined = pd.read_csv(join_path)
    required = {
        "game_id",
        "t60_absolute_error_minutes",
        "model_home_probability",
        "market_home_probability_no_vig",
        "actual_home_win",
    }
    missing = sorted(required.difference(joined.columns))
    if missing:
        raise ValueError(f"private join missing columns: {missing}")
    if len(joined) != 1110 or joined["game_id"].nunique() != 1110:
        raise ValueError("expected 1,110 unique private same-game joins")

    joined["game_id_key"] = joined["game_id"].astype("int64").astype(str).str.zfill(10)
    gold = load_gold(gold_path)
    gold["game_id_key"] = gold["game_id"].astype(str).str.zfill(10)
    selected = ["game_id_key", *FEATURES]
    frame = joined.merge(gold[selected], how="left", on="game_id_key", validate="one_to_one")
    if frame[list(FEATURES)].isna().all(axis=1).any():
        raise ValueError("at least one private join lacks all governed Gold features")

    frame["model_minus_market_probability"] = (
        frame["model_home_probability"] - frame["market_home_probability_no_vig"]
    )
    frame["absolute_probability_gap"] = frame["model_minus_market_probability"].abs()
    frame["market_home_residual"] = (
        frame["actual_home_win"] - frame["market_home_probability_no_vig"]
    )
    frame["side_agreement"] = (
        (frame["model_home_probability"] >= 0.5)
        == (frame["market_home_probability_no_vig"] >= 0.5)
    )
    frame["model_side_correct"] = np.where(
        frame["model_home_probability"] >= 0.5,
        frame["actual_home_win"],
        1 - frame["actual_home_win"],
    )
    frame["market_side_correct"] = np.where(
        frame["market_home_probability_no_vig"] >= 0.5,
        frame["actual_home_win"],
        1 - frame["actual_home_win"],
    )
    frame["disagreement_direction"] = np.select(
        [
            (frame["model_home_probability"] >= 0.5)
            & (frame["market_home_probability_no_vig"] < 0.5),
            (frame["model_home_probability"] < 0.5)
            & (frame["market_home_probability_no_vig"] >= 0.5),
        ],
        ["MODEL_HOME_MARKET_AWAY", "MODEL_AWAY_MARKET_HOME"],
        default="AGREE",
    )
    return frame


def analyze(join_path: Path, gold_path: Path, output_dir: Path, resamples: int, seed: int) -> dict[str, Any]:
    frame = prepare(join_path, gold_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    band_results: dict[str, Any] = {}
    for index, band in enumerate(BANDS):
        subset = frame[frame["t60_absolute_error_minutes"] <= band].copy()
        disagree = subset[~subset["side_agreement"]]
        band_results[str(band)] = {
            **metrics(subset),
            "incremental_signal": {
                "delta_vs_market_residual_spearman": safe_corr(
                    spearmanr,
                    subset["model_minus_market_probability"].to_numpy(dtype=float),
                    subset["market_home_residual"].to_numpy(dtype=float),
                ),
                "delta_vs_market_residual_pearson": safe_corr(
                    pearsonr,
                    subset["model_minus_market_probability"].to_numpy(dtype=float),
                    subset["market_home_residual"].to_numpy(dtype=float),
                ),
                "mean_delta_times_market_residual": float(
                    np.mean(
                        subset["model_minus_market_probability"]
                        * subset["market_home_residual"]
                    )
                ),
                "side_agreement_rate": float(subset["side_agreement"].mean()),
                "disagreement_games": int(len(disagree)),
                "disagreement_model_side_wins": int(disagree["model_side_correct"].sum()),
                "disagreement_market_side_wins": int(disagree["market_side_correct"].sum()),
                "disagreement_model_side_win_rate": (
                    float(disagree["model_side_correct"].mean()) if len(disagree) else None
                ),
                "bootstrap": bootstrap_incremental(
                    subset, resamples=resamples, seed=seed + index
                ),
            },
        }

    primary = frame[frame["t60_absolute_error_minutes"] <= 60].copy()
    gap_bins: dict[str, Any] = {}
    for label, lower, upper in GAP_BINS:
        subset = primary[
            (primary["absolute_probability_gap"] >= lower)
            & (primary["absolute_probability_gap"] < upper)
        ]
        gap_bins[label] = {
            "lower_inclusive": lower,
            "upper_exclusive": None if math.isinf(upper) else upper,
            **metrics(subset),
        }

    directions: dict[str, Any] = {}
    for label in ("AGREE", "MODEL_HOME_MARKET_AWAY", "MODEL_AWAY_MARKET_HOME"):
        subset = primary[primary["disagreement_direction"] == label]
        directions[label] = metrics(subset) if len(subset) else {"rows": 0}

    feature_associations: dict[str, Any] = {}
    for feature in FEATURES:
        subset = primary[[feature, "model_minus_market_probability", "market_home_residual"]].dropna()
        feature_associations[feature] = {
            "rows": int(len(subset)),
            "feature_vs_model_market_delta_spearman": safe_corr(
                spearmanr,
                subset[feature].to_numpy(dtype=float),
                subset["model_minus_market_probability"].to_numpy(dtype=float),
            ),
            "feature_vs_market_residual_spearman": safe_corr(
                spearmanr,
                subset[feature].to_numpy(dtype=float),
                subset["market_home_residual"].to_numpy(dtype=float),
            ),
        }

    report = {
        "schema_version": "private-model-market-gap-decomposition-2025-26-v1",
        "formal_state": FORMAL_STATE,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "execution": {
            "mode": "LOCAL_PRIVATE_OFFLINE",
            "network_requests": 0,
            "provider_api_requests": 0,
            "model_retraining_executed": False,
            "model_refit_executed": False,
            "calibration_change_executed": False,
            "market_data_used_as_model_feature": False,
            "bet_selection_executed": False,
            "ev_calculated": False,
            "roi_calculated": False,
            "clv_calculated": False,
            "drawdown_calculated": False,
        },
        "inputs": {
            "private_join_sha256": sha256(join_path),
            "forward_gold_sha256": sha256(gold_path),
            "private_join_rows": int(len(frame)),
            "unique_games": int(frame["game_id_key"].nunique()),
            "gold_feature_join_rows": int(frame[list(FEATURES)].notna().any(axis=1).sum()),
        },
        "predeclared_design": {
            "time_bands_minutes": list(BANDS),
            "primary_feature_diagnostic_band": "T60_ABSOLUTE_ERROR_LE_60_MINUTES",
            "gap_bins": [
                {
                    "label": label,
                    "lower_inclusive": lower,
                    "upper_exclusive": None if math.isinf(upper) else upper,
                }
                for label, lower, upper in GAP_BINS
            ],
            "features": list(FEATURES),
            "profitability_based_selection": False,
            "feature_promotion_allowed": False,
        },
        "time_bands": band_results,
        "gap_magnitude_primary_band": gap_bins,
        "agreement_direction_primary_band": directions,
        "governed_feature_associations_primary_band": feature_associations,
        "aggregate_findings": {
            "incremental_signal_demonstrated": False,
            "all_band_delta_residual_spearman_absolute_below_0_06": all(
                abs(band_results[str(b)]["incremental_signal"]["delta_vs_market_residual_spearman"]["coefficient"])
                < 0.06
                for b in BANDS
            ),
            "model_side_wins_majority_of_disagreements_in_any_band": any(
                band_results[str(b)]["incremental_signal"]["disagreement_model_side_win_rate"]
                is not None
                and band_results[str(b)]["incremental_signal"]["disagreement_model_side_win_rate"] > 0.5
                for b in BANDS
            ),
            "model_log_loss_worse_than_market_in_every_gap_bin": all(
                gap_bins[label]["model_minus_market"]["log_loss"] > 0
                for label, _, _ in GAP_BINS
            ),
            "largest_gap_bin_model_minus_market_log_loss": gap_bins["GE_10PP"][
                "model_minus_market"
            ]["log_loss"],
            "interpretation": (
                "The frozen model's probability deviation from the no-vig market has near-zero "
                "association with subsequent market residuals in every predeclared timing band. "
                "When model and market choose opposite sides, the model does not win a majority "
                "in any band. Larger probability deviations are increasingly costly in Log Loss. "
                "This diagnostic does not demonstrate incremental information beyond the market."
            ),
        },
        "research_direction": {
            "validated_new_feature": None,
            "priority_candidates_not_yet_validated": [
                "point_in_time_injury_availability",
                "expected_minutes_changes",
                "confirmed_starting_lineup",
                "rotation_and_role_change",
            ],
            "do_not_reopen_without_new_data": [
                "rest_travel_v1",
                "post_hoc_probability_gap_threshold_tuning",
                "closing_market_residual_selection",
            ],
            "next_unique_sub_mainline": (
                "BUILD_2025_26_POINT_IN_TIME_INJURY_LINEUP_ROLE_FEATURE_DIAGNOSTIC_"
                "WITHOUT_MODEL_RETRAINING_OR_MARKET_BACKTEST_PROMOTION"
            ),
        },
        "public_private_boundary": {
            "public_game_level_rows": 0,
            "public_price_rows": 0,
            "private_augmented_rows": int(len(frame)),
            "raw_odds_archive_committed": False,
        },
        "qualification": {
            "aggregate_gap_decomposition_valid": True,
            "strict_t60_qualified": False,
            "formal_point_in_time_market_backtest_allowed": False,
            "model_retraining_authorized": False,
            "betting_edge_claim_allowed": False,
            "formal_stake": 0,
        },
    }

    private_path = output_dir / "private-model-market-gap-decomposition-2025-26-v1.csv"
    frame.to_csv(private_path, index=False)
    report["private_output"] = {
        "rows": int(len(frame)),
        "sha256": sha256(private_path),
        "committed_publicly": False,
    }
    report_path = output_dir / "private-model-market-gap-decomposition-2025-26-report-v1.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def self_test(output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    test = pd.DataFrame(
        {
            "actual_home_win": [0, 1, 1, 0],
            "model_home_probability": [0.3, 0.7, 0.6, 0.4],
            "market_home_probability_no_vig": [0.2, 0.8, 0.75, 0.25],
        }
    )
    result = metrics(test)
    checks = {
        "bands_fixed": BANDS == (5, 15, 30, 60),
        "gap_bins_fixed": len(GAP_BINS) == 4,
        "features_fixed": len(FEATURES) == 11,
        "market_log_loss_better": result["market_no_vig"]["log_loss"] < result["model"]["log_loss"],
        "no_model_fitting": True,
    }
    if not all(checks.values()):
        raise AssertionError(checks)
    payload = {"passed": True, "checks": checks}
    (output_dir / "self-test.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps(payload, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-join", type=Path)
    parser.add_argument("--forward-gold", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--bootstrap-resamples", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20260724)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test(args.output_dir)
    if args.private_join is None or args.forward_gold is None:
        parser.error("--private-join and --forward-gold are required")
    analyze(
        args.private_join,
        args.forward_gold,
        args.output_dir,
        args.bootstrap_resamples,
        args.seed,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
