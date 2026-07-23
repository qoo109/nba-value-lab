#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

REQUEST_ID = "HISTORICAL-GOLD-5826-FREEZE-MANIFEST-REAL-ARTIFACT-EXECUTION-2026-07-23-001"
FORMAL_OUTCOME = "HISTORICAL_GOLD_5826_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_PASS_CONSUMED"
EXECUTION_RUN_ID = 30000293169
EXECUTION_JOB_ID = 89183633328
EXECUTED_HEAD = "5eb4bd9c11740ed0f68b5b3806ede24335796c6f"
SOURCE_ARTIFACT_ID = 8551587005
SOURCE_ARTIFACT_DIGEST = "sha256:3ed2d28da3af58b8b72d805860a144541ac5f38106653cfbda593e16bbaa8e8d"
OUTPUT_ARTIFACT_ID = 8560678596
OUTPUT_ARTIFACT_DIGEST = "sha256:a6bfa2afbd2aef32f7e3f87078caaf620d94c744cf1eec74760d20ae4d0d5531"
MANIFEST_SHA256 = "sha256:dcd9522e7ee55669d5b4fd413e424aa01ac9182a1330d51c6f9bf6b13ad8059d"
RECEIPT_SHA256 = "sha256:a0b6ceba02d5cd7d4987dc293f1c41e3dd78d53f583ea5ab1474c469e17bd134"
CORPUS_SEMANTIC_SHA256 = "sha256:c0c48fe17d843714209c822422b9675eadbff8b6be048782a599b2085bc20cbd"
EXECUTOR = Path(".github/workflows/run-approved-historical-gold-5826-freeze-manifest-real-artifact-execution-once-v1.yml")

PROHIBITED_KEYS = {
    "game_id", "game_date", "home_team_abbr", "away_team_abbr", "team_code",
    "feature_id", "matchup_feature_id", "raw_row", "sample_row",
    "row_level_hash", "individual_feature_value", "player_information",
    "market_price",
}


