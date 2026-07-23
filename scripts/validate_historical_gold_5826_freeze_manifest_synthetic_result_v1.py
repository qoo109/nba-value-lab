#!/usr/bin/env python3
"""Validate the recorded Gold 5,826 freeze-manifest synthetic result."""
from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RESULT_STATE = "HISTORICAL_GOLD_5826_FREEZE_MANIFEST_IMPLEMENTATION_SYNTHETIC_VALID"
STATUS_STATE = "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_IMPLEMENTATION_SYNTHETIC_VALIDATED_READY_FOR_REAL_ARTIFACT_EXECUTION_REQUEST_DESIGN"
NEXT = "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_REQUEST_READY_FOR_DESIGN"
ARTIFACT_DIGEST = "sha256:1ecf4862ff87c3eb23ccb8d6b1c9860a229b54b8c76c469930dd2723da213f6f"
EXPECTED_TESTS = {
    "stable_digest_repeats_identically",
    "row_insertion_order_does_not_change_digest",
    "volatile_feature_generated_at_change_does_not_change_digest",
    "policy_excluded_metadata_change_does_not_change_digest",
    "stable_feature_change_changes_table_and_corpus_digest",
    "stable_metadata_change_changes_metadata_and_corpus_digest",
    "missing_required_table_blocks",
    "unexpected_schema_column_blocks",
    "missing_stable_schema_column_blocks",
    "wrong_row_count_blocks",
    "duplicate_team_game_key_blocks",
    "orphan_or_incomplete_matchup_blocks",
    "wrong_season_set_blocks",
    "blank_date_blocks",
    "non_finite_real_blocks",
    "blob_value_blocks",
    "database_write_attempt_blocks",
    "database_sha_change_blocks",
    "forbidden_output_key_blocks",
    "output_size_limit_blocks",
}


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def validate(result: dict[str, Any], status: dict[str, Any]) -> dict[str, Any]:
    checks: dict[str, bool] = {}

    def add(name: str, condition: Any) -> None:
        checks[name] = bool(condition)

    add("result_schema", result.get("schema_version") == "historical-gold-5826-complete-corpus-freeze-manifest-synthetic-implementation-result-v1")
    add("result_state", result.get("formal_state") == RESULT_STATE)
    implementation = result.get("implementation", {})
    add("builder_path", implementation.get("builder_path") == "scripts/build_historical_gold_5826_complete_corpus_freeze_manifest_v1.py")
    add("test_path", implementation.get("synthetic_test_path") == "scripts/test_build_historical_gold_5826_complete_corpus_freeze_manifest_v1.py")
    add("workflow_path", implementation.get("workflow_path") == ".github/workflows/validate-historical-gold-5826-freeze-manifest-synthetic-implementation-v1.yml")
    add("implementation_pr", implementation.get("recording_pr") == 139)
    add("implementation_merge", implementation.get("recording_merge_commit") == "b561c941b5fc27a0bda3fa790244ff92c35b5c0b")
    add("validated_head", implementation.get("validated_head_sha") == "04fdbe44f642af85bc287a02a2f978f12bf62cb0")

    evidence = result.get("validation_evidence", {})
    add("run", evidence.get("workflow_run_id") == 29984329419)
    add("job", evidence.get("workflow_job_id") == 89132779309)
    add("job_name", evidence.get("workflow_job_name") == "validate-synthetic-implementation")
    add("conclusion", evidence.get("workflow_conclusion") == "success")
    add("artifact", evidence.get("artifact_id") == 8554394051)
    add("artifact_name", evidence.get("artifact_name") == "historical-gold-5826-freeze-manifest-synthetic-implementation-validation-v1")
    add("artifact_digest", evidence.get("artifact_digest") == ARTIFACT_DIGEST)
    add("artifact_size", evidence.get("artifact_size_bytes") == 864)
    add("artifact_expiry", evidence.get("artifact_expires_at") == "2026-08-06T06:12:27Z")
    add("report_schema", evidence.get("aggregate_report_schema") == "historical-gold-5826-freeze-manifest-synthetic-validation-report-v1")

    synthetic = result.get("synthetic_validation", {})
    add("tests_total", synthetic.get("tests_total") == 20)
    add("tests_passed", synthetic.get("tests_passed") == 20)
    add("tests_failed", synthetic.get("tests_failed") == 0)
    add("failed_tests_empty", synthetic.get("failed_tests") == [])
    tests = synthetic.get("tests", {})
    add("tests_exact", set(tests) == EXPECTED_TESTS)
    add("all_tests_true", all(tests.get(name) is True for name in EXPECTED_TESTS))

    properties = result.get("implementation_properties", {})
    for key in (
        "python_standard_library_only", "offline_only", "sqlite_uri_read_only", "sqlite_immutable",
        "sqlite_query_only", "sqlite_integrity_check_required", "pre_and_post_database_sha256_equality_required",
        "exact_schema_contract_required", "exact_relational_alignment_required", "policy_only_volatile_exclusions",
        "canonical_type_tagged_json_lines", "incremental_sha256", "aggregate_only_output",
    ):
        add(f"property_{key}", properties.get(key) is True)
    add("output_limit", properties.get("maximum_output_bytes") == 1048576)
    add("no_raw_identifiers", properties.get("raw_rows_or_identifiers_emitted") is False)
    add("no_row_hashes", properties.get("row_level_hashes_emitted") is False)

    corpus = result.get("governed_corpus", {})
    add("gold_matchups", corpus.get("gold_matchup_features") == 5826)
    add("gold_team_rows", corpus.get("gold_team_game_features") == 11652)
    add("exceptions_zero", corpus.get("remaining_source_exceptions") == 0)
    add("pit_zero", corpus.get("point_in_time_violations") == 0)
    add("seasons", corpus.get("seasons") == ["2019-20", "2020-21", "2021-22", "2022-23", "2023-24"])

    boundary = result.get("real_artifact_boundary", {})
    add("preferred_artifact", boundary.get("preferred_artifact_id") == 8551587005)
    add("preferred_expiry", boundary.get("preferred_artifact_expires_at") == "2026-08-06T03:14:00Z")
    for key in (
        "real_artifact_downloaded", "real_artifact_read", "real_execution_workflow_created",
        "real_execution_approved", "semantic_manifest_created", "corpus_frozen", "repeat_execution_allowed",
    ):
        add(f"boundary_{key}", boundary.get(key) is False)
    add("execution_zero", boundary.get("real_execution_count") == 0)

    scientific = result.get("scientific_boundaries", {})
    for key in (
        "market_backtest_executed", "model_training_or_retraining_executed",
        "injury_candidate_activated", "betting_edge_claim",
    ):
        add(f"scientific_{key}", scientific.get(key) is False)
    add("scientific_stake", scientific.get("formal_stake") == 0)
    add("result_next", result.get("next_research_step") == NEXT)
    add("result_ready_design", result.get("ready_for_real_artifact_execution_request_design") is True)
    add("result_not_ready_execution", result.get("ready_for_real_artifact_execution") is False)
    add("result_not_ready_market", result.get("ready_for_market_backtest") is False)
    add("result_not_ready_retrain", result.get("ready_for_model_retraining") is False)
    add("result_stake", result.get("formal_stake") == 0)

    add("status_schema", status.get("schema_version") == "historical-gold-5826-complete-corpus-freeze-manifest-implementation-current-status-v1")
    add("status_state", status.get("formal_state") == STATUS_STATE)
    add("status_result_path", status.get("result_path") == "data/research/historical-gold-5826-complete-corpus-freeze-manifest-synthetic-implementation-result-v1.json")
    status_evidence = status.get("synthetic_validation_evidence", {})
    add("status_run", status_evidence.get("workflow_run_id") == 29984329419)
    add("status_artifact", status_evidence.get("artifact_id") == 8554394051)
    add("status_digest", status_evidence.get("artifact_digest") == ARTIFACT_DIGEST)
    add("status_tests", (status_evidence.get("tests_total"), status_evidence.get("tests_passed"), status_evidence.get("tests_failed")) == (20, 20, 0))
    state = status.get("implementation_state", {})
    add("status_module", state.get("implementation_module_created") is True)
    add("status_synthetic_executed", state.get("synthetic_sqlite_tests_executed") is True)
    add("status_synthetic_passed", state.get("synthetic_sqlite_tests_passed") is True)
    add("status_request_design_absent", state.get("real_artifact_execution_request_design_created") is False)
    add("status_request_absent", state.get("real_artifact_execution_request_created") is False)
    add("status_workflow_absent", state.get("real_artifact_execution_workflow_created") is False)
    add("status_approval_absent", state.get("real_artifact_execution_approved") is False)
    add("status_execution_zero", state.get("real_artifact_execution_count") == 0)
    add("status_manifest_absent", state.get("semantic_manifest_created") is False)
    add("status_not_frozen", state.get("corpus_frozen") is False)
    add("status_next", status.get("next_research_step") == NEXT)
    add("status_ready_design", status.get("ready_for_real_artifact_execution_request_design") is True)
    add("status_not_ready_execution", status.get("ready_for_real_artifact_execution") is False)
    add("status_not_ready_market", status.get("ready_for_market_backtest") is False)
    add("status_not_ready_retrain", status.get("ready_for_model_retraining") is False)
    add("status_stake", status.get("formal_stake") == 0)

    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": "historical-gold-5826-freeze-manifest-synthetic-result-validation-report-v1",
        "validated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "formal_state": "HISTORICAL_GOLD_5826_FREEZE_MANIFEST_SYNTHETIC_RESULT_VALID" if not failed else "HISTORICAL_GOLD_5826_FREEZE_MANIFEST_SYNTHETIC_RESULT_INVALID",
        "checks": checks,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "checks_failed": len(failed),
        "failed_checks": failed,
        "tests_total": 20 if not failed else None,
        "tests_passed": 20 if not failed else None,
        "tests_failed": 0 if not failed else None,
        "ready_for_real_artifact_execution_request_design": not failed,
        "ready_for_real_artifact_execution": False,
        "ready_for_market_backtest": False,
        "ready_for_model_retraining": False,
        "formal_stake": 0,
    }


