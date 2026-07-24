#!/usr/bin/env python3
"""Build the deidentified 2025-26 prior-only player rotation source v1.

This script reuses the validated NBA Official LiveData boxscore importer. It
reads the governed 2025-26 Silver games table, fetches final official boxscores,
and emits a deidentified player-game source suitable for later *strictly prior*
rotation feature construction.

The output is a source layer, not a target-game feature table. Model fitting,
market joins, EV/ROI/CLV/Drawdown and betting selections are prohibited.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "prior-only-player-rotation-source-2025-26-v1"
FORMAL_STATE = "PRIOR_ONLY_PLAYER_ROTATION_SOURCE_2025_26_PASS"
EXPECTED_GAMES = 1230
EXPECTED_TEAM_ROWS = 2460
MIN_PLAYER_ROWS = 30000
MIN_UNIQUE_PLAYERS = 500
MINUTE_TOLERANCE = 0.35


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def resolve_sqlite(path: Path) -> tuple[Path, tempfile.TemporaryDirectory[str] | None]:
    if path.suffix != ".gz":
        return path, None
    temp = tempfile.TemporaryDirectory()
    resolved = Path(temp.name) / "silver.sqlite"
    with gzip.open(path, "rb") as source, resolved.open("wb") as target:
        shutil.copyfileobj(source, target)
    return resolved, temp


def load_governed_games(path: Path) -> list[dict[str, Any]]:
    sqlite_path, temp = resolve_sqlite(path)
    try:
        connection = sqlite3.connect(sqlite_path)
        connection.row_factory = sqlite3.Row
        try:
            rows = [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT
                        game_id,
                        game_date,
                        home_team_abbr,
                        away_team_abbr,
                        game_minutes
                    FROM games
                    ORDER BY game_date, game_id
                    """
                )
            ]
        finally:
            connection.close()
    finally:
        if temp is not None:
            temp.cleanup()
    if len(rows) != EXPECTED_GAMES:
        raise ValueError(f"expected {EXPECTED_GAMES} governed games, found {len(rows)}")
    if len({str(row["game_id"]) for row in rows}) != EXPECTED_GAMES:
        raise ValueError("governed Silver game IDs are not unique")
    return rows


def selected_game_rows(games: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "historical_game_id": str(game["game_id"]).zfill(10),
            "game_date": str(game["game_date"]),
            "home_team_abbr": str(game["home_team_abbr"]),
            "away_team_abbr": str(game["away_team_abbr"]),
        }
        for game in games
    ]


def run_official_import(
    selected_path: Path,
    output_dir: Path,
    *,
    max_workers: int,
) -> None:
    command = [
        sys.executable,
        str(Path(__file__).with_name("run_official_nba_participation_import.py")),
        "--selected-games",
        str(selected_path),
        "--output-dir",
        str(output_dir),
        "--max-workers",
        str(max_workers),
    ]
    subprocess.run(command, check=True)


