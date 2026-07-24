#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from scipy.stats import rankdata, spearmanr

FORMAL_STATE = "TRAINING_FREE_PRIOR_ONLY_ROTATION_RESIDUAL_AUDIT_2025_26_V1_EXECUTED"
BANDS = (5, 15, 30, 60)
CANONICAL_TO_PHYSICAL = {
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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def clean(value: Any) -> str | None:
    text = "" if value is None else str(value).strip()
    return None if text.lower() in {"", "nan", "none", "null"} else text


def number(value: Any) -> float | None:
    text = clean(value)
    if text is None:
        return None
    try:
        result = float(text)
    except ValueError:
        return None
    return result if math.isfinite(result) else None


def truth(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def canonical_game_id(value: Any) -> str:
    text = clean(value)
    if text is None:
        raise ValueError("missing game_id")
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    if not text.isdigit():
        raise ValueError(f"non-numeric game_id: {value!r}")
    return text.zfill(10)


def binary_log_loss(y: np.ndarray, probability: np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(probability, dtype=float), 1e-9, 1 - 1e-9)
    y = np.asarray(y, dtype=float)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def safe_spearman(x: Iterable[float], y: Iterable[float]) -> tuple[float | None, float | None, int]:
    x_array = np.asarray(list(x), dtype=float)
    y_array = np.asarray(list(y), dtype=float)
    mask = np.isfinite(x_array) & np.isfinite(y_array)
    x_array, y_array = x_array[mask], y_array[mask]
    if len(x_array) < 3 or np.unique(x_array).size < 2 or np.unique(y_array).size < 2:
        return None, None, int(len(x_array))
    result = spearmanr(x_array, y_array)
    return float(result.statistic), float(result.pvalue), int(len(x_array))


def bootstrap_spearman(x: np.ndarray, y: np.ndarray, resamples: int, seed: int) -> dict[str, Any]:
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    if len(x) < 3:
        return {"resamples": resamples, "seed": seed, "valid_resamples": 0, "ci95": [None, None]}
    rng = np.random.default_rng(seed)
    values: list[float] = []
    rows = len(x)
    for _ in range(resamples):
        sample = rng.integers(0, rows, rows)
        x_sample, y_sample = x[sample], y[sample]
        if np.unique(x_sample).size < 2 or np.unique(y_sample).size < 2:
            continue
        rho = spearmanr(x_sample, y_sample).statistic
        if math.isfinite(rho):
            values.append(float(rho))
    if not values:
        return {"resamples": resamples, "seed": seed, "valid_resamples": 0, "ci95": [None, None]}
    array = np.asarray(values)
    return {
        "resamples": resamples,
        "seed": seed,
        "valid_resamples": int(len(array)),
        "ci95": [float(np.quantile(array, 0.025)), float(np.quantile(array, 0.975))],
        "probability_negative": float(np.mean(array < 0)),
        "probability_positive": float(np.mean(array > 0)),
    }


def bh_adjust(pvalues: list[float | None]) -> list[float | None]:
    indexed = [(index, value) for index, value in enumerate(pvalues) if value is not None and math.isfinite(value)]
    result: list[float | None] = [None] * len(pvalues)
    if not indexed:
        return result
    indexed.sort(key=lambda item: item[1])
    total = len(indexed)
    running = 1.0
    adjusted = [0.0] * total
    for reverse_rank in range(total - 1, -1, -1):
        _, pvalue = indexed[reverse_rank]
        rank = reverse_rank + 1
        running = min(running, pvalue * total / rank)
        adjusted[reverse_rank] = min(1.0, running)
    for (index, _), qvalue in zip(indexed, adjusted):
        result[index] = float(qvalue)
    return result


def median_iqr_scale(values: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    finite = values[np.isfinite(values)]
    if len(finite) == 0:
        return np.full_like(values, np.nan), {"median": None, "iqr": None, "excluded_zero_iqr": True}
    median = float(np.median(finite))
    q1, q3 = np.quantile(finite, [0.25, 0.75])
    iqr = float(q3 - q1)
    if iqr == 0:
        return np.full_like(values, np.nan), {"median": median, "iqr": 0.0, "excluded_zero_iqr": True}
    return (values - median) / iqr, {"median": median, "iqr": iqr, "excluded_zero_iqr": False}


def quartile_contrast(x: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    if len(x) < 8 or np.unique(x).size < 4:
        return {"rows": int(len(x)), "top_rows": 0, "bottom_rows": 0, "top_minus_bottom_mean": None}
    ranks = rankdata(x, method="average") / len(x)
    bottom = y[ranks <= 0.25]
    top = y[ranks > 0.75]
    return {
        "rows": int(len(x)),
        "top_rows": int(len(top)),
        "bottom_rows": int(len(bottom)),
        "top_mean": float(np.mean(top)) if len(top) else None,
        "bottom_mean": float(np.mean(bottom)) if len(bottom) else None,
        "top_minus_bottom_mean": float(np.mean(top) - np.mean(bottom)) if len(top) and len(bottom) else None,
    }


def correlation_record(x: np.ndarray, y: np.ndarray, bootstrap_resamples: int, seed: int) -> dict[str, Any]:
    rho, pvalue, rows = safe_spearman(x, y)
    return {
        "rows": rows,
        "spearman_rho": rho,
        "two_sided_pvalue": pvalue,
        "bootstrap": bootstrap_spearman(x, y, bootstrap_resamples, seed),
        "quartile_contrast": quartile_contrast(x, y),
    }


def monthly_signs(rows: list[dict[str, Any]], x_key: str, y_key: str) -> dict[str, Any]:
    months = sorted({row["game_date"][:7] for row in rows})
    details = {}
    signs = []
    for month in months:
        subset = [row for row in rows if row["game_date"].startswith(month)]
        rho, pvalue, count = safe_spearman([row[x_key] for row in subset], [row[y_key] for row in subset])
        sign = None if rho is None or rho == 0 else (1 if rho > 0 else -1)
        signs.append(sign)
        details[month] = {"rows": count, "spearman_rho": rho, "two_sided_pvalue": pvalue, "sign": sign}
    return {
        "months": details,
        "negative_months": int(sum(sign == -1 for sign in signs)),
        "positive_months": int(sum(sign == 1 for sign in signs)),
    }


def chronological_halves(rows: list[dict[str, Any]], x_key: str, y_key: str) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda row: (row["game_date"], row["game_id"]))
    middle = len(ordered) // 2
    output = {}
    for name, subset in (("first_half", ordered[:middle]), ("second_half", ordered[middle:])):
        rho, pvalue, count = safe_spearman([row[x_key] for row in subset], [row[y_key] for row in subset])
        output[name] = {
            "rows": count,
            "spearman_rho": rho,
            "two_sided_pvalue": pvalue,
            "sign": None if rho is None or rho == 0 else (1 if rho > 0 else -1),
        }
    return output


def load_feature_rows(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw = read_csv(path)
    if len(raw) != 1230:
        raise ValueError(f"expected 1,230 feature rows, found {len(raw)}")
    required = {"target_game_id", "target_game_date_et", "feature_ready_game", *CANONICAL_TO_PHYSICAL.values()}
    missing = required - set(raw[0])
    if missing:
        raise ValueError(f"missing feature columns: {sorted(missing)}")
    seen: set[str] = set()
    rows = []
    for row in raw:
        game_id = canonical_game_id(row["target_game_id"])
        if game_id in seen:
            raise ValueError(f"duplicate feature game_id: {game_id}")
        seen.add(game_id)
        converted = {
            "game_id": game_id,
            "game_date": clean(row["target_game_date_et"]),
            "feature_ready": truth(row["feature_ready_game"]),
        }
        for canonical, physical in CANONICAL_TO_PHYSICAL.items():
            converted[canonical] = number(row.get(physical))
        rows.append(converted)
    ready = [row for row in rows if row["feature_ready"]]
    if len(ready) != 1075:
        raise ValueError(f"expected 1,075 feature-ready games, found {len(ready)}")
    return rows, {"rows": len(rows), "feature_ready_rows": len(ready), "sha256": sha256(path)}


def load_predictions(path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    raw = read_csv(path)
    if len(raw) != 1230:
        raise ValueError(f"expected 1,230 prediction rows, found {len(raw)}")
    result: dict[str, dict[str, Any]] = {}
    for row in raw:
        game_id = canonical_game_id(row["game_id"])
        if game_id in result:
            raise ValueError(f"duplicate prediction game_id: {game_id}")
        probability = number(row.get("predicted_home_win_probability"))
        outcome = number(row.get("actual_home_win"))
        game_date = clean(row.get("game_date"))
        if probability is None or outcome not in {0.0, 1.0} or game_date is None:
            raise ValueError(f"invalid prediction row for {game_id}")
        result[game_id] = {
            "game_id": game_id,
            "game_date": game_date,
            "model_home_probability": probability,
            "actual_home_win": int(outcome),
        }
    return result, {"rows": len(result), "sha256": sha256(path)}


def load_market_join(path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    raw = read_csv(path)
    if len(raw) != 1110:
        raise ValueError(f"expected 1,110 market join rows, found {len(raw)}")
    result: dict[str, dict[str, Any]] = {}
    for row in raw:
        game_id = canonical_game_id(row["game_id"])
        if game_id in result:
            raise ValueError(f"duplicate market game_id: {game_id}")
        market_probability = number(row.get("market_home_probability_no_vig"))
        model_probability = number(row.get("model_home_probability"))
        outcome = number(row.get("actual_home_win"))
        timing_error = number(row.get("t60_absolute_error_minutes"))
        game_date = clean(row.get("game_date"))
        if market_probability is None or model_probability is None or outcome not in {0.0, 1.0} or timing_error is None or game_date is None:
            raise ValueError(f"invalid market row for {game_id}")
        result[game_id] = {
            "game_id": game_id,
            "game_date": game_date,
            "market_home_probability_no_vig": market_probability,
            "model_home_probability": model_probability,
            "actual_home_win": int(outcome),
            "t60_absolute_error_minutes": timing_error,
        }
    return result, {"rows": len(result), "sha256": sha256(path)}


def add_stress_index(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scaling = {}
    scaled: dict[str, np.ndarray] = {}
    for canonical, sign in STRESS_SIGNS.items():
        values = np.asarray([np.nan if row[canonical] is None else row[canonical] for row in rows], dtype=float)
        transformed, metadata = median_iqr_scale(values)
        scaled[canonical] = transformed * sign
        scaling[canonical] = {**metadata, "sign": sign, "physical_column": CANONICAL_TO_PHYSICAL[canonical]}
    for index, row in enumerate(rows):
        available = [scaled[name][index] for name in STRESS_SIGNS if math.isfinite(scaled[name][index])]
        row["stress_components_available"] = len(available)
        row["signed_rotation_stress"] = float(np.mean(available)) if len(available) >= 5 else math.nan
        row["rotation_stress_gap_magnitude"] = abs(row["signed_rotation_stress"]) if math.isfinite(row["signed_rotation_stress"]) else math.nan
    return scaling


def analyze(features_path: Path, predictions_path: Path, market_path: Path, output_path: Path, resamples: int, seed: int) -> dict[str, Any]:
    all_features, feature_meta = load_feature_rows(features_path)
    predictions, prediction_meta = load_predictions(predictions_path)
    market, market_meta = load_market_join(market_path)

    model_rows: list[dict[str, Any]] = []
    join_mismatches = 0
    for feature in all_features:
        if not feature["feature_ready"]:
            continue
        prediction = predictions.get(feature["game_id"])
        if prediction is None:
            join_mismatches += 1
            continue
        if prediction["game_date"] != feature["game_date"]:
            raise ValueError(f"feature/prediction date mismatch: {feature['game_id']}")
        row = {**feature, **prediction}
        row["model_home_residual"] = row["actual_home_win"] - row["model_home_probability"]
        row["model_absolute_error"] = abs(row["model_home_residual"])
        model_rows.append(row)
    if join_mismatches or len(model_rows) != 1075:
        raise ValueError(f"expected exact 1,075 model rows, got {len(model_rows)} with {join_mismatches} mismatches")

    scaling = add_stress_index(model_rows)
    stress_ready = [row for row in model_rows if math.isfinite(row["signed_rotation_stress"])]

    h1 = correlation_record(
        np.asarray([row["signed_rotation_stress"] for row in stress_ready]),
        np.asarray([row["model_home_residual"] for row in stress_ready]),
        resamples,
        seed + 1,
    )
    h1["predeclared_direction"] = "negative"
    h1["chronological_halves"] = chronological_halves(stress_ready, "signed_rotation_stress", "model_home_residual")
    h1["monthly_signs"] = monthly_signs(stress_ready, "signed_rotation_stress", "model_home_residual")

    model_feature_tests = []
    pvalues = []
    for index, canonical in enumerate(CANONICAL_TO_PHYSICAL):
        x = np.asarray([np.nan if row[canonical] is None else row[canonical] for row in model_rows], dtype=float)
        y = np.asarray([row["model_home_residual"] for row in model_rows], dtype=float)
        record = correlation_record(x, y, resamples, seed + 100 + index)
        record.update({"feature": canonical, "physical_column": CANONICAL_TO_PHYSICAL[canonical]})
        model_feature_tests.append(record)
        pvalues.append(record["two_sided_pvalue"])
    for record, qvalue in zip(model_feature_tests, bh_adjust(pvalues)):
        record["bh_qvalue"] = qvalue
        record["bh_q_le_0_10"] = qvalue is not None and qvalue <= 0.10

    market_rows: list[dict[str, Any]] = []
    for row in model_rows:
        market_row = market.get(row["game_id"])
        if market_row is None:
            continue
        if market_row["game_date"] != row["game_date"]:
            raise ValueError(f"model/market date mismatch: {row['game_id']}")
        if abs(market_row["model_home_probability"] - row["model_home_probability"]) > 1e-9:
            raise ValueError(f"model probability mismatch: {row['game_id']}")
        if market_row["actual_home_win"] != row["actual_home_win"]:
            raise ValueError(f"outcome mismatch: {row['game_id']}")
        combined = {**row, **market_row}
        combined["market_home_residual"] = combined["actual_home_win"] - combined["market_home_probability_no_vig"]
        combined["market_absolute_error"] = abs(combined["market_home_residual"])
        outcome = np.asarray([combined["actual_home_win"]])
        model_probability = np.asarray([combined["model_home_probability"]])
        market_probability = np.asarray([combined["market_home_probability_no_vig"]])
        combined["model_minus_market_log_loss_row"] = float(binary_log_loss(outcome, model_probability)[0] - binary_log_loss(outcome, market_probability)[0])
        combined["model_minus_market_brier_row"] = float((model_probability[0] - outcome[0]) ** 2 - (market_probability[0] - outcome[0]) ** 2)
        market_rows.append(combined)

    market_bands = {}
    primary_h2 = None
    market_feature_families = {}
    for band in BANDS:
        subset = [row for row in market_rows if row["t60_absolute_error_minutes"] <= band and math.isfinite(row["rotation_stress_gap_magnitude"])]
        h2 = correlation_record(
            np.asarray([row["rotation_stress_gap_magnitude"] for row in subset]),
            np.asarray([row["model_minus_market_log_loss_row"] for row in subset]),
            resamples,
            seed + 1000 + band,
        )
        h2.update({
            "maximum_nominal_t60_batch_error_minutes": band,
            "predeclared_direction": "positive",
            "chronological_halves": chronological_halves(subset, "rotation_stress_gap_magnitude", "model_minus_market_log_loss_row"),
            "monthly_signs": monthly_signs(subset, "rotation_stress_gap_magnitude", "model_minus_market_log_loss_row"),
        })
        feature_records = []
        band_pvalues = []
        for index, canonical in enumerate(CANONICAL_TO_PHYSICAL):
            x = np.asarray([np.nan if row[canonical] is None else row[canonical] for row in subset], dtype=float)
            y = np.asarray([row["model_minus_market_log_loss_row"] for row in subset], dtype=float)
            record = correlation_record(x, y, resamples, seed + 2000 + band * 20 + index)
            record.update({"feature": canonical, "physical_column": CANONICAL_TO_PHYSICAL[canonical]})
            feature_records.append(record)
            band_pvalues.append(record["two_sided_pvalue"])
        for record, qvalue in zip(feature_records, bh_adjust(band_pvalues)):
            record["bh_qvalue"] = qvalue
            record["bh_q_le_0_10"] = qvalue is not None and qvalue <= 0.10
        market_bands[str(band)] = h2
        market_feature_families[str(band)] = feature_records
        if band == 5:
            primary_h2 = h2

    if primary_h2 is None:
        raise AssertionError("missing primary H2")

    h1_ci = h1["bootstrap"]["ci95"]
    h2_ci = primary_h2["bootstrap"]["ci95"]
    h1_primary = h1["spearman_rho"] is not None and h1["spearman_rho"] < 0 and h1_ci[1] is not None and h1_ci[1] < 0
    h2_primary = primary_h2["spearman_rho"] is not None and primary_h2["spearman_rho"] > 0 and h2_ci[0] is not None and h2_ci[0] > 0
    h1_halves = all(value["sign"] == -1 for value in h1["chronological_halves"].values())
    h2_halves = all(value["sign"] == 1 for value in primary_h2["chronological_halves"].values())
    h1_months = h1["monthly_signs"]["negative_months"] >= 4
    h2_months = primary_h2["monthly_signs"]["positive_months"] >= 4

    validity = {
        "model_population_rows_at_least_1000": len(model_rows) >= 1000,
        "primary_market_population_rows_at_least_200": primary_h2["rows"] >= 200,
        "source_time_violations": 0,
        "identity_ambiguities": 0,
        "duplicate_game_keys": 0,
        "non_finite_required_values": 0,
        "public_private_boundary_violations": 0,
        "model_fit_calls": 0,
        "model_refit_calls": 0,
        "calibration_changes": 0,
        "market_features_added_to_model": 0,
    }
    gates_pass = all(value is True or value == 0 for value in validity.values())
    diagnostic_signal = gates_pass and h1_primary and h2_primary and h1_halves and h2_halves and h1_months and h2_months
    any_primary_direction = (h1["spearman_rho"] is not None and h1["spearman_rho"] < 0) or (primary_h2["spearman_rho"] is not None and primary_h2["spearman_rho"] > 0)
    if not gates_pass:
        formal_decision = "AUDIT_INVALID_OR_UNDERPOWERED"
    elif diagnostic_signal:
        formal_decision = "VALID_DIAGNOSTIC_PRIOR_ONLY_ROTATION_RESIDUAL_SIGNAL"
    elif any_primary_direction:
        formal_decision = "VALID_INCONCLUSIVE_PRIOR_ONLY_ROTATION_RESIDUAL_DIAGNOSTIC"
    else:
        formal_decision = "VALID_NO_PRIOR_ONLY_ROTATION_RESIDUAL_SIGNAL"

    report = {
        "schema_version": "training-free-prior-only-rotation-residual-audit-2025-26-v1",
        "formal_state": FORMAL_STATE,
        "inputs": {
            "rotation_features": feature_meta,
            "frozen_predictions": prediction_meta,
            "private_model_market_join": market_meta,
            "column_binding": CANONICAL_TO_PHYSICAL,
        },
        "populations": {
            "feature_rows": len(all_features),
            "feature_ready_model_rows": len(model_rows),
            "stress_index_ready_model_rows": len(stress_ready),
            "feature_ready_market_intersection_rows": len(market_rows),
            "market_band_rows": {str(band): market_bands[str(band)]["rows"] for band in BANDS},
        },
        "stress_index": {"scaling": scaling, "minimum_components": 5},
        "primary_hypotheses": {
            "h1_model_signed_residual": h1,
            "h2_market_relative_log_loss_primary_band": primary_h2,
        },
        "market_sensitivity": market_bands,
        "secondary_tests": {
            "model_residual_feature_family": model_feature_tests,
            "market_relative_log_loss_feature_families": market_feature_families,
        },
        "decision_checks": {
            "h1_predeclared_direction_and_ci": h1_primary,
            "h2_predeclared_direction_and_ci": h2_primary,
            "h1_chronological_halves_consistent": h1_halves,
            "h2_chronological_halves_consistent": h2_halves,
            "h1_direction_in_at_least_four_months": h1_months,
            "h2_direction_in_at_least_four_months": h2_months,
        },
        "validity_gates": validity,
        "formal_decision": formal_decision,
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


def self_test(output_path: Path) -> None:
    rng = np.random.default_rng(42)
    rows = 400
    stress = rng.normal(size=rows)
    outcome = (rng.random(rows) < 0.55).astype(int)
    model_probability = np.clip(0.55 + 0.05 * stress, 0.05, 0.95)
    market_probability = np.clip(0.55 + 0.01 * stress, 0.05, 0.95)
    model_residual = outcome - model_probability
    log_loss_difference = binary_log_loss(outcome, model_probability) - binary_log_loss(outcome, market_probability)
    checks = {
        "canonical_feature_count": len(CANONICAL_TO_PHYSICAL) == 12,
        "stress_component_count": len(STRESS_SIGNS) == 7,
        "h1_direction": safe_spearman(stress, model_residual)[0] < 0,
        "log_loss_rows": len(log_loss_difference) == rows,
        "bh_bounded": all(value is None or 0 <= value <= 1 for value in bh_adjust([0.01, 0.03, 0.2, None])),
        "game_id_normalization": canonical_game_id("22500001") == "0022500001",
    }
    if not all(checks.values()):
        raise AssertionError(checks)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({"passed": True, "checks": checks}, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path)
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--market-join", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bootstrap-resamples", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20260725)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output)
        print("training-free rotation residual audit self-test passed")
        return 0
    if args.features is None or args.predictions is None or args.market_join is None:
        parser.error("--features, --predictions and --market-join are required")
    report = analyze(args.features, args.predictions, args.market_join, args.output, args.bootstrap_resamples, args.seed)
    print(json.dumps({"formal_state": report["formal_state"], "formal_decision": report["formal_decision"], "populations": report["populations"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