def self_test(result: dict[str, Any], status: dict[str, Any]) -> dict[str, bool]:
    baseline = validate(result, status)
    assert baseline["checks_failed"] == 0, baseline
    mutations = {
        "failed_test_blocks": ("result", ("synthetic_validation", "tests_failed"), 1),
        "test_false_blocks": ("result", ("synthetic_validation", "tests", "blank_date_blocks"), False),
        "wrong_digest_blocks": ("result", ("validation_evidence", "artifact_digest"), "sha256:bad"),
        "real_read_blocks": ("result", ("real_artifact_boundary", "real_artifact_read"), True),
        "workflow_created_blocks": ("result", ("real_artifact_boundary", "real_execution_workflow_created"), True),
        "execution_blocks": ("result", ("real_artifact_boundary", "real_execution_count"), 1),
        "manifest_blocks": ("result", ("real_artifact_boundary", "semantic_manifest_created"), True),
        "market_blocks": ("result", ("scientific_boundaries", "market_backtest_executed"), True),
        "wrong_next_blocks": ("status", ("next_research_step",), "WRONG"),
        "status_request_blocks": ("status", ("implementation_state", "real_artifact_execution_request_created"), True),
        "status_approval_blocks": ("status", ("implementation_state", "real_artifact_execution_approved"), True),
        "nonzero_stake_blocks": ("status", ("formal_stake",), 1),
    }
    output: dict[str, bool] = {"baseline_passes": True}
    for name, (target, path, replacement) in mutations.items():
        r = copy.deepcopy(result)
        s = copy.deepcopy(status)
        obj = r if target == "result" else s
        cursor = obj
        for key in path[:-1]:
            cursor = cursor[key]
        cursor[path[-1]] = replacement
        output[name] = validate(r, s)["checks_failed"] > 0
        assert output[name], name
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--current-status", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    result = load(args.result)
    status = load(args.current_status)
    report = validate(result, status)
    if args.self_test:
        report["self_test"] = self_test(result, status)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["checks_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
