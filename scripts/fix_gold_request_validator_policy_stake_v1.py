#!/usr/bin/env python3
from pathlib import Path

path = Path("scripts/validate_historical_gold_5826_freeze_manifest_real_artifact_execution_request_v1.py")
text = path.read_text(encoding="utf-8")
old = '    expect(policy, "formal_stake", 0)\n'
new = '    expect(policy, "decision.formal_stake", 0)\n'
if text.count(old) != 1:
    raise SystemExit(f"expected one policy Stake assertion, found {text.count(old)}")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
