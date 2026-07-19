#!/usr/bin/env python3
"""Execute one approved aggregate-only Eoin full-adapter validation run.

The runner may read the four approved Eoin files in temporary storage, but it
emits one aggregate JSON report only. It never writes raw rows, raw files,
Silver/Gold replacements, model inputs, or market outputs.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import run_eoin_kaggle_census_v1 as kaggle_source
import run_eoin_role_limited_adapter_v1 as adapter

REQUEST_SCHEMA = "eoin-full-adapter-one-time-execution-request-v1"
APPROVAL_SCHEMA = "eoin-full-adapter-one-time-execution-approval-v1"
REQUEST_ID = "EOIN-FULL-ADAPTER-2026-07-19-001"
APPROVAL_READY = "ONE_TIME_EXECUTION_APPROVAL_VALID_READY_FOR_MANUAL_DISPATCH"
APPROVAL_BLOCKED = "ONE_TIME_EXECUTION_APPROVAL_BLOCKED"
SELF_TEST_PASS = "ONE_TIME_EXECUTION_EXECUTOR_SELF_TEST_PASS"
EXECUTION_PASS = "ONE_TIME_FULL_ADAPTER_AGGREGATE_VALIDATION_PASS"
EXECUTION_RESEARCH_BLOCKED = "ONE_TIME_FULL_ADAPTER_AGGREGATE_VALIDATION_RESEARCH_BLOCKED"
EXPECTED_FILES = ("Games.csv", "TeamStatistics.csv", "PlayerStatistics.csv", "PlayByPlay.parquet")


class ExecutionBlocked(RuntimeError):
    """Raised before network or raw-data access when admission checks fail."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def ratio(numerator: int, denominator: int) -> float | None:
    return None if denominator == 0 else numerator / denominator


def validate_approval(
    request: dict[str, Any],
    approval: dict[str, Any],
    manifest: dict[str, Any],
    execution_policy: dict[str, Any],
    confirmation_request_id: str,
    workflow_event: str,
    workflow_ref: str,
) -> dict[str, Any]:
    failures: list[str] = []

    def check(condition: bool, name: str) -> None:
        if not condition:
            failures.append(name)

    check(request.get("schema_version") == REQUEST_SCHEMA, "request.schema_version")
    check(request.get("request_id") == REQUEST_ID, "request.request_id")
    check(request.get("request_state") == "AWAITING_EXPLICIT_USER_APPROVAL", "request.state")
    check(request.get("approval_boundary", {}).get("approval_granted") is False, "request.was_unapproved")
    check(request.get("approval_boundary", {}).get("execution_enabled") is False, "request.execution_was_disabled")
    check(request.get("frozen_scope", {}).get("one_time_only") is True, "request.one_time")
    check(request.get("frozen_scope", {}).get("workflow_dispatch_only") is True, "request.dispatch_only")
    check(request.get("frozen_scope", {}).get("required_input_files") == list(EXPECTED_FILES), "request.files")
    check(request.get("execution_boundary", {}).get("full_bundle_execution_count") == 0, "request.no_prior_execution")
    check(request.get("execution_boundary", {}).get("raw_eoin_rows_read") is False, "request.no_prior_raw_read")
    check(request.get("execution_boundary", {}).get("formal_stake") == 0, "request.stake")

    check(approval.get("schema_version") == APPROVAL_SCHEMA, "approval.schema_version")
    check(approval.get("request_id") == REQUEST_ID, "approval.request_id")
    check(approval.get("approval_state") == "EXPLICIT_USER_APPROVAL_GRANTED", "approval.state")
    check(approval.get("approved_by") == "repository_owner_user", "approval.approved_by")
    check(approval.get("user_response") == "好 我核准", "approval.user_response")
    authorization = approval.get("execution_authorization", {})
    check(authorization.get("one_time_only") is True, "approval.one_time")
    check(authorization.get("maximum_execution_count") == 1, "approval.maximum_execution_count")
    check(authorization.get("executions_recorded_before_approval") == 0, "approval.no_prior_execution")
    check(authorization.get("workflow_dispatch_only") is True, "approval.dispatch_only")
    check(authorization.get("approved_ref") == "refs/heads/main", "approval.approved_ref")
    check(authorization.get("required_input_files") == list(EXPECTED_FILES), "approval.files")
    check(authorization.get("temporary_network_download_allowed") is True, "approval.network_download")
    check(authorization.get("temporary_raw_rows_may_be_read") is True, "approval.temp_raw_read")
    check(authorization.get("aggregate_outputs_only") is True, "approval.aggregate_only")
    check(authorization.get("execution_enabled_for_this_request") is True, "approval.execution_enabled")
    check(approval.get("required_confirmation_input") == REQUEST_ID, "approval.confirmation_value")

    acknowledgements = approval.get("acknowledgements", {})
    for key in (
        "raw_rows_or_raw_files_may_be_uploaded_as_artifact",
        "downloaded_archive_may_be_uploaded_as_artifact",
        "historical_silver_replacement_authorized",
        "historical_gold_replacement_authorized",
        "player_stat_parity_claim_authorized",
        "player_stat_feature_import_authorized",
        "model_training_or_retraining_authorized",
        "market_backtest_authorized",
        "clv_ev_roi_drawdown_authorized",
        "betting_edge_claim_authorized",
        "betting_decision_layer_authorized",
    ):
        check(acknowledgements.get(key) is False, f"approval.no_{key}")
    check(acknowledgements.get("formal_stake") == 0, "approval.stake")

    check(confirmation_request_id == REQUEST_ID, "runtime.confirmation_request_id")
    check(workflow_event == "workflow_dispatch", "runtime.workflow_dispatch")
    check(workflow_ref == "refs/heads/main", "runtime.main_ref")

    switches = manifest.get("execution_switches", {})
    check(switches.get("explicit_user_approval_required") is True, "manifest.approval_required")
    check(switches.get("approval_record_required") is True, "manifest.record_required")
    check(switches.get("automatic_main_push_execution_allowed") is False, "manifest.no_push_execution")
    check(switches.get("scheduled_execution_allowed") is False, "manifest.no_schedule")
    check(manifest.get("operational_limits", {}).get("required_input_files") == list(EXPECTED_FILES), "manifest.files")
    check(execution_policy.get("activation_boundary", {}).get("automatic_main_push_execution_allowed") is False, "policy.no_push_execution")
    check(execution_policy.get("activation_boundary", {}).get("scheduled_execution_allowed") is False, "policy.no_schedule")
    check(execution_policy.get("forbidden_promotions", {}).get("formal_stake") == 0, "policy.stake")

    return {
        "schema_version": "eoin-full-adapter-one-time-execution-approval-validation-v1",
        "validated_at": utc_now(),
        "formal_state": APPROVAL_READY if not failures else APPROVAL_BLOCKED,
        "request_id": REQUEST_ID,
        "checks_failed": len(failures),
        "failed_checks": failures,
        "ready_for_one_time_aggregate_execution": not failures,
        "ready_for_repeat_execution": False,
        "ready_for_silver_replacement": False,
        "ready_for_gold_replacement": False,
        "ready_for_model_retraining": False,
        "ready_for_market_backtest": False,
        "ready_for_betting_edge_claim": False,
        "formal_stake": 0,
    }


