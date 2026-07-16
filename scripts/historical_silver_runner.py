#!/usr/bin/env python3
"""Orchestrate the full historical Silver SQLite build."""

from __future__ import annotations

import argparse
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
CONFIG = ROOT / "config" / "historical-source-pilot.json"
FEATURE_INSERT = "INSERT INTO team_game_features VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"


def prepare_source(key, source, root, max_mb):
    archive = root / f"{key}.tar.xz"
    extracted = root / f"{key}-raw"
    extracted.mkdir()
    info = download(source["url"], archive, max_mb * 1048576)
    info["member_count"] = extract(archive, extracted)
    csv_path = select_csv(extracted, source)
    info["csv_name"] = csv_path.name
    info["csv_bytes"] = csv_path.stat().st_size
    return csv_path, info


def game_minutes(periods):
    return 48.0 + max(periods - 4, 0) * 5.0


def make_games(nb_games, opponents, dates, possessions, season):
    possession_counts = Counter(row["game_id"] for row in possessions)
    periods = Counter()
    for row in possessions:
        periods[row["game_id"]] = max(periods[row["game_id"]], row["period"])
    output = {}
    for game_id in sorted(set(nb_games) | set(opponents)):
        nba = nb_games.get(game_id, {})
        home = nba.get("home_team_abbr")
        away = nba.get("away_team_abbr")
        flags = []
        if not home or not away:
            flags.append("home_away_team_unresolved")
        if opponents.get(game_id) and {home, away} != set(opponents[game_id]):
            flags.append("source_team_set_mismatch")
        max_period = nba.get("max_period") or periods.get(game_id, 4)
        output[game_id] = {
            "game_id": game_id,
            "game_date": dates.get(game_id),
            "season_label": season,
            "home_team_id": nba.get("home_team_id"),
            "home_team_abbr": home,
            "away_team_id": nba.get("away_team_id"),
            "away_team_abbr": away,
            "home_score": nba.get("home_score"),
            "away_score": nba.get("away_score"),
            "max_period": max_period,
            "game_minutes": game_minutes(max_period),
            "pbp_event_count": nba.get("event_count", 0),
            "possession_count": possession_counts.get(game_id, 0),
            "score_match": None,
            "quality_flags": flags,
        }
    return output


def insert_games(db, games):
    db.executemany(
        "INSERT INTO games VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [(
            row["game_id"], row["game_date"], row["season_label"],
            row["home_team_id"], row["home_team_abbr"],
            row["away_team_id"], row["away_team_abbr"],
            row["home_score"], row["away_score"], row["max_period"],
            row["game_minutes"], row["pbp_event_count"], row["possession_count"],
            row["score_match"], ",".join(row["quality_flags"]),
        ) for row in games.values()],
    )


def update_reconstruction_flags(db, games, feature_rows):
    matches = {}
    for row in feature_rows:
        matches.setdefault(row[0], []).append(row[26])
    matched = mismatched = unknown = 0
    updates = []
    for game_id, game in games.items():
        values = matches.get(game_id, [])
        if len(values) == 2 and all(value == 1 for value in values):
            value = 1
            matched += 1
        elif any(value == 0 for value in values):
            value = 0
            mismatched += 1
            game["quality_flags"].append("possession_score_reconstruction_mismatch")
        else:
            value = None
            unknown += 1
        updates.append((value, ",".join(game["quality_flags"]), game_id))
    db.executemany("UPDATE games SET score_match=?, quality_flags=? WHERE game_id=?", updates)
    known = matched + mismatched
    return {
        "reconstruction_matched_games": matched,
        "reconstruction_mismatched_games": mismatched,
        "reconstruction_unknown_games": unknown,
        "reconstruction_match_rate": round(matched / known, 6) if known else 0,
    }


