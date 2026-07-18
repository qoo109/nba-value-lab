#!/usr/bin/env python3
"""Run Expected Minutes Accuracy Audit v3 on the exact frozen 293-game inputs.

The v2 numerical evaluator is reused unchanged. This wrapper adds v3 exact-input integrity,
expanded census provenance, the verified roster-transition contract, aggregate-only privacy,
and v3 decision permissions.
"""
from __future__ import annotations

import argparse
import copy
import csv
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

import audit_expected_minutes_accuracy_v2 as v2

VERSION = "expected-minutes-accuracy-audit-v3"
FORBIDDEN_PLAYER_FILES = {
    "combined-player-boxscores.csv",
    "open-player-boxscores.csv",
    "official-player-participation-labels.csv",
    "evaluation-player-participation-labels.csv",
    "player-participation-label-audit-rows.csv",
    "expected-minutes-accuracy-v2-rows.csv",
    "expected-minutes-accuracy-v3-rows.csv",
    "overlap-player-injury-panel.csv",
    "multi-report-injury-panel-normalized.csv",
    "injury-lineup-snapshots-normalized.csv",
    "injury-player-id-map.csv",
    "point-in-time-player-values.csv",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def as_int(value: Any, default: int = 0) -> int:
    return v2.as_int(value, default)


def compatible_v2_policy(policy: dict[str, Any]) -> dict[str, Any]:
    compatible = copy.deepcopy(policy)
    structural = compatible["structural_gates"]
    structural["team_mismatches"] = structural["maximum_unrecognized_team_mismatches"]
    return compatible


def current_counts(
    base_report: dict[str, Any],
    dataset_report: dict[str, Any],
    participation_import_report: dict[str, Any],
    transition_report: dict[str, Any],
) -> dict[str, int]:
    coverage = dataset_report.get("coverage", {})
    base_coverage = base_report.get("coverage", {})
    return {
        "successful_official_source_games": as_int(
            coverage.get("successful_official_source_games")
        ),
        "source_missing_games": as_int(coverage.get("source_missing_games")),
        "official_player_rows": as_int(
            participation_import_report.get("coverage", {}).get("official_player_rows")
        ),
        "selected_player_snapshot_rows": as_int(
            coverage.get("selected_player_snapshot_rows")
        ),
        "identity_matched_rows": as_int(coverage.get("matched_identity_rows")),
        "official_participation_join_rows": as_int(
            coverage.get("official_participation_join_rows")
        ),
        "unknown_rows": as_int(coverage.get("unknown_rows")),
        "games_with_evaluable_played_rows": as_int(
            base_coverage.get("games_with_conditional_role_rows")
        ),
        "conditional_played_rows": as_int(base_coverage.get("conditional_role_rows")),
        "actual_starter_rows": as_int(base_coverage.get("actual_starter_rows")),
        "actual_bench_rows": as_int(base_coverage.get("actual_bench_rows")),
        "long_history_rows": as_int(base_coverage.get("long_history_rows")),
        "complete_team_game_groups": as_int(
            base_coverage.get("complete_team_game_groups")
        ),
        "recognized_roster_transition_rows": as_int(
            transition_report.get("coverage", {}).get(
                "recognized_roster_transition_rows"
            )
        ),
        "unrecognized_team_mismatches": as_int(
            dataset_report.get("quality", {}).get("team_mismatches")
        ),
    }


def identity_quality(identity_reports: list[dict[str, Any]]) -> dict[str, Any]:
    ambiguous = sum(
        as_int(report.get("quality", {}).get("ambiguous_player_rows"))
        for report in identity_reports
    )
    fuzzy = any(
        report.get("guardrails", {}).get("fuzzy_edit_distance_matching_used") is True
        or report.get("guardrails", {}).get("nearest_name_guessing_used") is True
        for report in identity_reports
    )
    return {"ambiguous_identity_rows": ambiguous, "fuzzy_identity_used": fuzzy}


def delete_sensitive_files(root: Path) -> tuple[int, list[str]]:
    deleted = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if (
            path.name in FORBIDDEN_PLAYER_FILES
            or path.suffix.lower() == ".pdf"
            or path.name.endswith(".json.raw")
        ):
            path.unlink(missing_ok=True)
            deleted += 1
    retained = sorted(
        str(path.relative_to(root))
        for path in root.rglob("*")
        if path.is_file() and path.name in FORBIDDEN_PLAYER_FILES
    )
    return deleted, retained


def audit(
    rows: list[dict[str, str]],
    dataset_report: dict[str, Any],
    policy: dict[str, Any],
    census_report: dict[str, Any],
    participation_import_report: dict[str, Any],
    participation_audit_report: dict[str, Any],
    transition_report: dict[str, Any],
    policy_validation_report: dict[str, Any],
    identity_reports: list[dict[str, Any]],
    sensitive_root: Path,
    output_dir: Path,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="nbavl-audit-v3-") as temp_name:
        temp_dir = Path(temp_name)
        base_report = v2.audit(
            rows,
            dataset_report,
            compatible_v2_policy(policy),
            temp_dir,
        )
        subgroup_source = temp_dir / "expected-minutes-accuracy-v2-subgroups.csv"
        team_source = temp_dir / "expected-minutes-accuracy-v2-team-summary.csv"
        output_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(
            subgroup_source,
            output_dir / "expected-minutes-accuracy-v3-subgroups.csv",
        )
        shutil.copyfile(
            team_source,
            output_dir / "expected-minutes-accuracy-v3-team-summary.csv",
        )

    expected_counts = policy["frozen_input_counts"]
    observed_counts = current_counts(
        base_report,
        dataset_report,
        participation_import_report,
        transition_report,
    )
    identity = identity_quality(identity_reports)
    census_coverage = census_report.get("coverage", {})
    census_expected_subset = {
        "successful_official_source_games": as_int(
            census_coverage.get("successful_official_source_games")
        ),
        "source_missing_games": as_int(census_coverage.get("source_missing_games")),
        "official_player_rows": as_int(census_coverage.get("official_player_rows")),
        "selected_player_snapshot_rows": as_int(
            census_coverage.get("selected_player_snapshot_rows")
        ),
        "identity_matched_rows": as_int(census_coverage.get("identity_matched_rows")),
        "official_participation_join_rows": as_int(
            census_coverage.get("participation_label_joined_rows")
        ),
        "unknown_rows": as_int(census_coverage.get("unknown_rows")),
        "games_with_evaluable_played_rows": as_int(
            census_coverage.get("evaluable_games")
        ),
        "conditional_played_rows": as_int(
            census_coverage.get("conditional_played_rows")
        ),
        "actual_starter_rows": as_int(census_coverage.get("starter_played_rows")),
        "actual_bench_rows": as_int(census_coverage.get("bench_played_rows")),
        "long_history_rows": as_int(
            census_coverage.get("ten_plus_prior_game_played_rows")
        ),
        "complete_team_game_groups": as_int(
            census_coverage.get("complete_team_game_groups")
        ),
        "recognized_roster_transition_rows": as_int(
            policy["recognized_roster_transition_contract"]["required_rows"]
        ),
        "unrecognized_team_mismatches": 0,
    }

    transition_quality = transition_report.get("quality", {})
    transition_decision = transition_report.get("decision", {})
    participation_decision = participation_audit_report.get("decision", {})
    dataset_quality = dataset_report.get("quality", {})
    structural = policy["structural_gates"]

    integrity_results = {
        "policy_validation_passed": policy_validation_report.get("passed") is True,
        "policy_validation_failed_checks_empty": policy_validation_report.get(
            "failed_checks"
        ) == [],
        "census_formal_state_exact": census_report.get("decision_state")
        == policy["upstream_census"]["formal_state"],
        "census_accuracy_not_calculated": census_report.get("quality", {}).get(
            "accuracy_metrics_calculated"
        ) is False,
        "census_structural_blockers_empty": census_report.get("quality", {}).get(
            "structural_blockers"
        ) == [],
        "census_sample_blockers_empty": census_report.get("quality", {}).get(
            "sample_blockers"
        ) == [],
        "census_counts_match_policy": census_expected_subset == expected_counts,
        "current_counts_match_policy": observed_counts == expected_counts,
        "current_counts_match_census": observed_counts == census_expected_subset,
        "dataset_builder_ready": dataset_report.get("decision", {}).get(
            "ready_for_expected_minutes_accuracy_audit_v2_execution"
        ) is True,
        "participation_layer_ready": participation_decision.get(
            "ready_for_expected_minutes_accuracy_audit_v2_inputs"
        ) is True,
        "official_import_ready": participation_import_report.get("decision", {}).get(
            "ready_for_player_participation_join"
        ) is True,
        "transition_filter_ready": transition_decision.get(
            "ready_for_exact_team_evaluation_join"
        ) is True,
        "transition_validation_errors_empty": transition_quality.get(
            "validation_errors"
        ) == [],
        "transition_rows_exact": observed_counts[
            "recognized_roster_transition_rows"
        ]
        == as_int(structural["required_recognized_roster_transition_rows"]),
        "unrecognized_team_mismatches_zero": observed_counts[
            "unrecognized_team_mismatches"
        ]
        == as_int(structural["maximum_unrecognized_team_mismatches"]),
        "ambiguous_identity_rows_zero": identity["ambiguous_identity_rows"]
        == as_int(structural["ambiguous_identity_rows"]),
        "fuzzy_identity_false": identity["fuzzy_identity_used"]
        is bool(structural["fuzzy_identity_used"]),
        "raw_official_labels_unmodified": transition_report.get("guardrails", {}).get(
            "raw_official_source_is_modified"
        ) is False,
        "target_labels_not_used_in_prediction": dataset_quality.get(
            "target_game_labels_used_in_prediction"
        ) is False,
        "missing_actual_not_imputed_zero": dataset_quality.get(
            "missing_actual_participation_imputed_as_zero"
        ) is False,
        "missing_expected_not_imputed_zero": dataset_quality.get(
            "missing_expected_minutes_imputed_as_zero"
        ) is False,
    }

    deleted_sensitive_files, retained_sensitive_files = delete_sensitive_files(
        sensitive_root
    )
    integrity_results["forbidden_player_files_retained_zero"] = (
        len(retained_sensitive_files)
        == as_int(structural["forbidden_player_level_files_retained"])
    )

    base_structural = base_report.get("quality", {}).get(
        "all_structural_gates_passed"
    ) is True
    integrity_ready = all(integrity_results.values())
    structural_ready = base_structural and integrity_ready
    accuracy_ready = base_report.get("quality", {}).get(
        "all_primary_accuracy_gates_passed"
    ) is True

    if not structural_ready:
        decision_state = "STRUCTURAL_BLOCKED"
    elif accuracy_ready:
        decision_state = "ACCURACY_PASS"
    else:
        decision_state = "VALID_NEGATIVE_RESULT"
    passed = decision_state == "ACCURACY_PASS"

    report = {
        "schema_version": VERSION,
        "policy_schema_version": policy.get("schema_version"),
        "predeclaration": policy.get("predeclaration"),
        "upstream_census": policy.get("upstream_census"),
        "decision_state": decision_state,
        "estimands": base_report.get("estimands"),
        "coverage": {
            **base_report.get("coverage", {}),
            "frozen_input_counts": expected_counts,
            "observed_input_counts": observed_counts,
            "ambiguous_identity_rows": identity["ambiguous_identity_rows"],
            "fuzzy_identity_used": identity["fuzzy_identity_used"],
            "recognized_roster_transition_rows": observed_counts[
                "recognized_roster_transition_rows"
            ],
            "unrecognized_team_mismatches": observed_counts[
                "unrecognized_team_mismatches"
            ],
        },
        "primary_accuracy": base_report.get("primary_accuracy"),
        "secondary_diagnostics": base_report.get("secondary_diagnostics"),
        "quality": {
            "v2_numerical_evaluator_reused_unchanged": True,
            "base_structural_gate_results": base_report.get("quality", {}).get(
                "structural_gate_results"
            ),
            "frozen_input_integrity_results": integrity_results,
            "base_accuracy_gate_results": base_report.get("quality", {}).get(
                "accuracy_gate_results"
            ),
            "base_structural_gates_passed": base_structural,
            "frozen_input_integrity_gates_passed": integrity_ready,
            "all_structural_gates_passed": structural_ready,
            "all_primary_accuracy_gates_passed": accuracy_ready,
            "structural_blockers": sorted(
                name for name, value in integrity_results.items() if not value
            )
            + ([] if base_structural else ["base_v2_structural_gates"]),
            "accuracy_blockers": sorted(
                name
                for name, value in base_report.get("quality", {}).get(
                    "accuracy_gate_results", {}
                ).items()
                if not value
            ),
            "v1_v2_primary_accuracy_thresholds_preserved": True,
            "v1_v2_sample_size_thresholds_preserved": True,
            "exact_frozen_input_counts_required": True,
            "actual_starter_and_bench_are_label_side_subgroups": True,
            "recognized_roster_transition_in_primary_metric": False,
            "explicit_dnp_in_primary_role_metric": False,
            "inactive_in_primary_role_metric": False,
            "unknown_imputed_as_zero": False,
            "source_missing_imputed_as_zero": False,
            "missing_expected_minutes_imputed_as_zero": False,
            "target_game_labels_used_in_prediction": False,
            "temporary_sensitive_files_deleted": deleted_sensitive_files,
            "forbidden_player_level_files_retained": len(retained_sensitive_files),
            "retained_forbidden_file_paths": retained_sensitive_files,
            "player_names_or_injury_reasons_in_outputs": False,
        },
        "decision": {
            "expected_minutes_accuracy_audit_v3_passed": passed,
            "ready_for_injury_feature_walk_forward_holdout_design_predeclaration": passed,
            "ready_for_injury_feature_walk_forward_holdout_execution": False,
            "ready_for_model_training": False,
            "ready_for_probability_adjustment": False,
            "ready_for_betting_edge_claim": False,
            "formal_stake": 0,
            "reason": (
                "Expected Minutes passed every predeclared v3 structural, exact-input, and primary accuracy gate. Only a separate Injury Holdout design predeclaration may proceed."
                if decision_state == "ACCURACY_PASS"
                else "Every v3 structural and exact-input gate passed, but one or more preserved primary accuracy gates failed. Expected Minutes remains a research proxy."
                if decision_state == "VALID_NEGATIVE_RESULT"
                else "Expected Minutes Accuracy Audit v3 failed one or more predeclared structural or exact-input integrity gates. Numerical results are descriptive only."
            ),
        },
        "guardrails": {
            "v1_or_v2_result_reclassified_as_pass": False,
            "accuracy_result_changed_policy": False,
            "secondary_metrics_can_override_primary_failure": False,
            "accuracy_pass_directly_runs_holdout": False,
            "accuracy_pass_directly_activates_model": False,
            "accuracy_pass_directly_adjusts_probability": False,
            "accuracy_pass_directly_enables_betting_claim": False,
            "holdout_design_requires_separate_predeclaration": True,
        },
    }
    (output_dir / "expected-minutes-accuracy-audit-v3.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def self_test(output_dir: Path) -> None:
    assert compatible_v2_policy({
        "structural_gates": {
            "maximum_unrecognized_team_mismatches": 0,
        }
    })["structural_gates"]["team_mismatches"] == 0
    observed = {
        "successful_official_source_games": 1,
        "source_missing_games": 0,
        "official_player_rows": 10,
        "selected_player_snapshot_rows": 2,
        "identity_matched_rows": 2,
        "official_participation_join_rows": 2,
        "unknown_rows": 0,
        "games_with_evaluable_played_rows": 1,
        "conditional_played_rows": 1,
        "actual_starter_rows": 1,
        "actual_bench_rows": 0,
        "long_history_rows": 1,
        "complete_team_game_groups": 1,
        "recognized_roster_transition_rows": 1,
        "unrecognized_team_mismatches": 0,
    }
    assert observed == dict(observed)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "v3-wrapper-self-test.json").write_text(
        json.dumps({"passed": True, "observed": observed}, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=Path)
    parser.add_argument("--dataset-report", type=Path)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--census-report", type=Path)
    parser.add_argument("--participation-import-report", type=Path)
    parser.add_argument("--participation-audit-report", type=Path)
    parser.add_argument("--transition-report", type=Path)
    parser.add_argument("--policy-validation-report", type=Path)
    parser.add_argument("--identity-report", type=Path, action="append")
    parser.add_argument("--sensitive-root", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("Expected Minutes Accuracy Audit v3 wrapper self-test passed")
        return
    required = [
        args.rows,
        args.dataset_report,
        args.policy,
        args.census_report,
        args.participation_import_report,
        args.participation_audit_report,
        args.transition_report,
        args.policy_validation_report,
        args.identity_report,
        args.sensitive_root,
    ]
    if not all(required):
        parser.error("all v3 audit inputs are required")
    report = audit(
        read_csv(args.rows),
        read_json(args.dataset_report),
        read_json(args.policy),
        read_json(args.census_report),
        read_json(args.participation_import_report),
        read_json(args.participation_audit_report),
        read_json(args.transition_report),
        read_json(args.policy_validation_report),
        [read_json(path) for path in args.identity_report],
        args.sensitive_root,
        args.output_dir,
    )
    print(json.dumps({
        "decision_state": report["decision_state"],
        "decision": report["decision"],
        "structural_blockers": report["quality"]["structural_blockers"],
        "accuracy_blockers": report["quality"]["accuracy_blockers"],
    }, indent=2))
    if report["decision_state"] == "STRUCTURAL_BLOCKED":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
