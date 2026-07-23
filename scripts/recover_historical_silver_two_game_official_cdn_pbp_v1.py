#!/usr/bin/env python3
"""Recover the two 2023-24 PBP Stats gaps from official CDN NBA play-by-play.

The recovery is fail-closed. It rebuilds all five historical Silver seasons in
working storage, identifies the two 2023-24 games that have no team feature rows,
derives replacement possession/team features from the archived official
``cdn.nba.com`` play-by-play source, rebuilds the multi-season Silver and Gold
artifacts, and emits an aggregate receipt. No repository database is modified.
"""
from __future__ import annotations

import argparse
import copy
import csv
import gzip
import json
import math
import shutil
import sqlite3
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import build_historical_gold_multiseason as gold_builder
import combine_historical_silver as silver_combiner
import historical_silver_runner as silver_builder
from historical_phase2_core import download, extract
from historical_silver_schema import gzip_file, safe_div, stable_id

YEARS = (2019, 2020, 2021, 2022, 2023)
LABELS = ("2019-20", "2020-21", "2021-22", "2022-23", "2023-24")
CDN_URL = "https://github.com/shufinskiy/nba_data/raw/main/datasets/cdnnba_2023.tar.xz"
RECOVERY_SOURCE_ID = "cdnnba_2023_official_recovery_v1"
RECOVERY_FLAG = "official_cdnnba_recovery_v1"
FORMAL_PASS = "HISTORICAL_SILVER_2023_24_TWO_GAME_OFFICIAL_CDN_PBP_RECOVERY_PASS"
FORMAL_BLOCKED = "HISTORICAL_SILVER_2023_24_TWO_GAME_OFFICIAL_CDN_PBP_RECOVERY_BLOCKED"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def season_label(year: int) -> str:
    return f"{year}-{str(year + 1)[-2:]}"


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def canonical_columns(fieldnames: Iterable[str] | None) -> dict[str, str]:
    return {str(name).strip().lower(): str(name) for name in (fieldnames or [])}


def value(row: dict[str, Any], columns: dict[str, str], *names: str) -> str:
    for name in names:
        actual = columns.get(name.lower())
        if actual is None:
            continue
        raw = row.get(actual)
        if raw is not None and str(raw).strip() not in {"", "nan", "None", "null"}:
            return str(raw).strip()
    return ""


def as_int(raw: Any, default: int = 0) -> int:
    try:
        return int(float(str(raw).strip()))
    except (TypeError, ValueError):
        return default


def normalize_id(raw: Any) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    try:
        return str(int(float(text)))
    except ValueError:
        return text


def truthy(raw: Any) -> bool:
    return str(raw or "").strip().lower() in {"1", "true", "t", "yes", "y"}


def clock_seconds(raw: str) -> float:
    text = (raw or "").strip().upper().replace("PT", "").replace("S", "")
    if "M" in text:
        minute, second = text.split("M", 1)
        try:
            return float(minute) * 60 + float(second)
        except ValueError:
            return 0.0
    if ":" in text:
        minute, second = text.split(":", 1)
        try:
            return float(minute) * 60 + float(second)
        except ValueError:
            return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def sort_key(row: dict[str, Any], columns: dict[str, str]) -> tuple[int, int, int]:
    period = as_int(value(row, columns, "period"))
    order = as_int(value(row, columns, "ordernumber", "actionnumber", "actionid"))
    # Higher clock is earlier in a period. Order number is authoritative when present.
    clock = int(round(clock_seconds(value(row, columns, "clock")) * 1000))
    return period, order if order else 10_000_000 - clock, order


def is_three_point(action_type: str, subtype: str, description: str, qualifiers: str) -> bool:
    text = " ".join((action_type, subtype, description, qualifiers)).lower()
    return any(token in text for token in ("3pt", "3-pt", "3 point", "3-pointer", "three point"))


