#!/usr/bin/env python3
"""Freeze expanded official participation counts without calculating accuracy metrics."""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "expanded-participation-census-v1"
CLASSIFIED_LABELS = {"PLAYED", "EXPLICIT_DNP", "INACTIVE_OR_NOT_DRESSED"}
PRESERVED_POPULATION = 293
PRESERVED_SAMPLE_THRESHOLDS = {
    "minimum_evaluable_games": 150,
    "minimum_conditional_played_rows": 500,
    "minimum_bench_played_rows": 200,
    "minimum_ten_plus_prior_game_played_rows": 400,
}
PRESERVED_STRUCTURAL_THRESHOLDS = {
    "minimum_official_game_source_coverage": 1.0,
    "minimum_identity_match_rate": 0.95,
    "minimum_participation_label_join_rate_for_matched_players": 0.99,
    "maximum_unknown_rate_for_matched_players": 0.05,
    "maximum_source_missing_games": 0,
    "maximum_strict_prior_date_violations": 0,
    "maximum_ambiguous_identity_rows": 0,
    "maximum_forbidden_player_level_files_retained": 0,
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


def as_float(value: Any) -> float | None:
    text = str(value or "").strip()
    return None if not text else float(text)


def as_int(value: Any, default: int = 0) -> int:
    number = as_float(value)
    return default if number is None else int(number)


def as_bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def role_eligible(row: dict[str, str]) -> bool:
    return all([
        str(row.get("participation_label") or "") == "PLAYED",
        as_int(row.get("actual_classified_label_available")) == 1,
        as_int(row.get("expected_minutes_available")) == 1,
        as_float(row.get("expected_minutes")) is not None,
        (as_float(row.get("actual_minutes")) or 0.0) > 0,
    ])


def complete_team_game_groups(rows: list[dict[str, str]]) -> int:
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[(
            str(row.get("historical_game_id") or ""),
            str(row.get("team_abbr") or ""),
        )].append(row)
    return sum(
        all(
            as_int(row.get("identity_matched")) == 1
            and as_int(row.get("expected_minutes_available")) == 1
            and str(row.get("participation_label") or "") in CLASSIFIED_LABELS
            and as_int(row.get("actual_classified_label_available")) == 1
            for row in items
        )
        for items in grouped.values()
    )


def delete_sensitive_files(root: Path, forbidden_names: set[str]) -> tuple[int, list[str]]:
    deleted = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.name in forbidden_names or path.suffix.lower() == ".pdf" or path.name.endswith(".json.raw"):
            path.unlink(missing_ok=True)
            deleted += 1
    retained = sorted(
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file() and path.name in forbidden_names
    )
    return deleted, retained


def audit(
    rows: list[dict[str, str]],
    dataset_report: dict[str, Any],
    participation_audit: dict[str, Any],
    participation_import: dict[str, Any],
    combined_report: dict[str, Any],
    identity_reports: list[dict[str, Any]],
    policy: dict[str, Any],
    sensitive_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    structural_policy = policy.get("structural_gates", {})
    sample_policy = policy.get("sample_thresholds", {})
    policy_thresholds_preserved = (
        as_int(structural_policy.get("required_combined_selected_games")) == PRESERVED_POPULATION
        and all(
            structural_policy.get(key) == value
            for key, value in PRESERVED_STRUCTURAL_THRESHOLDS.items()
        )
        and all(sample_policy.get(key) == value for key, value in PRESERVED_SAMPLE_THRESHOLDS.items())
    )

    row_keys = [
        (
            str(row.get("source_wave") or ""),
            str(row.get("historical_game_id") or ""),
            str(row.get("snapshot_record_id") or ""),
        )
        for row in rows
    ]
    duplicate_census_rows = len(row_keys) - len(set(row_keys))
    selected_games = {
        str(row.get("historical_game_id") or "")
        for row in rows
        if str(row.get("historical_game_id") or "").strip()
    }
    role_rows = [row for row in rows if role_eligible(row)]
    evaluable_games = {
        str(row.get("historical_game_id") or "") for row in role_rows
    }
    starter_rows = sum(str(row.get("actual_role") or "") == "STARTER" for row in role_rows)
    bench_rows = sum(str(row.get("actual_role") or "") == "BENCH" for row in role_rows)
    long_history_rows = sum(as_int(row.get("prior_games")) >= 10 for row in role_rows)
    complete_groups = complete_team_game_groups(rows)
    label_counts = Counter(str(row.get("participation_label") or "") for row in rows)
    wave_counts = Counter(str(row.get("source_wave") or "") for row in rows)

    dataset_coverage = dataset_report.get("coverage", {})
    dataset_quality = dataset_report.get("quality", {})
    participation_coverage = participation_audit.get("coverage", {})
    participation_quality = participation_audit.get("quality", {})
    combined_coverage = combined_report.get("coverage", {})
    combined_quality = combined_report.get("quality", {})
    import_coverage = participation_import.get("coverage", {})

    ambiguous_identity_rows = sum(
        as_int(report.get("quality", {}).get("ambiguous_player_rows"))
        for report in identity_reports
    )
    fuzzy_identity_used = any(
        report.get("guardrails", {}).get("fuzzy_edit_distance_matching_used") is True
        or report.get("guardrails", {}).get("nearest_name_guessing_used") is True
        for report in identity_reports
    )

    forbidden_names = set(policy.get("forbidden_player_level_filenames", []))
    deleted_sensitive_files, retained_sensitive_files = delete_sensitive_files(
        sensitive_root, forbidden_names
    )

    combined_games = as_int(dataset_coverage.get("combined_selected_games"))
    successful_sources = as_int(dataset_coverage.get("successful_official_source_games"))
    source_missing_games = as_int(dataset_coverage.get("source_missing_games"))
    official_player_rows = as_int(import_coverage.get("official_player_rows"))
    selected_snapshot_rows = as_int(dataset_coverage.get("selected_player_snapshot_rows"))
    identity_rows = as_int(dataset_coverage.get("matched_identity_rows"))
    joined_rows = as_int(dataset_coverage.get("official_participation_join_rows"))
    unknown_rows = as_int(dataset_coverage.get("unknown_rows"))
    source_coverage = as_float(dataset_coverage.get("official_game_source_coverage")) or 0.0
    identity_rate = as_float(dataset_coverage.get("identity_match_rate")) or 0.0
    join_rate = as_float(
        dataset_coverage.get("participation_label_join_rate_for_matched_players")
    ) or 0.0
    unknown_rate = as_float(dataset_coverage.get("unknown_rate_for_matched_players")) or 1.0
    strict_prior_violations = as_int(dataset_quality.get("strict_prior_date_violations"))

    structural_results = {
        "policy_thresholds_preserved": policy_thresholds_preserved,
        "combined_selected_games_exact": (
            len(selected_games) == combined_games == PRESERVED_POPULATION
            and as_int(combined_coverage.get("combined_independent_games")) == PRESERVED_POPULATION
        ),
        "wave_counts_exact": dict(combined_coverage.get("selected_source_wave_counts", {}))
        == {"wave1": 91, "wave2": 85, "wave3": 117},
        "cross_wave_duplicates_zero": as_int(
            combined_coverage.get("duplicate_games_across_waves")
        ) == 0,
        "combined_conflicts_zero": all([
            as_int(combined_quality.get("game_identity_conflicts")) == 0,
            as_int(combined_quality.get("selection_policy_conflicts")) == 0,
            as_int(combined_quality.get("duplicate_output_games")) == 0,
        ]),
        "dataset_builder_ready": dataset_report.get("decision", {}).get(
            "ready_for_expected_minutes_accuracy_audit_v2_execution"
        ) is True,
        "participation_layer_ready": participation_audit.get("decision", {}).get(
            "ready_for_expected_minutes_accuracy_audit_v2_inputs"
        ) is True,
        "participation_importer_ready": participation_import.get("decision", {}).get(
            "ready_for_player_participation_join"
        ) is True,
        "official_game_source_coverage": source_coverage >= 1.0,
        "source_missing_games": source_missing_games == 0,
        "identity_match_rate": identity_rate >= 0.95,
        "participation_label_join_rate": join_rate >= 0.99,
        "unknown_rate": unknown_rate <= 0.05,
        "strict_prior_date_violations": strict_prior_violations == 0,
        "ambiguous_identity_rows": ambiguous_identity_rows == 0,
        "fuzzy_identity_used": fuzzy_identity_used is False,
        "duplicate_selected_games": as_int(dataset_quality.get("duplicate_selected_games")) == 0,
        "duplicate_census_rows": duplicate_census_rows == 0,
        "duplicate_official_game_player_rows": as_int(
            dataset_quality.get("duplicate_official_game_player_rows")
        ) == 0,
        "team_mismatches": as_int(dataset_quality.get("team_mismatches")) == 0,
        "invalid_participation_labels": as_int(
            dataset_quality.get("invalid_participation_labels")
        ) == 0,
        "invalid_minutes_label_combinations": as_int(
            dataset_quality.get("invalid_minutes_label_combinations")
        ) == 0,
        "participation_structural_gates": participation_quality.get(
            "all_structural_gates_passed"
        ) is True,
        "forbidden_player_level_files_retained": len(retained_sensitive_files) == 0,
    }
    structural_ready = all(structural_results.values())

    sample_results = {
        "evaluable_games": len(evaluable_games) >= PRESERVED_SAMPLE_THRESHOLDS["minimum_evaluable_games"],
        "conditional_played_rows": len(role_rows) >= PRESERVED_SAMPLE_THRESHOLDS["minimum_conditional_played_rows"],
        "bench_played_rows": bench_rows >= PRESERVED_SAMPLE_THRESHOLDS["minimum_bench_played_rows"],
        "ten_plus_prior_game_played_rows": long_history_rows >= PRESERVED_SAMPLE_THRESHOLDS["minimum_ten_plus_prior_game_played_rows"],
    }
    sample_ready = all(sample_results.values())

    if not structural_ready:
        decision_state = "STRUCTURAL_BLOCKED"
    elif sample_ready:
        decision_state = "CENSUS_READY_AUDIT_V3_ELIGIBLE"
    else:
        decision_state = "CENSUS_READY_AUDIT_V3_NOT_ELIGIBLE"

    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "decision_state": decision_state,
        "coverage": {
            "combined_selected_games": combined_games,
            "successful_official_source_games": successful_sources,
            "source_missing_games": source_missing_games,
            "official_player_rows": official_player_rows,
            "selected_player_snapshot_rows": selected_snapshot_rows,
            "identity_matched_rows": identity_rows,
            "identity_match_rate": round(identity_rate, 6),
            "participation_label_joined_rows": joined_rows,
            "participation_label_join_rate": round(join_rate, 6),
            "unknown_rows": unknown_rows,
            "unknown_rate": round(unknown_rate, 6),
            "evaluable_games": len(evaluable_games),
            "conditional_played_rows": len(role_rows),
            "starter_played_rows": starter_rows,
            "bench_played_rows": bench_rows,
            "ten_plus_prior_game_played_rows": long_history_rows,
            "complete_team_game_groups": complete_groups,
            "participation_label_counts": dict(sorted(label_counts.items())),
            "source_wave_player_row_counts": dict(sorted(wave_counts.items())),
        },
        "thresholds": {
            "structural": structural_policy,
            "sample": sample_policy,
        },
        "quality": {
            "structural_gate_results": structural_results,
            "sample_gate_results": sample_results,
            "structural_blockers": sorted(
                name for name, passed in structural_results.items() if not passed
            ),
            "sample_blockers": sorted(
                name for name, passed in sample_results.items() if not passed
            ),
            "duplicate_census_rows": duplicate_census_rows,
            "ambiguous_identity_rows": ambiguous_identity_rows,
            "fuzzy_identity_used": fuzzy_identity_used,
            "strict_prior_date_violations": strict_prior_violations,
            "temporary_sensitive_files_deleted": deleted_sensitive_files,
            "forbidden_player_level_files_retained": len(retained_sensitive_files),
            "retained_forbidden_file_paths": retained_sensitive_files,
            "accuracy_metrics_calculated": False,
            "target_game_labels_used_in_prediction": False,
            "missing_actuals_imputed_as_zero": False,
            "missing_expected_minutes_imputed_as_zero": False,
        },
        "decision": {
            "ready_for_expected_minutes_accuracy_audit_v3_predeclaration": (
                decision_state == "CENSUS_READY_AUDIT_V3_ELIGIBLE"
            ),
            "ready_for_expected_minutes_accuracy_audit_v3_execution": False,
            "ready_for_injury_feature_walk_forward_holdout": False,
            "ready_for_model_training": False,
            "ready_for_probability_adjustment": False,
            "ready_for_betting_edge_claim": False,
            "formal_stake": 0,
        },
        "guardrails": {
            "census_counts_only": True,
            "accuracy_metrics_forbidden": True,
            "participation_labels_are_evaluation_only": True,
            "missing_player_row_is_dnp": False,
            "unknown_state_is_zero_minutes": False,
            "multiple_snapshots_are_independent_games": False,
            "separate_audit_v3_predeclaration_required": True,
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "expanded-participation-census-v1.json"
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def self_test(output_dir: Path) -> None:
    root = output_dir / "sensitive"
    root.mkdir(parents=True, exist_ok=True)
    (root / "official-player-participation-labels.csv").write_text("x\n", encoding="utf-8")
    rows = [{
        "source_wave": "wave1",
        "historical_game_id": "g1",
        "snapshot_record_id": "s1",
        "team_abbr": "AAA",
        "identity_matched": "1",
        "expected_minutes_available": "1",
        "expected_minutes": "30",
        "actual_classified_label_available": "1",
        "participation_label": "PLAYED",
        "actual_minutes": "31",
        "actual_role": "BENCH",
        "prior_games": "10",
    }]
    dataset = {
        "coverage": {
            "combined_selected_games": 1,
            "successful_official_source_games": 1,
            "source_missing_games": 0,
            "selected_player_snapshot_rows": 1,
            "matched_identity_rows": 1,
            "identity_match_rate": 1.0,
            "official_participation_join_rows": 1,
            "participation_label_join_rate_for_matched_players": 1.0,
            "unknown_rows": 0,
            "unknown_rate_for_matched_players": 0.0,
        },
        "quality": {
            "strict_prior_date_violations": 0,
            "duplicate_selected_games": 0,
            "duplicate_official_game_player_rows": 0,
            "team_mismatches": 0,
            "invalid_participation_labels": 0,
            "invalid_minutes_label_combinations": 0,
        },
        "decision": {"ready_for_expected_minutes_accuracy_audit_v2_execution": True},
    }
    participation = {
        "quality": {"all_structural_gates_passed": True},
        "decision": {"ready_for_expected_minutes_accuracy_audit_v2_inputs": True},
    }
    import_report = {
        "coverage": {"official_player_rows": 10},
        "decision": {"ready_for_player_participation_join": True},
    }
    combined = {
        "coverage": {
            "combined_independent_games": 1,
            "duplicate_games_across_waves": 0,
            "selected_source_wave_counts": {"wave1": 1},
        },
        "quality": {
            "game_identity_conflicts": 0,
            "selection_policy_conflicts": 0,
            "duplicate_output_games": 0,
        },
    }
    identity = [{
        "quality": {"ambiguous_player_rows": 0},
        "guardrails": {
            "fuzzy_edit_distance_matching_used": False,
            "nearest_name_guessing_used": False,
        },
    }]
    policy = {
        "structural_gates": {
            "required_combined_selected_games": 293,
            **PRESERVED_STRUCTURAL_THRESHOLDS,
        },
        "sample_thresholds": PRESERVED_SAMPLE_THRESHOLDS,
        "forbidden_player_level_filenames": ["official-player-participation-labels.csv"],
    }
    report = audit(
        rows, dataset, participation, import_report, combined, identity,
        policy, root, output_dir / "report",
    )
    assert report["decision_state"] == "STRUCTURAL_BLOCKED", report
    assert report["quality"]["forbidden_player_level_files_retained"] == 0, report
    assert not (root / "official-player-participation-labels.csv").exists()
    assert report["quality"]["accuracy_metrics_calculated"] is False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=Path)
    parser.add_argument("--dataset-report", type=Path)
    parser.add_argument("--participation-audit-report", type=Path)
    parser.add_argument("--participation-import-report", type=Path)
    parser.add_argument("--combined-report", type=Path)
    parser.add_argument("--identity-report", type=Path, action="append")
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--sensitive-root", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("expanded participation census self-test passed")
        return
    required = [
        args.rows,
        args.dataset_report,
        args.participation_audit_report,
        args.participation_import_report,
        args.combined_report,
        args.identity_report,
        args.policy,
        args.sensitive_root,
    ]
    if not all(required):
        parser.error("all census inputs are required")
    report = audit(
        read_csv(args.rows),
        read_json(args.dataset_report),
        read_json(args.participation_audit_report),
        read_json(args.participation_import_report),
        read_json(args.combined_report),
        [read_json(path) for path in args.identity_report],
        read_json(args.policy),
        args.sensitive_root,
        args.output_dir,
    )
    print(json.dumps({
        "decision_state": report["decision_state"],
        "coverage": report["coverage"],
        "structural_blockers": report["quality"]["structural_blockers"],
        "sample_blockers": report["quality"]["sample_blockers"],
        "decision": report["decision"],
    }, indent=2))
    if report["decision_state"] == "STRUCTURAL_BLOCKED":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
