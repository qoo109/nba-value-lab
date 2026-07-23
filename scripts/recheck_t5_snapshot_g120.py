#!/usr/bin/env python3
"""T-5 runtime wrapper preserving G1.2.0 EV-primary and parallel control output."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

import recheck_t5_snapshot as base
from g1_2_0_runtime import ev_primary_decision, resolve_execution
from lock_t60_snapshot_g120 import gate_results, g_decision, ranking_key

ROOT = base.ROOT
LOCKS_DIR = base.LOCKS_DIR
LOCKS_INDEX = base.LOCKS_DIR / "index.json"
load_json = base.load_json
append_many = base.append_many
last_execution_context: dict[str, Any] = {}

_LEGACY_LOAD = base.load_active_configs
_LEGACY_MAKE_RECORD = base.make_record


def make_record(*args: Any, **kwargs: Any) -> dict[str, Any]:
    record = _LEGACY_MAKE_RECORD(*args, **kwargs)
    item = args[0] if args else kwargs["item"]
    candidate = item["candidate"]
    decision = item["g"]
    parallel_config = last_execution_context.get("parallel_g_config")
    parallel = g_decision(candidate, parallel_config) if parallel_config else None
    parallel_entry = last_execution_context.get("parallel_g_entry") or {}
    record.update({
        "g_decision_metric": decision.get("decision_metric", "threshold_distance_pp"),
        "g_conservative_ev": decision.get("ev_conservative", candidate["p_conservative"] * candidate["target_odds"] - 1),
        "g_ev_grade_threshold": decision.get("grade_threshold_ev"),
        "g_ev_threshold_distance_pp": decision.get("selection_surplus_pp"),
        "g_pp_guard_min_pp": decision.get("pp_guard_min_pp"),
        "g_pp_guard_pass": decision.get("pp_guard_pass"),
        "g_pp_guard_surplus_pp": decision.get("pp_guard_surplus_pp"),
        "g_ev_candidate": decision.get("ev_candidate"),
        "g_minimum_candidate_odds": decision.get("minimum_candidate_odds"),
        "g_execution_status": last_execution_context.get("execution_status"),
        "g_primary_after_trigger": bool(last_execution_context.get("activated")),
        "g_parallel_role": last_execution_context.get("parallel_role"),
        "g_parallel_model": str(parallel_entry.get("version")) if parallel_entry else None,
        "g_parallel_revision": parallel_entry.get("revision_id"),
        "g_parallel_grade": parallel.get("grade") if parallel else None,
        "g_parallel_conclusion": parallel.get("conclusion") if parallel else None,
        "g_parallel_threshold_distance_pp": parallel.get("gap_pp") if parallel else None,
        "g_parallel_conservative_ev": candidate["p_conservative"] * candidate["target_odds"] - 1 if parallel else None,
    })
    return record


def load_active_configs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    if last_execution_context:
        return (
            last_execution_context["manifest"],
            last_execution_context["v_config"],
            last_execution_context["primary_g_config"],
            last_execution_context["coordination"],
        )
    return _LEGACY_LOAD()


def _configure(top: dict[str, Any]) -> None:
    global last_execution_context
    last_execution_context = resolve_execution(ROOT, ROOT / "models" / "manifest.json", top)
    base.load_active_configs = load_active_configs
    base.g_decision = g_decision
    base.gate_results = gate_results
    base.ranking_key = ranking_key
    base.make_record = make_record


def _enrich_output(path: Path) -> dict[str, Any]:
    payload = base.load_json(path)
    selection = payload["selection"]
    records = payload["records"]
    selection.update({
        "g_execution_status": last_execution_context["execution_status"],
        "g_primary_after_trigger": bool(last_execution_context["activated"]),
        "g_parallel_role": last_execution_context.get("parallel_role"),
        "g_parallel_model_revision": (last_execution_context.get("parallel_g_entry") or {}).get("revision_id"),
        "coordination_id": last_execution_context["coordination"]["coordination_id"],
    })
    by_id = {record["prediction_id"]: record for record in records}
    for trace in selection.get("ranking_trace", []):
        record = by_id.get(trace.get("prediction_id"))
        if record:
            for key in ("g_decision_metric", "g_conservative_ev", "g_ev_threshold_distance_pp", "g_pp_guard_pass", "g_parallel_grade"):
                trace[key] = record.get(key)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def run(input_path: Path, *, dry_run: bool, previous_output: Path | None = None, output_path: Path | None = None) -> dict[str, Any]:
    top = base.load_json(input_path)
    _configure(top)
    if output_path is None:
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory) / "g120-t5-output.json"
            base.run(input_path, dry_run=dry_run, previous_output=previous_output, output_path=temp)
            return _enrich_output(temp)["selection"]
    base.run(input_path, dry_run=dry_run, previous_output=previous_output, output_path=output_path)
    return _enrich_output(output_path)["selection"]


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
