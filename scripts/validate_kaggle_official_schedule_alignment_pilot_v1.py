#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "data" / "research" / "kaggle-official-schedule-alignment-pilot-v1.json"
OUTPUT_PATH = ROOT / "artifacts" / "kaggle-official-schedule-alignment-pilot-validation-v1.json"


def main() -> int:
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    tests = 0

    assert report["formal_state"] == "KAGGLE_OFFICIAL_SCHEDULE_ALIGNMENT_20_GAME_PILOT_VALID"
    assert report["scope"]["pilot_games"] == 20
    assert report["scope"]["season"] == "2025-26"
    assert report["scope"]["season_type"] == "regular_season"
    assert report["scope"]["official_schedule_subject_to_change"] is True
    assert report["scope"]["raw_archive_committed"] is False
    assert report["scope"]["quote_rows_committed"] is False
    assert report["scope"]["prices_committed"] is False
    assert report["method"]["quote_time_repair"] is False
    tests += 9

    summary = report["summary"]
    assert summary["official_games_uniquely_matched"] == 20
    assert summary["official_games_unmatched"] == 0
    assert summary["kaggle_team1_equals_official_away"] == 20
    assert summary["kaggle_team2_equals_official_home"] == 20
    assert summary["events_with_post_tip_snapshots"] == 0
    assert summary["closest_batch_within_t60_plus_minus_5_minutes"] == 4
    assert summary["closest_batch_within_t60_plus_minus_60_minutes"] == 6
    assert summary["selected_snapshots_with_detailed_group"] == 20
    assert summary["selected_snapshots_main_detail_moneyline_exact_match"] == 19
    assert summary["selected_snapshots_main_detail_moneyline_exact_match_pct"] == 0.95
    assert summary["largest_selected_main_detail_decimal_odds_difference"] == 0.02
    tests += 11

    games = report["games"]
    assert len(games) == 20
    assert len({game["source_event_id"] for game in games}) == 20
    assert all(game["kaggle_team1_equals_official_away"] for game in games)
    assert all(game["detail_group_present"] for game in games)
    assert sum(game["within_t60_plus_minus_5_minutes"] for game in games) == 4
    assert sum(game["main_detail_moneyline_exact_match"] for game in games) == 19
    assert all(game["snapshot_count"] > 0 for game in games)
    assert all(game["closest_batch_minutes_before_tip"] > 0 for game in games)
    assert all(game["t60_absolute_error_minutes"] >= 0 for game in games)
    tests += 9

    qualification = report["qualification"]
    assert qualification["official_match_identity_repaired"] is True
    assert qualification["official_home_away_repaired_for_pilot"] is True
    assert qualification["official_published_tipoff_repaired_for_pilot"] is True
    assert qualification["provider_origin_quote_time_verified"] is False
    assert qualification["quote_level_exact_observed_at_verified"] is False
    assert qualification["strict_t60_qualified"] is False
    assert qualification["point_in_time_qualified"] is False
    assert qualification["historical_backfill_qualified"] is False
    assert qualification["formal_history_write_authorized"] is False
    assert qualification["g1_2_0_real_input_qualified"] is False
    assert qualification["market_backtest_unlocked"] is False
    assert qualification["clv_ev_roi_unlocked"] is False
    assert qualification["betting_edge_claim_allowed"] is False
    assert qualification["formal_stake"] == 0
    tests += 14

    assert report["decision"] == (
        "OFFICIAL_SCHEDULE_ALIGNMENT_REPAIRS_GAME_ID_HOME_AWAY_AND_PUBLISHED_TIPOFF_BUT_NOT_QUOTE_TIME"
    )
    assert report["next_unique_mainline"] == (
        "EXPAND_KAGGLE_OFFICIAL_SCHEDULE_ALIGNMENT_TO_FULL_2025_26_REGULAR_SEASON_DIAGNOSTIC_ONLY"
    )
    tests += 2

    assert tests == 45
    qa = {
        "schema_version": 1,
        "formal_state": "KAGGLE_OFFICIAL_SCHEDULE_ALIGNMENT_PILOT_RECORD_VALID",
        "pilot_games": 20,
        "official_games_uniquely_matched": 20,
        "home_away_orientation_verified": 20,
        "closest_t60_within_plus_minus_5_minutes": 4,
        "strict_t60_qualified": False,
        "point_in_time_qualified": False,
        "historical_backfill_qualified": False,
        "market_metrics_executed": False,
        "formal_stake": 0,
        "contract_tests": tests,
        "next_unique_mainline": report["next_unique_mainline"],
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
