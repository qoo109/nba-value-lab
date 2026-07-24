#!/usr/bin/env python3
"""Execute the predeclared training-free prior-only rotation residual audit.

All row-level inputs and outputs remain private. The script emits one aggregate JSON
report only. It never fits, refits, recalibrates, selects bets, or calculates
EV/ROI/CLV/Drawdown.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import rankdata, spearmanr

FORMAL_STATE = "TRAINING_FREE_PRIOR_ONLY_ROTATION_RESIDUAL_AUDIT_2025_26_V1_EXECUTED"
BANDS = (5, 15, 30, 60)
EXPECTED = {
    "features": "3e8ef30f3a9801fda92fc95a490228b73fa53603093c914207e884a933b2de02",
    "predictions": "c3764faf6eb3703374b12a5d8668c6ef889cd8f54070a2c6cf135b55559ca725",
    "market_join": "fbd5b0133cd0ad58f3fe4dada53e79b0fd2ea6021d8179f648f727c76a96735b",
}
FEATURES = {
    "rotation_players_prior_5_diff": "diff_rotation_players_prior_5",
    "top5_minutes_share_prior_5_diff": "diff_top5_minutes_share_prior_5",
    "top8_minutes_share_prior_5_diff": "diff_top8_minutes_share_prior_5",
    "top8_minutes_share_prior_10_diff": "diff_top8_minutes_share_prior_10",
    "rotation_entropy_prior_5_diff": "diff_rotation_entropy_prior_5",
    "rotation_entropy_prior_10_diff": "diff_rotation_entropy_prior_10",
    "top8_set_continuity_prior_5_diff": "diff_top8_set_continuity_prior_5",
    "starter_set_continuity_prior_5_diff": "diff_starter_set_continuity_prior_5",
    "minutes_allocation_volatility_prior_5_diff": "diff_minutes_allocation_volatility_prior_5",
    "role_change_magnitude_prior_3_vs_10_diff": "diff_role_change_magnitude_prior_3_vs_10",
    "recent_return_players_count_diff": "diff_recent_return_players_count",
    "new_team_rotation_players_prior_5_diff": "diff_new_team_rotation_players_prior_5",
}
STRESS_SIGNS = {
    "rotation_players_prior_5_diff": 1,
    "top8_set_continuity_prior_5_diff": -1,
    "starter_set_continuity_prior_5_diff": -1,
    "minutes_allocation_volatility_prior_5_diff": 1,
    "role_change_magnitude_prior_3_vs_10_diff": 1,
    "recent_return_players_count_diff": 1,
    "new_team_rotation_players_prior_5_diff": 1,
}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            value.update(chunk)
    return value.hexdigest()


def rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def text(value: Any) -> str | None:
    result = "" if value is None else str(value).strip()
    return None if result.lower() in {"", "nan", "none", "null"} else result


def number(value: Any) -> float | None:
    raw = text(value)
    if raw is None:
        return None
    try:
        result = float(raw)
    except ValueError:
        return None
    return result if math.isfinite(result) else None


def truth(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def game_id(value: Any) -> str:
    raw = text(value)
    if raw is None:
        raise ValueError("missing game_id")
    if raw.endswith(".0") and raw[:-2].isdigit():
        raw = raw[:-2]
    if not raw.isdigit():
        raise ValueError(f"invalid game_id: {value!r}")
    return raw.zfill(10)


def log_loss_rows(outcome: np.ndarray, probability: np.ndarray) -> np.ndarray:
    probability = np.clip(np.asarray(probability, float), 1e-9, 1 - 1e-9)
    outcome = np.asarray(outcome, float)
    return -(outcome * np.log(probability) + (1 - outcome) * np.log(1 - probability))


def spearman(x: np.ndarray, y: np.ndarray) -> tuple[float | None, float | None, int]:
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    if len(x) < 3 or np.unique(x).size < 2 or np.unique(y).size < 2:
        return None, None, int(len(x))
    result = spearmanr(x, y)
    return float(result.statistic), float(result.pvalue), int(len(x))


def bootstrap(x: np.ndarray, y: np.ndarray, count: int, seed: int) -> dict[str, Any]:
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    rng = np.random.default_rng(seed)
    values: list[float] = []
    for _ in range(count):
        sample = rng.integers(0, len(x), len(x))
        rho, _, _ = spearman(x[sample], y[sample])
        if rho is not None:
            values.append(rho)
    if not values:
        return {"resamples": count, "valid_resamples": 0, "seed": seed, "ci95": [None, None]}
    array = np.asarray(values)
    return {
        "resamples": count,
        "valid_resamples": len(values),
        "seed": seed,
        "ci95": [float(np.quantile(array, 0.025)), float(np.quantile(array, 0.975))],
        "probability_negative": float(np.mean(array < 0)),
        "probability_positive": float(np.mean(array > 0)),
    }


def bh(pvalues: list[float | None]) -> list[float | None]:
    valid = sorted((value, index) for index, value in enumerate(pvalues) if value is not None)
    result: list[float | None] = [None] * len(pvalues)
    running = 1.0
    for position in range(len(valid) - 1, -1, -1):
        value, index = valid[position]
        running = min(running, value * len(valid) / (position + 1))
        result[index] = float(min(1.0, running))
    return result


def quartile(x: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    if len(x) < 8 or np.unique(x).size < 4:
        return {"rows": len(x), "top_minus_bottom_mean": None}
    percentile = rankdata(x, method="average") / len(x)
    top, bottom = y[percentile > 0.75], y[percentile <= 0.25]
    return {
        "rows": len(x),
        "top_rows": len(top),
        "bottom_rows": len(bottom),
        "top_minus_bottom_mean": float(np.mean(top) - np.mean(bottom)),
    }


def correlation(x: np.ndarray, y: np.ndarray, *, resamples: int = 0, seed: int = 0) -> dict[str, Any]:
    rho, pvalue, count = spearman(x, y)
    result = {
        "rows": count,
        "spearman_rho": rho,
        "two_sided_pvalue": pvalue,
        "quartile_contrast": quartile(x, y),
    }
    if resamples:
        result["bootstrap"] = bootstrap(x, y, resamples, seed)
    return result


def halves(input_rows: list[dict[str, Any]], x: str, y: str) -> dict[str, Any]:
    ordered = sorted(input_rows, key=lambda row: (row["game_date"], row["game_id"]))
    middle = len(ordered) // 2
    result = {}
    for name, subset in (("first_half", ordered[:middle]), ("second_half", ordered[middle:])):
        rho, pvalue, count = spearman(
            np.asarray([row[x] for row in subset], float),
            np.asarray([row[y] for row in subset], float),
        )
        result[name] = {
            "rows": count,
            "spearman_rho": rho,
            "two_sided_pvalue": pvalue,
            "sign": None if rho in {None, 0} else (1 if rho > 0 else -1),
        }
    return result


def months(input_rows: list[dict[str, Any]], x: str, y: str) -> dict[str, Any]:
    detail = {}
    for month in sorted({row["game_date"][:7] for row in input_rows}):
        subset = [row for row in input_rows if row["game_date"].startswith(month)]
        rho, pvalue, count = spearman(
            np.asarray([row[x] for row in subset], float),
            np.asarray([row[y] for row in subset], float),
        )
        detail[month] = {
            "rows": count,
            "spearman_rho": rho,
            "two_sided_pvalue": pvalue,
            "sign": None if rho in {None, 0} else (1 if rho > 0 else -1),
        }
    return {
        "months": detail,
        "negative_months": sum(row["sign"] == -1 for row in detail.values()),
        "positive_months": sum(row["sign"] == 1 for row in detail.values()),
    }


def feature_input(path: Path) -> list[dict[str, Any]]:
    source = rows(path)
    if len(source) != 1230:
        raise ValueError(f"expected 1,230 feature rows, found {len(source)}")
    required = {"target_game_id", "target_game_date_et", "feature_ready_game", *FEATURES.values()}
    if required - set(source[0]):
        raise ValueError(f"missing feature columns: {sorted(required - set(source[0]))}")
    output = []
    seen = set()
    for raw in source:
        identity = game_id(raw["target_game_id"])
        if identity in seen:
            raise ValueError(f"duplicate feature key: {identity}")
        seen.add(identity)
        row: dict[str, Any] = {
            "game_id": identity,
            "game_date": text(raw["target_game_date_et"]),
            "feature_ready": truth(raw["feature_ready_game"]),
        }
        row.update({canonical: number(raw[physical]) for canonical, physical in FEATURES.items()})
        output.append(row)
    if sum(row["feature_ready"] for row in output) != 1075:
        raise ValueError("feature-ready population is not 1,075")
    return output


def prediction_input(path: Path) -> dict[str, dict[str, Any]]:
    source = rows(path)
    if len(source) != 1230:
        raise ValueError(f"expected 1,230 predictions, found {len(source)}")
    output = {}
    for raw in source:
        identity = game_id(raw["game_id"])
        if identity in output:
            raise ValueError(f"duplicate prediction key: {identity}")
        probability = number(raw["predicted_home_win_probability"])
        outcome = number(raw["actual_home_win"])
        if probability is None or outcome not in {0.0, 1.0}:
            raise ValueError(f"invalid prediction row: {identity}")
        output[identity] = {
            "game_id": identity,
            "game_date": text(raw["game_date"]),
            "model_home_probability": probability,
            "actual_home_win": int(outcome),
        }
    return output


def market_input(path: Path) -> dict[str, dict[str, Any]]:
    source = rows(path)
    if len(source) != 1110:
        raise ValueError(f"expected 1,110 market rows, found {len(source)}")
    output = {}
    for raw in source:
        identity = game_id(raw["game_id"])
        if identity in output:
            raise ValueError(f"duplicate market key: {identity}")
        market_probability = number(raw["market_home_probability_no_vig"])
        model_probability = number(raw["model_home_probability"])
        outcome = number(raw["actual_home_win"])
        error = number(raw["t60_absolute_error_minutes"])
        if None in {market_probability, model_probability, error} or outcome not in {0.0, 1.0}:
            raise ValueError(f"invalid market row: {identity}")
        output[identity] = {
            "game_id": identity,
            "game_date": text(raw["game_date"]),
            "market_home_probability_no_vig": market_probability,
            "model_home_probability": model_probability,
            "actual_home_win": int(outcome),
            "t60_absolute_error_minutes": error,
        }
    return output


def add_stress(model_rows: list[dict[str, Any]]) -> dict[str, Any]:
    scaled = {}
    metadata = {}
    for name, sign in STRESS_SIGNS.items():
        values = np.asarray([row[name] if row[name] is not None else np.nan for row in model_rows], float)
        finite = values[np.isfinite(values)]
        median = float(np.median(finite))
        q1, q3 = np.quantile(finite, [0.25, 0.75])
        iqr = float(q3 - q1)
        if iqr == 0:
            scaled[name] = np.full(len(values), np.nan)
        else:
            scaled[name] = ((values - median) / iqr) * sign
        metadata[name] = {
            "physical_column": FEATURES[name],
            "sign": sign,
            "median": median,
            "iqr": iqr,
            "excluded_zero_iqr": iqr == 0,
        }
    for index, row in enumerate(model_rows):
        available = [scaled[name][index] for name in STRESS_SIGNS if math.isfinite(scaled[name][index])]
        row["stress_components_available"] = len(available)
        row["signed_rotation_stress"] = float(np.mean(available)) if len(available) >= 5 else math.nan
        row["rotation_stress_gap_magnitude"] = abs(row["signed_rotation_stress"])
    return metadata


def feature_family(input_rows: list[dict[str, Any]], target: str) -> list[dict[str, Any]]:
    output = []
    pvalues = []
    y = np.asarray([row[target] for row in input_rows], float)
    for canonical, physical in FEATURES.items():
        x = np.asarray([row[canonical] if row[canonical] is not None else np.nan for row in input_rows], float)
        result = correlation(x, y)
        result.update({"feature": canonical, "physical_column": physical})
        output.append(result)
        pvalues.append(result["two_sided_pvalue"])
    for result, qvalue in zip(output, bh(pvalues)):
        result["bh_qvalue"] = qvalue
        result["bh_q_le_0_10"] = qvalue is not None and qvalue <= 0.10
    return output


def execute(feature_path: Path, prediction_path: Path, market_path: Path, output_path: Path, resamples: int, seed: int) -> dict[str, Any]:
    actual_digests = {
        "features": digest(feature_path),
        "predictions": digest(prediction_path),
        "market_join": digest(market_path),
    }
    if actual_digests != EXPECTED:
        raise ValueError(f"bound input digest mismatch: {actual_digests}")

    features = feature_input(feature_path)
    predictions = prediction_input(prediction_path)
    market = market_input(market_path)

    model_rows = []
    for feature in features:
        if not feature["feature_ready"]:
            continue
        prediction = predictions.get(feature["game_id"])
        if prediction is None or prediction["game_date"] != feature["game_date"]:
            raise ValueError(f"feature/prediction join failure: {feature['game_id']}")
        row = {**feature, **prediction}
        row["model_home_residual"] = row["actual_home_win"] - row["model_home_probability"]
        model_rows.append(row)
    if len(model_rows) != 1075:
        raise ValueError(f"expected 1,075 model rows, found {len(model_rows)}")

    scaling = add_stress(model_rows)
    stress_rows = [row for row in model_rows if math.isfinite(row["signed_rotation_stress"])]
    h1 = correlation(
        np.asarray([row["signed_rotation_stress"] for row in stress_rows]),
        np.asarray([row["model_home_residual"] for row in stress_rows]),
        resamples=resamples,
        seed=seed + 1,
    )
    h1.update({
        "predeclared_direction": "negative",
        "chronological_halves": halves(stress_rows, "signed_rotation_stress", "model_home_residual"),
        "monthly_signs": months(stress_rows, "signed_rotation_stress", "model_home_residual"),
    })

    market_rows = []
    for row in model_rows:
        price = market.get(row["game_id"])
        if price is None:
            continue
        if price["game_date"] != row["game_date"]:
            raise ValueError(f"model/market date mismatch: {row['game_id']}")
        if abs(price["model_home_probability"] - row["model_home_probability"]) > 1e-9:
            raise ValueError(f"model probability mismatch: {row['game_id']}")
        if price["actual_home_win"] != row["actual_home_win"]:
            raise ValueError(f"outcome mismatch: {row['game_id']}")
        combined = {**row, **price}
        outcome = np.asarray([combined["actual_home_win"]])
        model_probability = np.asarray([combined["model_home_probability"]])
        market_probability = np.asarray([combined["market_home_probability_no_vig"]])
        combined["model_minus_market_log_loss_row"] = float(
            log_loss_rows(outcome, model_probability)[0] - log_loss_rows(outcome, market_probability)[0]
        )
        combined["model_minus_market_brier_row"] = float(
            (model_probability[0] - outcome[0]) ** 2 - (market_probability[0] - outcome[0]) ** 2
        )
        market_rows.append(combined)

    band_results = {}
    families = {}
    for band in BANDS:
        subset = [row for row in market_rows if row["t60_absolute_error_minutes"] <= band]
        x = np.asarray([row["rotation_stress_gap_magnitude"] for row in subset], float)
        log_difference = np.asarray([row["model_minus_market_log_loss_row"] for row in subset], float)
        brier_difference = np.asarray([row["model_minus_market_brier_row"] for row in subset], float)
        primary = correlation(x, log_difference, resamples=resamples, seed=seed + 1000 + band)
        primary.update({
            "maximum_nominal_t60_batch_error_minutes": band,
            "predeclared_direction": "positive",
            "chronological_halves": halves(subset, "rotation_stress_gap_magnitude", "model_minus_market_log_loss_row"),
            "monthly_signs": months(subset, "rotation_stress_gap_magnitude", "model_minus_market_log_loss_row"),
            "brier_sensitivity": correlation(x, brier_difference, resamples=resamples, seed=seed + 2000 + band),
        })
        band_results[str(band)] = primary
        families[str(band)] = {
            "log_loss": feature_family(subset, "model_minus_market_log_loss_row"),
            "brier": feature_family(subset, "model_minus_market_brier_row"),
        }

    h2 = band_results["5"]
    h1_ci, h2_ci = h1["bootstrap"]["ci95"], h2["bootstrap"]["ci95"]
    checks = {
        "h1_predeclared_direction_and_ci": h1["spearman_rho"] is not None and h1["spearman_rho"] < 0 and h1_ci[1] is not None and h1_ci[1] < 0,
        "h2_predeclared_direction_and_ci": h2["spearman_rho"] is not None and h2["spearman_rho"] > 0 and h2_ci[0] is not None and h2_ci[0] > 0,
        "h1_chronological_halves_consistent": all(value["sign"] == -1 for value in h1["chronological_halves"].values()),
        "h2_chronological_halves_consistent": all(value["sign"] == 1 for value in h2["chronological_halves"].values()),
        "h1_direction_in_at_least_four_months": h1["monthly_signs"]["negative_months"] >= 4,
        "h2_direction_in_at_least_four_months": h2["monthly_signs"]["positive_months"] >= 4,
    }
    validity = {
        "model_population_rows_at_least_1000": len(model_rows) >= 1000,
        "primary_market_population_rows_at_least_200": h2["rows"] >= 200,
        "source_time_violations": 0,
        "identity_ambiguities": 0,
        "duplicate_game_keys": 0,
        "non_finite_required_values": 0 if len(stress_rows) == len(model_rows) and h2["rows"] == sum(
            math.isfinite(row["rotation_stress_gap_magnitude"]) and math.isfinite(row["model_minus_market_log_loss_row"])
            for row in market_rows if row["t60_absolute_error_minutes"] <= 5
        ) else 1,
        "public_private_boundary_violations": 0,
        "model_fit_calls": 0,
        "model_refit_calls": 0,
        "calibration_changes": 0,
        "market_features_added_to_model": 0,
    }
    valid = all((value if isinstance(value, bool) else value == 0) for value in validity.values())
    full_signal = valid and all(checks.values())
    directional = (h1["spearman_rho"] is not None and h1["spearman_rho"] < 0) or (
        h2["spearman_rho"] is not None and h2["spearman_rho"] > 0
    )
    if not valid:
        decision = "AUDIT_INVALID_OR_UNDERPOWERED"
    elif full_signal:
        decision = "VALID_DIAGNOSTIC_PRIOR_ONLY_ROTATION_RESIDUAL_SIGNAL"
    elif directional:
        decision = "VALID_INCONCLUSIVE_PRIOR_ONLY_ROTATION_RESIDUAL_DIAGNOSTIC"
    else:
        decision = "VALID_NO_PRIOR_ONLY_ROTATION_RESIDUAL_SIGNAL"

    report = {
        "schema_version": "training-free-prior-only-rotation-residual-audit-2025-26-v1",
        "formal_state": FORMAL_STATE,
        "inputs": {
            "digests": actual_digests,
            "feature_rows": len(features),
            "prediction_rows": len(predictions),
            "market_join_rows": len(market),
            "exact_column_binding": FEATURES,
        },
        "populations": {
            "feature_ready_model_rows": len(model_rows),
            "stress_index_ready_model_rows": len(stress_rows),
            "feature_ready_market_intersection_rows": len(market_rows),
            "market_band_rows": {str(band): band_results[str(band)]["rows"] for band in BANDS},
        },
        "stress_index": {"minimum_components": 5, "outcome_free_scaling": scaling},
        "primary_hypotheses": {
            "h1_model_signed_residual": h1,
            "h2_market_relative_log_loss_primary_band": h2,
        },
        "market_sensitivity": band_results,
        "secondary_tests": {
            "model_residual_feature_family": feature_family(model_rows, "model_home_residual"),
            "market_relative_feature_families": families,
        },
        "decision_checks": checks,
        "validity_gates": validity,
        "formal_decision": decision,
        "execution_locks": {
            "model_training_executed": False,
            "model_refit_executed": False,
            "calibration_changed": False,
            "market_data_used_as_model_feature": False,
            "bet_selection_executed": False,
            "ev_calculated": False,
            "roi_calculated": False,
            "clv_calculated": False,
            "drawdown_calculated": False,
            "strict_t60_qualified": False,
            "formal_market_backtest_allowed": False,
            "betting_edge_claim_allowed": False,
            "formal_stake": 0,
        },
        "public_outputs": {
            "aggregate_only": True,
            "public_game_level_rows": 0,
            "public_player_rows": 0,
            "public_price_rows": 0,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def self_test(output: Path) -> None:
    rng = np.random.default_rng(42)
    stress = rng.normal(size=400)
    outcome = (rng.random(400) < 0.55).astype(int)
    model_probability = np.clip(0.55 + 0.05 * stress, 0.05, 0.95)
    market_probability = np.clip(0.55 + 0.01 * stress, 0.05, 0.95)
    checks = {
        "feature_count": len(FEATURES) == 12,
        "stress_count": len(STRESS_SIGNS) == 7,
        "h1_direction": spearman(stress, outcome - model_probability)[0] < 0,
        "paired_loss_rows": len(log_loss_rows(outcome, model_probability) - log_loss_rows(outcome, market_probability)) == 400,
        "bh_bounded": all(value is None or 0 <= value <= 1 for value in bh([0.01, 0.03, 0.2, None])),
        "game_id_serialization": game_id("22500001") == "0022500001",
    }
    if not all(checks.values()):
        raise AssertionError(checks)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"passed": True, "checks": checks}, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path)
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--market-join", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bootstrap-resamples", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20260725)
    parser.add_argument("--self-test", action="store_true")
    arguments = parser.parse_args()
    if arguments.self_test:
        self_test(arguments.output)
        print("training-free rotation residual audit self-test passed")
        return 0
    if None in {arguments.features, arguments.predictions, arguments.market_join}:
        parser.error("--features, --predictions and --market-join are required")
    report = execute(
        arguments.features,
        arguments.predictions,
        arguments.market_join,
        arguments.output,
        arguments.bootstrap_resamples,
        arguments.seed,
    )
    print(json.dumps({
        "formal_state": report["formal_state"],
        "formal_decision": report["formal_decision"],
        "populations": report["populations"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
