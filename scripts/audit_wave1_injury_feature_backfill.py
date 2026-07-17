#!/usr/bin/env python3
"""Audit the complete Wave 1 point-in-time injury feature backfill.

This audit is aggregate-only. It verifies upstream joins, strict-prior player values, team
submission reconciliation, frozen snapshot selection, and independent-game sample gates.
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

VERSION = "wave1-injury-feature-backfill-audit-v1"
FORBIDDEN_FILENAMES = {
    "overlap-player-injury-panel.csv",
    "multi-report-injury-panel-normalized.csv",
    "injury-lineup-snapshots-normalized.csv",
    "injury-player-id-map.csv",
    "point-in-time-player-values.csv",
    "combined-player-boxscores.csv",
    "open-player-boxscores.csv",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def as_int(value: Any, default: int = 0) -> int:
    text = str(value or "").strip()
    return default if not text else int(float(text))


def as_float(value: Any, default: float = 0.0) -> float:
    text = str(value or "").strip()
    return default if not text else float(text)


def forbidden_files(root: Path | None) -> list[str]:
    if root is None or not root.exists():
        return []
    return sorted(
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file() and path.name in FORBIDDEN_FILENAMES
    )


def audit(
    overlap: dict[str, Any],
    player_schedule: dict[str, Any],
    team_schedule: dict[str, Any],
    identity: dict[str, Any],
    values: dict[str, Any],
    features: dict[str, Any],
    reconciliation: dict[str, Any],
    selection: dict[str, Any],
    selected_rows: list[dict[str, str]],
    sensitive_root: Path | None,
    output_dir: Path,
) -> dict[str, Any]:
    overlap_cov = overlap.get("coverage", {})
    player_schedule_cov = player_schedule.get("coverage", {})
    player_schedule_quality = player_schedule.get("quality", {})
    team_schedule_cov = team_schedule.get("coverage", {})
    team_schedule_quality = team_schedule.get("quality", {})
    identity_cov = identity.get("coverage", {})
    identity_quality = identity.get("quality", {})
    value_cov = values.get("coverage", {})
    value_quality = values.get("quality", {})
    feature_cov = features.get("coverage", {})
    feature_quality = features.get("quality", {})
    reconcile_cov = reconciliation.get("coverage", {})
    reconcile_quality = reconciliation.get("quality", {})
    selection_cov = selection.get("coverage", {})
    selection_quality = selection.get("quality", {})
    sample = selection.get("sample_size", {})

    selected_ids = [str(row.get("historical_game_id", "")).strip() for row in selected_rows]
    duplicate_selected = len(selected_ids) - len(set(selected_ids))
    blank_selected_ids = sum(not value for value in selected_ids)
    retained_forbidden = forbidden_files(sensitive_root)

    structural_gates = {
        "overlap_filter_ready": overlap.get("decision", {}).get("ready_for_wave1_feature_pipeline") is True,
        "minimum_overlap_reports": as_int(overlap_cov.get("overlap_reports")) >= 18,
        "minimum_overlap_dates": as_int(overlap_cov.get("overlap_dates")) >= 8,
        "player_schedule_match_rate": as_float(player_schedule_quality.get("game_match_rate")) == 1.0,
        "player_unmatched_games_zero": as_int(player_schedule_quality.get("unmatched_games")) == 0,
        "player_duplicate_gold_keys_zero": as_int(player_schedule_quality.get("duplicate_gold_schedule_keys")) == 0,
        "team_schedule_match_rate": as_float(team_schedule_quality.get("game_match_rate")) == 1.0,
        "team_unmatched_games_zero": as_int(team_schedule_quality.get("unmatched_games")) == 0,
        "team_duplicate_gold_keys_zero": as_int(team_schedule_quality.get("duplicate_gold_schedule_keys")) == 0,
        "identity_match_rate": as_float(identity_quality.get("player_match_rate")) >= 0.95,
        "identity_high_confidence_rate": as_float(identity_quality.get("high_confidence_match_rate")) >= 0.90,
        "identity_ambiguous_zero": as_int(identity_quality.get("ambiguous_player_rows")) == 0,
        "identity_fuzzy_disabled": identity.get("guardrails", {}).get("fuzzy_edit_distance_matching_used") is False,
        "expected_minutes_coverage": as_float(value_cov.get("expected_minutes_coverage")) >= 0.85,
        "impact_coverage": as_float(value_cov.get("player_impact_coverage")) >= 0.85,
        "strict_prior_violations_zero": as_int(value_quality.get("strict_prior_date_violations")) == 0,
        "same_day_not_allowed": values.get("guardrails", {}).get("same_day_rows_allowed") is False,
        "future_not_allowed": values.get("guardrails", {}).get("future_rows_allowed") is False,
        "feature_panel_ready": features.get("decision", {}).get("ready_for_predeclared_snapshot_selection") is True,
        "feature_nonpregame_zero": as_int(feature_quality.get("non_pregame_observations")) == 0,
        "feature_duplicate_snapshots_zero": as_int(feature_quality.get("duplicate_snapshot_rows")) == 0,
        "reconciliation_ready": reconciliation.get("decision", {}).get("ready_for_predeclared_snapshot_selection") is True,
        "reconciliation_errors_zero": as_int(reconcile_quality.get("reconciliation_errors")) == 0,
        "reconciliation_missing_ledger_zero": as_int(reconcile_quality.get("original_team_rows_without_ledger")) == 0,
        "reconciliation_side_errors_zero": as_int(reconcile_quality.get("matchup_side_errors")) == 0,
        "selection_ready": selection.get("decision", {}).get("ready_for_selected_panel_research") is True,
        "selection_outcome_blind": selection_quality.get("outcomes_or_market_prices_used_for_selection") is False,
        "selection_duplicate_games_zero": as_int(selection_quality.get("duplicate_selected_independent_games")) == 0,
        "selected_csv_duplicate_games_zero": duplicate_selected == 0,
        "selected_csv_blank_ids_zero": blank_selected_ids == 0,
        "selected_csv_matches_report": len(selected_rows) == as_int(selection_cov.get("independent_games_selected")),
        "sensitive_player_files_removed": not retained_forbidden,
    }
    structural_ready = all(structural_gates.values())
    selected_games = len(selected_rows)
    minimum_gate = as_int(sample.get("minimum_activation_independent_games"), 100)
    reliability_gate = as_int(sample.get("initial_reliability_independent_games"), 300)
    ideal_gate = as_int(sample.get("ideal_independent_games"), 500)
    minimum_met = structural_ready and selected_games >= minimum_gate
    reliability_met = structural_ready and selected_games >= reliability_gate
    ideal_met = structural_ready and selected_games >= ideal_gate

    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "coverage": {
            "overlap_reports": as_int(overlap_cov.get("overlap_reports")),
            "overlap_dates": as_int(overlap_cov.get("overlap_dates")),
            "filtered_player_rows": as_int(overlap_cov.get("filtered_player_rows")),
            "filtered_team_rows": as_int(overlap_cov.get("filtered_team_rows")),
            "player_schedule_games": as_int(player_schedule_cov.get("snapshot_games")),
            "team_schedule_games": as_int(team_schedule_cov.get("snapshot_games")),
            "identity_rows": as_int(identity_cov.get("snapshot_rows")),
            "matched_player_rows": as_int(identity_cov.get("matched_player_rows")),
            "expected_minutes_rows": as_int(value_cov.get("expected_minutes_rows")),
            "player_impact_rows": as_int(value_cov.get("player_impact_rows")),
            "long_matchup_snapshots": as_int(feature_cov.get("long_matchup_snapshot_rows")),
            "long_independent_games": as_int(feature_cov.get("independent_games")),
            "reconciled_matchup_snapshots": as_int(reconcile_cov.get("reconciled_matchup_snapshot_rows")),
            "reconciled_independent_games": as_int(reconcile_cov.get("independent_games")),
            "selected_independent_games": selected_games,
            "games_without_primary_selection": as_int(selection_cov.get("games_without_primary_selection")),
            "selection_rate": as_float(selection_cov.get("primary_selection_rate")),
            "rejection_reason_counts": selection_cov.get("rejection_reason_counts", {}),
        },
        "quality": {
            "player_match_rate": as_float(identity_quality.get("player_match_rate")),
            "high_confidence_match_rate": as_float(identity_quality.get("high_confidence_match_rate")),
            "ambiguous_player_rows": as_int(identity_quality.get("ambiguous_player_rows")),
            "unmatched_player_rows": as_int(identity_quality.get("unmatched_player_rows")),
            "expected_minutes_coverage": as_float(value_cov.get("expected_minutes_coverage")),
            "player_impact_coverage": as_float(value_cov.get("player_impact_coverage")),
            "strict_prior_date_violations": as_int(value_quality.get("strict_prior_date_violations")),
            "same_day_source_rows_excluded": as_int(value_quality.get("same_day_source_rows_excluded")),
            "future_source_rows_excluded": as_int(value_quality.get("future_source_rows_excluded")),
            "duplicate_selected_games": duplicate_selected,
            "blank_selected_game_ids": blank_selected_ids,
            "forbidden_player_files_found": retained_forbidden,
            "structural_gates": structural_gates,
            "outcomes_or_market_prices_used": False,
        },
        "sample_size": {
            "minimum_activation_independent_games": minimum_gate,
            "initial_reliability_independent_games": reliability_gate,
            "ideal_independent_games": ideal_gate,
            "minimum_activation_met": minimum_met,
            "initial_reliability_met": reliability_met,
            "ideal_sample_met": ideal_met,
        },
        "decision": {
            "ready_for_wave1_selected_panel_research": structural_ready,
            "ready_for_expected_minutes_accuracy_audit": minimum_met,
            "ready_for_injury_feature_walk_forward_holdout": False,
            "ready_for_model_training": False,
            "ready_for_probability_adjustment": False,
            "ready_for_betting_edge_claim": False,
            "reason": (
                "Wave 1 passed structural point-in-time QA and reached the independent-game gate for the Expected Minutes accuracy audit. Holdout remains blocked until that audit is completed."
                if minimum_met
                else "Wave 1 passed structural QA but did not reach the minimum independent-game gate for the Expected Minutes accuracy audit."
                if structural_ready
                else "Wave 1 failed one or more structural point-in-time feature gates."
            ),
        },
        "guardrails": {
            "selected_rows_per_game_maximum": 1,
            "multiple_snapshots_are_independent_games": False,
            "minimum_sample_gate_directly_enables_model": False,
            "expected_minutes_audit_required_before_holdout": True,
            "holdout_required_before_model_activation": True,
            "player_level_rows_retained_in_artifact": False,
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "wave1-injury-feature-backfill-audit.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def self_test(output_dir: Path) -> None:
    with TemporaryDirectory(prefix="nbavl-wave1-feature-audit-") as temp_name:
        root = Path(temp_name)
        overlap = {"coverage": {"overlap_reports": 20, "overlap_dates": 10}, "decision": {"ready_for_wave1_feature_pipeline": True}}
        schedule = {"coverage": {"snapshot_games": 120}, "quality": {"game_match_rate": 1.0, "unmatched_games": 0, "duplicate_gold_schedule_keys": 0}}
        identity = {"coverage": {"snapshot_rows": 1000, "matched_player_rows": 990}, "quality": {"player_match_rate": 0.99, "high_confidence_match_rate": 0.99, "ambiguous_player_rows": 0, "unmatched_player_rows": 10}, "guardrails": {"fuzzy_edit_distance_matching_used": False}}
        values = {"coverage": {"expected_minutes_rows": 920, "player_impact_rows": 920, "expected_minutes_coverage": 0.92, "player_impact_coverage": 0.92}, "quality": {"strict_prior_date_violations": 0, "same_day_source_rows_excluded": 100, "future_source_rows_excluded": 1000}, "guardrails": {"same_day_rows_allowed": False, "future_rows_allowed": False}}
        features = {"coverage": {"long_matchup_snapshot_rows": 150, "independent_games": 120}, "quality": {"non_pregame_observations": 0, "duplicate_snapshot_rows": 0}, "decision": {"ready_for_predeclared_snapshot_selection": True}}
        reconciliation = {"coverage": {"reconciled_matchup_snapshot_rows": 160, "independent_games": 120}, "quality": {"reconciliation_errors": 0, "original_team_rows_without_ledger": 0, "matchup_side_errors": 0}, "decision": {"ready_for_predeclared_snapshot_selection": True}}
        selection = {"coverage": {"independent_games_selected": 105, "games_without_primary_selection": 15, "primary_selection_rate": 0.875, "rejection_reason_counts": {}}, "quality": {"outcomes_or_market_prices_used_for_selection": False, "duplicate_selected_independent_games": 0}, "sample_size": {"minimum_activation_independent_games": 100, "initial_reliability_independent_games": 300, "ideal_independent_games": 500}, "decision": {"ready_for_selected_panel_research": True}}
        selected = [{"historical_game_id": f"g{index}"} for index in range(105)]
        report = audit(overlap, schedule, schedule, identity, values, features, reconciliation, selection, selected, root, output_dir)
    assert report["decision"]["ready_for_wave1_selected_panel_research"] is True, report
    assert report["decision"]["ready_for_expected_minutes_accuracy_audit"] is True, report
    assert report["decision"]["ready_for_injury_feature_walk_forward_holdout"] is False, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--overlap-report", type=Path)
    parser.add_argument("--player-schedule-report", type=Path)
    parser.add_argument("--team-schedule-report", type=Path)
    parser.add_argument("--identity-report", type=Path)
    parser.add_argument("--player-value-report", type=Path)
    parser.add_argument("--feature-report", type=Path)
    parser.add_argument("--reconciliation-report", type=Path)
    parser.add_argument("--selection-report", type=Path)
    parser.add_argument("--selected-csv", type=Path)
    parser.add_argument("--sensitive-root", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("Wave 1 injury feature audit self-test passed")
        return
    required = (
        args.overlap_report,
        args.player_schedule_report,
        args.team_schedule_report,
        args.identity_report,
        args.player_value_report,
        args.feature_report,
        args.reconciliation_report,
        args.selection_report,
        args.selected_csv,
    )
    if any(value is None for value in required):
        parser.error("all upstream reports and selected CSV are required")
    report = audit(
        read_json(args.overlap_report),
        read_json(args.player_schedule_report),
        read_json(args.team_schedule_report),
        read_json(args.identity_report),
        read_json(args.player_value_report),
        read_json(args.feature_report),
        read_json(args.reconciliation_report),
        read_json(args.selection_report),
        read_csv(args.selected_csv),
        args.sensitive_root,
        args.output_dir,
    )
    print(json.dumps(report["decision"], indent=2))
    if not report["decision"]["ready_for_wave1_selected_panel_research"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
