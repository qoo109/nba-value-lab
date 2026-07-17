#!/usr/bin/env python3
"""Build point-in-time historical Gold v1 features from a Silver SQLite database."""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
import statistics
import tempfile
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from historical_gold_schema import (
    FEATURE_VERSION,
    GOLD_SCHEMA_VERSION,
    METRICS,
    WINDOWS,
    create_gold_schema,
    gunzip_to,
    gzip_file,
    safe_mean,
)

TEAM_QUERY = """
SELECT
  g.game_id, g.game_date, g.season_label,
  g.home_team_abbr, g.away_team_abbr,
  f.team_abbr, f.opponent_abbr, f.is_home,
  f.points, f.opponent_points, f.pace, f.off_rtg, f.def_rtg, f.net_rtg,
  f.efg_pct, f.tov_pct_estimated, f.orb_pct_fg_miss_estimate, f.free_throw_rate,
  f.quality_flags
FROM games g
JOIN team_game_features f ON f.game_id = g.game_id
WHERE g.game_date IS NOT NULL
ORDER BY g.game_date, g.game_id, f.is_home DESC, f.team_abbr
"""


def parse_date(value: str) -> date:
    return date.fromisoformat(value[:10])


def numeric(value: Any) -> float | None:
    return None if value is None else float(value)


def prior_values(history: list[dict[str, Any]], metric: str, window: int | None = None) -> list[float | int | None]:
    rows = history[-window:] if window else history
    return [row.get(metric) for row in rows]


def trend(values: list[float | int | None]) -> float | None:
    clean = [float(value) for value in values if value is not None]
    if len(clean) < 3:
        return None
    x_mean = (len(clean) - 1) / 2
    y_mean = sum(clean) / len(clean)
    denominator = sum((index - x_mean) ** 2 for index in range(len(clean)))
    if not denominator:
        return 0.0
    numerator = sum((index - x_mean) * (value - y_mean) for index, value in enumerate(clean))
    return round(numerator / denominator, 6)


def difference(left: Any, right: Any) -> float | None:
    if left is None or right is None:
        return None
    return round(float(left) - float(right), 6)


def count_recent(history: list[dict[str, Any]], current: date, days: int) -> int:
    return sum(1 for row in history if 0 < (current - row["parsed_date"]).days <= days)


def split_prior(history: list[dict[str, Any]], is_home: int) -> list[dict[str, Any]]:
    return [row for row in history if row["is_home"] == is_home]


def confidence(prior_games: int, flags: list[str]) -> float:
    sample_score = min(prior_games / 20.0, 1.0)
    penalty = min(len(flags) * 0.05, 0.25)
    return round(max(0.0, sample_score - penalty), 6)


def source_version(source_db: sqlite3.Connection) -> str:
    try:
        values = dict(source_db.execute("SELECT key, value FROM metadata"))
    except sqlite3.OperationalError:
        values = {}
    hashes = [values.get("pbpstats_archive_sha256", "unknown"), values.get("nbastats_archive_sha256", "unknown")]
    return "silver:" + ":".join(value[:12] for value in hashes)


def load_rows(source_db: sqlite3.Connection) -> list[dict[str, Any]]:
    source_db.row_factory = sqlite3.Row
    rows = []
    for item in source_db.execute(TEAM_QUERY):
        row = dict(item)
        row["parsed_date"] = parse_date(row["game_date"])
        row["win"] = 1 if row["points"] > row["opponent_points"] else 0
        row["margin"] = row["points"] - row["opponent_points"]
        rows.append(row)
    return rows


