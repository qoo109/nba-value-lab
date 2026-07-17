#!/usr/bin/env python3
"""Build point-in-time historical Gold features from a Silver SQLite database."""

from __future__ import annotations

import argparse
import gzip
import json
import shutil
import sqlite3
import statistics
import tempfile
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from historical_gold_schema import (
    BASE_METRICS,
    GOLD_FEATURE_VERSION,
    GOLD_SCHEMA_VERSION,
    ROLLING_WINDOWS,
    create_gold_schema,
    stable_id,
)


def mean(values: Iterable[float | int | None]) -> float | None:
    clean = [float(value) for value in values if value is not None]
    return round(sum(clean) / len(clean), 6) if clean else None


def stddev(values: Iterable[float | int | None]) -> float | None:
    clean = [float(value) for value in values if value is not None]
    return round(statistics.pstdev(clean), 6) if len(clean) >= 2 else None


def parse_date(value: str) -> date:
    text = value.strip()[:10]
    return date.fromisoformat(text)


def load_silver(source: Path, working_dir: Path) -> Path:
    if source.suffix != ".gz":
        return source
    target = working_dir / "historical-silver.sqlite"
    with gzip.open(source, "rb") as src, target.open("wb") as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)
    return target


def row_metric(row: dict[str, Any], metric: str) -> float | int | None:
    if metric == "margin":
        return row["points"] - row["opponent_points"]
    if metric == "win":
        return int(row["points"] > row["opponent_points"])
    return row.get(metric)


def average_metric(rows: list[dict[str, Any]], metric: str) -> float | None:
    return mean(row_metric(row, metric) for row in rows)


