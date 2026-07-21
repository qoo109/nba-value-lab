#!/usr/bin/env python3
"""Execute one approved aggregate-only Gold/Silver coverage reconciliation."""
from __future__ import annotations

import argparse
import copy
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import analyze_historical_gold_silver_coverage_v1 as analyzer
import build_historical_gold_multiseason as gold_builder
import combine_historical_silver as silver_combiner
import historical_silver_runner as silver_builder
import validate_historical_gold_silver_coverage_real_reference_approval_v1 as gate

REQUEST_ID = gate.REQUEST_ID
YEARS = [2019, 2020, 2021, 2022, 2023]
LABELS = ["2019-20", "2020-21", "2021-22", "2022-23", "2023-24"]
SELF_TEST_PASS = "HISTORICAL_GOLD_SILVER_COVERAGE_RECONCILIATION_EXECUTOR_SELF_TEST_PASS"
EXECUTION_BLOCKED = "HISTORICAL_GOLD_SILVER_COVERAGE_RECONCILIATION_EXECUTION_BLOCKED_BEFORE_RESULT"
REFERENCE_DRIFT = "HISTORICAL_GOLD_SILVER_COVERAGE_RECONCILIATION_REFERENCE_DRIFT_BLOCKED"
ALLOWED = {
    "HISTORICAL_GOLD_SILVER_COVERAGE_RECONCILIATION_NO_GAP",
    "HISTORICAL_GOLD_SILVER_COVERAGE_RECONCILIATION_BLOCKED",
    "HISTORICAL_GOLD_SILVER_COVERAGE_RECONCILIATION_MIXED_CAUSES",
    "HISTORICAL_GOLD_SILVER_COVERAGE_RECONCILIATION_BUILDER_REPAIR_REQUIRED",
    "HISTORICAL_GOLD_SILVER_COVERAGE_RECONCILIATION_SOURCE_DATA_GAP_CONFIRMED",
    REFERENCE_DRIFT,
}


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if len(payload.encode("utf-8")) > 1048576:
        raise RuntimeError("aggregate report exceeds 1 MiB")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def season_label(year: int) -> str:
    return f"{year}-{str(year + 1)[-2:]}"


def build_reference(root: Path) -> tuple[Path, Path, dict[str, Any]]:
    root.mkdir(parents=True, exist_ok=True)
    base = read_json(Path("config/historical-source-pilot.json"))
    season_root = root / "seasons"
    summaries: dict[str, Any] = {}
    for year in YEARS:
        config = copy.deepcopy(base)
        for kind in ("pbpstats", "nbastats"):
            item = config["sources"][f"{kind}_2023"]
            item["season_label"] = season_label(year)
            item["url"] = f"https://github.com/shufinskiy/nba_data/raw/main/datasets/{kind}_{year}.tar.xz"
        config_path = root / f"config-{year}.json"
        config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        report = silver_builder.build(config_path, season_root / str(year), 600)
        games = int(report["outputs"]["tables"]["games"])
        ready = report["decision"]["ready_for_private_model_feature_pipeline"] is True
        if games < 1000 or not ready:
            raise RuntimeError(f"Silver quality failed for {season_label(year)}")
        summaries[season_label(year)] = {"games": games, "ready": ready}

    combined_dir = root / "combined"
    sources = silver_combiner.discover_sources(season_root)
    if len(sources) != 5:
        raise RuntimeError(f"expected five Silver databases, found {len(sources)}")
    combined = silver_combiner.merge_sources(sources, combined_dir)
    if combined["seasons"] != LABELS:
        raise RuntimeError("combined Silver season drift")
    if combined["decision"]["ready_for_multiseason_gold"] is not True:
        raise RuntimeError("combined Silver not Gold-ready")
    if combined["quality"]["all_duplicate_checks_pass"] is not True:
        raise RuntimeError("combined Silver duplicate failure")

    silver_path = combined_dir / "historical-silver-multiseason.sqlite.gz"
    gold_dir = root / "gold"
    gold = gold_builder.build(silver_path, gold_dir)
    pit = gold["quality"]["point_in_time"]
    matchups = int(gold["outputs"]["tables"]["gold_matchup_features"])
    if matchups < 5700 or pit["passed"] is not True or pit["violations"] != 0:
        raise RuntimeError("Historical Gold quality failure")
    summary = {
        "season_silver": summaries,
        "combined_silver": {
            "seasons": combined["seasons"],
            "games": combined["outputs"]["tables"]["games"],
            "duplicate_checks_passed": combined["quality"]["all_duplicate_checks_pass"],
        },
        "historical_gold": {
            "matchup_rows": matchups,
            "team_feature_rows": gold["outputs"]["tables"]["gold_team_game_features"],
            "strict_point_in_time_violations": pit["violations"],
        },
        "raw_rows_emitted": 0,
        "raw_files_emitted": False,
    }
    return silver_path, gold_dir / "historical-gold-multiseason.sqlite.gz", summary


