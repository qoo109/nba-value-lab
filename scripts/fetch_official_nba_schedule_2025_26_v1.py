#!/usr/bin/env python3
"""Fetch and normalize official NBA 2025-26 schedule metadata.

The preferred source is the official structured schedule. When that route is
blocked, the script falls back to the official NBA Communications day-by-day
schedule-release PDF. The PDF supplies published matchup, orientation and ET
start time, but not NBA game IDs and not later NBA Cup determined games.

No odds or user-provided archive rows are sent by this script.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

SEASON = "2025-26"
REGULAR_GAME_ID_PREFIX = "00225"
STRUCTURED_CANDIDATES = (
    "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json",
    "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json",
    "https://stats.nba.com/stats/scheduleleaguev2?LeagueID=00&Season=2025-26",
)
OFFICIAL_RELEASE_PDF = "https://bit.ly/414Bl2J"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://pr.nba.com/2025-26-nba-regular-season-schedule/",
    "Accept": "application/json, application/pdf, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "close",
}
TEAM_NAME_MAP = {
    "Atlanta": "Atlanta Hawks",
    "Boston": "Boston Celtics",
    "Brooklyn": "Brooklyn Nets",
    "Charlotte": "Charlotte Hornets",
    "Chicago": "Chicago Bulls",
    "Cleveland": "Cleveland Cavaliers",
    "Dallas": "Dallas Mavericks",
    "Denver": "Denver Nuggets",
    "Detroit": "Detroit Pistons",
    "Golden State": "Golden State Warriors",
    "Houston": "Houston Rockets",
    "Indiana": "Indiana Pacers",
    "LA Clippers": "Los Angeles Clippers",
    "L.A. Lakers": "Los Angeles Lakers",
    "Memphis": "Memphis Grizzlies",
    "Miami": "Miami Heat",
    "Milwaukee": "Milwaukee Bucks",
    "Minnesota": "Minnesota Timberwolves",
    "New Orleans": "New Orleans Pelicans",
    "New York": "New York Knicks",
    "Oklahoma City": "Oklahoma City Thunder",
    "Orlando": "Orlando Magic",
    "Philadelphia": "Philadelphia 76ers",
    "Phoenix": "Phoenix Suns",
    "Portland": "Portland Trail Blazers",
    "Sacramento": "Sacramento Kings",
    "San Antonio": "San Antonio Spurs",
    "Toronto": "Toronto Raptors",
    "Utah": "Utah Jazz",
    "Washington": "Washington Wizards",
}
DAY_PATTERN = r"(?:Mon\.|Tue\.|Wed\.|Thu\.|Fri\.|Sat\.|Sun\.)"
DATE_PATTERN = r"\d{1,2}/\d{1,2}/\d{2}"
TIME_PATTERN = r"\d{1,2}:\d{2}\s+[AP]M"
SCHEDULE_LINE = re.compile(
    rf"^(?P<day>{DAY_PATTERN})\s+(?P<date>{DATE_PATTERN})\s+"
    rf"(?P<team1>.+?)\s+(?P<relation>at|vs)\s+(?P<team2>.+?)\s+"
    rf"(?P<local>{TIME_PATTERN})\s+(?P<et>{TIME_PATTERN})(?:\s+.*)?$"
)
ET_ZONE = ZoneInfo("America/New_York")


class ScheduleFetchError(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def stable_key(*values: str) -> str:
    payload = "|".join(values).encode("utf-8")
    return "nba-published-" + hashlib.sha256(payload).hexdigest()[:20]


def fetch_bytes(url: str, timeout: int) -> bytes:
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def fetch_json(url: str, timeout: int) -> tuple[dict[str, Any], bytes]:
    raw = fetch_bytes(url, timeout)
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


def normalize_structured_game(item: dict[str, Any]) -> dict[str, Any] | None:
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
        "official_schedule_row_id": stable_key(game_id),
        "official_game_id": game_id,
        "schedule_source_type": "official_structured_schedule",
        "schedule_version_date": None,
        "schedule_subject_to_change": False,
        "venue_relation": "at",
        "official_team1": away_name,
        "official_team2": home_name,
        "official_away_team": away_name,
        "official_home_team": home_name,
        "scheduled_tipoff_et": None,
        "scheduled_tipoff_utc": tipoff.strip(),
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


def extract_structured_games(payload: dict[str, Any]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for item in iter_dicts(payload):
        game = normalize_structured_game(item)
        if game:
            by_id[str(game["official_game_id"])] = game
    return sorted(by_id.values(), key=lambda row: (str(row["scheduled_tipoff_utc"]), str(row["official_game_id"])))


def parse_release_pdf(raw: bytes) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ScheduleFetchError("pypdf is required for official PDF fallback") from exc
    reader = PdfReader(io.BytesIO(raw))
    text_lines: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        text_lines.extend(text.splitlines())
    normalized_lines = [re.sub(r"\s+", " ", line).strip() for line in text_lines if line.strip()]
    games: list[dict[str, Any]] = []
    rejected_schedule_like: list[str] = []
    for line in normalized_lines:
        match = SCHEDULE_LINE.match(line)
        if not match:
            if re.match(rf"^{DAY_PATTERN}\s+{DATE_PATTERN}\s+", line):
                rejected_schedule_like.append(line[:300])
            continue
        short1 = match.group("team1").strip()
        short2 = match.group("team2").strip()
        if short1 not in TEAM_NAME_MAP or short2 not in TEAM_NAME_MAP:
            rejected_schedule_like.append(line[:300])
            continue
        date_text = match.group("date")
        et_text = match.group("et")
        scheduled_et = datetime.strptime(f"{date_text} {et_text}", "%m/%d/%y %I:%M %p").replace(tzinfo=ET_ZONE)
        scheduled_utc = scheduled_et.astimezone(timezone.utc)
        team1 = TEAM_NAME_MAP[short1]
        team2 = TEAM_NAME_MAP[short2]
        relation = match.group("relation")
        row_key = stable_key(date_text, team1, relation, team2, et_text)
        games.append({
            "official_schedule_row_id": row_key,
            "official_game_id": None,
            "schedule_source_type": "official_schedule_release_pdf",
            "schedule_version_date": "2025-08-14",
            "schedule_subject_to_change": True,
            "venue_relation": relation,
            "official_team1": team1,
            "official_team2": team2,
            "official_away_team": team1 if relation == "at" else None,
            "official_home_team": team2 if relation == "at" else None,
            "scheduled_tipoff_et": scheduled_et.isoformat(),
            "scheduled_tipoff_utc": scheduled_utc.isoformat().replace("+00:00", "Z"),
            "published_local_time": match.group("local"),
            "published_et_time": et_text,
            "game_status": None,
            "game_status_text": None,
            "game_label": "NBA regular-season schedule release",
            "game_sub_label": "neutral-site" if relation == "vs" else None,
            "week_name": None,
            "arena_name": None,
            "arena_city": None,
            "arena_state": None,
            "postponed_status": None,
        })
    deduped = {str(game["official_schedule_row_id"]): game for game in games}
    games = sorted(deduped.values(), key=lambda row: (str(row["scheduled_tipoff_utc"]), str(row["official_schedule_row_id"])))
    team_appearances = Counter()
    for game in games:
        team_appearances[str(game["official_team1"])] += 1
        team_appearances[str(game["official_team2"])] += 1
    diagnostics = {
        "pdf_page_count": len(reader.pages),
        "extracted_nonempty_line_count": len(normalized_lines),
        "published_games_normalized": len(games),
        "neutral_site_games": sum(game["venue_relation"] == "vs" for game in games),
        "team_appearance_min": min(team_appearances.values()) if team_appearances else 0,
        "team_appearance_max": max(team_appearances.values()) if team_appearances else 0,
        "team_appearance_counts": dict(sorted(team_appearances.items())),
        "rejected_schedule_like_count": len(rejected_schedule_like),
        "rejected_schedule_like_samples": rejected_schedule_like[:20],
    }
    return games, diagnostics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)

    attempts: list[dict[str, Any]] = []
    selected_url: str | None = None
    selected_raw: bytes | None = None
    selected_type: str | None = None
    source_diagnostics: dict[str, Any] = {}
    games: list[dict[str, Any]] = []

    for url in STRUCTURED_CANDIDATES:
        try:
            payload, raw = fetch_json(url, args.timeout)
            ids = raw_game_ids(payload)
            prefixes = Counter(value[:5] for value in ids if len(value) >= 5)
            candidate_games = extract_structured_games(payload)
            attempts.append({
                "url": url,
                "source_type": "official_structured_schedule",
                "success": True,
                "root_keys": sorted(payload.keys()),
                "raw_unique_game_ids": len(ids),
                "sample_game_ids": ids[:5],
                "game_id_prefix_counts": dict(prefixes.most_common()),
                "regular_season_games_normalized": len(candidate_games),
                "payload_sha256": sha256_bytes(raw),
            })
            if len(candidate_games) >= 1200:
                selected_url = url
                selected_raw = raw
                selected_type = "official_structured_schedule"
                games = candidate_games
                break
        except Exception as exc:
            attempts.append({
                "url": url,
                "source_type": "official_structured_schedule",
                "success": False,
                "error_type": type(exc).__name__,
                "error": str(exc)[:500],
            })

    if not games:
        try:
            raw = fetch_bytes(OFFICIAL_RELEASE_PDF, args.timeout)
            candidate_games, diagnostics = parse_release_pdf(raw)
            pdf_valid = (
                len(candidate_games) == 1200
                and diagnostics["team_appearance_min"] == 80
                and diagnostics["team_appearance_max"] == 80
                and diagnostics["rejected_schedule_like_count"] == 0
            )
            attempts.append({
                "url": OFFICIAL_RELEASE_PDF,
                "source_type": "official_schedule_release_pdf",
                "success": True,
                "payload_sha256": sha256_bytes(raw),
                **diagnostics,
                "source_valid": pdf_valid,
            })
            if pdf_valid:
                selected_url = OFFICIAL_RELEASE_PDF
                selected_raw = raw
                selected_type = "official_schedule_release_pdf"
                source_diagnostics = diagnostics
                games = candidate_games
        except Exception as exc:
            attempts.append({
                "url": OFFICIAL_RELEASE_PDF,
                "source_type": "official_schedule_release_pdf",
                "success": False,
                "error_type": type(exc).__name__,
                "error": str(exc)[:500],
            })

    valid = bool(games and selected_url and selected_raw and selected_type)
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
        "source_type": selected_type,
        "source_payload_sha256": sha256_bytes(selected_raw) if selected_raw else None,
        "source_attempts": attempts,
        "source_diagnostics": source_diagnostics,
        "published_schedule_game_count": len(games),
        "structured_game_ids_present": sum(bool(game.get("official_game_id")) for game in games),
        "schedule_release_omits_cup_determined_games": selected_type == "official_schedule_release_pdf",
        "games": games,
    }
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "formal_state": output["formal_state"],
        "source_url": selected_url,
        "source_type": selected_type,
        "published_schedule_game_count": len(games),
        "structured_game_ids_present": output["structured_game_ids_present"],
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
