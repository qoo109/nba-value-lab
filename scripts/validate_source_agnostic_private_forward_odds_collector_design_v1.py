#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DESIGN_PATH = ROOT / "data/research/source-agnostic-private-forward-odds-collector-design-v1.json"
SCHEMA_PATH = ROOT / "schemas/private-forward-odds-quote-v1.schema.json"
STATUS_PATH = ROOT / "data/research/no-cost-timestamped-odds-source-qualification-current-status-v5.json"
DOC_PATH = ROOT / "docs/source-agnostic-private-forward-odds-collector-v1.md"
HANDOFF_PATH = ROOT / "docs/handoffs/nba_value_lab_handoff_2026-07-24_source_agnostic_private_forward_collector_design.md"
PROJECT_STATUS_PATH = ROOT / "PROJECT_STATUS.md"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_utc(value: str | None) -> datetime | None:
    if value is None:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def synthetic_time_gate(record: dict[str, Any]) -> bool:
    authority = record["quote_time_authority"]
    observed = parse_utc(record.get("quote_observed_at_utc"))
    provider = parse_utc(record.get("provider_snapshot_at_utc"))
    book = parse_utc(record.get("bookmaker_last_update_utc"))
    fetched = parse_utc(record["collector_fetched_at_utc"])
    tipoff = parse_utc(record["scheduled_tipoff_utc"])
    assert fetched is not None and tipoff is not None

    if authority == "provider_snapshot":
        if provider is None or observed != provider:
            return False
    elif authority == "bookmaker_last_update":
        if book is None or observed != book:
            return False
    elif authority == "unverified":
        if observed is not None:
            return False
        return False
    else:
        return False

    if observed is None or observed >= tipoff:
        return False
    if fetched < observed:
        return False
    if record.get("mapping_state") != "exact":
        return False
    if record.get("source_rights_state") != "private_research_allowed":
        return False
    return True


def run_synthetic_contract_tests() -> dict[str, bool]:
    base = {
        "scheduled_tipoff_utc": "2026-10-21T00:00:00Z",
        "provider_snapshot_at_utc": "2026-10-20T22:59:30Z",
        "bookmaker_last_update_utc": "2026-10-20T22:59:00Z",
        "collector_fetched_at_utc": "2026-10-20T23:00:00Z",
        "quote_observed_at_utc": "2026-10-20T22:59:30Z",
        "quote_time_authority": "provider_snapshot",
        "mapping_state": "exact",
        "source_rights_state": "private_research_allowed",
    }

    tests: dict[str, bool] = {}
    tests["provider_snapshot_authority_passes"] = synthetic_time_gate(dict(base)) is True

    bookmaker = dict(base)
    bookmaker["quote_time_authority"] = "bookmaker_last_update"
    bookmaker["quote_observed_at_utc"] = bookmaker["bookmaker_last_update_utc"]
    tests["bookmaker_update_authority_passes"] = synthetic_time_gate(bookmaker) is True

    unverified = dict(base)
    unverified["quote_time_authority"] = "unverified"
    unverified["quote_observed_at_utc"] = None
    tests["unverified_time_is_not_eligible"] = synthetic_time_gate(unverified) is False

    fetched_substitution = dict(unverified)
    fetched_substitution["quote_observed_at_utc"] = fetched_substitution["collector_fetched_at_utc"]
    tests["fetched_at_substitution_rejected"] = synthetic_time_gate(fetched_substitution) is False

    future = dict(base)
    future["provider_snapshot_at_utc"] = "2026-10-21T00:00:01Z"
    future["quote_observed_at_utc"] = future["provider_snapshot_at_utc"]
    future["collector_fetched_at_utc"] = "2026-10-21T00:00:02Z"
    tests["post_tipoff_quote_rejected"] = synthetic_time_gate(future) is False

    fetched_before = dict(base)
    fetched_before["collector_fetched_at_utc"] = "2026-10-20T22:59:00Z"
    tests["fetched_before_observed_rejected"] = synthetic_time_gate(fetched_before) is False

    unmapped = dict(base)
    unmapped["mapping_state"] = "unmapped"
    tests["unmapped_quote_rejected"] = synthetic_time_gate(unmapped) is False

    rights_unknown = dict(base)
    rights_unknown["source_rights_state"] = "unreviewed"
    tests["unreviewed_rights_rejected"] = synthetic_time_gate(rights_unknown) is False

    if not all(tests.values()):
        failed = sorted(name for name, passed in tests.items() if not passed)
        raise SystemExit(f"synthetic contract tests failed: {failed}")
    return tests


