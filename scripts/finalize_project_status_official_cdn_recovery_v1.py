#!/usr/bin/env python3
"""Finalize the current 2023-24 zero-feature count after official-CDN recovery."""
from pathlib import Path

path = Path("PROJECT_STATUS.md")
text = path.read_text(encoding="utf-8")
old = "2023-24 games without team features: 2"
new = "2023-24 games without team features before recovery: 2\n2023-24 games without team features after recovery: 0"
if text.count(old) != 1:
    raise RuntimeError(f"expected one stale zero-feature count, found {text.count(old)}")
text = text.replace(old, new, 1)
required = (
    "reference coverage: 5,826 / 5,826",
    "source gap exception remaining count: 0",
    "2023-24 games without team features after recovery: 0",
    "raw Historical Gold matchups: 5,826",
    "Gold dataset complete for governed five-season scope: true",
    "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_POLICY_READY_FOR_DESIGN",
    "formal stake: 0",
)
for fragment in required:
    if fragment not in text:
        raise RuntimeError(f"required status fragment missing: {fragment}")
path.write_text(text, encoding="utf-8")
print({"status": "PROJECT_STATUS_RECOVERY_FINALIZED", "remaining_zero_feature_games": 0, "formal_stake": 0})
