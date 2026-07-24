#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
from pathlib import Path

SCRIPT = Path("scripts/run_training_free_prior_only_rotation_residual_audit_2025_26_v1.py")
DESIGN = Path("data/research/training-free-prior-only-rotation-residual-audit-2025-26-v1.json")
BINDING = Path("data/research/training-free-prior-only-rotation-residual-audit-2025-26-v1-column-binding-amendment.json")
DOC = Path("docs/training-free-prior-only-rotation-residual-audit-executor-v1.md")
STATUS = Path("data/research/training-free-prior-only-rotation-residual-audit-executor-status-v1.json")
OUT = Path("validation-output/training-free-prior-only-rotation-residual-audit-executor-v1.json")
FORMAL = "TRAINING_FREE_PRIOR_ONLY_ROTATION_RESIDUAL_AUDIT_EXECUTOR_V1_VALID"
NEXT = "RESTORE_EXACT_PRIVATE_MODEL_MARKET_JOIN_AND_EXECUTE_BOUND_TRAINING_FREE_ROTATION_RESIDUAL_AUDIT"

EXPECTED_PHYSICAL = {
    "diff_rotation_players_prior_5",
    "diff_top5_minutes_share_prior_5",
    "diff_top8_minutes_share_prior_5",
    "diff_top8_minutes_share_prior_10",
    "diff_rotation_entropy_prior_5",
    "diff_rotation_entropy_prior_10",
    "diff_top8_set_continuity_prior_5",
    "diff_starter_set_continuity_prior_5",
    "diff_minutes_allocation_volatility_prior_5",
    "diff_role_change_magnitude_prior_3_vs_10",
    "diff_recent_return_players_count",
    "diff_new_team_rotation_players_prior_5",
}


