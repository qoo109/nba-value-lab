#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGGREGATE = ROOT / "data" / "research" / "kaggle-official-schedule-full-alignment-aggregate-v1.json"
STATUS = ROOT / "data" / "research" / "no-cost-timestamped-odds-source-qualification-current-status-v16.json"
DOC = ROOT / "docs" / "kaggle-official-schedule-full-alignment-v1.md"
HANDOFF = ROOT / "docs" / "handoffs" / "nba_value_lab_handoff_2026-07-24_kaggle_official_schedule_full_alignment.md"
ALIGNER = ROOT / "scripts" / "align_kaggle_odds_to_official_schedule_2025_26_v1.py"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts" / "kaggle-official-schedule-full-alignment-validation-v1.json",
    )
    args = parser.parse_args()

    a = json.loads(AGGREGATE.read_text(encoding="utf-8"))
    s = json.loads(STATUS.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")
    handoff = HANDOFF.read_text(encoding="utf-8")
    aligner = ALIGNER.read_text(encoding="utf-8")
    tests = 0

    def check(condition: bool, message: str) -> None:
        nonlocal tests
        assert condition, message
        tests += 1

    check(a["formal_state"] == "KAGGLE_OFFICIAL_SCHEDULE_FULL_ALIGNMENT_DIAGNOSTIC_VALID", "aggregate state")
    check(a["recording_pr"] == 174, "recording PR")
    check(a["private_input"]["archive_sha256"] == "sha256:36685fa53deaba112f93515fefffb971b02613f32f2f24d5a22dd0088863d419", "archive hash")
    check(a["private_input"]["raw_archive_committed"] is False, "archive private")
    check(a["private_input"]["raw_quote_rows_committed"] is False, "quotes private")
    check(a["private_input"]["main_rows"] == 8153, "main rows")
    check(a["private_input"]["detailed_rows"] == 149752, "detail rows")
    check(a["private_input"]["source_events"] == 1199, "source events")

    o = a["official_schedule_evidence"]
    check(o["schedule_release_rows"] == 1200, "release rows")
    check(o["schedule_release_team_appearances_each"] == 80, "team appearances")
    check(o["schedule_release_neutral_site_rows"] == 3, "neutral rows")
    check(o["schedule_release_subject_to_change"] is True, "change control")
    check(o["schedule_release_payload_sha256"] == "sha256:98a06493d0a107cc410853ad230e67d48858777a2baf76ac77d089cbeaf2435d", "PDF hash")
    check(o["schedule_artifact_id"] == 8587613624, "schedule artifact")
    check(o["liveData_subset_requested"] == 38, "subset requested")
    check(o["liveData_subset_returned"] == 38, "subset returned")
    check(o["liveData_subset_artifact_id"] == 8587902294, "subset artifact")
    check(o["cup_determined_regular_season_games_added"] == 30, "Cup games")
    check(o["known_schedule_date_adjustments_reconciled"] == 4, "date adjustments")
    check(o["known_schedule_time_adjustments_reconciled"] == 4, "time adjustments")
    check(o["reconciled_schedule_rows"] == 1230, "schedule rows")
    check(o["reconciled_schedule_unique_row_ids"] == 1230, "schedule IDs")
    check(o["duplicate_matchup_tipoff_rows"] == 0, "schedule duplicates")
    check(sum(o["schedule_provenance_row_counts"].values()) == 1230, "schedule provenance sum")
    check(o["schedule_provenance_row_counts"]["OFFICIAL_SCHEDULE_RELEASE_PDF"] == 1192, "release retained")

    e = a["event_alignment"]
    check(e["source_events_classified"] == 1199, "classified events")
    check(e["unmatched_or_ambiguous"] == 0, "no unmatched")
    check(e["regular_season_events_matched"] == 1112, "regular matches")
    check(sum(e["classification_counts"].values()) == 1199, "classification sum")
    check(e["classification_counts"]["MATCHED_HIGH_CONFIDENCE_REGULAR_SEASON"] == 1102, "high confidence")
    check(e["classification_counts"]["MATCHED_SCHEDULE_ADJUSTED"] == 8, "adjusted")
    check(e["classification_counts"]["MATCHED_NEUTRAL_SITE_REGULAR_SEASON"] == 2, "neutral matched")
    check(e["classification_counts"]["EXCLUDED_POSTSEASON_OR_PLAY_IN"] == 83, "postseason")
    check(e["classification_counts"]["EXCLUDED_ALL_STAR"] == 3, "all star")
    check(e["classification_counts"]["EXCLUDED_NBA_CUP_CHAMPIONSHIP"] == 1, "Cup final")
    check(sum(e["regular_event_provenance_counts"].values()) == 1112, "regular provenance sum")
    check(e["one_to_one_regular_event_schedule_matches"] == 1112, "one-to-one matches")
    check(e["regular_events_with_published_tipoff"] == 1112, "tipoff coverage")
    check(e["regular_events_with_stable_official_schedule_row_id"] == 1112, "stable IDs")
    check(e["regular_events_with_true_official_nba_game_id"] == 38, "true NBA IDs")
    check(e["regular_events_using_stable_pdf_schedule_row_id"] == 1074, "PDF IDs")
    check(abs(e["archive_regular_schedule_coverage_pct"] - 90.40650406504065) < 1e-12, "coverage")

    r = a["row_enrichment"]
    check(r["regular_main_rows_enriched"] == 7713, "regular main")
    check(r["regular_detailed_rows_enriched"] == 144034, "regular detail")
    check(r["detailed_rows_mapped_to_main_event"] == 149752, "detail mapped")
    check(r["detailed_rows_unmapped"] == 0, "detail unmapped")
    check(sum(r["main_row_classification_counts"].values()) == 8153, "main classification sum")
    check(sum(r["detailed_row_classification_counts"].values()) == 149752, "detail classification sum")

    t = a["batch_time_diagnostics"]
    check(t["source_timestamp_preserved"] is True, "timestamp preserved")
    check(t["regular_events_with_pretip_batch_candidate"] == 1111, "pre-tip candidates")
    check(t["regular_events_without_pretip_batch_candidate"] == 1, "no pre-tip candidate")
    check(t["regular_events_with_at_or_post_tip_batch"] == 28, "post-tip events")
    check(t["regular_main_rows_at_or_post_tip"] == 34, "post-tip rows")
    check(t["closest_batch_candidate_within_t60_plus_minus_5_minutes"] == 315, "T60 5")
    check(t["closest_batch_candidate_within_t60_plus_minus_15_minutes"] == 497, "T60 15")
    check(t["closest_batch_candidate_within_t60_plus_minus_30_minutes"] == 616, "T60 30")
    check(t["closest_batch_candidate_within_t60_plus_minus_60_minutes"] == 699, "T60 60")
    check(abs(t["median_t60_batch_absolute_error_minutes"] - 23.516666666666666) < 1e-12, "median T60")
    check(t["provider_origin_quote_time_verified"] is False, "provider time lock")
    check(t["quote_level_exact_observed_at_verified"] is False, "exact observed lock")
    check(t["quote_strictly_pre_tip_verified"] is False, "pre-tip lock")
    check(t["strict_t60_qualified"] is False, "T60 lock")

    q = a["qualification_locks"]
    check(q["point_in_time_qualified"] is False, "PIT lock")
    check(q["historical_backfill_qualified"] is False, "backfill lock")
    check(q["formal_history_write_authorized"] is False, "history lock")
    check(q["g1_2_0_real_input_qualified"] is False, "G1 lock")
    check(q["market_backtest_unlocked"] is False, "market backtest lock")
    check(q["clv_ev_roi_drawdown_unlocked"] is False, "metric lock")
    check(q["betting_edge_claim_allowed"] is False, "edge claim lock")
    check(q["formal_stake"] == 0, "stake lock")

    check(s["formal_state"] == a["formal_state"], "status state")
    check(s["recording_pr"] == 174, "status PR")
    check(s["full_alignment"]["unmatched_or_ambiguous"] == 0, "status unmatched")
    check(s["formal_stake"] == 0, "status stake")
    check(s["next_unique_mainline"] == a["next_unique_mainline"], "status mainline")
    check("quote time unresolved" in doc.lower(), "documentation uncertainty")
    check("UNMATCHED_OR_AMBIGUOUS: 0" in handoff, "handoff classification")
    check("urllib" not in aligner and "requests" not in aligner, "aligner offline")
    check("strict_t60_qualified\":False" in aligner, "aligner T60 lock")
    check("PRIVATE_DIAGNOSTIC_ONLY" in aligner, "aligner scope")

    expected_tests = 80
    check(tests == expected_tests, f"expected {expected_tests} pre-final tests, got {tests}")

    qa = {
        "schema_version": 1,
        "formal_state": "KAGGLE_OFFICIAL_SCHEDULE_FULL_ALIGNMENT_RECORD_VALID",
        "aggregate_only": True,
        "private_archive_committed": False,
        "raw_quote_rows_committed": False,
        "official_schedule_rows": 1230,
        "source_events_classified": 1199,
        "regular_season_events_matched": 1112,
        "unmatched_or_ambiguous": 0,
        "main_rows": 8153,
        "detailed_rows": 149752,
        "regular_main_rows_enriched": 7713,
        "regular_detailed_rows_enriched": 144034,
        "regular_events_with_pretip_batch_candidate": 1111,
        "regular_events_without_pretip_batch_candidate": 1,
        "t60_batch_candidates_within_5m": 315,
        "t60_batch_candidates_within_15m": 497,
        "t60_batch_candidates_within_30m": 616,
        "t60_batch_candidates_within_60m": 699,
        "median_t60_batch_absolute_error_minutes": 23.516666666666666,
        "provider_origin_quote_time_verified": False,
        "strict_t60_qualified": False,
        "point_in_time_qualified": False,
        "historical_backfill_qualified": False,
        "market_metrics_executed": False,
        "contract_tests": tests,
        "formal_stake": 0,
        "decision": a["decision"],
        "next_unique_mainline": a["next_unique_mainline"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