def action_stats(row: dict[str, Any], columns: dict[str, str], score_delta: int) -> dict[str, int]:
    action_type = value(row, columns, "actiontype").lower().replace("_", " ")
    subtype = value(row, columns, "subtype").lower().replace("_", " ")
    description = value(row, columns, "description")
    qualifiers = value(row, columns, "qualifiers")
    text = " ".join((action_type, subtype, description, qualifiers)).lower()
    shot_result = value(row, columns, "shotresult").lower()
    is_fg = truthy(value(row, columns, "isfieldgoal")) or action_type in {"2pt", "3pt"}
    made = shot_result == "made" or ("miss" not in text and score_delta in {1, 2, 3})
    three = is_three_point(action_type, subtype, description, qualifiers)
    free_throw = "freethrow" in action_type.replace(" ", "") or "free throw" in text
    rebound = "rebound" in action_type or "rebound" in subtype
    offensive_rebound = rebound and ("offensive" in subtype or "offensive" in description.lower())
    turnover = "turnover" in action_type or action_type == "turnover"
    return {
        "fg2a": int(is_fg and not three),
        "fg2m": int(is_fg and not three and made),
        "fg3a": int(is_fg and three),
        "fg3m": int(is_fg and three and made),
        "fta": int(free_throw),
        "ftm": int(free_throw and made),
        "orb": int(offensive_rebound),
        "tov": int(turnover),
    }


def extract_target_rows(csv_path: Path, target_ids: set[str]) -> tuple[dict[str, list[dict[str, str]]], dict[str, Any]]:
    rows: dict[str, list[dict[str, str]]] = defaultdict(list)
    total_rows = 0
    with csv_path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = canonical_columns(reader.fieldnames)
        if "gameid" not in columns:
            raise RuntimeError("cdnnba archive does not expose gameId")
        required = {"period", "actiontype", "scorehome", "scoreaway", "teamid", "teamtricode", "possession"}
        missing = sorted(required - set(columns))
        if missing:
            raise RuntimeError(f"cdnnba archive missing fields: {missing}")
        for raw in reader:
            total_rows += 1
            game_id = normalize_id(value(raw, columns, "gameid"))
            if game_id in target_ids:
                rows[game_id].append(dict(raw))
    return dict(rows), {
        "archive_csv_rows_scanned": total_rows,
        "target_game_count_found": len(rows),
        "target_event_rows_found": sum(len(items) for items in rows.values()),
    }


def official_game_rows(db: sqlite3.Connection, game_ids: list[str]) -> dict[str, dict[str, Any]]:
    db.row_factory = sqlite3.Row
    placeholders = ",".join("?" for _ in game_ids)
    return {
        str(row["game_id"]): dict(row)
        for row in db.execute(f"SELECT * FROM games WHERE game_id IN ({placeholders})", game_ids)
    }


def missing_feature_game_ids(db: sqlite3.Connection) -> list[str]:
    rows = db.execute(
        """
        SELECT g.game_id
        FROM games g
        LEFT JOIN team_game_features f ON f.game_id=g.game_id
        WHERE g.season_label='2023-24'
        GROUP BY g.game_id
        HAVING COUNT(f.team_abbr)=0
        ORDER BY g.game_id
        """
    ).fetchall()
    return [str(row[0]) for row in rows]


