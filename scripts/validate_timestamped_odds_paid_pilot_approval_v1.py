#!/usr/bin/env python3
"""Validate the no-spend approval packet for Timestamped Odds paid pilot v1."""
from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "timestamped-odds-paid-pilot-approval-validator-v1"
READY_STATE = "APPROVAL_PACKET_VALID_AWAITING_USER_APPROVAL"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("approval packet root must be an object")
    return value


def validate(packet: dict[str, Any]) -> dict[str, Any]:
    checks: dict[str, bool] = {}

    checks["schema_version"] = (
        packet.get("schema_version") == "timestamped-odds-paid-pilot-approval-v1"
    )
    checks["approval_state"] = packet.get("approval_state") == "AWAITING_EXPLICIT_USER_APPROVAL"

    upstream = packet.get("upstream") or {}
    checks["manifest_pr"] = upstream.get("manifest_pr") == 60
    checks["manifest_merge_commit"] = upstream.get("manifest_merge_commit") == (
        "332d199122ad61815503d1165c81a696c28dbfee"
    )
    checks["manifest_state"] = (
        upstream.get("formal_manifest_state") == "PILOT_MANIFEST_READY_ACCESS_NOT_PROVIDED"
    )

    facts = packet.get("revalidated_official_facts") or {}
    plan = facts.get("lowest_listed_historical_enabled_plan") or {}
    checks["paid_historical_required"] = facts.get("historical_access_requires_paid_plan") is True
    checks["historical_start"] = facts.get("historical_featured_markets_available_from") == "2020-06-06"
    checks["historical_intervals"] = (
        facts.get("snapshot_interval_before_2022_09_minutes") == 10
        and facts.get("snapshot_interval_from_2022_09_minutes") == 5
    )
    checks["historical_direction"] = (
        facts.get("historical_snapshot_rule")
        == "closest available snapshot equal to or earlier than requested date"
    )
    checks["quota_formula"] = facts.get("historical_quota_formula") == "10 x regions x markets"
    checks["quota_headers"] = set(facts.get("response_headers_required") or []) == {
        "x-requests-last",
        "x-requests-used",
        "x-requests-remaining",
    }
    checks["empty_response_boundary"] = facts.get("empty_historical_response_charged") is False
    checks["lowest_plan"] = (
        plan.get("plan_name") == "START 20K"
        and plan.get("listed_price_usd_per_month") == 30
        and plan.get("monthly_credits") == 20000
        and plan.get("historical_odds_included") is True
        and plan.get("billing_starts_immediately") is True
        and plan.get("recurs_monthly_until_cancelled") is True
        and plan.get("taxes_fx_and_card_fees_verified") is False
    )

    pilot = packet.get("frozen_pilot") or {}
    requests = pilot.get("unique_historical_requests")
    credits_each = pilot.get("credits_per_request")
    maximum_credits = pilot.get("maximum_pilot_credits")
    checks["frozen_scope"] = (
        pilot.get("sport_key") == "basketball_nba"
        and pilot.get("region") == "us"
        and pilot.get("market") == "h2h"
        and pilot.get("odds_format") == "decimal"
        and pilot.get("independent_games") == 30
        and pilot.get("snapshot_labels")
        == ["T-6h", "T-3h", "T-1h", "T-30m", "T-5m", "Closing"]
    )
    checks["exact_credit_math"] = (
        requests == 180
        and credits_each == 10
        and maximum_credits == requests * credits_each == 1800
    )
    checks["quota_share"] = pilot.get("share_of_start_20k_quota_percent") == 9.0
    checks["non_activation_scope"] = (
        pilot.get("opening_requested") is False
        and pilot.get("production_backfill_authorized") is False
        and pilot.get("market_metrics_authorized") is False
    )

    exposure = packet.get("maximum_exposure") or {}
    checks["maximum_exposure"] = (
        exposure.get("base_subscription_price_usd") == 30
        and exposure.get("billing_unit") == "month"
        and exposure.get("recurring_subscription") is True
        and exposure.get("maximum_api_credits_for_this_pilot") == 1800
        and exposure.get("tax_fx_card_fee_amount") is None
        and exposure.get("automatic_purchase_or_subscription_allowed") is False
        and exposure.get("automatic_renewal_management_allowed") is False
        and exposure.get("explicit_user_approval_required") is True
    )

    terms = packet.get("terms_and_storage_boundary") or {}
    checks["terms_boundary"] = (
        terms.get("standalone_raw_data_resale_allowed") is False
        and terms.get("standalone_raw_data_redistribution_allowed") is False
        and terms.get("analytics_and_user_facing_tools_allowed_subject_to_terms") is True
        and terms.get("api_key_must_remain_private") is True
        and terms.get("public_raw_response_files_allowed") is False
        and terms.get("public_quote_level_files_allowed") is False
        and terms.get("public_price_rows_allowed") is False
        and terms.get(
            "public_outputs_limited_to_aggregate_qa_and_non_reconstructable_research_summaries"
        )
        is True
        and terms.get("formal_rights_review_required_before_production_backfill") is True
    )

    boundary = packet.get("execution_boundary") or {}
    checks["no_spend_boundary"] = (
        boundary.get("account_created_by_automation") is False
        and boundary.get("subscription_created_by_automation") is False
        and boundary.get("payment_created_by_automation") is False
        and boundary.get("api_key_read") is False
        and boundary.get("paid_endpoint_calls") == 0
        and boundary.get("real_quotes_downloaded") == 0
    )
    checks["permanent_non_activation"] = (
        boundary.get("ready_for_paid_qualification_execution") is False
        and boundary.get("ready_for_production_backfill") is False
        and boundary.get("ready_for_market_backtest") is False
        and boundary.get("ready_for_clv_ev_roi") is False
        and boundary.get("ready_for_betting_edge_claim") is False
        and boundary.get("formal_stake") == 0
    )

    acknowledgements = packet.get("required_user_acknowledgements") or []
    template = str(packet.get("approval_text_template") or "")
    checks["approval_acknowledgements"] = len(acknowledgements) == 5
    checks["approval_template"] = all(
        token in template
        for token in ("USD 30", "1,800 API credits", "does not authorize production backfill")
    )

    failures = sorted(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "formal_state": READY_STATE if not failures else "APPROVAL_PACKET_STRUCTURAL_BLOCKED",
        "checks": checks,
        "passed_checks": sum(checks.values()),
        "total_checks": len(checks),
        "failures": failures,
        "execution_boundary": {
            "approval_state": packet.get("approval_state"),
            "automatic_purchase_or_subscription_allowed": exposure.get(
                "automatic_purchase_or_subscription_allowed"
            ),
            "api_key_read": boundary.get("api_key_read"),
            "paid_endpoint_calls": boundary.get("paid_endpoint_calls"),
            "maximum_pilot_credits": maximum_credits,
            "base_subscription_price_usd": exposure.get("base_subscription_price_usd"),
            "ready_for_paid_qualification_execution": boundary.get(
                "ready_for_paid_qualification_execution"
            ),
            "formal_stake": boundary.get("formal_stake"),
        },
    }


def self_test(packet: dict[str, Any]) -> None:
    report = validate(packet)
    assert report["formal_state"] == READY_STATE, report
    assert report["passed_checks"] == report["total_checks"], report

    mutated = copy.deepcopy(packet)
    mutated["frozen_pilot"]["maximum_pilot_credits"] = 1801
    assert validate(mutated)["formal_state"] == "APPROVAL_PACKET_STRUCTURAL_BLOCKED"

    mutated = copy.deepcopy(packet)
    mutated["execution_boundary"]["paid_endpoint_calls"] = 1
    assert validate(mutated)["formal_state"] == "APPROVAL_PACKET_STRUCTURAL_BLOCKED"

    mutated = copy.deepcopy(packet)
    mutated["maximum_exposure"]["automatic_purchase_or_subscription_allowed"] = True
    assert validate(mutated)["formal_state"] == "APPROVAL_PACKET_STRUCTURAL_BLOCKED"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    packet = load_json(args.packet)
    if args.self_test:
        self_test(packet)

    report = validate(packet)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "formal_state": report["formal_state"],
        "passed_checks": report["passed_checks"],
        "total_checks": report["total_checks"],
    }, indent=2))
    if report["failures"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
