#!/usr/bin/env python3
"""Normalize NBA Stats event-level PBP into the historical Silver database."""

from __future__ import annotations

import csv
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from historical_silver_schema import as_int, clean, parse_score, row_fingerprint, stable_id


def _record_side_team(description, team_abbr, team_id, side_counts, side):
    if description and (team_abbr or team_id):
        side_counts[side][(team_abbr, team_id)] += 1


def _choose_team(counter):
    if not counter:
        return None, None
    return counter.most_common(1)[0][0]


def normalize_nbastats(csv_path: Path, connection: sqlite3.Connection, batch_size: int = 5000):
    games = defaultdict(lambda: {
        "side_counts": {"home": Counter(), "away": Counter()},
        "home_score": None,
        "away_score": None,
        "max_period": 0,
        "event_count": 0,
    })
    exact_seen = set()
    exact_duplicates = 0
    event_ids = set()
    event_id_collisions = 0
    batch = []

    with csv_path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = list(reader.fieldnames or [])
        for row_number, row in enumerate(reader, 1):
            fingerprint = row_fingerprint(row, columns)
            if fingerprint in exact_seen:
                exact_duplicates += 1
                continue
            exact_seen.add(fingerprint)

            game_id = clean(row.get("GAME_ID"))
            if not game_id:
                continue
            event_num = as_int(row.get("EVENTNUM"), -1)
            event_type = as_int(row.get("EVENTMSGTYPE"), -1)
            action_type = as_int(row.get("EVENTMSGACTIONTYPE"), -1)
            period = as_int(row.get("PERIOD"), 0)
            clock = clean(row.get("PCTIMESTRING"))
            home_description = clean(row.get("HOMEDESCRIPTION"))
            away_description = clean(row.get("VISITORDESCRIPTION"))
            neutral_description = clean(row.get("NEUTRALDESCRIPTION"))
            team_id = clean(row.get("PLAYER1_TEAM_ID"))
            team_abbr = clean(row.get("PLAYER1_TEAM_ABBREVIATION"))
            player1_id = clean(row.get("PLAYER1_ID"))
            player2_id = clean(row.get("PLAYER2_ID"))
            player3_id = clean(row.get("PLAYER3_ID"))
            side = "home" if home_description else "away" if away_description else "neutral"
            description = home_description or away_description or neutral_description
            away_score, home_score = parse_score(row.get("SCORE"))

            event_id = stable_id(game_id, event_num, event_type, action_type, period, clock, player1_id, description)
            if event_id in event_ids:
                event_id_collisions += 1
                event_id = stable_id(event_id, row_number, fingerprint)
            event_ids.add(event_id)

            game = games[game_id]
            game["event_count"] += 1
            game["max_period"] = max(game["max_period"], period)
            if away_score is not None and home_score is not None:
                game["away_score"] = away_score
                game["home_score"] = home_score
            _record_side_team(home_description, team_abbr, team_id, game["side_counts"], "home")
            _record_side_team(away_description, team_abbr, team_id, game["side_counts"], "away")

            batch.append((
                event_id, game_id, event_num if event_num >= 0 else None,
                event_type if event_type >= 0 else None,
                action_type if action_type >= 0 else None,
                period, clock, side, description, neutral_description,
                away_score, home_score, clean(row.get("SCOREMARGIN")),
                team_id, team_abbr, player1_id, player2_id, player3_id,
                as_int(row.get("VIDEO_AVAILABLE_FLAG"), 0),
                "nbastats_2023", row_number,
            ))
            if len(batch) >= batch_size:
                connection.executemany(
                    "INSERT INTO pbp_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    batch,
                )
                batch.clear()

    if batch:
        connection.executemany(
            "INSERT INTO pbp_events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            batch,
        )

    for game in games.values():
        game["home_team_abbr"], game["home_team_id"] = _choose_team(game["side_counts"]["home"])
        game["away_team_abbr"], game["away_team_id"] = _choose_team(game["side_counts"]["away"])
        del game["side_counts"]

    return dict(games), {
        "rows_after_exact_dedupe": len(exact_seen),
        "exact_duplicate_rows": exact_duplicates,
        "event_id_collisions_resolved": event_id_collisions,
        "game_count": len(games),
    }
