#!/usr/bin/env python3
"""Validate the frozen no-cost timestamped odds source qualification policy."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

EXPECTED_SNAPSHOTS = ["T-6h", "T-3h", "T-1h", "T-30m", "T-5m", "Closing"]
EXPECTED_DECISIONS = [
    "NO_COST_METADATA_BLOCKED",
    "NO_COST_SCHEMA_REVIEW_REQUIRED",
    "NO_COST_SOURCE_STRUCTURAL_BLOCKED",
    "NO_COST_SOURCE_QUALIFIED_FOR_FROZEN_PILOT",
]
EXPECTED_CANDIDATES = {
    "kaggle_christophertreasure_nba_odds",
    "kaggle_ehallmar_nba_historical_betting",
    "kaggle_erichqiu_nba_odds_scores",
    "kaggle_cviaxmiwnptr_nba_betting_data",
    "sportsbookreviewsonline_nba_archive_legacy",
    "oddsportal_nba_results",
    "public_github_odds_collectors",
    "user_supplied_timestamped_odds",
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("policy root must be an object")
    return data


def check(condition: bool, name: str, failures: list[str], checks: list[str]) -> None:
    checks.append(name)
    if not condition:
        failures.append(name)


def validate(policy: dict[str, Any]) -> dict[str, Any]:
    checks: list[str] = []
    failures: list[str] = []

    check(policy.get("schema_version") == "no-cost-timestamped-odds-source-qualification-v1", "schema_version", failures, checks)

    upstream = policy.get("upstream_decision", {})
    check(upstream.get("source_pr") == 65, "upstream_pr_65", failures, checks)
    check(upstream.get("formal_state") == "PAID_PILOT_NOT_APPROVED", "paid_pilot_not_approved", failures, checks)
    check(upstream.get("paid_access_authorized") is False, "paid_access_false", failures, checks)
    check(upstream.get("subscription_authorized") is False, "subscription_false", failures, checks)
    check(upstream.get("paid_endpoint_execution_authorized") is False, "paid_execution_false", failures, checks)
    check(upstream.get("formal_stake") == 0, "stake_zero", failures, checks)

    access = policy.get("access_boundary", {})
    for key in (
        "account_creation_allowed",
        "paid_plan_allowed",
        "api_key_or_secret_allowed",
        "login_or_consent_bypass_allowed",
        "robots_or_terms_bypass_allowed",
        "restricted_scraping_allowed",
        "public_raw_quote_redistribution_allowed",
    ):
        check(access.get(key) is False, f"access_{key}_false", failures, checks)

    reuse = policy.get("must_reuse", {})
    check(reuse.get("new_odds_schema_allowed") is False, "no_new_odds_schema", failures, checks)
    check(reuse.get("new_bookmaker_schema_allowed") is False, "no_new_bookmaker_schema", failures, checks)
    check(reuse.get("new_no_vig_method_allowed") is False, "no_new_no_vig_method", failures, checks)

    scope = policy.get("frozen_market_scope", {})
    check(scope.get("market") == "h2h_moneyline", "h2h_only", failures, checks)
    check(scope.get("snapshot_labels") == EXPECTED_SNAPSHOTS, "six_frozen_snapshots", failures, checks)
    check(scope.get("opening_required") is False, "opening_not_required", failures, checks)
    check(scope.get("opening_may_be_inferred") is False, "opening_not_inferred", failures, checks)
    check(scope.get("closing_only_source_may_unlock_market_backtest") is False, "closing_only_not_executable", failures, checks)

    sample = policy.get("frozen_sample", {})
    check(sample.get("games") == 30, "sample_30_games", failures, checks)
    check(sample.get("games_per_season") == 10, "sample_10_per_season", failures, checks)
    check(sample.get("seasons") == ["2021-22", "2022-23", "2023-24"], "sample_three_seasons", failures, checks)
    check(sample.get("requested_snapshot_slots") == 180, "sample_180_slots", failures, checks)
    check(sample.get("candidate_specific_game_replacement_allowed") is False, "no_candidate_replacement", failures, checks)

    candidates = policy.get("candidate_sources", [])
    candidate_ids = [item.get("source_id") for item in candidates if isinstance(item, dict)]
    check(len(candidate_ids) == len(set(candidate_ids)), "candidate_ids_unique", failures, checks)
    check(set(candidate_ids) == EXPECTED_CANDIDATES, "candidate_roster_frozen", failures, checks)

    metadata = policy.get("metadata_gates", {})
    check(all(value is True for value in metadata.values()), "metadata_gates_all_required", failures, checks)

    schema = policy.get("schema_gates", {})
    required_true = [
        "same_bookmaker_two_sided_prices",
        "bookmaker_key_present",
        "provider_snapshot_at_or_observed_at_present",
        "scheduled_tipoff_utc_present",
        "home_and_away_identity_present",
        "source_event_id_or_stable_source_key_present",
        "retrieval_or_file_version_provenance_present",
    ]
    check(all(schema.get(key) is True for key in required_true), "schema_required_fields", failures, checks)
    check(schema.get("fuzzy_matching_allowed") is False, "fuzzy_false", failures, checks)
    check(schema.get("future_snapshot_allowed") is False, "future_snapshot_false", failures, checks)

    gates = policy.get("frozen_source_health_gates", {})
    expected_gates = {
        "minimum_target_game_mapping_rate": 0.9,
        "minimum_mapped_games_each_season": 8,
        "minimum_primary_bookmaker_complete_t60_closing_games": 24,
        "minimum_primary_bookmaker_complete_t60_closing_games_each_season": 7,
        "minimum_primary_bookmaker_all_target_snapshot_coverage": 0.7,
        "maximum_point_in_time_violations": 0,
        "maximum_future_snapshot_rows": 0,
        "maximum_team_mismatches": 0,
        "maximum_fuzzy_matches": 0,
        "maximum_duplicate_quote_keys": 0,
        "maximum_opening_labels_inferred": 0,
    }
    check(all(gates.get(key) == value for key, value in expected_gates.items()), "original_source_health_gates_retained", failures, checks)

    check(policy.get("decision_states") == EXPECTED_DECISIONS, "decision_states_frozen", failures, checks)

    activation = policy.get("activation_boundary", {})
    for key in (
        "this_policy_downloads_quotes",
        "this_policy_runs_source_health_pilot",
        "this_policy_unlocks_market_backtest",
        "this_policy_unlocks_betting_claims",
    ):
        check(activation.get(key) is False, f"activation_{key}_false", failures, checks)
    check(activation.get("separate_execution_pr_required") is True, "separate_execution_pr", failures, checks)
    check(activation.get("formal_stake") == 0, "activation_stake_zero", failures, checks)

    forbidden = set(policy.get("forbidden_outputs", []))
    check({"model_edge", "EV", "ROI", "CLV", "drawdown", "bet_count", "profit_ranking", "stake_recommendation"}.issubset(forbidden), "market_outputs_forbidden", failures, checks)

    return {
        "policy_state": "POLICY_VALID" if not failures else "POLICY_INVALID",
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failures),
        "failures": failures,
        "candidate_count": len(candidate_ids),
        "quote_downloads": 0,
        "paid_calls": 0,
        "api_keys_read": 0,
        "market_metrics_calculated": False,
        "formal_stake": 0,
    }


def self_test() -> None:
    fixture = {
        "schema_version": "no-cost-timestamped-odds-source-qualification-v1",
        "upstream_decision": {
            "source_pr": 65,
            "formal_state": "PAID_PILOT_NOT_APPROVED",
            "paid_access_authorized": False,
            "subscription_authorized": False,
            "paid_endpoint_execution_authorized": False,
            "formal_stake": 0,
        },
        "access_boundary": {
            "account_creation_allowed": False,
            "paid_plan_allowed": False,
            "api_key_or_secret_allowed": False,
            "login_or_consent_bypass_allowed": False,
            "robots_or_terms_bypass_allowed": False,
            "restricted_scraping_allowed": False,
            "public_raw_quote_redistribution_allowed": False,
        },
        "must_reuse": {
            "new_odds_schema_allowed": False,
            "new_bookmaker_schema_allowed": False,
            "new_no_vig_method_allowed": False,
        },
        "frozen_market_scope": {
            "market": "h2h_moneyline",
            "snapshot_labels": EXPECTED_SNAPSHOTS,
            "opening_required": False,
            "opening_may_be_inferred": False,
            "closing_only_source_may_unlock_market_backtest": False,
        },
        "frozen_sample": {
            "games": 30,
            "games_per_season": 10,
            "seasons": ["2021-22", "2022-23", "2023-24"],
            "requested_snapshot_slots": 180,
            "candidate_specific_game_replacement_allowed": False,
        },
        "candidate_sources": [{"source_id": source_id} for source_id in sorted(EXPECTED_CANDIDATES)],
        "metadata_gates": {"license": True},
        "schema_gates": {
            "same_bookmaker_two_sided_prices": True,
            "bookmaker_key_present": True,
            "provider_snapshot_at_or_observed_at_present": True,
            "scheduled_tipoff_utc_present": True,
            "home_and_away_identity_present": True,
            "source_event_id_or_stable_source_key_present": True,
            "retrieval_or_file_version_provenance_present": True,
            "fuzzy_matching_allowed": False,
            "future_snapshot_allowed": False,
        },
        "frozen_source_health_gates": {
            "minimum_target_game_mapping_rate": 0.9,
            "minimum_mapped_games_each_season": 8,
            "minimum_primary_bookmaker_complete_t60_closing_games": 24,
            "minimum_primary_bookmaker_complete_t60_closing_games_each_season": 7,
            "minimum_primary_bookmaker_all_target_snapshot_coverage": 0.7,
            "maximum_point_in_time_violations": 0,
            "maximum_future_snapshot_rows": 0,
            "maximum_team_mismatches": 0,
            "maximum_fuzzy_matches": 0,
            "maximum_duplicate_quote_keys": 0,
            "maximum_opening_labels_inferred": 0,
        },
        "decision_states": EXPECTED_DECISIONS,
        "activation_boundary": {
            "this_policy_downloads_quotes": False,
            "this_policy_runs_source_health_pilot": False,
            "this_policy_unlocks_market_backtest": False,
            "this_policy_unlocks_betting_claims": False,
            "separate_execution_pr_required": True,
            "formal_stake": 0,
        },
        "forbidden_outputs": ["model_edge", "EV", "ROI", "CLV", "drawdown", "bet_count", "profit_ranking", "stake_recommendation"],
    }
    result = validate(fixture)
    if result["policy_state"] != "POLICY_VALID":
        raise AssertionError(result)
    fixture["access_boundary"]["paid_plan_allowed"] = True
    if validate(fixture)["policy_state"] != "POLICY_INVALID":
        raise AssertionError("paid-plan mutation must fail")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        print(json.dumps({"self_test": "PASS"}, indent=2))
        return 0
    if not args.policy or not args.output:
        parser.error("--policy and --output are required unless --self-test is used")

    result = validate(load_json(args.policy))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["policy_state"] == "POLICY_VALID" else 1


if __name__ == "__main__":
    raise SystemExit(main())
