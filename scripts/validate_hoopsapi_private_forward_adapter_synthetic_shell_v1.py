#!/usr/bin/env python3
"""Validate the offline HoopsAPI synthetic adapter shell and aggregate-only QA."""
from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

from hoopsapi_private_forward_adapter_v1 import (
    ADAPTER_ID,
    SOURCE_ID,
    HoopsApiSyntheticAdapterError,
    adapt_synthetic_game,
)
from private_forward_odds_collector_v1 import collect_offline

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/hoopsapi_private_forward_synthetic_game_v1.json"
OUTPUT = ROOT / "build/hoopsapi-private-forward-adapter-synthetic-shell-validation-v1.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    adapted = adapt_synthetic_game(payload, collector_fetched_at_utc="2026-07-24T05:00:00Z")

    require(len(adapted) == 1, "fixture must emit one same-book h2h row")
    row = adapted[0]
    require(row["source_id"] == SOURCE_ID, "source id mismatch")
    require(row["adapter_id"] == ADAPTER_ID, "adapter id mismatch")
    require(row["quote_time_authority"] == "unverified", "timestamp must fail closed")
    require(row["provider_snapshot_at_utc"] is None, "provider timestamp must remain null")
    require(row["bookmaker_last_update_utc"] is None, "bookmaker timestamp must remain null")
    require(row["mapping_state"] == "unmapped", "synthetic event must not be mapped")
    require(row["source_rights_state"] == "unreviewed", "rights must remain unreviewed")
    require(row["raw_payload_retained"] is False, "raw payload retention must be disabled")

    invalid_single_side = json.loads(json.dumps(payload))
    del invalid_single_side["providers"][0]["markets"]["h2h"]["away"]
    try:
        adapt_synthetic_game(invalid_single_side, collector_fetched_at_utc="2026-07-24T05:00:00Z")
    except HoopsApiSyntheticAdapterError:
        single_side_rejected = True
    else:
        single_side_rejected = False
    require(single_side_rejected, "single-sided moneyline must be rejected")

    with tempfile.TemporaryDirectory(prefix="nba-value-lab-hoopsapi-shell-") as temp_dir:
        db_path = Path(temp_dir) / "private-forward.sqlite"
        result = collect_offline(
            adapted,
            collector_run_id="synthetic-hoopsapi-shell-validation-v1",
            private_db_path=db_path,
            started_at_utc="2026-07-24T05:00:00Z",
        )
        qa = result.aggregate_qa
        require(qa["normalized_private_records"] == 1, "collector must normalize one row")
        require(qa["point_in_time_eligible_rows"] == 0, "unverified timestamp cannot be PIT eligible")
        require(qa["provider_requests_executed"] == 0, "network requests must remain zero")
        require(qa["real_provider_payloads_processed"] == 0, "real payload count must remain zero")
        require(qa["public_quote_rows_emitted"] == 0, "public quote rows must remain zero")
        require(qa["market_metrics_executed"] is False, "market metrics must remain disabled")
        require(qa["formal_stake"] == 0, "formal stake must remain zero")

        connection = sqlite3.connect(db_path)
        stored = connection.execute(
            "SELECT quote_time_authority, quote_observed_at_utc, point_in_time_eligible, mapping_state, source_rights_state FROM quotes"
        ).fetchone()
        connection.close()
        require(stored == ("unverified", None, 0, "unmapped", "unreviewed"), "stored row did not fail closed")

    report = {
        "schema_version": "hoopsapi-private-forward-adapter-synthetic-shell-validation-v1",
        "formal_state": "HOOPSAPI_PRIVATE_FORWARD_ADAPTER_SYNTHETIC_SHELL_VALID",
        "adapter_id": ADAPTER_ID,
        "source_id": SOURCE_ID,
        "synthetic_fixture_only": True,
        "network_client_included": False,
        "secret_reader_included": False,
        "account_workflow_included": False,
        "provider_requests_executed": 0,
        "real_provider_payloads_processed": 0,
        "synthetic_rows_emitted": 1,
        "timestamp_authority": "unverified",
        "quote_observed_at_utc": None,
        "point_in_time_eligible_rows": 0,
        "single_sided_market_rejected": True,
        "raw_payloads_retained": 0,
        "public_quote_rows_emitted": 0,
        "market_metrics_executed": False,
        "formal_stake": 0,
        "next_unique_mainline": "DESIGN_HOOPSAPI_PRIVATE_RUNTIME_PREFLIGHT_REQUEST_V1",
        "runtime_preflight_authorized": False
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
