#!/usr/bin/env python3
"""Fetch a tightly bounded official NBA boxscore metadata subset.

Scope:
- game IDs 0022501201..0022501230: the 30 regular-season games determined
  after NBA Cup group play and omitted from the Aug. 14 schedule release;
- four known schedule-adjusted games requiring exact official reconciliation.

Only official game metadata is emitted. No odds or private archive rows are sent.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_URL = "https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{game_id}.json"
CUP_DETERMINED_IDS = tuple(f"002250{number:04d}" for number in range(1201, 1231))
ADJUSTED_IDS = ("0022501111", "0022500651", "0022500652", "0022501003")
GAME_IDS = CUP_DETERMINED_IDS + ADJUSTED_IDS
HEADERS = {
    "User-Agent": "NBA-Value-Lab-Metadata-Research/1.0",
    "Referer": "https://www.nba.com/",
    "Accept": "application/json",
    "Connection": "close",
}


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def fetch(game_id: str, timeout: int) -> tuple[dict[str, Any], bytes]:
    url = BASE_URL.format(game_id=game_id)
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
    payload = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(payload, dict):
        raise RuntimeError("response root is not an object")
    return payload, raw


def full_team_name(team: dict[str, Any]) -> str:
    city = str(team.get("teamCity") or "").strip()
    name = str(team.get("teamName") or "").strip()
    if not city or not name:
        raise RuntimeError("official team city/name missing")
    return name if name.lower().startswith(city.lower()) else f"{city} {name}"


def normalize(game_id: str, payload: dict[str, Any], raw: bytes) -> dict[str, Any]:
    game = payload.get("game")
    if not isinstance(game, dict):
        raise RuntimeError("official payload game object missing")
    returned_id = str(game.get("gameId") or "").strip()
    if returned_id != game_id:
        raise RuntimeError(f"returned game ID mismatch: {returned_id}")
    home = game.get("homeTeam")
    away = game.get("awayTeam")
    if not isinstance(home, dict) or not isinstance(away, dict):
        raise RuntimeError("official home/away team objects missing")
    tipoff = str(game.get("gameTimeUTC") or "").strip()
    if not tipoff:
        raise RuntimeError("official gameTimeUTC missing")
    return {
        "official_game_id": game_id,
        "official_away_team": full_team_name(away),
        "official_home_team": full_team_name(home),
        "scheduled_tipoff_utc": tipoff,
        "game_time_local": game.get("gameTimeLocal"),
        "game_time_home": game.get("gameTimeHome"),
        "game_time_away": game.get("gameTimeAway"),
        "game_et": game.get("gameEt"),
        "game_status": game.get("gameStatus"),
        "game_status_text": game.get("gameStatusText"),
        "arena_name": (game.get("arena") or {}).get("arenaName") if isinstance(game.get("arena"), dict) else None,
        "arena_city": (game.get("arena") or {}).get("arenaCity") if isinstance(game.get("arena"), dict) else None,
        "arena_state": (game.get("arena") or {}).get("arenaState") if isinstance(game.get("arena"), dict) else None,
        "source_url": BASE_URL.format(game_id=game_id),
        "source_payload_sha256": sha256_bytes(raw),
        "subset_reason": (
            "NBA_CUP_DETERMINED_REGULAR_SEASON_GAME"
            if game_id in CUP_DETERMINED_IDS
            else "KNOWN_SCHEDULE_ADJUSTMENT_RECONCILIATION"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--delay-seconds", type=float, default=0.25)
    args = parser.parse_args()

    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for index, game_id in enumerate(GAME_IDS):
        try:
            payload, raw = fetch(game_id, args.timeout)
            rows.append(normalize(game_id, payload, raw))
        except Exception as exc:
            failures.append({"official_game_id": game_id, "error_type": type(exc).__name__, "error": str(exc)[:300]})
        if index + 1 < len(GAME_IDS):
            time.sleep(max(0.0, args.delay_seconds))

    returned_ids = {row["official_game_id"] for row in rows}
    missing_cup = [game_id for game_id in CUP_DETERMINED_IDS if game_id not in returned_ids]
    missing_adjusted = [game_id for game_id in ADJUSTED_IDS if game_id not in returned_ids]
    valid = not missing_cup and not missing_adjusted and len(rows) == len(GAME_IDS)
    output = {
        "schema_version": "official-nba-boxscore-metadata-subset-2025-26-v1",
        "formal_state": (
            "OFFICIAL_NBA_BOXSCORE_METADATA_SUBSET_VALID"
            if valid
            else "OFFICIAL_NBA_BOXSCORE_METADATA_SUBSET_INCOMPLETE"
        ),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "requested_game_ids": list(GAME_IDS),
        "requested_count": len(GAME_IDS),
        "returned_count": len(rows),
        "missing_cup_determined_game_ids": missing_cup,
        "missing_adjusted_game_ids": missing_adjusted,
        "failures": failures,
        "games": sorted(rows, key=lambda row: (row["scheduled_tipoff_utc"], row["official_game_id"])),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "formal_state": output["formal_state"],
        "requested_count": len(GAME_IDS),
        "returned_count": len(rows),
        "missing_cup": missing_cup,
        "missing_adjusted": missing_adjusted,
        "output": str(args.output),
    }, ensure_ascii=False, indent=2))
    return 0 if valid else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
