#!/usr/bin/env python3
"""Aggregate point-in-time player availability values into team and matchup injury features.

Unknown team snapshots and unknown player values remain explicit missing data. The script never
interprets a missing report or missing estimate as zero burden.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "team-injury-burden-v1"
STATUS_WEIGHTS = {
    "AVAILABLE": 0.0,
    "PROBABLE": 0.10,
    "QUESTIONABLE": 0.50,
    "DOUBTFUL": 0.75,
    "OUT": 1.0,
    "INACTIVE": 1.0,
    "SUSPENDED": 1.0,
}
STATUS_ORDER = (
    "AVAILABLE", "PROBABLE", "QUESTIONABLE", "DOUBTFUL", "OUT", "INACTIVE", "SUSPENDED"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def as_float(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError as exc:
        raise ValueError(f"numeric field is invalid: {value!r}") from exc


def as_int(value: Any, default: int = 0) -> int:
    number = as_float(value)
    return default if number is None else int(number)


def parse_date(value: Any) -> date:
    return date.fromisoformat(str(value or "").strip())


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def burden_zeroes() -> dict[str, float]:
    return {
        "definite_out_minutes": 0.0,
        "doubtful_minutes": 0.0,
        "questionable_minutes": 0.0,
        "probable_minutes": 0.0,
        "weighted_unavailable_minutes": 0.0,
        "weighted_absence_impact_signed": 0.0,
        "weighted_absence_impact_positive": 0.0,
        "weighted_absence_impact_absolute": 0.0,
    }


def aggregate(
    values: list[dict[str, str]],
    identity_rows: list[dict[str, str]],
    game_rows: list[dict[str, str]],
    output_dir: Path,
) -> dict[str, Any]:
    game_index: dict[str, dict[str, str]] = {}
    duplicate_game_maps = 0
    for row in game_rows:
        if str(row.get("matched", "")).lower() not in {"1", "true"}:
            continue
        game_id = str(row.get("historical_game_id", "")).strip()
        if not game_id:
            continue
        item = {
            "historical_game_id": game_id,
            "game_date": str(row.get("game_date", "")).strip(),
            "home_team_abbr": str(row.get("home_team_abbr", "")).strip(),
            "away_team_abbr": str(row.get("away_team_abbr", "")).strip(),
        }
        if game_id in game_index and game_index[game_id] != item:
            duplicate_game_maps += 1
        game_index[game_id] = item

    identity_counts: Counter[tuple[str, str]] = Counter()
    identity_snapshot_ids: set[str] = set()
    duplicate_identity_snapshots = 0
    for row in identity_rows:
        snapshot_id = str(row.get("snapshot_record_id", "")).strip()
        if snapshot_id in identity_snapshot_ids:
            duplicate_identity_snapshots += 1
        identity_snapshot_ids.add(snapshot_id)
        game_id = str(row.get("historical_game_id", "")).strip()
        team = str(row.get("team_abbr", "")).strip()
        if game_id and team:
            identity_counts[(game_id, team)] += 1

    grouped_values: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    value_snapshot_ids: set[str] = set()
    duplicate_value_snapshots = 0
    strict_prior_violations = 0
    unknown_status_rows = 0
    for row in values:
        snapshot_id = str(row.get("snapshot_record_id", "")).strip()
        if snapshot_id in value_snapshot_ids:
            duplicate_value_snapshots += 1
        value_snapshot_ids.add(snapshot_id)
        game_id = str(row.get("historical_game_id", "")).strip()
        team = str(row.get("team_abbr", "")).strip()
        status = str(row.get("availability_status", "")).strip().upper()
        if status not in STATUS_WEIGHTS:
            unknown_status_rows += 1
        latest = str(row.get("latest_source_game_date", "")).strip()
        target = str(row.get("target_game_date", "")).strip()
        if latest and target and parse_date(latest) >= parse_date(target):
            strict_prior_violations += 1
        if game_id and team:
            grouped_values[(game_id, team)].append(row)

    team_rows: list[dict[str, Any]] = []
    numeric_errors = 0
    all_status_counts: Counter[str] = Counter()
    expected_team_keys = []
    for game in game_index.values():
        for side, team in (("HOME", game["home_team_abbr"]), ("AWAY", game["away_team_abbr"])):
            expected_team_keys.append((game["historical_game_id"], team, side))

    for game_id, team, side in expected_team_keys:
        game = game_index[game_id]
        rows = grouped_values.get((game_id, team), [])
        identity_count = identity_counts[(game_id, team)]
        snapshot_available = int(identity_count > 0)
        status_counts: Counter[str] = Counter()
        burden = burden_zeroes()
        known_minutes = 0
        known_impact = 0
        observed_values = set()
        target_dates = set()
        missing_minutes = 0
        missing_impact = 0
        try:
            for row in rows:
                status = str(row.get("availability_status", "")).strip().upper()
                status_counts[status] += 1
                all_status_counts[status] += 1
                observed = str(row.get("observed_at", "")).strip()
                target_date = str(row.get("target_game_date", "")).strip()
                if observed:
                    observed_values.add(observed)
                if target_date:
                    target_dates.add(target_date)
                expected_minutes = as_float(row.get("expected_minutes"))
                impact = as_float(row.get("player_impact_estimate"))
                if expected_minutes is None:
                    missing_minutes += 1
                else:
                    known_minutes += 1
                    if status in {"OUT", "INACTIVE", "SUSPENDED"}:
                        burden["definite_out_minutes"] += expected_minutes
                    elif status == "DOUBTFUL":
                        burden["doubtful_minutes"] += expected_minutes
                    elif status == "QUESTIONABLE":
                        burden["questionable_minutes"] += expected_minutes
                    elif status == "PROBABLE":
                        burden["probable_minutes"] += expected_minutes
                    if status in STATUS_WEIGHTS:
                        burden["weighted_unavailable_minutes"] += (
                            STATUS_WEIGHTS[status] * expected_minutes
                        )
                if impact is None or expected_minutes is None:
                    missing_impact += 1
                else:
                    known_impact += 1
                    weight = STATUS_WEIGHTS.get(status)
                    if weight is not None:
                        scaled = weight * (expected_minutes / 36.0) * impact
                        burden["weighted_absence_impact_signed"] += scaled
                        burden["weighted_absence_impact_positive"] += max(scaled, 0.0)
                        burden["weighted_absence_impact_absolute"] += abs(scaled)
        except ValueError:
            numeric_errors += 1

        listed_players = identity_count
        value_rows = len(rows)
        missing_identity_rows = max(listed_players - value_rows, 0)
        minutes_coverage = known_minutes / listed_players if listed_players else 0.0
        impact_coverage = known_impact / listed_players if listed_players else 0.0
        feature_available = int(snapshot_available == 1 and minutes_coverage >= 0.75)
        row = {
            "historical_game_id": game_id,
            "game_date": game["game_date"],
            "team_abbr": team,
            "opponent_abbr": (
                game["away_team_abbr"] if side == "HOME" else game["home_team_abbr"]
            ),
            "is_home": int(side == "HOME"),
            "team_snapshot_available": snapshot_available,
            "team_feature_available": feature_available,
            "listed_player_rows": listed_players,
            "player_value_rows": value_rows,
            "missing_player_identity_rows": missing_identity_rows,
            "known_expected_minutes_rows": known_minutes,
            "missing_expected_minutes_rows": missing_minutes,
            "expected_minutes_coverage": round(minutes_coverage, 6),
            "known_impact_rows": known_impact,
            "missing_impact_rows": missing_impact,
            "impact_coverage": round(impact_coverage, 6),
            "observed_at": next(iter(observed_values)) if len(observed_values) == 1 else "",
            "target_game_date": next(iter(target_dates)) if len(target_dates) == 1 else game["game_date"],
            "feature_version": VERSION,
        }
        for status in STATUS_ORDER:
            row[f"{status.lower()}_player_count"] = status_counts[status]
        for key, value in burden.items():
            row[key] = round(value, 6) if snapshot_available else ""
        team_rows.append(row)

    team_index = {
        (row["historical_game_id"], row["team_abbr"]): row
        for row in team_rows
    }
    matchup_rows: list[dict[str, Any]] = []
    complete_matchups = 0
    feature_ready_matchups = 0
    for game_id, game in sorted(game_index.items(), key=lambda item: (item[1]["game_date"], item[0])):
        home = team_index[(game_id, game["home_team_abbr"])]
        away = team_index[(game_id, game["away_team_abbr"])]
        snapshot_complete = int(
            home["team_snapshot_available"] == 1 and away["team_snapshot_available"] == 1
        )
        feature_ready = int(
            home["team_feature_available"] == 1 and away["team_feature_available"] == 1
        )
        complete_matchups += snapshot_complete
        feature_ready_matchups += feature_ready
        row = {
            "historical_game_id": game_id,
            "game_date": game["game_date"],
            "home_team_abbr": game["home_team_abbr"],
            "away_team_abbr": game["away_team_abbr"],
            "matchup_snapshot_complete": snapshot_complete,
            "matchup_feature_available": feature_ready,
            "home_expected_minutes_coverage": home["expected_minutes_coverage"],
            "away_expected_minutes_coverage": away["expected_minutes_coverage"],
            "minimum_expected_minutes_coverage": min(
                home["expected_minutes_coverage"], away["expected_minutes_coverage"]
            ),
            "home_impact_coverage": home["impact_coverage"],
            "away_impact_coverage": away["impact_coverage"],
            "minimum_impact_coverage": min(home["impact_coverage"], away["impact_coverage"]),
            "feature_version": VERSION,
        }
        for feature in burden_zeroes():
            row[f"home_{feature}"] = home[feature] if snapshot_complete else ""
            row[f"away_{feature}"] = away[feature] if snapshot_complete else ""
            row[f"{feature}_home_minus_away"] = (
                round(float(home[feature]) - float(away[feature]), 6)
                if snapshot_complete
                else ""
            )
        matchup_rows.append(row)

    output_dir.mkdir(parents=True, exist_ok=True)
    team_fields = list(team_rows[0]) if team_rows else []
    matchup_fields = list(matchup_rows[0]) if matchup_rows else []
    write_csv(output_dir / "team-injury-burden.csv", team_rows, team_fields)
    write_csv(output_dir / "matchup-injury-burden.csv", matchup_rows, matchup_fields)

    total_matchups = len(matchup_rows)
    complete_rate = complete_matchups / total_matchups if total_matchups else 0.0
    feature_ready_rate = feature_ready_matchups / total_matchups if total_matchups else 0.0
    snapshot_team_rows = sum(row["team_snapshot_available"] for row in team_rows)
    feature_team_rows = sum(row["team_feature_available"] for row in team_rows)
    ready = (
        total_matchups >= 8
        and duplicate_game_maps == 0
        and duplicate_identity_snapshots == 0
        and duplicate_value_snapshots == 0
        and strict_prior_violations == 0
        and unknown_status_rows == 0
        and numeric_errors == 0
        and complete_rate >= 0.80
        and feature_ready_rate >= 0.70
    )
    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "status_weights": STATUS_WEIGHTS,
        "coverage": {
            "games": len(game_index),
            "team_rows": len(team_rows),
            "teams_with_snapshot_rows": snapshot_team_rows,
            "teams_with_feature_ready_values": feature_team_rows,
            "matchup_rows": total_matchups,
            "complete_snapshot_matchups": complete_matchups,
            "complete_snapshot_matchup_rate": round(complete_rate, 6),
            "feature_ready_matchups": feature_ready_matchups,
            "feature_ready_matchup_rate": round(feature_ready_rate, 6),
            "identity_snapshot_rows": len(identity_rows),
            "player_value_rows": len(values),
            "status_counts": dict(sorted(all_status_counts.items())),
        },
        "quality": {
            "duplicate_game_map_rows": duplicate_game_maps,
            "duplicate_identity_snapshot_rows": duplicate_identity_snapshots,
            "duplicate_player_value_snapshot_rows": duplicate_value_snapshots,
            "strict_prior_date_violations": strict_prior_violations,
            "unknown_status_rows": unknown_status_rows,
            "numeric_errors": numeric_errors,
            "team_snapshot_missing_rows": len(team_rows) - snapshot_team_rows,
            "team_feature_unavailable_rows": len(team_rows) - feature_team_rows,
            "missing_teams_are_not_treated_as_zero_burden": True,
            "unknown_player_values_are_not_imputed_as_zero": True,
        },
        "decision": {
            "ready_for_team_injury_feature_experiment": ready,
            "ready_for_model_training": False,
            "ready_for_betting_edge_claim": False,
            "reason": (
                "Single-report team aggregation pilot only; multi-report coverage and season "
                "holdout evaluation remain required."
            ),
        },
        "guardrails": {
            "player_level_names_or_reasons_in_outputs": False,
            "matchup_differences_are_home_burden_minus_away_burden": True,
            "positive_burden_difference_is_a_home_disadvantage": True,
            "status_weights_are_research_assumptions": True,
            "status_specific_unweighted_buckets_retained": True,
            "strict_prior_validation_rechecked": True,
        },
    }
    (output_dir / "team-injury-burden-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def self_test(output_dir: Path) -> None:
    values = [
        {
            "snapshot_record_id": "s1", "historical_game_id": "g1", "team_abbr": "AAA",
            "availability_status": "OUT", "expected_minutes": "30",
            "player_impact_estimate": "1.2", "observed_at": "2023-01-01T10:00:00Z",
            "target_game_date": "2023-01-02", "latest_source_game_date": "2022-12-31",
        },
        {
            "snapshot_record_id": "s2", "historical_game_id": "g1", "team_abbr": "BBB",
            "availability_status": "QUESTIONABLE", "expected_minutes": "20",
            "player_impact_estimate": "0.5", "observed_at": "2023-01-01T10:00:00Z",
            "target_game_date": "2023-01-02", "latest_source_game_date": "2022-12-30",
        },
    ]
    identities = [
        {"snapshot_record_id": "s1", "historical_game_id": "g1", "team_abbr": "AAA"},
        {"snapshot_record_id": "s2", "historical_game_id": "g1", "team_abbr": "BBB"},
    ]
    games = [
        {
            "historical_game_id": "g1", "game_date": "2023-01-02",
            "home_team_abbr": "AAA", "away_team_abbr": "BBB", "matched": "True",
        }
    ]
    report = aggregate(values, identities, games, output_dir)
    assert report["quality"]["strict_prior_date_violations"] == 0, report
    assert report["coverage"]["complete_snapshot_matchups"] == 1, report
    assert report["decision"]["ready_for_team_injury_feature_experiment"] is False, report
    matchup = read_csv(output_dir / "matchup-injury-burden.csv")[0]
    assert float(matchup["weighted_unavailable_minutes_home_minus_away"]) == 20.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--player-values", type=Path)
    parser.add_argument("--player-id-map", type=Path)
    parser.add_argument("--game-map", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("team injury burden self-test passed")
        return
    if not args.player_values or not args.player_id_map or not args.game_map:
        parser.error("--player-values, --player-id-map and --game-map are required")
    report = aggregate(
        read_csv(args.player_values),
        read_csv(args.player_id_map),
        read_csv(args.game_map),
        args.output_dir,
    )
    print(json.dumps(report["decision"], indent=2))
    if not report["decision"]["ready_for_team_injury_feature_experiment"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
