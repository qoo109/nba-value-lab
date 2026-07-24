#!/usr/bin/env python3
"""Offline HoopsAPI-shaped adapter shell for synthetic fixtures only.

This module has no HTTP client, secret reader, account workflow or scheduler. It
translates a synthetic payload shaped after the public HoopsAPI example into the
provider-neutral private forward quote contract. Because public evidence does
not establish a provider-origin quote timestamp, every emitted row is fail-closed:
`quote_time_authority=unverified`, `quote_observed_at_utc=None`, and
`point_in_time_eligible=False` after collector validation.
"""
from __future__ import annotations

from typing import Any

ADAPTER_ID = "hoopsapi-private-forward-adapter-synthetic-shell-v1"
ADAPTER_VERSION = "1.0.0"
SOURCE_ID = "hoopsapi_free_forward_collection"


class HoopsApiSyntheticAdapterError(ValueError):
    """Raised when a synthetic fixture does not match the adapter shell contract."""


def _required_text(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise HoopsApiSyntheticAdapterError(f"{field} is required")
    return text


def _decimal_price(value: Any, field: str) -> float:
    try:
        price = float(value)
    except (TypeError, ValueError) as exc:
        raise HoopsApiSyntheticAdapterError(f"{field} must be numeric") from exc
    if not 1.001 <= price <= 100.0:
        raise HoopsApiSyntheticAdapterError(f"{field} outside allowed decimal range")
    return round(price, 8)


def adapt_synthetic_game(payload: dict[str, Any], *, collector_fetched_at_utc: str) -> list[dict[str, Any]]:
    """Normalize one synthetic HoopsAPI-shaped game into collector input rows.

    Only a same-provider two-sided Moneyline is accepted. Provider and quote
    timestamps are intentionally not inferred from collector receipt time.
    """
    if not isinstance(payload, dict):
        raise HoopsApiSyntheticAdapterError("payload must be an object")

    game_id = _required_text(payload.get("id"), "id")
    home = payload.get("homeTeam")
    away = payload.get("awayTeam")
    if not isinstance(home, dict) or not isinstance(away, dict):
        raise HoopsApiSyntheticAdapterError("homeTeam and awayTeam must be objects")

    home_name = _required_text(home.get("name"), "homeTeam.name")
    away_name = _required_text(away.get("name"), "awayTeam.name")
    scheduled = _required_text(payload.get("startTime"), "startTime")

    providers = payload.get("providers")
    if not isinstance(providers, list) or not providers:
        raise HoopsApiSyntheticAdapterError("providers must be a non-empty list")

    output: list[dict[str, Any]] = []
    for provider in providers:
        if not isinstance(provider, dict):
            raise HoopsApiSyntheticAdapterError("provider must be an object")
        provider_key = _required_text(provider.get("key"), "provider.key")
        markets = provider.get("markets")
        if not isinstance(markets, dict):
            raise HoopsApiSyntheticAdapterError("provider.markets must be an object")
        h2h = markets.get("h2h")
        if not isinstance(h2h, dict):
            continue

        home_price = _decimal_price(h2h.get("home"), "provider.markets.h2h.home")
        away_price = _decimal_price(h2h.get("away"), "provider.markets.h2h.away")

        output.append(
            {
                "source_id": SOURCE_ID,
                "adapter_id": ADAPTER_ID,
                "adapter_version": ADAPTER_VERSION,
                "source_event_id": game_id,
                "canonical_game_id": None,
                "league": "NBA",
                "season_label": None,
                "competition_type": None,
                "home_team_source": home_name,
                "away_team_source": away_name,
                "scheduled_tipoff_utc": scheduled,
                "bookmaker_key": provider_key,
                "market_key": "h2h",
                "home_price_decimal": home_price,
                "away_price_decimal": away_price,
                "provider_snapshot_at_utc": None,
                "bookmaker_last_update_utc": None,
                "collector_fetched_at_utc": collector_fetched_at_utc,
                "quote_time_authority": "unverified",
                "mapping_state": "unmapped",
                "source_rights_state": "unreviewed",
                "raw_payload_retained": False,
            }
        )

    if not output:
        raise HoopsApiSyntheticAdapterError("no same-provider two-sided h2h market found")
    return output
