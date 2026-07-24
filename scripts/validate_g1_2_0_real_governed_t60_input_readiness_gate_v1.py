#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GATE_PATH = ROOT / "data/research/g1-2-0-real-governed-t60-input-readiness-gate-v1.json"
STATUS_PATH = ROOT / "data/research/no-cost-timestamped-odds-source-qualification-current-status-v9.json"
MANIFEST_PATH = ROOT / "models/manifest.json"
SCHEMA_PATH = ROOT / "schemas/prediction-record.schema.json"
FIXTURE_PATH = ROOT / "data/fixtures/t60-g1-2-0-ev-example.json"
RUNTIME_PATH = ROOT / "scripts/g1_2_0_runtime.py"
T60_PATH = ROOT / "scripts/lock_t60_snapshot.py"
DOC_PATH = ROOT / "docs/g1-2-0-real-governed-t60-input-readiness-gate-v1.md"
HANDOFF_PATH = ROOT / "docs/handoffs/nba_value_lab_handoff_2026-07-24_hoopsapi_deferred_g120_t60_readiness.md"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_readiness(state: dict[str, bool]) -> dict[str, bool]:
    ready = all(
        state[name]
        for name in (
            "season_explicit_and_correct",
            "competition_explicit_and_correct",
            "real_governed_data_mode",
            "t60_stage",
            "real_bookmaker_identity",
            "same_book_two_sided_h2h",
            "provider_origin_observed_at",
            "provider_timestamp_semantics_verified",
            "observed_at_pre_tip_and_pre_cutoff",
            "source_rights_allowed",
            "source_lineage_complete",
            "exact_mapping",
            "injury_data_gate_complete",
        )
    )
    return {
        "real_input_ready": ready,
        "fixture_substitution_allowed": False,
        "closing_substitution_allowed": False,
        "collector_fetched_at_substitution_allowed": False,
        "formal_history_write_allowed_during_readiness": False,
        "market_metrics_allowed": False,
        "stake_increase_allowed": False,
    }


def run_policy_scenarios() -> dict[str, bool]:
    complete = {
        "season_explicit_and_correct": True,
        "competition_explicit_and_correct": True,
        "real_governed_data_mode": True,
        "t60_stage": True,
        "real_bookmaker_identity": True,
        "same_book_two_sided_h2h": True,
        "provider_origin_observed_at": True,
        "provider_timestamp_semantics_verified": True,
        "observed_at_pre_tip_and_pre_cutoff": True,
        "source_rights_allowed": True,
        "source_lineage_complete": True,
        "exact_mapping": True,
        "injury_data_gate_complete": True,
    }
    results: dict[str, bool] = {}

    results["complete_evidence_can_be_ready"] = evaluate_readiness(dict(complete))["real_input_ready"] is True

    for name in (
        "season_explicit_and_correct",
        "competition_explicit_and_correct",
        "real_governed_data_mode",
        "real_bookmaker_identity",
        "same_book_two_sided_h2h",
        "provider_origin_observed_at",
        "provider_timestamp_semantics_verified",
        "observed_at_pre_tip_and_pre_cutoff",
        "source_rights_allowed",
        "source_lineage_complete",
        "exact_mapping",
        "injury_data_gate_complete",
    ):
        scenario = dict(complete)
        scenario[name] = False
        results[f"missing_{name}_blocks_readiness"] = evaluate_readiness(scenario)["real_input_ready"] is False

    invariants = evaluate_readiness(dict(complete))
    results["fixture_never_substitutes_real_input"] = invariants["fixture_substitution_allowed"] is False
    results["closing_never_substitutes_t60"] = invariants["closing_substitution_allowed"] is False
    results["collector_fetch_never_substitutes_observed_at"] = (
        invariants["collector_fetched_at_substitution_allowed"] is False
    )
    results["readiness_never_writes_formal_history"] = (
        invariants["formal_history_write_allowed_during_readiness"] is False
    )
    results["readiness_never_runs_market_metrics"] = invariants["market_metrics_allowed"] is False
    results["readiness_never_increases_stake"] = invariants["stake_increase_allowed"] is False

    if not all(results.values()):
        failed = sorted(name for name, passed in results.items() if not passed)
        raise SystemExit(f"readiness gate policy scenarios failed: {failed}")
    return results


