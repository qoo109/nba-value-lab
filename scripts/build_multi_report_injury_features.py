#!/usr/bin/env python3
"""Build long-form team and matchup injury features for multiple publication times.

Every `(historical_game_id, observed_at)` remains a distinct snapshot row. Multiple
snapshots from one game are never counted as independent games. Missing team snapshots
and unknown player values remain explicit missing data rather than zero burden.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "multi-report-injury-feature-long-v1"
STATUS_WEIGHTS = {
    "AVAILABLE": 0.0,
    "PROBABLE": 0.10,
    "QUESTIONABLE": 0.50,
    "DOUBTFUL": 0.75,
    "OUT": 1.0,
    "INACTIVE": 1.0,
    "SUSPENDED": 1.0,
}
STATUS_ORDER = tuple(STATUS_WEIGHTS)
BURDEN_FIELDS = (
    "definite_out_minutes",
    "doubtful_minutes",
    "questionable_minutes",
    "probable_minutes",
    "weighted_unavailable_minutes",
    "weighted_absence_impact_signed",
    "weighted_absence_impact_positive",
    "weighted_absence_impact_absolute",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def parse_timestamp(value: Any) -> datetime:
    text = str(value or "").strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"timestamp must include timezone: {value!r}")
    return parsed.astimezone(timezone.utc)


def as_float(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    number = float(text)
    if number != number or number in {float("inf"), float("-inf")}:
        raise ValueError(f"numeric field is not finite: {value!r}")
    return number


def burden_zeroes() -> dict[str, float]:
    return {field: 0.0 for field in BURDEN_FIELDS}


def build(
    snapshots: list[dict[str, str]],
    values: list[dict[str, str]],
    identity_rows: list[dict[str, str]],
    game_rows: list[dict[str, str]],
    output_dir: Path,
) -> dict[str, Any]:
    snapshot_index: dict[str, dict[str, str]] = {}
    duplicate_snapshot_rows = 0
    for row in snapshots:
        snapshot_id = str(row.get("snapshot_record_id", "")).strip()
        if not snapshot_id:
            continue
        if snapshot_id in snapshot_index:
            duplicate_snapshot_rows += 1
        snapshot_index[snapshot_id] = row

    game_index: dict[str, dict[str, str]] = {}
    duplicate_game_maps = 0
    for row in game_rows:
        if str(row.get("matched", "")).strip().lower() not in {"1", "true"}:
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

    identity_counts: Counter[tuple[str, str, str]] = Counter()
    identity_snapshot_ids: set[str] = set()
    duplicate_identity_snapshots = 0
    missing_identity_snapshot_refs = 0
    observation_commence: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in identity_rows:
        snapshot_id = str(row.get("snapshot_record_id", "")).strip()
        if snapshot_id in identity_snapshot_ids:
            duplicate_identity_snapshots += 1
        identity_snapshot_ids.add(snapshot_id)
        snapshot = snapshot_index.get(snapshot_id)
        if snapshot is None:
            missing_identity_snapshot_refs += 1
            continue
        game_id = str(row.get("historical_game_id", "")).strip()
        team = str(row.get("team_abbr", "")).strip()
        observed_at = str(snapshot.get("observed_at", "")).strip()
        commence_time = str(snapshot.get("commence_time", "")).strip()
        if game_id and team and observed_at:
            identity_counts[(game_id, observed_at, team)] += 1
            if commence_time:
                observation_commence[(game_id, observed_at)].add(commence_time)

    grouped_values: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    value_snapshot_ids: set[str] = set()
    duplicate_value_snapshots = 0
    missing_value_snapshot_refs = 0
    strict_prior_violations = 0
    unknown_status_rows = 0
    for row in values:
        snapshot_id = str(row.get("snapshot_record_id", "")).strip()
        if snapshot_id in value_snapshot_ids:
            duplicate_value_snapshots += 1
        value_snapshot_ids.add(snapshot_id)
        snapshot = snapshot_index.get(snapshot_id)
        if snapshot is None:
            missing_value_snapshot_refs += 1
            continue
        game_id = str(row.get("historical_game_id", "")).strip()
        team = str(row.get("team_abbr", "")).strip()
        observed_at = str(snapshot.get("observed_at", "")).strip()
        status = str(row.get("availability_status", "")).strip().upper()
        if status not in STATUS_WEIGHTS:
            unknown_status_rows += 1
        latest = str(row.get("latest_source_game_date", "")).strip()
        target = str(row.get("target_game_date", "")).strip()
        if latest and target and latest >= target:
            strict_prior_violations += 1
        if game_id and team and observed_at:
            grouped_values[(game_id, observed_at, team)].append(row)

    observation_keys = sorted(
        {(game_id, observed_at) for game_id, observed_at, _team in identity_counts},
        key=lambda item: (game_index.get(item[0], {}).get("game_date", ""), item[0], item[1]),
    )
    team_rows: list[dict[str, Any]] = []
    matchup_rows: list[dict[str, Any]] = []
    numeric_errors = 0
    missing_commence_times = 0
    multiple_commence_times = 0
    non_pregame_observations = 0
    all_status_counts: Counter[str] = Counter()

    for game_id, observed_at in observation_keys:
        game = game_index.get(game_id)
        if game is None:
            continue
        commence_values = observation_commence.get((game_id, observed_at), set())
        commence_time = next(iter(commence_values)) if len(commence_values) == 1 else ""
        if not commence_values:
            missing_commence_times += 1
        elif len(commence_values) > 1:
            multiple_commence_times += 1
        minutes_before_tip: float | None = None
        if commence_time:
            try:
                minutes_before_tip = (
                    parse_timestamp(commence_time) - parse_timestamp(observed_at)
                ).total_seconds() / 60.0
                if minutes_before_tip <= 0:
                    non_pregame_observations += 1
            except ValueError:
                numeric_errors += 1

        per_team: dict[str, dict[str, Any]] = {}
        for side, team in (("HOME", game["home_team_abbr"]), ("AWAY", game["away_team_abbr"])):
            key = (game_id, observed_at, team)
            rows = grouped_values.get(key, [])
            listed_players = identity_counts[key]
            snapshot_available = int(listed_players > 0)
            status_counts: Counter[str] = Counter()
            burden = burden_zeroes()
            known_minutes = known_impact = missing_minutes = missing_impact = 0
            try:
                for row in rows:
                    status = str(row.get("availability_status", "")).strip().upper()
                    status_counts[status] += 1
                    all_status_counts[status] += 1
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
                            burden["weighted_unavailable_minutes"] += STATUS_WEIGHTS[status] * expected_minutes
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

            value_rows = len(rows)
            minutes_coverage = known_minutes / listed_players if listed_players else 0.0
            impact_coverage = known_impact / listed_players if listed_players else 0.0
            feature_available = int(snapshot_available == 1 and minutes_coverage >= 0.75)
            team_row: dict[str, Any] = {
                "historical_game_id": game_id,
                "game_date": game["game_date"],
                "observed_at": observed_at,
                "commence_time": commence_time,
                "minutes_before_tip": "" if minutes_before_tip is None else round(minutes_before_tip, 3),
                "team_abbr": team,
                "opponent_abbr": game["away_team_abbr"] if side == "HOME" else game["home_team_abbr"],
                "is_home": int(side == "HOME"),
                "team_snapshot_available": snapshot_available,
                "team_feature_available": feature_available,
                "listed_player_rows": listed_players,
                "player_value_rows": value_rows,
                "missing_player_identity_rows": max(listed_players - value_rows, 0),
                "known_expected_minutes_rows": known_minutes,
                "missing_expected_minutes_rows": missing_minutes,
                "expected_minutes_coverage": round(minutes_coverage, 6),
                "known_impact_rows": known_impact,
                "missing_impact_rows": missing_impact,
                "impact_coverage": round(impact_coverage, 6),
                "feature_version": VERSION,
            }
            for status in STATUS_ORDER:
                team_row[f"{status.lower()}_player_count"] = status_counts[status]
            for field, value in burden.items():
                team_row[field] = round(value, 6) if snapshot_available else ""
            team_rows.append(team_row)
            per_team[side] = team_row

        home, away = per_team["HOME"], per_team["AWAY"]
        snapshot_complete = int(home["team_snapshot_available"] == 1 and away["team_snapshot_available"] == 1)
        feature_ready = int(home["team_feature_available"] == 1 and away["team_feature_available"] == 1)
        matchup: dict[str, Any] = {
            "historical_game_id": game_id,
            "game_date": game["game_date"],
            "observed_at": observed_at,
            "commence_time": commence_time,
            "minutes_before_tip": "" if minutes_before_tip is None else round(minutes_before_tip, 3),
            "home_team_abbr": game["home_team_abbr"],
            "away_team_abbr": game["away_team_abbr"],
            "matchup_snapshot_complete": snapshot_complete,
            "matchup_feature_available": feature_ready,
            "home_expected_minutes_coverage": home["expected_minutes_coverage"],
            "away_expected_minutes_coverage": away["expected_minutes_coverage"],
            "minimum_expected_minutes_coverage": min(home["expected_minutes_coverage"], away["expected_minutes_coverage"]),
            "home_impact_coverage": home["impact_coverage"],
            "away_impact_coverage": away["impact_coverage"],
            "minimum_impact_coverage": min(home["impact_coverage"], away["impact_coverage"]),
            "feature_version": VERSION,
        }
        for field in BURDEN_FIELDS:
            matchup[f"home_{field}"] = home[field] if snapshot_complete else ""
            matchup[f"away_{field}"] = away[field] if snapshot_complete else ""
            matchup[f"{field}_home_minus_away"] = (
                round(float(home[field]) - float(away[field]), 6) if snapshot_complete else ""
            )
        matchup_rows.append(matchup)

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "multi-report-team-injury-burden-long.csv", team_rows, list(team_rows[0]) if team_rows else [])
    write_csv(output_dir / "multi-report-matchup-injury-burden-long.csv", matchup_rows, list(matchup_rows[0]) if matchup_rows else [])

    unique_games = len({row["historical_game_id"] for row in matchup_rows})
    complete_rows = sum(int(row["matchup_snapshot_complete"]) for row in matchup_rows)
    feature_rows = sum(int(row["matchup_feature_available"]) for row in matchup_rows)
    quality_ok = all(value == 0 for value in (
        duplicate_snapshot_rows,
        duplicate_game_maps,
        duplicate_identity_snapshots,
        duplicate_value_snapshots,
        missing_identity_snapshot_refs,
        missing_value_snapshot_refs,
        strict_prior_violations,
        unknown_status_rows,
        numeric_errors,
        missing_commence_times,
        multiple_commence_times,
        non_pregame_observations,
    ))
    ready = bool(matchup_rows) and quality_ok
    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "coverage": {
            "snapshot_player_rows": len(snapshots),
            "identity_rows": len(identity_rows),
            "player_value_rows": len(values),
            "independent_games": unique_games,
            "long_matchup_snapshot_rows": len(matchup_rows),
            "long_team_snapshot_rows": len(team_rows),
            "complete_matchup_snapshot_rows": complete_rows,
            "feature_ready_matchup_snapshot_rows": feature_rows,
            "unique_observed_at": len({row["observed_at"] for row in matchup_rows}),
            "status_counts": dict(sorted(all_status_counts.items())),
        },
        "quality": {
            "duplicate_snapshot_rows": duplicate_snapshot_rows,
            "duplicate_game_map_rows": duplicate_game_maps,
            "duplicate_identity_snapshot_rows": duplicate_identity_snapshots,
            "duplicate_player_value_snapshot_rows": duplicate_value_snapshots,
            "missing_identity_snapshot_references": missing_identity_snapshot_refs,
            "missing_player_value_snapshot_references": missing_value_snapshot_refs,
            "strict_prior_date_violations": strict_prior_violations,
            "unknown_status_rows": unknown_status_rows,
            "numeric_errors": numeric_errors,
            "missing_commence_time_groups": missing_commence_times,
            "multiple_commence_time_groups": multiple_commence_times,
            "non_pregame_observations": non_pregame_observations,
            "multiple_snapshots_are_not_counted_as_independent_games": True,
            "missing_team_snapshots_are_not_treated_as_healthy": True,
            "unknown_player_values_are_not_imputed_as_zero": True,
            "outputs_contain_player_names_or_reasons": False,
        },
        "decision": {
            "ready_for_predeclared_snapshot_selection": ready,
            "ready_for_model_training": False,
            "ready_for_probability_adjustment": False,
            "ready_for_betting_edge_claim": False,
            "reason": (
                "Long point-in-time feature panel passed structural QA; a predeclared game-level "
                "snapshot policy and independent-game sample gate remain required."
                if ready else "Long feature panel failed one or more structural QA checks."
            ),
        },
        "guardrails": {
            "group_key": "historical_game_id + observed_at + team_abbr",
            "source_game_date_strictly_before_target_date": True,
            "observed_at_strictly_before_commence_time": True,
            "single_report_builder_modified": False,
            "long_panel_is_not_a_holdout_sample_table": True,
        },
    }
    (output_dir / "multi-report-injury-feature-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def self_test(output_dir: Path) -> None:
    snapshots = []
    identities = []
    values = []
    games = [{
        "historical_game_id": "g1", "game_date": "2024-01-02",
        "home_team_abbr": "AAA", "away_team_abbr": "BBB", "matched": "True",
    }]
    for observed, suffix in (("2024-01-02T20:00:00Z", "a"), ("2024-01-02T22:00:00Z", "b")):
        for team, player, status, minutes in (("AAA", "p1", "OUT", 30), ("BBB", "p2", "QUESTIONABLE", 20)):
            snapshot_id = f"{suffix}-{team}"
            snapshots.append({
                "snapshot_record_id": snapshot_id, "observed_at": observed,
                "commence_time": "2024-01-03T00:00:00Z", "team_abbr": team,
            })
            identities.append({
                "snapshot_record_id": snapshot_id, "historical_game_id": "g1",
                "team_abbr": team, "player_id": player,
            })
            values.append({
                "snapshot_record_id": snapshot_id, "historical_game_id": "g1",
                "team_abbr": team, "availability_status": status,
                "expected_minutes": str(minutes), "player_impact_estimate": "1.0",
                "latest_source_game_date": "2024-01-01", "target_game_date": "2024-01-02",
            })
    report = build(snapshots, values, identities, games, output_dir)
    assert report["decision"]["ready_for_predeclared_snapshot_selection"] is True, report
    assert report["coverage"]["independent_games"] == 1, report
    assert report["coverage"]["long_matchup_snapshot_rows"] == 2, report
    rows = read_csv(output_dir / "multi-report-matchup-injury-burden-long.csv")
    assert float(rows[0]["weighted_unavailable_minutes_home_minus_away"]) == 20.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-csv", type=Path)
    parser.add_argument("--player-values", type=Path)
    parser.add_argument("--player-id-map", type=Path)
    parser.add_argument("--game-map", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("multi-report injury feature long-panel self-test passed")
        return
    if not all((args.snapshot_csv, args.player_values, args.player_id_map, args.game_map)):
        parser.error("--snapshot-csv, --player-values, --player-id-map and --game-map are required")
    report = build(
        read_csv(args.snapshot_csv), read_csv(args.player_values),
        read_csv(args.player_id_map), read_csv(args.game_map), args.output_dir,
    )
    print(json.dumps(report["decision"], indent=2))
    if not report["decision"]["ready_for_predeclared_snapshot_selection"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
