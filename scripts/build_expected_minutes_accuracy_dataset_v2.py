#!/usr/bin/env python3
"""Build Expected Minutes Accuracy Audit v2 rows with official participation labels.

The existing open player archive is used only for deterministic identity support and prior-only
baselines. Target-game played, starter, minutes, DNP, and inactive labels come exclusively from
NBA Official LiveData final-game boxscores and never feed prediction construction.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import build_expected_minutes_accuracy_dataset as v1

VERSION = "expected-minutes-accuracy-dataset-v2"
CLASSIFIED_LABELS = {"PLAYED", "EXPLICIT_DNP", "INACTIVE_OR_NOT_DRESSED"}
ALL_LABELS = CLASSIFIED_LABELS | {"SOURCE_MISSING", "UNKNOWN", "IDENTITY_MISSING"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


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


def as_bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def build(
    selected_rows: list[dict[str, str]],
    wave_inputs: list[
        tuple[
            str,
            list[dict[str, str]],
            list[dict[str, str]],
            list[dict[str, str]],
        ]
    ],
    prior_player_logs: list[dict[str, str]],
    participation_rows: list[dict[str, str]],
    source_index_rows: list[dict[str, str]],
    participation_import_report: dict[str, Any],
    participation_audit_report: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    selected_index: dict[tuple[str, str], dict[str, str]] = {}
    selected_game_ids: set[str] = set()
    duplicate_selected_games = 0
    for row in selected_rows:
        wave = str(row.get("source_wave") or "").strip()
        game_id = str(row.get("historical_game_id") or "").strip()
        if not wave or not game_id:
            raise ValueError("combined selected row missing source_wave or historical_game_id")
        key = (wave, game_id)
        if key in selected_index:
            duplicate_selected_games += 1
        selected_index[key] = row
        selected_game_ids.add(game_id)

    by_player, _, prior_log_qa = v1.prepare_player_logs(prior_player_logs)

    source_success: dict[str, bool] = {}
    duplicate_source_games = 0
    for row in source_index_rows:
        game_id = str(row.get("historical_game_id") or "").strip()
        if not game_id:
            continue
        if game_id in source_success:
            duplicate_source_games += 1
        source_success[game_id] = as_bool(row.get("source_success"))

    participation_index: dict[tuple[str, str], dict[str, str]] = {}
    duplicate_official_game_player_rows = 0
    invalid_participation_rows = 0
    for row in participation_rows:
        game_id = str(row.get("historical_game_id") or "").strip()
        player_id = str(row.get("player_id") or "").strip()
        label = str(row.get("participation_label") or "").strip()
        if not game_id or not player_id or label not in ALL_LABELS - {"SOURCE_MISSING", "IDENTITY_MISSING"}:
            invalid_participation_rows += 1
            continue
        key = (game_id, player_id)
        if key in participation_index:
            duplicate_official_game_player_rows += 1
        participation_index[key] = row

    outputs: list[dict[str, Any]] = []
    selected_games_with_rows: set[str] = set()
    seen_identity_snapshots: set[tuple[str, str]] = set()
    duplicate_identity_snapshot_ids = 0
    missing_snapshot_rows = 0
    rows_outside_selected_snapshot = 0
    strict_prior_violations = 0
    value_latest_date_mismatches = 0
    value_player_id_mismatches = 0
    unknown_status_rows = 0
    team_mismatches = 0
    invalid_minutes_label_combinations = 0

    selected_wave_names = {str(row.get("source_wave") or "").strip() for row in selected_rows}
    supplied_wave_names = {name for name, _, _, _ in wave_inputs}
    missing_wave_inputs = sorted(selected_wave_names - supplied_wave_names)
    unexpected_wave_inputs = sorted(supplied_wave_names - selected_wave_names)

    for wave_name, snapshots, identities, values in wave_inputs:
        snapshot_index = {
            str(row.get("snapshot_record_id") or "").strip(): row
            for row in snapshots
            if str(row.get("snapshot_record_id") or "").strip()
        }
        value_index = {
            str(row.get("snapshot_record_id") or "").strip(): row
            for row in values
            if str(row.get("snapshot_record_id") or "").strip()
        }
        for identity in identities:
            snapshot_id = str(identity.get("snapshot_record_id") or "").strip()
            identity_key = (wave_name, snapshot_id)
            if identity_key in seen_identity_snapshots:
                duplicate_identity_snapshot_ids += 1
            seen_identity_snapshots.add(identity_key)

            snapshot = snapshot_index.get(snapshot_id)
            if snapshot is None:
                missing_snapshot_rows += 1
                continue
            game_id = str(identity.get("historical_game_id") or "").strip()
            selected = selected_index.get((wave_name, game_id))
            if selected is None:
                continue
            selected_observed = v1.canonical_timestamp(selected.get("observed_at"))
            snapshot_observed = v1.canonical_timestamp(snapshot.get("observed_at"))
            if selected_observed != snapshot_observed:
                rows_outside_selected_snapshot += 1
                continue

            selected_games_with_rows.add(game_id)
            target_date = v1.parse_date(selected.get("game_date"))
            season_label = str(identity.get("season_label") or "").strip()
            team_abbr = str(identity.get("team_abbr") or "").strip()
            player_id = str(identity.get("player_id") or "").strip()
            identity_matched = int(bool(player_id))

            value = value_index.get(snapshot_id)
            expected_minutes = as_float(value.get("expected_minutes")) if value else None
            expected_method = str(value.get("expected_minutes_method") or "").strip() if value else ""
            prior_games = as_int(value.get("prior_games")) if value else 0
            current_prior_games = as_int(value.get("current_season_prior_games")) if value else 0
            recent_value_sample = as_int(value.get("recent_value_sample")) if value else 0
            latest_source_date_text = str(value.get("latest_source_game_date") or "").strip() if value else ""
            latest_source_date = v1.parse_date(latest_source_date_text) if latest_source_date_text else None
            if latest_source_date is not None and latest_source_date >= target_date:
                strict_prior_violations += 1
            if value and str(value.get("player_id") or "").strip() != player_id:
                value_player_id_mismatches += 1

            baselines = (
                v1.prior_baselines(by_player.get(player_id, []), target_date, season_label)
                if player_id
                else {
                    "audit_prior_played_games": 0,
                    "audit_current_season_prior_played_games": 0,
                    "baseline_last_prior_game_minutes": None,
                    "baseline_recent10_mean_minutes": None,
                    "baseline_current_season_mean_minutes": None,
                    "audit_latest_prior_game_date": "",
                    "audit_latest_prior_game_id": "",
                }
            )
            audit_latest_date_text = str(baselines["audit_latest_prior_game_date"])
            if latest_source_date_text and audit_latest_date_text and latest_source_date_text != audit_latest_date_text:
                value_latest_date_mismatches += 1
            days_since_latest = (
                (target_date - latest_source_date).days if latest_source_date else None
            )

            source_available = bool(source_success.get(game_id, False))
            participation = participation_index.get((game_id, player_id)) if player_id else None
            if not identity_matched:
                participation_label = "IDENTITY_MISSING"
            elif not source_available:
                participation_label = "SOURCE_MISSING"
            elif participation is None:
                participation_label = "UNKNOWN"
            else:
                participation_label = str(participation.get("participation_label") or "").strip()
                if participation_label not in ALL_LABELS:
                    participation_label = "UNKNOWN"
                    invalid_participation_rows += 1

            label_row_found = int(participation is not None)
            classified_label_available = int(participation_label in CLASSIFIED_LABELS)
            actual_minutes = as_float(participation.get("actual_minutes")) if participation else None
            actual_played = as_int(participation.get("actual_played")) if participation else None
            actual_starter = as_int(participation.get("actual_starter")) if participation else None
            actual_team = str(participation.get("team_abbr") or "").strip() if participation else ""
            if participation and actual_team != team_abbr:
                team_mismatches += 1

            if participation_label == "PLAYED":
                actual_role = "STARTER" if actual_starter == 1 else "BENCH"
                if actual_played != 1 or actual_minutes is None or actual_minutes <= 0:
                    invalid_minutes_label_combinations += 1
            elif participation_label == "EXPLICIT_DNP":
                actual_role = "DNP"
                if actual_played != 0 or actual_minutes not in {0.0, None}:
                    invalid_minutes_label_combinations += 1
            elif participation_label == "INACTIVE_OR_NOT_DRESSED":
                actual_role = "INACTIVE_OR_NOT_DRESSED"
                if actual_played != 0 or actual_minutes not in {0.0, None}:
                    invalid_minutes_label_combinations += 1
            else:
                actual_role = participation_label

            status = str(snapshot.get("availability_status") or "").strip().upper()
            weight = v1.STATUS_UNAVAILABILITY_WEIGHTS.get(status)
            if weight is None:
                unknown_status_rows += 1
            predicted_play_probability = None if weight is None else 1.0 - weight
            predicted_realized_minutes = (
                None
                if expected_minutes is None or predicted_play_probability is None
                else expected_minutes * predicted_play_probability
            )

            outputs.append({
                "source_wave": wave_name,
                "snapshot_record_id": snapshot_id,
                "historical_game_id": game_id,
                "game_date": target_date.isoformat(),
                "observed_at": snapshot_observed,
                "commence_time": v1.canonical_timestamp(selected.get("commence_time")),
                "team_abbr": team_abbr,
                "player_id": player_id,
                "identity_matched": identity_matched,
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
                "latest_source_game_id": str(value.get("latest_source_game_id") or "").strip() if value else "",
                "days_since_latest_prior_game": "" if days_since_latest is None else days_since_latest,
                "prior_game_count_band": v1.band_prior_games(prior_games),
                "expected_minutes_band": v1.band_expected_minutes(expected_minutes),
                "days_since_latest_prior_game_band": v1.band_days_since_latest(days_since_latest),
                "predicted_realized_minutes": "" if predicted_realized_minutes is None else predicted_realized_minutes,
                "official_game_source_available": int(source_available),
                "official_participation_row_found": label_row_found,
                "actual_classified_label_available": classified_label_available,
                "participation_label": participation_label,
                "actual_played": "" if actual_played is None else actual_played,
                "actual_minutes": "" if actual_minutes is None else actual_minutes,
                "actual_starter": "" if actual_starter is None else actual_starter,
                "actual_role": actual_role,
                "actual_team_abbr": actual_team,
                "official_status": "" if participation is None else str(participation.get("official_status") or ""),
                "not_playing_reason_code": "" if participation is None else str(participation.get("not_playing_reason_code") or ""),
                "label_source_sha256": "" if participation is None else str(participation.get("source_sha256") or ""),
                **baselines,
                "dataset_version": VERSION,
            })

    outputs.sort(
        key=lambda row: (
            row["game_date"],
            row["historical_game_id"],
            row["team_abbr"],
            row["player_id"],
            row["snapshot_record_id"],
        )
    )
    output_keys = [
        (row["source_wave"], row["historical_game_id"], row["snapshot_record_id"])
        for row in outputs
    ]
    duplicate_output_rows = len(output_keys) - len(set(output_keys))
    games_missing_rows = sorted(selected_game_ids - selected_games_with_rows)
    output_game_ids = {str(row["historical_game_id"]) for row in outputs}

    total_rows = len(outputs)
    matched_identity_rows = sum(int(row["identity_matched"]) for row in outputs)
    expected_rows = sum(int(row["expected_minutes_available"]) for row in outputs)
    joined_rows = sum(
        int(row["official_participation_row_found"])
        for row in outputs
        if int(row["identity_matched"]) == 1
    )
    classified_rows = sum(int(row["actual_classified_label_available"]) for row in outputs)
    unknown_rows = sum(
        row["participation_label"] == "UNKNOWN"
        for row in outputs
        if int(row["identity_matched"]) == 1
    )
    identity_rate = matched_identity_rows / total_rows if total_rows else 0.0
    expected_coverage = expected_rows / total_rows if total_rows else 0.0
    join_rate = joined_rows / matched_identity_rows if matched_identity_rows else 0.0
    unknown_rate = unknown_rows / matched_identity_rows if matched_identity_rows else 1.0
    successful_source_games = sum(source_success.get(game_id, False) for game_id in selected_game_ids)
    source_coverage = successful_source_games / len(selected_game_ids) if selected_game_ids else 0.0
    label_counts = Counter(str(row["participation_label"]) for row in outputs)

    participation_import_ready = participation_import_report.get("decision", {}).get(
        "ready_for_player_participation_join"
    ) is True
    participation_layer_ready = participation_audit_report.get("decision", {}).get(
        "ready_for_expected_minutes_accuracy_audit_v2_inputs"
    ) is True
    ready = all([
        duplicate_selected_games == 0,
        not missing_wave_inputs,
        not unexpected_wave_inputs,
        missing_snapshot_rows == 0,
        duplicate_identity_snapshot_ids == 0,
        duplicate_output_rows == 0,
        duplicate_source_games == 0,
        duplicate_official_game_player_rows == 0,
        invalid_participation_rows == 0,
        strict_prior_violations == 0,
        value_latest_date_mismatches == 0,
        value_player_id_mismatches == 0,
        unknown_status_rows == 0,
        team_mismatches == 0,
        invalid_minutes_label_combinations == 0,
        not games_missing_rows,
        output_game_ids == selected_game_ids,
        participation_import_ready,
        participation_layer_ready,
        source_coverage == 1.0,
        identity_rate >= 0.95,
        expected_coverage >= 0.85,
        join_rate >= 0.95,
        unknown_rate <= 0.05,
    ])

    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(
        output_dir / "expected-minutes-accuracy-v2-rows.csv",
        outputs,
        list(outputs[0]) if outputs else [],
    )
    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "coverage": {
            "combined_selected_games": len(selected_game_ids),
            "selected_games_with_accuracy_rows": len(selected_games_with_rows),
            "selected_player_snapshot_rows": total_rows,
            "matched_identity_rows": matched_identity_rows,
            "identity_match_rate": round(identity_rate, 6),
            "expected_minutes_rows": expected_rows,
            "expected_minutes_coverage": round(expected_coverage, 6),
            "successful_official_source_games": successful_source_games,
            "official_game_source_coverage": round(source_coverage, 6),
            "official_participation_join_rows": joined_rows,
            "participation_label_join_rate_for_matched_players": round(join_rate, 6),
            "classified_participation_rows": classified_rows,
            "unknown_rows": unknown_rows,
            "unknown_rate_for_matched_players": round(unknown_rate, 6),
            "source_missing_games": sum(not source_success.get(game_id, False) for game_id in selected_game_ids),
            "participation_label_counts": dict(sorted(label_counts.items())),
            "actual_played_rows": label_counts["PLAYED"],
            "explicit_dnp_rows": label_counts["EXPLICIT_DNP"],
            "inactive_or_not_dressed_rows": label_counts["INACTIVE_OR_NOT_DRESSED"],
            "source_wave_counts": dict(sorted(Counter(str(row["source_wave"]) for row in outputs).items())),
        },
        "quality": {
            **prior_log_qa,
            "duplicate_selected_games": duplicate_selected_games,
            "missing_wave_inputs": missing_wave_inputs,
            "unexpected_wave_inputs": unexpected_wave_inputs,
            "missing_snapshot_rows": missing_snapshot_rows,
            "duplicate_identity_snapshot_ids": duplicate_identity_snapshot_ids,
            "rows_outside_selected_snapshot": rows_outside_selected_snapshot,
            "duplicate_accuracy_rows": duplicate_output_rows,
            "duplicate_source_games": duplicate_source_games,
            "duplicate_official_game_player_rows": duplicate_official_game_player_rows,
            "invalid_participation_labels": invalid_participation_rows,
            "invalid_minutes_label_combinations": invalid_minutes_label_combinations,
            "selected_games_without_accuracy_rows": games_missing_rows,
            "strict_prior_date_violations": strict_prior_violations,
            "value_latest_date_mismatches": value_latest_date_mismatches,
            "value_player_id_mismatches": value_player_id_mismatches,
            "unknown_status_rows": unknown_status_rows,
            "team_mismatches": team_mismatches,
            "participation_importer_ready": participation_import_ready,
            "participation_layer_ready": participation_layer_ready,
            "player_names_or_injury_reasons_in_output": False,
            "target_game_labels_used_in_prediction": False,
            "secondary_archive_used_for_target_game_labels": False,
            "missing_actual_participation_imputed_as_zero": False,
            "missing_expected_minutes_imputed_as_zero": False,
        },
        "decision": {
            "ready_for_expected_minutes_accuracy_audit_v2_execution": ready,
            "ready_for_injury_feature_walk_forward_holdout_design": False,
            "ready_for_injury_feature_walk_forward_holdout": False,
            "ready_for_model_training": False,
            "ready_for_probability_adjustment": False,
            "ready_for_betting_edge_claim": False,
            "reason": (
                "The frozen selected snapshots were joined to prior-only predictions and official target-game participation labels without structural or point-in-time violations."
                if ready
                else "The Expected Minutes v2 temporary dataset failed one or more source, join, missingness, or point-in-time gates."
            ),
        },
        "guardrails": {
            "primary_population": "official PLAYED labels only",
            "explicit_dnp_is_primary_role_minutes_row": False,
            "inactive_is_primary_role_minutes_row": False,
            "unknown_is_zero_minutes": False,
            "actual_role_is_prediction_feature": False,
            "target_game_minutes_are_label_only": True,
            "accuracy_rows_are_temporary": True,
        },
    }
    (output_dir / "expected-minutes-accuracy-v2-dataset-report.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def self_test(output_dir: Path) -> None:
    selected = [{
        "source_wave": "wave1",
        "historical_game_id": "g1",
        "game_date": "2024-01-10",
        "observed_at": "2024-01-10T18:00:00Z",
        "commence_time": "2024-01-11T00:00:00Z",
        "home_team_abbr": "AAA",
        "away_team_abbr": "BBB",
    }]
    snapshots = [{
        "snapshot_record_id": "s1",
        "observed_at": "2024-01-10T18:00:00Z",
        "availability_status": "QUESTIONABLE",
    }]
    identities = [{
        "snapshot_record_id": "s1",
        "historical_game_id": "g1",
        "season_label": "2023-24",
        "team_abbr": "AAA",
        "player_id": "p1",
    }]
    values = [{
        "snapshot_record_id": "s1",
        "player_id": "p1",
        "expected_minutes": "30",
        "expected_minutes_method": "current_season_stabilized",
        "prior_games": "5",
        "current_season_prior_games": "5",
        "recent_value_sample": "5",
        "latest_source_game_date": "2024-01-08",
        "latest_source_game_id": "g0",
    }]
    logs = []
    for day, minutes in ((1, 20), (3, 24), (5, 26), (7, 28), (8, 30)):
        logs.append({
            "SEASON_YEAR": "2023-24",
            "PLAYER_ID": "p1",
            "GAME_ID": f"p{day}",
            "GAME_DATE": f"2024-01-{day:02d}",
            "MIN": str(minutes),
            "PLAYED": "1",
            "STARTER": "1",
            "TEAM_ABBREVIATION": "AAA",
        })
    participation = [{
        "historical_game_id": "g1",
        "team_abbr": "AAA",
        "player_id": "p1",
        "participation_label": "PLAYED",
        "actual_minutes": "32",
        "actual_played": "1",
        "actual_starter": "1",
        "official_status": "ACTIVE",
        "not_playing_reason_code": "",
        "source_sha256": "a" * 64,
    }]
    source_index = [{"historical_game_id": "g1", "source_success": "1"}]
    import_report = {"decision": {"ready_for_player_participation_join": True}}
    participation_report = {
        "decision": {"ready_for_expected_minutes_accuracy_audit_v2_inputs": True}
    }
    report = build(
        selected,
        [("wave1", snapshots, identities, values)],
        logs,
        participation,
        source_index,
        import_report,
        participation_report,
        output_dir,
    )
    assert report["decision"]["ready_for_expected_minutes_accuracy_audit_v2_execution"] is True, report
    rows = read_csv(output_dir / "expected-minutes-accuracy-v2-rows.csv")
    assert len(rows) == 1, rows
    assert rows[0]["participation_label"] == "PLAYED", rows[0]
    assert float(rows[0]["actual_minutes"]) == 32.0, rows[0]
    assert float(rows[0]["baseline_last_prior_game_minutes"]) == 30.0, rows[0]
    assert rows[0]["actual_role"] == "STARTER", rows[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--combined-selected", type=Path)
    parser.add_argument(
        "--wave",
        action="append",
        nargs=4,
        metavar=("NAME", "SNAPSHOTS", "IDENTITY", "VALUES"),
    )
    parser.add_argument("--prior-player-logs", type=Path)
    parser.add_argument("--participation-labels", type=Path)
    parser.add_argument("--participation-source-index", type=Path)
    parser.add_argument("--participation-import-report", type=Path)
    parser.add_argument("--participation-audit-report", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test(args.output_dir)
        print("Expected Minutes accuracy dataset v2 self-test passed")
        return
    required = (
        args.combined_selected,
        args.wave,
        args.prior_player_logs,
        args.participation_labels,
        args.participation_source_index,
        args.participation_import_report,
        args.participation_audit_report,
    )
    if not all(required):
        parser.error("all v2 dataset inputs are required")
    wave_inputs = [
        (
            name,
            read_csv(Path(snapshot_path)),
            read_csv(Path(identity_path)),
            read_csv(Path(value_path)),
        )
        for name, snapshot_path, identity_path, value_path in args.wave
    ]
    report = build(
        read_csv(args.combined_selected),
        wave_inputs,
        read_csv(args.prior_player_logs),
        read_csv(args.participation_labels),
        read_csv(args.participation_source_index),
        read_json(args.participation_import_report),
        read_json(args.participation_audit_report),
        args.output_dir,
    )
    print(json.dumps(report["decision"], indent=2))
    if not report["decision"]["ready_for_expected_minutes_accuracy_audit_v2_execution"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
