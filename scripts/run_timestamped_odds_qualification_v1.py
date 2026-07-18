#!/usr/bin/env python3
"""Hardened offline runner for Timestamped Odds source qualification v1.

This module contains no HTTP client and never reads THE_ODDS_API_KEY. It reuses
the frozen manifest builder from ``qualify_timestamped_odds_v1`` while enforcing
strict event/tip-off identity, bookmaker update timestamps, quota provenance and
coverage-only bookmaker qualification.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

import qualify_timestamped_odds_v1 as base
from import_closing_odds_archive import team_abbr

VERSION = "timestamped-odds-qualification-runner-v1"
MARKET_KEY = "h2h"


def strict_event_match(
    request: dict[str, Any],
    events: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Match exact home, away and scheduled tip-off without fuzzy fallback."""
    expected_home = str(request["home_team_abbr"])
    expected_away = str(request["away_team_abbr"])
    expected_tipoff = base.parse_utc(request["scheduled_tipoff_utc"])
    exact: list[dict[str, Any]] = []
    team_only_tipoff_mismatch = 0
    reversed_home_away = 0
    unknown_team_events = 0
    invalid_commence_time = 0

    for event in events:
        try:
            home = team_abbr(event.get("home_team"))
            away = team_abbr(event.get("away_team"))
        except ValueError:
            unknown_team_events += 1
            continue

        if home == expected_away and away == expected_home:
            reversed_home_away += 1
            continue
        if home != expected_home or away != expected_away:
            continue
        try:
            event_tipoff = base.parse_utc(event.get("commence_time"))
        except (TypeError, ValueError):
            invalid_commence_time += 1
            continue
        if event_tipoff == expected_tipoff:
            exact.append(event)
        else:
            team_only_tipoff_mismatch += 1

    return (
        exact[0] if len(exact) == 1 else None,
        {
            "exact_event_candidates": len(exact),
            "team_only_tipoff_mismatches": team_only_tipoff_mismatch,
            "reversed_home_away_events": reversed_home_away,
            "unknown_team_events": unknown_team_events,
            "invalid_commence_time_events": invalid_commence_time,
            "ambiguous_event_matches": int(len(exact) > 1),
            "fuzzy_matching_used": False,
        },
    )


