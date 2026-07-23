#!/usr/bin/env python3
"""Synthetic-only validation for the Historical Gold freeze-manifest builder."""
from __future__ import annotations

import argparse
import copy
import json
import math
import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Callable

import build_historical_gold_5826_complete_corpus_freeze_manifest_v1 as builder


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError("policy must be an object")
    return value


def synthetic_policy(real_policy: dict[str, Any]) -> dict[str, Any]:
    policy = copy.deepcopy(real_policy)
    policy["policy_id"] = "SYNTHETIC-HISTORICAL-GOLD-FREEZE-POLICY-V1"
    policy["governed_scope"]["seasons"] = ["SYNTH-1"]
    policy["governed_scope"]["silver_games"] = 2
    policy["governed_scope"]["silver_team_game_features"] = 4
    policy["governed_scope"]["gold_matchup_features"] = 2
    policy["governed_scope"]["gold_team_game_features"] = 4
    policy["freeze_identity_design"]["team_table_expected_rows"] = 4
    policy["freeze_identity_design"]["matchup_table_expected_rows"] = 2
    policy["immutable_evidence_bindings"]["adopted_artifact_id"] = 0
    policy["immutable_evidence_bindings"]["adopted_artifact_digest"] = "sha256:" + "0" * 64
    policy["immutable_evidence_bindings"]["historical_gold_sha256"] = "sha256:" + "1" * 64
    policy["implementation_access_policy"]["aggregate_manifest_max_bytes"] = 1048576
    policy["decision"]["formal_stake"] = 0
    return policy


def create_tables(
    connection: sqlite3.Connection,
    *,
    unique_constraints: bool = True,
    omit: dict[str, set[str]] | None = None,
) -> None:
    omit = omit or {}
    for table in builder.REQUIRED_TABLES:
        descriptors = [
            row for row in builder.EXPECTED_SCHEMAS[table]
            if row[0] not in omit.get(table, set())
        ]
        definitions = []
        for name, declared_type, notnull, primary_key_position in descriptors:
            definition = f'"{name}" {declared_type}'
            if notnull:
                definition += " NOT NULL"
            if primary_key_position:
                definition += " PRIMARY KEY"
            definitions.append(definition)
        if unique_constraints and table == "gold_team_game_features":
            definitions.append("UNIQUE(game_id, team_abbr)")
        if unique_constraints and table == "gold_matchup_features":
            definitions.append("UNIQUE(game_id)")
        connection.execute(
            f'CREATE TABLE "{table}" (' + ", ".join(definitions) + ")"
        )


def base_team_rows(generated_at: str = "2026-01-01T00:00:00+00:00") -> list[dict[str, Any]]:
    games = [
        ("g1", "2026-01-01", "AAA", "BBB"),
        ("g2", "2026-01-02", "CCC", "DDD"),
    ]
    rows: list[dict[str, Any]] = []
    for index, (game_id, game_date, home, away) in enumerate(games, start=1):
        for is_home, team, opponent, suffix in (
            (1, home, away, "h"),
            (0, away, home, "a"),
        ):
            row: dict[str, Any] = {}
            for name, declared_type, notnull, _ in builder.EXPECTED_SCHEMAS["gold_team_game_features"]:
                if declared_type == "TEXT":
                    row[name] = ""
                elif declared_type == "INTEGER":
                    row[name] = 0 if notnull else None
                elif declared_type == "REAL":
                    row[name] = 0.0 if notnull else None
                else:
                    raise AssertionError(declared_type)
            row.update(
                {
                    "feature_id": f"f{index}{suffix}",
                    "game_id": game_id,
                    "game_date": game_date,
                    "season_label": "SYNTH-1",
                    "team_abbr": team,
                    "opponent_abbr": opponent,
                    "is_home": is_home,
                    "feature_cutoff_time": f"{game_date}T00:00:00Z",
                    "prior_games": index - 1,
                    "prior_home_games": 0,
                    "prior_away_games": 0,
                    "is_back_to_back": 0,
                    "games_last_3_days": 0,
                    "games_last_7_days": index - 1,
                    "source_version": "synthetic-source-v1",
                    "feature_version": "gold-team-game-v1",
                    "feature_generated_at": generated_at,
                    "quality_flags": "",
                }
            )
            rows.append(row)
    return rows


