#!/usr/bin/env python3
"""Offline fail-closed intake validator for one real governed G1.2.0 T-60 slate.

This module performs no network requests, writes no formal history, exposes no
quote-level public artifact, and does not run market metrics. The command-line
entry point never accepts contract fixtures as real input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

VALID_CONFIDENCE = {"高", "中", "低", "資料不足"}
VALID_ANALYSIS_GATE = {"可分析", "條件式可分析", "資料不足"}
VALID_TIME_AUTHORITY = {"provider_snapshot", "bookmaker_last_update"}
PLACEHOLDER_BOOKMAKERS = {"", "fixture_book", "fixture", "unknown", "placeholder", "synthetic"}
TOP_REQUIRED = {
    "schema_version", "data_mode", "slate_id", "slate_date", "analysis_cutoff",
    "evaluation_stage", "target_bookmaker_id", "market_id", "includes_overtime",
    "data_version", "lock_window_minutes", "candidates", "season", "competition_type",
}
CANDIDATE_REQUIRED = {
    "game_id", "scheduled_at", "candidate_side", "selection_team_id", "opponent_team_id",
    "target_odds", "opponent_odds", "observed_at", "p_conservative", "p_neutral",
    "p_optimistic", "coverage_pct", "confidence", "news_risk_level",
    "analysis_gate_status", "comparison_sources", "injury_confirmed",
    "starters_confirmed", "minutes_limit_confirmed", "source_lineage_complete",
    "market_rules_complete", "price_timestamp_valid", "out_of_distribution",
    "reverse_path_resolved", "stale_warning", "model_market_gap_pp",
    "independent_evidence_count", "data_age_minutes",
}
EVIDENCE_REQUIRED = {
    "evidence_schema_version", "contract_fixture_only", "source_id", "source_url",
    "source_rights_state", "rights_review_reference", "rights_reviewed_by_user",
    "provider_timestamp_semantics_verified", "provider_timestamp_semantics_note",
    "quote_time_authority", "provider_observed_at_field", "target_bookmaker_id",
    "market_id", "includes_overtime", "canonical_game_mapping_method",
    "normalized_input_sha256", "raw_source_sha256", "raw_source_retention_scope",
    "public_redistribution_allowed",
}


class IntakeValidationError(ValueError):
    """Raised when a governed input bundle fails the intake contract."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise IntakeValidationError(message)


