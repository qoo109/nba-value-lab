#!/usr/bin/env python3
"""Shared G1.1 policy: target two official main selections, hard cap three."""

from __future__ import annotations

from typing import Any


def record_rank(record: dict[str, Any]) -> tuple[Any, ...]:
    return (
        float(record.get("data_age_minutes") or 9999),
        -int(bool(record.get("injury_confirmed") and record.get("starters_confirmed") and record.get("minutes_limit_confirmed"))),
        (float(record.get("p_optimistic") or 0) - float(record.get("p_conservative") or 0)) * 100,
        -float(record.get("g_threshold_distance_pp") if record.get("g_threshold_distance_pp") is not None else -999),
        float(record.get("model_market_gap_pp") or 999),
        -int(bool(record.get("reverse_path_resolved"))),
        -float(record.get("similar_case_stability_score") or 0),
        str(record.get("game_id") or ""),
        str(record.get("candidate_side") or ""),
    )


def base_eligible(record: dict[str, Any]) -> bool:
    gates = record.get("main_gate_results") or {}
    return (
        record.get("g_grade") == "ㄅ"
        and not record.get("dual_side_conflict")
        and bool(gates)
        and all(bool(value) for value in gates.values())
    )


def third_slot_eligible(record: dict[str, Any], policy: dict[str, Any]) -> bool:
    if not policy.get("enabled"):
        return False
    width = (float(record["p_optimistic"]) - float(record["p_conservative"])) * 100
    return (
        base_eligible(record)
        and float(record.get("coverage_pct") or 0) >= float(policy.get("coverage_min_pct", 100))
        and width <= float(policy.get("interval_width_max_pp", 0)) + 1e-9
        and int(record.get("comparison_sources") or 0) >= int(policy.get("comparison_sources_min", 999))
        and float(record.get("g_threshold_distance_pp") or -999) >= float(policy.get("threshold_buffer_min_pp", 999))
        and int(record.get("news_risk_level") or 0) <= int(policy.get("news_risk_max", -1))
        and record.get("confidence") == policy.get("confidence_required", "高")
    )


def choose_main_records(records: list[dict[str, Any]], g_config: dict[str, Any]) -> list[dict[str, Any]]:
    selection = g_config.get("selection", {})
    target = max(0, min(3, int(selection.get("official_main_target", 2))))
    maximum = max(target, min(3, int(selection.get("official_main_max", 3))))
    eligible = sorted((record for record in records if base_eligible(record)), key=record_rank)

    selected = eligible[:target]
    if len(selected) >= target and len(selected) < maximum:
        selected_ids = {record["prediction_id"] for record in selected}
        strict = [
            record for record in eligible
            if record["prediction_id"] not in selected_ids
            and third_slot_eligible(record, selection.get("third_slot_policy", {}))
        ]
        selected.extend(strict[: maximum - len(selected)])
    return selected


def priority_records(records: list[dict[str, Any]], selected: list[dict[str, Any]], g_config: dict[str, Any]) -> list[dict[str, Any]]:
    selected_ids = {record["prediction_id"] for record in selected}
    limit = max(0, int(g_config.get("selection", {}).get("ui_priority_candidates_max", 2)))
    qualified = [
        record for record in sorted(records, key=record_rank)
        if record.get("g_grade") == "ㄅ"
        and not record.get("dual_side_conflict")
        and record.get("prediction_id") not in selected_ids
    ]
    return qualified[:limit]


def apply_multi_main(records: list[dict[str, Any]], selection_payload: dict[str, Any], g_config: dict[str, Any], stage: str) -> dict[str, Any]:
    selected = choose_main_records(records, g_config)
    selected_ids = [record["prediction_id"] for record in selected]
    priority = priority_records(records, selected, g_config)
    priority_ids = {record["prediction_id"] for record in priority}

    count = len(selected_ids)
    for record in records:
        record["main_candidate"] = record["prediction_id"] in selected_ids
        record["main_rank"] = selected_ids.index(record["prediction_id"]) + 1 if record["main_candidate"] else None
        if record["main_candidate"]:
            label = "最終主要場次" if stage == "T-5m" else "主要場次待 T-5m 確認"
            record["main_status"] = f"{label} {record['main_rank']}/{count}"
        else:
            record["main_status"] = "不通過"
        record["ui_priority_candidate"] = record["prediction_id"] in priority_ids

    selection = g_config.get("selection", {})
    selection_payload["selected_prediction_ids"] = selected_ids
    selection_payload["selected_prediction_id"] = selected_ids[0] if selected_ids else None
    selection_payload["selected_count"] = count
    selection_payload["target_main_count"] = int(selection.get("official_main_target", 2))
    selection_payload["maximum_main_count"] = int(selection.get("official_main_max", 3))
    selection_payload["priority_prediction_ids"] = sorted(priority_ids)
    if count:
        label = "最終主要場次" if stage == "T-5m" else "主要場次待 T-5m 確認"
        selection_payload["main_status"] = f"{label}共 {count} 場"
    else:
        selection_payload["main_status"] = "本批沒有通過全部硬閘門的主要場次"
    return selection_payload
