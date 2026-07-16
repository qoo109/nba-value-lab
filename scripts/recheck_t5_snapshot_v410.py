#!/usr/bin/env python3
"""V4.10 T-5m final recheck with target two and maximum three mains."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import recheck_t5_snapshot as prior
from append_research_record_v410 import append_many
from multi_main_policy import apply_multi_main, load_active_configs, rebuild_multi_lock_index

ROOT = prior.ROOT
LOCKS_DIR = prior.LOCKS_DIR
LOCKS_INDEX = prior.LOCKS_DIR / "index.json"
prior.load_active_configs = lambda: load_active_configs(ROOT, ROOT / "models" / "manifest.json")
prior.append_many = append_many


def previous_selected_ids(top: dict[str, Any], previous_output: Path | None) -> list[str]:
    if previous_output:
        payload = prior.load_json(previous_output)
        selection = payload.get("selection", {})
    else:
        reference = top.get("t60_selection_path")
        selection = prior.load_json(ROOT / reference) if reference else {}
    ids = selection.get("selected_prediction_ids")
    if isinstance(ids, list):
        return [str(value) for value in ids]
    single = selection.get("selected_prediction_id")
    return [single] if single else []


def run(input_path: Path, *, dry_run: bool, previous_output: Path | None = None, output_path: Path | None = None) -> dict[str, Any]:
    top = prior.load_json(input_path)
    if top.get("data_mode") == "fixture" and not dry_run:
        raise ValueError("fixture data can only run with --dry-run")
    with tempfile.TemporaryDirectory() as directory:
        raw_output = Path(directory) / "single-main-output.json"
        prior.run(input_path, dry_run=True, previous_output=previous_output, output_path=raw_output)
        payload = prior.load_json(raw_output)

    manifest, _, g_config, _ = prior.load_active_configs()
    records = payload["records"]
    selection = apply_multi_main(records, payload["selection"], g_config, "T-5m")
    selection["model_g_revision"] = manifest["active"]["G"]["revision_id"]
    old_ids = previous_selected_ids(top, previous_output)
    selection["t60_selected_prediction_ids"] = old_ids
    selection["t60_selected_prediction_id"] = old_ids[0] if old_ids else None
    selection["main_changed_from_t60"] = selection["selected_prediction_ids"] != old_ids
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
    print(f"Rechecked {len(records)} records; final_mains={selection['selected_count']}")
    return selection


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--previous-output", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    run(args.input, dry_run=args.dry_run, previous_output=args.previous_output, output_path=args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
