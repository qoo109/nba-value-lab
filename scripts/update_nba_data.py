#!/usr/bin/env python3
"""Build lightweight point-in-time NBA schedule and source-health snapshots.

The collector uses only Python's standard library and no API key. Source order:
1. NBA static schedule feed (official, preferred when reachable)
2. ESPN public scoreboard JSON (free schedule fallback; research use)
3. NBA Live Data S3 scoreboard (official same-day status fallback)

Every output records source, fetch time, hash, adapter version and stale state.
"""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "current"
TAIPEI = ZoneInfo("Asia/Taipei")
USER_AGENT = "NBA-Value-Lab/4.4 (+https://github.com/qoo109/nba-value-lab)"
ADAPTER_VERSION = "nba-free-data-v2"

NBA_SCHEDULE_URL = "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json"
NBA_LIVE_S3_URL = "https://nba-prod-us-east-1-mediaops-stats.s3.amazonaws.com/NBA/liveData/scoreboard/todaysScoreboard_00.json"
ESPN_URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard?dates={day}"


@dataclass
class FetchResult:
    source_id: str
    url: str
    payload: dict[str, Any] | None
    fetched_at: datetime
    raw_hash: str | None
    error: str | None
    observed_at: datetime | None = None
    notes: str | None = None


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    candidates = [value]
    if " " in value and "T" not in value:
        candidates.append(value.replace(" ", "T") + ("Z" if not value.endswith("Z") else ""))
    for candidate in candidates:
        try:
            parsed = datetime.fromisoformat(candidate.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            continue
    return None


def request_json(url: str, referer: str) -> tuple[dict[str, Any], bytes]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json,text/plain,*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": referer,
            "Cache-Control": "no-cache",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read()
    return json.loads(raw.decode("utf-8")), raw


def fetch_json(source_id: str, url: str, referer: str, notes: str | None = None) -> FetchResult:
    fetched_at = datetime.now(timezone.utc)
    try:
        payload, raw = request_json(url, referer)
        meta_time = payload.get("meta", {}).get("time") if isinstance(payload, dict) else None
        observed = parse_utc(meta_time) if isinstance(meta_time, str) else fetched_at
        return FetchResult(
            source_id=source_id,
            url=url,
            payload=payload,
            fetched_at=fetched_at,
            raw_hash=hashlib.sha256(raw).hexdigest(),
            error=None,
            observed_at=observed,
            notes=notes,
        )
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return FetchResult(
            source_id=source_id,
            url=url,
            payload=None,
            fetched_at=fetched_at,
            raw_hash=None,
            error=f"{type(exc).__name__}: {exc}",
            observed_at=None,
            notes=notes,
        )


def fetch_espn_range(start_day: date, end_day: date) -> FetchResult:
    fetched_at = datetime.now(timezone.utc)
    events: list[dict[str, Any]] = []
    hashes: list[str] = []
    errors: list[str] = []
    day = start_day
    while day <= end_day:
        url = ESPN_URL.format(day=day.strftime("%Y%m%d"))
        try:
            payload, raw = request_json(url, "https://www.espn.com/nba/")
            events.extend(payload.get("events", []))
            hashes.append(hashlib.sha256(raw).hexdigest())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
            errors.append(f"{day.isoformat()}: {type(exc).__name__}: {exc}")
        day += timedelta(days=1)

    if not events and errors:
        return FetchResult(
            source_id="espn_scoreboard_range",
            url=ESPN_URL.format(day="YYYYMMDD"),
            payload=None,
            fetched_at=fetched_at,
            raw_hash=None,
            error=" | ".join(errors),
            observed_at=None,
            notes="Free public JSON fallback; terms and schema must be monitored.",
        )

    combined_hash = hashlib.sha256("".join(hashes).encode("utf-8")).hexdigest() if hashes else None
    return FetchResult(
        source_id="espn_scoreboard_range",
        url=ESPN_URL.format(day="YYYYMMDD"),
        payload={"events": events, "partial_errors": errors},
        fetched_at=fetched_at,
        raw_hash=combined_hash,
        error=None if events else "No events returned",
        observed_at=fetched_at,
        notes="Free public JSON fallback; terms and schema must be monitored.",
    )


def nba_team(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "team_id": str(raw.get("teamId") or ""),
        "tricode": raw.get("teamTricode") or raw.get("teamCode") or "",
        "city": raw.get("teamCity") or "",
        "name": raw.get("teamName") or "",
        "score": raw.get("score"),
        "wins": raw.get("wins"),
        "losses": raw.get("losses"),
    }


def normalize_nba_game(game: dict[str, Any], source_id: str) -> dict[str, Any] | None:
    start_utc = parse_utc(game.get("gameTimeUTC") or game.get("gameDateTimeUTC"))
    if start_utc is None:
        return None
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
        "home": nba_team(game.get("homeTeam") or {}),
        "away": nba_team(game.get("awayTeam") or {}),
        "neutral_site": bool(game.get("isNeutral", False)),
        "source_id": source_id,
    }


def games_from_nba_schedule(payload: dict[str, Any]) -> list[dict[str, Any]]:
    dates = payload.get("leagueSchedule", {}).get("gameDates") or payload.get("schedule", {}).get("gameDates") or []
    games: list[dict[str, Any]] = []
    for date_block in dates:
        for game in date_block.get("games", []):
            normalized = normalize_nba_game(game, "nba_schedule_static")
            if normalized:
                games.append(normalized)
    return games


