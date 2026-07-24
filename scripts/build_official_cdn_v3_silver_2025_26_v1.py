#!/usr/bin/env python3
"""Build governed 2025-26 Silver from archived official NBA-derived sources.

Source composition:
- matchups_2025: stable home/away team identity
- cdnnba_2025: possession identity, score progression, action statistics,
  and event actual timestamps
- nbastatsv3_2025: normalized event/player identity and independent score/team QA

The builder is fail-closed. All three sources must cover the same 1,230 games,
team identity and terminal scores must agree, and every game must produce two
team feature rows. Raw archives stay in temporary storage and are not emitted.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import shutil
import sqlite3
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from itertools import groupby
from pathlib import Path
from typing import Any, Iterable, Iterator
from zoneinfo import ZoneInfo

import recover_historical_silver_two_game_official_cdn_pbp_v1 as cdn_parser
from historical_phase2_core import download, extract
from historical_silver_nbastats import insert_player_aliases
from historical_silver_schema import create_schema, gzip_file, stable_id
from player_identity_core import normalize_player_name, suffixless_player_name

SEASON_LABEL = "2025-26"
SOURCE_ID_CDN = "cdnnba_2025_official_v1"
SOURCE_ID_V3 = "nbastatsv3_2025_official_v1"
SOURCE_ID_MATCHUPS = "matchups_2025_official_identity_v1"
QUALITY_FLAG = "official_cdn_v3_2025_26_v1"
FORMAL_PASS = "OFFICIAL_CDN_V3_SILVER_2025_26_BUILD_PASS"
FORMAL_BLOCKED = "OFFICIAL_CDN_V3_SILVER_2025_26_BUILD_BLOCKED"

SOURCES = {
    "cdnnba_2025": "https://github.com/shufinskiy/nba_data/raw/main/datasets/cdnnba_2025.tar.xz",
    "nbastatsv3_2025": "https://github.com/shufinskiy/nba_data/raw/main/datasets/nbastatsv3_2025.tar.xz",
    "matchups_2025": "https://github.com/shufinskiy/nba_data/raw/main/datasets/matchups_2025.tar.xz",
}

FEATURE_INSERT = "INSERT INTO team_game_features VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
POSSESSION_INSERT = "INSERT INTO possessions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
EVENT_INSERT = "INSERT INTO pbp_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
GAME_INSERT = "INSERT INTO games VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
EASTERN = ZoneInfo("America/New_York")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def canonical_columns(fieldnames: Iterable[str] | None) -> dict[str, str]:
    return {
        str(name).strip().lower().replace("_", ""): str(name)
        for name in (fieldnames or [])
    }


def value(row: dict[str, Any], columns: dict[str, str], *names: str) -> str:
    for name in names:
        actual = columns.get(name.lower().replace("_", ""))
        if actual is None:
            continue
        raw = row.get(actual)
        text = str(raw or "").strip()
        if text.lower() not in {"", "nan", "none", "null"}:
            return text
    return ""


def as_int(raw: Any, default: int = 0) -> int:
    try:
        return int(float(str(raw).strip()))
    except (TypeError, ValueError):
        return default


def normalize_entity_id(raw: Any) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    try:
        return str(int(float(text)))
    except ValueError:
        return text


def normalize_game_id(raw: Any) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    try:
        numeric = str(int(float(text)))
    except ValueError:
        numeric = text
    return numeric.zfill(10) if numeric.isdigit() and len(numeric) <= 10 else numeric


def parse_utc(raw: str) -> datetime:
    text = str(raw or "").strip()
    if not text:
        raise ValueError("missing UTC timestamp")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp is timezone-naive: {raw}")
    return parsed.astimezone(timezone.utc)


def governed_game_date(first_event_utc: datetime) -> str:
    return first_event_utc.astimezone(EASTERN).date().isoformat()


def prepare_source(key: str, url: str, root: Path, max_mb: int) -> tuple[Path, dict[str, Any]]:
    archive = root / f"{key}.tar.xz"
    extracted = root / f"{key}-raw"
    extracted.mkdir()
    info = download(url, archive, max_mb * 1048576)
    info["member_count"] = extract(archive, extracted)
    csv_files = sorted(extracted.rglob("*.csv"))
    preferred = [path for path in csv_files if key.lower() in path.name.lower()]
    if len(preferred) == 1:
        csv_path = preferred[0]
    elif len(csv_files) == 1:
        csv_path = csv_files[0]
    else:
        raise RuntimeError(f"{key}: expected one identifiable CSV, found {[p.name for p in csv_files]}")
    info["csv_name"] = csv_path.name
    info["csv_bytes"] = csv_path.stat().st_size
    return csv_path, info


def load_matchup_identity(csv_path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    games: dict[str, dict[str, Any]] = {}
    row_count = 0
    conflicts = 0
    with csv_path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = canonical_columns(reader.fieldnames)
        required = {"gameid", "hometeamid", "awayteamid", "teamid", "teamtricode"}
        missing = required - set(columns)
        if missing:
            raise RuntimeError(f"matchups archive missing fields: {sorted(missing)}")
        for row in reader:
            row_count += 1
            game_id = normalize_game_id(value(row, columns, "game_id", "gameid"))
            home_id = normalize_entity_id(value(row, columns, "home_team_id", "hometeamid"))
            away_id = normalize_entity_id(value(row, columns, "away_team_id", "awayteamid"))
            team_id = normalize_entity_id(value(row, columns, "team_id", "teamid"))
            tricode = value(row, columns, "team_tricode", "teamtricode").upper()
            if not all((game_id, home_id, away_id)):
                raise RuntimeError("matchups row has incomplete game/home/away identity")
            item = games.setdefault(game_id, {
                "game_id": game_id,
                "home_team_id": home_id,
                "away_team_id": away_id,
                "team_map": {},
                "rows": 0,
            })
            if item["home_team_id"] != home_id or item["away_team_id"] != away_id:
                conflicts += 1
                continue
            item["rows"] += 1
            if team_id and tricode:
                previous = item["team_map"].get(team_id)
                if previous not in {None, tricode}:
                    conflicts += 1
                item["team_map"][team_id] = tricode

    unresolved = []
    for game_id, item in games.items():
        item["home_team_abbr"] = item["team_map"].get(item["home_team_id"])
        item["away_team_abbr"] = item["team_map"].get(item["away_team_id"])
        if not item["home_team_abbr"] or not item["away_team_abbr"]:
            unresolved.append(game_id)
        if item["home_team_abbr"] == item["away_team_abbr"]:
            unresolved.append(game_id)
        item.pop("team_map", None)
    if conflicts or unresolved:
        raise RuntimeError(
            f"matchup identity failed: conflicts={conflicts}, unresolved={unresolved[:10]}"
        )
    return games, {
        "rows": row_count,
        "games": len(games),
        "identity_conflicts": conflicts,
        "unresolved_games": len(unresolved),
    }


def scan_cdn_metadata(
    csv_path: Path,
    identities: dict[str, dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    metadata: dict[str, dict[str, Any]] = {
        game_id: {
            **identity,
            "first_event_utc": None,
            "terminal_order": -1,
            "home_score": None,
            "away_score": None,
            "max_period": 0,
            "cdn_event_count": 0,
            "observed_team_map": {},
        }
        for game_id, identity in identities.items()
    }
    rows = unknown_games = identity_mismatches = 0
    with csv_path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = canonical_columns(reader.fieldnames)
        required = {
            "gameid", "period", "actiontype", "scorehome", "scoreaway",
            "teamid", "teamtricode", "possession", "ordernumber", "timeactual",
        }
        missing = required - set(columns)
        if missing:
            raise RuntimeError(f"CDN archive missing fields: {sorted(missing)}")
        for row in reader:
            rows += 1
            game_id = normalize_game_id(value(row, columns, "gameid"))
            item = metadata.get(game_id)
            if item is None:
                unknown_games += 1
                continue
            item["cdn_event_count"] += 1
            item["max_period"] = max(item["max_period"], as_int(value(row, columns, "period"), 0))
            timestamp = value(row, columns, "timeactual")
            if timestamp:
                parsed = parse_utc(timestamp)
                if item["first_event_utc"] is None or parsed < item["first_event_utc"]:
                    item["first_event_utc"] = parsed
            team_id = normalize_entity_id(value(row, columns, "teamid"))
            tricode = value(row, columns, "teamtricode").upper()
            if team_id and tricode:
                previous = item["observed_team_map"].get(team_id)
                if previous not in {None, tricode}:
                    identity_mismatches += 1
                item["observed_team_map"][team_id] = tricode
            order = as_int(value(row, columns, "ordernumber", "actionnumber"), -1)
            home_raw = value(row, columns, "scorehome")
            away_raw = value(row, columns, "scoreaway")
            if order >= item["terminal_order"] and home_raw and away_raw:
                item["terminal_order"] = order
                item["home_score"] = as_int(home_raw, -1)
                item["away_score"] = as_int(away_raw, -1)

    failures = []
    for game_id, item in metadata.items():
        expected = {
            item["home_team_id"]: item["home_team_abbr"],
            item["away_team_id"]: item["away_team_abbr"],
        }
        for team_id, tricode in expected.items():
            if item["observed_team_map"].get(team_id) != tricode:
                failures.append(f"{game_id}:team:{team_id}")
        if item["first_event_utc"] is None:
            failures.append(f"{game_id}:time")
        if item["home_score"] is None or item["away_score"] is None:
            failures.append(f"{game_id}:score")
        if item["cdn_event_count"] <= 0:
            failures.append(f"{game_id}:events")
        item["game_date"] = governed_game_date(item["first_event_utc"]) if item["first_event_utc"] else None
        item["game_minutes"] = 48.0 + max(item["max_period"] - 4, 0) * 5.0
        item["quality_flags"] = QUALITY_FLAG
        item.pop("observed_team_map", None)
    if unknown_games or identity_mismatches or failures:
        raise RuntimeError(
            "CDN metadata validation failed: "
            f"unknown_games={unknown_games}, identity_mismatches={identity_mismatches}, "
            f"failures={failures[:20]}"
        )
    dates = [item["game_date"] for item in metadata.values()]
    return metadata, {
        "rows": rows,
        "games": len(metadata),
        "unknown_game_rows": unknown_games,
        "identity_mismatches": identity_mismatches,
        "game_date_rule": "earliest_timeActual_UTC_converted_to_America_New_York_date",
        "game_date_min": min(dates),
        "game_date_max": max(dates),
    }


def v3_side(location: str) -> str:
    key = str(location or "").strip().lower()
    if key in {"h", "home"}:
        return "home"
    if key in {"v", "a", "away", "visitor"}:
        return "away"
    return "neutral"


def score_margin(home: int | None, away: int | None) -> str | None:
    if home is None or away is None:
        return None
    value = home - away
    return "TIE" if value == 0 else str(value)


def normalize_v3_events(
    csv_path: Path,
    db: sqlite3.Connection,
    games: dict[str, dict[str, Any]],
    batch_size: int = 5000,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    aliases: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    event_ids: set[str] = set()
    game_stats = defaultdict(lambda: {
        "rows": 0,
        "max_period": 0,
        "terminal_action": -1,
        "home_score": None,
        "away_score": None,
        "team_map": {},
    })
    batch = []
    rows = collisions = unknown_games = identity_mismatches = incomplete_aliases = 0

    with csv_path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = canonical_columns(reader.fieldnames)
        required = {
            "gameid", "actionnumber", "period", "clock", "actiontype",
            "teamid", "teamtricode", "scorehome", "scoreaway",
        }
        missing = required - set(columns)
        if missing:
            raise RuntimeError(f"V3 archive missing fields: {sorted(missing)}")
        for row_number, row in enumerate(reader, start=1):
            rows += 1
            game_id = normalize_game_id(value(row, columns, "gameid"))
            game = games.get(game_id)
            if game is None:
                unknown_games += 1
                continue
            action_number = as_int(value(row, columns, "actionnumber", "actionid"), -1)
            period = as_int(value(row, columns, "period"), 0)
            clock = value(row, columns, "clock") or None
            action_type = value(row, columns, "actiontype")
            subtype = value(row, columns, "subtype")
            description = value(row, columns, "description") or action_type or None
            team_id = normalize_entity_id(value(row, columns, "teamid")) or None
            team_abbr = value(row, columns, "teamtricode").upper() or None
            player_id = normalize_entity_id(value(row, columns, "personid")) or None
            player_name = value(row, columns, "playername") or value(row, columns, "playernamei")
            home_raw = value(row, columns, "scorehome")
            away_raw = value(row, columns, "scoreaway")
            home_score = as_int(home_raw, -1) if home_raw else None
            away_score = as_int(away_raw, -1) if away_raw else None
            location = value(row, columns, "location")
            video_available = as_int(value(row, columns, "videoavailable"), 0)

            event_id = stable_id(SOURCE_ID_V3, game_id, action_number, period, clock, action_type, subtype, player_id, description)
            if event_id in event_ids:
                collisions += 1
                event_id = stable_id(event_id, row_number)
            event_ids.add(event_id)
            batch.append((
                event_id, game_id, action_number if action_number >= 0 else None,
                None, None, period, clock, v3_side(location), description, None,
                away_score, home_score, score_margin(home_score, away_score),
                team_id, team_abbr, player_id, None, None, video_available,
                SOURCE_ID_V3, row_number,
            ))
            if len(batch) >= batch_size:
                db.executemany(EVENT_INSERT, batch)
                batch.clear()

            stats = game_stats[game_id]
            stats["rows"] += 1
            stats["max_period"] = max(stats["max_period"], period)
            if team_id and team_abbr:
                previous = stats["team_map"].get(team_id)
                if previous not in {None, team_abbr}:
                    identity_mismatches += 1
                stats["team_map"][team_id] = team_abbr
            if action_number >= stats["terminal_action"] and home_score is not None and away_score is not None:
                stats["terminal_action"] = action_number
                stats["home_score"] = home_score
                stats["away_score"] = away_score

            if player_id or player_name:
                if not player_id or not player_name:
                    incomplete_aliases += 1
                else:
                    name_key = normalize_player_name(player_name)
                    if name_key:
                        suffix_key = suffixless_player_name(player_name)
                        key = (player_id, name_key, team_abbr or "", team_id or "")
                        item = aliases.setdefault(key, {
                            "player_id": player_id,
                            "player_name_key": name_key,
                            "player_name_key_suffixless": suffix_key,
                            "team_id": team_id,
                            "team_abbr": team_abbr,
                            "raw_names": Counter(),
                            "first_game_id": game_id,
                            "last_game_id": game_id,
                            "event_appearances": 0,
                        })
                        item["raw_names"][player_name] += 1
                        item["last_game_id"] = game_id
                        item["event_appearances"] += 1
    if batch:
        db.executemany(EVENT_INSERT, batch)

    finalized_aliases = []
    for item in aliases.values():
        raw_name = item["raw_names"].most_common(1)[0][0]
        flags = []
        if not item["team_abbr"]:
            flags.append("team_abbr_unavailable")
        if len(item["raw_names"]) > 1:
            flags.append("multiple_raw_name_variants")
        finalized_aliases.append({
            "player_id": item["player_id"],
            "player_name_raw": raw_name,
            "player_name_key": item["player_name_key"],
            "player_name_key_suffixless": item["player_name_key_suffixless"],
            "team_id": item["team_id"],
            "team_abbr": item["team_abbr"],
            "first_game_id": item["first_game_id"],
            "last_game_id": item["last_game_id"],
            "event_appearances": item["event_appearances"],
            "quality_flags": ",".join(flags),
        })

    failures = []
    score_mismatches = 0
    for game_id, game in games.items():
        stats = game_stats.get(game_id)
        if not stats:
            failures.append(f"{game_id}:missing")
            continue
        expected = {
            game["home_team_id"]: game["home_team_abbr"],
            game["away_team_id"]: game["away_team_abbr"],
        }
        for team_id, tricode in expected.items():
            if stats["team_map"].get(team_id) != tricode:
                failures.append(f"{game_id}:team:{team_id}")
        if stats["home_score"] != game["home_score"] or stats["away_score"] != game["away_score"]:
            score_mismatches += 1
            failures.append(f"{game_id}:score")
        if stats["max_period"] != game["max_period"]:
            failures.append(f"{game_id}:period")
        game["v3_event_count"] = stats["rows"]
    if unknown_games or identity_mismatches or failures:
        raise RuntimeError(
            "V3 cross-source validation failed: "
            f"unknown_games={unknown_games}, identity_mismatches={identity_mismatches}, "
            f"score_mismatches={score_mismatches}, failures={failures[:20]}"
        )
    return sorted(finalized_aliases, key=lambda row: (row["player_id"], row["team_abbr"] or "", row["player_name_key"])), {
        "rows": rows,
        "games": len(game_stats),
        "event_id_collisions_resolved": collisions,
        "unknown_game_rows": unknown_games,
        "identity_mismatches": identity_mismatches,
        "terminal_score_mismatches": score_mismatches,
        "player_alias_rows": len(finalized_aliases),
        "unique_player_ids": len({row["player_id"] for row in finalized_aliases}),
        "incomplete_player_identity_rows": incomplete_aliases,
    }


def iter_contiguous_game_groups(csv_path: Path) -> Iterator[tuple[str, list[dict[str, str]]]]:
    seen: set[str] = set()
    with csv_path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = canonical_columns(reader.fieldnames)
        if "gameid" not in columns:
            raise RuntimeError("CDN archive does not expose gameId")

        def key(row: dict[str, str]) -> str:
            return normalize_game_id(value(row, columns, "gameid"))

        for game_id, group in groupby(reader, key=key):
            if game_id in seen:
                raise RuntimeError(f"CDN archive is not contiguous by game ID: {game_id}")
            seen.add(game_id)
            yield game_id, [dict(row) for row in group]


def insert_games(db: sqlite3.Connection, games: dict[str, dict[str, Any]]) -> None:
    rows = []
    for game_id in sorted(games):
        game = games[game_id]
        rows.append((
            game_id, game["game_date"], SEASON_LABEL,
            game["home_team_id"], game["home_team_abbr"],
            game["away_team_id"], game["away_team_abbr"],
            game["home_score"], game["away_score"], game["max_period"],
            game["game_minutes"], game.get("v3_event_count", 0), 0,
            None, game["quality_flags"],
        ))
    db.executemany(GAME_INSERT, rows)


def build_cdn_possessions_and_features(
    csv_path: Path,
    db: sqlite3.Connection,
    games: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    cdn_parser.RECOVERY_SOURCE_ID = SOURCE_ID_CDN
    cdn_parser.RECOVERY_FLAG = QUALITY_FLAG
    processed: set[str] = set()
    total_possessions = total_features = 0
    min_possessions = None
    max_possessions = 0
    diagnostics = []

    for game_id, rows in iter_contiguous_game_groups(csv_path):
        game = games.get(game_id)
        if game is None:
            raise RuntimeError(f"CDN group has unknown game ID: {game_id}")
        feature_rows, possession_rows, diagnostic = cdn_parser.parse_game(game, rows)
        db.executemany(POSSESSION_INSERT, possession_rows)
        db.executemany(FEATURE_INSERT, feature_rows)
        possession_count = len(possession_rows)
        db.execute("UPDATE games SET possession_count=?, score_match=1 WHERE game_id=?", (possession_count, game_id))
        processed.add(game_id)
        total_possessions += possession_count
        total_features += len(feature_rows)
        min_possessions = possession_count if min_possessions is None else min(min_possessions, possession_count)
        max_possessions = max(max_possessions, possession_count)
        if len(diagnostics) < 10:
            diagnostics.append({"game_id": game_id, **diagnostic})

    missing = sorted(set(games) - processed)
    if missing:
        raise RuntimeError(f"CDN possession build missed games: {missing[:20]}")
    if total_features != 2 * len(games):
        raise RuntimeError(f"expected {2 * len(games)} team features, found {total_features}")
    return {
        "games_processed": len(processed),
        "possession_rows": total_possessions,
        "team_game_feature_rows": total_features,
        "minimum_possession_segments_per_game": min_possessions,
        "maximum_possession_segments_per_game": max_possessions,
        "sample_diagnostics": diagnostics,
    }


def write_aggregate_sample(db: sqlite3.Connection, path: Path) -> None:
    payload = {
        "schema_version": "official-cdn-v3-silver-2025-26-sample-v1",
        "raw_rows_included": False,
        "tables": {
            table: int(db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in ("games", "pbp_events", "player_aliases", "possessions", "team_game_features")
        },
        "date_range": {
            "min": db.execute("SELECT MIN(game_date) FROM games").fetchone()[0],
            "max": db.execute("SELECT MAX(game_date) FROM games").fetchone()[0],
        },
        "quality": {
            "games_with_two_team_features": int(db.execute(
                "SELECT COUNT(*) FROM (SELECT game_id FROM team_game_features GROUP BY game_id HAVING COUNT(*)=2)"
            ).fetchone()[0]),
            "games_with_score_match": int(db.execute("SELECT COUNT(*) FROM games WHERE score_match=1").fetchone()[0]),
        },
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def build(output_dir: Path, max_download_mb: int) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    sqlite_path = output_dir / "historical-silver-2025-26.sqlite"
    gzip_path = output_dir / "historical-silver-2025-26.sqlite.gz"
    if sqlite_path.exists():
        sqlite_path.unlink()

    with tempfile.TemporaryDirectory(prefix="nbavl-official-cdn-v3-silver-") as temp_name:
        temp = Path(temp_name)
        prepared = {
            key: prepare_source(key, url, temp, max_download_mb)
            for key, url in SOURCES.items()
        }
        cdn_csv, cdn_source = prepared["cdnnba_2025"]
        v3_csv, v3_source = prepared["nbastatsv3_2025"]
        matchup_csv, matchup_source = prepared["matchups_2025"]

        identities, matchup_report = load_matchup_identity(matchup_csv)
        if len(identities) != 1230:
            raise RuntimeError(f"expected 1,230 matchup identities, found {len(identities)}")
        games, cdn_report = scan_cdn_metadata(cdn_csv, identities)
        if cdn_report["game_date_min"] != "2025-10-21" or cdn_report["game_date_max"] != "2026-04-12":
            raise RuntimeError(f"unexpected governed game-date range: {cdn_report}")

        db = sqlite3.connect(sqlite_path)
        create_schema(db)
        aliases, v3_report = normalize_v3_events(v3_csv, db, games)
        alias_count = insert_player_aliases(db, aliases, SEASON_LABEL, SOURCE_ID_V3)
        insert_games(db, games)
        feature_report = build_cdn_possessions_and_features(cdn_csv, db, games)

        metadata = {
            "pipeline_name": "NBA Value Lab official CDN + Stats V3 Silver 2025-26",
            "schema_version": "1.0.0",
            "season_label": SEASON_LABEL,
            "rating_points_source": "official_cdn_and_stats_v3_terminal_score_cross_match",
            "possession_points_usage": "qa_only",
            "game_date_rule": "earliest_timeActual_UTC_converted_to_America_New_York_date",
            "same_day_history_policy": "excluded_by_downstream_gold",
            "cdnnba_archive_sha256": cdn_source["sha256"],
            "nbastatsv3_archive_sha256": v3_source["sha256"],
            "matchups_archive_sha256": matchup_source["sha256"],
            "raw_archives_committed": "false",
            "raw_rows_emitted": "false",
        }
        db.executemany("INSERT INTO metadata VALUES (?,?)", metadata.items())
        db.commit()

        table_counts = {
            table: int(db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in ("games", "pbp_events", "player_aliases", "possessions", "team_game_features")
        }
        games_with_two_features = int(db.execute(
            "SELECT COUNT(*) FROM (SELECT game_id FROM team_game_features GROUP BY game_id HAVING COUNT(*)=2)"
        ).fetchone()[0])
        duplicate_features = table_counts["team_game_features"] - int(db.execute(
            "SELECT COUNT(*) FROM (SELECT DISTINCT game_id, team_abbr FROM team_game_features)"
        ).fetchone()[0])
        finite_failures = int(db.execute(
            """
            SELECT COUNT(*) FROM team_game_features
            WHERE pace IS NULL OR off_rtg IS NULL OR def_rtg IS NULL OR net_rtg IS NULL
               OR efg_pct IS NULL OR tov_pct_estimated IS NULL
               OR orb_pct_fg_miss_estimate IS NULL OR free_throw_rate IS NULL
            """
        ).fetchone()[0])
        score_match_games = int(db.execute("SELECT COUNT(*) FROM games WHERE score_match=1").fetchone()[0])
        write_aggregate_sample(db, output_dir / "silver-2025-26-aggregate-sample.json")
        db.execute("VACUUM")
        db.close()

    gzip_file(sqlite_path, gzip_path)
    sqlite_path.unlink()

    blockers = []
    if table_counts["games"] != 1230:
        blockers.append("GAME_COUNT_NOT_1230")
    if table_counts["team_game_features"] != 2460 or games_with_two_features != 1230:
        blockers.append("TEAM_FEATURE_COVERAGE_INCOMPLETE")
    if score_match_games != 1230:
        blockers.append("TERMINAL_SCORE_MATCH_INCOMPLETE")
    if duplicate_features != 0:
        blockers.append("DUPLICATE_TEAM_FEATURE_KEYS")
    if finite_failures != 0:
        blockers.append("NONFINITE_OR_NULL_CORE_TEAM_FEATURES")
    if alias_count < 300:
        blockers.append("PLAYER_ALIAS_COVERAGE_TOO_LOW")

    formal_state = FORMAL_PASS if not blockers else FORMAL_BLOCKED
    report = {
        "schema_version": "official-cdn-v3-silver-2025-26-build-v1",
        "formal_state": formal_state,
        "generated_at_utc": utc_now(),
        "season_label": SEASON_LABEL,
        "sources": {
            "cdnnba_2025": {**cdn_source, **cdn_report},
            "nbastatsv3_2025": {**v3_source, **v3_report},
            "matchups_2025": {**matchup_source, **matchup_report},
        },
        "outputs": {
            "database_gzip_bytes": gzip_path.stat().st_size,
            "tables": table_counts,
            "games_with_two_team_features": games_with_two_features,
            "games_with_terminal_score_cross_match": score_match_games,
        },
        "quality": {
            "all_three_source_game_ids_match": True,
            "all_three_source_game_count": 1230,
            "team_identity_cross_source_mismatches": 0,
            "terminal_score_cross_source_mismatches": 0,
            "game_date_rule": cdn_report["game_date_rule"],
            "game_date_min": cdn_report["game_date_min"],
            "game_date_max": cdn_report["game_date_max"],
            "duplicate_team_feature_keys": duplicate_features,
            "core_feature_null_or_nonfinite_rows": finite_failures,
            "player_alias_count": alias_count,
            **feature_report,
        },
        "execution": {
            "provider_api_requests": 0,
            "raw_archives_committed": False,
            "raw_rows_emitted": 0,
            "model_retraining_executed": False,
            "model_scoring_executed": False,
            "odds_join_executed": False,
        },
        "blockers": blockers,
        "decision": {
            "ready_for_continuous_2024_25_to_2025_26_gold": not blockers,
            "ready_for_frozen_model_scoring": False,
            "market_backtest_allowed": False,
            "clv_allowed": False,
            "roi_allowed": False,
            "betting_edge_claim_allowed": False,
            "formal_stake": 0,
        },
        "next_unique_sub_mainline": (
            "BUILD_CONTINUOUS_2024_25_TO_2025_26_GOLD_AND_SCORE_FROZEN_MODEL"
            if not blockers else "REPAIR_OFFICIAL_CDN_V3_SILVER_2025_26_BLOCKERS"
        ),
    }
    (output_dir / "official-cdn-v3-silver-2025-26-build-report-v1.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def self_test(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    checks = {
        "game_id_padding": normalize_game_id("225000001.0") == "0225000001",
        "entity_id_normalization": normalize_entity_id("1610612737.0") == "1610612737",
        "eastern_date": governed_game_date(parse_utc("2026-04-13T03:05:51Z")) == "2026-04-12",
        "side_home": v3_side("h") == "home",
        "side_away": v3_side("v") == "away",
        "side_neutral": v3_side("") == "neutral",
    }
    if not all(checks.values()):
        raise AssertionError(checks)
    (output_dir / "self-test.json").write_text(json.dumps({"passed": True, "checks": checks}, indent=2) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-download-mb", type=int, default=600)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("official CDN/V3 Silver self-test passed")
        return 0
    report = build(args.output_dir, args.max_download_mb)
    return 0 if report["formal_state"] == FORMAL_PASS else 2


if __name__ == "__main__":
    raise SystemExit(main())
