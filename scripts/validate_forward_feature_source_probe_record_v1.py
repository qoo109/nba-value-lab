#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "data" / "research" / "forward-feature-source-probe-2024-25-2025-26-v1.json"
DOC = ROOT / "docs" / "forward-feature-source-probe-2024-25-2025-26-v1.md"
HANDOFF = ROOT / "docs" / "handoffs" / "nba_value_lab_handoff_2026-07-24_forward_feature_source_probe.md"


def main() -> int:
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")
    handoff = HANDOFF.read_text(encoding="utf-8")
    tests = 0

    def check(condition: bool, message: str) -> None:
        nonlocal tests
        assert condition, message
        tests += 1

    check(record["formal_state"] == "FORWARD_FEATURE_SOURCES_FOUND_2024_25_SILVER_VALID_2025_26_ADAPTER_READY", "formal state")
    evidence = record["execution_evidence"]
    check(evidence["workflow_run"] == 30078039872, "run binding")
    check(evidence["job"] == 89433051409, "job binding")
    check(evidence["artifact_id"] == 8590667307, "artifact binding")
    check(evidence["artifact_digest"] == "sha256:1d3a271b148e2abd5f2d5ed0ef75ed2a6107363a3985cd05ad2d475e61eaa4ed", "digest binding")
    check(evidence["branch_head"] == "849cd83d83d3e955414e806e4771ab2c2019bf59", "branch-head binding")
    check(evidence["artifact_inspected"] is True, "artifact inspected")

    season24 = record["season_2024_25"]
    check(season24["status"] == "GOVERNED_SILVER_READY_FOR_PRIVATE_FORWARD_FEATURE_PIPELINE", "2024-25 state")
    check(season24["tables"]["games"] == 1230, "2024-25 games")
    check(season24["tables"]["team_game_features"] == 2460, "2024-25 feature rows")
    check(season24["tables"]["pbp_events"] == 574358, "2024-25 event rows")
    check(season24["tables"]["possessions"] == 243782, "2024-25 possessions")
    check(season24["quality"]["team_inference_pass"] is True, "team inference")
    check(season24["quality"]["official_score_coverage_rate"] == 1.0, "score coverage")
    check(season24["quality"]["incomplete_team_games"] == 0, "complete features")
    check(season24["quality"]["reconstruction_mismatched_games"] == 201, "honest reconstruction mismatch record")
    check(season24["quality"]["rating_points_source"] == "nbastats_official_final_score", "official rating points")
    check(season24["quality"]["possession_points_usage"] == "qa_only", "possession points boundary")
    check(season24["derived_artifact"]["public_commit_allowed"] is False, "Silver public commit blocked")

    season25 = record["season_2025_26"]
    check(season25["status"] == "OFFICIAL_CDN_V3_ADAPTER_IMPLEMENTATION_READY", "2025-26 state")
    check(season25["all_three_game_id_intersection"] == 1230, "all-source game overlap")
    check(season25["game_id_union"] == 1230, "source game union")
    for key in ("cdnnba_2025", "nbastatsv3_2025", "matchups_2025"):
        check(season25["sources"][key]["unique_game_ids"] == 1230, f"{key} coverage")
    check(season25["sources"]["cdnnba_2025"]["cdn_required_columns_present"] is True, "CDN adapter schema")
    check(season25["sources"]["cdnnba_2025"]["games_with_terminal_score_candidate"] == 1230, "CDN terminal scores")
    check(season25["sources"]["nbastatsv3_2025"]["v3_core_columns_present"] is True, "V3 core schema")
    check(season25["sources"]["nbastatsv3_2025"]["games_with_terminal_score_candidate"] == 1230, "V3 terminal scores")

    locks = record["execution_boundaries"]
    check(locks["provider_api_requests"] == 0, "provider requests")
    check(locks["raw_archives_committed"] is False, "raw archive boundary")
    check(locks["raw_rows_emitted"] == 0, "raw row boundary")
    check(locks["model_retraining_executed"] is False, "retraining lock")
    check(locks["model_scoring_executed"] is False, "scoring lock")
    check(locks["odds_join_executed"] is False, "odds join lock")
    check(locks["market_backtest_allowed"] is False, "market backtest lock")
    check(locks["clv_allowed"] is False, "CLV lock")
    check(locks["roi_allowed"] is False, "ROI lock")
    check(locks["betting_edge_claim_allowed"] is False, "edge claim lock")
    check(locks["formal_stake"] == 0, "stake lock")

    check(record["decision"] == "IMPLEMENT_OFFICIAL_CDN_V3_2025_26_SILVER_ADAPTER_AND_CONTINUOUS_GOLD_STATE", "decision")
    check(record["next_unique_sub_mainline"] == "IMPLEMENT_OFFICIAL_CDN_V3_2025_26_SILVER_ADAPTER_AND_CONTINUOUS_GOLD_STATE", "next sub-mainline")
    check("America/New_York" in doc, "game-date rule documented")
    check("Do not retrain" in handoff, "no-retraining handoff boundary")
    check("Formal Stake: 0" in doc, "doc stake")
    check("Formal Stake: 0" in handoff, "handoff stake")

    qa = {
        "schema_version": 1,
        "formal_state": "FORWARD_FEATURE_SOURCE_PROBE_RECORD_VALID",
        "real_execution_bound": True,
        "season_2024_25_silver_ready": True,
        "season_2025_26_adapter_ready": True,
        "raw_rows_emitted": 0,
        "model_retraining_executed": False,
        "model_scoring_executed": False,
        "market_backtest_unlocked": False,
        "contract_tests": tests,
        "formal_stake": 0,
    }
    output = ROOT / "artifacts" / "forward-feature-source-probe-record-validation-v1.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
