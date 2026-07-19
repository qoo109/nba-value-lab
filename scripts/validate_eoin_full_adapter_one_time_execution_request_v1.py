#!/usr/bin/env python3
"""Validate a no-execution Eoin one-time full-adapter request packet."""
from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "eoin-full-adapter-one-time-execution-request-validation-v1"
READY_STATE = "ONE_TIME_EXECUTION_REQUEST_VALID_AWAITING_EXPLICIT_USER_APPROVAL"
BLOCKED_STATE = "ONE_TIME_EXECUTION_REQUEST_STRUCTURAL_BLOCKED"
REQUEST_STATE = "AWAITING_EXPLICIT_USER_APPROVAL"
REQUEST_ID = "EOIN-FULL-ADAPTER-2026-07-19-001"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("request packet root must be an object")
    return payload


def validate(packet: dict[str, Any]) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    checks["schema_version"] = packet.get("schema_version") == "eoin-full-adapter-one-time-execution-request-v1"
    checks["request_id"] = packet.get("request_id") == REQUEST_ID
    checks["request_state"] = packet.get("request_state") == REQUEST_STATE
    checks["source_and_handle"] = (
        packet.get("source_id") == "kaggle_eoinamoore_historical_nba"
        and packet.get("dataset_handle") == "eoinamoore/historical-nba-data-and-player-box-scores"
    )

    upstream = packet.get("upstream_evidence") or {}
    preflight = upstream.get("preflight") or {}
    policy = upstream.get("execution_policy") or {}
    runner = upstream.get("runner_implementation") or {}
    checks["preflight_evidence"] = (
        preflight.get("formal_state") == "FULL_ADAPTER_EXECUTION_PREFLIGHT_READY_BUT_DISABLED"
        and preflight.get("workflow_run_id") == 29677698906
        and preflight.get("artifact_id") == 8439486695
        and preflight.get("artifact_digest")
        == "sha256:39dd80ca107e2dc65f6bbba8012ba8b9ac40b60bd6a44db6f05cacb05a27d311"
    )
    checks["execution_policy_evidence"] = (
        policy.get("formal_state")
        == "FULL_ADAPTER_EXECUTION_POLICY_READY_FOR_IMPLEMENTATION_BUT_EXECUTION_DISABLED"
        and policy.get("workflow_run_id") == 29677971194
        and policy.get("artifact_id") == 8439578942
        and policy.get("artifact_digest")
        == "sha256:9b81c9ef61f1f9d19453b9e04a8e42cd362700ac86e79a4377328f24fdfe25a2"
    )
    checks["runner_evidence"] = (
        runner.get("formal_state")
        == "FULL_ADAPTER_RUNNER_READY_FOR_ONE_TIME_EXECUTION_APPROVAL_BUT_DISABLED"
        and runner.get("workflow_run_id") == 29679274470
        and runner.get("artifact_id") == 8440008401
        and runner.get("artifact_digest")
        == "sha256:15032709922439d062108994b08bfec76e815fb42443572c36e7d5db51d10331"
    )

    scope = packet.get("frozen_scope") or {}
    checks["one_time_scope"] = (
        scope.get("one_time_only") is True
        and scope.get("workflow_dispatch_only") is True
        and scope.get("automatic_main_push_execution_allowed") is False
        and scope.get("scheduled_execution_allowed") is False
        and scope.get("concurrent_execution_allowed") is False
        and scope.get("pilot_season") == "2023-24"
    )
    checks["required_files"] = scope.get("required_input_files") == [
        "Games.csv",
        "TeamStatistics.csv",
        "PlayerStatistics.csv",
        "PlayByPlay.parquet",
    ]
    checks["temporary_raw_boundary"] = (
        scope.get("temporary_raw_source_rows_may_be_read_if_later_approved") is True
        and scope.get("raw_rows_emitted") == 0
        and scope.get("raw_files_uploaded_as_artifact") is False
        and scope.get("silver_or_gold_replacement") is False
    )
    allowed_operations = set(scope.get("allowed_operations") or [])
    checks["allowed_operations"] = allowed_operations == {
        "download_public_dataset_to_temporary_storage",
        "validate_archive_inventory",
        "calculate_file_hashes_and_sizes",
        "read_schema_and_parquet_metadata",
        "calculate_aggregate_row_counts",
        "calculate_duplicate_key_groups",
        "calculate_deterministic_game_identity_coverage",
        "calculate_final_score_match_rate",
        "calculate_team_boxscore_coverage",
        "calculate_player_boxscore_candidate_coverage_only",
        "calculate_pbp_game_coverage",
        "emit_aggregate_validation_reports",
    }

    limits = packet.get("operational_limits") or {}
    checks["operational_limits"] = (
        limits.get("max_runtime_minutes") == 45
        and limits.get("max_concurrent_runs") == 1
        and limits.get("max_input_file_count") == 4
        and limits.get("max_total_input_bytes") == 10737418240
        and limits.get("max_single_input_file_bytes") == 8589934592
        and limits.get("max_public_output_bytes") == 10485760
        and limits.get("max_public_artifact_file_count") == 6
    )

    approval = packet.get("approval_boundary") or {}
    checks["approval_not_granted"] = (
        approval.get("explicit_user_approval_required") is True
        and approval.get("approval_granted") is False
        and approval.get("approved_by") is None
        and approval.get("approved_at") is None
        and approval.get("approval_record_sha256") is None
        and approval.get("execution_enabled") is False
    )
    template = str(approval.get("approval_text_template") or "")
    checks["approval_template"] = all(
        token in template
        for token in (
            REQUEST_ID,
            "one one-time aggregate-only Eoin full-adapter validation run",
            "does not authorize raw-row artifacts",
            "Formal Stake",
        )
    )
    acknowledgements = packet.get("required_user_acknowledgements") or []
    checks["acknowledgements"] = len(acknowledgements) == 6

    boundary = packet.get("execution_boundary") or {}
    checks["nothing_executed"] = (
        boundary.get("network_calls_made") == 0
        and boundary.get("full_bundle_execution_count") == 0
        and boundary.get("raw_eoin_rows_read") is False
        and boundary.get("raw_rows_emitted") == 0
        and boundary.get("raw_files_emitted") is False
    )
    checks["all_promotions_disabled"] = (
        boundary.get("ready_for_execution") is False
        and boundary.get("ready_for_silver_replacement") is False
        and boundary.get("ready_for_gold_replacement") is False
        and boundary.get("ready_for_model_retraining") is False
        and boundary.get("ready_for_market_backtest") is False
        and boundary.get("ready_for_betting_edge_claim") is False
        and boundary.get("formal_stake") == 0
    )

    next_state = packet.get("next_state_if_request_validation_passes") or {}
    checks["next_state"] = (
        next_state.get("formal_state") == READY_STATE
        and next_state.get("ready_for_user_approval") is True
        and next_state.get("ready_for_execution") is False
        and next_state.get("ready_for_silver_replacement") is False
        and next_state.get("ready_for_gold_replacement") is False
        and next_state.get("ready_for_model_retraining") is False
        and next_state.get("ready_for_market_backtest") is False
        and next_state.get("ready_for_betting_edge_claim") is False
        and next_state.get("formal_stake") == 0
    )
    checks["decision_states"] = packet.get("decision_states") == [BLOCKED_STATE, READY_STATE]

    failures = sorted(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": VERSION,
        "validated_at": utc_now(),
        "formal_state": READY_STATE if not failures else BLOCKED_STATE,
        "request_id": packet.get("request_id"),
        "checks": checks,
        "passed_checks": sum(checks.values()),
        "total_checks": len(checks),
        "failures": failures,
        "approval_boundary": {
            "request_state": packet.get("request_state"),
            "approval_granted": approval.get("approval_granted"),
            "execution_enabled": approval.get("execution_enabled"),
            "ready_for_user_approval": not failures,
            "ready_for_execution": False,
            "network_calls_made": boundary.get("network_calls_made"),
            "raw_eoin_rows_read": boundary.get("raw_eoin_rows_read"),
            "raw_rows_emitted": boundary.get("raw_rows_emitted"),
            "formal_stake": boundary.get("formal_stake"),
        },
    }


def self_test(packet: dict[str, Any]) -> None:
    report = validate(packet)
    assert report["formal_state"] == READY_STATE, report
    assert report["passed_checks"] == report["total_checks"], report

    mutated = copy.deepcopy(packet)
    mutated["approval_boundary"]["approval_granted"] = True
    assert validate(mutated)["formal_state"] == BLOCKED_STATE

    mutated = copy.deepcopy(packet)
    mutated["approval_boundary"]["execution_enabled"] = True
    assert validate(mutated)["formal_state"] == BLOCKED_STATE

    mutated = copy.deepcopy(packet)
    mutated["upstream_evidence"]["runner_implementation"]["artifact_digest"] = "sha256:bad"
    assert validate(mutated)["formal_state"] == BLOCKED_STATE


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    packet = load_json(args.packet)
    if args.self_test:
        self_test(packet)

    report = validate(packet)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["formal_state"] == READY_STATE else 1


if __name__ == "__main__":
    raise SystemExit(main())
