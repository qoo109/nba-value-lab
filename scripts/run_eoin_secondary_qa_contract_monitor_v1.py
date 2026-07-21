#!/usr/bin/env python3
"""Run the Eoin secondary QA evidence-contract monitor without source-data access."""
from __future__ import annotations

import argparse
import copy
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from validate_eoin_secondary_qa_integration_policy_v1 import (
    READY_STATE as POLICY_READY_STATE,
    load_json,
    validate as validate_policy,
)

SCHEMA_VERSION = "eoin-secondary-qa-contract-monitor-report-v1"
MANIFEST_SCHEMA = "eoin-secondary-qa-contract-monitor-v1"
MANIFEST_STATE = "SECONDARY_QA_CONTRACT_MONITOR_PREDECLARED"
HEALTHY = "EOIN_SECONDARY_QA_CONTRACT_HEALTHY"
ALERT_DISABLED = "EOIN_SECONDARY_QA_CONTRACT_ALERT_DISABLED"
BLOCKED = "EOIN_SECONDARY_QA_CONTRACT_BLOCKED"
VALIDATED_ROLE = "ROLE_LIMITED_SECONDARY_QA_SOURCE_VALIDATED"
REGISTRY_STATUS = "role_limited_secondary_qa_validated"
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


def find_source(registry: dict[str, Any], source_id: str) -> dict[str, Any] | None:
    for source in registry.get("sources") or []:
        if isinstance(source, dict) and source.get("source_id") == source_id:
            return source
    return None


def validate_manifest(manifest: dict[str, Any]) -> dict[str, bool]:
    checks: dict[str, bool] = {}
    checks["schema_version"] = manifest.get("schema_version") == MANIFEST_SCHEMA
    checks["source_id"] = manifest.get("source_id") == "kaggle_eoinamoore_historical_nba"
    checks["monitor_state"] = manifest.get("monitor_state") == MANIFEST_STATE
    checks["policy_path"] = manifest.get("integration_policy") == "data/eoin-secondary-qa-integration-policy-v1.json"
    checks["policy_state"] = manifest.get("integration_policy_required_state") == POLICY_READY_STATE
    checks["expected_role"] = manifest.get("expected_formal_role") == VALIDATED_ROLE
    checks["registry_status"] = manifest.get("expected_registry_status") == REGISTRY_STATUS

    expected_files = {
        "PROJECT_STATUS.md",
        "data/source-registry.json",
        "data/eoin-cross-source-audit-v1.json",
        "data/eoin-post-execution-role-review-policy-v1.json",
        "data/eoin-post-execution-role-review-evaluation-v1.json",
        "data/eoin-secondary-qa-integration-policy-v1.json",
    }
    checks["monitored_files"] = set(manifest.get("monitored_files") or []) == expected_files

    expected_contract_checks = {
        "integration_policy_validation",
        "formal_role_consistency",
        "source_registry_status_consistency",
        "source_registry_evaluation_evidence_consistency",
        "project_status_role_consistency",
        "request_consumed_and_repeat_disabled",
        "artifact_identity_and_digest_consistency",
        "forbidden_permission_regression",
        "evidence_freshness",
        "allowed_qa_domain_consistency",
    }
    checks["contract_checks"] = set(manifest.get("contract_checks") or []) == expected_contract_checks

    rules = manifest.get("state_rules") or {}
    checks["state_rules"] = (
        rules.get("healthy") == HEALTHY
        and rules.get("alert_disabled") == ALERT_DISABLED
        and rules.get("blocked") == BLOCKED
        and rules.get("stale_evidence") == ALERT_DISABLED
        and rules.get("role_or_artifact_drift") == ALERT_DISABLED
        and rules.get("forbidden_permission_or_missing_evidence") == BLOCKED
    )

    boundary = manifest.get("execution_boundary") or {}
    false_keys = (
        "network_calls_allowed",
        "external_artifact_download_allowed",
        "new_bundle_execution_allowed",
        "raw_source_rows_read_allowed",
        "source_archive_read_allowed",
        "database_read_allowed",
        "fuzzy_matching_allowed",
        "scheduled_execution_allowed",
        "automatic_data_mutation_allowed",
    )
    checks["execution_boundary"] = (
        all(boundary.get(key) is False for key in false_keys)
        and boundary.get("alert_only") is True
    )

    output = manifest.get("output_boundary") or {}
    checks["output_boundary"] = (
        output.get("aggregate_contract_report_only") is True
        and output.get("maximum_output_files") == 1
        and output.get("maximum_output_bytes") == 1048576
        and output.get("raw_rows_emitted") == 0
        and output.get("raw_files_emitted") is False
        and output.get("derived_tables_emitted") is False
        and output.get("archives_or_databases_emitted") is False
    )

    forbidden = manifest.get("forbidden_permissions") or {}
    forbidden_false_keys = (
        "primary_source_use",
        "historical_silver_replacement",
        "historical_gold_replacement",
        "player_stat_parity",
        "player_feature_import",
        "model_training_or_retraining",
        "market_backtest",
        "clv_ev_roi_drawdown",
        "betting_decision_layer",
        "betting_edge_claim",
        "repeat_full_bundle_execution",
    )
    checks["forbidden_permissions"] = (
        all(forbidden.get(key) is False for key in forbidden_false_keys)
        and forbidden.get("formal_stake") == 0
    )

    expected = manifest.get("expected_current_state") or {}
    expected_false_keys = (
        "source_data_integration_active",
        "ready_for_primary_source_use",
        "ready_for_silver_replacement",
        "ready_for_gold_replacement",
        "ready_for_player_stat_parity",
        "ready_for_player_feature_import",
        "ready_for_model_retraining",
        "ready_for_market_backtest",
        "ready_for_betting_edge_claim",
        "ready_for_repeat_full_bundle_execution",
    )
    checks["expected_state"] = (
        expected.get("formal_state") == HEALTHY
        and expected.get("integration_active_for_alerts_only") is True
        and expected.get("current_formal_role_unchanged") is True
        and all(expected.get(key) is False for key in expected_false_keys)
        and expected.get("formal_stake") == 0
    )
    return checks


