#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from g1_2_0_runtime import ev_primary_decision, resolve_execution
import lock_t60_snapshot_v410
import recheck_t5_snapshot_v410

g = json.loads((ROOT / "models/g1/1.2.0/config.json").read_text(encoding="utf-8"))

def candidate(p: float, odds: float = 2.0) -> dict:
    return {
        "analysis_gate_status": "可分析", "confidence": "高", "news_risk_level": 0,
        "p_conservative": p, "target_odds": odds,
    }

assert ev_primary_decision(candidate(0.55), g)["grade"] == "ㄅ"
assert ev_primary_decision(candidate(0.54), g)["grade"] == "ㄆ"
assert ev_primary_decision(candidate(0.525), g)["grade"] == "ㄇ"
low_guard = ev_primary_decision(candidate(0.51), g)
assert low_guard["grade"] == "ㄆ" and low_guard["pp_guard_pass"] is False
assert ev_primary_decision(candidate(0.49), g)["grade"] == "不支持"

active = resolve_execution(ROOT, ROOT / "models/manifest.json", {"data_mode": "fixture"})
assert active["primary_g_entry"]["version"] == "1.1.1"
assert active["parallel_g_entry"]["version"] == "1.2.0"
activated = resolve_execution(ROOT, ROOT / "models/manifest.json", {"season": "2026-27", "competition_type": "regular_season"})
assert activated["activated"] is True
assert activated["primary_g_entry"]["version"] == "1.2.0"
assert activated["parallel_g_entry"]["version"] == "1.1.1"

with tempfile.TemporaryDirectory() as directory:
    t60_out = Path(directory) / "t60.json"
    lock_t60_snapshot_v410.run(ROOT / "data/fixtures/t60-g1-2-0-ev-example.json", dry_run=True, output_path=t60_out)
    t60 = json.loads(t60_out.read_text(encoding="utf-8"))
    assert t60["selection"]["model_g_revision"] == "G1.2.0-20260723"
    assert t60["selection"]["g_primary_after_trigger"] is True
    assert t60["selection"]["selected_count"] >= 1
    assert all(record["model_g"] == "1.2.0" for record in t60["records"])
    assert all(record["g_decision_metric"] == "conservative_ev" for record in t60["records"])
    assert any(record["g_grade"] == "ㄅ" and record["g_pp_guard_pass"] for record in t60["records"])
    assert all(record["g_parallel_revision"] == "G1.1.1-20260719" for record in t60["records"])

    t5_out = Path(directory) / "t5.json"
    recheck_t5_snapshot_v410.run(
        ROOT / "data/fixtures/t5-g1-2-0-ev-example.json",
        dry_run=True,
        previous_output=t60_out,
        output_path=t5_out,
    )
    t5 = json.loads(t5_out.read_text(encoding="utf-8"))
    assert t5["selection"]["model_g_revision"] == "G1.2.0-20260723"
    assert t5["selection"]["g_primary_after_trigger"] is True
    assert all(record["model_g"] == "1.2.0" for record in t5["records"])
    assert all(record["g_parallel_role"] == "control_shadow" for record in t5["records"])

print("G1.2.0 live EV output, history and T-60/T-5 activation tests passed")