def find_single_file(root: Path, filename: str) -> Path:
    matches = sorted(path for path in root.rglob(filename) if path.is_file())
    if len(matches) != 1:
        raise ExecutionBlocked(f"expected exactly one {filename}; found {len(matches)}")
    return matches[0]


def inspect_inputs(paths: dict[str, Path], limits: dict[str, Any]) -> dict[str, Any]:
    items = [
        {"name": name, "size_bytes": path.stat().st_size, "sha256": sha256_file(path)}
        for name, path in paths.items()
    ]
    total_bytes = sum(item["size_bytes"] for item in items)
    largest = max((item["size_bytes"] for item in items), default=0)
    checks = {
        "exact_allowlisted_file_count": len(items) == int(limits["max_input_file_count"]) == 4,
        "required_file_names_exact": sorted(paths) == sorted(EXPECTED_FILES),
        "total_bytes_within_limit": total_bytes <= int(limits["max_total_input_bytes"]),
        "largest_file_within_limit": largest <= int(limits["max_single_input_file_bytes"]),
    }
    return {
        "files": items,
        "file_count": len(items),
        "total_bytes": total_bytes,
        "largest_file_bytes": largest,
        "checks": checks,
        "all_checks_passed": all(checks.values()),
        "raw_rows_emitted": 0,
        "raw_files_emitted": False,
    }


