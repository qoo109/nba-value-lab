#!/usr/bin/env python3
"""Diagnose the two PlayByPlayV3 terminal-score mismatches in 2025-26.

Downloads the same public archives used by the governed Silver adapter, scans
only the predeclared game IDs, and emits aggregate score-state histories. Raw
rows, descriptions, archives, and source CSV files are never emitted.
"""
from __future__ import annotations

import argparse
import csv
import json
import tempfile
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from historical_phase2_core import download, extract

TARGET_GAMES = ("0022500029", "0022500232")
SOURCES = {
    "cdnnba_2025": "https://github.com/shufinskiy/nba_data/raw/main/datasets/cdnnba_2025.tar.xz",
    "nbastatsv3_2025": "https://github.com/shufinskiy/nba_data/raw/main/datasets/nbastatsv3_2025.tar.xz",
    "matchups_2025": "https://github.com/shufinskiy/nba_data/raw/main/datasets/matchups_2025.tar.xz",
}


def canonical(name: Any) -> str:
    return str(name or "").strip().lower().replace("_", "")


def columns(fieldnames):
    return {canonical(name): str(name) for name in (fieldnames or [])}


def value(row, lookup, *names):
    for name in names:
        actual = lookup.get(canonical(name))
        if actual is None:
            continue
        text = str(row.get(actual, "") or "").strip()
        if text.lower() not in {"", "nan", "none", "null"}:
            return text
    return ""


def normalize_game_id(raw: Any) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    try:
        text = str(int(float(text)))
    except ValueError:
        pass
    return text.zfill(10) if text.isdigit() and len(text) <= 10 else text


def as_int(raw: Any, default: int = -1) -> int:
    try:
        return int(float(str(raw).strip()))
    except (TypeError, ValueError):
        return default


def prepare_source(key: str, root: Path, max_mb: int):
    archive = root / f"{key}.tar.xz"
    extracted = root / key
    extracted.mkdir()
    info = download(SOURCES[key], archive, max_mb * 1048576)
    info["member_count"] = extract(archive, extracted)
    csvs = sorted(extracted.rglob("*.csv"))
    preferred = [path for path in csvs if key.lower() in path.name.lower()]
    if len(preferred) == 1:
        path = preferred[0]
    elif len(csvs) == 1:
        path = csvs[0]
    else:
        raise RuntimeError(f"{key}: ambiguous CSV inventory")
    return path, info


def state(row, lookup, row_number: int) -> dict[str, Any] | None:
    home_raw = value(row, lookup, "scorehome")
    away_raw = value(row, lookup, "scoreaway")
    if not home_raw or not away_raw:
        return None
    return {
        "archive_row": row_number,
        "period": as_int(value(row, lookup, "period"), 0),
        "clock": value(row, lookup, "clock") or None,
        "action_number": as_int(value(row, lookup, "actionnumber", "ordernumber", "actionid"), -1),
        "home_score": as_int(home_raw),
        "away_score": as_int(away_raw),
        "score_total": as_int(home_raw) + as_int(away_raw),
        "action_type": value(row, lookup, "actiontype") or None,
        "sub_type": value(row, lookup, "subtype") or None,
        "time_actual": value(row, lookup, "timeactual") or None,
    }


def scan_score_source(path: Path, source_key: str) -> dict[str, Any]:
    result = {
        game_id: {
            "rows": 0,
            "team_identity": {},
            "last_score_by_archive_order": None,
            "last_score_by_max_action_number": None,
            "max_score_total_state": None,
            "last_distinct_score_states": [],
            "period_end_states": {},
        }
        for game_id in TARGET_GAMES
    }
    recent = {game_id: deque(maxlen=15) for game_id in TARGET_GAMES}
    last_pair = {game_id: None for game_id in TARGET_GAMES}
    max_action = {game_id: -1 for game_id in TARGET_GAMES}

    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        lookup = columns(reader.fieldnames)
        if "gameid" not in lookup:
            raise RuntimeError(f"{source_key}: missing gameId")
        for row_number, row in enumerate(reader, start=1):
            game_id = normalize_game_id(value(row, lookup, "gameid"))
            if game_id not in result:
                continue
            item = result[game_id]
            item["rows"] += 1
            team_id = value(row, lookup, "teamid")
            tricode = value(row, lookup, "teamtricode").upper()
            if team_id and tricode:
                item["team_identity"][team_id] = tricode
            score = state(row, lookup, row_number)
            if score is None:
                continue
            item["last_score_by_archive_order"] = score
            if score["action_number"] >= max_action[game_id]:
                max_action[game_id] = score["action_number"]
                item["last_score_by_max_action_number"] = score
            if (
                item["max_score_total_state"] is None
                or score["score_total"] >= item["max_score_total_state"]["score_total"]
            ):
                item["max_score_total_state"] = score
            pair = (score["home_score"], score["away_score"])
            if pair != last_pair[game_id]:
                recent[game_id].append(score)
                last_pair[game_id] = pair
            period = str(score["period"])
            previous = item["period_end_states"].get(period)
            if previous is None or score["archive_row"] > previous["archive_row"]:
                item["period_end_states"][period] = score

    for game_id in TARGET_GAMES:
        result[game_id]["last_distinct_score_states"] = list(recent[game_id])
        result[game_id]["team_identity"] = dict(sorted(result[game_id]["team_identity"].items()))
    return result


