#!/usr/bin/env python3
"""Validate PROJECT_STATUS after the two-game official-CDN PBP recovery."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

NEXT = "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_POLICY_READY_FOR_DESIGN"
RECOVERY = "HISTORICAL_SILVER_2023_24_TWO_GAME_OFFICIAL_CDN_PBP_RECOVERY_PASS"

REQUIRED_CURRENT_ONCE = (
    "candidate formal result: REFERENCE COVERAGE COMPLETE / MARKET EVALUATION NOT AUTHORIZED",
    "Gold/Silver reconciliation result: SOURCE GAP RESOLVED VIA OFFICIAL CDN PBP RECOVERY",
    "reference coverage: 5,826 / 5,826",
    "2023-24 games without team features before recovery: 2",
    "2023-24 games without team features after recovery: 0",
    "source gap exception historical count: 2",
    "source gap exception remaining count: 0",
    "source gap exception recovery: PASS / OFFICIAL CDN PBP",
    "official CDN recovery run: 29976204693",
    "official CDN recovery Artifact: 8551587005",
    "official CDN recovery Artifact digest: sha256:3ed2d28da3af58b8b72d805860a144541ac5f38106653cfbda593e16bbaa8e8d",
    "official CDN recovery recording PR: 133",
    "official CDN recovery recording merge: 98bcb2538070eb57bba2ce79920262262c0924ef",
    "eligible Historical Gold corpus for future policy design: 5,826",
    "documented exceptions excluded from Gold eligibility: 0",
    "raw Historical Silver games: 5,826",
    "raw Historical Gold matchups: 5,826",
    "raw missing Gold for Silver: 0",
    "documented source gap exceptions remaining: 0",
    "unexplained missing after recovery: 0",
    "Gold dataset complete for governed five-season scope: true",
    NEXT,
)

REQUIRED_ANYWHERE = (
    "### Two-game official CDN PBP recovery",
    RECOVERY,
    "source archive SHA-256: 33d49fefc809f73d5d6cbad6d1d6690e0df6c89fe2b5a4d814ecc9ea4df6101b",
    "source archive rows scanned: 674,937",
    "target games found: 2 / 2",
    "target event rows found: 1,108",
    "recovered game dates: 2",
    "possession rows added: 412",
    "team feature rows added: 4",
    "remaining games without team features: 0",
    "remaining documented exceptions: 0",
    "Silver games / team rows: 5,826 / 11,652",
    "Gold matchups / team rows: 5,826 / 11,652",
    "Gold point-in-time violations: 0",
    "Artifact: 8551587005",
    "Silver SHA-256: 48c032339402d5f75e43d7aaf8e977784aee9eceff74c9e7da952af8e1680eb8",
    "Gold SHA-256: a4e94fab1681b53817f305d08c196995d406fa0566ab70d6083aa5cebfc52085",
    "result SHA-256: 97d292d56f6ee8b6f0a2d4e4471990f7c953cca7c324eb64c129066695df7c30",
    "reproducibility run: 29976847034 / success",
    "result validation run: 29976847035 / success",
    "formal Stake: 0",
    "data/research/historical-silver-2023-24-two-game-official-cdn-pbp-recovery-result-v2.json",
    "data/research/historical-silver-2023-24-two-game-official-cdn-pbp-recovery-current-status-v1.json",
    "docs/historical-silver-two-game-official-cdn-pbp-recovery-result-v2.md",
)

BLOCKED = (
    "complete `5,826`-matchup corpus freeze before a separately validated freeze policy and implementation",
    "synthetic, copied, zero-imputed or manually entered source-gap rows",
    "further Silver／Gold rebuild or canonical replacement outside the adopted recovery recipe",
    "cross-source audit rerun",
    "point-in-time market evaluation",
    "CLV, EV, ROI, or Drawdown",
    "model retraining",
    "betting-edge claims",
    "formal Stake above `0`",
)

STALE_CURRENT = (
    "eligible Historical Gold corpus for future policy design: 5,824",
    "documented exceptions excluded from Gold eligibility: 2",
    "raw Historical Gold matchups: 5,824",
    "raw missing Gold for Silver: 2",
    "HISTORICAL_GOLD_5824_ELIGIBLE_CORPUS_FREEZE_AND_EXCEPTION_EXCLUSION_POLICY_READY_FOR_DESIGN",
)


def validate(text: str) -> dict[str, Any]:
    current, _, evidence = text.partition("## Completed Evidence")
    checks: dict[str, bool] = {}
    for index, fragment in enumerate(REQUIRED_CURRENT_ONCE):
        checks[f"current_once_{index}"] = current.count(fragment) == 1
    for index, fragment in enumerate(REQUIRED_ANYWHERE):
        checks[f"present_{index}"] = fragment in text
    for index, fragment in enumerate(BLOCKED):
        checks[f"blocked_{index}"] = fragment in text
    for index, fragment in enumerate(STALE_CURRENT):
        checks[f"stale_current_absent_{index}"] = fragment not in current
    checks.update({
        "evidence_partition_exists": bool(evidence),
        "research_position_preserved": "研究定位：**Research Candidate / Pre-Market-Backtest**" in text,
        "header_stake_zero": "正式 Stake：**0**" in text,
        "next_before_evidence": text.index("## Next Unique Mainline") < text.index("## Completed Evidence"),
        "recovery_evidence_before_consumed_scopes": text.index("### Two-game official CDN PBP recovery") < text.index("## Consumed One-time Scopes"),
        "historic_5824_evidence_preserved": "Gold matchups: 5,824" in evidence,
        "historic_exception_evidence_preserved": "documented source-gap exceptions: 2" in evidence,
    })
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": "project-status-after-official-cdn-recovery-validation-report-v1",
        "validated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "formal_state": "PROJECT_STATUS_OFFICIAL_CDN_RECOVERY_SYNC_VALID" if not failed else "PROJECT_STATUS_OFFICIAL_CDN_RECOVERY_SYNC_INVALID",
        "checks": checks,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "checks_failed": len(failed),
        "failed_checks": failed,
        "silver_games": 5826 if not failed else None,
        "gold_matchups": 5826 if not failed else None,
        "remaining_exceptions": 0 if not failed else None,
        "gold_complete_for_governed_scope": not failed,
        "ready_for_complete_corpus_freeze_policy_design": not failed,
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
        "remaining_exception_blocks": text.replace("source gap exception remaining count: 0", "source gap exception remaining count: 2", 1),
        "zero_feature_blocks": text.replace("2023-24 games without team features after recovery: 0", "2023-24 games without team features after recovery: 2", 1),
        "wrong_next_blocks": text.replace(NEXT, "WRONG_NEXT", 1),
        "missing_artifact_blocks": text.replace("official CDN recovery Artifact: 8551587005", "official CDN recovery Artifact: unavailable", 1),
        "pit_failure_blocks": text.replace("Gold point-in-time violations: 0", "Gold point-in-time violations: 1", 1),
        "market_boundary_removed_blocks": text.replace("point-in-time market evaluation", "market evaluation removed", 1),
        "nonzero_header_stake_blocks": text.replace("正式 Stake：**0**", "正式 Stake：**1**", 1),
    }
    output: dict[str, bool] = {"baseline_passes": True}
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
