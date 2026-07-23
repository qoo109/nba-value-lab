#!/usr/bin/env python3
"""Offline-only, provider-neutral private NBA moneyline collector core.

This module intentionally contains no HTTP client, no secret reader and no scheduler.
It accepts already-provided payload dictionaries, normalizes them into the private
forward quote contract, writes only to a caller-supplied private SQLite path and
returns aggregate QA that contains no quote prices or quote-level identities.
"""
from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

CORE_VERSION = "source-agnostic-private-forward-odds-collector-offline-core-v1"
SCHEMA_VERSION = "private-forward-odds-quote-v1"
ALLOWED_AUTHORITIES = {"provider_snapshot", "bookmaker_last_update", "unverified"}
ALLOWED_MAPPING_STATES = {"exact", "unmapped", "quarantined"}
ALLOWED_RIGHTS_STATES = {
    "unreviewed",
    "private_research_allowed",
    "private_retention_restricted",
    "blocked",
}


class CollectorContractError(ValueError):
    """Raised when a synthetic/offline quote violates the collector contract."""


def parse_utc(value: Any, field: str, *, nullable: bool = False) -> datetime | None:
    if value is None:
        if nullable:
            return None
        raise CollectorContractError(f"{field} is required")
    text = str(value).strip()
    if not text:
        if nullable:
            return None
        raise CollectorContractError(f"{field} is required")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise CollectorContractError(f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise CollectorContractError(f"{field} must include timezone")
    return parsed.astimezone(timezone.utc)


def iso_z(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def decimal_price(value: Any, field: str) -> float:
    try:
        price = float(value)
    except (TypeError, ValueError) as exc:
        raise CollectorContractError(f"{field} must be numeric") from exc
    if not math.isfinite(price) or not 1.001 <= price <= 100.0:
        raise CollectorContractError(f"{field} outside allowed decimal range")
    return round(price, 8)


def nonblank(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise CollectorContractError(f"{field} is required")
    return text


def canonical_hash_payload(record: dict[str, Any]) -> dict[str, Any]:
    """Return the frozen provider-neutral dedup key from the design contract.

    Run identity and adapter metadata are deliberately excluded so the same quote
    observed again in a later collector run is counted as a duplicate rather than
    inserted as a second coverage row.
    """
    return {
        key: record.get(key)
        for key in (
            "source_id",
            "source_event_id",
            "bookmaker_key",
            "market_key",
            "quote_time_authority",
            "quote_observed_at_utc",
            "collector_fetched_at_utc",
            "home_price_decimal",
            "away_price_decimal",
        )
    }


def deterministic_row_hash(record: dict[str, Any]) -> str:
    payload = json.dumps(canonical_hash_payload(record), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def derive_time_authority(item: dict[str, Any]) -> tuple[str, datetime | None, list[str]]:
    authority = str(item.get("quote_time_authority") or "unverified").strip()
    if authority not in ALLOWED_AUTHORITIES:
        raise CollectorContractError("quote_time_authority is invalid")
    provider = parse_utc(item.get("provider_snapshot_at_utc"), "provider_snapshot_at_utc", nullable=True)
    bookmaker = parse_utc(item.get("bookmaker_last_update_utc"), "bookmaker_last_update_utc", nullable=True)
    flags: list[str] = []

    if authority == "provider_snapshot":
        if provider is None:
            raise CollectorContractError("provider_snapshot authority requires provider timestamp")
        observed = provider
    elif authority == "bookmaker_last_update":
        if bookmaker is None:
            raise CollectorContractError("bookmaker_last_update authority requires bookmaker timestamp")
        observed = bookmaker
    else:
        observed = None
        flags.append("timestamp_unverified")
    return authority, observed, flags


def normalize_quote(item: dict[str, Any], collector_run_id: str) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise CollectorContractError("quote must be an object")

    scheduled = parse_utc(item.get("scheduled_tipoff_utc"), "scheduled_tipoff_utc")
    fetched = parse_utc(item.get("collector_fetched_at_utc"), "collector_fetched_at_utc")
    assert scheduled is not None and fetched is not None
    authority, observed, flags = derive_time_authority(item)
    provider = parse_utc(item.get("provider_snapshot_at_utc"), "provider_snapshot_at_utc", nullable=True)
    bookmaker_update = parse_utc(
        item.get("bookmaker_last_update_utc"), "bookmaker_last_update_utc", nullable=True
    )

    for provider_time, label in (
        (provider, "provider_snapshot_after_fetch"),
        (bookmaker_update, "bookmaker_update_after_fetch"),
    ):
        if provider_time is not None and provider_time > fetched:
            raise CollectorContractError(label)

    mapping_state = str(item.get("mapping_state") or "unmapped").strip()
    if mapping_state not in ALLOWED_MAPPING_STATES:
        raise CollectorContractError("mapping_state is invalid")
    canonical_game_id = item.get("canonical_game_id")
    if canonical_game_id is not None:
        canonical_game_id = nonblank(canonical_game_id, "canonical_game_id")
    if mapping_state == "exact" and canonical_game_id is None:
        raise CollectorContractError("exact mapping requires canonical_game_id")

    rights = str(item.get("source_rights_state") or "unreviewed").strip()
    if rights not in ALLOWED_RIGHTS_STATES:
        raise CollectorContractError("source_rights_state is invalid")

    market_key = str(item.get("market_key") or "").strip().lower()
    if market_key != "h2h":
        raise CollectorContractError("market_key must equal h2h")

    home_price = decimal_price(item.get("home_price_decimal"), "home_price_decimal")
    away_price = decimal_price(item.get("away_price_decimal"), "away_price_decimal")

    if observed is not None and observed >= scheduled:
        raise CollectorContractError("quote timestamp must be before tipoff")
    if fetched >= scheduled:
        flags.append("fetched_at_or_after_tipoff")

    eligible = bool(
        observed is not None
        and observed < scheduled
        and fetched >= observed
        and mapping_state == "exact"
        and rights == "private_research_allowed"
    )
    if not eligible:
        flags.append("point_in_time_ineligible")

    raw_payload_retained = bool(item.get("raw_payload_retained", False))
    if raw_payload_retained:
        raise CollectorContractError("raw payload retention is disabled in offline core v1")

    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "collector_run_id": collector_run_id,
        "quote_snapshot_id": "pending",
        "source_id": nonblank(item.get("source_id"), "source_id"),
        "adapter_id": nonblank(item.get("adapter_id"), "adapter_id"),
        "adapter_version": nonblank(item.get("adapter_version"), "adapter_version"),
        "source_event_id": nonblank(item.get("source_event_id"), "source_event_id"),
        "canonical_game_id": canonical_game_id,
        "league": "NBA",
        "season_label": item.get("season_label"),
        "competition_type": item.get("competition_type"),
        "home_team_source": nonblank(item.get("home_team_source"), "home_team_source"),
        "away_team_source": nonblank(item.get("away_team_source"), "away_team_source"),
        "scheduled_tipoff_utc": iso_z(scheduled),
        "bookmaker_key": nonblank(item.get("bookmaker_key"), "bookmaker_key"),
        "market_key": "h2h",
        "home_price_decimal": home_price,
        "away_price_decimal": away_price,
        "provider_snapshot_at_utc": iso_z(provider),
        "bookmaker_last_update_utc": iso_z(bookmaker_update),
        "collector_fetched_at_utc": iso_z(fetched),
        "quote_observed_at_utc": iso_z(observed),
        "quote_time_authority": authority,
        "point_in_time_eligible": eligible,
        "mapping_state": mapping_state,
        "source_rights_state": rights,
        "raw_payload_retained": False,
        "raw_payload_sha256": None,
        "normalized_row_sha256": "pending",
        "quality_flags": sorted(set(flags)),
    }
    row_hash = deterministic_row_hash(record)
    record["normalized_row_sha256"] = row_hash
    record["quote_snapshot_id"] = f"q_{row_hash[:24]}"
    return record


@dataclass(frozen=True)
class OfflineCollectionResult:
    aggregate_qa: dict[str, Any]
    private_db_path: Path


class PrivateForwardOddsStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(path))
        self.connection.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self.connection.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS collector_runs (
              collector_run_id TEXT PRIMARY KEY,
              core_version TEXT NOT NULL,
              started_at_utc TEXT NOT NULL,
              input_count INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS quotes (
              normalized_row_sha256 TEXT PRIMARY KEY,
              collector_run_id TEXT NOT NULL,
              quote_snapshot_id TEXT NOT NULL,
              source_id TEXT NOT NULL,
              adapter_id TEXT NOT NULL,
              adapter_version TEXT NOT NULL,
              source_event_id TEXT NOT NULL,
              canonical_game_id TEXT,
              league TEXT NOT NULL,
              season_label TEXT,
              competition_type TEXT,
              home_team_source TEXT NOT NULL,
              away_team_source TEXT NOT NULL,
              scheduled_tipoff_utc TEXT NOT NULL,
              bookmaker_key TEXT NOT NULL,
              market_key TEXT NOT NULL,
              home_price_decimal REAL NOT NULL,
              away_price_decimal REAL NOT NULL,
              provider_snapshot_at_utc TEXT,
              bookmaker_last_update_utc TEXT,
              collector_fetched_at_utc TEXT NOT NULL,
              quote_observed_at_utc TEXT,
              quote_time_authority TEXT NOT NULL,
              point_in_time_eligible INTEGER NOT NULL,
              mapping_state TEXT NOT NULL,
              source_rights_state TEXT NOT NULL,
              raw_payload_retained INTEGER NOT NULL,
              raw_payload_sha256 TEXT,
              quality_flags_json TEXT NOT NULL,
              FOREIGN KEY (collector_run_id) REFERENCES collector_runs(collector_run_id)
            );
            CREATE TABLE IF NOT EXISTS quarantine (
              quarantine_id INTEGER PRIMARY KEY AUTOINCREMENT,
              collector_run_id TEXT NOT NULL,
              source_id TEXT,
              adapter_id TEXT,
              reason_code TEXT NOT NULL,
              payload_sha256 TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    def begin_run(self, collector_run_id: str, started_at_utc: str, input_count: int) -> None:
        self.connection.execute(
            "INSERT INTO collector_runs VALUES (?, ?, ?, ?)",
            (collector_run_id, CORE_VERSION, started_at_utc, input_count),
        )
        self.connection.commit()

    def insert_quote(self, record: dict[str, Any]) -> bool:
        columns = [
            "normalized_row_sha256", "collector_run_id", "quote_snapshot_id", "source_id",
            "adapter_id", "adapter_version", "source_event_id", "canonical_game_id", "league",
            "season_label", "competition_type", "home_team_source", "away_team_source",
            "scheduled_tipoff_utc", "bookmaker_key", "market_key", "home_price_decimal",
            "away_price_decimal", "provider_snapshot_at_utc", "bookmaker_last_update_utc",
            "collector_fetched_at_utc", "quote_observed_at_utc", "quote_time_authority",
            "point_in_time_eligible", "mapping_state", "source_rights_state",
            "raw_payload_retained", "raw_payload_sha256", "quality_flags_json",
        ]
        values = [record.get(column) for column in columns]
        values[columns.index("point_in_time_eligible")] = int(record["point_in_time_eligible"])
        values[columns.index("raw_payload_retained")] = int(record["raw_payload_retained"])
        values[columns.index("quality_flags_json")] = json.dumps(record["quality_flags"], sort_keys=True)
        placeholders = ",".join("?" for _ in columns)
        try:
            self.connection.execute(
                f"INSERT INTO quotes ({','.join(columns)}) VALUES ({placeholders})", values
            )
            self.connection.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def quarantine(self, collector_run_id: str, item: Any, reason_code: str) -> None:
        stable = json.dumps(item, sort_keys=True, default=str, separators=(",", ":"))
        payload_hash = hashlib.sha256(stable.encode("utf-8")).hexdigest()
        source_id = item.get("source_id") if isinstance(item, dict) else None
        adapter_id = item.get("adapter_id") if isinstance(item, dict) else None
        self.connection.execute(
            "INSERT INTO quarantine (collector_run_id, source_id, adapter_id, reason_code, payload_sha256) VALUES (?, ?, ?, ?, ?)",
            (collector_run_id, source_id, adapter_id, reason_code, payload_hash),
        )
        self.connection.commit()

    def aggregate_counts(self) -> dict[str, Any]:
        quote_count = self.connection.execute("SELECT COUNT(*) FROM quotes").fetchone()[0]
        eligible_count = self.connection.execute(
            "SELECT COUNT(*) FROM quotes WHERE point_in_time_eligible = 1"
        ).fetchone()[0]
        quarantine_count = self.connection.execute("SELECT COUNT(*) FROM quarantine").fetchone()[0]
        mapping_counts = {
            row[0]: row[1]
            for row in self.connection.execute(
                "SELECT mapping_state, COUNT(*) FROM quotes GROUP BY mapping_state ORDER BY mapping_state"
            )
        }
        authority_counts = {
            row[0]: row[1]
            for row in self.connection.execute(
                "SELECT quote_time_authority, COUNT(*) FROM quotes GROUP BY quote_time_authority ORDER BY quote_time_authority"
            )
        }
        return {
            "private_quote_rows": quote_count,
            "point_in_time_eligible_rows": eligible_count,
            "quarantined_rows": quarantine_count,
            "mapping_state_counts": mapping_counts,
            "timestamp_authority_counts": authority_counts,
        }

    def close(self) -> None:
        self.connection.close()


def collect_offline(
    payloads: Iterable[dict[str, Any]],
    *,
    collector_run_id: str,
    private_db_path: Path,
    started_at_utc: str,
) -> OfflineCollectionResult:
    items = list(payloads)
    nonblank(collector_run_id, "collector_run_id")
    parse_utc(started_at_utc, "started_at_utc")
    store = PrivateForwardOddsStore(private_db_path)
    duplicate_count = 0
    normalized_count = 0
    try:
        store.begin_run(collector_run_id, started_at_utc, len(items))
        for item in items:
            try:
                record = normalize_quote(item, collector_run_id)
            except CollectorContractError as exc:
                reason = str(exc).split(":", 1)[0].replace(" ", "_").lower()[:120]
                store.quarantine(collector_run_id, item, reason)
                continue
            if store.insert_quote(record):
                normalized_count += 1
            else:
                duplicate_count += 1
        counts = store.aggregate_counts()
    finally:
        store.close()

    report = {
        "schema_version": 1,
        "formal_state": "SOURCE_AGNOSTIC_PRIVATE_FORWARD_ODDS_COLLECTOR_OFFLINE_CORE_VALID",
        "core_version": CORE_VERSION,
        "offline_only": True,
        "synthetic_inputs_only": True,
        "network_client_included": False,
        "secret_reader_included": False,
        "scheduler_included": False,
        "provider_requests_executed": 0,
        "real_provider_payloads_processed": 0,
        "input_records": len(items),
        "normalized_private_records": normalized_count,
        "duplicate_records": duplicate_count,
        **counts,
        "raw_payloads_retained": 0,
        "public_quote_rows_emitted": 0,
        "market_metrics_executed": False,
        "formal_stake": 0,
    }
    return OfflineCollectionResult(aggregate_qa=report, private_db_path=private_db_path)
