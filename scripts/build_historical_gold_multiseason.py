#!/usr/bin/env python3
"""Build season-aware point-in-time Gold features from combined Silver data."""

from __future__ import annotations

import argparse
import gzip
import json
import shutil
import sqlite3
import tempfile
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from build_historical_gold import (
    average_metric,
    build_matchups,
    insert_dicts,
    load_rows,
    load_silver,
    parse_date,
    rolling_payload,
    schedule_payload,
    venue_payload,
    write_preview,
)
from historical_gold_schema import GOLD_FEATURE_VERSION, GOLD_SCHEMA_VERSION, create_gold_schema, stable_id
from historical_silver_schema import create_schema


def source_version(db: sqlite3.Connection) -> str:
    metadata = dict(db.execute("SELECT key, value FROM metadata"))
    if metadata.get("source_manifest_sha256"):
        return metadata["source_manifest_sha256"]
    return stable_id(
        metadata.get("pbpstats_archive_sha256", "unknown"),
        metadata.get("nbastats_archive_sha256", "unknown"),
        metadata.get("rating_points_source", "unknown"),
    )


def build_team_features(
    rows: list[dict[str, Any]], generated_at: str, source_ver: str
) -> list[dict[str, Any]]:
    # Rolling, venue and schedule histories reset at each season boundary. This
    # prevents April performance from becoming an October L5/L10 observation.
    history: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    output: list[dict[str, Any]] = []
    grouped: dict[tuple[str, date], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["season_label"]), parse_date(row["game_date"]))].append(row)

    for season_label, game_day in sorted(grouped, key=lambda item: (item[1], item[0])):
        day_rows = grouped[(season_label, game_day)]
        for row in day_rows:
            team = str(row["team_abbr"])
            opponent = str(row["opponent_abbr"])
            prior = history[(season_label, team)]
            opp_prior = history[(season_label, opponent)]
            rolling = rolling_payload(prior)
            home = venue_payload(prior, 1)
            away = venue_payload(prior, 0)
            schedule = schedule_payload(prior, game_day)
            opponent_strength = average_metric(opp_prior[-10:], "net_rtg")
            own_net_10 = rolling["net_rtg_last_10"]
            adjusted = None
            if own_net_10 is not None and opponent_strength is not None:
                adjusted = round(float(own_net_10) - float(opponent_strength), 6)
            trend = None
            if rolling["net_rtg_last_5"] is not None and rolling["net_rtg_last_10"] is not None:
                trend = round(float(rolling["net_rtg_last_5"]) - float(rolling["net_rtg_last_10"]), 6)

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
                "season_label": season_label,
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

        # Strict date boundary inside each season: same-day games never enter
        # one another's features.
        for row in day_rows:
            history[(season_label, str(row["team_abbr"]))].append(row)
    return output


