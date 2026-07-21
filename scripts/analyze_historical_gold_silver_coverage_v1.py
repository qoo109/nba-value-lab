#!/usr/bin/env python3
"""Aggregate-only Historical Silver/Gold coverage reconciliation analyzer v1.

This tool classifies why games present in Historical Silver `games` do not have a
corresponding row in Historical Gold `gold_matchup_features`. It may inspect rows
locally, but it never emits game ids, dates, team codes, row hashes, or raw rows.
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

SCHEMA_VERSION = "historical-gold-silver-coverage-reconciliation-report-v1"
IMPLEMENTATION_STATE = "HISTORICAL_GOLD_SILVER_COVERAGE_RECONCILIATION_IMPLEMENTATION_READY_REAL_EXECUTION_DISABLED"

REASON_CATEGORIES = (
    "missing_home_team_feature",
    "missing_away_team_feature",
    "missing_both_team_features",
    "silver_feature_pair_identity_mismatch",
    "gold_team_feature_transfer_mismatch",
    "gold_matchup_builder_omission",
    "silver_game_outside_gold_identity_contract",
    "unclassified",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@contextmanager
def materialized_sqlite(path: Path) -> Iterator[Path]:
    if path.suffix.lower() != ".gz":
        yield path
        return
    with tempfile.TemporaryDirectory(prefix="nbavl-coverage-reconcile-") as temp_name:
        target = Path(temp_name) / path.with_suffix("").name
        with gzip.open(path, "rb") as source, target.open("wb") as destination:
            shutil.copyfileobj(source, destination, length=1024 * 1024)
        yield target


def table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")}


def require_table(connection: sqlite3.Connection, table: str, columns: set[str]) -> None:
    present = {
        str(row[0])
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    if table not in present:
        raise ValueError(f"missing required table: {table}")
    missing = sorted(columns - table_columns(connection, table))
    if missing:
        raise ValueError(f"{table} missing required columns: {missing}")


def normalize_side(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed in {0, 1} else None


def analyze(silver_path: Path, gold_path: Path, seasons: list[str]) -> dict[str, Any]:
    with materialized_sqlite(silver_path) as silver_db, materialized_sqlite(gold_path) as gold_db:
        silver = sqlite3.connect(silver_db)
        gold = sqlite3.connect(gold_db)
        silver.row_factory = sqlite3.Row
        gold.row_factory = sqlite3.Row
        try:
            require_table(
                silver,
                "games",
                {"game_id", "game_date", "season_label", "home_team_abbr", "away_team_abbr"},
            )
            require_table(
                silver,
                "team_game_features",
                {"game_id", "team_abbr", "opponent_abbr", "is_home"},
            )
            require_table(
                gold,
                "gold_team_game_features",
                {"game_id", "team_abbr", "opponent_abbr", "is_home"},
            )
            require_table(gold, "gold_matchup_features", {"game_id"})

            placeholders = ",".join("?" for _ in seasons)
            game_rows = list(
                silver.execute(
                    f"""
                    SELECT game_id, season_label, home_team_abbr, away_team_abbr
                    FROM games
                    WHERE season_label IN ({placeholders})
                    """,
                    seasons,
                )
            )
            silver_features: dict[str, list[sqlite3.Row]] = defaultdict(list)
            for row in silver.execute(
                f"""
                SELECT f.game_id, f.team_abbr, f.opponent_abbr, f.is_home
                FROM team_game_features AS f
                JOIN games AS g ON g.game_id = f.game_id
                WHERE g.season_label IN ({placeholders})
                """,
                seasons,
            ):
                silver_features[str(row["game_id"])].append(row)

            gold_features: dict[str, list[sqlite3.Row]] = defaultdict(list)
            for row in gold.execute(
                "SELECT game_id, team_abbr, opponent_abbr, is_home FROM gold_team_game_features"
            ):
                gold_features[str(row["game_id"])].append(row)
            gold_matchups = {
                str(row[0]) for row in gold.execute("SELECT game_id FROM gold_matchup_features")
            }

            reasons = Counter()
            reasons_by_season: dict[str, Counter[str]] = defaultdict(Counter)
            missing_by_season = Counter()
            covered_by_season = Counter()
            silver_feature_count_histogram = Counter()
            gold_feature_count_histogram = Counter()

            for game in game_rows:
                game_id = str(game["game_id"])
                season = str(game["season_label"])
                silver_sides = silver_features.get(game_id, [])
                gold_sides = gold_features.get(game_id, [])
                silver_feature_count_histogram[str(len(silver_sides))] += 1
                gold_feature_count_histogram[str(len(gold_sides))] += 1

                if game_id in gold_matchups:
                    covered_by_season[season] += 1
                    continue

                missing_by_season[season] += 1
                home_abbr = str(game["home_team_abbr"] or "").strip()
                away_abbr = str(game["away_team_abbr"] or "").strip()
                reason = "unclassified"

                if not home_abbr or not away_abbr:
                    reason = "silver_game_outside_gold_identity_contract"
                else:
                    silver_home = [
                        row
                        for row in silver_sides
                        if normalize_side(row["is_home"]) == 1
                        and str(row["team_abbr"] or "").strip() == home_abbr
                        and str(row["opponent_abbr"] or "").strip() == away_abbr
                    ]
                    silver_away = [
                        row
                        for row in silver_sides
                        if normalize_side(row["is_home"]) == 0
                        and str(row["team_abbr"] or "").strip() == away_abbr
                        and str(row["opponent_abbr"] or "").strip() == home_abbr
                    ]

                    if not silver_home and not silver_away:
                        reason = "missing_both_team_features"
                    elif not silver_home:
                        reason = "missing_home_team_feature"
                    elif not silver_away:
                        reason = "missing_away_team_feature"
                    elif len(silver_home) != 1 or len(silver_away) != 1 or len(silver_sides) != 2:
                        reason = "silver_feature_pair_identity_mismatch"
                    else:
                        gold_home = [
                            row
                            for row in gold_sides
                            if normalize_side(row["is_home"]) == 1
                            and str(row["team_abbr"] or "").strip() == home_abbr
                            and str(row["opponent_abbr"] or "").strip() == away_abbr
                        ]
                        gold_away = [
                            row
                            for row in gold_sides
                            if normalize_side(row["is_home"]) == 0
                            and str(row["team_abbr"] or "").strip() == away_abbr
                            and str(row["opponent_abbr"] or "").strip() == home_abbr
                        ]
                        if len(gold_home) != 1 or len(gold_away) != 1 or len(gold_sides) != 2:
                            reason = "gold_team_feature_transfer_mismatch"
                        else:
                            reason = "gold_matchup_builder_omission"

                reasons[reason] += 1
                reasons_by_season[season][reason] += 1

            silver_game_ids = {str(row["game_id"]) for row in game_rows}
            gold_only_matchups = len(gold_matchups - silver_game_ids)
            missing_count = sum(missing_by_season.values())
            classified_count = sum(reasons.values())
            unclassified_count = int(reasons.get("unclassified", 0))
            builder_repair_required = any(
                reasons.get(category, 0) > 0
                for category in (
                    "silver_feature_pair_identity_mismatch",
                    "gold_team_feature_transfer_mismatch",
                    "gold_matchup_builder_omission",
                )
            )
            source_data_reconciliation_required = any(
                reasons.get(category, 0) > 0
                for category in (
                    "missing_home_team_feature",
                    "missing_away_team_feature",
                    "missing_both_team_features",
                    "silver_game_outside_gold_identity_contract",
                )
            )

            if missing_count == 0:
                outcome = "HISTORICAL_GOLD_SILVER_COVERAGE_RECONCILIATION_NO_GAP"
            elif unclassified_count > 0:
                outcome = "HISTORICAL_GOLD_SILVER_COVERAGE_RECONCILIATION_BLOCKED"
            elif builder_repair_required and source_data_reconciliation_required:
                outcome = "HISTORICAL_GOLD_SILVER_COVERAGE_RECONCILIATION_MIXED_CAUSES"
            elif builder_repair_required:
                outcome = "HISTORICAL_GOLD_SILVER_COVERAGE_RECONCILIATION_BUILDER_REPAIR_REQUIRED"
            else:
                outcome = "HISTORICAL_GOLD_SILVER_COVERAGE_RECONCILIATION_SOURCE_DATA_GAP_CONFIRMED"

            return {
                "schema_version": SCHEMA_VERSION,
                "generated_at": utc_now(),
                "formal_outcome": outcome,
                "scope": {
                    "season_labels": seasons,
                    "silver_game_rows": len(game_rows),
                    "gold_matchup_rows": len(gold_matchups),
                    "gold_matchup_rows_outside_scope": gold_only_matchups,
                },
                "coverage": {
                    "covered_games": len(game_rows) - missing_count,
                    "missing_gold_for_silver": missing_count,
                    "classified_missing_games": classified_count,
                    "unclassified_missing_games": unclassified_count,
                    "covered_by_season": dict(sorted(covered_by_season.items())),
                    "missing_by_season": dict(sorted(missing_by_season.items())),
                    "missing_by_reason": {
                        category: int(reasons.get(category, 0)) for category in REASON_CATEGORIES
                    },
                    "missing_by_season_and_reason": {
                        season: {
                            category: int(reasons_by_season[season].get(category, 0))
                            for category in REASON_CATEGORIES
                        }
                        for season in sorted(reasons_by_season)
                    },
                    "silver_feature_count_histogram": dict(sorted(silver_feature_count_histogram.items())),
                    "gold_feature_count_histogram": dict(sorted(gold_feature_count_histogram.items())),
                },
                "decision": {
                    "builder_repair_required": builder_repair_required,
                    "source_data_reconciliation_required": source_data_reconciliation_required,
                    "ready_for_followup_repair_design": missing_count > 0 and unclassified_count == 0,
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
            silver.close()
            gold.close()


def write_fixture_databases(silver_path: Path, gold_path: Path) -> None:
    silver = sqlite3.connect(silver_path)
    gold = sqlite3.connect(gold_path)
    try:
        silver.executescript(
            """
            CREATE TABLE games (
              game_id TEXT PRIMARY KEY,
              game_date TEXT,
              season_label TEXT,
              home_team_abbr TEXT,
              away_team_abbr TEXT
            );
            CREATE TABLE team_game_features (
              game_id TEXT,
              team_abbr TEXT,
              opponent_abbr TEXT,
              is_home INTEGER
            );
            """
        )
        gold.executescript(
            """
            CREATE TABLE gold_team_game_features (
              game_id TEXT,
              team_abbr TEXT,
              opponent_abbr TEXT,
              is_home INTEGER
            );
            CREATE TABLE gold_matchup_features (game_id TEXT PRIMARY KEY);
            """
        )
        games = [
            ("covered", "2023-10-01", "2023-24", "AAA", "BBB"),
            ("missing-home", "2023-10-02", "2023-24", "CCC", "DDD"),
            ("missing-away", "2023-10-03", "2023-24", "EEE", "FFF"),
            ("transfer-gap", "2023-10-04", "2023-24", "GGG", "HHH"),
            ("builder-gap", "2023-10-05", "2023-24", "III", "JJJ"),
        ]
        silver.executemany("INSERT INTO games VALUES (?,?,?,?,?)", games)
        silver_features = [
            ("covered", "AAA", "BBB", 1),
            ("covered", "BBB", "AAA", 0),
            ("missing-home", "DDD", "CCC", 0),
            ("missing-away", "EEE", "FFF", 1),
            ("transfer-gap", "GGG", "HHH", 1),
            ("transfer-gap", "HHH", "GGG", 0),
            ("builder-gap", "III", "JJJ", 1),
            ("builder-gap", "JJJ", "III", 0),
        ]
        silver.executemany("INSERT INTO team_game_features VALUES (?,?,?,?)", silver_features)
        gold_features = [
            ("covered", "AAA", "BBB", 1),
            ("covered", "BBB", "AAA", 0),
            ("builder-gap", "III", "JJJ", 1),
            ("builder-gap", "JJJ", "III", 0),
            ("transfer-gap", "GGG", "HHH", 1),
        ]
        gold.executemany("INSERT INTO gold_team_game_features VALUES (?,?,?,?)", gold_features)
        gold.execute("INSERT INTO gold_matchup_features VALUES ('covered')")
        silver.commit()
        gold.commit()
    finally:
        silver.close()
        gold.close()


def self_test(output: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="nbavl-coverage-self-test-") as temp_name:
        root = Path(temp_name)
        silver = root / "silver.sqlite"
        gold = root / "gold.sqlite"
        write_fixture_databases(silver, gold)
        report = analyze(silver, gold, ["2023-24"])
        reasons = report["coverage"]["missing_by_reason"]
        assert report["coverage"]["missing_gold_for_silver"] == 4, report
        assert reasons["missing_home_team_feature"] == 1, report
        assert reasons["missing_away_team_feature"] == 1, report
        assert reasons["gold_team_feature_transfer_mismatch"] == 1, report
        assert reasons["gold_matchup_builder_omission"] == 1, report
        assert report["formal_outcome"] == "HISTORICAL_GOLD_SILVER_COVERAGE_RECONCILIATION_MIXED_CAUSES", report
        assert report["boundaries"]["raw_rows_emitted"] == 0, report
        assert report["boundaries"]["game_ids_emitted"] is False, report
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--silver-db", type=Path)
    parser.add_argument("--gold-db", type=Path)
    parser.add_argument("--seasons-json", default='["2019-20","2020-21","2021-22","2022-23","2023-24"]')
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        report = self_test(args.output)
    else:
        if not args.silver_db or not args.gold_db:
            parser.error("--silver-db and --gold-db are required unless --self-test is used")
        seasons = json.loads(args.seasons_json)
        if not isinstance(seasons, list) or not all(isinstance(item, str) for item in seasons):
            raise ValueError("--seasons-json must be a JSON string list")
        report = analyze(args.silver_db, args.gold_db, seasons)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if len(payload.encode("utf-8")) > 1048576:
            raise RuntimeError("aggregate report exceeds 1 MiB")
        args.output.write_text(payload, encoding="utf-8")

    print(json.dumps({
        "formal_outcome": report["formal_outcome"],
        "missing_gold_for_silver": report["coverage"]["missing_gold_for_silver"],
        "builder_repair_required": report["decision"]["builder_repair_required"],
        "source_data_reconciliation_required": report["decision"]["source_data_reconciliation_required"],
        "formal_stake": report["decision"]["formal_stake"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
