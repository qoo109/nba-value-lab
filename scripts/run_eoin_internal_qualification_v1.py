#!/usr/bin/env python3
"""Internal aggregate-only readiness audit for the Eoin NBA dataset.

This audit checks whether the downloaded files are internally coherent enough
to move to a later cross-source qualification pass. It emits aggregate counts
and rates only; no raw rows are written.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any

VERSION = "eoin-internal-qualification-v1"
REQUIRED_FILES = [
    "Games.csv",
    "TeamStatistics.csv",
    "PlayerStatistics.csv",
]
OPTIONAL_FILES = [
    "TeamStatisticsExtended.csv",
    "PlayerStatisticsExtended.csv",
    "LeagueSchedule24_25.csv",
    "LeagueSchedule25_26.csv",
    "PlayByPlay.parquet",
]
FROZEN_GATES = {
    "minimum_reference_games": 1000,
    "game_identity_duplicate_groups_maximum": 0,
    "team_boxscore_game_coverage_minimum": 0.98,
    "team_boxscore_score_match_rate_minimum": 0.98,
    "team_boxscore_duplicate_key_groups_maximum": 0,
    "player_boxscore_game_coverage_minimum": 0.95,
    "player_boxscore_duplicate_key_groups_maximum": 0,
}


class QualificationError(RuntimeError):
    """Raised when the local dataset cannot be inspected."""


def read_csv(path: Path):
    return path.open("r", encoding="utf-8-sig", newline="")


def parse_number(value: str | None) -> float | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def normalized_score(value: str | None) -> int | None:
    parsed = parse_number(value)
    if parsed is None:
        return None
    return int(round(parsed))


def parse_game_date(row: dict[str, str]) -> date | None:
    value = (row.get("gameDate") or row.get("gameDateTimeEst") or "").strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y"):
        try:
            return datetime.strptime(value[:19], fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def season_start_year(game_day: date) -> int:
    return game_day.year if game_day.month >= 10 else game_day.year - 1


def ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def inspect_games(path: Path) -> dict[str, Any]:
    games: dict[str, dict[str, Any]] = {}
    duplicate_game_ids: Counter[str] = Counter()
    season_counts: Counter[str] = Counter()
    game_type_counts: Counter[str] = Counter()
    date_min: date | None = None
    date_max: date | None = None
    missing_score_rows = 0
    row_count = 0

    with read_csv(path) as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            row_count += 1
            game_id = (row.get("gameId") or "").strip()
            if not game_id:
                continue
            if game_id in games:
                duplicate_game_ids[game_id] += 1
            game_day = parse_game_date(row)
            if game_day:
                date_min = game_day if date_min is None else min(date_min, game_day)
                date_max = game_day if date_max is None else max(date_max, game_day)
                season_counts[str(season_start_year(game_day))] += 1
            game_type = (row.get("gameType") or "<blank>").strip() or "<blank>"
            game_type_counts[game_type] += 1
            home_score = normalized_score(row.get("homeScore"))
            away_score = normalized_score(row.get("awayScore"))
            if home_score is None or away_score is None:
                missing_score_rows += 1
            games.setdefault(
                game_id,
                {
                    "home_team_id": (row.get("hometeamId") or "").strip(),
                    "away_team_id": (row.get("awayteamId") or "").strip(),
                    "home_score": home_score,
                    "away_score": away_score,
                    "season_start_year": season_start_year(game_day) if game_day else None,
                },
            )

    return {
        "row_count": row_count,
        "unique_games": len(games),
        "duplicate_game_id_groups": len(duplicate_game_ids),
        "missing_score_rows": missing_score_rows,
        "date_min": date_min.isoformat() if date_min else None,
        "date_max": date_max.isoformat() if date_max else None,
        "season_start_year_counts": dict(sorted(season_counts.items())),
        "game_type_counts": dict(sorted(game_type_counts.items())),
        "_games": games,
    }


def inspect_team_stats(path: Path, games: dict[str, dict[str, Any]]) -> dict[str, Any]:
    key_counts: Counter[tuple[str, str]] = Counter()
    rows_per_game: Counter[str] = Counter()
    unknown_game_rows = 0
    score_comparable_rows = 0
    score_match_rows = 0
    home_away_unresolved_rows = 0
    row_count = 0

    with read_csv(path) as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            row_count += 1
            game_id = (row.get("gameId") or "").strip()
            team_id = (row.get("teamId") or "").strip()
            if game_id:
                rows_per_game[game_id] += 1
            if game_id and team_id:
                key_counts[(game_id, team_id)] += 1
            game = games.get(game_id)
            if game is None:
                unknown_game_rows += 1
                continue
            team_score = normalized_score(row.get("teamScore"))
            opponent_score = normalized_score(row.get("opponentScore"))
            expected_team_score = None
            expected_opponent_score = None
            if team_id == game["home_team_id"]:
                expected_team_score = game["home_score"]
                expected_opponent_score = game["away_score"]
            elif team_id == game["away_team_id"]:
                expected_team_score = game["away_score"]
                expected_opponent_score = game["home_score"]
            else:
                home_away_unresolved_rows += 1
            if None not in (team_score, opponent_score, expected_team_score, expected_opponent_score):
                score_comparable_rows += 1
                if team_score == expected_team_score and opponent_score == expected_opponent_score:
                    score_match_rows += 1

    duplicate_key_groups = sum(1 for count in key_counts.values() if count > 1)
    covered_games = {game_id for game_id in rows_per_game if game_id in games}
    games_with_two_team_rows = sum(1 for game_id, count in rows_per_game.items() if game_id in games and count == 2)
    row_count_distribution = Counter(str(count) for game_id, count in rows_per_game.items() if game_id in games)

    return {
        "row_count": row_count,
        "unique_games": len(covered_games),
        "game_coverage_rate": ratio(len(covered_games), len(games)),
        "games_with_exactly_two_rows": games_with_two_team_rows,
        "games_with_exactly_two_rows_rate": ratio(games_with_two_team_rows, len(games)),
        "row_count_distribution_per_known_game": dict(sorted(row_count_distribution.items())),
        "unknown_game_rows": unknown_game_rows,
        "home_away_unresolved_rows": home_away_unresolved_rows,
        "duplicate_game_team_key_groups": duplicate_key_groups,
        "score_comparable_rows": score_comparable_rows,
        "score_match_rows": score_match_rows,
        "score_match_rate": ratio(score_match_rows, score_comparable_rows),
        "raw_rows_emitted": 0,
    }


def inspect_player_stats(path: Path, games: dict[str, dict[str, Any]]) -> dict[str, Any]:
    key_counts: Counter[tuple[str, str]] = Counter()
    covered_games: set[str] = set()
    unknown_game_rows = 0
    rows_with_minutes = 0
    rows_with_comment = 0
    row_count = 0

    with read_csv(path) as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            row_count += 1
            game_id = (row.get("gameId") or "").strip()
            person_id = (row.get("personId") or "").strip()
            if game_id in games:
                covered_games.add(game_id)
            elif game_id:
                unknown_game_rows += 1
            if game_id and person_id:
                key_counts[(game_id, person_id)] += 1
            minutes = parse_number(row.get("numMinutes"))
            if minutes is not None and minutes > 0:
                rows_with_minutes += 1
            if (row.get("comment") or "").strip():
                rows_with_comment += 1

    duplicate_key_groups = sum(1 for count in key_counts.values() if count > 1)
    return {
        "row_count": row_count,
        "unique_games": len(covered_games),
        "game_coverage_rate": ratio(len(covered_games), len(games)),
        "unknown_game_rows": unknown_game_rows,
        "duplicate_game_player_key_groups": duplicate_key_groups,
        "rows_with_positive_minutes": rows_with_minutes,
        "rows_with_comment": rows_with_comment,
        "raw_rows_emitted": 0,
    }


def inspect_schedule(path: Path, games: dict[str, dict[str, Any]]) -> dict[str, Any]:
    row_count = 0
    game_ids: set[str] = set()
    dates: list[date] = []
    with read_csv(path) as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            row_count += 1
            game_id = (row.get("gameId") or "").strip()
            if game_id:
                game_ids.add(game_id)
            game_day = parse_game_date(row)
            if game_day:
                dates.append(game_day)
    return {
        "row_count": row_count,
        "unique_games": len(game_ids),
        "known_completed_games": sum(1 for game_id in game_ids if game_id in games),
        "date_min": min(dates).isoformat() if dates else None,
        "date_max": max(dates).isoformat() if dates else None,
        "raw_rows_emitted": 0,
    }


def inspect_parquet(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "present": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else 0,
        "metadata_rows_read": False,
        "row_count": None,
        "column_count": None,
        "raw_rows_emitted": 0,
    }
    if not path.exists():
        return result
    try:
        import pyarrow.parquet as pq  # type: ignore
    except ImportError:
        result["metadata_error"] = "pyarrow_not_installed"
        return result
    metadata = pq.ParquetFile(path).metadata
    result["metadata_rows_read"] = True
    result["row_count"] = metadata.num_rows
    result["column_count"] = metadata.num_columns
    return result


def find_named_file(input_dir: Path, filename: str) -> Path | None:
    direct = input_dir / filename
    if direct.exists():
        return direct
    matches = sorted(path for path in input_dir.rglob(filename) if path.is_file())
    return matches[0] if matches else None


def gate(name: str, passed: bool, observed: Any, threshold: Any) -> dict[str, Any]:
    return {
        "name": name,
        "passed": passed,
        "observed": observed,
        "threshold": threshold,
    }


def run(input_dir: Path, output_dir: Path) -> dict[str, Any]:
    paths = {name: find_named_file(input_dir, name) for name in REQUIRED_FILES + OPTIONAL_FILES}
    missing = [name for name in REQUIRED_FILES if paths[name] is None]
    if missing:
        raise QualificationError(f"missing required files: {', '.join(missing)}")

    games_report = inspect_games(paths["Games.csv"])
    games = games_report.pop("_games")
    team_report = inspect_team_stats(paths["TeamStatistics.csv"], games)
    player_report = inspect_player_stats(paths["PlayerStatistics.csv"], games)
    optional_reports: dict[str, Any] = {}

    if paths["TeamStatisticsExtended.csv"] is not None:
        optional_reports["TeamStatisticsExtended.csv"] = inspect_team_stats(paths["TeamStatisticsExtended.csv"], games)
    if paths["PlayerStatisticsExtended.csv"] is not None:
        optional_reports["PlayerStatisticsExtended.csv"] = inspect_player_stats(paths["PlayerStatisticsExtended.csv"], games)
    for schedule_name in ("LeagueSchedule24_25.csv", "LeagueSchedule25_26.csv"):
        if paths[schedule_name] is not None:
            optional_reports[schedule_name] = inspect_schedule(paths[schedule_name], games)
    optional_reports["PlayByPlay.parquet"] = inspect_parquet(paths["PlayByPlay.parquet"] or input_dir / "PlayByPlay.parquet")

    gates = [
        gate(
            "minimum_reference_games",
            games_report["unique_games"] >= FROZEN_GATES["minimum_reference_games"],
            games_report["unique_games"],
            FROZEN_GATES["minimum_reference_games"],
        ),
        gate(
            "game_identity_duplicate_groups",
            games_report["duplicate_game_id_groups"] <= FROZEN_GATES["game_identity_duplicate_groups_maximum"],
            games_report["duplicate_game_id_groups"],
            FROZEN_GATES["game_identity_duplicate_groups_maximum"],
        ),
        gate(
            "team_boxscore_game_coverage",
            (team_report["game_coverage_rate"] or 0) >= FROZEN_GATES["team_boxscore_game_coverage_minimum"],
            team_report["game_coverage_rate"],
            FROZEN_GATES["team_boxscore_game_coverage_minimum"],
        ),
        gate(
            "team_boxscore_score_match_rate",
            (team_report["score_match_rate"] or 0) >= FROZEN_GATES["team_boxscore_score_match_rate_minimum"],
            team_report["score_match_rate"],
            FROZEN_GATES["team_boxscore_score_match_rate_minimum"],
        ),
        gate(
            "team_boxscore_duplicate_key_groups",
            team_report["duplicate_game_team_key_groups"] <= FROZEN_GATES["team_boxscore_duplicate_key_groups_maximum"],
            team_report["duplicate_game_team_key_groups"],
            FROZEN_GATES["team_boxscore_duplicate_key_groups_maximum"],
        ),
        gate(
            "player_boxscore_game_coverage",
            (player_report["game_coverage_rate"] or 0) >= FROZEN_GATES["player_boxscore_game_coverage_minimum"],
            player_report["game_coverage_rate"],
            FROZEN_GATES["player_boxscore_game_coverage_minimum"],
        ),
        gate(
            "player_boxscore_duplicate_key_groups",
            player_report["duplicate_game_player_key_groups"] <= FROZEN_GATES["player_boxscore_duplicate_key_groups_maximum"],
            player_report["duplicate_game_player_key_groups"],
            FROZEN_GATES["player_boxscore_duplicate_key_groups_maximum"],
        ),
    ]
    all_gates_passed = all(item["passed"] for item in gates)

    report = {
        "report_schema_version": VERSION,
        "report_type": "internal_aggregate_readiness_audit",
        "source_id": "kaggle_eoinamoore_historical_nba",
        "input_directory": str(input_dir),
        "resolved_files": {
            name: str(path.relative_to(input_dir)) if path is not None and path.is_relative_to(input_dir) else str(path)
            for name, path in paths.items()
            if path is not None
        },
        "required_files": REQUIRED_FILES,
        "optional_files": OPTIONAL_FILES,
        "missing_required_files": missing,
        "frozen_gates": FROZEN_GATES,
        "gate_results": gates,
        "all_internal_gates_passed": all_gates_passed,
        "formal_cross_source_qualification_executed": False,
        "formal_source_replacement_approved": False,
        "formal_stake": 0,
        "outcome": "INTERNAL_READY_FOR_CROSS_SOURCE_AUDIT" if all_gates_passed else "INTERNAL_BLOCKED",
        "games": games_report,
        "team_statistics": team_report,
        "player_statistics": player_report,
        "optional_reports": optional_reports,
        "boundaries": {
            "raw_rows_emitted": 0,
            "raw_files_emitted": False,
            "model_metrics": False,
            "market_metrics": False,
            "existing_silver_replacement": False,
            "existing_gold_replacement": False,
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "internal_qualification_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def self_test(output_dir: Path) -> None:
    root = output_dir / "synthetic-input"
    root.mkdir(parents=True, exist_ok=True)
    (root / "Games.csv").write_text(
        "gameId,gameDateTimeEst,hometeamId,awayteamId,homeScore,awayScore,gameType,gameDate\n"
        "0022300001,2023-10-24T19:30:00,1,2,110,105,Regular Season,2023-10-24\n",
        encoding="utf-8",
    )
    (root / "TeamStatistics.csv").write_text(
        "gameId,teamId,teamScore,opponentScore,numMinutes\n"
        "0022300001,1,110,105,240\n"
        "0022300001,2,105,110,240\n",
        encoding="utf-8",
    )
    (root / "PlayerStatistics.csv").write_text(
        "gameId,personId,numMinutes,comment\n"
        "0022300001,101,30,\n"
        "0022300001,102,0,DNP\n",
        encoding="utf-8",
    )
    report = run(root, output_dir)
    assert report["games"]["unique_games"] == 1, report
    assert report["team_statistics"]["score_match_rate"] == 1, report
    assert report["player_statistics"]["game_coverage_rate"] == 1, report
    assert report["boundaries"]["raw_rows_emitted"] == 0, report
    (output_dir / "self-test.json").write_text('{"passed":true}\n', encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test(args.output_dir)
        print("eoin internal qualification self-test passed")
        return 0
    if args.input_dir is None:
        parser.error("--input-dir is required unless --self-test is used")
    report = run(args.input_dir, args.output_dir)
    print(
        json.dumps(
            {
                "outcome": report["outcome"],
                "all_internal_gates_passed": report["all_internal_gates_passed"],
                "unique_games": report["games"]["unique_games"],
                "team_score_match_rate": report["team_statistics"]["score_match_rate"],
                "player_game_coverage_rate": report["player_statistics"]["game_coverage_rate"],
                "raw_rows_emitted": 0,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
