#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = ROOT / "data" / "research" / "the-odds-api-free-forward-public-review-v1.json"
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "the_odds_api_free_forward_synthetic_event_v1.json"
ADAPTER_PATH = ROOT / "scripts" / "the_odds_api_free_forward_adapter_v1.py"

spec = importlib.util.spec_from_file_location("the_odds_api_adapter", ADAPTER_PATH)
assert spec and spec.loader
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


def expect_error(fn, message: str) -> None:
    try:
        fn()
    except adapter.TheOddsApiSyntheticAdapterError:
        return
    raise AssertionError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts" / "the-odds-api-free-forward-public-review-validation-v1.json",
    )
    args = parser.parse_args()

    review = json.loads(REVIEW_PATH.read_text(encoding="utf-8"))
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    tests = 0

    assert review["source_id"] == "the_odds_api_free_forward"
    assert review["public_plan_claims"]["free_credits_per_month"] == 500
    assert review["public_plan_claims"]["current_odds_included"] is True
    assert review["public_plan_claims"]["historical_odds_included"] is False
    assert review["nba_forward_scope"]["sport_key"] == "basketball_nba"
    assert review["nba_forward_scope"]["market"] == "h2h"
    assert review["terms_boundary"]["standalone_resale_or_redistribution_prohibited"] is True
    assert review["terms_boundary"]["public_quote_rows_allowed"] is False
    assert review["runtime_state"]["provider_requests_executed"] == 0
    assert review["runtime_state"]["point_in_time_qualified"] is False
    assert review["preflight_request"]["maximum_provider_requests"] == 2
    assert review["preflight_request"]["execution_enabled"] is False
    assert review["formal_stake"] == 0
    tests += 13

    rows = adapter.adapt_synthetic_event(
        fixture,
        collector_fetched_at_utc="2026-10-20T23:00:00Z",
    )
    assert len(rows) == 1
    row = rows[0]
    assert row["source_id"] == "the_odds_api_free_forward"
    assert row["bookmaker_key"] == "example_book"
    assert row["market_key"] == "h2h"
    assert row["home_price_decimal"] == 1.78
    assert row["away_price_decimal"] == 2.15
    assert row["bookmaker_last_update_utc"] == "2026-10-20T22:59:30Z"
    assert row["quote_time_authority"] == "bookmaker_last_update"
    assert row["collector_fetched_at_utc"] != row["bookmaker_last_update_utc"]
    assert row["mapping_state"] == "unmapped"
    assert row["source_rights_state"] == "unreviewed"
    assert row["raw_payload_retained"] is False
    tests += 11

    bad = copy.deepcopy(fixture)
    bad["sport_key"] = "basketball_wnba"
    expect_error(
        lambda: adapter.adapt_synthetic_event(bad, collector_fetched_at_utc="2026-10-20T23:00:00Z"),
        "non-NBA sport must fail",
    )
    tests += 1

    bad = copy.deepcopy(fixture)
    bad["bookmakers"][0].pop("last_update")
    bad["bookmakers"][0]["markets"][0].pop("last_update")
    expect_error(
        lambda: adapter.adapt_synthetic_event(bad, collector_fetched_at_utc="2026-10-20T23:00:00Z"),
        "missing provider-origin last_update must fail",
    )
    tests += 1

    bad = copy.deepcopy(fixture)
    bad["bookmakers"][0]["markets"][0]["outcomes"] = [
        {"name": "Example Home", "price": 1.78}
    ]
    expect_error(
        lambda: adapter.adapt_synthetic_event(bad, collector_fetched_at_utc="2026-10-20T23:00:00Z"),
        "one-sided h2h must fail",
    )
    tests += 1

    bad = copy.deepcopy(fixture)
    bad["bookmakers"][0]["markets"][0]["outcomes"][0]["name"] = "Wrong Team"
    expect_error(
        lambda: adapter.adapt_synthetic_event(bad, collector_fetched_at_utc="2026-10-20T23:00:00Z"),
        "non-exact team outcomes must fail",
    )
    tests += 1

    bad = copy.deepcopy(fixture)
    bad["bookmakers"][0]["markets"][0]["outcomes"][0]["price"] = 1.0
    expect_error(
        lambda: adapter.adapt_synthetic_event(bad, collector_fetched_at_utc="2026-10-20T23:00:00Z"),
        "invalid decimal price must fail",
    )
    tests += 1

    assert tests == 29
    qa = {
        "schema_version": 1,
        "formal_state": "THE_ODDS_API_FREE_FORWARD_PUBLIC_REVIEW_AND_SYNTHETIC_ADAPTER_VALID",
        "public_review_only": True,
        "zero_cost_forward_candidate": True,
        "historical_backfill_eligible": False,
        "synthetic_adapter_only": True,
        "public_schema_has_bookmaker_last_update": True,
        "provider_timestamp_semantics_runtime_verified": False,
        "user_terms_review_completed": False,
        "account_created": False,
        "api_key_connected": False,
        "provider_requests_executed": 0,
        "real_quotes_retained": 0,
        "public_quote_rows_emitted": 0,
        "formal_history_write_authorized": False,
        "market_metrics_executed": False,
        "contract_tests": tests,
        "formal_stake": 0,
        "next_unique_mainline": "AWAIT_USER_TERMS_REVIEW_AND_CAPPED_THE_ODDS_API_FREE_FORWARD_PREFLIGHT_APPROVAL",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
