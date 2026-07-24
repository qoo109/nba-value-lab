#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

RESULT = Path("data/research/prior-only-player-rotation-state-features-2025-26-result-v1.json")
DOC = Path("docs/prior-only-player-rotation-state-features-2025-26-result-v1.md")
FORMAL_STATE = "PRIOR_ONLY_PLAYER_ROTATION_STATE_FEATURES_2025_26_RESULT_VALID"
NEXT = "PREDECLARE_TRAINING_FREE_PRIOR_ONLY_ROTATION_RESIDUAL_AUDIT_2025_26_V1"


def main() -> int:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")
    checks: dict[str, bool] = {
        "schema": result.get("schema_version") == "prior-only-player-rotation-state-features-2025-26-result-v1",
        "formal_state": result.get("formal_state") == FORMAL_STATE,
        "workflow_success": result.get("execution_evidence", {}).get("workflow_conclusion") == "success",
        "artifact_inspected": result.get("execution_evidence", {}).get("artifact_inspected") is True,
        "artifact_id": result.get("execution_evidence", {}).get("artifact_id") == 8603174927,
        "artifact_digest": result.get("execution_evidence", {}).get("artifact_digest") == "sha256:e164912d2330e9f915e27095d4ec7aa3ff0efe917c6dd406a697f7ce16f3ea0c",
        "source_artifact": result.get("bound_source", {}).get("source_artifact_id") == 8599479933,
        "source_rows": result.get("bound_source", {}).get("source_player_game_rows") == 43265,
        "pit_rule": result.get("bound_source", {}).get("source_time_rule") == "source_game_date_et < target_game_date_et",
        "player_rows": result.get("outputs", {}).get("private_player_feature_rows") == 44196,
        "team_rows": result.get("outputs", {}).get("private_team_feature_rows") == 2460,
        "matchup_rows": result.get("outputs", {}).get("private_matchup_feature_rows") == 1230,
        "public_player_rows_zero": result.get("outputs", {}).get("public_player_rows_committed") == 0,
        "public_game_rows_zero": result.get("outputs", {}).get("public_game_level_feature_rows_committed") == 0,
        "ready_games": result.get("coverage", {}).get("feature_ready_independent_games") == 1075,
        "ready_rate": result.get("coverage", {}).get("feature_ready_rate") == 0.87398374,
        "all_teams": result.get("coverage", {}).get("teams_with_feature_ready_rows") == 30,
        "six_months": result.get("coverage", {}).get("months_with_feature_ready_games") == 6,
        "missingness_audit": result.get("missingness", {}).get("subgroup_audit_completed") is True,
        "unknown_not_zero": result.get("missingness", {}).get("missing_source_row_policy") == "UNKNOWN_NOT_ZERO",
        "validation_38": result.get("quality", {}).get("validation_checks_passed") == 38,
        "validation_failures_zero": result.get("quality", {}).get("validation_checks_failed") == 0,
        "acceptance_pass": result.get("acceptance", {}).get("all_feature_construction_gates_passed") is True,
        "residual_eligible": result.get("acceptance", {}).get("dataset_eligible_for_training_free_residual_audit") is True,
        "next_mainline": result.get("next_unique_mainline") == NEXT,
        "doc_state": FORMAL_STATE in doc,
        "doc_next": NEXT in doc,
        "doc_stake": "Formal Stake above zero" in doc,
    }
    for key, value in result.get("quality", {}).items():
        if key in {"validation_checks_passed", "player_name_fields_found"}:
            continue
        checks[f"quality_{key}_zero"] = value == 0
    checks["quality_player_name_fields_zero"] = result.get("quality", {}).get("player_name_fields_found") == 0

    locks = result.get("preserved_locks", {})
    checks.update({
        "model_training_locked": locks.get("model_training_authorized") is False,
        "retraining_not_executed": locks.get("model_retraining_executed") is False,
        "refit_not_executed": locks.get("model_refit_executed") is False,
        "calibration_not_changed": locks.get("calibration_change_executed") is False,
        "strict_t60_locked": locks.get("strict_t60_qualified") is False,
        "market_backtest_locked": locks.get("formal_market_backtest_allowed") is False,
        "betting_edge_locked": locks.get("betting_edge_claim_allowed") is False,
        "stake_zero": locks.get("formal_stake") == 0,
    })

    failed = sorted(name for name, passed in checks.items() if not passed)
    output = {
        "schema_version": 1,
        "formal_state": "PRIOR_ONLY_PLAYER_ROTATION_STATE_FEATURES_2025_26_RESULT_VALIDATED" if not failed else "PRIOR_ONLY_PLAYER_ROTATION_STATE_FEATURES_2025_26_RESULT_INVALID",
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "checks_failed": len(failed),
        "failed_checks": failed,
        "next_unique_mainline": NEXT,
        "model_training_authorized": False,
        "formal_market_backtest_allowed": False,
        "formal_stake": 0,
    }
    path = Path("validation-output/prior-only-player-rotation-state-features-2025-26-result-v1.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