def build_aggregate_report(paths: dict[str, Path], approval_validation: dict[str, Any], fixture_mode: bool) -> dict[str, Any]:
    games_report = adapter.load_games(paths["Games.csv"])
    games = games_report.pop("_games")
    team_report = adapter.load_team_stats(paths["TeamStatistics.csv"])
    team_rows = team_report.pop("_rows_by_game")
    player_report = adapter.load_player_stats(paths["PlayerStatistics.csv"])
    player_games = player_report.pop("_games")
    pbp_report = adapter.load_pbp_metadata(paths["PlayByPlay.parquet"])
    pbp_games = pbp_report.pop("_games", set())

    game_ids = set(games)
    team_covered = team_score_matched = player_covered = pbp_covered = 0
    for game_id, game in games.items():
        rows = team_rows.get(game_id, [])
        if len(rows) == 2:
            team_covered += 1
            observed = [row.get("team_score") for row in rows]
            expected = [game.get("home_score"), game.get("away_score")]
            if all(value is not None for value in observed + expected) and sorted(observed) == sorted(expected):
                team_score_matched += 1
        if game_id in player_games:
            player_covered += 1
        if game_id in pbp_games:
            pbp_covered += 1

    thresholds = {
        "minimum_games": 2 if fixture_mode else 1000,
        "team_coverage_minimum": 1.0 if fixture_mode else 0.98,
        "team_score_match_minimum": 1.0 if fixture_mode else 0.98,
        "player_candidate_coverage_minimum": 1.0 if fixture_mode else 0.95,
        "pbp_coverage_minimum": 1.0 if fixture_mode else 0.95,
        "duplicate_game_id_groups_maximum": 0,
    }
    observed = {
        "games": len(game_ids),
        "team_boxscore_covered_games": team_covered,
        "team_boxscore_coverage_rate": ratio(team_covered, len(game_ids)),
        "team_boxscore_score_match_rate": ratio(team_score_matched, team_covered),
        "player_boxscore_candidate_covered_games": player_covered,
        "player_boxscore_candidate_coverage_rate": ratio(player_covered, len(game_ids)),
        "pbp_covered_games": pbp_covered,
        "pbp_game_coverage_rate": ratio(pbp_covered, len(game_ids)),
        "duplicate_game_id_groups": games_report["duplicate_game_id_groups"],
    }
    gates = {
        "minimum_games": observed["games"] >= thresholds["minimum_games"],
        "duplicate_game_id_groups": observed["duplicate_game_id_groups"] <= thresholds["duplicate_game_id_groups_maximum"],
        "team_boxscore_coverage": (observed["team_boxscore_coverage_rate"] or 0) >= thresholds["team_coverage_minimum"],
        "team_boxscore_score_match": (observed["team_boxscore_score_match_rate"] or 0) >= thresholds["team_score_match_minimum"],
        "player_boxscore_candidate_coverage": (observed["player_boxscore_candidate_coverage_rate"] or 0) >= thresholds["player_candidate_coverage_minimum"],
        "pbp_game_coverage": (observed["pbp_game_coverage_rate"] or 0) >= thresholds["pbp_coverage_minimum"],
    }
    all_gates = all(gates.values())
    return {
        "schema_version": "eoin-full-adapter-one-time-execution-report-v1",
        "generated_at": utc_now(),
        "formal_state": SELF_TEST_PASS if fixture_mode and all_gates else (EXECUTION_PASS if all_gates else EXECUTION_RESEARCH_BLOCKED),
        "request_id": REQUEST_ID,
        "source_id": "kaggle_eoinamoore_historical_nba",
        "pilot_season": "2023-24",
        "fixture_mode": fixture_mode,
        "approval_validation": approval_validation,
        "thresholds": thresholds,
        "gate_results": gates,
        "all_research_gates_passed": all_gates,
        "aggregate": observed,
        "inputs": {
            "games": games_report,
            "team_statistics": team_report,
            "player_statistics": player_report,
            "play_by_play": pbp_report,
        },
        "boundaries": {
            "temporary_raw_eoin_rows_read": not fixture_mode,
            "synthetic_fixture_rows_read": fixture_mode,
            "raw_rows_emitted": 0,
            "raw_files_emitted": False,
            "raw_files_uploaded_as_artifact": False,
            "historical_silver_replacement": False,
            "historical_gold_replacement": False,
            "player_stat_parity_claim": False,
            "model_training_or_retraining": False,
            "market_backtest": False,
            "betting_edge_claim": False,
            "formal_stake": 0,
        },
    }


def execute_dataset_root(
    root: Path,
    approval_validation: dict[str, Any],
    manifest: dict[str, Any],
    fixture_mode: bool,
) -> dict[str, Any]:
    paths = {name: find_single_file(root, name) for name in EXPECTED_FILES}
    inventory = inspect_inputs(paths, manifest["operational_limits"])
    if not inventory["all_checks_passed"]:
        raise ExecutionBlocked("input inventory failed the frozen operational limits")
    report = build_aggregate_report(paths, approval_validation, fixture_mode=fixture_mode)
    report["inventory"] = inventory
    return report


