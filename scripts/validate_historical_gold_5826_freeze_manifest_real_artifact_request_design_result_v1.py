#!/usr/bin/env python3
"""Validate the recorded Gold 5,826 real-Artifact request-design result."""
from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RESULT_STATE = "HISTORICAL_GOLD_5826_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_REQUEST_DESIGN_VALIDATED"
STATUS_STATE = "HISTORICAL_GOLD_5826_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_REQUEST_DESIGN_VALIDATED_READY_FOR_REQUEST_DRAFT"
NEXT = "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_REQUEST_READY_FOR_DRAFT"
ARTIFACT_DIGEST = "sha256:a4c0dce31c951fc0913bffc084411a9353928468fe1baafc0a412e050283c3e9"
SOURCE_ARTIFACT_DIGEST = "sha256:3ed2d28da3af58b8b72d805860a144541ac5f38106653cfbda593e16bbaa8e8d"
GOLD_SHA = "sha256:a4e94fab1681b53817f305d08c196995d406fa0566ab70d6083aa5cebfc52085"


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def validate(result: dict[str, Any], status: dict[str, Any], design: dict[str, Any]) -> dict[str, Any]:
    checks: dict[str, bool] = {}

    def add(name: str, condition: Any) -> None:
        checks[name] = bool(condition)

    add("result_schema", result.get("schema_version") == "historical-gold-5826-freeze-manifest-real-artifact-execution-request-design-result-v1")
    add("result_state", result.get("formal_state") == RESULT_STATE)
    evidence = result.get("recording_evidence", {})
    add("design_pr", evidence.get("design_pr") == 141)
    add("design_merge", evidence.get("design_merge_commit") == "5c6431110b7085dec1663cf6303df5393fd4dd97")
    add("validated_head", evidence.get("validated_head_sha") == "f84a217b0f4b2d144c58032f5edc793a2b92553b")
    add("run", evidence.get("workflow_run_id") == 29986783982)
    add("job", evidence.get("workflow_job_id") == 89140319716)
    add("job_name", evidence.get("workflow_job_name") == "validate-request-design")
    add("conclusion", evidence.get("workflow_conclusion") == "success")
    add("validation_artifact", evidence.get("validation_artifact_id") == 8555320565)
    add("validation_digest", evidence.get("validation_artifact_digest") == ARTIFACT_DIGEST)
    add("validation_size", evidence.get("validation_artifact_size_bytes") == 2637)
    add("validation_expiry", evidence.get("validation_artifact_expires_at") == "2026-08-06T06:59:00Z")

    contract = result.get("validated_contract", {})
    add("source_artifact", contract.get("exact_artifact_id") == 8551587005)
    add("source_name", contract.get("exact_artifact_name") == "historical-silver-gold-two-game-official-cdn-recovery-v2")
    add("source_digest", contract.get("exact_artifact_archive_digest") == SOURCE_ARTIFACT_DIGEST)
    add("source_expiry", contract.get("exact_artifact_expires_at") == "2026-08-06T03:14:00Z")
    add("gold_filename", contract.get("exact_gold_filename") == "historical-gold-multiseason-recovered-v1.sqlite.gz")
    add("gold_size", contract.get("exact_gold_size_bytes") == 5268851)
    add("gold_sha", contract.get("exact_gold_sha256") == GOLD_SHA)
    add("one_execution", contract.get("maximum_execution_count") == 1)
    add("dispatch_only", contract.get("workflow_dispatch_only") is True)
    add("main_only", contract.get("manual_dispatch_branch") == "main")
    add("separate_approval", contract.get("separate_explicit_user_approval_required") is True)
    add("consumed_after_attempt", contract.get("request_consumed_after_any_execution_attempt") is True)
    add("no_rerun", contract.get("workflow_rerun_allowed") is False)
    add("no_auto", contract.get("automatic_dispatch_allowed") is False)
    add("artifact_transport", contract.get("github_artifact_transport_only") is True)
    add("no_silver_read", contract.get("silver_database_read_allowed") is False)
    add("gold_read_only", contract.get("gold_database_read_only") is True)
    add("no_repo_db_write", contract.get("repository_database_write_allowed") is False)
    add("output_count", contract.get("aggregate_output_file_count") == 2)
    add("output_size", contract.get("aggregate_output_maximum_bytes") == 1048576)
    add("fail_closed", contract.get("fail_closed_on_expiry_or_identity_mismatch") is True)

    summary = result.get("validation_summary", {})
    add("checks_zero", summary.get("checks_failed") == 0)
    add("fixture_pass", summary.get("synthetic_request_fixture_passed") is True)
    add("mutations", summary.get("mutation_test_count_at_least", 0) >= 30)
    add("mutations_pass", summary.get("all_mutation_tests_passed") is True)
    add("synthetic_preserved", summary.get("synthetic_builder_tests_preserved") == 20)
    add("exceptions_zero", summary.get("source_exceptions_remaining") == 0)
    add("pit_zero", summary.get("point_in_time_violations") == 0)

    lifecycle = result.get("lifecycle_state", {})
    add("design_created", lifecycle.get("request_design_created") is True)
    add("design_validated", lifecycle.get("request_design_validated") is True)
    for key in (
        "request_draft_created",
        "request_validated",
        "approval_record_created",
        "approval_validated",
        "execution_workflow_created",
        "execution_enabled",
        "request_consumed",
        "repeat_execution_allowed",
        "automatic_dispatch_allowed",
        "real_artifact_downloaded",
        "real_artifact_read",
        "semantic_manifest_created",
        "corpus_frozen",
    ):
        add(f"result_{key}", lifecycle.get(key) is False)
    add("execution_zero", lifecycle.get("execution_count") == 0 and lifecycle.get("maximum_execution_count") == 1)

    scientific = result.get("scientific_boundaries", {})
    for key in (
        "market_backtest_executed",
        "model_training_or_retraining_executed",
        "injury_candidate_activated",
        "betting_edge_claim",
    ):
        add(f"scientific_{key}", scientific.get(key) is False)
    add("scientific_stake", scientific.get("formal_stake") == 0)
    add("result_next", result.get("next_research_step") == NEXT)
    add("result_ready_draft", result.get("ready_for_request_draft") is True)
    for key in (
        "ready_for_explicit_user_approval",
        "ready_for_real_artifact_execution",
        "ready_for_corpus_freeze_claim",
        "ready_for_market_backtest",
        "ready_for_model_retraining",
    ):
        add(f"result_{key}", result.get(key) is False)
    add("result_stake", result.get("formal_stake") == 0)

    add("status_schema", status.get("schema_version") == "historical-gold-5826-freeze-manifest-real-artifact-execution-request-design-current-status-v1")
    add("status_state", status.get("formal_state") == STATUS_STATE)
    add("status_result_path", status.get("result_path") == "data/research/historical-gold-5826-freeze-manifest-real-artifact-execution-request-design-result-v1.json")
    status_evidence = status.get("design_validation_evidence", {})
    add("status_run", status_evidence.get("workflow_run_id") == 29986783982)
    add("status_artifact", status_evidence.get("validation_artifact_id") == 8555320565)
    add("status_digest", status_evidence.get("validation_artifact_digest") == ARTIFACT_DIGEST)
    add("status_mutations", status_evidence.get("mutation_test_count_at_least", 0) >= 30 and status_evidence.get("all_mutation_tests_passed") is True)
    status_lifecycle = status.get("request_lifecycle", {})
    add("status_design_created", status_lifecycle.get("request_design_created") is True)
    add("status_design_validated", status_lifecycle.get("request_design_validated") is True)
    for key in (
        "request_draft_created",
        "request_validated",
        "approval_record_created",
        "approval_validated",
        "execution_workflow_created",
        "execution_enabled",
        "request_consumed",
        "repeat_execution_allowed",
        "automatic_dispatch_allowed",
        "real_artifact_downloaded",
        "real_artifact_read",
        "semantic_manifest_created",
        "corpus_frozen",
    ):
        add(f"status_{key}", status_lifecycle.get(key) is False)
    add("status_execution_zero", status_lifecycle.get("execution_count") == 0 and status_lifecycle.get("maximum_execution_count") == 1)
    add("status_next", status.get("next_research_step") == NEXT)
    add("status_ready_draft", status.get("ready_for_request_draft") is True)
    for key in (
        "ready_for_explicit_user_approval",
        "ready_for_real_artifact_execution",
        "ready_for_corpus_freeze_claim",
        "ready_for_market_backtest",
        "ready_for_model_retraining",
    ):
        add(f"status_{key}", status.get(key) is False)
    add("status_stake", status.get("formal_stake") == 0)

    add("design_schema", design.get("schema_version") == "historical-gold-5826-freeze-manifest-real-artifact-execution-request-design-v1")
    add("design_state", design.get("formal_state") == "HISTORICAL_GOLD_5826_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_REQUEST_DESIGN_READY")
    next_state = design.get("next_state_if_valid", {})
    add("design_next", next_state.get("next_research_step") == NEXT)
    add("design_ready_draft", next_state.get("ready_for_request_draft") is True)
    add("design_not_ready_execution", next_state.get("ready_for_real_artifact_execution") is False)
    add("design_stake", next_state.get("formal_stake") == 0)

    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": "historical-gold-5826-freeze-manifest-real-artifact-request-design-result-validation-report-v1",
        "validated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "formal_state": "HISTORICAL_GOLD_5826_FREEZE_MANIFEST_REAL_ARTIFACT_REQUEST_DESIGN_RESULT_VALID" if not failed else "HISTORICAL_GOLD_5826_FREEZE_MANIFEST_REAL_ARTIFACT_REQUEST_DESIGN_RESULT_INVALID",
        "checks": checks,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "checks_failed": len(failed),
        "failed_checks": failed,
        "artifact_id": 8551587005 if not failed else None,
        "request_design_validated": not failed,
        "request_draft_created": False,
        "approval_created": False,
        "execution_workflow_created": False,
        "real_artifact_read": False,
        "ready_for_request_draft": not failed,
        "ready_for_explicit_user_approval": False,
        "ready_for_real_artifact_execution": False,
        "ready_for_corpus_freeze_claim": False,
        "ready_for_market_backtest": False,
        "ready_for_model_retraining": False,
        "formal_stake": 0,
    }