def monitor(
    manifest: dict[str, Any],
    policy: dict[str, Any],
    cross_report: dict[str, Any],
    role_policy: dict[str, Any],
    evaluation_manifest: dict[str, Any],
    registry: dict[str, Any],
    project_status: str,
    as_of_date: date,
) -> dict[str, Any]:
    manifest_checks = validate_manifest(manifest)
    policy_report = validate_policy(policy, cross_report, role_policy, evaluation_manifest)
    alerts: list[str] = []
    blocking_failures: list[str] = []

    for name, passed in manifest_checks.items():
        if not passed:
            blocking_failures.append(f"manifest.{name}")
    if policy_report.get("formal_state") != POLICY_READY_STATE:
        blocking_failures.append("integration_policy.validation")

    source = find_source(registry, "kaggle_eoinamoore_historical_nba")
    if source is None:
        blocking_failures.append("source_registry.missing_eoin_source")
        source = {}

    if source.get("status") != REGISTRY_STATUS:
        alerts.append("source_registry.role_status_drift")

    evaluation = source.get("post_execution_role_review_evaluation") or {}
    expected_eval = (policy.get("pinned_evidence") or {}).get("role_review_evaluation") or {}
    evaluation_match = (
        evaluation.get("formal_outcome") == VALIDATED_ROLE
        and evaluation.get("workflow_run_id") == expected_eval.get("workflow_run_id")
        and evaluation.get("artifact_id") == expected_eval.get("artifact_id")
        and evaluation.get("artifact_digest") == expected_eval.get("artifact_digest")
        and evaluation.get("reviewed_formal_role") == VALIDATED_ROLE
        and evaluation.get("all_scientific_gates_passed") is True
        and evaluation.get("independent_player_stat_parity") is False
    )
    if not evaluation:
        blocking_failures.append("source_registry.missing_role_evaluation")
    elif not evaluation_match:
        alerts.append("source_registry.role_evaluation_drift")

    approval = source.get("one_time_execution_approval") or {}
    if not approval:
        blocking_failures.append("source_registry.missing_execution_approval")
    else:
        if approval.get("request_consumed") is not True:
            alerts.append("source_registry.request_not_consumed")
        if approval.get("ready_for_repeat_execution") is not False:
            alerts.append("source_registry.repeat_execution_drift")
        if approval.get("full_bundle_execution_count") != 1:
            alerts.append("source_registry.execution_count_drift")

    status_checks = {
        "formal_role": f"formal Eoin source role: {VALIDATED_ROLE}" in project_status,
        "request_consumed": "request consumed: true" in project_status,
        "repeat_disabled": "repeat execution allowed: false" in project_status,
        "stake_zero": "formal stake: 0" in project_status,
    }
    for name, passed in status_checks.items():
        if not passed:
            alerts.append(f"project_status.{name}_drift")

    pinned = policy.get("pinned_evidence") or {}
    cross_pin = pinned.get("cross_source_audit") or {}
    workflow = cross_report.get("workflow") or {}
    if not (
        workflow.get("run_id") == cross_pin.get("workflow_run_id")
        and workflow.get("artifact_id") == cross_pin.get("artifact_id")
        and workflow.get("artifact_digest") == cross_pin.get("artifact_digest")
    ):
        alerts.append("cross_source.artifact_identity_drift")

    allowed_domains = set((policy.get("allowed_integration_scope") or {}).get("allowed_qa_domains") or [])
    if allowed_domains != EXPECTED_DOMAINS:
        alerts.append("integration_policy.qa_domain_drift")

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
    enabled_forbidden = sorted(key for key in forbidden_false_keys if forbidden.get(key) is not False)
    if enabled_forbidden or forbidden.get("formal_stake") != 0:
        blocking_failures.extend(f"forbidden_permission.{key}" for key in enabled_forbidden)
        if forbidden.get("formal_stake") != 0:
            blocking_failures.append("forbidden_permission.nonzero_stake")

    freshness = policy.get("evidence_freshness") or {}
    try:
        due_date = date.fromisoformat(str(freshness.get("review_due_at")))
    except ValueError:
        blocking_failures.append("freshness.invalid_review_due_at")
        due_date = date.min
    evidence_stale = as_of_date > due_date
    if evidence_stale:
        alerts.append("freshness.evidence_stale")

    blocking_failures = sorted(set(blocking_failures))
    alerts = sorted(set(alerts))
    if blocking_failures:
        formal_state = BLOCKED
    elif alerts:
        formal_state = ALERT_DISABLED
    else:
        formal_state = HEALTHY

    return {
        "schema_version": SCHEMA_VERSION,
        "monitored_at": utc_now(),
        "as_of_date": as_of_date.isoformat(),
        "formal_state": formal_state,
        "source_id": "kaggle_eoinamoore_historical_nba",
        "formal_role": VALIDATED_ROLE,
        "integration_mode": "alert_only_evidence_contract_monitor",
        "integration_active_for_alerts_only": formal_state == HEALTHY,
        "source_data_integration_active": False,
        "manifest_checks": manifest_checks,
        "policy_validation": {
            "formal_state": policy_report.get("formal_state"),
            "checks_failed": policy_report.get("checks_failed"),
        },
        "project_status_checks": status_checks,
        "evidence_freshness": {
            "review_due_at": freshness.get("review_due_at"),
            "stale": evidence_stale,
            "stale_behavior": freshness.get("stale_behavior"),
        },
        "alerts": alerts,
        "blocking_failures": blocking_failures,
        "all_contract_checks_passed": formal_state == HEALTHY,
        "quality": {
            "network_calls_made": False,
            "external_artifacts_downloaded": False,
            "new_bundle_execution_performed": False,
            "raw_eoin_rows_read": False,
            "raw_rows_emitted": 0,
            "raw_files_emitted": False,
            "derived_tables_emitted": False,
            "data_or_model_mutation_performed": False,
            "formal_stake": 0,
        },
        "permissions": {
            "alert_metadata_only": True,
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
    manifest: dict[str, Any],
    policy: dict[str, Any],
    cross_report: dict[str, Any],
    role_policy: dict[str, Any],
    evaluation_manifest: dict[str, Any],
    registry: dict[str, Any],
    project_status: str,
) -> None:
    baseline_date = date(2026, 7, 21)
    report = monitor(
        manifest,
        policy,
        cross_report,
        role_policy,
        evaluation_manifest,
        registry,
        project_status,
        baseline_date,
    )
    assert report["formal_state"] == HEALTHY, report

    report = monitor(
        manifest,
        policy,
        cross_report,
        role_policy,
        evaluation_manifest,
        registry,
        project_status,
        date(2027, 7, 22),
    )
    assert report["formal_state"] == ALERT_DISABLED, report
    assert "freshness.evidence_stale" in report["alerts"], report

    mutated_registry = copy.deepcopy(registry)
    source = find_source(mutated_registry, "kaggle_eoinamoore_historical_nba")
    assert source is not None
    source["status"] = "role_limited_secondary_eligible"
    report = monitor(
        manifest,
        policy,
        cross_report,
        role_policy,
        evaluation_manifest,
        mutated_registry,
        project_status,
        baseline_date,
    )
    assert report["formal_state"] == ALERT_DISABLED, report

    mutated_policy = copy.deepcopy(policy)
    mutated_policy["forbidden_promotions"]["model_retraining_allowed"] = True
    report = monitor(
        manifest,
        mutated_policy,
        cross_report,
        role_policy,
        evaluation_manifest,
        registry,
        project_status,
        baseline_date,
    )
    assert report["formal_state"] == BLOCKED, report

    mutated_registry = copy.deepcopy(registry)
    mutated_registry["sources"] = [
        source
        for source in mutated_registry.get("sources") or []
        if source.get("source_id") != "kaggle_eoinamoore_historical_nba"
    ]
    report = monitor(
        manifest,
        policy,
        cross_report,
        role_policy,
        evaluation_manifest,
        mutated_registry,
        project_status,
        baseline_date,
    )
    assert report["formal_state"] == BLOCKED, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("data/eoin-secondary-qa-contract-monitor-v1.json"))
    parser.add_argument("--policy", type=Path, default=Path("data/eoin-secondary-qa-integration-policy-v1.json"))
    parser.add_argument("--cross-report", type=Path, default=Path("data/eoin-cross-source-audit-v1.json"))
    parser.add_argument("--role-policy", type=Path, default=Path("data/eoin-post-execution-role-review-policy-v1.json"))
    parser.add_argument("--evaluation-manifest", type=Path, default=Path("data/eoin-post-execution-role-review-evaluation-v1.json"))
    parser.add_argument("--source-registry", type=Path, default=Path("data/source-registry.json"))
    parser.add_argument("--project-status", type=Path, default=Path("PROJECT_STATUS.md"))
    parser.add_argument("--as-of-date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    manifest = load_json(args.manifest)
    policy = load_json(args.policy)
    cross_report = load_json(args.cross_report)
    role_policy = load_json(args.role_policy)
    evaluation_manifest = load_json(args.evaluation_manifest)
    registry = load_json(args.source_registry)
    project_status = args.project_status.read_text(encoding="utf-8")

    if args.self_test:
        self_test(
            manifest,
            policy,
            cross_report,
            role_policy,
            evaluation_manifest,
            registry,
            project_status,
        )

    report = monitor(
        manifest,
        policy,
        cross_report,
        role_policy,
        evaluation_manifest,
        registry,
        project_status,
        args.as_of_date,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "formal_state": report["formal_state"],
                "alerts": report["alerts"],
                "blocking_failures": report["blocking_failures"],
            },
            indent=2,
        )
    )
    return 0 if report["formal_state"] == HEALTHY else 1


if __name__ == "__main__":
    raise SystemExit(main())
