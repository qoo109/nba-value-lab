#!/usr/bin/env python3
"""Validate Eoin post-execution role review policy v1 without data execution."""
from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "eoin-post-execution-role-review-policy-validation-v1"
POLICY_SCHEMA = "eoin-post-execution-role-review-policy-v1"
READY_STATE = "EOIN_POST_EXECUTION_ROLE_REVIEW_POLICY_READY"
BLOCKED_STATE = "EOIN_POST_EXECUTION_ROLE_REVIEW_POLICY_BLOCKED"
CURRENT_ROLE = "ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE"
MAXIMUM_ROLE = "ROLE_LIMITED_SECONDARY_QA_SOURCE_VALIDATED"
EXPECTED_OUTCOMES = {
    "ROLE_LIMITED_SECONDARY_QA_SOURCE_VALIDATED",
    "RETAIN_ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE",
    "POST_EXECUTION_ROLE_REVIEW_BLOCKED",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def validate(policy: dict[str, Any]) -> dict[str, Any]:
    checks: dict[str, bool] = {}

    def check(name: str, condition: bool) -> None:
        checks[name] = bool(condition)

    check("schema_version", policy.get("schema_version") == POLICY_SCHEMA)
    check("source_id", policy.get("source_id") == "kaggle_eoinamoore_historical_nba")
    check("current_role", policy.get("current_formal_role") == CURRENT_ROLE)
    check("policy_state", policy.get("policy_state") == "POST_EXECUTION_ROLE_REVIEW_POLICY_PREDECLARED")

    evidence = policy.get("evidence_anchors") or {}
    cross = evidence.get("cross_source_audit") or {}
    execution = evidence.get("one_time_full_adapter_execution") or {}

    check(
        "cross_source_identity",
        cross.get("formal_state") == CURRENT_ROLE
        and cross.get("workflow_run_id") == 29672984966
        and cross.get("artifact_id") == 8437932113
        and cross.get("artifact_digest")
        == "sha256:96a87c6b52614ea6f7478e1bdbcc729c7c8eb2347490ca236475444ca5fcc63a",
    )
    check(
        "execution_identity",
        execution.get("formal_state") == "ONE_TIME_FULL_ADAPTER_AGGREGATE_VALIDATION_PASS"
        and execution.get("workflow_run_id") == 29680729672
        and execution.get("artifact_id") == 8440485189
        and execution.get("artifact_digest")
        == "sha256:e068940df05bfc51d8757aef500e9c6f812687bfa171b5fff8680ee3b59bb56c",
    )
    check(
        "consumed_once",
        execution.get("request_id") == "EOIN-FULL-ADAPTER-2026-07-19-001"
        and execution.get("request_consumed") is True
        and execution.get("execution_count") == 1,
    )

    scope = policy.get("review_scope") or {}
    check("no_network", scope.get("network_calls_allowed") is False)
    check("no_new_execution", scope.get("new_bundle_execution_allowed") is False)
    check("no_raw_read", scope.get("raw_source_rows_read_allowed") is False)
    check(
        "no_raw_output",
        scope.get("raw_rows_emitted") == 0 and scope.get("raw_files_emitted") is False,
    )
    check(
        "player_coverage_only",
        scope.get("player_statistics_role") == "coverage_only_not_stat_parity",
    )

    gates = policy.get("frozen_review_gates") or {}
    check(
        "frozen_gate_values",
        gates.get("minimum_cross_source_matched_games") == 1000
        and gates.get("minimum_game_identity_match_rate") == 0.98
        and gates.get("minimum_final_score_match_rate") == 0.98
        and gates.get("minimum_team_boxscore_coverage_rate") == 0.98
        and gates.get("minimum_team_boxscore_score_match_rate") == 0.98
        and gates.get("minimum_player_boxscore_candidate_coverage_rate") == 0.95
        and gates.get("minimum_pbp_game_coverage_rate") == 0.95
        and gates.get("minimum_full_bundle_games") == 1000
        and gates.get("maximum_duplicate_game_id_groups") == 0
        and gates.get("request_must_be_consumed") is True
        and gates.get("maximum_execution_count") == 1
        and gates.get("maximum_raw_rows_emitted") == 0
        and gates.get("raw_files_emitted_allowed") is False,
    )

    check(
        "cross_source_evidence_meets_frozen_gates",
        cross.get("matched_games", 0) >= gates.get("minimum_cross_source_matched_games", 10**9)
        and cross.get("game_identity_match_rate", 0) >= gates.get("minimum_game_identity_match_rate", 1.1)
        and cross.get("final_score_match_rate", 0) >= gates.get("minimum_final_score_match_rate", 1.1)
        and cross.get("team_boxscore_coverage_rate", 0) >= gates.get("minimum_team_boxscore_coverage_rate", 1.1)
        and cross.get("team_boxscore_score_match_rate", 0) >= gates.get("minimum_team_boxscore_score_match_rate", 1.1)
        and cross.get("player_boxscore_candidate_coverage_rate", 0)
        >= gates.get("minimum_player_boxscore_candidate_coverage_rate", 1.1)
        and cross.get("pbp_game_coverage_rate", 0) >= gates.get("minimum_pbp_game_coverage_rate", 1.1),
    )
    check(
        "execution_evidence_meets_frozen_gates",
        execution.get("games", 0) >= gates.get("minimum_full_bundle_games", 10**9)
        and execution.get("team_boxscore_coverage_rate", 0)
        >= gates.get("minimum_team_boxscore_coverage_rate", 1.1)
        and execution.get("team_boxscore_score_match_rate", 0)
        >= gates.get("minimum_team_boxscore_score_match_rate", 1.1)
        and execution.get("player_boxscore_candidate_coverage_rate", 0)
        >= gates.get("minimum_player_boxscore_candidate_coverage_rate", 1.1)
        and execution.get("pbp_game_coverage_rate", 0)
        >= gates.get("minimum_pbp_game_coverage_rate", 1.1)
        and execution.get("duplicate_game_id_groups", 10**9)
        <= gates.get("maximum_duplicate_game_id_groups", -1)
        and execution.get("raw_rows_emitted", 10**9)
        <= gates.get("maximum_raw_rows_emitted", -1)
        and execution.get("raw_files_emitted") is False,
    )

    check("candidate_outcomes", set(policy.get("candidate_review_outcomes") or []) == EXPECTED_OUTCOMES)
    check("maximum_role", policy.get("maximum_possible_role_if_later_evaluation_passes") == MAXIMUM_ROLE)

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

    next_state = policy.get("next_state_if_policy_validation_passes") or {}
    check("next_formal_state", next_state.get("formal_state") == READY_STATE)
    check("evaluation_ready", next_state.get("ready_for_evaluation_implementation") is True)
    check(
        "no_premature_promotion",
        next_state.get("role_promotion_completed") is False
        and next_state.get("current_role_unchanged") is True,
    )
    locked_false_keys = (
        "ready_for_primary_source_use",
        "ready_for_silver_replacement",
        "ready_for_gold_replacement",
        "ready_for_player_stat_parity",
        "ready_for_model_retraining",
        "ready_for_market_backtest",
        "ready_for_betting_edge_claim",
    )
    check("downstream_locked", all(next_state.get(key) is False for key in locked_false_keys))
    check("next_stake", next_state.get("formal_stake") == 0)

    failures = sorted(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": SCHEMA_VERSION,
        "validated_at": utc_now(),
        "formal_state": READY_STATE if not failures else BLOCKED_STATE,
        "current_formal_role": policy.get("current_formal_role"),
        "maximum_possible_role": policy.get("maximum_possible_role_if_later_evaluation_passes"),
        "checks": checks,
        "passed_checks": sum(checks.values()),
        "total_checks": len(checks),
        "checks_failed": len(failures),
        "failed_checks": failures,
        "quality": {
            "network_calls_made": False,
            "new_bundle_execution_performed": False,
            "raw_eoin_rows_read": False,
            "raw_rows_emitted": 0,
            "raw_files_emitted": False,
            "role_promotion_completed": False,
            "formal_stake": 0,
        },
        "decision": {
            "ready_for_evaluation_implementation": not failures,
            "current_role_unchanged": True,
            "ready_for_primary_source_use": False,
            "ready_for_silver_replacement": False,
            "ready_for_gold_replacement": False,
            "ready_for_player_stat_parity": False,
            "ready_for_model_retraining": False,
            "ready_for_market_backtest": False,
            "ready_for_betting_edge_claim": False,
            "formal_stake": 0,
        },
    }


def self_test(policy: dict[str, Any]) -> None:
    report = validate(policy)
    assert report["formal_state"] == READY_STATE, report
    assert report["checks_failed"] == 0, report

    mutated = copy.deepcopy(policy)
    mutated["forbidden_promotions"]["historical_gold_replacement_allowed"] = True
    assert validate(mutated)["formal_state"] == BLOCKED_STATE

    mutated = copy.deepcopy(policy)
    mutated["evidence_anchors"]["one_time_full_adapter_execution"]["execution_count"] = 2
    assert validate(mutated)["formal_state"] == BLOCKED_STATE

    mutated = copy.deepcopy(policy)
    mutated["review_scope"]["player_statistics_role"] = "stat_parity"
    assert validate(mutated)["formal_state"] == BLOCKED_STATE


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--policy",
        type=Path,
        default=Path("data/eoin-post-execution-role-review-policy-v1.json"),
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    policy = load_json(args.policy)
    if args.self_test:
        self_test(policy)

    report = validate(policy)
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
