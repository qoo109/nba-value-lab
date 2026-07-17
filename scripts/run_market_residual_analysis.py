#!/usr/bin/env python3
"""Run market residual analysis with the Christopher Treasure closing archive safely."""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from analyze_market_residuals import analyze
from run_christopher_treasure_closing_benchmark import (
    align_schedule_keys,
    download_dataset,
    find_source_file,
    normalize_team_centric_archive,
)

VERSION = "market-residual-analysis-runner-v1"


def run(
    output_dir: Path,
    predictions: Path,
    source_id: str,
    dataset_handle: str | None = None,
    dataset_root: Path | None = None,
) -> dict[str, Any]:
    if bool(dataset_handle) == bool(dataset_root):
        raise ValueError("Provide exactly one of dataset_handle or dataset_root")
    output_dir.mkdir(parents=True, exist_ok=True)
    status: dict[str, Any] = {
        "schema_version": VERSION,
        "dataset_handle": dataset_handle,
        "source_id": source_id,
        "anonymous_download_attempted": not bool(os.environ.get("KAGGLE_API_TOKEN")),
        "kaggle_api_token_present": bool(os.environ.get("KAGGLE_API_TOKEN")),
        "raw_files_committed": False,
        "raw_files_uploaded_as_artifact": False,
        "joined_game_rows_uploaded_as_artifact": False,
    }

    with tempfile.TemporaryDirectory(prefix="nbavl-market-residual-run-") as temp_name:
        temp = Path(temp_name)
        try:
            dataset = (
                download_dataset(dataset_handle, temp / "download")
                if dataset_handle
                else Path(dataset_root)
            )
            status["download_complete"] = True
            source_path = find_source_file(dataset)
            normalized_path = temp / "closing-moneyline-normalized.csv"
            import_report = normalize_team_centric_archive(
                source_path, normalized_path, source_id
            )
            alignment = align_schedule_keys(normalized_path, predictions)
            import_report["schedule_alignment"] = alignment
            import_report["quality"]["schedule_alignment_uses_outcomes"] = False
            import_report["quality"]["schedule_alignment_uses_model_probabilities"] = False
            import_report["artifact_policy"] = {
                "raw_rows_uploaded": False,
                "normalized_game_rows_uploaded": False,
                "reports_and_aggregate_segments_only": True,
            }
            (output_dir / "market-residual-import-report.json").write_text(
                json.dumps(import_report, indent=2) + "\n", encoding="utf-8"
            )

            report = analyze(predictions, normalized_path, output_dir / "analysis")
            status.update(
                {
                    "market_residual_analysis_complete": True,
                    "matched_games": report["coverage"]["matched_games"],
                    "matched_seasons": report["coverage"]["matched_seasons"],
                    "forward_holdout_complete": report["decision"][
                        "forward_holdout_complete"
                    ],
                    "incremental_model_signal_detected": report["decision"][
                        "incremental_model_signal_detected"
                    ],
                    "schedule_alignment": alignment["selected"],
                }
            )
        except Exception as exc:
            status["error"] = f"{type(exc).__name__}: {exc}"
            (output_dir / "market-residual-run-status.json").write_text(
                json.dumps(status, indent=2) + "\n", encoding="utf-8"
            )
            raise

    status["temporary_raw_and_normalized_files_deleted"] = True
    (output_dir / "market-residual-run-status.json").write_text(
        json.dumps(status, indent=2) + "\n", encoding="utf-8"
    )
    return status


def self_test(output_dir: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="nbavl-market-residual-wrapper-") as temp_name:
        root = Path(temp_name)
        dataset = root / "dataset"
        dataset.mkdir()
        predictions_path = root / "predictions.csv"
        source_rows: list[dict[str, Any]] = []
        prediction_rows: list[dict[str, Any]] = []
        pairs = [
            ("Boston", "Philadelphia", "BOS", "PHI"),
            ("Phoenix", "Dallas", "PHX", "DAL"),
            ("Milwaukee", "Brooklyn", "MIL", "BKN"),
            ("Denver", "Utah", "DEN", "UTA"),
        ]
        rng = np.random.default_rng(7)
        start = pd.Timestamp("2021-10-01")
        for index in range(120):
            home_name, away_name, home_abbr, away_abbr = pairs[index % len(pairs)]
            date = (start + pd.Timedelta(days=index)).date().isoformat()
            market = float(rng.uniform(0.38, 0.72))
            home_ml = -130 if market >= 0.5 else 120
            away_ml = 110 if market >= 0.5 else -140
            actual = int(rng.random() < market)
            model = float(np.clip(market + rng.normal(0, 0.04), 0.05, 0.95))
            prediction_rows.append(
                {
                    "test_season": "2021-22" if index < 80 else "2022-23",
                    "game_id": str(index + 1),
                    "game_date": date,
                    "home_team_abbr": home_abbr,
                    "away_team_abbr": away_abbr,
                    "actual_home_win": actual,
                    "predicted_home_win_probability": model,
                }
            )
            source_rows.extend(
                [
                    {
                        "date": date,
                        "season": 2022 if index < 80 else 2023,
                        "team": home_name,
                        "home/visitor": "V",
                        "opponent": away_name,
                        "moneyLine": home_ml,
                        "opponentMoneyLine": away_ml,
                    },
                    {
                        "date": date,
                        "season": 2022 if index < 80 else 2023,
                        "team": away_name,
                        "home/visitor": "H",
                        "opponent": home_name,
                        "moneyLine": away_ml,
                        "opponentMoneyLine": home_ml,
                    },
                ]
            )
        pd.DataFrame(source_rows).to_csv(dataset / "oddsData.csv", index=False)
        pd.DataFrame(prediction_rows).to_csv(predictions_path, index=False)
        status = run(
            output_dir,
            predictions_path,
            "self_test_market_residual",
            dataset_root=dataset,
        )
        assert status["market_residual_analysis_complete"] is True, status
        assert status["matched_games"] == 120, status
        assert status["schedule_alignment"]["swap_home_away"] is True, status
        assert status["temporary_raw_and_normalized_files_deleted"] is True
        report = json.loads(
            (output_dir / "analysis/market-residual-analysis-report.json").read_text()
        )
        assert report["guardrails"]["roi_computed"] is False
        assert report["decision"]["ready_for_betting_edge_claim"] is False
        (output_dir / "self-test.json").write_text(
            '{"passed":true}\n', encoding="utf-8"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-handle")
    parser.add_argument("--dataset-root", type=Path)
    parser.add_argument("--predictions", type=Path)
    parser.add_argument(
        "--source-id", default="kaggle_christophertreasure_nba_odds"
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("market residual runner self-test passed")
        return
    if not args.predictions:
        parser.error("--predictions is required unless --self-test is used")
    status = run(
        args.output_dir,
        args.predictions,
        args.source_id,
        dataset_handle=args.dataset_handle,
        dataset_root=args.dataset_root,
    )
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
