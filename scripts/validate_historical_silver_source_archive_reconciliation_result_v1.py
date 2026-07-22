#!/usr/bin/env python3
"""Validate the recorded aggregate-only 2023-24 source archive reconciliation result."""
from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REQUEST_ID = "HISTORICAL-SILVER-2023-24-SOURCE-ARCHIVE-RECONCILIATION-2026-07-22-001"
FORMAL_STATE = "HISTORICAL_SILVER_2023_24_SOURCE_ARCHIVE_RECONCILIATION_AGGREGATE_VALIDATION_PASS"
DECISION = "SOURCE_ARCHIVE_GAP_STABLE"
RUN_ID = 29901869841
ARTIFACT_ID = 8522225397
DIGEST = "sha256:2b42dca052d331bf94e31568b24492092beb00fef352405601fd812a8603b334"
NEXT_STEP = "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_MANIFEST_READY_FOR_DESIGN"


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def validate(result: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    checks: dict[str, bool] = {}

    def add(name: str, value: Any) -> None:
        checks[name] = bool(value)

    add("result_schema", result.get("schema_version") == "historical-silver-2023-24-source-archive-reconciliation-result-v1")
    add("result_request", result.get("request_id") == REQUEST_ID)
    add("result_source", result.get("source_id") == "shufinskiy_nba_data")
    add("result_season", result.get("season_label") == "2023-24")
    add("result_state", result.get("formal_state") == FORMAL_STATE)

    workflow = result.get("workflow_run", {})
    add("run_id", workflow.get("run_id") == RUN_ID)
    add("run_attempt", workflow.get("run_attempt") == 1)
    add("run_event", workflow.get("event") == "workflow_dispatch")
    add("run_ref", workflow.get("ref") == "refs/heads/main")
    add("run_sha", workflow.get("head_sha") == "fb0b67df9f5cb110e10bbcff2cd0702a9b7b8fbd")
    add("run_job", workflow.get("job_name") == "execute-once" and workflow.get("job_conclusion") == "success")

    artifact = result.get("artifact", {})
    add("artifact_id", artifact.get("artifact_id") == ARTIFACT_ID)
    add("artifact_name", artifact.get("artifact_name") == "historical-silver-source-archive-reconciliation-execution-v1")
    add("artifact_size", artifact.get("artifact_size_in_bytes") == 2414)
    add("artifact_digest", artifact.get("artifact_digest") == DIGEST)
    add("artifact_file", artifact.get("artifact_json_file") == "historical-silver-source-archive-reconciliation-execution-report.json")

    decision = result.get("decision", {})
    add("decision", decision.get("decision") == DECISION)
    add("gap_stable", decision.get("source_archive_gap_stable") is True)
    add("no_silver_repair", decision.get("silver_builder_repair_required") is False)
    add("no_silver_replace", decision.get("historical_silver_replacement_ready") is False)
    add("no_gold_rebuild", decision.get("historical_gold_rebuild_ready") is False)
    add("no_market", decision.get("ready_for_market_backtest") is False)
    add("no_retrain", decision.get("ready_for_model_retraining") is False)
    add("decision_stake", decision.get("formal_stake") == 0)

    coverage = result.get("coverage_overlap_counts", {})
    add("coverage_nbastats", coverage.get("nbastats_game_count") == 1230)
    add("coverage_pbpstats", coverage.get("pbpstats_game_count") == 1228)
    add("coverage_overlap", coverage.get("overlap_game_count") == 1228)
    add("coverage_nbastats_only", coverage.get("nbastats_only_game_count") == 2)
    add("coverage_pbpstats_only", coverage.get("pbpstats_only_game_count") == 0)
    add("coverage_union", coverage.get("union_game_count") == 1230)

    missing = result.get("missing_reason_count_histogram", {})
    add("missing_reason", missing.get("nbastats_game_present_pbpstats_game_absent") == 2)
    add("reverse_missing_zero", missing.get("pbpstats_game_present_nbastats_game_absent") == 0)

    manifests = result.get("archive_manifest_counts", {})
    nba = manifests.get("nbastats_2023", {})
    pbp = manifests.get("pbpstats_2023", {})
    add("nba_manifest", nba.get("row_count") == 567665 and nba.get("rows_after_exact_dedupe") == 567662 and nba.get("game_count") == 1230)
    add("pbp_manifest", pbp.get("row_count") == 478625 and pbp.get("rows_after_exact_dedupe") == 478085 and pbp.get("game_count") == 1228)
    add("manifest_fields", nba.get("expected_fields_missing_count") == 0 and pbp.get("expected_fields_missing_count") == 0)

    groups = result.get("pbpstats_grouping_counts", {})
    base = groups.get("possession_base", {})
    score = groups.get("possession_with_score_context", {})
    full = groups.get("possession_with_score_and_start_type", {})
    add("base_grouping_rejected", base.get("group_count") == 242363 and base.get("inconsistent_group_count") == 2 and base.get("usable_for_normalization") is False)
    add("score_grouping_rejected", score.get("group_count") == 242364 and score.get("inconsistent_group_count") == 1 and score.get("usable_for_normalization") is False)
    add("full_grouping_selected", full.get("group_count") == 242365 and full.get("inconsistent_group_count") == 0 and full.get("usable_for_normalization") is True)

    receipt = result.get("execution_receipt", {})
    add("receipt_count", receipt.get("execution_count_for_request") == 1 and receipt.get("maximum_execution_count_for_request") == 1)
    add("receipt_consumed", receipt.get("request_consumed") is True)
    add("receipt_no_repeat", receipt.get("repeat_execution_allowed") is False)
    add("receipt_network", receipt.get("network_download_performed") is True)
    add("receipt_deleted", receipt.get("temporary_material_deleted_with_runner") is True)

    boundaries = result.get("boundaries", {})
    false_boundaries = (
        "candidate_csv_downloaded_or_read",
        "chris_munch_csv_downloaded_or_read",
        "eoin_bundle_downloaded_or_read",
        "gold_database_created_or_read",
        "silver_database_created_modified_or_uploaded",
        "gold_builder_executed_or_changed",
        "silver_builder_changed_during_execution",
        "manual_row_insertion_or_override",
        "fuzzy_matching",
        "score_assisted_identity_repair",
        "source_archives_uploaded_as_artifact",
        "raw_files_emitted",
        "game_ids_emitted",
        "dates_emitted",
        "team_codes_emitted",
        "source_file_paths_emitted",
        "source_file_hashes_emitted",
        "row_level_records_emitted",
        "row_key_hashes_emitted",
        "historical_silver_replacement",
        "historical_gold_replacement",
        "cross_source_audit_rerun",
        "point_in_time_market_backtest",
        "clv_ev_roi_drawdown",
        "model_training_or_retraining",
        "betting_edge_claim",
    )
    for key in false_boundaries:
        add(f"boundary_{key}", boundaries.get(key) is False)
    add("boundary_raw_rows", boundaries.get("raw_rows_emitted") == 0)
    add("boundary_stake", boundaries.get("formal_stake") == 0)

    add("current_schema", current.get("schema_version") == "historical-silver-2023-24-source-archive-reconciliation-current-status-v2")
    add("current_state", current.get("formal_state") == FORMAL_STATE)
    add("current_decision", current.get("decision") == DECISION)
    add("current_request", current.get("request_id") == REQUEST_ID)
    add("current_result", current.get("result_record") == "data/research/historical-silver-2023-24-source-archive-reconciliation-result-v1.json")
    add("current_run", current.get("workflow_run_id") == RUN_ID)
    add("current_artifact", current.get("artifact_id") == ARTIFACT_ID and current.get("artifact_digest") == DIGEST)
    add("current_count", current.get("execution_count") == 1 and current.get("maximum_execution_count") == 1)
    add("current_consumed", current.get("request_consumed") is True and current.get("repeat_execution_allowed") is False)
    add("current_gap", current.get("source_archive_gap_stable") is True and current.get("silver_builder_repair_required") is False)
    add("current_no_activation", all(current.get(key) is False for key in (
        "ready_for_silver_builder_change",
        "ready_for_silver_exception_patch",
        "ready_for_gold_rebuild",
        "ready_for_cross_source_audit_rerun",
        "ready_for_chris_munch_data_execution",
        "ready_for_market_backtest",
        "ready_for_model_retraining",
        "ready_for_betting_edge_claim",
    )))
    add("current_next", current.get("next_research_step") == NEXT_STEP)
    add("current_stake", current.get("formal_stake") == 0)

    failed = sorted(name for name, ok in checks.items() if not ok)
    return {
        "schema_version": "historical-silver-2023-24-source-archive-reconciliation-result-validation-report-v1",
        "validated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "formal_state": "HISTORICAL_SILVER_2023_24_SOURCE_ARCHIVE_RECONCILIATION_RESULT_VALID" if not failed else "HISTORICAL_SILVER_2023_24_SOURCE_ARCHIVE_RECONCILIATION_RESULT_INVALID",
        "checks": checks,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "checks_failed": len(failed),
        "failed_checks": failed,
        "request_consumed": receipt.get("request_consumed") is True,
        "repeat_execution_allowed": False,
        "ready_for_silver_builder_change": False,
        "ready_for_gold_rebuild": False,
        "ready_for_market_backtest": False,
        "ready_for_model_retraining": False,
        "ready_for_betting_edge_claim": False,
        "next_research_step": NEXT_STEP,
        "formal_stake": 0,
    }


def self_test(result: dict[str, Any], current: dict[str, Any]) -> dict[str, bool]:
    baseline = validate(result, current)
    assert baseline["checks_failed"] == 0, baseline
    tests: dict[str, bool] = {"baseline_passes": True}

    cases = {
        "wrong_decision_blocks": ("result", ("decision", "decision"), "WRONG"),
        "wrong_overlap_blocks": ("result", ("coverage_overlap_counts", "overlap_game_count"), 999),
        "repeat_execution_blocks": ("result", ("execution_receipt", "repeat_execution_allowed"), True),
        "nonzero_stake_blocks": ("current", ("formal_stake",), 1),
        "silver_repair_blocks": ("current", ("ready_for_silver_builder_change",), True),
    }
    for name, (target, path, value) in cases.items():
        mutated_result = copy.deepcopy(result)
        mutated_current = copy.deepcopy(current)
        obj = mutated_result if target == "result" else mutated_current
        cursor: dict[str, Any] = obj
        for key in path[:-1]:
            cursor = cursor[key]
        cursor[path[-1]] = value
        report = validate(mutated_result, mutated_current)
        assert report["checks_failed"] > 0, (name, report)
        tests[name] = True
    return tests


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--current-status", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    result = read_json(args.result)
    current = read_json(args.current_status)
    report = validate(result, current)
    if args.self_test:
        report["self_test"] = self_test(result, current)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["checks_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
