#!/usr/bin/env python3
"""Validate PROJECT_STATUS after the consumed source-gap real-reference validation."""
from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REQUEST_ID = (
    "HISTORICAL-SILVER-2023-24-SOURCE-GAP-EXCEPTION-INTEGRATION-"
    "REAL-REFERENCE-VALIDATION-2026-07-22-001"
)
RESULT_STATE = (
    "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_"
    "REAL_REFERENCE_VALIDATION_PASS_CONSUMED"
)
NEXT_STEP = (
    "HISTORICAL_GOLD_5824_ELIGIBLE_CORPUS_FREEZE_AND_"
    "EXCEPTION_EXCLUSION_POLICY_READY_FOR_DESIGN"
)
RESULT_SHA = "sha256:048149cd058c74c1ab441a99f3a4eec0972668500e469ff81ce663b3e5264340"
QA_DIGEST = "sha256:5ce4c745b0262b30d9d1f390338b2bbce3bb9a60ef4428e3268d634f274de081"

REQUIRED_ONCE = (
    "狀態核對日期：2026-07-23  ",
    "candidate formal result: CROSS-SOURCE GATES PASS / MARKET EVALUATION NOT AUTHORIZED",
    "Gold/Silver reconciliation result: SOURCE_DATA_GAP_CONFIRMED / DOCUMENTED EXCEPTIONS RECOGNIZED",
    "real-reference validation request: EXECUTED / PASS / CONSUMED",
    "real-reference validation request execution count: 1 / 1",
    "real-reference validation approval granted: true",
    "real-reference validation execution enabled: false",
    "real-reference validation executed: true",
    "real-reference validation repeat execution: disabled",
    f"real-reference validation formal state: {RESULT_STATE}",
    f"real-reference validation result payload SHA-256: {RESULT_SHA}",
    "real-reference validation recording PR: 131",
    "real-reference validation recording merge: ce39a8f39032c5aebe07c2c6734ebc58b02e2108",
    "real-reference validation result QA run: 29972975866",
    "real-reference validation result QA artifact: 8550389215",
    f"real-reference validation result QA artifact digest: {QA_DIGEST}",
    "eligible Historical Gold corpus for future policy design: 5,824",
    "documented exceptions excluded from Gold eligibility: 2",
    NEXT_STEP,
    "### Source gap exception real-reference validation result",
)

REQUIRED_PRESENT = (
    REQUEST_ID,
    RESULT_STATE,
    RESULT_SHA,
    QA_DIGEST,
    "raw Historical Silver games: 5,826",
    "raw Historical Gold matchups: 5,824",
    "raw missing Gold for Silver: 2",
    "documented source-gap exceptions: 2",
    "unexplained missing after documentation: 0",
    "covered or documented: 5,826",
    "Gold dataset complete: false",
    "recognition gate passed: true",
    "exception code: SOURCE_ARCHIVE_PBPSTATS_GAME_ABSENT",
    "execution count: 1 / 1",
    "request consumed: true",
    "repeat execution allowed: false",
    "formal stake: 0",
    "workflow run: 29810347326",
    "source archive reconciliation run: 29901869841",
    "data/research/historical-silver-2023-24-source-gap-exception-integration-real-reference-validation-result-v1.json",
    "data/research/historical-silver-2023-24-source-gap-exception-integration-real-reference-validation-current-status-v3.json",
    "docs/historical-silver-2023-24-source-gap-exception-integration-real-reference-validation-result-v1.md",
    "scripts/validate_historical_silver_source_gap_exception_integration_real_reference_validation_result_v1.py",
    ".github/workflows/validate-historical-silver-source-gap-exception-integration-real-reference-validation-result-v1.yml",
)

STALE_CURRENT = (
    "real-reference validation request: VALID / AWAITING EXPLICIT USER APPROVAL",
    "real-reference validation request execution count: 0 / 1",
    "real-reference validation approval granted: false",
    "real-reference validation executed: false",
    "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_REAL_REFERENCE_VALIDATION_EXPLICIT_USER_APPROVAL_REQUIRED",
)