def main() -> None:
    gate = load_json(GATE_PATH)
    status = load_json(STATUS_PATH)
    manifest = load_json(MANIFEST_PATH)
    schema = load_json(SCHEMA_PATH)
    fixture = load_json(FIXTURE_PATH)
    runtime_source = RUNTIME_PATH.read_text(encoding="utf-8")
    t60_source = T60_PATH.read_text(encoding="utf-8")
    doc = DOC_PATH.read_text(encoding="utf-8")
    handoff = HANDOFF_PATH.read_text(encoding="utf-8")

    assert gate["formal_state"] == "G1_2_0_REAL_GOVERNED_T60_INPUT_READINESS_GATE_DESIGN_VALIDATED"
    assert gate["design_only"] is True
    assert gate["provider_path_transition"]["hoopsapi_runtime_path"] == "DEFERRED_BY_USER_NO_EXECUTION"
    assert gate["provider_path_transition"]["hoopsapi_execution_enabled"] is False
    assert gate["provider_path_transition"]["hoopsapi_provider_requests_executed"] == 0
    assert gate["provider_path_transition"]["qualified_timestamped_odds_sources"] == []

    activation = gate["activation_identity_gate"]
    assert activation["required_season"] == "2026-27"
    assert activation["required_competition_type"] == "regular_season"
    assert activation["season_must_be_explicit"] is True
    assert activation["competition_type_must_be_explicit"] is True
    assert activation["date_based_inference_allowed"] is False
    assert activation["scheduled_g_required"] == "1.2.0"
    assert activation["pre_trigger_primary_g"] == "1.1.1"
    assert activation["post_trigger_primary_g"] == "1.2.0"

    assert 'TARGET_SEASON = "2026-27"' in runtime_source
    assert 'TARGET_COMPETITION = "regular_season"' in runtime_source
    assert 'top.get("season") == TARGET_SEASON' in runtime_source
    assert 'top.get("competition_type") == TARGET_COMPETITION' in runtime_source

    top_gate = gate["top_level_input_gate"]
    expected_top = {
        "schema_version", "data_mode", "slate_id", "slate_date", "analysis_cutoff",
        "evaluation_stage", "target_bookmaker_id", "market_id", "includes_overtime",
        "data_version", "lock_window_minutes", "candidates", "season", "competition_type",
    }
    assert set(top_gate["required_fields"]) == expected_top
    assert top_gate["required_values"] == {
        "data_mode": "real_governed",
        "evaluation_stage": "T-60m",
        "market_id": "moneyline_ot_included",
        "includes_overtime": True,
        "season": "2026-27",
        "competition_type": "regular_season",
    }
    assert top_gate["fixture_data_mode_allowed"] is False
    assert top_gate["closing_only_data_mode_allowed"] is False
    assert top_gate["target_bookmaker_may_be_fixture_or_placeholder"] is False
    assert top_gate["lock_window_min_minutes"] == 30
    assert top_gate["lock_window_max_minutes"] == 90

    candidate_gate = gate["candidate_input_gate"]
    expected_candidate = {
        "game_id", "scheduled_at", "candidate_side", "selection_team_id", "opponent_team_id",
        "target_odds", "opponent_odds", "observed_at", "p_conservative", "p_neutral",
        "p_optimistic", "coverage_pct", "confidence", "news_risk_level",
        "analysis_gate_status", "comparison_sources", "injury_confirmed",
        "starters_confirmed", "minutes_limit_confirmed", "source_lineage_complete",
        "market_rules_complete", "price_timestamp_valid", "out_of_distribution",
        "reverse_path_resolved", "stale_warning", "model_market_gap_pp",
        "independent_evidence_count", "data_age_minutes",
    }
    assert set(candidate_gate["required_fields"]) == expected_candidate
    assert candidate_gate["exactly_two_sides_per_game"] is True
    assert set(candidate_gate["required_sides"]) == {"home", "away"}
    assert candidate_gate["same_snapshot_two_sided_odds_required"] is True
    assert candidate_gate["same_observed_at_required"] is True
    assert candidate_gate["fuzzy_team_or_game_mapping_allowed"] is False
    for field in expected_candidate:
        if f'"{field}"' not in t60_source:
            raise SystemExit(f"base T-60 validator no longer references required field: {field}")

    odds_gate = gate["odds_provenance_gate"]
    assert odds_gate["bookmaker_identity_required"] is True
    assert odds_gate["same_bookmaker_two_sided_h2h_required"] is True
    assert odds_gate["provider_origin_observed_at_required"] is True
    assert odds_gate["collector_fetched_at_may_substitute_observed_at"] is False
    assert odds_gate["closing_price_may_substitute_t60"] is False
    assert odds_gate["future_snapshot_fill_allowed"] is False
    assert odds_gate["opening_inference_allowed"] is False
    assert odds_gate["source_rights_state_required_value"] == "private_research_allowed"
    assert odds_gate["provider_timestamp_semantics_verified_required"] is True
    assert odds_gate["public_raw_quote_rows_allowed"] is False

    execution = gate["execution_boundary"]
    assert execution["real_input_available"] is False
    assert execution["real_validation_executed"] is False
    assert execution["fixture_may_prove_real_readiness"] is False
    assert execution["fixture_may_enter_formal_history"] is False
    assert execution["g1_2_0_early_activation_authorized"] is False
    assert execution["market_backtest_authorized"] is False
    assert execution["clv_ev_roi_drawdown_authorized"] is False
    assert execution["formal_stake"] == 0

    assert fixture["data_mode"] == "fixture"
    assert fixture["target_bookmaker_id"] == "fixture_book"
    assert fixture["season"] == "2026-27"
    assert fixture["competition_type"] == "regular_season"
    assert set(fixture) >= expected_top - {"data_mode"} | {"data_mode"}
    assert set(fixture["candidates"][0]) >= expected_candidate
    assert fixture["data_mode"] != top_gate["required_values"]["data_mode"]

    assert manifest["active"]["G"]["version"] == "1.1.1"
    assert manifest["scheduled_next"]["G"]["version"] == "1.2.0"
    assert manifest["compatibility"]["prediction_record_schema"] == "1.4.0"
    assert schema["schema_version"] == "1.4.0"

    assert status["formal_state"] == "NO_COST_TIMESTAMPED_ODDS_PROVIDER_PATHS_DEFERRED_G1_2_0_T60_READINESS_GATE_DESIGNED"
    assert status["user_decisions"]["hoopsapi_runtime_path"] == "DEFERRED_BY_USER_NO_EXECUTION"
    assert status["provider_execution_state"]["hoopsapi_provider_requests_executed"] == 0
    assert status["source_qualification_state"]["qualified_for_real_2026_27_t60_input"] == []
    assert status["next_non_provider_step"]["gate_id"] == gate["gate_id"]
    assert status["activation_state"]["active_g"] == "G1.1.1-20260719"
    assert status["activation_state"]["scheduled_g"] == "G1.2.0-20260723"
    assert status["next_unique_mainline"] == "AWAIT_REAL_GOVERNED_2026_27_T60_INPUT_AND_QUALIFIED_TIMESTAMPED_ODDS"
    assert status["market_backtest_unlocked"] is False
    assert status["formal_stake"] == 0

    required_text = (
        "DEFERRED_BY_USER_NO_EXECUTION",
        "G1_2_0_REAL_GOVERNED_T60_INPUT_READINESS_GATE_DESIGN_VALIDATED",
        "collector_fetched_at` 不得替代 `observed_at",
        "Closing-only",
        "AWAIT_REAL_GOVERNED_2026_27_T60_INPUT_AND_QUALIFIED_TIMESTAMPED_ODDS",
        "Formal Stake：0",
    )
    for text, label in ((doc, "documentation"), (handoff, "handoff")):
        for item in required_text:
            if item not in text:
                raise SystemExit(f"missing {label} evidence: {item}")

    scenarios = run_policy_scenarios()
    report = {
        "schema_version": 1,
        "formal_state": "G1_2_0_REAL_GOVERNED_T60_INPUT_READINESS_GATE_VALID",
        "gate_id": gate["gate_id"],
        "design_only": True,
        "hoopsapi_deferred": True,
        "hoopsapi_provider_requests_executed": 0,
        "qualified_timestamped_odds_sources": 0,
        "real_input_available": False,
        "fixture_rejected_as_real_input": True,
        "closing_only_rejected_as_t60": True,
        "provider_origin_observed_at_required": True,
        "policy_scenarios": len(scenarios),
        "real_validation_executed": False,
        "market_metrics_executed": False,
        "formal_stake": 0,
        "next_unique_mainline": "AWAIT_REAL_GOVERNED_2026_27_T60_INPUT_AND_QUALIFIED_TIMESTAMPED_ODDS",
    }
    report_text = json.dumps(report, sort_keys=True).lower()
    for forbidden in ("home_price", "away_price", "raw_payload", "api_key", "authorization_header"):
        if forbidden in report_text:
            raise SystemExit(f"aggregate report leaked forbidden fragment: {forbidden}")

    output = ROOT / "build/g1-2-0-real-governed-t60-input-readiness-gate-validation-v1.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