def parse_game(
    game: dict[str, Any],
    event_rows: list[dict[str, str]],
) -> tuple[list[tuple[Any, ...]], list[tuple[Any, ...]], dict[str, Any]]:
    columns = canonical_columns(event_rows[0].keys())
    ordered = sorted(event_rows, key=lambda row: sort_key(row, columns))
    home_id = normalize_id(game.get("home_team_id"))
    away_id = normalize_id(game.get("away_team_id"))
    home_abbr = str(game.get("home_team_abbr") or "")
    away_abbr = str(game.get("away_team_abbr") or "")
    official = {home_id: int(game["home_score"]), away_id: int(game["away_score"])}
    abbreviations = {home_id: home_abbr, away_id: away_abbr}
    if not all((home_id, away_id, home_abbr, away_abbr)):
        raise RuntimeError("official game identity is incomplete")

    observed_team_map: dict[str, str] = {}
    for row in ordered:
        team_id = normalize_id(value(row, columns, "teamid"))
        tricode = value(row, columns, "teamtricode")
        if team_id and tricode:
            observed_team_map[team_id] = tricode
    for team_id, abbr in abbreviations.items():
        if observed_team_map.get(team_id) not in {None, abbr}:
            raise RuntimeError("cdnnba team identity disagrees with NBA Stats")

    totals: dict[str, Counter[str]] = {home_id: Counter(), away_id: Counter()}
    segments: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    previous_home = 0
    previous_away = 0
    valid_possession_rows = 0
    maximum_period = 4

    for row in ordered:
        period = as_int(value(row, columns, "period"), 1)
        maximum_period = max(maximum_period, period)
        home_score = as_int(value(row, columns, "scorehome"), previous_home)
        away_score = as_int(value(row, columns, "scoreaway"), previous_away)
        delta_home = max(home_score - previous_home, 0)
        delta_away = max(away_score - previous_away, 0)
        previous_home, previous_away = max(previous_home, home_score), max(previous_away, away_score)

        action_team = normalize_id(value(row, columns, "teamid"))
        if action_team in totals:
            score_delta = delta_home if action_team == home_id else delta_away
            totals[action_team].update(action_stats(row, columns, score_delta))
        totals[home_id]["reconstructed_points"] += delta_home
        totals[away_id]["reconstructed_points"] += delta_away

        possession_team = normalize_id(value(row, columns, "possession"))
        if possession_team not in totals:
            continue
        valid_possession_rows += 1
        clock = value(row, columns, "clock")
        segment_key = (period, possession_team)
        if current is None or current["segment_key"] != segment_key:
            current = {
                "segment_key": segment_key,
                "period": period,
                "offense_team_id": possession_team,
                "start_clock": clock,
                "end_clock": clock,
                "rows": [],
                "start_home": previous_home - delta_home,
                "start_away": previous_away - delta_away,
                "end_home": previous_home,
                "end_away": previous_away,
            }
            segments.append(current)
        current["end_clock"] = clock
        current["end_home"] = previous_home
        current["end_away"] = previous_away
        current["rows"].append(row)

    if previous_home != official[home_id] or previous_away != official[away_id]:
        raise RuntimeError("cdnnba terminal score does not match NBA Stats official score")
    if totals[home_id]["reconstructed_points"] != official[home_id]:
        raise RuntimeError("home reconstructed score mismatch")
    if totals[away_id]["reconstructed_points"] != official[away_id]:
        raise RuntimeError("away reconstructed score mismatch")

    possession_counts = Counter(segment["offense_team_id"] for segment in segments)
    possession_rows: list[tuple[Any, ...]] = []
    for index, segment in enumerate(segments, start=1):
        offense_id = segment["offense_team_id"]
        defense_id = away_id if offense_id == home_id else home_id
        segment_totals = Counter()
        start_home, start_away = segment["start_home"], segment["start_away"]
        last_home, last_away = start_home, start_away
        descriptions: list[str] = []
        for row in segment["rows"]:
            row_home = as_int(value(row, columns, "scorehome"), last_home)
            row_away = as_int(value(row, columns, "scoreaway"), last_away)
            delta = max(row_home - last_home, 0) if offense_id == home_id else max(row_away - last_away, 0)
            action_team = normalize_id(value(row, columns, "teamid"))
            if action_team == offense_id:
                segment_totals.update(action_stats(row, columns, delta))
            last_home, last_away = max(last_home, row_home), max(last_away, row_away)
            description = value(row, columns, "description")
            if description:
                descriptions.append(description)
        points = (segment["end_home"] - start_home) if offense_id == home_id else (segment["end_away"] - start_away)
        start_diff = (start_home - start_away) if offense_id == home_id else (start_away - start_home)
        possession_rows.append((
            stable_id(RECOVERY_SOURCE_ID, game["game_id"], segment["period"], index, offense_id),
            game["game_id"], game.get("game_date"), segment["period"],
            segment["start_clock"], segment["end_clock"], abbreviations[offense_id], abbreviations[defense_id],
            start_diff, "official_cdn_possession_team_transition", points,
            segment_totals["fg2a"], segment_totals["fg2m"], segment_totals["fg3a"], segment_totals["fg3m"],
            segment_totals["fta"], segment_totals["ftm"], segment_totals["orb"], segment_totals["tov"],
            0, 0, len(segment["rows"]), "\n".join(descriptions)[:20000], RECOVERY_SOURCE_ID, RECOVERY_FLAG,
        ))

    feature_rows: list[tuple[Any, ...]] = []
    game_minutes = 48.0 + max(maximum_period - 4, 0) * 5.0
    for team_id, opponent_id, is_home in ((home_id, away_id, 1), (away_id, home_id, 0)):
        own, opp = totals[team_id], totals[opponent_id]
        possessions = possession_counts[team_id]
        opponent_possessions = possession_counts[opponent_id]
        if not (60 <= possessions <= 180 and 60 <= opponent_possessions <= 180):
            raise RuntimeError("recovered possession count outside fail-closed range")
        fga = own["fg2a"] + own["fg3a"]
        fgm = own["fg2m"] + own["fg3m"]
        missed_fg = max(fga - fgm, 0)
        if not (40 <= fga <= 150 and 0 <= own["fg3a"] <= fga and 0 <= own["fta"] <= 80):
            raise RuntimeError("recovered shooting totals outside fail-closed range")
        pace = safe_div(48 * (possessions + opponent_possessions), 2 * game_minutes)
        off_rtg = safe_div(100 * official[team_id], possessions)
        def_rtg = safe_div(100 * official[opponent_id], opponent_possessions)
        net_rtg = round(off_rtg - def_rtg, 6) if off_rtg is not None and def_rtg is not None else None
        efg = safe_div(own["fg2m"] + own["fg3m"] + 0.5 * own["fg3m"], fga)
        tov_pct = safe_div(own["tov"], fga + 0.44 * own["fta"] + own["tov"])
        orb_pct = safe_div(own["orb"], missed_fg)
        ftr = safe_div(own["fta"], fga)
        if any(number is not None and (not math.isfinite(float(number))) for number in (pace, off_rtg, def_rtg, net_rtg, efg, tov_pct, orb_pct, ftr)):
            raise RuntimeError("non-finite recovered metric")
        feature_rows.append((
            game["game_id"], abbreviations[team_id], abbreviations[opponent_id], is_home,
            official[team_id], official[opponent_id], own["reconstructed_points"], opp["reconstructed_points"],
            possessions, opponent_possessions, pace, off_rtg, def_rtg, net_rtg,
            fga, fgm, own["fg3a"], own["fg3m"], own["fta"], own["ftm"], own["orb"], own["tov"],
            efg, tov_pct, orb_pct, ftr, 1, RECOVERY_FLAG,
        ))

    if len(feature_rows) != 2 or len(possession_rows) < 120:
        raise RuntimeError("recovery did not produce the expected feature/possession rows")
    return feature_rows, possession_rows, {
        "event_rows": len(ordered),
        "valid_possession_rows": valid_possession_rows,
        "possession_segments": len(segments),
        "home_possessions": possession_counts[home_id],
        "away_possessions": possession_counts[away_id],
        "terminal_score_match": True,
        "two_team_features_created": True,
    }