def load(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha256(path: str) -> str:
    return "sha256:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()


def unsafe(value: Any) -> bool:
    if isinstance(value, dict):
        return any(str(key) in PROHIBITED_KEYS or unsafe(child) for key, child in value.items())
    if isinstance(value, list):
        return any(unsafe(child) for child in value)
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    manifest_path = "data/research/historical-gold-5826-complete-corpus-freeze-manifest-v1.json"
    receipt_path = "data/research/historical-gold-5826-freeze-manifest-real-artifact-execution-receipt-v1.json"
    result_path = "data/research/historical-gold-5826-freeze-manifest-real-artifact-execution-result-v1.json"
    status_path = "data/research/historical-gold-5826-freeze-manifest-real-artifact-execution-current-status-v2.json"
    approval_path = "data/research/historical-gold-5826-freeze-manifest-real-artifact-execution-approval-v1.json"

    manifest = load(manifest_path)
    receipt = load(receipt_path)
    result = load(result_path)
    status = load(status_path)
    approval = load(approval_path)

    assert sha256(manifest_path) == MANIFEST_SHA256
    assert sha256(receipt_path) == RECEIPT_SHA256

    assert approval["approval_state"] == "EXPLICIT_USER_APPROVAL_GRANTED"
    assert approval["approved_by"] == "qoo109"
    assert approval["request_id"] == REQUEST_ID
    assert approval["formal_stake"] == 0

    assert receipt["formal_outcome"] == FORMAL_OUTCOME
    assert receipt["request_id"] == REQUEST_ID
    assert receipt["workflow_run_id"] == EXECUTION_RUN_ID
    assert receipt["workflow_run_attempt"] == 1
    assert receipt["github_sha"] == EXECUTED_HEAD
    assert receipt["source_artifact_id"] == SOURCE_ARTIFACT_ID
    assert receipt["source_artifact_archive_digest"] == SOURCE_ARTIFACT_DIGEST
    assert receipt["execution_count_for_request"] == 1
    assert receipt["maximum_execution_count_for_request"] == 1
    assert receipt["request_consumed"] is True
    assert receipt["repeat_execution_allowed"] is False
    assert receipt["database_modified"] is False
    assert receipt["gold_sqlite_read_only"] is True
    assert receipt["real_artifact_read"] is True
    assert receipt["raw_rows_emitted"] == 0
    assert receipt["manifest_sha256"] == MANIFEST_SHA256
    assert receipt["formal_stake"] == 0

    assert manifest["formal_state"] == "HISTORICAL_GOLD_SEMANTIC_CORPUS_MANIFEST_VALID"
    assert manifest["corpus_semantic_sha256"] == CORPUS_SEMANTIC_SHA256
    assert manifest["source_binding"]["source_artifact_id"] == SOURCE_ARTIFACT_ID
    assert manifest["source_binding"]["source_artifact_digest"] == SOURCE_ARTIFACT_DIGEST
    assert manifest["tables"]["gold_matchup_features"]["row_count"] == 5826
    assert manifest["tables"]["gold_team_game_features"]["row_count"] == 11652
    assert manifest["season_labels"] == ["2019-20", "2020-21", "2021-22", "2022-23", "2023-24"]
    assert manifest["aggregate_validation"]["database_integrity_check_passed"] is True
    assert manifest["aggregate_validation"]["database_query_only"] is True
    assert manifest["aggregate_validation"]["database_sha256_unchanged"] is True
    assert manifest["aggregate_validation"]["schema_exact"] is True
    assert manifest["aggregate_validation"]["row_counts_exact"] is True
    assert manifest["aggregate_validation"]["season_set_exact"] is True
    assert manifest["point_in_time_validation"]["violations"] == 0
    assert manifest["duplicate_validation"]["duplicate_matchup_game_keys"] == 0
    assert manifest["duplicate_validation"]["duplicate_team_game_keys"] == 0
    assert manifest["duplicate_validation"]["two_team_rows_per_matchup"] is True
    assert manifest["duplicate_validation"]["team_matchup_alignment"] is True
    assert manifest["privacy_boundaries"]["aggregate_only"] is True
    assert manifest["scientific_boundaries"]["market_backtest_executed"] is False
    assert manifest["scientific_boundaries"]["model_training_or_retraining_executed"] is False
    assert manifest["scientific_boundaries"]["injury_candidate_activated"] is False
    assert manifest["scientific_boundaries"]["betting_edge_claim"] is False
    assert manifest["formal_stake"] == 0
    assert not unsafe(manifest)
    assert not unsafe(receipt)

    assert result["formal_state"] == FORMAL_OUTCOME
    assert result["execution"]["workflow_run_id"] == EXECUTION_RUN_ID
    assert result["execution"]["job_id"] == EXECUTION_JOB_ID
    assert result["execution"]["execution_count"] == 1
    assert result["execution"]["request_consumed"] is True
    assert result["execution"]["executor_retired_after_consumption"] is True
    assert result["output_artifact"]["artifact_id"] == OUTPUT_ARTIFACT_ID
    assert result["output_artifact"]["artifact_digest"] == OUTPUT_ARTIFACT_DIGEST
    assert result["semantic_freeze"]["manifest_sha256"] == MANIFEST_SHA256
    assert result["semantic_freeze"]["corpus_semantic_sha256"] == CORPUS_SEMANTIC_SHA256
    assert result["ready_for_market_backtest"] is False
    assert result["ready_for_model_retraining"] is False
    assert result["formal_stake"] == 0

    assert status["formal_state"] == FORMAL_OUTCOME
    control = status["execution_control"]
    assert control["execution_count"] == 1
    assert control["maximum_execution_count"] == 1
    assert control["request_consumed"] is True
    assert control["repeat_execution_allowed"] is False
    assert control["workflow_rerun_allowed"] is False
    assert control["execution_enabled"] is False
    assert control["executor_workflow_retired"] is True
    assert control["semantic_manifest_created"] is True
    assert control["corpus_frozen_by_semantic_manifest"] is True
    assert status["ready_for_market_backtest"] is False
    assert status["ready_for_model_retraining"] is False
    assert status["formal_stake"] == 0

    assert not EXECUTOR.exists(), "consumed one-time executor must be retired"

    qa = {
        "schema_version": "historical-gold-5826-freeze-manifest-real-artifact-execution-result-qa-v1",
        "formal_state": FORMAL_OUTCOME,
        "request_id": REQUEST_ID,
        "workflow_run_id": EXECUTION_RUN_ID,
        "job_id": EXECUTION_JOB_ID,
        "source_artifact_id": SOURCE_ARTIFACT_ID,
        "output_artifact_id": OUTPUT_ARTIFACT_ID,
        "output_artifact_digest": OUTPUT_ARTIFACT_DIGEST,
        "manifest_sha256": MANIFEST_SHA256,
        "execution_receipt_sha256": RECEIPT_SHA256,
        "corpus_semantic_sha256": CORPUS_SEMANTIC_SHA256,
        "gold_matchup_rows": 5826,
        "gold_team_game_rows": 11652,
        "execution_count": 1,
        "maximum_execution_count": 1,
        "request_consumed": True,
        "executor_retired": True,
        "market_backtest_executed": False,
        "model_retraining_executed": False,
        "formal_stake": 0,
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
