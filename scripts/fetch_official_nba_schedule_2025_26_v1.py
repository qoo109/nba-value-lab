#!/usr/bin/env python3
"""Fetch and normalize the official NBA 2025-26 schedule.

The script performs read-only requests against official NBA schedule candidates.
It emits schedule metadata only; no odds or user-provided archive rows are sent.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from collections import Counter
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
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
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


def raw_game_ids(payload: dict[str, Any]) -> list[str]:
    values: set[str] = set()
    for item in iter_dicts(payload):
        value = item.get("gameId") or item.get("GAME_ID") or item.get("game_id")
        if value is not None:
            values.add(str(value).strip())
    return sorted(values)


def team_name(team: Any) -> str | None:
    if not isinstance(team, dict):
        return None
    city = team.get("teamCity") or team.get("team_city")
    name = team.get("teamName") or team.get("team_name") or team.get("nickname")
    full = team.get("teamFullName") or team.get("team_full_name")
    if isinstance(full, str) and full.strip():
        return full.strip()
    if isinstance(city, str) and isinstance(name, str) and city.strip() and name.strip():
        if name.lower().startswith(city.lower()):
            return name.strip()
        return f"{city.strip()} {name.strip()}"
    if isinstance(name, str) and name.strip():
        return name.strip()
    return None


def normalize_game(item: dict[str, Any]) -> dict[str, Any] | None:
    game_id = item.get("gameId") or item.get("GAME_ID") or item.get("game_id")
    if game_id is None:
        return None
    game_id = str(game_id).strip()
    if not game_id.startswith(REGULAR_GAME_ID_PREFIX):
        return None

    home_name = team_name(item.get("homeTeam") or item.get("home_team"))
    away_name = team_name(item.get("awayTeam") or item.get("away_team"))
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
    return sorted(by_id.values(), key=lambda row: (row["scheduled_tipoff_utc"], row["official_game_id"]))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)

    attempts: list[dict[str, Any]] = []
    selected_url: str | None = None
    selected_raw: bytes | None = None
    games: list[dict[str, Any]] = []

    for url in CANDIDATES:
        try:
            payload, raw = fetch_json(url, args.timeout)
            ids = raw_game_ids(payload)
            prefixes = Counter(value[:5] for value in ids if len(value) >= 5)
            candidate_games = extract_games(payload)
            attempts.append({
                "url": url,
                "success": True,
                "root_keys": sorted(payload.keys()),
                "raw_unique_game_ids": len(ids),
                "sample_game_ids": ids[:5],
                "game_id_prefix_counts": dict(prefixes.most_common()),
                "regular_season_games_normalized": len(candidate_games),
                "payload_sha256": sha256_bytes(raw),
            })
            if len(candidate_games) >= 1000:
                selected_url = url
                selected_raw = raw
                games = candidate_games
                break
        except Exception as exc:
            attempts.append({
                "url": url,
                "success": False,
                "error_type": type(exc).__name__,
                "error": str(exc)[:500],
            })

    valid = selected_url is not None and selected_raw is not None
    output = {
        "schema_version": "official-nba-schedule-2025-26-v1",
        "formal_state": (
            "OFFICIAL_NBA_2025_26_SCHEDULE_FETCH_VALID"
            if valid
            else "OFFICIAL_NBA_2025_26_SCHEDULE_FETCH_NOT_YET_VALID"
        ),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "season": SEASON,
        "league_id": "00",
        "game_id_filter": REGULAR_GAME_ID_PREFIX,
        "source_url": selected_url,
        "source_payload_sha256": sha256_bytes(selected_raw) if selected_raw else None,
        "source_attempts": attempts,
        "regular_season_game_count": len(games),
        "games": games,
    }
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "formal_state": output["formal_state"],
        "source_url": selected_url,
        "regular_season_game_count": len(games),
        "source_attempts": attempts,
        "output": str(args.output),
    }, ensure_ascii=False, indent=2))
    return 0 if valid else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
