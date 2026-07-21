#!/usr/bin/env python3
"""Aggregate-only root-cause audit for Silver games with zero team features.

The analyzer may inspect temporary SQLite rows, but never emits game ids, dates,
team codes, row hashes, or raw records.
"""
from __future__ import annotations

import argparse
import gzip
import json
import shutil
import sqlite3
import tempfile
from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

SCHEMA_VERSION = "historical-silver-missing-team-features-root-cause-report-v1"
IMPLEMENTATION_STATE = "HISTORICAL_SILVER_2023_24_MISSING_TEAM_FEATURES_ROOT_CAUSE_IMPLEMENTATION_READY_REAL_EXECUTION_DISABLED"
SEASON = "2023-24"

REASONS = (
    "nbastats_game_present_pbpstats_game_absent",
    "no_event_or_possession_source_rows",
    "pbpstats_possessions_all_offense_unresolved",
    "pbpstats_single_expected_offense_team_coverage",
    "pbpstats_offense_team_identity_mismatch",
    "possession_metadata_count_mismatch",
    "feature_aggregation_omission_after_valid_possessions",
    "silver_game_identity_unresolved",
    "unclassified",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@contextmanager
def materialized_sqlite(path: Path) -> Iterator[Path]:
    if path.suffix.lower() != ".gz":
        yield path
        return
    with tempfile.TemporaryDirectory(prefix="nbavl-silver-root-cause-") as temp_name:
        target = Path(temp_name) / path.with_suffix("").name
        with gzip.open(path, "rb") as source, target.open("wb") as destination:
            shutil.copyfileobj(source, destination, length=1024 * 1024)
        yield target


def require_table(connection: sqlite3.Connection, table: str, columns: set[str]) -> None:
    tables = {
        str(row[0])
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    if table not in tables:
        raise ValueError(f"missing table: {table}")
    present = {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")}
    missing = sorted(columns - present)
    if missing:
        raise ValueError(f"{table} missing columns: {missing}")


def bucket_count(value: int) -> str:
    if value == 0:
        return "0"
    if value < 50:
        return "1-49"
    if value < 100:
        return "50-99"
    if value < 150:
        return "100-149"
    return "150+"


def analyze(silver_path: Path, season: str = SEASON) -> dict[str, Any]:
    with materialized_sqlite(silver_path) as database:
        connection = sqlite3.connect(database)
        connection.row_factory = sqlite3.Row
        try:
            require_table(
                connection,
                "games",
                {
                    "game_id", "season_label", "home_team_abbr", "away_team_abbr",
                    "pbp_event_count", "possession_count", "quality_flags",
                },
            )
            require_table(
                connection,
                "possessions",
                {"game_id", "offense_team_abbr", "defense_team_abbr", "quality_flags"},
            )
            require_table(connection, "team_game_features", {"game_id", "team_abbr"})

            games = list(
                connection.execute(
                    """
                    SELECT game_id, home_team_abbr, away_team_abbr,
                           pbp_event_count, possession_count, quality_flags
                    FROM games WHERE season_label=?
                    """,
                    (season,),
                )
            )
            feature_counts = Counter(
                str(row[0])
                for row in connection.execute(
                    """
                    SELECT f.game_id
                    FROM team_game_features AS f
                    JOIN games AS g ON g.game_id=f.game_id
                    WHERE g.season_label=?
                    """,
                    (season,),
                )
            )

            possession_rows: dict[str, list[sqlite3.Row]] = defaultdict(list)
            for row in connection.execute(
                """
                SELECT p.game_id, p.offense_team_abbr, p.defense_team_abbr, p.quality_flags
                FROM possessions AS p
                JOIN games AS g ON g.game_id=p.game_id
                WHERE g.season_label=?
                """,
                (season,),
            ):
                possession_rows[str(row["game_id"])].append(row)

            reasons = Counter()
            feature_histogram = Counter()
            possession_row_histogram = Counter()
            resolved_offense_count_histogram = Counter()
            pbp_event_presence = Counter()
            missing_quality_flags = Counter()
            missing_games = 0

            for game in games:
                game_id = str(game["game_id"])
                feature_count = int(feature_counts.get(game_id, 0))
                feature_histogram[str(feature_count)] += 1
                if feature_count != 0:
                    continue

                missing_games += 1
                rows = possession_rows.get(game_id, [])
                actual_possessions = len(rows)
                metadata_possessions = int(game["possession_count"] or 0)
                pbp_events = int(game["pbp_event_count"] or 0)
                possession_row_histogram[bucket_count(actual_possessions)] += 1
                pbp_event_presence["present" if pbp_events > 0 else "absent"] += 1
                for flag in str(game["quality_flags"] or "").split(","):
                    flag = flag.strip()
                    if flag:
                        missing_quality_flags[flag] += 1

                home = str(game["home_team_abbr"] or "").strip()
                away = str(game["away_team_abbr"] or "").strip()
                expected = {home, away} if home and away and home != away else set()
                resolved_offenses = {
                    str(row["offense_team_abbr"]).strip()
                    for row in rows
                    if row["offense_team_abbr"] is not None
                    and str(row["offense_team_abbr"]).strip()
                }
                resolved_offense_count_histogram[str(len(resolved_offenses))] += 1

                if not expected:
                    reason = "silver_game_identity_unresolved"
                elif actual_possessions == 0:
                    reason = (
                        "nbastats_game_present_pbpstats_game_absent"
                        if pbp_events > 0
                        else "no_event_or_possession_source_rows"
                    )
                elif metadata_possessions != actual_possessions:
                    reason = "possession_metadata_count_mismatch"
                elif not resolved_offenses:
                    reason = "pbpstats_possessions_all_offense_unresolved"
                elif len(resolved_offenses) == 1 and resolved_offenses <= expected:
                    reason = "pbpstats_single_expected_offense_team_coverage"
                elif resolved_offenses != expected:
                    reason = "pbpstats_offense_team_identity_mismatch"
                elif resolved_offenses == expected:
                    reason = "feature_aggregation_omission_after_valid_possessions"
                else:
                    reason = "unclassified"
                reasons[reason] += 1

            classified = sum(reasons.values())
            unclassified = int(reasons.get("unclassified", 0))
            source_gap = any(
                reasons.get(name, 0) > 0
                for name in (
                    "nbastats_game_present_pbpstats_game_absent",
                    "no_event_or_possession_source_rows",
                    "pbpstats_possessions_all_offense_unresolved",
                    "pbpstats_single_expected_offense_team_coverage",
                    "pbpstats_offense_team_identity_mismatch",
                )
            )
            builder_gap = any(
                reasons.get(name, 0) > 0
                for name in (
                    "possession_metadata_count_mismatch",
                    "feature_aggregation_omission_after_valid_possessions",
                )
            )
            identity_gap = reasons.get("silver_game_identity_unresolved", 0) > 0

            if missing_games == 0:
                outcome = "HISTORICAL_SILVER_MISSING_TEAM_FEATURES_NO_GAP"
            elif unclassified:
                outcome = "HISTORICAL_SILVER_MISSING_TEAM_FEATURES_ROOT_CAUSE_BLOCKED"
            elif builder_gap and source_gap:
                outcome = "HISTORICAL_SILVER_MISSING_TEAM_FEATURES_MIXED_ROOT_CAUSES"
            elif builder_gap:
                outcome = "HISTORICAL_SILVER_MISSING_TEAM_FEATURES_BUILDER_REPAIR_REQUIRED"
            elif identity_gap:
                outcome = "HISTORICAL_SILVER_MISSING_TEAM_FEATURES_IDENTITY_RECONCILIATION_REQUIRED"
            else:
                outcome = "HISTORICAL_SILVER_MISSING_TEAM_FEATURES_SOURCE_GAP_CONFIRMED"

            return {
                "schema_version": SCHEMA_VERSION,
                "generated_at": utc_now(),
                "formal_outcome": outcome,
                "scope": {
                    "season_label": season,
                    "silver_games": len(games),
                    "games_without_team_features": missing_games,
                    "classified_missing_games": classified,
                    "unclassified_missing_games": unclassified,
                },
                "root_cause": {
                    "missing_by_reason": {
                        name: int(reasons.get(name, 0)) for name in REASONS
                    },
                    "team_feature_count_histogram": dict(sorted(feature_histogram.items())),
                    "missing_game_possession_row_histogram": dict(sorted(possession_row_histogram.items())),
                    "missing_game_resolved_offense_team_count_histogram": dict(
                        sorted(resolved_offense_count_histogram.items())
                    ),
                    "missing_game_pbp_event_presence": dict(sorted(pbp_event_presence.items())),
                    "missing_game_quality_flag_counts": dict(sorted(missing_quality_flags.items())),
                },
                "decision": {
                    "source_archive_reconciliation_required": source_gap,
                    "silver_builder_repair_required": builder_gap,
                    "silver_game_identity_reconciliation_required": identity_gap,
                    "ready_for_followup_repair_design": missing_games > 0 and unclassified == 0,
                    "ready_for_gold_rebuild": False,
                    "ready_for_cross_source_audit_rerun": False,
                    "ready_for_market_backtest": False,
                    "ready_for_model_retraining": False,
                    "formal_stake": 0,
                },
                "boundaries": {
                    "raw_rows_emitted": 0,
                    "raw_files_emitted": False,
                    "game_ids_emitted": False,
                    "dates_emitted": False,
                    "team_codes_emitted": False,
                    "row_key_hashes_emitted": False,
                    "candidate_csv_downloaded_or_read": False,
                    "historical_silver_replacement_allowed": False,
                    "historical_gold_replacement_allowed": False,
                    "opening_or_closing_labels_allowed": False,
                    "point_in_time_market_backtest_allowed": False,
                    "model_retraining_allowed": False,
                    "betting_edge_claim_allowed": False,
                    "formal_stake": 0,
                },
            }
        finally:
            connection.close()


def write_fixture(path: Path) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.executescript(
            """
            CREATE TABLE games (
              game_id TEXT PRIMARY KEY, season_label TEXT, home_team_abbr TEXT,
              away_team_abbr TEXT, pbp_event_count INTEGER, possession_count INTEGER,
              quality_flags TEXT
            );
            CREATE TABLE possessions (
              game_id TEXT, offense_team_abbr TEXT, defense_team_abbr TEXT,
              quality_flags TEXT
            );
            CREATE TABLE team_game_features (game_id TEXT, team_abbr TEXT);
            """
        )
        games = [
            ("covered", SEASON, "AAA", "BBB", 400, 2, ""),
            ("source-absent", SEASON, "CCC", "DDD", 350, 0, ""),
            ("all-unresolved", SEASON, "EEE", "FFF", 300, 2, ""),
            ("single-team", SEASON, "GGG", "HHH", 300, 2, ""),
            ("identity-mismatch", SEASON, "III", "JJJ", 300, 2, "source_team_set_mismatch"),
            ("builder-gap", SEASON, "KKK", "LLL", 300, 2, ""),
            ("identity-unresolved", SEASON, NULL, "MMM", 300, 1, "home_away_team_unresolved"),
        ]
        connection.executemany("INSERT INTO games VALUES (?,?,?,?,?,?,?)", games)
        possessions = [
            ("covered", "AAA", "BBB", ""),
            ("covered", "BBB", "AAA", ""),
            ("all-unresolved", None, "FFF", "offense_team_unresolved"),
            ("all-unresolved", None, "EEE", "offense_team_unresolved"),
            ("single-team", "GGG", "HHH", ""),
            ("single-team", "GGG", "HHH", ""),
            ("identity-mismatch", "III", "JJJ", ""),
            ("identity-mismatch", "XXX", "III", ""),
            ("builder-gap", "KKK", "LLL", ""),
            ("builder-gap", "LLL", "KKK", ""),
            ("identity-unresolved", "MMM", "NNN", ""),
        ]
        connection.executemany("INSERT INTO possessions VALUES (?,?,?,?)", possessions)
        connection.executemany(
            "INSERT INTO team_game_features VALUES (?,?)",
            [("covered", "AAA"), ("covered", "BBB")],
        )
        connection.commit()
    finally:
        connection.close()


def self_test(output: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="nbavl-silver-root-cause-self-test-") as temp_name:
        database = Path(temp_name) / "fixture.sqlite"
        write_fixture(database)
        report = analyze(database)
        reasons = report["root_cause"]["missing_by_reason"]
        assert report["scope"]["silver_games"] == 7, report
        assert report["scope"]["games_without_team_features"] == 6, report
        assert reasons["nbastats_game_present_pbpstats_game_absent"] == 1, report
        assert reasons["pbpstats_possessions_all_offense_unresolved"] == 1, report
        assert reasons["pbpstats_single_expected_offense_team_coverage"] == 1, report
        assert reasons["pbpstats_offense_team_identity_mismatch"] == 1, report
        assert reasons["feature_aggregation_omission_after_valid_possessions"] == 1, report
        assert reasons["silver_game_identity_unresolved"] == 1, report
        assert report["formal_outcome"] == "HISTORICAL_SILVER_MISSING_TEAM_FEATURES_MIXED_ROOT_CAUSES", report
        assert report["boundaries"]["raw_rows_emitted"] == 0, report
        assert report["boundaries"]["game_ids_emitted"] is False, report
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--silver-db", type=Path)
    parser.add_argument("--season", default=SEASON)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        report = self_test(args.output)
    else:
        if not args.silver_db:
            parser.error("--silver-db is required unless --self-test is used")
        report = analyze(args.silver_db, args.season)
        payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if len(payload.encode("utf-8")) > 1048576:
            raise RuntimeError("aggregate report exceeds 1 MiB")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")

    print(json.dumps({
        "formal_outcome": report["formal_outcome"],
        "games_without_team_features": report["scope"]["games_without_team_features"],
        "missing_by_reason": report["root_cause"]["missing_by_reason"],
        "formal_stake": report["decision"]["formal_stake"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
