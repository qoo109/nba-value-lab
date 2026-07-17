#!/usr/bin/env python3
"""Apply the registered single-report Team Injury Burden v1 pilot gate.

The generic builder uses a conservative 70% feature-ready rate. This pilot gate preserves that
original decision, then evaluates the registered live-pilot requirement: at least seven ready
matchups, at least 60% ready coverage, and at least 80% complete snapshot coverage.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "team-injury-burden-pilot-gate-v1"
MIN_GAMES = 8
MIN_COMPLETE_SNAPSHOT_RATE = 0.80
MIN_FEATURE_READY_MATCHUPS = 7
MIN_FEATURE_READY_RATE = 0.60


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def apply_gate(report_path: Path, gate_report_path: Path | None = None) -> dict[str, Any]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    coverage = report.get("coverage", {})
    quality = report.get("quality", {})
    original_decision = dict(report.get("decision", {}))

    checks = {
        "minimum_games": int(coverage.get("games", 0)) >= MIN_GAMES,
        "minimum_complete_snapshot_rate": (
            float(coverage.get("complete_snapshot_matchup_rate", 0.0))
            >= MIN_COMPLETE_SNAPSHOT_RATE
        ),
        "minimum_feature_ready_matchups": (
            int(coverage.get("feature_ready_matchups", 0)) >= MIN_FEATURE_READY_MATCHUPS
        ),
        "minimum_feature_ready_rate": (
            float(coverage.get("feature_ready_matchup_rate", 0.0))
            >= MIN_FEATURE_READY_RATE
        ),
        "no_duplicate_game_maps": int(quality.get("duplicate_game_map_rows", 0)) == 0,
        "no_duplicate_identity_snapshots": (
            int(quality.get("duplicate_identity_snapshot_rows", 0)) == 0
        ),
        "no_duplicate_player_values": (
            int(quality.get("duplicate_player_value_snapshot_rows", 0)) == 0
        ),
        "no_strict_prior_violations": (
            int(quality.get("strict_prior_date_violations", 0)) == 0
        ),
        "no_unknown_statuses": int(quality.get("unknown_status_rows", 0)) == 0,
        "no_numeric_errors": int(quality.get("numeric_errors", 0)) == 0,
        "missing_teams_not_zero_filled": (
            quality.get("missing_teams_are_not_treated_as_zero_burden") is True
        ),
        "unknown_player_values_not_zero_filled": (
            quality.get("unknown_player_values_are_not_imputed_as_zero") is True
        ),
    }
    ready = all(checks.values())
    gate = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "thresholds": {
            "minimum_games": MIN_GAMES,
            "minimum_complete_snapshot_matchup_rate": MIN_COMPLETE_SNAPSHOT_RATE,
            "minimum_feature_ready_matchups": MIN_FEATURE_READY_MATCHUPS,
            "minimum_feature_ready_matchup_rate": MIN_FEATURE_READY_RATE,
        },
        "observed": {
            "games": int(coverage.get("games", 0)),
            "complete_snapshot_matchups": int(coverage.get("complete_snapshot_matchups", 0)),
            "complete_snapshot_matchup_rate": float(
                coverage.get("complete_snapshot_matchup_rate", 0.0)
            ),
            "feature_ready_matchups": int(coverage.get("feature_ready_matchups", 0)),
            "feature_ready_matchup_rate": float(
                coverage.get("feature_ready_matchup_rate", 0.0)
            ),
        },
        "checks": checks,
        "ready_for_team_injury_feature_experiment": ready,
        "ready_for_model_training": False,
        "ready_for_betting_edge_claim": False,
        "original_builder_decision": original_decision,
    }

    report["pilot_gate"] = gate
    report["decision"] = {
        "ready_for_team_injury_feature_experiment": ready,
        "ready_for_model_training": False,
        "ready_for_betting_edge_claim": False,
        "reason": (
            "Registered single-report pilot gate passed; multi-report coverage and season "
            "holdout evaluation remain required."
            if ready
            else "Registered single-report pilot gate did not pass."
        ),
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if gate_report_path:
        gate_report_path.write_text(json.dumps(gate, indent=2) + "\n", encoding="utf-8")
    return gate


def self_test(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "report.json"
    report_path.write_text(
        json.dumps({
            "coverage": {
                "games": 11,
                "complete_snapshot_matchups": 9,
                "complete_snapshot_matchup_rate": 9 / 11,
                "feature_ready_matchups": 7,
                "feature_ready_matchup_rate": 7 / 11,
            },
            "quality": {
                "duplicate_game_map_rows": 0,
                "duplicate_identity_snapshot_rows": 0,
                "duplicate_player_value_snapshot_rows": 0,
                "strict_prior_date_violations": 0,
                "unknown_status_rows": 0,
                "numeric_errors": 0,
                "missing_teams_are_not_treated_as_zero_burden": True,
                "unknown_player_values_are_not_imputed_as_zero": True,
            },
            "decision": {
                "ready_for_team_injury_feature_experiment": False,
                "ready_for_model_training": False,
            },
        }),
        encoding="utf-8",
    )
    gate = apply_gate(report_path, output_dir / "gate.json")
    assert gate["ready_for_team_injury_feature_experiment"] is True, gate
    updated = json.loads(report_path.read_text())
    assert updated["pilot_gate"]["original_builder_decision"][
        "ready_for_team_injury_feature_experiment"
    ] is False
    assert updated["decision"]["ready_for_model_training"] is False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path)
    parser.add_argument("--gate-report", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.self_test:
        if not args.output_dir:
            parser.error("--output-dir is required with --self-test")
        self_test(args.output_dir)
        print("team injury pilot gate self-test passed")
        return
    if not args.report:
        parser.error("--report is required")
    gate = apply_gate(args.report, args.gate_report)
    print(json.dumps(gate, indent=2))
    if not gate["ready_for_team_injury_feature_experiment"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
