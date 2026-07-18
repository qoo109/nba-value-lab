#!/usr/bin/env python3
"""Offline validator for Historical Secondary Source Qualification v1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SCHEMA = "historical-secondary-source-qualification-v1"
CANDIDATES = {
    "kaggle_eoinamoore_historical_nba",
    "kaggle_wyattowalsh_basketball",
}
OUTCOMES = {
    "METADATA_BLOCKED",
    "METADATA_READY_DOWNLOAD_NOT_AUTHORIZED",
    "DOWNLOAD_PILOT_ELIGIBLE",
    "ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE",
    "SECONDARY_SOURCE_REJECTED",
}


class PolicyError(ValueError):
    pass


def require(value: bool, label: str, passed: list[str]) -> None:
    if not value:
        raise PolicyError(label)
    passed.append(label)


def validate(policy: dict[str, Any]) -> dict[str, Any]:
    passed: list[str] = []
    require(policy.get("schema_version") == SCHEMA, "schema_version", passed)
    require(policy.get("formal_state") == "PREDECLARED_METADATA_ONLY", "formal_state", passed)

    reference = policy.get("reference", {})
    require(reference.get("primary_source") == "shufinskiy/nba_data", "primary_source", passed)
    require(reference.get("pilot_season") == "2023-24", "pilot_season", passed)
    require(reference.get("matching") == "deterministic_only", "matching", passed)
    require(reference.get("fuzzy_matching") is False, "no_fuzzy_matching", passed)

    candidates = policy.get("candidates", [])
    require(len(candidates) == 2, "candidate_count", passed)
    ids = {row.get("source_id") for row in candidates}
    require(ids == CANDIDATES, "candidate_ids", passed)
    by_id = {row["source_id"]: row for row in candidates}

    eoin = by_id["kaggle_eoinamoore_historical_nba"]
    require(eoin.get("declared_license") == "CC0: Public Domain", "eoin_license", passed)
    require("Games.csv" in eoin.get("currently_listed_files", []), "eoin_games", passed)
    require("PlaybyPlay.parquet" in eoin.get("not_presumed_available", []), "eoin_pbp_not_presumed", passed)
    require("TeamStatisticsExtended.csv" in eoin.get("not_presumed_available", []), "eoin_advanced_not_presumed", passed)

    wyatt = by_id["kaggle_wyattowalsh_basketball"]
    require(wyatt.get("declared_license") == "CC BY-SA 4.0", "wyatt_license", passed)
    require("SQLite database" in wyatt.get("currently_claimed_assets", []), "wyatt_sqlite", passed)
    require("freshness" in wyatt.get("risk", "").lower(), "wyatt_freshness_risk", passed)

    metadata = policy.get("metadata_gates", {})
    require(metadata.get("candidate_count") == 2, "metadata_count", passed)
    require(metadata.get("claims_are_not_verified_schema") is True, "claims_not_schema", passed)

    future = policy.get("future_download_pilot_gates", {})
    require(future.get("separate_pr_required") is True, "separate_future_pr", passed)
    require(future.get("sha256_required") is True, "sha256_required", passed)
    require(future.get("safe_extract_required") is True, "safe_extract_required", passed)
    require(future.get("commit_raw_archives") is False, "no_raw_archives", passed)
    require(future.get("commit_extracted_raw_data") is False, "no_extracted_raw", passed)
    require(future.get("commit_full_database") is False, "no_full_database", passed)
    require(future.get("aggregate_reports_only") is True, "aggregate_only", passed)

    schema = policy.get("schema_gates", {})
    for key in (
        "exact_file_inventory_required",
        "table_or_column_inventory_required",
        "row_counts_required",
        "duplicate_counts_required",
        "null_key_counts_required",
        "date_range_required",
        "season_coverage_required",
        "game_id_semantics_required",
        "team_id_semantics_required",
        "pbp_event_order_semantics_required_when_claimed",
        "advanced_metric_definition_required_when_claimed",
    ):
        require(schema.get(key) is True, key, passed)

    cross = policy.get("cross_source_gates", {})
    expected = {
        "pilot_season": "2023-24",
        "minimum_reference_games": 1000,
        "game_identity_match_rate_minimum": 0.98,
        "final_score_match_rate_minimum": 0.98,
        "team_boxscore_coverage_minimum": 0.98,
        "player_boxscore_coverage_minimum": 0.95,
        "pbp_game_coverage_minimum_when_claimed": 0.95,
        "exact_duplicate_game_count_maximum": 0,
        "future_information_leakage": False,
        "replace_verified_silver": False,
    }
    for key, value in expected.items():
        require(cross.get(key) == value, f"cross:{key}", passed)

    require(set(policy.get("formal_outcomes", [])) == OUTCOMES, "formal_outcomes", passed)

    boundaries = policy.get("boundaries", {})
    for key in ("downloads_in_this_pr", "external_data_calls_in_this_pr", "raw_rows_in_artifact", "formal_stake"):
        require(boundaries.get(key) == 0, f"zero:{key}", passed)
    for key in (
        "model_retraining",
        "model_metrics",
        "market_metrics",
        "existing_silver_replacement",
        "existing_gold_replacement",
    ):
        require(boundaries.get(key) is False, f"false:{key}", passed)

    return {
        "schema_version": SCHEMA,
        "formal_state": "PREDECLARED_METADATA_ONLY",
        "checks_passed": len(passed),
        "checks_failed": 0,
        "candidate_count": 2,
        "candidate_ids": sorted(ids),
        "downloads": 0,
        "external_data_calls": 0,
        "raw_rows_in_artifact": 0,
        "model_metrics": False,
        "market_metrics": False,
        "existing_silver_replacement": False,
        "existing_gold_replacement": False,
        "formal_stake": 0,
    }


def self_test() -> None:
    policy_path = Path("data/historical-secondary-source-qualification-v1.json")
    report = validate(json.loads(policy_path.read_text(encoding="utf-8")))
    if report["candidate_count"] != 2 or report["downloads"] != 0:
        raise AssertionError("unexpected self-test result")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, default=Path("data/historical-secondary-source-qualification-v1.json"))
    parser.add_argument("--output-report", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test()
        print("self-test: success")
        return 0

    report = validate(json.loads(args.policy.read_text(encoding="utf-8")))
    if args.output_report:
        args.output_report.parent.mkdir(parents=True, exist_ok=True)
        args.output_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