def rolling_payload(prior: list[dict[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for window in ROLLING_WINDOWS:
        selected = prior[-window:]
        for metric in BASE_METRICS:
            output[f"{metric}_last_{window}"] = average_metric(selected, metric)
        output[f"net_rtg_std_last_{window}"] = stddev(row_metric(row, "net_rtg") for row in selected)
        output[f"sample_size_last_{window}"] = len(selected)
    return output


def venue_payload(prior: list[dict[str, Any]], is_home: int) -> dict[str, Any]:
    selected = [row for row in prior if row["is_home"] == is_home]
    prefix = "home" if is_home else "away"
    return {
        f"prior_{prefix}_games": len(selected),
        f"{prefix}_off_rtg_prior": average_metric(selected, "off_rtg"),
        f"{prefix}_def_rtg_prior": average_metric(selected, "def_rtg"),
        f"{prefix}_net_rtg_prior": average_metric(selected, "net_rtg"),
        f"{prefix}_win_rate_prior": average_metric(selected, "win"),
    }


def schedule_payload(prior: list[dict[str, Any]], game_day: date) -> dict[str, Any]:
    if not prior:
        return {
            "days_rest": None,
            "is_back_to_back": 0,
            "games_last_3_days": 0,
            "games_last_7_days": 0,
        }
    previous_day = parse_date(prior[-1]["game_date"])
    gap = (game_day - previous_day).days
    return {
        "days_rest": max(gap - 1, 0),
        "is_back_to_back": int(gap == 1),
        "games_last_3_days": sum(0 < (game_day - parse_date(row["game_date"])).days <= 3 for row in prior),
        "games_last_7_days": sum(0 < (game_day - parse_date(row["game_date"])).days <= 7 for row in prior),
    }


def source_version(db: sqlite3.Connection) -> str:
    metadata = dict(db.execute("SELECT key, value FROM metadata"))
    parts = [
        metadata.get("pbpstats_archive_sha256", "unknown"),
        metadata.get("nbastats_archive_sha256", "unknown"),
        metadata.get("rating_points_source", "unknown"),
    ]
    return stable_id(*parts)


def load_rows(db: sqlite3.Connection) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    db.row_factory = sqlite3.Row
    games = {
        row["game_id"]: dict(row)
        for row in db.execute(
            "SELECT game_id, game_date, season_label, home_team_abbr, away_team_abbr FROM games"
        )
        if row["game_date"] and row["home_team_abbr"] and row["away_team_abbr"]
    }
    rows = []
    for row in db.execute("SELECT * FROM team_game_features"):
        item = dict(row)
        game = games.get(item["game_id"])
        if not game:
            continue
        item.update(
            game_date=game["game_date"],
            season_label=game["season_label"],
            home_team_abbr=game["home_team_abbr"],
            away_team_abbr=game["away_team_abbr"],
        )
        rows.append(item)
    rows.sort(key=lambda row: (parse_date(row["game_date"]), row["game_id"], row["team_abbr"]))
    return rows, games


def build_team_features(
    rows: list[dict[str, Any]], generated_at: str, source_ver: str
) -> list[dict[str, Any]]:
    history: dict[str, list[dict[str, Any]]] = defaultdict(list)
    opponent_history: dict[str, list[dict[str, Any]]] = defaultdict(list)
    output = []

    grouped: dict[date, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[parse_date(row["game_date"])].append(row)

    for game_day in sorted(grouped):
        day_rows = grouped[game_day]
        for row in day_rows:
            team = row["team_abbr"]
            opponent = row["opponent_abbr"]
            prior = history[team]
            opp_prior = opponent_history[opponent]
            rolling = rolling_payload(prior)
            home = venue_payload(prior, 1)
            away = venue_payload(prior, 0)
            schedule = schedule_payload(prior, game_day)
            opponent_strength = average_metric(opp_prior[-10:], "net_rtg")
            own_net_10 = rolling["net_rtg_last_10"]
            adjusted = None if own_net_10 is None or opponent_strength is None else round(own_net_10 - opponent_strength, 6)
            trend = None
            if rolling["net_rtg_last_5"] is not None and rolling["net_rtg_last_10"] is not None:
                trend = round(rolling["net_rtg_last_5"] - rolling["net_rtg_last_10"], 6)
            flags = []
            if len(prior) < 5:
                flags.append("insufficient_prior_games_5")
            if len(prior) < 10:
                flags.append("insufficient_prior_games_10")
            if len(prior) < 20:
                flags.append("insufficient_prior_games_20")
            if opponent_strength is None:
                flags.append("opponent_strength_unavailable")

            output.append({
                "feature_id": stable_id(GOLD_FEATURE_VERSION, row["game_id"], team),
                "game_id": row["game_id"],
                "game_date": row["game_date"],
                "season_label": row["season_label"],
                "team_abbr": team,
                "opponent_abbr": opponent,
                "is_home": int(row["is_home"]),
                "feature_cutoff_time": f"{game_day.isoformat()}T00:00:00Z",
                "prior_games": len(prior),
                "prior_home_games": home.pop("prior_home_games"),
                "prior_away_games": away.pop("prior_away_games"),
                **schedule,
                **home,
                **away,
                "opponent_strength_net_rtg_last_10": opponent_strength,
                "opponent_adjusted_net_rtg_last_10": adjusted,
                "trend_net_rtg_last_5_vs_10": trend,
                **rolling,
                "source_version": source_ver,
                "feature_version": GOLD_FEATURE_VERSION,
                "feature_generated_at": generated_at,
                "quality_flags": ",".join(flags),
            })

        # Strict date boundary: games on the same date never become features for one another.
        for row in day_rows:
            history[row["team_abbr"]].append(row)
            opponent_history[row["team_abbr"]].append(row)
    return output


def insert_dicts(db: sqlite3.Connection, table: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    columns = list(rows[0])
    placeholders = ",".join("?" for _ in columns)
    sql = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})"
    db.executemany(sql, ([row[column] for column in columns] for row in rows))


def difference(home: dict[str, Any], away: dict[str, Any], key: str) -> float | None:
    if home.get(key) is None or away.get(key) is None:
        return None
    return round(float(home[key]) - float(away[key]), 6)


def build_matchups(team_rows: list[dict[str, Any]], games: dict[str, dict[str, Any]], generated_at: str, source_ver: str) -> list[dict[str, Any]]:
    by_game: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in team_rows:
        by_game[row["game_id"]].append(row)
    output = []
    for game_id, sides in sorted(by_game.items()):
        if len(sides) != 2:
            continue
        home = next((row for row in sides if row["is_home"] == 1), None)
        away = next((row for row in sides if row["is_home"] == 0), None)
        if not home or not away:
            continue
        coverage = min(home["prior_games"], away["prior_games"], 20) / 20
        flags = []
        if coverage < 0.25:
            flags.append("low_evidence_coverage")
        output.append({
            "matchup_feature_id": stable_id(GOLD_FEATURE_VERSION, game_id, "matchup"),
            "game_id": game_id,
            "game_date": home["game_date"],
            "home_team_abbr": home["team_abbr"],
            "away_team_abbr": away["team_abbr"],
            "home_feature_id": home["feature_id"],
            "away_feature_id": away["feature_id"],
            "net_rtg_last_5_diff": difference(home, away, "net_rtg_last_5"),
            "net_rtg_last_10_diff": difference(home, away, "net_rtg_last_10"),
            "net_rtg_last_20_diff": difference(home, away, "net_rtg_last_20"),
            "pace_last_10_diff": difference(home, away, "pace_last_10"),
            "efg_pct_last_10_diff": difference(home, away, "efg_pct_last_10"),
            "tov_pct_last_10_diff": difference(home, away, "tov_pct_estimated_last_10"),
            "orb_pct_last_10_diff": difference(home, away, "orb_pct_fg_miss_estimate_last_10"),
            "free_throw_rate_last_10_diff": difference(home, away, "free_throw_rate_last_10"),
            "rest_days_diff": difference(home, away, "days_rest"),
            "prior_games_min": min(home["prior_games"], away["prior_games"]),
            "evidence_coverage": round(coverage, 6),
            "source_version": source_ver,
            "feature_version": GOLD_FEATURE_VERSION,
            "feature_generated_at": generated_at,
            "quality_flags": ",".join(flags),
        })
    return output


def validate_point_in_time(team_rows: list[dict[str, Any]], silver_rows: list[dict[str, Any]]) -> dict[str, Any]:
    dates_by_team: dict[str, list[date]] = defaultdict(list)
    for row in silver_rows:
        dates_by_team[row["team_abbr"]].append(parse_date(row["game_date"]))
    violations = []
    for row in team_rows:
        cutoff = parse_date(row["game_date"])
        expected = sum(game_day < cutoff for game_day in dates_by_team[row["team_abbr"]])
        if expected != row["prior_games"]:
            violations.append({
                "game_id": row["game_id"],
                "team_abbr": row["team_abbr"],
                "expected_prior_games": expected,
                "actual_prior_games": row["prior_games"],
            })
    return {
        "strict_prior_date_rule": True,
        "violations": len(violations),
        "examples": violations[:10],
        "passed": not violations,
    }


def write_preview(db: sqlite3.Connection, path: Path) -> None:
    db.row_factory = sqlite3.Row
    payload = {
        "schema_version": GOLD_SCHEMA_VERSION,
        "feature_version": GOLD_FEATURE_VERSION,
        "raw_data_included": False,
        "gold_team_game_features": [dict(row) for row in db.execute("SELECT * FROM gold_team_game_features WHERE prior_games >= 20 LIMIT 5")],
        "gold_matchup_features": [dict(row) for row in db.execute("SELECT * FROM gold_matchup_features WHERE prior_games_min >= 20 LIMIT 5")],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build(source: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    with tempfile.TemporaryDirectory(prefix="nbavl-gold-") as temp_name:
        temp = Path(temp_name)
        silver_path = load_silver(source, temp)
        silver = sqlite3.connect(silver_path)
        source_ver = source_version(silver)
        silver_rows, games = load_rows(silver)

        gold_path = output_dir / "historical-gold.sqlite"
        gold = sqlite3.connect(gold_path)
        create_gold_schema(gold)
        team_rows = build_team_features(silver_rows, generated_at, source_ver)
        matchup_rows = build_matchups(team_rows, games, generated_at, source_ver)
        insert_dicts(gold, "gold_team_game_features", team_rows)
        insert_dicts(gold, "gold_matchup_features", matchup_rows)
        gold.executemany("INSERT INTO gold_metadata VALUES (?,?)", {
            "pipeline_name": "NBA Value Lab historical Gold layer",
            "schema_version": GOLD_SCHEMA_VERSION,
            "feature_version": GOLD_FEATURE_VERSION,
            "source_version": source_ver,
            "feature_generated_at": generated_at,
            "point_in_time_rule": "strict_game_date_less_than_target_game_date",
            "same_day_games_policy": "excluded_from_each_other",
        }.items())
        gold.commit()
        point_in_time = validate_point_in_time(team_rows, silver_rows)
        write_preview(gold, output_dir / "gold-sample.json")
        gold.execute("VACUUM")
        gold.close()
        silver.close()

    gzip_path = output_dir / "historical-gold.sqlite.gz"
    with gold_path.open("rb") as src, gzip.open(gzip_path, "wb", compresslevel=6) as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)
    gold_path.unlink()

    mature_team_rows = sum(row["prior_games"] >= 20 for row in team_rows)
    mature_matchups = sum(row["prior_games_min"] >= 20 for row in matchup_rows)
    report = {
        "schema_version": GOLD_SCHEMA_VERSION,
        "feature_version": GOLD_FEATURE_VERSION,
        "pipeline_name": "NBA Value Lab historical Gold layer",
        "source_version": source_ver,
        "feature_generated_at": generated_at,
        "outputs": {
            "database_gzip_bytes": gzip_path.stat().st_size,
            "tables": {
                "gold_team_game_features": len(team_rows),
                "gold_matchup_features": len(matchup_rows),
            },
        },
        "coverage": {
            "team_rows_prior_5": sum(row["prior_games"] >= 5 for row in team_rows),
            "team_rows_prior_10": sum(row["prior_games"] >= 10 for row in team_rows),
            "team_rows_prior_20": mature_team_rows,
            "matchups_prior_20_both_sides": mature_matchups,
        },
        "quality": {
            "point_in_time": point_in_time,
            "duplicate_team_game_rows": len(team_rows) - len({(row["game_id"], row["team_abbr"]) for row in team_rows}),
            "duplicate_matchup_rows": len(matchup_rows) - len({row["game_id"] for row in matchup_rows}),
            "same_day_games_excluded": True,
        },
        "decision": {
            "ready_for_baseline_model_pilot": point_in_time["passed"] and len(matchup_rows) >= 1200 and mature_matchups > 0,
            "cross_season_training_ready": False,
            "reason": "Gold v1 is a single-season point-in-time feature dataset; add prior seasons before final model training.",
        },
    }
    (output_dir / "gold-build-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def self_test(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    silver_path = output_dir / "synthetic-silver.sqlite"
    db = sqlite3.connect(silver_path)
    db.executescript("""
        CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE games (game_id TEXT PRIMARY KEY, game_date TEXT, season_label TEXT, home_team_abbr TEXT, away_team_abbr TEXT);
        CREATE TABLE team_game_features (
          game_id TEXT, team_abbr TEXT, opponent_abbr TEXT, is_home INTEGER,
          points INTEGER, opponent_points INTEGER, pace REAL, off_rtg REAL,
          def_rtg REAL, net_rtg REAL, efg_pct REAL, tov_pct_estimated REAL,
          orb_pct_fg_miss_estimate REAL, free_throw_rate REAL
        );
    """)
    db.executemany("INSERT INTO metadata VALUES (?,?)", [
        ("pbpstats_archive_sha256", "pbp"),
        ("nbastats_archive_sha256", "nba"),
        ("rating_points_source", "official"),
    ])
    for index in range(1, 23):
        game_id = f"g{index:02d}"
        game_date = f"2023-10-{index:02d}"
        db.execute("INSERT INTO games VALUES (?,?,?,?,?)", (game_id, game_date, "2023-24", "AAA", "BBB"))
        db.executemany("INSERT INTO team_game_features VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", [
            (game_id, "AAA", "BBB", 1, 100 + index, 90 + index, 99.0, 110.0, 100.0, 10.0, .55, .12, .25, .22),
            (game_id, "BBB", "AAA", 0, 90 + index, 100 + index, 99.0, 100.0, 110.0, -10.0, .50, .15, .20, .18),
        ])
    db.commit()
    db.close()
    result = build(silver_path, output_dir / "gold")
    assert result["quality"]["point_in_time"]["passed"]
    assert result["outputs"]["tables"]["gold_team_game_features"] == 44
    assert result["outputs"]["tables"]["gold_matchup_features"] == 22
    assert result["coverage"]["matchups_prior_20_both_sides"] == 2
    (output_dir / "self-test.json").write_text('{"passed":true}\n', encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--silver-db", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("historical Gold builder self-test passed")
        return
    if not args.silver_db:
        parser.error("--silver-db is required unless --self-test is used")
    print(json.dumps(build(args.silver_db, args.output_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
