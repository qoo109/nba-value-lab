#!/usr/bin/env python3
"""Build a public-safe web export from private aligned odds files.

The output intentionally excludes prices, Pinnacle links, source event IDs,
quote rows and exact collector timestamps. It publishes only official schedule
alignment metadata and aggregate batch-time diagnostics.

Run locally. Do not upload the private input CSV files to a public repository.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

REGULAR_STATUSES = {
    "MATCHED_HIGH_CONFIDENCE_REGULAR_SEASON",
    "MATCHED_SCHEDULE_ADJUSTED",
    "MATCHED_NEUTRAL_SITE_REGULAR_SEASON",
}
FORBIDDEN_PUBLIC_KEYS = {
    "event_id",
    "game_link",
    "team1_moneyline",
    "team2_moneyline",
    "team1_spread",
    "team1_spread_odds",
    "team2_spread",
    "team2_spread_odds",
    "over_total",
    "over_total_odds",
    "under_total",
    "under_total_odds",
    "odds",
    "price",
    "selection",
    "market",
    "source_url",
    "source_payload_sha256",
    "collector_batch_timestamp_utc_assumed",
    "timestamp",
}


def as_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def as_float(value: Any) -> float | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def has_value(row: dict[str, str], fields: tuple[str, ...]) -> bool:
    return any(str(row.get(field, "")).strip() not in {"", "nan", "None"} for field in fields)


def quality_band(error: float | None) -> str:
    if error is None:
        return "NO_PRETIP_BATCH"
    if error <= 5:
        return "WITHIN_5_MINUTES"
    if error <= 15:
        return "WITHIN_15_MINUTES"
    if error <= 30:
        return "WITHIN_30_MINUTES"
    if error <= 60:
        return "WITHIN_60_MINUTES"
    return "OVER_60_MINUTES"


def assert_public_safe(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = key.lower()
            if lowered in FORBIDDEN_PUBLIC_KEYS:
                raise ValueError(f"forbidden public field at {path}.{key}")
            assert_public_safe(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            assert_public_safe(child, f"{path}[{index}]")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events-csv", type=Path, required=True)
    parser.add_argument("--main-csv", type=Path, required=True)
    parser.add_argument("--summary-json", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    summary = json.loads(args.summary_json.read_text(encoding="utf-8"))
    with args.events_csv.open(newline="", encoding="utf-8-sig") as handle:
        event_rows = list(csv.DictReader(handle))

    grouped_main: dict[str, list[dict[str, str]]] = defaultdict(list)
    with args.main_csv.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            if row.get("status") in REGULAR_STATUSES:
                grouped_main[str(row.get("event_id", ""))].append(row)

    public_events: list[dict[str, Any]] = []
    for event in event_rows:
        if event.get("status") not in REGULAR_STATUSES:
            continue
        rows = grouped_main.get(str(event.get("event_id", "")), [])
        pretip = [row for row in rows if as_bool(row.get("batch_pre_tip_by_assumed_utc"))]
        nearest = None
        if pretip:
            nearest = min(
                pretip,
                key=lambda row: as_float(row.get("t60_absolute_error_minutes"))
                if as_float(row.get("t60_absolute_error_minutes")) is not None
                else float("inf"),
            )
        error = as_float(nearest.get("t60_absolute_error_minutes")) if nearest else None
        minutes = as_float(nearest.get("batch_minutes_before_published_tipoff")) if nearest else None
        official_game_id = str(event.get("official_game_id", "")).strip()
        if official_game_id.lower() in {"", "nan", "none"}:
            official_game_id = None

        public_events.append(
            {
                "public_event_key": event["official_schedule_row_id"],
                "official_game_id": official_game_id,
                "away_team": event["official_away_team"],
                "home_team": event["official_home_team"],
                "scheduled_tipoff_utc": event["scheduled_tipoff_utc"],
                "alignment_status": event["status"],
                "alignment_provenance": event["alignment_provenance"],
                "venue_relation": event["venue_relation"],
                "schedule_subject_to_change": as_bool(event["schedule_subject_to_change"]),
                "snapshot_count": int(float(event["snapshot_count"])),
                "pretip_batch_count_assumed_utc": len(pretip),
                "at_or_post_tip_batch_count_assumed_utc": len(rows) - len(pretip),
                "closest_t60_batch_minutes_before_tip": round(minutes, 3) if minutes is not None else None,
                "closest_t60_batch_error_minutes": round(error, 3) if error is not None else None,
                "t60_batch_quality_band": quality_band(error),
                "markets_present": {
                    "moneyline": any(has_value(row, ("team1_moneyline", "team2_moneyline")) for row in rows),
                    "spread": any(
                        has_value(
                            row,
                            (
                                "team1_spread",
                                "team1_spread_odds",
                                "team2_spread",
                                "team2_spread_odds",
                            ),
                        )
                        for row in rows
                    ),
                    "total": any(
                        has_value(
                            row,
                            ("over_total", "over_total_odds", "under_total", "under_total_odds"),
                        )
                        for row in rows
                    ),
                },
                "provider_origin_quote_time_verified": False,
                "quote_level_exact_observed_at_verified": False,
                "strict_t60_qualified": False,
                "public_price_fields_present": False,
                "private_odds_available_locally": True,
            }
        )

    public_events.sort(key=lambda row: (row["scheduled_tipoff_utc"], row["public_event_key"]))
    summary_output = {
        "schema_version": "nba-value-lab-public-odds-alignment-2025-26-v1",
        "generated_at_utc": summary["generated_at_utc"],
        "formal_state": "PUBLIC_SAFE_ODDS_ALIGNMENT_METADATA_VALID",
        "scope": "PUBLIC_METADATA_ONLY_NO_PRICES",
        "season": "2025-26",
        "source_alignment_state": summary["formal_state"],
        "usage": {
            "website_display_allowed": True,
            "model_input_allowed": False,
            "market_backtest_allowed": False,
            "betting_edge_claim_allowed": False,
            "reason": (
                "Official schedule alignment and batch-time diagnostics only; "
                "no prices and no verified quote-level observed_at."
            ),
        },
        "summary": {
            "reconciled_schedule_rows": summary["reconciled_schedule_rows"],
            "source_events_classified": summary["source_events_classified"],
            "regular_season_events_matched": summary["regular_season_events_matched"],
            "public_regular_events": len(public_events),
            "classification_counts": summary["classification_counts"],
            "regular_events_with_pretip_batch_candidate": summary[
                "regular_events_with_pretip_batch_candidate"
            ],
            "regular_events_without_pretip_batch_candidate": summary[
                "regular_events_without_pretip_batch_candidate"
            ],
            "t60_candidate_counts": summary["t60_candidate_counts"],
            "median_t60_batch_error_minutes": summary["median_t60_batch_error_minutes"],
            "provider_origin_quote_time_verified": False,
            "strict_t60_qualified": False,
            "formal_stake": 0,
        },
        "events_url": "./odds-alignment-events-2025-26-v1.json",
    }
    events_output = {
        "schema_version": "nba-value-lab-public-odds-alignment-events-2025-26-v1",
        "generated_at_utc": summary["generated_at_utc"],
        "season": "2025-26",
        "scope": "PUBLIC_METADATA_ONLY_NO_PRICES",
        "event_count": len(public_events),
        "events": public_events,
    }

    assert_public_safe(summary_output)
    assert_public_safe(events_output)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "odds-alignment-summary-2025-26-v1.json").write_text(
        json.dumps(summary_output, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "odds-alignment-events-2025-26-v1.json").write_text(
        json.dumps(events_output, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "formal_state": "PUBLIC_SAFE_ODDS_ALIGNMENT_METADATA_VALID",
                "public_events": len(public_events),
                "price_fields_emitted": 0,
                "quote_rows_emitted": 0,
                "strict_t60_qualified": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
