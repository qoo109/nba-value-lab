#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

EXPECTED_FORMAL_STATE = "PRIOR_ONLY_PLAYER_ROTATION_STATE_FEATURES_2025_26_PASS"
VALIDATION_FORMAL_STATE = "PRIOR_ONLY_PLAYER_ROTATION_STATE_FEATURES_2025_26_VALID"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    checks = {
        "formal_state_pass": report.get("formal_state") == EXPECTED_FORMAL_STATE,
        "target_games_1230": report.get("inputs", {}).get("target_games") == 1230,
        "target_team_rows_2460": report.get("inputs", {}).get("target_team_rows") == 2460,
        "source_rows_43265": report.get("inputs", {}).get("source_player_game_rows") == 43265,
        "player_feature_rows_positive": report.get("outputs", {}).get("private_player_feature_rows", 0) > 0,
        "team_feature_rows_2460": report.get("outputs", {}).get("private_team_feature_rows") == 2460,
        "matchup_feature_rows_1230": report.get("outputs", {}).get("private_matchup_feature_rows") == 1230,
        "public_player_rows_zero": report.get("outputs", {}).get("public_player_rows_committed") == 0,
        "public_game_rows_zero": report.get("outputs", {}).get("public_game_level_feature_rows_committed") == 0,
        "feature_ready_games_gate": report.get("coverage", {}).get("feature_ready_independent_games", 0) >= 1000,
        "feature_ready_rate_gate": report.get("coverage", {}).get("feature_ready_rate", 0) >= 0.80,
        "all_30_teams": report.get("coverage", {}).get("teams_with_feature_ready_rows") == 30,
        "five_months_or_more": report.get("coverage", {}).get("months_with_feature_ready_games", 0) >= 5,
        "missingness_audit": report.get("missingness", {}).get("subgroup_audit_completed") is True,
        "unknown_not_zero": report.get("missingness", {}).get("missing_source_row_policy") == "UNKNOWN_NOT_ZERO",
        "early_season_null_policy": report.get("missingness", {}).get("early_season_policy") == "NULL_PLUS_SAMPLE_COUNTS",
        "dataset_residual_eligible": report.get("acceptance_gates", {}).get("dataset_eligible_for_training_free_residual_audit") is True,
    }

    zero_quality_fields = (
        "duplicate_target_game_team_keys",
        "duplicate_target_game_keys",
        "duplicate_target_game_team_player_keys",
        "source_time_violations",
        "identity_ambiguities",
        "source_index_mismatches",
        "non_finite_feature_values",
        "bounded_feature_violations",
        "fuzzy_identity_rows",
        "target_game_source_rows_used",
        "same_day_source_rows_used",
        "future_source_rows_used",
        "market_feature_rows_used",
    )
    quality = report.get("quality", {})
    for field in zero_quality_fields:
        checks[f"quality_{field}_zero"] = quality.get(field) == 0

    locks = report.get("preserved_locks", {})
    checks.update(
        {
            "model_training_not_authorized": locks.get("model_training_authorized") is False,
            "model_retraining_not_executed": locks.get("model_retraining_executed") is False,
            "model_refit_not_executed": locks.get("model_refit_executed") is False,
            "calibration_not_changed": locks.get("calibration_change_executed") is False,
            "strict_t60_not_qualified": locks.get("strict_t60_qualified") is False,
            "market_backtest_not_allowed": locks.get("formal_market_backtest_allowed") is False,
            "betting_edge_not_allowed": locks.get("betting_edge_claim_allowed") is False,
            "formal_stake_zero": locks.get("formal_stake") == 0,
        }
    )

    failed = sorted(name for name, passed in checks.items() if not passed)
    validation = {
        "schema_version": "prior-only-player-rotation-state-features-2025-26-validation-v1",
        "formal_state": VALIDATION_FORMAL_STATE if not failed else "PRIOR_ONLY_PLAYER_ROTATION_STATE_FEATURES_2025_26_INVALID",
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "checks_failed": len(failed),
        "failed_checks": failed,
        "checks": checks,
        "feature_ready_independent_games": report.get("coverage", {}).get("feature_ready_independent_games"),
        "feature_ready_rate": report.get("coverage", {}).get("feature_ready_rate"),
        "teams_with_feature_ready_rows": report.get("coverage", {}).get("teams_with_feature_ready_rows"),
        "months_with_feature_ready_games": report.get("coverage", {}).get("months_with_feature_ready_games"),
        "next_unique_sub_mainline": report.get("next_unique_sub_mainline"),
        "model_training_authorized": False,
        "formal_market_backtest_allowed": False,
        "formal_stake": 0,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(validation, ensure_ascii=False, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
