#!/usr/bin/env python3
"""Validate Eoin secondary QA integration policy v1 without source-data access."""
from __future__ import annotations

import argparse
import copy
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

POLICY_SCHEMA = "eoin-secondary-qa-integration-policy-v1"
REPORT_SCHEMA = "eoin-secondary-qa-integration-policy-validation-v1"
READY_STATE = "EOIN_SECONDARY_QA_INTEGRATION_POLICY_READY_FOR_IMPLEMENTATION"
BLOCKED_STATE = "EOIN_SECONDARY_QA_INTEGRATION_POLICY_BLOCKED"
VALIDATED_ROLE = "ROLE_LIMITED_SECONDARY_QA_SOURCE_VALIDATED"
EXPECTED_DOMAINS = {
    "game_identity_qa",
    "final_score_qa",
    "team_boxscore_qa",
    "player_boxscore_candidate_coverage_only",
    "pbp_game_coverage_qa",
    "cross_source_regression_detection",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def validate(
    policy: dict[str, Any],
    cross_report: dict[str, Any],
    role_policy: dict[str, Any],
    evaluation_manifest: dict[str, Any],
) -> dict[str, Any]:
    checks: dict[str, bool] = {}

    def check(name: str, condition: bool) -> None:
        checks[name] = bool(condition)

    check("schema_version", policy.get("schema_version") == POLICY_SCHEMA)
    check("source_id", policy.get("source_id") == "kaggle_eoinamoore_historical_nba")
    check("current_role", policy.get("current_formal_role") == VALIDATED_ROLE)
    check("policy_state", policy.get("policy_state") == "SECONDARY_QA_INTEGRATION_POLICY_PREDECLARED")

    pinned = policy.get("pinned_evidence") or {}
    cross = pinned.get("cross_source_audit") or {}
    execution = pinned.get("one_time_aggregate_execution") or {}
    review_policy = pinned.get("role_review_policy") or {}
    evaluation = pinned.get("role_review_evaluation") or {}

    check(
        "cross_source_pin",
        cross.get("repository_report") == "data/eoin-cross-source-audit-v1.json"
        and cross.get("repository_blob_sha") == "b0f758c3a78e060fa00337ae1e9a6011decb568f"
        and cross.get("formal_outcome") == "ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE"
        and cross.get("workflow_run_id") == 29672984966
        and cross.get("artifact_id") == 8437932113
        and cross.get("artifact_digest")
        == "sha256:96a87c6b52614ea6f7478e1bdbcc729c7c8eb2347490ca236475444ca5fcc63a",
    )
    check(
        "cross_source_report_match",
        cross_report.get("formal_outcome") == cross.get("formal_outcome")
        and (cross_report.get("workflow") or {}).get("run_id") == cross.get("workflow_run_id")
        and (cross_report.get("workflow") or {}).get("artifact_id") == cross.get("artifact_id")
        and (cross_report.get("workflow") or {}).get("artifact_digest") == cross.get("artifact_digest")
        and cross_report.get("deterministic_matching_only") is True
        and cross_report.get("fuzzy_matching") is False
        and (cross_report.get("boundaries") or {}).get("raw_rows_emitted") == 0
        and (cross_report.get("boundaries") or {}).get("raw_files_emitted") is False,
    )
    check(
        "execution_pin",
        execution.get("formal_outcome") == "ONE_TIME_FULL_ADAPTER_AGGREGATE_VALIDATION_PASS"
        and execution.get("workflow_run_id") == 29680729672
        and execution.get("artifact_id") == 8440485189
        and execution.get("artifact_digest")
        == "sha256:e068940df05bfc51d8757aef500e9c6f812687bfa171b5fff8680ee3b59bb56c"
        and execution.get("request_id") == "EOIN-FULL-ADAPTER-2026-07-19-001"
        and execution.get("request_consumed") is True
        and execution.get("execution_count") == 1,
    )
    check(
        "role_policy_pin",
        review_policy.get("repository_policy") == "data/eoin-post-execution-role-review-policy-v1.json"
        and review_policy.get("formal_state") == "EOIN_POST_EXECUTION_ROLE_REVIEW_POLICY_READY"
        and review_policy.get("workflow_run_id") == 29794965150
        and review_policy.get("artifact_id") == 8481660306
        and review_policy.get("artifact_digest")
        == "sha256:1b309073ae19c23483225b1264ea982ef1f6d71f1d482cd124ad63fc0bfd77d0",
    )
    check(
        "role_policy_file_match",
        (role_policy.get("next_state_if_policy_validation_passes") or {}).get("formal_state")
        == review_policy.get("formal_state")
        and role_policy.get("maximum_possible_role_if_later_evaluation_passes") == VALIDATED_ROLE,
    )
    check(
        "evaluation_pin",
        evaluation.get("repository_manifest") == "data/eoin-post-execution-role-review-evaluation-v1.json"
        and evaluation.get("formal_outcome") == VALIDATED_ROLE
        and evaluation.get("workflow_run_id") == 29795498102
        and evaluation.get("artifact_id") == 8481840798
        and evaluation.get("artifact_digest")
        == "sha256:f64248d5a3eaab52aa6a24fc36980144c5c962a31b91a4057834af1d36e42fd1"
        and evaluation.get("evaluation_merge_sha") == "ce0620cb46f5074ee9ab506cd300d5898014dbbf",
    )
    check(
        "evaluation_manifest_match",
        (evaluation_manifest.get("expected_result_for_frozen_evidence") or {}).get("formal_outcome")
        == VALIDATED_ROLE
        and (evaluation_manifest.get("role_boundary") or {}).get("maximum_possible_role")
        == VALIDATED_ROLE,
    )

    scope = policy.get("allowed_integration_scope") or {}
    check(
        "alert_only_scope",
        scope.get("contract_integrity_check") is True
        and scope.get("pinned_evidence_identity_check") is True
        and scope.get("formal_role_consistency_check") is True
        and scope.get("forbidden_permission_regression_check") is True
        and scope.get("evidence_freshness_check") is True
        and scope.get("deterministic_qa_domain_registry_check") is True
        and scope.get("alert_only") is True,
    )
    check("allowed_domains", set(scope.get("allowed_qa_domains") or []) == EXPECTED_DOMAINS)

    boundary = policy.get("execution_boundary") or {}
    boundary_false_keys = (
        "network_calls_allowed",
        "kaggle_download_allowed",
        "external_artifact_download_allowed",
        "new_bundle_execution_allowed",
        "raw_source_rows_read_allowed",
        "source_archive_read_allowed",
        "database_read_allowed",
        "fuzzy_matching_allowed",
        "scheduled_execution_allowed",
        "concurrent_execution_allowed",
        "automatic_data_mutation_allowed",
    )
    check("execution_boundary", all(boundary.get(key) is False for key in boundary_false_keys))

    targets = policy.get("integration_targets") or {}
    check(
        "alert_targets_only",
        targets.get("historical_silver_build_gate") is False
        and targets.get("historical_gold_build_gate") is False
        and targets.get("model_feature_pipeline") is False
        and targets.get("model_training_pipeline") is False
        and targets.get("market_backtest_pipeline") is False
        and targets.get("betting_decision_pipeline") is False
        and targets.get("research_status_alerts") is True
        and targets.get("source_registry_alerts") is True
        and targets.get("qa_dashboard_metadata") is True,
    )

    pinning = policy.get("version_pinning") or {}
    check(
        "strict_version_pinning",
        pinning.get("strict_artifact_id_and_digest_match_required") is True
        and pinning.get("strict_repository_path_match_required") is True
        and pinning.get("strict_formal_outcome_match_required") is True
        and pinning.get("strict_request_consumed_match_required") is True
        and pinning.get("strict_role_boundary_match_required") is True
        and pinning.get("unreviewed_evidence_substitution_allowed") is False,
    )

    freshness = policy.get("evidence_freshness") or {}
    try:
        evidence_as_of = date.fromisoformat(str(freshness.get("evidence_as_of")))
        review_due_at = date.fromisoformat(str(freshness.get("review_due_at")))
        valid_dates = review_due_at > evidence_as_of
    except ValueError:
        valid_dates = False
    check(
        "freshness_policy",
        valid_dates
        and freshness.get("review_interval_days") == 365
        and freshness.get("stale_behavior") == "ALERT_AND_DISABLE_QA_INTEGRATION"
        and freshness.get("automatic_reexecution_allowed") is False
        and freshness.get("new_execution_requires_separate_policy_and_explicit_approval") is True,
    )

    fail_closed = policy.get("fail_closed_policy") or {}
    check(
        "fail_closed_policy",
        fail_closed.get("contract_mismatch") == "ALERT_AND_DISABLE_QA_INTEGRATION"
        and fail_closed.get("artifact_identity_mismatch") == "ALERT_AND_DISABLE_QA_INTEGRATION"
        and fail_closed.get("role_drift") == "ALERT_AND_DISABLE_QA_INTEGRATION"
        and fail_closed.get("forbidden_permission_enabled") == "BLOCKED"
        and fail_closed.get("evidence_stale") == "ALERT_AND_DISABLE_QA_INTEGRATION"
        and fail_closed.get("missing_required_evidence") == "BLOCKED"
        and fail_closed.get("never_mutate_primary_data_on_alert") is True
        and fail_closed.get("never_mutate_model_or_market_outputs_on_alert") is True,
    )

    output = policy.get("allowed_public_output") or {}
    check(
        "output_boundary",
        output.get("aggregate_contract_report") is True
        and output.get("alert_summary") is True
        and output.get("maximum_output_files") == 1
        and output.get("maximum_output_bytes") == 1048576
        and output.get("raw_rows_emitted") == 0
        and output.get("raw_files_emitted") is False
        and output.get("derived_tables_emitted") is False
        and output.get("archives_or_databases_emitted") is False,
    )

    forbidden = policy.get("forbidden_promotions") or {}
    forbidden_false_keys = (
        "primary_source_allowed",
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
        "repeat_full_bundle_execution_allowed",
    )
    check("forbidden_promotions", all(forbidden.get(key) is False for key in forbidden_false_keys))
    check("formal_stake", forbidden.get("formal_stake") == 0)

    check(
        "decision_states",
        set(policy.get("integration_states") or [])
        == {BLOCKED_STATE, READY_STATE},
    )
    next_state = policy.get("next_state_if_policy_validation_passes") or {}
    check("next_state", next_state.get("formal_state") == READY_STATE)
    check("implementation_ready", next_state.get("ready_for_contract_monitor_implementation") is True)
    check(
        "integration_inactive",
        next_state.get("integration_active") is False
        and next_state.get("current_formal_role_unchanged") is True,
    )
    check(
        "downstream_locked",
        next_state.get("ready_for_data_layer_mutation") is False
        and next_state.get("ready_for_player_stat_parity") is False
        and next_state.get("ready_for_model_retraining") is False
        and next_state.get("ready_for_market_backtest") is False
        and next_state.get("ready_for_betting_edge_claim") is False
        and next_state.get("formal_stake") == 0,
    )

    failures = sorted(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": REPORT_SCHEMA,
        "validated_at": utc_now(),
        "formal_state": READY_STATE if not failures else BLOCKED_STATE,
        "current_formal_role": policy.get("current_formal_role"),
        "checks": checks,
        "passed_checks": sum(checks.values()),
        "total_checks": len(checks),
        "checks_failed": len(failures),
        "failed_checks": failures,
        "quality": {
            "network_calls_made": False,
            "external_artifacts_downloaded": False,
            "new_bundle_execution_performed": False,
            "raw_eoin_rows_read": False,
            "raw_rows_emitted": 0,
            "raw_files_emitted": False,
            "derived_tables_emitted": False,
            "integration_active": False,
            "formal_stake": 0,
        },
        "decision": {
            "ready_for_contract_monitor_implementation": not failures,
            "current_formal_role_unchanged": True,
            "alert_only": True,
            "ready_for_primary_source_use": False,
            "ready_for_silver_replacement": False,
            "ready_for_gold_replacement": False,
            "ready_for_player_stat_parity": False,
            "ready_for_player_feature_import": False,
            "ready_for_model_retraining": False,
            "ready_for_market_backtest": False,
            "ready_for_betting_edge_claim": False,
            "ready_for_repeat_full_bundle_execution": False,
            "formal_stake": 0,
        },
    }


def self_test(
    policy: dict[str, Any],
    cross_report: dict[str, Any],
    role_policy: dict[str, Any],
    evaluation_manifest: dict[str, Any],
) -> None:
    report = validate(policy, cross_report, role_policy, evaluation_manifest)
    assert report["formal_state"] == READY_STATE, report
    assert report["checks_failed"] == 0, report

    mutated = copy.deepcopy(policy)
    mutated["execution_boundary"]["network_calls_allowed"] = True
    assert validate(mutated, cross_report, role_policy, evaluation_manifest)["formal_state"] == BLOCKED_STATE

    mutated = copy.deepcopy(policy)
    mutated["pinned_evidence"]["role_review_evaluation"]["artifact_digest"] = "sha256:changed"
    assert validate(mutated, cross_report, role_policy, evaluation_manifest)["formal_state"] == BLOCKED_STATE

    mutated = copy.deepcopy(policy)
    mutated["forbidden_promotions"]["model_retraining_allowed"] = True
    assert validate(mutated, cross_report, role_policy, evaluation_manifest)["formal_state"] == BLOCKED_STATE

    mutated = copy.deepcopy(policy)
    mutated["allowed_integration_scope"]["allowed_qa_domains"].append("player_stat_parity")
    assert validate(mutated, cross_report, role_policy, evaluation_manifest)["formal_state"] == BLOCKED_STATE


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--policy",
        type=Path,
        default=Path("data/eoin-secondary-qa-integration-policy-v1.json"),
    )
    parser.add_argument(
        "--cross-report",
        type=Path,
        default=Path("data/eoin-cross-source-audit-v1.json"),
    )
    parser.add_argument(
        "--role-policy",
        type=Path,
        default=Path("data/eoin-post-execution-role-review-policy-v1.json"),
    )
    parser.add_argument(
        "--evaluation-manifest",
        type=Path,
        default=Path("data/eoin-post-execution-role-review-evaluation-v1.json"),
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    policy = load_json(args.policy)
    cross_report = load_json(args.cross_report)
    role_policy = load_json(args.role_policy)
    evaluation_manifest = load_json(args.evaluation_manifest)

    if args.self_test:
        self_test(policy, cross_report, role_policy, evaluation_manifest)

    report = validate(policy, cross_report, role_policy, evaluation_manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "formal_state": report["formal_state"],
                "passed_checks": report["passed_checks"],
                "total_checks": report["total_checks"],
                "checks_failed": report["checks_failed"],
            },
            indent=2,
        )
    )
    return 0 if report["formal_state"] == READY_STATE else 1


if __name__ == "__main__":
    raise SystemExit(main())