def main() -> int:
    source = SCRIPT.read_text(encoding="utf-8")
    tree = ast.parse(source)
    design = json.loads(DESIGN.read_text(encoding="utf-8"))
    binding = json.loads(BINDING.read_text(encoding="utf-8"))
    status = json.loads(STATUS.read_text(encoding="utf-8"))
    document = DOC.read_text(encoding="utf-8")
    checks: dict[str, bool] = {}

    def check(name: str, value: bool) -> None:
        checks[name] = bool(value)

    imports = set()
    calls = set()
    functions = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add(node.module or "")
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
        elif isinstance(node, ast.FunctionDef):
            functions.add(node.name)

    for name in (
        "execute",
        "self_test",
        "build_stress",
        "bootstrap_spearman",
        "bh_adjust",
        "chronological_halves",
        "monthly_correlations",
    ):
        check(f"function_{name}", name in functions)

    check("numpy_imported", "numpy" in imports)
    check("scipy_stats_imported", "scipy.stats" in imports)
    check("no_sklearn_import", not any(name.startswith("sklearn") for name in imports))
    check("no_fit_call", "fit" not in calls)
    check("no_fit_predict_call", "fit_predict" not in calls)
    check("no_partial_fit_call", "partial_fit" not in calls)
    check("no_predict_call", "predict" not in calls)
    check("no_ev_calculation", '"ev_calculated": False' in source)
    check("no_roi_calculation", '"roi_calculated": False' in source)
    check("no_clv_calculation", '"clv_calculated": False' in source)
    check("no_drawdown_calculation", '"drawdown_calculated": False' in source)
    check("stake_zero", '"formal_stake": 0' in source)
    check("strict_t60_false", '"strict_t60_qualified": False' in source)
    check("market_backtest_false", '"formal_market_backtest_allowed": False' in source)
    check("public_game_rows_zero", '"public_game_level_rows": 0' in source)
    check("public_player_rows_zero", '"public_player_rows": 0' in source)
    check("public_price_rows_zero", '"public_price_rows": 0' in source)
    check("exact_sha_validation", source.count("validate_file_digest(") >= 4)
    check("exact_unique_joins", source.count("exact_unique(") >= 4)
    check("bound_column_mapping_used", "canonical_to_physical_column_mapping" in source)
    check("physical_mapping_exact", set(binding["canonical_to_physical_column_mapping"].values()) == EXPECTED_PHYSICAL)
    check("identity_target_game_id", binding["identity_and_readiness_columns"]["game_id"] == "target_game_id")
    check("model_expected_1075", design["populations"]["primary_model_residual_population"]["expected_rows"] == 1075)
    check("model_min_1000", design["populations"]["primary_model_residual_population"]["minimum_rows"] == 1000)
    check("market_min_200", design["populations"]["primary_market_residual_population"]["minimum_rows"] == 200)
    check("sensitivity_15_30_60", [item["maximum_nominal_t60_batch_error_minutes"] for item in design["populations"]["market_sensitivity_populations"]] == [15, 30, 60])
    check("bootstrap_5000", design["uncertainty_and_robustness"]["bootstrap_resamples"] == 5000)
    check("seed_fixed", design["uncertainty_and_robustness"]["bootstrap_seed"] == 20260725)
    check("h1_negative", design["primary_hypotheses"]["model_signed_residual"]["predeclared_direction"] == "negative")
    check("h2_positive", design["primary_hypotheses"]["market_relative_error"]["predeclared_direction"] == "positive")
    check("bh_q10", "0.10" in design["secondary_tests"]["multiple_testing"])
    check("self_test_real_execution_false", '"real_private_residual_audit_executed": False' in source)
    check("real_requires_market_join", "--market-join" in source and "--features, --predictions and --market-join" in source and "outside --self-test" in source)
    check("no_committed_result_record", not Path("data/research/training-free-prior-only-rotation-residual-audit-2025-26-result-v1.json").exists())

    check("status_schema", status["schema_version"] == "training-free-prior-only-rotation-residual-audit-executor-status-v1")
    check("status_ready_blocked", status["formal_state"] == "TRAINING_FREE_PRIOR_ONLY_ROTATION_RESIDUAL_AUDIT_EXECUTOR_READY_PRIVATE_JOIN_REQUIRED")
    check("status_real_not_executed", status["implementation"]["real_private_residual_audit_executed"] is False)
    check("status_no_result", status["implementation"]["real_residual_result_recorded"] is False)
    check("status_blocker", status["blocker"]["code"] == "EXACT_PRIVATE_MODEL_MARKET_JOIN_NOT_AVAILABLE")
    check("status_no_partial_h1", status["blocker"]["partial_h1_execution_allowed"] is False)
    check("status_market_digest", status["bound_inputs"]["private_model_market_join_sha256"] == "sha256:fbd5b0133cd0ad58f3fe4dada53e79b0fd2ea6021d8179f648f727c76a96735b")
    check("status_next", status["next_unique_mainline"] == NEXT)

    for marker, name in (
        ("EXECUTOR_READY", "doc_ready"),
        ("EXACT_PRIVATE_MODEL_MARKET_JOIN_NOT_AVAILABLE", "doc_blocker"),
        ("8603761824", "doc_feature_artifact"),
        ("8592208938", "doc_prediction_artifact"),
        ("fbd5b0133cd0ad58f3fe4dada53e79b0fd2ea6021d8179f648f727c76a96735b", "doc_market_digest"),
        ("Formal Stake: 0", "doc_stake"),
        (NEXT, "doc_next"),
    ):
        check(name, marker in document)

    failed = sorted(name for name, value in checks.items() if not value)
    output = {
        "schema_version": 1,
        "formal_state": FORMAL if not failed else "TRAINING_FREE_PRIOR_ONLY_ROTATION_RESIDUAL_AUDIT_EXECUTOR_V1_INVALID",
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "checks_failed": len(failed),
        "failed_checks": failed,
        "real_private_residual_audit_executed": False,
        "execution_blocker": "EXACT_PRIVATE_MODEL_MARKET_JOIN_NOT_AVAILABLE",
        "model_training_authorized": False,
        "model_promotion_authorized": False,
        "strict_t60_qualified": False,
        "formal_market_backtest_allowed": False,
        "formal_stake": 0,
        "next_unique_mainline": NEXT,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
