#!/usr/bin/env python3
"""Validate PROJECT_STATUS after Gold 5,826 real-Artifact request-design result."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

NEXT = "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_REQUEST_READY_FOR_DRAFT"
STATUS_STATE = "HISTORICAL_GOLD_5826_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_REQUEST_DESIGN_VALIDATED_READY_FOR_REQUEST_DRAFT"
RESULT_STATE = "HISTORICAL_GOLD_5826_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_REQUEST_DESIGN_VALIDATED"

REQUIRED_CURRENT = (
    "reference coverage: 5,826 / 5,826",
    "source gap exception remaining count: 0",
    "freeze manifest synthetic validation: PASS / 20 OF 20",
    "real Artifact execution request design: VALIDATED / DESIGN ONLY",
    "real Artifact execution request design recording PR: 141",
    "real Artifact execution request design recording merge: 5c6431110b7085dec1663cf6303df5393fd4dd97",
    "real Artifact execution request design validation run: 29986783982",
    "real Artifact execution request design validation job: 89140319716",
    "real Artifact execution request design validation artifact: 8555320565",
    "real Artifact execution request design validation digest: sha256:a4c0dce31c951fc0913bffc084411a9353928468fe1baafc0a412e050283c3e9",
    "real Artifact execution request design validated: true",
    "real Artifact execution request created: false",
    "real Artifact freeze workflow created: false",
    "real Artifact execution approved: false",
    "real Artifact execution count: 0",
    "semantic freeze manifest created: false",
    "corpus freeze executed: false",
    NEXT,
)

REQUIRED_EVIDENCE = (
    "### Historical Gold 5,826 real Artifact execution request design",
    "formal state: HISTORICAL_GOLD_5826_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_REQUEST_DESIGN_VALIDATED",
    "exact Artifact ID: 8551587005",
    "exact Artifact expiry: 2026-08-06T03:14:00Z",
    "maximum execution attempts: 1",
    "manual workflow_dispatch on main only: true",
    "separate explicit user approval required: true",
    "request consumed after any execution attempt: true",
    "rerun allowed: false",
    "automatic dispatch allowed: false",
    "GitHub Artifact transport only: true",
    "Silver database read allowed: false",
    "request draft created: false",
    "approval created: false",
    "execution workflow created: false",
    "real Artifact downloaded: false",
    "real Artifact read: false",
    "semantic manifest created: false",
    "corpus frozen: false",
    "workflow run: 29986783982",
    "job: 89140319716 / validate-request-design / success",
    "Artifact: 8555320565",
    "Artifact digest: sha256:a4c0dce31c951fc0913bffc084411a9353928468fe1baafc0a412e050283c3e9",
)

BLOCKED = (
    "it may not grant approval",
    "create or dispatch the execution workflow",
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

    lifecycle = status.get("request_lifecycle", {})
    checks.update({
        "evidence_marker": bool(marker),
        "header_stake_zero": "正式 Stake：**0**" in text,
        "research_position": "研究定位：**Research Candidate / Pre-Market-Backtest**" in text,
        "stale_design_next_absent": "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_REQUEST_READY_FOR_DESIGN" not in current,
        "status_state": status.get("formal_state") == STATUS_STATE,
        "status_design_created": lifecycle.get("request_design_created") is True,
        "status_design_validated": lifecycle.get("request_design_validated") is True,
        "status_request_absent": lifecycle.get("request_draft_created") is False,
        "status_request_not_validated": lifecycle.get("request_validated") is False,
        "status_approval_absent": lifecycle.get("approval_record_created") is False,
        "status_workflow_absent": lifecycle.get("execution_workflow_created") is False,
        "status_execution_disabled": lifecycle.get("execution_enabled") is False,
        "status_execution_zero": lifecycle.get("execution_count") == 0,
        "status_max_one": lifecycle.get("maximum_execution_count") == 1,
        "status_not_consumed": lifecycle.get("request_consumed") is False,
        "status_no_repeat": lifecycle.get("repeat_execution_allowed") is False,
        "status_no_auto": lifecycle.get("automatic_dispatch_allowed") is False,
        "status_no_download": lifecycle.get("real_artifact_downloaded") is False,
        "status_no_real_read": lifecycle.get("real_artifact_read") is False,
        "status_no_manifest": lifecycle.get("semantic_manifest_created") is False,
        "status_not_frozen": lifecycle.get("corpus_frozen") is False,
        "status_ready_draft": status.get("ready_for_request_draft") is True,
        "status_not_ready_approval": status.get("ready_for_explicit_user_approval") is False,
        "status_not_ready_execution": status.get("ready_for_real_artifact_execution") is False,
        "status_not_ready_freeze": status.get("ready_for_corpus_freeze_claim") is False,
        "status_not_ready_market": status.get("ready_for_market_backtest") is False,
        "status_not_ready_retrain": status.get("ready_for_model_retraining") is False,
        "status_stake": status.get("formal_stake") == 0,
        "result_state": result.get("formal_state") == RESULT_STATE,
        "result_ready_draft": result.get("ready_for_request_draft") is True,
        "result_not_ready_approval": result.get("ready_for_explicit_user_approval") is False,
        "result_not_ready_execution": result.get("ready_for_real_artifact_execution") is False,
        "result_stake": result.get("formal_stake") == 0,
    })
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": "project-status-after-gold-5826-real-artifact-request-design-result-validation-report-v1",
        "validated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "formal_state": "PROJECT_STATUS_GOLD_5826_REAL_ARTIFACT_REQUEST_DESIGN_RESULT_SYNC_VALID" if not failed else "PROJECT_STATUS_GOLD_5826_REAL_ARTIFACT_REQUEST_DESIGN_RESULT_SYNC_INVALID",
        "checks": checks,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "checks_failed": len(failed),
        "failed_checks": failed,
        "gold_matchups": 5826 if not failed else None,
        "request_design_validated": not failed,
        "request_draft_created": False,
        "approval_created": False,
        "execution_workflow_created": False,
        "real_artifact_read": False,
        "ready_for_request_draft": not failed,
        "ready_for_explicit_user_approval": False,
        "ready_for_real_artifact_execution": False,
        "ready_for_corpus_freeze_claim": False,
        "ready_for_market_backtest": False,
        "ready_for_model_retraining": False,
        "formal_stake": 0,
    }


def self_test(text: str, status: dict[str, Any], result: dict[str, Any]) -> dict[str, bool]:
    baseline = validate(text, status, result)
    assert baseline["checks_failed"] == 0, baseline
    cases = {
        "wrong_next_blocks": text.replace(NEXT, "WRONG_NEXT", 1),
        "design_not_valid_blocks": text.replace("real Artifact execution request design validated: true", "real Artifact execution request design validated: false", 1),
        "request_created_blocks": text.replace("real Artifact execution request created: false", "real Artifact execution request created: true", 1),
        "approval_blocks": text.replace("real Artifact execution approved: false", "real Artifact execution approved: true", 1),
        "execution_blocks": text.replace("real Artifact execution count: 0", "real Artifact execution count: 1", 1),
        "manifest_blocks": text.replace("semantic freeze manifest created: false", "semantic freeze manifest created: true", 1),
        "freeze_blocks": text.replace("corpus freeze executed: false", "corpus freeze executed: true", 1),
        "nonzero_stake_blocks": text.replace("正式 Stake：**0**", "正式 Stake：**1**", 1),
    }
    output: dict[str, bool] = {"baseline_passes": True}
    for name, mutated in cases.items():
        output[name] = validate(mutated, status, result)["checks_failed"] > 0
        assert output[name], name

    status_mutations = {
        "status_request_blocks": ("request_draft_created", True),
        "status_approval_blocks": ("approval_record_created", True),
        "status_workflow_blocks": ("execution_workflow_created", True),
        "status_execution_blocks": ("execution_count", 1),
        "status_consumed_blocks": ("request_consumed", True),
        "status_download_blocks": ("real_artifact_downloaded", True),
        "status_read_blocks": ("real_artifact_read", True),
        "status_manifest_blocks": ("semantic_manifest_created", True),
        "status_freeze_blocks": ("corpus_frozen", True),
    }
    for name, (key, value) in status_mutations.items():
        mutated = json.loads(json.dumps(status))
        mutated["request_lifecycle"][key] = value
        output[name] = validate(text, mutated, result)["checks_failed"] > 0
        assert output[name], name

    bad_result = json.loads(json.dumps(result))
    bad_result["ready_for_real_artifact_execution"] = True
    output["bad_result_blocks"] = validate(text, status, bad_result)["checks_failed"] > 0
    assert output["bad_result_blocks"]
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", required=True, type=Path)
    parser.add_argument("--request-design-status", required=True, type=Path)
    parser.add_argument("--request-design-result", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    text = args.status.read_text(encoding="utf-8")
    status = json.loads(args.request_design_status.read_text(encoding="utf-8"))
    result = json.loads(args.request_design_result.read_text(encoding="utf-8"))
    report = validate(text, status, result)
    if args.self_test:
        report["self_test"] = self_test(text, status, result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["checks_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
