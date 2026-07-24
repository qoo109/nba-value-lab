#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "data" / "public" / "odds-alignment-summary-2025-26-v1.json"
HTML = ROOT / "odds-alignment.html"
JS = ROOT / "js" / "v4-odds-alignment-public.js"
DOC = ROOT / "docs" / "public-private-odds-usage-v1.md"
BUILDER = ROOT / "scripts" / "build_public_odds_alignment_web_v1.py"
QUERY = ROOT / "scripts" / "query_private_aligned_odds_v1.py"

FORBIDDEN_PUBLIC_TOKENS = (
    "team1_moneyline",
    "team2_moneyline",
    "team1_spread_odds",
    "team2_spread_odds",
    "over_total_odds",
    "under_total_odds",
    "game_link",
    "source_event_id",
    "pinnacle.com",
    "collector_batch_timestamp_utc_assumed",
)


def recursive_keys(value: Any) -> list[str]:
    keys: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            keys.append(str(key))
            keys.extend(recursive_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.extend(recursive_keys(child))
    return keys


def main() -> int:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    html = HTML.read_text(encoding="utf-8")
    js = JS.read_text(encoding="utf-8")
    doc = DOC.read_text(encoding="utf-8")
    builder = BUILDER.read_text(encoding="utf-8")
    query = QUERY.read_text(encoding="utf-8")
    tests = 0

    def check(condition: bool, message: str) -> None:
        nonlocal tests
        assert condition, message
        tests += 1

    check(summary["formal_state"] == "PUBLIC_SAFE_ODDS_ALIGNMENT_METADATA_VALID", "public state")
    check(summary["scope"] == "PUBLIC_METADATA_ONLY_NO_PRICES", "public scope")
    check(summary["season"] == "2025-26", "season")
    check(summary["usage"]["website_display_allowed"] is True, "website allowed")
    check(summary["usage"]["model_input_allowed"] is False, "public model input blocked")
    check(summary["usage"]["market_backtest_allowed"] is False, "backtest blocked")
    check(summary["usage"]["betting_edge_claim_allowed"] is False, "edge claim blocked")
    check(summary["summary"]["regular_season_events_matched"] == 1112, "regular events")
    check(summary["summary"]["regular_events_with_pretip_batch_candidate"] == 1111, "pretip events")
    check(summary["summary"]["regular_events_without_pretip_batch_candidate"] == 1, "no pretip event")
    check(summary["summary"]["t60_candidate_counts"] == {"5": 315, "15": 497, "30": 616, "60": 699}, "T60 bands")
    check(abs(summary["summary"]["median_t60_batch_error_minutes"] - 23.516666666666666) < 1e-12, "median error")
    check(summary["summary"]["provider_origin_quote_time_verified"] is False, "provider time lock")
    check(summary["summary"]["strict_t60_qualified"] is False, "T60 lock")
    check(summary["summary"]["formal_stake"] == 0, "stake lock")
    check(summary["public_event_export"]["status"] == "AGGREGATE_ONLY", "aggregate only")
    check(summary["public_event_export"]["per_event_rows_public"] is False, "no public event rows")
    check(summary["private_odds_access"]["method"] == "LOCAL_PRIVATE_CSV_QUERY", "private access")
    check(summary["private_odds_access"]["utility"] == "scripts/query_private_aligned_odds_v1.py", "query utility")

    rendered = json.dumps(summary, ensure_ascii=False).lower()
    for token in FORBIDDEN_PUBLIC_TOKENS:
        check(token.lower() not in rendered, f"forbidden public token: {token}")
    check("price" not in {key.lower() for key in recursive_keys(summary)}, "no public price key")
    check("odds" not in {key.lower() for key in recursive_keys(summary)}, "no public odds key")

    check("data/public/odds-alignment-summary-2025-26-v1.json" in js, "JS data path")
    check("PUBLIC_SAFE_ODDS_ALIGNMENT_METADATA_VALID" in js, "JS state guard")
    check("批次候選，非精確報價時間" in js, "JS uncertainty warning")
    check("./js/v4-odds-alignment-public.js" in html, "HTML JS link")
    check("完整逐筆賠率保留在私人本地資料層" in html, "HTML private boundary")
    check("本頁不構成投注建議" in html, "HTML disclaimer")

    check("PRIVATE_DIAGNOSTIC_ONLY" in query, "private query scope")
    check('"strict_t60_qualified": False' in query, "query T60 lock")
    check('"market_backtest_allowed": False' in query, "query backtest lock")
    check("not an exact provider-origin T-60 quote" in query, "query warning")
    check("Run locally" in builder, "builder local-only")
    check("Do not upload the private input CSV files" in builder, "builder private boundary")
    check("Market Backtest: locked" in doc, "doc backtest lock")
    check("Formal Stake: 0" in doc, "doc stake lock")

    headers = [
        "status", "official_schedule_row_id", "official_game_id",
        "official_away_team", "official_home_team", "scheduled_tipoff_utc",
        "timestamp", "batch_pre_tip_by_assumed_utc",
        "batch_minutes_before_published_tipoff",
        "team1_moneyline", "team2_moneyline", "team1_spread",
        "team1_spread_odds", "team2_spread", "team2_spread_odds",
        "over_total", "over_total_odds", "under_total", "under_total_odds",
    ]
    synthetic_rows = [
        {
            "status": "MATCHED_HIGH_CONFIDENCE_REGULAR_SEASON",
            "official_schedule_row_id": "pdf-001",
            "official_game_id": "0022500001",
            "official_away_team": "Away Team",
            "official_home_team": "Home Team",
            "scheduled_tipoff_utc": "2025-10-21T23:30:00+00:00",
            "timestamp": "2025-10-21T22:32:00+00:00",
            "batch_pre_tip_by_assumed_utc": "true",
            "batch_minutes_before_published_tipoff": "58",
            "team1_moneyline": "1.91",
            "team2_moneyline": "2.01",
        },
        {
            "status": "MATCHED_HIGH_CONFIDENCE_REGULAR_SEASON",
            "official_schedule_row_id": "pdf-001",
            "official_game_id": "0022500001",
            "official_away_team": "Away Team",
            "official_home_team": "Home Team",
            "scheduled_tipoff_utc": "2025-10-21T23:30:00+00:00",
            "timestamp": "2025-10-21T22:00:00+00:00",
            "batch_pre_tip_by_assumed_utc": "true",
            "batch_minutes_before_published_tipoff": "90",
            "team1_moneyline": "1.95",
            "team2_moneyline": "1.97",
        },
    ]
    with tempfile.TemporaryDirectory() as directory:
        private_csv = Path(directory) / "private.csv"
        output_json = Path(directory) / "selected.json"
        with private_csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers)
            writer.writeheader()
            for row in synthetic_rows:
                writer.writerow(row)
        subprocess.run(
            [
                sys.executable,
                str(QUERY),
                "--main-csv", str(private_csv),
                "--official-schedule-row-id", "pdf-001",
                "--target-minutes-before-tip", "60",
                "--output", str(output_json),
            ],
            check=True,
        )
        selected = json.loads(output_json.read_text(encoding="utf-8"))
        check(selected["formal_state"] == "PRIVATE_DIAGNOSTIC_ODDS_BATCH_SELECTED", "query state")
        check(selected["selected_batch"]["minutes_before_published_tipoff"] == 58.0, "nearest batch")
        check(selected["selected_batch"]["absolute_target_error_minutes"] == 2.0, "target error")
        check(selected["prices"]["team1_moneyline"] == 1.91, "price read privately")
        check(selected["qualification"]["strict_t60_qualified"] is False, "selected T60 lock")
        check(selected["qualification"]["market_backtest_allowed"] is False, "selected backtest lock")
        check(selected["qualification"]["formal_stake"] == 0, "selected stake")

    qa = {
        "schema_version": 1,
        "formal_state": "PUBLIC_ODDS_ALIGNMENT_WEB_EXPORT_VALID",
        "public_scope": "AGGREGATE_ONLY_NO_PRICES",
        "website_summary_valid": True,
        "private_query_utility_valid": True,
        "price_fields_in_public_export": 0,
        "quote_rows_in_public_export": 0,
        "provider_origin_quote_time_verified": False,
        "strict_t60_qualified": False,
        "market_backtest_unlocked": False,
        "contract_tests": tests,
        "formal_stake": 0,
    }
    output = ROOT / "artifacts" / "public-odds-alignment-web-export-validation-v1.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
