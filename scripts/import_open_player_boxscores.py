#!/usr/bin/env python3
"""Import a MIT-licensed player boxscore archive and validate it against Gold.

The archive is a secondary research source. Gold remains the authority for game identity, date,
and home/away teams. Player-level rows are temporary and are not committed or uploaded by default.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import re
import shutil
import sqlite3
import tempfile
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "open-player-boxscore-archive-v1"
SOURCE_REPOSITORY = "NocturneBear/NBA-Data-2010-2024"
SOURCE_BASE = "https://raw.githubusercontent.com/NocturneBear/NBA-Data-2010-2024/main/"
SOURCE_FILES = [f"regular_season_box_scores_2010_2024_part_{part}.csv" for part in (1, 2, 3)]
OUTPUT_COLUMNS = [
    "SEASON_YEAR", "PLAYER_ID", "PLAYER_NAME", "TEAM_ID", "TEAM_ABBREVIATION",
    "GAME_ID", "OFFICIAL_GAME_ID", "GAME_DATE", "MATCHUP", "MIN", "FGM", "FGA",
    "FTM", "FTA", "OREB", "DREB", "REB", "AST", "TOV", "STL", "BLK", "PF",
    "PTS", "PLUS_MINUS", "STARTER", "PLAYED", "SOURCE_FILE",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
        return result if math.isfinite(result) else default
    except (TypeError, ValueError):
        return default


def as_int(value: Any, default: int = 0) -> int:
    return int(round(as_float(value, default)))


def parse_minutes(value: Any) -> float:
    text = str(value or "").strip()
    if not text:
        return 0.0
    if re.fullmatch(r"\d+(?:\.\d+)?", text):
        return float(text)
    match = re.fullmatch(
        r"P(?:\d+D)?T(?:(\d+(?:\.\d+)?)H)?(?:(\d+(?:\.\d+)?)M)?"
        r"(?:(\d+(?:\.\d+)?)S)?",
        text,
    )
    if not match:
        raise ValueError(f"unsupported minutes format: {value!r}")
    hours = float(match.group(1) or 0)
    minutes = float(match.group(2) or 0)
    seconds = float(match.group(3) or 0)
    return round(hours * 60 + minutes + seconds / 60, 6)


def normalize_official_game_id(value: Any) -> str:
    raw = re.sub(r"\.0$", "", str(value or "").strip())
    if not re.fullmatch(r"\d{8}|\d{10}", raw):
        raise ValueError(f"unsupported game ID: {value!r}")
    return raw.zfill(10)


def normalize_date(value: Any) -> str:
    text = str(value or "").strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}", text):
        return text[:10]
    for pattern in ("%m/%d/%Y", "%b %d, %Y"):
        try:
            return datetime.strptime(text, pattern).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"unsupported game date: {value!r}")


def gunzip(source: Path, destination: Path) -> None:
    with gzip.open(source, "rb") as src, destination.open("wb") as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)


def open_gold(path: Path, temp_root: Path) -> sqlite3.Connection:
    if path.suffix.lower() == ".gz":
        sqlite_path = temp_root / "historical-gold.sqlite"
        gunzip(path, sqlite_path)
    else:
        sqlite_path = path
    db = sqlite3.connect(sqlite_path)
    tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    missing = sorted({"gold_matchup_features", "gold_team_game_features"} - tables)
    if missing:
        db.close()
        raise ValueError(f"Gold database missing tables: {missing}")
    return db


def gold_schedule(db: sqlite3.Connection, season: str) -> dict[str, dict[str, str]]:
    rows = db.execute(
        """
        SELECT m.game_id, m.game_date, m.home_team_abbr, m.away_team_abbr, h.season_label
        FROM gold_matchup_features m
        JOIN gold_team_game_features h ON h.feature_id=m.home_feature_id
        WHERE h.season_label=?
        ORDER BY m.game_date, m.game_id
        """,
        (season,),
    ).fetchall()
    schedule = {}
    for historical_id, game_date, home, away, season_label in rows:
        official_id = normalize_official_game_id(historical_id)
        if official_id in schedule:
            raise ValueError(f"duplicate Gold official game ID: {official_id}")
        schedule[official_id] = {
            "historical_game_id": str(historical_id),
            "official_game_id": official_id,
            "game_date": str(game_date),
            "home_team_abbr": str(home),
            "away_team_abbr": str(away),
            "season_label": str(season_label),
        }
    if not schedule:
        raise ValueError(f"Gold schedule has no rows for {season}")
    return schedule


def download_file(url: str, destination: Path) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "NBA-Value-Lab-Research/1.0"})
    with urllib.request.urlopen(request, timeout=180) as response:
        payload = response.read()
    destination.write_bytes(payload)
    return {
        "url": url,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def normalized_row(raw: dict[str, str], source_file: str, schedule: dict[str, str]) -> dict[str, Any]:
    minutes = parse_minutes(raw.get("minutes"))
    played = int(minutes > 0)
    position = str(raw.get("position") or "").strip()
    return {
        "SEASON_YEAR": str(raw.get("season_year") or "").strip(),
        "PLAYER_ID": re.sub(r"\.0$", "", str(raw.get("personId") or "").strip()),
        "PLAYER_NAME": str(raw.get("personName") or "").strip(),
        "TEAM_ID": re.sub(r"\.0$", "", str(raw.get("teamId") or "").strip()),
        "TEAM_ABBREVIATION": str(raw.get("teamTricode") or "").strip(),
        "GAME_ID": schedule["historical_game_id"],
        "OFFICIAL_GAME_ID": schedule["official_game_id"],
        "GAME_DATE": schedule["game_date"],
        "MATCHUP": str(raw.get("matchup") or "").strip(),
        "MIN": minutes,
        "FGM": as_int(raw.get("fieldGoalsMade")),
        "FGA": as_int(raw.get("fieldGoalsAttempted")),
        "FTM": as_int(raw.get("freeThrowsMade")),
        "FTA": as_int(raw.get("freeThrowsAttempted")),
        "OREB": as_int(raw.get("reboundsOffensive")),
        "DREB": as_int(raw.get("reboundsDefensive")),
        "REB": as_int(raw.get("reboundsTotal")),
        "AST": as_int(raw.get("assists")),
        "TOV": as_int(raw.get("turnovers")),
        "STL": as_int(raw.get("steals")),
        "BLK": as_int(raw.get("blocks")),
        "PF": as_int(raw.get("foulsPersonal")),
        "PTS": as_int(raw.get("points")),
        "PLUS_MINUS": as_float(raw.get("plusMinusPoints")),
        "STARTER": int(bool(position) and played == 1),
        "PLAYED": played,
        "SOURCE_FILE": source_file,
    }


def import_archive(season: str, gold_path: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="nbavl-open-player-boxscores-") as temp_name:
        temp = Path(temp_name)
        db = open_gold(gold_path, temp)
        schedule = gold_schedule(db, season)
        db.close()

        source_reports = []
        accepted: dict[tuple[str, str], dict[str, Any]] = {}
        archive_games = set()
        unmatched_archive_games = set()
        archive_rows_for_season = 0
        rows_outside_gold = 0
        date_mismatches = 0
        team_mismatches = 0
        invalid_player_ids = 0
        invalid_minutes = 0
        duplicate_rows = 0

        for name in SOURCE_FILES:
            source_path = temp / name
            source_report = download_file(SOURCE_BASE + name, source_path)
            source_report["name"] = name
            selected_rows = 0
            with source_path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
                reader = csv.DictReader(handle)
                for raw in reader:
                    if str(raw.get("season_year") or "").strip() != season:
                        continue
                    archive_rows_for_season += 1
                    selected_rows += 1
                    try:
                        official_id = normalize_official_game_id(raw.get("gameId"))
                    except ValueError:
                        rows_outside_gold += 1
                        continue
                    archive_games.add(official_id)
                    game = schedule.get(official_id)
                    if game is None:
                        unmatched_archive_games.add(official_id)
                        rows_outside_gold += 1
                        continue
                    try:
                        archive_date = normalize_date(raw.get("game_date"))
                    except ValueError:
                        date_mismatches += 1
                        continue
                    if archive_date != game["game_date"]:
                        date_mismatches += 1
                        continue
                    team = str(raw.get("teamTricode") or "").strip()
                    if team not in {game["home_team_abbr"], game["away_team_abbr"]}:
                        team_mismatches += 1
                        continue
                    try:
                        row = normalized_row(raw, name, game)
                    except ValueError:
                        invalid_minutes += 1
                        continue
                    if not re.fullmatch(r"\d+", row["PLAYER_ID"]):
                        invalid_player_ids += 1
                        continue
                    key = (row["GAME_ID"], row["PLAYER_ID"])
                    if key in accepted:
                        duplicate_rows += 1
                        if row["PLAYED"] > accepted[key]["PLAYED"]:
                            accepted[key] = row
                    else:
                        accepted[key] = row
            source_report["selected_season_rows"] = selected_rows
            source_reports.append(source_report)

        rows = sorted(
            accepted.values(),
            key=lambda row: (row["GAME_DATE"], row["GAME_ID"], row["TEAM_ABBREVIATION"], row["PLAYER_ID"]),
        )
        output_path = output_dir / "open-player-boxscores.csv"
        with output_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)

    gold_games = set(schedule)
    matched_games = {row["OFFICIAL_GAME_ID"] for row in rows}
    played_rows = [row for row in rows if row["PLAYED"] == 1]
    played_counts: dict[str, int] = defaultdict(int)
    teams_by_game: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        teams_by_game[row["OFFICIAL_GAME_ID"]].add(row["TEAM_ABBREVIATION"])
        if row["PLAYED"] == 1:
            played_counts[row["OFFICIAL_GAME_ID"]] += 1
    missing_gold_games = sorted(gold_games - matched_games)
    team_set_errors = sum(
        teams_by_game[official_id] != {game["home_team_abbr"], game["away_team_abbr"]}
        for official_id, game in schedule.items()
        if official_id in matched_games
    )
    low_played_games = sum(count < 10 for count in played_counts.values())
    game_coverage = len(matched_games) / len(gold_games) if gold_games else 0.0
    unique_players = len({row["PLAYER_ID"] for row in rows})
    ready = (
        len(gold_games) >= 1200
        and game_coverage >= 0.995
        and len(played_rows) >= 20000
        and unique_players >= 500
        and date_mismatches == 0
        and team_mismatches == 0
        and team_set_errors == 0
        and invalid_player_ids == 0
        and invalid_minutes == 0
        and low_played_games == 0
    )
    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "source": {
            "repository": SOURCE_REPOSITORY,
            "license": "MIT",
            "classification": "secondary_open_archive",
            "upstream_collection_method_fully_documented": False,
            "source_files": source_reports,
        },
        "coverage": {
            "season": season,
            "archive_rows_for_season": archive_rows_for_season,
            "normalized_roster_rows": len(rows),
            "played_player_rows": len(played_rows),
            "unique_players": unique_players,
            "gold_games": len(gold_games),
            "matched_gold_games": len(matched_games),
            "game_coverage": round(game_coverage, 6),
        },
        "quality": {
            "rows_outside_gold": rows_outside_gold,
            "unmatched_archive_games": len(unmatched_archive_games),
            "unmatched_archive_game_examples": sorted(unmatched_archive_games)[:20],
            "missing_gold_games": len(missing_gold_games),
            "missing_gold_game_examples": missing_gold_games[:20],
            "date_mismatches": date_mismatches,
            "row_team_mismatches": team_mismatches,
            "game_team_set_errors": team_set_errors,
            "invalid_player_ids": invalid_player_ids,
            "invalid_minutes_rows": invalid_minutes,
            "duplicate_game_player_rows_resolved": duplicate_rows,
            "games_with_fewer_than_10_played_players": low_played_games,
        },
        "decision": {
            "ready_for_point_in_time_feature_research": ready,
            "approved_as_primary_source": False,
            "ready_for_model_training": False,
            "ready_for_betting_edge_claim": False,
            "reason": "Gold-validated secondary archive; source-method review and holdout validation remain required.",
        },
        "guardrails": {
            "gold_controls_game_identity_date_and_teams": True,
            "rows_not_present_in_gold_are_excluded": True,
            "raw_archive_committed_or_uploaded": False,
            "player_rows_uploaded_by_default": False,
            "same_game_statistics_allowed_as_target_features": False,
        },
    }
    (output_dir / "open-player-boxscore-import-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def self_test(output_dir: Path) -> None:
    assert parse_minutes("PT30M12S") == 30.2
    assert normalize_official_game_id("22300061") == "0022300061"
    assert normalize_date("2023-10-24T00:00:00") == "2023-10-24"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "self-test.json").write_text('{"passed":true}\n', encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", default="2023-24")
    parser.add_argument("--gold", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("open player boxscore importer self-test passed")
        return
    if not args.gold:
        parser.error("--gold is required unless --self-test is used")
    report = import_archive(args.season, args.gold, args.output_dir)
    print(json.dumps(report["decision"], indent=2))
    if not report["decision"]["ready_for_point_in_time_feature_research"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
