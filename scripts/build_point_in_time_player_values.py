#!/usr/bin/env python3
"""Build strict point-in-time expected-minutes and player-impact estimates.

Inputs may contain public player names, but outputs are ID-only and exclude names and injury
reasons. Every source boxscore must be strictly earlier than the target game date.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "point-in-time-player-value-v1"
OFFICIAL_GAME_RE = re.compile(r"^official:(\d{4}-\d{2}-\d{2}):[A-Z]{3}@[A-Z]{3}$")


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
        return result if math.isfinite(result) else default
    except (TypeError, ValueError):
        return default


def parse_date(value: Any) -> date:
    text = str(value or "").strip()
    for pattern in ("%Y-%m-%d", "%m/%d/%Y", "%b %d, %Y"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    raise ValueError(f"unsupported game date: {value!r}")


def target_date(snapshot: dict[str, str]) -> date:
    match = OFFICIAL_GAME_RE.fullmatch(str(snapshot.get("game_id", "")))
    if match:
        return date.fromisoformat(match.group(1))
    commence = str(snapshot.get("commence_time", "")).replace("Z", "+00:00")
    if commence:
        return datetime.fromisoformat(commence).date()
    raise ValueError("snapshot has no usable target date")


def box_contribution(row: dict[str, str]) -> float:
    pts = as_float(row.get("PTS"))
    fgm = as_float(row.get("FGM"))
    fga = as_float(row.get("FGA"))
    ftm = as_float(row.get("FTM"))
    fta = as_float(row.get("FTA"))
    oreb = as_float(row.get("OREB"))
    dreb = as_float(row.get("DREB"))
    ast = as_float(row.get("AST"))
    tov = as_float(row.get("TOV"))
    stl = as_float(row.get("STL"))
    blk = as_float(row.get("BLK"))
    pf = as_float(row.get("PF"))
    return (
        pts + 0.4 * fgm - 0.7 * fga - 0.4 * (fta - ftm)
        + 0.7 * oreb + 0.3 * dreb + stl + 0.7 * ast + 0.7 * blk
        - 0.4 * pf - tov
    )


def per36(value: float, minutes: float) -> float:
    return 36.0 * value / max(minutes, 1.0)


def mean(values: list[float]) -> float | None:
    return statistics.fmean(values) if values else None


def stdev(values: list[float]) -> float | None:
    return statistics.pstdev(values) if len(values) >= 2 else None


def weighted_expected_minutes(current: list[dict], all_prior: list[dict]) -> tuple[float | None, str]:
    if current:
        recent5 = mean([row["minutes"] for row in current[-5:]])
        recent10 = mean([row["minutes"] for row in current[-10:]])
        season = mean([row["minutes"] for row in current])
        if len(current) >= 5:
            value = 0.5 * recent5 + 0.3 * recent10 + 0.2 * season
            return min(max(value, 0.0), 48.0), "current_season_stabilized"
        older = [row for row in all_prior if row["season"] != current[-1]["season"]]
        carry = mean([row["minutes"] for row in older[-10:]])
        if carry is None:
            return min(max(season, 0.0), 48.0), "current_season_small_sample"
        value = 0.6 * season + 0.4 * carry
        return min(max(value, 0.0), 48.0), "current_plus_prior_season"
    carry = mean([row["minutes"] for row in all_prior[-10:]])
    if carry is None:
        return None, "no_prior_games"
    return min(max(carry, 0.0), 48.0), "prior_season_carryover"


def z_score(value: float | None, population: list[float]) -> float:
    if value is None or len(population) < 20:
        return 0.0
    center = mean(population)
    spread = stdev(population)
    if center is None or spread is None or spread < 1e-9:
        return 0.0
    return (value - center) / spread


def prepare_logs(rows: list[dict[str, str]]) -> tuple[list[dict], dict[str, list[dict]]]:
    prepared = []
    by_player: dict[str, list[dict]] = defaultdict(list)
    for raw in rows:
        minutes = as_float(raw.get("MIN"))
        if minutes <= 0:
            continue
        item = {
            "player_id": str(raw.get("PLAYER_ID", "")).strip(),
            "game_id": str(raw.get("GAME_ID", "")).strip(),
            "game_date": parse_date(raw.get("GAME_DATE")),
            "season": str(raw.get("SEASON_YEAR", "")).strip(),
            "minutes": minutes,
            "box_per36": per36(box_contribution(raw), minutes),
            "plus_minus_per36": per36(as_float(raw.get("PLUS_MINUS")), minutes),
            "starter": int(as_float(raw.get("STARTER")) > 0),
        }
        if not item["player_id"]:
            continue
        prepared.append(item)
        by_player[item["player_id"]].append(item)
    prepared.sort(key=lambda row: (row["game_date"], row["game_id"], row["player_id"]))
    for values in by_player.values():
        values.sort(key=lambda row: (row["game_date"], row["game_id"]))
    return prepared, by_player


def build(
    player_logs: list[dict[str, str]],
    snapshots: list[dict[str, str]],
    player_map: list[dict[str, str]],
    output_dir: Path,
) -> dict[str, Any]:
    prepared, by_player = prepare_logs(player_logs)
    snapshots_by_id = {str(row.get("snapshot_record_id", "")): row for row in snapshots}
    outputs = []
    missing_snapshots = 0
    missing_player_ids = 0
    no_prior_history = 0
    strict_violations = 0
    same_day_rows_excluded = 0
    future_rows_excluded = 0
    league_cache: dict[date, tuple[list[float], list[float]]] = {}

    for identity in player_map:
        snapshot_id = str(identity.get("snapshot_record_id", ""))
        snapshot = snapshots_by_id.get(snapshot_id)
        if snapshot is None:
            missing_snapshots += 1
            continue
        player_id = str(identity.get("player_id", "")).strip()
        if not player_id:
            missing_player_ids += 1
            continue
        game_date = target_date(snapshot)
        season = str(identity.get("season_label", ""))
        player_rows = by_player.get(player_id, [])
        prior = [row for row in player_rows if row["game_date"] < game_date]
        same_day_rows_excluded += sum(row["game_date"] == game_date for row in player_rows)
        future_rows_excluded += sum(row["game_date"] > game_date for row in player_rows)
        if any(row["game_date"] >= game_date for row in prior):
            strict_violations += 1
        if not prior:
            no_prior_history += 1
        current = [row for row in prior if row["season"] == season]
        expected_minutes, minutes_method = weighted_expected_minutes(current, prior)
        recent = prior[-10:]
        player_box = mean([row["box_per36"] for row in recent])
        player_pm = mean([row["plus_minus_per36"] for row in recent])
        if game_date not in league_cache:
            league_prior = [row for row in prepared if row["game_date"] < game_date]
            league_cache[game_date] = (
                [row["box_per36"] for row in league_prior],
                [row["plus_minus_per36"] for row in league_prior],
            )
        league_box, league_pm = league_cache[game_date]
        raw_impact = z_score(player_box, league_box) + 0.25 * z_score(player_pm, league_pm)
        shrink = len(recent) / (len(recent) + 8.0) if recent else 0.0
        impact = min(max(raw_impact * shrink, -3.0), 3.0)
        latest_date = prior[-1]["game_date"].isoformat() if prior else ""
        latest_id = prior[-1]["game_id"] if prior else ""
        outputs.append({
            "snapshot_record_id": snapshot_id,
            "historical_game_id": str(identity.get("historical_game_id", "")),
            "season_label": season,
            "team_abbr": str(identity.get("team_abbr", "")),
            "player_id": player_id,
            "availability_status": str(snapshot.get("availability_status", "")),
            "target_game_date": game_date.isoformat(),
            "observed_at": str(snapshot.get("observed_at", "")),
            "expected_minutes": "" if expected_minutes is None else round(expected_minutes, 6),
            "expected_minutes_method": minutes_method,
            "prior_games": len(prior),
            "current_season_prior_games": len(current),
            "recent_value_sample": len(recent),
            "player_impact_estimate": round(impact, 6),
            "latest_source_game_date": latest_date,
            "latest_source_game_id": latest_id,
            "player_value_asof": str(snapshot.get("observed_at", "")),
            "feature_version": VERSION,
        })

    output_dir.mkdir(parents=True, exist_ok=True)
    fields = [
        "snapshot_record_id", "historical_game_id", "season_label", "team_abbr", "player_id",
        "availability_status", "target_game_date", "observed_at", "expected_minutes",
        "expected_minutes_method", "prior_games", "current_season_prior_games",
        "recent_value_sample", "player_impact_estimate", "latest_source_game_date",
        "latest_source_game_id", "player_value_asof", "feature_version",
    ]
    with (output_dir / "point-in-time-player-values.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(outputs)

    mapped_rows = len(player_map)
    feature_rows = len(outputs)
    expected_minutes_rows = sum(str(row["expected_minutes"]) != "" for row in outputs)
    coverage = expected_minutes_rows / mapped_rows if mapped_rows else 0.0
    ready = (
        mapped_rows > 0
        and missing_snapshots == 0
        and strict_violations == 0
        and coverage >= 0.95
        and no_prior_history <= max(2, int(mapped_rows * 0.05))
    )
    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "coverage": {
            "player_log_rows": len(prepared),
            "snapshot_rows": len(snapshots),
            "player_id_map_rows": mapped_rows,
            "feature_rows": feature_rows,
            "expected_minutes_rows": expected_minutes_rows,
            "expected_minutes_coverage": round(coverage, 6),
            "target_dates": sorted({row["target_game_date"] for row in outputs}),
        },
        "quality": {
            "missing_snapshot_rows": missing_snapshots,
            "missing_player_id_rows": missing_player_ids,
            "players_without_prior_history": no_prior_history,
            "strict_prior_date_violations": strict_violations,
            "same_day_source_rows_excluded": same_day_rows_excluded,
            "future_source_rows_excluded": future_rows_excluded,
            "output_contains_player_names": False,
            "output_contains_injury_reasons": False,
        },
        "decision": {
            "ready_for_injury_snapshot_feature_join": ready,
            "ready_for_model_training": False,
            "ready_for_betting_edge_claim": False,
            "reason": "One-report prior-only feature pilot; multi-report and holdout validation remain required.",
        },
        "guardrails": {
            "source_game_date_strictly_before_target_date": True,
            "same_day_rows_allowed": False,
            "future_rows_allowed": False,
            "target_game_boxscore_used": False,
            "player_value_asof_equals_snapshot_observed_at": True,
            "transparent_box_score_proxy_not_official_metric": True,
        },
    }
    (output_dir / "point-in-time-player-value-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def self_test(output_dir: Path) -> None:
    logs = []
    for day, minutes, points in ((1, 20, 10), (2, 24, 12), (3, 28, 14), (4, 32, 16), (5, 36, 18)):
        logs.append({
            "SEASON_YEAR": "2023-24", "PLAYER_ID": "p1", "GAME_ID": f"g{day}",
            "GAME_DATE": f"2023-12-{day:02d}", "MIN": str(minutes), "PTS": str(points),
            "FGM": "5", "FGA": "10", "FTM": "2", "FTA": "2", "OREB": "1",
            "DREB": "4", "AST": "5", "TOV": "2", "STL": "1", "BLK": "1",
            "PF": "2", "PLUS_MINUS": "3", "STARTER": "1",
        })
    logs.append({**logs[-1], "GAME_ID": "target", "GAME_DATE": "2023-12-10", "MIN": "48"})
    snapshots = [{
        "snapshot_record_id": "s1", "game_id": "official:2023-12-10:LAL@DEN",
        "commence_time": "2023-12-11T02:00:00Z", "observed_at": "2023-12-10T15:00:00Z",
        "availability_status": "QUESTIONABLE",
    }]
    identities = [{
        "snapshot_record_id": "s1", "historical_game_id": "22300100",
        "season_label": "2023-24", "team_abbr": "DEN", "player_id": "p1",
    }]
    report = build(logs, snapshots, identities, output_dir)
    assert report["quality"]["strict_prior_date_violations"] == 0, report
    assert report["quality"]["same_day_source_rows_excluded"] == 1, report
    assert report["decision"]["ready_for_injury_snapshot_feature_join"] is True, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--player-logs", type=Path)
    parser.add_argument("--snapshot-csv", type=Path)
    parser.add_argument("--player-id-map", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("point-in-time player value builder self-test passed")
        return
    if not args.player_logs or not args.snapshot_csv or not args.player_id_map:
        parser.error("--player-logs, --snapshot-csv and --player-id-map are required")
    report = build(
        read_csv(args.player_logs),
        read_csv(args.snapshot_csv),
        read_csv(args.player_id_map),
        args.output_dir,
    )
    print(json.dumps(report["decision"], indent=2))
    if not report["decision"]["ready_for_injury_snapshot_feature_join"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
