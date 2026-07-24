#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Callable

from g1_2_0_real_t60_intake_validator_v1 import IntakeValidationError, validate_intake

ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / "tests/fixtures/g1_2_0_real_t60_intake_contract_fixture_v1.json"
EVIDENCE_PATH = ROOT / "tests/fixtures/g1_2_0_real_t60_source_evidence_contract_fixture_v1.json"
RAW_PATH = ROOT / "tests/fixtures/g1_2_0_real_t60_raw_source_contract_fixture_v1.json"
DESIGN_PATH = ROOT / "data/research/g1-2-0-real-governed-t60-intake-validator-v1.json"
STATUS_PATH = ROOT / "data/research/no-cost-timestamped-odds-source-qualification-current-status-v10.json"
SCHEMA_PATH = ROOT / "schemas/g1-2-0-real-governed-t60-intake-v1.schema.json"
DOC_PATH = ROOT / "docs/g1-2-0-real-governed-t60-intake-validator-v1.md"
HANDOFF_PATH = ROOT / "docs/handoffs/nba_value_lab_handoff_2026-07-24_g120_real_t60_intake_validator.md"
OUTPUT = ROOT / "build/g1-2-0-real-governed-t60-intake-validator-validation-v1.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def expect_rejected(
    name: str,
    payload: dict[str, Any],
    evidence: dict[str, Any],
    *,
    normalized_bytes: bytes,
    raw_bytes: bytes,
    contract_test: bool = True,
) -> bool:
    try:
        validate_intake(
            payload,
            evidence,
            normalized_bytes=normalized_bytes,
            raw_source_bytes=raw_bytes,
            contract_test=contract_test,
        )
    except IntakeValidationError:
        return True
    raise AssertionError(f"scenario unexpectedly accepted: {name}")


