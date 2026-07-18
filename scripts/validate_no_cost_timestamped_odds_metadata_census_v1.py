#!/usr/bin/env python3
"""Validate the aggregate no-cost timestamped odds metadata census result."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

EXPECTED_IDS = {
    "kaggle_christophertreasure_nba_odds",
    "kaggle_ehallmar_nba_historical_betting",
    "kaggle_erichqiu_nba_odds_scores",
    "kaggle_cviaxmiwnptr_nba_betting_data",
    "sportsbookreviewsonline_nba_archive_legacy",
    "oddsportal_nba_results",
    "public_github_odds_collectors",
    "user_supplied_timestamped_odds",
}


def load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("result root must be an object")
    return data


def validate(data: dict[str, Any]) -> dict[str, Any]:
    checks: list[str] = []
    failures: list[str] = []

    def check(condition: bool, name: str) -> None:
        checks.append(name)
        if not condition:
            failures.append(name)

    check(data.get("schema_version") == "no-cost-timestamped-odds-metadata-census-v1", "schema_version")
    check(data.get("formal_state") == "NO_COST_METADATA_BLOCKED", "formal_state")

    policy = data.get("policy_source", {})
    check(policy.get("pr") == 66, "policy_pr_66")
    check(policy.get("merge_sha") == "4006ffdd01e57b6bf8bdd2e14e11bb1e2672c6e3", "policy_merge_sha")

    summary = data.get("summary", {})
    expected_summary = {
        "candidate_count": 8,
        "metadata_gate_pass_count": 0,
        "qualified_for_frozen_pilot_count": 0,
        "quote_downloads": 0,
        "paid_calls": 0,
        "accounts_created": 0,
        "api_keys_read": 0,
        "market_metrics_calculated": False,
        "formal_stake": 0,
    }
    check(all(summary.get(key) == value for key, value in expected_summary.items()), "summary_boundary")

    candidates = data.get("candidates", [])
    ids = [item.get("source_id") for item in candidates if isinstance(item, dict)]
    check(len(ids) == 8, "candidate_count")
    check(len(ids) == len(set(ids)), "candidate_ids_unique")
    check(set(ids) == EXPECTED_IDS, "candidate_roster_unchanged")
    check(all(str(item.get("decision", "")).startswith("BLOCKED_") for item in candidates), "all_candidates_blocked")
    check(all(item.get("allowed_use") not in (None, "") for item in candidates), "allowed_use_recorded")

    gate_failures = data.get("gate_failures", {})
    check("timestamp_semantics_explicit" in gate_failures, "timestamp_gate_recorded")
    check("bookmaker_definition_explicit" in gate_failures, "bookmaker_gate_recorded")
    check("license_or_permission_explicit" in gate_failures, "license_gate_recorded")

    activation = data.get("activation_boundary", {})
    for key in (
        "ready_for_frozen_source_health_pilot",
        "ready_for_production_backfill",
        "ready_for_point_in_time_odds_join",
        "ready_for_market_backtest",
        "ready_for_clv_ev_roi_drawdown",
        "ready_for_betting_edge_claim",
    ):
        check(activation.get(key) is False, f"{key}_false")
    check(activation.get("formal_stake") == 0, "activation_stake_zero")

    return {
        "census_state": "CENSUS_VALID" if not failures else "CENSUS_INVALID",
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failures),
        "failures": failures,
        "candidate_count": len(ids),
        "qualified_candidate_count": summary.get("qualified_for_frozen_pilot_count"),
        "quote_downloads": summary.get("quote_downloads"),
        "paid_calls": summary.get("paid_calls"),
        "api_keys_read": summary.get("api_keys_read"),
        "market_metrics_calculated": summary.get("market_metrics_calculated"),
        "formal_stake": summary.get("formal_stake"),
    }


def self_test() -> None:
    fixture = {
        "schema_version": "no-cost-timestamped-odds-metadata-census-v1",
        "formal_state": "NO_COST_METADATA_BLOCKED",
        "policy_source": {"pr": 66, "merge_sha": "4006ffdd01e57b6bf8bdd2e14e11bb1e2672c6e3"},
        "summary": {
            "candidate_count": 8,
            "metadata_gate_pass_count": 0,
            "qualified_for_frozen_pilot_count": 0,
            "quote_downloads": 0,
            "paid_calls": 0,
            "accounts_created": 0,
            "api_keys_read": 0,
            "market_metrics_calculated": False,
            "formal_stake": 0,
        },
        "candidates": [
            {"source_id": source_id, "decision": "BLOCKED_TEST", "allowed_use": "none"}
            for source_id in sorted(EXPECTED_IDS)
        ],
        "gate_failures": {
            "timestamp_semantics_explicit": [],
            "bookmaker_definition_explicit": [],
            "license_or_permission_explicit": [],
        },
        "activation_boundary": {
            "ready_for_frozen_source_health_pilot": False,
            "ready_for_production_backfill": False,
            "ready_for_point_in_time_odds_join": False,
            "ready_for_market_backtest": False,
            "ready_for_clv_ev_roi_drawdown": False,
            "ready_for_betting_edge_claim": False,
            "formal_stake": 0,
        },
    }
    assert validate(fixture)["census_state"] == "CENSUS_VALID"
    fixture["summary"]["quote_downloads"] = 1
    assert validate(fixture)["census_state"] == "CENSUS_INVALID"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        print(json.dumps({"self_test": "PASS"}, indent=2))
        return 0
    if not args.input or not args.output:
        parser.error("--input and --output are required unless --self-test is used")

    report = validate(load(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["census_state"] == "CENSUS_VALID" else 1


if __name__ == "__main__":
    raise SystemExit(main())
