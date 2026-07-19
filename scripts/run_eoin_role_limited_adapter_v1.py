#!/usr/bin/env python3
"""Role-limited Eoin secondary-source adapter v1.

This implementation is deliberately self-test only. It validates the frozen
predeclaration, runs a synthetic fixture adapter path, and writes aggregate
reports. It does not execute against the full Eoin bundle yet.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import tempfile
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any

import validate_eoin_adapter_predeclaration_v1 as policy_validator

VERSION = "eoin-role-limited-secondary-adapter-v1"
REPORT_NAME = "eoin-role-limited-secondary-adapter-v1-report.json"
STATUS_NAME = "eoin-role-limited-secondary-adapter-v1-status.json"
PASS_STATE = "ROLE_LIMITED_ADAPTER_SELF_TEST_PASS"
BLOCKED_STATE = "ROLE_LIMITED_ADAPTER_SELF_TEST_BLOCKED"
PILOT_SEASON_START_YEAR = 2023


class AdapterError(RuntimeError):
    """Raised when the role-limited adapter self-test cannot proceed."""


def normalize_game_id(value: Any) -> str:
    raw = re.sub(r"\.0$", "", str(value or "").strip())
    if not raw:
        return ""
    if not raw.isdigit():
        return raw
    return raw.zfill(10)


def parse_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y"):
        try:
            return datetime.strptime(text[:19], fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def season_start_year(game_day: date) -> int:
    return game_day.year if game_day.month >= 10 else game_day.year - 1


def as_int(value: Any) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return int(round(float(text)))
    except ValueError:
        return None


def ratio(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else numerator / denominator


def read_csv(path: Path):
    return path.open("r", encoding="utf-8-sig", errors="replace", newline="")


def find_named_file(input_dir: Path, filename: str) -> Path | None:
    direct = input_dir / filename
    if direct.exists():
        return direct
    matches = sorted(path for path in input_dir.rglob(filename) if path.is_file())
    return matches[0] if matches else None


def load_games(path: Path) -> dict[str, Any]:
    games: dict[str, dict[str, Any]] = {}
    key_counts = Counter()
    total_rows = selected_rows = missing_id_rows = 0
    with read_csv(path) as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            total_rows += 1
            game_day = parse_date(row.get("gameDate") or row.get("gameDateTimeEst"))
            if game_day is None or season_start_year(game_day) != PILOT_SEASON_START_YEAR:
                continue
            selected_rows += 1
            game_id = normalize_game_id(row.get("gameId"))
            if not game_id:
                missing_id_rows += 1
                continue
            key_counts[game_id] += 1
            games.setdefault(
                game_id,
                {
                    "home_score": as_int(row.get("homeScore")),
                    "away_score": as_int(row.get("awayScore")),
                },
            )
    return {
        "_games": games,
        "total_rows": total_rows,
        "selected_rows": selected_rows,
        "unique_games": len(games),
        "missing_id_rows": missing_id_rows,
        "duplicate_game_id_groups": sum(1 for count in key_counts.values() if count > 1),
        "raw_rows_emitted": 0,
    }


def load_team_stats(path: Path) -> dict[str, Any]:
    rows_by_game: dict[str, list[dict[str, Any]]] = {}
    key_counts = Counter()
    total_rows = selected_rows = missing_id_rows = 0
    with read_csv(path) as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            total_rows += 1
            game_day = parse_date(row.get("gameDateTimeEst") or row.get("gameDate"))
            if game_day is None or season_start_year(game_day) != PILOT_SEASON_START_YEAR:
                continue
            selected_rows += 1
            game_id = normalize_game_id(row.get("gameId"))
            team_id = str(row.get("teamId") or "").strip()
            if not game_id:
                missing_id_rows += 1
                continue
            key_counts[(game_id, team_id)] += 1
            rows_by_game.setdefault(game_id, []).append({"team_score": as_int(row.get("teamScore"))})
    return {
        "_rows_by_game": rows_by_game,
        "total_rows": total_rows,
        "selected_rows": selected_rows,
        "unique_games": len(rows_by_game),
        "missing_id_rows": missing_id_rows,
        "duplicate_game_team_key_groups": sum(1 for count in key_counts.values() if count > 1),
        "raw_rows_emitted": 0,
    }


def load_player_stats(path: Path) -> dict[str, Any]:
    games = set()
    key_counts = Counter()
    total_rows = selected_rows = missing_id_rows = 0
    with read_csv(path) as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            total_rows += 1
            game_day = parse_date(row.get("gameDate") or row.get("gameDateTimeEst"))
            if game_day is None or season_start_year(game_day) != PILOT_SEASON_START_YEAR:
                continue
            selected_rows += 1
            game_id = normalize_game_id(row.get("gameId"))
            person_id = str(row.get("personId") or "").strip()
            if not game_id:
                missing_id_rows += 1
                continue
            games.add(game_id)
            if person_id:
                key_counts[(game_id, person_id)] += 1
    return {
        "_games": games,
        "total_rows": total_rows,
        "selected_rows": selected_rows,
        "unique_games": len(games),
        "missing_id_rows": missing_id_rows,
        "duplicate_game_player_key_groups": sum(1 for count in key_counts.values() if count > 1),
        "coverage_only": True,
        "raw_rows_emitted": 0,
    }


def load_pbp_metadata(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "present": path.exists(),
        "pyarrow_available": False,
        "metadata_rows_read": False,
        "game_column": None,
        "row_count": None,
        "unique_games": None,
        "raw_rows_emitted": 0,
    }
    if not path.exists():
        return result
    try:
        import pyarrow.compute as pc  # type: ignore
        import pyarrow.parquet as pq  # type: ignore
    except ImportError:
        result["metadata_error"] = "pyarrow_not_installed"
        return result

    result["pyarrow_available"] = True
    parquet = pq.ParquetFile(path)
    result["metadata_rows_read"] = True
    result["row_count"] = parquet.metadata.num_rows
    candidates = [name for name in parquet.schema.names if name.lower().replace("_", "") == "gameid"]
    if not candidates:
        return result

    column = candidates[0]
    result["game_column"] = column
    games = set()
    for batch in parquet.iter_batches(columns=[column], batch_size=50_000):
        unique = pc.unique(batch.column(0))
        games.update(normalize_game_id(item.as_py()) for item in unique if normalize_game_id(item.as_py()))
    result["_games"] = games
    result["unique_games"] = len(games)
    return result


def validate_predeclaration(policy_path: Path, evidence_path: Path) -> dict[str, Any]:
    policy = policy_validator.read_json(policy_path)
    evidence = policy_validator.read_json(evidence_path)
    report = policy_validator.validate(policy, evidence)
    if report["formal_state"] != "ROLE_LIMITED_ADAPTER_READY_FOR_IMPLEMENTATION":
        raise AdapterError("Eoin adapter predeclaration is not ready for implementation")
    return report


def build_aggregate_report(
    input_dir: Path,
    output_dir: Path,
    policy_path: Path,
    evidence_path: Path,
    require_parquet_fixture: bool,
) -> dict[str, Any]:
    policy_report = validate_predeclaration(policy_path, evidence_path)
    files = {
        name: find_named_file(input_dir, name)
        for name in ("Games.csv", "TeamStatistics.csv", "PlayerStatistics.csv", "PlayByPlay.parquet")
    }
    missing_required = [name for name in ("Games.csv", "TeamStatistics.csv", "PlayerStatistics.csv") if files[name] is None]
    if missing_required:
        raise AdapterError(f"missing fixture files: {', '.join(missing_required)}")

    games_report = load_games(files["Games.csv"])
    games = games_report.pop("_games")
    team_report = load_team_stats(files["TeamStatistics.csv"])
    team_rows = team_report.pop("_rows_by_game")
    player_report = load_player_stats(files["PlayerStatistics.csv"])
    player_games = player_report.pop("_games")
    pbp_report = load_pbp_metadata(files["PlayByPlay.parquet"] or input_dir / "PlayByPlay.parquet")
    pbp_games = pbp_report.pop("_games", set())

    if require_parquet_fixture and not pbp_report.get("metadata_rows_read"):
        raise AdapterError("Parquet fixture metadata is required but was not evaluable")

    game_ids = set(games)
    team_covered = 0
    team_score_matched = 0
    player_covered = 0
    pbp_covered = 0
    for game_id, game in games.items():
        rows = team_rows.get(game_id, [])
        if len(rows) == 2:
            team_covered += 1
            observed = sorted(row.get("team_score") for row in rows)
            expected = sorted([game.get("home_score"), game.get("away_score")])
            if observed == expected:
                team_score_matched += 1
        if game_id in player_games:
            player_covered += 1
        if game_id in pbp_games:
            pbp_covered += 1

    gate_results = [
        {
            "name": "policy_ready_for_implementation",
            "passed": policy_report["formal_state"] == "ROLE_LIMITED_ADAPTER_READY_FOR_IMPLEMENTATION",
            "observed": policy_report["formal_state"],
            "threshold": "ROLE_LIMITED_ADAPTER_READY_FOR_IMPLEMENTATION",
        },
        {
            "name": "fixture_games_present",
            "passed": len(game_ids) >= 2,
            "observed": len(game_ids),
            "threshold": 2,
        },
        {
            "name": "duplicate_game_id_groups",
            "passed": games_report["duplicate_game_id_groups"] == 0,
            "observed": games_report["duplicate_game_id_groups"],
            "threshold": 0,
        },
        {
            "name": "team_boxscore_fixture_coverage",
            "passed": (ratio(team_covered, len(game_ids)) or 0) == 1.0,
            "observed": ratio(team_covered, len(game_ids)),
            "threshold": 1.0,
        },
        {
            "name": "team_boxscore_score_match",
            "passed": (ratio(team_score_matched, team_covered) or 0) == 1.0,
            "observed": ratio(team_score_matched, team_covered),
            "threshold": 1.0,
        },
        {
            "name": "player_boxscore_candidate_fixture_coverage",
            "passed": (ratio(player_covered, len(game_ids)) or 0) == 1.0,
            "observed": ratio(player_covered, len(game_ids)),
            "threshold": 1.0,
            "note": "coverage-only; player stat parity remains blocked",
        },
        {
            "name": "pbp_parquet_fixture_coverage",
            "passed": (ratio(pbp_covered, len(game_ids)) or 0) == 1.0 if pbp_report.get("metadata_rows_read") else not require_parquet_fixture,
            "observed": ratio(pbp_covered, len(game_ids)) if pbp_report.get("metadata_rows_read") else None,
            "threshold": 1.0 if require_parquet_fixture else "optional_local_dependency",
            "status": "evaluated" if pbp_report.get("metadata_rows_read") else "not_evaluable_without_pyarrow",
        },
    ]
    all_passed = all(item["passed"] for item in gate_results)
    report = {
        "report_schema_version": VERSION,
        "report_type": "role_limited_adapter_self_test",
        "formal_state": PASS_STATE if all_passed else BLOCKED_STATE,
        "source_id": "kaggle_eoinamoore_historical_nba",
        "adapter_version": VERSION,
        "fixture_only": True,
        "full_eoin_bundle_execution": False,
        "deterministic_matching_only": True,
        "fuzzy_matching": False,
        "gate_results": gate_results,
        "all_adapter_gates_passed": all_passed,
        "policy_validation": {
            "schema_version": policy_report["schema_version"],
            "formal_state": policy_report["formal_state"],
            "failed_checks": policy_report["quality"]["failed_checks"],
        },
        "aggregate": {
            "fixture_games": len(game_ids),
            "team_boxscore_covered_games": team_covered,
            "team_boxscore_coverage_rate": ratio(team_covered, len(game_ids)),
            "team_boxscore_score_match_rate": ratio(team_score_matched, team_covered),
            "player_boxscore_candidate_covered_games": player_covered,
            "player_boxscore_candidate_coverage_rate": ratio(player_covered, len(game_ids)),
            "pbp_covered_games": pbp_covered if pbp_report.get("metadata_rows_read") else None,
            "pbp_game_coverage_rate": ratio(pbp_covered, len(game_ids)) if pbp_report.get("metadata_rows_read") else None,
        },
        "inputs": {
            "games": games_report,
            "team_statistics": team_report,
            "player_statistics": player_report,
            "play_by_play": pbp_report,
        },
        "boundaries": {
            "raw_eoin_rows_read": False,
            "synthetic_fixture_rows_read": True,
            "raw_rows_emitted": 0,
            "raw_files_emitted": False,
            "derived_tables_publicly_committed": [],
            "existing_silver_replacement": False,
            "existing_gold_replacement": False,
            "model_retraining": False,
            "market_metrics": False,
            "betting_decision_layer": False,
            "formal_stake": 0,
        },
        "permissions": {
            "ready_for_full_adapter_execution": False,
            "ready_for_silver_replacement": False,
            "ready_for_gold_replacement": False,
            "ready_for_model_retraining": False,
            "ready_for_market_backtest": False,
            "ready_for_betting_edge_claim": False,
            "formal_stake": 0,
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / REPORT_NAME).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / STATUS_NAME).write_text(
        json.dumps(
            {
                "schema_version": VERSION,
                "formal_state": report["formal_state"],
                "fixture_only": True,
                "all_adapter_gates_passed": all_passed,
                "raw_files_uploaded_as_artifact": False,
                "raw_rows_uploaded_as_artifact": False,
                "formal_stake": 0,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return report


def write_fixture(input_dir: Path, include_parquet: bool) -> None:
    input_dir.mkdir(parents=True, exist_ok=True)
    (input_dir / "Games.csv").write_text(
        "gameId,gameDateTimeEst,hometeamId,awayteamId,homeScore,awayScore\n"
        "22300001,2023-10-24 19:30:00,1,2,110,105\n"
        "22300002,2023-10-25 19:30:00,3,4,99,101\n"
        "22300003,2023-10-26 19:30:00,5,6,120,118\n",
        encoding="utf-8",
    )
    (input_dir / "TeamStatistics.csv").write_text(
        "gameId,gameDateTimeEst,teamId,teamScore,opponentScore\n"
        "22300001,2023-10-24 19:30:00,1,110,105\n"
        "22300001,2023-10-24 19:30:00,2,105,110\n"
        "22300002,2023-10-25 19:30:00,3,99,101\n"
        "22300002,2023-10-25 19:30:00,4,101,99\n"
        "22300003,2023-10-26 19:30:00,5,120,118\n"
        "22300003,2023-10-26 19:30:00,6,118,120\n",
        encoding="utf-8",
    )
    (input_dir / "PlayerStatistics.csv").write_text(
        "gameId,gameDate,personId,points\n"
        "22300001,2023-10-24,101,30\n"
        "22300001,2023-10-24,102,22\n"
        "22300002,2023-10-25,103,18\n"
        "22300003,2023-10-26,104,27\n",
        encoding="utf-8",
    )
    if not include_parquet:
        return
    try:
        import pyarrow as pa  # type: ignore
        import pyarrow.parquet as pq  # type: ignore
    except ImportError as exc:
        raise AdapterError("pyarrow is required to write the Parquet fixture") from exc
    table = pa.table(
        {
            "gameId": ["0022300001", "0022300001", "0022300002", "0022300003"],
            "eventNum": [1, 2, 1, 1],
        }
    )
    pq.write_table(table, input_dir / "PlayByPlay.parquet")


def self_test(output_dir: Path, policy_path: Path, evidence_path: Path, require_parquet_fixture: bool) -> None:
    with tempfile.TemporaryDirectory(prefix="nbavl-eoin-adapter-fixture-") as temp_name:
        fixture = Path(temp_name)
        write_fixture(fixture, include_parquet=require_parquet_fixture)
        report = build_aggregate_report(
            input_dir=fixture,
            output_dir=output_dir,
            policy_path=policy_path,
            evidence_path=evidence_path,
            require_parquet_fixture=require_parquet_fixture,
        )
    assert report["formal_state"] == PASS_STATE, report
    assert report["fixture_only"] is True, report
    assert report["full_eoin_bundle_execution"] is False, report
    assert report["boundaries"]["raw_eoin_rows_read"] is False, report
    assert report["boundaries"]["raw_rows_emitted"] == 0, report
    assert report["permissions"]["ready_for_full_adapter_execution"] is False, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, default=Path("data/eoin-adapter-predeclaration-v1.json"))
    parser.add_argument("--evidence", type=Path, default=Path("data/eoin-cross-source-audit-v1.json"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--require-parquet-fixture", action="store_true")
    args = parser.parse_args()

    if not args.self_test:
        raise AdapterError("full Eoin adapter execution is disabled; only --self-test is allowed in v1")

    self_test(
        output_dir=args.output_dir,
        policy_path=args.policy,
        evidence_path=args.evidence,
        require_parquet_fixture=args.require_parquet_fixture,
    )
    print("eoin role-limited adapter self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
