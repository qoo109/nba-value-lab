#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "data" / "research" / "kaggle-basketball-odds-history-real-archive-aggregate-inspection-v1.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts" / "kaggle-basketball-odds-history-real-archive-inspection-validation-v1.json",
    )
    args = parser.parse_args()

    data = json.loads(REPORT.read_text(encoding="utf-8"))
    tests = 0

    assert data["formal_state"] == "KAGGLE_BASKETBALL_ODDS_HISTORY_REAL_ARCHIVE_INSPECTED_NOT_QUALIFIED"
    assert data["archive"]["sha256"] == "sha256:36685fa53deaba112f93515fefffb971b02613f32f2f24d5a22dd0088863d419"
    assert data["archive"]["notebook_present"] is True
    tests += 3

    regular = data["nba_files"]["nba_main_lines.csv"]
    detailed = data["nba_files"]["nba_detailed_odds.csv"]
    preseason = data["nba_files"]["nba_preseason_main_lines.csv"]
    preseason_detailed = data["nba_files"]["nba_preseason_detailed_odds.csv"]

    assert regular["rows"] == 8153
    assert regular["unique_source_event_ids"] == 1199
    assert regular["duplicate_event_timestamp_keys"] == 0
    assert regular["explicit_timezone_suffix_rows"] == 0
    assert regular["nonstandard_team_rows"] == 11
    assert regular["median_within_event_gap_minutes"] > 20
    assert regular["pct_within_event_gaps_le_15m"] < 0.30
    tests += 7

    assert detailed["rows"] == 149752
    assert detailed["duplicate_quote_keys"] == 0
    assert detailed["detail_group_mapping_pct"] == 1.0
    assert detailed["moneyline_exact_match_pct"] < 0.80
    assert detailed["moneyline_groups_diff_gt_0_05"] == 449
    assert detailed["moneyline_groups_diff_gt_0_10"] == 188
    tests += 6

    assert preseason["rows"] == 629
    assert preseason["unique_source_event_ids"] == 50
    assert preseason_detailed["rows"] == 12868
    assert preseason_detailed["detail_group_mapping_pct"] == 1.0
    tests += 4

    provenance = data["notebook_provenance"]
    assert provenance["provider_origin_timestamp_present"] is False
    assert provenance["scheduled_tipoff_field_present"] is False
    assert provenance["row_level_bookmaker_field_present"] is False
    assert provenance["home_away_semantics_documented"] is False
    assert provenance["upstream_terms_or_automation_rights_evidence_in_archive"] is False
    tests += 5

    q = data["qualification"]
    assert q["schema_candidate"] is True
    assert q["point_in_time_qualified"] is False
    assert q["historical_backfill_qualified"] is False
    assert q["formal_history_write_authorized"] is False
    assert q["g1_2_0_real_input_qualified"] is False
    assert q["market_backtest_unlocked"] is False
    assert q["clv_ev_roi_unlocked"] is False
    assert q["betting_edge_claim_allowed"] is False
    assert q["formal_stake"] == 0
    tests += 9

    assert data["decision"] == "KEEP_PRIVATE_RESEARCH_DIAGNOSTIC_ONLY_REJECT_FORMAL_POINT_IN_TIME_INGESTION"
    assert data["next_unique_mainline"] == "AWAIT_REAL_GOVERNED_2026_27_T60_INPUT_AND_QUALIFIED_TIMESTAMPED_ODDS"
    tests += 2

    assert tests == 36
    qa = {
        "schema_version": 1,
        "formal_state": "KAGGLE_BASKETBALL_ODDS_HISTORY_REAL_ARCHIVE_INSPECTION_RECORD_VALID",
        "archive_inspected": True,
        "aggregate_only": True,
        "raw_archive_committed": False,
        "quote_rows_emitted": 0,
        "prices_emitted": 0,
        "provider_requests_executed": 0,
        "point_in_time_qualified": False,
        "historical_backfill_qualified": False,
        "formal_history_write_authorized": False,
        "market_metrics_executed": False,
        "contract_tests": tests,
        "formal_stake": 0,
        "next_unique_mainline": "AWAIT_REAL_GOVERNED_2026_27_T60_INPUT_AND_QUALIFIED_TIMESTAMPED_ODDS",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
