#!/usr/bin/env python3
"""Aggregate-only Eoin vs shufinskiy 2023-24 cross-source audit.

The audit compares Eoin game/team/player/PBP availability against the existing
shufinskiy/nba_data 2023-24 event-level reference. It writes aggregate reports
only and does not approve Silver or Gold replacement.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import tarfile
import tempfile
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any

from historical_phase2_core import download, select_csv
from historical_silver_schema import parse_score
import run_eoin_kaggle_census_v1 as eoin_download

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "historical-source-pilot.json"
VERSION = "eoin-cross-source-audit-v1"
PILOT_SEASON_LABEL = "2023-24"
PILOT_SEASON_START_YEAR = 2023
FROZEN_GATES = {
    "minimum_reference_games": 1000,
    "game_identity_match_rate_minimum": 0.98,
    "final_score_match_rate_minimum": 0.98,
    "team_boxscore_coverage_minimum": 0.98,
    "player_boxscore_coverage_minimum": 0.95,
    "pbp_game_coverage_minimum_when_claimed": 0.95,
    "exact_duplicate_games_maximum": 0,
}


class CrossSourceError(RuntimeError):
    """Raised when input data cannot be audited."""


def read_csv(path: Path):
    return path.open("r", encoding="utf-8-sig", errors="replace", newline="")


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


def find_named_file(input_dir: Path, filename: str) -> Path | None:
    direct = input_dir / filename
    if direct.exists():
        return direct
    matches = sorted(path for path in input_dir.rglob(filename) if path.is_file())
    return matches[0] if matches else None


def load_eoin_games(path: Path, season_start: int) -> dict[str, dict[str, Any]]:
    games: dict[str, dict[str, Any]] = {}
    duplicate_ids = Counter()
    total_rows = selected_rows = missing_id_rows = 0
    with read_csv(path) as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            total_rows += 1
            game_day = parse_date(row.get("gameDate") or row.get("gameDateTimeEst"))
            if game_day is None or season_start_year(game_day) != season_start:
                continue
            selected_rows += 1
            game_id = normalize_game_id(row.get("gameId"))
            if not game_id:
                missing_id_rows += 1
                continue
            if game_id in games:
                duplicate_ids[game_id] += 1
            games.setdefault(
                game_id,
                {
                    "game_date": game_day.isoformat(),
                    "home_team_id": str(row.get("hometeamId") or "").strip(),
                    "away_team_id": str(row.get("awayteamId") or "").strip(),
                    "home_score": as_int(row.get("homeScore")),
                    "away_score": as_int(row.get("awayScore")),
                },
            )
    return {
        "_games": games,
        "total_rows": total_rows,
        "selected_rows": selected_rows,
        "unique_games": len(games),
        "duplicate_game_id_groups": len(duplicate_ids),
        "missing_id_rows": missing_id_rows,
    }


def load_eoin_team_stats(path: Path, season_start: int) -> dict[str, Any]:
    rows_by_game: dict[str, list[dict[str, Any]]] = {}
    key_counts = Counter()
    total_rows = selected_rows = 0
    with read_csv(path) as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            total_rows += 1
            game_day = parse_date(row.get("gameDateTimeEst") or row.get("gameDate"))
            if game_day is None or season_start_year(game_day) != season_start:
                continue
            selected_rows += 1
            game_id = normalize_game_id(row.get("gameId"))
            team_id = str(row.get("teamId") or "").strip()
            if not game_id:
                continue
            key_counts[(game_id, team_id)] += 1
            rows_by_game.setdefault(game_id, []).append(
                {
                    "team_id": team_id,
                    "team_score": as_int(row.get("teamScore")),
                    "opponent_score": as_int(row.get("opponentScore")),
                }
            )
    return {
        "_rows_by_game": rows_by_game,
        "total_rows": total_rows,
        "selected_rows": selected_rows,
        "unique_games": len(rows_by_game),
        "duplicate_game_team_key_groups": sum(1 for count in key_counts.values() if count > 1),
    }


def load_eoin_player_stats(path: Path, season_start: int) -> dict[str, Any]:
    games = set()
    key_counts = Counter()
    total_rows = selected_rows = 0
    with read_csv(path) as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            total_rows += 1
            game_day = parse_date(row.get("gameDate") or row.get("gameDateTimeEst"))
            if game_day is None or season_start_year(game_day) != season_start:
                continue
            selected_rows += 1
            game_id = normalize_game_id(row.get("gameId"))
            person_id = str(row.get("personId") or "").strip()
            if not game_id:
                continue
            games.add(game_id)
            if person_id:
                key_counts[(game_id, person_id)] += 1
    return {
        "_games": games,
        "total_rows": total_rows,
        "selected_rows": selected_rows,
        "unique_games": len(games),
        "duplicate_game_player_key_groups": sum(1 for count in key_counts.values() if count > 1),
    }


def load_reference_nbastats(path: Path) -> dict[str, Any]:
    games: dict[str, dict[str, Any]] = {}
    event_counts = Counter()
    exact_keys = Counter()
    total_rows = missing_game_id_rows = score_rows = 0
    with read_csv(path) as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            total_rows += 1
            game_id = normalize_game_id(row.get("GAME_ID"))
            if not game_id:
                missing_game_id_rows += 1
                continue
            event_num = str(row.get("EVENTNUM") or "").strip()
            exact_keys[(game_id, event_num)] += 1
            event_counts[game_id] += 1
            away_score, home_score = parse_score(row.get("SCORE"))
            if away_score is not None and home_score is not None:
                score_rows += 1
                games.setdefault(game_id, {})
                games[game_id].update({"away_score": away_score, "home_score": home_score})
            else:
                games.setdefault(game_id, {})
    duplicate_event_key_groups = sum(1 for count in exact_keys.values() if count > 1)
    return {
        "_games": games,
        "total_rows": total_rows,
        "unique_games": len(games),
        "missing_game_id_rows": missing_game_id_rows,
        "score_rows": score_rows,
        "duplicate_game_event_key_groups": duplicate_event_key_groups,
        "event_rows_per_game": {
            "min": min(event_counts.values()) if event_counts else None,
            "max": max(event_counts.values()) if event_counts else None,
            "total": sum(event_counts.values()),
        },
    }


def load_eoin_pbp_games(path: Path) -> dict[str, Any]:
    result = {
        "present": path.exists(),
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
    parquet = pq.ParquetFile(path)
    result["metadata_rows_read"] = True
    result["row_count"] = parquet.metadata.num_rows
    candidates = [name for name in parquet.schema.names if name.lower().replace("_", "") == "gameid"]
    if not candidates:
        return result
    column = candidates[0]
    result["game_column"] = column
    chunks = []
    for batch in parquet.iter_batches(columns=[column], batch_size=250_000):
        chunks.append(batch.column(0))
    if not chunks:
        result["unique_games"] = 0
        result["_games"] = set()
        return result
    values = pc.unique(chunks[0].combine_chunks() if hasattr(chunks[0], "combine_chunks") else chunks[0])
    # When there are multiple batches, merge in Python after the column-only unique pass.
    games = {normalize_game_id(item.as_py()) for item in values if normalize_game_id(item.as_py())}
    for chunk in chunks[1:]:
        unique = pc.unique(chunk)
        games.update(normalize_game_id(item.as_py()) for item in unique if normalize_game_id(item.as_py()))
    result["unique_games"] = len(games)
    result["_games"] = games
    return result


def prepare_reference_csv(config_path: Path, output_dir: Path, max_mb: int) -> tuple[Path, dict[str, Any]]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    source = config["sources"]["nbastats_2023"]
    archive = output_dir / "nbastats_2023.tar.xz"
    extracted = output_dir / "nbastats_2023_raw"
    extracted.mkdir(parents=True, exist_ok=True)
    info = download(source["url"], archive, max_mb * 1048576)
    info["member_count"] = safe_extract_tar_xz(archive, extracted)
    csv_path = select_csv(extracted, source)
    info["csv_name"] = csv_path.name
    info["csv_bytes"] = csv_path.stat().st_size
    return csv_path, info


def safe_extract_tar_xz(archive: Path, destination: Path) -> int:
    root = destination.resolve()
    with tarfile.open(archive, "r:xz") as handle:
        members = handle.getmembers()
        for member in members:
            resolved = (root / member.name).resolve()
            if root not in resolved.parents and resolved != root:
                raise ValueError(f"unsafe archive path: {member.name}")
            if member.issym() or member.islnk():
                raise ValueError(f"archive link rejected: {member.name}")
        handle.extractall(root, members=members)
    return len(members)


def compare_sources(eoin_root: Path, reference_csv: Path, output_dir: Path) -> dict[str, Any]:
    games_path = find_named_file(eoin_root, "Games.csv")
    team_path = find_named_file(eoin_root, "TeamStatistics.csv")
    player_path = find_named_file(eoin_root, "PlayerStatistics.csv")
    pbp_path = find_named_file(eoin_root, "PlayByPlay.parquet") or eoin_root / "PlayByPlay.parquet"
    missing = [
        name
        for name, path in {
            "Games.csv": games_path,
            "TeamStatistics.csv": team_path,
            "PlayerStatistics.csv": player_path,
        }.items()
        if path is None
    ]
    if missing:
        raise CrossSourceError(f"missing Eoin required files: {', '.join(missing)}")

    eoin_games_report = load_eoin_games(games_path, PILOT_SEASON_START_YEAR)
    eoin_games = eoin_games_report.pop("_games")
    eoin_team_report = load_eoin_team_stats(team_path, PILOT_SEASON_START_YEAR)
    eoin_team_rows = eoin_team_report.pop("_rows_by_game")
    eoin_player_report = load_eoin_player_stats(player_path, PILOT_SEASON_START_YEAR)
    eoin_player_games = eoin_player_report.pop("_games")
    eoin_pbp_report = load_eoin_pbp_games(pbp_path)
    eoin_pbp_games = eoin_pbp_report.pop("_games", set())
    reference_report = load_reference_nbastats(reference_csv)
    reference_games = reference_report.pop("_games")

    reference_ids = set(reference_games)
    eoin_ids = set(eoin_games)
    matched_ids = reference_ids & eoin_ids
    missing_from_eoin = reference_ids - eoin_ids
    extra_eoin = eoin_ids - reference_ids

    score_comparable = score_matches = 0
    team_boxscore_covered = team_boxscore_score_matches = 0
    player_covered = 0
    pbp_covered = 0
    pbp_evaluable = eoin_pbp_report.get("unique_games") is not None
    for game_id in matched_ids:
        reference = reference_games[game_id]
        eoin = eoin_games[game_id]
        if None not in (
            reference.get("home_score"),
            reference.get("away_score"),
            eoin.get("home_score"),
            eoin.get("away_score"),
        ):
            score_comparable += 1
            if (
                reference["home_score"] == eoin["home_score"]
                and reference["away_score"] == eoin["away_score"]
            ):
                score_matches += 1

        team_rows = eoin_team_rows.get(game_id, [])
        if len(team_rows) == 2:
            team_boxscore_covered += 1
            scores = sorted(row["team_score"] for row in team_rows)
            expected = sorted([reference.get("home_score"), reference.get("away_score")])
            if scores == expected:
                team_boxscore_score_matches += 1
        if game_id in eoin_player_games:
            player_covered += 1
        if pbp_evaluable and game_id in eoin_pbp_games:
            pbp_covered += 1

    pbp_gate = {
        "name": "pbp_game_coverage_when_claimed",
        "passed": (ratio(pbp_covered, len(reference_ids)) or 0) >= FROZEN_GATES["pbp_game_coverage_minimum_when_claimed"] if pbp_evaluable else None,
        "observed": ratio(pbp_covered, len(reference_ids)) if pbp_evaluable else None,
        "threshold": FROZEN_GATES["pbp_game_coverage_minimum_when_claimed"],
        "status": "evaluated" if pbp_evaluable else "not_evaluable",
    }
    if not pbp_evaluable:
        pbp_gate["note"] = "PBP Parquet game coverage requires pyarrow metadata access and a detectable gameId column"

    gates = [
        {
            "name": "minimum_reference_games",
            "passed": len(reference_ids) >= FROZEN_GATES["minimum_reference_games"],
            "observed": len(reference_ids),
            "threshold": FROZEN_GATES["minimum_reference_games"],
        },
        {
            "name": "game_identity_match_rate",
            "passed": (ratio(len(matched_ids), len(reference_ids)) or 0) >= FROZEN_GATES["game_identity_match_rate_minimum"],
            "observed": ratio(len(matched_ids), len(reference_ids)),
            "threshold": FROZEN_GATES["game_identity_match_rate_minimum"],
        },
        {
            "name": "final_score_match_rate",
            "passed": (ratio(score_matches, score_comparable) or 0) >= FROZEN_GATES["final_score_match_rate_minimum"],
            "observed": ratio(score_matches, score_comparable),
            "threshold": FROZEN_GATES["final_score_match_rate_minimum"],
        },
        {
            "name": "team_boxscore_coverage",
            "passed": (ratio(team_boxscore_covered, len(reference_ids)) or 0) >= FROZEN_GATES["team_boxscore_coverage_minimum"],
            "observed": ratio(team_boxscore_covered, len(reference_ids)),
            "threshold": FROZEN_GATES["team_boxscore_coverage_minimum"],
        },
        {
            "name": "player_boxscore_candidate_coverage",
            "passed": (ratio(player_covered, len(reference_ids)) or 0) >= FROZEN_GATES["player_boxscore_coverage_minimum"],
            "observed": ratio(player_covered, len(reference_ids)),
            "threshold": FROZEN_GATES["player_boxscore_coverage_minimum"],
            "note": "coverage only; shufinskiy nbastats is not an independent player boxscore stat reference",
        },
        pbp_gate,
        {
            "name": "exact_duplicate_games",
            "passed": eoin_games_report["duplicate_game_id_groups"] <= FROZEN_GATES["exact_duplicate_games_maximum"],
            "observed": eoin_games_report["duplicate_game_id_groups"],
            "threshold": FROZEN_GATES["exact_duplicate_games_maximum"],
        },
    ]
    any_not_evaluable = any(item.get("passed") is None for item in gates)
    all_core = (not any_not_evaluable) and all(item["passed"] for item in gates)
    formal_outcome = (
        "AUDIT_INCOMPLETE"
        if any_not_evaluable
        else "ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE"
        if all_core
        else "SECONDARY_SOURCE_REJECTED"
    )
    report = {
        "report_schema_version": VERSION,
        "report_type": "aggregate_cross_source_audit",
        "source_id": "kaggle_eoinamoore_historical_nba",
        "reference_source_id": "shufinskiy_nba_data_nbastats_2023",
        "pilot_season": PILOT_SEASON_LABEL,
        "deterministic_matching_only": True,
        "fuzzy_matching": False,
        "frozen_gates": FROZEN_GATES,
        "gate_results": gates,
        "all_core_gates_passed": all_core,
        "formal_outcome": formal_outcome,
        "formal_source_replacement_approved": False,
        "existing_silver_replacement": False,
        "existing_gold_replacement": False,
        "formal_stake": 0,
        "reference": reference_report | {"unique_games": len(reference_ids)},
        "eoin": {
            "games": eoin_games_report,
            "team_statistics": eoin_team_report,
            "player_statistics": eoin_player_report,
            "play_by_play": eoin_pbp_report,
        },
        "comparison": {
            "reference_games": len(reference_ids),
            "eoin_pilot_games": len(eoin_ids),
            "matched_games": len(matched_ids),
            "game_identity_match_rate": ratio(len(matched_ids), len(reference_ids)),
            "missing_from_eoin_count": len(missing_from_eoin),
            "extra_eoin_pilot_game_count": len(extra_eoin),
            "score_comparable_games": score_comparable,
            "score_match_games": score_matches,
            "final_score_match_rate": ratio(score_matches, score_comparable),
            "team_boxscore_covered_games": team_boxscore_covered,
            "team_boxscore_coverage_rate": ratio(team_boxscore_covered, len(reference_ids)),
            "team_boxscore_score_match_games": team_boxscore_score_matches,
            "team_boxscore_score_match_rate": ratio(team_boxscore_score_matches, team_boxscore_covered),
            "player_boxscore_candidate_covered_games": player_covered,
            "player_boxscore_candidate_coverage_rate": ratio(player_covered, len(reference_ids)),
            "pbp_covered_games": pbp_covered,
            "pbp_game_coverage_rate": ratio(pbp_covered, len(reference_ids)),
        },
        "limitations": [
            "shufinskiy nbastats provides independent game and event-level reference, not complete independent player boxscore stat rows",
            "player boxscore result is coverage-only and cannot approve player stat parity by itself",
            "raw Eoin rows, raw shufinskiy rows, archives, and databases are not uploaded",
        ],
        "boundaries": {
            "raw_rows_emitted": 0,
            "raw_files_emitted": False,
            "model_metrics": False,
            "market_metrics": False,
            "betting_decision_layer": False,
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "eoin_cross_source_audit_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def run_live(output_dir: Path, dataset_handle: str, config_path: Path, max_download_mb: int) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    status = {
        "schema_version": VERSION,
        "dataset_handle": dataset_handle,
        "cross_source_audit_complete": False,
        "raw_files_uploaded_as_artifact": False,
        "raw_rows_uploaded_as_artifact": False,
        "formal_stake": 0,
    }
    with tempfile.TemporaryDirectory(prefix="nbavl-eoin-cross-source-") as temp_name:
        temp = Path(temp_name)
        try:
            eoin_root = eoin_download.download_dataset(dataset_handle, temp / "eoin")
            reference_csv, reference_download = prepare_reference_csv(config_path, temp / "reference", max_download_mb)
            report = compare_sources(eoin_root, reference_csv, output_dir)
            status.update(
                {
                    "cross_source_audit_complete": True,
                    "formal_outcome": report["formal_outcome"],
                    "all_core_gates_passed": report["all_core_gates_passed"],
                    "reference_games": report["comparison"]["reference_games"],
                    "matched_games": report["comparison"]["matched_games"],
                    "final_score_match_rate": report["comparison"]["final_score_match_rate"],
                    "reference_download": reference_download,
                    "temporary_raw_files_deleted": True,
                }
            )
        except Exception as exc:
            status["error"] = f"{type(exc).__name__}: {exc}"
            (output_dir / "eoin-cross-source-run-status.json").write_text(
                json.dumps(status, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            raise
    (output_dir / "eoin-cross-source-run-status.json").write_text(
        json.dumps(status, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return status


def self_test(output_dir: Path) -> None:
    root = output_dir / "synthetic"
    eoin = root / "eoin"
    ref = root / "ref"
    eoin.mkdir(parents=True, exist_ok=True)
    ref.mkdir(parents=True, exist_ok=True)
    (eoin / "Games.csv").write_text(
        "gameId,gameDateTimeEst,hometeamId,awayteamId,homeScore,awayScore\n"
        "22300001,2023-10-24 19:30:00,1,2,110,105\n"
        "22300002,2023-10-25 19:30:00,3,4,99,101\n",
        encoding="utf-8",
    )
    (eoin / "TeamStatistics.csv").write_text(
        "gameId,gameDateTimeEst,teamId,teamScore,opponentScore\n"
        "22300001,2023-10-24 19:30:00,1,110,105\n"
        "22300001,2023-10-24 19:30:00,2,105,110\n"
        "22300002,2023-10-25 19:30:00,3,99,101\n"
        "22300002,2023-10-25 19:30:00,4,101,99\n",
        encoding="utf-8",
    )
    (eoin / "PlayerStatistics.csv").write_text(
        "gameId,gameDateTimeEst,personId\n"
        "22300001,2023-10-24 19:30:00,101\n"
        "22300002,2023-10-25 19:30:00,102\n",
        encoding="utf-8",
    )
    ref_csv = ref / "nbastats.csv"
    ref_csv.write_text(
        "GAME_ID,EVENTNUM,SCORE\n"
        "0022300001,1,\n"
        "0022300001,2,105 - 110\n"
        "0022300002,1,\n"
        "0022300002,2,101 - 99\n",
        encoding="utf-8",
    )
    report = compare_sources(eoin, ref_csv, output_dir)
    assert report["comparison"]["matched_games"] == 2, report
    assert report["comparison"]["final_score_match_rate"] == 1.0, report
    assert report["comparison"]["team_boxscore_coverage_rate"] == 1.0, report
    assert report["boundaries"]["raw_rows_emitted"] == 0, report
    (output_dir / "self-test.json").write_text('{"passed":true}\n', encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-handle", default=eoin_download.DEFAULT_DATASET_HANDLE)
    parser.add_argument("--eoin-root", type=Path)
    parser.add_argument("--reference-csv", type=Path)
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--max-download-mb", type=int, default=600)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test(args.output_dir)
        print("eoin cross-source audit self-test passed")
        return 0

    if args.eoin_root and args.reference_csv:
        report = compare_sources(args.eoin_root, args.reference_csv, args.output_dir)
        print(json.dumps({
            "formal_outcome": report["formal_outcome"],
            "all_core_gates_passed": report["all_core_gates_passed"],
            "matched_games": report["comparison"]["matched_games"],
            "final_score_match_rate": report["comparison"]["final_score_match_rate"],
            "raw_rows_emitted": 0,
        }, sort_keys=True))
        return 0

    status = run_live(args.output_dir, args.dataset_handle, args.config, args.max_download_mb)
    print(json.dumps(status, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
