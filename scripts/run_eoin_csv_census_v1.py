#!/usr/bin/env python3
"""Aggregate-only file census for the Eoin A Moore secondary-source pilot.

The runner inspects local CSV files and inventories Parquet assets. It never
downloads data, never emits raw rows, and never decides source qualification by
itself.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

EXPECTED_FILES = [
    "PlayerStatistics.csv",
    "TeamStatistics.csv",
    "Games.csv",
    "LeagueSchedule24_25.csv",
    "Players.csv",
    "TeamHistories.csv",
]

INVENTORY_SUFFIXES = {".csv", ".parquet"}

DATE_NAME_HINTS = ("date", "datetime", "timestamp", "time")
SEASON_NAME_HINTS = ("season", "season_year", "year")
GAME_ID_HINTS = ("game_id", "gameid", "game id")
TEAM_ID_HINTS = ("team_id", "teamid", "team id")
PLAYER_ID_HINTS = ("player_id", "playerid", "person_id", "player id")
SCORE_HINTS = ("pts", "points", "score")


class CensusError(RuntimeError):
    """Raised when the CSV input directory is unusable."""


def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def lowered(value: str) -> str:
    return value.strip().lower().replace("-", "_")


def contains_any(values: set[str], hints: tuple[str, ...]) -> bool:
    return any(any(hint in value for hint in hints) for value in values)


def detect_columns(columns: list[str], hints: tuple[str, ...]) -> list[str]:
    return [column for column in columns if any(hint in lowered(column) for hint in hints)]


def preferred_key(columns: list[str], role: str) -> list[str]:
    names = {lowered(column): column for column in columns}
    game_columns = [column for key, column in names.items() if any(hint in key for hint in GAME_ID_HINTS)]
    team_columns = [column for key, column in names.items() if any(hint in key for hint in TEAM_ID_HINTS)]
    player_columns = [column for key, column in names.items() if any(hint in key for hint in PLAYER_ID_HINTS)]

    if role == "games":
        return game_columns[:1]
    if role == "team_boxscore":
        return game_columns[:1] + team_columns[:1]
    if role == "player_boxscore":
        return game_columns[:1] + player_columns[:1]
    return []


def role_scores(filename: str, columns: list[str]) -> dict[str, int]:
    file_lower = filename.lower()
    names = {lowered(column) for column in columns}
    has_game_id = contains_any(names, GAME_ID_HINTS)
    has_team_id = contains_any(names, TEAM_ID_HINTS)
    has_player_id = contains_any(names, PLAYER_ID_HINTS)
    has_date = contains_any(names, DATE_NAME_HINTS)
    has_score = contains_any(names, SCORE_HINTS)

    return {
        "games": int("game" in file_lower) * 3 + int(has_game_id) * 3 + int(has_date) + int(has_score),
        "team_boxscore": int("team" in file_lower) * 3 + int(has_game_id) * 2 + int(has_team_id) * 3 + int(has_score),
        "player_boxscore": int("player" in file_lower) * 3 + int(has_game_id) * 2 + int(has_player_id) * 3 + int(has_score),
        "schedule": int("schedule" in file_lower) * 5 + int(has_date) + int(has_team_id),
    }


def summarize_file(path: Path) -> dict[str, Any]:
    size_bytes = path.stat().st_size
    if size_bytes == 0:
        raise CensusError(f"empty CSV file: {path.name}")

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        sample = handle.read(4096)
        handle.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample)
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(handle, dialect=dialect)
        columns = list(reader.fieldnames or [])
        if not columns:
            raise CensusError(f"missing CSV header: {path.name}")

        null_counts = Counter()
        distinct_values: dict[str, set[str]] = {
            column: set() for column in detect_columns(columns, DATE_NAME_HINTS + SEASON_NAME_HINTS)
        }
        role_score = role_scores(path.name, columns)
        best_role = max(role_score, key=role_score.get)
        key_columns = preferred_key(columns, best_role)
        key_counts: Counter[tuple[str, ...]] = Counter()
        key_null_rows = 0
        row_count = 0

        for row in reader:
            row_count += 1
            for column in columns:
                if not (row.get(column) or "").strip():
                    null_counts[column] += 1
            for column in distinct_values:
                value = (row.get(column) or "").strip()
                if value and len(distinct_values[column]) < 50:
                    distinct_values[column].add(value)
            if key_columns:
                key = tuple((row.get(column) or "").strip() for column in key_columns)
                if any(not item for item in key):
                    key_null_rows += 1
                else:
                    key_counts[key] += 1

    duplicate_key_groups = sum(1 for count in key_counts.values() if count > 1) if key_columns else None
    field_summaries = [
        {
            "name": column,
            "null_count": int(null_counts[column]),
            "observed_distinct_sample": sorted(distinct_values.get(column, set()))[:20],
            "sample_truncated": len(distinct_values.get(column, set())) > 20,
        }
        for column in columns
    ]

    return {
        "filename": path.name,
        "relative_path": path.name,
        "file_type": "csv",
        "size_bytes": size_bytes,
        "sha256": sha256_file(path),
        "row_count": row_count,
        "column_count": len(columns),
        "columns": field_summaries,
        "role_scores": role_score,
        "selected_key_columns": key_columns,
        "selected_key_null_rows": key_null_rows if key_columns else None,
        "selected_key_duplicate_group_count": duplicate_key_groups,
        "raw_rows_emitted": 0,
    }


def summarize_inventory_file(path: Path, input_dir: Path) -> dict[str, Any]:
    return {
        "filename": path.name,
        "relative_path": str(path.relative_to(input_dir)),
        "file_type": path.suffix.lower().lstrip(".") or "unknown",
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "row_count": None,
        "column_count": None,
        "columns": [],
        "raw_rows_emitted": 0,
        "note": "file-level inventory only; no Parquet rows were decoded",
    }


def summarize_roles(files: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    roles = ("games", "team_boxscore", "player_boxscore", "schedule")
    result: dict[str, list[dict[str, Any]]] = {}
    for role in roles:
        result[role] = sorted(
            (
                {"file": item["filename"], "score": int(item["role_scores"][role])}
                for item in files
                if int(item["role_scores"][role]) > 0
            ),
            key=lambda item: (-item["score"], item["file"]),
        )[:10]
    return result


def inspect_directory(input_dir: Path) -> dict[str, Any]:
    if not input_dir.exists() or not input_dir.is_dir():
        raise CensusError("input directory does not exist")

    found: dict[str, Path] = {}
    duplicate_names: dict[str, list[str]] = {}
    inventory_files: list[Path] = []
    for path in sorted(input_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in INVENTORY_SUFFIXES:
            continue
        inventory_files.append(path)
        if path.suffix.lower() != ".csv":
            continue
        if path.name in found:
            duplicate_names.setdefault(path.name, [str(found[path.name].relative_to(input_dir))])
            duplicate_names[path.name].append(str(path.relative_to(input_dir)))
            continue
        found[path.name] = path
    files = [summarize_file(path) | {"relative_path": str(path.relative_to(input_dir))} for path in found.values()]
    files = sorted(files, key=lambda item: item["relative_path"])
    non_csv_files = [
        summarize_inventory_file(path, input_dir)
        for path in inventory_files
        if path.suffix.lower() != ".csv"
    ]
    non_csv_files = sorted(non_csv_files, key=lambda item: item["relative_path"])
    missing = [name for name in EXPECTED_FILES if name not in found]
    extra_csv = sorted(name for name in found if name not in EXPECTED_FILES)

    return {
        "report_schema_version": "eoin-csv-census-v1",
        "report_type": "file_level_csv_census",
        "source_id": "kaggle_eoinamoore_historical_nba",
        "qualification_evaluated": False,
        "cross_source_audit_executed": False,
        "formal_qualification_outcome": None,
        "input": {
            "directory": str(input_dir),
            "expected_files": EXPECTED_FILES,
            "present_expected_files": [name for name in EXPECTED_FILES if name in found],
            "missing_expected_files": missing,
            "duplicate_csv_names": duplicate_names,
            "extra_csv_files": extra_csv,
            "inventory_suffixes": sorted(INVENTORY_SUFFIXES),
        },
        "aggregate": {
            "file_count": len(files) + len(non_csv_files),
            "csv_file_count": len(files),
            "non_csv_file_count": len(non_csv_files),
            "total_rows": sum(item["row_count"] for item in files),
            "raw_rows_emitted": 0,
            "raw_files_emitted": False,
        },
        "role_candidates": summarize_roles(files),
        "files": files,
        "non_csv_files": non_csv_files,
        "boundaries": {
            "input_modified": False,
            "raw_rows_in_report": 0,
            "raw_files_in_output": False,
            "existing_silver_replacement": False,
            "existing_gold_replacement": False,
            "model_metrics": False,
            "market_metrics": False,
            "formal_stake": 0,
        },
    }


def privacy_safe_sample(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "report_schema_version": report["report_schema_version"],
        "report_type": report["report_type"],
        "source_id": report["source_id"],
        "input": report["input"],
        "aggregate": report["aggregate"],
        "role_candidates": report["role_candidates"],
        "files": [
            {
                "filename": item["filename"],
                "size_bytes": item["size_bytes"],
                "sha256": item["sha256"],
                "row_count": item["row_count"],
                "column_count": item["column_count"],
                "columns": item["columns"],
                "role_scores": item["role_scores"],
                "selected_key_columns": item["selected_key_columns"],
                "selected_key_null_rows": item["selected_key_null_rows"],
                "selected_key_duplicate_group_count": item["selected_key_duplicate_group_count"],
            }
            for item in report["files"]
        ],
        "non_csv_files": report["non_csv_files"],
        "raw_rows_emitted": 0,
    }


def coverage_placeholder(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "report_schema_version": "eoin-csv-cross-source-coverage-v1",
        "source_id": report["source_id"],
        "pilot_season": "2023-24",
        "cross_source_audit_executed": False,
        "reason": "reference extraction and deterministic cross-source join are not part of the CSV census runner",
        "frozen_gates": {
            "minimum_reference_games": 1000,
            "game_identity_match_rate_minimum": 0.98,
            "final_score_match_rate_minimum": 0.98,
            "team_boxscore_coverage_minimum": 0.98,
            "player_boxscore_coverage_minimum": 0.95,
            "pbp_game_coverage_minimum_when_claimed": 0.95,
            "exact_duplicate_games_maximum": 0,
        },
        "qualification_evaluated": False,
        "formal_outcome": None,
        "raw_rows_emitted": 0,
    }


def write_reports(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "aggregate_schema_report.json": report,
        "aggregate_coverage_report.json": coverage_placeholder(report),
        "privacy_safe_schema_sample.json": privacy_safe_sample(report),
    }
    for filename, payload in outputs.items():
        (output_dir / filename).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def run_self_test(output_dir: Path | None) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        (root / "Games.csv").write_text(
            "game_id,game_date,home_team_id,away_team_id,home_pts,away_pts\n"
            "0022300001,2023-10-24,1,2,110,105\n",
            encoding="utf-8",
        )
        (root / "TeamStatistics.csv").write_text(
            "game_id,team_id,pts\n0022300001,1,110\n0022300001,2,105\n",
            encoding="utf-8",
        )
        (root / "PlayerStatistics.csv").write_text(
            "game_id,player_id,team_id,pts\n0022300001,101,1,30\n",
            encoding="utf-8",
        )
        (root / "LeagueSchedule25_26.csv").write_text(
            "game_id,game_date,home_team_id,away_team_id\n0022500001,2025-10-21,1,2\n",
            encoding="utf-8",
        )
        (root / "PlayByPlay.parquet").write_bytes(b"PAR1synthetic-metadata-only")
        report = inspect_directory(root)
        if report["aggregate"]["file_count"] != 5:
            raise AssertionError("unexpected synthetic file count")
        if report["aggregate"]["csv_file_count"] != 4:
            raise AssertionError("unexpected synthetic CSV file count")
        if report["aggregate"]["non_csv_file_count"] != 1:
            raise AssertionError("unexpected synthetic non-CSV file count")
        if report["aggregate"]["raw_rows_emitted"] != 0:
            raise AssertionError("raw row boundary failed")
        if not report["role_candidates"]["games"]:
            raise AssertionError("game role detection failed")
        if output_dir is not None:
            write_reports(report, output_dir)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("out/eoin-csv-census-v1"))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        run_self_test(args.output_dir)
        print("self-test: success")
        return 0

    if args.input_dir is None:
        parser.error("--input-dir is required unless --self-test is used")

    report = inspect_directory(args.input_dir)
    write_reports(report, args.output_dir)
    print(
        json.dumps(
            {
                "file_count": report["aggregate"]["file_count"],
                "missing_expected_files": report["input"]["missing_expected_files"],
                "qualification_evaluated": False,
                "raw_rows_emitted": 0,
                "total_rows": report["aggregate"]["total_rows"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
