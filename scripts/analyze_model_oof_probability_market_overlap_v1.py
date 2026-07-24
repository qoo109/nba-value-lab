#!/usr/bin/env python3
"""Analyze the frozen walk-forward OOF probabilities and audit odds-season overlap.

This diagnostic never retrains a model, never commits raw prediction rows or raw
prices, and never performs a market backtest when model and odds seasons do not
overlap. The optional private odds input is used only to identify its season
coverage and event count.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EPSILON = 1e-15
MODEL_FIELD = "predicted_home_win_probability"
ELO_FIELD = "elo_home_win_probability"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def clip_probability(value: Any) -> float:
    return min(1.0 - EPSILON, max(EPSILON, float(value)))


def row_log_loss(actual: int, probability: float) -> float:
    probability = clip_probability(probability)
    return -(
        actual * math.log(probability)
        + (1 - actual) * math.log(1 - probability)
    )


def row_brier(actual: int, probability: float) -> float:
    return (float(probability) - actual) ** 2


def roc_auc_rank(actuals: list[int], scores: list[float]) -> float | None:
    pairs = sorted(zip(scores, actuals), key=lambda item: item[0])
    ranks = [0.0] * len(pairs)
    index = 0
    while index < len(pairs):
        end = index + 1
        while end < len(pairs) and pairs[end][0] == pairs[index][0]:
            end += 1
        average_rank = (index + 1 + end) / 2.0
        for rank_index in range(index, end):
            ranks[rank_index] = average_rank
        index = end
    positives = sum(actuals)
    negatives = len(actuals) - positives
    if positives == 0 or negatives == 0:
        return None
    positive_rank_sum = sum(
        rank for rank, (_, actual) in zip(ranks, pairs) if actual == 1
    )
    return (
        positive_rank_sum - positives * (positives + 1) / 2
    ) / (positives * negatives)


def probability_metrics(
    rows: list[dict[str, str]], probability_field: str
) -> dict[str, Any]:
    actuals = [int(row["actual_home_win"]) for row in rows]
    probabilities = [clip_probability(row[probability_field]) for row in rows]
    predictions = [1 if probability >= 0.5 else 0 for probability in probabilities]
    return {
        "rows": len(rows),
        "log_loss": sum(
            row_log_loss(actual, probability)
            for actual, probability in zip(actuals, probabilities)
        )
        / len(rows),
        "brier_score": sum(
            row_brier(actual, probability)
            for actual, probability in zip(actuals, probabilities)
        )
        / len(rows),
        "accuracy": sum(
            actual == prediction
            for actual, prediction in zip(actuals, predictions)
        )
        / len(rows),
        "roc_auc": roc_auc_rank(actuals, probabilities),
        "mean_probability": sum(probabilities) / len(probabilities),
        "actual_home_win_rate": sum(actuals) / len(actuals),
    }


def reliability_table(
    rows: list[dict[str, str]], probability_field: str, bin_count: int = 10
) -> dict[str, Any]:
    bins: list[dict[str, Any]] = []
    ece = 0.0
    mce = 0.0
    total = len(rows)
    for bin_index in range(bin_count):
        lower = bin_index / bin_count
        upper = (bin_index + 1) / bin_count
        subset = [
            row
            for row in rows
            if lower <= clip_probability(row[probability_field]) < upper
        ]
        if not subset:
            bins.append(
                {
                    "lower": lower,
                    "upper": upper,
                    "rows": 0,
                    "mean_predicted": None,
                    "observed_rate": None,
                    "absolute_gap": None,
                }
            )
            continue
        mean_predicted = sum(
            clip_probability(row[probability_field]) for row in subset
        ) / len(subset)
        observed_rate = sum(int(row["actual_home_win"]) for row in subset) / len(
            subset
        )
        absolute_gap = abs(mean_predicted - observed_rate)
        ece += len(subset) / total * absolute_gap
        mce = max(mce, absolute_gap)
        bins.append(
            {
                "lower": lower,
                "upper": upper,
                "rows": len(subset),
                "mean_predicted": mean_predicted,
                "observed_rate": observed_rate,
                "absolute_gap": absolute_gap,
            }
        )
    return {
        "binning": "equal_width_10",
        "ece": ece,
        "mce": mce,
        "bins": bins,
    }


def confidence_thresholds(
    rows: list[dict[str, str]], probability_field: str
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for threshold in (0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80):
        selected: list[tuple[bool, float]] = []
        for row in rows:
            probability = clip_probability(row[probability_field])
            selected_side_probability = max(probability, 1 - probability)
            if selected_side_probability + 1e-12 < threshold:
                continue
            predicted_home_win = probability >= 0.5
            actual_home_win = bool(int(row["actual_home_win"]))
            selected.append(
                (predicted_home_win == actual_home_win, selected_side_probability)
            )
        accuracy = (
            sum(result for result, _ in selected) / len(selected) if selected else None
        )
        mean_probability = (
            sum(probability for _, probability in selected) / len(selected)
            if selected
            else None
        )
        output.append(
            {
                "minimum_selected_side_probability": threshold,
                "rows": len(selected),
                "coverage": len(selected) / len(rows),
                "accuracy": accuracy,
                "mean_selected_side_probability": mean_probability,
                "accuracy_minus_mean_probability": (
                    accuracy - mean_probability
                    if accuracy is not None and mean_probability is not None
                    else None
                ),
            }
        )
    return output


def home_probability_bands(
    rows: list[dict[str, str]], probability_field: str
) -> list[dict[str, Any]]:
    edges = [0.0, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 1.0000001]
    output: list[dict[str, Any]] = []
    for lower, upper in zip(edges, edges[1:]):
        subset = [
            row
            for row in rows
            if lower <= clip_probability(row[probability_field]) < upper
        ]
        if not subset:
            continue
        output.append(
            {
                "lower": lower,
                "upper": min(upper, 1.0),
                "rows": len(subset),
                "mean_predicted_home_win": sum(
                    clip_probability(row[probability_field]) for row in subset
                )
                / len(subset),
                "actual_home_win_rate": sum(
                    int(row["actual_home_win"]) for row in subset
                )
                / len(subset),
            }
        )
    return output


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def paired_bootstrap(
    rows: list[dict[str, str]], resamples: int = 5000, seed: int = 20260724
) -> dict[str, Any]:
    randomizer = random.Random(seed)
    row_count = len(rows)
    log_loss_differences: list[float] = []
    brier_differences: list[float] = []
    accuracy_differences: list[float] = []
    for _ in range(resamples):
        sample = [rows[randomizer.randrange(row_count)] for _ in range(row_count)]
        actuals = [int(row["actual_home_win"]) for row in sample]
        model_probabilities = [clip_probability(row[MODEL_FIELD]) for row in sample]
        elo_probabilities = [clip_probability(row[ELO_FIELD]) for row in sample]
        log_loss_differences.append(
            sum(
                row_log_loss(actual, model_probability)
                - row_log_loss(actual, elo_probability)
                for actual, model_probability, elo_probability in zip(
                    actuals, model_probabilities, elo_probabilities
                )
            )
            / row_count
        )
        brier_differences.append(
            sum(
                row_brier(actual, model_probability)
                - row_brier(actual, elo_probability)
                for actual, model_probability, elo_probability in zip(
                    actuals, model_probabilities, elo_probabilities
                )
            )
            / row_count
        )
        model_accuracy = sum(
            (probability >= 0.5) == bool(actual)
            for actual, probability in zip(actuals, model_probabilities)
        ) / row_count
        elo_accuracy = sum(
            (probability >= 0.5) == bool(actual)
            for actual, probability in zip(actuals, elo_probabilities)
        ) / row_count
        accuracy_differences.append(model_accuracy - elo_accuracy)

    def summary(values: list[float], better_when_negative: bool) -> dict[str, Any]:
        return {
            "mean": statistics.fmean(values),
            "ci95": [percentile(values, 0.025), percentile(values, 0.975)],
            "probability_model_better": sum(
                value < 0 if better_when_negative else value > 0 for value in values
            )
            / len(values),
        }

    return {
        "resamples": resamples,
        "seed": seed,
        "model_minus_elo_log_loss": summary(log_loss_differences, True),
        "model_minus_elo_brier": summary(brier_differences, True),
        "model_minus_elo_accuracy": summary(accuracy_differences, False),
    }


def infer_odds_scope(rows: list[dict[str, str]]) -> dict[str, Any]:
    seasons: set[str] = set()
    dates: list[str] = []
    regular_events: set[str] = set()
    for row in rows:
        if not row.get("status", "").startswith("MATCHED_"):
            continue
        tipoff = row.get("scheduled_tipoff_utc", "")
        if tipoff:
            parsed = datetime.fromisoformat(tipoff.replace("Z", "+00:00"))
            dates.append(parsed.date().isoformat())
            season_start = parsed.year if parsed.month >= 7 else parsed.year - 1
            seasons.add(f"{season_start}-{str(season_start + 1)[-2:]}")
        event_key = row.get("official_schedule_row_id") or row.get("official_game_id")
        if event_key:
            regular_events.add(event_key)
    return {
        "seasons": sorted(seasons),
        "first_tipoff": min(dates) if dates else None,
        "last_tipoff": max(dates) if dates else None,
        "unique_regular_events": len(regular_events),
        "rows": len(rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--odds-main", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    prediction_rows = read_csv(args.predictions)
    odds_rows = read_csv(args.odds_main)
    prediction_seasons = sorted({row["test_season"] for row in prediction_rows})
    odds_scope = infer_odds_scope(odds_rows)

    model_metrics = probability_metrics(prediction_rows, MODEL_FIELD)
    elo_metrics = probability_metrics(prediction_rows, ELO_FIELD)
    rows_by_season: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in prediction_rows:
        rows_by_season[row["test_season"]].append(row)

    per_season: dict[str, Any] = {}
    for season, rows in sorted(rows_by_season.items()):
        model_season = probability_metrics(rows, MODEL_FIELD)
        elo_season = probability_metrics(rows, ELO_FIELD)
        per_season[season] = {
            "model": model_season,
            "elo": elo_season,
            "model_minus_elo": {
                "log_loss": model_season["log_loss"] - elo_season["log_loss"],
                "brier_score": model_season["brier_score"]
                - elo_season["brier_score"],
                "accuracy": model_season["accuracy"] - elo_season["accuracy"],
            },
        }

    overlap_seasons = sorted(set(prediction_seasons) & set(odds_scope["seasons"]))
    output = {
        "schema_version": "model-oof-probability-and-market-overlap-diagnostic-v1",
        "formal_state": (
            "MODEL_OOF_PROBABILITY_DIAGNOSTIC_VALID_"
            "MARKET_JOIN_BLOCKED_NO_SEASON_OVERLAP"
        ),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "model_artifact_run": 29551715399,
            "model_artifact_id": 8396002523,
            "model_artifact_digest": (
                "sha256:6063adac9851b47d339a93e35935115008b736a16925548d36a8c54a0353b41b"
            ),
            "prediction_rows": len(prediction_rows),
            "prediction_test_seasons": prediction_seasons,
            "odds": odds_scope,
            "raw_predictions_committed": False,
            "raw_odds_committed": False,
        },
        "model_only_oof": {
            "selected_probability_method": "raw_logistic_elo",
            "model": model_metrics,
            "elo_benchmark": elo_metrics,
            "model_minus_elo": {
                "log_loss": model_metrics["log_loss"] - elo_metrics["log_loss"],
                "brier_score": model_metrics["brier_score"]
                - elo_metrics["brier_score"],
                "accuracy": model_metrics["accuracy"] - elo_metrics["accuracy"],
                "roc_auc": model_metrics["roc_auc"] - elo_metrics["roc_auc"],
            },
            "per_season": per_season,
            "reliability": reliability_table(prediction_rows, MODEL_FIELD),
            "confidence_thresholds": confidence_thresholds(
                prediction_rows, MODEL_FIELD
            ),
            "home_probability_bands": home_probability_bands(
                prediction_rows, MODEL_FIELD
            ),
            "paired_game_bootstrap_vs_elo": paired_bootstrap(prediction_rows),
        },
        "market_overlap_gate": {
            "prediction_seasons": prediction_seasons,
            "odds_seasons": odds_scope["seasons"],
            "overlap_seasons": overlap_seasons,
            "market_sensitivity_executed": False,
            "reason": (
                "NO_SEASON_OVERLAP_BETWEEN_2021_22_TO_2023_24_"
                "OOF_PREDICTIONS_AND_2025_26_ODDS"
            ),
            "strict_t60_qualified": False,
        },
        "forward_scoring_readiness_2025_26": {
            "trained_model_artifact_available": True,
            "governed_2024_25_silver_gold_available": False,
            "governed_2025_26_pre_game_gold_available": False,
            "2025_26_final_outcomes_available_in_model_pipeline": False,
            "continuous_elo_state_through_2024_25_available": False,
            "ready_to_score_2025_26": False,
            "blockers": [
                "MISSING_GOVERNED_2024_25_SEASON_STATE",
                "MISSING_GOVERNED_2025_26_PRE_GAME_GOLD_FEATURES",
                "MISSING_2025_26_MODEL_PREDICTION_ROWS",
            ],
        },
        "qualification": {
            "model_probability_quality_analysis_allowed": True,
            "market_probability_analysis_allowed_private_diagnostic": True,
            "model_vs_market_same_game_comparison_allowed": False,
            "market_backtest_allowed": False,
            "clv_allowed": False,
            "roi_allowed": False,
            "betting_edge_claim_allowed": False,
            "formal_stake": 0,
        },
        "decision": (
            "KEEP_RAW_LOGISTIC_ELO_AS_RESEARCH_PROBABILITY_BASELINE_AND_BUILD_"
            "2024_25_TO_2025_26_GOVERNED_FORWARD_FEATURE_CHAIN_BEFORE_ODDS_JOIN"
        ),
        "next_unique_sub_mainline": (
            "BUILD_GOVERNED_2024_25_AND_2025_26_PRE_GAME_FEATURE_CHAIN_"
            "WITHOUT_RETRAINING_THEN_SCORE_2025_26_FORWARD"
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "formal_state": output["formal_state"],
                "prediction_rows": len(prediction_rows),
                "model_accuracy": model_metrics["accuracy"],
                "model_log_loss": model_metrics["log_loss"],
                "model_brier": model_metrics["brier_score"],
                "ece": output["model_only_oof"]["reliability"]["ece"],
                "overlap_seasons": overlap_seasons,
                "formal_stake": 0,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