def patch_season_silver(gzip_path: Path, cdn_csv: Path, cdn_sha256: str, working_dir: Path) -> dict[str, Any]:
    sqlite_path = working_dir / "historical-silver-2023-recovery.sqlite"
    with gzip.open(gzip_path, "rb") as src, sqlite_path.open("wb") as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)
    db = sqlite3.connect(sqlite_path)
    try:
        target_ids = missing_feature_game_ids(db)
        if len(target_ids) != 2:
            raise RuntimeError(f"expected exactly two target games, found {len(target_ids)}")
        games = official_game_rows(db, target_ids)
        if len(games) != 2:
            raise RuntimeError("official game records missing")
        events_by_game, scan = extract_target_rows(cdn_csv, set(target_ids))
        if set(events_by_game) != set(target_ids):
            raise RuntimeError("official CDN archive does not cover both target games")

        before_features = int(db.execute("SELECT COUNT(*) FROM team_game_features").fetchone()[0])
        before_possessions = int(db.execute("SELECT COUNT(*) FROM possessions").fetchone()[0])
        diagnostics = []
        total_feature_rows: list[tuple[Any, ...]] = []
        total_possession_rows: list[tuple[Any, ...]] = []
        for game_id in target_ids:
            features, possessions, diagnostic = parse_game(games[game_id], events_by_game[game_id])
            total_feature_rows.extend(features)
            total_possession_rows.extend(possessions)
            diagnostics.append(diagnostic)

        db.executemany(
            "INSERT INTO possessions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            total_possession_rows,
        )
        db.executemany(
            "INSERT INTO team_game_features VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            total_feature_rows,
        )
        for game_id in target_ids:
            possession_count = int(db.execute("SELECT COUNT(*) FROM possessions WHERE game_id=?", (game_id,)).fetchone()[0])
            current_flags = str(db.execute("SELECT quality_flags FROM games WHERE game_id=?", (game_id,)).fetchone()[0] or "")
            flags = ",".join(filter(None, (current_flags, RECOVERY_FLAG)))
            db.execute(
                "UPDATE games SET possession_count=?, score_match=1, quality_flags=? WHERE game_id=?",
                (possession_count, flags, game_id),
            )
        metadata = {
            "official_cdnnba_recovery_version": "v1",
            "official_cdnnba_recovery_archive_sha256": cdn_sha256,
            "official_cdnnba_recovery_game_count": "2",
            "official_cdnnba_recovery_team_feature_rows": "4",
            "official_cdnnba_recovery_possession_rows": str(len(total_possession_rows)),
            "official_cdnnba_recovery_raw_archives_committed": "false",
        }
        db.executemany("INSERT OR REPLACE INTO metadata VALUES (?,?)", metadata.items())
        db.commit()

        after_features = int(db.execute("SELECT COUNT(*) FROM team_game_features").fetchone()[0])
        after_possessions = int(db.execute("SELECT COUNT(*) FROM possessions").fetchone()[0])
        remaining_missing = len(missing_feature_game_ids(db))
        duplicate_features = int(db.execute(
            "SELECT COUNT(*)-COUNT(DISTINCT game_id || ':' || team_abbr) FROM team_game_features"
        ).fetchone()[0])
        recovered_rows = int(db.execute(
            "SELECT COUNT(*) FROM team_game_features WHERE quality_flags LIKE ?", (f"%{RECOVERY_FLAG}%",)
        ).fetchone()[0])
        if after_features - before_features != 4 or recovered_rows != 4 or remaining_missing != 0 or duplicate_features != 0:
            raise RuntimeError("post-patch Silver invariants failed")
        db.execute("VACUUM")
    finally:
        db.close()

    gzip_file(sqlite_path, gzip_path)
    sqlite_path.unlink()
    return {
        **scan,
        "target_games": 2,
        "recovered_games": 2,
        "team_feature_rows_before": before_features,
        "team_feature_rows_after": after_features,
        "team_feature_rows_added": 4,
        "possession_rows_before": before_possessions,
        "possession_rows_after": after_possessions,
        "possession_rows_added": after_possessions - before_possessions,
        "remaining_games_without_team_features": remaining_missing,
        "duplicate_team_feature_rows": duplicate_features,
        "per_game_diagnostics": diagnostics,
        "game_identifiers_emitted_in_report": False,
    }


