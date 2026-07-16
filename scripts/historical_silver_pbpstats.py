#!/usr/bin/env python3
"""Normalize pbpstats possession-event rows and derive team game features."""

from __future__ import annotations

import csv
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from historical_silver_schema import as_int, clean, parse_free_throws, row_fingerprint, safe_div, stable_id

GROUPING_FIELDS = (
    "GAMEID", "PERIOD", "STARTTIME", "ENDTIME", "OPPONENT",
    "STARTSCOREDIFFERENTIAL", "STARTTYPE",
)


def normalize_pbpstats(csv_path: Path):
    groups = {}
    opponents = defaultdict(set)
    game_dates = {}
    exact_seen = set()
    exact_duplicates = 0
    incomplete_rows = 0

    with csv_path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = list(reader.fieldnames or [])
        for row in reader:
            fingerprint = row_fingerprint(row, columns)
            if fingerprint in exact_seen:
                exact_duplicates += 1
                continue
            exact_seen.add(fingerprint)
            key = tuple((clean(row.get(field)) or "") for field in GROUPING_FIELDS)
            if any(not value for value in key):
                incomplete_rows += 1
                continue

            game_id, period, start_clock, end_clock, opponent, score_diff, start_type = key
            opponents[game_id].add(opponent)
            game_date = clean(row.get("GAMEDATE"))
            if game_date:
                game_dates[game_id] = game_date

            if key not in groups:
                groups[key] = {
                    "game_id": game_id,
                    "game_date": game_date,
                    "period": as_int(period),
                    "start_clock": start_clock,
                    "end_clock": end_clock,
                    "defense_team_abbr": opponent,
                    "start_score_differential": as_int(score_diff),
                    "start_type": start_type,
                    "fg2a": as_int(row.get("FG2A")),
                    "fg2m": as_int(row.get("FG2M")),
                    "fg3a": as_int(row.get("FG3A")),
                    "fg3m": as_int(row.get("FG3M")),
                    "offensive_rebounds": as_int(row.get("OFFENSIVEREBOUNDS")),
                    "turnovers": as_int(row.get("TURNOVERS")),
                    "shooting_fouls_drawn": as_int(row.get("SHOOTINGFOULSDRAWN")),
                    "nonshooting_fouls_resulting_in_fts": as_int(row.get("NONSHOOTINGFOULSTHATRESULTEDINFTS")),
                    "events_text": clean(row.get("EVENTS")),
                    "event_rows": 0,
                }
            groups[key]["event_rows"] += 1

    possessions = []
    team_inference_failures = 0
    for key, item in groups.items():
        game_teams = opponents[item["game_id"]]
        offense_candidates = sorted(game_teams - {item["defense_team_abbr"]})
        offense = offense_candidates[0] if len(offense_candidates) == 1 else None
        flags = []
        if offense is None:
            team_inference_failures += 1
            flags.append("offense_team_unresolved")
        fta, ftm = parse_free_throws(item["events_text"])
        item.update({
            "possession_id": stable_id(*key),
            "offense_team_abbr": offense,
            "fta": fta,
            "ftm": ftm,
            "points_scored": 2 * item["fg2m"] + 3 * item["fg3m"] + ftm,
            "quality_flags": ",".join(flags),
        })
        possessions.append(item)

    return possessions, dict(opponents), game_dates, {
        "rows_after_exact_dedupe": len(exact_seen),
        "exact_duplicate_rows": exact_duplicates,
        "incomplete_grouping_rows": incomplete_rows,
        "possession_count": len(possessions),
        "team_inference_failures": team_inference_failures,
        "game_count": len(opponents),
    }


