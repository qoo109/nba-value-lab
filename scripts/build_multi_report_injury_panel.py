#!/usr/bin/env python3
"""Build a temporary multi-report panel from official NBA injury PDFs.

Raw PDFs are deleted by the single-report importer. Player-level normalized rows are written only
for downstream in-workflow joins and must be deleted before Artifact upload. The retained source
index and QA report contain aggregate coverage and provenance only.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from import_official_nba_injury_report import ET, parse_report_time, run as import_report

VERSION = "multi-report-injury-panel-v1"
MIN_SUCCESSFUL_REPORTS = 4
MIN_UNIQUE_REPORT_DATES = 3
MIN_NORMALIZED_ROWS = 300
MAX_FAILURE_RATE = 0.50


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_report_times(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload = payload.get("report_times")
    if not isinstance(payload, list) or not payload:
        raise ValueError("report-times JSON must be a non-empty array or contain report_times")
    values = [str(value).strip() for value in payload if str(value).strip()]
    if len(values) != len(set(values)):
        raise ValueError("report-times JSON contains duplicate timestamps")
    for value in values:
        parse_report_time(value)
    return values


def slug_for_time(value: str) -> str:
    parsed = parse_report_time(value).astimezone(ET)
    return parsed.strftime("%Y%m%d-%H%M-ET")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def summarize(
    requested_times: list[str],
    successful: list[dict[str, Any]],
    failures: list[dict[str, str]],
    normalized_rows: list[dict[str, str]],
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    snapshot_ids = [str(row.get("snapshot_record_id", "")).strip() for row in normalized_rows]
    duplicate_snapshot_rows = len(snapshot_ids) - len(set(snapshot_ids))
    report_times = sorted({str(row.get("observed_at", "")) for row in normalized_rows if row.get("observed_at")})
    game_ids = {str(row.get("game_id", "")) for row in normalized_rows if row.get("game_id")}
    teams = {str(row.get("team_abbr", "")) for row in normalized_rows if row.get("team_abbr")}
    status_counts = Counter(
        str(row.get("availability_status", "")).strip()
        for row in normalized_rows
        if str(row.get("availability_status", "")).strip()
    )
    report_dates = {
        parse_report_time(item["requested_report_time"]).date().isoformat()
        for item in successful
    }
    source_urls = [item["source_url"] for item in successful]
    duplicate_source_urls = len(source_urls) - len(set(source_urls))
    source_hashes = [item["source_file_sha256"] for item in successful]
    duplicate_source_hashes = len(source_hashes) - len(set(source_hashes))
    failure_rate = len(failures) / len(requested_times) if requested_times else 1.0

    source_fields = [
        "requested_report_time", "official_report_time", "report_date_et", "source_url",
        "source_file_sha256", "source_size_bytes", "validated_rows", "games", "teams",
        "players", "not_yet_submitted_team_rows", "ready",
    ]
    write_csv(output_dir / "multi-report-source-index.csv", successful, source_fields)

    ready = (
        len(successful) >= MIN_SUCCESSFUL_REPORTS
        and len(report_dates) >= MIN_UNIQUE_REPORT_DATES
        and len(normalized_rows) >= MIN_NORMALIZED_ROWS
        and failure_rate <= MAX_FAILURE_RATE
        and duplicate_snapshot_rows == 0
        and duplicate_source_urls == 0
        and all(item["ready"] for item in successful)
    )
    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "thresholds": {
            "minimum_successful_reports": MIN_SUCCESSFUL_REPORTS,
            "minimum_unique_report_dates": MIN_UNIQUE_REPORT_DATES,
            "minimum_normalized_rows": MIN_NORMALIZED_ROWS,
            "maximum_failure_rate": MAX_FAILURE_RATE,
        },
        "coverage": {
            "requested_reports": len(requested_times),
            "successful_reports": len(successful),
            "failed_reports": len(failures),
            "failure_rate": round(failure_rate, 6),
            "unique_report_dates": len(report_dates),
            "report_dates_et": sorted(report_dates),
            "normalized_player_rows": len(normalized_rows),
            "unique_snapshot_record_ids": len(set(snapshot_ids)),
            "unique_report_times": len(report_times),
            "unique_games": len(game_ids),
            "unique_teams": len(teams),
            "status_counts": dict(sorted(status_counts.items())),
        },
        "quality": {
            "duplicate_snapshot_rows": duplicate_snapshot_rows,
            "duplicate_source_urls": duplicate_source_urls,
            "duplicate_source_hashes": duplicate_source_hashes,
            "failed_report_examples": failures[:20],
            "all_successful_reports_passed_single_report_gate": all(
                item["ready"] for item in successful
            ),
            "raw_pdf_rows_retained": False,
            "normalized_player_rows_must_be_deleted_before_artifact_upload": True,
            "retained_source_index_contains_player_names": False,
            "retained_source_index_contains_injury_reasons": False,
        },
        "decision": {
            "ready_for_multi_report_identity_value_join": ready,
            "ready_for_model_training": False,
            "ready_for_betting_edge_claim": False,
            "reason": (
                "Multi-report source panel passed ingestion and provenance gates; player identity, "
                "prior-only value joins, and holdout testing remain required."
                if ready
                else "Multi-report source panel did not meet the registered ingestion gate."
            ),
        },
        "guardrails": {
            "official_publication_timestamp_used": True,
            "actual_retrieval_timestamp_stored_per_report": True,
            "missing_reports_are_recorded_not_imputed": True,
            "failed_reports_do_not_create_empty_healthy_team_rows": True,
            "player_level_panel_is_temporary": True,
            "model_activation_from_ingestion_only": False,
        },
    }
    (output_dir / "multi-report-injury-panel-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def build(report_times_path: Path, output_dir: Path) -> dict[str, Any]:
    requested_times = read_report_times(report_times_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    reports_root = output_dir / "reports"
    reports_root.mkdir(parents=True, exist_ok=True)
    successful: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    combined_rows: list[dict[str, str]] = []
    fieldnames: list[str] | None = None

    for requested in requested_times:
        report_dir = reports_root / slug_for_time(requested)
        try:
            report = import_report(requested, report_dir, retain_normalized=True)
            normalized_path = report_dir / "validation" / "injury-lineup-snapshots-normalized.csv"
            if not normalized_path.exists():
                raise FileNotFoundError("single-report normalized CSV was not produced")
            rows = read_csv(normalized_path)
            if fieldnames is None and rows:
                fieldnames = list(rows[0])
            combined_rows.extend(rows)
            source = report["source"]
            coverage = report["coverage"]
            successful.append({
                "requested_report_time": requested,
                "official_report_time": source["report_time"],
                "report_date_et": parse_report_time(requested).date().isoformat(),
                "source_url": source["report_url"],
                "source_file_sha256": source["source_file_sha256"],
                "source_size_bytes": source["source_size_bytes"],
                "validated_rows": coverage["validated_rows"],
                "games": coverage["games"],
                "teams": coverage["teams"],
                "players": coverage["players"],
                "not_yet_submitted_team_rows": coverage["not_yet_submitted_team_rows"],
                "ready": bool(report["decision"]["ready_for_manual_official_pdf_pilot"]),
            })
        except Exception as exc:
            failures.append({
                "requested_report_time": requested,
                "error_type": type(exc).__name__,
                "error": re.sub(r"\s+", " ", str(exc)).strip()[:1000],
            })

    combined_rows.sort(
        key=lambda row: (
            str(row.get("observed_at", "")),
            str(row.get("game_id", "")),
            str(row.get("team_abbr", "")),
            str(row.get("snapshot_record_id", "")),
        )
    )
    if fieldnames is None:
        fieldnames = [
            "snapshot_record_id", "record_type", "game_id", "commence_time", "team_abbr",
            "opponent_abbr", "is_home", "player_id", "player_name", "availability_status",
            "lineup_role", "reason_category", "reason_text", "observed_at",
            "source_report_time", "source_provider", "source_url", "source_file_sha256",
            "source_status_raw", "source_lineup_role_raw", "prior_expected_minutes",
            "prior_impact_estimate", "player_value_asof", "player_value_version",
        ]
    write_csv(
        output_dir / "multi-report-injury-panel-normalized.csv",
        combined_rows,
        fieldnames,
    )
    return summarize(requested_times, successful, failures, combined_rows, output_dir)


def self_test(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    requested = [
        "2023-12-18T08:30:00-05:00",
        "2023-12-18T13:30:00-05:00",
        "2024-01-15T08:30:00-05:00",
        "2024-02-12T08:30:00-05:00",
    ]
    successful = []
    rows = []
    for index, value in enumerate(requested):
        parsed = parse_report_time(value)
        successful.append({
            "requested_report_time": value,
            "official_report_time": parsed.astimezone(timezone.utc).isoformat(),
            "report_date_et": parsed.date().isoformat(),
            "source_url": f"https://example.test/report-{index}.pdf",
            "source_file_sha256": f"{index + 1:064x}",
            "source_size_bytes": 1000,
            "validated_rows": 100,
            "games": 10,
            "teams": 20,
            "players": 100,
            "not_yet_submitted_team_rows": 0,
            "ready": True,
        })
        for row_index in range(100):
            rows.append({
                "snapshot_record_id": f"{index}-{row_index}",
                "game_id": f"g-{index}-{row_index // 10}",
                "team_abbr": "ATL",
                "availability_status": "OUT",
                "observed_at": parsed.astimezone(timezone.utc).isoformat(),
            })
    report = summarize(requested, successful, [], rows, output_dir)
    assert report["decision"]["ready_for_multi_report_identity_value_join"] is True, report
    assert report["coverage"]["successful_reports"] == 4, report
    assert report["quality"]["duplicate_snapshot_rows"] == 0, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-times", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("multi-report injury panel self-test passed")
        return
    if not args.report_times:
        parser.error("--report-times is required unless --self-test is used")
    report = build(args.report_times, args.output_dir)
    print(json.dumps(report["decision"], indent=2))
    if not report["decision"]["ready_for_multi_report_identity_value_join"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
