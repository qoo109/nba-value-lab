#!/usr/bin/env python3
"""Query the private officially-aligned NBA odds CSV.

This utility is intentionally local-only. It reads the private main-lines CSV,
selects one game, then returns the nearest available *pre-tip collector batch*
to a requested target such as T-60. The collector timestamp is not a verified
provider-origin quote time and must never be relabeled as exact observed_at.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

REGULAR_STATUSES = {
    "MATCHED_HIGH_CONFIDENCE_REGULAR_SEASON",
    "MATCHED_SCHEDULE_ADJUSTED",
    "MATCHED_NEUTRAL_SITE_REGULAR_SEASON",
}
PRICE_FIELDS = (
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
)


def clean(value: Any) -> str | None:
    text = "" if value is None else str(value).strip()
    return None if text.lower() in {"", "nan", "none", "null"} else text


def number(value: Any) -> float | None:
    text = clean(value)
    if text is None:
        return None
    try:
        result = float(text)
    except ValueError:
        return None
    return result if math.isfinite(result) else None


def boolean(value: Any) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def identify_game(rows: list[dict[str, str]], args: argparse.Namespace) -> list[dict[str, str]]:
    candidates = [row for row in rows if row.get("status") in REGULAR_STATUSES]
    if args.official_schedule_row_id:
        candidates = [
            row
            for row in candidates
            if clean(row.get("official_schedule_row_id")) == args.official_schedule_row_id
        ]
    elif args.official_game_id:
        candidates = [
            row
            for row in candidates
            if clean(row.get("official_game_id")) == args.official_game_id
        ]
    else:
        away = args.away_team.casefold()
        home = args.home_team.casefold()
        candidates = [
            row
            for row in candidates
            if (clean(row.get("official_away_team")) or "").casefold() == away
            and (clean(row.get("official_home_team")) or "").casefold() == home
        ]
        if args.scheduled_tipoff_utc:
            candidates = [
                row
                for row in candidates
                if clean(row.get("scheduled_tipoff_utc")) == args.scheduled_tipoff_utc
            ]

    game_keys = {
        clean(row.get("official_schedule_row_id"))
        or clean(row.get("official_game_id"))
        or clean(row.get("event_id"))
        for row in candidates
    }
    game_keys.discard(None)
    if not candidates:
        raise SystemExit("No matching regular-season game found in the private aligned CSV.")
    if len(game_keys) != 1:
        raise SystemExit(
            "Selection is ambiguous. Add --scheduled-tipoff-utc or use "
            "--official-schedule-row-id / --official-game-id."
        )
    return candidates


def select_batch(rows: list[dict[str, str]], target: float) -> dict[str, str]:
    pretip = [
        row
        for row in rows
        if boolean(row.get("batch_pre_tip_by_assumed_utc"))
        and number(row.get("batch_minutes_before_published_tipoff")) is not None
    ]
    if not pretip:
        raise SystemExit("The selected game has no pre-tip collector batch candidate.")
    return min(
        pretip,
        key=lambda row: abs(
            number(row.get("batch_minutes_before_published_tipoff")) - target
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--main-csv", type=Path, required=True)
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--official-schedule-row-id")
    selector.add_argument("--official-game-id")
    selector.add_argument("--away-team")
    parser.add_argument("--home-team")
    parser.add_argument("--scheduled-tipoff-utc")
    parser.add_argument("--target-minutes-before-tip", type=float, default=60.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.away_team and not args.home_team:
        parser.error("--away-team requires --home-team")
    if args.home_team and not args.away_team:
        parser.error("--home-team requires --away-team")
    if args.target_minutes_before_tip < 0:
        parser.error("--target-minutes-before-tip must be non-negative")

    rows = identify_game(load_rows(args.main_csv), args)
    selected = select_batch(rows, args.target_minutes_before_tip)
    minutes = number(selected.get("batch_minutes_before_published_tipoff"))
    error = abs(minutes - args.target_minutes_before_tip) if minutes is not None else None
    prices = {field: number(selected.get(field)) for field in PRICE_FIELDS}

    output = {
        "schema_version": "private-aligned-odds-query-v1",
        "formal_state": "PRIVATE_DIAGNOSTIC_ODDS_BATCH_SELECTED",
        "scope": "PRIVATE_DIAGNOSTIC_ONLY",
        "game": {
            "official_schedule_row_id": clean(selected.get("official_schedule_row_id")),
            "official_game_id": clean(selected.get("official_game_id")),
            "away_team": clean(selected.get("official_away_team")),
            "home_team": clean(selected.get("official_home_team")),
            "scheduled_tipoff_utc": clean(selected.get("scheduled_tipoff_utc")),
            "alignment_status": clean(selected.get("status")),
        },
        "selected_batch": {
            "collector_batch_timestamp_utc_assumed": clean(selected.get("timestamp")),
            "minutes_before_published_tipoff": minutes,
            "requested_target_minutes_before_tip": args.target_minutes_before_tip,
            "absolute_target_error_minutes": error,
            "pre_tip_by_assumed_utc": True,
        },
        "prices": prices,
        "qualification": {
            "provider_origin_quote_time_verified": False,
            "quote_level_exact_observed_at_verified": False,
            "strict_t60_qualified": False,
            "point_in_time_qualified": False,
            "market_backtest_allowed": False,
            "betting_edge_claim_allowed": False,
            "formal_stake": 0,
        },
        "warning": (
            "The selected row is the nearest available pre-tip collector batch, "
            "not an exact provider-origin T-60 quote. Keep model probabilities "
            "separate from market prices and use this only for exploratory sensitivity analysis."
        ),
    }
    rendered = json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
