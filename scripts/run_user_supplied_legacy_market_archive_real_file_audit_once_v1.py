#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import build_historical_gold_multiseason as gold_builder
import combine_historical_silver as silver_combiner
import historical_silver_runner as silver_builder
import run_eoin_kaggle_census_v1 as kaggle_source
import run_user_supplied_legacy_market_archive_cross_source_audit_v1 as audit
import validate_user_supplied_legacy_market_archive_real_file_audit_approval_v1 as gate

REQUEST_ID = gate.REQUEST_ID
YEARS = gate.EXPECTED_YEARS
ALLOWED = {audit.VALIDATED, audit.RETAIN, audit.BLOCKED}
SELF_TEST_PASS = "LEGACY_MARKET_ARCHIVE_REAL_FILE_AUDIT_EXECUTOR_SELF_TEST_PASS"
EXECUTION_BLOCKED = "LEGACY_MARKET_ARCHIVE_REAL_FILE_AUDIT_EXECUTION_BLOCKED_BEFORE_SCIENTIFIC_RESULT"


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"invalid JSON object: {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if len(payload.encode("utf-8")) > 1048576:
        raise RuntimeError("aggregate report exceeds 1 MiB")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def exact_candidate(root: Path) -> Path:
    matches = []
    for path in root.rglob(gate.EXPECTED_FILE):
        if not path.is_file() or path.stat().st_size != gate.EXPECTED_BYTES:
            continue
        if audit.sha256_file(path) == gate.EXPECTED_SHA256:
            matches.append(path)
    if len(matches) != 1:
        raise RuntimeError(f"exact candidate count must be 1, found {len(matches)}")
    return matches[0]


def label(year: int) -> str:
    return f"{year}-{str(year + 1)[-2:]}"


def reference_build(root: Path) -> tuple[Path, Path, dict[str, Any]]:
    base = read_json(Path("config/historical-source-pilot.json"))
    season_root = root / "seasons"
    summaries = {}
    for year in YEARS:
        config = copy.deepcopy(base)
        for kind in ("pbpstats", "nbastats"):
            item = config["sources"][f"{kind}_2023"]
            item["season_label"] = label(year)
            item["url"] = (
                f"https://github.com/shufinskiy/nba_data/raw/main/datasets/{kind}_{year}.tar.xz"
            )
        config_path = root / f"config-{year}.json"
        config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        report = silver_builder.build(config_path, season_root / str(year), 600)
        games = int(report["outputs"]["tables"]["games"])
        ready = report["decision"]["ready_for_private_model_feature_pipeline"] is True
        if games < 1000 or not ready:
            raise RuntimeError(f"Silver quality failed for {label(year)}")
        summaries[label(year)] = {"games": games, "ready": ready}

    combined_dir = root / "combined"
    sources = silver_combiner.discover_sources(season_root)
    if len(sources) != 5:
        raise RuntimeError(f"expected five Silver databases, found {len(sources)}")
    combined = silver_combiner.merge_sources(sources, combined_dir)
    expected = [label(year) for year in YEARS]
    if combined["seasons"] != expected:
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
    return (
        silver_path,
        gold_dir / "historical-gold-multiseason.sqlite.gz",
        summary,
    )


