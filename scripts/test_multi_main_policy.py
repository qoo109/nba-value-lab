#!/usr/bin/env python3

from multi_main_policy import choose_main_records

CONFIG = {
    "selection": {
        "official_main_target": 2,
        "official_main_max": 3,
        "third_slot_policy": {
            "enabled": True,
            "coverage_min_pct": 90,
            "interval_width_max_pp": 5,
            "comparison_sources_min": 4,
            "threshold_buffer_min_pp": 2,
            "news_risk_max": 0,
            "confidence_required": "高",
        },
    }
}


def record(name: str, *, age: int, gap: float, coverage: int = 91, width: float = 4, sources: int = 4, risk: int = 0):
    return {
        "prediction_id": name,
        "game_id": name,
        "candidate_side": "home",
        "g_grade": "ㄅ",
        "dual_side_conflict": False,
        "main_gate_results": {"all": True},
        "data_age_minutes": age,
        "injury_confirmed": True,
        "starters_confirmed": True,
        "minutes_limit_confirmed": True,
        "p_conservative": 0.70,
        "p_optimistic": 0.70 + width / 100,
        "g_threshold_distance_pp": gap,
        "model_market_gap_pp": 3,
        "reverse_path_resolved": True,
        "similar_case_stability_score": 0.8,
        "coverage_pct": coverage,
        "comparison_sources": sources,
        "news_risk_level": risk,
        "confidence": "高",
    }


records = [
    record("A", age=1, gap=3.0),
    record("B", age=2, gap=2.5),
    record("C", age=3, gap=2.1),
    record("D", age=4, gap=1.5),
]
selected = choose_main_records(records, CONFIG)
assert [item["prediction_id"] for item in selected] == ["A", "B", "C"]

records[2]["coverage_pct"] = 88
selected = choose_main_records(records, CONFIG)
assert [item["prediction_id"] for item in selected] == ["A", "B"]

selected = choose_main_records(records[:1], CONFIG)
assert [item["prediction_id"] for item in selected] == ["A"]

print("G1.1 multi-main policy tests passed")