def base_matchup_rows(generated_at: str = "2026-01-01T00:00:00+00:00") -> list[dict[str, Any]]:
    rows = []
    payloads = [
        ("m1", "g1", "2026-01-01", "AAA", "BBB", "f1h", "f1a"),
        ("m2", "g2", "2026-01-02", "CCC", "DDD", "f2h", "f2a"),
    ]
    for matchup_id, game_id, game_date, home, away, home_feature, away_feature in payloads:
        row: dict[str, Any] = {}
        for name, declared_type, notnull, _ in builder.EXPECTED_SCHEMAS["gold_matchup_features"]:
            if declared_type == "TEXT":
                row[name] = ""
            elif declared_type == "INTEGER":
                row[name] = 0 if notnull else None
            elif declared_type == "REAL":
                row[name] = 0.0 if notnull else None
            else:
                raise AssertionError(declared_type)
        row.update(
            {
                "matchup_feature_id": matchup_id,
                "game_id": game_id,
                "game_date": game_date,
                "home_team_abbr": home,
                "away_team_abbr": away,
                "home_feature_id": home_feature,
                "away_feature_id": away_feature,
                "prior_games_min": 0,
                "evidence_coverage": 0.0,
                "source_version": "synthetic-source-v1",
                "feature_version": "gold-team-game-v1",
                "feature_generated_at": generated_at,
                "quality_flags": "",
            }
        )
        rows.append(row)
    return rows


def base_metadata(generated_at: str = "2026-01-01T00:00:00+00:00") -> dict[str, str]:
    return {
        "pipeline_name": "NBA Value Lab synthetic Gold",
        "schema_version": "1.0.0",
        "feature_version": "gold-team-game-v1",
        "source_version": "synthetic-source-v1",
        "feature_generated_at": generated_at,
        "point_in_time_rule": "same_season_source_game_date_less_than_target_game_date",
        "same_day_games_policy": "excluded_from_each_other",
        "season_history_policy": "rolling_features_reset_each_season",
        "season_labels": "SYNTH-1",
    }


def insert_dict_rows(
    connection: sqlite3.Connection,
    table: str,
    rows: list[dict[str, Any]],
    *,
    reverse: bool = False,
) -> None:
    columns = [row[0] for row in builder.EXPECTED_SCHEMAS[table] if row[0] in rows[0]]
    placeholders = ", ".join("?" for _ in columns)
    names = ", ".join(f'"{name}"' for name in columns)
    ordered = list(reversed(rows)) if reverse else rows
    connection.executemany(
        f'INSERT INTO "{table}" ({names}) VALUES ({placeholders})',
        [[row[name] for name in columns] for row in ordered],
    )


def create_database(
    path: Path,
    *,
    reverse: bool = False,
    generated_at: str = "2026-01-01T00:00:00+00:00",
    metadata_generated_at: str | None = None,
    unique_constraints: bool = True,
    omit: dict[str, set[str]] | None = None,
) -> None:
    connection = sqlite3.connect(path)
    create_tables(connection, unique_constraints=unique_constraints, omit=omit)
    metadata = base_metadata(metadata_generated_at or generated_at)
    connection.executemany(
        "INSERT INTO gold_metadata(key, value) VALUES (?, ?)",
        list(reversed(list(metadata.items()))) if reverse else metadata.items(),
    )
    insert_dict_rows(
        connection,
        "gold_team_game_features",
        base_team_rows(generated_at),
        reverse=reverse,
    )
    insert_dict_rows(
        connection,
        "gold_matchup_features",
        base_matchup_rows(generated_at),
        reverse=reverse,
    )
    connection.commit()
    connection.close()


def digest_tuple(manifest: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        manifest["tables"]["gold_team_game_features"]["semantic_sha256"],
        manifest["tables"]["gold_matchup_features"]["semantic_sha256"],
        manifest["metadata_semantic_identity"]["semantic_sha256"],
        manifest["corpus_semantic_sha256"],
    )


def expect_blocks(call: Callable[[], Any]) -> bool:
    try:
        call()
    except (builder.ManifestValidationError, sqlite3.Error, OSError, ValueError):
        return True
    return False


