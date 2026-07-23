#!/usr/bin/env python3
"""Validate the scheduled G1.2.0 EV-primary season activation record."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "models/manifest.json"
CONFIG = ROOT / "models/g1/1.2.0/config.json"
SPEC = ROOT / "models/g1/1.2.0/spec.md"
DECISION = ROOT / "data/research/g1.2.0-ev-primary-season-activation-decision-v1.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    manifest = load(MANIFEST)
    config = load(CONFIG)
    decision = load(DECISION)

    active_g = manifest["active"]["G"]
    require(active_g["version"] == "1.1.1", "offseason active G changed prematurely")
    require(active_g["revision_id"] == "G1.1.1-20260719", "control revision changed")

    scheduled = manifest["scheduled_next"]["G"]
    require(scheduled["version"] == "1.2.0", "scheduled version mismatch")
    require(scheduled["revision_id"] == "G1.2.0-20260723", "scheduled revision mismatch")
    require(scheduled["config"] == "models/g1/1.2.0/config.json", "scheduled config path mismatch")
    require(scheduled["spec"] == "models/g1/1.2.0/spec.md", "scheduled spec path mismatch")
    require(
        scheduled["activation_status"] == "USER_APPROVED_FOR_2026_27_REGULAR_SEASON",
        "activation was not user-approved",
    )
    require(
        scheduled["activation_trigger"]
        == "first_2026_27_regular_season_game_with_complete_T60_data_gate",
        "activation trigger changed",
    )
    require(scheduled["primary_after_activation"] is True, "G1.2.0 is not primary after activation")
    require(
        scheduled["previous_G1.1.1_role_after_activation"] == "parallel_control_shadow",
        "G1.1.1 control role changed",
    )
    require(scheduled["formal_stake_fraction"] == 0, "scheduled Stake changed")

    require(config["engine_id"] == "G", "engine mismatch")
    require(config["version"] == "1.2.0", "config version mismatch")
    require(config["revision_id"] == "G1.2.0-20260723", "config revision mismatch")

    activation = config["activation"]
    require(activation["approved_by_user"] is True, "user approval missing")
    require(activation["mode"] == "primary_from_2026_27_regular_season", "activation mode changed")
    require(
        activation["trigger"] == "first_2026_27_regular_season_game_with_complete_T60_data_gate",
        "config trigger changed",
    )
    require(activation["previous_control_version"] == "1.1.1", "control version changed")
    require(activation["automatic_real_money_activation"] is False, "real-money activation enabled")

    ev = config["ev_policy"]
    require(ev["primary_metric"] == "conservative_ev", "EV is not primary")
    require(ev["formula"] == "P_C * decimal_odds - 1", "EV formula changed")
    require(ev["candidate_min_ev"] == 0.05, "candidate EV threshold changed")
    require(ev["grade_m_min_ev"] == 0.05, "M EV threshold changed")
    require(ev["grade_p_min_ev"] == 0.07, "P EV threshold changed")
    require(ev["grade_b_min_ev"] == 0.10, "B EV threshold changed")
    require(ev["pp_guard_min"] == 2.0, "PP guard changed")
    require(ev["pp_guard_role"] == "hard_safety_floor", "PP guard weakened")
    require(ev["price_band_required_margin_pp_role"] == "control_diagnostic_only", "old PP bands restored as primary")
    require(ev["post_result_threshold_tuning_forbidden"] is True, "post-result tuning allowed")

    gate = config["core_gate"]
    require(gate["coverage_min_pct"] == 85, "coverage gate changed")
    require(gate["comparison_sources_min"] == 3, "source gate changed")
    require(gate["injury_and_rotation_confirmation_required"] is True, "injury gate removed")
    require(gate["news_risk_max"] == 1, "news risk gate changed")
    require(gate["out_of_distribution_allowed"] is False, "OOD enabled")
    require(gate["stale_warning_allowed"] is False, "stale price enabled")

    selection = config["selection"]
    require(selection["official_main_target"] == 2, "main target changed")
    require(selection["official_main_max"] == 3, "main maximum changed")
    require(selection["allow_zero_main"] is True, "zero-main option removed")
    require(selection["highest_ev_alone_forbidden"] is True, "highest EV alone can select")
    require("higher_conservative_ev" in selection["ranking_order"], "EV ranking missing")

    control = config["control_comparison"]
    require(control["enabled"] is True, "control comparison disabled")
    require(control["control_version"] == "G1.1.1-20260719", "control revision mismatch")
    require(control["control_must_not_drive_primary_output"] is True, "control drives primary output")

    publication = config["publication"]
    require(publication["allow_formal_stake"] is False, "formal Stake enabled")
    require(publication["formal_stake_fraction"] == 0, "formal Stake changed")

    digest = hashlib.sha256(SPEC.read_bytes()).hexdigest()
    integrity = config["spec_integrity"]
    require(integrity["algorithm"] == "sha256", "spec hash algorithm changed")
    require(integrity["subject"] == "models/g1/1.2.0/spec.md", "spec subject mismatch")
    require(integrity["digest"] == digest, "spec digest mismatch")

    require(
        decision["formal_state"] == "G1_2_0_EV_PRIMARY_USER_APPROVED_FOR_2026_27_SEASON",
        "decision state mismatch",
    )
    require(decision["user_decision"]["approved"] is True, "decision approval missing")
    require(decision["activation"]["primary_engine_after_trigger"] == "G1.2.0-20260723", "primary engine mismatch")
    require(decision["activation"]["control_engine_after_trigger"] == "G1.1.1-20260719", "control engine mismatch")
    require(decision["boundaries"]["formal_stake"] == 0, "decision Stake changed")
    require(decision["boundaries"]["real_money_execution_authorized"] is False, "real money authorized")
    require(decision["boundaries"]["model_retraining_authorized"] is False, "model retraining authorized")

    print(
        json.dumps(
            {
                "formal_state": decision["formal_state"],
                "offseason_active_G": active_g["revision_id"],
                "scheduled_primary_G": scheduled["revision_id"],
                "activation_trigger": scheduled["activation_trigger"],
                "candidate_min_ev": ev["candidate_min_ev"],
                "grade_p_min_ev": ev["grade_p_min_ev"],
                "grade_b_min_ev": ev["grade_b_min_ev"],
                "pp_guard_min": ev["pp_guard_min"],
                "formal_stake": 0,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
