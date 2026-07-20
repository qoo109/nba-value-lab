#!/usr/bin/env python3
"""Recheck a locked NBA slate at T-5m and append immutable research records.

Rules:
- both sides of every game are required at the same bookmaker snapshot;
- unchanged prediction state reuses the T-60m prediction_id and only creates a
  new price_evaluation_id;
- any probability, injury, starter, minutes-limit, coverage, risk or Gate-state
  change creates a new prediction_id linked to the T-60m parent;
- G1 main selection is rerun and yields zero or one final main candidate;
- T-60m records are never overwritten;
- fixture data is dry-run only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from append_research_record_v49 import append_many, iter_records
from lock_t60_snapshot import (
    LOCKS_DIR,
    PROBABILITY_KEYS,
    ROOT,
    canonical_hash,
    coordination_decision,
    gate_results,
    g_decision,
    load_active_configs,
    load_json,
    parse_time,
    ranking_key,
    rebuild_locks_index,
    require,
    validate_candidate,
    validate_game_pair,
    v_decision,
)

PREDICTION_STATE_KEYS = (
    "scheduled_at",
    "selection_team_id",
    "opponent_team_id",
    "p_f",
    "p_market_consensus",
    "p_conservative",
    "p_neutral",
    "p_optimistic",
    "coverage_pct",
    "confidence",
    "news_risk_level",
    "analysis_gate_status",
    "comparison_sources",
    "injury_confirmed",
    "starters_confirmed",
    "minutes_limit_confirmed",
    "source_lineage_complete",
    "market_rules_complete",
    "out_of_distribution",
    "reverse_path_resolved",
    "stale_warning",
    "model_market_gap_pp",
    "independent_evidence_count",
)


def prediction_state(candidate: dict[str, Any]) -> dict[str, Any]:
    return {key: candidate.get(key) for key in PREDICTION_STATE_KEYS}


def state_from_record(record: dict[str, Any]) -> dict[str, Any]:
    if isinstance(record.get("prediction_state"), dict):
        return record["prediction_state"]
    return {key: record.get(key) for key in PREDICTION_STATE_KEYS}


def value_equal(left: Any, right: Any, tolerance: float = 1e-9) -> bool:
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return abs(float(left) - float(right)) <= tolerance
    return left == right


def state_changes(previous: dict[str, Any], current: dict[str, Any]) -> list[str]:
    changes: list[str] = []
    for key in PREDICTION_STATE_KEYS:
        if not value_equal(previous.get(key), current.get(key)):
            changes.append(key)
    return changes


def load_previous(top: dict[str, Any], previous_output: Path | None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if previous_output:
        payload = load_json(previous_output)
        require(isinstance(payload, dict), "previous output must be an object")
        selection = payload.get("selection")
        records = payload.get("records")
        require(isinstance(selection, dict), "previous output missing selection")
        require(isinstance(records, list) and records, "previous output missing records")
        return selection, records

    reference = top.get("t60_selection_path")
    require(isinstance(reference, str) and reference, "research T-5m input requires t60_selection_path")
    lock_path = ROOT / reference
    require(lock_path.is_file(), f"T-60m selection lock not found: {reference}")
    selection = load_json(lock_path)
    require(selection.get("evaluation_stage") == "T-60m", "referenced selection must be T-60m")
    prediction_ids = {item.get("prediction_id") for item in selection.get("ranking_trace", [])}
    records = [
        record for record in iter_records()
        if record.get("evaluation_stage") == "T-60m" and record.get("prediction_id") in prediction_ids
    ]
    require(records, "no matching T-60m history records found")
    return selection, records


def previous_map(records: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    output: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        key = (record.get("game_id"), record.get("candidate_side"))
        require(key[0] and key[1] in {"home", "away"}, "invalid previous candidate identity")
        current = output.get(key)
        current_time = (
            current.get("price_evaluated_at")
            or current.get("observed_at")
            or current.get("predicted_at")
        ) if current else None
        record_time = record.get("price_evaluated_at") or record.get("observed_at") or record.get("predicted_at")
        if current is None or parse_time(record_time, "previous record time") > parse_time(current_time, "previous record time"):
            output[key] = record
    return output


def build_t5_ids(
    candidate: dict[str, Any],
    top: dict[str, Any],
    manifest: dict[str, Any],
    previous: dict[str, Any],
    change_type: str,
    current_state: dict[str, Any],
) -> tuple[str, str]:
    if change_type == "price_only":
        prediction_id = previous["prediction_id"]
    else:
        basis = {
            "parent_prediction_id": previous["prediction_id"],
            "game_id": candidate["game_id"],
            "candidate_side": candidate["candidate_side"],
            "analysis_cutoff": top["analysis_cutoff"],
            "model_v": manifest["active"]["V"]["revision_id"],
            "model_g": manifest["active"]["G"]["revision_id"],
            "state_hash": canonical_hash(current_state, 32),
        }
        prediction_id = f"pred_{candidate['game_id']}_{candidate['candidate_side']}_{canonical_hash(basis, 12)}"
    price_basis = {
        "prediction_id": prediction_id,
        "stage": "T-5m",
        "bookmaker": top["target_bookmaker_id"],
        "market_id": top["market_id"],
        "target_odds": candidate["target_odds"],
        "opponent_odds": candidate["opponent_odds"],
        "observed_at": candidate["observed_at"],
    }
    price_id = f"price_{canonical_hash(price_basis, 16)}"
    return prediction_id, price_id


def make_record(
    item: dict[str, Any],
    top: dict[str, Any],
    manifest: dict[str, Any],
    coordination: dict[str, Any],
    main_id: str | None,
    priority_ids: set[str],
) -> dict[str, Any]:
    candidate = item["candidate"]
    previous = item["previous"]
    v = item["v"]
    g = item["g"]
    combined = item["coordination"]
    prediction_id = item["prediction_id"]
    price_id = item["price_evaluation_id"]
    is_main = prediction_id == main_id
    p_c, p_n, p_o = (candidate[key] for key in PROBABILITY_KEYS)
    no_vig = (1 / candidate["target_odds"]) / ((1 / candidate["target_odds"]) + (1 / candidate["opponent_odds"]))
    predicted_at = previous["predicted_at"] if item["change_type"] == "price_only" else top["analysis_cutoff"]
    prediction_cutoff = previous.get("analysis_cutoff") if item["change_type"] == "price_only" else top["analysis_cutoff"]
    state = item["prediction_state"]
    return {
        "prediction_id": prediction_id,
        "price_evaluation_id": price_id,
        "parent_prediction_id": previous["prediction_id"] if item["change_type"] == "fundamental_update" else None,
        "game_id": candidate["game_id"],
        "candidate_side": candidate["candidate_side"],
        "selection_team_id": candidate["selection_team_id"],
        "opponent_team_id": candidate["opponent_team_id"],
        "scheduled_at": candidate["scheduled_at"],
        "predicted_at": predicted_at,
        "analysis_cutoff": prediction_cutoff,
        "evaluation_cutoff": top["analysis_cutoff"],
        "price_evaluated_at": candidate["observed_at"],
        "evaluation_stage": "T-5m",
        "change_type": item["change_type"],
        "change_reasons": item["change_reasons"],
        "model_v": str(manifest["active"]["V"]["version"]),
        "model_v_revision": manifest["active"]["V"]["revision_id"],
        "model_g": str(manifest["active"]["G"]["version"]),
        "model_g_revision": manifest["active"]["G"]["revision_id"],
        "coordination_version": coordination["version"],
        "p_f": candidate.get("p_f"),
        "p_market_consensus": candidate.get("p_market_consensus"),
        "p_conservative": p_c,
        "p_neutral": p_n,
        "p_optimistic": p_o,
        "coverage_pct": candidate["coverage_pct"],
        "confidence": candidate["confidence"],
        "news_risk_level": candidate["news_risk_level"],
        "analysis_gate_status": candidate["analysis_gate_status"],
        "comparison_sources": candidate["comparison_sources"],
        "injury_confirmed": candidate["injury_confirmed"],
        "starters_confirmed": candidate["starters_confirmed"],
        "minutes_limit_confirmed": candidate["minutes_limit_confirmed"],
        "source_lineage_complete": candidate["source_lineage_complete"],
        "market_rules_complete": candidate["market_rules_complete"],
        "price_timestamp_valid": candidate["price_timestamp_valid"],
        "out_of_distribution": candidate["out_of_distribution"],
        "reverse_path_resolved": candidate["reverse_path_resolved"],
        "stale_warning": candidate["stale_warning"],
        "model_market_gap_pp": candidate["model_market_gap_pp"],
        "independent_evidence_count": candidate["independent_evidence_count"],
        "data_age_minutes": candidate["data_age_minutes"],
        "similar_case_stability_score": candidate.get("similar_case_stability_score"),
        "prediction_state": state,
        "prediction_state_hash": canonical_hash(state, 32),
        "target_bookmaker_id": top["target_bookmaker_id"],
        "market_id": top["market_id"],
        "target_odds": candidate["target_odds"],
        "opponent_odds": candidate["opponent_odds"],
        "includes_overtime": True,
        "observed_at": candidate["observed_at"],
        "break_even_probability": 1 / candidate["target_odds"],
        "no_vig_probability": no_vig,
        "ev_conservative": p_c * candidate["target_odds"] - 1,
        "ev_neutral": p_n * candidate["target_odds"] - 1,
        "ev_optimistic": p_o * candidate["target_odds"] - 1,
        "v_price_segment": v["segment"]["id"],
        "g_price_segment": g["segment"]["id"],
        "v_required_margin_pp": v["segment"].get("required_margin_pp"),
        "g_required_margin_pp": g["segment"].get("required_margin_pp"),
        "v_threshold_distance_pp": v["gap_pp"],
        "g_threshold_distance_pp": g["gap_pp"],
        "v_minimum_acceptable_odds": v["minimum_odds"],
        "g_minimum_acceptable_odds": g["minimum_odds"],
        "v_grade": v["grade"],
        "g_grade": g["grade"],
        "v_conclusion": v["conclusion"],
        "g_conclusion": g["conclusion"],
        "coordination_grade": combined["grade"],
        "coordination_label": combined["label"],
        "dual_side_conflict": item["dual_conflict"],
        "main_candidate": is_main,
        "main_status": "最終主要場次" if is_main else "不通過",
        "main_gate_results": item["gates"],
        "main_rejection_reasons": [key for key, passed in item["gates"].items() if not passed],
        "ui_priority_candidate": prediction_id in priority_ids,
        "t60_selection_id": top["t60_selection_id"],
        "t60_main_prediction_id": top.get("t60_main_prediction_id"),
        "data_version": top["data_version"],
        "config_hash": canonical_hash(
            {
                "manifest": manifest["registry_version"],
                "v": manifest["active"]["V"]["revision_id"],
                "g": manifest["active"]["G"]["revision_id"],
                "coordination": manifest["coordination"]["coordination_id"],
            },
            32,
        ),
        "formal_stake_fraction": 0,
        "won": None,
        "score": None,
        "closing_odds": None,
        "clv_odds": None,
        "clv_probability": None,
    }


def run(
    input_path: Path,
    *,
    dry_run: bool,
    previous_output: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    top = load_json(input_path)
    require(isinstance(top, dict), "input must be a JSON object")
    require(top.get("schema_version") == "1.0.0", "schema_version must be 1.0.0")
    require(top.get("evaluation_stage") == "T-5m", "this tool only accepts T-5m")
    require(top.get("data_mode") in {"fixture", "research"}, "data_mode must be fixture or research")
    if top["data_mode"] == "fixture" and not dry_run:
        raise ValueError("fixture data can only run with --dry-run")
    for key in (
        "slate_id", "slate_date", "analysis_cutoff", "target_bookmaker_id",
        "market_id", "data_version", "candidates",
    ):
        require(key in top, f"missing top-level field: {key}")
    require(isinstance(top["candidates"], list) and top["candidates"], "candidates must be a non-empty list")
    cutoff = parse_time(top["analysis_cutoff"], "analysis_cutoff")
    require(top["slate_date"] == cutoff.date().isoformat(), "slate_date must match analysis_cutoff local date")
    require(top.get("includes_overtime") is True, "includes_overtime must be true")
    top["lock_window_minutes"] = top.get("recheck_window_minutes", {"min": 0, "max": 15})

    selection, previous_records = load_previous(top, previous_output)
    require(selection.get("slate_id") == top["slate_id"], "T-5m slate_id must match T-60m lock")
    require(selection.get("slate_date") == top["slate_date"], "T-5m slate_date must match T-60m lock")
    t60_cutoff = parse_time(selection["analysis_cutoff"], "T-60m analysis_cutoff")
    require(t60_cutoff < cutoff, "T-5m cutoff must be after T-60m cutoff")
    top["t60_selection_id"] = selection["selection_id"]
    top["t60_main_prediction_id"] = selection.get("selected_prediction_id")

    manifest, v_config, g_config, coordination = load_active_configs()
    require(selection.get("model_v_revision") == manifest["active"]["V"]["revision_id"], "V revision changed after T-60m; open a new model run")
    require(selection.get("model_g_revision") == manifest["active"]["G"]["revision_id"], "G revision changed after T-60m; open a new model run")

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in top["candidates"]:
        validate_candidate(candidate, top, cutoff)
        grouped[candidate["game_id"]].append(candidate)
    for game_id, pair in grouped.items():
        validate_game_pair(game_id, pair)

    prior = previous_map(previous_records)
    current_keys = {(item["game_id"], item["candidate_side"]) for item in top["candidates"]}
    require(current_keys == set(prior), "T-5m candidate set must exactly match T-60m candidate set")

    game_g_grades: dict[str, list[str]] = {}
    for game_id, pair in grouped.items():
        game_g_grades[game_id] = [g_decision(candidate, g_config)["grade"] for candidate in pair]

    items: list[dict[str, Any]] = []
    for candidate in top["candidates"]:
        previous = prior[(candidate["game_id"], candidate["candidate_side"])]
        prior_state = state_from_record(previous)
        current_state = prediction_state(candidate)
        changes = state_changes(prior_state, current_state)
        declared = candidate.get("fundamental_change_declared")
        if declared is False and changes:
            raise ValueError(f"{candidate['game_id']} {candidate['candidate_side']} declared price-only but changed: {', '.join(changes)}")
        if declared is True and not changes:
            changes = ["declared_fundamental_update"]
        change_type = "fundamental_update" if changes else "price_only"
        v = v_decision(candidate, v_config)
        g = g_decision(candidate, g_config)
        dual_conflict = sorted(game_g_grades[candidate["game_id"]]) == ["ㄅ", "ㄅ"]
        gates = gate_results(candidate, g_config, g, dual_conflict)
        combined = coordination_decision(v, g, dual_conflict, coordination)
        prediction_id, price_id = build_t5_ids(candidate, top, manifest, previous, change_type, current_state)
        items.append(
            {
                "candidate": candidate,
                "previous": previous,
                "prediction_state": current_state,
                "change_type": change_type,
                "change_reasons": changes,
                "v": v,
                "g": g,
                "coordination": combined,
                "dual_conflict": dual_conflict,
                "gates": gates,
                "prediction_id": prediction_id,
                "price_evaluation_id": price_id,
            }
        )

    qualified = [item for item in items if item["g"]["grade"] == "ㄅ" and not item["dual_conflict"]]
    main_eligible = [item for item in qualified if all(item["gates"].values())]
    main_eligible.sort(key=ranking_key)
    selected = main_eligible[0] if main_eligible else None
    selected_prediction_id = selected["prediction_id"] if selected else None

    priority_limit = coordination.get("ui_policy", {}).get("priority_display_max", 2)
    priority_items = [item for item in sorted(qualified, key=ranking_key) if item is not selected][:max(0, priority_limit)]
    priority_ids = {item["prediction_id"] for item in priority_items}
    records = [make_record(item, top, manifest, coordination, selected_prediction_id, priority_ids) for item in items]

    selection_id = f"sel_{re.sub(r'[^A-Za-z0-9_-]+', '-', top['slate_id'])}_T5_{canonical_hash({'cutoff': top['analysis_cutoff'], 'data': top['data_version']}, 12)}"
    trace = [
        {
            "prediction_id": record["prediction_id"],
            "parent_prediction_id": record["parent_prediction_id"],
            "price_evaluation_id": record["price_evaluation_id"],
            "game_id": record["game_id"],
            "candidate_side": record["candidate_side"],
            "selection_team_id": record["selection_team_id"],
            "change_type": record["change_type"],
            "change_reasons": record["change_reasons"],
            "v_grade": record["v_grade"],
            "g_grade": record["g_grade"],
            "g_threshold_distance_pp": record["g_threshold_distance_pp"],
            "gate_results": record["main_gate_results"],
            "rejection_reasons": record["main_rejection_reasons"],
            "main_candidate": record["main_candidate"],
            "ui_priority_candidate": record["ui_priority_candidate"],
        }
        for record in records
    ]
    selection_payload = {
        "schema_version": "1.0.0",
        "selection_id": selection_id,
        "slate_id": top["slate_id"],
        "slate_date": top["slate_date"],
        "analysis_cutoff": top["analysis_cutoff"],
        "evaluation_stage": "T-5m",
        "t60_selection_id": selection["selection_id"],
        "t60_selected_prediction_id": selection.get("selected_prediction_id"),
        "model_v_revision": manifest["active"]["V"]["revision_id"],
        "model_g_revision": manifest["active"]["G"]["revision_id"],
        "coordination_id": coordination["coordination_id"],
        "data_version": top["data_version"],
        "candidate_count": len(records),
        "price_only_count": sum(record["change_type"] == "price_only" for record in records),
        "fundamental_update_count": sum(record["change_type"] == "fundamental_update" for record in records),
        "eligible_prediction_ids": [record["prediction_id"] for record in records if record["g_grade"] == "ㄅ" and not record["dual_side_conflict"]],
        "selected_prediction_id": selected_prediction_id,
        "main_status": "最終主要場次" if selected_prediction_id else "本批沒有通過全部硬閘門的最終主要場次",
        "main_changed_from_t60": selected_prediction_id != selection.get("selected_prediction_id"),
        "priority_prediction_ids": sorted(priority_ids),
        "ranking_trace": sorted(trace, key=lambda item: (not item["main_candidate"], not item["ui_priority_candidate"], item["game_id"], item["candidate_side"])),
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps({"selection": selection_payload, "records": records}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if dry_run:
        append_many(records, validate_only=True)
        print(json.dumps(selection_payload, ensure_ascii=False, indent=2))
        return selection_payload

    day_dir = LOCKS_DIR / top["slate_date"]
    day_dir.mkdir(parents=True, exist_ok=True)
    lock_path = day_dir / f"{selection_id}.json"
    if lock_path.exists():
        raise ValueError(f"selection lock already exists: {lock_path.relative_to(ROOT)}")
    temp = lock_path.with_suffix(".json.tmp")
    temp.write_text(json.dumps(selection_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        append_many(records)
        os.replace(temp, lock_path)
        rebuild_locks_index()
    finally:
        if temp.exists():
            temp.unlink()
    print(f"Rechecked {len(records)} candidate records; final_main={selected_prediction_id or 'none'}")
    return selection_payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="T-5m slate-wave JSON")
    parser.add_argument("--previous-output", type=Path, help="T-60m dry-run output JSON for fixture testing")
    parser.add_argument("--dry-run", action="store_true", help="validate and calculate without writing")
    parser.add_argument("--output", type=Path, help="optional calculation output JSON")
    args = parser.parse_args()
    run(args.input, dry_run=args.dry_run, previous_output=args.previous_output, output_path=args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