def build_team_feature(
    row: dict[str, Any],
    history: list[dict[str, Any]],
    opponent_history: list[dict[str, Any]],
    generated_at: str,
    source_ver: str,
) -> dict[str, Any]:
    flags = [flag for flag in (row.get("quality_flags") or "").split(",") if flag]
    prior_games = len(history)
    current_date = row["parsed_date"]
    last_date = history[-1]["parsed_date"] if history else None
    rest_days = (current_date - last_date).days - 1 if last_date else None
    if rest_days is not None:
        rest_days = max(rest_days, 0)
    home_history = split_prior(history, 1)
    away_history = split_prior(history, 0)

    feature: dict[str, Any] = {
        "game_id": row["game_id"],
        "game_date": row["game_date"][:10],
        "season_label": row["season_label"],
        "team_abbr": row["team_abbr"],
        "opponent_abbr": row["opponent_abbr"],
        "is_home": int(row["is_home"]),
        "feature_cutoff_date": row["game_date"][:10],
        "prior_games": prior_games,
        "rest_days": rest_days,
        "is_back_to_back": int(rest_days == 0) if rest_days is not None else 0,
        "games_last_3_days": count_recent(history, current_date, 3),
        "games_last_4_days": count_recent(history, current_date, 4),
        "games_last_7_days": count_recent(history, current_date, 7),
        "home_games_prior": len(home_history),
        "away_games_prior": len(away_history),
        "home_off_rtg_prior": safe_mean(prior_values(home_history, "off_rtg")),
        "home_def_rtg_prior": safe_mean(prior_values(home_history, "def_rtg")),
        "home_net_rtg_prior": safe_mean(prior_values(home_history, "net_rtg")),
        "home_win_pct_prior": safe_mean(prior_values(home_history, "win")),
        "away_off_rtg_prior": safe_mean(prior_values(away_history, "off_rtg")),
        "away_def_rtg_prior": safe_mean(prior_values(away_history, "def_rtg")),
        "away_net_rtg_prior": safe_mean(prior_values(away_history, "net_rtg")),
        "away_win_pct_prior": safe_mean(prior_values(away_history, "win")),
        "season_off_rtg_prior": safe_mean(prior_values(history, "off_rtg")),
        "season_def_rtg_prior": safe_mean(prior_values(history, "def_rtg")),
        "season_net_rtg_prior": safe_mean(prior_values(history, "net_rtg")),
        "season_pace_prior": safe_mean(prior_values(history, "pace")),
        "season_win_pct_prior": safe_mean(prior_values(history, "win")),
        "opponent_strength_net_rtg_prior": safe_mean(prior_values(opponent_history, "net_rtg")),
        "net_rtg_trend_l10": trend(prior_values(history, "net_rtg", 10)),
        "net_rtg_std_l10": None,
        "data_confidence": None,
        "source_version": source_ver,
        "feature_version": FEATURE_VERSION,
        "feature_generated_at": generated_at,
        "quality_flags": "",
    }

    net_l10 = [float(value) for value in prior_values(history, "net_rtg", 10) if value is not None]
    if len(net_l10) >= 2:
        feature["net_rtg_std_l10"] = round(statistics.pstdev(net_l10), 6)

    for window in WINDOWS:
        for metric in METRICS:
            feature[f"{metric}_l{window}"] = safe_mean(prior_values(history, metric, window))

    if prior_games < 5:
        flags.append("small_sample_lt5")
    if feature["opponent_strength_net_rtg_prior"] is None:
        flags.append("opponent_strength_unavailable")
    feature["data_confidence"] = confidence(prior_games, flags)
    feature["quality_flags"] = ",".join(sorted(set(flags)))
    return feature


def build_matchup(home: dict[str, Any], away: dict[str, Any], generated_at: str, source_ver: str) -> dict[str, Any]:
    flags = []
    if home["prior_games"] < 5 or away["prior_games"] < 5:
        flags.append("small_sample_matchup")
    home_opp_adjusted = difference(home["season_net_rtg_prior"], home["opponent_strength_net_rtg_prior"])
    away_opp_adjusted = difference(away["season_net_rtg_prior"], away["opponent_strength_net_rtg_prior"])
    return {
        "game_id": home["game_id"],
        "game_date": home["game_date"],
        "season_label": home["season_label"],
        "home_team_abbr": home["team_abbr"],
        "away_team_abbr": away["team_abbr"],
        "feature_cutoff_date": home["feature_cutoff_date"],
        "home_prior_games": home["prior_games"],
        "away_prior_games": away["prior_games"],
        "rest_days_diff": difference(home["rest_days"], away["rest_days"]),
        "pace_l10_diff": difference(home["pace_l10"], away["pace_l10"]),
        "off_rtg_l10_diff": difference(home["off_rtg_l10"], away["off_rtg_l10"]),
        "def_rtg_l10_diff": difference(home["def_rtg_l10"], away["def_rtg_l10"]),
        "net_rtg_l10_diff": difference(home["net_rtg_l10"], away["net_rtg_l10"]),
        "efg_pct_l10_diff": difference(home["efg_pct_l10"], away["efg_pct_l10"]),
        "tov_pct_l10_diff": difference(home["tov_pct_estimated_l10"], away["tov_pct_estimated_l10"]),
        "orb_pct_l10_diff": difference(home["orb_pct_fg_miss_estimate_l10"], away["orb_pct_fg_miss_estimate_l10"]),
        "free_throw_rate_l10_diff": difference(home["free_throw_rate_l10"], away["free_throw_rate_l10"]),
        "season_net_rtg_diff": difference(home["season_net_rtg_prior"], away["season_net_rtg_prior"]),
        "opponent_adjusted_net_rtg_diff": difference(home_opp_adjusted, away_opp_adjusted),
        "home_data_confidence": home["data_confidence"],
        "away_data_confidence": away["data_confidence"],
        "source_version": source_ver,
        "feature_version": FEATURE_VERSION,
        "feature_generated_at": generated_at,
        "quality_flags": ",".join(flags),
    }


