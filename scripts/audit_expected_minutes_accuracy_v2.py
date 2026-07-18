#!/usr/bin/env python3
"""Run Expected Minutes Accuracy Audit v2 using official participation labels.

Primary accuracy remains conditional role minutes for official PLAYED labels only. Explicit DNP
and inactive labels are evaluated through secondary realized-minutes and play-probability diagnostics.
UNKNOWN, source-missing, identity-missing, and missing predictions remain missing.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import audit_expected_minutes_accuracy as v1

VERSION = "expected-minutes-accuracy-audit-v2"
CLASSIFIED_LABELS = {"PLAYED", "EXPLICIT_DNP", "INACTIVE_OR_NOT_DRESSED"}


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
    return v1.as_float(value)


def as_int(value: Any, default: int = 0) -> int:
    return v1.as_int(value, default)


def role_pair(
    row: dict[str, str],
    prediction_field: str = "expected_minutes",
) -> tuple[float, float] | None:
    if str(row.get("participation_label") or "") != "PLAYED":
        return None
    if as_int(row.get("actual_classified_label_available")) != 1:
        return None
    prediction = as_float(row.get(prediction_field))
    actual = as_float(row.get("actual_minutes"))
    if prediction is None or actual is None or actual <= 0:
        return None
    return prediction, actual


def realized_pair(row: dict[str, str]) -> tuple[float, float] | None:
    if str(row.get("participation_label") or "") not in CLASSIFIED_LABELS:
        return None
    if as_int(row.get("actual_classified_label_available")) != 1:
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
        value = str(row.get(dimension) or "").strip() or "MISSING"
        grouped[value].append(pair)
    output = []
    for value, pairs in sorted(grouped.items()):
        output.append({
            "metric_type": metric_type,
            "group_dimension": dimension,
            "group_value": value,
            **v1.rounded(v1.metrics(pairs)),
        })
    return output


def subgroup_lookup(
    rows: list[dict[str, Any]],
    dimension: str,
    value: str,
    metric_type: str = "conditional_role_minutes",
) -> dict[str, Any]:
    for row in rows:
        if (
            row["metric_type"] == metric_type
            and row["group_dimension"] == dimension
            and row["group_value"] == value
        ):
            return row
    return {
        "n": 0,
        "mae": None,
        "rmse": None,
        "median_absolute_error": None,
        "bias": None,
    }


def paired_baseline_metrics(
    rows: list[dict[str, str]],
    baseline_field: str,
) -> dict[str, Any]:
    proxy_pairs = []
    baseline_pairs = []
    for row in rows:
        if str(row.get("participation_label") or "") != "PLAYED":
            continue
        proxy = as_float(row.get("expected_minutes"))
        baseline = as_float(row.get(baseline_field))
        actual = as_float(row.get("actual_minutes"))
        if proxy is None or baseline is None or actual is None or actual <= 0:
            continue
        proxy_pairs.append((proxy, actual))
        baseline_pairs.append((baseline, actual))
    proxy_metrics = v1.metrics(proxy_pairs)
    baseline_metrics = v1.metrics(baseline_pairs)
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


def team_aggregates(
    rows: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(
            str(row.get("historical_game_id") or ""),
            str(row.get("team_abbr") or ""),
        )].append(row)

    summaries = []
    complete_groups = 0
    played_groups = 0
    played_pairs = []
    realized_pairs = []
    for (game_id, team), items in sorted(grouped.items()):
        complete = all(
            as_int(row.get("identity_matched")) == 1
            and as_int(row.get("expected_minutes_available")) == 1
            and str(row.get("participation_label") or "") in CLASSIFIED_LABELS
            and as_int(row.get("actual_classified_label_available")) == 1
            for row in items
        )
        if not complete:
            continue
        complete_groups += 1
        played_items = [
            row for row in items
            if str(row.get("participation_label") or "") == "PLAYED"
        ]
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
            "official_played_rows": len(played_items),
            "predicted_played_role_minutes": "" if not played_items else round(predicted_played, 6),
            "actual_played_minutes": "" if not played_items else round(actual_played, 6),
            "predicted_status_adjusted_realized_minutes": round(predicted_realized, 6),
            "actual_realized_minutes": round(actual_realized, 6),
        })
    return summaries, {
        "complete_team_game_groups": complete_groups,
        "complete_team_game_groups_with_played_rows": played_groups,
        "played_role_aggregate": v1.metrics(played_pairs),
        "status_adjusted_realized_aggregate": v1.metrics(realized_pairs),
    }


def audit(
    rows: list[dict[str, str]],
    dataset_report: dict[str, Any],
    policy: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    structural = policy["structural_gates"]
    accuracy_gate = policy["primary_accuracy_gates"]
    expected_games = as_int(
        policy["evaluation_population"]["combined_selected_independent_games"]
    )

    row_keys = [
        (
            str(row.get("source_wave") or ""),
            str(row.get("historical_game_id") or ""),
            str(row.get("snapshot_record_id") or ""),
        )
        for row in rows
    ]
    duplicate_rows = len(row_keys) - len(set(row_keys))
    selected_games = {
        str(row.get("historical_game_id") or "")
        for row in rows
        if row.get("historical_game_id")
    }
    role_rows = [row for row in rows if role_pair(row) is not None]
    role_games = {
        str(row.get("historical_game_id") or "") for row in role_rows
    }
    role_pairs = [pair for row in rows if (pair := role_pair(row)) is not None]
    overall = v1.rounded(v1.metrics(role_pairs))

    realized_pairs = [
        pair for row in rows if (pair := realized_pair(row)) is not None
    ]
    realized = v1.rounded(v1.metrics(realized_pairs))

    play_pairs = []
    for row in rows:
        label = str(row.get("participation_label") or "")
        if label not in CLASSIFIED_LABELS:
            continue
        probability = as_float(row.get("predicted_play_probability"))
        if probability is None:
            continue
        play_pairs.append((probability, 1 if label == "PLAYED" else 0))
    play_brier = v1.brier_binary(play_pairs)
    play_log_loss = v1.log_loss_binary(play_pairs)

    subgroup_rows = []
    for dimension in policy.get("required_subgroups", []):
        subgroup_rows.extend(
            group_metrics(
                rows,
                dimension,
                "conditional_role_minutes",
                role_pair,
            )
        )
    subgroup_rows.extend(
        group_metrics(
            rows,
            "availability_status",
            "status_adjusted_realized_minutes",
            realized_pair,
        )
    )
    subgroup_rows.extend(
        group_metrics(
            rows,
            "participation_label",
            "status_adjusted_realized_minutes",
            realized_pair,
        )
    )

    starter = subgroup_lookup(subgroup_rows, "actual_role", "STARTER")
    bench = subgroup_lookup(subgroup_rows, "actual_role", "BENCH")
    long_history_pairs = [
        pair
        for row in rows
        if as_int(row.get("prior_games")) >= 10
        and (pair := role_pair(row)) is not None
    ]
    long_history = v1.rounded(v1.metrics(long_history_pairs))
    last_game_baseline = v1.rounded(
        paired_baseline_metrics(rows, "baseline_last_prior_game_minutes")
    )
    recent10_baseline = v1.rounded(
        paired_baseline_metrics(rows, "baseline_recent10_mean_minutes")
    )
    season_mean_baseline = v1.rounded(
        paired_baseline_metrics(rows, "baseline_current_season_mean_minutes")
    )

    team_rows, team_summary_raw = team_aggregates(rows)
    team_played = v1.rounded(team_summary_raw["played_role_aggregate"])
    team_realized = v1.rounded(
        team_summary_raw["status_adjusted_realized_aggregate"]
    )

    monitored_min_n = as_int(accuracy_gate["minimum_monitored_subgroup_rows"])
    monitored = [
        row
        for row in subgroup_rows
        if row["metric_type"] == "conditional_role_minutes"
        and as_int(row.get("n")) >= monitored_min_n
        and row.get("bias") is not None
    ]
    worst_monitored_bias = max(
        (abs(float(row["bias"])) for row in monitored),
        default=0.0,
    )
    worst_monitored_rows = [
        row
        for row in monitored
        if abs(float(row["bias"])) == worst_monitored_bias
    ]

    coverage = dataset_report.get("coverage", {})
    quality = dataset_report.get("quality", {})
    identity_rate = as_float(coverage.get("identity_match_rate")) or 0.0
    expected_coverage = as_float(coverage.get("expected_minutes_coverage")) or 0.0
    source_coverage = as_float(coverage.get("official_game_source_coverage")) or 0.0
    participation_join_rate = as_float(
        coverage.get("participation_label_join_rate_for_matched_players")
    ) or 0.0
    unknown_rate = as_float(
        coverage.get("unknown_rate_for_matched_players")
    ) or 0.0
    source_missing_games = as_int(coverage.get("source_missing_games"))
    complete_team_groups = as_int(team_summary_raw["complete_team_game_groups"])

    structural_results = {
        "dataset_builder_ready": dataset_report.get("decision", {}).get(
            "ready_for_expected_minutes_accuracy_audit_v2_execution"
        ) is True,
        "combined_selected_games_exact": len(selected_games)
        == expected_games
        == as_int(structural["required_combined_selected_games"]),
        "minimum_evaluable_games": len(role_games)
        >= as_int(structural["minimum_games_with_evaluable_player_rows"]),
        "minimum_player_snapshot_rows": len(rows)
        >= as_int(structural["minimum_selected_player_snapshot_rows"]),
        "official_game_source_coverage": source_coverage
        >= float(structural["minimum_official_game_source_coverage"]),
        "identity_match_rate": identity_rate
        >= float(structural["minimum_identity_match_rate"]),
        "expected_minutes_coverage": expected_coverage
        >= float(structural["minimum_expected_minutes_coverage"]),
        "participation_label_join_rate": participation_join_rate
        >= float(
            structural[
                "minimum_participation_label_join_rate_for_matched_players"
            ]
        ),
        "unknown_rate": unknown_rate
        <= float(structural["maximum_unknown_rate_for_matched_players"]),
        "source_missing_games": source_missing_games
        <= as_int(structural["maximum_source_missing_games"]),
        "minimum_conditional_role_rows": len(role_rows)
        >= as_int(structural["minimum_conditional_role_rows"]),
        "minimum_actual_starter_rows": as_int(starter.get("n"))
        >= as_int(structural["minimum_actual_starter_rows"]),
        "minimum_actual_bench_rows": as_int(bench.get("n"))
        >= as_int(structural["minimum_actual_bench_rows"]),
        "minimum_long_history_rows": as_int(long_history.get("n"))
        >= as_int(structural["minimum_long_history_rows"]),
        "minimum_complete_team_game_groups": complete_team_groups
        >= as_int(structural["minimum_complete_team_game_groups"]),
        "strict_prior_date_violations": as_int(
            quality.get("strict_prior_date_violations")
        )
        == as_int(structural["strict_prior_date_violations"]),
        "duplicate_selected_games": as_int(
            quality.get("duplicate_selected_games")
        )
        == as_int(structural["duplicate_selected_games"]),
        "duplicate_accuracy_rows": duplicate_rows
        == as_int(structural["duplicate_accuracy_rows"]),
        "duplicate_official_game_player_rows": as_int(
            quality.get("duplicate_official_game_player_rows")
        )
        == as_int(structural["duplicate_official_game_player_rows"]),
        "team_mismatches": as_int(quality.get("team_mismatches"))
        == as_int(structural["team_mismatches"]),
        "invalid_participation_labels": as_int(
            quality.get("invalid_participation_labels")
        )
        == as_int(structural["invalid_participation_labels"]),
        "invalid_minutes_label_combinations": as_int(
            quality.get("invalid_minutes_label_combinations")
        )
        == as_int(structural["invalid_minutes_label_combinations"]),
        "target_labels_not_used_in_prediction": quality.get(
            "target_game_labels_used_in_prediction"
        ) is False,
        "secondary_archive_not_used_for_target_labels": quality.get(
            "secondary_archive_used_for_target_game_labels"
        ) is False,
        "missing_actual_not_imputed_zero": quality.get(
            "missing_actual_participation_imputed_as_zero"
        ) is False,
        "missing_expected_not_imputed_zero": quality.get(
            "missing_expected_minutes_imputed_as_zero"
        ) is False,
    }
    structural_ready = all(structural_results.values())

    accuracy_results = {
        "overall_mae": overall["mae"] is not None
        and overall["mae"]
        <= float(accuracy_gate["maximum_overall_mae_minutes"]),
        "overall_rmse": overall["rmse"] is not None
        and overall["rmse"]
        <= float(accuracy_gate["maximum_overall_rmse_minutes"]),
        "overall_median_absolute_error": overall["median_absolute_error"]
        is not None
        and overall["median_absolute_error"]
        <= float(
            accuracy_gate["maximum_overall_median_absolute_error_minutes"]
        ),
        "overall_absolute_bias": overall["bias"] is not None
        and abs(overall["bias"])
        <= float(accuracy_gate["maximum_absolute_overall_bias_minutes"]),
        "improvement_vs_last_game": last_game_baseline["mae_improvement"]
        is not None
        and last_game_baseline["mae_improvement"]
        >= float(
            accuracy_gate[
                "minimum_mae_improvement_vs_last_prior_game_minutes"
            ]
        ),
        "improvement_vs_recent10": recent10_baseline["mae_improvement"]
        is not None
        and recent10_baseline["mae_improvement"]
        >= float(
            accuracy_gate[
                "minimum_mae_improvement_vs_recent10_mean_minutes"
            ]
        ),
        "starter_mae": starter.get("mae") is not None
        and float(starter["mae"])
        <= float(accuracy_gate["maximum_actual_starter_mae_minutes"]),
        "bench_mae": bench.get("mae") is not None
        and float(bench["mae"])
        <= float(accuracy_gate["maximum_actual_bench_mae_minutes"]),
        "long_history_mae": long_history["mae"] is not None
        and long_history["mae"]
        <= float(accuracy_gate["maximum_long_history_mae_minutes"]),
        "team_played_aggregate_mae": team_played["mae"] is not None
        and team_played["mae"]
        <= float(
            accuracy_gate[
                "maximum_complete_team_played_aggregate_mae_minutes"
            ]
        ),
        "team_played_aggregate_absolute_bias": team_played["bias"]
        is not None
        and abs(team_played["bias"])
        <= float(
            accuracy_gate[
                "maximum_absolute_complete_team_played_aggregate_bias_minutes"
            ]
        ),
        "monitored_subgroup_absolute_bias": worst_monitored_bias
        <= float(
            accuracy_gate["maximum_monitored_subgroup_absolute_bias_minutes"]
        ),
    }
    all_accuracy_gates = all(accuracy_results.values())
    if not structural_ready:
        decision_state = "STRUCTURAL_BLOCKED"
    elif all_accuracy_gates:
        decision_state = "ACCURACY_PASS"
    else:
        decision_state = "VALID_NEGATIVE_RESULT"
    accuracy_passed = decision_state == "ACCURACY_PASS"

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(
        output_dir / "expected-minutes-accuracy-v2-subgroups.csv",
        subgroup_rows,
        [
            "metric_type",
            "group_dimension",
            "group_value",
            "n",
            "mae",
            "rmse",
            "median_absolute_error",
            "bias",
        ],
    )
    write_csv(
        output_dir / "expected-minutes-accuracy-v2-team-summary.csv",
        [
            {"metric": "conditional_played_role_team_aggregate", **team_played},
            {"metric": "status_adjusted_realized_team_aggregate", **team_realized},
        ],
        ["metric", "n", "mae", "rmse", "median_absolute_error", "bias"],
    )

    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "policy_schema_version": policy.get("schema_version"),
        "predeclaration": policy.get("predeclaration"),
        "decision_state": decision_state,
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
            "official_game_source_coverage": round(source_coverage, 6),
            "participation_label_join_rate_for_matched_players": round(
                participation_join_rate, 6
            ),
            "unknown_rate_for_matched_players": round(unknown_rate, 6),
            "source_missing_games": source_missing_games,
            "conditional_role_rows": len(role_rows),
            "actual_starter_rows": as_int(starter.get("n")),
            "actual_bench_rows": as_int(bench.get("n")),
            "explicit_dnp_rows": sum(
                str(row.get("participation_label") or "") == "EXPLICIT_DNP"
                for row in rows
            ),
            "inactive_or_not_dressed_rows": sum(
                str(row.get("participation_label") or "")
                == "INACTIVE_OR_NOT_DRESSED"
                for row in rows
            ),
            "unknown_rows": sum(
                str(row.get("participation_label") or "") == "UNKNOWN"
                for row in rows
            ),
            "long_history_rows": as_int(long_history.get("n")),
            "complete_team_game_groups": complete_team_groups,
            "complete_team_game_groups_with_played_rows": as_int(
                team_summary_raw["complete_team_game_groups_with_played_rows"]
            ),
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
            "worst_monitored_subgroup_absolute_bias": round(
                worst_monitored_bias, 6
            ),
            "worst_monitored_subgroup_examples": worst_monitored_rows[:10],
        },
        "secondary_diagnostics": {
            "status_adjusted_realized_minutes": realized,
            "play_probability_rows": len(play_pairs),
            "play_probability_brier": None
            if play_brier is None
            else round(play_brier, 6),
            "play_probability_log_loss": None
            if play_log_loss is None
            else round(play_log_loss, 6),
            "complete_team_status_adjusted_realized_aggregate": team_realized,
            "status_weights_are_research_assumptions": True,
            "secondary_metrics_are_promotion_gates": False,
        },
        "quality": {
            "duplicate_accuracy_rows": duplicate_rows,
            "dataset_quality": quality,
            "structural_gate_results": structural_results,
            "accuracy_gate_results": accuracy_results,
            "all_structural_gates_passed": structural_ready,
            "all_primary_accuracy_gates_passed": all_accuracy_gates,
            "v1_primary_accuracy_thresholds_preserved": True,
            "v1_sample_size_thresholds_preserved": True,
            "actual_starter_and_bench_are_label_side_subgroups": True,
            "explicit_dnp_in_primary_role_metric": False,
            "inactive_in_primary_role_metric": False,
            "unknown_imputed_as_zero": False,
            "source_missing_imputed_as_zero": False,
            "missing_expected_minutes_imputed_as_zero": False,
            "target_game_labels_used_in_prediction": False,
            "player_names_or_injury_reasons_in_outputs": False,
        },
        "decision": {
            "expected_minutes_accuracy_audit_v2_passed": accuracy_passed,
            "ready_for_injury_feature_walk_forward_holdout_design": accuracy_passed,
            "ready_for_injury_feature_walk_forward_holdout": False,
            "ready_for_model_training": False,
            "ready_for_probability_adjustment": False,
            "ready_for_betting_edge_claim": False,
            "reason": (
                "Expected Minutes passed every predeclared v2 structural and primary accuracy gate. A separate Injury Feature Walk-forward Holdout design may proceed."
                if decision_state == "ACCURACY_PASS"
                else "Every v2 structural gate passed, but one or more preserved primary accuracy gates failed. Expected Minutes remains a research proxy."
                if decision_state == "VALID_NEGATIVE_RESULT"
                else "Expected Minutes Accuracy Audit v2 failed one or more predeclared structural, coverage, sample-size, or point-in-time gates."
            ),
        },
        "guardrails": {
            "v1_result_reclassified_as_pass": False,
            "accuracy_pass_directly_activates_model": False,
            "accuracy_pass_directly_runs_holdout": False,
            "holdout_promotion_gate_still_required": True,
            "secondary_metrics_can_override_primary_failure": False,
            "formal_stake": 0,
        },
    }
    (output_dir / "expected-minutes-accuracy-audit-v2.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
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
            "official_game_source_available": "1",
            "official_participation_row_found": "1",
            "actual_classified_label_available": "1",
            "participation_label": "PLAYED",
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
            "baseline_current_season_mean_minutes": str(actual + 1.0),
        })
    dataset_report = {
        "coverage": {
            "identity_match_rate": 1.0,
            "expected_minutes_coverage": 1.0,
            "official_game_source_coverage": 1.0,
            "participation_label_join_rate_for_matched_players": 1.0,
            "unknown_rate_for_matched_players": 0.0,
            "source_missing_games": 0,
        },
        "quality": {
            "strict_prior_date_violations": 0,
            "duplicate_selected_games": 0,
            "duplicate_official_game_player_rows": 0,
            "team_mismatches": 0,
            "invalid_participation_labels": 0,
            "invalid_minutes_label_combinations": 0,
            "target_game_labels_used_in_prediction": False,
            "secondary_archive_used_for_target_game_labels": False,
            "missing_actual_participation_imputed_as_zero": False,
            "missing_expected_minutes_imputed_as_zero": False,
        },
        "decision": {
            "ready_for_expected_minutes_accuracy_audit_v2_execution": True
        },
    }
    policy = {
        "schema_version": "test-v2",
        "predeclaration": {
            "v1_primary_accuracy_thresholds_preserved": True,
            "v1_sample_size_thresholds_preserved": True,
        },
        "evaluation_population": {
            "combined_selected_independent_games": 12
        },
        "primary_estimand": {"name": "test"},
        "secondary_estimands": [],
        "required_subgroups": ["actual_role", "source_wave"],
        "structural_gates": {
            "required_combined_selected_games": 12,
            "minimum_games_with_evaluable_player_rows": 12,
            "minimum_selected_player_snapshot_rows": 12,
            "minimum_official_game_source_coverage": 1.0,
            "minimum_identity_match_rate": 1.0,
            "minimum_expected_minutes_coverage": 1.0,
            "minimum_participation_label_join_rate_for_matched_players": 1.0,
            "maximum_unknown_rate_for_matched_players": 0.0,
            "maximum_source_missing_games": 0,
            "minimum_conditional_role_rows": 12,
            "minimum_actual_starter_rows": 6,
            "minimum_actual_bench_rows": 6,
            "minimum_long_history_rows": 12,
            "minimum_complete_team_game_groups": 12,
            "strict_prior_date_violations": 0,
            "duplicate_selected_games": 0,
            "duplicate_accuracy_rows": 0,
            "duplicate_official_game_player_rows": 0,
            "team_mismatches": 0,
            "invalid_participation_labels": 0,
            "invalid_minutes_label_combinations": 0,
        },
        "primary_accuracy_gates": {
            "maximum_overall_mae_minutes": 1.0,
            "maximum_overall_rmse_minutes": 1.0,
            "maximum_overall_median_absolute_error_minutes": 1.0,
            "maximum_absolute_overall_bias_minutes": 1.0,
            "minimum_mae_improvement_vs_last_prior_game_minutes": 1.0,
            "minimum_mae_improvement_vs_recent10_mean_minutes": 0.0,
            "maximum_actual_starter_mae_minutes": 1.0,
            "maximum_actual_bench_mae_minutes": 1.0,
            "maximum_long_history_mae_minutes": 1.0,
            "maximum_complete_team_played_aggregate_mae_minutes": 12.0,
            "maximum_absolute_complete_team_played_aggregate_bias_minutes": 12.0,
            "maximum_monitored_subgroup_absolute_bias_minutes": 1.0,
            "minimum_monitored_subgroup_rows": 1,
        },
    }
    report = audit(rows, dataset_report, policy, output_dir)
    assert report["decision_state"] == "ACCURACY_PASS", report
    assert report["decision"]["expected_minutes_accuracy_audit_v2_passed"] is True, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=Path)
    parser.add_argument("--dataset-report", type=Path)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test(args.output_dir)
        print("Expected Minutes accuracy audit v2 self-test passed")
        return
    if not args.rows or not args.dataset_report or not args.policy:
        parser.error("--rows, --dataset-report and --policy are required")
    report = audit(
        read_csv(args.rows),
        read_json(args.dataset_report),
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
