#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REQUEST_PATH = ROOT / "data/research/hoopsapi-private-runtime-preflight-request-v1.json"
STATUS_PATH = ROOT / "data/research/no-cost-timestamped-odds-source-qualification-current-status-v8.json"
PUBLIC_REVIEW_PATH = ROOT / "data/research/hoopsapi-free-forward-collection-public-review-v1.json"
GATE_PATH = ROOT / "data/research/first-provider-private-forward-adapter-qualification-gate-v1.json"
ADAPTER_PATH = ROOT / "scripts/hoopsapi_private_forward_adapter_v1.py"
DOC_PATH = ROOT / "docs/hoopsapi-private-runtime-preflight-request-v1.md"
HANDOFF_PATH = ROOT / "docs/handoffs/nba_value_lab_handoff_2026-07-24_hoopsapi_runtime_preflight_request_design.md"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_preflight(state: dict[str, bool]) -> dict[str, bool]:
    prerequisites = all(
        state[name]
        for name in (
            "terms_accepted_by_user",
            "account_created_by_user",
            "api_key_connected_privately",
            "explicit_preflight_approval",
        )
    )
    preflight_allowed = prerequisites
    runtime_collection_allowed = prerequisites and state["separate_runtime_activation"]
    point_in_time_allowed = (
        runtime_collection_allowed
        and state["runtime_schema_verified"]
        and state["provider_timestamp_semantics_verified"]
        and state["private_retention_policy_activated"]
    )
    return {
        "preflight_allowed": preflight_allowed,
        "runtime_collection_allowed": runtime_collection_allowed,
        "point_in_time_allowed": point_in_time_allowed,
        "collector_fetched_at_substitution_allowed": False,
        "historical_backfill_allowed": False,
        "raw_publication_allowed": False,
        "market_metrics_allowed": False,
    }


def run_policy_scenarios() -> dict[str, bool]:
    base = {
        "terms_accepted_by_user": False,
        "account_created_by_user": False,
        "api_key_connected_privately": False,
        "explicit_preflight_approval": False,
        "separate_runtime_activation": False,
        "runtime_schema_verified": False,
        "provider_timestamp_semantics_verified": False,
        "private_retention_policy_activated": False,
    }
    results: dict[str, bool] = {}

    results["design_only_does_not_execute"] = evaluate_preflight(dict(base))["preflight_allowed"] is False

    terms_only = dict(base)
    terms_only["terms_accepted_by_user"] = True
    results["terms_only_insufficient"] = evaluate_preflight(terms_only)["preflight_allowed"] is False

    secret_without_approval = dict(base)
    secret_without_approval.update(
        {
            "terms_accepted_by_user": True,
            "account_created_by_user": True,
            "api_key_connected_privately": True,
        }
    )
    results["secret_without_explicit_approval_blocked"] = (
        evaluate_preflight(secret_without_approval)["preflight_allowed"] is False
    )

    approval_without_secret = dict(base)
    approval_without_secret.update(
        {
            "terms_accepted_by_user": True,
            "account_created_by_user": True,
            "explicit_preflight_approval": True,
        }
    )
    results["approval_without_secret_blocked"] = (
        evaluate_preflight(approval_without_secret)["preflight_allowed"] is False
    )

    approved = dict(secret_without_approval)
    approved["explicit_preflight_approval"] = True
    approved_result = evaluate_preflight(approved)
    results["capped_preflight_can_be_authorized_only_after_all_prerequisites"] = (
        approved_result["preflight_allowed"] is True
        and approved_result["runtime_collection_allowed"] is False
        and approved_result["point_in_time_allowed"] is False
    )

    runtime_without_timestamp = dict(approved)
    runtime_without_timestamp.update(
        {
            "separate_runtime_activation": True,
            "runtime_schema_verified": True,
            "private_retention_policy_activated": True,
        }
    )
    runtime_without_timestamp_result = evaluate_preflight(runtime_without_timestamp)
    results["runtime_schema_without_timestamp_not_point_in_time"] = (
        runtime_without_timestamp_result["runtime_collection_allowed"] is True
        and runtime_without_timestamp_result["point_in_time_allowed"] is False
    )

    fully_qualified = dict(runtime_without_timestamp)
    fully_qualified["provider_timestamp_semantics_verified"] = True
    results["timestamp_semantics_required_for_point_in_time"] = (
        evaluate_preflight(fully_qualified)["point_in_time_allowed"] is True
    )

    invariants = evaluate_preflight(fully_qualified)
    results["collector_fetched_at_never_substitutes_observed_at"] = (
        invariants["collector_fetched_at_substitution_allowed"] is False
    )
    results["historical_backfill_remains_blocked"] = invariants["historical_backfill_allowed"] is False
    results["raw_publication_remains_blocked"] = invariants["raw_publication_allowed"] is False
    results["market_metrics_remain_blocked"] = invariants["market_metrics_allowed"] is False

    if not all(results.values()):
        failed = sorted(name for name, passed in results.items() if not passed)
        raise SystemExit(f"runtime preflight policy scenarios failed: {failed}")
    return results


