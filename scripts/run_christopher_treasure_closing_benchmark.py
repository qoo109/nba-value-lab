#!/usr/bin/env python3
"""Run a closing-market benchmark for Christopher Treasure's NBA odds archive.

The Kaggle dataset uses a team-centric schema: each game is normally represented twice,
once from each team's perspective. This adapter converts those mirrored rows into one
canonical home-versus-away closing moneyline record, computes no-vig probabilities, joins
against walk-forward predictions, and deletes game-level odds before artifact upload.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd

from evaluate_closing_market_benchmark import evaluate
from import_closing_odds_archive import (
    american_to_decimal,
    as_american,
    parse_game_date,
    team_abbr,
    utc_now,
)

VERSION = "christopher-treasure-closing-adapter-v1"
REQUIRED_NORMALIZED_COLUMNS = {
    "date",
    "season",
    "team",
    "home_visitor",
    "opponent",
    "moneyline",
    "opponentmoneyline",
}


def norm_col(value: Any) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def download_dataset(handle: str, destination: Path) -> Path:
    try:
        import kagglehub
    except ImportError as exc:
        raise RuntimeError("kagglehub is required for live dataset download") from exc

    destination.mkdir(parents=True, exist_ok=True)
    try:
        resolved = kagglehub.dataset_download(
            handle,
            force_download=True,
            output_dir=str(destination),
        )
    except Exception as exc:
        raise RuntimeError(
            "Kaggle download failed. Add KAGGLE_API_TOKEN only if Kaggle requires authentication. "
            f"Original error: {type(exc).__name__}: {exc}"
        ) from exc
    return Path(resolved)


def find_source_file(root: Path) -> Path:
    matches = [
        path
        for path in root.rglob("*")
        if path.is_file() and path.name.lower() == "oddsdata.csv"
    ]
    if not matches:
        csv_files = [path for path in root.rglob("*.csv") if path.is_file()]
        if len(csv_files) == 1:
            return csv_files[0]
        raise ValueError("Christopher Treasure oddsData.csv was not found")
    return max(matches, key=lambda path: path.stat().st_size)


def canonical_site(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"h", "home"} or text.startswith("h"):
        return "H"
    if text in {"v", "visitor", "a", "away"} or text.startswith(("v", "a")):
        return "V"
    raise ValueError(f"unknown home/visitor value: {value!r}")


def normalize_team_centric_archive(
    source_path: Path,
    output_path: Path,
    source_id: str,
) -> dict[str, Any]:
    frame = pd.read_csv(source_path)
    rename = {str(column): norm_col(column) for column in frame.columns}
    frame = frame.rename(columns=rename)
    missing = sorted(REQUIRED_NORMALIZED_COLUMNS - set(frame.columns))
    if missing:
        raise ValueError(f"Christopher Treasure archive missing columns: {missing}")

    source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    canonical: dict[tuple[str, str, str], dict[str, Any]] = {}
    invalid_rows = 0
    mirrored_rows_deduplicated = 0
    inconsistent_mirrors = 0
    invalid_overround = 0

    for _, item in frame.iterrows():
        try:
            game_date = parse_game_date(item["date"], None)
            site = canonical_site(item["home_visitor"])
            team = team_abbr(item["team"])
            opponent = team_abbr(item["opponent"])
            team_ml = as_american(item["moneyline"])
            opponent_ml = as_american(item["opponentmoneyline"])
            if site == "H":
                home_team, away_team = team, opponent
                home_ml, away_ml = team_ml, opponent_ml
            else:
                home_team, away_team = opponent, team
                home_ml, away_ml = opponent_ml, team_ml
        except Exception:
            invalid_rows += 1
            continue

        key = (game_date, home_team, away_team)
        existing = canonical.get(key)
        if existing is not None:
            mirrored_rows_deduplicated += 1
            if (
                existing["home_moneyline_american"] != home_ml
                or existing["away_moneyline_american"] != away_ml
            ):
                inconsistent_mirrors += 1
                existing["quality_flags"].add("inconsistent_mirrored_moneyline")
            continue

        home_decimal = american_to_decimal(home_ml)
        away_decimal = american_to_decimal(away_ml)
        home_implied = 1.0 / home_decimal
        away_implied = 1.0 / away_decimal
        total_implied = home_implied + away_implied
        overround = total_implied - 1.0
        flags = {"closing_timestamp_unavailable", "team_centric_mirrored_source"}
        if not -0.05 <= overround <= 0.30:
            invalid_overround += 1
            flags.add("overround_outside_expected_range")

        canonical[key] = {
            "game_date": game_date,
            "home_team_abbr": home_team,
            "away_team_abbr": away_team,
            "home_moneyline_american": home_ml,
            "away_moneyline_american": away_ml,
            "home_price_decimal": round(home_decimal, 8),
            "away_price_decimal": round(away_decimal, 8),
            "home_implied_probability": round(home_implied, 10),
            "away_implied_probability": round(away_implied, 10),
            "overround": round(overround, 10),
            "fair_home_probability": round(home_implied / total_implied, 10),
            "fair_away_probability": round(away_implied / total_implied, 10),
            "snapshot_label": "Closing",
            "timestamp_quality": "closing_label_only",
            "source_id": source_id,
            "source_file_sha256": source_hash,
            "adapter_version": VERSION,
            "quality_flags": flags,
        }

    rows = []
    for item in canonical.values():
        row = dict(item)
        row["quality_flags"] = ",".join(sorted(row["quality_flags"]))
        rows.append(row)
    rows.sort(key=lambda row: (row["game_date"], row["home_team_abbr"], row["away_team_abbr"]))
    if not rows:
        raise ValueError("No valid closing moneyline games were produced from oddsData.csv")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output_path, index=False)
    seasons = sorted(
        {
            int(row["game_date"][:4])
            if int(row["game_date"][5:7]) >= 7
            else int(row["game_date"][:4]) - 1
            for row in rows
        }
    )
    return {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "source": {
            "source_id": source_id,
            "input_file": source_path.name,
            "input_sha256": source_hash,
            "detected_schema": "team_centric_mirrored_rows",
            "detected_columns": list(frame.columns),
        },
        "coverage": {
            "input_rows": int(len(frame)),
            "normalized_games": int(len(rows)),
            "season_start_years": seasons,
            "season_count": len(seasons),
        },
        "quality": {
            "invalid_rows_excluded": invalid_rows,
            "mirrored_rows_deduplicated": mirrored_rows_deduplicated,
            "inconsistent_mirrored_moneylines": inconsistent_mirrors,
            "overround_outside_expected_range": invalid_overround,
            "exact_observation_timestamps_available": False,
            "same_bookmaker_open_to_close_history_available": False,
        },
        "decision": {
            "ready_for_closing_market_benchmark": len(rows) >= 500 and len(seasons) >= 3,
            "ready_for_point_in_time_odds_layer": False,
            "ready_for_clv_analysis": False,
            "ready_for_entry_price_roi_backtest": False,
            "ready_for_betting_edge_claim": False,
        },
    }


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
    }

    with tempfile.TemporaryDirectory(prefix="nbavl-christopher-treasure-") as temp_name:
        temp = Path(temp_name)
        try:
            root = download_dataset(dataset_handle, temp / "download") if dataset_handle else Path(dataset_root)
            status["download_complete"] = True
            source_path = find_source_file(root)
            normalized_path = output_dir / "selected-import" / "closing-moneyline-normalized.csv"
            import_report = normalize_team_centric_archive(source_path, normalized_path, source_id)
            (output_dir / "kaggle-selected-import-report.json").write_text(
                json.dumps(import_report, indent=2) + "\n", encoding="utf-8"
            )
            manifest = {
                "schema_version": VERSION,
                "selected": {
                    "path": str(source_path.relative_to(root)),
                    "size_bytes": source_path.stat().st_size,
                    "input_sha256": import_report["source"]["input_sha256"],
                    "detected_schema": import_report["source"]["detected_schema"],
                    "detected_columns": import_report["source"]["detected_columns"],
                    "normalized_games": import_report["coverage"]["normalized_games"],
                    "season_count": import_report["coverage"]["season_count"],
                },
                "raw_rows_uploaded": False,
            }
            (output_dir / "kaggle-candidate-manifest.json").write_text(
                json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
            )
            benchmark_report = evaluate(predictions, normalized_path, output_dir / "benchmark")
            joined_path = output_dir / "benchmark" / "closing-benchmark-joined.csv"
            if joined_path.exists():
                joined_path.unlink()
            status.update(
                {
                    "benchmark_complete": True,
                    "matched_games": benchmark_report["coverage"]["matched_games"],
                    "matched_seasons": benchmark_report["coverage"]["matched_seasons"],
                    "ready_for_market_accuracy_comparison": benchmark_report["decision"]["ready_for_market_accuracy_comparison"],
                }
            )
        except Exception as exc:
            status["error"] = f"{type(exc).__name__}: {exc}"
            (output_dir / "kaggle-run-status.json").write_text(
                json.dumps(status, indent=2) + "\n", encoding="utf-8"
            )
            raise

    normalized_path = output_dir / "selected-import" / "closing-moneyline-normalized.csv"
    if normalized_path.exists():
        normalized_path.unlink()
    status["temporary_raw_and_normalized_files_deleted"] = True
    (output_dir / "kaggle-run-status.json").write_text(
        json.dumps(status, indent=2) + "\n", encoding="utf-8"
    )
    return status


def self_test(output_dir: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="nbavl-christopher-test-") as temp_name:
        root = Path(temp_name)
        dataset = root / "dataset"
        dataset.mkdir()
        pd.DataFrame(
            [
                {"date": "2022-10-18", "season": 2023, "team": "Boston", "home/visitor": "H", "opponent": "Philadelphia", "score": 126, "opponentScore": 117, "moneyLine": -140, "opponentMoneyLine": 120, "total": 214.5, "spread": -3, "secondHalfTotal": 108.5},
                {"date": "2022-10-18", "season": 2023, "team": "Philadelphia", "home/visitor": "V", "opponent": "Boston", "score": 117, "opponentScore": 126, "moneyLine": 120, "opponentMoneyLine": -140, "total": 214.5, "spread": 3, "secondHalfTotal": 108.5},
                {"date": "2022-10-19", "season": 2023, "team": "Phoenix", "home/visitor": "H", "opponent": "Dallas", "score": 107, "opponentScore": 105, "moneyLine": -130, "opponentMoneyLine": 110, "total": 218.0, "spread": -2, "secondHalfTotal": 109.0},
                {"date": "2022-10-19", "season": 2023, "team": "Dallas", "home/visitor": "V", "opponent": "Phoenix", "score": 105, "opponentScore": 107, "moneyLine": 110, "opponentMoneyLine": -130, "total": 218.0, "spread": 2, "secondHalfTotal": 109.0},
            ]
        ).to_csv(dataset / "oddsData.csv", index=False)
        predictions = root / "predictions.csv"
        pd.DataFrame(
            [
                {"test_season": "2022-23", "game_id": "1", "game_date": "2022-10-18", "home_team_abbr": "BOS", "away_team_abbr": "PHI", "actual_home_win": 1, "predicted_home_win_probability": 0.62},
                {"test_season": "2022-23", "game_id": "2", "game_date": "2022-10-19", "home_team_abbr": "PHX", "away_team_abbr": "DAL", "actual_home_win": 1, "predicted_home_win_probability": 0.54},
            ]
        ).to_csv(predictions, index=False)
        status = run(output_dir, predictions, "self_test_christopher", dataset_root=dataset)
        assert status["benchmark_complete"] is True, status
        assert status["matched_games"] == 2, status
        report = json.loads((output_dir / "kaggle-selected-import-report.json").read_text())
        assert report["coverage"]["normalized_games"] == 2, report
        assert report["quality"]["mirrored_rows_deduplicated"] == 2, report
        assert not (output_dir / "selected-import" / "closing-moneyline-normalized.csv").exists()
        (output_dir / "self-test.json").write_text('{"passed":true}\n', encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-handle")
    parser.add_argument("--dataset-root", type=Path)
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--source-id", default="kaggle_christophertreasure_nba_odds")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("Christopher Treasure closing adapter self-test passed")
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
