#!/usr/bin/env python3
"""Validate PROJECT_STATUS after Historical Gold 5,826 freeze-policy validation."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

POLICY_ID = "HISTORICAL-GOLD-5826-COMPLETE-CORPUS-FREEZE-POLICY-2026-07-23-001"
POLICY_STATE = "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_POLICY_DESIGN_VALIDATED"
NEXT = "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_IMPLEMENTATION_READY_FOR_DESIGN"

CURRENT_ONCE = (
    "reference coverage: 5,826 / 5,826",
    "raw Historical Silver games: 5,826",
    "raw Historical Gold matchups: 5,826",
    "raw missing Gold for Silver: 0",
    "documented source gap exceptions remaining: 0",
    "Gold dataset complete for governed five-season scope: true",
    "complete corpus freeze policy: VALIDATED / DESIGN ONLY",
    f"complete corpus freeze policy id: {POLICY_ID}",
    f"complete corpus freeze policy formal state: {POLICY_STATE}",
    "complete corpus freeze policy recording PR: 135",
    "complete corpus freeze policy recording merge: b6edf9b8acaf51b1287d6976c6e42cac056dc726",
    "complete corpus freeze policy validation run: 29978555275",
    "complete corpus freeze policy validation artifact: 8552326235",
    "complete corpus freeze policy validation digest: sha256:96fdcee4b39f6ca03b9597677aa01db2e47b15d6d8f780f2e4525be978dd3722",
    "freeze manifest implementation created: false",
    "semantic freeze manifest created: false",
    "corpus freeze executed: false",
    "adopted Gold Artifact expiry: 2026-08-06T03:14:00Z",
    "timestamped bookmaker odds: POLICY ONLY / REAL OBSERVED_AT DATA NOT ACQUIRED",
    "injury panel activation: 41 independent games / 31 T-60 selected / below 100-game gate",
    "team submission completeness ledger: REQUIRED BEFORE FORMAL INJURY HOLDOUT",
    NEXT,
)

REQUIRED_ANYWHERE = (
    "### Historical Gold 5,826 complete corpus freeze policy",
    f"policy id: {POLICY_ID}",
    f"formal state: {POLICY_STATE}",
    "Silver games / team rows: 5,826 / 11,652",
    "Gold matchups / team rows: 5,826 / 11,652",
    "remaining source exceptions: 0",
    "Gold point-in-time violations: 0",
    "policy role: DESIGN ONLY / NO FREEZE EXECUTION",
    "corpus freeze executed: false",
    "recording PR: 135",
    "recording merge: b6edf9b8acaf51b1287d6976c6e42cac056dc726",
    "validation run: 29978555275",
    "validation job: 89115413805 / validate-freeze-policy / success",
    "validation Artifact: 8552326235",
    "validation digest: sha256:96fdcee4b39f6ca03b9597677aa01db2e47b15d6d8f780f2e4525be978dd3722",
    "Gold binary SHA-256: a4e94fab1681b53817f305d08c196995d406fa0566ab70d6083aa5cebfc52085",
    "Silver binary SHA-256: 48c032339402d5f75e43d7aaf8e977784aee9eceff74c9e7da952af8e1680eb8",
    "excluded volatile column: feature_generated_at only",
    "partial freeze: prohibited",
    "row exclusions: prohibited",
    "timestamped bookmaker odds: real legal auditable observed_at data still missing",
    "injury panel: 41 independent games / 31 selected T-60 games / below 100-game gate",
    "data/research/historical-gold-5826-complete-corpus-freeze-policy-v1.json",
    "data/research/historical-gold-5826-complete-corpus-freeze-policy-current-status-v1.json",
)

BLOCKED = (
    "freeze-manifest implementation before a separately validated implementation design",
    "real Artifact freeze execution before a separately approved one-time workflow",
    "any unbound rebuild after Artifact `8551587005` expires",
    "point-in-time market evaluation",
    "CLV, EV, ROI, or Drawdown",
    "model retraining",
    "betting-edge claims",
    "formal Stake above `0`",
)

STALE_CURRENT = (
    "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_POLICY_READY_FOR_DESIGN",
    "complete `5,826`-matchup corpus freeze before a separately validated freeze policy and implementation",
)


def validate(text: str) -> dict[str, Any]:
    current, separator, evidence = text.partition("## Completed Evidence")
    checks: dict[str, bool] = {}
    for index, fragment in enumerate(CURRENT_ONCE):
        checks[f"current_once_{index}"] = current.count(fragment) == 1
    for index, fragment in enumerate(REQUIRED_ANYWHERE):
        checks[f"present_{index}"] = fragment in text
    for index, fragment in enumerate(BLOCKED):
        checks[f"blocked_{index}"] = fragment in text
    for index, fragment in enumerate(STALE_CURRENT):
        checks[f"stale_absent_{index}"] = fragment not in current
    checks.update({
        "evidence_partition": bool(separator and evidence),
        "research_position": "研究定位：**Research Candidate / Pre-Market-Backtest**" in text,
        "stake_header": "正式 Stake：**0**" in text,
        "policy_evidence_before_consumed": text.index("### Historical Gold 5,826 complete corpus freeze policy") < text.index("## Consumed One-time Scopes"),
        "recovery_evidence_preserved": "### Two-game official CDN PBP recovery" in evidence,
        "historical_5824_evidence_preserved": "Gold matchups: 5,824" in evidence,
        "next_before_evidence": text.index("## Next Unique Mainline") < text.index("## Completed Evidence"),
    })
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": "project-status-after-gold-5826-freeze-policy-validation-report-v1",
        "validated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "formal_state": "PROJECT_STATUS_GOLD_5826_FREEZE_POLICY_SYNC_VALID" if not failed else "PROJECT_STATUS_GOLD_5826_FREEZE_POLICY_SYNC_INVALID",
        "checks": checks,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "checks_failed": len(failed),
        "failed_checks": failed,
        "policy_validated": not failed,
        "gold_matchups": 5826 if not failed else None,
        "remaining_exceptions": 0 if not failed else None,
        "corpus_freeze_executed": False,
        "ready_for_freeze_manifest_implementation_design": not failed,
        "ready_for_market_backtest": False,
        "ready_for_model_retraining": False,
        "formal_stake": 0,
    }


def self_test(text: str) -> dict[str, bool]:
    baseline = validate(text)
    assert baseline["checks_failed"] == 0, baseline
    mutations = {
        "wrong_gold_count_blocks": text.replace("raw Historical Gold matchups: 5,826", "raw Historical Gold matchups: 5,824", 1),
        "remaining_gap_blocks": text.replace("raw missing Gold for Silver: 0", "raw missing Gold for Silver: 2", 1),
        "policy_state_blocks": text.replace(POLICY_STATE, "WRONG_POLICY_STATE", 1),
        "manifest_false_ready_blocks": text.replace("semantic freeze manifest created: false", "semantic freeze manifest created: true", 1),
        "freeze_false_ready_blocks": text.replace("corpus freeze executed: false", "corpus freeze executed: true", 1),
        "wrong_next_blocks": text.replace(NEXT, "WRONG_NEXT", 1),
        "odds_false_ready_blocks": text.replace("timestamped bookmaker odds: POLICY ONLY / REAL OBSERVED_AT DATA NOT ACQUIRED", "timestamped bookmaker odds: READY", 1),
        "injury_false_ready_blocks": text.replace("injury panel activation: 41 independent games / 31 T-60 selected / below 100-game gate", "injury panel activation: READY", 1),
        "unbound_rebuild_removed_blocks": text.replace("any unbound rebuild after Artifact `8551587005` expires", "unbound rebuild allowed", 1),
        "stake_blocks": text.replace("正式 Stake：**0**", "正式 Stake：**1**", 1),
    }
    output = {"baseline_passes": True}
    for name, mutated in mutations.items():
        report = validate(mutated)
        output[name] = report["checks_failed"] > 0
        assert output[name], (name, report)
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
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
