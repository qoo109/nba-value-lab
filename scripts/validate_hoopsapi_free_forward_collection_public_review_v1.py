#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
review = json.loads(
    (root / "data/research/hoopsapi-free-forward-collection-public-review-v1.json").read_text(
        encoding="utf-8"
    )
)
current = json.loads(
    (root / "data/research/no-cost-timestamped-odds-source-qualification-current-status-v4.json").read_text(
        encoding="utf-8"
    )
)
status = (root / "PROJECT_STATUS.md").read_text(encoding="utf-8")
doc = (root / "docs/hoopsapi-free-forward-collection-public-review-v1.md").read_text(
    encoding="utf-8"
)
handoff = (
    root / "docs/handoffs/nba_value_lab_handoff_2026-07-24_hoopsapi_public_forward_review.md"
).read_text(encoding="utf-8")

assert review["formal_state"] == "HOOPSAPI_FREE_PUBLIC_REVIEW_FORWARD_ONLY_CANDIDATE"
assert review["public_plan_claims"]["free_requests_per_day"] == 10
assert review["public_plan_claims"]["credit_card_required"] is False
assert review["public_plan_claims"]["full_history_and_snapshots_free_tier"] is False
assert review["public_schema_evidence"]["game_id_present"] is True
assert review["public_schema_evidence"]["scheduled_start_time_present"] is True
assert review["public_schema_evidence"]["same_provider_two_sided_moneyline_shape_present"] is True
assert review["public_schema_evidence"]["quote_level_observed_at_present_in_public_example"] is False
assert review["terms_findings"]["raw_odds_redistribution_prohibited"] is True
assert review["decision"]["qualified_for_historical_backfill"] is False
assert review["decision"]["qualified_for_market_backtest"] is False
assert review["decision"]["structurally_promising_for_private_forward_collection"] is True
assert review["decision"]["forward_collection_authorized"] is False
assert review["decision"]["api_request_execution_authorized"] is False
assert review["decision"]["formal_stake"] == 0

assert current["formal_state"] == "NO_COST_TIMESTAMPED_ODDS_QUALIFICATION_FORWARD_COLLECTOR_DESIGN_READY"
assert current["recording_pr"] == 156
assert current["user_decisions"]["bloombet_schema_probe"] == "DEFERRED_BY_USER_NO_EXECUTION"
assert current["next_unique_mainline"] == "DESIGN_SOURCE_AGNOSTIC_PRIVATE_FORWARD_ODDS_COLLECTOR_V1"
assert current["next_task_requires_account_or_api_key"] is False
assert current["next_task_executes_provider_requests"] is False
assert current["provider_request_execution_authorized"] is False
assert current["market_backtest_unlocked"] is False
assert current["formal_stake"] == 0

required_status = [
    "bloombet schema probe: DEFERRED BY USER / NO EXECUTION",
    "hoopsapi public review: COMPLETED / FORWARD-ONLY CANDIDATE",
    "hoopsapi provider requests executed: 0",
    "DESIGN_SOURCE_AGNOSTIC_PRIVATE_FORWARD_ODDS_COLLECTOR_V1",
    "READY — DESIGN ONLY / NO ACCOUNT OR API KEY REQUIRED",
    "formal stake: 0",
]
for item in required_status:
    if item not in status:
        raise SystemExit(f"missing PROJECT_STATUS evidence: {item}")

for text, label in ((doc, "documentation"), (handoff, "handoff")):
    for item in (
        "HOOPSAPI_FREE_PUBLIC_REVIEW_FORWARD_ONLY_CANDIDATE",
        "DESIGN_SOURCE_AGNOSTIC_PRIVATE_FORWARD_ODDS_COLLECTOR_V1",
        "Formal Stake",
    ):
        if item not in text:
            raise SystemExit(f"missing {label} evidence: {item}")

report = {
    "schema_version": 1,
    "formal_state": "HOOPSAPI_FREE_PUBLIC_FORWARD_REVIEW_VALID",
    "recording_pr": 156,
    "public_review_valid": True,
    "bloombet_probe_deferred": True,
    "historical_backfill_qualified": False,
    "forward_only_candidate": True,
    "forward_collection_authorized": False,
    "next_design_requires_account_or_key": False,
    "provider_requests_executed": 0,
    "raw_quotes_retained": False,
    "market_backtest_executed": False,
    "market_metrics_executed": False,
    "formal_stake": 0,
    "next_unique_mainline": "DESIGN_SOURCE_AGNOSTIC_PRIVATE_FORWARD_ODDS_COLLECTOR_V1",
}

out = root / "build/hoopsapi-free-forward-collection-public-review-validation-v1.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
