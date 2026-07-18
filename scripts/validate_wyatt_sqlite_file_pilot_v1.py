#!/usr/bin/env python3
"""Offline policy validator for Wyatt SQLite File-level Pilot v1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SCHEMA = "wyatt-sqlite-file-pilot-v1"
OUTCOMES = {
    "INPUT_FILE_REQUIRED",
    "STRUCTURAL_BLOCKED",
    "ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE",
    "SECONDARY_SOURCE_REJECTED",
}


class PolicyError(ValueError):
    pass


def require(condition: bool, label: str, passed: list[str]) -> None:
    if not condition:
        raise PolicyError(label)
    passed.append(label)


def validate(policy: dict[str, Any]) -> dict[str, Any]:
    passed: list[str] = []

    require(policy.get("schema_version") == SCHEMA, "schema_version", passed)
    require(policy.get("formal_state") == "INPUT_FILE_REQUIRED", "formal_state", passed)
    require(policy.get("source_id") == "kaggle_wyattowalsh_basketball", "source_id", passed)
    require(policy.get("source_role") == "secondary_historical_crosscheck_only", "source_role", passed)
    require(policy.get("pilot_season") == "2023-24", "pilot_season", passed)

    input_contract = policy.get("input_contract", {})
    require(set(input_contract.get("accepted_extensions", [])) == {".sqlite", ".sqlite3", ".db"}, "extensions", passed)
    require(input_contract.get("minimum_size_bytes") == 1048576, "minimum_size", passed)
    require(input_contract.get("maximum_size_bytes") == 3221225472, "maximum_size", passed)
    require(
        input_contract.get("maximum_size_basis") == "operational_safety_ceiling_only_not_a_research_promotion_gate",
        "maximum_size_basis",
        passed,
    )
    amendment = input_contract.get("size_ceiling_amendment", {})
    require(amendment.get("observed_archive_name") == "nba.sqlite.zip", "amendment_archive_name", passed)
    require(amendment.get("observed_archive_size_bytes") == 434150473, "amendment_archive_size", passed)
    require(amendment.get("observed_member_name") == "nba.sqlite", "amendment_member_name", passed)
    require(amendment.get("observed_member_size_bytes") == 2349588480, "amendment_member_size", passed)
    require(amendment.get("observed_member_size_bytes") < input_contract.get("maximum_size_bytes"), "amendment_within_ceiling", passed)
    require(amendment.get("content_inspected_before_amendment") is False, "amendment_preinspection", passed)

    for key in (
        "sqlite_header_required",
        "read_only_open_required",
        "integrity_check_required",
        "source_filename_recorded",
        "source_size_recorded",
        "sha256_recorded",
    ):
        require(input_contract.get(key) is True, key, passed)
    require(input_contract.get("raw_file_committed") is False, "raw_not_committed", passed)
    require(input_contract.get("raw_file_uploaded_as_artifact") is False, "raw_not_artifact", passed)

    schema = policy.get("schema_census", {})
    for key in (
        "table_inventory_required",
        "column_inventory_required",
        "row_count_required",
        "primary_key_inventory_required",
        "index_inventory_required",
        "foreign_key_inventory_required",
        "null_key_count_required",
        "duplicate_count_required",
        "date_range_required",
        "season_coverage_required",
        "game_id_semantics_required",
        "team_id_semantics_required",
        "pbp_event_order_semantics_required",
    ):
        require(schema.get(key) is True, f"schema:{key}", passed)

    reference = policy.get("reference_contract", {})
    require(reference.get("reference_source") == "existing_verified_historical_gold_and_silver", "reference_source", passed)
    require(reference.get("minimum_reference_games") == 1000, "minimum_reference_games", passed)
    require(reference.get("matching") == "deterministic_only", "deterministic_matching", passed)
    require(reference.get("fuzzy_matching") is False, "fuzzy_matching_disabled", passed)
    require(reference.get("future_information_leakage") is False, "future_leakage_disabled", passed)

    gates = policy.get("qualification_gates", {})
    expected_gates = {
        "game_identity_match_rate_minimum": 0.98,
        "final_score_match_rate_minimum": 0.98,
        "team_boxscore_coverage_minimum": 0.98,
        "player_boxscore_coverage_minimum": 0.95,
        "pbp_game_coverage_minimum_when_claimed": 0.95,
        "exact_duplicate_game_count_maximum": 0,
        "integrity_check_must_equal": "ok",
    }
    for key, value in expected_gates.items():
        require(gates.get(key) == value, f"gate:{key}", passed)

    require(set(policy.get("formal_outcomes", [])) == OUTCOMES, "formal_outcomes", passed)
    require("full_sqlite_database" in policy.get("forbidden_outputs", []), "full_database_forbidden", passed)
    require("raw_play_by_play_rows" in policy.get("forbidden_outputs", []), "raw_pbp_forbidden", passed)

    boundaries = policy.get("boundaries", {})
    require(boundaries.get("input_file_present_in_this_pr") is False, "input_absent", passed)
    require(boundaries.get("database_opened_in_this_pr") is False, "database_not_opened", passed)
    require(boundaries.get("raw_rows_in_artifact") == 0, "raw_rows_zero", passed)
    require(boundaries.get("formal_stake") == 0, "stake_zero", passed)
    for key in (
        "existing_silver_replacement",
        "existing_gold_replacement",
        "model_retraining",
        "model_metrics",
        "market_metrics",
    ):
        require(boundaries.get(key) is False, f"boundary:{key}", passed)

    return {
        "schema_version": SCHEMA,
        "formal_state": "INPUT_FILE_REQUIRED",
        "checks_passed": len(passed),
        "checks_failed": 0,
        "source_id": policy["source_id"],
        "pilot_season": "2023-24",
        "maximum_size_bytes": input_contract["maximum_size_bytes"],
        "observed_member_size_bytes": amendment["observed_member_size_bytes"],
        "input_file_present": False,
        "database_opened": False,
        "raw_rows_in_artifact": 0,
        "existing_silver_replacement": False,
        "existing_gold_replacement": False,
        "model_metrics": False,
        "market_metrics": False,
        "formal_stake": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, default=Path("data/wyatt-sqlite-file-pilot-v1.json"))
    parser.add_argument("--output-report", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    report = validate(json.loads(args.policy.read_text(encoding="utf-8")))
    if args.output_report:
        args.output_report.parent.mkdir(parents=True, exist_ok=True)
        args.output_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("self-test: success" if args.self_test else json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
