#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
review = json.loads(
    (root / "data/research/bloombet-free-api-public-review-v1.json").read_text(
        encoding="utf-8"
    )
)
request = json.loads(
    (
        root
        / "data/research/bloombet-free-api-zero-cost-schema-probe-request-v1.json"
    ).read_text(encoding="utf-8")
)
current = json.loads(
    (
        root
        / "data/research/no-cost-timestamped-odds-source-qualification-current-status-v3.json"
    ).read_text(encoding="utf-8")
)
status = (root / "PROJECT_STATUS.md").read_text(encoding="utf-8")
doc = (root / "docs/bloombet-free-api-public-review-v1.md").read_text(
    encoding="utf-8"
)
handoff = (
    root
    / "docs/handoffs/nba_value_lab_handoff_2026-07-24_bloombet_public_review.md"
).read_text(encoding="utf-8")

assert review["formal_state"] == "BLOOMBET_FREE_API_PUBLIC_REVIEW_BLOCKED"
assert review["public_claims"]["free_price_usd_per_month"] == 0
assert review["public_claims"]["free_requests_per_month"] == 500
assert review["public_claims"]["credit_card_required"] is False
assert review["qualification_gate_result"]["overall"] == "BLOCKED"
assert review["decision"]["qualified_for_historical_backfill"] is False
assert review["decision"]["qualified_for_point_in_time_odds_join"] is False
assert review["decision"]["account_creation_authorized"] is False
assert review["decision"]["api_key_connection_authorized"] is False
assert review["decision"]["api_request_execution_authorized"] is False
assert review["decision"]["market_metrics_allowed"] is False
assert review["decision"]["formal_stake"] == 0

assert (
    request["formal_state"]
    == "BLOOMBET_FREE_API_ZERO_COST_SCHEMA_PROBE_REQUEST_VALID_AWAITING_EXPLICIT_USER_APPROVAL"
)
assert request["approval"]["approval_granted"] is False
assert request["approval"]["account_creation_authorized"] is False
assert request["approval"]["private_api_key_connection_authorized"] is False
assert request["approval"]["execution_enabled"] is False
assert request["execution_limits"]["maximum_execution_count"] == 1
assert request["execution_limits"]["execution_count"] == 0
assert request["execution_limits"]["maximum_api_requests"] == 3
assert request["execution_limits"]["bulk_history_download_allowed"] is False
assert request["execution_limits"]["pagination_allowed"] is False
assert request["user_only_setup"]["secret_may_be_pasted_into_chat"] is False
assert request["user_only_setup"]["secret_may_be_committed"] is False
assert request["user_only_setup"]["secret_may_appear_in_logs_or_artifacts"] is False
assert request["activation_boundary"]["this_request_executes_api_calls"] is False
assert request["activation_boundary"]["this_request_unlocks_market_backtest"] is False
assert request["activation_boundary"]["formal_stake"] == 0

assert (
    current["formal_state"]
    == "NO_COST_TIMESTAMPED_ODDS_QUALIFICATION_BLOOMBET_PUBLIC_REVIEW_BLOCKED_AWAITING_SCHEMA_PROBE_APPROVAL"
)
assert (
    current["next_unique_mainline"]
    == "BLOOMBET_FREE_API_ZERO_COST_SCHEMA_PROBE_AWAITING_EXPLICIT_USER_APPROVAL"
)
assert current["account_creation_authorized"] is False
assert current["free_api_key_connection_authorized"] is False
assert current["market_backtest_unlocked"] is False
assert current["formal_stake"] == 0

required_status = [
    "bloombet public review: COMPLETED / BLOCKED",
    "bloombet public response schema: NOT VERIFIED",
    "bloombet zero-cost schema probe request design: VALIDATED / AWAITING EXPLICIT USER APPROVAL",
    "BLOOMBET_FREE_API_ZERO_COST_SCHEMA_PROBE_AWAITING_EXPLICIT_USER_APPROVAL",
    "BLOCKED — ACCOUNT CREATION AND PRIVATE API KEY CONNECTION NOT AUTHORIZED",
    "formal Stake: 0",
]
for item in required_status:
    if item not in status:
        raise SystemExit(f"missing PROJECT_STATUS evidence: {item}")

for text, label in [(doc, "documentation"), (handoff, "handoff")]:
    for item in [
        "BLOOMBET_FREE_API_PUBLIC_REVIEW_BLOCKED",
        "BLOOMBET_FREE_API_ZERO_COST_SCHEMA_PROBE_AWAITING_EXPLICIT_USER_APPROVAL",
        "Formal Stake",
    ]:
        if item not in text:
            raise SystemExit(f"missing {label} evidence: {item}")

report = {
    "schema_version": 1,
    "formal_state": "BLOOMBET_FREE_API_PUBLIC_REVIEW_AND_SCHEMA_PROBE_REQUEST_VALID",
    "public_review_valid": True,
    "request_design_valid": True,
    "approval_granted": False,
    "execution_enabled": False,
    "execution_count": 0,
    "maximum_api_requests": 3,
    "account_created": False,
    "api_key_connected": False,
    "api_requests_executed": 0,
    "raw_quotes_retained": False,
    "market_backtest_executed": False,
    "market_metrics_executed": False,
    "formal_stake": 0,
    "next_unique_mainline": (
        "BLOOMBET_FREE_API_ZERO_COST_SCHEMA_PROBE_AWAITING_EXPLICIT_USER_APPROVAL"
    ),
}
out = root / "build/bloombet-free-api-public-review-validation-v1.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
