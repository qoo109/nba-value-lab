#!/usr/bin/env python3
"""Fail-closed validation for the no-cost timestamped-odds source matrix."""

from __future__ import annotations

import json
from pathlib import Path

MATRIX_PATH = Path(
    "data/research/no-cost-timestamped-odds-source-qualification-matrix-v1.json"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    payload = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))

    require(
        payload["schema_version"]
        == "no-cost-timestamped-odds-source-qualification-matrix-v1",
        "unexpected schema version",
    )
    require(
        payload["formal_state"]
        == "NO_COST_TIMESTAMPED_ODDS_SOURCE_QUALIFICATION_MATRIX_RESEARCH_ONLY",
        "matrix must remain research-only",
    )
    require(payload["user_decision"] == "PAID_PILOT_NOT_APPROVED", "paid decision changed")

    gates = payload["qualification_gates"]
    require(gates["cost_usd"] == 0, "non-zero source cost allowed")
    require(gates["credit_card_or_paid_trial_allowed"] is False, "paid trial allowed")
    require(gates["real_observed_at_required"] is True, "observed_at gate removed")
    require(gates["bookmaker_identity_required"] is True, "bookmaker gate removed")
    require(
        gates["two_sided_same_bookmaker_h2h_required"] is True,
        "same-book two-sided gate removed",
    )
    require(gates["strictly_pre_tip_required"] is True, "pre-tip gate removed")
    require(gates["future_snapshot_fill_allowed"] is False, "future fill allowed")
    require(gates["opening_inference_allowed"] is False, "opening inference allowed")
    require(gates["fuzzy_matching_allowed"] is False, "fuzzy matching allowed")
    require(gates["terms_or_access_control_bypass_allowed"] is False, "bypass allowed")

    candidates = payload["candidates"]
    require(len(candidates) >= 8, "candidate recall unexpectedly narrow")
    ids = [candidate["source_id"] for candidate in candidates]
    require(len(ids) == len(set(ids)), "duplicate source IDs")

    by_id = {candidate["source_id"]: candidate for candidate in candidates}
    required_ids = {
        "bloombet_free_api",
        "kaggle_zachht_basketball_odds_history",
        "hoopsapi_free_forward_collection",
        "balldontlie_nba_odds",
        "the_odds_api_historical_v4",
        "kaggle_christophertreasure_nba_odds",
        "kaggle_cviaxmiwnptr_nba_betting_data",
        "oddsportal_manual_reference",
        "covers_sports_odds_history_nba",
        "oddscrowd_current_comparison",
    }
    require(required_ids <= set(ids), "required source candidate missing")

    require(
        by_id["bloombet_free_api"]["decision"]
        == "PROMISING_NEEDS_ZERO_COST_SCHEMA_AND_TERMS_PILOT",
        "BloomBet was promoted without qualification",
    )
    require(
        by_id["kaggle_zachht_basketball_odds_history"]["decision"]
        == "PROMISING_NEEDS_FILE_SCHEMA_AND_PROVENANCE_REVIEW",
        "ZachHT archive was promoted without file review",
    )
    require(
        by_id["hoopsapi_free_forward_collection"]["decision"]
        == "FORWARD_COLLECTION_CANDIDATE_ONLY_NOT_HISTORICAL_BACKFILL",
        "HoopsAPI free tier incorrectly treated as historical backfill",
    )
    require(
        by_id["balldontlie_nba_odds"]["decision"]
        == "REJECT_NO_COST_HISTORICAL_GATE",
        "paid BALLDONTLIE odds accepted as free",
    )
    require(
        by_id["the_odds_api_historical_v4"]["decision"]
        == "REJECT_USER_DECLINED_PAID_PATH",
        "declined paid path reopened",
    )

    for candidate in candidates:
        require(candidate["market_metrics_allowed"] is False, f"market metrics enabled: {candidate['source_id']}")

    summary = payload["summary"]
    require(summary["qualified_for_historical_backfill"] == [], "source prematurely qualified")
    require(summary["market_backtest_unlocked"] is False, "market backtest unlocked")
    require(summary["clv_ev_roi_unlocked"] is False, "CLV/EV/ROI unlocked")
    require(summary["betting_edge_claim_allowed"] is False, "edge claim enabled")
    require(summary["formal_stake"] == 0, "Stake changed")

    print(
        json.dumps(
            {
                "formal_state": payload["formal_state"],
                "candidate_count": len(candidates),
                "qualified_historical_sources": 0,
                "promising_for_next_review": summary["promising_for_next_review"],
                "market_backtest_unlocked": False,
                "formal_stake": 0,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
