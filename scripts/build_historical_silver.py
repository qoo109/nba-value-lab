#!/usr/bin/env python3
"""Build a normalized, compressed SQLite Silver database from historical NBA sources."""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import tempfile
from collections import Counter
from pathlib import Path

from historical_phase2_core import download, extract, select_csv
from historical_silver_nbastats import normalize_nbastats
from historical_silver_pbpstats import aggregate_team_features, insert_possessions, normalize_pbpstats
from historical_silver_schema import create_schema, gzip_file

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "historical-source-pilot.json"


def game_minutes(max_period):
    return 48.0 + max(max_period - 4, 0) * 5.0


def prepare_source(key, source, temp_root, max_download_mb):
    archive = temp_root / f"{key}.tar.xz"
    extracted = temp_root / f"{key}-raw"
    extracted.mkdir()
    archive_info = download(source["url"], archive, max_download_mb * 1048576)
    archive_info["member_count"] = extract(archive, extracted)
    csv_path = select_csv(extracted, source)
    archive_info["csv_name"] = csv_path.name
    archive_info["csv_bytes"] = csv_path.stat().st_size
    return csv_path, archive_info


def build_games(nb_games, opponents, game_dates, possessions, season_label):
    possession_counts = Counter(item["game_id"] for item in possessions)
    periods_by_game = Counter()
    for item in possessions:
        periods_by_game[item["game_id"]] = max(periods_by_game[item["game_id"]], item["period"])
    games = {}
    for game_id in sorted(set(nb_games) | set(opponents)):
        nb = nb_games.get(game_id, {})
        pbp_teams = sorted(opponents.get(game_id, set()))
        flags = []
        home_abbr = nb.get("home_team_abbr")
        away_abbr = nb.get("away_team_abbr")
        if not home_abbr or not away_abbr:
            flags.append("home_away_team_unresolved")
        if pbp_teams and {home_abbr, away_abbr} != set(pbp_teams):
            flags.append("source_team_set_mismatch")
        max_period = nb.get("max_period") or periods_by_game.get(game_id, 4)
        games[game_id] = {
            "game_id": game_id,
            "game_date": game_dates.get(game_id),
            "season_label": season_label,
            "home_team_id": nb.get("home_team_id"),
            "home_team_abbr": home_abbr,
            "away_team_id": nb.get("away_team_id"),
            "away_team_abbr": away_abbr,
            "home_score": nb.get("home_score"),
            "away_score": nb.get("away_score"),
            "max_period": max_period,
            "game_minutes": game_minutes(max_period),
            "pbp_event_count": nb.get("event_count", 0),
            "possession_count": possession_counts.get(game_id, 0),
            "score_match": None,
            "quality_flags": flags,
        }
    return games


def insert_games(connection, games):
    connection.executemany(
        "INSERT INTO games VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [(
            game["game_id"], game["game_date"], game["season_label"],
            game["home_team_id"], game["home_team_abbr"], game["away_team_id"],
            game["away_team_abbr"], game["home_score"], game["away_score"],
            game["max_period"], game["game_minutes"], game["pbp_event_count"],
            game["possession_count"], game["score_match"],
            ",".join(game["quality_flags"]),
        ) for game in games.values()],
    )


def update_game_score_flags(connection, games, feature_rows):
    matches = {}
    for row in feature_rows:
        matches.setdefault(row[0], []).append(row[24])
    matched_games = mismatched_games = unknown_games = 0
    updates = []
    for game_id, game in games.items():
        values = matches.get(game_id, [])
        if len(values) == 2 and all(value == 1 for value in values):
            score_match = 1
            matched_games += 1
        elif any(value == 0 for value in values):
            score_match = 0
            mismatched_games += 1
            game["quality_flags"].append("possession_score_mismatch")
        else:
            score_match = None
            unknown_games += 1
        updates.append((score_match, ",".join(game["quality_flags"]), game_id))
    connection.executemany(
        "UPDATE games SET score_match=?, quality_flags=? WHERE game_id=?",
        updates,
    )
    known = matched_games + mismatched_games
    return {
        "matched_games": matched_games,
        "mismatched_games": mismatched_games,
        "unknown_games": unknown_games,
        "score_match_rate": round(matched_games / known, 6) if known else 0,
    }


