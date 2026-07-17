#!/usr/bin/env python3
"""Build official player game logs from NBA LiveData boxscores and an audited Gold schedule.

The row-level CSV is temporary. Aggregate provenance and QA may be retained without uploading
player-level source rows.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import gzip
import hashlib
import json
import math
import re
import shutil
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

VERSION = "official-player-game-logs-v1"
ENDPOINT_TEMPLATE = "https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{game_id}.json"
OUTPUT_COLUMNS = [
    "SEASON_YEAR", "PLAYER_ID", "PLAYER_NAME", "TEAM_ID", "TEAM_ABBREVIATION",
    "GAME_ID", "GAME_DATE", "MATCHUP", "WL", "MIN", "FGM", "FGA", "FTM", "FTA",
    "OREB", "DREB", "REB", "AST", "TOV", "STL", "BLK", "PF", "PTS", "PLUS_MINUS",
    "STARTER", "PLAYED",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def gunzip(source: Path, destination: Path) -> None:
    with gzip.open(source, "rb") as src, destination.open("wb") as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)


def open_gold(path: Path, temp_root: Path) -> sqlite3.Connection:
    if path.suffix.lower() == ".gz":
        sqlite_path = temp_root / "historical-gold.sqlite"
        gunzip(path, sqlite_path)
    else:
        sqlite_path = path
    db = sqlite3.connect(sqlite_path)
    tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    required = {"gold_matchup_features", "gold_team_game_features"}
    missing = sorted(required - tables)
    if missing:
        db.close()
        raise ValueError(f"Gold database missing tables: {missing}")
    return db


def schedule_rows(db: sqlite3.Connection, season: str) -> list[dict[str, str]]:
    rows = db.execute(
        """
        SELECT m.game_id, m.game_date, m.home_team_abbr, m.away_team_abbr, h.season_label
        FROM gold_matchup_features m
        JOIN gold_team_game_features h ON h.feature_id=m.home_feature_id
        WHERE h.season_label=?
        ORDER BY m.game_date, m.game_id
        """,
        (season,),
    ).fetchall()
    output = [
        {
            "game_id": str(game_id),
            "game_date": str(game_date),
            "home_team_abbr": str(home),
            "away_team_abbr": str(away),
            "season_label": str(season_label),
        }
        for game_id, game_date, home, away, season_label in rows
    ]
    duplicate_ids = len(output) - len({row["game_id"] for row in output})
    if duplicate_ids:
        raise ValueError(f"Gold schedule contains {duplicate_ids} duplicate game IDs")
    invalid = [row["game_id"] for row in output if not re.fullmatch(r"\d{10}", row["game_id"])]
    if invalid:
        raise ValueError(f"Gold schedule contains invalid game IDs: {invalid[:5]}")
    if not output:
        raise ValueError(f"Gold schedule has no rows for {season}")
    return output


def parse_duration_minutes(value: Any) -> float:
    text = str(value or "").strip()
    if not text:
        return 0.0
    if re.fullmatch(r"\d+(?:\.\d+)?", text):
        return float(text)
    match = re.fullmatch(
        r"P(?:\d+D)?T(?:(\d+(?:\.\d+)?)H)?(?:(\d+(?:\.\d+)?)M)?(?:(\d+(?:\.\d+)?)S)?",
        text,
    )
    if not match:
        raise ValueError(f"unsupported NBA minutes duration: {value!r}")
    hours = float(match.group(1) or 0)
    minutes = float(match.group(2) or 0)
    seconds = float(match.group(3) or 0)
    return round(hours * 60 + minutes + seconds / 60, 6)


def number(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
        return result if math.isfinite(result) else default
    except (TypeError, ValueError):
        return default


def integer(value: Any, default: int = 0) -> int:
    return int(round(number(value, default)))


def played_flag(player: dict[str, Any], minutes: float) -> bool:
    raw = player.get("played")
    if isinstance(raw, bool):
        return raw or minutes > 0
    return str(raw or "").strip().lower() in {"1", "true", "yes"} or minutes > 0


def player_rows(payload: dict[str, Any], schedule: dict[str, str]) -> list[dict[str, Any]]:
    game = payload.get("game")
    if not isinstance(game, dict):
        raise ValueError("official boxscore response missing game")
    if str(game.get("gameId")) != schedule["game_id"]:
        raise ValueError("official boxscore game ID does not match Gold schedule")
    home = game.get("homeTeam") or {}
    away = game.get("awayTeam") or {}
    home_abbr = str(home.get("teamTricode") or "")
    away_abbr = str(away.get("teamTricode") or "")
    if home_abbr != schedule["home_team_abbr"] or away_abbr != schedule["away_team_abbr"]:
        raise ValueError(
            f"official boxscore sides {away_abbr}@{home_abbr} do not match "
            f"Gold {schedule['away_team_abbr']}@{schedule['home_team_abbr']}"
        )
    home_score, away_score = integer(home.get("score")), integer(away.get("score"))
    output: list[dict[str, Any]] = []
    for team, opponent, is_home in ((home, away, True), (away, home, False)):
        team_abbr = str(team.get("teamTricode") or "")
        opponent_abbr = str(opponent.get("teamTricode") or "")
        team_score = home_score if is_home else away_score
        opponent_score = away_score if is_home else home_score
        wl = "W" if team_score > opponent_score else "L" if team_score < opponent_score else "T"
        matchup = f"{team_abbr} vs. {opponent_abbr}" if is_home else f"{team_abbr} @ {opponent_abbr}"
        for player in team.get("players") or []:
            statistics = player.get("statistics") or {}
            minutes = parse_duration_minutes(statistics.get("minutes"))
            if not played_flag(player, minutes):
                continue
            player_id = str(player.get("personId") or "").strip()
            if not player_id or player_id == "0":
                raise ValueError("played player is missing personId")
            name = str(
                player.get("name")
                or " ".join(filter(None, [player.get("firstName"), player.get("familyName")]))
            ).strip()
            output.append({
                "SEASON_YEAR": schedule["season_label"],
                "PLAYER_ID": player_id,
                "PLAYER_NAME": name,
                "TEAM_ID": str(team.get("teamId") or ""),
                "TEAM_ABBREVIATION": team_abbr,
                "GAME_ID": schedule["game_id"],
                "GAME_DATE": schedule["game_date"],
                "MATCHUP": matchup,
                "WL": wl,
                "MIN": minutes,
                "FGM": integer(statistics.get("fieldGoalsMade")),
                "FGA": integer(statistics.get("fieldGoalsAttempted")),
                "FTM": integer(statistics.get("freeThrowsMade")),
                "FTA": integer(statistics.get("freeThrowsAttempted")),
                "OREB": integer(statistics.get("reboundsOffensive")),
                "DREB": integer(statistics.get("reboundsDefensive")),
                "REB": integer(statistics.get("reboundsTotal")),
                "AST": integer(statistics.get("assists")),
                "TOV": integer(statistics.get("turnovers")),
                "STL": integer(statistics.get("steals")),
                "BLK": integer(statistics.get("blocks")),
                "PF": integer(statistics.get("foulsPersonal")),
                "PTS": integer(statistics.get("points")),
                "PLUS_MINUS": number(statistics.get("plusMinusPoints")),
                "STARTER": int(str(player.get("starter") or "").lower() in {"1", "true", "yes"}),
                "PLAYED": 1,
            })
    return output


async def fetch_one(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
    schedule: dict[str, str],
    retries: int,
) -> tuple[str, list[dict[str, Any]], str, int]:
    url = ENDPOINT_TEMPLATE.format(game_id=schedule["game_id"])
    errors = []
    async with semaphore:
        for attempt in range(1, retries + 1):
            try:
                response = await client.get(url)
                response.raise_for_status()
                rows = player_rows(response.json(), schedule)
                digest = hashlib.sha256(response.content).hexdigest()
                return schedule["game_id"], rows, digest, attempt
            except Exception as exc:
                errors.append(f"attempt {attempt}: {type(exc).__name__}: {exc}")
                if attempt < retries:
                    await asyncio.sleep(min(0.5 * (2 ** (attempt - 1)), 4.0))
    raise RuntimeError(f"{schedule['game_id']}: " + " | ".join(errors))


async def fetch_all(
    schedules: list[dict[str, str]],
    concurrency: int,
    retries: int,
    timeout_seconds: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)
    semaphore = asyncio.Semaphore(concurrency)
    successes: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(timeout_seconds, connect=10.0),
        follow_redirects=True,
        limits=limits,
        headers={"User-Agent": "NBA-Value-Lab-Research/1.0", "Accept": "application/json"},
    ) as client:
        tasks = [fetch_one(client, semaphore, schedule, retries) for schedule in schedules]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    for schedule, result in zip(schedules, results):
        if isinstance(result, Exception):
            errors.append(f"{schedule['game_id']}: {type(result).__name__}: {result}")
            continue
        game_id, game_rows, digest, attempts = result
        rows.extend(game_rows)
        successes.append({
            "game_id": game_id,
            "response_sha256": digest,
            "player_rows": len(game_rows),
            "attempts": attempts,
        })
    return rows, successes, errors


def fetch(
    season: str,
    gold_path: Path,
    output_dir: Path,
    concurrency: int = 8,
    retries: int = 3,
    timeout_seconds: float = 25.0,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    retrieved_at = utc_now()
    with tempfile.TemporaryDirectory(prefix="nbavl-player-boxscores-") as temp_name:
        db = open_gold(gold_path, Path(temp_name))
        schedules = schedule_rows(db, season)
        db.close()
    rows, successes, errors = asyncio.run(
        fetch_all(schedules, concurrency, retries, timeout_seconds)
    )
    rows.sort(key=lambda row: (row["GAME_DATE"], row["GAME_ID"], row["PLAYER_ID"]))
    keys = [(str(row["GAME_ID"]), str(row["PLAYER_ID"])) for row in rows]
    duplicate_keys = len(keys) - len(set(keys))
    minutes_invalid = sum(not 0 <= number(row["MIN"]) <= 69 for row in rows)
    game_player_counts: dict[str, int] = {}
    for row in rows:
        game_player_counts[row["GAME_ID"]] = game_player_counts.get(row["GAME_ID"], 0) + 1
    low_player_games = sum(count < 10 for count in game_player_counts.values())
    unique_players = len({row["PLAYER_ID"] for row in rows})
    aggregate_hash = hashlib.sha256(
        "\n".join(
            f"{item['game_id']}:{item['response_sha256']}" for item in sorted(successes, key=lambda item: item["game_id"])
        ).encode("utf-8")
    ).hexdigest()

    csv_path = output_dir / "official-player-game-logs.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    success_games = len(successes)
    schedule_games = len(schedules)
    game_coverage = success_games / schedule_games if schedule_games else 0.0
    ready = (
        schedule_games >= 1200
        and game_coverage >= 0.995
        and len(rows) >= 20000
        and unique_players >= 500
        and duplicate_keys == 0
        and minutes_invalid == 0
        and low_player_games == 0
    )
    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "source": {
            "provider": "NBA Official LiveData",
            "endpoint_template": ENDPOINT_TEMPLATE,
            "season_requested": season,
            "retrieved_at": retrieved_at,
            "combined_response_sha256": aggregate_hash,
            "gold_schedule_path_name": gold_path.name,
            "concurrency": concurrency,
            "retries": retries,
        },
        "coverage": {
            "schedule_games": schedule_games,
            "successful_games": success_games,
            "failed_games": len(errors),
            "game_coverage": round(game_coverage, 6),
            "player_game_rows": len(rows),
            "unique_players": unique_players,
        },
        "quality": {
            "duplicate_game_player_keys": duplicate_keys,
            "invalid_minutes_rows": minutes_invalid,
            "games_with_fewer_than_10_played_players": low_player_games,
            "failed_game_examples": errors[:20],
            "retried_games": sum(item["attempts"] > 1 for item in successes),
            "official_game_and_team_sides_validated": True,
        },
        "decision": {
            "ready_for_point_in_time_feature_build": ready,
            "ready_for_model_training": False,
            "ready_for_betting_edge_claim": False,
            "reason": "Source and schema pilot only; strict prior-game feature generation is still required.",
        },
        "guardrails": {
            "source_rows_committed": False,
            "postgame_rows_may_only_influence_later_games": True,
            "same_game_statistics_allowed_as_features": False,
            "gold_schedule_is_request_allowlist": True,
        },
    }
    (output_dir / "official-player-game-logs-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def self_test(output_dir: Path) -> None:
    assert parse_duration_minutes("PT34M12.00S") == 34.2
    assert parse_duration_minutes("PT1H2M30S") == 62.5
    schedule = {
        "game_id": "0022300001", "game_date": "2023-10-24", "season_label": "2023-24",
        "home_team_abbr": "DEN", "away_team_abbr": "LAL",
    }
    player = {
        "personId": 1, "name": "Example Player", "played": "1", "starter": "1",
        "statistics": {
            "minutes": "PT30M", "fieldGoalsMade": 5, "fieldGoalsAttempted": 10,
            "freeThrowsMade": 2, "freeThrowsAttempted": 2, "reboundsOffensive": 1,
            "reboundsDefensive": 4, "reboundsTotal": 5, "assists": 6, "turnovers": 2,
            "steals": 1, "blocks": 1, "foulsPersonal": 2, "points": 13,
            "plusMinusPoints": 4,
        },
    }
    payload = {
        "game": {
            "gameId": schedule["game_id"],
            "homeTeam": {"teamId": 10, "teamTricode": "DEN", "score": 110, "players": [player]},
            "awayTeam": {"teamId": 20, "teamTricode": "LAL", "score": 100, "players": [player]},
        }
    }
    rows = player_rows(payload, schedule)
    assert len(rows) == 2
    assert rows[0]["MIN"] == 30.0
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "self-test.json").write_text('{"passed":true}\n', encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", default="2023-24")
    parser.add_argument("--gold", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--timeout-seconds", type=float, default=25.0)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("official player game logs importer self-test passed")
        return
    if not args.gold:
        parser.error("--gold is required unless --self-test is used")
    report = fetch(
        args.season, args.gold, args.output_dir, args.concurrency, args.retries, args.timeout_seconds
    )
    print(json.dumps(report["decision"], indent=2))
    if not report["decision"]["ready_for_point_in_time_feature_build"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
