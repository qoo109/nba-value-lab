#!/usr/bin/env python3
"""Validate the successful two-game official CDN PBP recovery record."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

PASS = "HISTORICAL_SILVER_2023_24_TWO_GAME_OFFICIAL_CDN_PBP_RECOVERY_PASS"
ADOPTED = "HISTORICAL_SILVER_2023_24_TWO_GAME_OFFICIAL_CDN_PBP_RECOVERY_PASS_ARTIFACT_ADOPTED"
NEXT = "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_POLICY_READY_FOR_DESIGN"
RESULT_SHA = "sha256:97d292d56f6ee8b6f0a2d4e4471990f7c953cca7c324eb64c129066695df7c30"
SILVER_SHA = "sha256:48c032339402d5f75e43d7aaf8e977784aee9eceff74c9e7da952af8e1680eb8"
GOLD_SHA = "sha256:a4e94fab1681b53817f305d08c196995d406fa0566ab70d6083aa5cebfc52085"
ARTIFACT_DIGEST = "sha256:3ed2d28da3af58b8b72d805860a144541ac5f38106653cfbda593e16bbaa8e8d"
SOURCE_SHA = "sha256:33d49fefc809f73d5d6cbad6d1d6690e0df6c89fe2b5a4d814ecc9ea4df6101b"
FORBIDDEN_KEYS = {
    "game_id", "game_ids", "game_date", "game_dates", "team_abbr", "home_team_abbr",
    "away_team_abbr", "team_code", "team_codes", "source_row", "raw_row", "row_key_hash",
}


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def file_sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def contains_forbidden_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).lower() in FORBIDDEN_KEYS or contains_forbidden_key(child):
                return True
    elif isinstance(value, list):
        return any(contains_forbidden_key(item) for item in value)
    return False


def validate(result: dict[str, Any], status: dict[str, Any], result_sha: str) -> dict[str, Any]:
    checks: dict[str, bool] = {}

    def add(name: str, condition: Any) -> None:
        checks[name] = bool(condition)

    add("result_schema", result.get("schema_version") == "historical-silver-2023-24-two-game-official-cdn-pbp-recovery-result-v2")
    add("result_state", result.get("formal_state") == PASS)
    add("result_version", result.get("recovery_version") == "v2")
    add("result_file_sha", result_sha == RESULT_SHA)
    add("result_privacy", not contains_forbidden_key(result))

    baseline = result.get("baseline_seasons", {})
    add("five_baseline_seasons", sorted(baseline) == ["2019-20", "2020-21", "2021-22", "2022-23", "2023-24"])
    add("baseline_2023_gap", baseline.get("2023-24", {}).get("team_game_features") == 2456)
    add("all_baselines_ready", all(item.get("ready") is True for item in baseline.values()))

    source = result.get("source", {})
    add("source_key", source.get("source_key") == "cdnnba_2023")
    add("source_provider", source.get("provider") == "shufinskiy/nba_data archive of official cdn.nba.com play-by-play")
    add("source_sha", "sha256:" + str(source.get("archive_sha256")) == SOURCE_SHA)
    add("source_bytes", source.get("archive_bytes") == 18598380)
    add("source_not_committed", source.get("raw_archive_committed") is False)

    recovery = result.get("recovery", {})
    expected_recovery = {
        "archive_csv_rows_scanned": 674937,
        "target_games": 2,
        "target_game_count_found": 2,
        "target_event_rows_found": 1108,
        "recovered_games": 2,
        "recovered_game_dates": 2,
        "team_feature_rows_before": 2456,
        "team_feature_rows_after": 2460,
        "team_feature_rows_added": 4,
        "possession_rows_before": 242365,
        "possession_rows_after": 242777,
        "possession_rows_added": 412,
        "remaining_games_without_team_features": 0,
        "remaining_recovered_games_without_dates": 0,
        "duplicate_team_feature_rows": 0,
    }
    for key, expected in expected_recovery.items():
        add(f"recovery_{key}", recovery.get(key) == expected)
    add("no_identifiers_in_report", recovery.get("game_identifiers_emitted_in_report") is False)
    add("no_dates_in_report", recovery.get("game_dates_emitted_in_report") is False)
    diagnostics = recovery.get("per_game_diagnostics", [])
    add("two_diagnostics", isinstance(diagnostics, list) and len(diagnostics) == 2)
    add("all_terminal_scores_match", all(item.get("terminal_score_match") is True for item in diagnostics))
    add("all_features_created", all(item.get("two_team_features_created") is True for item in diagnostics))
    add("plausible_possessions", all(60 <= int(item.get(side, 0)) <= 180 for item in diagnostics for side in ("home_possessions", "away_possessions")))

    outputs = result.get("final_outputs", {})
    add("silver_games", outputs.get("silver_games") == 5826)
    add("silver_features", outputs.get("silver_team_game_features") == 11652)
    add("gold_matchups", outputs.get("gold_matchup_features") == 5826)
    add("gold_features", outputs.get("gold_team_game_features") == 11652)
    add("pit_pass", outputs.get("gold_point_in_time_passed") is True)
    add("pit_zero", outputs.get("gold_point_in_time_violations") == 0)

    decision = result.get("decision", {})
    add("exceptions_resolved", decision.get("two_source_exceptions_resolved") is True)
    add("exceptions_zero", decision.get("documented_exception_count_after_recovery") == 0)
    add("silver_complete", decision.get("historical_silver_complete_for_governed_five_season_scope") is True)
    add("gold_complete", decision.get("historical_gold_complete_for_governed_five_season_scope") is True)
    add("no_market_backtest", decision.get("ready_for_market_backtest") is False)
    add("no_retraining", decision.get("ready_for_model_retraining") is False)
    add("no_edge_claim", decision.get("betting_edge_claim") is False)
    add("result_stake_zero", decision.get("formal_stake") == 0)

    boundaries = result.get("boundaries", {})
    add("official_source_used", boundaries.get("official_alternate_pbp_source_used") is True)
    for key in ("manual_or_synthetic_feature_rows", "market_backtest_executed", "model_retraining_executed", "raw_game_identifiers_emitted_in_aggregate_report", "repository_database_modified", "source_archives_committed"):
        add(f"result_boundary_{key}", boundaries.get(key) is False)
    add("result_boundary_stake", boundaries.get("formal_stake") == 0)

    add("status_schema", status.get("schema_version") == "historical-silver-2023-24-two-game-official-cdn-pbp-recovery-current-status-v1")
    add("status_state", status.get("formal_state") == ADOPTED)
    add("status_next", status.get("next_research_step") == NEXT)
    add("status_privacy", not contains_forbidden_key(status))
    exception = status.get("source_exception_state", {})
    add("old_exception_count", exception.get("previous_documented_exception_count") == 2)
    add("remaining_exception_count", exception.get("remaining_documented_exception_count") == 0)
    add("status_resolved", exception.get("two_source_exceptions_resolved") is True)

    evidence = status.get("execution_evidence", {})
    add("run_id", evidence.get("workflow_run_id") == 29976204693)
    add("job_id", evidence.get("job_id") == 89108363564)
    add("job_success", evidence.get("job_conclusion") == "success")
    add("head_sha", evidence.get("head_sha") == "ad12518a55e6077295c4df1a099977a6e5cd024b")
    add("artifact_id", evidence.get("artifact_id") == 8551587005)
    add("artifact_size", evidence.get("artifact_archive_size_bytes") == 374591375)
    add("artifact_digest", evidence.get("artifact_archive_digest") == ARTIFACT_DIGEST)

    files = status.get("artifact_files", {})
    silver = files.get("historical_silver", {})
    gold = files.get("historical_gold", {})
    aggregate = files.get("aggregate_result", {})
    add("silver_file_sha", silver.get("sha256") == SILVER_SHA)
    add("silver_file_size", silver.get("size_bytes") == 369318173)
    add("silver_file_counts", silver.get("games") == 5826 and silver.get("team_game_features") == 11652)
    add("gold_file_sha", gold.get("sha256") == GOLD_SHA)
    add("gold_file_size", gold.get("size_bytes") == 5268851)
    add("gold_file_counts", gold.get("matchup_features") == 5826 and gold.get("team_game_features") == 11652)
    add("gold_file_pit", gold.get("point_in_time_passed") is True and gold.get("point_in_time_violations") == 0)
    add("aggregate_file_sha", aggregate.get("sha256") == RESULT_SHA)
    add("aggregate_file_size", aggregate.get("size_bytes") == 3751)

    adoption = status.get("adoption", {})
    add("canonical_recipe", adoption.get("canonical_rebuild_recipe") is True)
    add("canonical_result", adoption.get("canonical_aggregate_result") is True)
    add("supersedes_5824", adoption.get("old_5824_gold_reference_superseded_for_coverage_counts") is True)
    add("new_5826", adoption.get("new_gold_matchup_reference_count") == 5826)
    add("governed_complete", adoption.get("gold_complete_for_governed_five_season_scope") is True)

    status_boundaries = status.get("boundaries", {})
    for key in ("manual_or_synthetic_feature_rows", "source_archive_committed", "repository_database_modified", "raw_game_identifiers_emitted_in_public_aggregate_record", "raw_game_dates_emitted_in_public_aggregate_record", "market_backtest_executed", "model_retraining_executed", "betting_edge_claim"):
        add(f"status_boundary_{key}", status_boundaries.get(key) is False)
    add("status_stake_zero", status.get("formal_stake") == 0 and status_boundaries.get("formal_stake") == 0)
    add("status_market_blocked", status.get("ready_for_market_backtest") is False)
    add("status_retraining_blocked", status.get("ready_for_model_retraining") is False)

    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": "historical-silver-two-game-official-cdn-recovery-validation-report-v2",
        "validated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "formal_state": "HISTORICAL_SILVER_TWO_GAME_OFFICIAL_CDN_RECOVERY_RESULT_VALID_ADOPTED" if not failed else "HISTORICAL_SILVER_TWO_GAME_OFFICIAL_CDN_RECOVERY_RESULT_INVALID",
        "checks": checks,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "checks_failed": len(failed),
        "failed_checks": failed,
        "result_file_sha256": result_sha,
        "source_exceptions_remaining": 0 if not failed else None,
        "historical_gold_matchups": 5826 if not failed else None,
        "ready_for_complete_corpus_freeze_policy_design": not failed,
        "ready_for_market_backtest": False,
        "formal_stake": 0,
    }


def self_test(result: dict[str, Any], status: dict[str, Any]) -> dict[str, bool]:
    baseline = validate(result, status, RESULT_SHA)
    assert baseline["checks_failed"] == 0, baseline
    tests: dict[str, bool] = {"baseline_passes": True}
    mutations = {
        "wrong_state_blocks": ("result", ("formal_state",), "WRONG"),
        "missing_game_blocks": ("result", ("recovery", "recovered_games"), 1),
        "remaining_exception_blocks": ("result", ("decision", "documented_exception_count_after_recovery"), 1),
        "wrong_gold_count_blocks": ("result", ("final_outputs", "gold_matchup_features"), 5824),
        "pit_violation_blocks": ("result", ("final_outputs", "gold_point_in_time_violations"), 1),
        "synthetic_rows_blocks": ("result", ("boundaries", "manual_or_synthetic_feature_rows"), True),
        "wrong_artifact_digest_blocks": ("status", ("execution_evidence", "artifact_archive_digest"), "sha256:wrong"),
        "wrong_silver_hash_blocks": ("status", ("artifact_files", "historical_silver", "sha256"), "sha256:wrong"),
        "market_ready_blocks": ("status", ("ready_for_market_backtest",), True),
        "nonzero_stake_blocks": ("status", ("formal_stake",), 1),
    }
    for name, (target, path, replacement) in mutations.items():
        mutated_result = copy.deepcopy(result)
        mutated_status = copy.deepcopy(status)
        obj = mutated_result if target == "result" else mutated_status
        cursor = obj
        for key in path[:-1]:
            cursor = cursor[key]
        cursor[path[-1]] = replacement
        report = validate(mutated_result, mutated_status, RESULT_SHA)
        tests[name] = report["checks_failed"] > 0
        assert tests[name], (name, report)
    unsafe = copy.deepcopy(result)
    unsafe["game_id"] = "forbidden"
    tests["public_identifier_blocks"] = validate(unsafe, status, RESULT_SHA)["checks_failed"] > 0
    assert tests["public_identifier_blocks"]
    return tests


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--current-status", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    result = read_json(args.result)
    status = read_json(args.current_status)
    report = validate(result, status, file_sha256(args.result))
    if args.self_test:
        report["self_test"] = self_test(result, status)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["checks_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
