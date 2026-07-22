#!/usr/bin/env python3
"""Validate the design-only real-reference validation request contract v1."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

EXPECTED_SCHEMA = "historical-silver-2023-24-source-gap-exception-integration-real-reference-validation-request-design-v1"
EXPECTED_STATE = "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_REAL_REFERENCE_VALIDATION_REQUEST_DESIGN_READY"
NEXT_STATE = "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_REAL_REFERENCE_VALIDATION_REQUEST_READY_FOR_DRAFT"
PROHIBITED_OUTPUT_FIELDS = {
    "game_id", "game_date", "home_team_abbr", "away_team_abbr", "team_code",
    "source_file_path", "source_file_hash", "row_level_record", "row_key_hash",
}


class DesignValidationError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DesignValidationError(message)


def validate(payload: dict[str, Any]) -> list[str]:
    checks: list[str] = []

    def check(condition: bool, name: str) -> None:
        require(condition, name)
        checks.append(name)

    check(payload.get("schema_version") == EXPECTED_SCHEMA, "schema_version")
    check(payload.get("formal_state") == EXPECTED_STATE, "formal_state")
    check(payload.get("design_role") == "ONE_TIME_AGGREGATE_ONLY_REAL_REFERENCE_VALIDATION_REQUEST_CONTRACT", "design_role")
    check(payload.get("triggering_state") == "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_IMPLEMENTATION_VALIDATED_SYNTHETIC_ONLY", "triggering_state")

    request = payload["future_request_contract"]
    check(request["maximum_execution_count"] == 1, "maximum_execution_count")
    check(request["initial_execution_count"] == 0, "initial_execution_count")
    check(request["workflow_dispatch_only"] is True, "workflow_dispatch_only")
    check(request["explicit_user_approval_required"] is True, "explicit_user_approval_required")
    check(request["approval_must_be_separate_from_request"] is True, "approval_separation")
    check(request["approval_must_bind_exact_request_id"] is True, "request_id_binding")
    check(request["approval_must_bind_exact_request_file_sha256"] is True, "request_hash_binding")
    check(request["approval_must_bind_exact_implementation_file_sha256"] is True, "implementation_hash_binding")
    check(request["request_reuse_after_any_execution_attempt"] is False, "request_reuse_disabled")
    check(request["automatic_dispatch_allowed"] is False, "automatic_dispatch_disabled")

    inputs = payload["allowed_real_reference_inputs"]
    check(inputs["input_role"] == "COMMITTED_AGGREGATE_RECORDS_ONLY", "aggregate_inputs_only")
    for key in ("database_files_allowed", "source_archives_allowed", "raw_csv_allowed", "raw_rows_allowed", "network_download_allowed", "temporary_reference_rebuild_allowed"):
        check(inputs[key] is False, f"input_boundary_{key}")

    scope = payload["validation_scope"]
    check(scope["execute_transformer_once"] is True, "single_transform")
    check(scope["expected_raw_silver_game_count"] == 5826, "silver_count")
    check(scope["expected_raw_gold_matchup_count"] == 5824, "gold_count")
    check(scope["expected_raw_missing_gold_for_silver"] == 2, "raw_gap")
    check(scope["expected_documented_exception_count"] == 2, "documented_count")
    check(scope["expected_unexplained_missing_count"] == 0, "unexplained_count")
    check(scope["expected_covered_or_documented_count"] == 5826, "covered_or_documented")
    check(scope["expected_gold_dataset_complete"] is False, "gold_incomplete")
    check(scope["expected_recognition_gate_passed"] is True, "recognition_expected")
    check(scope["preserve_raw_report_without_mutation"] is True, "raw_preserved")
    check(scope["fail_closed_on_any_mismatch"] is True, "fail_closed")
    check(scope["partial_recognition_allowed"] is False, "partial_recognition_disabled")

    output = payload["allowed_output"]
    check(output["single_json_artifact_only"] is True, "single_artifact")
    check(output["aggregate_only"] is True, "aggregate_output")
    check(output["maximum_output_bytes"] == 1048576, "output_size_limit")
    check(set(output["prohibited_fields"]) == PROHIBITED_OUTPUT_FIELDS, "prohibited_fields")

    separation = payload["approval_and_execution_separation"]
    for key in ("this_design_grants_approval", "this_design_enables_execution", "future_request_grants_approval", "future_request_enables_execution"):
        check(separation[key] is False, f"separation_{key}")
    check(separation["future_approval_may_enable_exactly_one_manual_dispatch"] is True, "future_single_manual_dispatch")
    check(separation["manual_dispatch_must_use_main"] is True, "main_only")
    check(separation["manual_dispatch_before_approval_validation"] is False, "dispatch_before_approval_disabled")

    non_auth = payload["non_authorizations"]
    check(all(value is False for value in non_auth.values()), "all_non_authorizations_false")

    design_validation = payload["design_validation_requirements"]
    check(design_validation["synthetic_request_fixture_tests_required"] is True, "synthetic_tests_required")
    check(design_validation["mutation_tests_required"] is True, "mutation_tests_required")
    check(design_validation["minimum_mutation_test_count"] >= 10, "minimum_mutations")
    check(design_validation["validate_no_execution_workflow_created"] is True, "no_execution_workflow")
    check(design_validation["validate_no_approval_record_created"] is True, "no_approval_record")
    check(design_validation["validate_no_real_reference_transform_executed"] is True, "no_real_execution")
    check(design_validation["validate_formal_stake_zero"] is True, "stake_validation")

    next_state = payload["next_state_if_valid"]
    check(next_state["next_research_step"] == NEXT_STATE, "next_state")
    check(next_state["ready_for_request_draft"] is True, "request_draft_ready")
    check(next_state["ready_for_explicit_user_approval"] is False, "approval_not_ready")
    check(next_state["ready_for_real_reference_validation_execution"] is False, "execution_not_ready")
    check(next_state["formal_stake"] == 0, "formal_stake_zero")
    return checks


def run_mutation_tests(payload: dict[str, Any]) -> int:
    mutations = [
        lambda p: p.update(schema_version="wrong"),
        lambda p: p["future_request_contract"].update(maximum_execution_count=2),
        lambda p: p["future_request_contract"].update(initial_execution_count=1),
        lambda p: p["future_request_contract"].update(explicit_user_approval_required=False),
        lambda p: p["future_request_contract"].update(automatic_dispatch_allowed=True),
        lambda p: p["allowed_real_reference_inputs"].update(database_files_allowed=True),
        lambda p: p["allowed_real_reference_inputs"].update(network_download_allowed=True),
        lambda p: p["validation_scope"].update(expected_documented_exception_count=1),
        lambda p: p["validation_scope"].update(expected_gold_dataset_complete=True),
        lambda p: p["validation_scope"].update(partial_recognition_allowed=True),
        lambda p: p["allowed_output"].update(aggregate_only=False),
        lambda p: p["approval_and_execution_separation"].update(this_design_grants_approval=True),
        lambda p: p["non_authorizations"].update(market_backtest=True),
        lambda p: p["next_state_if_valid"].update(formal_stake=1),
    ]
    rejected = 0
    for mutation in mutations:
        candidate = copy.deepcopy(payload)
        mutation(candidate)
        try:
            validate(candidate)
        except (DesignValidationError, KeyError, TypeError):
            rejected += 1
    require(rejected == len(mutations), "not all mutations were rejected")
    return rejected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--design", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = json.loads(args.design.read_text(encoding="utf-8"))
    checks = validate(payload)
    mutations = run_mutation_tests(payload)
    result = {
        "schema_version": "historical-silver-source-gap-exception-real-reference-validation-request-design-validation-v1",
        "formal_state": "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_REAL_REFERENCE_VALIDATION_REQUEST_DESIGN_VALIDATION_PASS",
        "checks_passed": len(checks),
        "mutation_tests_passed": mutations,
        "design_only": True,
        "approval_granted": False,
        "execution_enabled": False,
        "real_reference_validation_executed": False,
        "database_access": False,
        "network_access": False,
        "raw_rows_read": False,
        "formal_stake": 0,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