def main() -> int:
    payload = load_json(INPUT_PATH)
    evidence = load_json(EVIDENCE_PATH)
    normalized_bytes = INPUT_PATH.read_bytes()
    raw_bytes = RAW_PATH.read_bytes()

    valid = validate_intake(
        payload,
        evidence,
        normalized_bytes=normalized_bytes,
        raw_source_bytes=raw_bytes,
        contract_test=True,
    )
    assert valid["formal_state"] == "G1_2_0_REAL_GOVERNED_T60_INPUT_INTAKE_CONTRACT_VALID"
    assert valid["game_count"] == 1
    assert valid["candidate_count"] == 2
    assert valid["fully_gated_game_count"] == 1
    assert valid["formal_history_write_authorized"] is False
    assert valid["market_metrics_executed"] is False
    assert valid["formal_stake"] == 0

    scenarios: dict[str, bool] = {"contract_fixture_passes_only_in_contract_mode": True}

    scenarios["contract_fixture_rejected_as_real"] = expect_rejected(
        "contract fixture as real",
        payload,
        evidence,
        normalized_bytes=normalized_bytes,
        raw_bytes=raw_bytes,
        contract_test=False,
    )

    def mutated_payload(mutator: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
        item = copy.deepcopy(payload)
        mutator(item)
        return item

    def mutated_evidence(mutator: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
        item = copy.deepcopy(evidence)
        mutator(item)
        return item

    bad = mutated_evidence(lambda item: item.__setitem__("source_rights_state", "unreviewed"))
    scenarios["unreviewed_rights_rejected"] = expect_rejected(
        "unreviewed rights", payload, bad, normalized_bytes=normalized_bytes, raw_bytes=raw_bytes
    )

    bad = mutated_evidence(lambda item: item.__setitem__("rights_reviewed_by_user", False))
    scenarios["rights_not_reviewed_by_user_rejected"] = expect_rejected(
        "rights not reviewed", payload, bad, normalized_bytes=normalized_bytes, raw_bytes=raw_bytes
    )

    bad = mutated_evidence(lambda item: item.__setitem__("provider_timestamp_semantics_verified", False))
    scenarios["unverified_timestamp_semantics_rejected"] = expect_rejected(
        "unverified timestamp semantics", payload, bad, normalized_bytes=normalized_bytes, raw_bytes=raw_bytes
    )

    bad = mutated_evidence(lambda item: item.__setitem__("quote_time_authority", "collector_fetched_at"))
    scenarios["collector_fetch_time_authority_rejected"] = expect_rejected(
        "collector fetch time", payload, bad, normalized_bytes=normalized_bytes, raw_bytes=raw_bytes
    )

    bad = mutated_evidence(lambda item: item.__setitem__("canonical_game_mapping_method", "fuzzy"))
    scenarios["fuzzy_mapping_rejected"] = expect_rejected(
        "fuzzy mapping", payload, bad, normalized_bytes=normalized_bytes, raw_bytes=raw_bytes
    )

    bad = mutated_evidence(lambda item: item.__setitem__("normalized_input_sha256", "sha256:" + "0" * 64))
    scenarios["normalized_hash_mismatch_rejected"] = expect_rejected(
        "normalized hash mismatch", payload, bad, normalized_bytes=normalized_bytes, raw_bytes=raw_bytes
    )

    bad = mutated_evidence(lambda item: item.__setitem__("raw_source_sha256", "sha256:" + "0" * 64))
    scenarios["raw_hash_mismatch_rejected"] = expect_rejected(
        "raw hash mismatch", payload, bad, normalized_bytes=normalized_bytes, raw_bytes=raw_bytes
    )

    bad = mutated_evidence(lambda item: item.__setitem__("public_redistribution_allowed", True))
    scenarios["public_redistribution_rejected"] = expect_rejected(
        "public redistribution", payload, bad, normalized_bytes=normalized_bytes, raw_bytes=raw_bytes
    )

    bad = mutated_evidence(lambda item: item.__setitem__("source_url", "http://example.invalid/source"))
    scenarios["non_https_source_rejected"] = expect_rejected(
        "non-https source", payload, bad, normalized_bytes=normalized_bytes, raw_bytes=raw_bytes
    )

    bad_payload = mutated_payload(lambda item: item.__setitem__("target_bookmaker_id", "fixture_book"))
    scenarios["placeholder_bookmaker_rejected"] = expect_rejected(
        "placeholder bookmaker", bad_payload, evidence, normalized_bytes=normalized_bytes, raw_bytes=raw_bytes
    )

    bad_payload = mutated_payload(lambda item: item.__setitem__("data_mode", "closing_only"))
    scenarios["closing_only_rejected"] = expect_rejected(
        "closing only", bad_payload, evidence, normalized_bytes=normalized_bytes, raw_bytes=raw_bytes
    )

    bad_payload = mutated_payload(lambda item: item.__setitem__("season", "2025-26"))
    scenarios["wrong_season_rejected"] = expect_rejected(
        "wrong season", bad_payload, evidence, normalized_bytes=normalized_bytes, raw_bytes=raw_bytes
    )

    bad_payload = mutated_payload(lambda item: item.__setitem__("competition_type", "preseason"))
    scenarios["wrong_competition_rejected"] = expect_rejected(
        "wrong competition", bad_payload, evidence, normalized_bytes=normalized_bytes, raw_bytes=raw_bytes
    )

    def change_observed(item: dict[str, Any]) -> None:
        item["candidates"][1]["observed_at"] = "2026-10-23T08:56:00+08:00"
    bad_payload = mutated_payload(change_observed)
    scenarios["two_sided_observed_at_mismatch_rejected"] = expect_rejected(
        "observed mismatch", bad_payload, evidence, normalized_bytes=normalized_bytes, raw_bytes=raw_bytes
    )

    def future_observed(item: dict[str, Any]) -> None:
        for candidate in item["candidates"]:
            candidate["observed_at"] = "2026-10-23T09:01:00+08:00"
    bad_payload = mutated_payload(future_observed)
    scenarios["post_cutoff_observed_at_rejected"] = expect_rejected(
        "post cutoff observed", bad_payload, evidence, normalized_bytes=normalized_bytes, raw_bytes=raw_bytes
    )

    def outside_window(item: dict[str, Any]) -> None:
        for candidate in item["candidates"]:
            candidate["scheduled_at"] = "2026-10-23T11:00:00+08:00"
    bad_payload = mutated_payload(outside_window)
    scenarios["outside_t60_window_rejected"] = expect_rejected(
        "outside T-60 window", bad_payload, evidence, normalized_bytes=normalized_bytes, raw_bytes=raw_bytes
    )

    def no_injury_gate(item: dict[str, Any]) -> None:
        for candidate in item["candidates"]:
            candidate["injury_confirmed"] = False
    bad_payload = mutated_payload(no_injury_gate)
    scenarios["no_fully_gated_game_rejected"] = expect_rejected(
        "no fully gated game", bad_payload, evidence, normalized_bytes=normalized_bytes, raw_bytes=raw_bytes
    )

    design = load_json(DESIGN_PATH)
    status = load_json(STATUS_PATH)
    schema = load_json(SCHEMA_PATH)
    doc = DOC_PATH.read_text(encoding="utf-8")
    handoff = HANDOFF_PATH.read_text(encoding="utf-8")

    assert design["formal_state"] == "G1_2_0_REAL_GOVERNED_T60_INPUT_INTAKE_VALIDATOR_IMPLEMENTED_CONTRACT_VALIDATED"
    assert design["implementation"]["network_client_included"] is False
    assert design["implementation"]["formal_history_writer_included"] is False
    assert design["implementation"]["contract_fixture_only"] is True
    assert design["execution_boundary"]["real_input_validated"] is False
    assert design["execution_boundary"]["market_metrics_executed"] is False
    assert design["execution_boundary"]["formal_stake"] == 0
    assert design["next_unique_mainline"] == "AWAIT_REAL_GOVERNED_2026_27_T60_INPUT_AND_QUALIFIED_TIMESTAMPED_ODDS"

    assert status["formal_state"] == "G1_2_0_REAL_GOVERNED_T60_INPUT_INTAKE_VALIDATOR_CONTRACT_VALIDATED"
    assert status["intake_validator"]["real_input_validated"] is False
    assert status["intake_validator"]["contract_tests"] == len(scenarios)
    assert status["provider_execution_state"]["hoopsapi_provider_requests_executed"] == 0
    assert status["next_unique_mainline"] == "AWAIT_REAL_GOVERNED_2026_27_T60_INPUT_AND_QUALIFIED_TIMESTAMPED_ODDS"
    assert status["formal_stake"] == 0

    assert schema["title"] == "G1.2.0 Real Governed T-60 Intake v1"
    required_text = (
        "IMPLEMENT_G1_2_0_REAL_GOVERNED_T60_INPUT_INTAKE_VALIDATOR_V1",
        "contract fixture only",
        "collector_fetched_at",
        "formal history",
        "AWAIT_REAL_GOVERNED_2026_27_T60_INPUT_AND_QUALIFIED_TIMESTAMPED_ODDS",
        "Formal Stake：0",
    )
    for text, label in ((doc, "documentation"), (handoff, "handoff")):
        lower_text = text.lower()
        for item in required_text:
            if item.lower() not in lower_text:
                raise AssertionError(f"missing {label} evidence: {item}")

    assert all(scenarios.values())
    report = {
        "schema_version": "g1-2-0-real-governed-t60-intake-validator-validation-v1",
        "formal_state": "G1_2_0_REAL_GOVERNED_T60_INPUT_INTAKE_VALIDATOR_CONTRACT_VALID",
        "contract_fixture_only": True,
        "contract_tests": len(scenarios),
        "contract_tests_passed": len(scenarios),
        "real_input_validated": False,
        "real_g120_dry_run_executed": False,
        "provider_requests_executed": 0,
        "formal_history_write_authorized": False,
        "raw_quote_rows_emitted": 0,
        "market_metrics_executed": False,
        "formal_stake": 0,
        "next_unique_mainline": "AWAIT_REAL_GOVERNED_2026_27_T60_INPUT_AND_QUALIFIED_TIMESTAMPED_ODDS",
    }
    serialized = json.dumps(report, sort_keys=True).lower()
    for forbidden in ("target_odds", "opponent_odds", "team_id", "raw_payload", "api_key", "authorization_header"):
        if forbidden in serialized:
            raise AssertionError(f"aggregate QA leaked forbidden fragment: {forbidden}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