def main() -> None:
    design = load_json(DESIGN_PATH)
    schema = load_json(SCHEMA_PATH)
    current = load_json(STATUS_PATH)
    doc = DOC_PATH.read_text(encoding="utf-8")
    handoff = HANDOFF_PATH.read_text(encoding="utf-8")
    project_status = PROJECT_STATUS_PATH.read_text(encoding="utf-8")

    assert design["formal_state"] == "SOURCE_AGNOSTIC_PRIVATE_FORWARD_ODDS_COLLECTOR_DESIGN_VALIDATED"
    assert design["v1_scope"]["direction"] == "forward_only"
    assert design["v1_scope"]["historical_backfill"] is False
    assert design["v1_scope"]["closing_substitution_for_t60_or_t5"] is False
    assert design["adapter_contract"]["network_client_included"] is False
    assert design["adapter_contract"]["secret_reader_included"] is False
    assert design["timestamp_contract"]["quote_observed_at_utc"].startswith("Nullable")
    assert any("never substitute" in rule for rule in design["timestamp_contract"]["eligibility_rules"])
    assert design["event_mapping_contract"]["fuzzy_matching_allowed"] is False
    assert design["event_mapping_contract"]["season_or_competition_inference_allowed"] is False
    assert design["quote_contract"]["same_book_two_sided_required"] is True
    assert design["quote_contract"]["snapshot_label_at_ingest"] is False
    assert design["private_storage_contract"]["public_repository_quote_rows_allowed"] is False
    assert design["private_storage_contract"]["public_artifact_quote_rows_allowed"] is False
    assert design["activation_boundary"]["network_requests_authorized"] is False
    assert design["activation_boundary"]["real_quote_ingestion_authorized"] is False
    assert design["activation_boundary"]["market_backtest_authorized"] is False
    assert design["activation_boundary"]["formal_stake"] == 0
    assert design["next_unique_mainline"] == "IMPLEMENT_SOURCE_AGNOSTIC_PRIVATE_FORWARD_ODDS_COLLECTOR_OFFLINE_CORE_V1"

    assert schema["$schema"].endswith("2020-12/schema")
    assert schema["schema_version"] == "1.0.0"
    assert schema["additionalProperties"] is False
    required = set(schema["required"])
    for field in (
        "source_event_id",
        "scheduled_tipoff_utc",
        "bookmaker_key",
        "home_price_decimal",
        "away_price_decimal",
        "collector_fetched_at_utc",
        "quote_observed_at_utc",
        "quote_time_authority",
        "point_in_time_eligible",
        "mapping_state",
        "source_rights_state",
        "normalized_row_sha256",
    ):
        assert field in required
    assert schema["properties"]["market_key"]["const"] == "h2h"
    assert "snapshot_label" not in schema["properties"]

    assert current["formal_state"] == "NO_COST_TIMESTAMPED_ODDS_PRIVATE_FORWARD_COLLECTOR_DESIGN_VALIDATED"
    assert isinstance(current["recording_pr"], int) and current["recording_pr"] > 0
    assert current["collector_design"]["source_agnostic"] is True
    assert current["collector_design"]["collector_fetched_at_may_substitute_observed_at"] is False
    assert current["collector_design"]["provider_requests_executed"] == 0
    assert current["next_unique_mainline"] == "IMPLEMENT_SOURCE_AGNOSTIC_PRIVATE_FORWARD_ODDS_COLLECTOR_OFFLINE_CORE_V1"
    assert current["next_task_requires_account_or_api_key"] is False
    assert current["next_task_executes_provider_requests"] is False
    assert current["provider_request_execution_authorized"] is False
    assert current["real_quote_ingestion_authorized"] is False
    assert current["market_backtest_unlocked"] is False
    assert current["formal_stake"] == 0

    required_text = (
        "SOURCE_AGNOSTIC_PRIVATE_FORWARD_ODDS_COLLECTOR_DESIGN_VALIDATED",
        "collector_fetched_at_utc NEVER substitutes quote_observed_at_utc",
        "IMPLEMENT_SOURCE_AGNOSTIC_PRIVATE_FORWARD_ODDS_COLLECTOR_OFFLINE_CORE_V1",
        "Formal Stake",
    )
    for text, label in ((doc, "documentation"), (handoff, "handoff")):
        for item in required_text:
            if item not in text:
                raise SystemExit(f"missing {label} evidence: {item}")

    for item in (
        "forward odds collector design: VALIDATED / SOURCE-AGNOSTIC / PRIVATE",
        "forward collector fetched_at substitution: PROHIBITED",
        "forward collector provider requests executed: 0",
        "IMPLEMENT_SOURCE_AGNOSTIC_PRIVATE_FORWARD_ODDS_COLLECTOR_OFFLINE_CORE_V1",
        "READY — OFFLINE IMPLEMENTATION ONLY / NETWORK DISABLED",
        "formal stake: 0",
    ):
        if item not in project_status:
            raise SystemExit(f"missing PROJECT_STATUS evidence: {item}")

    synthetic_tests = run_synthetic_contract_tests()
    report = {
        "schema_version": 1,
        "formal_state": "SOURCE_AGNOSTIC_PRIVATE_FORWARD_ODDS_COLLECTOR_DESIGN_VALID",
        "design_valid": True,
        "quote_schema_valid": True,
        "source_agnostic": True,
        "forward_only": True,
        "private_storage_only": True,
        "fetched_at_substitution_allowed": False,
        "network_client_included": False,
        "secret_reader_included": False,
        "provider_requests_executed": 0,
        "real_quotes_retained": False,
        "public_quote_rows_allowed": False,
        "historical_backfill_authorized": False,
        "market_backtest_executed": False,
        "market_metrics_executed": False,
        "synthetic_contract_tests": len(synthetic_tests),
        "formal_stake": 0,
        "next_unique_mainline": "IMPLEMENT_SOURCE_AGNOSTIC_PRIVATE_FORWARD_ODDS_COLLECTOR_OFFLINE_CORE_V1",
    }
    forbidden_fragments = ("home_price", "away_price", "raw_payload", "api_key")
    report_text = json.dumps(report, sort_keys=True)
    for fragment in forbidden_fragments:
        if fragment in report_text:
            raise SystemExit(f"aggregate report leaked forbidden fragment: {fragment}")

    out = ROOT / "build/source-agnostic-private-forward-odds-collector-design-validation-v1.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
