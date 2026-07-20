#!/usr/bin/env python3

from lock_t60_snapshot import (
    base_grade,
    coordination_decision,
    find_segment,
    g_decision,
    load_active_configs,
    v_decision,
)


manifest, v_config, g_config, coordination = load_active_configs()

assert str(manifest["active"]["V"]["version"]) == str(v_config["version"])
assert str(manifest["active"]["G"]["version"]) == str(g_config["version"])


def candidate(odds: float, p_c: float, *, confidence: str = "高", risk: int = 0) -> dict:
    return {
        "analysis_gate_status": "可分析",
        "confidence": confidence,
        "news_risk_level": risk,
        "p_conservative": p_c,
        "target_odds": odds,
    }


v_segments = v_config["price_policy"]["price_segments"]
v_outside = v_config["price_policy"]["outside_conclusion"]
assert find_segment(v_segments, 1.20, v_outside)["id"] == "extreme_low_excluded"
assert find_segment(v_segments, 1.30, v_outside)["id"] == "low_extension"
assert find_segment(v_segments, 1.40, v_outside)["id"] == "core"
assert find_segment(v_segments, 1.60, v_outside)["id"] == "core"
assert find_segment(v_segments, 1.600001, v_outside)["id"] == "high_extension"
assert find_segment(v_segments, 1.75, v_outside)["id"] == "high_extension"
assert find_segment(v_segments, 1.750001, v_outside)["id"] == "separate_calibration"
assert find_segment(v_segments, 1.999999, v_outside)["id"] == "separate_calibration"
assert find_segment(v_segments, 2.00, v_outside)["id"] == "outside"

g_segments = g_config["price_bands"]
assert find_segment(g_segments, 1.20, "只記錄")["id"] == "low_research"
assert find_segment(g_segments, 1.35, "只記錄")["id"] == "favorite_core"
assert find_segment(g_segments, 1.60, "只記錄")["id"] == "favorite_core"
assert find_segment(g_segments, 1.600001, "只記錄")["id"] == "near_even_core"
assert find_segment(g_segments, 2.20, "只記錄")["id"] == "near_even_core"
assert find_segment(g_segments, 2.200001, "只記錄")["id"] == "medium_high_extension"
assert find_segment(g_segments, 3.50, "只記錄")["id"] == "medium_high_extension"
assert find_segment(g_segments, 3.500001, "只記錄")["id"] == "high_volatility"

grading = g_config["grading"]
assert base_grade(candidate(2.0, 0.56), 5.0, grading)[0] == "ㄅ"
assert base_grade(candidate(2.0, 0.53), 5.0, grading)[0] == "ㄆ"
assert base_grade(candidate(2.0, 0.51), 5.0, grading)[0] == "ㄇ"
assert base_grade(candidate(2.0, 0.49), 5.0, grading)[0] == "不支持"
assert base_grade(candidate(2.0, 0.56, confidence="資料不足"), 5.0, grading)[0] == "資料不足"

core_candidate = candidate(1.50, 0.75)
core_v = v_decision(core_candidate, v_config)
core_g = g_decision(core_candidate, g_config)
core_combined = coordination_decision(core_v, core_g, False, coordination)
assert core_v["grade"] == "ㄅ" and core_g["grade"] == "ㄅ"
assert core_combined["grade"] == "ㄅ"
assert core_combined["label"] == coordination["combined_policy"]["v_and_g_label"]

extension_candidate = candidate(1.65, 0.70)
extension_v = v_decision(extension_candidate, v_config)
extension_g = g_decision(extension_candidate, g_config)
extension_combined = coordination_decision(extension_v, extension_g, False, coordination)
assert extension_v["grade"] == "ㄆ" and extension_g["grade"] == "ㄅ"
assert extension_combined["grade"] == "ㄆ"
assert extension_combined["label"] == coordination["combined_policy"]["g_only_label"]

conflict = coordination_decision(core_v, core_g, True, coordination)
assert conflict["grade"] == "ㄆ"
assert conflict["label"] == coordination["combined_policy"]["dual_side_conflict_label"]

print("Model decision boundary and coordination tests passed")