def parse_time(value: Any, field: str) -> datetime:
    require(isinstance(value, str) and value.strip(), f"{field} must be a non-empty ISO 8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise IntakeValidationError(f"{field} must be ISO 8601") from exc
    require(parsed.tzinfo is not None, f"{field} must include timezone")
    return parsed


def sha256_bytes(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def _validate_evidence(
    payload: dict[str, Any],
    evidence: dict[str, Any],
    *,
    normalized_bytes: bytes,
    raw_source_bytes: bytes,
    contract_test: bool,
) -> None:
    missing = sorted(EVIDENCE_REQUIRED - evidence.keys())
    require(not missing, "source evidence missing: " + ", ".join(missing))
    require(evidence["evidence_schema_version"] == "g1-2-0-real-t60-source-evidence-v1", "invalid evidence schema")
    require(bool(evidence["contract_fixture_only"]) is contract_test, "contract fixture evidence flag mismatch")
    require(isinstance(evidence["source_id"], str) and evidence["source_id"].strip(), "source_id required")
    require(isinstance(evidence["source_url"], str) and evidence["source_url"].startswith("https://"), "source_url must be HTTPS")
    require(evidence["source_rights_state"] == "private_research_allowed", "source rights must allow private research")
    require(isinstance(evidence["rights_review_reference"], str) and evidence["rights_review_reference"].strip(), "rights review reference required")
    require(evidence["rights_reviewed_by_user"] is True, "rights must be reviewed by user")
    require(evidence["provider_timestamp_semantics_verified"] is True, "provider timestamp semantics must be verified")
    require(
        isinstance(evidence["provider_timestamp_semantics_note"], str)
        and len(evidence["provider_timestamp_semantics_note"].strip()) >= 20,
        "provider timestamp semantics note is insufficient",
    )
    require(evidence["quote_time_authority"] in VALID_TIME_AUTHORITY, "invalid quote time authority")
    require(
        isinstance(evidence["provider_observed_at_field"], str)
        and evidence["provider_observed_at_field"].strip(),
        "provider observed_at field required",
    )
    require(evidence["target_bookmaker_id"] == payload["target_bookmaker_id"], "bookmaker evidence mismatch")
    require(evidence["market_id"] == payload["market_id"], "market evidence mismatch")
    require(evidence["includes_overtime"] is payload["includes_overtime"], "overtime evidence mismatch")
    require(evidence["canonical_game_mapping_method"] == "exact", "only exact canonical game mapping is allowed")
    require(evidence["normalized_input_sha256"] == sha256_bytes(normalized_bytes), "normalized input SHA-256 mismatch")
    require(evidence["raw_source_sha256"] == sha256_bytes(raw_source_bytes), "raw source SHA-256 mismatch")
    require(
        evidence["raw_source_retention_scope"] in {"private_ephemeral", "private_user_controlled"},
        "raw source retention must remain private",
    )
    require(evidence["public_redistribution_allowed"] is False, "public redistribution must remain disabled")


def _validate_candidate(candidate: dict[str, Any], cutoff: datetime, *, contract_test: bool) -> None:
    missing = sorted(CANDIDATE_REQUIRED - candidate.keys())
    require(not missing, f"{candidate.get('game_id', 'candidate')} missing: " + ", ".join(missing))
    require(candidate["candidate_side"] in {"home", "away"}, "candidate_side must be home or away")
    require(candidate["selection_team_id"] != candidate["opponent_team_id"], "selection and opponent must differ")
    require(isinstance(candidate["target_odds"], (int, float)) and candidate["target_odds"] > 1, "target_odds must be > 1")
    require(isinstance(candidate["opponent_odds"], (int, float)) and candidate["opponent_odds"] > 1, "opponent_odds must be > 1")
    for key in ("p_conservative", "p_neutral", "p_optimistic"):
        require(isinstance(candidate[key], (int, float)) and 0 <= candidate[key] <= 1, f"{key} must be 0..1")
    require(
        candidate["p_conservative"] <= candidate["p_neutral"] <= candidate["p_optimistic"],
        "P_C <= P_N <= P_O required",
    )
    require(isinstance(candidate["coverage_pct"], (int, float)) and 0 <= candidate["coverage_pct"] <= 100, "coverage_pct invalid")
    require(candidate["confidence"] in VALID_CONFIDENCE, "invalid confidence")
    require(isinstance(candidate["news_risk_level"], int) and 0 <= candidate["news_risk_level"] <= 3, "news_risk_level invalid")
    require(candidate["analysis_gate_status"] in VALID_ANALYSIS_GATE, "invalid analysis_gate_status")
    for key in ("comparison_sources", "independent_evidence_count"):
        require(isinstance(candidate[key], int) and candidate[key] >= 0, f"{key} must be non-negative integer")
    require(isinstance(candidate["data_age_minutes"], (int, float)) and candidate["data_age_minutes"] >= 0, "data_age_minutes invalid")
    for key in (
        "injury_confirmed", "starters_confirmed", "minutes_limit_confirmed",
        "source_lineage_complete", "market_rules_complete", "price_timestamp_valid",
        "out_of_distribution", "reverse_path_resolved", "stale_warning",
    ):
        require(isinstance(candidate[key], bool), f"{key} must be boolean")
    require(candidate["source_lineage_complete"] is True, "source lineage must be complete")
    require(candidate["market_rules_complete"] is True, "market rules must be complete")
    require(candidate["price_timestamp_valid"] is True, "price timestamp must be valid")

    scheduled = parse_time(candidate["scheduled_at"], "scheduled_at")
    observed = parse_time(candidate["observed_at"], "observed_at")
    require(observed <= cutoff, "observed_at cannot be after analysis_cutoff")
    require(observed < scheduled, "observed_at must be strictly pre-tip")
    require(cutoff < scheduled, "analysis_cutoff must be strictly pre-tip")
    minutes_to_tip = (scheduled - cutoff).total_seconds() / 60
    require(30 <= minutes_to_tip <= 90, f"T-60 window must be 30..90 minutes; got {minutes_to_tip:.1f}")
    if not contract_test:
        require("fixture" not in str(candidate["game_id"]).lower(), "fixture game id prohibited in real intake")


def _validate_pairs(candidates: list[dict[str, Any]]) -> tuple[int, int]:
    by_game: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        by_game[str(candidate["game_id"])].append(candidate)

    fully_gated_games = 0
    for game_id, pair in by_game.items():
        require(len(pair) == 2, f"{game_id} must contain exactly two sides")
        require({item["candidate_side"] for item in pair} == {"home", "away"}, f"{game_id} must contain home and away")
        home = next(item for item in pair if item["candidate_side"] == "home")
        away = next(item for item in pair if item["candidate_side"] == "away")
        require(home["selection_team_id"] == away["opponent_team_id"], f"{game_id} team mapping mismatch")
        require(away["selection_team_id"] == home["opponent_team_id"], f"{game_id} team mapping mismatch")
        require(abs(home["target_odds"] - away["opponent_odds"]) <= 1e-9, f"{game_id} home odds mismatch")
        require(abs(away["target_odds"] - home["opponent_odds"]) <= 1e-9, f"{game_id} away odds mismatch")
        require(home["observed_at"] == away["observed_at"], f"{game_id} observed_at mismatch")
        require(home["scheduled_at"] == away["scheduled_at"], f"{game_id} scheduled_at mismatch")
        require(abs(home["p_neutral"] + away["p_neutral"] - 1) <= 1e-6, f"{game_id} neutral probabilities not complementary")
        require(abs(home["p_conservative"] + away["p_optimistic"] - 1) <= 1e-6, f"{game_id} P_C/P_O mismatch")
        require(abs(home["p_optimistic"] + away["p_conservative"] - 1) <= 1e-6, f"{game_id} P_O/P_C mismatch")
        fully_gated = all(
            item["injury_confirmed"]
            and item["starters_confirmed"]
            and item["minutes_limit_confirmed"]
            and item["analysis_gate_status"] != "資料不足"
            and item["confidence"] != "資料不足"
            and item["news_risk_level"] < 3
            for item in pair
        )
        fully_gated_games += int(fully_gated)
    return len(by_game), fully_gated_games


def validate_intake(
    payload: dict[str, Any],
    evidence: dict[str, Any],
    *,
    normalized_bytes: bytes,
    raw_source_bytes: bytes,
    contract_test: bool = False,
) -> dict[str, Any]:
    require(isinstance(payload, dict), "input must be an object")
    require(isinstance(evidence, dict), "source evidence must be an object")
    missing = sorted(TOP_REQUIRED - payload.keys())
    require(not missing, "top-level input missing: " + ", ".join(missing))
    require(bool(payload.get("contract_fixture_only", False)) is contract_test, "contract fixture input flag mismatch")

    expected_mode = "contract_fixture" if contract_test else "real_governed"
    require(payload["data_mode"] == expected_mode, f"data_mode must be {expected_mode}")
    require(payload["season"] == "2026-27", "season must be 2026-27")
    require(payload["competition_type"] == "regular_season", "competition_type must be regular_season")
    require(payload["evaluation_stage"] == "T-60m", "evaluation_stage must be T-60m")
    require(payload["market_id"] == "moneyline_ot_included", "market must be moneyline_ot_included")
    require(payload["includes_overtime"] is True, "market must include overtime")
    bookmaker = str(payload["target_bookmaker_id"]).strip()
    require(bookmaker.lower() not in PLACEHOLDER_BOOKMAKERS, "real bookmaker identity required")
    require(isinstance(payload["candidates"], list) and payload["candidates"], "candidates must be non-empty")
    window = payload["lock_window_minutes"]
    require(isinstance(window, dict) and window.get("min") == 30 and window.get("max") == 90, "lock window must be 30..90")
    cutoff = parse_time(payload["analysis_cutoff"], "analysis_cutoff")

    if not contract_test:
        serialized = json.dumps(payload, ensure_ascii=False).lower()
        for forbidden in ("contract_fixture", "fixture_book", "synthetic"):
            require(forbidden not in serialized, f"real intake contains prohibited fixture marker: {forbidden}")

    _validate_evidence(
        payload,
        evidence,
        normalized_bytes=normalized_bytes,
        raw_source_bytes=raw_source_bytes,
        contract_test=contract_test,
    )
    for candidate in payload["candidates"]:
        require(isinstance(candidate, dict), "candidate must be an object")
        _validate_candidate(candidate, cutoff, contract_test=contract_test)
    game_count, fully_gated_games = _validate_pairs(payload["candidates"])
    require(fully_gated_games >= 1, "at least one game must satisfy complete injury/information gates")

    return {
        "schema_version": "g1-2-0-real-t60-intake-validation-v1",
        "formal_state": (
            "G1_2_0_REAL_GOVERNED_T60_INPUT_INTAKE_CONTRACT_VALID"
            if contract_test
            else "G1_2_0_REAL_GOVERNED_T60_INPUT_INTAKE_VALID"
        ),
        "contract_test_only": contract_test,
        "intake_valid": True,
        "g120_dry_run_ready": True,
        "game_count": game_count,
        "candidate_count": len(payload["candidates"]),
        "fully_gated_game_count": fully_gated_games,
        "provider_origin_observed_at_verified": True,
        "source_rights_private_research_allowed": True,
        "exact_mapping_required": True,
        "formal_history_write_authorized": False,
        "provider_requests_executed": 0,
        "raw_quote_rows_emitted": 0,
        "market_metrics_executed": False,
        "formal_stake": 0,
        "next_unique_mainline": (
            "AWAIT_REAL_GOVERNED_2026_27_T60_INPUT_AND_QUALIFIED_TIMESTAMPED_ODDS"
            if contract_test
            else "RUN_ONE_REAL_G1_2_0_T60_DRY_RUN_AGGREGATE_VALIDATION"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path, help="private normalized T-60 input JSON")
    parser.add_argument("--evidence", required=True, type=Path, help="private source evidence JSON")
    parser.add_argument("--raw-source", required=True, type=Path, help="private raw provider response or export")
    parser.add_argument("--output", required=True, type=Path, help="aggregate-only QA JSON")
    args = parser.parse_args()

    normalized_bytes = args.input.read_bytes()
    payload = json.loads(normalized_bytes.decode("utf-8"))
    evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
    raw_source_bytes = args.raw_source.read_bytes()
    report = validate_intake(
        payload,
        evidence,
        normalized_bytes=normalized_bytes,
        raw_source_bytes=raw_source_bytes,
        contract_test=False,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
