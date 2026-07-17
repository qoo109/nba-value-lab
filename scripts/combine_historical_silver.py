#!/usr/bin/env python3
"""Combine independently audited single-season Silver databases."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import shutil
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from historical_silver_schema import create_schema, gzip_file

TABLES = ("games", "pbp_events", "possessions", "team_game_features")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def gunzip_to(source: Path, destination: Path) -> None:
    with gzip.open(source, "rb") as src, destination.open("wb") as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)


def discover_sources(root: Path) -> list[Path]:
    paths = sorted(root.rglob("historical-silver.sqlite.gz"))
    if not paths:
        raise FileNotFoundError(f"No historical-silver.sqlite.gz files found below {root}")
    return paths


def table_counts(db: sqlite3.Connection) -> dict[str, int]:
    return {
        table: int(db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        for table in TABLES
    }


def duplicate_counts(db: sqlite3.Connection) -> dict[str, int]:
    queries = {
        "games": "SELECT COUNT(*)-COUNT(DISTINCT game_id) FROM games",
        "pbp_events": "SELECT COUNT(*)-COUNT(DISTINCT event_id) FROM pbp_events",
        "possessions": "SELECT COUNT(*)-COUNT(DISTINCT possession_id) FROM possessions",
        "team_game_features": (
            "SELECT COUNT(*)-COUNT(DISTINCT game_id || ':' || team_abbr) "
            "FROM team_game_features"
        ),
    }
    return {key: int(db.execute(sql).fetchone()[0]) for key, sql in queries.items()}


def metadata(db: sqlite3.Connection) -> dict[str, str]:
    try:
        return dict(db.execute("SELECT key, value FROM metadata"))
    except sqlite3.OperationalError:
        return {}


def write_preview(db: sqlite3.Connection, destination: Path) -> None:
    db.row_factory = sqlite3.Row
    seasons = [
        row[0]
        for row in db.execute("SELECT DISTINCT season_label FROM games ORDER BY season_label")
    ]
    payload: dict[str, Any] = {
        "schema_version": "multiseason-silver-v1",
        "raw_data_included": False,
        "seasons": seasons,
        "sample_games": {},
    }
    for season in seasons:
        payload["sample_games"][season] = [
            dict(row)
            for row in db.execute(
                "SELECT * FROM games WHERE season_label=? ORDER BY game_date, game_id LIMIT 2",
                (season,),
            )
        ]
    destination.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def merge_sources(sources: list[Path], output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    sqlite_path = output_dir / "historical-silver-multiseason.sqlite"
    gzip_path = output_dir / "historical-silver-multiseason.sqlite.gz"
    if sqlite_path.exists():
        sqlite_path.unlink()

    generated_at = utc_now()
    db = sqlite3.connect(sqlite_path)
    create_schema(db)
    manifest: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix="nbavl-combine-silver-") as temp_name:
        temp = Path(temp_name)
        for index, source in enumerate(sources):
            unpacked = temp / f"season-{index}.sqlite"
            gunzip_to(source, unpacked)
            source_db = sqlite3.connect(unpacked)
            seasons = [
                row[0]
                for row in source_db.execute(
                    "SELECT DISTINCT season_label FROM games ORDER BY season_label"
                )
            ]
            if len(seasons) != 1:
                source_db.close()
                raise ValueError(f"Expected one season in {source}, found {seasons}")
            source_counts = table_counts(source_db)
            source_metadata = metadata(source_db)
            source_db.close()

            db.execute("ATTACH DATABASE ? AS season_db", (str(unpacked),))
            for table in TABLES:
                db.execute(f"INSERT INTO {table} SELECT * FROM season_db.{table}")
            # SQLite cannot detach an attached database while its insert
            # transaction remains open. Commit first, then detach.
            db.commit()
            db.execute("DETACH DATABASE season_db")

            manifest.append({
                "season_label": seasons[0],
                "source_file": str(source),
                "tables": source_counts,
                "pbpstats_archive_sha256": source_metadata.get("pbpstats_archive_sha256"),
                "nbastats_archive_sha256": source_metadata.get("nbastats_archive_sha256"),
            })

    db.execute(
        """UPDATE pbp_events SET source_id='nbastats_' || substr((
        SELECT season_label FROM games WHERE games.game_id=pbp_events.game_id),1,4)"""
    )
    db.execute(
        """UPDATE possessions SET source_id='pbpstats_' || substr((
        SELECT season_label FROM games WHERE games.game_id=possessions.game_id),1,4)"""
    )

    manifest_json = json.dumps(
        manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    manifest_hash = hashlib.sha256(manifest_json.encode("utf-8")).hexdigest()
    combined_metadata = {
        "pipeline_name": "NBA Value Lab combined historical Silver",
        "schema_version": "multiseason-silver-v1",
        "generated_at": generated_at,
        "season_count": str(len(manifest)),
        "season_labels": ",".join(item["season_label"] for item in manifest),
        "source_manifest_sha256": manifest_hash,
        "source_manifest_json": manifest_json,
        "rating_points_source": "nbastats_official_final_score",
        "possession_points_usage": "qa_only",
        "raw_archives_committed": "false",
    }
    db.executemany("INSERT INTO metadata VALUES (?,?)", combined_metadata.items())
    db.commit()

    counts = table_counts(db)
    duplicates = duplicate_counts(db)
    seasons = [
        row[0]
        for row in db.execute("SELECT DISTINCT season_label FROM games ORDER BY season_label")
    ]
    season_game_counts = {
        row[0]: int(row[1])
        for row in db.execute(
            "SELECT season_label, COUNT(*) FROM games GROUP BY season_label ORDER BY season_label"
        )
    }
    write_preview(db, output_dir / "multiseason-silver-sample.json")
    db.execute("VACUUM")
    db.close()
    gzip_file(sqlite_path, gzip_path)
    sqlite_path.unlink()

    report = {
        "schema_version": "multiseason-silver-v1",
        "generated_at": generated_at,
        "source_manifest_sha256": manifest_hash,
        "seasons": seasons,
        "season_game_counts": season_game_counts,
        "source_manifest": manifest,
        "outputs": {"database_gzip_bytes": gzip_path.stat().st_size, "tables": counts},
        "quality": {
            "duplicate_rows": duplicates,
            "all_duplicate_checks_pass": all(value == 0 for value in duplicates.values()),
            "season_count": len(seasons),
        },
        "decision": {
            "ready_for_multiseason_gold": (
                len(seasons) >= 3
                and counts["games"] >= 3000
                and counts["team_game_features"] >= 6000
                and all(value == 0 for value in duplicates.values())
            ),
            "raw_data_public_commit_allowed": False,
        },
    }
    (output_dir / "multiseason-silver-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def build_fixture(path: Path, season: str, game_id: str) -> None:
    db = sqlite3.connect(path)
    create_schema(db)
    db.execute(
        "INSERT INTO games VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (game_id, f"{season[:4]}-10-01", season, "1", "AAA", "2", "BBB", 101, 99, 4, 48.0, 0, 0, None, ""),
    )
    rows = [
        (game_id, "AAA", "BBB", 1, 101, 99, 101, 99, 90, 90, 96.0, 112.2, 110.0, 2.2, 80, 40, 30, 12, 20, 15, 8, 10, .575, .10, .20, .25, 1, ""),
        (game_id, "BBB", "AAA", 0, 99, 101, 99, 101, 90, 90, 96.0, 110.0, 112.2, -2.2, 82, 39, 31, 11, 18, 14, 7, 11, .543, .11, .18, .22, 1, ""),
    ]
    db.executemany(
        "INSERT INTO team_game_features VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        rows,
    )
    db.executemany("INSERT INTO metadata VALUES (?,?)", [
        ("pbpstats_archive_sha256", season + "-pbp"),
        ("nbastats_archive_sha256", season + "-nba"),
    ])
    db.commit()
    db.close()


def self_test(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    fixture_root = output_dir / "fixtures"
    fixture_root.mkdir(exist_ok=True)
    sources: list[Path] = []
    for index, season in enumerate(("2021-22", "2022-23", "2023-24"), 1):
        sqlite_path = fixture_root / f"{season}.sqlite"
        gzip_path = fixture_root / season / "historical-silver.sqlite.gz"
        gzip_path.parent.mkdir()
        build_fixture(sqlite_path, season, f"g{index}")
        gzip_file(sqlite_path, gzip_path)
        sources.append(gzip_path)
    report = merge_sources(sources, output_dir / "result")
    assert report["quality"]["season_count"] == 3
    assert report["outputs"]["tables"]["games"] == 3
    assert report["outputs"]["tables"]["team_game_features"] == 6
    assert report["quality"]["all_duplicate_checks_pass"] is True
    (output_dir / "self-test.json").write_text('{"passed":true}\n', encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("multi-season Silver combiner self-test passed")
        return
    if not args.input_root:
        parser.error("--input-root is required unless --self-test is used")
    report = merge_sources(discover_sources(args.input_root), args.output_dir)
    print(json.dumps(report["decision"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
