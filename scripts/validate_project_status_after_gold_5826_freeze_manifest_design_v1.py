#!/usr/bin/env python3
"""Validate PROJECT_STATUS after Gold 5,826 freeze-manifest implementation design."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

NEXT = "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_IMPLEMENTATION_READY_FOR_SYNTHETIC_VALIDATION"
DESIGN_STATE = "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_IMPLEMENTATION_DESIGN_VALIDATED_READY_FOR_SYNTHETIC_VALIDATION"

REQUIRED_CURRENT = (
    "reference coverage: 5,826 / 5,826",
    "source gap exception remaining count: 0",
    "raw Historical Gold matchups: 5,826",
    "Gold dataset complete for governed five-season scope: true",
    "complete corpus freeze policy: VALIDATED / DESIGN ONLY",
    "freeze manifest implementation design: VALIDATED / DESIGN ONLY",
    "freeze manifest implementation design id: HISTORICAL-GOLD-5826-COMPLETE-CORPUS-FREEZE-MANIFEST-IMPLEMENTATION-DESIGN-2026-07-23-001",
    "freeze manifest implementation design recording PR: 137",
    "freeze manifest implementation design recording merge: 1730859888bd21cf7727ef6c5cbf348fb7aeddeb",
    "freeze manifest implementation design validation run: 29982518227",
    "freeze manifest implementation design validation artifact: 8553727483",
    "freeze manifest implementation design validation digest: sha256:b752398847700bfc4a09831bbab069451606ecce2615cdcb511b5ddab06d3dc7",
    "freeze manifest implementation module created: false",
    "freeze manifest synthetic validation executed: false",
    "real Artifact freeze workflow created: false",
    "real Artifact execution approved: false",
    "semantic freeze manifest created: false",
    "corpus freeze executed: false",
    NEXT,
)

REQUIRED_EVIDENCE = (
    "### Historical Gold 5,826 freeze-manifest implementation design",
    "formal state: HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_IMPLEMENTATION_DESIGN_VALIDATED",
    "Gold matchups / team rows: 5,826 / 11,652",
    "remaining source exceptions: 0",
    "point-in-time violations: 0",
    "read-only SQLite required: true",
    "policy-driven stable columns required: true",
    "canonical type-tagged JSON Lines: true",
    "incremental SHA-256: true",
    "aggregate output maximum: 1 MiB",
    "real Artifact read: false",
    "workflow run: 29982518227",
    "job: 89127261444 / validate-implementation-design / success",
    "Artifact: 8553727483",
    "Artifact digest: sha256:b752398847700bfc4a09831bbab069451606ecce2615cdcb511b5ddab06d3dc7",
)

BLOCKED = (
    "Artifact `8551587005` must not be downloaded or read",
    "no canonical manifest or corpus freeze may occur without a later separate explicit approval",
    "Market backtesting",
    "injury-model activation",
    "model retraining",
    "betting-edge claims",
    "Stake above `0`",
)


def validate(text: str, design_status: dict[str, Any]) -> dict[str, Any]:
    current, marker, evidence = text.partition("## Completed Evidence")
    checks: dict[str, bool] = {}
    for index, fragment in enumerate(REQUIRED_CURRENT):
        checks[f"current_{index}"] = current.count(fragment) == 1
    for index, fragment in enumerate(REQUIRED_EVIDENCE):
        checks[f"evidence_{index}"] = fragment in evidence
    for index, fragment in enumerate(BLOCKED):
        checks[f"blocked_{index}"] = fragment in current
    checks.update({
        "evidence_marker": bool(marker),
        "header_stake_zero": "正式 Stake：**0**" in text,
        "research_position": "研究定位：**Research Candidate / Pre-Market-Backtest**" in text,
        "stale_next_absent": "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_IMPLEMENTATION_READY_FOR_DESIGN" not in current,
        "design_status_state": design_status.get("formal_state") == DESIGN_STATE,
        "design_status_ready_synthetic": design_status.get("ready_for_synthetic_implementation") is True,
        "design_status_not_ready_real": design_status.get("ready_for_real_artifact_execution") is False,
        "design_status_not_ready_market": design_status.get("ready_for_market_backtest") is False,
        "design_status_not_ready_retrain": design_status.get("ready_for_model_retraining") is False,
        "design_status_stake": design_status.get("formal_stake") == 0,
        "design_status_execution_zero": design_status.get("implementation_state", {}).get("real_artifact_execution_count") == 0,
        "design_status_not_frozen": design_status.get("implementation_state", {}).get("corpus_frozen") is False,
    })
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": "project-status-after-gold-5826-freeze-manifest-design-validation-report-v1",
        "validated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "formal_state": "PROJECT_STATUS_GOLD_5826_FREEZE_MANIFEST_DESIGN_SYNC_VALID" if not failed else "PROJECT_STATUS_GOLD_5826_FREEZE_MANIFEST_DESIGN_SYNC_INVALID",
        "checks": checks,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "checks_failed": len(failed),
        "failed_checks": failed,
        "gold_matchups": 5826 if not failed else None,
        "remaining_exceptions": 0 if not failed else None,
        "design_validated": not failed,
        "implementation_module_created": False,
        "synthetic_validation_executed": False,
        "real_artifact_execution_approved": False,
        "corpus_freeze_executed": False,
        "ready_for_synthetic_implementation": not failed,
        "ready_for_real_artifact_execution": False,
        "ready_for_market_backtest": False,
        "ready_for_model_retraining": False,
        "formal_stake": 0,
    }


def self_test(text: str, design_status: dict[str, Any]) -> dict[str, bool]:
    baseline = validate(text, design_status)
    assert baseline["checks_failed"] == 0, baseline
    cases = {
        "wrong_next_blocks": text.replace(NEXT, "WRONG_NEXT", 1),
        "module_created_blocks": text.replace("freeze manifest implementation module created: false", "freeze manifest implementation module created: true", 1),
        "real_approved_blocks": text.replace("real Artifact execution approved: false", "real Artifact execution approved: true", 1),
        "manifest_created_blocks": text.replace("semantic freeze manifest created: false", "semantic freeze manifest created: true", 1),
        "corpus_frozen_blocks": text.replace("corpus freeze executed: false", "corpus freeze executed: true", 1),
        "wrong_gold_blocks": text.replace("raw Historical Gold matchups: 5,826", "raw Historical Gold matchups: 5,824", 1),
        "nonzero_stake_blocks": text.replace("正式 Stake：**0**", "正式 Stake：**1**", 1),
    }
    output: dict[str, bool] = {"baseline_passes": True}
    for name, mutated in cases.items():
        output[name] = validate(mutated, design_status)["checks_failed"] > 0
        assert output[name], name
    bad_status = json.loads(json.dumps(design_status))
    bad_status["ready_for_real_artifact_execution"] = True
    output["bad_design_status_blocks"] = validate(text, bad_status)["checks_failed"] > 0
    assert output["bad_design_status_blocks"]
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", required=True, type=Path)
    parser.add_argument("--design-status", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    text = args.status.read_text(encoding="utf-8")
    design_status = json.loads(args.design_status.read_text(encoding="utf-8"))
    report = validate(text, design_status)
    if args.self_test:
        report["self_test"] = self_test(text, design_status)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["checks_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
