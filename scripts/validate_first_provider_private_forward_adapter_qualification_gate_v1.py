#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GATE_PATH = ROOT / "data/research/first-provider-private-forward-adapter-qualification-gate-v1.json"
STATUS_PATH = ROOT / "data/research/no-cost-timestamped-odds-source-qualification-current-status-v7.json"
PUBLIC_REVIEW_PATH = ROOT / "data/research/hoopsapi-free-forward-collection-public-review-v1.json"
DOC_PATH = ROOT / "docs/first-provider-private-forward-adapter-qualification-gate-v1.md"
HANDOFF_PATH = ROOT / "docs/handoffs/nba_value_lab_handoff_2026-07-24_first_provider_adapter_gate.md"
PROJECT_STATUS_PATH = ROOT / "PROJECT_STATUS.md"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_candidate(state: dict[str, bool]) -> dict[str, bool]:
    structural = all(
        state[name]
        for name in (
            "stable_event_id",
            "teams_present",
            "scheduled_tipoff_present",
            "provider_identity_present",
            "same_book_two_sided_h2h",
        )
    )
    synthetic_shell_allowed = structural
    preflight_allowed = all(
        state[name]
        for name in (
            "terms_accepted_by_user",
            "secret_connected_privately",
            "explicit_preflight_approval",
        )
    )
    runtime_allowed = all(
        state[name]
        for name in (
            "terms_accepted_by_user",
            "secret_connected_privately",
            "explicit_runtime_approval",
            "runtime_schema_verified",
            "private_normalized_retention_allowed",
        )
    ) and structural
    point_in_time_allowed = runtime_allowed and state["provider_timestamp_semantics_verified"]
    return {
        "synthetic_shell_allowed": synthetic_shell_allowed,
        "preflight_allowed": preflight_allowed,
        "runtime_allowed": runtime_allowed,
        "point_in_time_allowed": point_in_time_allowed,
        "fetched_at_substitution_allowed": False,
        "raw_publication_allowed": False,
        "rate_limit_bypass_allowed": False,
    }


def run_policy_scenarios() -> dict[str, bool]:
    base = {
        "stable_event_id": True,
        "teams_present": True,
        "scheduled_tipoff_present": True,
        "provider_identity_present": True,
        "same_book_two_sided_h2h": True,
        "terms_accepted_by_user": False,
        "secret_connected_privately": False,
        "explicit_preflight_approval": False,
        "explicit_runtime_approval": False,
        "runtime_schema_verified": False,
        "private_normalized_retention_allowed": False,
        "provider_timestamp_semantics_verified": False,
    }

    results: dict[str, bool] = {}

    public_only = evaluate_candidate(dict(base))
    results["public_shape_allows_synthetic_shell_only"] = (
        public_only["synthetic_shell_allowed"] is True
        and public_only["preflight_allowed"] is False
        and public_only["runtime_allowed"] is False
        and public_only["point_in_time_allowed"] is False
    )

    missing_event = dict(base)
    missing_event["stable_event_id"] = False
    results["missing_event_identity_blocks_shell"] = (
        evaluate_candidate(missing_event)["synthetic_shell_allowed"] is False
    )

    private_secret_without_approval = dict(base)
    private_secret_without_approval["terms_accepted_by_user"] = True
    private_secret_without_approval["secret_connected_privately"] = True
    results["secret_without_explicit_approval_blocks_preflight"] = (
        evaluate_candidate(private_secret_without_approval)["preflight_allowed"] is False
    )

    approved_preflight = dict(private_secret_without_approval)
    approved_preflight["explicit_preflight_approval"] = True
    approved_preflight_result = evaluate_candidate(approved_preflight)
    results["approved_preflight_does_not_equal_runtime"] = (
        approved_preflight_result["preflight_allowed"] is True
        and approved_preflight_result["runtime_allowed"] is False
    )

    runtime_without_timestamp = dict(approved_preflight)
    runtime_without_timestamp["explicit_runtime_approval"] = True
    runtime_without_timestamp["runtime_schema_verified"] = True
    runtime_without_timestamp["private_normalized_retention_allowed"] = True
    runtime_without_timestamp_result = evaluate_candidate(runtime_without_timestamp)
    results["runtime_without_provider_timestamp_is_not_point_in_time"] = (
        runtime_without_timestamp_result["runtime_allowed"] is True
        and runtime_without_timestamp_result["point_in_time_allowed"] is False
    )

    timestamp_qualified = dict(runtime_without_timestamp)
    timestamp_qualified["provider_timestamp_semantics_verified"] = True
    results["provider_timestamp_required_for_point_in_time"] = (
        evaluate_candidate(timestamp_qualified)["point_in_time_allowed"] is True
    )

    invariants = evaluate_candidate(timestamp_qualified)
    results["fetched_at_never_substitutes_observed_at"] = (
        invariants["fetched_at_substitution_allowed"] is False
    )
    results["raw_publication_always_blocked"] = invariants["raw_publication_allowed"] is False
    results["rate_limit_bypass_always_blocked"] = invariants["rate_limit_bypass_allowed"] is False

    if not all(results.values()):
        failed = sorted(name for name, passed in results.items() if not passed)
        raise SystemExit(f"qualification gate policy scenarios failed: {failed}")
    return results


