#!/usr/bin/env python3
"""Fetch and normalize the official NBA 2025-26 schedule.

The script performs one read-only request against each official NBA schedule
candidate until a valid payload is found. It emits schedule metadata only;
no odds or user-provided archive rows are involved.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SEASON = "2025-26"
REGULAR_GAME_ID_PREFIX = "00225"
CANDIDATES = (
    "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json",
    "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json",
    "https://stats.nba.com/stats/scheduleleaguev2?LeagueID=00&Season=2025-26",
)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "close",
}


class ScheduleFetchError(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def fetch_json(url: str, timeout: int) -> tuple[dict[str, Any], bytes]:
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
    payload = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(payload, dict):
        raise ScheduleFetchError("official response root is not an object")
    return payload, raw


def iter_dicts(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from iter_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_dicts(child)


def team_name(team: Any) -> str | None:
    if not isinstance(team, dict):
        return None
    full = team.get("teamName") or team.get("team_name")
    city = team.get("teamCity") or team.get("team_city")
    name = team.get("teamName") or team.get("team_name") or team.get("nickname")
    if isinstance(full, str) and full.strip() and city and full.lower().startswith(str(city).lower()):
        return full.strip()
    if isinstance(city, str) and isinstance(name, str) and city.strip() and name.strip():
        return f"{city.strip()} {name.strip()}"
    if isinstance(full, str) and full.strip():
        return full.strip()
    return None


def normalize_game(item: dict[str, Any]) -> dict[str, Any] | None:
    game_id = item.get("gameId") or item.get("GAME_ID") or item.get("game_id")
    if game_id is None:
        return None
    game_id = str(game_id).strip()
    if not game_id.startswith(REGULAR_GAME_ID_PREFIX):
        return None

    home = item.get("homeTeam") or item.get("home_team")
    away = item.get("awayTeam") or item.get("away_team")
    home_name = team_name(home)
    away_name = team_name(away)
    if not home_name or not away_name:
        return None

    tipoff = (
        item.get("gameDateTimeUTC")
        or item.get("gameDateTimeUtc")
        or item.get("game_datetime_utc")
        or item.get("GAME_DATE_TIME_UTC")
    )
    if not isinstance(tipoff, str) or not tipoff.strip():
        game_date = item.get("gameDateUTC") or item.get("GAME_DATE_UTC")
        game_time = item.get("gameTimeUTC") or item.get("GAME_TIME_UTC")
        if isinstance(game_date, str) and isinstance(game_time, str):
            tipoff = f"{game_date.strip()}T{game_time.strip()}"
    if not isinstance(tipoff, str) or not tipoff.strip():
        return None

    return {
        "official_game_id": game_id,
        "scheduled_tipoff_utc": tipoff.strip(),
        "official_away_team": away_name,
        "official_home_team": home_name,
        "game_status": item.get("gameStatus") or item.get("GAME_STATUS"),
        "game_status_text": item.get("gameStatusText") or item.get("GAME_STATUS_TEXT"),
        "game_label": item.get("gameLabel") or item.get("GAME_LABEL"),
        "game_sub_label": item.get("gameSubLabel") or item.get("GAME_SUB_LABEL"),
        "week_name": item.get("weekName") or item.get("WEEK_NAME"),
        "arena_name": item.get("arenaName") or item.get("ARENA_NAME"),
        "arena_city": item.get("arenaCity") or item.get("ARENA_CITY"),
        "arena_state": item.get("arenaState") or item.get("ARENA_STATE"),
        "postponed_status": item.get("postponedStatus") or item.get("POSTPONED_STATUS"),
    }


def extract_games(payload: dict[str, Any]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for item in iter_dicts(payload):
        game = normalize_game(item)
        if game:
            by_id[game["official_game_id"]] = game
    games = sorted(by_id.values(), key=lambda row: (row["scheduled_tipoff_utc"], row["official_game_id"]))
    return games


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=45)
    args = parser.parse_args()

    attempts: list[dict[str, Any]] = []
    selected_url: str | None = None
    selected_raw: bytes | None = None
    games: list[dict[str, Any]] = []

    for url in CANDIDATES:
        try:
            payload, raw = fetch_json(url, args.timeout)
            candidate_games = extract_games(payload)
            attempts.append({"url": url, "success": True, "regular_season_games": len(candidate_games)})
            if len(candidate_games) >= 1000:
                selected_url = url
                selected_raw = raw
                games = candidate_games
                break
        except Exception as exc:  # network and schema evidence must be retained
            attempts.append({"url": url, "success": False, "error_type": type(exc).__name__, "error": str(exc)[:300]})

    if selected_url is None or selected_raw is None:
        raise ScheduleFetchError(f"no official schedule candidate yielded >=1000 regular-season games: {attempts}")

    output = {
        "schema_version": "official-nba-schedule-2025-26-v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "season": SEASON,
        "league_id": "00",
        "game_id_filter": REGULAR_GAME_ID_PREFIX,
        "source_url": selected_url,
        "source_payload_sha256": sha256_bytes(selected_raw),
        "source_attempts": attempts,
        "regular_season_game_count": len(games),
        "games": games,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "formal_state": "OFFICIAL_NBA_2025_26_SCHEDULE_FETCH_VALID",
        "source_url": selected_url,
        "regular_season_game_count": len(games),
        "output": str(args.output),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
