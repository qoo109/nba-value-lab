#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT / "models/manifest.json").read_text(encoding="utf-8"))
schema = json.loads((ROOT / "schemas/prediction-record.schema.json").read_text(encoding="utf-8"))
scheduled_g = manifest["scheduled_next"]["G"]
scheduled_c = manifest["scheduled_next"]["coordination"]
g = json.loads((ROOT / scheduled_g["config"]).read_text(encoding="utf-8"))
c = json.loads((ROOT / scheduled_c["config"]).read_text(encoding="utf-8"))
assert manifest["active"]["G"]["version"] == "1.1.1"
assert scheduled_g["version"] == "1.2.0"
assert scheduled_c["coordination_id"] == "V3.1.1_X_G1.2.0-20260724"
assert c["engine_versions"] == {"V": "3.1.1", "G": "1.2.0"}
assert c["combined_policy"]["formal_stake_fraction"] == 0
assert g["ev_policy"]["candidate_min_ev"] == 0.05
assert g["ev_policy"]["grade_p_min_ev"] == 0.07
assert g["ev_policy"]["grade_b_min_ev"] == 0.10
assert g["ev_policy"]["pp_guard_min"] == 2.0
assert schema["schema_version"] == "1.4.0"
assert "1.2.0" in schema["properties"]["model_g"]["enum"]
assert manifest["compatibility"]["prediction_record_schema"] == "1.4.0"
for entry in (scheduled_g, scheduled_c):
    assert (ROOT / entry["config"]).is_file()
    assert (ROOT / entry["spec"]).is_file()
digest = hashlib.sha256((ROOT / scheduled_c["spec"]).read_bytes()).hexdigest()
assert c["spec_integrity"]["digest"] == digest
for path in (
    "scripts/g1_2_0_runtime.py", "scripts/lock_t60_snapshot_g120.py",
    "scripts/recheck_t5_snapshot_g120.py", "js/v4-11-g1-2-0-ev-primary.js",
):
    assert (ROOT / path).is_file(), path
print(json.dumps({
    "formal_state": "G1_2_0_LIVE_OUTPUT_IMPLEMENTATION_VALID",
    "active_G": manifest["active"]["G"]["revision_id"],
    "scheduled_G": scheduled_g["revision_id"],
    "scheduled_coordination": scheduled_c["coordination_id"],
    "record_schema": schema["schema_version"],
    "formal_stake": 0,
}, ensure_ascii=False, indent=2))