def main() -> None:
    gate = load_json(GATE_PATH)
    status = load_json(STATUS_PATH)
    public_review = load_json(PUBLIC_REVIEW_PATH)
    doc = DOC_PATH.read_text(encoding="utf-8")
    handoff = HANDOFF_PATH.read_text(encoding="utf-8")
    project_status = PROJECT_STATUS_PATH.read_text(encoding="utf-8")

    assert public_review["formal_state"] == "HOOPSAPI_FREE_PUBLIC_REVIEW_FORWARD_ONLY_CANDIDATE"
    assert public_review["public_schema_evidence"]["game_id_present"] is True
    assert public_review["public_schema_evidence"]["scheduled_start_time_present"] is True
    assert public_review["public_schema_evidence"]["same_provider_two_sided_moneyline_shape_present"] is True
    assert public_review["public_schema_evidence"]["quote_level_observed_at_present_in_public_example"] is False
    assert public_review["public_schema_evidence"]["provider_last_update_present_in_public_example"] is False
    assert public_review["terms_findings"]["raw_odds_redistribution_prohibited"] is True
    assert public_review["decision"]["forward_collection_authorized"] is False
    assert public_review["decision"]["api_request_execution_authorized"] is False
    assert public_review["decision"]["formal_stake"] == 0

    assert gate["formal_state"] == "FIRST_PROVIDER_PRIVATE_FORWARD_ADAPTER_QUALIFICATION_GATE_VALIDATED"
    assert gate["candidate_provider"]["source_id"] == "hoopsapi_free_forward_collection"
    contract = gate["gate_contract"]
    assert contract["structural_schema_gate"]["synthetic_adapter_shell_allowed"] is True
    assert contract["structural_schema_gate"]["runtime_schema_qualification"] is False
    assert contract["timestamp_authority_gate"]["collector_fetched_at_may_substitute_observed_at"] is False
    required_output = contract["timestamp_authority_gate"]["required_adapter_output_before_timestamp_qualification"]
    assert required_output == {
        "quote_time_authority": "unverified",
        "quote_observed_at_utc": None,
        "point_in_time_eligible": False,
    }
    assert contract["rights_and_retention_gate"]["user_must_accept_provider_terms_personally"] is True
    assert contract["rights_and_retention_gate"]["raw_payload_retention_default"] is False
    assert contract["rights_and_retention_gate"]["public_raw_quote_rows_allowed"] is False
    assert contract["access_and_secret_gate"]["account_creation_authorized"] is False
    assert contract["access_and_secret_gate"]["provider_terms_acceptance_authorized"] is False
    assert contract["access_and_secret_gate"]["api_key_connection_authorized"] is False
    assert contract["access_and_secret_gate"]["secret_setup_requires_separate_user_action"] is True
    assert contract["quota_and_request_gate"]["initial_schema_preflight_request_cap_if_later_approved"] == 3
    assert contract["quota_and_request_gate"]["initial_schema_preflight_authorized"] is False
    assert contract["quota_and_request_gate"]["provider_requests_executed"] == 0
    assert contract["event_mapping_gate"]["exact_mapping_required"] is True
    assert contract["event_mapping_gate"]["fuzzy_matching_allowed"] is False
    assert contract["event_mapping_gate"]["season_or_competition_inference_allowed"] is False
    assert contract["market_gate"]["same_book_two_sided_required"] is True
    assert contract["market_gate"]["closing_substitution_for_t60_or_t5_allowed"] is False
    assert contract["private_storage_gate"]["aggregate_only_qa_required"] is True
    assert contract["private_storage_gate"]["cross_run_deduplication_required"] is True
    activation = contract["activation_gate"]
    assert activation["synthetic_adapter_shell_authorized"] is True
    assert activation["real_provider_payload_authorized"] is False
    assert activation["provider_request_execution_authorized"] is False
    assert activation["real_quote_ingestion_authorized"] is False
    assert activation["point_in_time_qualification_authorized"] is False
    assert activation["market_backtest_authorized"] is False
    assert activation["formal_stake"] == 0
    decision = gate["candidate_decision"]
    assert decision["gate_design_valid"] is True
    assert decision["provider_selected_for_synthetic_shell"] is True
    assert decision["provider_runtime_qualified"] is False
    assert decision["provider_point_in_time_qualified"] is False
    assert decision["qualified_for_historical_backfill"] is False
    assert gate["next_unique_mainline"] == "IMPLEMENT_HOOPSAPI_PRIVATE_FORWARD_ADAPTER_SYNTHETIC_SHELL_V1"

    assert status["formal_state"] == "NO_COST_TIMESTAMPED_ODDS_FIRST_PROVIDER_ADAPTER_GATE_VALIDATED"
    assert isinstance(status["recording_pr"], int) and status["recording_pr"] > 0
    status_gate = status["first_provider_adapter_gate"]
    assert status_gate["candidate_source_id"] == "hoopsapi_free_forward_collection"
    assert status_gate["synthetic_adapter_shell_authorized"] is True
    assert status_gate["provider_runtime_qualified"] is False
    assert status_gate["provider_point_in_time_qualified"] is False
    assert status_gate["provider_requests_executed"] == 0
    assert status["next_unique_mainline"] == "IMPLEMENT_HOOPSAPI_PRIVATE_FORWARD_ADAPTER_SYNTHETIC_SHELL_V1"
    assert status["next_task_requires_account_or_api_key"] is False
    assert status["next_task_executes_provider_requests"] is False
    assert status["market_backtest_unlocked"] is False
    assert status["formal_stake"] == 0

    required_doc_text = (
        "FIRST_PROVIDER_PRIVATE_FORWARD_ADAPTER_QUALIFICATION_GATE_VALIDATED",
        "collector_fetched_at_utc NEVER substitutes quote_observed_at_utc",
        "IMPLEMENT_HOOPSAPI_PRIVATE_FORWARD_ADAPTER_SYNTHETIC_SHELL_V1",
        "Provider Requests Executed：0",
        "Formal Stake：0",
    )
    for text, label in ((doc, "documentation"), (handoff, "handoff")):
        for item in required_doc_text:
            if item not in text:
                raise SystemExit(f"missing {label} evidence: {item}")

    required_project_status = (
        "first provider adapter qualification gate: VALIDATED / HOOPSAPI / RUNTIME BLOCKED",
        "hoopsapi synthetic adapter shell: AUTHORIZED",
        "hoopsapi provider runtime qualified: false",
        "hoopsapi point-in-time qualified: false",
        "hoopsapi account, terms, key and requests: NOT AUTHORIZED",
        "first provider adapter requests executed: 0",
        "IMPLEMENT_HOOPSAPI_PRIVATE_FORWARD_ADAPTER_SYNTHETIC_SHELL_V1",
        "READY — SYNTHETIC SHELL ONLY / NETWORK DISABLED",
        "formal stake: 0",
    )
    for item in required_project_status:
        if item not in project_status:
            raise SystemExit(f"missing PROJECT_STATUS evidence: {item}")

    scenarios = run_policy_scenarios()
    report = {
        "schema_version": 1,
        "formal_state": "FIRST_PROVIDER_PRIVATE_FORWARD_ADAPTER_QUALIFICATION_GATE_VALID",
        "gate_valid": True,
        "candidate_source_id": "hoopsapi_free_forward_collection",
        "synthetic_shell_authorized": True,
        "provider_runtime_qualified": False,
        "provider_point_in_time_qualified": False,
        "provider_requests_executed": 0,
        "real_quotes_retained": False,
        "public_quote_rows_allowed": False,
        "network_requests_executed": 0,
        "policy_scenarios": len(scenarios),
        "market_metrics_executed": False,
        "formal_stake": 0,
        "next_unique_mainline": "IMPLEMENT_HOOPSAPI_PRIVATE_FORWARD_ADAPTER_SYNTHETIC_SHELL_V1",
    }
    report_text = json.dumps(report, sort_keys=True)
    for forbidden in ("home_price", "away_price", "raw_payload", "authorization_header"):
        if forbidden in report_text:
            raise SystemExit(f"aggregate report leaked forbidden fragment: {forbidden}")

    out = ROOT / "build/first-provider-private-forward-adapter-qualification-gate-validation-v1.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
