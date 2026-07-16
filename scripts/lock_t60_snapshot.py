#!/usr/bin/env python3
"""Lock one T-60m NBA slate wave into compact append-only research records.

The input contains both sides of every game. The script validates point-in-time
fields, complementary probabilities, same-book two-sided prices and G1 gates,
then writes:

- compact price-evaluation records to data/history/YYYY-MM.jsonl
- one immutable selection trace to data/locks/YYYY-MM-DD/
- data/locks/index.json for the website

Fixture inputs are dry-run only and can never enter formal history.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from append_research_record import append_many

ROOT = Path(__file__).resolve().parents[1]
MODELS_MANIFEST = ROOT / "models" / "manifest.json"
LOCKS_DIR = ROOT / "data" / "locks"
LOCKS_INDEX = LOCKS_DIR / "index.json"
GRADE_ORDER = {"資料不足": 0, "不支持": 1, "ㄇ": 2, "ㄆ": 3, "ㄅ": 4}
VALID_CONFIDENCE = {"高", "中", "低", "資料不足"}
VALID_ANALYSIS_GATE = {"可分析", "條件式可分析", "資料不足"}
PROBABILITY_KEYS = ("p_conservative", "p_neutral", "p_optimistic")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_hash(payload: Any, length: int = 16) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:length]


def parse_time(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"{field} must be ISO 8601") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone")
    return parsed


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def segment_contains(segment: dict[str, Any], odds: float) -> bool:
    above = odds > segment["min"] if segment.get("min_inclusive") is False else odds >= segment["min"]
    maximum = segment.get("max")
    below = True if maximum is None else (odds < maximum if segment.get("max_inclusive") is False else odds <= maximum)
    return above and below


def find_segment(segments: list[dict[str, Any]], odds: float, outside_label: str) -> dict[str, Any]:
    for segment in segments:
        if segment_contains(segment, odds):
            return segment
    return {
        "id": "outside",
        "label": outside_label,
        "required_margin_pp": None,
        "eligible": False,
        "eligible_b": False,
        "maximum_conclusion": outside_label,
    }


def base_grade(candidate: dict[str, Any], margin_pp: float | None, watch_gap_min_pp: float) -> tuple[str, float | None, float | None]:
    if (
        candidate["analysis_gate_status"] == "資料不足"
        or candidate["confidence"] == "資料不足"
        or candidate["news_risk_level"] >= 3
    ):
        return "資料不足", None, None

    p_c = candidate["p_conservative"]
    odds = candidate["target_odds"]
    break_even = 1 / odds
    edge_pp = (p_c - break_even) * 100
    if edge_pp < 0:
        return "不支持", edge_pp, None if margin_pp is None else edge_pp - margin_pp
    if margin_pp is None:
        return "ㄆ", edge_pp, None
    gap_pp = edge_pp - margin_pp
    if gap_pp >= 0:
        grade = "ㄅ"
    elif gap_pp >= watch_gap_min_pp:
        grade = "ㄆ"
    else:
        grade = "ㄇ"
    if candidate["news_risk_level"] == 2 or candidate["confidence"] == "低":
        if grade == "ㄅ":
            grade = "ㄆ"
    return grade, edge_pp, gap_pp


def v_decision(candidate: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    segment = find_segment(config["price_policy"]["price_segments"], candidate["target_odds"], config["price_policy"].get("outside_conclusion", "範圍外"))
    grade, edge_pp, gap_pp = base_grade(candidate, segment.get("required_margin_pp"), config["grading"].get("watch_gap_min_pp", -3))
    conclusion = grade
    if grade not in {"資料不足", "不支持"}:
        if segment["id"] == "extreme_low_excluded":
            grade, conclusion = "ㄆ", "排除・極低價格"
        elif segment["id"] == "separate_calibration":
            if grade == "ㄇ":
                conclusion = "ㄇ級・價格合理"
            else:
                grade, conclusion = "ㄆ", "另行校準"
        elif segment["id"] == "outside":
            grade, conclusion = "ㄆ", "範圍外"
        elif not segment.get("eligible_b", False) and grade in {"ㄅ", "ㄆ"}:
            grade, conclusion = "ㄆ", segment.get("maximum_conclusion", "ㄆ級・延伸研究")
        else:
            conclusion = {"ㄅ": "ㄅ級・研究候選", "ㄆ": "ㄆ級・條件觀察", "ㄇ": "ㄇ級・價格合理"}.get(grade, grade)
    minimum_odds = None
    margin_pp = segment.get("required_margin_pp")
    if margin_pp is not None and candidate["p_conservative"] > margin_pp / 100:
        minimum_odds = 1 / (candidate["p_conservative"] - margin_pp / 100)
    return {
        "grade": grade,
        "conclusion": conclusion,
        "segment": segment,
        "edge_pp": edge_pp,
        "gap_pp": gap_pp,
        "minimum_odds": minimum_odds,
    }


def g_decision(candidate: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    segment = find_segment(config["price_bands"], candidate["target_odds"], "只記錄")
    grade, edge_pp, gap_pp = base_grade(candidate, segment.get("required_margin_pp"), config["grading"].get("watch_gap_min_pp", -3))
    conclusion = grade
    if grade not in {"資料不足", "不支持"}:
        if segment.get("required_margin_pp") is None:
            grade, conclusion = "ㄆ", segment.get("maximum_conclusion", "只記錄")
        elif not segment.get("eligible", False) and grade in {"ㄅ", "ㄆ"}:
            grade, conclusion = "ㄆ", segment.get("maximum_conclusion", "ㄆ級・延伸研究")
        else:
            conclusion = {"ㄅ": "ㄅ級・研究候選", "ㄆ": "ㄆ級・條件觀察", "ㄇ": "ㄇ級・價格合理"}.get(grade, grade)
    minimum_odds = None
    margin_pp = segment.get("required_margin_pp")
    if margin_pp is not None and candidate["p_conservative"] > margin_pp / 100:
        minimum_odds = 1 / (candidate["p_conservative"] - margin_pp / 100)
    return {
        "grade": grade,
        "conclusion": conclusion,
        "segment": segment,
        "edge_pp": edge_pp,
        "gap_pp": gap_pp,
        "minimum_odds": minimum_odds,
    }


def load_active_configs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    manifest = load_json(MODELS_MANIFEST)
    v_entry = manifest["active"]["V"]
    g_entry = manifest["active"]["G"]
    coordination_entry = manifest["coordination"]
    v_config = load_json(ROOT / v_entry["config"])
    g_config = load_json(ROOT / g_entry["config"])
    coordination = load_json(ROOT / coordination_entry["config"])
    require(str(v_config["version"]) == "3.1", "active V model must be 3.1")
    require(str(g_config["version"]) == "1.0", "active G model must be 1.0")
    return manifest, v_config, g_config, coordination


def validate_candidate(candidate: dict[str, Any], top: dict[str, Any], cutoff: datetime) -> None:
    required = {
        "game_id", "scheduled_at", "candidate_side", "selection_team_id", "opponent_team_id",
        "target_odds", "opponent_odds", "observed_at", "p_conservative", "p_neutral",
        "p_optimistic", "coverage_pct", "confidence", "news_risk_level",
        "analysis_gate_status", "comparison_sources", "injury_confirmed",
        "starters_confirmed", "minutes_limit_confirmed", "source_lineage_complete",
        "market_rules_complete", "price_timestamp_valid", "out_of_distribution",
        "reverse_path_resolved", "stale_warning", "model_market_gap_pp",
        "independent_evidence_count", "data_age_minutes",
    }
    missing = sorted(required - candidate.keys())
    require(not missing, f"{candidate.get('game_id', 'candidate')} missing: {', '.join(missing)}")
    require(candidate["candidate_side"] in {"home", "away"}, "candidate_side must be home or away")
    require(candidate["selection_team_id"] != candidate["opponent_team_id"], "selection and opponent teams must differ")
    for key in ("target_odds", "opponent_odds"):
        require(isinstance(candidate[key], (int, float)) and candidate[key] > 1, f"{key} must be > 1")
    for key in PROBABILITY_KEYS:
        require(isinstance(candidate[key], (int, float)) and 0 <= candidate[key] <= 1, f"{key} must be 0..1")
    require(candidate["p_conservative"] <= candidate["p_neutral"] <= candidate["p_optimistic"], "P_C <= P_N <= P_O required")
    if candidate.get("p_f") is not None:
        require(0 <= candidate["p_f"] <= 1, "p_f must be 0..1")
    if candidate.get("p_market_consensus") is not None:
        require(0 <= candidate["p_market_consensus"] <= 1, "p_market_consensus must be 0..1")
    require(0 <= candidate["coverage_pct"] <= 100, "coverage_pct must be 0..100")
    require(candidate["confidence"] in VALID_CONFIDENCE, "invalid confidence")
    require(isinstance(candidate["news_risk_level"], int) and 0 <= candidate["news_risk_level"] <= 3, "news_risk_level must be 0..3")
    require(candidate["analysis_gate_status"] in VALID_ANALYSIS_GATE, "invalid analysis_gate_status")
    require(isinstance(candidate["comparison_sources"], int) and candidate["comparison_sources"] >= 0, "comparison_sources must be non-negative")
    require(isinstance(candidate["independent_evidence_count"], int) and candidate["independent_evidence_count"] >= 0, "independent_evidence_count must be non-negative")
    require(isinstance(candidate["data_age_minutes"], (int, float)) and candidate["data_age_minutes"] >= 0, "data_age_minutes must be non-negative")
    for key in (
        "injury_confirmed", "starters_confirmed", "minutes_limit_confirmed",
        "source_lineage_complete", "market_rules_complete", "price_timestamp_valid",
        "out_of_distribution", "reverse_path_resolved", "stale_warning",
    ):
        require(isinstance(candidate[key], bool), f"{key} must be boolean")

    scheduled = parse_time(candidate["scheduled_at"], "scheduled_at")
    observed = parse_time(candidate["observed_at"], "observed_at")
    require(cutoff < scheduled, "analysis_cutoff must be before scheduled_at")
    require(observed <= cutoff, "observed_at cannot be after analysis_cutoff")
    minutes_to_tip = (scheduled - cutoff).total_seconds() / 60
    window = top.get("lock_window_minutes", {"min": 30, "max": 90})
    require(window["min"] <= minutes_to_tip <= window["max"], f"T-60m lock must be {window['min']}..{window['max']} minutes before tip; got {minutes_to_tip:.1f}")
    require(candidate.get("includes_overtime", top.get("includes_overtime")) is True, "market must include overtime")


def validate_game_pair(game_id: str, pair: list[dict[str, Any]], tolerance: float = 1e-6) -> None:
    require(len(pair) == 2, f"{game_id} must contain exactly two candidate sides")
    sides = {item["candidate_side"] for item in pair}
    require(sides == {"home", "away"}, f"{game_id} must contain home and away candidates")
    home = next(item for item in pair if item["candidate_side"] == "home")
    away = next(item for item in pair if item["candidate_side"] == "away")
    require(home["selection_team_id"] == away["opponent_team_id"], f"{game_id} team mapping mismatch")
    require(away["selection_team_id"] == home["opponent_team_id"], f"{game_id} team mapping mismatch")
    require(abs(home["target_odds"] - away["opponent_odds"]) <= tolerance, f"{game_id} home odds are not same-snapshot complements")
    require(abs(away["target_odds"] - home["opponent_odds"]) <= tolerance, f"{game_id} away odds are not same-snapshot complements")
    require(home["observed_at"] == away["observed_at"], f"{game_id} two-sided odds must share observed_at")
    require(home["scheduled_at"] == away["scheduled_at"], f"{game_id} scheduled_at mismatch")
    require(abs(home["p_neutral"] + away["p_neutral"] - 1) <= tolerance, f"{game_id} neutral probabilities must sum to 1")
    require(abs(home["p_conservative"] + away["p_optimistic"] - 1) <= tolerance, f"{game_id} home P_C + away P_O must sum to 1")
    require(abs(home["p_optimistic"] + away["p_conservative"] - 1) <= tolerance, f"{game_id} home P_O + away P_C must sum to 1")
    if home.get("p_market_consensus") is not None and away.get("p_market_consensus") is not None:
        require(abs(home["p_market_consensus"] + away["p_market_consensus"] - 1) <= tolerance, f"{game_id} market consensus must sum to 1")


def gate_results(candidate: dict[str, Any], g: dict[str, Any], decision: dict[str, Any], dual_conflict: bool) -> dict[str, bool]:
    gate = g["core_gate"]
    gap_explained = candidate["model_market_gap_pp"] <= gate["model_market_gap_max_pp"] or candidate["independent_evidence_count"] >= gate["independent_evidence_min_if_gap_exceeded"]
    return {
        "g_grade_b": decision["grade"] == "ㄅ",
        "no_dual_side_conflict": not dual_conflict,
        "confidence_high": candidate["confidence"] == gate["confidence_required"],
        "coverage": candidate["coverage_pct"] >= gate["coverage_min_pct"],
        "injury_rotation_confirmed": candidate["injury_confirmed"] and candidate["starters_confirmed"] and candidate["minutes_limit_confirmed"],
        "interval_width": (candidate["p_optimistic"] - candidate["p_conservative"]) * 100 <= gate["interval_width_max_pp"] + 1e-9,
        "comparison_sources": candidate["comparison_sources"] >= gate["comparison_sources_min"],
        "main_surplus": decision["gap_pp"] is not None and decision["gap_pp"] >= gate["threshold_buffer_min_pp"],
        "model_market_gap_explained": gap_explained,
        "not_out_of_distribution": not candidate["out_of_distribution"],
        "reverse_path_resolved": candidate["reverse_path_resolved"],
        "not_stale": not candidate["stale_warning"],
        "source_lineage_complete": candidate["source_lineage_complete"],
        "market_rules_complete": candidate["market_rules_complete"],
        "price_timestamp_valid": candidate["price_timestamp_valid"],
    }


def ranking_key(item: dict[str, Any]) -> tuple[Any, ...]:
    candidate = item["candidate"]
    g_dec = item["g"]
    return (
        candidate["data_age_minutes"],
        -int(candidate["injury_confirmed"] and candidate["starters_confirmed"] and candidate["minutes_limit_confirmed"]),
        (candidate["p_optimistic"] - candidate["p_conservative"]) * 100,
        -(g_dec["gap_pp"] if g_dec["gap_pp"] is not None else -999),
        candidate["model_market_gap_pp"],
        -int(candidate["reverse_path_resolved"]),
        -float(candidate.get("similar_case_stability_score", 0)),
        candidate["game_id"],
        candidate["candidate_side"],
    )


def coordination_label(v: dict[str, Any], g: dict[str, Any], dual_conflict: bool) -> str:
    if dual_conflict:
        return "雙邊價值衝突・停止主要場次"
    if v["segment"]["id"] == "core" and v["grade"] == "ㄅ" and g["grade"] == "ㄅ":
        return "V3.1 × G1 雙引擎通過"
    if g["grade"] == "ㄅ":
        return "G1 通過・V3.1 獨立顯示"
    if v["grade"] == "ㄅ":
        return "V3.1 通過・G1 Gate 未通過"
    if g["grade"] == "資料不足" or v["grade"] == "資料不足":
        return "資料不足"
    if g["grade"] == "不支持" and v["grade"] == "不支持":
        return "雙引擎皆不支持"
    return f"V：{v['conclusion']}・G：{g['conclusion']}"


def build_ids(candidate: dict[str, Any], top: dict[str, Any], manifest: dict[str, Any]) -> tuple[str, str]:
    prediction_basis = {
        "game_id": candidate["game_id"],
        "candidate_side": candidate["candidate_side"],
        "analysis_cutoff": top["analysis_cutoff"],
        "model_v": manifest["active"]["V"]["revision_id"],
        "model_g": manifest["active"]["G"]["revision_id"],
        "data_version": top["data_version"],
        "probabilities": {key: candidate[key] for key in PROBABILITY_KEYS},
        "p_f": candidate.get("p_f"),
        "p_market_consensus": candidate.get("p_market_consensus"),
        "coverage_pct": candidate["coverage_pct"],
        "confidence": candidate["confidence"],
        "news_risk_level": candidate["news_risk_level"],
    }
    prediction_id = f"pred_{candidate['game_id']}_{candidate['candidate_side']}_{canonical_hash(prediction_basis, 12)}"
    price_basis = {
        "prediction_id": prediction_id,
        "bookmaker": top["target_bookmaker_id"],
        "market_id": top["market_id"],
        "target_odds": candidate["target_odds"],
        "opponent_odds": candidate["opponent_odds"],
        "observed_at": candidate["observed_at"],
    }
    price_id = f"price_{canonical_hash(price_basis, 16)}"
    return prediction_id, price_id


def make_record(item: dict[str, Any], top: dict[str, Any], manifest: dict[str, Any], coordination: dict[str, Any], main_id: str | None, priority_ids: set[str]) -> dict[str, Any]:
    candidate = item["candidate"]
    v = item["v"]
    g = item["g"]
    prediction_id, price_id = build_ids(candidate, top, manifest)
    is_main = prediction_id == main_id
    no_vig = (1 / candidate["target_odds"]) / ((1 / candidate["target_odds"]) + (1 / candidate["opponent_odds"]))
    p_c, p_n, p_o = (candidate[key] for key in PROBABILITY_KEYS)
    main_status = "主要場次待 T-5m 確認" if is_main else "不通過"
    return {
        "prediction_id": prediction_id,
        "price_evaluation_id": price_id,
        "game_id": candidate["game_id"],
        "candidate_side": candidate["candidate_side"],
        "selection_team_id": candidate["selection_team_id"],
        "opponent_team_id": candidate["opponent_team_id"],
        "predicted_at": top["analysis_cutoff"],
        "analysis_cutoff": top["analysis_cutoff"],
        "evaluation_stage": "T-60m",
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
        "coordination_label": coordination_label(v, g, item["dual_conflict"]),
        "dual_side_conflict": item["dual_conflict"],
        "main_candidate": is_main,
        "main_status": main_status,
        "main_gate_results": item["gates"],
        "main_rejection_reasons": [key for key, passed in item["gates"].items() if not passed],
        "ui_priority_candidate": prediction_id in priority_ids,
        "data_version": top["data_version"],
        "config_hash": canonical_hash({
            "manifest": manifest["registry_version"],
            "v": manifest["active"]["V"]["revision_id"],
            "g": manifest["active"]["G"]["revision_id"],
            "coordination": manifest["coordination"]["coordination_id"],
        }, 32),
        "formal_stake_fraction": 0,
        "won": None,
        "score": None,
        "closing_odds": None,
        "clv_odds": None,
        "clv_probability": None,
    }


def rebuild_locks_index() -> None:
    records: list[dict[str, Any]] = []
    if LOCKS_DIR.exists():
        for path in sorted(LOCKS_DIR.glob("????-??-??/*.json")):
            try:
                payload = load_json(path)
            except (OSError, json.JSONDecodeError):
                continue
            records.append({
                "selection_id": payload.get("selection_id"),
                "slate_id": payload.get("slate_id"),
                "slate_date": payload.get("slate_date"),
                "analysis_cutoff": payload.get("analysis_cutoff"),
                "evaluation_stage": payload.get("evaluation_stage"),
                "selected_prediction_id": payload.get("selected_prediction_id"),
                "qualified_count": len(payload.get("eligible_prediction_ids", [])),
                "candidate_count": payload.get("candidate_count", 0),
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            })
    records.sort(key=lambda item: item.get("analysis_cutoff") or "", reverse=True)
    payload = {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "lock_count": len(records),
        "latest_lock_at": records[0]["analysis_cutoff"] if records else None,
        "latest_selected_prediction_id": records[0]["selected_prediction_id"] if records else None,
        "locks": records[:100],
    }
    LOCKS_DIR.mkdir(parents=True, exist_ok=True)
    temp = LOCKS_INDEX.with_suffix(".json.tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, LOCKS_INDEX)


def run(input_path: Path, *, dry_run: bool, output_path: Path | None = None) -> dict[str, Any]:
    top = load_json(input_path)
    require(isinstance(top, dict), "input must be a JSON object")
    require(top.get("schema_version") == "1.0.0", "schema_version must be 1.0.0")
    require(top.get("evaluation_stage") == "T-60m", "this tool only accepts T-60m")
    require(top.get("data_mode") in {"fixture", "research"}, "data_mode must be fixture or research")
    if top["data_mode"] == "fixture" and not dry_run:
        raise ValueError("fixture data can only run with --dry-run")
    for key in ("slate_id", "slate_date", "analysis_cutoff", "target_bookmaker_id", "market_id", "data_version", "candidates"):
        require(key in top, f"missing top-level field: {key}")
    require(isinstance(top["candidates"], list) and top["candidates"], "candidates must be a non-empty list")
    cutoff = parse_time(top["analysis_cutoff"], "analysis_cutoff")
    require(top["slate_date"] == cutoff.date().isoformat(), "slate_date must match analysis_cutoff local date")
    require(top.get("includes_overtime") is True, "includes_overtime must be true")

    manifest, v_config, g_config, coordination = load_active_configs()
    require(manifest["coordination"]["coordination_id"] == coordination["coordination_id"], "coordination config mismatch")

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in top["candidates"]:
        validate_candidate(candidate, top, cutoff)
        grouped[candidate["game_id"]].append(candidate)
    for game_id, pair in grouped.items():
        validate_game_pair(game_id, pair)

    items: list[dict[str, Any]] = []
    game_g_grades: dict[str, list[str]] = {}
    for game_id, pair in grouped.items():
        grades = [g_decision(candidate, g_config)["grade"] for candidate in pair]
        game_g_grades[game_id] = grades

    for candidate in top["candidates"]:
        v = v_decision(candidate, v_config)
        g = g_decision(candidate, g_config)
        dual_conflict = game_g_grades[candidate["game_id"]] == ["ㄅ", "ㄅ"] or sorted(game_g_grades[candidate["game_id"]]) == ["ㄅ", "ㄅ"]
        gates = gate_results(candidate, g_config, g, dual_conflict)
        items.append({"candidate": candidate, "v": v, "g": g, "dual_conflict": dual_conflict, "gates": gates})

    qualified = [item for item in items if item["g"]["grade"] == "ㄅ" and not item["dual_conflict"]]
    main_eligible = [item for item in qualified if all(item["gates"].values())]
    main_eligible.sort(key=ranking_key)
    selected = main_eligible[0] if main_eligible else None

    selected_prediction_id = None
    if selected:
        selected_prediction_id, _ = build_ids(selected["candidate"], top, manifest)

    priority_limit = coordination.get("ui_policy", {}).get("priority_display_max", 2)
    priority_items = [item for item in sorted(qualified, key=ranking_key) if item is not selected][:max(0, priority_limit)]
    priority_ids = {build_ids(item["candidate"], top, manifest)[0] for item in priority_items}

    records = [
        make_record(item, top, manifest, coordination, selected_prediction_id, priority_ids)
        for item in items
    ]

    selection_id = f"sel_{re.sub(r'[^A-Za-z0-9_-]+', '-', top['slate_id'])}_T60_{canonical_hash({'cutoff': top['analysis_cutoff'], 'data': top['data_version']}, 12)}"
    trace = []
    for item, record in zip(items, records):
        trace.append({
            "prediction_id": record["prediction_id"],
            "game_id": record["game_id"],
            "candidate_side": record["candidate_side"],
            "selection_team_id": record["selection_team_id"],
            "g_grade": record["g_grade"],
            "v_grade": record["v_grade"],
            "g_threshold_distance_pp": record["g_threshold_distance_pp"],
            "interval_width_pp": (record["p_optimistic"] - record["p_conservative"]) * 100,
            "data_age_minutes": item["candidate"]["data_age_minutes"],
            "gate_results": item["gates"],
            "rejection_reasons": record["main_rejection_reasons"],
            "main_candidate": record["main_candidate"],
            "ui_priority_candidate": record["ui_priority_candidate"],
        })

    selection_payload = {
        "schema_version": "1.0.0",
        "selection_id": selection_id,
        "slate_id": top["slate_id"],
        "slate_date": top["slate_date"],
        "analysis_cutoff": top["analysis_cutoff"],
        "evaluation_stage": "T-60m",
        "model_v_revision": manifest["active"]["V"]["revision_id"],
        "model_g_revision": manifest["active"]["G"]["revision_id"],
        "coordination_id": coordination["coordination_id"],
        "data_version": top["data_version"],
        "candidate_count": len(records),
        "eligible_prediction_ids": [record["prediction_id"] for record in records if record["g_grade"] == "ㄅ" and not record["dual_side_conflict"]],
        "selected_prediction_id": selected_prediction_id,
        "main_status": "主要場次待 T-5m 確認" if selected_prediction_id else "本批沒有通過全部硬閘門的 G1 主要場次",
        "priority_prediction_ids": sorted(priority_ids),
        "ranking_trace": sorted(trace, key=lambda item: (
            not item["main_candidate"],
            not item["ui_priority_candidate"],
            item["data_age_minutes"],
            item["game_id"],
            item["candidate_side"],
        )),
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
    print(f"Locked {len(records)} candidate records; main={selected_prediction_id or 'none'}")
    return selection_payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="T-60m slate-wave JSON")
    parser.add_argument("--dry-run", action="store_true", help="validate and calculate without writing")
    parser.add_argument("--output", type=Path, help="optional calculation output JSON")
    args = parser.parse_args()
    run(args.input, dry_run=args.dry_run, output_path=args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
