#!/usr/bin/env python3
"""Reconcile team submission states with the long injury feature panel.

Only an explicit `SUBMITTED_NO_INJURIES` state may create a zero-burden healthy team.
`NOT_YET_SUBMITTED`, unknown, missing, or conflicting states remain incomplete.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "injury-team-submission-reconciliation-v1"
SUBMITTED_STATES = {"SUBMITTED_WITH_PLAYER_ROWS", "SUBMITTED_NO_INJURIES"}
ALL_STATES = SUBMITTED_STATES | {"NOT_YET_SUBMITTED", "UNKNOWN_NO_PLAYER_ROWS"}
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
STATUS_COUNTS = (
    "available_player_count",
    "probable_player_count",
    "questionable_player_count",
    "doubtful_player_count",
    "out_player_count",
    "inactive_player_count",
    "suspended_player_count",
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


def as_int(value: Any) -> int:
    text = str(value or "").strip()
    return int(float(text)) if text else 0


def blank_team_row(fields: list[str]) -> dict[str, Any]:
    return {field: "" for field in fields}


def make_submission_only_row(
    fields: list[str],
    game: dict[str, str],
    ledger: dict[str, str],
) -> dict[str, Any]:
    observed = str(ledger["observed_at"])
    commence = str(ledger["commence_time"])
    minutes = (parse_timestamp(commence) - parse_timestamp(observed)).total_seconds() / 60.0
    row = blank_team_row(fields)
    row.update({
        "historical_game_id": game["historical_game_id"],
        "game_date": game["game_date"],
        "observed_at": observed,
        "commence_time": commence,
        "minutes_before_tip": round(minutes, 3),
        "team_abbr": ledger["team_abbr"],
        "opponent_abbr": ledger["opponent_abbr"],
        "is_home": as_int(ledger["is_home"]),
        "team_snapshot_available": 0,
        "team_feature_available": 0,
        "listed_player_rows": 0,
        "player_value_rows": 0,
        "missing_player_identity_rows": 0,
        "known_expected_minutes_rows": 0,
        "missing_expected_minutes_rows": 0,
        "expected_minutes_coverage": 0.0,
        "known_impact_rows": 0,
        "missing_impact_rows": 0,
        "impact_coverage": 0.0,
        "feature_version": VERSION,
    })
    for field in STATUS_COUNTS:
        row[field] = 0
    for field in BURDEN_FIELDS:
        row[field] = ""
    return row


def apply_submission_state(row: dict[str, Any], ledger: dict[str, str]) -> tuple[dict[str, Any], list[str], bool]:
    status = str(ledger.get("submission_status", "")).strip()
    errors: list[str] = []
    explicit_zero = False
    player_rows = as_int(ledger.get("player_status_rows"))
    listed_rows = as_int(row.get("listed_player_rows"))
    row["team_submission_status"] = status
    row["team_submission_player_status_rows"] = player_rows
    row["team_submission_source_hash"] = str(ledger.get("source_file_sha256", ""))
    row["team_submission_reconciliation_version"] = VERSION

    if status not in ALL_STATES:
        errors.append(f"unknown submission status {status!r}")
        status = "UNKNOWN_NO_PLAYER_ROWS"
        row["team_submission_status"] = status

    if status == "SUBMITTED_WITH_PLAYER_ROWS":
        if player_rows <= 0:
            errors.append("submitted-with-player-rows has zero source player rows")
        if listed_rows <= 0:
            errors.append("submitted-with-player-rows has no long-panel player rows")
            row["team_snapshot_available"] = 0
            row["team_feature_available"] = 0
        else:
            row["team_snapshot_available"] = 1
    elif status == "SUBMITTED_NO_INJURIES":
        if player_rows != 0 or listed_rows != 0:
            errors.append("submitted-no-injuries conflicts with player rows")
            row["team_snapshot_available"] = 0
            row["team_feature_available"] = 0
        else:
            explicit_zero = True
            row.update({
                "team_snapshot_available": 1,
                "team_feature_available": 1,
                "expected_minutes_coverage": 1.0,
                "impact_coverage": 1.0,
                "explicit_zero_burden_from_submitted_no_injuries": 1,
            })
            for field in STATUS_COUNTS:
                row[field] = 0
            for field in BURDEN_FIELDS:
                row[field] = 0.0
    else:
        if listed_rows > 0:
            errors.append(f"{status} conflicts with existing player rows")
        row["team_snapshot_available"] = 0
        row["team_feature_available"] = 0
        row["explicit_zero_burden_from_submitted_no_injuries"] = 0
        for field in BURDEN_FIELDS:
            row[field] = ""

    row.setdefault("explicit_zero_burden_from_submitted_no_injuries", int(explicit_zero))
    return row, errors, explicit_zero


def rebuild_matchups(
    team_rows: list[dict[str, Any]],
    game_index: dict[str, dict[str, str]],
) -> tuple[list[dict[str, Any]], int]:
    grouped: dict[tuple[str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in team_rows:
        key = (str(row["historical_game_id"]), str(row["observed_at"]))
        grouped[key][str(row["team_abbr"])] = row

    outputs: list[dict[str, Any]] = []
    side_errors = 0
    for (game_id, observed_at), sides in sorted(
        grouped.items(), key=lambda item: (game_index.get(item[0][0], {}).get("game_date", ""), item[0])
    ):
        game = game_index.get(game_id)
        if not game:
            side_errors += 1
            continue
        home = sides.get(game["home_team_abbr"])
        away = sides.get(game["away_team_abbr"])
        if home is None or away is None:
            side_errors += 1
            continue
        complete = int(as_int(home["team_snapshot_available"]) == 1 and as_int(away["team_snapshot_available"]) == 1)
        feature_ready = int(as_int(home["team_feature_available"]) == 1 and as_int(away["team_feature_available"]) == 1)
        row: dict[str, Any] = {
            "historical_game_id": game_id,
            "game_date": game["game_date"],
            "observed_at": observed_at,
            "commence_time": home["commence_time"],
            "minutes_before_tip": home["minutes_before_tip"],
            "home_team_abbr": game["home_team_abbr"],
            "away_team_abbr": game["away_team_abbr"],
            "home_submission_status": home["team_submission_status"],
            "away_submission_status": away["team_submission_status"],
            "matchup_snapshot_complete": complete,
            "matchup_feature_available": feature_ready,
            "home_expected_minutes_coverage": home["expected_minutes_coverage"],
            "away_expected_minutes_coverage": away["expected_minutes_coverage"],
            "minimum_expected_minutes_coverage": min(float(home["expected_minutes_coverage"]), float(away["expected_minutes_coverage"])),
            "home_impact_coverage": home["impact_coverage"],
            "away_impact_coverage": away["impact_coverage"],
            "minimum_impact_coverage": min(float(home["impact_coverage"]), float(away["impact_coverage"])),
            "explicit_healthy_team_count": as_int(home.get("explicit_zero_burden_from_submitted_no_injuries")) + as_int(away.get("explicit_zero_burden_from_submitted_no_injuries")),
            "feature_version": VERSION,
        }
        for field in BURDEN_FIELDS:
            home_value = home.get(field, "")
            away_value = away.get(field, "")
            row[f"home_{field}"] = home_value if feature_ready else ""
            row[f"away_{field}"] = away_value if feature_ready else ""
            row[f"{field}_home_minus_away"] = (
                round(float(home_value) - float(away_value), 6) if feature_ready else ""
            )
        outputs.append(row)
    return outputs, side_errors


def reconcile(
    original_team_rows: list[dict[str, str]],
    submission_rows: list[dict[str, str]],
    game_map_rows: list[dict[str, str]],
    output_dir: Path,
) -> dict[str, Any]:
    if not original_team_rows:
        raise ValueError("original team long panel is empty")
    base_fields = list(original_team_rows[0])
    for field in (
        "team_submission_status",
        "team_submission_player_status_rows",
        "team_submission_source_hash",
        "explicit_zero_burden_from_submitted_no_injuries",
        "team_submission_reconciliation_version",
    ):
        if field not in base_fields:
            base_fields.append(field)

    official_map: dict[str, dict[str, str]] = {}
    game_index: dict[str, dict[str, str]] = {}
    duplicate_game_maps = 0
    for row in game_map_rows:
        if str(row.get("matched", "")).strip().lower() not in {"1", "true"}:
            continue
        official = str(row.get("official_game_id", "")).strip()
        historical = str(row.get("historical_game_id", "")).strip()
        item = {
            "official_game_id": official,
            "historical_game_id": historical,
            "game_date": str(row.get("game_date", "")).strip(),
            "home_team_abbr": str(row.get("home_team_abbr", "")).strip(),
            "away_team_abbr": str(row.get("away_team_abbr", "")).strip(),
        }
        if official in official_map and official_map[official] != item:
            duplicate_game_maps += 1
        official_map[official] = item
        game_index[historical] = item

    team_index: dict[tuple[str, str, str], dict[str, Any]] = {}
    duplicate_original_rows = 0
    for raw in original_team_rows:
        row = {field: raw.get(field, "") for field in base_fields}
        key = (str(row["historical_game_id"]), str(row["observed_at"]), str(row["team_abbr"]))
        if key in team_index:
            duplicate_original_rows += 1
        team_index[key] = row

    ledger_keys: set[tuple[str, str, str]] = set()
    duplicate_submission_rows = 0
    unmapped_submission_rows = 0
    reconciliation_errors: list[str] = []
    explicit_healthy_teams = 0
    new_team_rows = 0
    status_counts: Counter[str] = Counter()

    for ledger in submission_rows:
        game = official_map.get(str(ledger.get("game_id", "")).strip())
        if game is None:
            unmapped_submission_rows += 1
            continue
        key = (
            game["historical_game_id"],
            str(ledger.get("observed_at", "")).strip(),
            str(ledger.get("team_abbr", "")).strip(),
        )
        if key in ledger_keys:
            duplicate_submission_rows += 1
        ledger_keys.add(key)
        row = team_index.get(key)
        if row is None:
            row = make_submission_only_row(base_fields, game, ledger)
            team_index[key] = row
            new_team_rows += 1
        row, errors, explicit_zero = apply_submission_state(row, ledger)
        reconciliation_errors.extend(f"{key}: {message}" for message in errors)
        explicit_healthy_teams += int(explicit_zero)
        status_counts[str(row["team_submission_status"])] += 1

    missing_ledger_rows = 0
    for key, row in team_index.items():
        if key in ledger_keys:
            continue
        missing_ledger_rows += 1
        row["team_submission_status"] = "MISSING_TEAM_LEDGER"
        row["team_submission_player_status_rows"] = ""
        row["team_submission_source_hash"] = ""
        row["explicit_zero_burden_from_submitted_no_injuries"] = 0
        row["team_submission_reconciliation_version"] = VERSION
        row["team_snapshot_available"] = 0
        row["team_feature_available"] = 0
        for field in BURDEN_FIELDS:
            row[field] = ""

    team_rows = sorted(
        team_index.values(),
        key=lambda row: (str(row["game_date"]), str(row["historical_game_id"]), str(row["observed_at"]), str(row["team_abbr"])),
    )
    matchup_rows, side_errors = rebuild_matchups(team_rows, game_index)
    non_pregame = 0
    for row in team_rows:
        try:
            if parse_timestamp(row["observed_at"]) >= parse_timestamp(row["commence_time"]):
                non_pregame += 1
        except ValueError:
            non_pregame += 1

    unique_games = len({str(row["historical_game_id"]) for row in matchup_rows})
    complete_rows = sum(as_int(row["matchup_snapshot_complete"]) for row in matchup_rows)
    feature_rows = sum(as_int(row["matchup_feature_available"]) for row in matchup_rows)
    quality_ok = all(value == 0 for value in (
        duplicate_game_maps,
        duplicate_original_rows,
        duplicate_submission_rows,
        unmapped_submission_rows,
        missing_ledger_rows,
        side_errors,
        non_pregame,
        len(reconciliation_errors),
    ))
    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "coverage": {
            "original_team_rows": len(original_team_rows),
            "team_submission_rows": len(submission_rows),
            "reconciled_team_rows": len(team_rows),
            "new_submission_only_team_rows": new_team_rows,
            "reconciled_matchup_snapshot_rows": len(matchup_rows),
            "independent_games": unique_games,
            "complete_matchup_snapshot_rows": complete_rows,
            "feature_ready_matchup_snapshot_rows": feature_rows,
            "explicit_submitted_no_injuries_teams": explicit_healthy_teams,
            "submission_status_counts": dict(sorted(status_counts.items())),
        },
        "quality": {
            "duplicate_game_map_rows": duplicate_game_maps,
            "duplicate_original_team_rows": duplicate_original_rows,
            "duplicate_submission_rows": duplicate_submission_rows,
            "unmapped_submission_rows": unmapped_submission_rows,
            "original_team_rows_without_ledger": missing_ledger_rows,
            "matchup_side_errors": side_errors,
            "non_pregame_rows": non_pregame,
            "reconciliation_errors": len(reconciliation_errors),
            "reconciliation_error_examples": reconciliation_errors[:50],
            "not_yet_submitted_imputed_as_zero": False,
            "unknown_submission_imputed_as_zero": False,
            "explicit_submitted_no_injuries_imputed_as_zero": True,
            "player_names_or_injury_reasons_in_output": False,
        },
        "decision": {
            "ready_for_predeclared_snapshot_selection": bool(matchup_rows) and quality_ok,
            "ready_for_model_training": False,
            "ready_for_probability_adjustment": False,
            "ready_for_betting_edge_claim": False,
            "reason": (
                "Team submission states were reconciled without converting missing or unsubmitted teams to zero burden."
                if quality_ok else "Submission reconciliation failed one or more structural gates."
            ),
        },
        "guardrails": {
            "zero_burden_requires_explicit_submitted_no_injuries": True,
            "group_key": "historical_game_id + observed_at + team_abbr",
            "multiple_snapshots_are_not_independent_games": True,
            "outcomes_or_market_prices_used": False,
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "reconciled-team-injury-burden-long.csv", team_rows, base_fields)
    write_csv(
        output_dir / "reconciled-matchup-injury-burden-long.csv",
        matchup_rows,
        list(matchup_rows[0]) if matchup_rows else [],
    )
    (output_dir / "injury-team-submission-reconciliation-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def self_test(output_dir: Path) -> None:
    original = [{
        "historical_game_id":"g1","game_date":"2024-01-01","observed_at":"2024-01-01T20:00:00Z",
        "commence_time":"2024-01-02T00:00:00Z","minutes_before_tip":"240","team_abbr":"AAA",
        "opponent_abbr":"BBB","is_home":"1","team_snapshot_available":"1","team_feature_available":"1",
        "listed_player_rows":"1","player_value_rows":"1","missing_player_identity_rows":"0",
        "known_expected_minutes_rows":"1","missing_expected_minutes_rows":"0","expected_minutes_coverage":"1.0",
        "known_impact_rows":"1","missing_impact_rows":"0","impact_coverage":"1.0","feature_version":"old",
        **{field:"0" for field in STATUS_COUNTS},
        **{field:("30" if field == "definite_out_minutes" else "0") for field in BURDEN_FIELDS},
    }]
    submissions = [
        {"game_id":"official:2024-01-01:BBB@AAA","commence_time":"2024-01-02T00:00:00Z","team_abbr":"AAA","opponent_abbr":"BBB","is_home":"1","submission_status":"SUBMITTED_WITH_PLAYER_ROWS","player_status_rows":"1","observed_at":"2024-01-01T20:00:00Z","source_file_sha256":"a"*64},
        {"game_id":"official:2024-01-01:BBB@AAA","commence_time":"2024-01-02T00:00:00Z","team_abbr":"BBB","opponent_abbr":"AAA","is_home":"0","submission_status":"SUBMITTED_NO_INJURIES","player_status_rows":"0","observed_at":"2024-01-01T20:00:00Z","source_file_sha256":"a"*64},
        {"game_id":"official:2024-01-02:DDD@CCC","commence_time":"2024-01-03T00:00:00Z","team_abbr":"CCC","opponent_abbr":"DDD","is_home":"1","submission_status":"NOT_YET_SUBMITTED","player_status_rows":"0","observed_at":"2024-01-02T20:00:00Z","source_file_sha256":"b"*64},
        {"game_id":"official:2024-01-02:DDD@CCC","commence_time":"2024-01-03T00:00:00Z","team_abbr":"DDD","opponent_abbr":"CCC","is_home":"0","submission_status":"NOT_YET_SUBMITTED","player_status_rows":"0","observed_at":"2024-01-02T20:00:00Z","source_file_sha256":"b"*64},
    ]
    maps = [
        {"official_game_id":"official:2024-01-01:BBB@AAA","historical_game_id":"g1","game_date":"2024-01-01","away_team_abbr":"BBB","home_team_abbr":"AAA","matched":"True"},
        {"official_game_id":"official:2024-01-02:DDD@CCC","historical_game_id":"g2","game_date":"2024-01-02","away_team_abbr":"DDD","home_team_abbr":"CCC","matched":"True"},
    ]
    report = reconcile(original, submissions, maps, output_dir)
    assert report["decision"]["ready_for_predeclared_snapshot_selection"] is True, report
    assert report["coverage"]["independent_games"] == 2, report
    assert report["coverage"]["explicit_submitted_no_injuries_teams"] == 1, report
    matchups = read_csv(output_dir / "reconciled-matchup-injury-burden-long.csv")
    g1 = next(row for row in matchups if row["historical_game_id"] == "g1")
    g2 = next(row for row in matchups if row["historical_game_id"] == "g2")
    assert g1["matchup_feature_available"] == "1", g1
    assert float(g1["away_weighted_unavailable_minutes"]) == 0.0, g1
    assert g2["matchup_feature_available"] == "0", g2


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--team-long", type=Path)
    parser.add_argument("--team-submissions", type=Path)
    parser.add_argument("--team-game-map", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("team submission reconciliation self-test passed")
        return
    if not args.team_long or not args.team_submissions or not args.team_game_map:
        parser.error("--team-long, --team-submissions and --team-game-map are required")
    report = reconcile(
        read_csv(args.team_long),
        read_csv(args.team_submissions),
        read_csv(args.team_game_map),
        args.output_dir,
    )
    print(json.dumps(report["decision"], indent=2))
    if not report["decision"]["ready_for_predeclared_snapshot_selection"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
