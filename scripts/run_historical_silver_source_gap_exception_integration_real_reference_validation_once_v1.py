#!/usr/bin/env python3
"""Run one approved aggregate-only source-gap exception validation once.

The runner reads only committed aggregate JSON records, performs no network,
database, archive, CSV, Silver-row, or Gold-row access, and writes one aggregate
JSON result. The request is treated as consumed after any non-validate-only
execution attempt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from integrate_historical_silver_source_gap_exception_v1 import (
    IntegrationValidationError,
    integrate_documented_source_gap,
)

REQUEST_ID = (
    "HISTORICAL-SILVER-2023-24-SOURCE-GAP-EXCEPTION-INTEGRATION-"
    "REAL-REFERENCE-VALIDATION-2026-07-22-001"
)
REQUEST_SHA256 = "sha256:192a06862fe830027686d149d36572b4ad76ea609f489c6a3d540b7ea4b27e97"
IMPLEMENTATION_SHA256 = "sha256:c4bd7ccb05bcf78747a7210e0eefad083d599de2ca8b0d44c9c455006f084cbc"
APPROVAL_STATE = "EXPLICIT_USER_APPROVAL_GRANTED"
READY_STATE = (
    "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_"
    "REAL_REFERENCE_VALIDATION_APPROVAL_VALID"
)
PASS_STATE = (
    "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_"
    "REAL_REFERENCE_VALIDATION_PASS"
)
FAIL_CLOSED_STATE = (
    "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_"
    "REAL_REFERENCE_VALIDATION_FAIL_CLOSED"
)
ADMISSION_STATE = (
    "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_"
    "REAL_REFERENCE_VALIDATION_ADMISSION_VALID"
)
OUTPUT_SCHEMA = (
    "historical-silver-2023-24-source-gap-exception-integration-"
    "real-reference-validation-execution-result-v1"
)
MAX_OUTPUT_BYTES = 1_048_576
ALLOWED_INPUT_PATHS = {
    "aggregate_coverage_report": "data/research/historical-gold-silver-coverage-real-reference-result-v1.json",
    "exception_manifest": "data/research/historical-silver-2023-24-source-gap-exception-manifest-v1.json",
    "integration_policy": "data/research/historical-silver-2023-24-source-gap-exception-integration-policy-v1.json",
}
PROHIBITED_KEYS = {
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


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def contains_prohibited_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            str(key) in PROHIBITED_KEYS or contains_prohibited_key(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(contains_prohibited_key(item) for item in value)
    return False


def validate_admission(
    request: Mapping[str, Any],
    approval: Mapping[str, Any],
    approval_status: Mapping[str, Any],
    request_sha256: str,
    implementation_sha256: str,
    confirmation_request_id: str,
    workflow_event: str,
    workflow_ref: str,
    execution_count_before: int,
) -> dict[str, Any]:
    checks: dict[str, bool] = {}

    def check(name: str, value: Any) -> None:
        checks[name] = bool(value)

    check("request_id", request.get("request_id") == REQUEST_ID)
    check("approval_request_id", approval.get("request_id") == REQUEST_ID)
    check("approval_state", approval.get("approval_state") == APPROVAL_STATE)
    check("approved_by", approval.get("approved_by") == "qoo109")
    check("approval_status_state", approval_status.get("formal_state") == READY_STATE)
    check("approval_status_granted", approval_status.get("approval_granted") is True)
    check("request_hash_constant", request_sha256 == REQUEST_SHA256)
    check("implementation_hash_constant", implementation_sha256 == IMPLEMENTATION_SHA256)

    bindings = approval.get("immutable_bindings", {})
    check("approval_request_hash", bindings.get("request_file_sha256") == REQUEST_SHA256)
    check("approval_implementation_hash", bindings.get("implementation_file_sha256") == IMPLEMENTATION_SHA256)

    authorization = approval.get("execution_authorization", {})
    check("one_time_only", authorization.get("one_time_only") is True)
    check("maximum_one", authorization.get("maximum_execution_count") == 1)
    check("before_zero", authorization.get("executions_recorded_before_approval") == 0)
    check("dispatch_only", authorization.get("workflow_dispatch_only") is True)
    check("automatic_dispatch_false", authorization.get("automatic_dispatch_allowed") is False)
    check("approved_ref", authorization.get("approved_ref") == "refs/heads/main")
    check("no_repeat", authorization.get("repeat_execution_allowed") is False)

    check("confirmation", confirmation_request_id == REQUEST_ID)
    check("event", workflow_event == "workflow_dispatch")
    check("ref", workflow_ref == "refs/heads/main")
    check("execution_count_before", execution_count_before == 0)

    request_paths = request.get("allowed_committed_inputs", {})
    approval_paths = approval.get("allowed_committed_inputs", {})
    for key, expected in ALLOWED_INPUT_PATHS.items():
        check(f"request_path_{key}", request_paths.get(key) == expected)
        check(f"approval_path_{key}", approval_paths.get(key) == expected)
    check("request_no_additional_paths", request_paths.get("additional_input_paths_allowed") is False)
    check("approval_no_additional_paths", approval_paths.get("additional_input_paths_allowed") is False)

    for key in (
        "database_files_allowed",
        "source_archives_allowed",
        "raw_csv_allowed",
        "raw_rows_allowed",
        "network_download_allowed",
        "temporary_reference_rebuild_allowed",
    ):
        check(f"request_forbids_{key}", request_paths.get(key) is False)
        check(f"approval_forbids_{key}", approval_paths.get(key) is False)

    check("request_stake_zero", request.get("formal_stake") == 0)
    check("approval_stake_zero", approval.get("formal_stake") == 0)
    check("status_stake_zero", approval_status.get("formal_stake") == 0)

    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": "historical-silver-source-gap-exception-real-reference-validation-admission-v1",
        "request_id": REQUEST_ID,
        "formal_state": ADMISSION_STATE if not failed else FAIL_CLOSED_STATE,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "checks_failed": len(failed),
        "failed_checks": failed,
        "request_file_sha256": request_sha256,
        "implementation_file_sha256": implementation_sha256,
        "execution_count_before": execution_count_before,
        "maximum_execution_count": 1,
        "aggregate_only": True,
        "formal_stake": 0,
    }


def adapt_coverage_record(coverage: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "formal_outcome",
        "silver_game_rows",
        "gold_matchup_rows",
        "missing_gold_for_silver",
        "missing_season",
        "missing_both_team_features",
        "other_reason_count",
        "builder_repair_required",
        "formal_stake",
    }
    missing = sorted(required.difference(coverage.keys()))
    if missing:
        raise ValueError(f"coverage record missing fields: {missing}")

    silver = int(coverage["silver_game_rows"])
    missing_count = int(coverage["missing_gold_for_silver"])
    season = str(coverage["missing_season"])
    reason_count = int(coverage["missing_both_team_features"])
    other_reason_count = int(coverage["other_reason_count"])

    return {
        "schema_version": "historical-gold-silver-coverage-reconciliation-report-v1",
        "formal_outcome": coverage["formal_outcome"],
        "scope": {
            "season_labels": [season],
            "silver_game_rows": silver,
            "gold_matchup_rows": int(coverage["gold_matchup_rows"]),
        },
        "coverage": {
            "covered_games": silver - missing_count,
            "missing_gold_for_silver": missing_count,
            "unclassified_missing_games": other_reason_count,
            "missing_by_season": {season: missing_count},
            "missing_by_reason": {
                "missing_both_team_features": reason_count,
                "other": other_reason_count,
            },
            "missing_by_season_and_reason": {
                season: {
                    "missing_both_team_features": reason_count,
                    "other": other_reason_count,
                }
            },
        },
        "decision": {
            "builder_repair_required": bool(coverage["builder_repair_required"]),
            "formal_stake": int(coverage["formal_stake"]),
        },
        "boundaries": {
            "game_ids_emitted": False,
            "dates_emitted": False,
            "team_codes_emitted": False,
            "row_key_hashes_emitted": False,
        },
    }


def evaluate_result(
    transformed: Mapping[str, Any],
    admission: Mapping[str, Any],
    input_digests: Mapping[str, str],
) -> dict[str, Any]:
    reporting = transformed.get("documented_exception_reporting", {})
    expected = {
        "documented_source_gap_exception_code": "SOURCE_ARCHIVE_PBPSTATS_GAME_ABSENT",
        "documented_source_gap_exception_count": 2,
        "unexplained_missing_count_after_documentation": 0,
        "covered_or_documented_count": 5826,
        "gold_matchup_count_after_documentation": 5824,
        "gold_dataset_complete": False,
        "recognition_gate_passed": True,
    }
    checks = {
        "admission_valid": admission.get("formal_state") == ADMISSION_STATE,
        "output_schema": transformed.get("schema_version") == "historical-gold-silver-coverage-with-documented-exceptions-v1",
        "raw_silver": transformed.get("raw_coverage_report", {}).get("scope", {}).get("silver_game_rows") == 5826,
        "raw_gold": transformed.get("raw_coverage_report", {}).get("scope", {}).get("gold_matchup_rows") == 5824,
        "raw_gap": transformed.get("raw_coverage_report", {}).get("coverage", {}).get("missing_gold_for_silver") == 2,
    }
    for key, value in expected.items():
        checks[f"reporting_{key}"] = reporting.get(key) == value
    checks["aggregate_privacy"] = not contains_prohibited_key(transformed)
    failed = sorted(name for name, passed in checks.items() if not passed)

    return {
        "schema_version": OUTPUT_SCHEMA,
        "request_id": REQUEST_ID,
        "formal_state": PASS_STATE if not failed else FAIL_CLOSED_STATE,
        "checks": checks,
        "checks_failed": len(failed),
        "failed_checks": failed,
        "execution_receipt": {
            "execution_attempted": True,
            "execution_count_for_request": 1,
            "maximum_execution_count": 1,
            "request_consumed": True,
            "repeat_execution_allowed": False,
            "workflow_dispatch_only": True,
            "aggregate_only": True,
        },
        "immutable_bindings": {
            "request_file_sha256": REQUEST_SHA256,
            "implementation_file_sha256": IMPLEMENTATION_SHA256,
            "input_file_sha256": dict(input_digests),
        },
        "aggregate_result": transformed,
        "boundaries": {
            "database_access": False,
            "network_access": False,
            "source_archive_access": False,
            "raw_csv_access": False,
            "raw_rows_read": False,
            "raw_rows_emitted": 0,
            "raw_files_emitted": False,
            "silver_or_gold_write": False,
            "coverage_analyzer_modified": False,
            "transformer_modified": False,
            "cross_source_audit_rerun": False,
            "market_backtest": False,
            "model_training_or_retraining": False,
            "betting_edge_claim": False,
            "formal_stake": 0,
        },
    }


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    encoded = payload.encode("utf-8")
    if len(encoded) > MAX_OUTPUT_BYTES:
        raise RuntimeError("aggregate output exceeds 1 MiB")
    if contains_prohibited_key(value):
        raise RuntimeError("aggregate output contains prohibited identifier evidence")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded)


def self_test() -> dict[str, bool]:
    synthetic_coverage = {
        "formal_outcome": "HISTORICAL_GOLD_SILVER_COVERAGE_RECONCILIATION_SOURCE_DATA_GAP_CONFIRMED",
        "silver_game_rows": 5826,
        "gold_matchup_rows": 5824,
        "missing_gold_for_silver": 2,
        "missing_season": "2023-24",
        "missing_both_team_features": 2,
        "other_reason_count": 0,
        "builder_repair_required": False,
        "formal_stake": 0,
    }
    raw = adapt_coverage_record(synthetic_coverage)
    manifest = {
        "formal_state": "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_MANIFEST_DESIGN_READY",
        "aggregate_scope": {"source_gap_exception_games": 2, "unclassified_games": 0},
        "exception_class": {"exception_code": "SOURCE_ARCHIVE_PBPSTATS_GAME_ABSENT"},
        "public_evidence_policy": {"aggregate_only": True},
        "exception_handling_policy": {"mode": "DOCUMENTED_AGGREGATE_ONLY_NO_ROW_PATCH"},
    }
    policy = {
        "schema_version": "historical-silver-2023-24-source-gap-exception-integration-policy-v1",
        "formal_state": "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_POLICY_DESIGN_READY",
        "recognition_gate": {
            "on_any_mismatch": "FAIL_CLOSED_UNEXPLAINED_COVERAGE_GAP",
            "partial_recognition_allowed": False,
            "automatic_count_adjustment_allowed": False,
        },
        "reporting_contract": {
            "preserve_raw_metrics": True,
            "gold_coverage_rewritten_as_complete": False,
        },
        "decision_semantics": {"formal_stake": 0},
    }
    transformed = integrate_documented_source_gap(raw, manifest, policy)
    reporting = transformed["documented_exception_reporting"]

    tests = {
        "adapter_schema": raw["schema_version"] == "historical-gold-silver-coverage-reconciliation-report-v1",
        "adapter_silver": raw["scope"]["silver_game_rows"] == 5826,
        "adapter_gold": raw["scope"]["gold_matchup_rows"] == 5824,
        "adapter_gap": raw["coverage"]["missing_gold_for_silver"] == 2,
        "adapter_covered": raw["coverage"]["covered_games"] == 5824,
        "adapter_season": raw["scope"]["season_labels"] == ["2023-24"],
        "recognition_passes": reporting["recognition_gate_passed"] is True,
        "documented_two": reporting["documented_source_gap_exception_count"] == 2,
        "unexplained_zero": reporting["unexplained_missing_count_after_documentation"] == 0,
        "covered_or_documented": reporting["covered_or_documented_count"] == 5826,
        "gold_not_complete": reporting["gold_dataset_complete"] is False,
        "aggregate_privacy": not contains_prohibited_key(transformed),
        "stake_zero": raw["decision"]["formal_stake"] == 0,
        "no_database_boundary": True,
        "no_network_boundary": True,
    }

    mutated = dict(synthetic_coverage)
    mutated["missing_gold_for_silver"] = 3
    mutated_raw = adapt_coverage_record(mutated)
    mutated_result = integrate_documented_source_gap(mutated_raw, manifest, policy)
    tests["mutation_fails_closed"] = (
        mutated_result["documented_exception_reporting"]["recognition_gate_passed"] is False
        and mutated_result["documented_exception_reporting"]["documented_source_gap_exception_count"] == 0
    )

    unsafe = dict(raw)
    unsafe["game_id"] = "forbidden"
    try:
        integrate_documented_source_gap(unsafe, manifest, policy)
    except IntegrationValidationError:
        tests["privacy_mutation_raises"] = True
    else:
        tests["privacy_mutation_raises"] = False

    if not all(tests.values()):
        raise AssertionError(tests)
    return tests


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path)
    parser.add_argument("--approval", type=Path)
    parser.add_argument("--approval-status", type=Path)
    parser.add_argument("--implementation", type=Path)
    parser.add_argument("--coverage", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--confirmation-request-id", default="")
    parser.add_argument("--workflow-event", default="")
    parser.add_argument("--workflow-ref", default="")
    parser.add_argument("--execution-count-before", type=int, default=0)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.self_test:
        tests = self_test()
        report = {
            "schema_version": "historical-silver-source-gap-exception-real-reference-validation-runner-self-test-v1",
            "formal_state": "SELF_TEST_PASS",
            "tests_run": len(tests),
            "tests_passed": sum(tests.values()),
            "tests": tests,
            "real_reference_inputs_read": False,
            "formal_stake": 0,
        }
        write_json(args.output, report)
        return 0

    required_paths = {
        "request": args.request,
        "approval": args.approval,
        "approval_status": args.approval_status,
        "implementation": args.implementation,
    }
    if any(path is None for path in required_paths.values()):
        raise SystemExit("request, approval, approval-status, and implementation are required")

    request = read_json(args.request)
    approval = read_json(args.approval)
    approval_status = read_json(args.approval_status)
    admission = validate_admission(
        request=request,
        approval=approval,
        approval_status=approval_status,
        request_sha256=sha256_file(args.request),
        implementation_sha256=sha256_file(args.implementation),
        confirmation_request_id=args.confirmation_request_id,
        workflow_event=args.workflow_event,
        workflow_ref=args.workflow_ref,
        execution_count_before=args.execution_count_before,
    )
    if admission["formal_state"] != ADMISSION_STATE:
        write_json(args.output, admission)
        return 2
    if args.validate_only:
        write_json(args.output, admission)
        return 0

    if args.coverage is None or args.manifest is None or args.policy is None:
        raise SystemExit("coverage, manifest, and policy are required for execution")

    provided_paths = {
        "aggregate_coverage_report": args.coverage.as_posix(),
        "exception_manifest": args.manifest.as_posix(),
        "integration_policy": args.policy.as_posix(),
    }
    if provided_paths != ALLOWED_INPUT_PATHS:
        raise SystemExit(f"input path mismatch: {provided_paths}")

    coverage = read_json(args.coverage)
    manifest = read_json(args.manifest)
    policy = read_json(args.policy)
    raw_report = adapt_coverage_record(coverage)
    transformed = integrate_documented_source_gap(raw_report, manifest, policy)
    result = evaluate_result(
        transformed,
        admission,
        {
            "aggregate_coverage_report": sha256_file(args.coverage),
            "exception_manifest": sha256_file(args.manifest),
            "integration_policy": sha256_file(args.policy),
        },
    )
    write_json(args.output, result)
    return 0 if result["formal_state"] == PASS_STATE else 2


if __name__ == "__main__":
    raise SystemExit(main())
