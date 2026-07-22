#!/usr/bin/env python3
"""Execute one approved aggregate-only 2023-24 Silver root-cause audit."""
from __future__ import annotations

import argparse
import copy
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import historical_silver_runner as silver_builder
import analyze_historical_silver_missing_team_features_root_cause_v1 as analyzer
import validate_historical_silver_missing_team_features_root_cause_approval_v1 as gate

REQUEST_ID = gate.REQUEST_ID
SELF_TEST_PASS = "HISTORICAL_SILVER_2023_24_MISSING_TEAM_FEATURES_ROOT_CAUSE_EXECUTOR_SELF_TEST_PASS"
EXECUTION_BLOCKED = "HISTORICAL_SILVER_2023_24_MISSING_TEAM_FEATURES_ROOT_CAUSE_BLOCKED_BEFORE_RESULT"
ALLOWED_OUTCOMES = {
    "HISTORICAL_SILVER_MISSING_TEAM_FEATURES_NO_GAP",
    "HISTORICAL_SILVER_MISSING_TEAM_FEATURES_ROOT_CAUSE_BLOCKED",
    "HISTORICAL_SILVER_MISSING_TEAM_FEATURES_MIXED_ROOT_CAUSES",
    "HISTORICAL_SILVER_MISSING_TEAM_FEATURES_BUILDER_REPAIR_REQUIRED",
    "HISTORICAL_SILVER_MISSING_TEAM_FEATURES_IDENTITY_RECONCILIATION_REQUIRED",
    "HISTORICAL_SILVER_MISSING_TEAM_FEATURES_SOURCE_GAP_CONFIRMED",
}


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
        "candidate_csv_downloaded_or_read": False,
        "gold_database_created_or_read": False,
        "gold_builder_executed_or_changed": False,
        "silver_builder_changed_during_execution": False,
        "manual_row_insertion_or_override": False,
        "fuzzy_matching": False,
        "score_assisted_identity_repair": False,
        "raw_rows_emitted": 0,
        "raw_files_emitted": False,
        "silver_database_uploaded_as_artifact": False,
        "source_archives_uploaded_as_artifact": False,
        "game_ids_emitted": False,
        "dates_emitted": False,
        "team_codes_emitted": False,
        "row_level_records_emitted": False,
        "row_key_hashes_emitted": False,
        "historical_silver_replacement": False,
        "historical_gold_replacement": False,
        "opening_or_closing_labels": False,
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
        "network_download_performed": network,
        "temporary_material_deleted_with_runner": True,
    }


def approval_validation(request, approval, implementation, result, current, confirmation, event, ref):
    return gate.validate(request, approval, implementation, result, current, confirmation, event, ref)


def rebuild_summary(report: dict[str, Any]) -> dict[str, Any]:
    outputs = report.get("outputs") or {}
    tables = outputs.get("tables") or {}
    quality = report.get("quality") or {}
    sources = report.get("sources") or {}
    pbp_source = sources.get("pbpstats_2023") or {}
    return {
        "season_label": "2023-24",
        "games": int(tables["games"]),
        "team_game_features": int(tables["team_game_features"]),
        "incomplete_team_games": int(quality["incomplete_team_games"]),
        "team_inference_failures": int(pbp_source["team_inference_failures"]),
        "raw_rows_emitted": 0,
        "raw_files_emitted": False,
    }


def build_2023_24_silver(root: Path) -> tuple[Path, dict[str, Any]]:
    root.mkdir(parents=True, exist_ok=True)
    config = read_json(Path("config/historical-source-pilot.json"))
    for kind in ("pbpstats", "nbastats"):
        source = config["sources"][f"{kind}_2023"]
        source["season_label"] = "2023-24"
        source["url"] = f"https://github.com/shufinskiy/nba_data/raw/main/datasets/{kind}_2023.tar.xz"
    config_path = root / "config-2023.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    output_dir = root / "silver"
    report = silver_builder.build(config_path, output_dir, 600)
    games = int(report["outputs"]["tables"]["games"])
    features = int(report["outputs"]["tables"]["team_game_features"])
    if games != 1230:
        raise RuntimeError(f"expected 1230 Silver games, found {games}")
    if report["decision"]["ready_for_private_model_feature_pipeline"] is not True:
        raise RuntimeError("rebuilt Silver failed existing quality gate")
    summary = rebuild_summary(report)
    if summary["games"] != games or summary["team_game_features"] != features:
        raise RuntimeError("Silver rebuild summary drift")
    return output_dir / "historical-silver.sqlite.gz", summary


