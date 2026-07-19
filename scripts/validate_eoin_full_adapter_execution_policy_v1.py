#!/usr/bin/env python3
"""Validate Eoin full adapter execution policy v1 without executing the bundle."""
from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

POLICY_SCHEMA = "eoin-full-adapter-execution-policy-v1"
POLICY_STATE = "FULL_ADAPTER_EXECUTION_POLICY_PREDECLARED_EXECUTION_DISABLED"
READY_STATE = "FULL_ADAPTER_EXECUTION_POLICY_READY_FOR_IMPLEMENTATION_BUT_EXECUTION_DISABLED"
BLOCKED_STATE = "FULL_ADAPTER_EXECUTION_POLICY_BLOCKED"
PREFLIGHT_STATE = "FULL_ADAPTER_EXECUTION_PREFLIGHT_READY_BUT_DISABLED"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def require(condition: bool, name: str, failures: list[str]) -> None:
    if not condition:
        failures.append(name)


def validate(policy: dict[str, Any], preflight: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []

    require(policy.get("schema_version") == POLICY_SCHEMA, "policy.schema_version", failures)
    require(policy.get("formal_state") == POLICY_STATE, "policy.formal_state", failures)
    require(policy.get("source_id") == "kaggle_eoinamoore_historical_nba", "policy.source_id", failures)
    require(policy.get("adapter_version") == "eoin-role-limited-secondary-adapter-v1", "policy.adapter_version", failures)

    upstream = policy.get("upstream_requirements", {})
    require(upstream.get("preflight_policy") == "data/eoin-full-adapter-preflight-v1.json", "upstream.preflight_policy", failures)
    require(upstream.get("preflight_workflow") == ".github/workflows/validate-eoin-full-adapter-preflight-v1.yml", "upstream.preflight_workflow", failures)
    require(upstream.get("preflight_required_state") == PREFLIGHT_STATE, "upstream.preflight_required_state", failures)
    require(upstream.get("preflight_artifact_required") is True, "upstream.artifact_required", failures)
    require(upstream.get("preflight_artifact_digest_required") is True, "upstream.digest_required", failures)
    require(upstream.get("preflight_checks_failed_required") == 0, "upstream.checks_failed_required", failures)
    require(upstream.get("preflight_raw_rows_read_required") is False, "upstream.no_raw_rows_read", failures)
    require(upstream.get("preflight_raw_rows_emitted_required") == 0, "upstream.no_raw_rows_emitted", failures)
    require(upstream.get("preflight_raw_files_emitted_required") is False, "upstream.no_raw_files_emitted", failures)

    require(preflight.get("formal_state") == PREFLIGHT_STATE, "preflight.formal_state", failures)
    quality = preflight.get("quality", {})
    require(quality.get("checks_failed") == 0, "preflight.checks_failed", failures)
    require(quality.get("raw_rows_read") is False, "preflight.raw_rows_read", failures)
    require(quality.get("raw_rows_emitted") == 0, "preflight.raw_rows_emitted", failures)
    require(quality.get("raw_files_emitted") is False, "preflight.raw_files_emitted", failures)
    require(quality.get("formal_stake") == 0, "preflight.formal_stake", failures)
    decision = preflight.get("decision", {})
    require(decision.get("ready_for_full_adapter_execution_policy") is True, "preflight.policy_ready", failures)
    require(decision.get("ready_for_full_adapter_execution") is False, "preflight.execution_disabled", failures)
    require(decision.get("ready_for_market_backtest") is False, "preflight.market_disabled", failures)
    require(decision.get("ready_for_betting_edge_claim") is False, "preflight.edge_disabled", failures)

    boundary = policy.get("activation_boundary", {})
    expected_boundary = {
        "full_bundle_execution_enabled": False,
        "requires_future_explicit_user_approval": True,
        "requires_separate_execution_implementation_pr": True,
        "requires_green_policy_validation": True,
        "workflow_dispatch_only_when_later_enabled": True,
        "automatic_main_push_execution_allowed": False,
        "scheduled_execution_allowed": False,
        "concurrent_execution_allowed": False,
        "dataset_handle_locked": "eoinamoore/historical-nba-data-and-player-box-scores",
        "read_only_source_access": True,
        "temporary_actions_storage_only": True,
        "safe_extract_required": True,
        "deterministic_matching_only": True,
        "fuzzy_matching_allowed": False,
        "size_and_runtime_limits_must_be_frozen_before_implementation": True,
    }
    for key, expected in expected_boundary.items():
        require(boundary.get(key) == expected, f"boundary.{key}", failures)

    inputs = policy.get("allowed_runtime_inputs_when_later_enabled", {})
    expected_inputs = {"Games.csv", "TeamStatistics.csv", "PlayerStatistics.csv", "PlayByPlay.parquet"}
    require(set(inputs) == expected_inputs | {"other_files"}, "inputs.keys", failures)
    for key in expected_inputs:
        require(inputs.get(key) is True, f"inputs.{key}", failures)
    require(inputs.get("other_files") is False, "inputs.other_files", failures)

    temp = policy.get("temporary_private_material", {})
    require(temp.get("downloaded_archive_allowed_during_job") is True, "temp.archive_allowed", failures)
    require(temp.get("extracted_source_files_allowed_during_job") is True, "temp.extract_allowed", failures)
    require(temp.get("raw_source_rows_may_be_read_for_aggregate_calculation") is True, "temp.raw_read_for_aggregates", failures)
    require(temp.get("temporary_material_must_be_deleted_with_runner") is True, "temp.deleted_with_runner", failures)
    require(temp.get("temporary_material_may_be_committed") is False, "temp.no_commit", failures)
    require(temp.get("temporary_material_may_be_uploaded_as_artifact") is False, "temp.no_artifact", failures)

    public = policy.get("allowed_public_outputs", {})
    for key in ("aggregate_json_reports", "schema_metadata", "row_counts", "coverage_rates", "duplicate_group_counts", "hashes_and_file_sizes", "source_health_status"):
        require(public.get(key) is True, f"public.{key}", failures)
    for key in ("raw_game_rows", "raw_team_rows", "raw_player_rows", "raw_pbp_rows", "derived_game_id_lists", "full_csv_or_parquet_files", "full_sqlite_or_duckdb_files", "downloaded_archives"):
        require(public.get(key) is False, f"public.no_{key}", failures)

    forbidden = policy.get("forbidden_promotions", {})
    for key in (
        "historical_silver_replacement_allowed",
        "historical_gold_replacement_allowed",
        "player_stat_parity_claim_allowed",
        "player_stat_feature_import_allowed",
        "model_training_input_allowed",
        "model_retraining_allowed",
        "market_backtest_allowed",
        "clv_ev_roi_drawdown_allowed",
        "betting_decision_layer_allowed",
        "betting_edge_claim_allowed",
    ):
        require(forbidden.get(key) is False, f"forbidden.{key}", failures)
    require(forbidden.get("formal_stake") == 0, "forbidden.formal_stake", failures)

    next_state = policy.get("next_state_if_policy_validation_passes", {})
    require(next_state.get("formal_state") == READY_STATE, "next_state.formal_state", failures)
    require(next_state.get("ready_for_execution_implementation") is True, "next_state.implementation_ready", failures)
    for key in ("ready_for_full_adapter_execution", "ready_for_silver_replacement", "ready_for_gold_replacement", "ready_for_model_retraining", "ready_for_market_backtest", "ready_for_betting_edge_claim"):
        require(next_state.get(key) is False, f"next_state.no_{key}", failures)
    require(next_state.get("formal_stake") == 0, "next_state.formal_stake", failures)
    require(policy.get("decision_states") == [POLICY_STATE, BLOCKED_STATE, READY_STATE], "decision_states", failures)

    passed = not failures
    return {
        "schema_version": "eoin-full-adapter-execution-policy-validation-v1",
        "validated_at": utc_now(),
        "formal_state": READY_STATE if passed else BLOCKED_STATE,
        "quality": {
            "checks_failed": len(failures),
            "failed_checks": failures,
            "network_calls_made": False,
            "full_bundle_execution_performed": False,
            "raw_rows_read": False,
            "raw_rows_emitted": 0,
            "raw_files_emitted": False,
            "formal_stake": 0,
        },
        "decision": {
            "ready_for_execution_implementation": passed,
            "ready_for_full_adapter_execution": False,
            "ready_for_silver_replacement": False,
            "ready_for_gold_replacement": False,
            "ready_for_model_retraining": False,
            "ready_for_market_backtest": False,
            "ready_for_betting_edge_claim": False,
            "formal_stake": 0,
        },
    }


def self_test(policy: dict[str, Any], preflight: dict[str, Any]) -> None:
    base = validate(policy, preflight)
    assert base["formal_state"] == READY_STATE, base

    mutated = copy.deepcopy(policy)
    mutated["activation_boundary"]["full_bundle_execution_enabled"] = True
    blocked = validate(mutated, preflight)
    assert blocked["formal_state"] == BLOCKED_STATE, blocked
    assert "boundary.full_bundle_execution_enabled" in blocked["quality"]["failed_checks"], blocked

    mutated = copy.deepcopy(policy)
    mutated["forbidden_promotions"]["market_backtest_allowed"] = True
    blocked = validate(mutated, preflight)
    assert blocked["formal_state"] == BLOCKED_STATE, blocked

    mutated_preflight = copy.deepcopy(preflight)
    mutated_preflight["quality"]["raw_rows_emitted"] = 1
    blocked = validate(policy, mutated_preflight)
    assert blocked["formal_state"] == BLOCKED_STATE, blocked


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="data/eoin-full-adapter-execution-policy-v1.json")
    parser.add_argument("--preflight-report", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    policy = read_json(Path(args.policy))
    preflight = read_json(Path(args.preflight_report))
    if args.self_test:
        self_test(policy, preflight)

    report = validate(policy, preflight)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["formal_state"] == READY_STATE else 1


if __name__ == "__main__":
    raise SystemExit(main())
