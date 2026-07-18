#!/usr/bin/env python3
"""Offline adapter and qualification helpers for Timestamped Odds v1.

This module intentionally contains no HTTP client. It can build a deterministic
request manifest, parse already-supplied The Odds API Historical v4 payloads,
and aggregate source/bookmaker coverage. Paid network execution belongs to a
separate, explicitly approved stage.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from import_closing_odds_archive import team_abbr

VERSION = "timestamped-odds-qualification-adapter-v1"
SOURCE_ID = "the_odds_api_historical_v4"
MARKET_KEY = "h2h"
DECISIONS = {
    "ACCESS_NOT_PROVIDED",
    "SOURCE_QUALIFICATION_BLOCKED",
    "NO_QUALIFIED_BOOKMAKER",
    "QUALIFIED_FOR_PRODUCTION_MANIFEST",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_utc(value: Any) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise ValueError("blank timestamp")
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp lacks timezone: {value!r}")
    return parsed.astimezone(timezone.utc)


def iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be object: {path}")
    return payload


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or (list(rows[0]) if rows else [])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if fields:
            writer.writeheader()
            writer.writerows(rows)


def response_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def snapshot_targets(policy: dict[str, Any]) -> list[dict[str, Any]]:
    return list(policy["snapshot_contract"]["required_targets"])


def build_request_manifest(
    policy: dict[str, Any],
    schedule_rows: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build a no-price manifest from the frozen 30-game sample and exact tipoffs."""
    pilot = policy["qualification_pilot"]
    source = policy["source_candidate"]
    sample = pilot["sample"]
    schedule_by_id: dict[str, dict[str, str]] = {}
    duplicate_schedule_games = 0
    for row in schedule_rows:
        game_id = str(row.get("historical_game_id") or row.get("game_id") or "").strip()
        if not game_id:
            continue
        if game_id in schedule_by_id:
            duplicate_schedule_games += 1
        schedule_by_id[game_id] = row

    output: list[dict[str, Any]] = []
    missing_schedule_games: list[str] = []
    identity_mismatches: list[str] = []
    seen_requested: set[str] = set()
    duplicate_requested_timestamps = 0
    for game in sample:
        game_id = str(game["game_id"])
        schedule = schedule_by_id.get(game_id)
        if schedule is None:
            missing_schedule_games.append(game_id)
            continue
        scheduled_date = str(schedule.get("game_date") or "").strip()
        scheduled_home = str(schedule.get("home_team_abbr") or "").strip()
        scheduled_away = str(schedule.get("away_team_abbr") or "").strip()
        if (
            scheduled_date != str(game["game_date"])
            or scheduled_home != str(game["home"])
            or scheduled_away != str(game["away"])
        ):
            identity_mismatches.append(game_id)
            continue
        tipoff = parse_utc(schedule.get("scheduled_tipoff_utc") or schedule.get("commence_time"))
        for target in snapshot_targets(policy):
            requested = tipoff - timedelta(seconds=int(target["seconds_before_tipoff"]))
            requested_text = iso_utc(requested)
            if requested_text in seen_requested:
                duplicate_requested_timestamps += 1
            seen_requested.add(requested_text)
            output.append({
                "request_id": hashlib.sha256(
                    f"{game_id}|{target['label']}|{requested_text}".encode("utf-8")
                ).hexdigest()[:24],
                "source_id": source["source_id"],
                "endpoint": source["endpoint"],
                "sport_key": source["sport_key"],
                "region": policy["market_scope"]["region"],
                "market": policy["market_scope"]["market"],
                "odds_format": policy["market_scope"]["odds_format"],
                "historical_game_id": game_id,
                "season": game["season"],
                "game_date": game["game_date"],
                "away_team_abbr": game["away"],
                "home_team_abbr": game["home"],
                "scheduled_tipoff_utc": iso_utc(tipoff),
                "snapshot_label": target["label"],
                "seconds_before_tipoff": int(target["seconds_before_tipoff"]),
                "requested_at_utc": requested_text,
            })

    output.sort(key=lambda row: (row["requested_at_utc"], row["historical_game_id"], row["snapshot_label"]))
    expected_slots = int(pilot["maximum_requested_snapshot_slots"])
    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "coverage": {
            "frozen_sample_games": len(sample),
            "schedule_input_rows": len(schedule_rows),
            "manifest_rows": len(output),
            "unique_requested_timestamps": len(seen_requested),
            "expected_request_slots": expected_slots,
            "estimated_quota_credits": len(output)
            * int(source["quota_cost_per_region_per_market_per_request"]),
        },
        "quality": {
            "duplicate_schedule_games": duplicate_schedule_games,
            "missing_schedule_games": sorted(missing_schedule_games),
            "identity_mismatches": sorted(identity_mismatches),
            "duplicate_requested_timestamps": duplicate_requested_timestamps,
            "prices_in_manifest": False,
            "network_calls_made": False,
            "api_key_read": False,
        },
        "decision": {
            "manifest_structurally_ready": (
                duplicate_schedule_games == 0
                and not missing_schedule_games
                and not identity_mismatches
                and len(output) == expected_slots
                and len(output)
                * int(source["quota_cost_per_region_per_market_per_request"])
                <= int(pilot["maximum_paid_quota_credits"])
            ),
            "ready_for_paid_qualification_execution": False,
        },
    }
    return output, report


