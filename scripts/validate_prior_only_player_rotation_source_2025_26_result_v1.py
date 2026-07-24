#!/usr/bin/env python3
"""Validate the aggregate-only prior-only player rotation source result v1."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULT = ROOT / "data" / "research" / "prior-only-player-rotation-source-2025-26-result-v1.json"
EXCEPTIONS = ROOT / "data" / "research" / "prior-only-player-rotation-source-exceptions-2025-26-v1.json"
DOC = ROOT / "docs" / "prior-only-player-rotation-source-2025-26-result-v1.md"
BUILDER = ROOT / "scripts" / "build_prior_only_player_rotation_source_2025_26_v1.py"
WORKFLOW = ROOT / ".github" / "workflows" / "build-prior-only-player-rotation-source-2025-26-v1.yml"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "prior-only-player-rotation-source-2025-26-result-validation-v1.json")
    args = parser.parse_args()

    result = json.loads(args.result.read_text(encoding="utf-8"))
    exceptions = json.loads(EXCEPTIONS.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")
    builder = BUILDER.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")
    tests = 0

    def check(condition: bool, label: str) -> None:
        nonlocal tests
        if not condition:
            raise AssertionError(label)
        tests += 1

    check(result["schema_version"] == "prior-only-player-rotation-source-2025-26-result-v1", "schema")
    check(result["formal_state"] == "PRIOR_ONLY_PLAYER_ROTATION_SOURCE_2025_26_PASS_RECORDED", "state")
    check(result["recorded_at_utc"].endswith("Z"), "record time")

    evidence = result["execution_evidence"]
    check(evidence["execution_mode"] == "GITHUB_ACTIONS_OFFICIAL_SOURCE_BUILD", "execution mode")
    check(evidence["branch_head"] == "1cc53c6b898cf7c80fdf28649366f04ca9f636c3", "source head")
    check(evidence["workflow_run"] == 30099845472, "run")
    check(evidence["job"] == 89502852068, "job")
    check(evidence["artifact_id"] == 8599159260, "artifact")
    check(evidence["artifact_digest"] == "sha256:5f83f1c21e4a73696fd4d5dca8faa7f98908373f0795c45c6637a149bd345ee9", "digest")
    check(evidence["artifact_inspected"] is True, "artifact inspected")
    check(evidence["provider_api_requests"] == 1230, "request count")
    check(evidence["provider_requests_authorized_scope"] == "NBA_OFFICIAL_LIVEDATA_FINAL_BOXSCORE_ONLY", "request scope")
    check(evidence["authentication_used"] is False, "no auth")
    check(evidence["access_control_bypass_used"] is False, "no bypass")

    inputs = result["inputs"]
    check(inputs["governed_silver_artifact_id"] == 8591673536, "silver artifact")
    check(inputs["governed_silver_sha256"] == "sha256:3b9bfc3500e83136022ec1a90189c193ae64d918374380e0d02fa61251244bc8", "silver digest")
    check(inputs["governed_games"] == 1230, "governed games")
    check(inputs["official_source_provider"] == "NBA Official LiveData Boxscore", "provider")
    check(inputs["official_source_url_template"].startswith("https://cdn.nba.com/"), "official URL")
    check(inputs["source_exception_manifest_sha256"] == "sha256:092607eb428cf3954ad33bbd97a3037589b4775d8644f0e4446bda3156196517", "exception digest")
    check(inputs["declared_source_exceptions"] == 1, "exception count")

    coverage = result["coverage"]
    expected_coverage = {
        "requested_games": 1230,
        "successful_games": 1230,
        "failed_games": 0,
        "team_game_rows": 2460,
        "player_game_rows": 43265,
        "unique_player_ids": 603,
        "months_covered": 7,
        "teams_represented": 30,
    }
    for key, value in expected_coverage.items():
        check(coverage[key] == value, f"coverage {key}")
    check(coverage["official_game_source_coverage"] == 1.0, "source coverage")

    quality = result["quality"]
    zero_quality = (
        "duplicate_game_player_rows",
        "missing_team_rows",
        "unexpected_team_rows",
        "invalid_team_rows",
        "invalid_minutes",
        "starter_without_play",
        "starter_count_errors",
        "minute_reconciliation_errors",
        "unmatched_source_reconciliation_exceptions",
        "source_reconciliation_value_mismatches",
        "official_import_team_mismatches",
        "official_import_invalid_player_rows",
        "official_import_duplicate_rows",
    )
    for key in zero_quality:
        check(quality[key] == 0, f"quality {key}")
    check(quality["source_reconciliation_exceptions_applied"] == 1, "applied exception")
    check(0 <= quality["max_abs_team_minute_error"] <= 0.003333, "minute tolerance")
    check(quality["player_names_retained"] is False, "no names")
    check(quality["not_playing_descriptions_retained"] is False, "no descriptions")
    check(quality["raw_json_retained"] is False, "no raw JSON")

    reconciliation = result["source_reconciliation"]
    check(reconciliation["exception_id"] == "OFFICIAL_LIVEDATA_PLAYER_MINUTES_DISCREPANCY_2025_26_001", "exception id")
    check(reconciliation["scope"] == "ONE_FIELD_OFFICIAL_TO_OFFICIAL_RECONCILIATION_ONLY", "exception scope")
    check(reconciliation["policy"] == "EXACT_DEIDENTIFIED_SUBJECT_KEY_AND_EXACT_LIVE_VALUE_ONLY", "exception policy")
    check(reconciliation["official_evidence_source"] == "NBA.com Official Game Box Score", "official evidence")
    check(reconciliation["official_evidence_url"].startswith("https://www.nba.com/game/"), "evidence URL")
    check(reconciliation["field_changed"] == "minutes", "minutes only")
    check(reconciliation["identity_changed"] is False, "identity lock")
    check(reconciliation["played_flag_changed"] is False, "played lock")
    check(reconciliation["starter_flag_changed"] is False, "starter lock")
    check(reconciliation["player_name_published"] is False, "name lock")
    check(reconciliation["model_or_market_result_used_to_create_exception"] is False, "outcome independence")

    time = result["time_authority"]
    check(time["source_game_end_timestamp_available"] is False, "no source end time")
    check(time["primary_design_rule"] == "source_game_end_time_utc < target_analysis_cutoff_utc < target_tipoff_utc", "primary PIT rule")
    check(time["approved_build_fallback"] == "source_game_date_et < target_game_date_et", "date fallback")
    check(time["same_day_source_rows_allowed"] is False, "same-day lock")
    check(time["future_source_rows_allowed"] is False, "future lock")
    check(time["target_game_source_rows_allowed"] is False, "target-game lock")

    private = result["private_outputs"]
    check(private["source_csv_sha256"] == "sha256:f1b0683111a46e453debf3e964f6b9e704f25c3269e56faa1574ad0ccb163f76", "private output digest")
    check(private["private_player_rows"] == 43265, "private rows")
    check(private["public_player_rows_committed"] == 0, "public player rows")
    check(private["public_game_level_feature_rows_committed"] == 0, "public feature rows")
    check(private["raw_official_json_committed"] == 0, "public raw JSON")

    boundaries = result["execution_boundaries"]
    for key in (
        "real_rotation_feature_build_executed",
        "residual_audit_executed",
        "model_retraining_executed",
        "model_refit_executed",
        "calibration_change_executed",
        "market_data_used_as_model_feature",
        "odds_join_executed",
        "bet_selection_executed",
        "ev_calculated",
        "roi_calculated",
        "clv_calculated",
        "drawdown_calculated",
    ):
        check(boundaries[key] is False, f"boundary {key}")

    qualification = result["qualification"]
    check(qualification["official_source_qualified_for_prior_only_rotation_v1"] is True, "source qualified")
    check(qualification["ready_for_prior_only_rotation_feature_build"] is True, "feature build ready")
    check(qualification["source_time_requires_strict_earlier_eastern_date_fallback"] is True, "fallback required")
    check(qualification["model_training_authorized"] is False, "training lock")
    check(qualification["strict_t60_qualified"] is False, "T60 lock")
    check(qualification["formal_point_in_time_market_backtest_allowed"] is False, "backtest lock")
    check(qualification["betting_edge_claim_allowed"] is False, "edge lock")
    check(qualification["formal_stake"] == 0, "stake")
    check(result["next_unique_sub_mainline"] == "BUILD_PRIOR_ONLY_PLAYER_ROTATION_STATE_FEATURES_2025_26_V1_WITHOUT_MODEL_RETRAINING", "next mainline")

    check(exceptions["formal_state"] == "OFFICIAL_SOURCE_RECONCILIATION_EXCEPTION_MANIFEST_PREDECLARED", "manifest state")
    check(exceptions["scope"] == "ONE_FIELD_OFFICIAL_TO_OFFICIAL_RECONCILIATION_ONLY", "manifest scope")
    check(len(exceptions["exceptions"]) == 1, "manifest population")
    exception = exceptions["exceptions"][0]
    check(exception["exception_id"] == reconciliation["exception_id"], "manifest exception ID")
    check(exception["subject_key_sha256"].startswith("sha256:"), "deidentified subject")
    check("player_id" not in exception, "no raw player ID in manifest")
    check("player_name" not in exception, "no player name in manifest")
    check(exception["field"] == "minutes", "manifest field")
    check(exception["live_data_value"] == 28.136667, "manifest source value")
    check(exception["reconciled_official_value"] == 36.8, "manifest official value")
    check(exception["allowed_mutation"] == "MINUTES_ONLY", "manifest mutation")
    check(exception["played_flag_change_allowed"] is False, "manifest played lock")
    check(exception["starter_flag_change_allowed"] is False, "manifest starter lock")
    check(exception["identity_change_allowed"] is False, "manifest identity lock")
    for key, value in exceptions["guardrails"].items():
        check(value is False, f"manifest guardrail {key}")

    check("Official Source Qualified / Feature Build Not Yet Executed" in doc, "doc state")
    check("43,265" in doc, "doc rows")
    check("This is a source reconciliation, not an imputation or lowered QA gate." in doc, "doc exception interpretation")
    check("source_game_date_et < target_game_date_et" in doc, "doc PIT fallback")
    check("BUILD_PRIOR_ONLY_PLAYER_ROTATION_STATE_FEATURES_2025_26_V1" in doc, "doc next")
    check("Formal Stake: **0**" in doc, "doc stake")

    check("load_exceptions" in builder, "builder loads manifest")
    check("subject_key(game_id, player_id)" in builder, "builder subject key")
    check("EXACT_DEIDENTIFIED_SUBJECT_KEY_AND_EXACT_LIVE_VALUE_ONLY" in builder, "builder exception policy")
    check('"model_training_authorized": False' in builder, "builder training lock")
    check('"formal_market_backtest_allowed": False' in builder, "builder backtest lock")
    check('"formal_stake": 0' in builder, "builder stake lock")
    check("--exceptions" in workflow, "workflow manifest input")
    check("SILVER_2025_26_ARTIFACT_ID: \"8591673536\"" in workflow, "workflow Silver pin")
    check("source_reconciliation_exceptions_applied" in workflow, "workflow exception QA")
    check("player_name" in workflow, "workflow privacy QA")
    check("private-prior-only-player-rotation-source-2025-26-v1" in workflow, "workflow private artifact")

    output = {
        "schema_version": 1,
        "formal_state": "PRIOR_ONLY_PLAYER_ROTATION_SOURCE_2025_26_RESULT_VALID",
        "all_contract_tests_passed": True,
        "contract_tests": tests,
        "validated_population": {
            "official_games": coverage["successful_games"],
            "team_game_rows": coverage["team_game_rows"],
            "private_player_game_rows": coverage["player_game_rows"],
            "unique_player_ids": coverage["unique_player_ids"],
        },
        "source_reconciliation": {
            "declared": 1,
            "applied": quality["source_reconciliation_exceptions_applied"],
            "unmatched": quality["unmatched_source_reconciliation_exceptions"],
            "official_to_official_only": True,
        },
        "preserved_locks": {
            "real_rotation_feature_build_executed": False,
            "model_training_authorized": False,
            "strict_t60_qualified": False,
            "formal_point_in_time_market_backtest_allowed": False,
            "betting_edge_claim_allowed": False,
            "formal_stake": 0,
        },
        "next_unique_sub_mainline": result["next_unique_sub_mainline"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
