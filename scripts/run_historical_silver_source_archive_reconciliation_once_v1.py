#!/usr/bin/env python3
"""Run one approved aggregate-only Shufinskiy source archive reconciliation."""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from historical_phase2_core import audit_source
import validate_historical_silver_source_archive_reconciliation_approval_v1 as gate

REQUEST_ID = gate.REQUEST_ID
SELF_TEST_PASS = "HISTORICAL_SILVER_2023_24_SOURCE_ARCHIVE_RECONCILIATION_EXECUTOR_SELF_TEST_PASS"
EXECUTION_BLOCKED = "HISTORICAL_SILVER_2023_24_SOURCE_ARCHIVE_RECONCILIATION_BLOCKED_BEFORE_RESULT"
EXECUTION_PASS = "HISTORICAL_SILVER_2023_24_SOURCE_ARCHIVE_RECONCILIATION_AGGREGATE_VALIDATION_PASS"


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if len(payload.encode("utf-8")) > 1048576:
        raise RuntimeError("aggregate report exceeds 1 MiB")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def boundaries() -> dict[str, Any]:
    return {
        "chris_munch_csv_downloaded_or_read": False,
        "eoin_bundle_downloaded_or_read": False,
        "candidate_csv_downloaded_or_read": False,
        "gold_database_created_or_read": False,
        "silver_database_created_modified_or_uploaded": False,
        "gold_builder_executed_or_changed": False,
        "silver_builder_changed_during_execution": False,
        "manual_row_insertion_or_override": False,
        "fuzzy_matching": False,
        "score_assisted_identity_repair": False,
        "raw_rows_emitted": 0,
        "raw_files_emitted": False,
        "source_archives_uploaded_as_artifact": False,
        "silver_database_uploaded_as_artifact": False,
        "gold_database_uploaded_as_artifact": False,
        "game_ids_emitted": False,
        "dates_emitted": False,
        "team_codes_emitted": False,
        "source_file_paths_emitted": False,
        "source_file_hashes_emitted": False,
        "row_level_records_emitted": False,
        "row_key_hashes_emitted": False,
        "historical_silver_replacement": False,
        "historical_gold_replacement": False,
        "cross_source_audit_rerun": False,
        "point_in_time_market_backtest": False,
        "clv_ev_roi_drawdown": False,
        "model_training_or_retraining": False,
        "betting_edge_claim": False,
        "formal_stake": 0,
    }


def receipt(network: bool) -> dict[str, Any]:
    return {
        "workflow_event": os.environ.get("GITHUB_EVENT_NAME"),
        "workflow_ref": os.environ.get("GITHUB_REF"),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "github_sha": os.environ.get("GITHUB_SHA"),
        "execution_count_for_request": 1,
        "maximum_execution_count_for_request": 1,
        "request_consumed": True,
        "repeat_execution_allowed": False,
        "network_download_performed": network,
        "temporary_material_deleted_with_runner": True,
    }


def validate_approval(request, approval, design, result, current, registry, confirmation, event, ref):
    return gate.validate(request, approval, design, result, current, registry, confirmation, event, ref)


def summarize_source(audit: dict[str, Any]) -> dict[str, Any]:
    scan = audit["scan"]
    archive = audit["archive"]
    rows = scan["rows"]
    dedupe = scan["exact_row_deduplication"]
    return {
        "archive_bytes": int(archive["bytes"]),
        "archive_megabytes": archive["megabytes"],
        "archive_member_count": int(archive["member_count"]),
        "csv_bytes": int(scan["file"]["bytes"]),
        "csv_megabytes": scan["file"]["megabytes"],
        "column_count": int(scan["column_count"]),
        "row_count": int(rows["row_count"]),
        "game_count": int(rows["game_count"]),
        "rows_after_exact_dedupe": int(dedupe["rows_after_exact_dedupe"]),
        "exact_duplicate_rows": int(dedupe["exact_duplicate_rows"]),
        "expected_fields_missing_count": len(scan["expected_fields_missing"]),
    }


def summarize_grouping(audit: dict[str, Any]) -> dict[str, Any]:
    output = {}
    for group in audit["scan"].get("grouping_checks", []):
        if not group.get("available"):
            continue
        output[group["name"]] = {
            "group_count": int(group["group_count"]),
            "incomplete_rows": int(group["incomplete_rows"]),
            "inconsistent_group_count": int(group["inconsistent_group_count"]),
            "usable_for_normalization": bool(group["usable_for_normalization"]),
        }
    return output


def reconcile(pbp_audit: dict[str, Any], nba_audit: dict[str, Any]) -> dict[str, Any]:
    pbp_games = set(pbp_audit["scan"]["game_ids"])
    nba_games = set(nba_audit["scan"]["game_ids"])
    nbastats_only = len(nba_games - pbp_games)
    pbpstats_only = len(pbp_games - nba_games)
    overlap = len(nba_games & pbp_games)
    union = len(nba_games | pbp_games)
    missing_histogram = {
        "nbastats_game_present_pbpstats_game_absent": nbastats_only,
        "pbpstats_game_present_nbastats_game_absent": pbpstats_only,
    }
    stable = (
        union == 1230
        and len(nba_games) == 1230
        and len(pbp_games) == 1228
        and overlap == 1228
        and nbastats_only == 2
        and pbpstats_only == 0
    )
    return {
        "coverage_overlap_counts": {
            "nbastats_game_count": len(nba_games),
            "pbpstats_game_count": len(pbp_games),
            "overlap_game_count": overlap,
            "union_game_count": union,
            "nbastats_only_game_count": nbastats_only,
            "pbpstats_only_game_count": pbpstats_only,
        },
        "missing_reason_count_histogram": missing_histogram,
        "decision_summary": {
            "decision": "SOURCE_ARCHIVE_GAP_STABLE" if stable else "SOURCE_ARCHIVE_GAP_NOT_CONFIRMED",
            "source_archive_gap_stable": stable,
            "silver_builder_repair_required": False,
            "historical_silver_replacement_ready": False,
            "historical_gold_rebuild_ready": False,
            "ready_for_market_backtest": False,
            "ready_for_model_retraining": False,
            "formal_stake": 0,
        },
    }


