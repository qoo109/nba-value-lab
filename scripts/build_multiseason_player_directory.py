#!/usr/bin/env python3
"""Build a compact multi-season NBA Stats player identity directory."""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import shutil
import sqlite3
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from historical_phase2_core import download, extract, select_csv
from historical_silver_schema import stable_id
from player_identity_core import normalize_player_name, suffixless_player_name

VERSION = "multiseason-player-directory-v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def source_for_year(year: int) -> dict:
    return {
        "provider": "shufinskiy/nba_data",
        "season_label": f"{year}-{str(year + 1)[-2:]}",
        "url": f"https://github.com/shufinskiy/nba_data/raw/main/datasets/nbastats_{year}.tar.xz",
        "preferred_filename_contains": "nbastats",
    }


def collect_aliases(csv_path: Path, season_label: str) -> tuple[list[dict], dict]:
    buckets: dict[tuple[str, str, str], dict] = {}
    incomplete = 0
    unusable = 0
    rows_scanned = 0
    with csv_path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows_scanned += 1
            game_id = str(row.get("GAME_ID") or "").strip()
            for slot in (1, 2, 3):
                player_id = str(row.get(f"PLAYER{slot}_ID") or "").strip()
                player_name = str(row.get(f"PLAYER{slot}_NAME") or "").strip()
                if not player_id and not player_name:
                    continue
                if not player_id or not player_name:
                    incomplete += 1
                    continue
                name_key = normalize_player_name(player_name)
                if not name_key:
                    unusable += 1
                    continue
                suffixless_key = suffixless_player_name(player_name)
                team_id = str(row.get(f"PLAYER{slot}_TEAM_ID") or "").strip()
                team_abbr = str(row.get(f"PLAYER{slot}_TEAM_ABBREVIATION") or "").strip()
                key = (player_id, name_key, team_abbr)
                if key not in buckets:
                    buckets[key] = {
                        "player_id": player_id,
                        "player_name_key": name_key,
                        "player_name_key_suffixless": suffixless_key,
                        "team_id": team_id,
                        "team_abbr": team_abbr,
                        "season_label": season_label,
                        "raw_names": Counter(),
                        "first_game_id": game_id,
                        "last_game_id": game_id,
                        "event_appearances": 0,
                    }
                item = buckets[key]
                item["raw_names"][player_name] += 1
                if not item["team_id"] and team_id:
                    item["team_id"] = team_id
                item["last_game_id"] = game_id
                item["event_appearances"] += 1

    aliases = []
    for item in buckets.values():
        raw_name = item["raw_names"].most_common(1)[0][0]
        flags = []
        if not item["team_abbr"]:
            flags.append("team_abbr_unavailable")
        if len(item["raw_names"]) > 1:
            flags.append("multiple_raw_name_variants")
        aliases.append({
            **{key: value for key, value in item.items() if key != "raw_names"},
            "player_name_raw": raw_name,
            "quality_flags": ",".join(flags),
        })
    aliases.sort(key=lambda row: (row["season_label"], row["player_id"], row["team_abbr"], row["player_name_key"]))
    report = {
        "rows_scanned": rows_scanned,
        "alias_rows": len(aliases),
        "unique_player_ids": len({row["player_id"] for row in aliases}),
        "incomplete_player_identity_rows": incomplete,
        "unusable_player_name_rows": unusable,
    }
    return aliases, report


def create_directory_schema(db: sqlite3.Connection) -> None:
    db.executescript(
        """
        PRAGMA journal_mode=OFF;
        PRAGMA synchronous=OFF;
        PRAGMA temp_store=MEMORY;
        CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE player_aliases (
          player_alias_id TEXT PRIMARY KEY,
          player_id TEXT NOT NULL,
          player_name_raw TEXT NOT NULL,
          player_name_key TEXT NOT NULL,
          player_name_key_suffixless TEXT NOT NULL,
          team_id TEXT,
          team_abbr TEXT,
          season_label TEXT NOT NULL,
          first_game_id TEXT,
          last_game_id TEXT,
          event_appearances INTEGER NOT NULL,
          source_id TEXT NOT NULL,
          quality_flags TEXT NOT NULL,
          UNIQUE(player_id, player_name_key, team_abbr, season_label)
        );
        CREATE INDEX idx_directory_exact ON player_aliases(player_name_key, team_abbr, season_label);
        CREATE INDEX idx_directory_suffixless ON player_aliases(player_name_key_suffixless, team_abbr, season_label);
        CREATE INDEX idx_directory_player ON player_aliases(player_id, season_label);
        """
    )


