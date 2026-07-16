#!/usr/bin/env python3
"""V4.9 wrapper for the V4.8 T-60m locker.

It enriches every future T-60m record with an explicit prediction-state snapshot
and hash. T-5m can then prove whether a change is price-only or requires a new
prediction_id without rewriting the original T-60m record.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import lock_t60_snapshot as base


PREDICTION_STATE_KEYS = (
    "scheduled_at",
    "selection_team_id",
    "opponent_team_id",
    "p_f",
    "p_market_consensus",
    "p_conservative",
    "p_neutral",
    "p_optimistic",
    "coverage_pct",
    "confidence",
    "news_risk_level",
    "analysis_gate_status",
    "comparison_sources",
    "injury_confirmed",
    "starters_confirmed",
    "minutes_limit_confirmed",
    "source_lineage_complete",
    "market_rules_complete",
    "out_of_distribution",
    "reverse_path_resolved",
    "stale_warning",
    "model_market_gap_pp",
    "independent_evidence_count",
)


def prediction_state(candidate: dict[str, Any]) -> dict[str, Any]:
    return {key: candidate.get(key) for key in PREDICTION_STATE_KEYS}


_ORIGINAL_MAKE_RECORD = base.make_record


def enriched_make_record(*args: Any, **kwargs: Any) -> dict[str, Any]:
    record = _ORIGINAL_MAKE_RECORD(*args, **kwargs)
    item = args[0] if args else kwargs["item"]
    candidate = item["candidate"]
    state = prediction_state(candidate)
    record.update(
        {
            "scheduled_at": candidate["scheduled_at"],
            "analysis_gate_status": candidate["analysis_gate_status"],
            "comparison_sources": candidate["comparison_sources"],
            "injury_confirmed": candidate["injury_confirmed"],
            "starters_confirmed": candidate["starters_confirmed"],
            "minutes_limit_confirmed": candidate["minutes_limit_confirmed"],
            "source_lineage_complete": candidate["source_lineage_complete"],
            "market_rules_complete": candidate["market_rules_complete"],
            "price_timestamp_valid": candidate["price_timestamp_valid"],
            "out_of_distribution": candidate["out_of_distribution"],
            "reverse_path_resolved": candidate["reverse_path_resolved"],
            "stale_warning": candidate["stale_warning"],
            "model_market_gap_pp": candidate["model_market_gap_pp"],
            "independent_evidence_count": candidate["independent_evidence_count"],
            "data_age_minutes": candidate["data_age_minutes"],
            "similar_case_stability_score": candidate.get("similar_case_stability_score"),
            "prediction_state": state,
            "prediction_state_hash": base.canonical_hash(state, 32),
            "price_evaluated_at": candidate["observed_at"],
            "change_type": "initial_lock",
            "parent_prediction_id": None,
            "change_reasons": [],
        }
    )
    return record


base.make_record = enriched_make_record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="T-60m slate-wave JSON")
    parser.add_argument("--dry-run", action="store_true", help="validate and calculate without writing")
    parser.add_argument("--output", type=Path, help="optional calculation output JSON")
    args = parser.parse_args()
    base.run(args.input, dry_run=args.dry_run, output_path=args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
