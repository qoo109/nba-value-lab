#!/usr/bin/env python3
"""Validate the recorded consumed aggregate-only real-reference validation result."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

REQUEST_ID = (
    "HISTORICAL-SILVER-2023-24-SOURCE-GAP-EXCEPTION-INTEGRATION-"
    "REAL-REFERENCE-VALIDATION-2026-07-22-001"
)
PASS_STATE = (
    "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_"
    "REAL_REFERENCE_VALIDATION_PASS"
)
CURRENT_STATE = (
    "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_"
    "REAL_REFERENCE_VALIDATION_PASS_CONSUMED"
)
NEXT_STEP = (
    "HISTORICAL_GOLD_5824_ELIGIBLE_CORPUS_FREEZE_AND_"
    "EXCEPTION_EXCLUSION_POLICY_READY_FOR_DESIGN"
)
RESULT_SCHEMA = (
    "historical-silver-2023-24-source-gap-exception-integration-"
    "real-reference-validation-execution-result-v1"
)
CURRENT_SCHEMA = (
    "historical-silver-2023-24-source-gap-exception-integration-"
    "real-reference-validation-current-status-v3"
)
RESULT_PATH = (
    "data/research/historical-silver-2023-24-source-gap-exception-"
    "integration-real-reference-validation-result-v1.json"
)
RESULT_SHA256 = "sha256:048149cd058c74c1ab441a99f3a4eec0972668500e469ff81ce663b3e5264340"
REQUEST_SHA256 = "sha256:192a06862fe830027686d149d36572b4ad76ea609f489c6a3d540b7ea4b27e97"
IMPLEMENTATION_SHA256 = "sha256:c4bd7ccb05bcf78747a7210e0eefad083d599de2ca8b0d44c9c455006f084cbc"
EXCEPTION_CODE = "SOURCE_ARCHIVE_PBPSTATS_GAME_ABSENT"

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


def sha256_json_file(path: Path) -> str:
    value = read_json(path)
    canonical = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def contains_prohibited_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            str(key) in PROHIBITED_KEYS or contains_prohibited_key(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(contains_prohibited_key(item) for item in value)
    return False


def validate(result: dict[str, Any], current: dict[str, Any], result_sha: str) -> dict[str, Any]:
    checks: dict[str, bool] = {}

    def add(name: str, value: Any) -> None:
        checks[name] = bool(value)

    add("result_schema", result.get("schema_version") == RESULT_SCHEMA)
    add("result_request", result.get("request_id") == REQUEST_ID)
    add("result_state", result.get("formal_state") == PASS_STATE)
    add("result_checks_zero", result.get("checks_failed") == 0)
    add("result_failed_checks_empty", result.get("failed_checks") == [])
    add("result_payload_sha", result_sha == RESULT_SHA256)
    add("result_aggregate_privacy", not contains_prohibited_key(result))

    result_checks = result.get("checks", {})
    add("all_result_checks_true", bool(result_checks) and all(value is True for value in result_checks.values()))

    receipt = result.get("execution_receipt", {})
    add("receipt_attempted", receipt.get("execution_attempted") is True)
    add("receipt_count", receipt.get("execution_count_for_request") == 1)
    add("receipt_maximum", receipt.get("maximum_execution_count") == 1)
    add("receipt_consumed", receipt.get("request_consumed") is True)
    add("receipt_no_repeat", receipt.get("repeat_execution_allowed") is False)
    add("receipt_dispatch_only", receipt.get("workflow_dispatch_only") is True)
    add("receipt_aggregate_only", receipt.get("aggregate_only") is True)

    bindings = result.get("immutable_bindings", {})
    add("request_binding", bindings.get("request_file_sha256") == REQUEST_SHA256)
    add("implementation_binding", bindings.get("implementation_file_sha256") == IMPLEMENTATION_SHA256)
    input_hashes = bindings.get("input_file_sha256", {})
    add("input_hash_count", isinstance(input_hashes, dict) and len(input_hashes) == 3)
    add("input_hashes_sha256", all(str(value).startswith("sha256:") for value in input_hashes.values()))

    aggregate = result.get("aggregate_result", {})
    raw = aggregate.get("raw_coverage_report", {})
    reporting = aggregate.get("documented_exception_reporting", {})
    add("output_schema", aggregate.get("schema_version") == "historical-gold-silver-coverage-with-documented-exceptions-v1")
    add("raw_silver", raw.get("scope", {}).get("silver_game_rows") == 5826)
    add("raw_gold", raw.get("scope", {}).get("gold_matchup_rows") == 5824)
    add("raw_gap", raw.get("coverage", {}).get("missing_gold_for_silver") == 2)
    add("raw_unclassified_zero", raw.get("coverage", {}).get("unclassified_missing_games") == 0)
    add("builder_repair_false", raw.get("decision", {}).get("builder_repair_required") is False)
    add("raw_stake_zero", raw.get("decision", {}).get("formal_stake") == 0)
    add("exception_code", reporting.get("documented_source_gap_exception_code") == EXCEPTION_CODE)
    add("exception_count", reporting.get("documented_source_gap_exception_count") == 2)
    add("unexplained_zero", reporting.get("unexplained_missing_count_after_documentation") == 0)
    add("covered_or_documented", reporting.get("covered_or_documented_count") == 5826)
    add("gold_after_documentation", reporting.get("gold_matchup_count_after_documentation") == 5824)
    add("gold_incomplete", reporting.get("gold_dataset_complete") is False)
    add("recognition_gate", reporting.get("recognition_gate_passed") is True)
    add("recognition_failures_empty", reporting.get("recognition_failure_reasons") == [])

    boundaries = result.get("boundaries", {})
    false_boundaries = (
        "betting_edge_claim",
        "coverage_analyzer_modified",
        "cross_source_audit_rerun",
        "database_access",
        "market_backtest",
        "model_training_or_retraining",
        "network_access",
        "raw_csv_access",
        "raw_files_emitted",
        "raw_rows_read",
        "silver_or_gold_write",
        "source_archive_access",
        "transformer_modified",
    )
    for key in false_boundaries:
        add(f"result_boundary_{key}", boundaries.get(key) is False)
    add("result_raw_rows_zero", boundaries.get("raw_rows_emitted") == 0)
    add("result_stake_zero", boundaries.get("formal_stake") == 0)

    add("current_schema", current.get("schema_version") == CURRENT_SCHEMA)
    add("current_state", current.get("formal_state") == CURRENT_STATE)
    add("current_request", current.get("request_id") == REQUEST_ID)
    add("current_result_path", current.get("result_record") == RESULT_PATH)
    add("current_result_sha", current.get("result_payload_sha256") == RESULT_SHA256)
    add("current_result_size", current.get("result_payload_size_bytes") == 4349)

    evidence = current.get("execution_evidence", {})
    add("evidence_run_number", evidence.get("workflow_run_number") == 2)
    add("evidence_run_id_unknown", evidence.get("workflow_run_id") is None and evidence.get("workflow_run_id_unavailable_not_guessed") is True)
    add("evidence_event_ref", evidence.get("event") == "workflow_dispatch" and evidence.get("ref") == "refs/heads/main")
    add("evidence_head", evidence.get("head_sha") == "596ade65cd26cb148f8a3b9a0ffa6092b16a6737")
    add("evidence_job", evidence.get("job_name") == "execute-once" and evidence.get("job_conclusion") == "success")
    add("evidence_artifact_count", evidence.get("observed_artifact_count") == 1)
    add("evidence_screenshot", evidence.get("observed_via_user_screenshot") is True)

    artifact = current.get("artifact_evidence", {})
    add("artifact_name", artifact.get("artifact_name") == "historical-silver-source-gap-exception-integration-real-reference-validation-execution-v1")
    add("artifact_file", artifact.get("artifact_json_file") == "real-reference-validation-execution-result-v1.json")
    add("artifact_id_unknown", artifact.get("artifact_id") is None and artifact.get("artifact_metadata_unavailable_not_guessed") is True)
    add("artifact_sha", artifact.get("artifact_payload_sha256") == RESULT_SHA256)
    add("artifact_size", artifact.get("artifact_payload_size_bytes") == 4349)
    add("artifact_user_payload", artifact.get("artifact_payload_received_from_user") is True)

    current_lifecycle = current.get("execution_lifecycle", {})
    add("current_count", current_lifecycle.get("execution_count") == 1)
    add("current_maximum", current_lifecycle.get("maximum_execution_count") == 1)
    add("current_consumed", current_lifecycle.get("request_consumed") is True)
    add("current_no_repeat", current_lifecycle.get("repeat_execution_allowed") is False)
    add("current_manual_only", current_lifecycle.get("workflow_dispatch_only") is True)
    add("current_no_auto", current_lifecycle.get("automatic_dispatch_allowed") is False)
    add("current_executed", current_lifecycle.get("real_reference_validation_executed") is True)
    add("current_disabled", current_lifecycle.get("execution_enabled") is False)

    scope = current.get("aggregate_scope", {})
    add("current_scope_counts", (
        scope.get("raw_silver_game_count") == 5826
        and scope.get("raw_gold_matchup_count") == 5824
        and scope.get("raw_missing_gold_for_silver") == 2
        and scope.get("documented_source_gap_exception_count") == 2
        and scope.get("unexplained_missing_count_after_documentation") == 0
        and scope.get("covered_or_documented_count") == 5826
    ))
    add("current_gold_incomplete", scope.get("gold_dataset_complete") is False)
    add("current_no_builder_repair", scope.get("silver_builder_repair_required") is False)

    downstream = current.get("downstream_state", {})
    add("eligible_corpus_5824", downstream.get("eligible_gold_matchup_corpus_count") == 5824)
    add("excluded_exceptions_2", downstream.get("documented_exception_count_excluded_from_gold_eligibility") == 2)
    add("policy_design_ready", downstream.get("ready_for_eligible_corpus_freeze_policy_design") is True)
    add("downstream_still_blocked", all(downstream.get(key) is False for key in (
        "ready_for_gold_rebuild",
        "ready_for_cross_source_audit_rerun",
        "ready_for_market_backtest",
        "ready_for_model_retraining",
        "ready_for_betting_edge_claim",
    )))

    current_boundaries = current.get("boundaries", {})
    add("current_boundaries_match", all(current_boundaries.get(key) is False for key in (
        "betting_edge_claim",
        "coverage_analyzer_modified",
        "cross_source_audit_rerun",
        "database_access",
        "market_backtest",
        "model_training_or_retraining",
        "network_access",
        "raw_csv_access",
        "raw_files_emitted",
        "raw_rows_read",
        "silver_or_gold_write",
        "source_archive_access",
        "transformer_modified",
        "opening_or_closing_semantics",
        "clv_ev_roi_drawdown",
        "formal_stake_above_zero",
    )))
    add("current_raw_rows_zero", current_boundaries.get("raw_rows_emitted") == 0)
    add("current_next", current.get("next_research_step") == NEXT_STEP)
    add("current_stake_zero", current.get("formal_stake") == 0)
    add("current_aggregate_privacy", not contains_prohibited_key(current))

    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": "historical-silver-2023-24-source-gap-exception-integration-real-reference-validation-result-validation-report-v1",
        "validated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "formal_state": (
            "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_REAL_REFERENCE_VALIDATION_RESULT_VALID_CONSUMED"
            if not failed
            else "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_REAL_REFERENCE_VALIDATION_RESULT_INVALID"
        ),
        "checks": checks,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "checks_failed": len(failed),
        "failed_checks": failed,
        "result_payload_sha256": result_sha,
        "execution_count": 1,
        "maximum_execution_count": 1,
        "request_consumed": True,
        "repeat_execution_allowed": False,
        "real_reference_validation_executed": True,
        "ready_for_eligible_corpus_freeze_policy_design": not failed,
        "ready_for_market_backtest": False,
        "formal_stake": 0,
    }


def self_test(result: dict[str, Any], current: dict[str, Any]) -> dict[str, bool]:
    baseline = validate(result, current, RESULT_SHA256)
    assert baseline["checks_failed"] == 0, baseline
    tests: dict[str, bool] = {"baseline_passes": True}

    cases = {
        "wrong_state_blocks": ("result", ("formal_state",), "WRONG"),
        "check_failure_blocks": ("result", ("checks_failed",), 1),
        "repeat_execution_blocks": ("result", ("execution_receipt", "repeat_execution_allowed"), True),
        "consumed_false_blocks": ("current", ("execution_lifecycle", "request_consumed"), False),
        "count_zero_blocks": ("current", ("execution_lifecycle", "execution_count"), 0),
        "nonzero_stake_blocks": ("current", ("formal_stake",), 1),
        "market_ready_blocks": ("current", ("downstream_state", "ready_for_market_backtest"), True),
        "wrong_exception_count_blocks": ("current", ("aggregate_scope", "documented_source_gap_exception_count"), 3),
        "wrong_sha_blocks": ("current", ("result_payload_sha256",), "sha256:wrong"),
        "unknown_run_id_claim_blocks": ("current", ("execution_evidence", "workflow_run_id_unavailable_not_guessed"), False),
    }
    for name, (target, path, value) in cases.items():
        mutated_result = copy.deepcopy(result)
        mutated_current = copy.deepcopy(current)
        obj = mutated_result if target == "result" else mutated_current
        cursor: dict[str, Any] = obj
        for key in path[:-1]:
            cursor = cursor[key]
        cursor[path[-1]] = value
        report = validate(mutated_result, mutated_current, RESULT_SHA256)
        tests[name] = report["checks_failed"] > 0
        assert tests[name], (name, report)

    unsafe_result = copy.deepcopy(result)
    unsafe_result["game_id"] = "forbidden"
    unsafe_report = validate(unsafe_result, current, RESULT_SHA256)
    tests["prohibited_identifier_blocks"] = unsafe_report["checks_failed"] > 0
    assert tests["prohibited_identifier_blocks"], unsafe_report
    return tests


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--current-status", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    result = read_json(args.result)
    current = read_json(args.current_status)
    result_sha = sha256_json_file(args.result)
    report = validate(result, current, result_sha)
    if args.self_test:
        report["self_test"] = self_test(result, current)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["checks_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
