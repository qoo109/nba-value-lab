#!/usr/bin/env python3
"""Match injury-report names to player IDs from a Gold-validated boxscore roster."""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from player_identity_core import normalize_player_name, suffixless_player_name

VERSION = "injury-player-boxscore-identity-v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def unique(values: set[str]) -> str | None:
    cleaned = sorted(value for value in values if value)
    return cleaned[0] if len(cleaned) == 1 else None


def build_indexes(boxscores: list[dict[str, str]]) -> dict[str, Any]:
    team_season_exact = defaultdict(set)
    season_exact = defaultdict(set)
    global_exact = defaultdict(set)
    team_season_suffixless = defaultdict(set)
    season_suffixless = defaultdict(set)
    global_suffixless = defaultdict(set)
    for row in boxscores:
        player_id = str(row.get("PLAYER_ID", "")).strip()
        player_name = str(row.get("PLAYER_NAME", "")).strip()
        team = str(row.get("TEAM_ABBREVIATION", "")).strip()
        season = str(row.get("SEASON_YEAR", "")).strip()
        if not player_id or not player_name or not team or not season:
            continue
        exact = normalize_player_name(player_name)
        suffixless = suffixless_player_name(player_name)
        if not exact:
            continue
        team_season_exact[(season, team, exact)].add(player_id)
        season_exact[(season, exact)].add(player_id)
        global_exact[exact].add(player_id)
        team_season_suffixless[(season, team, suffixless)].add(player_id)
        season_suffixless[(season, suffixless)].add(player_id)
        global_suffixless[suffixless].add(player_id)
    return {
        "team_season_exact": team_season_exact,
        "season_exact": season_exact,
        "global_exact": global_exact,
        "team_season_suffixless": team_season_suffixless,
        "season_suffixless": season_suffixless,
        "global_suffixless": global_suffixless,
        "alias_rows": sum(len(values) for values in team_season_exact.values()),
    }


def choose(indexes: dict[str, Any], season: str, team: str, name: str):
    exact = normalize_player_name(name)
    suffixless = suffixless_player_name(name)
    scopes = [
        ("team_season_exact", indexes["team_season_exact"][(season, team, exact)], "HIGH"),
        ("season_unique_exact", indexes["season_exact"][(season, exact)], "HIGH"),
        ("global_unique_exact", indexes["global_exact"][exact], "HIGH"),
        ("team_season_unique_suffixless", indexes["team_season_suffixless"][(season, team, suffixless)], "MEDIUM"),
        ("season_unique_suffixless", indexes["season_suffixless"][(season, suffixless)], "MEDIUM"),
        ("global_unique_suffixless", indexes["global_suffixless"][suffixless], "MEDIUM"),
    ]
    for method, candidates, confidence in scopes:
        player_id = unique(candidates)
        if player_id:
            return player_id, method, confidence, len(candidates)
        if len(candidates) > 1:
            return "", f"ambiguous_{method}", "BLOCKED", len(candidates)
    return "", "unmatched", "BLOCKED", 0


