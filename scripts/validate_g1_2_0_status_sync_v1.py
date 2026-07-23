#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"missing {label}: {needle}")


def forbid(text: str, needle: str, label: str) -> None:
    if needle in text:
        raise SystemExit(f"stale {label}: {needle}")


root = Path(__file__).resolve().parents[1]
status = (root / "PROJECT_STATUS.md").read_text(encoding="utf-8")
readme = (root / "README.md").read_text(encoding="utf-8")
handoff = (
    root
    / "docs/handoffs/nba_value_lab_handoff_2026-07-24_g1_2_0_status_sync.md"
).read_text(encoding="utf-8")
manifest = json.loads((root / "models/manifest.json").read_text(encoding="utf-8"))

required_status = [
    "IMPLEMENTED / FIXTURE VALIDATED / REAL GOVERNED INPUT VALIDATION REQUIRED",
    "G1_2_0_LIVE_OUTPUT_IMPLEMENTATION_VALID",
    "validation run: 30025555150",
    "validation artifact: 8571205516",
    "VALIDATE_G1_2_0_END_TO_END_WITH_REAL_GOVERNED_2026_27_T60_INPUT",
    "BLOCKED — REAL GOVERNED INPUT NOT AVAILABLE",
    "TIMESTAMPED_BOOKMAKER_ODDS_REAL_OBSERVED_AT_DATA_ACQUISITION_REQUIRED",
    "formal Stake: 0",
]
for item in required_status:
    require(status, item, "PROJECT_STATUS value")
forbid(
    status,
    "G1.2.0 live decision output: IMPLEMENTED / FIXTURE VALIDATION REQUIRED",
    "PROJECT_STATUS lifecycle",
)

required_readme = [
    "G1.2.0 EV-primary live output 已由 PR #153 合併",
    "G1_2_0_LIVE_OUTPUT_IMPLEMENTATION_VALID",
    "BLOCKED — REAL GOVERNED INPUT NOT AVAILABLE",
    "不得直接修改 `main`",
    "正式 Stake 維持 0",
]
for item in required_readme:
    require(readme, item, "README value")
forbid(readme, "尚未完成 real-reference transformer validation", "README old blocker")

required_handoff = [
    "main: bcb66ba5b207d6a86cf87b3aeed18f3f3c2c0115",
    "latest merged PR: 153",
    "validation artifact: 8571205516",
    "VALIDATE_G1_2_0_END_TO_END_WITH_REAL_GOVERNED_2026_27_T60_INPUT",
    "BLOCKED — REAL GOVERNED INPUT NOT AVAILABLE",
    "Formal Stake: `0`",
]
for item in required_handoff:
    require(handoff, item, "handoff value")

assert manifest["active"]["V"]["revision_id"] == "V3.1.1-20260719"
assert manifest["active"]["G"]["revision_id"] == "G1.1.1-20260719"
assert manifest["scheduled_next"]["G"]["revision_id"] == "G1.2.0-20260723"
assert (
    manifest["scheduled_next"]["G"]["activation_trigger"]
    == "first_2026_27_regular_season_game_with_complete_T60_data_gate"
)
assert manifest["scheduled_next"]["G"]["formal_stake_fraction"] == 0
assert (
    manifest["scheduled_next"]["coordination"]["coordination_id"]
    == "V3.1.1_X_G1.2.0-20260724"
)

report = {
    "schema_version": 1,
    "formal_state": "G1_2_0_STATUS_DOCUMENTATION_SYNC_VALID",
    "project_status_synced": True,
    "readme_synced": True,
    "handoff_created": True,
    "active_g": manifest["active"]["G"]["revision_id"],
    "scheduled_g": manifest["scheduled_next"]["G"]["revision_id"],
    "next_mainline": "VALIDATE_G1_2_0_END_TO_END_WITH_REAL_GOVERNED_2026_27_T60_INPUT",
    "current_status": "BLOCKED_REAL_GOVERNED_INPUT_NOT_AVAILABLE",
    "market_backtest_executed": False,
    "model_retraining_executed": False,
    "formal_stake": 0,
}
out = root / "build/g1-2-0-status-sync-validation-v1.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
