#!/usr/bin/env python3
"""Audit official participation labels against the frozen selected injury snapshots.

The join is deidentified and uses only historical_game_id, player_id, team and the frozen
selected observed_at. Participation labels are target-game evaluation labels only.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "player-participation-label-audit-v1"
OFFICIAL_LABELS = {
    "PLAYED",
    "EXPLICIT_DNP",
    "INACTIVE_OR_NOT_DRESSED",
    "SOURCE_MISSING",
    "UNKNOWN",
}


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


def canonical_timestamp(value: Any) -> str:
    text = str(value or "").strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"timestamp must include timezone: {value!r}")
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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


def audit(
    selected_rows: list[dict[str, str]],
    wave_inputs: list[tuple[str, list[dict[str, str]], list[dict[str, str]]]],
    official_labels: list[dict[str, str]],
    source_index_rows: list[dict[str, str]],
    import_report: dict[str, Any],
    policy: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    selected_index: dict[tuple[str, str], dict[str, str]] = {}
    duplicate_selected_games = 0
    selected_game_ids: set[str] = set()
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

    source_success: dict[str, bool] = {}
    duplicate_source_games = 0
    for row in source_index_rows:
        game_id = str(row.get("historical_game_id") or "").strip()
        if not game_id:
            continue
        if game_id in source_success:
            duplicate_source_games += 1
        source_success[game_id] = as_bool(row.get("source_success"))

    label_index: dict[tuple[str, str], dict[str, str]] = {}
    duplicate_official_game_player_rows = 0
    invalid_official_labels = 0
    for row in official_labels:
        game_id = str(row.get("historical_game_id") or "").strip()
        player_id = str(row.get("player_id") or "").strip()
        label = str(row.get("participation_label") or "").strip()
        if not game_id or not player_id or label not in OFFICIAL_LABELS - {"SOURCE_MISSING"}:
            invalid_official_labels += 1
            continue
        key = (game_id, player_id)
        if key in label_index:
            duplicate_official_game_player_rows += 1
        label_index[key] = row

    outputs: list[dict[str, Any]] = []
    seen_identity_snapshots: set[tuple[str, str]] = set()
    duplicate_identity_snapshot_ids = 0
    missing_snapshot_rows = 0
    rows_outside_selected_snapshot = 0
    selected_games_with_rows: set[str] = set()
    selected_waves = {str(row.get("source_wave") or "").strip() for row in selected_rows}
    supplied_waves = {name for name, _, _ in wave_inputs}
    missing_wave_inputs = sorted(selected_waves - supplied_waves)
    unexpected_wave_inputs = sorted(supplied_waves - selected_waves)

    team_mismatches = 0
    invalid_minutes_labels = 0
    selected_snapshot_rows = 0
    identity_matched_rows = 0
    official_label_join_rows = 0
    classified_rows = 0
    source_missing_rows = 0
    unknown_rows = 0
    label_counts: Counter[str] = Counter()
    source_wave_counts: Counter[str] = Counter()
    availability_label_counts: Counter[tuple[str, str]] = Counter()
    selected_team_game_counts: Counter[tuple[str, str]] = Counter()
    joined_team_game_counts: Counter[tuple[str, str]] = Counter()

    for wave_name, snapshots, identities in wave_inputs:
        snapshot_index = {
            str(row.get("snapshot_record_id") or "").strip(): row
            for row in snapshots
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
            if canonical_timestamp(snapshot.get("observed_at")) != canonical_timestamp(
                selected.get("observed_at")
            ):
                rows_outside_selected_snapshot += 1
                continue

            selected_snapshot_rows += 1
            selected_games_with_rows.add(game_id)
            source_wave_counts[wave_name] += 1
            team_abbr = str(identity.get("team_abbr") or "").strip()
            player_id = str(identity.get("player_id") or "").strip()
            availability_status = str(snapshot.get("availability_status") or "").strip().upper()
            identity_matched = int(bool(player_id))
            identity_matched_rows += identity_matched
            selected_team_game_counts[(game_id, team_abbr)] += 1

            label_row = label_index.get((game_id, player_id)) if player_id else None
            source_available = bool(source_success.get(game_id, False))
            label_row_found = int(label_row is not None)
            official_label_join_rows += int(identity_matched and label_row_found)

            if not identity_matched:
                final_label = "IDENTITY_MISSING"
            elif not source_available:
                final_label = "SOURCE_MISSING"
                source_missing_rows += 1
            elif label_row is None:
                final_label = "UNKNOWN"
                unknown_rows += 1
            else:
                final_label = str(label_row["participation_label"])
                if final_label == "UNKNOWN":
                    unknown_rows += 1
                else:
                    classified_rows += 1
                joined_team_game_counts[(game_id, team_abbr)] += 1

            actual_minutes = as_float(label_row.get("actual_minutes")) if label_row else None
            actual_played = as_int(label_row.get("actual_played")) if label_row else None
            actual_starter = as_int(label_row.get("actual_starter")) if label_row else None
            label_team = str(label_row.get("team_abbr") or "").strip() if label_row else ""
            if label_row and label_team != team_abbr:
                team_mismatches += 1

            if label_row:
                if final_label == "PLAYED" and (
                    actual_minutes is None or actual_minutes <= 0 or actual_played != 1
                ):
                    invalid_minutes_labels += 1
                if final_label in {"EXPLICIT_DNP", "INACTIVE_OR_NOT_DRESSED"} and (
                    actual_minutes not in {0.0, None} or actual_played != 0
                ):
                    invalid_minutes_labels += 1

            if final_label in OFFICIAL_LABELS:
                label_counts[final_label] += 1
                availability_label_counts[(availability_status, final_label)] += 1

            outputs.append({
                "source_wave": wave_name,
                "snapshot_record_id": snapshot_id,
                "historical_game_id": game_id,
                "game_date": str(selected.get("game_date") or "").strip(),
                "observed_at": canonical_timestamp(snapshot.get("observed_at")),
                "team_abbr": team_abbr,
                "player_id": player_id,
                "identity_matched": identity_matched,
                "official_game_source_available": int(source_available),
                "official_label_row_found": label_row_found,
                "participation_label": final_label,
                "actual_minutes": "" if actual_minutes is None else actual_minutes,
                "actual_played": "" if actual_played is None else actual_played,
                "actual_starter": "" if actual_starter is None else actual_starter,
                "availability_status": availability_status,
                "official_status": "" if label_row is None else str(label_row.get("official_status") or ""),
                "not_playing_reason_code": "" if label_row is None else str(label_row.get("not_playing_reason_code") or ""),
                "label_source_sha256": "" if label_row is None else str(label_row.get("source_sha256") or ""),
                "audit_version": VERSION,
            })

    outputs.sort(
        key=lambda row: (
            str(row["game_date"]),
            str(row["historical_game_id"]),
            str(row["team_abbr"]),
            str(row["player_id"]),
            str(row["snapshot_record_id"]),
        )
    )
    output_keys = [
        (row["source_wave"], row["historical_game_id"], row["snapshot_record_id"])
        for row in outputs
    ]
    duplicate_audit_rows = len(output_keys) - len(set(output_keys))
    games_without_rows = sorted(selected_game_ids - selected_games_with_rows)

    successful_source_games = sum(source_success.get(game_id, False) for game_id in selected_game_ids)
    source_game_coverage = (
        successful_source_games / len(selected_game_ids) if selected_game_ids else 0.0
    )
    identity_match_rate = (
        identity_matched_rows / selected_snapshot_rows if selected_snapshot_rows else 0.0
    )
    label_join_rate = (
        official_label_join_rows / identity_matched_rows if identity_matched_rows else 0.0
    )
    unknown_rate = (
        unknown_rows / identity_matched_rows if identity_matched_rows else 1.0
    )
    source_missing_games = sum(
        not source_success.get(game_id, False) for game_id in selected_game_ids
    )
    complete_team_game_groups = sum(
        selected_team_game_counts[key] > 0
        and joined_team_game_counts[key] == selected_team_game_counts[key]
        for key in selected_team_game_counts
    )

    summary_rows: list[dict[str, Any]] = []
    for label, count in sorted(label_counts.items()):
        summary_rows.append({
            "dimension": "participation_label",
            "group_value": label,
            "participation_label": label,
            "rows": count,
        })
    for (status, label), count in sorted(availability_label_counts.items()):
        summary_rows.append({
            "dimension": "availability_status",
            "group_value": status or "BLANK",
            "participation_label": label,
            "rows": count,
        })
    for wave, count in sorted(source_wave_counts.items()):
        summary_rows.append({
            "dimension": "source_wave",
            "group_value": wave,
            "participation_label": "ALL",
            "rows": count,
        })

    gates = policy.get("structural_gates", {})
    required_games = int(gates.get("required_combined_selected_games", 176))
    minimum_source_coverage = float(gates.get("minimum_official_game_source_coverage", 1.0))
    minimum_identity_rate = float(gates.get("minimum_identity_match_rate", 0.95))
    minimum_join_rate = float(
        gates.get("minimum_participation_label_join_rate_for_matched_players", 0.95)
    )
    maximum_unknown_rate = float(
        gates.get("maximum_unknown_rate_for_matched_players", 0.05)
    )
    maximum_source_missing_games = int(gates.get("maximum_source_missing_games", 0))

    import_ready = import_report.get("decision", {}).get(
        "ready_for_player_participation_join"
    ) is True
    gate_results = {
        "importer_ready": import_ready,
        "combined_selected_games_exact": len(selected_game_ids) == required_games,
        "official_game_source_coverage": source_game_coverage >= minimum_source_coverage,
        "identity_match_rate": identity_match_rate >= minimum_identity_rate,
        "participation_label_join_rate": label_join_rate >= minimum_join_rate,
        "unknown_rate": unknown_rate <= maximum_unknown_rate,
        "source_missing_games": source_missing_games <= maximum_source_missing_games,
        "duplicate_selected_games": duplicate_selected_games
        == int(gates.get("duplicate_selected_games", 0)),
        "duplicate_official_game_player_rows": duplicate_official_game_player_rows
        == int(gates.get("duplicate_official_game_player_rows", 0)),
        "duplicate_participation_audit_rows": duplicate_audit_rows
        == int(gates.get("duplicate_participation_audit_rows", 0)),
        "team_mismatches": team_mismatches == int(gates.get("team_mismatches", 0)),
        "duplicate_source_games": duplicate_source_games == 0,
        "invalid_official_labels": invalid_official_labels == 0,
        "invalid_minutes_labels": invalid_minutes_labels == 0,
        "missing_wave_inputs": not missing_wave_inputs,
        "unexpected_wave_inputs": not unexpected_wave_inputs,
        "missing_snapshot_rows": missing_snapshot_rows == 0,
        "duplicate_identity_snapshot_ids": duplicate_identity_snapshot_ids == 0,
        "selected_games_without_rows": not games_without_rows,
    }
    structural_ready = all(gate_results.values())

    write_csv(
        output_dir / "player-participation-label-audit-rows.csv",
        outputs,
        list(outputs[0]) if outputs else [],
    )
    write_csv(
        output_dir / "player-participation-label-summary.csv",
        summary_rows,
        ["dimension", "group_value", "participation_label", "rows"],
    )

    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "policy_schema_version": policy.get("schema_version"),
        "coverage": {
            "combined_selected_games": len(selected_game_ids),
            "successful_official_source_games": successful_source_games,
            "official_game_source_coverage": round(source_game_coverage, 6),
            "selected_player_snapshot_rows": selected_snapshot_rows,
            "identity_matched_rows": identity_matched_rows,
            "identity_match_rate": round(identity_match_rate, 6),
            "official_participation_label_join_rows": official_label_join_rows,
            "participation_label_join_rate_for_matched_players": round(label_join_rate, 6),
            "classified_participation_rows": classified_rows,
            "unknown_rows": unknown_rows,
            "unknown_rate_for_matched_players": round(unknown_rate, 6),
            "source_missing_rows": source_missing_rows,
            "source_missing_games": source_missing_games,
            "complete_team_game_groups": complete_team_game_groups,
            "participation_label_counts": dict(sorted(label_counts.items())),
            "source_wave_counts": dict(sorted(source_wave_counts.items())),
        },
        "quality": {
            "duplicate_selected_games": duplicate_selected_games,
            "duplicate_source_games": duplicate_source_games,
            "duplicate_official_game_player_rows": duplicate_official_game_player_rows,
            "invalid_official_labels": invalid_official_labels,
            "invalid_minutes_labels": invalid_minutes_labels,
            "missing_wave_inputs": missing_wave_inputs,
            "unexpected_wave_inputs": unexpected_wave_inputs,
            "missing_snapshot_rows": missing_snapshot_rows,
            "duplicate_identity_snapshot_ids": duplicate_identity_snapshot_ids,
            "rows_outside_selected_snapshot": rows_outside_selected_snapshot,
            "duplicate_participation_audit_rows": duplicate_audit_rows,
            "selected_games_without_participation_rows": games_without_rows,
            "team_mismatches": team_mismatches,
            "structural_gate_results": gate_results,
            "all_structural_gates_passed": structural_ready,
            "player_names_or_injury_reasons_in_output": False,
            "missing_official_player_row_imputed_as_dnp": False,
            "missing_official_player_row_imputed_as_zero": False,
            "source_fetch_failure_imputed_as_dnp": False,
            "target_game_labels_used_in_prediction": False,
        },
        "decision": {
            "ready_for_expected_minutes_accuracy_audit_v2_inputs": structural_ready,
            "ready_for_expected_minutes_accuracy_audit_v2": False,
            "ready_for_injury_feature_walk_forward_holdout_design": False,
            "ready_for_injury_feature_walk_forward_holdout": False,
            "ready_for_model_training": False,
            "ready_for_probability_adjustment": False,
            "ready_for_betting_edge_claim": False,
            "reason": (
                "The official participation layer passed the frozen source, join and "
                "classification coverage gates. A separately predeclared Accuracy Audit "
                "v2 is still required."
                if structural_ready
                else "The official participation layer failed one or more frozen "
                "source, join or classification gates."
            ),
        },
        "guardrails": {
            "participation_labels_are_evaluation_only": True,
            "participation_layer_directly_passes_accuracy_audit": False,
            "participation_layer_directly_enables_holdout": False,
            "multiple_snapshots_are_independent_games": False,
            "player_level_audit_rows_are_temporary": True,
        },
    }
    (output_dir / "player-participation-label-audit.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def self_test(output_dir: Path) -> None:
    selected = [{
        "source_wave": "wave1",
        "historical_game_id": "22300001",
        "game_date": "2023-10-24",
        "observed_at": "2023-10-24T20:00:00Z",
    }]
    snapshots = [
        {
            "snapshot_record_id": "s1",
            "observed_at": "2023-10-24T20:00:00Z",
            "availability_status": "QUESTIONABLE",
        },
        {
            "snapshot_record_id": "s2",
            "observed_at": "2023-10-24T20:00:00Z",
            "availability_status": "OUT",
        },
    ]
    identities = [
        {
            "snapshot_record_id": "s1",
            "historical_game_id": "22300001",
            "team_abbr": "AAA",
            "player_id": "1",
        },
        {
            "snapshot_record_id": "s2",
            "historical_game_id": "22300001",
            "team_abbr": "BBB",
            "player_id": "2",
        },
    ]
    labels = [
        {
            "historical_game_id": "22300001",
            "team_abbr": "AAA",
            "player_id": "1",
            "participation_label": "PLAYED",
            "actual_minutes": "31.5",
            "actual_played": "1",
            "actual_starter": "1",
            "official_status": "ACTIVE",
            "not_playing_reason_code": "",
            "source_sha256": "a" * 64,
        },
        {
            "historical_game_id": "22300001",
            "team_abbr": "BBB",
            "player_id": "2",
            "participation_label": "INACTIVE_OR_NOT_DRESSED",
            "actual_minutes": "0",
            "actual_played": "0",
            "actual_starter": "0",
            "official_status": "INACTIVE",
            "not_playing_reason_code": "INACTIVE_INJURY",
            "source_sha256": "a" * 64,
        },
    ]
    source_index = [{"historical_game_id": "22300001", "source_success": "1"}]
    import_report = {
        "decision": {"ready_for_player_participation_join": True}
    }
    policy = {
        "schema_version": "test-policy",
        "structural_gates": {
            "required_combined_selected_games": 1,
            "minimum_official_game_source_coverage": 1.0,
            "minimum_identity_match_rate": 1.0,
            "minimum_participation_label_join_rate_for_matched_players": 1.0,
            "maximum_unknown_rate_for_matched_players": 0.0,
            "maximum_source_missing_games": 0,
            "duplicate_selected_games": 0,
            "duplicate_official_game_player_rows": 0,
            "duplicate_participation_audit_rows": 0,
            "team_mismatches": 0,
        },
    }
    report = audit(
        selected,
        [("wave1", snapshots, identities)],
        labels,
        source_index,
        import_report,
        policy,
        output_dir,
    )
    assert report["decision"]["ready_for_expected_minutes_accuracy_audit_v2_inputs"] is True, report
    assert report["coverage"]["participation_label_join_rate_for_matched_players"] == 1.0, report
    assert report["coverage"]["participation_label_counts"] == {
        "INACTIVE_OR_NOT_DRESSED": 1,
        "PLAYED": 1,
    }, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--combined-selected", type=Path)
    parser.add_argument(
        "--wave",
        action="append",
        nargs=3,
        metavar=("NAME", "SNAPSHOTS", "IDENTITIES"),
    )
    parser.add_argument("--labels", type=Path)
    parser.add_argument("--source-index", type=Path)
    parser.add_argument("--import-report", type=Path)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test(args.output_dir)
        print("player participation label audit self-test passed")
        return
    required = (
        args.combined_selected,
        args.wave,
        args.labels,
        args.source_index,
        args.import_report,
        args.policy,
    )
    if not all(required):
        parser.error(
            "--combined-selected, --wave, --labels, --source-index, "
            "--import-report and --policy are required"
        )
    wave_inputs = [
        (name, read_csv(Path(snapshot_path)), read_csv(Path(identity_path)))
        for name, snapshot_path, identity_path in args.wave
    ]
    report = audit(
        read_csv(args.combined_selected),
        wave_inputs,
        read_csv(args.labels),
        read_csv(args.source_index),
        read_json(args.import_report),
        read_json(args.policy),
        args.output_dir,
    )
    print(json.dumps(report["decision"], indent=2))
    if not report["decision"]["ready_for_expected_minutes_accuracy_audit_v2_inputs"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
