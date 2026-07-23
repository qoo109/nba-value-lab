#!/usr/bin/env python3
"""Validate the aggregate-only ZachHT/Pinnacle archive audit record."""

from __future__ import annotations

import json
from pathlib import Path

AUDIT = Path("data/research/kaggle-zachht-pinnacle-basketball-odds-archive-audit-v1.json")


def require(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def main() -> None:
    payload = json.loads(AUDIT.read_text(encoding="utf-8"))

    require(
        payload["schema_version"]
        == "kaggle-zachht-pinnacle-basketball-odds-archive-audit-v1",
        "schema mismatch",
    )
    require(
        payload["formal_state"]
        == "KAGGLE_ZACHHT_PINNACLE_BASKETBALL_ODDS_ARCHIVE_RESEARCH_BLOCKED",
        "archive was promoted",
    )

    archive = payload["source_archive"]
    require(archive["user_supplied"] is True, "archive identity changed")
    require(archive["retained_in_repository"] is False, "raw archive retained")
    require(archive["zip_size_bytes"] == 7477620, "zip size mismatch")
    require(
        archive["zip_sha256"]
        == "sha256:36685fa53deaba112f93515fefffb971b02613f32f2f24d5a22dd0088863d419",
        "zip digest mismatch",
    )
    require(archive["csv_file_count"] == 595, "CSV count mismatch")

    evidence = payload["upstream_and_collection_evidence"]
    require(evidence["upstream_bookmaker"] == "Pinnacle", "upstream bookmaker mismatch")
    require(evidence["notebook_generates_timestamp_with_datetime_utcnow"] is True, "UTC evidence removed")
    require(evidence["notebook_uses_undetected_chromedriver"] is True, "automation-evasion evidence removed")
    require(evidence["notebook_masks_navigator_webdriver"] is True, "webdriver masking evidence removed")
    require(evidence["pinnacle_terms_scraping_allowed"] is False, "scraping incorrectly allowed")
    require(evidence["pinnacle_terms_automated_access_allowed"] is False, "automated access incorrectly allowed")
    require(evidence["kaggle_license_overrides_upstream_rights"] is False, "upstream-rights gate removed")

    main_lines = payload["nba_regular_main_lines"]
    require(main_lines["rows"] == 8153, "main-line row count mismatch")
    require(main_lines["unique_pinnacle_event_urls"] == 1199, "event count mismatch")
    require(main_lines["unique_scrape_timestamps"] == 1979, "timestamp count mismatch")
    require(main_lines["complete_two_sided_moneyline_rows"] == 8109, "moneyline count mismatch")
    require(main_lines["moneyline_missing_rows"] == 44, "missing count mismatch")
    require(main_lines["full_row_duplicates"] == 0, "full duplicate count mismatch")
    require(main_lines["repeated_identical_snapshots_ignoring_timestamp"] == 3181, "repeat count mismatch")

    detailed = payload["nba_regular_detailed_odds"]
    require(detailed["rows"] == 149752, "detailed row count mismatch")
    require(detailed["moneyline_rows"] == 16214, "detailed moneyline count mismatch")
    require(detailed["complete_two_sided_moneyline_snapshots"] == 8107, "detailed snapshot count mismatch")
    require(detailed["rows_joining_uniquely_to_main_lines_by_matchup_and_timestamp"] == 149752, "join mismatch")
    require(detailed["bookmaker_column_present"] is False, "bookmaker column invented")
    require(detailed["scheduled_tipoff_column_present"] is False, "tipoff column invented")

    blockers = payload["blocking_findings"]
    require(blockers["upstream_terms_prohibit_scraping_and_automated_access"] is True, "terms blocker removed")
    require(blockers["collection_uses_automation_evasion_techniques"] is True, "evasion blocker removed")
    require(blockers["scheduled_tipoff_not_stored"] is True, "tipoff blocker removed")
    require(blockers["strict_pre_tip_and_t_minus_validation_possible_from_archive_alone"] is False, "PIT gate bypassed")
    require(blockers["overlap_with_frozen_gold_2019_20_through_2023_24"] is False, "Gold overlap invented")
    require(blockers["historical_backfill_for_current_market_backtest_possible"] is False, "backfill incorrectly enabled")

    decision = payload["decision"]
    for key in (
        "qualified_for_historical_backfill",
        "qualified_for_point_in_time_odds_join",
        "qualified_for_market_backtest",
        "qualified_for_forward_collection",
        "raw_or_quote_level_rows_may_be_committed",
        "raw_or_quote_level_rows_may_be_uploaded_as_public_artifact",
        "market_metrics_allowed",
        "clv_ev_roi_allowed",
        "betting_edge_claim_allowed",
    ):
        require(decision[key] is False, f"forbidden permission enabled: {key}")
    require(decision["formal_stake"] == 0, "Stake changed")

    print(
        json.dumps(
            {
                "formal_state": payload["formal_state"],
                "zip_sha256": archive["zip_sha256"],
                "nba_main_rows": main_lines["rows"],
                "unique_events": main_lines["unique_pinnacle_event_urls"],
                "complete_moneyline_rows": main_lines["complete_two_sided_moneyline_rows"],
                "qualified_for_market_backtest": False,
                "formal_stake": 0,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
