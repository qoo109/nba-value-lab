#!/usr/bin/env python3
"""Validate the one-time Legacy Market Archive real-file audit request.

This validator is policy-only. It performs no network calls, reads no real candidate
or reference rows, and never enables execution.
"""
from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REQUEST_SCHEMA = "user-supplied-legacy-market-archive-real-file-audit-execution-request-v1"
POLICY_SCHEMA = "user-supplied-legacy-market-archive-cross-source-audit-predeclaration-v1"
IMPLEMENTATION_SCHEMA = "user-supplied-legacy-market-archive-cross-source-audit-implementation-v1"
REQUEST_ID = "LEGACY-MARKET-ARCHIVE-AUDIT-2026-07-21-001"
SOURCE_ID = "kaggle_cviaxmiwnptr_nba_betting_data_user_supplied"
READY_STATE = "LEGACY_MARKET_ARCHIVE_REAL_FILE_AUDIT_REQUEST_VALID_AWAITING_EXPLICIT_USER_APPROVAL"
BLOCKED_STATE = "LEGACY_MARKET_ARCHIVE_REAL_FILE_AUDIT_REQUEST_STRUCTURAL_BLOCKED"

EXPECTED_CANDIDATE = {
    "dataset_handle": "cviaxmiwnptr/nba-betting-data-october-2007-to-june-2024",
    "file_name": "nba_2008-2026.csv",
    "file_bytes": 2493308,
    "file_sha256": "729eb2ead85c14affbb81ae9a4c611fee9790b8dd3d1d7824e1ddba14410a8c4",
    "row_count": 24440,
    "column_count": 27,
}
EXPECTED_SEASONS = [2019, 2020, 2021, 2022, 2023]
EXPECTED_LABELS = ["2019-20", "2020-21", "2021-22", "2022-23", "2023-24"]
EXPECTED_JOIN_KEY = ["game_date", "home_team_abbr", "away_team_abbr"]
EXPECTED_IMPLEMENTATION_STATE = (
    "USER_SUPPLIED_LEGACY_MARKET_ARCHIVE_CROSS_SOURCE_AUDIT_"
    "IMPLEMENTATION_READY_BUT_REAL_FILE_EXECUTION_DISABLED"
)
EXPECTED_POLICY_STATE = (
    "USER_SUPPLIED_LEGACY_MARKET_ARCHIVE_CROSS_SOURCE_AUDIT_PREDECLARATION_READY"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def add(checks: dict[str, bool], name: str, value: Any) -> None:
    checks[name] = bool(value)


def evaluate(
    request: dict[str, Any],
    policy: dict[str, Any],
    implementation: dict[str, Any],
    current: dict[str, Any],
) -> dict[str, Any]:
    checks: dict[str, bool] = {}

    add(checks, "request_schema", request.get("schema_version") == REQUEST_SCHEMA)
    add(checks, "request_id", request.get("request_id") == REQUEST_ID)
    add(checks, "request_source", request.get("source_id") == SOURCE_ID)
    add(checks, "request_awaiting_approval", request.get("request_state") == "AWAITING_EXPLICIT_USER_APPROVAL")

    upstream = request.get("upstream_evidence", {})
    predeclared = upstream.get("predeclaration", {})
    implemented = upstream.get("implementation", {})
    status_sync = upstream.get("status_sync", {})
    add(checks, "upstream_policy_state", predeclared.get("formal_state") == EXPECTED_POLICY_STATE)
    add(checks, "upstream_policy_pr", predeclared.get("merged_pr") == 105)
    add(checks, "upstream_implementation_state", implemented.get("formal_state") == EXPECTED_IMPLEMENTATION_STATE)
    add(checks, "upstream_implementation_pr", implemented.get("merged_pr") == 106)
    add(checks, "upstream_implementation_run", implemented.get("workflow_run_id") == 29798628467)
    add(checks, "upstream_implementation_artifact", implemented.get("artifact_id") == 8482916767)
    add(
        checks,
        "upstream_implementation_digest",
        implemented.get("artifact_digest")
        == "sha256:b6b7b9483b603dea278989c162ae0f3025e6df962f9f51571e465fbb26fe8c70",
    )
    add(checks, "upstream_self_tests", implemented.get("self_tests_passed") == implemented.get("self_tests_total") == 5)
    add(checks, "upstream_status_commit", status_sync.get("commit") == "5ce01fee19ed821bbfbfe3a5f5e89347ad15b957")

    candidate = request.get("frozen_candidate_identity", {})
    for key, expected in EXPECTED_CANDIDATE.items():
        add(checks, f"candidate_{key}", candidate.get(key) == expected)
    add(checks, "candidate_provenance_confirmed", candidate.get("provenance_status") == "user_confirmed")
    add(checks, "candidate_no_derived_substitution", candidate.get("cleaned_or_derived_substitution_allowed") is False)
    add(checks, "candidate_exact_identity", candidate.get("exact_identity_required") is True)

    reference = request.get("frozen_reference_scope", {})
    add(checks, "reference_years", reference.get("season_start_years") == EXPECTED_SEASONS)
    add(checks, "reference_labels", reference.get("season_labels") == EXPECTED_LABELS)
    add(checks, "reference_source", reference.get("reference_source_path") == "shufinskiy/nba_data")
    add(checks, "reference_rebuild_required", reference.get("reference_rebuild_required") is True)
    add(checks, "reference_temp_only", reference.get("reference_rebuild_location") == "temporary_workflow_storage_only")
    add(checks, "reference_no_db_artifact", reference.get("reference_database_artifact_upload_allowed") is False)

    contract = request.get("frozen_audit_contract", {})
    add(checks, "join_key", contract.get("join_key") == EXPECTED_JOIN_KEY)
    add(checks, "gold_silver_join", contract.get("gold_to_silver_join_key") == ["game_id"])
    add(checks, "no_fuzzy", contract.get("fuzzy_matching_allowed") is False)
    add(checks, "no_manual_override", contract.get("manual_key_overrides_allowed") is False)
    add(checks, "no_many_to_many", contract.get("many_to_many_join_allowed") is False)
    add(checks, "score_validation_only", contract.get("score_validation_only") is True)
    add(checks, "no_score_identity_repair", contract.get("score_used_to_repair_identity") is False)
    add(
        checks,
        "frozen_gate_source",
        contract.get("frozen_gates_source")
        == "data/research/user-supplied-legacy-market-archive-cross-source-audit-predeclaration-v1.json",
    )

    scope = request.get("one_time_execution_scope", {})
    add(checks, "one_time_only", scope.get("one_time_only") is True)
    add(checks, "dispatch_only", scope.get("workflow_dispatch_only") is True)
    add(checks, "no_main_push", scope.get("automatic_main_push_execution_allowed") is False)
    add(checks, "no_pull_request_execution", scope.get("pull_request_execution_allowed") is False)
    add(checks, "no_schedule", scope.get("scheduled_execution_allowed") is False)
    add(checks, "no_concurrency", scope.get("concurrent_execution_allowed") is False)
    add(checks, "max_execution_one", scope.get("maximum_execution_count") == 1)
    add(checks, "raw_rows_zero", scope.get("raw_rows_emitted") == 0)
    add(checks, "no_raw_artifact", scope.get("raw_files_uploaded_as_artifact") is False)
    add(checks, "no_reference_db_artifact", scope.get("reference_databases_uploaded_as_artifact") is False)
    add(checks, "no_source_archive_artifact", scope.get("source_archives_uploaded_as_artifact") is False)

    limits = request.get("operational_limits", {})
    add(checks, "runtime_limit", limits.get("maximum_runtime_minutes") == 300)
    add(checks, "concurrency_limit", limits.get("maximum_concurrent_runs") == 1)
    add(checks, "season_limit", limits.get("maximum_reference_seasons") == 5)
    add(checks, "single_archive_limit", limits.get("maximum_source_archive_bytes_each") == 629145600)
    add(checks, "temporary_input_limit", limits.get("maximum_total_temporary_input_bytes") == 10737418240)
    add(checks, "output_file_limit", limits.get("maximum_public_output_files") == 1)
    add(checks, "output_byte_limit", limits.get("maximum_public_output_bytes") == 1048576)
    add(checks, "retention_limit", limits.get("artifact_retention_days") == 14)

    approval = request.get("approval_boundary", {})
    add(checks, "approval_required", approval.get("explicit_user_approval_required") is True)
    add(checks, "approval_not_granted", approval.get("approval_granted") is False)
    add(checks, "approval_identity_empty", approval.get("approved_by") is None and approval.get("approved_at") is None)
    add(checks, "approval_record_empty", approval.get("approval_record") is None)
    add(checks, "execution_disabled", approval.get("execution_enabled") is False)
    add(checks, "approval_template_has_request_id", REQUEST_ID in str(approval.get("approval_text_template", "")))
    add(checks, "approval_template_stake_zero", "Stake" in str(approval.get("approval_text_template", "")) and "0" in str(approval.get("approval_text_template", "")))

    boundary = request.get("current_execution_boundary", {})
    add(checks, "network_not_called", boundary.get("network_calls_made") == 0)
    add(checks, "execution_count_zero", boundary.get("real_file_execution_count") == 0)
    add(checks, "candidate_not_read", boundary.get("candidate_rows_read") is False)
    add(checks, "reference_not_read", boundary.get("reference_rows_read") is False)
    add(checks, "boundary_raw_rows_zero", boundary.get("raw_rows_emitted") == 0)
    add(checks, "boundary_raw_files_false", boundary.get("raw_files_emitted") is False)
    add(checks, "boundary_execution_false", boundary.get("ready_for_execution") is False)
    add(checks, "boundary_market_false", boundary.get("ready_for_point_in_time_market_backtest") is False)
    add(checks, "boundary_model_false", boundary.get("ready_for_model_retraining") is False)
    add(checks, "boundary_edge_false", boundary.get("ready_for_betting_edge_claim") is False)
    add(checks, "boundary_stake_zero", boundary.get("formal_stake") == 0)

    next_state = request.get("next_state_if_request_validation_passes", {})
    add(checks, "next_state", next_state.get("formal_state") == READY_STATE)
    add(checks, "ready_for_user_approval", next_state.get("ready_for_user_approval") is True)
    add(checks, "not_ready_for_execution", next_state.get("ready_for_execution") is False)
    add(checks, "next_not_executed", next_state.get("real_file_audit_executed") is False)
    add(checks, "next_role_unchanged", next_state.get("source_role_changed") is False)
    add(checks, "next_market_false", next_state.get("ready_for_point_in_time_market_backtest") is False)
    add(checks, "next_model_false", next_state.get("ready_for_model_retraining") is False)
    add(checks, "next_edge_false", next_state.get("ready_for_betting_edge_claim") is False)
    add(checks, "next_stake_zero", next_state.get("formal_stake") == 0)
    add(checks, "decision_states", request.get("decision_states") == [BLOCKED_STATE, READY_STATE])

    add(checks, "policy_schema", policy.get("schema_version") == POLICY_SCHEMA)
    add(
        checks,
        "policy_ready",
        policy.get("next_state_if_validation_passes", {}).get("formal_state") == EXPECTED_POLICY_STATE,
    )
    add(checks, "policy_join_key", policy.get("deterministic_join_contract", {}).get("join_key") == EXPECTED_JOIN_KEY)
    add(checks, "policy_no_fuzzy", policy.get("deterministic_join_contract", {}).get("fuzzy_matching_allowed") is False)
    frozen_gates = policy.get("frozen_execution_gates", {})
    add(checks, "policy_reference_games", frozen_gates.get("minimum_reference_games") == 5700)
    add(checks, "policy_candidate_games", frozen_gates.get("minimum_candidate_eligible_games") == 5700)
    add(checks, "policy_reference_match", frozen_gates.get("minimum_reference_match_rate") == 0.985)
    add(checks, "policy_candidate_match", frozen_gates.get("minimum_candidate_match_rate") == 0.985)
    add(checks, "policy_score_match", frozen_gates.get("minimum_matched_score_pair_rate") == 0.99)
    add(checks, "policy_season_match", frozen_gates.get("minimum_each_season_reference_match_rate") == 0.97)

    add(checks, "implementation_schema", implementation.get("schema_version") == IMPLEMENTATION_SCHEMA)
    add(checks, "implementation_source", implementation.get("source_id") == SOURCE_ID)
    add(checks, "implementation_exact_hash", implementation.get("candidate_input", {}).get("file_sha256") == EXPECTED_CANDIDATE["file_sha256"])
    add(checks, "implementation_no_network", implementation.get("validation_mode", {}).get("network_calls") is False)
    add(checks, "implementation_not_executed", implementation.get("validation_mode", {}).get("real_file_audit_executed") is False)
    add(checks, "implementation_ready_request", implementation.get("next_state_if_validation_passes", {}).get("ready_for_separate_real_file_execution_request") is True)
    add(checks, "implementation_execution_disabled", implementation.get("downstream_permissions", {}).get("ready_for_real_file_audit_execution") is False)
    add(checks, "implementation_stake_zero", implementation.get("downstream_permissions", {}).get("formal_stake") == 0)

    add(checks, "current_source", current.get("source_id") == SOURCE_ID)
    add(checks, "current_role", current.get("current_formal_outcome") == "ROLE_LIMITED_LEGACY_MARKET_ARCHIVE_ELIGIBLE")
    add(checks, "current_implementation_state", current.get("cross_source_audit_implementation", {}).get("formal_state") == EXPECTED_IMPLEMENTATION_STATE)
    add(checks, "current_not_executed", current.get("real_cross_source_audit_executed") is False)
    add(checks, "current_stake_zero", current.get("formal_stake") == 0)

    failed = sorted(name for name, passed in checks.items() if not passed)
    formal_state = READY_STATE if not failed else BLOCKED_STATE
    return {
        "schema_version": "user-supplied-legacy-market-archive-real-file-audit-execution-request-validation-report-v1",
        "validated_at": utc_now(),
        "request_id": request.get("request_id"),
        "source_id": request.get("source_id"),
        "formal_state": formal_state,
        "checks": checks,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "checks_failed": len(failed),
        "failed_checks": failed,
        "quality": {
            "network_calls_made": False,
            "real_candidate_csv_read": False,
            "real_reference_database_read": False,
            "external_artifacts_downloaded": False,
            "real_file_audit_executed": False,
            "raw_rows_emitted": 0,
            "raw_files_emitted": False,
            "execution_enabled": False,
            "source_role_changed": False,
            "formal_stake": 0,
        },
        "decision": {
            "ready_for_explicit_user_approval": formal_state == READY_STATE,
            "ready_for_execution": False,
            "ready_for_point_in_time_market_backtest": False,
            "ready_for_model_retraining": False,
            "ready_for_betting_edge_claim": False,
            "formal_stake": 0,
        },
    }


def run_self_tests(
    request: dict[str, Any],
    policy: dict[str, Any],
    implementation: dict[str, Any],
    current: dict[str, Any],
) -> dict[str, bool]:
    baseline = evaluate(request, policy, implementation, current)
    assert baseline["formal_state"] == READY_STATE, baseline

    cases: dict[str, tuple[list[str], Any]] = {
        "approval_drift_blocks": (["approval_boundary", "approval_granted"], True),
        "scheduled_execution_blocks": (["one_time_execution_scope", "scheduled_execution_allowed"], True),
        "candidate_hash_drift_blocks": (["frozen_candidate_identity", "file_sha256"], "0" * 64),
        "raw_artifact_permission_blocks": (["one_time_execution_scope", "raw_files_uploaded_as_artifact"], True),
        "nonzero_stake_blocks": (["current_execution_boundary", "formal_stake"], 1),
        "gate_drift_blocks": (["minimum_reference_match_rate"], 0.90),
    }
    results: dict[str, bool] = {"baseline_passes": True}
    for name, (path, value) in cases.items():
        request_copy = copy.deepcopy(request)
        policy_copy = copy.deepcopy(policy)
        target = request_copy
        if name == "gate_drift_blocks":
            target = policy_copy["frozen_execution_gates"]
            target[path[0]] = value
        else:
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
        report = evaluate(request_copy, policy_copy, implementation, current)
        results[name] = report["formal_state"] == BLOCKED_STATE
    assert all(results.values()), results
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--implementation", type=Path, required=True)
    parser.add_argument("--current-status", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    request = load_json(args.request)
    policy = load_json(args.policy)
    implementation = load_json(args.implementation)
    current = load_json(args.current_status)
    report = evaluate(request, policy, implementation, current)
    if args.self_test:
        report["self_tests"] = run_self_tests(request, policy, implementation, current)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if len(payload.encode("utf-8")) > 1048576:
        raise RuntimeError("validation report exceeds 1 MiB boundary")
    args.output.write_text(payload, encoding="utf-8")
    print(json.dumps({
        "formal_state": report["formal_state"],
        "checks_passed": report["checks_passed"],
        "checks_total": report["checks_total"],
        "ready_for_explicit_user_approval": report["decision"]["ready_for_explicit_user_approval"],
        "ready_for_execution": report["decision"]["ready_for_execution"],
        "formal_stake": report["decision"]["formal_stake"],
    }, indent=2))
    return 0 if report["formal_state"] == READY_STATE else 1


if __name__ == "__main__":
    raise SystemExit(main())