def validate_snapshot_time(
    policy: dict[str, Any],
    requested_at: datetime,
    provider_snapshot_at: datetime,
) -> tuple[float, bool]:
    lag_minutes = (requested_at - provider_snapshot_at).total_seconds() / 60.0
    if provider_snapshot_at > requested_at:
        return lag_minutes, False
    boundary = datetime(2022, 9, 1, tzinfo=timezone.utc)
    max_lag = (
        float(policy["snapshot_contract"]["maximum_snapshot_lag_minutes_before_2022_09"])
        if requested_at < boundary
        else float(policy["snapshot_contract"]["maximum_snapshot_lag_minutes_from_2022_09"])
    )
    return lag_minutes, 0.0 <= lag_minutes <= max_lag


def exact_event_match(
    request: dict[str, Any],
    events: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    unknown_team_events = 0
    for event in events:
        try:
            home = team_abbr(event.get("home_team"))
            away = team_abbr(event.get("away_team"))
        except ValueError:
            unknown_team_events += 1
            continue
        if home == request["home_team_abbr"] and away == request["away_team_abbr"]:
            candidates.append(event)
    return (
        candidates[0] if len(candidates) == 1 else None,
        {
            "exact_candidate_events": len(candidates),
            "unknown_team_events": unknown_team_events,
            "ambiguous_event_match": int(len(candidates) > 1),
            "fuzzy_matching_used": False,
        },
    )


def parse_two_way_h2h(
    request: dict[str, Any],
    event: dict[str, Any],
    provider_snapshot_at: datetime,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    tipoff = parse_utc(request["scheduled_tipoff_utc"])
    event_tipoff = parse_utc(event.get("commence_time"))
    event_tipoff_match = event_tipoff == tipoff
    for bookmaker in event.get("bookmakers") or []:
        bookmaker_key = str(bookmaker.get("key") or "").strip()
        bookmaker_last_update = str(bookmaker.get("last_update") or "").strip()
        h2h_markets = [
            market
            for market in (bookmaker.get("markets") or [])
            if str(market.get("key") or "") == MARKET_KEY
        ]
        if len(h2h_markets) != 1:
            diagnostics.append({
                "bookmaker_key": bookmaker_key,
                "reason": "missing_or_duplicate_h2h_market",
                "market_rows": len(h2h_markets),
            })
            continue
        market = h2h_markets[0]
        outcomes: dict[str, float] = {}
        invalid_outcome_names = 0
        duplicate_outcomes = 0
        for outcome in market.get("outcomes") or []:
            try:
                abbr = team_abbr(outcome.get("name"))
            except ValueError:
                invalid_outcome_names += 1
                continue
            if abbr in outcomes:
                duplicate_outcomes += 1
            try:
                outcomes[abbr] = float(outcome.get("price"))
            except (TypeError, ValueError):
                outcomes[abbr] = float("nan")
        home = request["home_team_abbr"]
        away = request["away_team_abbr"]
        if set(outcomes) != {home, away}:
            diagnostics.append({
                "bookmaker_key": bookmaker_key,
                "reason": "outcome_team_set_mismatch",
                "outcome_teams": sorted(outcomes),
                "invalid_outcome_names": invalid_outcome_names,
                "duplicate_outcomes": duplicate_outcomes,
            })
            continue
        home_price = outcomes[home]
        away_price = outcomes[away]
        finite_prices = math.isfinite(home_price) and math.isfinite(away_price)
        overround = (
            (1.0 / home_price + 1.0 / away_price - 1.0)
            if finite_prices and home_price > 0 and away_price > 0
            else float("nan")
        )
        rows.append({
            "request_id": request["request_id"],
            "source_id": SOURCE_ID,
            "source_event_id": str(event.get("id") or ""),
            "historical_game_id": request["historical_game_id"],
            "season": request["season"],
            "snapshot_label": request["snapshot_label"],
            "requested_at_utc": request["requested_at_utc"],
            "provider_snapshot_at_utc": iso_utc(provider_snapshot_at),
            "scheduled_tipoff_utc": request["scheduled_tipoff_utc"],
            "event_commence_time_utc": iso_utc(event_tipoff),
            "event_tipoff_match": int(event_tipoff_match),
            "bookmaker_key": bookmaker_key,
            "bookmaker_last_update_utc": bookmaker_last_update,
            "market_key": MARKET_KEY,
            "home_team_abbr": home,
            "away_team_abbr": away,
            "home_price_decimal": home_price,
            "away_price_decimal": away_price,
            "two_way_overround": overround,
        })
    return rows, diagnostics


def parse_historical_payload(
    policy: dict[str, Any],
    request: dict[str, Any],
    payload: dict[str, Any],
    fetched_at: str,
    http_meta: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    requested_at = parse_utc(request["requested_at_utc"])
    provider_snapshot_at = parse_utc(payload.get("timestamp"))
    lag_minutes, time_valid = validate_snapshot_time(policy, requested_at, provider_snapshot_at)
    events = payload.get("data") if isinstance(payload.get("data"), list) else []
    event, match_qa = exact_event_match(request, events)
    quote_rows: list[dict[str, Any]] = []
    bookmaker_diagnostics: list[dict[str, Any]] = []
    if event is not None:
        quote_rows, bookmaker_diagnostics = parse_two_way_h2h(
            request, event, provider_snapshot_at
        )
    tipoff = parse_utc(request["scheduled_tipoff_utc"])
    future_snapshot_rows = int(provider_snapshot_at > requested_at)
    pre_tip_violation = int(provider_snapshot_at >= tipoff)
    meta = http_meta or {}
    source_index = {
        "request_id": request["request_id"],
        "historical_game_id": request["historical_game_id"],
        "season": request["season"],
        "snapshot_label": request["snapshot_label"],
        "requested_at_utc": request["requested_at_utc"],
        "provider_snapshot_at_utc": iso_utc(provider_snapshot_at),
        "snapshot_lag_minutes": lag_minutes,
        "snapshot_time_valid": int(time_valid),
        "fetched_at_utc": iso_utc(parse_utc(fetched_at)),
        "http_status": int(meta.get("http_status", 200)),
        "response_bytes": int(meta.get("response_bytes", 0)),
        "response_sha256": str(meta.get("response_sha256") or response_sha256(payload)),
        "x_requests_last": str(meta.get("x_requests_last", "")),
        "x_requests_used": str(meta.get("x_requests_used", "")),
        "x_requests_remaining": str(meta.get("x_requests_remaining", "")),
        "source_event_match": int(event is not None),
        "quote_bookmakers": len(quote_rows),
        "future_snapshot_rows": future_snapshot_rows,
        "pre_tip_violations": pre_tip_violation,
        "opening_inferred": 0,
        "fuzzy_matching_used": False,
        **match_qa,
        "bookmaker_diagnostic_count": len(bookmaker_diagnostics),
    }
    return quote_rows, source_index


def qualify_aggregate(
    policy: dict[str, Any],
    manifest_rows: list[dict[str, Any]],
    quote_rows: list[dict[str, Any]],
    source_index_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    gates = policy["pilot_source_gates"]
    manifest_by_request = {row["request_id"]: row for row in manifest_rows}
    successful_requests = sum(
        int(row.get("http_status", 0)) == 200 and int(row.get("snapshot_time_valid", 0)) == 1
        for row in source_index_rows
    )
    unresolved_access_errors = sum(
        int(row.get("http_status", 0)) in {401, 403, 429}
        for row in source_index_rows
    )
    mapped_games = {
        str(row["historical_game_id"])
        for row in source_index_rows
        if int(row.get("source_event_match", 0)) == 1
    }
    mapped_by_season: Counter[str] = Counter()
    for game_id in mapped_games:
        for request in manifest_rows:
            if request["historical_game_id"] == game_id:
                mapped_by_season[str(request["season"])] += 1
                break

    quote_keys = [
        (
            row["request_id"],
            row["bookmaker_key"],
            row["market_key"],
        )
        for row in quote_rows
    ]
    duplicate_quote_keys = len(quote_keys) - len(set(quote_keys))
    min_price = float(gates["minimum_decimal_price"])
    max_price = float(gates["maximum_decimal_price"])
    min_overround = float(gates["minimum_two_way_overround"])
    max_overround = float(gates["maximum_two_way_overround"])
    abnormal_rows = 0
    for row in quote_rows:
        prices = (float(row["home_price_decimal"]), float(row["away_price_decimal"]))
        overround = float(row["two_way_overround"])
        if (
            not all(math.isfinite(value) and min_price <= value <= max_price for value in prices)
            or not math.isfinite(overround)
            or not min_overround <= overround <= max_overround
            or int(row["event_tipoff_match"]) != 1
        ):
            abnormal_rows += 1

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
    book_keys = sorted({key[0] for key in by_book_game})
    for bookmaker in book_keys:
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
            "all_target_snapshot_coverage": len(all_targets) / int(policy["qualification_pilot"]["games"]),
            "minimum_per_season_complete_t60_closing": min(
                (season_complete.get(season, 0) for season in policy["qualification_pilot"]["seasons"]),
                default=0,
            ),
        })

    qualified_books = [
        row for row in bookmaker_summary
        if row["complete_t60_closing_games"] >= int(gates["minimum_primary_bookmaker_complete_t60_closing_games"])
        and row["minimum_per_season_complete_t60_closing"] >= int(gates["minimum_primary_bookmaker_complete_t60_closing_games_each_season"])
        and row["all_target_snapshot_coverage"] >= float(gates["minimum_primary_bookmaker_all_target_snapshot_coverage"])
    ]
    qualified_books.sort(
        key=lambda row: (
            -row["complete_t60_closing_games"],
            -row["all_target_snapshot_coverage"],
            -row["minimum_per_season_complete_t60_closing"],
            row["bookmaker_key"],
        )
    )

    request_success_rate = successful_requests / len(manifest_rows) if manifest_rows else 0.0
    mapping_rate = len(mapped_games) / int(policy["qualification_pilot"]["games"])
    source_blockers: list[str] = []
    if request_success_rate < float(gates["minimum_http_request_success_rate"]):
        source_blockers.append("http_request_success_rate")
    if unresolved_access_errors > int(gates["maximum_http_401_403_429_after_retries"]):
        source_blockers.append("unresolved_access_errors")
    if mapping_rate < float(gates["minimum_target_game_mapping_rate"]):
        source_blockers.append("target_game_mapping_rate")
    if any(mapped_by_season.get(season, 0) < int(gates["minimum_mapped_games_each_season"]) for season in policy["qualification_pilot"]["seasons"]):
        source_blockers.append("mapped_games_each_season")
    if sum(int(row.get("future_snapshot_rows", 0)) for row in source_index_rows) > int(gates["maximum_future_snapshot_rows"]):
        source_blockers.append("future_snapshot_rows")
    if sum(int(row.get("pre_tip_violations", 0)) for row in source_index_rows) > int(gates["maximum_point_in_time_violations"]):
        source_blockers.append("point_in_time_violations")
    if sum(int(row.get("ambiguous_event_match", 0)) for row in source_index_rows) > 0:
        source_blockers.append("ambiguous_event_match")
    if sum(int(bool(row.get("fuzzy_matching_used"))) for row in source_index_rows) > int(gates["maximum_fuzzy_matches"]):
        source_blockers.append("fuzzy_matches")
    if duplicate_quote_keys > int(gates["maximum_duplicate_quote_keys"]):
        source_blockers.append("duplicate_quote_keys")
    if abnormal_rows > int(gates["maximum_selected_primary_bookmaker_abnormal_quote_rows"]):
        source_blockers.append("abnormal_quote_rows")
    if sum(int(row.get("opening_inferred", 0)) for row in source_index_rows) > int(gates["maximum_opening_labels_inferred"]):
        source_blockers.append("opening_inferred")

    state = (
        "SOURCE_QUALIFICATION_BLOCKED"
        if source_blockers
        else "QUALIFIED_FOR_PRODUCTION_MANIFEST"
        if qualified_books
        else "NO_QUALIFIED_BOOKMAKER"
    )
    return {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "decision_state": state,
        "coverage": {
            "manifest_requests": len(manifest_rows),
            "successful_requests": successful_requests,
            "request_success_rate": request_success_rate,
            "mapped_games": len(mapped_games),
            "mapping_rate": mapping_rate,
            "mapped_games_by_season": dict(sorted(mapped_by_season.items())),
            "normalized_quote_rows": len(quote_rows),
            "bookmakers": len(bookmaker_summary),
            "qualified_bookmakers": len(qualified_books),
        },
        "quality": {
            "unresolved_401_403_429": unresolved_access_errors,
            "future_snapshot_rows": sum(int(row.get("future_snapshot_rows", 0)) for row in source_index_rows),
            "point_in_time_violations": sum(int(row.get("pre_tip_violations", 0)) for row in source_index_rows),
            "ambiguous_event_matches": sum(int(row.get("ambiguous_event_match", 0)) for row in source_index_rows),
            "fuzzy_matches": sum(int(bool(row.get("fuzzy_matching_used"))) for row in source_index_rows),
            "duplicate_quote_keys": duplicate_quote_keys,
            "abnormal_quote_rows": abnormal_rows,
            "opening_labels_inferred": sum(int(row.get("opening_inferred", 0)) for row in source_index_rows),
            "source_blockers": sorted(source_blockers),
            "market_metrics_calculated": False,
            "bookmaker_selected_by_roi_or_model_performance": False,
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


def access_not_provided_report(policy: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "decision_state": "ACCESS_NOT_PROVIDED",
        "coverage": {
            "frozen_sample_games": int(policy["qualification_pilot"]["games"]),
            "planned_request_slots": int(policy["qualification_pilot"]["maximum_requested_snapshot_slots"]),
            "maximum_paid_quota_credits": int(policy["qualification_pilot"]["maximum_paid_quota_credits"]),
            "network_requests_made": 0,
            "quotes_downloaded": 0,
        },
        "quality": {
            "explicit_paid_access_acknowledgement": False,
            "api_key_read": False,
            "paid_endpoint_called": False,
            "subscription_or_purchase_created": False,
            "market_metrics_calculated": False,
            "raw_or_quote_level_files_retained": 0,
        },
        "decision": {
            "ready_for_production_manifest": False,
            "ready_for_production_backfill": False,
            "ready_for_market_backtest": False,
            "ready_for_clv_ev_roi": False,
            "ready_for_betting_edge_claim": False,
            "formal_stake": 0,
        },
    }


def self_test(policy: dict[str, Any], output_dir: Path) -> None:
    sample_game = policy["qualification_pilot"]["sample"][20]
    schedule = [{
        "historical_game_id": sample_game["game_id"],
        "game_date": sample_game["game_date"],
        "away_team_abbr": sample_game["away"],
        "home_team_abbr": sample_game["home"],
        "scheduled_tipoff_utc": "2023-10-25T01:30:00Z",
    }]
    mini_policy = json.loads(json.dumps(policy))
    mini_policy["qualification_pilot"]["sample"] = [sample_game]
    mini_policy["qualification_pilot"]["games"] = 1
    mini_policy["qualification_pilot"]["games_per_season"] = 1
    mini_policy["qualification_pilot"]["maximum_requested_snapshot_slots"] = 6
    mini_policy["qualification_pilot"]["maximum_paid_quota_credits"] = 60
    manifest, manifest_report = build_request_manifest(mini_policy, schedule)
    assert manifest_report["decision"]["manifest_structurally_ready"] is True, manifest_report
    assert len(manifest) == 6
    t60 = next(row for row in manifest if row["snapshot_label"] == "T-1h")
    payload = {
        "timestamp": "2023-10-25T00:29:30Z",
        "previous_timestamp": "2023-10-25T00:24:30Z",
        "next_timestamp": "2023-10-25T00:34:30Z",
        "data": [{
            "id": "synthetic-event-1",
            "sport_key": "basketball_nba",
            "commence_time": "2023-10-25T01:30:00Z",
            "home_team": "Denver Nuggets",
            "away_team": "Los Angeles Lakers",
            "bookmakers": [{
                "key": "synthetic_book",
                "title": "Synthetic Book",
                "last_update": "2023-10-25T00:28:00Z",
                "markets": [{
                    "key": "h2h",
                    "last_update": "2023-10-25T00:28:00Z",
                    "outcomes": [
                        {"name": "Denver Nuggets", "price": 1.75},
                        {"name": "Los Angeles Lakers", "price": 2.20},
                    ],
                }],
            }],
        }],
    }
    quotes, source = parse_historical_payload(
        mini_policy,
        t60,
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
    assert source["snapshot_time_valid"] == 1, source
    assert source["future_snapshot_rows"] == 0, source
    assert source["fuzzy_matching_used"] is False, source
    assert abs(quotes[0]["two_way_overround"] - (1 / 1.75 + 1 / 2.2 - 1)) < 1e-12

    future_payload = json.loads(json.dumps(payload))
    future_payload["timestamp"] = "2023-10-25T00:31:00Z"
    _, future_source = parse_historical_payload(
        mini_policy, t60, future_payload, "2026-07-18T08:00:00Z"
    )
    assert future_source["snapshot_time_valid"] == 0, future_source
    assert future_source["future_snapshot_rows"] == 1, future_source

    ambiguous_payload = json.loads(json.dumps(payload))
    ambiguous_payload["data"].append(json.loads(json.dumps(payload["data"][0])))
    ambiguous_payload["data"][1]["id"] = "synthetic-event-duplicate"
    ambiguous_quotes, ambiguous_source = parse_historical_payload(
        mini_policy, t60, ambiguous_payload, "2026-07-18T08:00:00Z"
    )
    assert ambiguous_quotes == [], ambiguous_quotes
    assert ambiguous_source["ambiguous_event_match"] == 1, ambiguous_source

    blocked = access_not_provided_report(policy)
    assert blocked["decision_state"] == "ACCESS_NOT_PROVIDED"
    assert blocked["coverage"]["network_requests_made"] == 0
    assert blocked["quality"]["api_key_read"] is False
    assert blocked["quality"]["paid_endpoint_called"] is False
    assert blocked["quality"]["subscription_or_purchase_created"] is False

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "synthetic-adapter-self-test.json").write_text(
        json.dumps({
            "manifest_report": manifest_report,
            "valid_source_index": source,
            "valid_quote_count": len(quotes),
            "future_snapshot_rejected": True,
            "ambiguous_event_rejected": True,
            "access_state": blocked,
        }, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--schedule", type=Path)
    parser.add_argument("--build-manifest", action="store_true")
    parser.add_argument("--access-not-provided", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    policy = read_json(args.policy)
    if args.self_test:
        self_test(policy, args.output_dir)
        print("Timestamped Odds qualification adapter v1 self-test passed")
        return
    if args.access_not_provided:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        report = access_not_provided_report(policy)
        (args.output_dir / "timestamped-odds-qualification-v1-report.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(report["decision"], indent=2))
        return
    if args.build_manifest:
        if not args.schedule:
            parser.error("--schedule is required with --build-manifest")
        manifest, report = build_request_manifest(policy, read_csv(args.schedule))
        args.output_dir.mkdir(parents=True, exist_ok=True)
        write_csv(args.output_dir / "timestamped-odds-request-manifest.csv", manifest)
        (args.output_dir / "timestamped-odds-request-manifest-report.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(report["decision"], indent=2))
        if not report["decision"]["manifest_structurally_ready"]:
            raise SystemExit(2)
        return
    parser.error("choose --self-test, --access-not-provided, or --build-manifest")


if __name__ == "__main__":
    main()