def validate_and_emit(
    *,
    games: list[dict[str, Any]],
    import_dir: Path,
    output_dir: Path,
    silver_path: Path,
) -> dict[str, Any]:
    import_report_path = import_dir / "official-player-participation-import-report.json"
    labels_path = import_dir / "official-player-participation-labels.csv"
    source_index_path = import_dir / "official-player-participation-source-index.csv"
    report = json.loads(import_report_path.read_text(encoding="utf-8"))
    labels = read_csv(labels_path)
    source_index = read_csv(source_index_path)

    game_minutes = {str(row["game_id"]).zfill(10): float(row["game_minutes"]) for row in games}
    expected_teams: set[tuple[str, str]] = set()
    for row in games:
        game_id = str(row["game_id"]).zfill(10)
        expected_teams.add((game_id, str(row["home_team_abbr"])))
        expected_teams.add((game_id, str(row["away_team_abbr"])))

    private_rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    team_minutes: Counter[tuple[str, str]] = Counter()
    team_starters: Counter[tuple[str, str]] = Counter()
    team_players: Counter[tuple[str, str]] = Counter()
    duplicate_game_player_rows = 0
    invalid_minutes = 0
    starter_without_play = 0
    invalid_team_rows = 0

    for row in labels:
        game_id = str(row["historical_game_id"]).zfill(10)
        player_id = str(row["player_id"]).strip()
        team = str(row["team_abbr"]).strip()
        key = (game_id, player_id)
        if key in seen:
            duplicate_game_player_rows += 1
            continue
        seen.add(key)
        if (game_id, team) not in expected_teams:
            invalid_team_rows += 1
        minutes = float(row["actual_minutes"])
        played = int(row["actual_played"])
        starter = int(row["actual_starter"])
        if minutes < 0 or minutes > game_minutes.get(game_id, 60.0) + 0.01 or (played == 0 and minutes > 1e-9):
            invalid_minutes += 1
        if starter and not played:
            starter_without_play += 1
        team_key = (game_id, team)
        team_minutes[team_key] += minutes
        team_starters[team_key] += starter
        team_players[team_key] += 1
        private_rows.append(
            {
                "source_game_id": game_id,
                "source_game_date_et": row["game_date"],
                "team_abbr": team,
                "player_id": player_id,
                "minutes": round(minutes, 6),
                "played": played,
                "starter": starter,
                "source_provider": row["source_provider"],
                "source_sha256": row["source_sha256"],
                "retrieved_at": row["retrieved_at"],
                "source_time_semantics": "STRICTLY_EARLIER_EASTERN_GAME_DATE_FALLBACK",
                "source_version": VERSION,
            }
        )

    missing_team_rows = sorted(expected_teams - set(team_players))
    unexpected_team_rows = sorted(set(team_players) - expected_teams)
    starter_count_errors = [
        {"source_game_id": game_id, "team_abbr": team, "starter_count": count}
        for (game_id, team), count in sorted(team_starters.items())
        if count != 5
    ]
    minute_reconciliation_errors = []
    max_abs_minute_error = 0.0
    for game_id, team in sorted(expected_teams):
        expected = game_minutes[game_id] * 5.0
        actual = float(team_minutes.get((game_id, team), 0.0))
        error = actual - expected
        max_abs_minute_error = max(max_abs_minute_error, abs(error))
        if abs(error) > MINUTE_TOLERANCE:
            minute_reconciliation_errors.append(
                {
                    "source_game_id": game_id,
                    "team_abbr": team,
                    "expected_team_minutes": expected,
                    "actual_team_minutes": round(actual, 6),
                    "difference": round(error, 6),
                }
            )

    private_rows.sort(
        key=lambda row: (
            row["source_game_date_et"],
            row["source_game_id"],
            row["team_abbr"],
            row["player_id"],
        )
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    source_output = output_dir / "prior-only-player-rotation-source-2025-26-v1.csv"
    write_csv(
        source_output,
        private_rows,
        [
            "source_game_id",
            "source_game_date_et",
            "team_abbr",
            "player_id",
            "minutes",
            "played",
            "starter",
            "source_provider",
            "source_sha256",
            "retrieved_at",
            "source_time_semantics",
            "source_version",
        ],
    )
    shutil.copy2(source_index_path, output_dir / "prior-only-player-rotation-source-index-2025-26-v1.csv")

    successful_games = int(report["coverage"]["successful_official_games"])
    player_rows = len(private_rows)
    unique_players = len({row["player_id"] for row in private_rows})
    source_ready = (
        successful_games == EXPECTED_GAMES
        and len(source_index) == EXPECTED_GAMES
        and len(team_players) == EXPECTED_TEAM_ROWS
        and player_rows >= MIN_PLAYER_ROWS
        and unique_players >= MIN_UNIQUE_PLAYERS
        and duplicate_game_player_rows == 0
        and invalid_team_rows == 0
        and invalid_minutes == 0
        and starter_without_play == 0
        and not missing_team_rows
        and not unexpected_team_rows
        and not starter_count_errors
        and not minute_reconciliation_errors
        and report["quality"]["team_mismatches"] == 0
        and report["quality"]["invalid_player_rows"] == 0
        and report["quality"]["duplicate_official_game_player_rows"] == 0
    )

    output_report = {
        "schema_version": VERSION,
        "formal_state": FORMAL_STATE if source_ready else "PRIOR_ONLY_PLAYER_ROTATION_SOURCE_2025_26_BLOCKED",
        "generated_at_utc": utc_now(),
        "inputs": {
            "governed_silver_sha256": sha256(silver_path),
            "governed_games": len(games),
            "expected_team_game_rows": EXPECTED_TEAM_ROWS,
            "official_source_provider": report["source"]["provider"],
            "official_source_url_template": report["source"]["url_template"],
        },
        "coverage": {
            "requested_games": EXPECTED_GAMES,
            "successful_games": successful_games,
            "failed_games": int(report["coverage"]["failed_official_games"]),
            "team_game_rows": len(team_players),
            "player_game_rows": player_rows,
            "unique_player_ids": unique_players,
            "months_covered": len({row["source_game_date_et"][:7] for row in private_rows}),
            "teams_represented": len({row["team_abbr"] for row in private_rows}),
        },
        "quality": {
            "duplicate_game_player_rows": duplicate_game_player_rows,
            "missing_team_rows": len(missing_team_rows),
            "unexpected_team_rows": len(unexpected_team_rows),
            "invalid_team_rows": invalid_team_rows,
            "invalid_minutes": invalid_minutes,
            "starter_without_play": starter_without_play,
            "starter_count_errors": len(starter_count_errors),
            "minute_reconciliation_errors": len(minute_reconciliation_errors),
            "max_abs_team_minute_error": round(max_abs_minute_error, 6),
            "official_import_team_mismatches": report["quality"]["team_mismatches"],
            "official_import_invalid_player_rows": report["quality"]["invalid_player_rows"],
            "official_import_duplicate_rows": report["quality"]["duplicate_official_game_player_rows"],
            "player_names_retained": False,
            "not_playing_descriptions_retained": False,
            "raw_json_retained": False,
        },
        "time_authority": {
            "source_game_end_timestamp_available": False,
            "primary_feature_rule": "source_game_end_time_utc < target_analysis_cutoff_utc",
            "approved_fallback": "source_game_date_et < target_game_date_et",
            "same_day_source_rows_allowed": False,
            "future_source_rows_allowed": False,
            "target_game_source_rows_allowed": False,
        },
        "outputs": {
            "private_source_csv": source_output.name,
            "private_source_csv_sha256": sha256(source_output),
            "private_source_index_csv": "prior-only-player-rotation-source-index-2025-26-v1.csv",
            "public_player_rows_committed": 0,
            "public_game_level_feature_rows_committed": 0,
        },
        "qualification": {
            "official_source_qualified_for_prior_only_rotation_v1": source_ready,
            "ready_for_prior_only_rotation_feature_build": source_ready,
            "real_feature_build_executed": False,
            "residual_audit_executed": False,
            "model_training_authorized": False,
            "strict_t60_qualified": False,
            "formal_market_backtest_allowed": False,
            "betting_edge_claim_allowed": False,
            "formal_stake": 0,
        },
        "next_unique_sub_mainline": (
            "BUILD_PRIOR_ONLY_PLAYER_ROTATION_STATE_FEATURES_2025_26_V1_WITHOUT_MODEL_RETRAINING"
            if source_ready
            else "REPAIR_PRIOR_ONLY_PLAYER_ROTATION_SOURCE_COVERAGE_OR_RECONCILIATION_WITHOUT_LOWERING_GATES"
        ),
    }
    report_path = output_dir / "prior-only-player-rotation-source-2025-26-report-v1.json"
    report_path.write_text(json.dumps(output_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output_report, ensure_ascii=False, indent=2))
    if not source_ready:
        raise SystemExit(2)
    return output_report


def self_test(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    labels = []
    for team in ("AAA", "BBB"):
        for index in range(6):
            labels.append(
                {
                    "historical_game_id": "0022500001",
                    "game_date": "2025-10-21",
                    "team_abbr": team,
                    "player_id": str(1000 + index + (100 if team == "BBB" else 0)),
                    "actual_minutes": "48" if index < 5 else "0",
                    "actual_played": "1" if index < 5 else "0",
                    "actual_starter": "1" if index < 5 else "0",
                    "source_provider": "NBA Official LiveData Boxscore",
                    "source_sha256": "abc",
                    "retrieved_at": "2026-07-24T00:00:00Z",
                }
            )
    checks = {
        "rows": len(labels) == 12,
        "team_minutes": all(
            abs(sum(float(row["actual_minutes"]) for row in labels if row["team_abbr"] == team) - 240.0) < 1e-9
            for team in ("AAA", "BBB")
        ),
        "starters": all(
            sum(int(row["actual_starter"]) for row in labels if row["team_abbr"] == team) == 5
            for team in ("AAA", "BBB")
        ),
        "no_names": all("player_name" not in row for row in labels),
        "locks": True,
    }
    if not all(checks.values()):
        raise AssertionError(checks)
    (output_dir / "self-test.json").write_text(
        json.dumps({"passed": True, "checks": checks}, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--silver", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-workers", type=int, default=4)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("prior-only player rotation source self-test passed")
        return 0
    if args.silver is None:
        parser.error("--silver is required")
    if not 1 <= args.max_workers <= 6:
        parser.error("--max-workers must be between 1 and 6")
    games = load_governed_games(args.silver)
    with tempfile.TemporaryDirectory() as temp_name:
        temp = Path(temp_name)
        selected_path = temp / "selected-games.csv"
        write_csv(
            selected_path,
            selected_game_rows(games),
            ["historical_game_id", "game_date", "home_team_abbr", "away_team_abbr"],
        )
        import_dir = temp / "official-import"
        run_official_import(selected_path, import_dir, max_workers=args.max_workers)
        validate_and_emit(
            games=games,
            import_dir=import_dir,
            output_dir=args.output_dir,
            silver_path=args.silver,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
