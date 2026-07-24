#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "data" / "research" / "frozen-model-forward-score-2025-26-result-v1.json"
DOC = ROOT / "docs" / "frozen-model-forward-score-2025-26-result-v1.md"
HANDOFF = ROOT / "docs" / "handoffs" / "nba_value_lab_handoff_2026-07-24_frozen_model_forward_score_2025_26.md"


def main() -> int:
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")
    handoff = HANDOFF.read_text(encoding="utf-8")
    tests = 0

    def check(condition: bool, label: str) -> None:
        nonlocal tests
        assert condition, label
        tests += 1

    check(record["formal_state"] == "FROZEN_MODEL_FORWARD_SCORE_2025_26_PASS_RECORDED", "formal state")
    evidence = record["execution_evidence"]
    check(evidence["branch_head"] == "daacc74f5500f73b6816933af7e4fa8f3c9616f9", "execution head")
    check(evidence["workflow_run"] == 30081647871, "run")
    check(evidence["job"] == 89444366089, "job")
    check(evidence["artifact_id"] == 8592067225, "artifact")
    check(evidence["artifact_digest"] == "sha256:b366f12085208182845e96eeb9e6782415dd499ba2010146373ae23eb2278a9f", "artifact digest")
    check(evidence["artifact_inspected"] is True, "artifact inspected")

    frozen = record["frozen_model"]
    check(frozen["artifact_id"] == 8396002523, "model artifact")
    check(frozen["artifact_sha256"] == "sha256:6063adac9851b47d339a93e35935115008b736a16925548d36a8c54a0353b41b", "model artifact digest")
    check(frozen["model_file_sha256"] == "sha256:007ce32cc5a80df3b87554d13847d388e2ca6cbf6122f00df2d4e87d5b49a343", "model hash")
    check(frozen["version"] == "walk-forward-v2", "version")
    check(frozen["training_seasons"] == ["2019-20", "2020-21", "2021-22", "2022-23", "2023-24"], "training seasons")
    check(frozen["selected_probability_method"] == "raw_logistic_elo", "method")
    check(frozen["fit_or_refit_calls_executed"] == 0, "no fit")
    check(frozen["calibration_applied"] is False, "no calibration")

    population = record["population"]
    check(population["frozen_training_elo_games"] == 5824, "training games")
    check(population["frozen_training_exclusions"] == ["22301177", "22301195"], "exclusions")
    check(population["state_update_games_2024_25"] == 1230, "2024 state")
    check(population["forward_scored_games_2025_26"] == 1230, "forward rows")
    check(population["first_game_date"] == "2025-10-21", "first date")
    check(population["last_game_date"] == "2026-04-12", "last date")

    gold = record["forward_gold"]
    check(gold["team_rows"] == 2460, "gold team")
    check(gold["matchup_rows"] == 1230, "gold matchups")
    check(gold["point_in_time_violations"] == 0, "PIT")
    check(gold["same_day_games_excluded"] is True, "same day")
    check(gold["season_history_reset"] is True, "season reset")
    check(gold["mature_matchups_prior_20_both_sides"] == 921, "mature matchups")
    check(gold["low_evidence_matchups"] == 79, "low evidence")

    quality = record["probability_quality"]
    model = quality["model"]
    elo = quality["elo_benchmark"]
    check(abs(model["log_loss"] - 0.6008653315472677) < 1e-15, "model log loss")
    check(abs(model["brier_score"] - 0.2068232035389188) < 1e-15, "model brier")
    check(abs(model["accuracy"] - 0.683739837398374) < 1e-15, "model accuracy")
    check(abs(model["roc_auc"] - 0.7327177472868549) < 1e-15, "model AUC")
    check(model["log_loss"] < elo["log_loss"], "log loss improvement")
    check(model["brier_score"] < elo["brier_score"], "brier improvement")
    check(model["accuracy"] > elo["accuracy"], "accuracy improvement")
    check(model["roc_auc"] > elo["roc_auc"], "AUC improvement")
    check(abs(model["ece"] - 0.029773234611016167) < 1e-15, "ECE")

    thresholds = quality["confidence_thresholds"]
    check([row["minimum_selected_side_probability"] for row in thresholds] == [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8], "thresholds")
    check([row["rows"] for row in thresholds] == [1230, 1016, 795, 596, 424, 250, 140], "threshold counts")
    check(all(thresholds[index]["accuracy"] <= thresholds[index + 1]["accuracy"] for index in range(len(thresholds) - 1)), "monotone threshold accuracy")

    bootstrap = quality["paired_game_bootstrap_vs_elo"]
    check(bootstrap["resamples"] == 5000, "bootstrap count")
    check(bootstrap["seed"] == 20260724, "bootstrap seed")
    check(bootstrap["model_minus_elo_log_loss"]["ci95"][1] < 0, "log loss CI below zero")
    check(bootstrap["model_minus_elo_brier"]["ci95"][1] < 0, "brier CI below zero")
    check(bootstrap["model_minus_elo_accuracy"]["ci95"][0] < 0 < bootstrap["model_minus_elo_accuracy"]["ci95"][1], "accuracy CI crosses zero")

    private = record["private_outputs"]
    check(private["prediction_rows"] == 1230, "private prediction rows")
    check(private["predictions_csv_sha256"] == "sha256:c3764faf6eb3703374b12a5d8668c6ef889cd8f54070a2c6cf135b55559ca725", "prediction digest")
    check(private["forward_gold_sqlite_gzip_sha256"] == "sha256:3a9bd07dac35ff2a6c9e880d3637d37ae5e18b5602e740dcfc7e3d3be413aead", "forward gold digest")
    check(private["public_prediction_rows_committed"] == 0, "no public predictions")
    check(private["odds_rows_emitted"] == 0, "no odds")

    qualification = record["qualification"]
    check(qualification["model_only_forward_probability_diagnostic_valid"] is True, "model diagnostic")
    check(qualification["ready_for_private_same_game_odds_sensitivity_join"] is True, "private join readiness")
    for key in ("strict_t60_qualified", "market_backtest_allowed", "clv_allowed", "roi_allowed", "betting_edge_claim_allowed"):
        check(qualification[key] is False, key)
    check(qualification["formal_stake"] == 0, "stake")

    execution = record["execution_boundaries"]
    check(execution["model_retraining_executed"] is False, "no retraining")
    check(execution["model_refit_executed"] is False, "no refit")
    check(execution["market_data_used_as_model_feature"] is False, "no market feature")
    check(execution["odds_join_executed"] is False, "no odds join")
    check(execution["provider_api_requests"] == 0, "no provider requests")
    check(record["next_unique_sub_mainline"] == "JOIN_2025_26_FORWARD_PROBABILITIES_TO_PRIVATE_ALIGNED_ODDS_FOR_TIME_BANDED_SENSITIVITY_ONLY", "next")
    check("not betting win rates" in doc, "interpretation boundary")
    check("Do not retrain" in handoff, "handoff no retraining")
    check("Formal Stake: 0" in doc and "Formal Stake: 0" in handoff, "stake docs")

    qa = {
        "schema_version": 1,
        "formal_state": "FROZEN_MODEL_FORWARD_SCORE_2025_26_RESULT_VALID",
        "real_artifact_bound": True,
        "frozen_model_hash_bound": True,
        "prediction_rows": 1230,
        "point_in_time_violations": 0,
        "model_retraining_executed": False,
        "odds_join_executed": False,
        "market_backtest_unlocked": False,
        "contract_tests": tests,
        "formal_stake": 0,
    }
    path = ROOT / "artifacts" / "frozen-model-forward-score-2025-26-result-validation-v1.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