def games_from_nba_scoreboard(payload: dict[str, Any]) -> list[dict[str, Any]]:
    games: list[dict[str, Any]] = []
    for game in payload.get("scoreboard", {}).get("games", []):
        normalized = normalize_nba_game(game, "nba_live_scoreboard_s3")
        if normalized:
            games.append(normalized)
    return games


def espn_team(raw: dict[str, Any]) -> dict[str, Any]:
    team_data = raw.get("team", {})
    records = raw.get("records") or []
    record = records[0].get("summary") if records else None
    score: int | str | None = raw.get("score")
    if isinstance(score, str) and score.isdigit():
        score = int(score)
    wins = losses = None
    if isinstance(record, str) and "-" in record:
        parts = record.split("-")
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            wins, losses = int(parts[0]), int(parts[1])
    return {
        "team_id": str(team_data.get("id") or ""),
        "tricode": team_data.get("abbreviation") or "",
        "city": team_data.get("location") or "",
        "name": team_data.get("name") or team_data.get("shortDisplayName") or "",
        "score": score,
        "wins": wins,
        "losses": losses,
    }


def games_from_espn(payload: dict[str, Any]) -> list[dict[str, Any]]:
    games: list[dict[str, Any]] = []
    for event in payload.get("events", []):
        start_utc = parse_utc(event.get("date"))
        competitions = event.get("competitions") or []
        if start_utc is None or not competitions:
            continue
        competition = competitions[0]
        competitors = competition.get("competitors") or []
        home_raw = next((item for item in competitors if item.get("homeAway") == "home"), {})
        away_raw = next((item for item in competitors if item.get("homeAway") == "away"), {})
        status_type = event.get("status", {}).get("type", {})
        games.append(
            {
                "game_id": str(event.get("id") or competition.get("id") or ""),
                "game_code": event.get("shortName") or event.get("name") or "",
                "scheduled_at_utc": iso(start_utc),
                "scheduled_at_taipei": start_utc.astimezone(TAIPEI).isoformat(),
                "taipei_date": start_utc.astimezone(TAIPEI).date().isoformat(),
                "status_code": status_type.get("id"),
                "status_text": status_type.get("description") or status_type.get("detail") or "",
                "period": event.get("status", {}).get("period"),
                "clock": event.get("status", {}).get("displayClock") or "",
                "home": espn_team(home_raw),
                "away": espn_team(away_raw),
                "neutral_site": bool(competition.get("neutralSite", False)),
                "source_id": "espn_scoreboard_range",
            }
        )
    return games


def source_status(result: FetchResult) -> dict[str, Any]:
    observed = result.observed_at
    age_hours = None
    stale = True
    if observed:
        age_hours = max(0.0, (result.fetched_at - observed).total_seconds() / 3600)
        stale = age_hours > 36
    if result.error and not result.payload:
        status = "error"
    elif stale:
        status = "stale"
    else:
        status = "ok"
    return {
        "source_id": result.source_id,
        "url": result.url,
        "status": status,
        "observed_at": iso(observed) if observed else None,
        "fetched_at": iso(result.fetched_at),
        "data_age_hours": round(age_hours, 2) if age_hours is not None else None,
        "stale": stale,
        "raw_hash": result.raw_hash,
        "adapter_version": ADAPTER_VERSION,
        "notes": result.notes,
        "error": result.error,
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def dedupe_games(games: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    output: list[dict[str, Any]] = []
    for game in sorted(games, key=lambda item: item["scheduled_at_utc"]):
        key = (game["game_id"], game["scheduled_at_utc"])
        if key in seen:
            continue
        seen.add(key)
        output.append(game)
    return output


def main() -> int:
    now = datetime.now(timezone.utc)
    start_local = now.astimezone(TAIPEI).date()
    end_local = start_local + timedelta(days=3)

    nba_schedule = fetch_json(
        "nba_schedule_static",
        NBA_SCHEDULE_URL,
        "https://www.nba.com/schedule",
        "Official preferred schedule feed; GitHub-hosted runners may be blocked.",
    )
    espn_range = fetch_espn_range(start_local - timedelta(days=1), end_local)
    nba_live = fetch_json(
        "nba_live_scoreboard_s3",
        NBA_LIVE_S3_URL,
        "https://www.nba.com/",
        "Official same-day status fallback; may be stale during offseason.",
    )
    results = [nba_schedule, espn_range, nba_live]

    candidates: list[tuple[str, list[dict[str, Any]]]] = []
    if nba_schedule.payload:
        candidates.append(("nba_schedule_static", games_from_nba_schedule(nba_schedule.payload)))
    if espn_range.payload:
        candidates.append(("espn_scoreboard_range", games_from_espn(espn_range.payload)))
    if nba_live.payload:
        candidates.append(("nba_live_scoreboard_s3", games_from_nba_scoreboard(nba_live.payload)))

    selected: list[dict[str, Any]] = []
    active_source = None
    for source_id, games in candidates:
        in_window = [
            game
            for game in games
            if start_local.isoformat() <= game["taipei_date"] <= end_local.isoformat()
        ]
        if in_window:
            selected = dedupe_games(in_window)
            active_source = source_id
            break

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
                "formal_model_publishable": False,
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
            "collector_version": "4.4.1",
            "adapter_version": ADAPTER_VERSION,
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