def boundary() -> dict[str, Any]:
    return {
        "raw_rows_emitted": 0,
        "raw_files_emitted": False,
        "raw_files_uploaded_as_artifact": False,
        "candidate_csv_uploaded_as_artifact": False,
        "reference_databases_uploaded_as_artifact": False,
        "source_archives_uploaded_as_artifact": False,
        "unmatched_keys_or_game_ids_emitted": False,
        "opening_or_closing_labels": False,
        "point_in_time_market_backtest": False,
        "clv_ev_roi_drawdown": False,
        "historical_silver_replacement": False,
        "historical_gold_replacement": False,
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


def self_test(request, approval, implementation, current, policy) -> dict[str, Any]:
    validation = gate.validate_approval(
        request, approval, implementation, current,
        REQUEST_ID, "workflow_dispatch", "refs/heads/main",
    )
    if validation["formal_state"] != gate.READY:
        raise AssertionError(validation)
    approval_tests = gate.self_test(request, approval, implementation, current)
    audit_test = audit.self_test(implementation, policy)
    return {
        "schema_version": "legacy-market-real-file-audit-executor-self-test-v1",
        "formal_state": SELF_TEST_PASS,
        "request_id": REQUEST_ID,
        "approval_validation": validation,
        "approval_self_tests": approval_tests,
        "audit_fixture_games": audit_test["fixture_games"],
        "audit_self_tests": audit_test["self_tests"],
        "network_calls_made": False,
        "real_candidate_csv_read": False,
        "real_reference_database_read": False,
        "real_file_audit_executed": False,
        "boundaries": boundary(),
    }


def execute(request, approval, implementation, current, policy, confirmation, event, ref):
    validation = gate.validate_approval(
        request, approval, implementation, current, confirmation, event, ref
    )
    if validation["formal_state"] != gate.READY:
        return {
            "schema_version": "legacy-market-real-file-audit-execution-report-v1",
            "formal_state": EXECUTION_BLOCKED,
            "request_id": REQUEST_ID,
            "approval_validation": validation,
            "error_type": "ApprovalValidationBlocked",
            "execution_receipt": receipt(False),
            "boundaries": boundary(),
        }, 2

    network = False
    try:
        with tempfile.TemporaryDirectory(prefix="nbavl-legacy-market-approved-") as temp_name:
            temp = Path(temp_name)
            dataset = kaggle_source.download_dataset(
                gate.EXPECTED_DATASET, temp / "candidate"
            )
            network = True
            candidate = exact_candidate(dataset)
            silver, gold, reference = reference_build(temp / "reference")
            report = audit.run_audit(
                implementation, policy, candidate, gold, silver, fixture_mode=False
            )
            if report["formal_outcome"] not in ALLOWED:
                raise RuntimeError("unexpected scientific outcome")
            report["schema_version"] = "legacy-market-real-file-audit-execution-report-v1"
            report["request_id"] = REQUEST_ID
            report["approval_validation"] = validation
            report["candidate_download"] = {
                "dataset_handle": gate.EXPECTED_DATASET,
                "file_name": candidate.name,
                "file_bytes": candidate.stat().st_size,
                "file_sha256": audit.sha256_file(candidate),
                "exact_identity_passed": True,
                "temporary_storage_only": True,
            }
            report["reference_rebuild"] = reference
        report["execution_receipt"] = receipt(True)
        report["boundaries"] = boundary()
        return report, 0
    except Exception as exc:
        return {
            "schema_version": "legacy-market-real-file-audit-execution-report-v1",
            "formal_state": EXECUTION_BLOCKED,
            "request_id": REQUEST_ID,
            "approval_validation": validation,
            "error_type": type(exc).__name__,
            "error_summary": str(exc).replace("/tmp/", "<temporary>/")[:500],
            "execution_receipt": receipt(network),
            "boundaries": boundary(),
        }, 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--implementation", type=Path, required=True)
    parser.add_argument("--current-status", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--confirmation-request-id", default="")
    parser.add_argument("--workflow-event", default=os.environ.get("GITHUB_EVENT_NAME", ""))
    parser.add_argument("--workflow-ref", default=os.environ.get("GITHUB_REF", ""))
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    request = read_json(args.request)
    approval = read_json(args.approval)
    implementation = read_json(args.implementation)
    current = read_json(args.current_status)
    policy = read_json(args.policy)
    confirmation = args.confirmation_request_id or (REQUEST_ID if args.self_test else "")
    event = args.workflow_event or ("workflow_dispatch" if args.self_test else "")
    ref = args.workflow_ref or ("refs/heads/main" if args.self_test else "")

    if args.validate_only:
        report = gate.validate_approval(
            request, approval, implementation, current, confirmation, event, ref
        )
        code = 0 if report["formal_state"] == gate.READY else 1
    elif args.self_test:
        report = self_test(request, approval, implementation, current, policy)
        code = 0
    else:
        report, code = execute(
            request, approval, implementation, current, policy,
            confirmation, event, ref,
        )
    write_json(args.output, report)
    print(json.dumps({
        "formal_state": report.get("formal_state"),
        "formal_outcome": report.get("formal_outcome"),
        "request_id": report.get("request_id"),
        "formal_stake": report.get("boundaries", {}).get("formal_stake", 0),
    }, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