def insert_possessions(connection: sqlite3.Connection, possessions, batch_size: int = 5000):
    batch = []
    for item in possessions:
        batch.append((
            item["possession_id"], item["game_id"], item["game_date"], item["period"],
            item["start_clock"], item["end_clock"], item["offense_team_abbr"],
            item["defense_team_abbr"], item["start_score_differential"], item["start_type"],
            item["points_scored"], item["fg2a"], item["fg2m"], item["fg3a"], item["fg3m"],
            item["fta"], item["ftm"], item["offensive_rebounds"], item["turnovers"],
            item["shooting_fouls_drawn"], item["nonshooting_fouls_resulting_in_fts"],
            item["event_rows"], item["events_text"], "pbpstats_2023", item["quality_flags"],
        ))
        if len(batch) >= batch_size:
            connection.executemany(
                "INSERT INTO possessions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                batch,
            )
            batch.clear()
    if batch:
        connection.executemany(
            "INSERT INTO possessions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            batch,
        )


def aggregate_team_features(possessions, game_rows):
    totals = defaultdict(Counter)
    teams_by_game = defaultdict(set)
    for item in possessions:
        game_id = item["game_id"]
        team = item["offense_team_abbr"]
        if not team:
            continue
        teams_by_game[game_id].add(team)
        bucket = totals[(game_id, team)]
        bucket["possessions"] += 1
        bucket["points"] += item["points_scored"]
        bucket["fg2a"] += item["fg2a"]
        bucket["fg2m"] += item["fg2m"]
        bucket["fg3a"] += item["fg3a"]
        bucket["fg3m"] += item["fg3m"]
        bucket["fta"] += item["fta"]
        bucket["ftm"] += item["ftm"]
        bucket["orb"] += item["offensive_rebounds"]
        bucket["tov"] += item["turnovers"]

    output = []
    score_mismatch_rows = 0
    incomplete_team_games = 0
    for game_id, game in game_rows.items():
        teams = sorted(teams_by_game.get(game_id, set()))
        if len(teams) != 2:
            incomplete_team_games += 1
            continue
        for team in teams:
            opponent = next(item for item in teams if item != team)
            own = totals[(game_id, team)]
            opp = totals[(game_id, opponent)]
            fga = own["fg2a"] + own["fg3a"]
            fgm = own["fg2m"] + own["fg3m"]
            missed_fg = max(fga - fgm, 0)
            game_minutes = game["game_minutes"]
            pace = safe_div(48 * (own["possessions"] + opp["possessions"]), 2 * game_minutes)
            off_rtg = safe_div(100 * own["points"], own["possessions"])
            def_rtg = safe_div(100 * opp["points"], opp["possessions"])
            net_rtg = round(off_rtg - def_rtg, 6) if off_rtg is not None and def_rtg is not None else None
            efg = safe_div(own["fg2m"] + own["fg3m"] + 0.5 * own["fg3m"], fga)
            tov_pct = safe_div(own["tov"], fga + 0.44 * own["fta"] + own["tov"])
            orb_pct = safe_div(own["orb"], missed_fg)
            ftr = safe_div(own["fta"], fga)
            home_abbr = game.get("home_team_abbr")
            is_home = int(team == home_abbr) if home_abbr else None
            official_points = game.get("home_score") if is_home == 1 else game.get("away_score") if is_home == 0 else None
            points_match = int(official_points == own["points"]) if official_points is not None else None
            flags = []
            if points_match == 0:
                score_mismatch_rows += 1
                flags.append("possession_points_do_not_match_final_score")
            if orb_pct is None:
                flags.append("orb_pct_unavailable")
            output.append((
                game_id, team, opponent, is_home, own["points"], opp["points"],
                own["possessions"], opp["possessions"], pace, off_rtg, def_rtg, net_rtg,
                fga, fgm, own["fg3a"], own["fg3m"], own["fta"], own["ftm"],
                own["orb"], own["tov"], efg, tov_pct, orb_pct, ftr, points_match,
                ",".join(flags),
            ))
    return output, {
        "team_game_row_count": len(output),
        "score_mismatch_rows": score_mismatch_rows,
        "incomplete_team_games": incomplete_team_games,
    }