def write_sample(db, path):
    db.row_factory = sqlite3.Row
    payload = {"schema_version": "0.2.0-silver", "raw_data_included": False, "tables": {}}
    for table in ("games", "pbp_events", "possessions", "team_game_features"):
        payload["tables"][table] = [dict(row) for row in db.execute(f"SELECT * FROM {table} LIMIT 5")]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build(config_path, output_dir, max_mb):
    config = json.loads(config_path.read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True, exist_ok=True)
    sqlite_path = output_dir / "historical-silver.sqlite"
    gzip_path = output_dir / "historical-silver.sqlite.gz"

    with tempfile.TemporaryDirectory(prefix="nbavl-silver-") as temp:
        temp = Path(temp)
        pbp_csv, pbp_source = prepare_source(
            "pbpstats_2023", config["sources"]["pbpstats_2023"], temp, max_mb
        )
        nba_csv, nba_source = prepare_source(
            "nbastats_2023", config["sources"]["nbastats_2023"], temp, max_mb
        )
        db = sqlite3.connect(sqlite_path)
        create_schema(db)
        nb_games, nb_report = normalize_nbastats(nba_csv, db)
        possessions, opponents, dates, pbp_report = normalize_pbpstats(pbp_csv)
        insert_possessions(db, possessions)
        games = make_games(
            nb_games, opponents, dates, possessions,
            config["sources"]["pbpstats_2023"]["season_label"],
        )
        insert_games(db, games)
        features, feature_report = aggregate_team_features(possessions, games)
        db.executemany(FEATURE_INSERT, features)
        reconstruction = update_reconstruction_flags(db, games, features)
        metadata = {
            "pipeline_name": "NBA Value Lab historical Silver adapters",
            "follows_current_site_version": "true",
            "rating_points_source": "nbastats_official_final_score",
            "possession_points_usage": "qa_only",
            "pbpstats_archive_sha256": pbp_source["sha256"],
            "nbastats_archive_sha256": nba_source["sha256"],
            "raw_archives_committed": "false",
        }
        db.executemany("INSERT INTO metadata VALUES (?,?)", metadata.items())
        db.commit()
        write_sample(db, output_dir / "silver-sample.json")
        db.execute("VACUUM")
        db.close()

    gzip_file(sqlite_path, gzip_path)
    sqlite_path.unlink()

    game_count = len(games)
    inference_pass = pbp_report["team_inference_failures"] == 0
    official_pass = feature_report["official_score_coverage_rate"] >= 0.98
    feature_pass = feature_report["team_game_row_count"] >= 2 * int(game_count * 0.98)
    report = {
        "schema_version": "1.1.0",
        "pipeline_name": "NBA Value Lab historical Silver adapters",
        "follows_current_site_version": True,
        "sources": {
            "pbpstats_2023": {**pbp_source, **pbp_report},
            "nbastats_2023": {**nba_source, **nb_report},
        },
        "outputs": {
            "database_gzip_bytes": gzip_path.stat().st_size,
            "tables": {
                "games": game_count,
                "pbp_events": nb_report["rows_after_exact_dedupe"],
                "possessions": pbp_report["possession_count"],
                "team_game_features": feature_report["team_game_row_count"],
            },
        },
        "quality": {
            **feature_report,
            **reconstruction,
            "team_inference_pass": inference_pass,
            "official_score_coverage_pass_98pct": official_pass,
            "feature_coverage_pass_98pct": feature_pass,
        },
        "decision": {
            "ready_for_private_model_feature_pipeline": inference_pass and official_pass and feature_pass,
            "rating_points_source": "nbastats_official_final_score",
            "possession_points_status": "qa_only_not_used_for_ratings",
            "raw_data_public_commit_allowed": False,
            "orb_metric_status": "estimated_from_field_goal_misses",
            "tov_metric_status": "estimated_four_factor_denominator",
        },
    }
    (output_dir / "silver-build-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def self_test(output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(output_dir / "self-test.sqlite")
    create_schema(db)
    names = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"games", "pbp_events", "possessions", "team_game_features"} <= names
    db.close()
    (output_dir / "self-test.json").write_text('{"passed":true}\n', encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-download-mb", type=int, default=600)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("historical Silver runner self-test passed")
        return
    print(json.dumps(build(args.config, args.output_dir, args.max_download_mb), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
