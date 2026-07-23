#!/usr/bin/env python3
"""Shared G1.2.0 EV-primary decision and season activation resolver."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

TARGET_SEASON = "2026-27"
TARGET_COMPETITION = "regular_season"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def segment_contains(segment: dict[str, Any], odds: float) -> bool:
    above = odds > segment["min"] if segment.get("min_inclusive") is False else odds >= segment["min"]
    maximum = segment.get("max")
    below = True if maximum is None else (odds < maximum if segment.get("max_inclusive") is False else odds <= maximum)
    return above and below


def price_segment(config: dict[str, Any], odds: float) -> dict[str, Any]:
    for segment in config["price_bands"]:
        if segment_contains(segment, odds):
            return segment
    return {
        "id": "outside",
        "label": "範圍外",
        "required_margin_pp": None,
        "eligible": False,
        "maximum_conclusion": "只記錄",
    }


def ev_primary_decision(candidate: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    segment = price_segment(config, float(candidate["target_odds"]))
    p_c = candidate.get("p_conservative")
    odds = float(candidate["target_odds"])
    policy = config["ev_policy"]
    insufficient = (
        candidate.get("analysis_gate_status") == "資料不足"
        or candidate.get("confidence") in {"資料不足", "不足"}
        or int(candidate.get("news_risk_level", candidate.get("newsRisk", 0))) >= 3
        or p_c is None
    )
    if insufficient:
        return {
            "grade": "資料不足", "conclusion": "資料不足", "segment": segment,
            "edge_pp": None, "gap_pp": None, "minimum_odds": None,
            "decision_metric": "conservative_ev", "ev_conservative": None,
            "ev_candidate": False, "pp_guard_pass": False,
            "pp_guard_min_pp": float(policy["pp_guard_min"]),
            "pp_guard_surplus_pp": None, "grade_threshold_ev": None,
            "selection_surplus_pp": None, "minimum_candidate_odds": None,
        }

    p_c = float(p_c)
    break_even = 1 / odds
    edge_pp = (p_c - break_even) * 100
    ev = p_c * odds - 1
    guard = float(policy["pp_guard_min"])
    guard_pass = edge_pp + 1e-12 >= guard
    candidate_min = float(policy["candidate_min_ev"])
    p_min = float(policy["grade_p_min_ev"])
    b_min = float(policy["grade_b_min_ev"])

    if ev <= 0:
        grade, conclusion, threshold = "不支持", "模型不支持", 0.0
    elif not guard_pass:
        grade, conclusion, threshold = "ㄆ", "觀察・PP 安全線未通過", candidate_min
    elif ev + 1e-12 < candidate_min:
        grade, conclusion, threshold = "ㄆ", "觀察・EV 未達 5%", candidate_min
    elif ev + 1e-12 < p_min:
        grade, conclusion, threshold = "ㄇ", "ㄇ級・最低正 EV", candidate_min
    elif ev + 1e-12 < b_min:
        grade, conclusion, threshold = "ㄆ", "ㄆ級・EV 觀察候選", p_min
    else:
        grade, conclusion, threshold = "ㄅ", "ㄅ級・EV 核心候選", b_min

    risk = int(candidate.get("news_risk_level", candidate.get("newsRisk", 0)))
    confidence = candidate.get("confidence")
    if grade == "ㄅ" and (risk == 2 or confidence == "低"):
        grade, conclusion, threshold = "ㄆ", "ㄆ級・風險降級", p_min

    if grade not in {"資料不足", "不支持"}:
        if segment.get("required_margin_pp") is None:
            grade, conclusion = "ㄆ", segment.get("maximum_conclusion", "只記錄")
        elif not segment.get("eligible", False) and grade == "ㄅ":
            grade, conclusion = "ㄆ", segment.get("maximum_conclusion", "ㄆ級・延伸研究")

    ev_candidate = ev + 1e-12 >= candidate_min and guard_pass and bool(segment.get("eligible"))
    selection_surplus_pp = (ev - b_min) * 100 if grade == "ㄅ" else (ev - threshold) * 100
    minimum_candidate_odds = (1 + candidate_min) / p_c if p_c > 0 else None
    minimum_grade_odds = (1 + threshold) / p_c if p_c > 0 and threshold > 0 else minimum_candidate_odds
    return {
        "grade": grade,
        "conclusion": conclusion,
        "segment": segment,
        "edge_pp": edge_pp,
        "gap_pp": selection_surplus_pp,
        "minimum_odds": minimum_grade_odds,
        "decision_metric": "conservative_ev",
        "ev_conservative": ev,
        "ev_candidate": ev_candidate,
        "pp_guard_pass": guard_pass,
        "pp_guard_min_pp": guard,
        "pp_guard_surplus_pp": edge_pp - guard,
        "grade_threshold_ev": threshold,
        "selection_surplus_pp": selection_surplus_pp,
        "minimum_candidate_odds": minimum_candidate_odds,
    }


def activation_requested(top: dict[str, Any], manifest: dict[str, Any]) -> bool:
    scheduled = manifest.get("scheduled_next", {}).get("G")
    if not scheduled or scheduled.get("activation_status") != "USER_APPROVED_FOR_2026_27_REGULAR_SEASON":
        return False
    if top.get("g_execution_mode") == "active_only":
        return False
    return top.get("season") == TARGET_SEASON and top.get("competition_type") == TARGET_COMPETITION


def resolve_execution(root: Path, manifest_path: Path, top: dict[str, Any]) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    active_v_entry = manifest["active"]["V"]
    active_g_entry = manifest["active"]["G"]
    active_coord_entry = manifest["coordination"]
    active_v = load_json(root / active_v_entry["config"])
    active_g = load_json(root / active_g_entry["config"])
    active_coord = load_json(root / active_coord_entry["config"])

    scheduled_root = manifest.get("scheduled_next", {})
    scheduled_g_entry = scheduled_root.get("G")
    scheduled_coord_entry = scheduled_root.get("coordination")
    scheduled_g = load_json(root / scheduled_g_entry["config"]) if scheduled_g_entry else None
    scheduled_coord = load_json(root / scheduled_coord_entry["config"]) if scheduled_coord_entry else None
    activated = activation_requested(top, manifest)

    if activated:
        if scheduled_g is None or scheduled_coord is None:
            raise ValueError("scheduled G1.2.0 or coordination config is missing")
        primary_entry, primary_g = scheduled_g_entry, scheduled_g
        coordination_entry, coordination = scheduled_coord_entry, scheduled_coord
        parallel_entry, parallel_g = active_g_entry, active_g
        parallel_role = "control_shadow"
        status = "G1_2_0_PRIMARY_2026_27"
    else:
        primary_entry, primary_g = active_g_entry, active_g
        coordination_entry, coordination = active_coord_entry, active_coord
        parallel_entry, parallel_g = scheduled_g_entry, scheduled_g
        parallel_role = "scheduled_shadow" if scheduled_g else None
        status = "G1_1_1_PRIMARY_G1_2_0_SCHEDULED_SHADOW" if scheduled_g else "ACTIVE_ONLY"

    execution_manifest = copy.deepcopy(manifest)
    execution_manifest["active"]["G"] = copy.deepcopy(primary_entry)
    execution_manifest["coordination"] = copy.deepcopy(coordination_entry)
    return {
        "manifest": execution_manifest,
        "repository_manifest": manifest,
        "v_config": active_v,
        "primary_g_config": primary_g,
        "primary_g_entry": primary_entry,
        "coordination": coordination,
        "coordination_entry": coordination_entry,
        "parallel_g_config": parallel_g,
        "parallel_g_entry": parallel_entry,
        "parallel_role": parallel_role,
        "activated": activated,
        "execution_status": status,
    }
