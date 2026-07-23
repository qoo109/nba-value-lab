#!/usr/bin/env python3
"""Build a deterministic aggregate semantic manifest for Historical Gold.

The module is offline and read-only.  It accepts a decompressed SQLite file and
a validated freeze policy.  Verification of the compressed GitHub Artifact
archive remains the responsibility of a separately approved workflow.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sqlite3
import unicodedata
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

MANIFEST_SCHEMA_VERSION = "historical-gold-5826-complete-corpus-freeze-manifest-v1"
IMPLEMENTATION_DESIGN_ID = (
    "HISTORICAL-GOLD-5826-COMPLETE-CORPUS-FREEZE-MANIFEST-"
    "IMPLEMENTATION-DESIGN-2026-07-23-001"
)
VALID_POLICY_SCHEMA = "historical-gold-5826-complete-corpus-freeze-policy-v1"
VALID_POLICY_STATE = "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_POLICY_DESIGN_VALIDATED"
VALID_POLICY_ROLE = "DESIGN_ONLY_NO_CORPUS_FREEZE_EXECUTION"
REQUIRED_TABLES = (
    "gold_team_game_features",
    "gold_matchup_features",
    "gold_metadata",
)
TEAM_SORT_ORDER = ("season_label", "game_date", "game_id", "team_abbr")
MATCHUP_SORT_ORDER = ("game_date", "game_id")
VOLATILE_COLUMNS = ("feature_generated_at",)
VOLATILE_METADATA_KEYS = ("feature_generated_at",)
REQUIRED_METADATA_KEYS = (
    "pipeline_name",
    "schema_version",
    "feature_version",
    "source_version",
    "point_in_time_rule",
    "same_day_games_policy",
    "season_history_policy",
    "season_labels",
)
EXPECTED_MANIFEST_TOP_LEVEL_KEYS = frozenset(
    {
        "schema_version",
        "formal_state",
        "implementation_design_id",
        "policy_id",
        "source_binding",
        "gold_metadata_identity",
        "season_labels",
        "tables",
        "metadata_semantic_identity",
        "corpus_semantic_sha256",
        "point_in_time_validation",
        "duplicate_validation",
        "aggregate_validation",
        "privacy_boundaries",
        "scientific_boundaries",
        "formal_stake",
    }
)

FORBIDDEN_OUTPUT_KEYS = frozenset(
    {
        "game_ids",
        "game_dates",
        "team_codes",
        "feature_ids",
        "raw_rows",
        "sample_rows",
        "row_level_hashes",
        "individual_feature_values",
        "player_information",
        "market_prices",
    }
)
ROLLING_WINDOWS = (5, 10, 20)
BASE_METRICS = (
    "pace",
    "off_rtg",
    "def_rtg",
    "net_rtg",
    "efg_pct",
    "tov_pct_estimated",
    "orb_pct_fg_miss_estimate",
    "free_throw_rate",
    "points",
    "opponent_points",
    "margin",
    "win",
)


class ManifestValidationError(RuntimeError):
    """Raised when any fail-closed validation gate is not satisfied."""


def _rolling_schema() -> list[tuple[str, str, int, int]]:
    output: list[tuple[str, str, int, int]] = []
    for window in ROLLING_WINDOWS:
        for metric in BASE_METRICS:
            output.append((f"{metric}_last_{window}", "REAL", 0, 0))
        output.append((f"net_rtg_std_last_{window}", "REAL", 0, 0))
        output.append((f"sample_size_last_{window}", "INTEGER", 1, 0))
    return output


EXPECTED_SCHEMAS: dict[str, tuple[tuple[str, str, int, int], ...]] = {
    "gold_metadata": (
        ("key", "TEXT", 0, 1),
        ("value", "TEXT", 1, 0),
    ),
    "gold_team_game_features": tuple(
        [
            ("feature_id", "TEXT", 0, 1),
            ("game_id", "TEXT", 1, 0),
            ("game_date", "TEXT", 1, 0),
            ("season_label", "TEXT", 1, 0),
            ("team_abbr", "TEXT", 1, 0),
            ("opponent_abbr", "TEXT", 1, 0),
            ("is_home", "INTEGER", 1, 0),
            ("feature_cutoff_time", "TEXT", 1, 0),
            ("prior_games", "INTEGER", 1, 0),
            ("prior_home_games", "INTEGER", 1, 0),
            ("prior_away_games", "INTEGER", 1, 0),
            ("days_rest", "INTEGER", 0, 0),
            ("is_back_to_back", "INTEGER", 1, 0),
            ("games_last_3_days", "INTEGER", 1, 0),
            ("games_last_7_days", "INTEGER", 1, 0),
            ("home_off_rtg_prior", "REAL", 0, 0),
            ("home_def_rtg_prior", "REAL", 0, 0),
            ("home_net_rtg_prior", "REAL", 0, 0),
            ("home_win_rate_prior", "REAL", 0, 0),
            ("away_off_rtg_prior", "REAL", 0, 0),
            ("away_def_rtg_prior", "REAL", 0, 0),
            ("away_net_rtg_prior", "REAL", 0, 0),
            ("away_win_rate_prior", "REAL", 0, 0),
            ("opponent_strength_net_rtg_last_10", "REAL", 0, 0),
            ("opponent_adjusted_net_rtg_last_10", "REAL", 0, 0),
            ("trend_net_rtg_last_5_vs_10", "REAL", 0, 0),
            *_rolling_schema(),
            ("source_version", "TEXT", 1, 0),
            ("feature_version", "TEXT", 1, 0),
            ("feature_generated_at", "TEXT", 1, 0),
            ("quality_flags", "TEXT", 1, 0),
        ]
    ),
    "gold_matchup_features": (
        ("matchup_feature_id", "TEXT", 0, 1),
        ("game_id", "TEXT", 1, 0),
        ("game_date", "TEXT", 1, 0),
        ("home_team_abbr", "TEXT", 1, 0),
        ("away_team_abbr", "TEXT", 1, 0),
        ("home_feature_id", "TEXT", 1, 0),
        ("away_feature_id", "TEXT", 1, 0),
        ("net_rtg_last_5_diff", "REAL", 0, 0),
        ("net_rtg_last_10_diff", "REAL", 0, 0),
        ("net_rtg_last_20_diff", "REAL", 0, 0),
        ("pace_last_10_diff", "REAL", 0, 0),
        ("efg_pct_last_10_diff", "REAL", 0, 0),
        ("tov_pct_last_10_diff", "REAL", 0, 0),
        ("orb_pct_last_10_diff", "REAL", 0, 0),
        ("free_throw_rate_last_10_diff", "REAL", 0, 0),
        ("rest_days_diff", "REAL", 0, 0),
        ("prior_games_min", "INTEGER", 1, 0),
        ("evidence_coverage", "REAL", 1, 0),
        ("source_version", "TEXT", 1, 0),
        ("feature_version", "TEXT", 1, 0),
        ("feature_generated_at", "TEXT", 1, 0),
        ("quality_flags", "TEXT", 1, 0),
    ),
}

EXPECTED_UNIQUE_KEYS: dict[str, frozenset[tuple[str, ...]]] = {
    "gold_metadata": frozenset({("key",)}),
    "gold_team_game_features": frozenset({("feature_id",), ("game_id", "team_abbr")}),
    "gold_matchup_features": frozenset({("matchup_feature_id",), ("game_id",)}),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _canonical_json_bytes(value: Any, *, newline: bool = False) -> bytes:
    data = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return data + (b"\n" if newline else b"")


def _normalise_text(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def _canonical_value(
    value: Any,
    *,
    declared_type: str,
    notnull: int,
    table: str,
    column: str,
) -> dict[str, str]:
    if value is None:
        if notnull:
            raise ManifestValidationError(f"{table}.{column} is NULL but declared NOT NULL")
        return {"type": "null"}

    declared = declared_type.upper()
    if isinstance(value, (bytes, bytearray, memoryview)):
        raise ManifestValidationError(f"{table}.{column} contains a prohibited BLOB value")

    if declared == "TEXT":
        if not isinstance(value, str):
            raise ManifestValidationError(
                f"{table}.{column} expected TEXT, received {type(value).__name__}"
            )
        return {"type": "text", "value": _normalise_text(value)}

    if declared == "INTEGER":
        if type(value) is not int:
            raise ManifestValidationError(
                f"{table}.{column} expected INTEGER, received {type(value).__name__}"
            )
        return {"type": "int", "value": str(value)}

    if declared == "REAL":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ManifestValidationError(
                f"{table}.{column} expected REAL, received {type(value).__name__}"
            )
        number = float(value)
        if not math.isfinite(number):
            raise ManifestValidationError(f"{table}.{column} contains a non-finite REAL")
        if number == 0.0:
            number = 0.0
        return {"type": "real", "value": number.hex()}

    raise ManifestValidationError(
        f"{table}.{column} has unsupported declared type {declared_type!r}"
    )


def _quote_identifier(identifier: str) -> str:
    if not identifier or "\x00" in identifier:
        raise ManifestValidationError("invalid SQLite identifier")
    return '"' + identifier.replace('"', '""') + '"'


def _read_policy(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestValidationError(f"cannot read policy: {exc}") from exc
    if not isinstance(value, dict):
        raise ManifestValidationError("policy must be a JSON object")
    return value


def _require(condition: Any, message: str) -> None:
    if not condition:
        raise ManifestValidationError(message)


def validate_policy(policy: Mapping[str, Any]) -> dict[str, Any]:
    _require(policy.get("schema_version") == VALID_POLICY_SCHEMA, "unexpected policy schema")
    _require(policy.get("formal_state") == VALID_POLICY_STATE, "policy formal state is not validated")
    _require(policy.get("policy_role") == VALID_POLICY_ROLE, "unexpected policy role")
    policy_id = policy.get("policy_id")
    _require(isinstance(policy_id, str) and bool(policy_id.strip()), "policy_id is required")

    scope = policy.get("governed_scope")
    identity = policy.get("freeze_identity_design")
    bindings = policy.get("immutable_evidence_bindings")
    access = policy.get("implementation_access_policy")
    decision = policy.get("decision")
    for name, value in (
        ("governed_scope", scope),
        ("freeze_identity_design", identity),
        ("immutable_evidence_bindings", bindings),
        ("implementation_access_policy", access),
        ("decision", decision),
    ):
        _require(isinstance(value, Mapping), f"{name} must be an object")

    seasons = scope.get("seasons")
    _require(
        isinstance(seasons, list)
        and seasons
        and all(isinstance(item, str) and item.strip() for item in seasons),
        "governed seasons must be a non-empty text list",
    )
    expected_seasons = sorted({_normalise_text(item.strip()) for item in seasons})
    _require(len(expected_seasons) == len(seasons), "governed seasons must be unique")

    team_rows = identity.get("team_table_expected_rows")
    matchup_rows = identity.get("matchup_table_expected_rows")
    _require(type(team_rows) is int and team_rows > 0, "team expected rows must be positive")
    _require(type(matchup_rows) is int and matchup_rows > 0, "matchup expected rows must be positive")
    _require(team_rows == scope.get("gold_team_game_features"), "team row counts disagree")
    _require(matchup_rows == scope.get("gold_matchup_features"), "matchup row counts disagree")
    _require(team_rows == matchup_rows * 2, "team row count must be twice matchup row count")

    _require(tuple(identity.get("required_tables", ())) == REQUIRED_TABLES, "required table set changed")
    _require(tuple(identity.get("team_table_sort_order", ())) == TEAM_SORT_ORDER, "team sort order changed")
    _require(
        tuple(identity.get("matchup_table_sort_order", ())) == MATCHUP_SORT_ORDER,
        "matchup sort order changed",
    )
    _require(
        tuple(identity.get("volatile_columns_excluded_from_semantic_digest", ()))
        == VOLATILE_COLUMNS,
        "volatile column policy changed",
    )
    _require(
        tuple(identity.get("volatile_metadata_keys_excluded_from_semantic_digest", ()))
        == VOLATILE_METADATA_KEYS,
        "volatile metadata policy changed",
    )
    _require(
        tuple(identity.get("required_metadata_keys", ())) == REQUIRED_METADATA_KEYS,
        "required metadata key contract changed",
    )
    _require(identity.get("nonfinite_numeric_values_allowed") is False, "non-finite values must be blocked")
    _require(identity.get("duplicate_primary_keys_allowed") is False, "duplicates must be blocked")
    _require(scope.get("row_exclusions_allowed") is False, "row exclusions must remain disabled")
    _require(scope.get("partial_freeze_allowed") is False, "partial freeze must remain disabled")
    _require(scope.get("gold_point_in_time_violations") == 0, "point-in-time violations must be zero")
    _require(scope.get("gold_point_in_time_passed") is True, "point-in-time validation must pass")
    _require(scope.get("documented_source_exceptions_remaining") == 0, "source exceptions remain")
    _require(access.get("database_write_allowed") is False, "database writes must remain disabled")
    _require(access.get("database_mutation_allowed") is False, "database mutation must remain disabled")
    maximum_output_bytes = access.get("aggregate_manifest_max_bytes")
    _require(type(maximum_output_bytes) is int and 0 < maximum_output_bytes <= 1048576, "invalid output limit")
    _require(decision.get("formal_stake") == 0, "formal Stake must remain zero")

    artifact_id = bindings.get("adopted_artifact_id")
    artifact_digest = bindings.get("adopted_artifact_digest")
    gold_binary_sha = bindings.get("historical_gold_sha256")
    _require(type(artifact_id) is int and artifact_id >= 0, "artifact id is invalid")
    _require(isinstance(artifact_digest, str) and artifact_digest.startswith("sha256:"), "artifact digest invalid")
    _require(isinstance(gold_binary_sha, str) and gold_binary_sha.startswith("sha256:"), "Gold binary SHA invalid")

    return {
        "policy_id": policy_id,
        "seasons": expected_seasons,
        "team_rows": team_rows,
        "matchup_rows": matchup_rows,
        "artifact_id": artifact_id,
        "artifact_digest": artifact_digest,
        "gold_binary_sha256": gold_binary_sha,
        "maximum_output_bytes": maximum_output_bytes,
        "point_in_time": {
            "passed": True,
            "violations": 0,
            "rule": "POLICY_BOUND_GOVERNED_CORPUS_VALIDATION",
        },
    }


def open_read_only_connection(path: Path) -> sqlite3.Connection:
    resolved = path.resolve(strict=True)
    uri = f"file:{resolved.as_posix()}?mode=ro&immutable=1"
    connection = sqlite3.connect(uri, uri=True)
    connection.execute("PRAGMA query_only=ON")
    query_only = connection.execute("PRAGMA query_only").fetchone()
    if not query_only or int(query_only[0]) != 1:
        connection.close()
        raise ManifestValidationError("SQLite query_only could not be enforced")
    integrity = connection.execute("PRAGMA integrity_check").fetchone()
    if not integrity or str(integrity[0]).lower() != "ok":
        connection.close()
        raise ManifestValidationError(f"SQLite integrity_check failed: {integrity!r}")
    return connection


def _schema_descriptor(connection: sqlite3.Connection, table: str) -> tuple[tuple[str, str, int, int], ...]:
    rows = connection.execute(f"PRAGMA table_info({_quote_identifier(table)})").fetchall()
    return tuple((str(row[1]), str(row[2]).upper(), int(row[3]), int(row[5])) for row in rows)


def _unique_keys(connection: sqlite3.Connection, table: str) -> frozenset[tuple[str, ...]]:
    keys: set[tuple[str, ...]] = set()
    for row in connection.execute(f"PRAGMA index_list({_quote_identifier(table)})"):
        index_name = str(row[1])
        unique = int(row[2])
        if not unique:
            continue
        columns = tuple(str(info[2]) for info in connection.execute(
            f"PRAGMA index_info({_quote_identifier(index_name)})"
        ))
        keys.add(columns)
    return frozenset(keys)


def validate_schema(connection: sqlite3.Connection) -> dict[str, tuple[tuple[str, str, int, int], ...]]:
    user_tables = {
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    }
    _require(user_tables == set(REQUIRED_TABLES), f"unexpected user table set: {sorted(user_tables)}")

    descriptors: dict[str, tuple[tuple[str, str, int, int], ...]] = {}
    for table in REQUIRED_TABLES:
        descriptor = _schema_descriptor(connection, table)
        _require(descriptor == EXPECTED_SCHEMAS[table], f"schema drift detected in {table}")
        unique_keys = _unique_keys(connection, table)
        _require(
            unique_keys == EXPECTED_UNIQUE_KEYS[table],
            f"unique-key schema drift detected in {table}: {sorted(unique_keys)}",
        )
        descriptors[table] = descriptor
    return descriptors


def _scalar(connection: sqlite3.Connection, sql: str, params: Sequence[Any] = ()) -> Any:
    row = connection.execute(sql, params).fetchone()
    if row is None:
        raise ManifestValidationError("aggregate query returned no row")
    return row[0]


def _blank_count(connection: sqlite3.Connection, table: str, columns: Sequence[str]) -> int:
    predicates = [
        f"{_quote_identifier(column)} IS NULL OR TRIM(CAST({_quote_identifier(column)} AS TEXT))=''"
        for column in columns
    ]
    return int(_scalar(
        connection,
        f"SELECT COUNT(*) FROM {_quote_identifier(table)} WHERE " + " OR ".join(f"({p})" for p in predicates),
    ))


def validate_relational_invariants(
    connection: sqlite3.Connection,
    *,
    expected_team_rows: int,
    expected_matchup_rows: int,
    expected_seasons: Sequence[str],
) -> dict[str, Any]:
    team_count = int(_scalar(connection, "SELECT COUNT(*) FROM gold_team_game_features"))
    matchup_count = int(_scalar(connection, "SELECT COUNT(*) FROM gold_matchup_features"))
    _require(team_count == expected_team_rows, f"team row count {team_count} != {expected_team_rows}")
    _require(matchup_count == expected_matchup_rows, f"matchup row count {matchup_count} != {expected_matchup_rows}")

    duplicate_team = int(_scalar(
        connection,
        "SELECT COUNT(*) FROM ("
        "SELECT game_id, team_abbr FROM gold_team_game_features "
        "GROUP BY game_id, team_abbr HAVING COUNT(*) > 1"
        ")",
    ))
    duplicate_matchups = int(_scalar(
        connection,
        "SELECT COUNT(*) FROM ("
        "SELECT game_id FROM gold_matchup_features GROUP BY game_id HAVING COUNT(*) > 1"
        ")",
    ))
    _require(duplicate_team == 0, "duplicate team-game keys detected")
    _require(duplicate_matchups == 0, "duplicate matchup game keys detected")

    blank_team = _blank_count(
        connection,
        "gold_team_game_features",
        ("feature_id", "game_id", "game_date", "season_label", "team_abbr", "opponent_abbr"),
    )
    blank_matchup = _blank_count(
        connection,
        "gold_matchup_features",
        (
            "matchup_feature_id",
            "game_id",
            "game_date",
            "home_team_abbr",
            "away_team_abbr",
            "home_feature_id",
            "away_feature_id",
        ),
    )
    _require(blank_team == 0, "blank or NULL team identifiers/dates detected")
    _require(blank_matchup == 0, "blank or NULL matchup identifiers/dates detected")

    incomplete = int(_scalar(
        connection,
        "SELECT COUNT(*) FROM ("
        "SELECT m.game_id, COUNT(t.feature_id) AS team_rows, "
        "SUM(CASE WHEN t.team_abbr=m.home_team_abbr THEN 1 ELSE 0 END) AS home_rows, "
        "SUM(CASE WHEN t.team_abbr=m.away_team_abbr THEN 1 ELSE 0 END) AS away_rows "
        "FROM gold_matchup_features m "
        "LEFT JOIN gold_team_game_features t ON t.game_id=m.game_id "
        "GROUP BY m.game_id "
        "HAVING team_rows != 2 OR home_rows != 1 OR away_rows != 1"
        ")",
    ))
    orphan_team_games = int(_scalar(
        connection,
        "SELECT COUNT(*) FROM ("
        "SELECT DISTINCT t.game_id FROM gold_team_game_features t "
        "LEFT JOIN gold_matchup_features m ON m.game_id=t.game_id "
        "WHERE m.game_id IS NULL"
        ")",
    ))
    _require(incomplete == 0, "matchup without exactly one home and one away team row")
    _require(orphan_team_games == 0, "team-game rows without a matchup detected")

    home_feature_mismatch = int(_scalar(
        connection,
        "SELECT COUNT(*) FROM gold_matchup_features m "
        "LEFT JOIN gold_team_game_features h ON h.feature_id=m.home_feature_id "
        "LEFT JOIN gold_team_game_features a ON a.feature_id=m.away_feature_id "
        "WHERE h.feature_id IS NULL OR a.feature_id IS NULL "
        "OR h.game_id != m.game_id OR a.game_id != m.game_id "
        "OR h.team_abbr != m.home_team_abbr OR a.team_abbr != m.away_team_abbr "
        "OR h.is_home != 1 OR a.is_home != 0",
    ))
    _require(home_feature_mismatch == 0, "matchup feature references do not align to team rows")

    seasons = [
        _normalise_text(str(row[0]))
        for row in connection.execute(
            "SELECT DISTINCT season_label FROM gold_team_game_features ORDER BY season_label"
        )
    ]
    _require(seasons == list(expected_seasons), f"season set {seasons!r} != {list(expected_seasons)!r}")

    return {
        "team_row_count": team_count,
        "matchup_row_count": matchup_count,
        "duplicate_team_game_keys": duplicate_team,
        "duplicate_matchup_game_keys": duplicate_matchups,
        "two_team_rows_per_matchup": True,
        "team_matchup_alignment": True,
        "season_set_exact": True,
    }


def load_metadata(
    connection: sqlite3.Connection,
    *,
    expected_seasons: Sequence[str],
) -> tuple[dict[str, str], list[tuple[str, str]]]:
    metadata: dict[str, str] = {}
    rows: list[tuple[str, str]] = []
    for key, value in connection.execute("SELECT key, value FROM gold_metadata ORDER BY key"):
        if not isinstance(key, str) or not isinstance(value, str):
            raise ManifestValidationError("gold_metadata must contain TEXT key/value pairs")
        normal_key = _normalise_text(key)
        normal_value = _normalise_text(value)
        if normal_key in metadata:
            raise ManifestValidationError(f"duplicate metadata key: {normal_key}")
        metadata[normal_key] = normal_value
        if normal_key not in VOLATILE_METADATA_KEYS:
            rows.append((normal_key, normal_value))

    missing = [key for key in REQUIRED_METADATA_KEYS if key not in metadata]
    _require(not missing, f"missing required metadata keys: {missing}")
    _require(all(metadata[key].strip() for key in REQUIRED_METADATA_KEYS), "required metadata value is blank")
    metadata_seasons = sorted(item.strip() for item in metadata["season_labels"].split(",") if item.strip())
    _require(metadata_seasons == list(expected_seasons), "metadata season_labels does not match governed scope")
    return metadata, rows


def _schema_digest(
    table: str,
    descriptor: Sequence[tuple[str, str, int, int]],
    included_names: Sequence[str],
) -> str:
    descriptor_by_name = {row[0]: row for row in descriptor}
    payload = {
        "table": table,
        "columns": [
            {
                "name": name,
                "declared_type": descriptor_by_name[name][1],
                "notnull": descriptor_by_name[name][2],
                "primary_key_position": descriptor_by_name[name][3],
            }
            for name in included_names
        ],
    }
    return f"sha256:{hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()}"


def _stream_table_digest(
    connection: sqlite3.Connection,
    *,
    table: str,
    descriptor: Sequence[tuple[str, str, int, int]],
    excluded_columns: Sequence[str],
    order_by: Sequence[str],
) -> tuple[str, int, str, int]:
    descriptor_by_name = {row[0]: row for row in descriptor}
    included = [row[0] for row in descriptor if row[0] not in set(excluded_columns)]
    _require(all(column in included for column in order_by), f"{table} sort key excluded or missing")
    schema_sha = _schema_digest(table, descriptor, included)

    select_columns = ", ".join(_quote_identifier(column) for column in included)
    order_clause = ", ".join(_quote_identifier(column) for column in order_by)
    cursor = connection.execute(
        f"SELECT {select_columns} FROM {_quote_identifier(table)} ORDER BY {order_clause}"
    )
    digest = hashlib.sha256()
    row_count = 0
    for row in cursor:
        values = []
        for column, value in zip(included, row):
            _, declared_type, notnull, _ = descriptor_by_name[column]
            values.append(
                _canonical_value(
                    value,
                    declared_type=declared_type,
                    notnull=notnull,
                    table=table,
                    column=column,
                )
            )
        digest.update(_canonical_json_bytes({"values": values}, newline=True))
        row_count += 1
    return f"sha256:{digest.hexdigest()}", row_count, schema_sha, len(included)


def _stream_metadata_digest(rows: Iterable[tuple[str, str]]) -> tuple[str, int]:
    digest = hashlib.sha256()
    count = 0
    for key, value in rows:
        digest.update(
            _canonical_json_bytes(
                {
                    "key": {"type": "text", "value": key},
                    "value": {"type": "text", "value": value},
                },
                newline=True,
            )
        )
        count += 1
    return f"sha256:{digest.hexdigest()}", count


def _walk_output_keys(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            yield str(key)
            yield from _walk_output_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_output_keys(child)


def serialise_and_validate_manifest(
    manifest: Mapping[str, Any],
    *,
    maximum_output_bytes: int,
    pretty: bool = True,
) -> bytes:
    _require(
        set(manifest) == set(EXPECTED_MANIFEST_TOP_LEVEL_KEYS),
        f"unexpected manifest top-level keys: {sorted(set(manifest) ^ set(EXPECTED_MANIFEST_TOP_LEVEL_KEYS))}",
    )
    keys = {key for key in _walk_output_keys(manifest)}
    prohibited = sorted(keys & FORBIDDEN_OUTPUT_KEYS)
    _require(not prohibited, f"forbidden output keys present: {prohibited}")
    data = json.dumps(
        manifest,
        ensure_ascii=False,
        sort_keys=True,
        indent=2 if pretty else None,
        separators=None if pretty else (",", ":"),
        allow_nan=False,
    ).encode("utf-8") + b"\n"
    _require(len(data) <= maximum_output_bytes, f"manifest exceeds {maximum_output_bytes} bytes")
    return data


def build_manifest(
    gold_sqlite: Path,
    policy: Mapping[str, Any],
    *,
    hash_file: Callable[[Path], str] = sha256_file,
) -> dict[str, Any]:
    policy_values = validate_policy(policy)
    _require(gold_sqlite.is_file(), f"Gold SQLite does not exist: {gold_sqlite}")
    before_sha = hash_file(gold_sqlite)

    connection = open_read_only_connection(gold_sqlite)
    try:
        descriptors = validate_schema(connection)
        relational = validate_relational_invariants(
            connection,
            expected_team_rows=policy_values["team_rows"],
            expected_matchup_rows=policy_values["matchup_rows"],
            expected_seasons=policy_values["seasons"],
        )
        metadata, stable_metadata_rows = load_metadata(
            connection,
            expected_seasons=policy_values["seasons"],
        )

        team_sha, team_rows, team_schema_sha, team_included_columns = _stream_table_digest(
            connection,
            table="gold_team_game_features",
            descriptor=descriptors["gold_team_game_features"],
            excluded_columns=VOLATILE_COLUMNS,
            order_by=TEAM_SORT_ORDER,
        )
        matchup_sha, matchup_rows, matchup_schema_sha, matchup_included_columns = _stream_table_digest(
            connection,
            table="gold_matchup_features",
            descriptor=descriptors["gold_matchup_features"],
            excluded_columns=VOLATILE_COLUMNS,
            order_by=MATCHUP_SORT_ORDER,
        )
        metadata_sha, metadata_count = _stream_metadata_digest(stable_metadata_rows)
    finally:
        connection.close()

    after_sha = hash_file(gold_sqlite)
    _require(before_sha == after_sha, "database SHA-256 changed during read-only processing")
    _require(team_rows == policy_values["team_rows"], "team stream count changed")
    _require(matchup_rows == policy_values["matchup_rows"], "matchup stream count changed")

    corpus_payload = {
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "policy_id": policy_values["policy_id"],
        "team_schema_sha256": team_schema_sha,
        "team_table_sha256": team_sha,
        "team_row_count": team_rows,
        "matchup_schema_sha256": matchup_schema_sha,
        "matchup_table_sha256": matchup_sha,
        "matchup_row_count": matchup_rows,
        "metadata_sha256": metadata_sha,
        "metadata_entry_count": metadata_count,
        "season_set": policy_values["seasons"],
        "point_in_time_validation_state": policy_values["point_in_time"],
    }
    corpus_sha = f"sha256:{hashlib.sha256(_canonical_json_bytes(corpus_payload)).hexdigest()}"

    manifest: dict[str, Any] = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "formal_state": "HISTORICAL_GOLD_SEMANTIC_CORPUS_MANIFEST_VALID",
        "implementation_design_id": IMPLEMENTATION_DESIGN_ID,
        "policy_id": policy_values["policy_id"],
        "source_binding": {
            "source_artifact_id": policy_values["artifact_id"],
            "source_artifact_digest": policy_values["artifact_digest"],
            "source_gold_binary_sha256": policy_values["gold_binary_sha256"],
            "database_sqlite_sha256": before_sha,
            "compressed_artifact_validation": "SEPARATE_GOVERNED_WORKFLOW_REQUIRED",
        },
        "gold_metadata_identity": {
            "gold_schema_version": metadata["schema_version"],
            "gold_feature_version": metadata["feature_version"],
            "source_version": metadata["source_version"],
        },
        "season_labels": policy_values["seasons"],
        "tables": {
            "gold_team_game_features": {
                "row_count": team_rows,
                "schema_sha256": team_schema_sha,
                "semantic_sha256": team_sha,
                "schema_column_count": len(descriptors["gold_team_game_features"]),
                "included_column_count": team_included_columns,
                "excluded_columns": list(VOLATILE_COLUMNS),
            },
            "gold_matchup_features": {
                "row_count": matchup_rows,
                "schema_sha256": matchup_schema_sha,
                "semantic_sha256": matchup_sha,
                "schema_column_count": len(descriptors["gold_matchup_features"]),
                "included_column_count": matchup_included_columns,
                "excluded_columns": list(VOLATILE_COLUMNS),
            },
        },
        "metadata_semantic_identity": {
            "entry_count": metadata_count,
            "semantic_sha256": metadata_sha,
            "excluded_keys": list(VOLATILE_METADATA_KEYS),
            "required_keys_present": True,
        },
        "corpus_semantic_sha256": corpus_sha,
        "point_in_time_validation": policy_values["point_in_time"],
        "duplicate_validation": {
            "duplicate_team_game_keys": relational["duplicate_team_game_keys"],
            "duplicate_matchup_game_keys": relational["duplicate_matchup_game_keys"],
            "two_team_rows_per_matchup": relational["two_team_rows_per_matchup"],
            "team_matchup_alignment": relational["team_matchup_alignment"],
        },
        "aggregate_validation": {
            "required_table_set_exact": True,
            "schema_exact": True,
            "row_counts_exact": True,
            "season_set_exact": relational["season_set_exact"],
            "database_integrity_check_passed": True,
            "database_query_only": True,
            "database_sha256_unchanged": True,
            "nonfinite_values_detected": 0,
            "blob_values_detected": 0,
        },
        "privacy_boundaries": {
            "aggregate_only": True,
            "row_level_values_emitted": False,
            "row_level_hashes_emitted": False,
            "game_ids_emitted": False,
            "game_dates_emitted": False,
            "team_codes_emitted": False,
            "maximum_output_bytes": policy_values["maximum_output_bytes"],
        },
        "scientific_boundaries": {
            "semantic_manifest_only": True,
            "corpus_database_modified": False,
            "market_backtest_executed": False,
            "model_training_or_retraining_executed": False,
            "injury_candidate_activated": False,
            "betting_edge_claim": False,
        },
        "formal_stake": 0,
    }
    serialise_and_validate_manifest(
        manifest,
        maximum_output_bytes=policy_values["maximum_output_bytes"],
    )
    return manifest


def write_manifest(
    manifest: Mapping[str, Any],
    output: Path,
    *,
    maximum_output_bytes: int,
) -> None:
    data = serialise_and_validate_manifest(
        manifest,
        maximum_output_bytes=maximum_output_bytes,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold-sqlite", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    policy = _read_policy(args.policy)
    manifest = build_manifest(args.gold_sqlite, policy)
    maximum = validate_policy(policy)["maximum_output_bytes"]
    write_manifest(manifest, args.output, maximum_output_bytes=maximum)
    print(
        json.dumps(
            {
                "formal_state": manifest["formal_state"],
                "policy_id": manifest["policy_id"],
                "team_rows": manifest["tables"]["gold_team_game_features"]["row_count"],
                "matchup_rows": manifest["tables"]["gold_matchup_features"]["row_count"],
                "corpus_semantic_sha256": manifest["corpus_semantic_sha256"],
                "output": str(args.output),
                "formal_stake": manifest["formal_stake"],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