def scan_matchups(path: Path) -> dict[str, Any]:
    result = {
        game_id: {
            "home_team_id": None,
            "away_team_id": None,
            "team_identity": {},
            "rows": 0,
        }
        for game_id in TARGET_GAMES
    }
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        lookup = columns(reader.fieldnames)
        for row in reader:
            game_id = normalize_game_id(value(row, lookup, "gameid"))
            if game_id not in result:
                continue
            item = result[game_id]
            item["rows"] += 1
            item["home_team_id"] = value(row, lookup, "hometeamid") or item["home_team_id"]
            item["away_team_id"] = value(row, lookup, "awayteamid") or item["away_team_id"]
            team_id = value(row, lookup, "teamid")
            tricode = value(row, lookup, "teamtricode").upper()
            if team_id and tricode:
                item["team_identity"][team_id] = tricode
    for item in result.values():
        item["home_team_abbr"] = item["team_identity"].get(item["home_team_id"])
        item["away_team_abbr"] = item["team_identity"].get(item["away_team_id"])
        item["team_identity"] = dict(sorted(item["team_identity"].items()))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-download-mb", type=int, default=600)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="nbavl-v3-score-diagnostic-") as temp_name:
        temp = Path(temp_name)
        cdn_path, cdn_info = prepare_source("cdnnba_2025", temp, args.max_download_mb)
        v3_path, v3_info = prepare_source("nbastatsv3_2025", temp, args.max_download_mb)
        matchup_path, matchup_info = prepare_source("matchups_2025", temp, args.max_download_mb)
        cdn = scan_score_source(cdn_path, "cdnnba_2025")
        v3 = scan_score_source(v3_path, "nbastatsv3_2025")
        matchups = scan_matchups(matchup_path)

    games = {}
    for game_id in TARGET_GAMES:
        games[game_id] = {
            "matchup_identity": matchups[game_id],
            "cdnnba": cdn[game_id],
            "nbastatsv3": v3[game_id],
            "comparisons": {
                "archive_order_terminal_scores_equal": (
                    cdn[game_id]["last_score_by_archive_order"] is not None
                    and v3[game_id]["last_score_by_archive_order"] is not None
                    and (
                        cdn[game_id]["last_score_by_archive_order"]["home_score"],
                        cdn[game_id]["last_score_by_archive_order"]["away_score"],
                    ) == (
                        v3[game_id]["last_score_by_archive_order"]["home_score"],
                        v3[game_id]["last_score_by_archive_order"]["away_score"],
                    )
                ),
                "cdn_terminal_score": {
                    "home": cdn[game_id]["last_score_by_archive_order"]["home_score"],
                    "away": cdn[game_id]["last_score_by_archive_order"]["away_score"],
                },
                "v3_terminal_score": {
                    "home": v3[game_id]["last_score_by_archive_order"]["home_score"],
                    "away": v3[game_id]["last_score_by_archive_order"]["away_score"],
                },
                "v3_contains_cdn_terminal_score_in_recent_history": any(
                    state["home_score"] == cdn[game_id]["last_score_by_archive_order"]["home_score"]
                    and state["away_score"] == cdn[game_id]["last_score_by_archive_order"]["away_score"]
                    for state in v3[game_id]["last_distinct_score_states"]
                ),
            },
        }

    report = {
        "schema_version": "v3-terminal-score-exception-diagnostic-2025-26-v1",
        "formal_state": "V3_TERMINAL_SCORE_EXCEPTION_DIAGNOSTIC_COMPLETE",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "target_game_ids": list(TARGET_GAMES),
        "sources": {
            "cdnnba_2025": {"sha256": cdn_info["sha256"], "bytes": cdn_info["bytes"]},
            "nbastatsv3_2025": {"sha256": v3_info["sha256"], "bytes": v3_info["bytes"]},
            "matchups_2025": {"sha256": matchup_info["sha256"], "bytes": matchup_info["bytes"]},
        },
        "games": games,
        "execution": {
            "raw_archives_committed": False,
            "raw_rows_emitted": 0,
            "provider_api_requests": 0,
            "model_retraining_executed": False,
            "model_scoring_executed": False,
            "market_join_executed": False,
            "formal_stake": 0,
        },
    }
    path = args.output_dir / "v3-terminal-score-exception-diagnostic-2025-26-v1.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
