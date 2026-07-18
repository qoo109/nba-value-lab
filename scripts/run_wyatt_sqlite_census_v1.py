#!/usr/bin/env python3
"""Read-only SQLite census runner for the Wyatt Walsh secondary-source pilot.

This module never downloads data, never modifies the input database, never emits
raw source rows, and never makes a source-qualification decision by itself.
Cross-source qualification remains a later, separately reviewed execution step.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote

SQLITE_HEADER = b"SQLite format 3\x00"
ACCEPTED_EXTENSIONS = {".sqlite", ".sqlite3", ".db"}
MINIMUM_SIZE_BYTES = 1_048_576
MAXIMUM_SIZE_BYTES = 2_147_483_648
DATE_NAME_HINTS = ("date", "datetime", "timestamp", "created_at", "updated_at")
SEASON_NAME_HINTS = ("season", "season_id", "season_year", "year")


class CensusError(RuntimeError):
    """Raised when the SQLite input violates the frozen structural contract."""


def quote_identifier(value: str) -> str:
    """Return a safely quoted SQLite identifier."""

    return '"' + value.replace('"', '""') + '"'


def sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def read_header(path: Path) -> bytes:
    with path.open("rb") as handle:
        return handle.read(len(SQLITE_HEADER))


def connect_read_only(path: Path) -> sqlite3.Connection:
    absolute = path.resolve()
    uri = f"file:{quote(absolute.as_posix())}?mode=ro&immutable=1"
    connection = sqlite3.connect(uri, uri=True, timeout=30.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    connection.execute("PRAGMA trusted_schema = OFF")
    return connection


def fetch_scalar(connection: sqlite3.Connection, sql: str, params: Iterable[Any] = ()) -> Any:
    row = connection.execute(sql, tuple(params)).fetchone()
    return None if row is None else row[0]


def inventory_objects(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT type, name, tbl_name, sql
        FROM sqlite_master
        WHERE type IN ('table', 'view')
          AND name NOT LIKE 'sqlite_%'
        ORDER BY type, name
        """
    ).fetchall()
    return [dict(row) for row in rows]


