#!/usr/bin/env python3
"""Validate the design-only source-gap exception integration policy."""
from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VALID_STATE = "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_POLICY_VALIDATED"
NEXT_STEP = "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_IMPLEMENTATION_READY_FOR_DESIGN"


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain an object")
    return data


def validate(policy: dict[str, Any], manifest: dict[str, Any], status: dict[str, Any]) -> dict[str, Any]:
    p = policy
    m = manifest
    s = status
    checks = {
        "policy_schema": p.get("schema_version") == "historical-silver-2023-24-source-gap-exception-integration-policy-v1",
        "policy_state": p.get("formal_state") == "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_POLICY_DESIGN_READY",
        "policy_role": p.get("policy_role") == "QA_AND_COVERAGE_REPORTING_ONLY",
        "contract": p.get("frozen_exception_contract") == {
            "exception_code": "SOURCE_ARCHIVE_PBPSTATS_GAME_ABSENT",
            "source_id": "shufinskiy_nba_data",
            "exception_count": 2,
            "unclassified_count": 0,
            "missing_reason": "nbastats_game_present_pbpstats_game_absent",
            "source_archive_gap_stable": True,
            "silver_builder_repair_required": False,
            "handling_mode": "DOCUMENTED_AGGREGATE_ONLY_NO_ROW_PATCH"
        },
        "gate_fail_closed": p.get("recognition_gate", {}).get("on_any_mismatch") == "FAIL_CLOSED_UNEXPLAINED_COVERAGE_GAP",
        "gate_all_required": p.get("recognition_gate", {}).get("all_conditions_required") is True,
        "gate_no_partial": p.get("recognition_gate", {}).get("partial_recognition_allowed") is False,
        "gate_no_adjustment": p.get("recognition_gate", {}).get("automatic_count_adjustment_allowed") is False,
        "raw_counts_preserved": all((
            p.get("reporting_contract", {}).get("raw_silver_game_count") == 5826,
            p.get("reporting_contract", {}).get("raw_gold_matchup_count") == 5824,
            p.get("reporting_contract", {}).get("raw_missing_gold_for_silver") == 2,
            p.get("reporting_contract", {}).get("gold_matchup_count_after_documentation") == 5824,
            p.get("reporting_contract", {}).get("gold_coverage_rewritten_as_complete") is False
        )),
        "documented_counts": all((
            p.get("reporting_contract", {}).get("documented_source_gap_exception_count") == 2,
            p.get("reporting_contract", {}).get("unexplained_missing_count_after_documentation") == 0,
            p.get("reporting_contract", {}).get("covered_or_documented_count") == 5826
        )),
        "privacy_fields_prohibited": {"game_id", "game_date", "home_team_abbr", "away_team_abbr", "team_code", "source_file_path", "source_file_hash", "row_level_record", "row_key_hash"}.issubset(set(p.get("reporting_contract", {}).get("prohibited_fields", []))),
        "raw_outcome_unchanged": p.get("decision_semantics", {}).get("raw_outcome_unchanged") == "HISTORICAL_GOLD_SILVER_COVERAGE_RECONCILIATION_SOURCE_DATA_GAP_CONFIRMED",
        "documented_state": p.get("decision_semantics", {}).get("documented_exception_state") == "HISTORICAL_GOLD_SILVER_COVERAGE_DOCUMENTED_SOURCE_EXCEPTION_RECOGNIZED",
        "gold_not_complete": p.get("decision_semantics", {}).get("gold_dataset_complete") is False,
        "no_activation": all(p.get("decision_semantics", {}).get(key) is False for key in (
            "silver_dataset_modified", "gold_dataset_modified", "builder_repair_required",
            "manual_repair_required", "cross_source_audit_rerun_ready", "market_backtest_ready",
            "model_retraining_ready", "betting_edge_claim_ready"
        )),
        "design_only": p.get("implementation_boundary", {}).get("design_only") is True,
        "no_execution": all(p.get("implementation_boundary", {}).get(key) is False for key in (
            "current_analyzer_changed", "current_builder_changed", "database_read_or_write",
            "network_calls_made", "source_archives_read", "silver_exception_patch",
            "historical_silver_replacement", "historical_gold_replacement",
            "cross_source_audit_rerun", "market_backtest", "model_training_or_retraining"
        )),
        "manifest_count": m.get("aggregate_scope", {}).get("source_gap_exception_games") == 2,
        "manifest_code": m.get("exception_class", {}).get("exception_code") == "SOURCE_ARCHIVE_PBPSTATS_GAME_ABSENT",
        "manifest_no_patch": m.get("exception_handling_policy", {}).get("mode") == "DOCUMENTED_AGGREGATE_ONLY_NO_ROW_PATCH",
        "status_state": s.get("formal_state") == VALID_STATE,
        "status_counts": all((s.get("exception_count") == 2, s.get("unexplained_missing_count_after_documentation") == 0, s.get("raw_silver_game_count") == 5826, s.get("raw_gold_matchup_count") == 5824)),
        "status_no_activation": all(s.get(key) is False for key in (
            "ready_for_real_data_execution", "ready_for_silver_builder_change", "ready_for_gold_rebuild",
            "ready_for_cross_source_audit_rerun", "ready_for_market_backtest",
            "ready_for_model_retraining", "ready_for_betting_edge_claim"
        )),
        "next_step": s.get("next_research_step") == NEXT_STEP and p.get("next_state_if_valid", {}).get("next_research_step") == NEXT_STEP,
        "stake_zero": p.get("decision_semantics", {}).get("formal_stake") == 0 and s.get("formal_stake") == 0
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": "historical-silver-2023-24-source-gap-exception-integration-policy-validation-report-v1",
        "validated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "formal_state": VALID_STATE if not failed else "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_POLICY_INVALID",
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "checks_failed": len(failed),
        "failed_checks": failed,
        "checks": checks,
        "ready_for_implementation_design": not failed,
        "ready_for_real_data_execution": False,
        "ready_for_cross_source_audit_rerun": False,
        "ready_for_market_backtest": False,
        "next_research_step": NEXT_STEP,
        "formal_stake": 0
    }


def self_test(policy: dict[str, Any], manifest: dict[str, Any], status: dict[str, Any]) -> dict[str, bool]:
    assert validate(policy, manifest, status)["checks_failed"] == 0
    tests = {"baseline_passes": True}
    for name, target, path, value in (
        ("count_mismatch_blocks", "policy", ("reporting_contract", "documented_source_gap_exception_count"), 3),
        ("raw_rewrite_blocks", "policy", ("reporting_contract", "gold_coverage_rewritten_as_complete"), True),
        ("market_activation_blocks", "status", ("ready_for_market_backtest",), True),
        ("nonzero_stake_blocks", "status", ("formal_stake",), 1)
    ):
        test_policy = copy.deepcopy(policy)
        test_status = copy.deepcopy(status)
        obj = test_policy if target == "policy" else test_status
        cursor = obj
        for key in path[:-1]:
            cursor = cursor[key]
        cursor[path[-1]] = value
        assert validate(test_policy, manifest, test_status)["checks_failed"] > 0
        tests[name] = True
    return tests


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--status", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    policy, manifest, status = load(args.policy), load(args.manifest), load(args.status)
    report = validate(policy, manifest, status)
    if args.self_test:
        report["self_test"] = self_test(policy, manifest, status)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["checks_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