def run_suite(real_policy: dict[str, Any], root: Path) -> dict[str, bool]:
    policy = synthetic_policy(real_policy)
    root.mkdir(parents=True, exist_ok=True)
    results: dict[str, bool] = {}

    baseline_path = root / "baseline.sqlite"
    create_database(baseline_path)
    baseline = builder.build_manifest(baseline_path, policy)
    repeat = builder.build_manifest(baseline_path, policy)
    results["stable_digest_repeats_identically"] = digest_tuple(baseline) == digest_tuple(repeat)

    reversed_path = root / "reversed.sqlite"
    create_database(reversed_path, reverse=True)
    reversed_manifest = builder.build_manifest(reversed_path, policy)
    results["row_insertion_order_does_not_change_digest"] = (
        digest_tuple(baseline) == digest_tuple(reversed_manifest)
    )

    volatile_path = root / "volatile-feature.sqlite"
    create_database(
        volatile_path,
        generated_at="2030-12-31T23:59:59+00:00",
        metadata_generated_at="2026-01-01T00:00:00+00:00",
    )
    volatile_manifest = builder.build_manifest(volatile_path, policy)
    results["volatile_feature_generated_at_change_does_not_change_digest"] = (
        digest_tuple(baseline) == digest_tuple(volatile_manifest)
    )

    volatile_meta_path = root / "volatile-metadata.sqlite"
    create_database(
        volatile_meta_path,
        generated_at="2026-01-01T00:00:00+00:00",
        metadata_generated_at="2031-02-03T04:05:06+00:00",
    )
    volatile_meta_manifest = builder.build_manifest(volatile_meta_path, policy)
    results["policy_excluded_metadata_change_does_not_change_digest"] = (
        digest_tuple(baseline) == digest_tuple(volatile_meta_manifest)
    )

    stable_feature_path = root / "stable-feature.sqlite"
    create_database(stable_feature_path)
    connection = sqlite3.connect(stable_feature_path)
    connection.execute(
        "UPDATE gold_team_game_features SET home_off_rtg_prior=123.456 WHERE feature_id='f2h'"
    )
    connection.commit()
    connection.close()
    stable_feature_manifest = builder.build_manifest(stable_feature_path, policy)
    results["stable_feature_change_changes_table_and_corpus_digest"] = (
        baseline["tables"]["gold_team_game_features"]["semantic_sha256"]
        != stable_feature_manifest["tables"]["gold_team_game_features"]["semantic_sha256"]
        and baseline["corpus_semantic_sha256"]
        != stable_feature_manifest["corpus_semantic_sha256"]
    )

    stable_metadata_path = root / "stable-metadata.sqlite"
    create_database(stable_metadata_path)
    connection = sqlite3.connect(stable_metadata_path)
    connection.execute(
        "UPDATE gold_metadata SET value='synthetic-source-v2' WHERE key='source_version'"
    )
    connection.commit()
    connection.close()
    stable_metadata_manifest = builder.build_manifest(stable_metadata_path, policy)
    results["stable_metadata_change_changes_metadata_and_corpus_digest"] = (
        baseline["metadata_semantic_identity"]["semantic_sha256"]
        != stable_metadata_manifest["metadata_semantic_identity"]["semantic_sha256"]
        and baseline["corpus_semantic_sha256"]
        != stable_metadata_manifest["corpus_semantic_sha256"]
    )

    missing_table_path = root / "missing-table.sqlite"
    create_database(missing_table_path)
    connection = sqlite3.connect(missing_table_path)
    connection.execute("DROP TABLE gold_metadata")
    connection.commit()
    connection.close()
    results["missing_required_table_blocks"] = expect_blocks(
        lambda: builder.build_manifest(missing_table_path, policy)
    )

    extra_column_path = root / "extra-column.sqlite"
    create_database(extra_column_path)
    connection = sqlite3.connect(extra_column_path)
    connection.execute("ALTER TABLE gold_matchup_features ADD COLUMN unexpected TEXT")
    connection.commit()
    connection.close()
    results["unexpected_schema_column_blocks"] = expect_blocks(
        lambda: builder.build_manifest(extra_column_path, policy)
    )

    missing_column_path = root / "missing-column.sqlite"
    connection = sqlite3.connect(missing_column_path)
    create_tables(
        connection,
        omit={"gold_team_game_features": {"quality_flags"}},
    )
    connection.close()
    results["missing_stable_schema_column_blocks"] = expect_blocks(
        lambda: builder.build_manifest(missing_column_path, policy)
    )

    wrong_count_path = root / "wrong-count.sqlite"
    create_database(wrong_count_path)
    connection = sqlite3.connect(wrong_count_path)
    connection.execute("DELETE FROM gold_matchup_features WHERE game_id='g2'")
    connection.commit()
    connection.close()
    results["wrong_row_count_blocks"] = expect_blocks(
        lambda: builder.build_manifest(wrong_count_path, policy)
    )

    duplicate_path = root / "duplicate.sqlite"
    create_database(duplicate_path, unique_constraints=False)
    connection = sqlite3.connect(duplicate_path)
    duplicate = base_team_rows()[0].copy()
    duplicate["feature_id"] = "duplicate-feature"
    insert_dict_rows(connection, "gold_team_game_features", [duplicate])
    connection.commit()
    connection.close()
    results["duplicate_team_game_key_blocks"] = expect_blocks(
        lambda: builder.build_manifest(duplicate_path, policy)
    )

    incomplete_path = root / "incomplete.sqlite"
    create_database(incomplete_path)
    connection = sqlite3.connect(incomplete_path)
    connection.execute("DELETE FROM gold_team_game_features WHERE feature_id='f2a'")
    orphan = base_team_rows()[0].copy()
    orphan.update(
        {
            "feature_id": "orphan",
            "game_id": "g3",
            "game_date": "2026-01-03",
            "team_abbr": "EEE",
            "opponent_abbr": "FFF",
        }
    )
    insert_dict_rows(connection, "gold_team_game_features", [orphan])
    connection.commit()
    connection.close()
    results["orphan_or_incomplete_matchup_blocks"] = expect_blocks(
        lambda: builder.build_manifest(incomplete_path, policy)
    )

    wrong_season_path = root / "wrong-season.sqlite"
    create_database(wrong_season_path)
    connection = sqlite3.connect(wrong_season_path)
    connection.execute("UPDATE gold_team_game_features SET season_label='SYNTH-2'")
    connection.execute("UPDATE gold_metadata SET value='SYNTH-2' WHERE key='season_labels'")
    connection.commit()
    connection.close()
    results["wrong_season_set_blocks"] = expect_blocks(
        lambda: builder.build_manifest(wrong_season_path, policy)
    )

    blank_date_path = root / "blank-date.sqlite"
    create_database(blank_date_path)
    connection = sqlite3.connect(blank_date_path)
    connection.execute("UPDATE gold_team_game_features SET game_date='' WHERE feature_id='f1h'")
    connection.commit()
    connection.close()
    results["blank_date_blocks"] = expect_blocks(
        lambda: builder.build_manifest(blank_date_path, policy)
    )

    nonfinite_path = root / "nonfinite.sqlite"
    create_database(nonfinite_path)
    connection = sqlite3.connect(nonfinite_path)
    connection.execute(
        "UPDATE gold_matchup_features SET evidence_coverage=? WHERE matchup_feature_id='m1'",
        (math.inf,),
    )
    connection.commit()
    connection.close()
    results["non_finite_real_blocks"] = expect_blocks(
        lambda: builder.build_manifest(nonfinite_path, policy)
    )

    blob_path = root / "blob.sqlite"
    create_database(blob_path)
    connection = sqlite3.connect(blob_path)
    connection.execute(
        "UPDATE gold_team_game_features SET quality_flags=? WHERE feature_id='f1h'",
        (sqlite3.Binary(b"forbidden"),),
    )
    connection.commit()
    connection.close()
    results["blob_value_blocks"] = expect_blocks(
        lambda: builder.build_manifest(blob_path, policy)
    )

    read_only_connection = builder.open_read_only_connection(baseline_path)
    try:
        results["database_write_attempt_blocks"] = expect_blocks(
            lambda: read_only_connection.execute(
                "INSERT INTO gold_metadata(key, value) VALUES ('forbidden', 'write')"
            )
        )
    finally:
        read_only_connection.close()

    real_hash = builder.sha256_file(baseline_path)
    calls = 0

    def changing_hash(_: Path) -> str:
        nonlocal calls
        calls += 1
        return real_hash if calls == 1 else "sha256:" + "f" * 64

    results["database_sha_change_blocks"] = expect_blocks(
        lambda: builder.build_manifest(baseline_path, policy, hash_file=changing_hash)
    )

    forbidden_manifest = copy.deepcopy(baseline)
    forbidden_manifest["privacy_boundaries"]["game_ids"] = []
    results["forbidden_output_key_blocks"] = expect_blocks(
        lambda: builder.serialise_and_validate_manifest(
            forbidden_manifest,
            maximum_output_bytes=1048576,
        )
    )

    oversized_manifest = copy.deepcopy(baseline)
    oversized_manifest["source_binding"]["compressed_artifact_validation"] = "x" * 1100000
    results["output_size_limit_blocks"] = expect_blocks(
        lambda: builder.serialise_and_validate_manifest(
            oversized_manifest,
            maximum_output_bytes=1048576,
        )
    )

    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    real_policy = load_json(args.policy)
    with tempfile.TemporaryDirectory(prefix="nbavl-freeze-manifest-synthetic-") as temp_name:
        results = run_suite(real_policy, Path(temp_name))
    failed = sorted(name for name, passed in results.items() if not passed)
    report = {
        "schema_version": "historical-gold-5826-freeze-manifest-synthetic-validation-report-v1",
        "formal_state": (
            "HISTORICAL_GOLD_5826_FREEZE_MANIFEST_IMPLEMENTATION_SYNTHETIC_VALID"
            if not failed
            else "HISTORICAL_GOLD_5826_FREEZE_MANIFEST_IMPLEMENTATION_SYNTHETIC_INVALID"
        ),
        "tests": results,
        "tests_total": len(results),
        "tests_passed": len(results) - len(failed),
        "tests_failed": len(failed),
        "failed_tests": failed,
        "real_artifact_read": False,
        "real_artifact_downloaded": False,
        "real_execution_workflow_created": False,
        "semantic_manifest_created": False,
        "corpus_frozen": False,
        "ready_for_real_artifact_execution_request_design": not failed,
        "ready_for_real_artifact_execution": False,
        "ready_for_market_backtest": False,
        "ready_for_model_retraining": False,
        "formal_stake": 0,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