BLOCKED_REQUIRED = (
    "reuse, rerun, or re-dispatch of consumed real-reference validation Request `001`",
    "eligible-corpus freeze before a separately validated policy design and implementation",
    "Gold rebuild",
    "cross-source audit rerun",
    "point-in-time market evaluation",
    "CLV, EV, ROI, or Drawdown",
    "model retraining",
    "betting-edge claims",
    "formal Stake above `0`",
)


def validate(text: str) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    for index, fragment in enumerate(REQUIRED_ONCE):
        checks[f"required_once_{index}"] = text.count(fragment) == 1
    for index, fragment in enumerate(REQUIRED_PRESENT):
        checks[f"required_present_{index}"] = fragment in text
    for index, fragment in enumerate(STALE_CURRENT):
        checks[f"stale_absent_{index}"] = fragment not in text
    for index, fragment in enumerate(BLOCKED_REQUIRED):
        checks[f"blocked_present_{index}"] = fragment in text

    checks.update(
        {
            "current_block_precedes_evidence": text.index("## Current Control Block") < text.index("## Completed Evidence"),
            "next_step_precedes_evidence": text.index("## Next Unique Mainline") < text.index("## Completed Evidence"),
            "result_evidence_precedes_consumed_scopes": text.index("### Source gap exception real-reference validation result") < text.index("## Consumed One-time Scopes"),
            "request_listed_as_consumed": text.index(REQUEST_ID, text.index("## Consumed One-time Scopes")) > 0,
            "formal_stake_header_zero": "正式 Stake：**0**" in text,
            "research_position_unchanged": "研究定位：**Research Candidate / Pre-Market-Backtest**" in text,
        }
    )
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": "project-status-after-source-gap-real-reference-validation-report-v1",
        "validated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "formal_state": "PROJECT_STATUS_SOURCE_GAP_REAL_REFERENCE_VALIDATION_SYNC_VALID" if not failed else "PROJECT_STATUS_SOURCE_GAP_REAL_REFERENCE_VALIDATION_SYNC_INVALID",
        "checks": checks,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "checks_failed": len(failed),
        "failed_checks": failed,
        "request_consumed": True,
        "execution_count": 1,
        "maximum_execution_count": 1,
        "eligible_gold_corpus_count": 5824,
        "documented_exception_exclusion_count": 2,
        "gold_dataset_complete": False,
        "ready_for_policy_design": not failed,
        "ready_for_market_backtest": False,
        "formal_stake": 0,
    }


def self_test(text: str) -> dict[str, bool]:
    baseline = validate(text)
    assert baseline["checks_failed"] == 0, baseline
    tests: dict[str, bool] = {"baseline_passes": True}

    mutations = {
        "stale_state_blocks": text + "\nreal-reference validation executed: false\n",
        "wrong_count_blocks": text.replace("real-reference validation request execution count: 1 / 1", "real-reference validation request execution count: 0 / 1", 1),
        "approval_false_blocks": text.replace("real-reference validation approval granted: true", "real-reference validation approval granted: false", 1),
        "nonzero_stake_blocks": text.replace("正式 Stake：**0**", "正式 Stake：**1**", 1),
        "wrong_next_step_blocks": text.replace(NEXT_STEP, "WRONG_NEXT_STEP", 1),
        "missing_consumed_evidence_blocks": text.replace("request consumed: true", "request consumed: unavailable", 1),
        "market_block_removed_blocks": text.replace("point-in-time market evaluation", "point-in-time evaluation removed", 1),
        "wrong_eligible_count_blocks": text.replace("eligible Historical Gold corpus for future policy design: 5,824", "eligible Historical Gold corpus for future policy design: 5,826", 1),
    }
    for name, mutated in mutations.items():
        report = validate(mutated)
        tests[name] = report["checks_failed"] > 0
        assert tests[name], (name, report)
    return tests


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    text = args.status.read_text(encoding="utf-8")
    report = validate(text)
    if args.self_test:
        report["self_test"] = self_test(text)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["checks_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
