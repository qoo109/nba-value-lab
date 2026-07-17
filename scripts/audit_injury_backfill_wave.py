#!/usr/bin/env python3
"""Audit a systematic official NBA injury-report acquisition wave.

The audit consumes only aggregate ingestion reports, provenance indexes, and the team-level
submission panel. It never reads outcomes, market prices, player names, or injury reasons.
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

VERSION = "injury-backfill-wave-acquisition-audit-v1"
ET = ZoneInfo("America/New_York")
FORBIDDEN_PLAYER_FILENAMES = {
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


def local_timestamp(value: Any) -> datetime:
    return parse_timestamp(value).astimezone(ET)


def as_int(value: Any, default: int = 0) -> int:
    text = str(value or "").strip()
    if not text:
        return default
    return int(float(text))


def as_float(value: Any, default: float = 0.0) -> float:
    text = str(value or "").strip()
    if not text:
        return default
    return float(text)


def validate_registry(registry: dict[str, Any]) -> dict[str, Any]:
    times = registry.get("report_times")
    policy = registry.get("sampling_policy")
    gate = registry.get("acquisition_gate")
    errors: list[str] = []
    if not isinstance(times, list) or not times:
        raise ValueError("registry report_times must be a non-empty list")
    if not isinstance(policy, dict) or not isinstance(gate, dict):
        raise ValueError("registry requires sampling_policy and acquisition_gate objects")

    values = [str(value).strip() for value in times]
    duplicate_requested = len(values) - len(set(values))
    if duplicate_requested:
        errors.append(f"duplicate requested timestamps: {duplicate_requested}")

    parsed = [local_timestamp(value) for value in values]
    requested_dates = sorted({item.date().isoformat() for item in parsed})
    slots = sorted({item.strftime("%H:%M") for item in parsed})
    weekdays = sorted({item.strftime("%A") for item in parsed})
    dates = sorted({item.date() for item in parsed})
    date_gaps = [(later - earlier).days for earlier, later in zip(dates, dates[1:])]

    expected_count = as_int(policy.get("candidate_reports"), -1)
    expected_dates = as_int(policy.get("dates"), -1)
    expected_slots = sorted(str(value) for value in policy.get("official_slots_et", []))
    if expected_count != len(values):
        errors.append(f"candidate_reports={expected_count}, actual={len(values)}")
    if expected_dates != len(requested_dates):
        errors.append(f"dates={expected_dates}, actual={len(requested_dates)}")
    if expected_slots != slots:
        errors.append(f"official_slots_et={expected_slots}, actual={slots}")
    if weekdays != [str(policy.get("weekday", ""))]:
        errors.append(f"weekday policy mismatch: {weekdays}")
    if date_gaps and any(gap != 14 for gap in date_gaps):
        errors.append(f"calendar cadence is not consistently 14 days: {date_gaps}")
    if requested_dates[0] != str(policy.get("start_date", "")):
        errors.append("start_date does not match first requested date")
    if requested_dates[-1] != str(policy.get("end_date", "")):
        errors.append("end_date does not match last requested date")
    if str(policy.get("selection_basis", "")) != "calendar_only_before_outcome_or_market_join":
        errors.append("selection_basis is not the registered calendar-only policy")

    required_gate_fields = {
        "minimum_successful_player_reports",
        "minimum_successful_team_reports",
        "minimum_overlapping_successful_reports",
        "minimum_unique_successful_dates",
        "maximum_failure_rate_per_pipeline",
    }
    missing_gate = sorted(required_gate_fields - set(gate))
    if missing_gate:
        errors.append(f"acquisition gate missing fields: {missing_gate}")

    return {
        "requested_times": values,
        "requested_dates": requested_dates,
        "slots_et": slots,
        "weekdays": weekdays,
        "date_gaps_days": date_gaps,
        "duplicate_requested_timestamps": duplicate_requested,
        "errors": errors,
    }


def index_sources(rows: list[dict[str, str]]) -> tuple[dict[str, dict[str, str]], int, int]:
    indexed: dict[str, dict[str, str]] = {}
    duplicate_times = 0
    for row in rows:
        value = str(row.get("requested_report_time", "")).strip()
        if not value:
            continue
        if value in indexed:
            duplicate_times += 1
        indexed[value] = row
    urls = [str(row.get("source_url", "")).strip() for row in rows if row.get("source_url")]
    duplicate_urls = len(urls) - len(set(urls))
    return indexed, duplicate_times, duplicate_urls


def failure_index(report: dict[str, Any]) -> dict[str, dict[str, str]]:
    output: dict[str, dict[str, str]] = {}
    examples = report.get("quality", {}).get("failed_report_examples", [])
    if not isinstance(examples, list):
        return output
    for item in examples:
        if not isinstance(item, dict):
            continue
        value = str(item.get("requested_report_time", "")).strip()
        if value:
            output[value] = {
                "error_type": str(item.get("error_type", "")),
                "error": str(item.get("error", ""))[:500],
            }
    return output


def find_forbidden_files(root: Path | None) -> list[str]:
    if root is None or not root.exists():
        return []
    found = []
    for path in root.rglob("*"):
        if path.is_file() and path.name in FORBIDDEN_PLAYER_FILENAMES:
            found.append(str(path.relative_to(root)))
    return sorted(found)


def audit(
    registry: dict[str, Any],
    player_report: dict[str, Any],
    player_sources: list[dict[str, str]],
    team_report: dict[str, Any],
    team_sources: list[dict[str, str]],
    team_panel: list[dict[str, str]],
    sensitive_root: Path | None,
    output_dir: Path,
) -> dict[str, Any]:
    registry_qa = validate_registry(registry)
    requested = registry_qa["requested_times"]
    requested_set = set(requested)
    gate = registry["acquisition_gate"]

    player_index, duplicate_player_times, duplicate_player_urls = index_sources(player_sources)
    team_index, duplicate_team_times, duplicate_team_urls = index_sources(team_sources)
    player_failures = failure_index(player_report)
    team_failures = failure_index(team_report)

    player_success = set(player_index)
    team_success = set(team_index)
    overlap = player_success & team_success
    unexpected_player = sorted(player_success - requested_set)
    unexpected_team = sorted(team_success - requested_set)
    missing_player = sorted(requested_set - player_success)
    missing_team = sorted(requested_set - team_success)
    overlap_dates = sorted({local_timestamp(value).date().isoformat() for value in overlap})
    player_dates = sorted({local_timestamp(value).date().isoformat() for value in player_success})
    team_dates = sorted({local_timestamp(value).date().isoformat() for value in team_success})

    player_failure_rate = len(missing_player) / len(requested) if requested else 1.0
    team_failure_rate = len(missing_team) / len(requested) if requested else 1.0
    player_report_coverage = player_report.get("coverage", {})
    team_report_coverage = team_report.get("coverage", {})
    team_quality = team_report.get("quality", {})

    team_status_counts = Counter(
        str(row.get("submission_status", "")).strip()
        for row in team_panel
        if str(row.get("submission_status", "")).strip()
    )
    team_panel_times = {str(row.get("observed_at", "")).strip() for row in team_panel if row.get("observed_at")}
    team_panel_games = {str(row.get("game_id", "")).strip() for row in team_panel if row.get("game_id")}
    team_panel_conflicts = sum(as_int(row.get("submission_conflict")) for row in team_panel)
    forbidden_files = find_forbidden_files(sensitive_root)

    report_crosschecks = {
        "player_requested_matches_registry": as_int(player_report_coverage.get("requested_reports"), -1) == len(requested),
        "team_requested_matches_registry": as_int(team_report_coverage.get("requested_reports"), -1) == len(requested),
        "player_success_matches_source_index": as_int(player_report_coverage.get("successful_reports"), -1) == len(player_success),
        "team_success_matches_source_index": as_int(team_report_coverage.get("successful_reports"), -1) == len(team_success),
        "team_panel_rows_match_report": as_int(team_report_coverage.get("team_submission_rows"), -1) == len(team_panel),
        "team_panel_times_match_report": as_int(team_report_coverage.get("unique_report_times"), -1) == len(team_panel_times),
    }

    threshold_results = {
        "successful_player_reports": len(player_success) >= as_int(gate["minimum_successful_player_reports"]),
        "successful_team_reports": len(team_success) >= as_int(gate["minimum_successful_team_reports"]),
        "overlapping_successful_reports": len(overlap) >= as_int(gate["minimum_overlapping_successful_reports"]),
        "unique_overlapping_dates": len(overlap_dates) >= as_int(gate["minimum_unique_successful_dates"]),
        "player_failure_rate": player_failure_rate <= as_float(gate["maximum_failure_rate_per_pipeline"]),
        "team_failure_rate": team_failure_rate <= as_float(gate["maximum_failure_rate_per_pipeline"]),
        "unique_requested_timestamps": registry_qa["duplicate_requested_timestamps"] == 0,
        "zero_team_submission_conflicts": team_panel_conflicts == 0 and as_int(team_quality.get("submission_conflicts")) == 0,
        "no_unexpected_success_times": not unexpected_player and not unexpected_team,
        "no_duplicate_success_times": duplicate_player_times == 0 and duplicate_team_times == 0,
        "no_duplicate_source_urls": duplicate_player_urls == 0 and duplicate_team_urls == 0,
        "player_rows_removed_before_artifact": not forbidden_files,
        "registry_policy_valid": not registry_qa["errors"],
        "aggregate_report_crosschecks": all(report_crosschecks.values()),
    }
    ready = all(threshold_results.values())

    rows: list[dict[str, Any]] = []
    for value in requested:
        local = local_timestamp(value)
        player = player_index.get(value, {})
        team = team_index.get(value, {})
        player_error = player_failures.get(value, {})
        team_error = team_failures.get(value, {})
        rows.append({
            "requested_report_time": value,
            "report_date_et": local.date().isoformat(),
            "slot_et": local.strftime("%H:%M"),
            "player_pipeline_status": "SUCCESS" if value in player_success else "FAILED",
            "team_pipeline_status": "SUCCESS" if value in team_success else "FAILED",
            "overlap_success": int(value in overlap),
            "player_source_url": str(player.get("source_url", "")),
            "player_source_file_sha256": str(player.get("source_file_sha256", "")),
            "team_source_url": str(team.get("source_url", "")),
            "team_source_file_sha256": str(team.get("source_file_sha256", "")),
            "player_error_type": str(player_error.get("error_type", "")),
            "team_error_type": str(team_error.get("error_type", "")),
        })

    output_dir.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else []
    write_csv(output_dir / "injury-backfill-wave-report-index.csv", rows, fields)
    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "registry_schema_version": registry.get("schema_version"),
        "sampling_policy": registry.get("sampling_policy"),
        "acquisition_gate": gate,
        "coverage": {
            "requested_reports": len(requested),
            "requested_dates": len(registry_qa["requested_dates"]),
            "player_successful_reports": len(player_success),
            "team_successful_reports": len(team_success),
            "overlapping_successful_reports": len(overlap),
            "player_successful_dates": len(player_dates),
            "team_successful_dates": len(team_dates),
            "overlapping_successful_dates": len(overlap_dates),
            "player_failure_rate": round(player_failure_rate, 6),
            "team_failure_rate": round(team_failure_rate, 6),
            "player_normalized_rows": as_int(player_report_coverage.get("normalized_player_rows")),
            "player_unique_games": as_int(player_report_coverage.get("unique_games")),
            "team_submission_rows": len(team_panel),
            "team_unique_games": len(team_panel_games),
            "team_submission_status_counts": dict(sorted(team_status_counts.items())),
        },
        "quality": {
            "registry_errors": registry_qa["errors"],
            "duplicate_requested_timestamps": registry_qa["duplicate_requested_timestamps"],
            "duplicate_player_source_times": duplicate_player_times,
            "duplicate_team_source_times": duplicate_team_times,
            "duplicate_player_source_urls": duplicate_player_urls,
            "duplicate_team_source_urls": duplicate_team_urls,
            "unexpected_player_success_times": unexpected_player,
            "unexpected_team_success_times": unexpected_team,
            "missing_player_report_times": missing_player,
            "missing_team_report_times": missing_team,
            "team_submission_conflicts": team_panel_conflicts,
            "forbidden_player_files_found": forbidden_files,
            "report_crosschecks": report_crosschecks,
            "threshold_results": threshold_results,
            "player_failure_examples": list(player_failures.values())[:20],
            "team_failure_examples": list(team_failures.values())[:20],
            "player_names_or_injury_reasons_in_outputs": False,
            "outcomes_or_market_prices_used": False,
        },
        "decision": {
            "ready_for_wave1_feature_backfill": ready,
            "ready_for_model_training": False,
            "ready_for_probability_adjustment": False,
            "ready_for_betting_edge_claim": False,
            "reason": (
                "The calendar-fixed acquisition wave passed its predeclared provenance and coverage gates."
                if ready
                else "The acquisition wave failed one or more predeclared coverage or provenance gates."
            ),
        },
        "guardrails": {
            "failed_times_may_be_replaced_with_handpicked_dates": False,
            "multiple_publication_times_are_independent_games": False,
            "player_level_rows_retained_in_artifact": False,
            "acquisition_readiness_is_model_readiness": False,
        },
    }
    (output_dir / "injury-backfill-wave-audit.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def self_test(output_dir: Path) -> None:
    with TemporaryDirectory(prefix="nbavl-wave-audit-") as temp_name:
        root = Path(temp_name)
        times = [
            "2024-01-01T08:30:00-05:00",
            "2024-01-01T13:30:00-05:00",
            "2024-01-15T08:30:00-05:00",
            "2024-01-15T13:30:00-05:00",
        ]
        registry = {
            "schema_version": "test",
            "sampling_policy": {
                "selection_basis": "calendar_only_before_outcome_or_market_join",
                "weekday": "Monday",
                "official_slots_et": ["08:30", "13:30"],
                "start_date": "2024-01-01",
                "end_date": "2024-01-15",
                "dates": 2,
                "candidate_reports": 4,
            },
            "acquisition_gate": {
                "minimum_successful_player_reports": 2,
                "minimum_successful_team_reports": 2,
                "minimum_overlapping_successful_reports": 2,
                "minimum_unique_successful_dates": 2,
                "maximum_failure_rate_per_pipeline": 0.50,
            },
            "report_times": times,
        }
        player_sources = [
            {"requested_report_time": value, "source_url": f"https://player/{index}", "source_file_sha256": f"{index + 1:064x}"}
            for index, value in enumerate(times[:3])
        ]
        team_sources = [
            {"requested_report_time": value, "source_url": f"https://team/{index}", "source_file_sha256": f"{index + 11:064x}"}
            for index, value in enumerate(times[1:])
        ]
        player_report = {
            "coverage": {"requested_reports": 4, "successful_reports": 3, "normalized_player_rows": 300, "unique_games": 20},
            "quality": {"failed_report_examples": [{"requested_report_time": times[3], "error_type": "HTTPStatusError", "error": "404"}]},
        }
        team_report = {
            "coverage": {"requested_reports": 4, "successful_reports": 3, "team_submission_rows": 8, "unique_report_times": 3},
            "quality": {"submission_conflicts": 0, "failed_report_examples": [{"requested_report_time": times[0], "error_type": "HTTPStatusError", "error": "404"}]},
        }
        team_panel = []
        for value in times[1:]:
            for team in ("AAA", "BBB"):
                team_panel.append({
                    "observed_at": parse_timestamp(value).isoformat().replace("+00:00", "Z"),
                    "game_id": f"g-{value}-{team}",
                    "submission_status": "SUBMITTED_WITH_PLAYER_ROWS",
                    "submission_conflict": "0",
                })
        # Align report count to synthetic panel rows.
        team_report["coverage"]["team_submission_rows"] = len(team_panel)
        report = audit(
            registry,
            player_report,
            player_sources,
            team_report,
            team_sources,
            team_panel,
            root,
            output_dir,
        )
    assert report["decision"]["ready_for_wave1_feature_backfill"] is True, report
    assert report["coverage"]["overlapping_successful_reports"] == 2, report
    assert report["decision"]["ready_for_model_training"] is False, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path)
    parser.add_argument("--player-report", type=Path)
    parser.add_argument("--player-source-index", type=Path)
    parser.add_argument("--team-report", type=Path)
    parser.add_argument("--team-source-index", type=Path)
    parser.add_argument("--team-panel", type=Path)
    parser.add_argument("--sensitive-root", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("injury backfill wave acquisition audit self-test passed")
        return
    required = (
        args.registry,
        args.player_report,
        args.player_source_index,
        args.team_report,
        args.team_source_index,
        args.team_panel,
    )
    if any(value is None for value in required):
        parser.error("registry, player/team reports, source indexes, and team panel are required")
    report = audit(
        read_json(args.registry),
        read_json(args.player_report),
        read_csv(args.player_source_index),
        read_json(args.team_report),
        read_csv(args.team_source_index),
        read_csv(args.team_panel),
        args.sensitive_root,
        args.output_dir,
    )
    print(json.dumps(report["decision"], indent=2))
    if not report["decision"]["ready_for_wave1_feature_backfill"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