def build_report(
    request: dict[str, Any],
    approval: dict[str, Any],
    validation: dict[str, Any],
    pbp_audit: dict[str, Any],
    nba_audit: dict[str, Any],
    network: bool,
) -> dict[str, Any]:
    reconciliation = reconcile(pbp_audit, nba_audit)
    return {
        "schema_version": "historical-silver-2023-24-source-archive-reconciliation-execution-report-v1",
        "formal_state": EXECUTION_PASS,
        "request_id": REQUEST_ID,
        "approval_validation": validation,
        "season_label": "2023-24",
        "source_id": request["frozen_scope"]["source_id"],
        "archive_manifest_counts": {
            "pbpstats_2023": summarize_source(pbp_audit),
            "nbastats_2023": summarize_source(nba_audit),
        },
        "pbpstats_grouping_counts": summarize_grouping(pbp_audit),
        **reconciliation,
        "execution_receipt": receipt(network),
        "boundaries": boundaries(),
    }


def self_test(request, approval, design, result, current, registry) -> dict[str, Any]:
    validation = validate_approval(request, approval, design, result, current, registry, REQUEST_ID, "workflow_dispatch", "refs/heads/main")
    if validation["formal_state"] != gate.READY:
        raise AssertionError(validation)
    pbp = {"scan": {"game_ids": [f"g{i}" for i in range(1228)]}}
    nba = {"scan": {"game_ids": [f"g{i}" for i in range(1230)]}}
    reconciliation = reconcile(pbp, nba)
    assert reconciliation["decision_summary"]["decision"] == "SOURCE_ARCHIVE_GAP_STABLE", reconciliation
    return {
        "schema_version": "historical-silver-2023-24-source-archive-reconciliation-executor-self-test-v1",
        "formal_state": SELF_TEST_PASS,
        "request_id": REQUEST_ID,
        "approval_validation": validation,
        "reconciliation_fixture": reconciliation,
        "network_calls_made": False,
        "shufinskiy_source_archives_read": False,
        "real_reconciliation_executed": False,
        "boundaries": boundaries(),
    }


def execute(request, approval, design, result, current, registry, confirmation, event, ref):
    validation = validate_approval(request, approval, design, result, current, registry, confirmation, event, ref)
    if validation["formal_state"] != gate.READY:
        return {
            "schema_version": "historical-silver-2023-24-source-archive-reconciliation-execution-report-v1",
            "formal_state": EXECUTION_BLOCKED,
            "request_id": REQUEST_ID,
            "approval_validation": validation,
            "error_type": "ApprovalValidationBlocked",
            "execution_receipt": receipt(False),
            "boundaries": boundaries(),
        }, 2
    network = False
    try:
        with tempfile.TemporaryDirectory(prefix="nbavl-source-archive-reconciliation-") as temp_name:
            temp = Path(temp_name)
            config = read_json(Path("config/historical-source-pilot.json"))
            sources = config["sources"]
            pbp_audit = audit_source("pbpstats_2023", sources["pbpstats_2023"], temp, 600, 0)
            network = True
            nba_audit = audit_source("nbastats_2023", sources["nbastats_2023"], temp, 600, 0)
            report = build_report(request, approval, validation, pbp_audit, nba_audit, network)
        return report, 0
    except Exception as exc:
        return {
            "schema_version": "historical-silver-2023-24-source-archive-reconciliation-execution-report-v1",
            "formal_state": EXECUTION_BLOCKED,
            "request_id": REQUEST_ID,
            "approval_validation": validation,
            "error_type": type(exc).__name__,
            "error_summary": str(exc).replace("/tmp/", "<temporary>/")[:500],
            "execution_receipt": receipt(network),
            "boundaries": boundaries(),
        }, 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--design", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--current-status", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--confirmation-request-id", default="")
    parser.add_argument("--workflow-event", default=os.environ.get("GITHUB_EVENT_NAME", ""))
    parser.add_argument("--workflow-ref", default=os.environ.get("GITHUB_REF", ""))
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    request = read_json(args.request)
    approval = read_json(args.approval)
    design = read_json(args.design)
    result = read_json(args.result)
    current = read_json(args.current_status)
    registry = read_json(args.registry)
    confirmation = args.confirmation_request_id or (REQUEST_ID if args.self_test else "")
    event = args.workflow_event or ("workflow_dispatch" if args.self_test else "")
    ref = args.workflow_ref or ("refs/heads/main" if args.self_test else "")
    if args.validate_only:
        report = validate_approval(request, approval, design, result, current, registry, confirmation, event, ref)
        code = 0 if report["formal_state"] == gate.READY else 1
    elif args.self_test:
        report = self_test(request, approval, design, result, current, registry)
        code = 0
    else:
        report, code = execute(request, approval, design, result, current, registry, confirmation, event, ref)
    write_json(args.output, report)
    print(json.dumps({
        "formal_state": report.get("formal_state"),
        "decision": report.get("decision_summary", {}).get("decision"),
        "request_id": report.get("request_id"),
        "formal_stake": report.get("boundaries", {}).get("formal_stake", 0),
    }, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
