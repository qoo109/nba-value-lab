#!/usr/bin/env python3
"""Fetch one NBA regular season of official player game logs.

The row-level CSV is intended for temporary feature construction. Aggregate provenance and QA
may be retained without redistributing player-level source rows.
"""
from __future__ import annotations

import argparse
import calendar
import csv
import hashlib
import json
import re
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import httpx

VERSION = "official-player-game-logs-v1"
ENDPOINT = "https://stats.nba.com/stats/playergamelogs"
REQUIRED_COLUMNS = {
    "SEASON_YEAR", "PLAYER_ID", "PLAYER_NAME", "TEAM_ID", "TEAM_ABBREVIATION",
    "GAME_ID", "GAME_DATE", "MATCHUP", "MIN", "FGM", "FGA", "FTM", "FTA",
    "OREB", "DREB", "REB", "AST", "TOV", "STL", "BLK", "PF", "PTS", "PLUS_MINUS",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def request_headers() -> dict[str, str]:
    return {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://www.nba.com",
        "Referer": "https://www.nba.com/",
        "Connection": "keep-alive",
    }


def request_params(season: str, date_from: date, date_to: date) -> dict[str, str]:
    return {
        "DateFrom": date_from.strftime("%m/%d/%Y"),
        "DateTo": date_to.strftime("%m/%d/%Y"),
        "GameSegment": "",
        "LastNGames": "0",
        "LeagueID": "00",
        "Location": "",
        "MeasureType": "Base",
        "Month": "0",
        "OppTeamID": "0",
        "Outcome": "",
        "PORound": "0",
        "PerMode": "Totals",
        "Period": "0",
        "PlayerID": "",
        "Season": season,
        "SeasonSegment": "",
        "SeasonType": "Regular Season",
        "ShotClockRange": "",
        "TeamID": "",
        "VsConference": "",
        "VsDivision": "",
    }


def season_windows(season: str) -> list[tuple[date, date]]:
    match = re.fullmatch(r"(\d{4})-(\d{2})", season)
    if not match:
        raise ValueError(f"season must look like 2023-24: {season!r}")
    start_year = int(match.group(1))
    expected_end = (start_year + 1) % 100
    if int(match.group(2)) != expected_end:
        raise ValueError(f"season end year is inconsistent: {season!r}")
    windows = []
    year, month = start_year, 10
    for _ in range(12):
        last_day = calendar.monthrange(year, month)[1]
        windows.append((date(year, month, 1), date(year, month, last_day)))
        month += 1
        if month == 13:
            month = 1
            year += 1
    return windows


def result_rows(payload: dict[str, Any]) -> tuple[list[str], list[list[Any]]]:
    result_sets = payload.get("resultSets") or payload.get("resultSet")
    if isinstance(result_sets, dict):
        result_sets = [result_sets]
    if not isinstance(result_sets, list) or not result_sets:
        raise ValueError("official response has no result set")
    chosen = None
    for item in result_sets:
        if str(item.get("name", "")).lower() in {"playergamelogs", "player_game_logs"}:
            chosen = item
            break
    chosen = chosen or result_sets[0]
    headers = [str(value) for value in chosen.get("headers", [])]
    rows = chosen.get("rowSet", [])
    if not headers or not isinstance(rows, list):
        raise ValueError("official response result set is malformed")
    missing = sorted(REQUIRED_COLUMNS - set(headers))
    if missing:
        raise ValueError(f"official response missing required columns: {missing}")
    return headers, rows


def safe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fetch_window(
    client: httpx.Client,
    season: str,
    date_from: date,
    date_to: date,
    retries: int,
) -> tuple[list[str], list[list[Any]], bytes, dict[str, Any]]:
    errors = []
    for attempt in range(1, retries + 1):
        started = time.monotonic()
        try:
            response = client.get(ENDPOINT, params=request_params(season, date_from, date_to))
            response.raise_for_status()
            headers, rows = result_rows(response.json())
            elapsed = round(time.monotonic() - started, 3)
            return headers, rows, response.content, {
                "date_from": date_from.isoformat(),
                "date_to": date_to.isoformat(),
                "attempts": attempt,
                "rows": len(rows),
                "http_status": response.status_code,
                "response_bytes": len(response.content),
                "elapsed_seconds": elapsed,
            }
        except Exception as exc:
            errors.append(f"attempt {attempt}: {type(exc).__name__}: {exc}")
            if attempt < retries:
                time.sleep(min(2 ** attempt, 8))
    raise RuntimeError(
        f"official player logs failed for {date_from}..{date_to}: " + " | ".join(errors)
    )


def fetch(
    season: str,
    output_dir: Path,
    timeout_seconds: float = 35.0,
    retries: int = 3,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    retrieved_at = utc_now()
    all_rows: list[list[Any]] = []
    canonical_headers: list[str] | None = None
    response_hasher = hashlib.sha256()
    request_reports = []
    with httpx.Client(
        headers=request_headers(),
        timeout=httpx.Timeout(timeout_seconds, connect=15.0),
        follow_redirects=True,
        http2=False,
    ) as client:
        for date_from, date_to in season_windows(season):
            headers, rows, raw_bytes, request_report = fetch_window(
                client, season, date_from, date_to, retries
            )
            if canonical_headers is None:
                canonical_headers = headers
            elif headers != canonical_headers:
                raise ValueError(
                    f"official response headers changed in {date_from}..{date_to}"
                )
            all_rows.extend(rows)
            response_hasher.update(raw_bytes)
            request_reports.append(request_report)

    headers = canonical_headers or []
    width_errors = sum(1 for row in all_rows if len(row) != len(headers))
    if width_errors:
        raise ValueError(f"official response contains {width_errors} row-width errors")
    records = [dict(zip(headers, row)) for row in all_rows]
    deduped = {}
    for row in records:
        key = (str(row["GAME_ID"]), str(row["PLAYER_ID"]))
        deduped[key] = row
    frame_rows = sorted(
        deduped.values(),
        key=lambda row: (str(row["GAME_DATE"]), str(row["GAME_ID"]), str(row["PLAYER_ID"])),
    )
    duplicate_keys = len(records) - len(frame_rows)

    csv_path = output_dir / "official-player-game-logs.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(frame_rows)

    invalid_game_ids = sum(not re.fullmatch(r"\d{10}", str(row["GAME_ID"])) for row in frame_rows)
    seasons_found = sorted({str(row["SEASON_YEAR"]) for row in frame_rows})
    min_values = [safe_float(row["MIN"]) for row in frame_rows]
    plus_minus_values = [safe_float(row["PLUS_MINUS"]) for row in frame_rows]
    minutes_present = sum(value is not None for value in min_values)
    plus_minus_present = sum(value is not None for value in plus_minus_values)
    unique_games = len({str(row["GAME_ID"]) for row in frame_rows})
    unique_players = len({str(row["PLAYER_ID"]) for row in frame_rows})
    ready = (
        bool(frame_rows)
        and invalid_game_ids == 0
        and season in seasons_found
        and minutes_present / len(frame_rows) >= 0.99
        and plus_minus_present / len(frame_rows) >= 0.95
        and unique_games >= 1000
        and unique_players >= 400
    )
    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "source": {
            "provider": "NBA Official Stats",
            "endpoint": ENDPOINT,
            "season_requested": season,
            "retrieved_at": retrieved_at,
            "combined_response_sha256": response_hasher.hexdigest(),
            "request_count": len(request_reports),
            "request_reports": request_reports,
        },
        "coverage": {
            "rows_before_window_dedupe": len(records),
            "rows": len(frame_rows),
            "unique_games": unique_games,
            "unique_players": unique_players,
            "season_values": seasons_found,
            "minutes_present_rows": minutes_present,
            "plus_minus_present_rows": plus_minus_present,
            "nonempty_windows": sum(report["rows"] > 0 for report in request_reports),
        },
        "quality": {
            "duplicate_game_player_keys_removed": duplicate_keys,
            "duplicate_game_player_keys_after_dedupe": 0,
            "invalid_game_ids": invalid_game_ids,
            "row_width_errors": width_errors,
            "required_columns_present": True,
            "minutes_coverage": round(minutes_present / len(frame_rows), 6) if frame_rows else 0.0,
            "plus_minus_coverage": round(plus_minus_present / len(frame_rows), 6) if frame_rows else 0.0,
            "all_windows_completed": len(request_reports) == len(season_windows(season)),
        },
        "decision": {
            "ready_for_point_in_time_feature_build": ready,
            "ready_for_model_training": False,
            "ready_for_betting_edge_claim": False,
            "reason": "Source and schema pilot only; strict prior-game feature generation is still required.",
        },
        "guardrails": {
            "source_rows_committed": False,
            "postgame_rows_may_only_influence_later_games": True,
            "same_game_statistics_allowed_as_features": False,
            "monthly_requests_used_to_limit_response_size": True,
        },
    }
    (output_dir / "official-player-game-logs-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def self_test(output_dir: Path) -> None:
    headers = sorted(REQUIRED_COLUMNS)
    row = ["" for _ in headers]
    payload = {"resultSets": [{"name": "PlayerGameLogs", "headers": headers, "rowSet": [row]}]}
    parsed_headers, rows = result_rows(payload)
    assert parsed_headers == headers
    assert len(rows) == 1
    windows = season_windows("2023-24")
    assert windows[0] == (date(2023, 10, 1), date(2023, 10, 31))
    assert windows[-1] == (date(2024, 9, 1), date(2024, 9, 30))
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "self-test.json").write_text('{"passed":true}\n', encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", default="2023-24")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=float, default=35.0)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("official player game logs importer self-test passed")
        return
    report = fetch(args.season, args.output_dir, args.timeout_seconds, args.retries)
    print(json.dumps(report["decision"], indent=2))
    if not report["decision"]["ready_for_point_in_time_feature_build"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