def normalize_bookmaker_quotes(
    request: dict[str, Any],
    event: dict[str, Any],
    provider_snapshot_at: datetime,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return valid same-book two-way h2h rows and deidentified diagnostics."""
    rows: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    tipoff = base.parse_utc(request["scheduled_tipoff_utc"])
    event_tipoff = base.parse_utc(event.get("commence_time"))
    event_id = str(event.get("id") or "").strip()
    if not event_id:
        return [], [{"bookmaker_key": "", "reason": "missing_source_event_id"}]

    seen_bookmakers: set[str] = set()
    for bookmaker in event.get("bookmakers") or []:
        bookmaker_key = str(bookmaker.get("key") or "").strip()
        if not bookmaker_key:
            diagnostics.append({"bookmaker_key": "", "reason": "blank_bookmaker_key"})
            continue
        if bookmaker_key in seen_bookmakers:
            diagnostics.append({"bookmaker_key": bookmaker_key, "reason": "duplicate_bookmaker_key"})
            continue
        seen_bookmakers.add(bookmaker_key)

        try:
            bookmaker_last_update = base.parse_utc(bookmaker.get("last_update"))
        except (TypeError, ValueError):
            diagnostics.append({"bookmaker_key": bookmaker_key, "reason": "invalid_bookmaker_last_update"})
            continue
        if bookmaker_last_update > provider_snapshot_at:
            diagnostics.append({"bookmaker_key": bookmaker_key, "reason": "bookmaker_update_after_provider_snapshot"})
            continue
        if bookmaker_last_update >= tipoff:
            diagnostics.append({"bookmaker_key": bookmaker_key, "reason": "bookmaker_update_not_pre_tip"})
            continue

        markets = [
            market
            for market in (bookmaker.get("markets") or [])
            if str(market.get("key") or "").strip() == MARKET_KEY
        ]
        if len(markets) != 1:
            diagnostics.append({
                "bookmaker_key": bookmaker_key,
                "reason": "missing_or_duplicate_h2h_market",
                "market_rows": len(markets),
            })
            continue

        outcomes: dict[str, float] = {}
        duplicate_outcomes = 0
        invalid_outcomes = 0
        for outcome in markets[0].get("outcomes") or []:
            try:
                outcome_team = team_abbr(outcome.get("name"))
            except ValueError:
                invalid_outcomes += 1
                continue
            if outcome_team in outcomes:
                duplicate_outcomes += 1
                continue
            try:
                outcomes[outcome_team] = float(outcome.get("price"))
            except (TypeError, ValueError):
                outcomes[outcome_team] = float("nan")

        home = str(request["home_team_abbr"])
        away = str(request["away_team_abbr"])
        if set(outcomes) != {home, away} or duplicate_outcomes or invalid_outcomes:
            diagnostics.append({
                "bookmaker_key": bookmaker_key,
                "reason": "invalid_two_way_outcomes",
                "outcome_teams": sorted(outcomes),
                "duplicate_outcomes": duplicate_outcomes,
                "invalid_outcomes": invalid_outcomes,
            })
            continue

        home_price = outcomes[home]
        away_price = outcomes[away]
        finite = math.isfinite(home_price) and math.isfinite(away_price)
        overround = (
            1.0 / home_price + 1.0 / away_price - 1.0
            if finite and home_price > 0 and away_price > 0
            else float("nan")
        )
        rows.append({
            "request_id": request["request_id"],
            "source_id": base.SOURCE_ID,
            "source_event_id": event_id,
            "historical_game_id": request["historical_game_id"],
            "season": request["season"],
            "snapshot_label": request["snapshot_label"],
            "requested_at_utc": request["requested_at_utc"],
            "provider_snapshot_at_utc": base.iso_utc(provider_snapshot_at),
            "scheduled_tipoff_utc": request["scheduled_tipoff_utc"],
            "event_commence_time_utc": base.iso_utc(event_tipoff),
            "bookmaker_key": bookmaker_key,
            "bookmaker_last_update_utc": base.iso_utc(bookmaker_last_update),
            "market_key": MARKET_KEY,
            "home_team_abbr": home,
            "away_team_abbr": away,
            "home_price_decimal": home_price,
            "away_price_decimal": away_price,
            "two_way_overround": overround,
            "quote_time_valid": True,
        })
    return rows, diagnostics


def parse_payload(
    policy: dict[str, Any],
    request: dict[str, Any],
    payload: dict[str, Any],
    fetched_at_utc: str,
    http_meta: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    requested_at = base.parse_utc(request["requested_at_utc"])
    tipoff = base.parse_utc(request["scheduled_tipoff_utc"])
    provider_snapshot_at = base.parse_utc(payload.get("timestamp"))
    lag_minutes, snapshot_time_valid = base.validate_snapshot_time(
        policy, requested_at, provider_snapshot_at
    )
    events = payload.get("data") if isinstance(payload.get("data"), list) else []
    event, event_qa = strict_event_match(request, events)
    quotes: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    if event is not None:
        quotes, diagnostics = normalize_bookmaker_quotes(request, event, provider_snapshot_at)

    meta = http_meta or {}
    index = {
        "request_id": request["request_id"],
        "historical_game_id": request["historical_game_id"],
        "season": request["season"],
        "snapshot_label": request["snapshot_label"],
        "requested_at_utc": request["requested_at_utc"],
        "provider_snapshot_at_utc": base.iso_utc(provider_snapshot_at),
        "snapshot_lag_minutes": lag_minutes,
        "snapshot_time_valid": int(snapshot_time_valid),
        "fetched_at_utc": base.iso_utc(base.parse_utc(fetched_at_utc)),
        "http_status": int(meta.get("http_status", 200)),
        "response_bytes": int(meta.get("response_bytes", 0)),
        "response_sha256": str(meta.get("response_sha256") or base.response_sha256(payload)),
        "x_requests_last": str(meta.get("x_requests_last", "")),
        "x_requests_used": str(meta.get("x_requests_used", "")),
        "x_requests_remaining": str(meta.get("x_requests_remaining", "")),
        "source_event_match": int(event is not None),
        "source_event_id_present": int(bool(event and str(event.get("id") or "").strip())),
        "quote_bookmakers": len(quotes),
        "future_snapshot_rows": int(provider_snapshot_at > requested_at),
        "point_in_time_violations": int(provider_snapshot_at >= tipoff),
        "opening_inferred": 0,
        "bookmaker_diagnostic_count": len(diagnostics),
        "invalid_bookmaker_timestamp_rows": sum(
            item.get("reason") in {
                "invalid_bookmaker_last_update",
                "bookmaker_update_after_provider_snapshot",
                "bookmaker_update_not_pre_tip",
            }
            for item in diagnostics
        ),
        **event_qa,
    }
    return quotes, index


def _int_header(value: Any) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = int(text)
    except ValueError:
        return None
    return parsed if parsed >= 0 else None


def aggregate_qualification(
    policy: dict[str, Any],
    manifest_rows: list[dict[str, Any]],
    quote_rows: list[dict[str, Any]],
    source_index_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Apply frozen structural gates without calculating market performance."""
    gates = policy["pilot_source_gates"]
    pilot = policy["qualification_pilot"]
    manifest_by_request = {str(row["request_id"]): row for row in manifest_rows}

    index_by_request: dict[str, dict[str, Any]] = {}
    duplicate_source_indexes = 0
    for row in source_index_rows:
        request_id = str(row.get("request_id") or "")
        if request_id in index_by_request:
            duplicate_source_indexes += 1
        index_by_request[request_id] = row

    successful_requests = sum(
        int(row.get("http_status", 0)) == 200
        and int(row.get("snapshot_time_valid", 0)) == 1
        for row in source_index_rows
    )
    request_success_rate = successful_requests / len(manifest_rows) if manifest_rows else 0.0
    unresolved_access_errors = sum(
        int(row.get("http_status", 0)) in {401, 403, 429}
        for row in source_index_rows
    )
    missing_source_index_rows = len(set(manifest_by_request) - set(index_by_request))

    mapped_games = {
        str(row["historical_game_id"])
        for row in source_index_rows
        if int(row.get("source_event_match", 0)) == 1
    }
    mapped_by_season: Counter[str] = Counter()
    game_season = {
        str(row["historical_game_id"]): str(row["season"])
        for row in manifest_rows
    }
    for game_id in mapped_games:
        mapped_by_season[game_season[game_id]] += 1

    quote_keys = [
        (str(row["request_id"]), str(row["bookmaker_key"]), str(row["market_key"]))
        for row in quote_rows
    ]
    duplicate_quote_keys = len(quote_keys) - len(set(quote_keys))

    min_price = float(gates["minimum_decimal_price"])
    max_price = float(gates["maximum_decimal_price"])
    min_overround = float(gates["minimum_two_way_overround"])
    max_overround = float(gates["maximum_two_way_overround"])
    abnormal_by_book: Counter[str] = Counter()
    for row in quote_rows:
        prices = (float(row["home_price_decimal"]), float(row["away_price_decimal"]))
        overround = float(row["two_way_overround"])
        abnormal = (
            not all(math.isfinite(value) and min_price <= value <= max_price for value in prices)
            or not math.isfinite(overround)
            or not min_overround <= overround <= max_overround
            or not bool(row.get("quote_time_valid"))
            or not str(row.get("source_event_id") or "").strip()
        )
        if abnormal:
            abnormal_by_book[str(row["bookmaker_key"])] += 1

    by_book_game: dict[tuple[str, str], set[str]] = defaultdict(set)
    by_book_game_season: dict[tuple[str, str], str] = {}
    for row in quote_rows:
        request = manifest_by_request.get(str(row["request_id"]))
        if request is None:
            continue
        key = (str(row["bookmaker_key"]), str(row["historical_game_id"]))
        by_book_game[key].add(str(row["snapshot_label"]))
        by_book_game_season[key] = str(row["season"])

    required_labels = {item["label"] for item in policy["snapshot_contract"]["required_targets"]}
    bookmaker_summary: list[dict[str, Any]] = []
    for bookmaker in sorted({key[0] for key in by_book_game}):
        book_games = [key for key in by_book_game if key[0] == bookmaker]
        t60_closing = [
            key for key in book_games
            if {"T-1h", "Closing"}.issubset(by_book_game[key])
        ]
        all_targets = [key for key in book_games if required_labels.issubset(by_book_game[key])]
        season_complete = Counter(by_book_game_season[key] for key in t60_closing)
        bookmaker_summary.append({
            "bookmaker_key": bookmaker,
            "games_with_any_quote": len(book_games),
            "complete_t60_closing_games": len(t60_closing),
            "all_target_games": len(all_targets),
            "all_target_snapshot_coverage": len(all_targets) / int(pilot["games"]),
            "minimum_per_season_complete_t60_closing": min(
                (season_complete.get(season, 0) for season in pilot["seasons"]),
                default=0,
            ),
            "abnormal_quote_rows": abnormal_by_book.get(bookmaker, 0),
        })

    qualified_books = [
        row for row in bookmaker_summary
        if row["complete_t60_closing_games"] >= int(gates["minimum_primary_bookmaker_complete_t60_closing_games"])
        and row["minimum_per_season_complete_t60_closing"] >= int(gates["minimum_primary_bookmaker_complete_t60_closing_games_each_season"])
        and row["all_target_snapshot_coverage"] >= float(gates["minimum_primary_bookmaker_all_target_snapshot_coverage"])
        and row["abnormal_quote_rows"] <= int(gates["maximum_selected_primary_bookmaker_abnormal_quote_rows"])
    ]
    qualified_books.sort(key=lambda row: (
        -row["complete_t60_closing_games"],
        -row["all_target_snapshot_coverage"],
        -row["minimum_per_season_complete_t60_closing"],
        row["bookmaker_key"],
    ))

    quota_values = [_int_header(row.get("x_requests_last")) for row in source_index_rows]
    missing_quota_headers = sum(value is None for value in quota_values)
    quota_credits_used = sum(value or 0 for value in quota_values)
    missing_hashes = sum(not str(row.get("response_sha256") or "").strip() for row in source_index_rows)
    missing_source_event_ids = sum(
        int(row.get("source_event_match", 0)) == 1
        and int(row.get("source_event_id_present", 0)) != 1
        for row in source_index_rows
    )

    source_blockers: list[str] = []
    if len(manifest_rows) != int(pilot["maximum_requested_snapshot_slots"]):
        source_blockers.append("manifest_request_slots")
    if duplicate_source_indexes:
        source_blockers.append("duplicate_source_indexes")
    if missing_source_index_rows:
        source_blockers.append("missing_source_index_rows")
    if request_success_rate < float(gates["minimum_http_request_success_rate"]):
        source_blockers.append("http_request_success_rate")
    if unresolved_access_errors > int(gates["maximum_http_401_403_429_after_retries"]):
        source_blockers.append("unresolved_access_errors")
    mapping_rate = len(mapped_games) / int(pilot["games"])
    if mapping_rate < float(gates["minimum_target_game_mapping_rate"]):
        source_blockers.append("target_game_mapping_rate")
    if any(mapped_by_season.get(season, 0) < int(gates["minimum_mapped_games_each_season"]) for season in pilot["seasons"]):
        source_blockers.append("mapped_games_each_season")
    if sum(int(row.get("future_snapshot_rows", 0)) for row in source_index_rows) > int(gates["maximum_future_snapshot_rows"]):
        source_blockers.append("future_snapshot_rows")
    if sum(int(row.get("point_in_time_violations", 0)) for row in source_index_rows) > int(gates["maximum_point_in_time_violations"]):
        source_blockers.append("point_in_time_violations")
    if sum(int(row.get("team_only_tipoff_mismatches", 0)) for row in source_index_rows):
        source_blockers.append("tipoff_identity_mismatches")
    if sum(int(row.get("reversed_home_away_events", 0)) for row in source_index_rows) > int(gates["maximum_team_mismatches"]):
        source_blockers.append("team_mismatches")
    if sum(int(row.get("ambiguous_event_matches", 0)) for row in source_index_rows):
        source_blockers.append("ambiguous_event_matches")
    if sum(int(bool(row.get("fuzzy_matching_used"))) for row in source_index_rows) > int(gates["maximum_fuzzy_matches"]):
        source_blockers.append("fuzzy_matches")
    if duplicate_quote_keys > int(gates["maximum_duplicate_quote_keys"]):
        source_blockers.append("duplicate_quote_keys")
    if sum(int(row.get("opening_inferred", 0)) for row in source_index_rows) > int(gates["maximum_opening_labels_inferred"]):
        source_blockers.append("opening_inferred")
    if quota_credits_used > int(gates["maximum_quota_credits_used"]):
        source_blockers.append("quota_credit_cap")
    if missing_quota_headers:
        source_blockers.append("missing_quota_headers")
    if missing_hashes:
        source_blockers.append("missing_response_hashes")
    if missing_source_event_ids:
        source_blockers.append("missing_source_event_ids")

    state = (
        "SOURCE_QUALIFICATION_BLOCKED"
        if source_blockers
        else "QUALIFIED_FOR_PRODUCTION_MANIFEST"
        if qualified_books
        else "NO_QUALIFIED_BOOKMAKER"
    )
    return {
        "schema_version": VERSION,
        "generated_at": base.utc_now(),
        "decision_state": state,
        "coverage": {
            "manifest_requests": len(manifest_rows),
            "source_index_rows": len(source_index_rows),
            "successful_requests": successful_requests,
            "request_success_rate": request_success_rate,
            "mapped_games": len(mapped_games),
            "mapping_rate": mapping_rate,
            "mapped_games_by_season": dict(sorted(mapped_by_season.items())),
            "normalized_quote_rows_temporary": len(quote_rows),
            "bookmakers": len(bookmaker_summary),
            "qualified_bookmakers": len(qualified_books),
        },
        "quota": {
            "credits_used": quota_credits_used,
            "maximum_allowed": int(gates["maximum_quota_credits_used"]),
            "missing_quota_headers": missing_quota_headers,
        },
        "quality": {
            "duplicate_source_indexes": duplicate_source_indexes,
            "missing_source_index_rows": missing_source_index_rows,
            "unresolved_401_403_429": unresolved_access_errors,
            "future_snapshot_rows": sum(int(row.get("future_snapshot_rows", 0)) for row in source_index_rows),
            "point_in_time_violations": sum(int(row.get("point_in_time_violations", 0)) for row in source_index_rows),
            "tipoff_identity_mismatches": sum(int(row.get("team_only_tipoff_mismatches", 0)) for row in source_index_rows),
            "team_mismatches": sum(int(row.get("reversed_home_away_events", 0)) for row in source_index_rows),
            "ambiguous_event_matches": sum(int(row.get("ambiguous_event_matches", 0)) for row in source_index_rows),
            "fuzzy_matches": sum(int(bool(row.get("fuzzy_matching_used"))) for row in source_index_rows),
            "duplicate_quote_keys": duplicate_quote_keys,
            "opening_labels_inferred": sum(int(row.get("opening_inferred", 0)) for row in source_index_rows),
            "source_blockers": sorted(source_blockers),
            "market_metrics_calculated": False,
            "bookmaker_selected_by_roi_model_or_price": False,
            "quote_level_rows_retained_in_report": 0,
        },
        "bookmaker_coverage": bookmaker_summary,
        "selected_primary_bookmaker": qualified_books[0]["bookmaker_key"] if qualified_books else None,
        "decision": {
            "ready_for_production_manifest": state == "QUALIFIED_FOR_PRODUCTION_MANIFEST",
            "ready_for_production_backfill": False,
            "ready_for_market_backtest": False,
            "ready_for_clv_ev_roi": False,
            "ready_for_betting_edge_claim": False,
            "formal_stake": 0,
        },
    }


def _synthetic_schedule(policy: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for game in policy["qualification_pilot"]["sample"]:
        day = date.fromisoformat(str(game["game_date"]))
        tipoff = datetime.combine(day + timedelta(days=1), time(1, 0), tzinfo=timezone.utc)
        rows.append({
            "historical_game_id": str(game["game_id"]),
            "game_date": str(game["game_date"]),
            "away_team_abbr": str(game["away"]),
            "home_team_abbr": str(game["home"]),
            "scheduled_tipoff_utc": base.iso_utc(tipoff),
        })
    return rows


def _synthetic_full_rows(
    policy: dict[str, Any],
    manifest: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    quotes: list[dict[str, Any]] = []
    indexes: list[dict[str, Any]] = []
    for request in manifest:
        requested = base.parse_utc(request["requested_at_utc"])
        snapshot = requested - timedelta(minutes=5)
        indexes.append({
            "request_id": request["request_id"],
            "historical_game_id": request["historical_game_id"],
            "season": request["season"],
            "snapshot_label": request["snapshot_label"],
            "http_status": 200,
            "snapshot_time_valid": 1,
            "source_event_match": 1,
            "source_event_id_present": 1,
            "future_snapshot_rows": 0,
            "point_in_time_violations": 0,
            "team_only_tipoff_mismatches": 0,
            "reversed_home_away_events": 0,
            "ambiguous_event_matches": 0,
            "fuzzy_matching_used": False,
            "opening_inferred": 0,
            "response_sha256": "a" * 64,
            "x_requests_last": "10",
        })
        for bookmaker in ("synthetic_a", "synthetic_b"):
            quotes.append({
                "request_id": request["request_id"],
                "source_event_id": f"synthetic-{request['historical_game_id']}",
                "historical_game_id": request["historical_game_id"],
                "season": request["season"],
                "snapshot_label": request["snapshot_label"],
                "bookmaker_key": bookmaker,
                "market_key": MARKET_KEY,
                "home_price_decimal": 1.80,
                "away_price_decimal": 2.10,
                "two_way_overround": 1 / 1.80 + 1 / 2.10 - 1,
                "quote_time_valid": True,
                "provider_snapshot_at_utc": base.iso_utc(snapshot),
            })
    return quotes, indexes


def self_test(policy: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    schedule = _synthetic_schedule(policy)
    manifest, manifest_report = base.build_request_manifest(policy, schedule)
    assert manifest_report["decision"]["manifest_structurally_ready"] is True, manifest_report
    assert len(manifest) == 180
    assert all(row["snapshot_label"] != "Opening" for row in manifest)

    sample_request = next(row for row in manifest if row["snapshot_label"] == "T-1h")
    home_name = next(
        game["home"] for game in policy["qualification_pilot"]["sample"]
        if game["game_id"] == sample_request["historical_game_id"]
    )
    away_name = next(
        game["away"] for game in policy["qualification_pilot"]["sample"]
        if game["game_id"] == sample_request["historical_game_id"]
    )
    provider_home = {
        "DEN": "Denver Nuggets", "LAL": "Los Angeles Lakers", "CHI": "Chicago Bulls",
        "DET": "Detroit Pistons", "ORL": "Orlando Magic", "WAS": "Washington Wizards",
    }.get(home_name)
    provider_away = {
        "DEN": "Denver Nuggets", "LAL": "Los Angeles Lakers", "CHI": "Chicago Bulls",
        "DET": "Detroit Pistons", "ORL": "Orlando Magic", "WAS": "Washington Wizards",
    }.get(away_name)
    # The first T-1h request is guaranteed to use teams covered by the shared alias map;
    # fall back to the policy's Lakers @ Nuggets row for a stable payload fixture.
    sample_request = next(
        row for row in manifest
        if row["historical_game_id"] == "22300061" and row["snapshot_label"] == "T-1h"
    )
    payload = {
        "timestamp": base.iso_utc(base.parse_utc(sample_request["requested_at_utc"]) - timedelta(minutes=5)),
        "data": [{
            "id": "synthetic-event-1",
            "sport_key": "basketball_nba",
            "commence_time": sample_request["scheduled_tipoff_utc"],
            "home_team": "Denver Nuggets",
            "away_team": "Los Angeles Lakers",
            "bookmakers": [{
                "key": "synthetic_book",
                "title": "Synthetic Book",
                "last_update": base.iso_utc(base.parse_utc(sample_request["requested_at_utc"]) - timedelta(minutes=6)),
                "markets": [{
                    "key": "h2h",
                    "outcomes": [
                        {"name": "Denver Nuggets", "price": 1.75},
                        {"name": "Los Angeles Lakers", "price": 2.20},
                    ],
                }],
            }],
        }],
    }
    quotes, index = parse_payload(
        policy,
        sample_request,
        payload,
        "2026-07-18T08:00:00Z",
        {
            "http_status": 200,
            "response_bytes": 1234,
            "x_requests_last": "10",
            "x_requests_used": "10",
            "x_requests_remaining": "19990",
        },
    )
    assert len(quotes) == 1, quotes
    assert index["source_event_match"] == 1, index
    assert index["snapshot_time_valid"] == 1, index
    assert index["invalid_bookmaker_timestamp_rows"] == 0, index

    wrong_tipoff = json.loads(json.dumps(payload))
    wrong_tipoff["data"][0]["commence_time"] = base.iso_utc(
        base.parse_utc(sample_request["scheduled_tipoff_utc"]) + timedelta(minutes=30)
    )
    wrong_quotes, wrong_index = parse_payload(
        policy, sample_request, wrong_tipoff, "2026-07-18T08:00:00Z"
    )
    assert wrong_quotes == []
    assert wrong_index["source_event_match"] == 0
    assert wrong_index["team_only_tipoff_mismatches"] == 1

    bad_update = json.loads(json.dumps(payload))
    bad_update["data"][0]["bookmakers"][0]["last_update"] = base.iso_utc(
        base.parse_utc(payload["timestamp"]) + timedelta(minutes=1)
    )
    bad_quotes, bad_index = parse_payload(
        policy, sample_request, bad_update, "2026-07-18T08:00:00Z"
    )
    assert bad_quotes == []
    assert bad_index["invalid_bookmaker_timestamp_rows"] == 1

    future = json.loads(json.dumps(payload))
    future["timestamp"] = base.iso_utc(
        base.parse_utc(sample_request["requested_at_utc"]) + timedelta(minutes=1)
    )
    _, future_index = parse_payload(
        policy, sample_request, future, "2026-07-18T08:00:00Z"
    )
    assert future_index["future_snapshot_rows"] == 1
    assert future_index["snapshot_time_valid"] == 0

    synthetic_quotes, synthetic_indexes = _synthetic_full_rows(policy, manifest)
    qualified = aggregate_qualification(policy, manifest, synthetic_quotes, synthetic_indexes)
    assert qualified["decision_state"] == "QUALIFIED_FOR_PRODUCTION_MANIFEST", qualified
    assert qualified["selected_primary_bookmaker"] == "synthetic_a", qualified
    assert qualified["quota"]["credits_used"] == 1800, qualified

    # An abnormal non-selected book must not globally block an otherwise qualified book.
    synthetic_quotes[0]["home_price_decimal"] = 1000.0
    qualified_other_book = aggregate_qualification(policy, manifest, synthetic_quotes, synthetic_indexes)
    assert qualified_other_book["decision_state"] == "QUALIFIED_FOR_PRODUCTION_MANIFEST", qualified_other_book
    assert qualified_other_book["selected_primary_bookmaker"] == "synthetic_b", qualified_other_book

    blocked_indexes = json.loads(json.dumps(synthetic_indexes))
    blocked_indexes[0]["future_snapshot_rows"] = 1
    blocked = aggregate_qualification(policy, manifest, synthetic_quotes, blocked_indexes)
    assert blocked["decision_state"] == "SOURCE_QUALIFICATION_BLOCKED", blocked
    assert "future_snapshot_rows" in blocked["quality"]["source_blockers"], blocked

    access = base.access_not_provided_report(policy)
    assert access["decision_state"] == "ACCESS_NOT_PROVIDED"
    assert access["coverage"]["network_requests_made"] == 0
    assert access["quality"]["api_key_read"] is False

    report = {
        "schema_version": VERSION,
        "generated_at": base.utc_now(),
        "checks": {
            "manifest_rows": len(manifest),
            "manifest_quota_ceiling": manifest_report["coverage"]["estimated_quota_credits"],
            "opening_labels_created": sum(row["snapshot_label"] == "Opening" for row in manifest),
            "strict_event_and_tipoff_match": True,
            "wrong_tipoff_rejected": True,
            "future_snapshot_rejected": True,
            "bookmaker_update_after_snapshot_rejected": True,
            "coverage_only_tie_break": "synthetic_a",
            "nonselected_abnormal_book_does_not_block": True,
            "global_pit_violation_blocks": True,
            "quota_headers_enforced": True,
        },
        "execution_boundary": {
            "network_requests_made": 0,
            "api_key_read": False,
            "paid_endpoint_called": False,
            "real_quotes_downloaded": 0,
            "subscription_or_purchase_created": False,
            "market_metrics_calculated": False,
            "quote_level_rows_retained": 0,
            "ready_for_paid_qualification_execution": False,
            "ready_for_production_backfill": False,
            "ready_for_market_backtest": False,
            "ready_for_betting_edge_claim": False,
            "formal_stake": 0,
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "timestamped-odds-adapter-v1-hardening-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    policy = base.read_json(args.policy)
    if not args.self_test:
        parser.error("offline runner currently permits only --self-test; paid execution is intentionally absent")
    report = self_test(policy, args.output_dir)
    print(json.dumps(report["execution_boundary"], indent=2))


if __name__ == "__main__":
    main()
