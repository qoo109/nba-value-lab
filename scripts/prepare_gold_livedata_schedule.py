#!/usr/bin/env python3
"""Create a temporary Gold schedule copy with NBA LiveData 10-digit game IDs.

The source Gold database is never modified. A private mapping CSV preserves the historical ID for
later feature joins and must not be committed or uploaded with public artifacts.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import re
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Any


def normalize_official_game_id(value: Any) -> str:
    raw = str(value or "").strip()
    if not re.fullmatch(r"\d{8}|\d{10}", raw):
        raise ValueError(f"unsupported historical game ID: {value!r}")
    return raw.zfill(10)


def gunzip(source: Path, destination: Path) -> None:
    with gzip.open(source, "rb") as src, destination.open("wb") as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)


def prepare(source: Path, output_db: Path, mapping_csv: Path) -> dict:
    output_db.parent.mkdir(parents=True, exist_ok=True)
    mapping_csv.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix.lower() == ".gz":
        gunzip(source, output_db)
    else:
        shutil.copy2(source, output_db)

    db = sqlite3.connect(output_db)
    tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    required = {"gold_matchup_features", "gold_team_game_features"}
    missing = sorted(required - tables)
    if missing:
        db.close()
        raise ValueError(f"Gold database missing tables: {missing}")

    game_ids = sorted({
        str(row[0]).strip()
        for row in db.execute("SELECT game_id FROM gold_matchup_features")
    })
    mapping = [(game_id, normalize_official_game_id(game_id)) for game_id in game_ids]
    official_ids = [item[1] for item in mapping]
    if len(official_ids) != len(set(official_ids)):
        db.close()
        raise ValueError("historical IDs collide after 10-digit normalization")

    db.execute("BEGIN")
    for historical_id, official_id in mapping:
        db.execute(
            "UPDATE gold_matchup_features SET game_id=? WHERE game_id=?",
            (official_id, historical_id),
        )
        db.execute(
            "UPDATE gold_team_game_features SET game_id=? WHERE game_id=?",
            (official_id, historical_id),
        )
    db.commit()

    matchup_count = int(db.execute("SELECT COUNT(*) FROM gold_matchup_features").fetchone()[0])
    team_count = int(db.execute("SELECT COUNT(*) FROM gold_team_game_features").fetchone()[0])
    invalid_matchups = int(db.execute(
        "SELECT COUNT(*) FROM gold_matchup_features WHERE length(game_id)<>10 OR game_id GLOB '*[^0-9]*'"
    ).fetchone()[0])
    invalid_teams = int(db.execute(
        "SELECT COUNT(*) FROM gold_team_game_features WHERE length(game_id)<>10 OR game_id GLOB '*[^0-9]*'"
    ).fetchone()[0])
    db.execute("VACUUM")
    db.close()

    with mapping_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["historical_game_id", "official_game_id"])
        writer.writerows(mapping)

    report = {
        "source_name": source.name,
        "historical_game_ids": len(mapping),
        "matchup_rows": matchup_count,
        "team_feature_rows": team_count,
        "invalid_matchup_ids_after_normalization": invalid_matchups,
        "invalid_team_ids_after_normalization": invalid_teams,
        "mapping_unique": len(official_ids) == len(set(official_ids)),
        "source_database_modified": False,
        "mapping_contains_player_data": False,
        "ready_for_livedata_requests": bool(mapping) and invalid_matchups == 0 and invalid_teams == 0,
    }
    report_path = mapping_csv.with_name("gold-livedata-id-adapter-report.json")
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def self_test(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    source = output_dir / "source.sqlite"
    db = sqlite3.connect(source)
    db.executescript(
        """
        CREATE TABLE gold_matchup_features (game_id TEXT PRIMARY KEY);
        CREATE TABLE gold_team_game_features (feature_id TEXT PRIMARY KEY, game_id TEXT);
        INSERT INTO gold_matchup_features VALUES ('22300061');
        INSERT INTO gold_team_game_features VALUES ('f1','22300061');
        INSERT INTO gold_team_game_features VALUES ('f2','22300061');
        """
    )
    db.commit()
    db.close()
    target = output_dir / "target.sqlite"
    mapping = output_dir / "map.csv"
    report = prepare(source, target, mapping)
    assert report["ready_for_livedata_requests"] is True, report
    check = sqlite3.connect(target)
    assert check.execute("SELECT game_id FROM gold_matchup_features").fetchone()[0] == "0022300061"
    check.close()
    original = sqlite3.connect(source)
    assert original.execute("SELECT game_id FROM gold_matchup_features").fetchone()[0] == "22300061"
    original.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold", type=Path)
    parser.add_argument("--output-db", type=Path)
    parser.add_argument("--mapping-csv", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.self_test:
        if not args.output_dir:
            parser.error("--output-dir is required with --self-test")
        self_test(args.output_dir)
        print("Gold LiveData schedule adapter self-test passed")
        return
    if not args.gold or not args.output_db or not args.mapping_csv:
        parser.error("--gold, --output-db and --mapping-csv are required")
    report = prepare(args.gold, args.output_db, args.mapping_csv)
    print(json.dumps(report, indent=2))
    if not report["ready_for_livedata_requests"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
