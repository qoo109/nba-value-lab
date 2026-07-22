#!/usr/bin/env python3
"""Validate the 2023-24 Historical Silver source archive reconciliation design."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

READY = "HISTORICAL_SILVER_2023_24_SOURCE_ARCHIVE_RECONCILIATION_DESIGN_READY"
NEXT = "HISTORICAL_SILVER_2023_24_SOURCE_ARCHIVE_RECONCILIATION_REQUEST_DRAFT_READY_FOR_IMPLEMENTATION"
ROOT_CAUSE = "HISTORICAL_SILVER_MISSING_TEAM_FEATURES_SOURCE_GAP_CONFIRMED"


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def validate(design: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    checks: dict[str, bool] = {}

    def add(name: str, value: Any) -> None:
        checks[name] = bool(value)

    add("schema", design.get("schema_version") == "historical-silver-2023-24-source-archive-reconciliation-design-v1")
    add("state", design.get("formal_state") == READY)
    add("triggering_result", design.get("triggering_result", "").endswith("root-cause-retry-002-result-v1.json"))
    add("season", design.get("season_label") == "2023-24")
    add("root_cause", design.get("root_cause_outcome") == ROOT_CAUSE)

    observed = design.get("observed_gap", {})
    add("observed_silver_games", observed.get("silver_games") == 1230)
    add("observed_gap_count", observed.get("games_without_team_features") == 2)
    add("observed_classified", observed.get("classified_missing_games") == 2)
    add("observed_unclassified", observed.get("unclassified_missing_games") == 0)
    add("observed_reason", observed.get("missing_reason") == "nbastats_game_present_pbpstats_game_absent")
    add("observed_reason_count", observed.get("missing_reason_count") == 2)

    add("result_outcome", result.get("formal_outcome") == ROOT_CAUSE)
    add("result_run", result.get("workflow_run_id") == design.get("triggering_workflow_run_id") == 29890527281)
    add("result_artifact", result.get("artifact_id") == design.get("triggering_artifact_id") == 8518081820)
    add("result_digest", result.get("artifact_digest") == design.get("triggering_artifact_digest"))
    add("result_no_raw", result.get("boundaries", {}).get("raw_rows_emitted") == 0)
    add("result_no_files", result.get("boundaries", {}).get("raw_files_emitted") is False)
    add("result_stake", result.get("boundaries", {}).get("formal_stake") == 0)

    lanes = {lane.get("lane_id"): lane for lane in design.get("allowed_followup_lanes", [])}
    add("lane_source_archive", "source_archive_reconciliation" in lanes)
    add("lane_secondary_qa", "secondary_team_feature_qa_reference" in lanes)
    add("lane_exception", "documented_exception" in lanes)

    source_lane = lanes.get("source_archive_reconciliation", {})
    add("source_lane_separate_request", source_lane.get("raw_data_execution_requires_separate_request") is True)
    add("source_lane_no_candidate", source_lane.get("candidate_csv_allowed") is False)
    add("source_lane_no_builder", source_lane.get("silver_builder_change_allowed") is False)
    add("source_lane_no_gold", source_lane.get("gold_builder_execution_allowed") is False)

    secondary_lane = lanes.get("secondary_team_feature_qa_reference", {})
    candidates = secondary_lane.get("candidate_sources", [])
    add("secondary_lane_no_execution", secondary_lane.get("raw_data_execution_requires_separate_request") is True)
    add("secondary_lane_no_candidate_now", secondary_lane.get("candidate_csv_allowed_in_this_design") is False)
    add("secondary_lane_no_patch", secondary_lane.get("silver_or_gold_patch_allowed") is False)
    add("chris_candidate_present", any(c.get("source_id") == "kaggle_chrismunch_team_statistics" for c in candidates))
    for candidate in candidates:
        if candidate.get("source_id") == "kaggle_chrismunch_team_statistics":
            files = set(candidate.get("allowed_files", []))
            add("chris_role", candidate.get("candidate_role") == "ROLE_LIMITED_SECONDARY_TEAM_FEATURE_QA_CANDIDATE")
            add("chris_manifest_required", candidate.get("required_manifest_before_execution") is True)
            add("chris_fetch_required", candidate.get("required_fetch_verify_script_before_execution") is True)
            add("chris_raw_not_git", candidate.get("raw_csv_committed_to_git") is False)
            add("chris_raw_not_artifact", candidate.get("raw_csv_uploaded_as_artifact") is False)
            add("chris_required_files", {
                "cumulative_scraped/games_advanced.csv",
                "cumulative_scraped/games_four-factors.csv",
                "cumulative_scraped/games_traditional.csv",
                "data_dictionary.csv",
            }.issubset(files))
            add("chris_processed_not_main_key", candidate.get("processed_files_main_key_allowed") is False)

    boundary = design.get("output_boundary", {})
    for key in [
        "network_calls_made",
        "candidate_csv_downloaded_or_read",
        "chris_munch_raw_rows_read",
        "shufinskiy_raw_rows_read",
        "gold_database_created_or_read",
        "raw_files_emitted",
        "silver_database_uploaded_as_artifact",
        "source_archives_uploaded_as_artifact",
        "game_ids_emitted",
        "dates_emitted",
        "team_codes_emitted",
        "row_level_records_emitted",
        "row_key_hashes_emitted",
    ]:
        add(f"boundary_{key}", boundary.get(key) is False)
    add("boundary_design_only", boundary.get("design_only") is True)
    add("boundary_raw_rows", boundary.get("raw_rows_emitted") == 0)
    add("boundary_size", boundary.get("maximum_public_output_bytes") == 1048576)

    perms = design.get("downstream_permissions", {})
    add("ready_request", perms.get("ready_for_source_archive_reconciliation_request") is True)
    add("ready_chris_manifest", perms.get("ready_for_chris_munch_manifest_predeclaration") is True)
    for key in [
        "ready_for_chris_munch_data_execution",
        "ready_for_silver_builder_change",
        "ready_for_silver_exception_patch",
        "ready_for_gold_rebuild",
        "ready_for_cross_source_audit_rerun",
        "ready_for_historical_silver_replacement",
        "ready_for_historical_gold_replacement",
        "ready_for_market_backtest",
        "ready_for_model_retraining",
        "ready_for_betting_edge_claim",
    ]:
        add(f"perm_{key}", perms.get(key) is False)
    add("stake", perms.get("formal_stake") == 0)
    add("next", design.get("next_research_step") == NEXT)

    failed = sorted(name for name, ok in checks.items() if not ok)
    return {
        "formal_state": READY if not failed else "HISTORICAL_SILVER_2023_24_SOURCE_ARCHIVE_RECONCILIATION_DESIGN_BLOCKED",
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "checks_failed": len(failed),
        "failed_checks": failed,
        "network_calls_made": False,
        "raw_rows_emitted": 0,
        "raw_files_emitted": False,
        "formal_stake": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--design", type=Path, default=Path("data/research/historical-silver-2023-24-source-archive-reconciliation-design-v1.json"))
    parser.add_argument("--result", type=Path, default=Path("data/research/historical-silver-2023-24-missing-team-features-root-cause-retry-002-result-v1.json"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = validate(read_json(args.design), read_json(args.result))
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if report["checks_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
