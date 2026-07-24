#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from scipy.stats import rankdata, spearmanr

VERSION = "training-free-prior-only-rotation-residual-audit-2025-26-v1"
FORMAL_EXECUTED = "TRAINING_FREE_PRIOR_ONLY_ROTATION_RESIDUAL_AUDIT_2025_26_V1_EXECUTED"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def truth(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def finite_float(value: Any, *, field: str) -> float:
    try:
        number = float(str(value).strip())
    except Exception as exc:
        raise ValueError(f"invalid numeric {field}: {value!r}") from exc
    if not math.isfinite(number):
        raise ValueError(f"non-finite numeric {field}: {value!r}")
    return number


def optional_float(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def exact_unique(
    rows: list[dict[str, str]],
    key: str,
    label: str,
) -> dict[str, dict[str, str]]:
    output: dict[str, dict[str, str]] = {}
    for row in rows:
        value = str(row.get(key) or "").strip()
        if not value:
            raise ValueError(f"{label} missing {key}")
        if value in output:
            raise ValueError(f"duplicate {label} key: {value}")
        output[value] = row
    return output


def binary_log_loss(y: np.ndarray, probability: np.ndarray) -> np.ndarray:
    probability = np.clip(np.asarray(probability, dtype=float), 1e-6, 1 - 1e-6)
    y = np.asarray(y, dtype=float)
    return -(y * np.log(probability) + (1 - y) * np.log(1 - probability))


def pearson(x: np.ndarray, y: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) < 3 or np.std(x) <= 1e-15 or np.std(y) <= 1e-15:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def spearman(x: Iterable[float], y: Iterable[float]) -> dict[str, Any]:
    x_array = np.asarray(list(x), dtype=float)
    y_array = np.asarray(list(y), dtype=float)
    mask = np.isfinite(x_array) & np.isfinite(y_array)
    x_array, y_array = x_array[mask], y_array[mask]
    if (
        len(x_array) < 3
        or np.unique(x_array).size < 2
        or np.unique(y_array).size < 2
    ):
        return {"rows": int(len(x_array)), "rho": None, "p_value": None}
    result = spearmanr(x_array, y_array)
    return {
        "rows": int(len(x_array)),
        "rho": float(result.statistic),
        "p_value": float(result.pvalue),
    }


def bootstrap_spearman(
    x: np.ndarray,
    y: np.ndarray,
    *,
    resamples: int,
    seed: int,
) -> dict[str, Any]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    if len(x) < 3:
        raise ValueError("bootstrap population too small")
    rng = np.random.default_rng(seed)
    values: list[float] = []
    for _ in range(resamples):
        indices = rng.integers(0, len(x), len(x))
        x_sample, y_sample = x[indices], y[indices]
        if np.unique(x_sample).size < 2 or np.unique(y_sample).size < 2:
            continue
        rho = pearson(rankdata(x_sample), rankdata(y_sample))
        if math.isfinite(rho):
            values.append(rho)
    if len(values) < max(50, int(resamples * 0.9)):
        raise ValueError(
            f"too few valid bootstrap resamples: {len(values)} / {resamples}"
        )
    array = np.asarray(values, dtype=float)
    return {
        "requested_resamples": resamples,
        "valid_resamples": int(len(array)),
        "seed": seed,
        "mean": float(array.mean()),
        "ci95": [
            float(np.quantile(array, 0.025)),
            float(np.quantile(array, 0.975)),
        ],
        "probability_negative": float(np.mean(array < 0)),
        "probability_positive": float(np.mean(array > 0)),
    }


def bh_adjust(p_values: list[float | None]) -> list[float | None]:
    valid = [
        (index, float(value))
        for index, value in enumerate(p_values)
        if value is not None and math.isfinite(float(value))
    ]
    output: list[float | None] = [None] * len(p_values)
    if not valid:
        return output
    ordered = sorted(valid, key=lambda item: item[1])
    count = len(ordered)
    adjusted = [0.0] * count
    running = 1.0
    for reverse_index in range(count - 1, -1, -1):
        _, p_value = ordered[reverse_index]
        rank = reverse_index + 1
        running = min(running, p_value * count / rank)
        adjusted[reverse_index] = min(1.0, running)
    for (original_index, _), q_value in zip(ordered, adjusted):
        output[original_index] = float(q_value)
    return output


def quartile_contrast(x: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    if len(x) < 20 or np.unique(x).size < 4:
        return {
            "rows": int(len(x)),
            "bottom_rows": 0,
            "top_rows": 0,
            "top_minus_bottom_mean": None,
        }
    q25, q75 = np.quantile(x, [0.25, 0.75])
    bottom = y[x <= q25]
    top = y[x >= q75]
    return {
        "rows": int(len(x)),
        "q25": float(q25),
        "q75": float(q75),
        "bottom_rows": int(len(bottom)),
        "top_rows": int(len(top)),
        "bottom_mean": float(bottom.mean()) if len(bottom) else None,
        "top_mean": float(top.mean()) if len(top) else None,
        "top_minus_bottom_mean": (
            float(top.mean() - bottom.mean()) if len(bottom) and len(top) else None
        ),
    }


def chronological_halves(
    rows: list[dict[str, Any]],
    x_key: str,
    y_key: str,
) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda row: (row["game_date_et"], row["game_id"]))
    split = len(ordered) // 2
    parts = {"first": ordered[:split], "second": ordered[split:]}
    return {
        name: spearman(
            (row[x_key] for row in part),
            (row[y_key] for row in part),
        )
        for name, part in parts.items()
    }


def monthly_correlations(
    rows: list[dict[str, Any]],
    x_key: str,
    y_key: str,
    minimum_rows: int = 10,
) -> dict[str, Any]:
    months: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        month = row["game_date_et"][:7]
        months.setdefault(month, []).append(row)
    output: dict[str, Any] = {}
    for month in sorted(months):
        part = months[month]
        if len(part) < minimum_rows:
            output[month] = {
                "rows": len(part),
                "rho": None,
                "p_value": None,
                "minimum_rows_met": False,
            }
        else:
            stats = spearman(
                (row[x_key] for row in part),
                (row[y_key] for row in part),
            )
            stats["minimum_rows_met"] = True
            output[month] = stats
    return output


def direction_count(months: dict[str, Any], direction: str) -> int:
    count = 0
    for stats in months.values():
        rho = stats.get("rho")
        if rho is None:
            continue
        if direction == "negative" and rho < 0:
            count += 1
        if direction == "positive" and rho > 0:
            count += 1
    return count


def build_stress(
    model_rows: list[dict[str, Any]],
    *,
    components: list[dict[str, Any]],
    minimum_components: int,
) -> dict[str, Any]:
    scaling: dict[str, Any] = {}
    active: list[dict[str, Any]] = []
    for component in components:
        column = component["physical"]
        values = np.asarray(
            [row[column] for row in model_rows if row[column] is not None],
            dtype=float,
        )
        if not len(values):
            scaling[column] = {
                "rows": 0,
                "median": None,
                "iqr": None,
                "excluded": True,
                "reason": "NO_VALUES",
            }
            continue
        q25, median, q75 = np.quantile(values, [0.25, 0.5, 0.75])
        iqr = float(q75 - q25)
        excluded = iqr <= 1e-15
        scaling[column] = {
            "rows": int(len(values)),
            "q25": float(q25),
            "median": float(median),
            "q75": float(q75),
            "iqr": iqr,
            "sign": int(component["sign"]),
            "excluded": excluded,
            "reason": "ZERO_IQR" if excluded else None,
        }
        if not excluded:
            active.append(component)
    for row in model_rows:
        scaled_values = []
        for component in active:
            column = component["physical"]
            value = row[column]
            if value is None:
                continue
            component_scaling = scaling[column]
            scaled_values.append(
                int(component["sign"])
                * (value - component_scaling["median"])
                / component_scaling["iqr"]
            )
        row["stress_components_available"] = len(scaled_values)
        row["signed_rotation_stress"] = (
            float(np.mean(scaled_values))
            if len(scaled_values) >= minimum_components
            else None
        )
        row["rotation_stress_gap_magnitude"] = (
            abs(row["signed_rotation_stress"])
            if row["signed_rotation_stress"] is not None
            else None
        )
    return {
        "component_scaling": scaling,
        "active_components": len(active),
        "minimum_components_per_game": minimum_components,
        "rows_with_stress_index": sum(
            row["signed_rotation_stress"] is not None for row in model_rows
        ),
    }


def validate_file_digest(path: Path, expected: str, label: str) -> None:
    actual = sha256(path)
    if actual != expected:
        raise ValueError(
            f"{label} SHA mismatch: expected {expected}, got {actual}"
        )


def execute(
    *,
    feature_path: Path,
    prediction_path: Path,
    market_path: Path,
    design_path: Path,
    binding_path: Path,
    output_dir: Path,
    resamples: int | None = None,
) -> dict[str, Any]:
    design = json.loads(design_path.read_text(encoding="utf-8"))
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    if (
        design["formal_state"]
        != "TRAINING_FREE_PRIOR_ONLY_ROTATION_RESIDUAL_AUDIT_2025_26_V1_PREDECLARED"
    ):
        raise ValueError("unsupported residual audit design state")
    if (
        binding["formal_state"]
        != "TRAINING_FREE_PRIOR_ONLY_ROTATION_RESIDUAL_AUDIT_2025_26_V1_COLUMN_BINDING_AMENDMENT_PREDECLARED"
    ):
        raise ValueError("unsupported column binding state")

    inputs = design["bound_private_inputs"]
    validate_file_digest(
        feature_path,
        inputs["rotation_matchup_csv_sha256"],
        "rotation matchup CSV",
    )
    validate_file_digest(
        prediction_path,
        inputs["frozen_prediction_csv_sha256"],
        "frozen predictions CSV",
    )
    validate_file_digest(
        market_path,
        inputs["private_model_market_join_csv_sha256"],
        "private model-market join CSV",
    )

    feature_rows_raw = read_csv(feature_path)
    prediction_rows_raw = read_csv(prediction_path)
    market_rows_raw = read_csv(market_path)
    if len(feature_rows_raw) != inputs["rotation_matchup_rows"]:
        raise ValueError(
            f"expected {inputs['rotation_matchup_rows']} feature rows, "
            f"found {len(feature_rows_raw)}"
        )
    if len(prediction_rows_raw) != 1230:
        raise ValueError(
            f"expected 1230 prediction rows, found {len(prediction_rows_raw)}"
        )

    column_mapping = binding["canonical_to_physical_column_mapping"]
    identity = binding["identity_and_readiness_columns"]
    required_feature_columns = set(column_mapping.values()) | set(identity.values())
    missing_columns = required_feature_columns - set(feature_rows_raw[0])
    if missing_columns:
        raise ValueError(
            f"bound feature columns missing: {sorted(missing_columns)}"
        )

    features_by_game = exact_unique(
        feature_rows_raw,
        identity["game_id"],
        "feature",
    )
    predictions_by_game = exact_unique(
        prediction_rows_raw,
        "game_id",
        "prediction",
    )
    markets_by_game = exact_unique(market_rows_raw, "game_id", "market")

    model_rows: list[dict[str, Any]] = []
    identity_mismatches = 0
    for game_id, feature_row in features_by_game.items():
        if not truth(feature_row[identity["feature_ready_game"]]):
            continue
        prediction_row = predictions_by_game.get(game_id)
        if prediction_row is None:
            continue
        if (
            str(feature_row[identity["game_date_et"]])
            != str(prediction_row["game_date"])
            or str(feature_row[identity["home_team"]])
            != str(prediction_row["home_team_abbr"])
            or str(feature_row[identity["away_team"]])
            != str(prediction_row["away_team_abbr"])
        ):
            identity_mismatches += 1
            continue
        row: dict[str, Any] = {
            "game_id": game_id,
            "game_date_et": str(feature_row[identity["game_date_et"]]),
            "home_team_abbr": str(feature_row[identity["home_team"]]),
            "away_team_abbr": str(feature_row[identity["away_team"]]),
            "model_home_probability": finite_float(
                prediction_row["predicted_home_win_probability"],
                field="model_home_probability",
            ),
            "actual_home_win": int(
                finite_float(
                    prediction_row["actual_home_win"],
                    field="actual_home_win",
                )
            ),
        }
        if row["actual_home_win"] not in {0, 1}:
            raise ValueError(f"invalid binary outcome for {game_id}")
        for physical_column in column_mapping.values():
            row[physical_column] = optional_float(feature_row.get(physical_column))
        row["model_home_residual"] = (
            row["actual_home_win"] - row["model_home_probability"]
        )
        row["model_absolute_error"] = abs(row["model_home_residual"])
        model_rows.append(row)

    expected_model_rows = design["populations"]
    expected_model_rows = expected_model_rows["primary_model_residual_population"]
    expected_model_rows = expected_model_rows["expected_rows"]
    if len(model_rows) != expected_model_rows:
        raise ValueError(
            f"expected {expected_model_rows} exact feature-ready prediction joins, "
            f"found {len(model_rows)}"
        )
    if identity_mismatches:
        raise ValueError(f"identity mismatches: {identity_mismatches}")

    stress = build_stress(
        model_rows,
        components=binding["stress_index_physical_components"],
        minimum_components=design["predeclared_rotation_stress_index"]
        ["minimum_components"],
    )
    model_rows = [
        row for row in model_rows if row["signed_rotation_stress"] is not None
    ]
    model_minimum = design["validity_gates"]
    model_minimum = model_minimum["exact_feature_ready_model_rows_minimum"]
    if len(model_rows) < model_minimum:
        raise ValueError(
            "insufficient model residual rows after stress-index availability"
        )
    model_by_game = {row["game_id"]: row for row in model_rows}

    h1 = spearman(
        (row["signed_rotation_stress"] for row in model_rows),
        (row["model_home_residual"] for row in model_rows),
    )
    actual_resamples = (
        resamples
        or design["uncertainty_and_robustness"]["bootstrap_resamples"]
    )
    seed = design["uncertainty_and_robustness"]["bootstrap_seed"]
    h1["bootstrap"] = bootstrap_spearman(
        np.asarray([row["signed_rotation_stress"] for row in model_rows]),
        np.asarray([row["model_home_residual"] for row in model_rows]),
        resamples=actual_resamples,
        seed=seed,
    )
    h1["chronological_halves"] = chronological_halves(
        model_rows,
        "signed_rotation_stress",
        "model_home_residual",
    )
    h1["monthly"] = monthly_correlations(
        model_rows,
        "signed_rotation_stress",
        "model_home_residual",
    )
    h1["months_with_predeclared_negative_sign"] = direction_count(
        h1["monthly"],
        "negative",
    )

    market_enriched: list[dict[str, Any]] = []
    market_identity_mismatches = 0
    probability_mismatches = 0
    outcome_mismatches = 0
    for game_id, market_row in markets_by_game.items():
        base = model_by_game.get(game_id)
        if base is None:
            continue
        if (
            str(market_row.get("game_date") or "") != base["game_date_et"]
            or str(market_row.get("home_team_abbr") or "")
            != base["home_team_abbr"]
            or str(market_row.get("away_team_abbr") or "")
            != base["away_team_abbr"]
        ):
            market_identity_mismatches += 1
            continue
        market_join_model_probability = finite_float(
            market_row["model_home_probability"],
            field="market_join_model_probability",
        )
        outcome = int(
            finite_float(
                market_row["actual_home_win"],
                field="market_join_actual_home_win",
            )
        )
        if (
            abs(
                market_join_model_probability - base["model_home_probability"]
            )
            > 1e-8
        ):
            probability_mismatches += 1
            continue
        if outcome != base["actual_home_win"]:
            outcome_mismatches += 1
            continue
        market_probability = finite_float(
            market_row["market_home_probability_no_vig"],
            field="market_home_probability_no_vig",
        )
        timing_error = finite_float(
            market_row["t60_absolute_error_minutes"],
            field="t60_absolute_error_minutes",
        )
        y = float(outcome)
        row = dict(base)
        model_log_loss = binary_log_loss(
            np.asarray([y]),
            np.asarray([base["model_home_probability"]]),
        )[0]
        market_log_loss = binary_log_loss(
            np.asarray([y]),
            np.asarray([market_probability]),
        )[0]
        row.update(
            {
                "market_home_probability_no_vig": market_probability,
                "t60_absolute_error_minutes": timing_error,
                "market_home_residual": y - market_probability,
                "market_absolute_error": abs(y - market_probability),
                "model_minus_market_log_loss_row": float(
                    model_log_loss - market_log_loss
                ),
                "model_minus_market_brier_row": float(
                    (base["model_home_probability"] - y) ** 2
                    - (market_probability - y) ** 2
                ),
            }
        )
        market_enriched.append(row)
    if (
        market_identity_mismatches
        or probability_mismatches
        or outcome_mismatches
    ):
        raise ValueError(
            "market join inconsistencies: "
            f"identity={market_identity_mismatches}, "
            f"probability={probability_mismatches}, "
            f"outcome={outcome_mismatches}"
        )

    primary_market = [
        row
        for row in market_enriched
        if row["t60_absolute_error_minutes"] <= 5
    ]
    market_minimum = design["populations"]
    market_minimum = market_minimum["primary_market_residual_population"]
    market_minimum = market_minimum["minimum_rows"]
    if len(primary_market) < market_minimum:
        raise ValueError(
            f"primary market population underpowered: "
            f"{len(primary_market)} < {market_minimum}"
        )

    h2 = spearman(
        (
            row["rotation_stress_gap_magnitude"]
            for row in primary_market
        ),
        (
            row["model_minus_market_log_loss_row"]
            for row in primary_market
        ),
    )
    h2["bootstrap"] = bootstrap_spearman(
        np.asarray(
            [row["rotation_stress_gap_magnitude"] for row in primary_market]
        ),
        np.asarray(
            [row["model_minus_market_log_loss_row"] for row in primary_market]
        ),
        resamples=actual_resamples,
        seed=seed + 1,
    )
    h2["chronological_halves"] = chronological_halves(
        primary_market,
        "rotation_stress_gap_magnitude",
        "model_minus_market_log_loss_row",
    )
    h2["monthly"] = monthly_correlations(
        primary_market,
        "rotation_stress_gap_magnitude",
        "model_minus_market_log_loss_row",
    )
    h2["months_with_predeclared_positive_sign"] = direction_count(
        h2["monthly"],
        "positive",
    )

    feature_model_tests: list[dict[str, Any]] = []
    feature_market_tests: list[dict[str, Any]] = []
    for canonical_name, physical_column in column_mapping.items():
        model_test = spearman(
            (row[physical_column] for row in model_rows),
            (row["model_home_residual"] for row in model_rows),
        )
        model_test.update(
            {
                "canonical_feature": canonical_name,
                "physical_column": physical_column,
                "quartile_contrast": quartile_contrast(
                    np.asarray(
                        [
                            (
                                row[physical_column]
                                if row[physical_column] is not None
                                else np.nan
                            )
                            for row in model_rows
                        ]
                    ),
                    np.asarray(
                        [row["model_home_residual"] for row in model_rows]
                    ),
                ),
            }
        )
        feature_model_tests.append(model_test)

        market_test = spearman(
            (row[physical_column] for row in primary_market),
            (
                row["model_minus_market_log_loss_row"]
                for row in primary_market
            ),
        )
        market_test.update(
            {
                "canonical_feature": canonical_name,
                "physical_column": physical_column,
                "quartile_contrast": quartile_contrast(
                    np.asarray(
                        [
                            (
                                row[physical_column]
                                if row[physical_column] is not None
                                else np.nan
                            )
                            for row in primary_market
                        ]
                    ),
                    np.asarray(
                        [
                            row["model_minus_market_log_loss_row"]
                            for row in primary_market
                        ]
                    ),
                ),
            }
        )
        feature_market_tests.append(market_test)

    for tests in (feature_model_tests, feature_market_tests):
        q_values = bh_adjust([test["p_value"] for test in tests])
        for test, q_value in zip(tests, q_values):
            test["bh_q_value"] = q_value
            test["bh_q_le_0_10"] = bool(
                q_value is not None and q_value <= 0.10
            )

    sensitivity_results: dict[str, Any] = {}
    sensitivity_populations = design["populations"]
    sensitivity_populations = sensitivity_populations[
        "market_sensitivity_populations"
    ]
    for item in sensitivity_populations:
        band = int(item["maximum_nominal_t60_batch_error_minutes"])
        part = [
            row
            for row in market_enriched
            if row["t60_absolute_error_minutes"] <= band
        ]
        if len(part) < int(item["minimum_rows"]):
            raise ValueError(
                f"market sensitivity band {band} underpowered: {len(part)}"
            )
        sensitivity_results[str(band)] = {
            "rows": len(part),
            "stress_gap_vs_model_minus_market_log_loss": spearman(
                (
                    row["rotation_stress_gap_magnitude"]
                    for row in part
                ),
                (
                    row["model_minus_market_log_loss_row"]
                    for row in part
                ),
            ),
            "stress_gap_vs_model_minus_market_brier": spearman(
                (
                    row["rotation_stress_gap_magnitude"]
                    for row in part
                ),
                (
                    row["model_minus_market_brier_row"]
                    for row in part
                ),
            ),
        }

    h1_ci = h1["bootstrap"]["ci95"]
    h2_ci = h2["bootstrap"]["ci95"]
    h1_halves_ok = all(
        value.get("rho") is not None and value["rho"] < 0
        for value in h1["chronological_halves"].values()
    )
    h2_halves_ok = all(
        value.get("rho") is not None and value["rho"] > 0
        for value in h2["chronological_halves"].values()
    )
    primary_signal = (
        h1["rho"] is not None
        and h1["rho"] < 0
        and h1_ci[1] < 0
        and h2["rho"] is not None
        and h2["rho"] > 0
        and h2_ci[0] > 0
        and h1_halves_ok
        and h2_halves_ok
        and h1["months_with_predeclared_negative_sign"] >= 4
        and h2["months_with_predeclared_positive_sign"] >= 4
    )
    both_intervals_include_zero = (
        h1_ci[0] <= 0 <= h1_ci[1]
        and h2_ci[0] <= 0 <= h2_ci[1]
    )
    if primary_signal:
        formal_decision = design["decision_policy"]["diagnostic_signal"]
    elif both_intervals_include_zero:
        formal_decision = design["decision_policy"]["no_signal"]
    else:
        formal_decision = design["decision_policy"]["inconclusive"]

    report = {
        "schema_version": VERSION,
        "formal_state": FORMAL_EXECUTED,
        "generated_at_utc": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "input_digests": {
            "rotation_matchup_csv": sha256(feature_path),
            "frozen_prediction_csv": sha256(prediction_path),
            "private_model_market_join_csv": sha256(market_path),
            "design_json": sha256(design_path),
            "column_binding_json": sha256(binding_path),
        },
        "population": {
            "feature_rows": len(feature_rows_raw),
            "prediction_rows": len(prediction_rows_raw),
            "private_market_join_rows": len(market_rows_raw),
            "exact_feature_ready_model_rows": len(model_rows),
            "exact_feature_ready_market_rows_all_timing": len(market_enriched),
            "primary_market_rows_t60_batch_error_le_5": len(primary_market),
            "independent_game_keys": True,
            "identity_mismatches": 0,
            "duplicate_game_keys": 0,
        },
        "stress_index": stress,
        "primary_hypotheses": {
            "h1_signed_rotation_stress_vs_model_home_residual": h1,
            "h2_stress_gap_vs_model_minus_market_log_loss": h2,
        },
        "secondary": {
            "individual_features_vs_model_home_residual": feature_model_tests,
            "individual_features_vs_model_minus_market_log_loss": (
                feature_market_tests
            ),
            "primary_market_stress_gap_vs_model_minus_market_brier": (
                spearman(
                    (
                        row["rotation_stress_gap_magnitude"]
                        for row in primary_market
                    ),
                    (
                        row["model_minus_market_brier_row"]
                        for row in primary_market
                    ),
                )
            ),
            "market_timing_sensitivity": sensitivity_results,
            "multiple_testing": (
                "Benjamini-Hochberg q <= 0.10 separately by 12-feature family"
            ),
        },
        "decision": {
            "formal_decision": formal_decision,
            "diagnostic_signal_requirements_all_passed": primary_signal,
            "h1_predeclared_direction": "negative",
            "h2_predeclared_direction": "positive",
            "h1_chronological_halves_sign_consistent": h1_halves_ok,
            "h2_chronological_halves_sign_consistent": h2_halves_ok,
            "h1_months_in_direction": h1[
                "months_with_predeclared_negative_sign"
            ],
            "h2_months_in_direction": h2[
                "months_with_predeclared_positive_sign"
            ],
        },
        "execution_boundaries": {
            "model_fit_calls": 0,
            "model_refit_calls": 0,
            "model_retraining_executed": False,
            "calibration_changes": 0,
            "market_features_added_to_model": 0,
            "feature_selection_executed": False,
            "model_promotion_authorized": False,
            "strict_t60_qualified": False,
            "formal_market_backtest_allowed": False,
            "ev_calculated": False,
            "roi_calculated": False,
            "clv_calculated": False,
            "drawdown_calculated": False,
            "betting_edge_claim_allowed": False,
            "formal_stake": 0,
        },
        "public_output": {
            "aggregate_only": True,
            "public_game_level_rows": 0,
            "public_player_rows": 0,
            "public_price_rows": 0,
            "raw_private_artifacts_committed": 0,
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / (
        "training-free-prior-only-rotation-residual-audit-2025-26-report-v1.json"
    )
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "formal_state": report["formal_state"],
                "formal_decision": formal_decision,
                "model_rows": len(model_rows),
                "primary_market_rows": len(primary_market),
                "h1_rho": h1["rho"],
                "h2_rho": h2["rho"],
                "output": str(report_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return report


def self_test(output_dir: Path) -> dict[str, Any]:
    # The self-test exercises statistical mechanics only. It does not inspect
    # any bound private outcome, feature, prediction, price or joined row.
    rng = np.random.default_rng(20260725)
    rows = 320
    stress = rng.normal(size=rows)
    model_residual = -0.35 * stress + rng.normal(scale=0.7, size=rows)
    market_relative = 0.30 * np.abs(stress) + rng.normal(
        scale=0.7,
        size=rows,
    )
    h1 = spearman(stress, model_residual)
    h2 = spearman(np.abs(stress), market_relative)
    h1_bootstrap = bootstrap_spearman(
        stress,
        model_residual,
        resamples=200,
        seed=20260725,
    )
    h2_bootstrap = bootstrap_spearman(
        np.abs(stress),
        market_relative,
        resamples=200,
        seed=20260726,
    )
    p_values = [0.001, 0.01, 0.2, None]
    q_values = bh_adjust(p_values)
    checks = {
        "h1_negative": h1["rho"] is not None and h1["rho"] < 0,
        "h2_positive": h2["rho"] is not None and h2["rho"] > 0,
        "h1_ci_negative": h1_bootstrap["ci95"][1] < 0,
        "h2_ci_positive": h2_bootstrap["ci95"][0] > 0,
        "bh_ordered": (
            q_values[0] is not None
            and q_values[1] is not None
            and q_values[0] <= q_values[1]
        ),
        "none_preserved": q_values[3] is None,
        "no_model_fit_api": True,
    }
    if not all(checks.values()):
        raise AssertionError(checks)
    output_dir.mkdir(parents=True, exist_ok=True)
    result = {
        "schema_version": 1,
        "formal_state": (
            "TRAINING_FREE_PRIOR_ONLY_ROTATION_RESIDUAL_AUDIT_"
            "EXECUTOR_SELF_TEST_PASS"
        ),
        "checks": checks,
        "h1": h1,
        "h2": h2,
        "bootstrap_resamples": 200,
        "real_private_residual_audit_executed": False,
        "model_training_authorized": False,
        "formal_market_backtest_allowed": False,
        "formal_stake": 0,
    }
    (output_dir / "self-test.json").write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", type=Path)
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--market-join", type=Path)
    parser.add_argument(
        "--design",
        type=Path,
        default=Path(
            "data/research/"
            "training-free-prior-only-rotation-residual-audit-2025-26-v1.json"
        ),
    )
    parser.add_argument(
        "--column-binding",
        type=Path,
        default=Path(
            "data/research/"
            "training-free-prior-only-rotation-residual-audit-2025-26-v1-"
            "column-binding-amendment.json"
        ),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--bootstrap-resamples", type=int)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        return 0
    if (
        args.features is None
        or args.predictions is None
        or args.market_join is None
    ):
        parser.error(
            "--features, --predictions and --market-join are required "
            "outside --self-test"
        )
    execute(
        feature_path=args.features,
        prediction_path=args.predictions,
        market_path=args.market_join,
        design_path=args.design,
        binding_path=args.column_binding,
        output_dir=args.output_dir,
        resamples=args.bootstrap_resamples,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
