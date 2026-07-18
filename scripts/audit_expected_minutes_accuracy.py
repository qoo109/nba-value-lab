#!/usr/bin/env python3
"""Audit prior-only Expected Minutes against label-only target-game minutes.

Primary accuracy measures role minutes conditional on actual appearance. Explicit DNP rows are
excluded from the primary estimand and evaluated separately through status-adjusted realized minutes
and play-probability diagnostics. Missing boxscore rows and missing predictions remain missing.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

VERSION = "expected-minutes-accuracy-audit-v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def as_float(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    number = float(text)
    return number if math.isfinite(number) else None


def as_int(value: Any, default: int = 0) -> int:
    number = as_float(value)
    return default if number is None else int(number)


def metrics(pairs: list[tuple[float, float]]) -> dict[str, Any]:
    if not pairs:
        return {"n": 0, "mae": None, "rmse": None, "median_absolute_error": None, "bias": None}
    errors = [prediction - actual for prediction, actual in pairs]
    absolute = [abs(value) for value in errors]
    return {
        "n": len(pairs),
        "mae": statistics.fmean(absolute),
        "rmse": math.sqrt(statistics.fmean([value * value for value in errors])),
        "median_absolute_error": statistics.median(absolute),
        "bias": statistics.fmean(errors),
    }


def rounded(payload: dict[str, Any]) -> dict[str, Any]:
    output = {}
    for key, value in payload.items():
        output[key] = round(value, 6) if isinstance(value, float) else value
    return output


def log_loss_binary(pairs: list[tuple[float, int]]) -> float | None:
    if not pairs:
        return None
    epsilon = 1e-12
    losses = []
    for probability, label in pairs:
        p = min(max(probability, epsilon), 1.0 - epsilon)
        losses.append(-(label * math.log(p) + (1 - label) * math.log(1 - p)))
    return statistics.fmean(losses)


def brier_binary(pairs: list[tuple[float, int]]) -> float | None:
    if not pairs:
        return None
    return statistics.fmean([(probability - label) ** 2 for probability, label in pairs])


def role_pair(row: dict[str, str], prediction_field: str = "expected_minutes") -> tuple[float, float] | None:
    if as_int(row.get("actual_boxscore_row_found")) != 1 or as_int(row.get("actual_played")) != 1:
        return None
    prediction = as_float(row.get(prediction_field))
    actual = as_float(row.get("actual_minutes"))
    if prediction is None or actual is None:
        return None
    return prediction, actual


def realized_pair(row: dict[str, str]) -> tuple[float, float] | None:
    if as_int(row.get("actual_boxscore_row_found")) != 1:
        return None
    prediction = as_float(row.get("predicted_realized_minutes"))
    actual = as_float(row.get("actual_minutes"))
    if prediction is None or actual is None:
        return None
    return prediction, actual


def group_metrics(
    rows: list[dict[str, str]],
    dimension: str,
    metric_type: str,
    pair_fn: Callable[[dict[str, str]], tuple[float, float] | None],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for row in rows:
        pair = pair_fn(row)
        if pair is None:
            continue
        value = str(row.get(dimension, "")).strip() or "MISSING"
        grouped[value].append(pair)
    output = []
    for value, pairs in sorted(grouped.items()):
        item = rounded(metrics(pairs))
        output.append({
            "metric_type": metric_type,
            "group_dimension": dimension,
            "group_value": value,
            **item,
        })
    return output


def subgroup_lookup(rows: list[dict[str, Any]], dimension: str, value: str, metric_type: str = "conditional_role_minutes") -> dict[str, Any]:
    for row in rows:
        if row["metric_type"] == metric_type and row["group_dimension"] == dimension and row["group_value"] == value:
            return row
    return {"n": 0, "mae": None, "rmse": None, "median_absolute_error": None, "bias": None}


def paired_baseline_metrics(rows: list[dict[str, str]], baseline_field: str) -> dict[str, Any]:
    proxy_pairs = []
    baseline_pairs = []
    for row in rows:
        if as_int(row.get("actual_boxscore_row_found")) != 1 or as_int(row.get("actual_played")) != 1:
            continue
        proxy = as_float(row.get("expected_minutes"))
        baseline = as_float(row.get(baseline_field))
        actual = as_float(row.get("actual_minutes"))
        if proxy is None or baseline is None or actual is None:
            continue
        proxy_pairs.append((proxy, actual))
        baseline_pairs.append((baseline, actual))
    proxy_metrics = metrics(proxy_pairs)
    baseline_metrics = metrics(baseline_pairs)
    improvement = None
    if proxy_metrics["mae"] is not None and baseline_metrics["mae"] is not None:
        improvement = baseline_metrics["mae"] - proxy_metrics["mae"]
    return {
        "n": proxy_metrics["n"],
        "proxy_mae": proxy_metrics["mae"],
        "baseline_mae": baseline_metrics["mae"],
        "mae_improvement": improvement,
        "proxy_bias": proxy_metrics["bias"],
        "baseline_bias": baseline_metrics["bias"],
    }


def team_aggregates(rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row.get("historical_game_id", "")), str(row.get("team_abbr", "")))].append(row)

    summaries = []
    complete_groups = 0
    played_groups = 0
    played_pairs = []
    realized_pairs = []
    for (game_id, team), items in sorted(grouped.items()):
        complete = all(
            as_int(row.get("identity_matched")) == 1
            and as_int(row.get("expected_minutes_available")) == 1
            and as_int(row.get("actual_boxscore_row_found")) == 1
            for row in items
        )
        if not complete:
            continue
        complete_groups += 1
        played_items = [row for row in items if as_int(row.get("actual_played")) == 1]
        if played_items:
            predicted_played = sum(float(row["expected_minutes"]) for row in played_items)
            actual_played = sum(float(row["actual_minutes"]) for row in played_items)
            played_pairs.append((predicted_played, actual_played))
            played_groups += 1
        predicted_realized = sum(float(row["predicted_realized_minutes"]) for row in items)
        actual_realized = sum(float(row["actual_minutes"]) for row in items)
        realized_pairs.append((predicted_realized, actual_realized))
        summaries.append({
            "historical_game_id": game_id,
            "team_abbr": team,
            "listed_player_rows": len(items),
            "actual_played_rows": len(played_items),
            "predicted_played_role_minutes": "" if not played_items else round(predicted_played, 6),
            "actual_played_minutes": "" if not played_items else round(actual_played, 6),
            "predicted_status_adjusted_realized_minutes": round(predicted_realized, 6),
            "actual_realized_minutes": round(actual_realized, 6),
        })
    return summaries, {
        "complete_team_game_groups": complete_groups,
        "complete_team_game_groups_with_played_rows": played_groups,
        "played_role_aggregate": metrics(played_pairs),
        "status_adjusted_realized_aggregate": metrics(realized_pairs),
    }


def audit(
    rows: list[dict[str, str]],
    dataset_report: dict[str, Any],
    policy: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    structural = policy["structural_gates"]
    accuracy_gate = policy["primary_accuracy_gates"]
    expected_games = as_int(policy["evaluation_population"]["combined_selected_independent_games"])

    row_keys = [
        (str(row.get("source_wave", "")), str(row.get("historical_game_id", "")), str(row.get("snapshot_record_id", "")))
        for row in rows
    ]
    duplicate_rows = len(row_keys) - len(set(row_keys))
    selected_games = {str(row.get("historical_game_id", "")) for row in rows if row.get("historical_game_id")}
    role_rows = [row for row in rows if role_pair(row) is not None]
    role_games = {str(row.get("historical_game_id", "")) for row in role_rows}
    role_pairs = [role_pair(row) for row in rows]
    role_pairs = [pair for pair in role_pairs if pair is not None]
    overall = rounded(metrics(role_pairs))
    realized_pairs = [realized_pair(row) for row in rows]
    realized_pairs = [pair for pair in realized_pairs if pair is not None]
    realized = rounded(metrics(realized_pairs))

    play_pairs = []
    for row in rows:
        probability = as_float(row.get("predicted_play_probability"))
        actual = as_float(row.get("actual_played"))
        if probability is None or actual is None or as_int(row.get("actual_boxscore_row_found")) != 1:
            continue
        play_pairs.append((probability, int(actual)))
    play_brier = brier_binary(play_pairs)
    play_log_loss = log_loss_binary(play_pairs)

    subgroup_rows = []
    for dimension in policy.get("required_subgroups", []):
        subgroup_rows.extend(group_metrics(rows, dimension, "conditional_role_minutes", role_pair))
    subgroup_rows.extend(group_metrics(rows, "availability_status", "status_adjusted_realized_minutes", realized_pair))

    starter = subgroup_lookup(subgroup_rows, "actual_role", "STARTER")
    bench = subgroup_lookup(subgroup_rows, "actual_role", "BENCH")
    long_history_pairs = [
        role_pair(row) for row in rows
        if as_int(row.get("prior_games")) >= 10 and role_pair(row) is not None
    ]
    long_history = rounded(metrics([pair for pair in long_history_pairs if pair is not None]))
    last_game_baseline = rounded(paired_baseline_metrics(rows, "baseline_last_prior_game_minutes"))
    recent10_baseline = rounded(paired_baseline_metrics(rows, "baseline_recent10_mean_minutes"))
    season_mean_baseline = rounded(paired_baseline_metrics(rows, "baseline_current_season_mean_minutes"))

    team_rows, team_summary_raw = team_aggregates(rows)
    team_played = rounded(team_summary_raw["played_role_aggregate"])
    team_realized = rounded(team_summary_raw["status_adjusted_realized_aggregate"])

    monitored_min_n = as_int(accuracy_gate["minimum_monitored_subgroup_rows"])
    monitored = [
        row for row in subgroup_rows
        if row["metric_type"] == "conditional_role_minutes"
        and as_int(row.get("n")) >= monitored_min_n
        and row.get("bias") is not None
    ]
    worst_monitored_bias = max((abs(float(row["bias"])) for row in monitored), default=0.0)
    worst_monitored_rows = [
        row for row in monitored
        if abs(float(row["bias"])) == worst_monitored_bias
    ]

    dataset_coverage = dataset_report.get("coverage", {})
    dataset_quality = dataset_report.get("quality", {})
    actual_join_rate = as_float(dataset_coverage.get("actual_boxscore_join_rate_for_matched_players")) or 0.0
    identity_rate = as_float(dataset_coverage.get("identity_match_rate")) or 0.0
    expected_coverage = as_float(dataset_coverage.get("expected_minutes_coverage")) or 0.0
    complete_team_groups = as_int(team_summary_raw["complete_team_game_groups"])

    structural_results = {
        "dataset_builder_ready": dataset_report.get("decision", {}).get("ready_for_expected_minutes_accuracy_audit") is True,
        "combined_selected_games_exact": len(selected_games) == expected_games == as_int(structural["required_combined_selected_games"]),
        "minimum_evaluable_games": len(role_games) >= as_int(structural["minimum_games_with_evaluable_player_rows"]),
        "minimum_player_snapshot_rows": len(rows) >= as_int(structural["minimum_selected_player_snapshot_rows"]),
        "identity_match_rate": identity_rate >= float(structural["minimum_identity_match_rate"]),
        "expected_minutes_coverage": expected_coverage >= float(structural["minimum_expected_minutes_coverage"]),
        "actual_boxscore_join_rate": actual_join_rate >= float(structural["minimum_actual_boxscore_join_rate_for_matched_players"]),
        "minimum_conditional_role_rows": len(role_rows) >= as_int(structural["minimum_conditional_role_rows"]),
        "minimum_actual_starter_rows": as_int(starter.get("n")) >= as_int(structural["minimum_actual_starter_rows"]),
        "minimum_actual_bench_rows": as_int(bench.get("n")) >= as_int(structural["minimum_actual_bench_rows"]),
        "minimum_long_history_rows": as_int(long_history.get("n")) >= as_int(structural["minimum_long_history_rows"]),
        "minimum_complete_team_game_groups": complete_team_groups >= as_int(structural["minimum_complete_team_game_groups"]),
        "strict_prior_date_violations": as_int(dataset_quality.get("strict_prior_date_violations")) == as_int(structural["strict_prior_date_violations"]),
        "duplicate_selected_games": as_int(dataset_quality.get("duplicate_selected_games")) == as_int(structural["duplicate_selected_games"]),
        "duplicate_accuracy_rows": duplicate_rows == as_int(structural["duplicate_accuracy_rows"]),
        "target_labels_not_used_in_prediction": dataset_quality.get("target_game_labels_used_in_prediction") is False,
        "missing_actual_not_imputed_zero": dataset_quality.get("missing_actual_boxscore_row_imputed_as_zero") is False,
        "missing_expected_not_imputed_zero": dataset_quality.get("missing_expected_minutes_imputed_as_zero") is False,
    }
    structural_ready = all(structural_results.values())

    accuracy_results = {
        "overall_mae": overall["mae"] is not None and overall["mae"] <= float(accuracy_gate["maximum_overall_mae_minutes"]),
        "overall_rmse": overall["rmse"] is not None and overall["rmse"] <= float(accuracy_gate["maximum_overall_rmse_minutes"]),
        "overall_median_absolute_error": overall["median_absolute_error"] is not None and overall["median_absolute_error"] <= float(accuracy_gate["maximum_overall_median_absolute_error_minutes"]),
        "overall_absolute_bias": overall["bias"] is not None and abs(overall["bias"]) <= float(accuracy_gate["maximum_absolute_overall_bias_minutes"]),
        "improvement_vs_last_game": last_game_baseline["mae_improvement"] is not None and last_game_baseline["mae_improvement"] >= float(accuracy_gate["minimum_mae_improvement_vs_last_prior_game_minutes"]),
        "improvement_vs_recent10": recent10_baseline["mae_improvement"] is not None and recent10_baseline["mae_improvement"] >= float(accuracy_gate["minimum_mae_improvement_vs_recent10_mean_minutes"]),
        "starter_mae": starter.get("mae") is not None and float(starter["mae"]) <= float(accuracy_gate["maximum_actual_starter_mae_minutes"]),
        "bench_mae": bench.get("mae") is not None and float(bench["mae"]) <= float(accuracy_gate["maximum_actual_bench_mae_minutes"]),
        "long_history_mae": long_history["mae"] is not None and long_history["mae"] <= float(accuracy_gate["maximum_long_history_mae_minutes"]),
        "team_played_aggregate_mae": team_played["mae"] is not None and team_played["mae"] <= float(accuracy_gate["maximum_complete_team_played_aggregate_mae_minutes"]),
        "team_played_aggregate_absolute_bias": team_played["bias"] is not None and abs(team_played["bias"]) <= float(accuracy_gate["maximum_absolute_complete_team_played_aggregate_bias_minutes"]),
        "monitored_subgroup_absolute_bias": worst_monitored_bias <= float(accuracy_gate["maximum_monitored_subgroup_absolute_bias_minutes"]),
    }
    accuracy_passed = structural_ready and all(accuracy_results.values())

    output_dir.mkdir(parents=True, exist_ok=True)
    subgroup_fields = [
        "metric_type", "group_dimension", "group_value", "n", "mae", "rmse",
        "median_absolute_error", "bias",
    ]
    write_csv(output_dir / "expected-minutes-accuracy-subgroups.csv", subgroup_rows, subgroup_fields)
    team_metric_rows = [
        {"metric": "conditional_played_role_team_aggregate", **team_played},
        {"metric": "status_adjusted_realized_team_aggregate", **team_realized},
    ]
    write_csv(
        output_dir / "expected-minutes-team-aggregate-summary.csv",
        team_metric_rows,
        ["metric", "n", "mae", "rmse", "median_absolute_error", "bias"],
    )

    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "policy_schema_version": policy.get("schema_version"),
        "estimands": {
            "primary": policy.get("primary_estimand"),
            "secondary": policy.get("secondary_estimands"),
        },
        "coverage": {
            "combined_selected_games": len(selected_games),
            "games_with_conditional_role_rows": len(role_games),
            "selected_player_snapshot_rows": len(rows),
            "identity_match_rate": round(identity_rate, 6),
            "expected_minutes_coverage": round(expected_coverage, 6),
            "actual_boxscore_join_rate_for_matched_players": round(actual_join_rate, 6),
            "conditional_role_rows": len(role_rows),
            "actual_starter_rows": as_int(starter.get("n")),
            "actual_bench_rows": as_int(bench.get("n")),
            "actual_dnp_rows": sum(str(row.get("actual_role")) == "DNP" for row in rows),
            "missing_actual_boxscore_rows": sum(str(row.get("actual_role")) == "MISSING_BOXSCORE_ROW" for row in rows),
            "long_history_rows": as_int(long_history.get("n")),
            "complete_team_game_groups": complete_team_groups,
            "complete_team_game_groups_with_played_rows": as_int(team_summary_raw["complete_team_game_groups_with_played_rows"]),
            "monitored_subgroups": len(monitored),
        },
        "primary_accuracy": {
            "overall": overall,
            "actual_starter": starter,
            "actual_bench": bench,
            "long_history_prior_games_10_plus": long_history,
            "paired_baseline_last_prior_game": last_game_baseline,
            "paired_baseline_recent10_mean": recent10_baseline,
            "paired_baseline_current_season_mean": season_mean_baseline,
            "complete_team_played_role_aggregate": team_played,
            "worst_monitored_subgroup_absolute_bias": round(worst_monitored_bias, 6),
            "worst_monitored_subgroup_examples": worst_monitored_rows[:10],
        },
        "secondary_diagnostics": {
            "status_adjusted_realized_minutes": realized,
            "play_probability_rows": len(play_pairs),
            "play_probability_brier": None if play_brier is None else round(play_brier, 6),
            "play_probability_log_loss": None if play_log_loss is None else round(play_log_loss, 6),
            "complete_team_status_adjusted_realized_aggregate": team_realized,
            "status_weights_are_research_assumptions": True,
            "secondary_metrics_are_promotion_gates": False,
        },
        "quality": {
            "duplicate_accuracy_rows": duplicate_rows,
            "dataset_quality": dataset_quality,
            "structural_gate_results": structural_results,
            "accuracy_gate_results": accuracy_results,
            "all_structural_gates_passed": structural_ready,
            "all_primary_accuracy_gates_passed": all(accuracy_results.values()),
            "actual_starter_and_bench_are_label_side_subgroups": True,
            "actual_dnp_in_primary_role_metric": False,
            "missing_boxscore_rows_imputed_as_zero": False,
            "missing_expected_minutes_imputed_as_zero": False,
            "target_game_labels_used_in_prediction": False,
            "player_names_or_injury_reasons_in_outputs": False,
        },
        "decision": {
            "expected_minutes_accuracy_audit_passed": accuracy_passed,
            "ready_for_injury_feature_walk_forward_holdout_design": accuracy_passed,
            "ready_for_injury_feature_walk_forward_holdout": False,
            "ready_for_model_training": False,
            "ready_for_probability_adjustment": False,
            "ready_for_betting_edge_claim": False,
            "reason": (
                "Expected Minutes passed the predeclared structural, overall, baseline, subgroup, and team-level accuracy gates. A separate injury holdout design may proceed."
                if accuracy_passed
                else "Expected Minutes did not pass all predeclared accuracy gates; it remains a research proxy and injury holdout design stays blocked."
                if structural_ready
                else "The Expected Minutes audit failed one or more structural or point-in-time gates."
            ),
        },
        "guardrails": {
            "accuracy_pass_directly_activates_model": False,
            "accuracy_pass_directly_runs_holdout": False,
            "holdout_promotion_gate_still_required": True,
            "secondary_status_metrics_can_override_primary_failure": False,
        },
    }
    (output_dir / "expected-minutes-accuracy-audit.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def self_test(output_dir: Path) -> None:
    rows = []
    for index in range(12):
        actual = 30.0 + (index % 3)
        predicted = actual + (0.5 if index % 2 == 0 else -0.5)
        role = "STARTER" if index < 6 else "BENCH"
        rows.append({
            "source_wave": "wave1" if index < 6 else "wave2",
            "historical_game_id": f"g{index}",
            "snapshot_record_id": f"s{index}",
            "team_abbr": "AAA",
            "identity_matched": "1",
            "expected_minutes_available": "1",
            "actual_boxscore_row_found": "1",
            "actual_played": "1",
            "actual_starter": "1" if role == "STARTER" else "0",
            "actual_role": role,
            "actual_minutes": str(actual),
            "expected_minutes": str(predicted),
            "predicted_realized_minutes": str(predicted),
            "predicted_play_probability": "0.9",
            "availability_status": "PROBABLE",
            "expected_minutes_method": "current_season_stabilized",
            "prior_games": "12",
            "prior_game_count_band": "10+",
            "expected_minutes_band": "24-31.99",
            "days_since_latest_prior_game_band": "0-3",
            "baseline_last_prior_game_minutes": str(actual + 2.0),
            "baseline_recent10_mean_minutes": str(actual + 1.0),
            "baseline_current_season_mean_minutes": str(actual + 1.5),
        })
    dataset_report = {
        "coverage": {
            "identity_match_rate": 1.0,
            "expected_minutes_coverage": 1.0,
            "actual_boxscore_join_rate_for_matched_players": 1.0,
        },
        "quality": {
            "strict_prior_date_violations": 0,
            "duplicate_selected_games": 0,
            "target_game_labels_used_in_prediction": False,
            "missing_actual_boxscore_row_imputed_as_zero": False,
            "missing_expected_minutes_imputed_as_zero": False,
        },
        "decision": {"ready_for_expected_minutes_accuracy_audit": True},
    }
    policy = {
        "schema_version": "test",
        "evaluation_population": {"combined_selected_independent_games": 12},
        "primary_estimand": {},
        "secondary_estimands": [],
        "required_subgroups": ["availability_status", "actual_role", "source_wave"],
        "structural_gates": {
            "required_combined_selected_games": 12,
            "minimum_games_with_evaluable_player_rows": 10,
            "minimum_selected_player_snapshot_rows": 10,
            "minimum_identity_match_rate": 0.95,
            "minimum_expected_minutes_coverage": 0.85,
            "minimum_actual_boxscore_join_rate_for_matched_players": 0.90,
            "minimum_conditional_role_rows": 10,
            "minimum_actual_starter_rows": 5,
            "minimum_actual_bench_rows": 5,
            "minimum_long_history_rows": 10,
            "minimum_complete_team_game_groups": 10,
            "strict_prior_date_violations": 0,
            "duplicate_selected_games": 0,
            "duplicate_accuracy_rows": 0,
        },
        "primary_accuracy_gates": {
            "maximum_overall_mae_minutes": 1.0,
            "maximum_overall_rmse_minutes": 1.0,
            "maximum_overall_median_absolute_error_minutes": 1.0,
            "maximum_absolute_overall_bias_minutes": 1.0,
            "minimum_mae_improvement_vs_last_prior_game_minutes": 0.25,
            "minimum_mae_improvement_vs_recent10_mean_minutes": 0.0,
            "maximum_actual_starter_mae_minutes": 1.0,
            "maximum_actual_bench_mae_minutes": 1.0,
            "maximum_long_history_mae_minutes": 1.0,
            "maximum_complete_team_played_aggregate_mae_minutes": 1.0,
            "maximum_absolute_complete_team_played_aggregate_bias_minutes": 1.0,
            "maximum_monitored_subgroup_absolute_bias_minutes": 1.0,
            "minimum_monitored_subgroup_rows": 2,
        },
    }
    report = audit(rows, dataset_report, policy, output_dir)
    assert report["decision"]["expected_minutes_accuracy_audit_passed"] is True, report
    assert report["decision"]["ready_for_injury_feature_walk_forward_holdout"] is False, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--accuracy-rows", type=Path)
    parser.add_argument("--dataset-report", type=Path)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("Expected Minutes accuracy audit self-test passed")
        return
    if not args.accuracy_rows or not args.dataset_report or not args.policy:
        parser.error("--accuracy-rows, --dataset-report, and --policy are required")
    report = audit(
        read_csv(args.accuracy_rows),
        read_json(args.dataset_report),
        read_json(args.policy),
        args.output_dir,
    )
    print(json.dumps(report["decision"], indent=2))
    if not report["quality"]["all_structural_gates_passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