def run(
    snapshot_csv: Path,
    game_map_csv: Path,
    boxscore_csv: Path,
    output_dir: Path,
) -> dict[str, Any]:
    snapshots = read_csv(snapshot_csv)
    game_map = {
        str(row.get("official_game_id", "")): row
        for row in read_csv(game_map_csv)
        if str(row.get("matched", "")).lower() in {"true", "1"}
    }
    boxscores = read_csv(boxscore_csv)
    indexes = build_indexes(boxscores)
    seasons = sorted({str(row.get("SEASON_YEAR", "")) for row in boxscores if row.get("SEASON_YEAR")})
    output = []
    missing_games = 0
    ambiguous = 0
    unmatched = 0
    methods = defaultdict(int)
    confidence = defaultdict(int)

    for snapshot in snapshots:
        official_id = str(snapshot.get("game_id", ""))
        game = game_map.get(official_id)
        if game is None:
            missing_games += 1
            continue
        season = seasons[-1] if len(seasons) == 1 else ""
        if not season:
            game_date = str(game.get("game_date", ""))
            season = next(
                (
                    row.get("SEASON_YEAR", "")
                    for row in boxscores
                    if row.get("GAME_DATE", "") == game_date
                ),
                "",
            )
        team = str(snapshot.get("team_abbr", "")).strip()
        player_id, method, level, candidate_count = choose(
            indexes, season, team, str(snapshot.get("player_name", ""))
        )
        methods[method] += 1
        confidence[level] += 1
        if method.startswith("ambiguous_"):
            ambiguous += 1
        elif method == "unmatched":
            unmatched += 1
        output.append({
            "snapshot_record_id": str(snapshot.get("snapshot_record_id", "")),
            "historical_game_id": str(game.get("historical_game_id", "")),
            "season_label": season,
            "team_abbr": team,
            "player_id": player_id,
            "match_method": method,
            "confidence": level,
            "candidate_count": candidate_count,
        })

    output_dir.mkdir(parents=True, exist_ok=True)
    fields = [
        "snapshot_record_id", "historical_game_id", "season_label", "team_abbr",
        "player_id", "match_method", "confidence", "candidate_count",
    ]
    with (output_dir / "injury-player-id-map.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output)

    total = len(snapshots)
    matched = sum(bool(row["player_id"]) for row in output)
    high = sum(row["confidence"] == "HIGH" for row in output)
    match_rate = matched / total if total else 0.0
    high_rate = high / total if total else 0.0
    ready = (
        total > 0
        and missing_games == 0
        and ambiguous == 0
        and match_rate >= 0.95
        and high_rate >= 0.90
    )
    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "coverage": {
            "snapshot_rows": total,
            "boxscore_roster_rows": len(boxscores),
            "alias_rows_available": indexes["alias_rows"],
            "matched_player_rows": matched,
            "high_confidence_rows": high,
        },
        "quality": {
            "player_match_rate": round(match_rate, 6),
            "high_confidence_match_rate": round(high_rate, 6),
            "missing_historical_game_rows": missing_games,
            "ambiguous_player_rows": ambiguous,
            "unmatched_player_rows": unmatched,
            "match_method_counts": dict(sorted(methods.items())),
            "confidence_counts": dict(sorted(confidence.items())),
        },
        "decision": {
            "ready_for_player_id_join": ready,
            "ready_for_model_training": False,
            "ready_for_betting_edge_claim": False,
        },
        "guardrails": {
            "fuzzy_edit_distance_matching_used": False,
            "nearest_name_guessing_used": False,
            "ambiguous_names_blocked": True,
            "output_contains_player_names": False,
            "output_contains_injury_reasons": False,
        },
    }
    (output_dir / "injury-player-boxscore-identity-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def self_test(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    snapshots = output_dir / "snapshots.csv"
    games = output_dir / "games.csv"
    boxscores = output_dir / "boxscores.csv"
    with snapshots.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["snapshot_record_id", "game_id", "team_abbr", "player_name"])
        writer.writeheader()
        writer.writerow({
            "snapshot_record_id": "s1", "game_id": "official:2023-12-18:DAL@DEN",
            "team_abbr": "DEN", "player_name": "Jokić, Nikola",
        })
    with games.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["official_game_id", "historical_game_id", "game_date", "matched"])
        writer.writeheader()
        writer.writerow({
            "official_game_id": "official:2023-12-18:DAL@DEN", "historical_game_id": "22300300",
            "game_date": "2023-12-18", "matched": "True",
        })
    with boxscores.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["SEASON_YEAR", "PLAYER_ID", "PLAYER_NAME", "TEAM_ABBREVIATION", "GAME_DATE"])
        writer.writeheader()
        writer.writerow({
            "SEASON_YEAR": "2023-24", "PLAYER_ID": "203999", "PLAYER_NAME": "Nikola Jokic",
            "TEAM_ABBREVIATION": "DEN", "GAME_DATE": "2023-12-01",
        })
    report = run(snapshots, games, boxscores, output_dir / "result")
    assert report["decision"]["ready_for_player_id_join"] is True, report
    assert report["quality"]["player_match_rate"] == 1.0, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-csv", type=Path)
    parser.add_argument("--game-map-csv", type=Path)
    parser.add_argument("--boxscore-csv", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("injury boxscore identity matcher self-test passed")
        return
    if not args.snapshot_csv or not args.game_map_csv or not args.boxscore_csv:
        parser.error("--snapshot-csv, --game-map-csv and --boxscore-csv are required")
    report = run(args.snapshot_csv, args.game_map_csv, args.boxscore_csv, args.output_dir)
    print(json.dumps(report["decision"], indent=2))
    if not report["decision"]["ready_for_player_id_join"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