def validate_point_in_time(
    team_rows: list[dict[str, Any]], silver_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    dates: dict[tuple[str, str], list[date]] = defaultdict(list)
    for row in silver_rows:
        dates[(str(row["season_label"]), str(row["team_abbr"]))].append(parse_date(row["game_date"]))
    violations = []
    for row in team_rows:
        key = (str(row["season_label"]), str(row["team_abbr"]))
        cutoff = parse_date(row["game_date"])
        expected = sum(game_day < cutoff for game_day in dates[key])
        if expected != int(row["prior_games"]):
            violations.append({
                "game_id": row["game_id"],
                "season_label": row["season_label"],
                "team_abbr": row["team_abbr"],
                "expected_prior_games": expected,
                "actual_prior_games": row["prior_games"],
            })
    return {
        "strict_prior_date_rule": True,
        "season_history_reset": True,
        "violations": len(violations),
        "examples": violations[:10],
        "passed": not violations,
    }


def build(source: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    with tempfile.TemporaryDirectory(prefix="nbavl-gold-multiseason-") as temp_name:
        temp = Path(temp_name)
        silver_path = load_silver(source, temp)
        silver = sqlite3.connect(silver_path)
        source_ver = source_version(silver)
        silver_rows, games = load_rows(silver)
        seasons = sorted({str(row["season_label"]) for row in silver_rows})

        gold_path = output_dir / "historical-gold-multiseason.sqlite"
        if gold_path.exists():
            gold_path.unlink()
        gold = sqlite3.connect(gold_path)
        create_gold_schema(gold)
        team_rows = build_team_features(silver_rows, generated_at, source_ver)
        matchup_rows = build_matchups(team_rows, games, generated_at, source_ver)
        insert_dicts(gold, "gold_team_game_features", team_rows)
        insert_dicts(gold, "gold_matchup_features", matchup_rows)
        gold.executemany("INSERT INTO gold_metadata VALUES (?,?)", {
            "pipeline_name": "NBA Value Lab historical Gold multi-season",
            "schema_version": GOLD_SCHEMA_VERSION,
            "feature_version": GOLD_FEATURE_VERSION,
            "source_version": source_ver,
            "feature_generated_at": generated_at,
            "point_in_time_rule": "same_season_source_game_date_less_than_target_game_date",
            "same_day_games_policy": "excluded_from_each_other",
            "season_history_policy": "rolling_features_reset_each_season",
            "season_labels": ",".join(seasons),
        }.items())
        gold.commit()
        point_in_time = validate_point_in_time(team_rows, silver_rows)
        write_preview(gold, output_dir / "multiseason-gold-sample.json")
        gold.execute("VACUUM")
        gold.close()
        silver.close()

    gzip_path = output_dir / "historical-gold-multiseason.sqlite.gz"
    with gold_path.open("rb") as src, gzip.open(gzip_path, "wb", compresslevel=6) as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)
    gold_path.unlink()

    duplicate_team_rows = len(team_rows) - len({(row["game_id"], row["team_abbr"]) for row in team_rows})
    duplicate_matchups = len(matchup_rows) - len({row["game_id"] for row in matchup_rows})
    season_matchup_counts = {
        season: sum(row["season_label"] == season for row in team_rows if row["is_home"] == 1)
        for season in seasons
    }
    mature_matchups = sum(row["prior_games_min"] >= 20 for row in matchup_rows)
    report = {
        "schema_version": GOLD_SCHEMA_VERSION,
        "feature_version": GOLD_FEATURE_VERSION,
        "pipeline_name": "NBA Value Lab historical Gold multi-season",
        "source_version": source_ver,
        "feature_generated_at": generated_at,
        "seasons": seasons,
        "season_matchup_counts": season_matchup_counts,
        "season_history_policy": "rolling_features_reset_each_season",
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
            "team_rows_prior_20": sum(row["prior_games"] >= 20 for row in team_rows),
            "matchups_prior_20_both_sides": mature_matchups,
        },
        "quality": {
            "point_in_time": point_in_time,
            "duplicate_team_game_rows": duplicate_team_rows,
            "duplicate_matchup_rows": duplicate_matchups,
            "same_day_games_excluded": True,
            "season_boundary_reset_verified": point_in_time["passed"],
        },
        "decision": {
            "ready_for_walk_forward_model": (
                len(seasons) >= 3
                and len(matchup_rows) >= 3000
                and mature_matchups > 0
                and point_in_time["passed"]
                and duplicate_team_rows == 0
                and duplicate_matchups == 0
            ),
            "cross_season_training_ready": len(seasons) >= 3 and point_in_time["passed"],
            "odds_backtest_ready": False,
        },
    }
    (output_dir / "multiseason-gold-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def build_fixture(path: Path) -> None:
    db = sqlite3.connect(path)
    create_schema(db)
    db.execute("INSERT INTO metadata VALUES (?,?)", ("source_manifest_sha256", "fixture-manifest"))
    for season_start in (2021, 2022, 2023):
        season = f"{season_start}-{str(season_start + 1)[-2:]}"
        for index in range(1, 23):
            game_id = f"{season_start}-g{index:02d}"
            game_date = f"{season_start}-10-{index:02d}"
            db.execute(
                "INSERT INTO games VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (game_id, game_date, season, "1", "AAA", "2", "BBB", 100 + index, 90 + index, 4, 48.0, 0, 180, None, ""),
            )
            rows = [
                (game_id, "AAA", "BBB", 1, 100 + index, 90 + index, 100 + index, 90 + index, 90, 90, 96.0, 112.0, 102.0, 10.0, 80, 40, 30, 12, 20, 15, 8, 10, .575, .10, .20, .25, 1, ""),
                (game_id, "BBB", "AAA", 0, 90 + index, 100 + index, 90 + index, 100 + index, 90, 90, 96.0, 102.0, 112.0, -10.0, 82, 39, 31, 11, 18, 14, 7, 11, .543, .11, .18, .22, 1, ""),
            ]
            db.executemany("INSERT INTO team_game_features VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    db.commit()
    db.close()


def self_test(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    silver_path = output_dir / "synthetic-multiseason-silver.sqlite"
    build_fixture(silver_path)
    report = build(silver_path, output_dir / "result")
    assert report["quality"]["point_in_time"]["passed"] is True
    assert report["outputs"]["tables"]["gold_team_game_features"] == 132
    assert report["outputs"]["tables"]["gold_matchup_features"] == 66
    assert report["coverage"]["matchups_prior_20_both_sides"] == 6
    assert report["decision"]["cross_season_training_ready"] is True
    with gzip.open(output_dir / "result" / "historical-gold-multiseason.sqlite.gz", "rb") as src:
        with tempfile.NamedTemporaryFile(suffix=".sqlite") as temp:
            temp.write(src.read())
            temp.flush()
            db = sqlite3.connect(temp.name)
            first_games = list(db.execute(
                "SELECT season_label, prior_games FROM gold_team_game_features WHERE team_abbr='AAA' AND game_id LIKE '%-g01' ORDER BY season_label"
            ))
            db.close()
    assert first_games == [("2021-22", 0), ("2022-23", 0), ("2023-24", 0)]
    (output_dir / "self-test.json").write_text('{"passed":true}\n', encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--silver-db", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("multi-season Gold builder self-test passed")
        return
    if not args.silver_db:
        parser.error("--silver-db is required unless --self-test is used")
    report = build(args.silver_db, args.output_dir)
    print(json.dumps(report["decision"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