def boundaries() -> dict[str, Any]:
    return {
        "candidate_csv_downloaded_or_read": False,
        "raw_rows_emitted": 0,
        "raw_files_emitted": False,
        "reference_databases_uploaded_as_artifact": False,
        "source_archives_uploaded_as_artifact": False,
        "game_ids_emitted": False,
        "dates_emitted": False,
        "team_codes_emitted": False,
        "row_key_hashes_emitted": False,
        "gold_builder_changed_during_execution": False,
        "manual_row_insertion_or_override": False,
        "fuzzy_matching": False,
        "score_assisted_identity_repair": False,
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
        "network_reference_download_performed": network,
        "temporary_material_deleted_with_runner": True,
    }


def validate(request, approval, implementation, result, confirmation, event, ref):
    return gate.evaluate(request, approval, implementation, result, confirmation, event, ref)


def self_test(request, approval, implementation, result) -> dict[str, Any]:
    validation = validate(request, approval, implementation, result, REQUEST_ID, "workflow_dispatch", "refs/heads/main")
    if validation["formal_state"] != gate.READY:
        raise AssertionError(validation)
    with tempfile.TemporaryDirectory(prefix="nbavl-gold-silver-executor-self-test-") as temp_name:
        root = Path(temp_name)
        silver, gold = root / "silver.sqlite", root / "gold.sqlite"
        analyzer.write_fixture_databases(silver, gold)
        diagnostic = analyzer.analyze(silver, gold, ["2023-24"])
    return {
        "schema_version": "historical-gold-silver-coverage-real-reference-executor-self-test-v1",
        "formal_state": SELF_TEST_PASS,
        "request_id": REQUEST_ID,
        "approval_validation": validation,
        "fixture_formal_outcome": diagnostic["formal_outcome"],
        "fixture_missing_gold_for_silver": diagnostic["coverage"]["missing_gold_for_silver"],
        "network_calls_made": False,
        "real_reference_rows_read": False,
        "real_reconciliation_executed": False,
        "boundaries": boundaries(),
    }


def execute(request, approval, implementation, result, confirmation, event, ref):
    validation = validate(request, approval, implementation, result, confirmation, event, ref)
    if validation["formal_state"] != gate.READY:
        return {
            "schema_version": "historical-gold-silver-coverage-real-reference-execution-report-v1",
            "formal_outcome": EXECUTION_BLOCKED,
            "request_id": REQUEST_ID,
            "approval_validation": validation,
            "error_type": "ApprovalValidationBlocked",
            "execution_receipt": receipt(False),
            "boundaries": boundaries(),
        }, 2

    network = False
    try:
        with tempfile.TemporaryDirectory(prefix="nbavl-gold-silver-approved-") as temp_name:
            network = True
            silver, gold, reference = build_reference(Path(temp_name) / "reference")
            report = analyzer.analyze(silver, gold, LABELS)
            observed = (
                report["scope"]["silver_game_rows"],
                report["scope"]["gold_matchup_rows"],
                report["coverage"]["missing_gold_for_silver"],
            )
            report["diagnostic_formal_outcome"] = report["formal_outcome"]
            if observed != (5826, 5824, 2):
                report["formal_outcome"] = REFERENCE_DRIFT
            if report["formal_outcome"] not in ALLOWED:
                raise RuntimeError("unexpected reconciliation outcome")
            report["schema_version"] = "historical-gold-silver-coverage-real-reference-execution-report-v1"
            report["request_id"] = REQUEST_ID
            report["approval_validation"] = validation
            report["reference_rebuild"] = reference
        report["execution_receipt"] = receipt(True)
        report["boundaries"] = boundaries()
        return report, 0
    except Exception as exc:
        return {
            "schema_version": "historical-gold-silver-coverage-real-reference-execution-report-v1",
            "formal_outcome": EXECUTION_BLOCKED,
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
    parser.add_argument("--confirmation-request-id", default="")
    parser.add_argument("--workflow-event", default=os.environ.get("GITHUB_EVENT_NAME", ""))
    parser.add_argument("--workflow-ref", default=os.environ.get("GITHUB_REF", ""))
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    request, approval = read_json(args.request), read_json(args.approval)
    implementation, result = read_json(args.implementation), read_json(args.result)
    confirmation = args.confirmation_request_id or (REQUEST_ID if args.self_test else "")
    event = args.workflow_event or ("workflow_dispatch" if args.self_test else "")
    ref = args.workflow_ref or ("refs/heads/main" if args.self_test else "")
    if args.self_test:
        report, code = self_test(request, approval, implementation, result), 0
    elif args.validate_only:
        report = validate(request, approval, implementation, result, confirmation, event, ref)
        code = 0 if report["formal_state"] == gate.READY else 2
    else:
        report, code = execute(request, approval, implementation, result, confirmation, event, ref)
    write_json(args.output, report)
    print(json.dumps({
        "formal_outcome": report.get("formal_outcome", report.get("formal_state")),
        "request_id": REQUEST_ID,
        "formal_stake": report.get("boundaries", {}).get("formal_stake", report.get("formal_stake", 0)),
    }, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
