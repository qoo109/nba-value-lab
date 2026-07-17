#!/usr/bin/env python3
"""Build a point-in-time team submission-status panel from official NBA injury PDFs.

The output contains team/game provenance only. Player names, injury reasons, and raw PDF bytes are
never retained. A missing side is synthesized as UNKNOWN_NO_PLAYER_ROWS rather than silently treated
as healthy or causing the whole report to be discarded.
"""
from __future__ import annotations

import argparse
import csv
import json
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pymupdf

from import_official_nba_injury_report import (
    ALLOWED_STATUSES,
    TEAM_NAME_TO_ABBR,
    download_pdf,
    group_physical_lines,
    is_header_line,
    iso_utc,
    normalize_space,
    page_words,
    parse_game_time,
    parse_matchup,
    parse_report_time,
    report_url,
    update_context,
)

VERSION = "multi-report-team-submission-panel-v1.1"
NO_INJURY_MARKERS = (
    "NO INJURIES TO REPORT",
    "NO INJURY TO REPORT",
    "NO INJURIES REPORTED",
    "NONE TO REPORT",
)
SUBMISSION_STATUSES = {
    "SUBMITTED_WITH_PLAYER_ROWS",
    "SUBMITTED_NO_INJURIES",
    "NOT_YET_SUBMITTED",
    "UNKNOWN_NO_PLAYER_ROWS",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_report_times(path: Path) -> list[str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload = payload.get("report_times")
    if not isinstance(payload, list) or not payload:
        raise ValueError("report-times JSON must contain a non-empty report_times list")
    values = [str(value).strip() for value in payload if str(value).strip()]
    if len(values) != len(set(values)):
        raise ValueError("report-times JSON contains duplicate timestamps")
    for value in values:
        parse_report_time(value)
    return values


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def classify_submission(*, player_status_rows: int, not_yet_submitted: bool, no_injuries: bool) -> tuple[str, bool]:
    active = int(player_status_rows > 0) + int(not_yet_submitted) + int(no_injuries)
    if active > 1:
        return "UNKNOWN_NO_PLAYER_ROWS", True
    if player_status_rows > 0:
        return "SUBMITTED_WITH_PLAYER_ROWS", False
    if no_injuries:
        return "SUBMITTED_NO_INJURIES", False
    if not_yet_submitted:
        return "NOT_YET_SUBMITTED", False
    return "UNKNOWN_NO_PLAYER_ROWS", False


def parse_official_game_id(game_id: str) -> tuple[str, str]:
    matchup = game_id.rsplit(":", 1)[-1]
    away, home = matchup.split("@", 1)
    return away, home


def base_record(
    *, game_id: str, commence_time: str, team: str, away: str, home: str,
    observed_at: str, source_url: str, source_hash: str,
) -> dict[str, Any]:
    opponent = home if team == away else away
    return {
        "record_type": "TEAM_SUBMISSION_STATUS",
        "game_id": game_id,
        "commence_time": commence_time,
        "team_abbr": team,
        "opponent_abbr": opponent,
        "is_home": int(team == home),
        "submission_status": "UNKNOWN_NO_PLAYER_ROWS",
        "player_status_rows": 0,
        "not_yet_submitted_marker": 0,
        "no_injuries_marker": 0,
        "submission_conflict": 0,
        "synthetic_missing_side": 0,
        "observed_at": observed_at,
        "source_report_time": observed_at,
        "source_provider": "NBA Official Injury Report",
        "source_url": source_url,
        "source_file_sha256": source_hash,
    }


def extract_team_submissions(
    pdf_path: Path,
    report_time: datetime,
    source_url: str,
    source_hash: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    document = pymupdf.open(pdf_path)
    state = {"game_date": "", "game_time": "", "matchup": "", "team": ""}
    records: dict[tuple[str, str], dict[str, Any]] = {}
    game_meta: dict[str, dict[str, str]] = {}
    context_errors: list[str] = []
    marker_lines = 0
    status_anchor_lines = 0

    for page_index, page in enumerate(document):
        lines = [line for line in group_physical_lines(page_words(page)) if not is_header_line(line)]
        for line in lines:
            cells = line["cells"]
            update_context(state, cells)
            team_name = normalize_space(state.get("team"))
            matchup = normalize_space(state.get("matchup"))
            game_date = normalize_space(state.get("game_date"))
            game_time = normalize_space(state.get("game_time"))
            if team_name not in TEAM_NAME_TO_ABBR or not matchup or not game_date or not game_time:
                continue
            try:
                away, home = parse_matchup(matchup)
                team = TEAM_NAME_TO_ABBR[team_name]
                if team not in {away, home}:
                    raise ValueError(f"team {team} does not belong to {away}@{home}")
                commence = parse_game_time(game_date, game_time)
                if report_time >= commence:
                    raise ValueError("report timestamp is not before scheduled tip-off")
                game_id = f"official:{commence.date().isoformat()}:{away}@{home}"
                observed_at = iso_utc(report_time)
                commence_time = iso_utc(commence)
            except Exception as exc:
                context_errors.append(
                    f"page {page_index + 1} line {line['center_y']:.2f}: {type(exc).__name__}: {exc}"
                )
                continue

            game_meta[game_id] = {
                "away": away,
                "home": home,
                "commence_time": commence_time,
                "observed_at": observed_at,
            }
            key = (game_id, team)
            record = records.setdefault(
                key,
                base_record(
                    game_id=game_id,
                    commence_time=commence_time,
                    team=team,
                    away=away,
                    home=home,
                    observed_at=observed_at,
                    source_url=source_url,
                    source_hash=source_hash,
                ),
            )
            combined = normalize_space(" ".join(str(value) for value in cells.values())).upper()
            if "NOT YET SUBMITTED" in combined:
                record["not_yet_submitted_marker"] = 1
                marker_lines += 1
            if any(marker in combined for marker in NO_INJURY_MARKERS):
                record["no_injuries_marker"] = 1
                marker_lines += 1
            status = normalize_space(cells.get("current_status"))
            if status in ALLOWED_STATUSES:
                record["player_status_rows"] += 1
                status_anchor_lines += 1

    synthetic_missing_sides = 0
    for game_id, meta in game_meta.items():
        for team in (meta["away"], meta["home"]):
            key = (game_id, team)
            if key in records:
                continue
            row = base_record(
                game_id=game_id,
                commence_time=meta["commence_time"],
                team=team,
                away=meta["away"],
                home=meta["home"],
                observed_at=meta["observed_at"],
                source_url=source_url,
                source_hash=source_hash,
            )
            row["synthetic_missing_side"] = 1
            records[key] = row
            synthetic_missing_sides += 1

    output: list[dict[str, Any]] = []
    conflicts = 0
    for record in records.values():
        status, conflict = classify_submission(
            player_status_rows=int(record["player_status_rows"]),
            not_yet_submitted=bool(record["not_yet_submitted_marker"]),
            no_injuries=bool(record["no_injuries_marker"]),
        )
        record["submission_status"] = status
        record["submission_conflict"] = int(conflict)
        conflicts += int(conflict)
        output.append(record)
    output.sort(key=lambda row: (row["commence_time"], row["game_id"], row["team_abbr"]))

    games: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in output:
        games[str(row["game_id"])].append(row)
    duplicate_keys = len(output) - len({(row["game_id"], row["team_abbr"]) for row in output})
    invalid_team_counts = sum(len(rows) != 2 for rows in games.values())
    statuses = Counter(str(row["submission_status"]) for row in output)
    return output, {
        "page_count": len(document),
        "team_rows": len(output),
        "games": len(games),
        "submission_status_counts": dict(sorted(statuses.items())),
        "marker_lines": marker_lines,
        "player_status_anchor_lines": status_anchor_lines,
        "synthetic_unknown_team_rows": synthetic_missing_sides,
        "context_errors": len(context_errors),
        "context_error_examples": context_errors[:50],
        "submission_conflicts": conflicts,
        "duplicate_game_team_rows": duplicate_keys,
        "games_without_exactly_two_teams": invalid_team_counts,
    }


def build(report_times_file: Path, output_dir: Path) -> dict[str, Any]:
    requested_times = read_report_times(report_times_file)
    output_dir.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict[str, Any]] = []
    source_index: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    for requested in requested_times:
        report_time = parse_report_time(requested)
        url = report_url(report_time)
        retrieved_at = utc_now()
        try:
            with tempfile.TemporaryDirectory(prefix="nbavl-team-submission-") as temp_name:
                pdf_path = Path(temp_name) / "official-injury-report.pdf"
                source_hash, source_bytes = download_pdf(url, pdf_path)
                rows, qa = extract_team_submissions(pdf_path, report_time, url, source_hash)
            if not rows:
                raise ValueError("team-submission parser produced no team rows")
            if qa["context_errors"] or qa["submission_conflicts"] or qa["duplicate_game_team_rows"] or qa["games_without_exactly_two_teams"]:
                raise ValueError(f"team-submission QA failed: {qa}")
            all_rows.extend(rows)
            source_index.append({
                "requested_report_time": requested,
                "observed_at": iso_utc(report_time),
                "source_url": url,
                "source_file_sha256": source_hash,
                "source_size_bytes": source_bytes,
                "retrieved_at": retrieved_at,
                "team_rows": qa["team_rows"],
                "games": qa["games"],
                "synthetic_unknown_team_rows": qa["synthetic_unknown_team_rows"],
                "submission_status_counts": json.dumps(qa["submission_status_counts"], sort_keys=True),
            })
        except Exception as exc:
            failures.append({
                "requested_report_time": requested,
                "source_url": url,
                "error_type": type(exc).__name__,
                "error": str(exc),
            })

    all_rows.sort(key=lambda row: (row["observed_at"], row["game_id"], row["team_abbr"]))
    duplicate_rows = len(all_rows) - len({
        (row["source_file_sha256"], row["game_id"], row["team_abbr"]) for row in all_rows
    })
    status_counts = Counter(str(row["submission_status"]) for row in all_rows)
    report_dates = {parse_report_time(row["requested_report_time"]).date().isoformat() for row in source_index}
    failure_rate = len(failures) / len(requested_times) if requested_times else 1.0
    synthetic_rows = sum(int(row["synthetic_missing_side"]) for row in all_rows)
    ready = (
        len(source_index) >= 4
        and len(report_dates) >= 3
        and len(all_rows) >= 80
        and failure_rate <= 0.50
        and duplicate_rows == 0
        and all(str(row["submission_status"]) in SUBMISSION_STATUSES for row in all_rows)
        and all(int(row["submission_conflict"]) == 0 for row in all_rows)
    )

    row_fields = [
        "record_type", "game_id", "commence_time", "team_abbr", "opponent_abbr", "is_home",
        "submission_status", "player_status_rows", "not_yet_submitted_marker", "no_injuries_marker",
        "submission_conflict", "synthetic_missing_side", "observed_at", "source_report_time",
        "source_provider", "source_url", "source_file_sha256",
    ]
    index_fields = [
        "requested_report_time", "observed_at", "source_url", "source_file_sha256",
        "source_size_bytes", "retrieved_at", "team_rows", "games", "synthetic_unknown_team_rows",
        "submission_status_counts",
    ]
    write_csv(output_dir / "multi-report-team-submission-panel.csv", all_rows, row_fields)
    write_csv(output_dir / "multi-report-team-submission-source-index.csv", source_index, index_fields)
    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "coverage": {
            "requested_reports": len(requested_times),
            "successful_reports": len(source_index),
            "failed_reports": len(failures),
            "failure_rate": round(failure_rate, 6),
            "unique_report_dates": len(report_dates),
            "unique_report_times": len({row["observed_at"] for row in all_rows}),
            "team_submission_rows": len(all_rows),
            "unique_games": len({str(row["game_id"]) for row in all_rows}),
            "synthetic_unknown_team_rows": synthetic_rows,
            "submission_status_counts": dict(sorted(status_counts.items())),
        },
        "quality": {
            "duplicate_team_submission_rows": duplicate_rows,
            "submission_conflicts": sum(int(row["submission_conflict"]) for row in all_rows),
            "unknown_no_player_rows": status_counts["UNKNOWN_NO_PLAYER_ROWS"],
            "failed_report_examples": failures[:20],
            "raw_pdfs_retained": False,
            "player_names_or_injury_reasons_retained": False,
            "missing_sides_synthesized_as_unknown_not_healthy": True,
        },
        "decision": {
            "ready_for_team_submission_reconciliation": ready,
            "ready_for_model_training": False,
            "ready_for_probability_adjustment": False,
            "ready_for_betting_edge_claim": False,
            "reason": (
                "Team-level submission states passed point-in-time and structural QA."
                if ready else "Team-level submission panel failed one or more ingestion gates."
            ),
        },
        "guardrails": {
            "explicit_submitted_no_injuries_may_create_zero_burden": True,
            "not_yet_submitted_may_create_zero_burden": False,
            "unknown_no_player_rows_may_create_zero_burden": False,
            "synthetic_missing_side_may_create_zero_burden": False,
            "source_publication_time_used_as_observed_at": True,
            "player_level_data_in_output": False,
        },
    }
    (output_dir / "multi-report-team-submission-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def self_test(output_dir: Path) -> None:
    assert classify_submission(player_status_rows=2, not_yet_submitted=False, no_injuries=False) == ("SUBMITTED_WITH_PLAYER_ROWS", False)
    assert classify_submission(player_status_rows=0, not_yet_submitted=False, no_injuries=True) == ("SUBMITTED_NO_INJURIES", False)
    assert classify_submission(player_status_rows=0, not_yet_submitted=True, no_injuries=False) == ("NOT_YET_SUBMITTED", False)
    assert classify_submission(player_status_rows=0, not_yet_submitted=False, no_injuries=False) == ("UNKNOWN_NO_PLAYER_ROWS", False)
    assert classify_submission(player_status_rows=1, not_yet_submitted=True, no_injuries=False)[1] is True
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "team-submission-self-test.json").write_text('{"passed":true}\n', encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-times", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("team submission panel self-test passed")
        return
    if not args.report_times:
        parser.error("--report-times is required")
    report = build(args.report_times, args.output_dir)
    print(json.dumps(report["decision"], indent=2))
    if not report["decision"]["ready_for_team_submission_reconciliation"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