def build_all(output_root: Path) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)
    base_config = read_json(Path("config/historical-source-pilot.json"))
    season_root = output_root / "seasons"
    summaries: dict[str, Any] = {}
    for year in YEARS:
        config = copy.deepcopy(base_config)
        for kind in ("pbpstats", "nbastats"):
            item = config["sources"][f"{kind}_2023"]
            item["season_label"] = season_label(year)
            item["url"] = f"https://github.com/shufinskiy/nba_data/raw/main/datasets/{kind}_{year}.tar.xz"
        config_path = output_root / f"config-{year}.json"
        write_json(config_path, config)
        report = silver_builder.build(config_path, season_root / str(year), 600)
        summaries[season_label(year)] = {
            "games": int(report["outputs"]["tables"]["games"]),
            "team_game_features": int(report["outputs"]["tables"]["team_game_features"]),
            "ready": report["decision"]["ready_for_private_model_feature_pipeline"] is True,
        }
        if summaries[season_label(year)]["games"] < 1000 or not summaries[season_label(year)]["ready"]:
            raise RuntimeError(f"baseline Silver quality failed for {season_label(year)}")

    with tempfile.TemporaryDirectory(prefix="nbavl-cdnnba-recovery-source-") as temp_name:
        temp = Path(temp_name)
        archive = temp / "cdnnba_2023.tar.xz"
        source_info = download(CDN_URL, archive, 600 * 1048576)
        extracted = temp / "cdnnba_2023"
        extracted.mkdir()
        source_info["member_count"] = extract(archive, extracted)
        candidates = sorted(extracted.rglob("*.csv"))
        if len(candidates) != 1:
            raise RuntimeError(f"expected one cdnnba CSV, found {len(candidates)}")
        recovery = patch_season_silver(
            season_root / "2023" / "historical-silver.sqlite.gz",
            candidates[0],
            str(source_info["sha256"]),
            output_root,
        )

    combined_dir = output_root / "combined"
    sources = silver_combiner.discover_sources(season_root)
    if len(sources) != 5:
        raise RuntimeError(f"expected five Silver databases, found {len(sources)}")
    combined = silver_combiner.merge_sources(sources, combined_dir)
    silver_path = combined_dir / "historical-silver-multiseason.sqlite.gz"
    # Restore alternate-source provenance after the standard combiner normalizes source IDs.
    combined_sqlite = output_root / "combined-recovery-provenance.sqlite"
    with gzip.open(silver_path, "rb") as src, combined_sqlite.open("wb") as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)
    combined_db = sqlite3.connect(combined_sqlite)
    combined_db.execute(
        "UPDATE possessions SET source_id=? WHERE quality_flags LIKE ?",
        (RECOVERY_SOURCE_ID, f"%{RECOVERY_FLAG}%"),
    )
    combined_db.execute("INSERT OR REPLACE INTO metadata VALUES (?,?)", (
        "official_cdnnba_recovery_source_id", RECOVERY_SOURCE_ID,
    ))
    combined_db.commit()
    combined_db.execute("VACUUM")
    combined_db.close()
    gzip_file(combined_sqlite, silver_path)
    combined_sqlite.unlink()

    gold_dir = output_root / "gold"
    gold = gold_builder.build(silver_path, gold_dir)
    silver_games = int(combined["outputs"]["tables"]["games"])
    silver_features = int(combined["outputs"]["tables"]["team_game_features"])
    gold_matchups = int(gold["outputs"]["tables"]["gold_matchup_features"])
    gold_team_rows = int(gold["outputs"]["tables"]["gold_team_game_features"])
    pit = gold["quality"]["point_in_time"]
    passed = (
        silver_games == 5826
        and silver_features == 11652
        and gold_matchups == 5826
        and gold_team_rows == 11652
        and recovery["recovered_games"] == 2
        and recovery["remaining_games_without_team_features"] == 0
        and pit["passed"] is True
        and int(pit["violations"]) == 0
        and combined["quality"]["all_duplicate_checks_pass"] is True
    )
    if not passed:
        raise RuntimeError("final multi-season recovery invariants failed")

    artifact_dir = output_root / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(silver_path, artifact_dir / "historical-silver-multiseason-recovered-v1.sqlite.gz")
    shutil.copy2(gold_dir / "historical-gold-multiseason.sqlite.gz", artifact_dir / "historical-gold-multiseason-recovered-v1.sqlite.gz")
    result = {
        "schema_version": "historical-silver-2023-24-two-game-official-cdn-pbp-recovery-result-v1",
        "created_at": utc_now(),
        "formal_state": FORMAL_PASS,
        "source": {
            "provider": "shufinskiy/nba_data archive of official cdn.nba.com play-by-play",
            "source_key": "cdnnba_2023",
            "url": CDN_URL,
            "archive_sha256": source_info["sha256"],
            "archive_bytes": int(source_info["bytes"]),
            "archive_member_count": int(source_info["member_count"]),
            "raw_archive_committed": False,
        },
        "baseline_seasons": summaries,
        "recovery": recovery,
        "final_outputs": {
            "silver_seasons": combined["seasons"],
            "silver_games": silver_games,
            "silver_team_game_features": silver_features,
            "gold_matchup_features": gold_matchups,
            "gold_team_game_features": gold_team_rows,
            "gold_point_in_time_passed": pit["passed"],
            "gold_point_in_time_violations": pit["violations"],
            "silver_artifact_file": "historical-silver-multiseason-recovered-v1.sqlite.gz",
            "gold_artifact_file": "historical-gold-multiseason-recovered-v1.sqlite.gz",
        },
        "decision": {
            "two_source_exceptions_resolved": True,
            "historical_silver_complete_for_governed_five_season_scope": True,
            "historical_gold_complete_for_governed_five_season_scope": True,
            "documented_exception_count_after_recovery": 0,
            "ready_for_separate_artifact_adoption_record": True,
            "ready_for_market_backtest": False,
            "ready_for_model_retraining": False,
            "betting_edge_claim": False,
            "formal_stake": 0,
        },
        "boundaries": {
            "repository_database_modified": False,
            "source_archives_committed": False,
            "manual_or_synthetic_feature_rows": False,
            "official_alternate_pbp_source_used": True,
            "raw_game_identifiers_emitted_in_aggregate_report": False,
            "market_backtest_executed": False,
            "model_retraining_executed": False,
            "formal_stake": 0,
        },
    }
    write_json(artifact_dir / "two-game-official-cdn-pbp-recovery-result-v1.json", result)
    return result


