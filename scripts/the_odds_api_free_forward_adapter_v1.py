#!/usr/bin/env python3
"""Offline synthetic adapter shell for The Odds API free forward candidate.

This module has no HTTP client, secret reader, scheduler or formal history writer.
It translates only a supplied synthetic payload shaped after the public v4 docs
into the provider-neutral private forward quote contract input.
"""
from __future__ import annotations

from typing import Any

ADAPTER_ID = "the-odds-api-free-forward-adapter-synthetic-shell-v1"
ADAPTER_VERSION = "1.0.0"
SOURCE_ID = "the_odds_api_free_forward"


class TheOddsApiSyntheticAdapterError(ValueError):
    """Raised when a synthetic payload violates the adapter contract."""


def _required_text(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise TheOddsApiSyntheticAdapterError(f"{field} is required")
    return text


def _decimal_price(value: Any, field: str) -> float:
    try:
        price = float(value)
    except (TypeError, ValueError) as exc:
        raise TheOddsApiSyntheticAdapterError(f"{field} must be numeric") from exc
    if not 1.001 <= price <= 100.0:
        raise TheOddsApiSyntheticAdapterError(f"{field} outside allowed decimal range")
    return round(price, 8)


def adapt_synthetic_event(payload: dict[str, Any], *, collector_fetched_at_utc: str) -> list[dict[str, Any]]:
    """Normalize one synthetic NBA event into provider-neutral collector rows.

    A same-bookmaker two-sided h2h market is mandatory. The quote timestamp is
    taken only from a provider-origin `market.last_update` or
    `bookmaker.last_update` field. Collector receipt time is never substituted.
    Source rights and game mapping remain unreviewed/unmapped in this synthetic
    shell, so runtime point-in-time qualification is not implied.
    """
    if not isinstance(payload, dict):
        raise TheOddsApiSyntheticAdapterError("payload must be an object")
    if payload.get("sport_key") != "basketball_nba":
        raise TheOddsApiSyntheticAdapterError("sport_key must be basketball_nba")

    event_id = _required_text(payload.get("id"), "id")
    commence_time = _required_text(payload.get("commence_time"), "commence_time")
    home_team = _required_text(payload.get("home_team"), "home_team")
    away_team = _required_text(payload.get("away_team"), "away_team")
    if home_team == away_team:
        raise TheOddsApiSyntheticAdapterError("home and away teams must differ")

    bookmakers = payload.get("bookmakers")
    if not isinstance(bookmakers, list) or not bookmakers:
        raise TheOddsApiSyntheticAdapterError("bookmakers must be a non-empty list")

    output: list[dict[str, Any]] = []
    for bookmaker in bookmakers:
        if not isinstance(bookmaker, dict):
            raise TheOddsApiSyntheticAdapterError("bookmaker must be an object")
        bookmaker_key = _required_text(bookmaker.get("key"), "bookmaker.key")
        bookmaker_last_update = bookmaker.get("last_update")
        markets = bookmaker.get("markets")
        if not isinstance(markets, list):
            raise TheOddsApiSyntheticAdapterError("bookmaker.markets must be a list")

        for market in markets:
            if not isinstance(market, dict):
                raise TheOddsApiSyntheticAdapterError("market must be an object")
            if market.get("key") != "h2h":
                continue

            quote_observed_at = market.get("last_update") or bookmaker_last_update
            quote_observed_at = _required_text(quote_observed_at, "h2h/bookmaker last_update")
            outcomes = market.get("outcomes")
            if not isinstance(outcomes, list) or len(outcomes) != 2:
                raise TheOddsApiSyntheticAdapterError("h2h outcomes must contain exactly two sides")

            by_name: dict[str, float] = {}
            for outcome in outcomes:
                if not isinstance(outcome, dict):
                    raise TheOddsApiSyntheticAdapterError("outcome must be an object")
                name = _required_text(outcome.get("name"), "outcome.name")
                if name in by_name:
                    raise TheOddsApiSyntheticAdapterError("duplicate h2h outcome name")
                by_name[name] = _decimal_price(outcome.get("price"), f"outcome[{name}].price")

            if set(by_name) != {home_team, away_team}:
                raise TheOddsApiSyntheticAdapterError("h2h outcomes must match home and away teams exactly")

            output.append(
                {
                    "source_id": SOURCE_ID,
                    "adapter_id": ADAPTER_ID,
                    "adapter_version": ADAPTER_VERSION,
                    "source_event_id": event_id,
                    "canonical_game_id": None,
                    "league": "NBA",
                    "season_label": None,
                    "competition_type": None,
                    "home_team_source": home_team,
                    "away_team_source": away_team,
                    "scheduled_tipoff_utc": commence_time,
                    "bookmaker_key": bookmaker_key,
                    "market_key": "h2h",
                    "home_price_decimal": by_name[home_team],
                    "away_price_decimal": by_name[away_team],
                    "provider_snapshot_at_utc": None,
                    "bookmaker_last_update_utc": quote_observed_at,
                    "collector_fetched_at_utc": _required_text(
                        collector_fetched_at_utc, "collector_fetched_at_utc"
                    ),
                    "quote_time_authority": "bookmaker_last_update",
                    "mapping_state": "unmapped",
                    "source_rights_state": "unreviewed",
                    "raw_payload_retained": False,
                }
            )

    if not output:
        raise TheOddsApiSyntheticAdapterError("no same-bookmaker two-sided h2h market found")
    return output
