#!/usr/bin/env python3
from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

from private_forward_odds_collector_v1 import collect_offline

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data/fixtures/private-forward-odds-synthetic-v1.json"
DESIGN = ROOT / "data/research/source-agnostic-private-forward-odds-collector-offline-core-v1.json"
CURRENT = ROOT / "data/research/no-cost-timestamped-odds-source-qualification-current-status-v6.json"
DOC = ROOT / "docs/source-agnostic-private-forward-odds-collector-offline-core-v1.md"
HANDOFF = ROOT / "docs/handoffs/nba_value_lab_handoff_2026-07-24_private_forward_collector_offline_core.md"
PROJECT_STATUS = ROOT / "PROJECT_STATUS.md"
CORE = ROOT / "scripts/private_forward_odds_collector_v1.py"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    fixture = load(FIXTURE)
    policy = load(DESIGN)
    current = load(CURRENT)
    doc = DOC.read_text(encoding="utf-8")
    handoff = HANDOFF.read_text(encoding="utf-8")
    status = PROJECT_STATUS.read_text(encoding="utf-8")
    core_text = CORE.read_text(encoding="utf-8")

    assert policy["formal_state"] == "SOURCE_AGNOSTIC_PRIVATE_FORWARD_ODDS_COLLECTOR_OFFLINE_CORE_VALIDATED"
    assert policy["offline_only"] is True
    assert policy["synthetic_inputs_only"] is True
    assert policy["network_client_included"] is False
    assert policy["secret_reader_included"] is False
    assert policy["scheduler_included"] is False
    assert policy["real_quote_ingestion_authorized"] is False
    assert policy["market_backtest_authorized"] is False
    assert policy["formal_stake"] == 0

    forbidden_core_fragments = (
        "import requests",
        "from requests",
        "urllib.request",
        "http.client",
        "os.environ",
        "getenv(",
        "THE_ODDS_API_KEY",
        "BLOOMBET_API_KEY",
    )
    for fragment in forbidden_core_fragments:
        if fragment in core_text:
            raise SystemExit(f"offline core contains forbidden capability: {fragment}")

    with tempfile.TemporaryDirectory(prefix="nbavl-private-forward-") as tmp:
        db_path = Path(tmp) / "forward-odds.sqlite"
        result = collect_offline(
            fixture["quotes"],
            collector_run_id=fixture["collector_run_id"],
            private_db_path=db_path,
            started_at_utc=fixture["started_at_utc"],
        )
        report = result.aggregate_qa
        assert db_path.exists()
        connection = sqlite3.connect(str(db_path))
        try:
            quote_rows = connection.execute("SELECT COUNT(*) FROM quotes").fetchone()[0]
            eligible_rows = connection.execute(
                "SELECT COUNT(*) FROM quotes WHERE point_in_time_eligible = 1"
            ).fetchone()[0]
            unverified_rows = connection.execute(
                "SELECT COUNT(*) FROM quotes WHERE quote_time_authority = 'unverified' AND quote_observed_at_utc IS NULL"
            ).fetchone()[0]
            raw_payload_rows = connection.execute(
                "SELECT COUNT(*) FROM quotes WHERE raw_payload_retained != 0 OR raw_payload_sha256 IS NOT NULL"
            ).fetchone()[0]
            quarantine_rows = connection.execute("SELECT COUNT(*) FROM quarantine").fetchone()[0]
        finally:
            connection.close()

        assert report["formal_state"] == "SOURCE_AGNOSTIC_PRIVATE_FORWARD_ODDS_COLLECTOR_OFFLINE_CORE_VALID"
        assert report["input_records"] == 6
        assert report["normalized_private_records"] == 3
        assert report["duplicate_records"] == 1
        assert report["quarantined_rows"] == 2
        assert report["point_in_time_eligible_rows"] == 2
        assert report["provider_requests_executed"] == 0
        assert report["real_provider_payloads_processed"] == 0
        assert report["raw_payloads_retained"] == 0
        assert report["public_quote_rows_emitted"] == 0
        assert report["market_metrics_executed"] is False
        assert report["formal_stake"] == 0
        assert quote_rows == 3
        assert eligible_rows == 2
        assert unverified_rows == 1
        assert raw_payload_rows == 0
        assert quarantine_rows == 2

    assert current["formal_state"] == "NO_COST_TIMESTAMPED_ODDS_PRIVATE_FORWARD_COLLECTOR_OFFLINE_CORE_VALIDATED"
    assert isinstance(current["recording_pr"], int) and current["recording_pr"] > 0
    assert current["offline_core"]["network_client_included"] is False
    assert current["offline_core"]["provider_requests_executed"] == 0
    assert current["offline_core"]["synthetic_contract_tests"] == 12
    assert current["next_unique_mainline"] == "DESIGN_FIRST_PROVIDER_PRIVATE_FORWARD_ADAPTER_QUALIFICATION_GATE_V1"
    assert current["formal_stake"] == 0

    required_text = (
        "SOURCE_AGNOSTIC_PRIVATE_FORWARD_ODDS_COLLECTOR_OFFLINE_CORE_VALIDATED",
        "collector_fetched_at_utc NEVER substitutes quote_observed_at_utc",
        "DESIGN_FIRST_PROVIDER_PRIVATE_FORWARD_ADAPTER_QUALIFICATION_GATE_V1",
        "Formal Stake",
    )
    for text, label in ((doc, "documentation"), (handoff, "handoff")):
        for item in required_text:
            if item not in text:
                raise SystemExit(f"missing {label} evidence: {item}")

    for item in (
        "forward odds collector offline core: VALIDATED / SYNTHETIC ONLY",
        "forward collector offline SQLite writes: TEMPORARY PRIVATE ONLY",
        "forward collector offline synthetic tests: 12 / PASS",
        "forward collector offline provider requests executed: 0",
        "DESIGN_FIRST_PROVIDER_PRIVATE_FORWARD_ADAPTER_QUALIFICATION_GATE_V1",
        "READY — DESIGN ONLY / NO PROVIDER EXECUTION",
        "formal stake: 0",
    ):
        if item not in status:
            raise SystemExit(f"missing PROJECT_STATUS evidence: {item}")

    public_report = {
        **report,
        "synthetic_contract_tests": 12,
        "sqlite_private_write_valid": True,
        "deduplication_valid": True,
        "quarantine_valid": True,
        "unverified_timestamp_fail_closed": True,
        "aggregate_only_output_valid": True,
        "next_unique_mainline": "DESIGN_FIRST_PROVIDER_PRIVATE_FORWARD_ADAPTER_QUALIFICATION_GATE_V1",
    }
    text = json.dumps(public_report, sort_keys=True)
    for forbidden in (
        "home_price_decimal",
        "away_price_decimal",
        "source_event_id",
        "canonical_game_id",
        "home_team_source",
        "away_team_source",
        "raw_payload_sha256",
        "api_key",
    ):
        if forbidden in text:
            raise SystemExit(f"aggregate artifact leaked forbidden field: {forbidden}")

    out = ROOT / "build/private-forward-odds-collector-offline-core-validation-v1.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(public_report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(public_report, indent=2))


if __name__ == "__main__":
    main()