def self_test(request, approval, implementation, result, current) -> dict[str, Any]:
    validation = approval_validation(request, approval, implementation, result, current, REQUEST_ID, "workflow_dispatch", "refs/heads/main")
    if validation["formal_state"] != gate.READY:
        raise AssertionError(validation)
    summary = rebuild_summary({
        "sources": {"pbpstats_2023": {"team_inference_failures": 0}},
        "outputs": {"tables": {"games": 1230, "team_game_features": 2456}},
        "quality": {"incomplete_team_games": 2},
    })
    assert summary["team_inference_failures"] == 0, summary
    assert summary["incomplete_team_games"] == 2, summary
    with tempfile.TemporaryDirectory(prefix="nbavl-silver-root-cause-executor-test-") as temp_name:
        fixture = analyzer.self_test(Path(temp_name) / "fixture-report.json")
    return {
        "schema_version": "historical-silver-2023-24-missing-team-features-root-cause-executor-self-test-v1",
        "formal_state": SELF_TEST_PASS,
        "request_id": REQUEST_ID,
        "approval_validation": validation,
        "analyzer_fixture_outcome": fixture["formal_outcome"],
        "network_calls_made": False,
        "real_reference_rows_read": False,
        "real_root_cause_audit_executed": False,
        "boundaries": boundaries(),
    }


def execute(request, approval, implementation, result, current, confirmation, event, ref):
    validation = approval_validation(request, approval, implementation, result, current, confirmation, event, ref)
    if validation["formal_state"] != gate.READY:
        return {
            "schema_version": "historical-silver-2023-24-missing-team-features-root-cause-execution-report-v1",
            "formal_state": EXECUTION_BLOCKED,
            "request_id": REQUEST_ID,
            "approval_validation": validation,
            "error_type": "ApprovalValidationBlocked",
            "execution_receipt": receipt(False),
            "boundaries": boundaries(),
        }, 2
    network = False
    try:
        with tempfile.TemporaryDirectory(prefix="nbavl-silver-root-cause-real-") as temp_name:
            silver_path, rebuild = build_2023_24_silver(Path(temp_name) / "reference")
            network = True
            report = analyzer.analyze(silver_path, "2023-24")
            if report["formal_outcome"] not in ALLOWED_OUTCOMES:
                raise RuntimeError("unexpected root-cause outcome")
            if report["scope"]["silver_games"] != 1230:
                raise RuntimeError("Silver game-count drift")
            if report["scope"]["games_without_team_features"] != 2:
                raise RuntimeError("missing-feature game-count drift")
            report["schema_version"] = "historical-silver-2023-24-missing-team-features-root-cause-execution-report-v1"
            report["request_id"] = REQUEST_ID
            report["approval_validation"] = validation
            report["reference_rebuild"] = rebuild
        report["execution_receipt"] = receipt(network)
        report["boundaries"] = boundaries()
        return report, 0
    except Exception as exc:
        return {
            "schema_version": "historical-silver-2023-24-missing-team-features-root-cause-execution-report-v1",
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
    parser.add_argument("--implementation", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--current-status", type=Path, required=True)
    parser.add_argument("--confirmation-request-id", default="")
    parser.add_argument("--workflow-event", default=os.environ.get("GITHUB_EVENT_NAME", ""))
    parser.add_argument("--workflow-ref", default=os.environ.get("GITHUB_REF", ""))
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    request, approval = read_json(args.request), read_json(args.approval)
    implementation, result, current = read_json(args.implementation), read_json(args.result), read_json(args.current_status)
    confirmation = args.confirmation_request_id or (REQUEST_ID if args.self_test else "")
    event = args.workflow_event or ("workflow_dispatch" if args.self_test else "")
    ref = args.workflow_ref or ("refs/heads/main" if args.self_test else "")
    if args.validate_only:
        report = approval_validation(request, approval, implementation, result, current, confirmation, event, ref)
        code = 0 if report["formal_state"] == gate.READY else 1
    elif args.self_test:
        report, code = self_test(request, approval, implementation, result, current), 0
    else:
        report, code = execute(request, approval, implementation, result, current, confirmation, event, ref)
    write_json(args.output, report)
    print(json.dumps({"formal_state": report.get("formal_state"), "formal_outcome": report.get("formal_outcome"), "request_id": report.get("request_id"), "formal_stake": report.get("boundaries", {}).get("formal_stake", 0)}, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
