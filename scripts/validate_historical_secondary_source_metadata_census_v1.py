#!/usr/bin/env python3
"""Offline validator for Historical Secondary Source Metadata Census v1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SCHEMA = "historical-secondary-source-metadata-census-v1"
EXPECTED_IDS = {
    "kaggle_eoinamoore_historical_nba",
    "kaggle_wyattowalsh_basketball",
}


class CensusError(ValueError):
    pass


def require(condition: bool, label: str, passed: list[str]) -> None:
    if not condition:
        raise CensusError(label)
    passed.append(label)


def validate(payload: dict[str, Any]) -> dict[str, Any]:
    passed: list[str] = []
    require(payload.get("schema_version") == SCHEMA, "schema", passed)
    require(payload.get("policy_dependency") == "historical-secondary-source-qualification-v1", "policy_dependency", passed)
    require(payload.get("formal_state") == "METADATA_READY_DOWNLOAD_NOT_AUTHORIZED", "formal_state", passed)
    require(payload.get("candidate_count") == 2, "candidate_count", passed)
    require(payload.get("metadata_ready_count") == 2, "metadata_ready_count", passed)
    require(payload.get("full_secondary_source_qualified_count") == 0, "qualified_count", passed)

    results = payload.get("results", [])
    require(len(results) == 2, "result_count", passed)
    ids = {row.get("source_id") for row in results}
    require(ids == EXPECTED_IDS, "candidate_ids", passed)
    by_id = {row["source_id"]: row for row in results}

    eoin = by_id["kaggle_eoinamoore_historical_nba"]
    require(eoin.get("formal_outcome") == "METADATA_READY_DOWNLOAD_NOT_AUTHORIZED", "eoin_outcome", passed)
    require(eoin.get("license_label") == "CC0: Public Domain", "eoin_license", passed)
    require("Games.csv" in eoin.get("listed_assets", []), "eoin_games", passed)
    require(any("advanced" in role for role in eoin.get("blocked_future_roles", [])), "eoin_advanced_blocked", passed)
    require(any("pbp" in role for role in eoin.get("blocked_future_roles", [])), "eoin_pbp_blocked", passed)

    wyatt = by_id["kaggle_wyattowalsh_basketball"]
    require(wyatt.get("formal_outcome") == "METADATA_READY_DOWNLOAD_NOT_AUTHORIZED", "wyatt_outcome", passed)
    require(wyatt.get("license_label") == "CC BY-SA 4.0", "wyatt_license", passed)
    require("SQLite database" in wyatt.get("listed_assets", []), "wyatt_sqlite", passed)
    require(any("freshness" in role for role in wyatt.get("blocked_future_roles", [])), "wyatt_freshness_blocked", passed)

    gate = payload.get("next_execution_gate", {})
    require(gate.get("separate_download_pilot_pr_required") is True, "separate_pr", passed)
    require(gate.get("first_pilot_season") == "2023-24", "pilot_season", passed)
    require(gate.get("minimum_reference_games") == 1000, "minimum_reference_games", passed)
    require(gate.get("deterministic_matching_only") is True, "deterministic_only", passed)
    require(gate.get("fuzzy_matching") is False, "no_fuzzy", passed)
    require(gate.get("existing_silver_replacement") is False, "no_silver_replacement", passed)

    boundaries = payload.get("boundaries", {})
    for key in ("downloads_in_this_pr", "external_data_calls_in_workflow", "raw_rows_in_artifact", "formal_stake"):
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
        "formal_state": "METADATA_READY_DOWNLOAD_NOT_AUTHORIZED",
        "checks_passed": len(passed),
        "checks_failed": 0,
        "candidate_count": 2,
        "metadata_ready_count": 2,
        "full_secondary_source_qualified_count": 0,
        "downloads": 0,
        "external_data_calls": 0,
        "raw_rows_in_artifact": 0,
        "model_metrics": False,
        "market_metrics": False,
        "existing_silver_replacement": False,
        "existing_gold_replacement": False,
        "formal_stake": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("data/historical-secondary-source-metadata-census-v1.json"))
    parser.add_argument("--output-report", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    report = validate(json.loads(args.input.read_text(encoding="utf-8")))
    if args.output_report:
        args.output_report.parent.mkdir(parents=True, exist_ok=True)
        args.output_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("self-test: success" if args.self_test else json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