def table_columns(connection: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    rows = connection.execute(f"PRAGMA table_info({quote_identifier(table)})").fetchall()
    return [
        {
            "cid": int(row[0]),
            "name": str(row[1]),
            "declared_type": str(row[2] or ""),
            "not_null": bool(row[3]),
            "default_present": row[4] is not None,
            "primary_key_position": int(row[5]),
        }
        for row in rows
    ]


def table_indexes(connection: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in connection.execute(f"PRAGMA index_list({quote_identifier(table)})").fetchall():
        index_name = str(row[1])
        columns = [
            str(index_row[2])
            for index_row in connection.execute(
                f"PRAGMA index_info({quote_identifier(index_name)})"
            ).fetchall()
            if index_row[2] is not None
        ]
        result.append(
            {
                "name": index_name,
                "unique": bool(row[2]),
                "origin": str(row[3]) if len(row) > 3 else None,
                "partial": bool(row[4]) if len(row) > 4 else False,
                "columns": columns,
            }
        )
    return result


def table_foreign_keys(connection: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    rows = connection.execute(f"PRAGMA foreign_key_list({quote_identifier(table)})").fetchall()
    return [
        {
            "id": int(row[0]),
            "sequence": int(row[1]),
            "referenced_table": str(row[2]),
            "from_column": str(row[3]),
            "to_column": None if row[4] is None else str(row[4]),
            "on_update": str(row[5]),
            "on_delete": str(row[6]),
            "match": str(row[7]),
        }
        for row in rows
    ]


def detect_date_columns(columns: list[dict[str, Any]]) -> list[str]:
    detected: list[str] = []
    for column in columns:
        lowered = column["name"].lower()
        if any(hint in lowered for hint in DATE_NAME_HINTS):
            detected.append(column["name"])
    return detected


def detect_season_columns(columns: list[dict[str, Any]]) -> list[str]:
    detected: list[str] = []
    for column in columns:
        lowered = column["name"].lower()
        if lowered in SEASON_NAME_HINTS or lowered.startswith("season_"):
            detected.append(column["name"])
    return detected


def aggregate_min_max(
    connection: sqlite3.Connection,
    table: str,
    column: str,
) -> dict[str, Any]:
    query = (
        f"SELECT MIN({quote_identifier(column)}), MAX({quote_identifier(column)}), "
        f"SUM(CASE WHEN {quote_identifier(column)} IS NULL THEN 1 ELSE 0 END) "
        f"FROM {quote_identifier(table)}"
    )
    row = connection.execute(query).fetchone()
    return {
        "minimum": None if row[0] is None else str(row[0]),
        "maximum": None if row[1] is None else str(row[1]),
        "null_count": int(row[2] or 0),
    }


def aggregate_distinct_sample(
    connection: sqlite3.Connection,
    table: str,
    column: str,
    limit: int = 20,
) -> dict[str, Any]:
    distinct_count = int(
        fetch_scalar(
            connection,
            f"SELECT COUNT(DISTINCT {quote_identifier(column)}) FROM {quote_identifier(table)}",
        )
        or 0
    )
    rows = connection.execute(
        f"SELECT DISTINCT {quote_identifier(column)} "
        f"FROM {quote_identifier(table)} "
        f"WHERE {quote_identifier(column)} IS NOT NULL "
        f"ORDER BY {quote_identifier(column)} LIMIT ?",
        (limit,),
    ).fetchall()
    return {
        "distinct_count": distinct_count,
        "sample_values": [str(row[0]) for row in rows],
        "sample_truncated": distinct_count > limit,
    }


def role_scores(table: str, columns: list[dict[str, Any]]) -> dict[str, int]:
    table_lower = table.lower()
    names = {column["name"].lower() for column in columns}

    def contains_any(values: Iterable[str], hints: Iterable[str]) -> bool:
        return any(any(hint in value for hint in hints) for value in values)

    has_game_id = contains_any(names, ("game_id", "gameid"))
    has_team_id = contains_any(names, ("team_id", "teamid"))
    has_player_id = contains_any(names, ("player_id", "playerid", "person_id"))
    has_event = contains_any(names, ("event", "action", "period", "clock", "pctimestring"))
    has_score = contains_any(names, ("score", "pts", "points"))
    has_date = contains_any(names, DATE_NAME_HINTS)

    return {
        "games": int("game" in table_lower) * 3 + int(has_game_id) * 3 + int(has_date) + int(has_score),
        "team_boxscore": int("team" in table_lower) * 3 + int(has_game_id) * 2 + int(has_team_id) * 3 + int(has_score),
        "player_boxscore": int("player" in table_lower) * 3 + int(has_game_id) * 2 + int(has_player_id) * 3,
        "play_by_play": int(any(hint in table_lower for hint in ("play", "pbp", "event", "action"))) * 3
        + int(has_game_id) * 2
        + int(has_event) * 3,
    }


def primary_key_columns(columns: list[dict[str, Any]]) -> list[str]:
    return [
        column["name"]
        for column in sorted(columns, key=lambda item: item["primary_key_position"])
        if column["primary_key_position"] > 0
    ]


def null_count_for_columns(
    connection: sqlite3.Connection,
    table: str,
    columns: list[str],
) -> int | None:
    if not columns:
        return None
    condition = " OR ".join(f"{quote_identifier(column)} IS NULL" for column in columns)
    return int(
        fetch_scalar(
            connection,
            f"SELECT COUNT(*) FROM {quote_identifier(table)} WHERE {condition}",
        )
        or 0
    )


def duplicate_group_count(
    connection: sqlite3.Connection,
    table: str,
    columns: list[str],
) -> int | None:
    if not columns:
        return None
    group_columns = ", ".join(quote_identifier(column) for column in columns)
    query = (
        "SELECT COUNT(*) FROM ("
        f"SELECT 1 FROM {quote_identifier(table)} "
        f"GROUP BY {group_columns} HAVING COUNT(*) > 1"
        ")"
    )
    return int(fetch_scalar(connection, query) or 0)


def inspect_table(connection: sqlite3.Connection, table: str) -> dict[str, Any]:
    columns = table_columns(connection, table)
    pk_columns = primary_key_columns(columns)
    date_columns = detect_date_columns(columns)
    season_columns = detect_season_columns(columns)
    row_count = int(fetch_scalar(connection, f"SELECT COUNT(*) FROM {quote_identifier(table)}") or 0)

    return {
        "name": table,
        "row_count": row_count,
        "column_count": len(columns),
        "columns": columns,
        "primary_key_columns": pk_columns,
        "primary_key_null_count": null_count_for_columns(connection, table, pk_columns),
        "primary_key_duplicate_group_count": duplicate_group_count(connection, table, pk_columns),
        "indexes": table_indexes(connection, table),
        "foreign_keys": table_foreign_keys(connection, table),
        "date_columns": {
            column: aggregate_min_max(connection, table, column) for column in date_columns
        },
        "season_columns": {
            column: aggregate_distinct_sample(connection, table, column)
            for column in season_columns
        },
        "role_scores": role_scores(table, columns),
    }


def summarize_roles(tables: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    roles = ("games", "team_boxscore", "player_boxscore", "play_by_play")
    result: dict[str, list[dict[str, Any]]] = {}
    for role in roles:
        ranked = sorted(
            (
                {"table": table["name"], "score": int(table["role_scores"][role])}
                for table in tables
                if int(table["role_scores"][role]) > 0
            ),
            key=lambda item: (-item["score"], item["table"]),
        )
        result[role] = ranked[:10]
    return result


def inspect_database(path: Path, *, enforce_size: bool = True, synthetic: bool = False) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        raise CensusError("input file does not exist")
    extension = path.suffix.lower()
    if extension not in ACCEPTED_EXTENSIONS:
        raise CensusError(f"unsupported extension: {extension}")

    size_bytes = path.stat().st_size
    if enforce_size and size_bytes < MINIMUM_SIZE_BYTES:
        raise CensusError("input file is below the frozen minimum size")
    if size_bytes > MAXIMUM_SIZE_BYTES:
        raise CensusError("input file exceeds the frozen maximum size")

    header_ok = read_header(path) == SQLITE_HEADER
    if not header_ok:
        raise CensusError("SQLite header check failed")

    digest = sha256_file(path)
    with connect_read_only(path) as connection:
        integrity_rows = [str(row[0]) for row in connection.execute("PRAGMA integrity_check").fetchall()]
        integrity_ok = integrity_rows == ["ok"]
        if not integrity_ok:
            raise CensusError("SQLite integrity_check did not return ok")

        objects = inventory_objects(connection)
        table_names = [item["name"] for item in objects if item["type"] == "table"]
        view_names = [item["name"] for item in objects if item["type"] == "view"]
        tables = [inspect_table(connection, table) for table in table_names]

        database_metadata = {
            "integrity_check": integrity_rows,
            "page_count": int(fetch_scalar(connection, "PRAGMA page_count") or 0),
            "page_size": int(fetch_scalar(connection, "PRAGMA page_size") or 0),
            "freelist_count": int(fetch_scalar(connection, "PRAGMA freelist_count") or 0),
            "user_version": int(fetch_scalar(connection, "PRAGMA user_version") or 0),
            "application_id": int(fetch_scalar(connection, "PRAGMA application_id") or 0),
            "schema_version": int(fetch_scalar(connection, "PRAGMA schema_version") or 0),
            "table_count": len(table_names),
            "view_count": len(view_names),
            "view_names": view_names,
        }

    total_rows = sum(table["row_count"] for table in tables)
    return {
        "report_schema_version": "wyatt-sqlite-census-runner-v1",
        "report_type": "synthetic_self_test" if synthetic else "file_level_schema_census",
        "qualification_evaluated": False,
        "cross_source_audit_executed": False,
        "formal_qualification_outcome": None,
        "input": {
            "filename": path.name,
            "extension": extension,
            "size_bytes": size_bytes,
            "sha256": digest,
            "sqlite_header_ok": header_ok,
            "opened_read_only": True,
        },
        "database": database_metadata,
        "aggregate": {
            "table_count": len(tables),
            "total_table_rows": total_rows,
            "raw_rows_emitted": 0,
            "raw_database_emitted": False,
        },
        "role_candidates": summarize_roles(tables),
        "tables": tables,
        "boundaries": {
            "input_modified": False,
            "raw_rows_in_report": 0,
            "raw_database_in_output": False,
            "existing_silver_replacement": False,
            "existing_gold_replacement": False,
            "model_metrics": False,
            "market_metrics": False,
            "formal_stake": 0,
        },
    }


def privacy_safe_schema_sample(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "report_schema_version": report["report_schema_version"],
        "report_type": report["report_type"],
        "input": {
            "filename": report["input"]["filename"],
            "size_bytes": report["input"]["size_bytes"],
            "sha256": report["input"]["sha256"],
        },
        "database": report["database"],
        "role_candidates": report["role_candidates"],
        "tables": [
            {
                "name": table["name"],
                "row_count": table["row_count"],
                "columns": table["columns"],
                "primary_key_columns": table["primary_key_columns"],
                "indexes": table["indexes"],
                "foreign_keys": table["foreign_keys"],
                "date_columns": table["date_columns"],
                "season_columns": table["season_columns"],
                "role_scores": table["role_scores"],
            }
            for table in report["tables"]
        ],
        "raw_rows_emitted": 0,
    }


def coverage_placeholder(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "report_schema_version": "wyatt-sqlite-cross-source-coverage-v1",
        "input_sha256": report["input"]["sha256"],
        "pilot_season": "2023-24",
        "cross_source_audit_executed": False,
        "reason": "reference extraction and deterministic cross-source join are not part of the schema runner",
        "frozen_gates": {
            "minimum_reference_games": 1000,
            "game_identity_match_rate_minimum": 0.98,
            "final_score_match_rate_minimum": 0.98,
            "team_boxscore_coverage_minimum": 0.98,
            "player_boxscore_coverage_minimum": 0.95,
            "pbp_game_coverage_minimum_when_claimed": 0.95,
            "exact_duplicate_game_count_maximum": 0,
        },
        "qualification_evaluated": False,
        "formal_outcome": None,
        "raw_rows_emitted": 0,
    }


def input_required_report() -> dict[str, Any]:
    return {
        "report_schema_version": "wyatt-sqlite-census-runner-v1",
        "formal_state": "INPUT_FILE_REQUIRED",
        "runner_ready": True,
        "input_file_present": False,
        "database_opened": False,
        "qualification_evaluated": False,
        "raw_rows_emitted": 0,
        "existing_silver_replacement": False,
        "existing_gold_replacement": False,
        "model_metrics": False,
        "market_metrics": False,
        "formal_stake": 0,
    }


def build_synthetic_database(path: Path) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.executescript(
            """
            CREATE TABLE game (
                game_id TEXT PRIMARY KEY,
                game_date TEXT NOT NULL,
                season TEXT NOT NULL,
                home_team_id INTEGER NOT NULL,
                away_team_id INTEGER NOT NULL,
                home_score INTEGER NOT NULL,
                away_score INTEGER NOT NULL
            );
            CREATE TABLE team (
                game_id TEXT NOT NULL,
                team_id INTEGER NOT NULL,
                pts INTEGER NOT NULL,
                PRIMARY KEY (game_id, team_id),
                FOREIGN KEY (game_id) REFERENCES game(game_id)
            );
            CREATE TABLE player (
                game_id TEXT NOT NULL,
                player_id INTEGER NOT NULL,
                team_id INTEGER NOT NULL,
                pts INTEGER NOT NULL,
                PRIMARY KEY (game_id, player_id),
                FOREIGN KEY (game_id) REFERENCES game(game_id)
            );
            CREATE TABLE play_by_play (
                game_id TEXT NOT NULL,
                event_num INTEGER NOT NULL,
                period INTEGER NOT NULL,
                game_clock TEXT NOT NULL,
                score TEXT,
                PRIMARY KEY (game_id, event_num),
                FOREIGN KEY (game_id) REFERENCES game(game_id)
            );
            CREATE INDEX idx_game_date ON game(game_date);
            CREATE INDEX idx_pbp_game_period ON play_by_play(game_id, period);
            """
        )
        connection.execute(
            "INSERT INTO game VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("0022300001", "2023-10-24", "2023-24", 1, 2, 110, 105),
        )
        connection.executemany(
            "INSERT INTO team VALUES (?, ?, ?)",
            [("0022300001", 1, 110), ("0022300001", 2, 105)],
        )
        connection.executemany(
            "INSERT INTO player VALUES (?, ?, ?, ?)",
            [("0022300001", 101, 1, 30), ("0022300001", 201, 2, 28)],
        )
        connection.executemany(
            "INSERT INTO play_by_play VALUES (?, ?, ?, ?, ?)",
            [
                ("0022300001", 1, 1, "PT12M00.00S", "0-0"),
                ("0022300001", 2, 1, "PT11M42.00S", "2-0"),
            ],
        )
        connection.commit()
    finally:
        connection.close()


def write_reports(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "aggregate_schema_report.json": report,
        "aggregate_coverage_report.json": coverage_placeholder(report),
        "privacy_safe_schema_sample.json": privacy_safe_schema_sample(report),
    }
    for filename, payload in outputs.items():
        (output_dir / filename).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def run_self_test(output_dir: Path | None) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        database_path = Path(temporary) / "synthetic.sqlite"
        build_synthetic_database(database_path)
        before = sha256_file(database_path)
        report = inspect_database(database_path, enforce_size=False, synthetic=True)
        after = sha256_file(database_path)
        if before != after:
            raise AssertionError("read-only census changed the synthetic database")
        if report["database"]["integrity_check"] != ["ok"]:
            raise AssertionError("synthetic integrity check failed")
        if report["database"]["table_count"] != 4:
            raise AssertionError("unexpected synthetic table count")
        if report["aggregate"]["raw_rows_emitted"] != 0:
            raise AssertionError("raw row boundary failed")
        if not report["role_candidates"]["play_by_play"]:
            raise AssertionError("play-by-play role detection failed")
        if output_dir is not None:
            write_reports(report, output_dir)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("out/wyatt-sqlite-census-v1"))
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--write-input-required-report", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        run_self_test(args.output_dir)
        print("self-test: success")
        return 0

    if args.write_input_required_report:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        path = args.output_dir / "input-required-report.json"
        path.write_text(json.dumps(input_required_report(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(path)
        return 0

    if args.input is None:
        parser.error("--input is required unless --self-test or --write-input-required-report is used")

    report = inspect_database(args.input)
    write_reports(report, args.output_dir)
    print(json.dumps({
        "input_sha256": report["input"]["sha256"],
        "table_count": report["database"]["table_count"],
        "total_table_rows": report["aggregate"]["total_table_rows"],
        "qualification_evaluated": False,
        "raw_rows_emitted": 0,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
