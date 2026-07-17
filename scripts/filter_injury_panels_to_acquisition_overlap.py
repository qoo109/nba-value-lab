#!/usr/bin/env python3
"""Filter player and team injury panels to report times that succeeded in both pipelines.

Player rows remain temporary and may contain public player names. Aggregate reports and the
team-level panel are safe to retain. The filter never reads outcomes or market prices.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from zoneinfo import ZoneInfo

VERSION = "injury-acquisition-overlap-filter-v1"
ET = ZoneInfo("America/New_York")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def parse_timestamp(value: Any) -> datetime:
    text = str(value or "").strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"timestamp must include timezone: {value!r}")
    return parsed.astimezone(timezone.utc)


def canonical_timestamp(value: Any) -> str:
    return parse_timestamp(value).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def source_index(
    rows: list[dict[str, str]],
    observed_field: str,
) -> tuple[dict[str, dict[str, str]], int, list[str]]:
    output: dict[str, dict[str, str]] = {}
    duplicates = 0
    errors: list[str] = []
    for row in rows:
        requested = str(row.get("requested_report_time", "")).strip()
        observed = str(row.get(observed_field, "")).strip()
        if not requested or not observed:
            errors.append("source index row missing requested or observed timestamp")
            continue
        if requested in output:
            duplicates += 1
        item = dict(row)
        item["canonical_observed_at"] = canonical_timestamp(observed)
        output[requested] = item
    return output, duplicates, errors


def filter_panels(
    player_rows: list[dict[str, str]],
    player_sources: list[dict[str, str]],
    team_rows: list[dict[str, str]],
    team_sources: list[dict[str, str]],
    output_dir: Path,
    minimum_overlap_reports: int = 18,
    minimum_overlap_dates: int = 8,
) -> dict[str, Any]:
    player_index, duplicate_player_sources, player_source_errors = source_index(
        player_sources, "official_report_time"
    )
    team_index, duplicate_team_sources, team_source_errors = source_index(
        team_sources, "observed_at"
    )
    overlap_requested = sorted(set(player_index) & set(team_index), key=parse_timestamp)
    overlap_records: list[dict[str, Any]] = []
    observed_mismatches = 0
    allowed_observed: set[str] = set()
    for requested in overlap_requested:
        player = player_index[requested]
        team = team_index[requested]
        player_observed = player["canonical_observed_at"]
        team_observed = team["canonical_observed_at"]
        mismatch = player_observed != team_observed
        observed_mismatches += int(mismatch)
        if not mismatch:
            allowed_observed.add(player_observed)
        local = parse_timestamp(requested).astimezone(ET)
        overlap_records.append({
            "requested_report_time": requested,
            "report_date_et": local.date().isoformat(),
            "slot_et": local.strftime("%H:%M"),
            "player_observed_at": player_observed,
            "team_observed_at": team_observed,
            "observed_at_match": int(not mismatch),
            "player_source_url": str(player.get("source_url", "")),
            "player_source_file_sha256": str(player.get("source_file_sha256", "")),
            "team_source_url": str(team.get("source_url", "")),
            "team_source_file_sha256": str(team.get("source_file_sha256", "")),
        })

    filtered_player = [
        row for row in player_rows
        if canonical_timestamp(row.get("observed_at")) in allowed_observed
    ]
    filtered_team = [
        row for row in team_rows
        if canonical_timestamp(row.get("observed_at")) in allowed_observed
    ]
    filtered_player.sort(key=lambda row: (
        canonical_timestamp(row.get("observed_at")),
        str(row.get("game_id", "")),
        str(row.get("team_abbr", "")),
        str(row.get("snapshot_record_id", "")),
    ))
    filtered_team.sort(key=lambda row: (
        canonical_timestamp(row.get("observed_at")),
        str(row.get("game_id", "")),
        str(row.get("team_abbr", "")),
    ))

    player_snapshot_ids = [str(row.get("snapshot_record_id", "")).strip() for row in filtered_player]
    duplicate_player_rows = len(player_snapshot_ids) - len(set(player_snapshot_ids))
    team_keys = [
        (
            canonical_timestamp(row.get("observed_at")),
            str(row.get("game_id", "")).strip(),
            str(row.get("team_abbr", "")).strip(),
        )
        for row in filtered_team
    ]
    duplicate_team_rows = len(team_keys) - len(set(team_keys))
    player_observed = {canonical_timestamp(row.get("observed_at")) for row in filtered_player}
    team_observed = {canonical_timestamp(row.get("observed_at")) for row in filtered_team}
    missing_player_observed = sorted(allowed_observed - player_observed)
    missing_team_observed = sorted(allowed_observed - team_observed)
    outside_player_rows = sum(
        canonical_timestamp(row.get("observed_at")) not in allowed_observed for row in filtered_player
    )
    outside_team_rows = sum(
        canonical_timestamp(row.get("observed_at")) not in allowed_observed for row in filtered_team
    )
    overlap_dates = sorted({parse_timestamp(value).astimezone(ET).date().isoformat() for value in overlap_requested})
    player_games = {str(row.get("game_id", "")).strip() for row in filtered_player if row.get("game_id")}
    team_games = {str(row.get("game_id", "")).strip() for row in filtered_team if row.get("game_id")}
    status_counts = Counter(
        str(row.get("submission_status", "")).strip()
        for row in filtered_team
        if str(row.get("submission_status", "")).strip()
    )

    ready = (
        len(overlap_requested) >= minimum_overlap_reports
        and len(overlap_dates) >= minimum_overlap_dates
        and observed_mismatches == 0
        and duplicate_player_sources == 0
        and duplicate_team_sources == 0
        and duplicate_player_rows == 0
        and duplicate_team_rows == 0
        and not player_source_errors
        and not team_source_errors
        and not missing_player_observed
        and not missing_team_observed
        and outside_player_rows == 0
        and outside_team_rows == 0
        and bool(filtered_player)
        and bool(filtered_team)
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(
        output_dir / "overlap-player-injury-panel.csv",
        filtered_player,
        list(filtered_player[0]) if filtered_player else [],
    )
    write_csv(
        output_dir / "overlap-team-submission-panel.csv",
        filtered_team,
        list(filtered_team[0]) if filtered_team else [],
    )
    write_csv(
        output_dir / "overlap-report-index.csv",
        overlap_records,
        list(overlap_records[0]) if overlap_records else [],
    )
    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "thresholds": {
            "minimum_overlap_reports": minimum_overlap_reports,
            "minimum_overlap_dates": minimum_overlap_dates,
        },
        "coverage": {
            "player_successful_reports": len(player_index),
            "team_successful_reports": len(team_index),
            "overlap_reports": len(overlap_requested),
            "overlap_dates": len(overlap_dates),
            "filtered_player_rows": len(filtered_player),
            "filtered_team_rows": len(filtered_team),
            "player_ingestion_games": len(player_games),
            "team_ingestion_games": len(team_games),
            "team_submission_status_counts": dict(sorted(status_counts.items())),
        },
        "quality": {
            "duplicate_player_source_times": duplicate_player_sources,
            "duplicate_team_source_times": duplicate_team_sources,
            "player_source_errors": player_source_errors,
            "team_source_errors": team_source_errors,
            "observed_at_mismatches": observed_mismatches,
            "duplicate_filtered_player_rows": duplicate_player_rows,
            "duplicate_filtered_team_rows": duplicate_team_rows,
            "missing_player_overlap_observed_at": missing_player_observed,
            "missing_team_overlap_observed_at": missing_team_observed,
            "outside_overlap_player_rows": outside_player_rows,
            "outside_overlap_team_rows": outside_team_rows,
            "outcomes_or_market_prices_used": False,
        },
        "decision": {
            "ready_for_wave1_feature_pipeline": ready,
            "ready_for_model_training": False,
            "ready_for_probability_adjustment": False,
            "ready_for_betting_edge_claim": False,
            "reason": (
                "Player and team panels were restricted to the predeclared acquisition-success intersection."
                if ready else "The acquisition overlap failed one or more structural gates."
            ),
        },
        "guardrails": {
            "player_only_success_times_allowed": False,
            "team_only_success_times_allowed": False,
            "failed_registry_times_replaced": False,
            "player_panel_is_temporary": True,
            "multiple_snapshots_are_independent_games": False,
        },
    }
    (output_dir / "overlap-filter-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def self_test(output_dir: Path) -> None:
    with TemporaryDirectory(prefix="nbavl-overlap-filter-"):
        times = [
            "2024-01-01T08:30:00-05:00",
            "2024-01-01T13:30:00-05:00",
            "2024-01-15T08:30:00-05:00",
        ]
        observed = [canonical_timestamp(value) for value in times]
        player_sources = [
            {"requested_report_time": times[0], "official_report_time": observed[0], "source_url": "https://p/0", "source_file_sha256": "1" * 64},
            {"requested_report_time": times[1], "official_report_time": observed[1], "source_url": "https://p/1", "source_file_sha256": "2" * 64},
        ]
        team_sources = [
            {"requested_report_time": times[1], "observed_at": observed[1], "source_url": "https://t/1", "source_file_sha256": "3" * 64},
            {"requested_report_time": times[2], "observed_at": observed[2], "source_url": "https://t/2", "source_file_sha256": "4" * 64},
        ]
        player_rows = [
            {"snapshot_record_id": "s0", "observed_at": observed[0], "game_id": "g0", "team_abbr": "AAA", "player_name": "A"},
            {"snapshot_record_id": "s1", "observed_at": observed[1], "game_id": "g1", "team_abbr": "BBB", "player_name": "B"},
        ]
        team_rows = [
            {"observed_at": observed[1], "game_id": "g1", "team_abbr": "BBB", "submission_status": "SUBMITTED_WITH_PLAYER_ROWS"},
            {"observed_at": observed[2], "game_id": "g2", "team_abbr": "CCC", "submission_status": "NOT_YET_SUBMITTED"},
        ]
        report = filter_panels(
            player_rows,
            player_sources,
            team_rows,
            team_sources,
            output_dir,
            minimum_overlap_reports=1,
            minimum_overlap_dates=1,
        )
    assert report["decision"]["ready_for_wave1_feature_pipeline"] is True, report
    assert report["coverage"]["overlap_reports"] == 1, report
    assert report["coverage"]["filtered_player_rows"] == 1, report
    assert report["coverage"]["filtered_team_rows"] == 1, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--player-panel", type=Path)
    parser.add_argument("--player-source-index", type=Path)
    parser.add_argument("--team-panel", type=Path)
    parser.add_argument("--team-source-index", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--minimum-overlap-reports", type=int, default=18)
    parser.add_argument("--minimum-overlap-dates", type=int, default=8)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("injury acquisition overlap filter self-test passed")
        return
    required = (args.player_panel, args.player_source_index, args.team_panel, args.team_source_index)
    if any(value is None for value in required):
        parser.error("player/team panels and source indexes are required")
    report = filter_panels(
        read_csv(args.player_panel),
        read_csv(args.player_source_index),
        read_csv(args.team_panel),
        read_csv(args.team_source_index),
        args.output_dir,
        minimum_overlap_reports=args.minimum_overlap_reports,
        minimum_overlap_dates=args.minimum_overlap_dates,
    )
    print(json.dumps(report["decision"], indent=2))
    if not report["decision"]["ready_for_wave1_feature_pipeline"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