def self_test(output: Path) -> dict[str, Any]:
    columns = {
        "actiontype": "actionType", "subtype": "subType", "description": "description",
        "qualifiers": "qualifiers", "shotresult": "shotResult", "isfieldgoal": "isFieldGoal",
    }
    made_three = action_stats({
        "actionType": "3pt", "subType": "Jump Shot", "description": "Made 3PT", "qualifiers": "",
        "shotResult": "Made", "isFieldGoal": "1",
    }, columns, 3)
    missed_two = action_stats({
        "actionType": "2pt", "subType": "Layup", "description": "MISS Layup", "qualifiers": "",
        "shotResult": "Missed", "isFieldGoal": "1",
    }, columns, 0)
    free_throw = action_stats({
        "actionType": "freethrow", "subType": "1 of 1", "description": "Free Throw Made", "qualifiers": "",
        "shotResult": "Made", "isFieldGoal": "0",
    }, columns, 1)
    assert made_three["fg3a"] == 1 and made_three["fg3m"] == 1
    assert missed_two["fg2a"] == 1 and missed_two["fg2m"] == 0
    assert free_throw["fta"] == 1 and free_throw["ftm"] == 1
    report = {
        "schema_version": "historical-silver-two-game-official-cdn-recovery-self-test-v1",
        "formal_state": "HISTORICAL_SILVER_TWO_GAME_OFFICIAL_CDN_RECOVERY_SELF_TEST_PASS",
        "network_calls_made": False,
        "real_rows_read": False,
        "market_backtest_executed": False,
        "model_retraining_executed": False,
        "formal_stake": 0,
    }
    write_json(output, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    args.output_root.mkdir(parents=True, exist_ok=True)
    if args.self_test:
        report = self_test(args.output_root / "recovery-self-test-v1.json")
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    try:
        report = build_all(args.output_root)
        print(json.dumps({
            "formal_state": report["formal_state"],
            "recovered_games": report["recovery"]["recovered_games"],
            "silver_games": report["final_outputs"]["silver_games"],
            "gold_matchups": report["final_outputs"]["gold_matchup_features"],
            "formal_stake": 0,
        }, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        blocked = {
            "schema_version": "historical-silver-2023-24-two-game-official-cdn-pbp-recovery-result-v1",
            "created_at": utc_now(),
            "formal_state": FORMAL_BLOCKED,
            "error_type": type(exc).__name__,
            "error_summary": str(exc).replace("/tmp/", "<temporary>/")[:1000],
            "decision": {
                "two_source_exceptions_resolved": False,
                "historical_silver_complete_for_governed_five_season_scope": False,
                "historical_gold_complete_for_governed_five_season_scope": False,
                "ready_for_market_backtest": False,
                "ready_for_model_retraining": False,
                "formal_stake": 0,
            },
            "boundaries": {
                "repository_database_modified": False,
                "source_archives_committed": False,
                "raw_game_identifiers_emitted_in_aggregate_report": False,
                "market_backtest_executed": False,
                "model_retraining_executed": False,
                "formal_stake": 0,
            },
        }
        write_json(args.output_root / "artifacts" / "two-game-official-cdn-pbp-recovery-result-v1.json", blocked)
        print(json.dumps(blocked, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