def insert_aliases(db: sqlite3.Connection, aliases: list[dict]) -> None:
    rows = []
    for item in aliases:
        alias_id = stable_id(
            item["player_id"], item["player_name_key"], item["team_abbr"], item["season_label"]
        )
        rows.append((
            alias_id,
            item["player_id"],
            item["player_name_raw"],
            item["player_name_key"],
            item["player_name_key_suffixless"],
            item["team_id"],
            item["team_abbr"],
            item["season_label"],
            item["first_game_id"],
            item["last_game_id"],
            item["event_appearances"],
            f"nbastats_{item['season_label'][:4]}",
            item["quality_flags"],
        ))
    db.executemany("INSERT INTO player_aliases VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)


def build(years: list[int], output_dir: Path, max_download_mb: int) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    sqlite_path = output_dir / "player-directory.sqlite"
    gzip_path = output_dir / "player-directory.sqlite.gz"
    if sqlite_path.exists():
        sqlite_path.unlink()
    db = sqlite3.connect(sqlite_path)
    create_directory_schema(db)
    source_reports = []

    with tempfile.TemporaryDirectory(prefix="nbavl-player-directory-") as temp_name:
        temp = Path(temp_name)
        for year in years:
            source = source_for_year(year)
            archive = temp / f"nbastats_{year}.tar.xz"
            extracted = temp / f"nbastats_{year}-raw"
            extracted.mkdir()
            archive_info = download(source["url"], archive, max_download_mb * 1048576)
            archive_info["member_count"] = extract(archive, extracted)
            csv_path = select_csv(extracted, source)
            aliases, alias_report = collect_aliases(csv_path, source["season_label"])
            insert_aliases(db, aliases)
            source_reports.append({
                "season_label": source["season_label"],
                "source_url": source["url"],
                "archive": archive_info,
                "csv_name": csv_path.name,
                "csv_bytes": csv_path.stat().st_size,
                **alias_report,
            })
            db.commit()

    generated_at = utc_now()
    metadata = {
        "schema_version": VERSION,
        "generated_at": generated_at,
        "season_labels": ",".join(report["season_label"] for report in source_reports),
        "raw_archives_committed": "false",
        "identity_matching_only": "true",
    }
    db.executemany("INSERT INTO metadata VALUES (?,?)", metadata.items())
    total_rows = int(db.execute("SELECT COUNT(*) FROM player_aliases").fetchone()[0])
    unique_ids = int(db.execute("SELECT COUNT(DISTINCT player_id) FROM player_aliases").fetchone()[0])
    duplicate_ids = int(db.execute(
        "SELECT COUNT(*)-COUNT(DISTINCT player_alias_id) FROM player_aliases"
    ).fetchone()[0])
    season_counts = {
        row[0]: int(row[1])
        for row in db.execute(
            "SELECT season_label, COUNT(*) FROM player_aliases GROUP BY season_label ORDER BY season_label"
        )
    }
    db.commit()
    db.execute("VACUUM")
    db.close()
    with sqlite_path.open("rb") as source, gzip.open(gzip_path, "wb", compresslevel=6) as target:
        shutil.copyfileobj(source, target, length=1024 * 1024)
    sqlite_path.unlink()

    ready = (
        len(season_counts) == len(years)
        and total_rows >= 3000
        and unique_ids >= 1000
        and duplicate_ids == 0
        and all(report["unusable_player_name_rows"] == 0 for report in source_reports)
    )
    report = {
        "schema_version": VERSION,
        "generated_at": generated_at,
        "seasons": list(season_counts),
        "season_alias_counts": season_counts,
        "source_reports": source_reports,
        "outputs": {
            "database_gzip_bytes": gzip_path.stat().st_size,
            "player_alias_rows": total_rows,
            "unique_player_ids": unique_ids,
        },
        "quality": {
            "duplicate_player_alias_ids": duplicate_ids,
            "all_seasons_present": len(season_counts) == len(years),
        },
        "decision": {
            "ready_for_player_identity_matching": ready,
            "ready_for_model_training": False,
            "raw_data_public_commit_allowed": False,
        },
    }
    (output_dir / "player-directory-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def self_test(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "fixture.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        fields = [
            "GAME_ID", "PLAYER1_ID", "PLAYER1_NAME", "PLAYER1_TEAM_ID", "PLAYER1_TEAM_ABBREVIATION",
            "PLAYER2_ID", "PLAYER2_NAME", "PLAYER2_TEAM_ID", "PLAYER2_TEAM_ABBREVIATION",
            "PLAYER3_ID", "PLAYER3_NAME", "PLAYER3_TEAM_ID", "PLAYER3_TEAM_ABBREVIATION",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerow({
            "GAME_ID": "g1", "PLAYER1_ID": "p1", "PLAYER1_NAME": "Jokić, Nikola",
            "PLAYER1_TEAM_ID": "1", "PLAYER1_TEAM_ABBREVIATION": "DEN",
        })
        writer.writerow({
            "GAME_ID": "g2", "PLAYER1_ID": "p1", "PLAYER1_NAME": "Nikola Jokic",
            "PLAYER1_TEAM_ID": "1", "PLAYER1_TEAM_ABBREVIATION": "DEN",
        })
    aliases, report = collect_aliases(csv_path, "2023-24")
    assert report["alias_rows"] == 1, report
    assert aliases[0]["player_name_key"] == "nikola jokic", aliases
    assert aliases[0]["event_appearances"] == 2, aliases
    (output_dir / "self-test.json").write_text('{"passed":true}\n', encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--years-json", default="[2019,2020,2021,2022,2023]")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-download-mb", type=int, default=600)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("multi-season player directory self-test passed")
        return
    years = [int(value) for value in json.loads(args.years_json)]
    report = build(years, args.output_dir, args.max_download_mb)
    print(json.dumps(report["decision"], indent=2))
    if not report["decision"]["ready_for_player_identity_matching"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
