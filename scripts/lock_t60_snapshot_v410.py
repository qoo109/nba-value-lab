#!/usr/bin/env python3
"""V4.10 T-60m locker with target two and maximum three main selections."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import lock_t60_snapshot_v49 as prior
from append_research_record_v410 import append_many
from multi_main_policy import apply_multi_main, load_active_configs, rebuild_multi_lock_index

base = prior.base
ROOT = base.ROOT
LOCKS_DIR = base.LOCKS_DIR
LOCKS_INDEX = base.LOCKS_INDEX
base.load_active_configs = lambda: load_active_configs(ROOT, base.MODELS_MANIFEST)


def run(input_path: Path, *, dry_run: bool, output_path: Path | None = None) -> dict[str, Any]:
    top = base.load_json(input_path)
    if top.get("data_mode") == "fixture" and not dry_run:
        raise ValueError("fixture data can only run with --dry-run")
    with tempfile.TemporaryDirectory() as directory:
        raw_output = Path(directory) / "single-main-output.json"
        base.run(input_path, dry_run=True, output_path=raw_output)
        payload = base.load_json(raw_output)

    manifest, _, g_config, _ = base.load_active_configs()
    records = payload["records"]
    selection = apply_multi_main(records, payload["selection"], g_config, "T-60m")
    selection["model_g_revision"] = manifest["active"]["G"]["revision_id"]
    for trace in selection.get("ranking_trace", []):
        match = next((record for record in records if record["prediction_id"] == trace.get("prediction_id")), None)
        if match:
            trace["main_candidate"] = match["main_candidate"]
            trace["main_rank"] = match.get("main_rank")
            trace["ui_priority_candidate"] = match["ui_priority_candidate"]

    result = {"selection": selection, "records": records}
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if dry_run:
        append_many(records, validate_only=True)
        print(json.dumps(selection, ensure_ascii=False, indent=2))
        return selection

    day_dir = LOCKS_DIR / top["slate_date"]
    day_dir.mkdir(parents=True, exist_ok=True)
    lock_path = day_dir / f"{selection['selection_id']}.json"
    if lock_path.exists():
        raise ValueError(f"selection lock already exists: {lock_path.relative_to(ROOT)}")
    temp = lock_path.with_suffix(".json.tmp")
    temp.write_text(json.dumps(selection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        append_many(records)
        os.replace(temp, lock_path)
        rebuild_multi_lock_index(LOCKS_DIR, LOCKS_INDEX, ROOT)
    finally:
        if temp.exists():
            temp.unlink()
    print(f"Locked {len(records)} records; mains={selection['selected_count']}")
    return selection


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    run(args.input, dry_run=args.dry_run, output_path=args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
