#!/usr/bin/env python3
"""Build lightweight point-in-time NBA schedule and source-health snapshots.

Uses only Python's standard library so it can run on GitHub Actions for free.
No API key is required. The script prefers the NBA static schedule feed and
falls back to the NBA Live Data scoreboard feed.
"""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "current"
TAIPEI = ZoneInfo("Asia/Taipei")
USER_AGENT = "NBA-Value-Lab/4.4 research-contact-github-qoo109"

SOURCES = [
    (
        "nba_schedule_static",
        "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json",
        "schedule",
    ),
    (
        "nba_live_scoreboard",
        "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json",
        "scoreboard",
    ),
]


@dataclass
class FetchResult:
    source_id: str
    url: str
    payload: dict[str, Any] | None
    fetched_at: datetime
    raw_hash: str | None
    error: str | None


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def fetch_json(source_id: str, url: str) -> FetchResult:
    fetched_at = datetime.now(timezone.utc)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json,text/plain,*/*",
            "Referer": "https://www.nba.com/",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()
        payload = json.loads(raw.decode("utf-8"))
        return FetchResult(
            source_id=source_id,
            url=url,
            payload=payload,
            fetched_at=fetched_at,
            raw_hash=hashlib.sha256(raw).hexdigest(),
            error=None,
        )
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return FetchResult(
            source_id=source_id,
            url=url,
            payload=None,
            fetched_at=fetched_at,
            raw_hash=None,
            error=f"{type(exc).__name__}: {exc}",
        )


def team(team: dict[str, Any]) -> dict[str, Any]:
    return {
        "team_id": str(team.get("teamId") or team.get("teamId", "")),
        "tricode": team.get("teamTricode") or team.get("teamCode") or "",
        "city": team.get("teamCity") or "",
        "name": team.get("teamName") or "",
        "score": team.get("score"),
        "wins": team.get("wins"),
        "losses": team.get("losses"),
    }


def normalize_game(game: dict[str, Any], source_id: str) -> dict[str, Any] | None:
    start_utc = parse_utc(game.get("gameTimeUTC") or game.get("gameDateTimeUTC"))
    if start_utc is None:
        return None
    home = team(game.get("homeTeam") or {})
    away = team(game.get("awayTeam") or {})
    return {
        "game_id": str(game.get("gameId") or ""),
        "game_code": game.get("gameCode") or "",
        "scheduled_at_utc": iso(start_utc),
        "scheduled_at_taipei": start_utc.astimezone(TAIPEI).isoformat(),
        "taipei_date": start_utc.astimezone(TAIPEI).date().isoformat(),
        "status_code": game.get("gameStatus"),
        "status_text": game.get("gameStatusText") or "",
        "period": game.get("period"),
        "clock": game.get("gameClock") or "",
        "home": home,
        "away": away,
        "neutral_site": bool(game.get("isNeutral", False)),
        "source_id": source_id,
    }


def games_from_schedule(payload: dict[str, Any]) -> list[dict[str, Any]]:
    dates = (
        payload.get("leagueSchedule", {}).get("gameDates")
        or payload.get("schedule", {}).get("gameDates")
        or []
    )
    games: list[dict[str, Any]] = []
    for date_block in dates:
        for game in date_block.get("games", []):
            normalized = normalize_game(game, "nba_schedule_static")
            if normalized:
                games.append(normalized)
    return games


def games_from_scoreboard(payload: dict[str, Any]) -> list[dict[str, Any]]:
    games: list[dict[str, Any]] = []
    for game in payload.get("scoreboard", {}).get("games", []):
        normalized = normalize_game(game, "nba_live_scoreboard")
        if normalized:
            games.append(normalized)
    return games


def observed_at(result: FetchResult) -> datetime | None:
    if not result.payload:
        return None
    meta_time = result.payload.get("meta", {}).get("time")
    if isinstance(meta_time, str):
        for value in (meta_time, meta_time.replace(" ", "T") + "Z"):
            parsed = parse_utc(value)
            if parsed:
                return parsed
    scoreboard_date = result.payload.get("scoreboard", {}).get("gameDate")
    if isinstance(scoreboard_date, str):
        try:
            return datetime.fromisoformat(scoreboard_date).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return result.fetched_at


def source_status(result: FetchResult) -> dict[str, Any]:
    observed = observed_at(result)
    age_hours = None
    stale = True
    if observed:
        age_hours = max(0.0, (result.fetched_at - observed).total_seconds() / 3600)
        stale = age_hours > 36
    return {
        "source_id": result.source_id,
        "url": result.url,
        "status": "error" if result.error else ("stale" if stale else "ok"),
        "observed_at": iso(observed) if observed else None,
        "fetched_at": iso(result.fetched_at),
        "data_age_hours": round(age_hours, 2) if age_hours is not None else None,
        "stale": stale,
        "raw_hash": result.raw_hash,
        "adapter_version": "nba-free-data-v1",
        "error": result.error,
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    now = datetime.now(timezone.utc)
    results = [fetch_json(source_id, url) for source_id, url, _ in SOURCES]

    all_games: list[dict[str, Any]] = []
    active_source = None
    for result in results:
        if not result.payload:
            continue
        parsed = (
            games_from_schedule(result.payload)
            if result.source_id == "nba_schedule_static"
            else games_from_scoreboard(result.payload)
        )
        if parsed:
            all_games = parsed
            active_source = result.source_id
            break

    start_local = now.astimezone(TAIPEI).date()
    end_local = start_local + timedelta(days=3)
    selected = [
        game
        for game in all_games
        if start_local.isoformat() <= game["taipei_date"] <= end_local.isoformat()
    ]
    selected.sort(key=lambda game: game["scheduled_at_utc"])

    statuses = [source_status(result) for result in results]
    usable = any(status["status"] == "ok" for status in statuses)

    write_json(
        OUT_DIR / "games.json",
        {
            "meta": {
                "generated_at": iso(now),
                "timezone": "Asia/Taipei",
                "window_start": start_local.isoformat(),
                "window_end": end_local.isoformat(),
                "active_source": active_source,
                "game_count": len(selected),
                "data_mode": "free_public_sources",
            },
            "games": selected,
        },
    )
    write_json(
        OUT_DIR / "source-status.json",
        {
            "meta": {
                "generated_at": iso(now),
                "overall_status": "ok" if usable else "degraded",
                "formal_model_publishable": False,
                "reason": "Schedule/status layer only; injuries, market consensus and model calibration are not yet connected.",
            },
            "sources": statuses,
        },
    )
    write_json(
        OUT_DIR / "update-meta.json",
        {
            "generated_at": iso(now),
            "collector_version": "4.4.0",
            "python": sys.version.split()[0],
            "game_count": len(selected),
            "active_source": active_source,
        },
    )

    print(f"Generated {len(selected)} games; active source: {active_source or 'none'}")
    for status in statuses:
        print(status["source_id"], status["status"], status.get("error") or "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