def self_test(
    request: dict[str, Any], approval: dict[str, Any], manifest: dict[str, Any], policy: dict[str, Any]
) -> dict[str, Any]:
    validation = validate_approval(request, approval, manifest, policy, REQUEST_ID, "workflow_dispatch", "refs/heads/main")
    if validation["formal_state"] != APPROVAL_READY:
        raise AssertionError(validation)

    mutated = copy.deepcopy(approval)
    mutated["approval_state"] = "AWAITING_APPROVAL"
    assert validate_approval(request, mutated, manifest, policy, REQUEST_ID, "workflow_dispatch", "refs/heads/main")["formal_state"] == APPROVAL_BLOCKED
    mutated = copy.deepcopy(approval)
    mutated["execution_authorization"]["maximum_execution_count"] = 2
    assert validate_approval(request, mutated, manifest, policy, REQUEST_ID, "workflow_dispatch", "refs/heads/main")["formal_state"] == APPROVAL_BLOCKED
    assert validate_approval(request, approval, manifest, policy, "WRONG", "workflow_dispatch", "refs/heads/main")["formal_state"] == APPROVAL_BLOCKED

    with tempfile.TemporaryDirectory(prefix="nbavl-eoin-approved-execution-self-test-") as temp_name:
        fixture = Path(temp_name)
        adapter.write_fixture(fixture, include_parquet=True)
        report = execute_dataset_root(fixture, validation, manifest, fixture_mode=True)
    assert report["formal_state"] == SELF_TEST_PASS, report
    assert report["boundaries"]["raw_rows_emitted"] == 0, report
    assert report["boundaries"]["formal_stake"] == 0, report
    return report


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, default=Path("data/eoin-full-adapter-one-time-execution-request-v1.json"))
    parser.add_argument("--approval", type=Path, default=Path("data/eoin-full-adapter-one-time-execution-approval-v1.json"))
    parser.add_argument("--manifest", type=Path, default=Path("data/eoin-full-adapter-runner-implementation-v1.json"))
    parser.add_argument("--execution-policy", type=Path, default=Path("data/eoin-full-adapter-execution-policy-v1.json"))
    parser.add_argument("--confirmation-request-id", default="")
    parser.add_argument("--workflow-event", default=os.environ.get("GITHUB_EVENT_NAME", ""))
    parser.add_argument("--workflow-ref", default=os.environ.get("GITHUB_REF", ""))
    parser.add_argument("--dataset-handle", default="eoinamoore/historical-nba-data-and-player-box-scores")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    request = read_json(args.request)
    approval = read_json(args.approval)
    manifest = read_json(args.manifest)
    policy = read_json(args.execution_policy)

    confirmation = args.confirmation_request_id or (REQUEST_ID if args.self_test else "")
    event = args.workflow_event or ("workflow_dispatch" if args.self_test else "")
    ref = args.workflow_ref or ("refs/heads/main" if args.self_test else "")
    validation = validate_approval(request, approval, manifest, policy, confirmation, event, ref)

    if args.validate_only:
        write_report(args.output, validation)
        print(json.dumps(validation, ensure_ascii=False, indent=2))
        return 0 if validation["formal_state"] == APPROVAL_READY else 1

    if args.self_test:
        report = self_test(request, approval, manifest, policy)
        write_report(args.output, report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    if validation["formal_state"] != APPROVAL_READY:
        blocked = {
            "schema_version": "eoin-full-adapter-one-time-execution-report-v1",
            "formal_state": "ONE_TIME_FULL_ADAPTER_EXECUTION_BLOCKED_BEFORE_NETWORK_ACCESS",
            "request_id": REQUEST_ID,
            "approval_validation": validation,
            "boundaries": {
                "network_download_performed": False,
                "raw_eoin_rows_read": False,
                "raw_rows_emitted": 0,
                "raw_files_emitted": False,
                "formal_stake": 0,
            },
        }
        write_report(args.output, blocked)
        print(json.dumps(blocked, ensure_ascii=False, indent=2))
        return 2

    with tempfile.TemporaryDirectory(prefix="nbavl-eoin-approved-one-time-") as temp_name:
        temp = Path(temp_name)
        dataset_root = kaggle_source.download_dataset(args.dataset_handle, temp / "download")
        report = execute_dataset_root(dataset_root, validation, manifest, fixture_mode=False)
        report["execution_receipt"] = {
            "workflow_event": args.workflow_event,
            "workflow_ref": args.workflow_ref,
            "github_run_id": os.environ.get("GITHUB_RUN_ID"),
            "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
            "github_sha": os.environ.get("GITHUB_SHA"),
            "execution_count_for_request": 1,
            "network_download_performed": True,
            "temporary_raw_material_only": True,
        }
    report["execution_receipt"]["temporary_raw_material_deleted_with_runner"] = True
    write_report(args.output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
