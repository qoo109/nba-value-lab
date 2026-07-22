#!/usr/bin/env python3
"""Validate the immutable aggregate-only real-reference validation request v1.

This validator does not execute the transformer and does not read the committed
real-reference aggregate inputs. It validates request governance, computes the
request and implementation SHA-256 digests, and runs request mutation tests.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

EXPECTED_SCHEMA = (
    "historical-silver-2023-24-source-gap-exception-integration-real-reference-validation-request-v1"
)
EXPECTED_STATE = (
    "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_REAL_REFERENCE_VALIDATION_REQUEST_DRAFT_READY_FOR_VALIDATION"
)
EXPECTED_REQUEST_ID = (
    "HISTORICAL-SILVER-2023-24-SOURCE-GAP-EXCEPTION-INTEGRATION-REAL-REFERENCE-VALIDATION-2026-07-22-001"
)
EXPECTED_NEXT_STATE = (
    "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_REAL_REFERENCE_VALIDATION_REQUEST_VALID_AWAITING_EXPLICIT_USER_APPROVAL"
)
EXPECTED_NEXT_STEP = (
    "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_REAL_REFERENCE_VALIDATION_EXPLICIT_USER_APPROVAL_REQUIRED"
)
EXPECTED_DESIGN_STATUS = (
    "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_REAL_REFERENCE_VALIDATION_REQUEST_DESIGN_VALIDATED"
)
EXPECTED_IMPLEMENTATION_STATUS = (
    "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_IMPLEMENTATION_VALIDATED_SYNTHETIC_ONLY"
)
EXPECTED_ACTION = "VALIDATE_AGGREGATE_TRANSFORMER_AGAINST_COMMITTED_REAL_REFERENCE_RECORDS_ONCE"
EXPECTED_IMPLEMENTATION_PATH = "scripts/integrate_historical_silver_source_gap_exception_v1.py"
EXPECTED_INPUTS = {
    "aggregate_coverage_report": "data/research/historical-gold-silver-coverage-real-reference-result-v1.json",
    "exception_manifest": "data/research/historical-silver-2023-24-source-gap-exception-manifest-v1.json",
    "integration_policy": "data/research/historical-silver-2023-24-source-gap-exception-integration-policy-v1.json",
}
PROHIBITED_FIELDS = {
    "game_id",
    "game_date",
    "home_team_abbr",
    "away_team_abbr",
    "team_code",
    "source_file_path",
    "source_file_hash",
    "row_level_record",
    "row_key_hash",
}


class RequestValidationError(ValueError):
    """Raised when the request violates its frozen governance contract."""


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RequestValidationError(f"{name} must be a mapping")
    return value


def _path(payload: Mapping[str, Any], dotted: str) -> Any:
    current: Any = payload
    for part in dotted.split("."):
        if not isinstance(current, Mapping) or part not in current:
            raise RequestValidationError(f"missing field: {dotted}")
        current = current[part]
    return current


def _expect(payload: Mapping[str, Any], dotted: str, expected: Any) -> None:
    actual = _path(payload, dotted)
    if actual != expected:
        raise RequestValidationError(f"{dotted}: expected {expected!r}, got {actual!r}")


def _contains_prohibited_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            str(key) in PROHIBITED_FIELDS or _contains_prohibited_key(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_prohibited_key(child) for child in value)
    return False


def validate_request(
    request: Mapping[str, Any],
    design_status: Mapping[str, Any],
    implementation_status: Mapping[str, Any],
) -> None:
    request = _mapping(request, "request")
    design_status = _mapping(design_status, "design_status")
    implementation_status = _mapping(implementation_status, "implementation_status")

    if _contains_prohibited_key(request):
        raise RequestValidationError("request contains prohibited row-level identifier fields")

    _expect(request, "schema_version", EXPECTED_SCHEMA)
    _expect(request, "formal_state", EXPECTED_STATE)
    _expect(request, "request_id", EXPECTED_REQUEST_ID)
    _expect(request, "request_role", "ONE_TIME_AGGREGATE_ONLY_REAL_REFERENCE_VALIDATION_REQUEST")
    _expect(request, "requested_action", EXPECTED_ACTION)
    _expect(request, "implementation_binding.module_path", EXPECTED_IMPLEMENTATION_PATH)
    _expect(request, "implementation_binding.implementation_merge_commit", "28b70855931b38402a205dc9aac30cb09c2b2789")
    _expect(request, "implementation_binding.request_creation_base_commit", "6e5e8fb43a617afa8b485d3e1f1c86bb0c2d2db8")
    _expect(request, "implementation_binding.implementation_file_sha256_must_be_computed_by_request_validator", True)
    _expect(request, "implementation_binding.approval_must_bind_computed_implementation_file_sha256", True)

    for key, expected in EXPECTED_INPUTS.items():
        _expect(request, f"allowed_committed_inputs.{key}", expected)
    _expect(request, "allowed_committed_inputs.input_role", "COMMITTED_AGGREGATE_RECORDS_ONLY")
    for field in (
        "additional_input_paths_allowed",
        "database_files_allowed",
        "source_archives_allowed",
        "raw_csv_allowed",
        "raw_rows_allowed",
        "network_download_allowed",
        "temporary_reference_rebuild_allowed",
    ):
        _expect(request, f"allowed_committed_inputs.{field}", False)

    _expect(request, "execution_control.maximum_execution_count", 1)
    _expect(request, "execution_control.execution_count", 0)
    _expect(request, "execution_control.request_consumed", False)
    _expect(request, "execution_control.repeat_execution_allowed", False)
    _expect(request, "execution_control.workflow_dispatch_only", True)
    _expect(request, "execution_control.automatic_dispatch_allowed", False)
    _expect(request, "execution_control.explicit_user_approval_required", True)
    _expect(request, "execution_control.approval_granted", False)
    _expect(request, "execution_control.execution_enabled", False)
    _expect(request, "execution_control.execution_workflow_created", False)
    _expect(request, "execution_control.real_reference_validation_executed", False)

    for field in (
        "approval_record_must_be_separate",
        "approval_must_bind_exact_request_id",
        "approval_must_bind_request_file_sha256_from_validation_artifact",
        "approval_must_bind_implementation_file_sha256_from_validation_artifact",
        "approval_must_name_repository_owner",
        "approval_may_not_expand_allowed_inputs",
        "approval_may_not_enable_automatic_dispatch",
    ):
        _expect(request, f"approval_binding_requirements.{field}", True)
    _expect(request, "approval_binding_requirements.approval_must_preserve_maximum_execution_count", 1)

    expected_result = {
        "output_schema": "historical-gold-silver-coverage-with-documented-exceptions-v1",
        "raw_silver_game_count": 5826,
        "raw_gold_matchup_count": 5824,
        "raw_missing_gold_for_silver": 2,
        "documented_source_gap_exception_code": "SOURCE_ARCHIVE_PBPSTATS_GAME_ABSENT",
        "documented_source_gap_exception_count": 2,
        "unexplained_missing_count_after_documentation": 0,
        "covered_or_documented_count": 5826,
        "gold_dataset_complete": False,
        "recognition_gate_passed": True,
        "raw_report_must_remain_unmodified": True,
        "fail_closed_on_any_semantic_mismatch": True,
        "partial_recognition_allowed": False,
    }
    for field, expected in expected_result.items():
        _expect(request, f"expected_validation_result.{field}", expected)

    _expect(request, "allowed_future_output.single_json_artifact_only", True)
    _expect(request, "allowed_future_output.aggregate_only", True)
    _expect(request, "allowed_future_output.maximum_output_bytes", 1_048_576)
    _expect(request, "allowed_future_output.validation_receipt_required", True)
    _expect(request, "allowed_future_output.raw_rows_emitted", 0)
    _expect(request, "allowed_future_output.raw_files_emitted", False)
    prohibited = set(_path(request, "allowed_future_output.prohibited_fields"))
    if prohibited != PROHIBITED_FIELDS:
        raise RequestValidationError("allowed_future_output.prohibited_fields mismatch")

    _expect(request, "failure_semantics.request_is_consumed_after_any_execution_attempt", True)

    non_authorizations = _mapping(_path(request, "non_authorizations"), "non_authorizations")
    if any(value is not False for value in non_authorizations.values()):
        raise RequestValidationError("all non_authorizations must remain false")

    _expect(request, "request_validation_requirements.compute_request_file_sha256", True)
    _expect(request, "request_validation_requirements.compute_implementation_file_sha256", True)
    _expect(request, "request_validation_requirements.validate_exact_request_id", True)
    _expect(request, "request_validation_requirements.validate_allowed_paths_exactly", True)
    _expect(request, "request_validation_requirements.validate_execution_count_zero", True)
    _expect(request, "request_validation_requirements.validate_approval_not_granted", True)
    _expect(request, "request_validation_requirements.validate_execution_disabled", True)
    _expect(request, "request_validation_requirements.validate_no_execution_workflow_created", True)
    _expect(request, "request_validation_requirements.validate_no_approval_record_created", True)
    _expect(request, "request_validation_requirements.mutation_tests_required", True)
    minimum_tests = _path(request, "request_validation_requirements.minimum_mutation_test_count")
    if not isinstance(minimum_tests, int) or isinstance(minimum_tests, bool) or minimum_tests < 12:
        raise RequestValidationError("minimum_mutation_test_count must be at least 12")
    _expect(request, "request_validation_requirements.validate_formal_stake_zero", True)

    _expect(request, "next_state_if_valid.formal_state", EXPECTED_NEXT_STATE)
    _expect(request, "next_state_if_valid.next_research_step", EXPECTED_NEXT_STEP)
    _expect(request, "next_state_if_valid.ready_for_explicit_user_approval", True)
    for field in (
        "ready_for_real_reference_validation_execution",
        "ready_for_analyzer_replacement",
        "ready_for_cross_source_audit_rerun",
        "ready_for_market_backtest",
    ):
        _expect(request, f"next_state_if_valid.{field}", False)
    _expect(request, "next_state_if_valid.formal_stake", 0)
    _expect(request, "formal_stake", 0)

    _expect(design_status, "formal_state", EXPECTED_DESIGN_STATUS)
    _expect(design_status, "ready_for_request_draft", True)
    _expect(design_status, "approval_granted", False)
    _expect(design_status, "execution_enabled", False)
    _expect(design_status, "real_reference_validation_executed", False)
    _expect(design_status, "formal_stake", 0)

    _expect(implementation_status, "formal_state", EXPECTED_IMPLEMENTATION_STATUS)
    _expect(implementation_status, "implementation_module", EXPECTED_IMPLEMENTATION_PATH)
    _expect(implementation_status, "real_reference_validation_executed", False)
    _expect(implementation_status, "formal_stake", 0)


def mutation_tests(
    request: Mapping[str, Any],
    design_status: Mapping[str, Any],
    implementation_status: Mapping[str, Any],
) -> int:
    mutations: list[tuple[str, Any]] = [
        ("request_id", "OTHER"),
        ("formal_state", "OTHER"),
        ("execution_control.maximum_execution_count", 2),
        ("execution_control.execution_count", 1),
        ("execution_control.approval_granted", True),
        ("execution_control.execution_enabled", True),
        ("execution_control.automatic_dispatch_allowed", True),
        ("allowed_committed_inputs.network_download_allowed", True),
        ("allowed_committed_inputs.database_files_allowed", True),
        ("expected_validation_result.gold_dataset_complete", True),
        ("expected_validation_result.documented_source_gap_exception_count", 1),
        ("formal_stake", 1),
        ("next_state_if_valid.ready_for_real_reference_validation_execution", True),
        ("non_authorizations.market_backtest", True),
    ]

    passed = 0
    for dotted, replacement in mutations:
        candidate = copy.deepcopy(request)
        current: Any = candidate
        parts = dotted.split(".")
        for part in parts[:-1]:
            current = current[part]
        current[parts[-1]] = replacement
        try:
            validate_request(candidate, design_status, implementation_status)
        except RequestValidationError:
            passed += 1
        else:
            raise RequestValidationError(f"mutation was not rejected: {dotted}")

    privacy_candidate = copy.deepcopy(request)
    privacy_candidate["game_id"] = "synthetic-prohibited"
    try:
        validate_request(privacy_candidate, design_status, implementation_status)
    except RequestValidationError:
        passed += 1
    else:
        raise RequestValidationError("privacy mutation was not rejected")

    return passed


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--implementation", type=Path, required=True)
    parser.add_argument("--design-status", type=Path, required=True)
    parser.add_argument("--implementation-status", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    request_bytes = args.request.read_bytes()
    implementation_bytes = args.implementation.read_bytes()
    request = json.loads(request_bytes)
    design_status = json.loads(args.design_status.read_text(encoding="utf-8"))
    implementation_status = json.loads(args.implementation_status.read_text(encoding="utf-8"))

    validate_request(request, design_status, implementation_status)
    mutation_count = mutation_tests(request, design_status, implementation_status)

    report = {
        "schema_version": "historical-silver-2023-24-source-gap-exception-integration-real-reference-validation-request-validation-v1",
        "formal_state": EXPECTED_NEXT_STATE,
        "request_id": EXPECTED_REQUEST_ID,
        "request_file": str(args.request),
        "request_file_sha256": sha256_bytes(request_bytes),
        "implementation_file": str(args.implementation),
        "implementation_file_sha256": sha256_bytes(implementation_bytes),
        "mutation_tests_passed": mutation_count,
        "request_valid": True,
        "ready_for_explicit_user_approval": True,
        "approval_granted": False,
        "execution_enabled": False,
        "real_reference_validation_executed": False,
        "execution_count": 0,
        "maximum_execution_count": 1,
        "aggregate_only": True,
        "database_access": False,
        "network_access": False,
        "source_archive_access": False,
        "real_reference_inputs_read": False,
        "raw_rows_read": False,
        "raw_rows_emitted": 0,
        "execution_workflow_created": False,
        "formal_stake": 0,
        "next_research_step": EXPECTED_NEXT_STEP,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