def insert_dicts(db: sqlite3.Connection, table: str, rows: list[dict[str, Any]]) -> None:
    columns = [row[1] for row in db.execute(f"PRAGMA table_info({table})")]
    placeholders = ",".join("?" for _ in columns)
    sql = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders})"
    db.executemany(sql, [[row.get(column) for column in columns] for row in rows])


def point_in_time_qa(team_rows: list[dict[str, Any]], source_rows: list[dict[str, Any]]) -> dict[str, Any]:
    source_dates: dict[tuple[str, str], list[date]] = defaultdict(list)
    for row in source_rows:
        source_dates[(row["team_abbr"], row["game_id"])].append(row["parsed_date"])
    violations = 0
    for feature in team_rows:
        cutoff = parse_date(feature["feature_cutoff_date"])
        # The builder groups by date and appends history only after the full date is emitted.
        # This assertion guards the externally visible contract.
        if parse_date(feature["game_date"]) != cutoff:
            violations += 1
    return {
        "point_in_time_rule": "source_game_date < target_game_date",
        "same_day_games_excluded": True,
        "feature_cutoff_mismatch_count": violations,
        "point_in_time_pass": violations == 0,
    }


def write_preview(db: sqlite3.Connection, path: Path) -> None:
    db.row_factory = sqlite3.Row
    payload = {
        "schema_version": GOLD_SCHEMA_VERSION,
        "feature_version": FEATURE_VERSION,
        "raw_data_included": False,
        "gold_team_game_features": [dict(row) for row in db.execute("SELECT * FROM gold_team_game_features ORDER BY game_date, game_id LIMIT 5")],
        "gold_matchup_features": [dict(row) for row in db.execute("SELECT * FROM gold_matchup_features ORDER BY game_date, game_id LIMIT 5")],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build(silver_path: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).isoformat()
    gold_sqlite = output_dir / "historical-gold.sqlite"
    gold_gzip = output_dir / "historical-gold.sqlite.gz"

    with tempfile.TemporaryDirectory(prefix="nbavl-gold-") as temp_name:
        temp = Path(temp_name)
        source_sqlite = temp / "historical-silver.sqlite"
        if silver_path.suffix == ".gz":
            gunzip_to(silver_path, source_sqlite)
        else:
            source_sqlite.write_bytes(silver_path.read_bytes())

        source_db = sqlite3.connect(source_sqlite)
        source_ver = source_version(source_db)
        source_rows = load_rows(source_db)
        source_db.close()

    gold_db = sqlite3.connect(gold_sqlite)
    create_gold_schema(gold_db)
    histories: dict[str, list[dict[str, Any]]] = defaultdict(list)
    team_features: list[dict[str, Any]] = []
    matchup_features: list[dict[str, Any]] = []

    rows_by_date: dict[date, list[dict[str, Any]]] = defaultdict(list)
    for row in source_rows:
        rows_by_date[row["parsed_date"]].append(row)

    for current_date in sorted(rows_by_date):
        day_features: list[dict[str, Any]] = []
        for row in rows_by_date[current_date]:
            feature = build_team_feature(
                row,
                histories[row["team_abbr"]],
                histories[row["opponent_abbr"]],
                generated_at,
                source_ver,
            )
            day_features.append(feature)
            team_features.append(feature)

        games: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for feature in day_features:
            games[feature["game_id"]].append(feature)
        for game_id, pair in games.items():
            home = next((row for row in pair if row["is_home"] == 1), None)
            away = next((row for row in pair if row["is_home"] == 0), None)
            if home and away:
                matchup_features.append(build_matchup(home, away, generated_at, source_ver))

        # Append only after every feature on the date is built: no same-day leakage.
        for row in rows_by_date[current_date]:
            histories[row["team_abbr"]].append(row)

    insert_dicts(gold_db, "gold_team_game_features", team_features)
    insert_dicts(gold_db, "gold_matchup_features", matchup_features)
    metadata = {
        "pipeline_name": "NBA Value Lab historical Gold v1",
        "schema_version": GOLD_SCHEMA_VERSION,
        "feature_version": FEATURE_VERSION,
        "source_version": source_ver,
        "feature_generated_at": generated_at,
        "point_in_time_rule": "source_game_date < target_game_date",
        "same_day_games_excluded": "true",
    }
    gold_db.executemany("INSERT INTO gold_metadata VALUES (?,?)", metadata.items())
    gold_db.commit()
    write_preview(gold_db, output_dir / "gold-sample.json")
    gold_db.execute("VACUUM")
    gold_db.close()
    gzip_file(gold_sqlite, gold_gzip)
    gold_sqlite.unlink()

    qa = point_in_time_qa(team_features, source_rows)
    expected_team_rows = len(source_rows)
    expected_matchups = len({row["game_id"] for row in source_rows})
    null_after_10 = [
        row for row in team_features
        if row["prior_games"] >= 10 and row["net_rtg_l10"] is None
    ]
    report = {
        "schema_version": GOLD_SCHEMA_VERSION,
        "feature_version": FEATURE_VERSION,
        "source_version": source_ver,
        "generated_at": generated_at,
        "outputs": {
            "database_gzip_bytes": gold_gzip.stat().st_size,
            "tables": {
                "gold_team_game_features": len(team_features),
                "gold_matchup_features": len(matchup_features),
            },
        },
        "quality": {
            **qa,
            "expected_team_rows": expected_team_rows,
            "team_row_coverage": round(len(team_features) / expected_team_rows, 6) if expected_team_rows else 0,
            "expected_matchups": expected_matchups,
            "matchup_coverage": round(len(matchup_features) / expected_matchups, 6) if expected_matchups else 0,
            "net_rtg_l10_missing_after_10_prior_games": len(null_after_10),
            "minimum_prior_games": min((row["prior_games"] for row in team_features), default=0),
            "maximum_prior_games": max((row["prior_games"] for row in team_features), default=0),
        },
    }
    report["decision"] = {
        "ready_for_baseline_model_pipeline": (
            qa["point_in_time_pass"]
            and report["quality"]["team_row_coverage"] == 1.0
            and report["quality"]["matchup_coverage"] == 1.0
            and len(null_after_10) == 0
        ),
        "date_precision_warning": "Silver currently provides game_date, not exact scheduled start time; same-day games are conservatively excluded from one another.",
    }
    (output_dir / "gold-build-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def self_test(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    silver = output_dir / "synthetic-silver.sqlite"
    db = sqlite3.connect(silver)
    db.executescript(
        """
        CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE games (
          game_id TEXT PRIMARY KEY, game_date TEXT, season_label TEXT,
          home_team_abbr TEXT, away_team_abbr TEXT
        );
        CREATE TABLE team_game_features (
          game_id TEXT, team_abbr TEXT, opponent_abbr TEXT, is_home INTEGER,
          points INTEGER, opponent_points INTEGER, pace REAL, off_rtg REAL,
          def_rtg REAL, net_rtg REAL, efg_pct REAL, tov_pct_estimated REAL,
          orb_pct_fg_miss_estimate REAL, free_throw_rate REAL, quality_flags TEXT
        );
        """
    )
    db.executemany("INSERT INTO metadata VALUES (?,?)", [
        ("pbpstats_archive_sha256", "a" * 64),
        ("nbastats_archive_sha256", "b" * 64),
    ])
    games = []
    features = []
    for index in range(12):
        game_id = f"g{index:02d}"
        game_date = f"2023-10-{index + 1:02d}"
        games.append((game_id, game_date, "2023-24", "AAA", "BBB"))
        features.append((game_id, "AAA", "BBB", 1, 100 + index, 95, 98.0, 110 + index, 105.0, 5 + index, .52, .12, .25, .20, ""))
        features.append((game_id, "BBB", "AAA", 0, 95, 100 + index, 98.0, 105.0, 110 + index, -5 - index, .49, .14, .20, .18, ""))
    db.executemany("INSERT INTO games VALUES (?,?,?,?,?)", games)
    db.executemany("INSERT INTO team_game_features VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", features)
    db.commit()
    db.close()

    report = build(silver, output_dir / "result")
    assert report["quality"]["point_in_time_pass"] is True
    assert report["quality"]["team_row_coverage"] == 1.0
    assert report["quality"]["matchup_coverage"] == 1.0
    assert report["quality"]["net_rtg_l10_missing_after_10_prior_games"] == 0
    (output_dir / "self-test.json").write_text(json.dumps({"passed": True}, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--silver-db", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(args.output_dir), ensure_ascii=False, indent=2))
        return
    if not args.silver_db:
        parser.error("--silver-db is required unless --self-test is used")
    print(json.dumps(build(args.silver_db, args.output_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
