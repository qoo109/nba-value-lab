#!/usr/bin/env python3
"""Audit report times that are both player-single-report-ready and team-pipeline-successful.

The multi-report player importer records downloads/parses in its source index even when an
individual report does not pass the stricter single-report readiness gate. This audit keeps those
states separate and writes a filtered player source index for downstream feature backfills.
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

VERSION = "ready-injury-report-overlap-audit-v1"
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


def is_true(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes"}


def parse_timestamp(value: Any) -> datetime:
    text = str(value or "").strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"timestamp must include timezone: {value!r}")
    return parsed.astimezone(timezone.utc)


def unique_index(rows: list[dict[str, str]]) -> tuple[dict[str, dict[str, str]], int, list[str]]:
    output: dict[str, dict[str, str]] = {}
    duplicates = 0
    errors: list[str] = []
    for number, row in enumerate(rows, 2):
        value = str(row.get("requested_report_time", "")).strip()
        if not value:
            errors.append(f"row {number} missing requested_report_time")
            continue
        try:
            parse_timestamp(value)
        except ValueError as exc:
            errors.append(f"row {number}: {exc}")
            continue
        if value in output:
            duplicates += 1
        output[value] = row
    return output, duplicates, errors


def audit(
    player_sources: list[dict[str, str]],
    team_sources: list[dict[str, str]],
    output_dir: Path,
    minimum_overlap_reports: int = 18,
    minimum_overlap_dates: int = 8,
) -> dict[str, Any]:
    player_all, duplicate_player, player_errors = unique_index(player_sources)
    team_all, duplicate_team, team_errors = unique_index(team_sources)
    player_ready = {
        timestamp: row for timestamp, row in player_all.items()
        if is_true(row.get("ready"))
    }
    player_not_ready = sorted(set(player_all) - set(player_ready), key=parse_timestamp)
    overlap = sorted(set(player_ready) & set(team_all), key=parse_timestamp)
    overlap_dates = sorted({parse_timestamp(value).astimezone(ET).date().isoformat() for value in overlap})
    player_ready_only = sorted(set(player_ready) - set(team_all), key=parse_timestamp)
    team_only = sorted(set(team_all) - set(player_ready), key=parse_timestamp)

    duplicate_player_urls = len(player_sources) - len({
        str(row.get("source_url", "")).strip()
        for row in player_sources if str(row.get("source_url", "")).strip()
    })
    duplicate_team_urls = len(team_sources) - len({
        str(row.get("source_url", "")).strip()
        for row in team_sources if str(row.get("source_url", "")).strip()
    })
    ready = (
        len(overlap) >= minimum_overlap_reports
        and len(overlap_dates) >= minimum_overlap_dates
        and duplicate_player == 0
        and duplicate_team == 0
        and duplicate_player_urls == 0
        and duplicate_team_urls == 0
        and not player_errors
        and not team_errors
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    ready_player_rows = [player_ready[value] for value in sorted(player_ready, key=parse_timestamp)]
    write_csv(
        output_dir / "ready-player-source-index.csv",
        ready_player_rows,
        list(ready_player_rows[0]) if ready_player_rows else [],
    )
    overlap_rows = []
    for value in overlap:
        local = parse_timestamp(value).astimezone(ET)
        player = player_ready[value]
        team = team_all[value]
        overlap_rows.append({
            "requested_report_time": value,
            "report_date_et": local.date().isoformat(),
            "slot_et": local.strftime("%H:%M"),
            "player_ready": 1,
            "team_success": 1,
            "player_source_url": str(player.get("source_url", "")),
            "player_source_file_sha256": str(player.get("source_file_sha256", "")),
            "team_source_url": str(team.get("source_url", "")),
            "team_source_file_sha256": str(team.get("source_file_sha256", "")),
        })
    write_csv(
        output_dir / "ready-overlap-report-index.csv",
        overlap_rows,
        list(overlap_rows[0]) if overlap_rows else [],
    )
    (output_dir / "ready-overlap-report-times.json").write_text(
        json.dumps({
            "schema_version": VERSION,
            "report_times": overlap,
            "notes": [
                "Only player reports with ready=true and successful team reports are included.",
                "This file is derived from the fixed acquisition registry and does not replace failed times."
            ],
        }, indent=2) + "\n",
        encoding="utf-8",
    )
    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "thresholds": {
            "minimum_ready_overlap_reports": minimum_overlap_reports,
            "minimum_ready_overlap_dates": minimum_overlap_dates,
        },
        "coverage": {
            "player_parsed_reports": len(player_all),
            "player_single_report_ready": len(player_ready),
            "player_single_report_not_ready": len(player_not_ready),
            "team_successful_reports": len(team_all),
            "ready_overlap_reports": len(overlap),
            "ready_overlap_dates": len(overlap_dates),
        },
        "quality": {
            "duplicate_player_source_times": duplicate_player,
            "duplicate_team_source_times": duplicate_team,
            "duplicate_player_source_urls": duplicate_player_urls,
            "duplicate_team_source_urls": duplicate_team_urls,
            "player_source_errors": player_errors,
            "team_source_errors": team_errors,
            "player_not_ready_times": player_not_ready,
            "player_ready_without_team_success": player_ready_only,
            "team_success_without_player_ready": team_only,
            "failed_registry_times_replaced": False,
            "outcomes_or_market_prices_used": False,
        },
        "decision": {
            "ready_for_feature_backfill": ready,
            "ready_for_model_training": False,
            "ready_for_probability_adjustment": False,
            "ready_for_betting_edge_claim": False,
            "reason": (
                "The single-report-ready player and successful team source intersection passed its predeclared gate."
                if ready
                else "The ready source intersection failed one or more provenance or coverage gates."
            ),
        },
        "guardrails": {
            "player_ready_false_allowed_in_feature_pipeline": False,
            "player_only_success_allowed_in_feature_pipeline": False,
            "team_only_success_allowed_in_feature_pipeline": False,
            "multiple_publication_times_are_independent_games": False,
        },
    }
    (output_dir / "ready-overlap-audit.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def self_test(output_dir: Path) -> None:
    player = [
        {"requested_report_time": "2024-01-01T08:30:00-05:00", "ready": "True", "source_url": "https://p/1", "source_file_sha256": "1" * 64},
        {"requested_report_time": "2024-01-01T13:30:00-05:00", "ready": "False", "source_url": "https://p/2", "source_file_sha256": "2" * 64},
        {"requested_report_time": "2024-01-15T08:30:00-05:00", "ready": "True", "source_url": "https://p/3", "source_file_sha256": "3" * 64},
    ]
    team = [
        {"requested_report_time": "2024-01-01T08:30:00-05:00", "source_url": "https://t/1", "source_file_sha256": "4" * 64},
        {"requested_report_time": "2024-01-01T13:30:00-05:00", "source_url": "https://t/2", "source_file_sha256": "5" * 64},
        {"requested_report_time": "2024-01-15T08:30:00-05:00", "source_url": "https://t/3", "source_file_sha256": "6" * 64},
    ]
    report = audit(player, team, output_dir, minimum_overlap_reports=2, minimum_overlap_dates=2)
    assert report["decision"]["ready_for_feature_backfill"] is True, report
    assert report["coverage"]["player_parsed_reports"] == 3, report
    assert report["coverage"]["player_single_report_ready"] == 2, report
    assert report["coverage"]["ready_overlap_reports"] == 2, report
    assert report["quality"]["player_not_ready_times"] == ["2024-01-01T13:30:00-05:00"], report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--player-source-index", type=Path)
    parser.add_argument("--team-source-index", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--minimum-overlap-reports", type=int, default=18)
    parser.add_argument("--minimum-overlap-dates", type=int, default=8)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("ready injury report overlap audit self-test passed")
        return
    if not args.player_source_index or not args.team_source_index:
        parser.error("--player-source-index and --team-source-index are required")
    report = audit(
        read_csv(args.player_source_index),
        read_csv(args.team_source_index),
        args.output_dir,
        minimum_overlap_reports=args.minimum_overlap_reports,
        minimum_overlap_dates=args.minimum_overlap_dates,
    )
    print(json.dumps(report["decision"], indent=2))
    if not report["decision"]["ready_for_feature_backfill"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
