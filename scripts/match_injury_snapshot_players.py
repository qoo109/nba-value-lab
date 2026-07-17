#!/usr/bin/env python3
"""Match normalized official injury snapshots to audited NBA Stats player IDs."""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
import shutil
import sqlite3
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from player_identity_core import normalize_player_name, suffixless_player_name

VERSION = "player-identity-layer-v1"
OFFICIAL_GAME_RE = re.compile(r"^official:(\d{4}-\d{2}-\d{2}):([A-Z]{3})@([A-Z]{3})$")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def open_database(path: Path, temp_root: Path, name: str, required_tables: set[str]) -> sqlite3.Connection:
    if path.suffix.lower() == ".gz":
        sqlite_path = temp_root / f"{name}.sqlite"
        with gzip.open(path, "rb") as source, sqlite_path.open("wb") as target:
            shutil.copyfileobj(source, target, length=1024 * 1024)
    else:
        sqlite_path = path
    db = sqlite3.connect(sqlite_path)
    names = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    missing = sorted(required_tables - names)
    if missing:
        db.close()
        raise ValueError(f"{path} missing required tables: {missing}")
    return db


def read_snapshots(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def schedule_index(db: sqlite3.Connection) -> tuple[dict[tuple[str, str, str], tuple[str, str]], int]:
    index: dict[tuple[str, str, str], tuple[str, str]] = {}
    duplicates = 0
    for game_id, game_date, season_label, away, home in db.execute(
        "SELECT game_id, game_date, season_label, away_team_abbr, home_team_abbr FROM games"
    ):
        key = (str(game_date), str(away), str(home))
        if key in index and index[key][0] != game_id:
            duplicates += 1
        index[key] = (str(game_id), str(season_label))
    return index, duplicates


def add_index(index, key, player_id):
    index[key].add(str(player_id))


def alias_indexes(db: sqlite3.Connection):
    team_season_exact = defaultdict(set)
    season_exact = defaultdict(set)
    global_exact = defaultdict(set)
    team_season_suffixless = defaultdict(set)
    season_suffixless = defaultdict(set)
    global_suffixless = defaultdict(set)
    alias_rows = 0
    seasons = set()
    for player_id, name_key, suffixless_key, team_abbr, season_label in db.execute(
        "SELECT player_id, player_name_key, player_name_key_suffixless, team_abbr, season_label FROM player_aliases"
    ):
        alias_rows += 1
        team = str(team_abbr or "")
        season = str(season_label)
        seasons.add(season)
        exact = str(name_key)
        suffixless = str(suffixless_key)
        add_index(team_season_exact, (season, team, exact), player_id)
        add_index(season_exact, (season, exact), player_id)
        add_index(global_exact, exact, player_id)
        add_index(team_season_suffixless, (season, team, suffixless), player_id)
        add_index(season_suffixless, (season, suffixless), player_id)
        add_index(global_suffixless, suffixless, player_id)
    return {
        "team_season_exact": team_season_exact,
        "season_exact": season_exact,
        "global_exact": global_exact,
        "team_season_suffixless": team_season_suffixless,
        "season_suffixless": season_suffixless,
        "global_suffixless": global_suffixless,
        "alias_rows": alias_rows,
        "seasons": sorted(seasons),
    }


def unique_candidate(candidates) -> str | None:
    values = sorted(set(candidates))
    return values[0] if len(values) == 1 else None


def choose_player(indexes, season: str, team: str, name: str) -> tuple[str | None, str, str, int]:
    exact = normalize_player_name(name)
    suffixless = suffixless_player_name(name)
    exact_scopes = [
        ("team_season_exact", indexes["team_season_exact"][(season, team, exact)], "HIGH"),
        ("season_unique_exact", indexes["season_exact"][(season, exact)], "HIGH"),
        ("global_unique_exact", indexes["global_exact"][exact], "HIGH"),
    ]
    for method, candidates, confidence in exact_scopes:
        player_id = unique_candidate(candidates)
        if player_id:
            return player_id, method, confidence, len(candidates)
        if len(candidates) > 1:
            return None, f"ambiguous_{method}", "BLOCKED", len(candidates)

    suffix_scopes = [
        ("team_season_unique_suffixless", indexes["team_season_suffixless"][(season, team, suffixless)]),
        ("season_unique_suffixless", indexes["season_suffixless"][(season, suffixless)]),
        ("global_unique_suffixless", indexes["global_suffixless"][suffixless]),
    ]
    for method, candidates in suffix_scopes:
        player_id = unique_candidate(candidates)
        if player_id:
            return player_id, method, "MEDIUM", len(candidates)
        if len(candidates) > 1:
            return None, f"ambiguous_{method}", "BLOCKED", len(candidates)
    return None, "unmatched", "BLOCKED", 0


def match(
    snapshot_rows: list[dict[str, str]],
    schedule_db: sqlite3.Connection,
    alias_db: sqlite3.Connection,
    output_dir: Path,
) -> dict[str, Any]:
    schedule, duplicate_schedule_keys = schedule_index(schedule_db)
    indexes = alias_indexes(alias_db)
    output = []
    method_counts = defaultdict(int)
    confidence_counts = defaultdict(int)
    unmatched_game_rows = 0
    side_errors = 0
    ambiguous_rows = 0
    unmatched_player_rows = 0

    for row in snapshot_rows:
        official_game_id = str(row.get("game_id", ""))
        parsed = OFFICIAL_GAME_RE.fullmatch(official_game_id)
        if not parsed:
            unmatched_game_rows += 1
            continue
        game_date, away, home = parsed.groups()
        schedule_match = schedule.get((game_date, away, home))
        if not schedule_match:
            unmatched_game_rows += 1
            continue
        historical_game_id, season = schedule_match
        team = str(row.get("team_abbr", ""))
        if team not in {away, home}:
            side_errors += 1
            continue
        player_id, method, confidence, candidate_count = choose_player(
            indexes, season, team, str(row.get("player_name", ""))
        )
        method_counts[method] += 1
        confidence_counts[confidence] += 1
        if method.startswith("ambiguous_"):
            ambiguous_rows += 1
        elif method == "unmatched":
            unmatched_player_rows += 1
        output.append({
            "snapshot_record_id": str(row.get("snapshot_record_id", "")),
            "historical_game_id": historical_game_id,
            "season_label": season,
            "team_abbr": team,
            "player_id": player_id or "",
            "match_method": method,
            "confidence": confidence,
            "candidate_count": candidate_count,
        })

    matched_rows = sum(1 for row in output if row["player_id"])
    total_rows = len(snapshot_rows)
    match_rate = round(matched_rows / total_rows, 6) if total_rows else 0.0
    high_confidence_rows = sum(1 for row in output if row["confidence"] == "HIGH")
    high_confidence_rate = round(high_confidence_rows / total_rows, 6) if total_rows else 0.0
    ready = (
        total_rows > 0
        and duplicate_schedule_keys == 0
        and unmatched_game_rows == 0
        and side_errors == 0
        and ambiguous_rows == 0
        and match_rate >= 0.95
        and high_confidence_rate >= 0.90
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "snapshot_record_id", "historical_game_id", "season_label", "team_abbr",
        "player_id", "match_method", "confidence", "candidate_count",
    ]
    with (output_dir / "injury-player-id-map.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output)

    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "coverage": {
            "snapshot_rows": total_rows,
            "rows_with_historical_game": total_rows - unmatched_game_rows,
            "matched_player_rows": matched_rows,
            "high_confidence_rows": high_confidence_rows,
            "alias_rows_available": indexes["alias_rows"],
            "alias_seasons_available": indexes["seasons"],
        },
        "quality": {
            "player_match_rate": match_rate,
            "high_confidence_match_rate": high_confidence_rate,
            "duplicate_schedule_keys": duplicate_schedule_keys,
            "unmatched_game_rows": unmatched_game_rows,
            "snapshot_side_errors": side_errors,
            "ambiguous_player_rows": ambiguous_rows,
            "unmatched_player_rows": unmatched_player_rows,
            "match_method_counts": dict(sorted(method_counts.items())),
            "confidence_counts": dict(sorted(confidence_counts.items())),
        },
        "decision": {
            "ready_for_player_id_join": ready,
            "ready_for_point_in_time_player_value_join": False,
            "ready_for_model_training": False,
            "ready_for_betting_edge_claim": False,
            "reason": "Identity QA only; multi-report coverage and point-in-time player values remain required.",
        },
        "guardrails": {
            "fuzzy_edit_distance_matching_used": False,
            "nearest_name_guessing_used": False,
            "team_and_season_preferred": True,
            "global_fallback_requires_unique_exact_identity": True,
            "ambiguous_names_blocked": True,
            "future_events_used_only_for_stable_identity_resolution": True,
            "player_names_or_reasons_in_map_output": False,
        },
    }
    (output_dir / "injury-player-identity-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def self_test(output_dir: Path) -> None:
    from historical_silver_schema import create_schema

    output_dir.mkdir(parents=True, exist_ok=True)
    db_path = output_dir / "fixture.sqlite"
    db = sqlite3.connect(db_path)
    create_schema(db)
    db.execute(
        "INSERT INTO games VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("g1", "2023-12-18", "2023-24", "1", "DEN", "2", "DAL", 100, 90, 4, 48.0, 1, 1, 1, ""),
    )
    aliases = [
        ("a1", "p1", "Dereck Lively II", "dereck lively ii", "dereck lively", "10", "DAL", "2023-24", "g1", "g1", 4, "nbastats_2023", ""),
        ("a2", "p2", "Nikola Jokic", "nikola jokic", "nikola jokic", "20", "DEN", "2023-24", "g1", "g1", 5, "nbastats_2023", ""),
        ("a3", "p3", "Steven Adams", "steven adams", "steven adams", "30", "MEM", "2022-23", "g0", "g0", 5, "nbastats_2022", ""),
    ]
    db.executemany("INSERT INTO player_aliases VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", aliases)
    db.commit()
    fixture_csv = output_dir / "snapshots.csv"
    with fixture_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["snapshot_record_id", "game_id", "team_abbr", "player_name"])
        writer.writeheader()
        writer.writerow({"snapshot_record_id": "s1", "game_id": "official:2023-12-18:DAL@DEN", "team_abbr": "DAL", "player_name": "Lively II, Dereck"})
        writer.writerow({"snapshot_record_id": "s2", "game_id": "official:2023-12-18:DAL@DEN", "team_abbr": "DEN", "player_name": "Jokić, Nikola"})
    report = match(read_snapshots(fixture_csv), db, db, output_dir / "result")
    db.close()
    assert report["quality"]["player_match_rate"] == 1.0, report
    assert report["quality"]["ambiguous_player_rows"] == 0, report
    assert report["decision"]["ready_for_player_id_join"] is True, report
    (output_dir / "self-test.json").write_text('{"passed":true}\n', encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-csv", type=Path)
    parser.add_argument("--silver", type=Path)
    parser.add_argument("--player-directory", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("player identity matcher self-test passed")
        return
    if not args.snapshot_csv or not args.silver:
        parser.error("--snapshot-csv and --silver are required unless --self-test is used")
    with tempfile.TemporaryDirectory(prefix="nbavl-player-identity-") as temp_name:
        temp_root = Path(temp_name)
        schedule_db = open_database(args.silver, temp_root, "schedule", {"games"})
        if args.player_directory:
            alias_db = open_database(args.player_directory, temp_root, "directory", {"player_aliases"})
        else:
            names = {row[0] for row in schedule_db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "player_aliases" not in names:
                schedule_db.close()
                raise ValueError("Silver database does not contain player_aliases and no --player-directory was supplied")
            alias_db = schedule_db
        report = match(read_snapshots(args.snapshot_csv), schedule_db, alias_db, args.output_dir)
        if alias_db is not schedule_db:
            alias_db.close()
        schedule_db.close()
    print(json.dumps(report["decision"], indent=2))
    if not report["decision"]["ready_for_player_id_join"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
