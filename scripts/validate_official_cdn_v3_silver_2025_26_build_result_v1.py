#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "data" / "research" / "official-cdn-v3-silver-2025-26-build-result-v1.json"
EXCEPTIONS = ROOT / "data" / "research" / "official-cdn-v3-terminal-score-exceptions-2025-26-v1.json"
DOC = ROOT / "docs" / "official-cdn-v3-silver-2025-26-build-result-v1.md"
HANDOFF = ROOT / "docs" / "handoffs" / "nba_value_lab_handoff_2026-07-24_official_cdn_v3_silver_2025_26.md"


def main() -> int:
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    exceptions = json.loads(EXCEPTIONS.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")
    handoff = HANDOFF.read_text(encoding="utf-8")
    tests = 0

    def check(condition: bool, label: str) -> None:
        nonlocal tests
        assert condition, label
        tests += 1

    check(record["formal_state"] == "OFFICIAL_CDN_V3_SILVER_2025_26_BUILD_PASS_RECORDED", "state")
    evidence = record["execution_evidence"]
    check(evidence["branch_head"] == "85477bb0f39188f48360fbc51d52ac58b423d190", "head")
    check(evidence["workflow_run"] == 30080247460, "run")
    check(evidence["job"] == 89439929496, "job")
    check(evidence["artifact_id"] == 8591518327, "artifact")
    check(evidence["artifact_digest"] == "sha256:880a3e9688a0035a7c6c8a5e934f32f6011ba44417ae5659c21b9d65fe00db6a", "artifact digest")
    check(evidence["artifact_inspected"] is True, "inspected")
    check(evidence["build_report_sha256"] == "sha256:9de72ae0ffc4056b405a9c8caf569cfb2eed2596390055c8542d6fc92ad52911", "report digest")
    check(evidence["silver_database_gzip_sha256"] == "sha256:f0027956f6d0a1061955f2b00572d3295a8cfc4ef00de431290c38c80847a59a", "db digest")
    check(evidence["silver_database_gzip_bytes"] == 84333787, "db bytes")
    check(evidence["sqlite_integrity_check"] == "ok", "integrity")

    outputs = record["outputs"]
    check(outputs["games"] == 1230, "games")
    check(outputs["pbp_events"] == 621887, "events")
    check(outputs["player_aliases"] == 1006, "aliases")
    check(outputs["possessions"] == 249957, "possessions")
    check(outputs["team_game_features"] == 2460, "features")
    check(outputs["games_with_two_team_features"] == 1230, "two features")
    check(outputs["games_with_official_terminal_score"] == 1230, "scores")
    check(outputs["game_date_min"] == "2025-10-21", "min date")
    check(outputs["game_date_max"] == "2026-04-12", "max date")
    check(outputs["game_date_rule"] == "earliest_timeActual_UTC_converted_to_America_New_York_date", "date rule")

    quality = record["quality"]
    check(quality["all_three_source_game_count"] == 1230, "source count")
    check(quality["all_three_source_game_ids_match"] is True, "source IDs")
    check(quality["team_identity_cross_source_mismatches"] == 0, "team mismatches")
    check(quality["unexplained_terminal_score_cross_source_mismatches"] == 0, "unexplained scores")
    check(quality["documented_v3_terminal_score_exceptions"] == 2, "documented scores")
    check(quality["documented_v3_terminal_score_exception_ids"] == ["0022500029", "0022500232"], "exception IDs")
    check(quality["terminal_score_exception_manifest"] == "data/research/official-cdn-v3-terminal-score-exceptions-2025-26-v1.json", "manifest")
    check(quality["v3_event_rows_modified"] is False, "raw V3 preserved")
    check(quality["official_game_scores_modified"] is False, "official scores preserved")
    check(quality["duplicate_team_feature_keys"] == 0, "duplicates")
    check(quality["core_feature_null_or_nonfinite_rows"] == 0, "finite features")
    check(quality["minimum_possession_segments_per_game"] >= 150, "min possessions")
    check(quality["maximum_possession_segments_per_game"] <= 300, "max possessions")

    check(exceptions["formal_state"] == "TWO_DOCUMENTED_V3_TERMINAL_SCORE_EXCEPTIONS_VALIDATED", "exception state")
    check(exceptions["exception_count"] == 2, "exception count")
    check([row["game_id"] for row in exceptions["exceptions"]] == ["0022500029", "0022500232"], "manifest IDs")
    check(exceptions["boundaries"]["wildcard_exceptions_allowed"] is False, "no wildcard")
    check(exceptions["boundaries"]["v3_event_rows_modified"] is False, "manifest V3 lock")
    check(exceptions["boundaries"]["official_game_scores_modified"] is False, "manifest score lock")
    check(exceptions["boundaries"]["unexplained_terminal_score_mismatch_allowed"] is False, "fail closed")

    locks = record["execution_boundaries"]
    for key in (
        "raw_source_archives_committed", "model_retraining_executed",
        "model_scoring_executed", "odds_join_executed", "market_backtest_allowed",
        "clv_allowed", "roi_allowed", "betting_edge_claim_allowed",
    ):
        check(locks[key] is False, key)
    check(locks["raw_source_rows_emitted"] == 0, "raw rows")
    check(locks["provider_api_requests"] == 0, "provider requests")
    check(locks["formal_stake"] == 0, "stake")
    check(record["decision"] == "READY_TO_BUILD_CONTINUOUS_2024_25_TO_2025_26_GOLD_AND_SCORE_FROZEN_MODEL", "decision")
    check(record["next_unique_sub_mainline"] == "BUILD_CONTINUOUS_2024_25_TO_2025_26_GOLD_AND_SCORE_FROZEN_MODEL", "next")
    check("courtside statistics system froze" in doc, "glitch documented")
    check("Do not retrain" in handoff, "handoff retraining lock")

    qa = {
        "schema_version": 1,
        "formal_state": "OFFICIAL_CDN_V3_SILVER_2025_26_BUILD_RESULT_VALID",
        "real_artifact_bound": True,
        "sqlite_integrity_ok": True,
        "games": 1230,
        "team_game_features": 2460,
        "documented_v3_terminal_score_exceptions": 2,
        "unexplained_terminal_score_mismatches": 0,
        "model_retraining_executed": False,
        "model_scoring_executed": False,
        "market_backtest_unlocked": False,
        "contract_tests": tests,
        "formal_stake": 0,
    }
    path = ROOT / "artifacts" / "official-cdn-v3-silver-2025-26-build-result-validation-v1.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