def main() -> None:
    request = load_json(REQUEST_PATH)
    status = load_json(STATUS_PATH)
    public_review = load_json(PUBLIC_REVIEW_PATH)
    gate = load_json(GATE_PATH)
    adapter_source = ADAPTER_PATH.read_text(encoding="utf-8")
    doc = DOC_PATH.read_text(encoding="utf-8")
    handoff = HANDOFF_PATH.read_text(encoding="utf-8")

    assert public_review["formal_state"] == "HOOPSAPI_FREE_PUBLIC_REVIEW_FORWARD_ONLY_CANDIDATE"
    assert public_review["public_schema_evidence"]["quote_level_observed_at_present_in_public_example"] is False
    assert public_review["public_schema_evidence"]["historical_snapshot_endpoint_available_on_free_tier"] is False
    assert public_review["terms_findings"]["raw_odds_redistribution_prohibited"] is True
    assert public_review["decision"]["api_request_execution_authorized"] is False

    assert gate["formal_state"] == "FIRST_PROVIDER_PRIVATE_FORWARD_ADAPTER_QUALIFICATION_GATE_VALIDATED"
    assert gate["gate_contract"]["quota_and_request_gate"]["initial_schema_preflight_request_cap_if_later_approved"] == 3
    assert gate["gate_contract"]["quota_and_request_gate"]["initial_schema_preflight_authorized"] is False
    assert gate["gate_contract"]["timestamp_authority_gate"]["collector_fetched_at_may_substitute_observed_at"] is False

    assert request["formal_state"] == "HOOPSAPI_PRIVATE_RUNTIME_PREFLIGHT_REQUEST_DESIGN_VALIDATED_AWAITING_USER_SETUP_AND_EXPLICIT_APPROVAL"
    assert request["design_only"] is True
    authorization = request["authorization_state"]
    assert authorization["user_must_accept_provider_terms_personally"] is True
    assert authorization["provider_terms_accepted_by_user"] is False
    assert authorization["account_creation_authorized"] is False
    assert authorization["account_created_by_user"] is False
    assert authorization["api_key_connection_authorized"] is False
    assert authorization["api_key_connected_privately"] is False
    assert authorization["explicit_preflight_approval_required"] is True
    assert authorization["explicit_preflight_approval_granted"] is False
    assert authorization["execution_enabled"] is False
    assert authorization["execution_count"] == 0
    assert authorization["execution_limit"] == 1
    assert authorization["provider_requests_executed"] == 0
    assert authorization["provider_request_cap"] == 3

    secret = request["secret_contract"]
    assert secret["secret_location"] == "UNSELECTED_USER_CONTROLLED_PRIVATE_SECRET_STORE"
    assert secret["secret_may_be_committed_to_repository"] is False
    assert secret["secret_may_be_written_to_logs"] is False
    assert secret["secret_may_be_written_to_artifacts"] is False
    assert secret["secret_setup_is_separate_user_action"] is True

    plan = request["preflight_plan"]
    assert plan["maximum_requests"] == 3
    assert plan["rate_limit_bypass_allowed"] is False
    assert plan["pagination_allowed"] is False
    assert plan["historical_endpoint_allowed"] is False
    assert plan["continuous_collection_allowed"] is False
    assert plan["scheduler_allowed"] is False
    assert plan["retry_on_auth_failure_allowed"] is False

    checks = request["runtime_qualification_checks"]
    assert checks["collector_fetched_at_may_substitute_provider_observed_at"] is False
    assert checks["exact_event_mapping_required_for_point_in_time"] is True
    assert checks["fuzzy_or_nearest_time_mapping_allowed"] is False

    fail_closed = request["fail_closed_outputs"]["missing_provider_timestamp"]
    assert fail_closed == {
        "quote_time_authority": "unverified",
        "quote_observed_at_utc": None,
        "point_in_time_eligible": False,
    }

    aggregate = request["aggregate_only_qa_contract"]
    assert aggregate["public_artifact_must_be_aggregate_only"] is True
    for item in ("API key", "authorization header", "raw payload", "raw quote rows", "bookmaker prices"):
        assert item in aggregate["forbidden_outputs"]

    activation = request["activation_boundaries"]
    assert activation["provider_runtime_schema_qualified"] is False
    assert activation["provider_point_in_time_qualified"] is False
    assert activation["real_quote_ingestion_authorized"] is False
    assert activation["historical_backfill_authorized"] is False
    assert activation["market_backtest_authorized"] is False
    assert activation["clv_ev_roi_authorized"] is False
    assert activation["betting_claim_authorized"] is False
    assert activation["formal_stake"] == 0
    assert request["next_unique_mainline"] == "AWAIT_HOOPSAPI_USER_SETUP_AND_EXPLICIT_PREFLIGHT_APPROVAL"

    assert status["formal_state"] == "NO_COST_TIMESTAMPED_ODDS_HOOPSAPI_RUNTIME_PREFLIGHT_REQUEST_DESIGNED"
    assert status["synthetic_adapter_shell"]["merged_pr"] == 165
    assert status["synthetic_adapter_shell"]["provider_requests_executed"] == 0
    assert status["runtime_preflight_request"]["request_id"] == request["request_id"]
    assert status["runtime_preflight_request"]["execution_enabled"] is False
    assert status["runtime_preflight_request"]["provider_request_cap"] == 3
    assert status["next_unique_mainline"] == "AWAIT_HOOPSAPI_USER_SETUP_AND_EXPLICIT_PREFLIGHT_APPROVAL"
    assert status["provider_request_execution_authorized"] is False
    assert status["market_backtest_unlocked"] is False
    assert status["formal_stake"] == 0

    forbidden_runtime_fragments = ("import requests", "from requests", "urllib.request", "httpx", "aiohttp", "os.environ")
    for fragment in forbidden_runtime_fragments:
        if fragment in adapter_source:
            raise SystemExit(f"synthetic adapter unexpectedly contains runtime fragment: {fragment}")

    required_text = (
        "HOOPSAPI-PRIVATE-RUNTIME-PREFLIGHT-2026-07-24-001",
        "provider request cap: 3",
        "execution count: 0 / 1",
        "collector_fetched_at_utc` NEVER substitutes `quote_observed_at_utc",
        "AWAIT_HOOPSAPI_USER_SETUP_AND_EXPLICIT_PREFLIGHT_APPROVAL",
        "Formal Stake：0",
    )
    for text, label in ((doc, "documentation"), (handoff, "handoff")):
        for item in required_text:
            if item not in text:
                raise SystemExit(f"missing {label} evidence: {item}")

    scenarios = run_policy_scenarios()
    report = {
        "schema_version": 1,
        "formal_state": "HOOPSAPI_PRIVATE_RUNTIME_PREFLIGHT_REQUEST_DESIGN_VALID",
        "request_id": request["request_id"],
        "design_only": True,
        "request_cap": 3,
        "execution_count": 0,
        "provider_requests_executed": 0,
        "account_creation_authorized": False,
        "terms_acceptance_authorized_for_assistant": False,
        "api_key_connection_authorized": False,
        "execution_enabled": False,
        "runtime_schema_qualified": False,
        "point_in_time_qualified": False,
        "policy_scenarios": len(scenarios),
        "public_artifact_aggregate_only": True,
        "market_metrics_executed": False,
        "formal_stake": 0,
        "next_unique_mainline": "AWAIT_HOOPSAPI_USER_SETUP_AND_EXPLICIT_PREFLIGHT_APPROVAL",
    }
    report_text = json.dumps(report, sort_keys=True).lower()
    for forbidden in ("api_key_value", "authorization_header", "raw_payload", "home_price", "away_price"):
        if forbidden in report_text:
            raise SystemExit(f"aggregate report leaked forbidden fragment: {forbidden}")

    out = ROOT / "build/hoopsapi-private-runtime-preflight-request-validation-v1.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
