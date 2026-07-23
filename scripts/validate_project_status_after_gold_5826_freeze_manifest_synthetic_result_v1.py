#!/usr/bin/env python3
"""Validate PROJECT_STATUS after Gold 5,826 freeze-manifest synthetic result."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

NEXT = "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_REQUEST_READY_FOR_DESIGN"
STATUS_STATE = "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_IMPLEMENTATION_SYNTHETIC_VALIDATED_READY_FOR_REAL_ARTIFACT_EXECUTION_REQUEST_DESIGN"

REQUIRED_CURRENT = (
    "reference coverage: 5,826 / 5,826",
    "source gap exception remaining count: 0",
    "raw Historical Gold matchups: 5,826",
    "freeze manifest implementation module created: true",
    "freeze manifest synthetic validation: PASS / 20 OF 20",
    "freeze manifest synthetic implementation recording PR: 139",
    "freeze manifest synthetic implementation recording merge: b561c941b5fc27a0bda3fa790244ff92c35b5c0b",
    "freeze manifest synthetic validation run: 29984329419",
    "freeze manifest synthetic validation job: 89132779309",
    "freeze manifest synthetic validation artifact: 8554394051",
    "freeze manifest synthetic validation digest: sha256:1ecf4862ff87c3eb23ccb8d6b1c9860a229b54b8c76c469930dd2723da213f6f",
    "real Artifact execution request design created: false",
    "real Artifact execution request created: false",
    "real Artifact freeze workflow created: false",
    "real Artifact execution approved: false",
    "real Artifact execution count: 0",
    "semantic freeze manifest created: false",
    "corpus freeze executed: false",
    NEXT,
)

REQUIRED_EVIDENCE = (
    "### Historical Gold 5,826 freeze-manifest synthetic implementation validation",
    "formal state: HISTORICAL_GOLD_5826_FREEZE_MANIFEST_IMPLEMENTATION_SYNTHETIC_VALID",
    "synthetic SQLite tests: 20 / 20 PASS",
    "Gold matchups / team rows: 5,826 / 11,652",
    "remaining source exceptions: 0",
    "point-in-time violations: 0",
    "real Artifact downloaded: false",
    "real Artifact read: false",
    "real execution workflow created: false",
    "real execution approved: false",
    "real execution count: 0",
    "semantic manifest created: false",
    "corpus frozen: false",
    "workflow run: 29984329419",
    "job: 89132779309 / validate-synthetic-implementation / success",
    "Artifact: 8554394051",
    "Artifact digest: sha256:1ecf4862ff87c3eb23ccb8d6b1c9860a229b54b8c76c469930dd2723da213f6f",
)

BLOCKED = (
    "it may not create the request, approval, execution workflow",
    "download Artifact `8551587005`",
    "read the real Gold database",
    "create the canonical manifest",
    "freeze the corpus",
    "Market backtesting",
    "injury-model activation",
    "model retraining",
    "betting-edge claims",
    "Stake above `0`",
)


def validate(text: str, status: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    current, marker, evidence = text.partition("## Completed Evidence")
    checks: dict[str, bool] = {}
    for index, fragment in enumerate(REQUIRED_CURRENT):
        checks[f"current_{index}"] = current.count(fragment) == 1
    for index, fragment in enumerate(REQUIRED_EVIDENCE):
        checks[f"evidence_{index}"] = fragment in evidence
    for index, fragment in enumerate(BLOCKED):
        checks[f"blocked_{index}"] = fragment in current
    state = status.get("implementation_state", {})
    checks.update({
        "evidence_marker": bool(marker),
        "header_stake_zero": "正式 Stake：**0**" in text,
        "research_position": "研究定位：**Research Candidate / Pre-Market-Backtest**" in text,
        "stale_next_absent": "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_IMPLEMENTATION_READY_FOR_SYNTHETIC_VALIDATION" not in current,
        "status_state": status.get("formal_state") == STATUS_STATE,
        "status_module": state.get("implementation_module_created") is True,
        "status_synthetic_executed": state.get("synthetic_sqlite_tests_executed") is True,
        "status_synthetic_passed": state.get("synthetic_sqlite_tests_passed") is True,
        "status_tests": (state.get("synthetic_tests_total"), state.get("synthetic_tests_passed"), state.get("synthetic_tests_failed")) == (20, 20, 0),
        "status_request_design_absent": state.get("real_artifact_execution_request_design_created") is False,
        "status_request_absent": state.get("real_artifact_execution_request_created") is False,
        "status_workflow_absent": state.get("real_artifact_execution_workflow_created") is False,
        "status_approval_absent": state.get("real_artifact_execution_approved") is False,
        "status_execution_zero": state.get("real_artifact_execution_count") == 0,
        "status_manifest_absent": state.get("semantic_manifest_created") is False,
        "status_not_frozen": state.get("corpus_frozen") is False,
        "status_ready_design": status.get("ready_for_real_artifact_execution_request_design") is True,
        "status_not_ready_execution": status.get("ready_for_real_artifact_execution") is False,
        "status_not_ready_market": status.get("ready_for_market_backtest") is False,
        "status_not_ready_retrain": status.get("ready_for_model_retraining") is False,
        "status_stake": status.get("formal_stake") == 0,
        "result_state": result.get("formal_state") == "HISTORICAL_GOLD_5826_FREEZE_MANIFEST_IMPLEMENTATION_SYNTHETIC_VALID",
        "result_tests": (
            result.get("synthetic_validation", {}).get("tests_total"),
            result.get("synthetic_validation", {}).get("tests_passed"),
            result.get("synthetic_validation", {}).get("tests_failed"),
        ) == (20, 20, 0),
        "result_real_read_false": result.get("real_artifact_boundary", {}).get("real_artifact_read") is False,
        "result_ready_design": result.get("ready_for_real_artifact_execution_request_design") is True,
        "result_not_ready_execution": result.get("ready_for_real_artifact_execution") is False,
        "result_stake": result.get("formal_stake") == 0,
    })
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": "project-status-after-gold-5826-freeze-manifest-synthetic-result-validation-report-v1",
        "validated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "formal_state": "PROJECT_STATUS_GOLD_5826_FREEZE_MANIFEST_SYNTHETIC_RESULT_SYNC_VALID" if not failed else "PROJECT_STATUS_GOLD_5826_FREEZE_MANIFEST_SYNTHETIC_RESULT_SYNC_INVALID",
        "checks": checks,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "checks_failed": len(failed),
        "failed_checks": failed,
        "gold_matchups": 5826 if not failed else None,
        "remaining_exceptions": 0 if not failed else None,
        "synthetic_tests_passed": 20 if not failed else None,
        "request_design_created": False,
        "real_artifact_execution_approved": False,
        "corpus_freeze_executed": False,
        "ready_for_real_artifact_execution_request_design": not failed,
        "ready_for_real_artifact_execution": False,
        "ready_for_market_backtest": False,
        "ready_for_model_retraining": False,
        "formal_stake": 0,
    }


def self_test(text: str, status: dict[str, Any], result: dict[str, Any]) -> dict[str, bool]:
    baseline = validate(text, status, result)
    assert baseline["checks_failed"] == 0, baseline
    cases = {
        "wrong_next_blocks": text.replace(NEXT, "WRONG_NEXT", 1),
        "tests_fail_blocks": text.replace("freeze manifest synthetic validation: PASS / 20 OF 20", "freeze manifest synthetic validation: FAIL", 1),
        "request_design_created_blocks": text.replace("real Artifact execution request design created: false", "real Artifact execution request design created: true", 1),
        "approval_blocks": text.replace("real Artifact execution approved: false", "real Artifact execution approved: true", 1),
        "execution_blocks": text.replace("real Artifact execution count: 0", "real Artifact execution count: 1", 1),
        "manifest_blocks": text.replace("semantic freeze manifest created: false", "semantic freeze manifest created: true", 1),
        "nonzero_stake_blocks": text.replace("正式 Stake：**0**", "正式 Stake：**1**", 1),
    }
    output: dict[str, bool] = {"baseline_passes": True}
    for name, mutated in cases.items():
        output[name] = validate(mutated, status, result)["checks_failed"] > 0
        assert output[name], name
    bad_status = json.loads(json.dumps(status))
    bad_status["implementation_state"]["real_artifact_execution_request_created"] = True
    output["bad_status_blocks"] = validate(text, bad_status, result)["checks_failed"] > 0
    assert output["bad_status_blocks"]
    bad_result = json.loads(json.dumps(result))
    bad_result["synthetic_validation"]["tests_failed"] = 1
    output["bad_result_blocks"] = validate(text, status, bad_result)["checks_failed"] > 0
    assert output["bad_result_blocks"]
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", required=True, type=Path)
    parser.add_argument("--implementation-status", required=True, type=Path)
    parser.add_argument("--synthetic-result", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    text = args.status.read_text(encoding="utf-8")
    status = json.loads(args.implementation_status.read_text(encoding="utf-8"))
    result = json.loads(args.synthetic_result.read_text(encoding="utf-8"))
    report = validate(text, status, result)
    if args.self_test:
        report["self_test"] = self_test(text, status, result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["checks_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