def self_test(result: dict[str, Any], status: dict[str, Any], design: dict[str, Any]) -> dict[str, bool]:
    baseline = validate(result, status, design)
    assert baseline["checks_failed"] == 0, baseline
    output: dict[str, bool] = {"baseline_passes": True}
    mutations = {
        "wrong_run_blocks": ("result", ("recording_evidence", "workflow_run_id"), 1),
        "wrong_digest_blocks": ("result", ("recording_evidence", "validation_artifact_digest"), "sha256:bad"),
        "wrong_source_artifact_blocks": ("result", ("validated_contract", "exact_artifact_id"), 1),
        "wrong_gold_sha_blocks": ("result", ("validated_contract", "exact_gold_sha256"), "sha256:bad"),
        "two_executions_blocks": ("result", ("validated_contract", "maximum_execution_count"), 2),
        "auto_dispatch_blocks": ("result", ("validated_contract", "automatic_dispatch_allowed"), True),
        "rerun_blocks": ("result", ("validated_contract", "workflow_rerun_allowed"), True),
        "silver_read_blocks": ("result", ("validated_contract", "silver_database_read_allowed"), True),
        "request_created_blocks": ("result", ("lifecycle_state", "request_draft_created"), True),
        "approval_blocks": ("result", ("lifecycle_state", "approval_record_created"), True),
        "execution_blocks": ("result", ("lifecycle_state", "execution_workflow_created"), True),
        "real_read_blocks": ("result", ("lifecycle_state", "real_artifact_read"), True),
        "manifest_blocks": ("result", ("lifecycle_state", "semantic_manifest_created"), True),
        "wrong_next_blocks": ("status", ("next_research_step",), "WRONG"),
        "status_request_blocks": ("status", ("request_lifecycle", "request_draft_created"), True),
        "status_approval_blocks": ("status", ("request_lifecycle", "approval_record_created"), True),
        "status_execution_blocks": ("status", ("request_lifecycle", "execution_count"), 1),
        "status_consumed_blocks": ("status", ("request_lifecycle", "request_consumed"), True),
        "status_real_read_blocks": ("status", ("request_lifecycle", "real_artifact_read"), True),
        "nonzero_stake_blocks": ("status", ("formal_stake",), 1),
    }
    for name, (target, path, replacement) in mutations.items():
        r = copy.deepcopy(result)
        s = copy.deepcopy(status)
        d = copy.deepcopy(design)
        obj = {"result": r, "status": s, "design": d}[target]
        cursor = obj
        for key in path[:-1]:
            cursor = cursor[key]
        cursor[path[-1]] = replacement
        report = validate(r, s, d)
        output[name] = report["checks_failed"] > 0
        assert output[name], (name, report)
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--current-status", required=True, type=Path)
    parser.add_argument("--design", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    result = load(args.result)
    status = load(args.current_status)
    design = load(args.design)
    report = validate(result, status, design)
    if args.self_test:
        report["self_test"] = self_test(result, status, design)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["checks_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