def write_sample(connection, output):
    tables = ("games", "pbp_events", "possessions", "team_game_features")
    payload = {
        "schema_version": "0.1.0-silver",
        "raw_data_included": False,
        "tables": {},
    }
    connection.row_factory = sqlite3.Row
    for table in tables:
        payload["tables"][table] = [
            dict(row) for row in connection.execute(f"SELECT * FROM {table} LIMIT 5").fetchall()
        ]
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build(config_path, output_dir, max_download_mb):
    config = json.loads(config_path.read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True, exist_ok=True)
    database = output_dir / "historical-silver.sqlite"
    compressed_database = output_dir / "historical-silver.sqlite.gz"
    report_path = output_dir / "silver-build-report.json"
    sample_path = output_dir / "silver-sample.json"

    with tempfile.TemporaryDirectory(prefix="nbavl-silver-") as temp:
        temp_root = Path(temp)
        pbp_csv, pbp_archive = prepare_source(
            "pbpstats_2023", config["sources"]["pbpstats_2023"], temp_root, max_download_mb
        )
        nba_csv, nba_archive = prepare_source(
            "nbastats_2023", config["sources"]["nbastats_2023"], temp_root, max_download_mb
        )

        connection = sqlite3.connect(database)
        create_schema(connection)
        nb_games, nb_report = normalize_nbastats(nba_csv, connection)
        possessions, opponents, game_dates, pbp_report = normalize_pbpstats(pbp_csv)
        insert_possessions(connection, possessions)
        games = build_games(
            nb_games, opponents, game_dates, possessions,
            config["sources"]["pbpstats_2023"]["season_label"],
        )
        insert_games(connection, games)
        feature_rows, feature_report = aggregate_team_features(possessions, games)
        connection.executemany(
            "INSERT INTO team_game_features VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            feature_rows,
        )
        score_report = update_game_score_flags(connection, games, feature_rows)
        metadata = {
            "pipeline_name": "NBA Value Lab historical Silver adapters",
            "follows_current_site_version": "true",
            "season_label": config["sources"]["pbpstats_2023"]["season_label"],
            "pbpstats_archive_sha256": pbp_archive["sha256"],
            "nbastats_archive_sha256": nba_archive["sha256"],
            "raw_archives_committed": "false",
        }
        connection.executemany("INSERT INTO metadata(key,value) VALUES (?,?)", metadata.items())
        connection.commit()
        write_sample(connection, sample_path)
        connection.execute("VACUUM")
        connection.close()

    gzip_file(database, compressed_database)
    database.unlink()

    game_count = len(games)
    score_pass = score_report["score_match_rate"] >= 0.98
    team_inference_pass = pbp_report["team_inference_failures"] == 0
    features_pass = feature_report["team_game_row_count"] >= 2 * int(game_count * 0.98)
    report = {
        "schema_version": "1.0.0",
        "pipeline_name": "NBA Value Lab historical Silver adapters",
        "follows_current_site_version": True,
        "sources": {
            "pbpstats_2023": {**pbp_archive, **pbp_report},
            "nbastats_2023": {**nba_archive, **nb_report},
        },
        "outputs": {
            "database_gzip_bytes": compressed_database.stat().st_size,
            "tables": {
                "games": game_count,
                "pbp_events": nb_report["rows_after_exact_dedupe"],
                "possessions": pbp_report["possession_count"],
                "team_game_features": feature_report["team_game_row_count"],
            },
        },
        "quality": {
            **feature_report,
            **score_report,
            "team_inference_pass": team_inference_pass,
            "score_validation_pass_98pct": score_pass,
            "feature_coverage_pass_98pct": features_pass,
        },
        "decision": {
            "ready_for_private_model_feature_pipeline": team_inference_pass and score_pass and features_pass,
            "raw_data_public_commit_allowed": False,
            "orb_metric_status": "estimated_from_field_goal_misses",
            "tov_metric_status": "estimated_four_factor_denominator",
        },
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def self_test(output_dir):
    with tempfile.TemporaryDirectory(prefix="nbavl-silver-selftest-") as temp:
        root = Path(temp)
        pbp_csv = root / "pbpstats.csv"
        nba_csv = root / "nbastats.csv"
        pbp_csv.write_text(
            "ENDTIME,EVENTS,FG2A,FG2M,FG3A,FG3M,GAMEDATE,GAMEID,NONSHOOTINGFOULSTHATRESULTEDINFTS,OFFENSIVEREBOUNDS,OPPONENT,PERIOD,SHOOTINGFOULSDRAWN,STARTSCOREDIFFERENTIAL,STARTTIME,STARTTYPE,TURNOVERS,DESCRIPTION,URL\n"
            "11:40,A Shot,1,1,0,0,2023-10-01,1,0,0,B,1,0,0,12:00,Start,0,A Shot,\n"
            "11:20,B Shot,1,1,0,0,2023-10-01,1,0,0,A,1,0,-2,11:40,Made,0,B Shot,\n",
            encoding="utf-8",
        )
        nba_csv.write_text(
            "GAME_ID,EVENTNUM,EVENTMSGTYPE,EVENTMSGACTIONTYPE,PERIOD,WCTIMESTRING,PCTIMESTRING,HOMEDESCRIPTION,NEUTRALDESCRIPTION,VISITORDESCRIPTION,SCORE,SCOREMARGIN,PERSON1TYPE,PLAYER1_ID,PLAYER1_NAME,PLAYER1_TEAM_ID,PLAYER1_TEAM_CITY,PLAYER1_TEAM_NICKNAME,PLAYER1_TEAM_ABBREVIATION,PERSON2TYPE,PLAYER2_ID,PLAYER2_NAME,PLAYER2_TEAM_ID,PLAYER2_TEAM_CITY,PLAYER2_TEAM_NICKNAME,PLAYER2_TEAM_ABBREVIATION,PERSON3TYPE,PLAYER3_ID,PLAYER3_NAME,PLAYER3_TEAM_ID,PLAYER3_TEAM_CITY,PLAYER3_TEAM_NICKNAME,PLAYER3_TEAM_ABBREVIATION,VIDEO_AVAILABLE_FLAG\n"
            "1,1,1,1,1,,11:40,A Shot,,,0 - 2,2,,10,A,100,,,A,,,,,,,,,,,,,,,0\n"
            "1,2,1,1,1,,11:20,,,B Shot,2 - 2,0,,20,B,200,,,B,,,,,,,,,,,,,,,0\n",
            encoding="utf-8",
        )
        connection = sqlite3.connect(root / "test.sqlite")
        create_schema(connection)
        nb_games, _ = normalize_nbastats(nba_csv, connection)
        possessions, opponents, dates, pbp_report = normalize_pbpstats(pbp_csv)
        assert pbp_report["team_inference_failures"] == 0
        insert_possessions(connection, possessions)
        games = build_games(nb_games, opponents, dates, possessions, "test")
        insert_games(connection, games)
        features, _ = aggregate_team_features(possessions, games)
        connection.executemany(
            "INSERT INTO team_game_features VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            features,
        )
        connection.commit()
        assert connection.execute("SELECT COUNT(*) FROM games").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM possessions").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM team_game_features").fetchone()[0] == 2
        connection.close()
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "self-test.json").write_text('{"passed":true}\n', encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-download-mb", type=int, default=600)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("historical Silver adapter self-test passed")
        return
    report = build(args.config, args.output_dir, args.max_download_mb)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
