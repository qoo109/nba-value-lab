#!/usr/bin/env python3
"""Build a temporary deidentified Expected Minutes accuracy dataset.

The dataset joins frozen selected injury snapshots to prior-only Expected Minutes predictions and
Gold-validated target-game player boxscores. Target-game minutes, played, and starter labels are
used only for evaluation and never feed the prediction calculation. Player names and injury reasons
are excluded from the output.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "expected-minutes-accuracy-dataset-v1"
STATUS_UNAVAILABILITY_WEIGHTS = {
    "AVAILABLE": 0.0,
    "PROBABLE": 0.10,
    "QUESTIONABLE": 0.50,
    "DOUBTFUL": 0.75,
    "OUT": 1.0,
    "INACTIVE": 1.0,
    "SUSPENDED": 1.0,
}


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


def as_float(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    return float(text)


def as_int(value: Any, default: int = 0) -> int:
    number = as_float(value)
    return default if number is None else int(number)


def parse_date(value: Any) -> date:
    text = str(value or "").strip()
    for pattern in ("%Y-%m-%d", "%m/%d/%Y", "%b %d, %Y"):
        try:
            return datetime.strptime(text[:10] if pattern == "%Y-%m-%d" else text, pattern).date()
        except ValueError:
            continue
    raise ValueError(f"unsupported date: {value!r}")


def canonical_timestamp(value: Any) -> str:
    text = str(value or "").strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"timestamp must include timezone: {value!r}")
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def mean(values: list[float]) -> float | None:
    return statistics.fmean(values) if values else None


def prepare_player_logs(rows: list[dict[str, str]]) -> tuple[dict[str, list[dict[str, Any]]], dict[tuple[str, str], dict[str, Any]], dict[str, Any]]:
    by_player: dict[str, list[dict[str, Any]]] = defaultdict(list)
    target_index: dict[tuple[str, str], dict[str, Any]] = {}
    duplicate_target_rows = 0
    invalid_rows = 0
    for raw in rows:
        player_id = str(raw.get("PLAYER_ID", "")).strip()
        game_id = str(raw.get("GAME_ID", "")).strip()
        if not player_id or not game_id:
            invalid_rows += 1
            continue
        try:
            game_date = parse_date(raw.get("GAME_DATE"))
            minutes = as_float(raw.get("MIN"))
        except (ValueError, TypeError):
            invalid_rows += 1
            continue
        if minutes is None or minutes < 0:
            invalid_rows += 1
            continue
        item = {
            "player_id": player_id,
            "game_id": game_id,
            "game_date": game_date,
            "season": str(raw.get("SEASON_YEAR", "")).strip(),
            "team_abbr": str(raw.get("TEAM_ABBREVIATION", "")).strip(),
            "minutes": float(minutes),
            "played": int(as_int(raw.get("PLAYED"), int(minutes > 0)) > 0 or minutes > 0),
            "starter": int(as_int(raw.get("STARTER")) > 0),
        }
        key = (game_id, player_id)
        if key in target_index:
            duplicate_target_rows += 1
        target_index[key] = item
        by_player[player_id].append(item)
    for values in by_player.values():
        values.sort(key=lambda row: (row["game_date"], row["game_id"]))
    return by_player, target_index, {
        "prepared_player_log_rows": len(target_index),
        "duplicate_target_game_player_rows": duplicate_target_rows,
        "invalid_player_log_rows": invalid_rows,
    }


def prior_baselines(
    player_rows: list[dict[str, Any]],
    target_date: date,
    season_label: str,
) -> dict[str, Any]:
    prior = [row for row in player_rows if row["game_date"] < target_date and row["played"] == 1]
    current = [row for row in prior if row["season"] == season_label]
    last = prior[-1] if prior else None
    recent10 = prior[-10:]
    return {
        "audit_prior_played_games": len(prior),
        "audit_current_season_prior_played_games": len(current),
        "baseline_last_prior_game_minutes": None if last is None else last["minutes"],
        "baseline_recent10_mean_minutes": mean([row["minutes"] for row in recent10]),
        "baseline_current_season_mean_minutes": mean([row["minutes"] for row in current]),
        "audit_latest_prior_game_date": "" if last is None else last["game_date"].isoformat(),
        "audit_latest_prior_game_id": "" if last is None else last["game_id"],
    }


def band_prior_games(value: int) -> str:
    if value <= 0:
        return "0"
    if value <= 4:
        return "1-4"
    if value <= 9:
        return "5-9"
    return "10+"


def band_expected_minutes(value: float | None) -> str:
    if value is None:
        return "MISSING"
    if value < 12:
        return "<12"
    if value < 24:
        return "12-23.99"
    if value < 32:
        return "24-31.99"
    return "32+"


def band_days_since_latest(value: int | None) -> str:
    if value is None:
        return "NO_PRIOR_GAME"
    if value <= 3:
        return "0-3"
    if value <= 7:
        return "4-7"
    if value <= 13:
        return "8-13"
    return "14+"


def build(
    selected_rows: list[dict[str, str]],
    wave_inputs: list[tuple[str, list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]],
    player_logs: list[dict[str, str]],
    output_dir: Path,
) -> dict[str, Any]:
    selected_index: dict[tuple[str, str], dict[str, str]] = {}
    duplicate_selected_games = 0
    selected_game_ids: set[str] = set()
    for row in selected_rows:
        wave = str(row.get("source_wave", "")).strip()
        game_id = str(row.get("historical_game_id", "")).strip()
        if not wave or not game_id:
            raise ValueError("combined selected row missing source_wave or historical_game_id")
        key = (wave, game_id)
        if key in selected_index:
            duplicate_selected_games += 1
        selected_index[key] = row
        selected_game_ids.add(game_id)

    by_player, target_index, log_qa = prepare_player_logs(player_logs)
    outputs: list[dict[str, Any]] = []
    missing_snapshot_rows = 0
    duplicate_identity_snapshot_ids = 0
    seen_identity_snapshots: set[tuple[str, str]] = set()
    selected_wave_names = {str(row.get("source_wave", "")).strip() for row in selected_rows}
    supplied_wave_names = {name for name, _, _, _ in wave_inputs}
    missing_wave_inputs = sorted(selected_wave_names - supplied_wave_names)
    unexpected_wave_inputs = sorted(supplied_wave_names - selected_wave_names)
    selected_games_with_rows: set[str] = set()
    rows_outside_selected_snapshot = 0
    strict_prior_violations = 0
    value_latest_date_mismatches = 0
    value_player_id_mismatches = 0
    unknown_status_rows = 0

    for wave_name, snapshots, identities, values in wave_inputs:
        snapshot_index = {str(row.get("snapshot_record_id", "")).strip(): row for row in snapshots}
        value_index = {str(row.get("snapshot_record_id", "")).strip(): row for row in values}
        for identity in identities:
            snapshot_id = str(identity.get("snapshot_record_id", "")).strip()
            identity_key = (wave_name, snapshot_id)
            if identity_key in seen_identity_snapshots:
                duplicate_identity_snapshot_ids += 1
            seen_identity_snapshots.add(identity_key)
            snapshot = snapshot_index.get(snapshot_id)
            if snapshot is None:
                missing_snapshot_rows += 1
                continue
            game_id = str(identity.get("historical_game_id", "")).strip()
            selected = selected_index.get((wave_name, game_id))
            if selected is None:
                continue
            selected_observed = canonical_timestamp(selected.get("observed_at"))
            snapshot_observed = canonical_timestamp(snapshot.get("observed_at"))
            if snapshot_observed != selected_observed:
                rows_outside_selected_snapshot += 1
                continue
            selected_games_with_rows.add(game_id)
            target_date = parse_date(selected.get("game_date"))
            season_label = str(identity.get("season_label", "")).strip()
            team_abbr = str(identity.get("team_abbr", "")).strip()
            player_id = str(identity.get("player_id", "")).strip()
            value = value_index.get(snapshot_id)
            expected_minutes = as_float(value.get("expected_minutes")) if value else None
            expected_method = str(value.get("expected_minutes_method", "")).strip() if value else ""
            prior_games = as_int(value.get("prior_games")) if value else 0
            current_prior_games = as_int(value.get("current_season_prior_games")) if value else 0
            recent_value_sample = as_int(value.get("recent_value_sample")) if value else 0
            latest_source_date_text = str(value.get("latest_source_game_date", "")).strip() if value else ""
            latest_source_date = parse_date(latest_source_date_text) if latest_source_date_text else None
            if latest_source_date is not None and latest_source_date >= target_date:
                strict_prior_violations += 1
            if value and str(value.get("player_id", "")).strip() != player_id:
                value_player_id_mismatches += 1

            baselines = prior_baselines(by_player.get(player_id, []), target_date, season_label) if player_id else {
                "audit_prior_played_games": 0,
                "audit_current_season_prior_played_games": 0,
                "baseline_last_prior_game_minutes": None,
                "baseline_recent10_mean_minutes": None,
                "baseline_current_season_mean_minutes": None,
                "audit_latest_prior_game_date": "",
                "audit_latest_prior_game_id": "",
            }
            audit_latest_date_text = str(baselines["audit_latest_prior_game_date"])
            if latest_source_date_text and audit_latest_date_text and latest_source_date_text != audit_latest_date_text:
                value_latest_date_mismatches += 1
            days_since_latest = (target_date - latest_source_date).days if latest_source_date else None

            actual = target_index.get((game_id, player_id)) if player_id else None
            actual_found = int(actual is not None)
            actual_minutes = None if actual is None else float(actual["minutes"])
            actual_played = None if actual is None else int(actual["played"])
            actual_starter = None if actual is None else int(actual["starter"])
            if actual is None:
                actual_role = "MISSING_BOXSCORE_ROW"
            elif actual_played == 0:
                actual_role = "DNP"
            elif actual_starter == 1:
                actual_role = "STARTER"
            else:
                actual_role = "BENCH"

            status = str(snapshot.get("availability_status", "")).strip().upper()
            weight = STATUS_UNAVAILABILITY_WEIGHTS.get(status)
            if weight is None:
                unknown_status_rows += 1
            predicted_play_probability = None if weight is None else 1.0 - weight
            predicted_realized_minutes = (
                None if expected_minutes is None or predicted_play_probability is None
                else expected_minutes * predicted_play_probability
            )
            output = {
                "source_wave": wave_name,
                "snapshot_record_id": snapshot_id,
                "historical_game_id": game_id,
                "game_date": target_date.isoformat(),
                "observed_at": snapshot_observed,
                "commence_time": canonical_timestamp(selected.get("commence_time")),
                "team_abbr": team_abbr,
                "player_id": player_id,
                "identity_matched": int(bool(player_id)),
                "availability_status": status,
                "status_unavailability_weight": "" if weight is None else weight,
                "predicted_play_probability": "" if predicted_play_probability is None else predicted_play_probability,
                "expected_minutes": "" if expected_minutes is None else expected_minutes,
                "expected_minutes_available": int(expected_minutes is not None),
                "expected_minutes_method": expected_method,
                "prior_games": prior_games,
                "current_season_prior_games": current_prior_games,
                "recent_value_sample": recent_value_sample,
                "latest_source_game_date": latest_source_date_text,
                "latest_source_game_id": str(value.get("latest_source_game_id", "")).strip() if value else "",
                "days_since_latest_prior_game": "" if days_since_latest is None else days_since_latest,
                "prior_game_count_band": band_prior_games(prior_games),
                "expected_minutes_band": band_expected_minutes(expected_minutes),
                "days_since_latest_prior_game_band": band_days_since_latest(days_since_latest),
                "predicted_realized_minutes": "" if predicted_realized_minutes is None else predicted_realized_minutes,
                "actual_boxscore_row_found": actual_found,
                "actual_played": "" if actual_played is None else actual_played,
                "actual_minutes": "" if actual_minutes is None else actual_minutes,
                "actual_starter": "" if actual_starter is None else actual_starter,
                "actual_role": actual_role,
                "actual_team_abbr": "" if actual is None else actual["team_abbr"],
                **baselines,
                "dataset_version": VERSION,
            }
            outputs.append(output)

    outputs.sort(key=lambda row: (
        row["game_date"], row["historical_game_id"], row["team_abbr"], row["player_id"], row["snapshot_record_id"]
    ))
    output_keys = [
        (row["source_wave"], row["historical_game_id"], row["snapshot_record_id"])
        for row in outputs
    ]
    duplicate_output_rows = len(output_keys) - len(set(output_keys))
    games_missing_rows = sorted(selected_game_ids - selected_games_with_rows)
    output_game_ids = {str(row["historical_game_id"]) for row in outputs}
    identity_rows = len(outputs)
    matched_identity_rows = sum(int(row["identity_matched"]) for row in outputs)
    expected_rows = sum(int(row["expected_minutes_available"]) for row in outputs)
    actual_join_rows = sum(int(row["actual_boxscore_row_found"]) for row in outputs if int(row["identity_matched"]) == 1)
    identity_rate = matched_identity_rows / identity_rows if identity_rows else 0.0
    expected_coverage = expected_rows / identity_rows if identity_rows else 0.0
    actual_join_rate = actual_join_rows / matched_identity_rows if matched_identity_rows else 0.0
    ready = (
        duplicate_selected_games == 0
        and not missing_wave_inputs
        and not unexpected_wave_inputs
        and missing_snapshot_rows == 0
        and duplicate_identity_snapshot_ids == 0
        and duplicate_output_rows == 0
        and strict_prior_violations == 0
        and value_latest_date_mismatches == 0
        and value_player_id_mismatches == 0
        and unknown_status_rows == 0
        and not games_missing_rows
        and output_game_ids == selected_game_ids
        and identity_rate >= 0.95
        and expected_coverage >= 0.85
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    fields = list(outputs[0]) if outputs else []
    write_csv(output_dir / "expected-minutes-accuracy-rows.csv", outputs, fields)
    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "coverage": {
            "combined_selected_games": len(selected_game_ids),
            "selected_games_with_accuracy_rows": len(selected_games_with_rows),
            "accuracy_player_snapshot_rows": identity_rows,
            "matched_identity_rows": matched_identity_rows,
            "identity_match_rate": round(identity_rate, 6),
            "expected_minutes_rows": expected_rows,
            "expected_minutes_coverage": round(expected_coverage, 6),
            "actual_boxscore_join_rows": actual_join_rows,
            "actual_boxscore_join_rate_for_matched_players": round(actual_join_rate, 6),
            "actual_played_rows": sum(row["actual_role"] in {"STARTER", "BENCH"} for row in outputs),
            "actual_dnp_rows": sum(row["actual_role"] == "DNP" for row in outputs),
            "missing_actual_boxscore_rows": sum(row["actual_role"] == "MISSING_BOXSCORE_ROW" for row in outputs),
            "source_wave_counts": dict(sorted(__import__("collections").Counter(row["source_wave"] for row in outputs).items())),
        },
        "quality": {
            **log_qa,
            "duplicate_selected_games": duplicate_selected_games,
            "missing_wave_inputs": missing_wave_inputs,
            "unexpected_wave_inputs": unexpected_wave_inputs,
            "missing_snapshot_rows": missing_snapshot_rows,
            "duplicate_identity_snapshot_ids": duplicate_identity_snapshot_ids,
            "rows_outside_selected_snapshot": rows_outside_selected_snapshot,
            "duplicate_accuracy_rows": duplicate_output_rows,
            "selected_games_without_accuracy_rows": games_missing_rows,
            "strict_prior_date_violations": strict_prior_violations,
            "value_latest_date_mismatches": value_latest_date_mismatches,
            "value_player_id_mismatches": value_player_id_mismatches,
            "unknown_status_rows": unknown_status_rows,
            "player_names_or_injury_reasons_in_output": False,
            "target_game_labels_used_in_prediction": False,
            "missing_actual_boxscore_row_imputed_as_zero": False,
            "missing_expected_minutes_imputed_as_zero": False,
        },
        "decision": {
            "ready_for_expected_minutes_accuracy_audit": ready,
            "ready_for_injury_feature_walk_forward_holdout": False,
            "ready_for_model_training": False,
            "ready_for_probability_adjustment": False,
            "ready_for_betting_edge_claim": False,
            "reason": (
                "The frozen selected snapshots were joined to deidentified prior-only predictions and label-only target-game minutes."
                if ready else "The temporary accuracy dataset failed one or more structural or point-in-time gates."
            ),
        },
        "guardrails": {
            "primary_population": "actual appearance rows only",
            "actual_dnp_is_primary_role_minutes_row": False,
            "actual_role_is_prediction_feature": False,
            "target_game_minutes_are_label_only": True,
            "accuracy_rows_are_temporary": True,
        },
    }
    (output_dir / "expected-minutes-accuracy-dataset-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def self_test(output_dir: Path) -> None:
    selected = [{
        "source_wave": "wave1", "historical_game_id": "g1", "game_date": "2024-01-10",
        "observed_at": "2024-01-10T18:00:00Z", "commence_time": "2024-01-11T00:00:00Z",
        "home_team_abbr": "AAA", "away_team_abbr": "BBB",
    }]
    snapshots = [{
        "snapshot_record_id": "s1", "observed_at": "2024-01-10T18:00:00Z",
        "availability_status": "QUESTIONABLE",
    }]
    identities = [{
        "snapshot_record_id": "s1", "historical_game_id": "g1", "season_label": "2023-24",
        "team_abbr": "AAA", "player_id": "p1",
    }]
    values = [{
        "snapshot_record_id": "s1", "player_id": "p1", "expected_minutes": "30",
        "expected_minutes_method": "current_season_stabilized", "prior_games": "5",
        "current_season_prior_games": "5", "recent_value_sample": "5",
        "latest_source_game_date": "2024-01-08", "latest_source_game_id": "g0",
    }]
    logs = []
    for day, minutes in ((1, 20), (3, 24), (5, 26), (7, 28), (8, 30)):
        logs.append({
            "SEASON_YEAR": "2023-24", "PLAYER_ID": "p1", "GAME_ID": f"p{day}",
            "GAME_DATE": f"2024-01-{day:02d}", "MIN": str(minutes), "PLAYED": "1",
            "STARTER": "1", "TEAM_ABBREVIATION": "AAA",
        })
    logs.append({
        "SEASON_YEAR": "2023-24", "PLAYER_ID": "p1", "GAME_ID": "g1",
        "GAME_DATE": "2024-01-10", "MIN": "32", "PLAYED": "1", "STARTER": "1",
        "TEAM_ABBREVIATION": "AAA",
    })
    report = build(selected, [("wave1", snapshots, identities, values)], logs, output_dir)
    assert report["decision"]["ready_for_expected_minutes_accuracy_audit"] is True, report
    rows = read_csv(output_dir / "expected-minutes-accuracy-rows.csv")
    assert len(rows) == 1, rows
    assert float(rows[0]["actual_minutes"]) == 32.0, rows[0]
    assert float(rows[0]["baseline_last_prior_game_minutes"]) == 30.0, rows[0]
    assert rows[0]["actual_role"] == "STARTER", rows[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--combined-selected", type=Path)
    parser.add_argument("--wave", action="append", nargs=4, metavar=("NAME", "SNAPSHOTS", "IDENTITY", "VALUES"))
    parser.add_argument("--player-logs", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("Expected Minutes accuracy dataset self-test passed")
        return
    if not args.combined_selected or not args.wave or not args.player_logs:
        parser.error("--combined-selected, --wave, and --player-logs are required")
    wave_inputs = [
        (name, read_csv(Path(snapshot_path)), read_csv(Path(identity_path)), read_csv(Path(value_path)))
        for name, snapshot_path, identity_path, value_path in args.wave
    ]
    report = build(
        read_csv(args.combined_selected),
        wave_inputs,
        read_csv(args.player_logs),
        args.output_dir,
    )
    print(json.dumps(report["decision"], indent=2))
    if not report["decision"]["ready_for_expected_minutes_accuracy_audit"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
