#!/usr/bin/env python3
"""Download a Kaggle NBA odds dataset and run the closing-only benchmark safely.

Raw Kaggle files remain in a temporary directory. Only manifests, QA reports and aggregate
benchmark metrics are written to the requested output directory.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd

from evaluate_closing_market_benchmark import evaluate
from import_closing_odds_archive import normalize

VERSION = "kaggle-closing-benchmark-runner-v1"
SUPPORTED_SUFFIXES = {".csv", ".xlsx", ".xls"}


def infer_season_start_year(path: Path) -> int | None:
    years = [int(value) for value in re.findall(r"(?:19|20)\d{2}", path.stem)]
    plausible = [year for year in years if 1990 <= year <= 2035]
    return plausible[0] if plausible else None


def candidate_files(root: Path) -> list[Path]:
    files = [
        path for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    ]
    return sorted(files, key=lambda path: (-path.stat().st_size, str(path).lower()))


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
            "Kaggle download failed. Public datasets are attempted anonymously first; "
            "if Kaggle requires authentication, add a free KAGGLE_API_TOKEN repository secret. "
            f"Original error: {type(exc).__name__}: {exc}"
        ) from exc
    return Path(resolved)


def choose_best_archive(dataset_root: Path, working_root: Path, source_id: str) -> tuple[Path, dict[str, Any]]:
    attempts: list[dict[str, Any]] = []
    best: tuple[int, Path, Path, dict[str, Any]] | None = None

    for index, candidate in enumerate(candidate_files(dataset_root), 1):
        attempt_dir = working_root / f"candidate-{index:03d}"
        try:
            report = normalize(
                candidate,
                attempt_dir,
                source_id,
                infer_season_start_year(candidate),
            )
            normalized = attempt_dir / "closing-moneyline-normalized.csv"
            games = int(report["coverage"]["normalized_games"])
            attempts.append({
                "path": str(candidate.relative_to(dataset_root)),
                "size_bytes": candidate.stat().st_size,
                "status": "parsed",
                "normalized_games": games,
                "season_count": int(report["coverage"]["season_count"]),
                "detected_schema": report["source"]["detected_schema"],
                "input_sha256": report["source"]["input_sha256"],
            })
            if games > 0 and (best is None or games > best[0]):
                best = (games, candidate, normalized, report)
        except Exception as exc:
            attempts.append({
                "path": str(candidate.relative_to(dataset_root)),
                "size_bytes": candidate.stat().st_size,
                "status": "rejected",
                "error": f"{type(exc).__name__}: {exc}",
            })

    manifest = {
        "schema_version": VERSION,
        "dataset_root_file_count": len(candidate_files(dataset_root)),
        "candidate_attempts": attempts,
    }
    if best is None:
        raise ValueError("No supported Kaggle file produced a valid closing moneyline archive")
    _, selected_source, normalized_path, selected_report = best
    manifest["selected"] = {
        "path": str(selected_source.relative_to(dataset_root)),
        "normalized_games": int(selected_report["coverage"]["normalized_games"]),
        "season_count": int(selected_report["coverage"]["season_count"]),
        "input_sha256": selected_report["source"]["input_sha256"],
    }
    return normalized_path, manifest


def run(
    output_dir: Path,
    source_id: str,
    predictions: Path,
    dataset_handle: str | None = None,
    dataset_root: Path | None = None,
) -> dict[str, Any]:
    if bool(dataset_handle) == bool(dataset_root):
        raise ValueError("Provide exactly one of dataset_handle or dataset_root")
    output_dir.mkdir(parents=True, exist_ok=True)

    status = {
        "schema_version": VERSION,
        "dataset_handle": dataset_handle,
        "source_id": source_id,
        "anonymous_download_attempted": not bool(os.environ.get("KAGGLE_API_TOKEN")),
        "kaggle_api_token_present": bool(os.environ.get("KAGGLE_API_TOKEN")),
        "raw_files_committed": False,
        "raw_files_uploaded_as_artifact": False,
    }

    with tempfile.TemporaryDirectory(prefix="nbavl-kaggle-closing-") as temp_name:
        temp = Path(temp_name)
        try:
            resolved_root = download_dataset(dataset_handle, temp / "download") if dataset_handle else Path(dataset_root)
            status["download_complete"] = True
            normalized_path, manifest = choose_best_archive(resolved_root, temp / "attempts", source_id)
            selected_dir = output_dir / "selected-import"
            selected_dir.mkdir(exist_ok=True)
            shutil.copy2(normalized_path, selected_dir / "closing-moneyline-normalized.csv")

            selected_attempt = next(
                item for item in manifest["candidate_attempts"]
                if item.get("path") == manifest["selected"]["path"] and item.get("status") == "parsed"
            )
            import_report = {
                "schema_version": VERSION,
                "source_id": source_id,
                "dataset_handle": dataset_handle,
                "selected_file": manifest["selected"],
                "selected_attempt": selected_attempt,
                "guardrails": {
                    "closing_label_only": True,
                    "exact_observation_timestamp_available": False,
                    "roi_allowed": False,
                    "clv_allowed": False,
                    "raw_dataset_redistributed": False,
                },
            }
            (output_dir / "kaggle-selected-import-report.json").write_text(
                json.dumps(import_report, indent=2) + "\n", encoding="utf-8"
            )
            (output_dir / "kaggle-candidate-manifest.json").write_text(
                json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
            )

            benchmark_dir = output_dir / "benchmark"
            benchmark_report = evaluate(
                predictions,
                selected_dir / "closing-moneyline-normalized.csv",
                benchmark_dir,
            )
            joined_path = benchmark_dir / "closing-benchmark-joined.csv"
            if joined_path.exists():
                joined_path.unlink()
            status["benchmark_complete"] = True
            status["matched_games"] = benchmark_report["coverage"]["matched_games"]
            status["matched_seasons"] = benchmark_report["coverage"]["matched_seasons"]
            status["ready_for_market_accuracy_comparison"] = benchmark_report["decision"]["ready_for_market_accuracy_comparison"]
        except Exception as exc:
            status["error"] = f"{type(exc).__name__}: {exc}"
            (output_dir / "kaggle-run-status.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
            raise

    normalized_output = output_dir / "selected-import" / "closing-moneyline-normalized.csv"
    if normalized_output.exists():
        normalized_output.unlink()
    status["temporary_raw_and_normalized_files_deleted"] = True
    (output_dir / "kaggle-run-status.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    return status


def self_test(output_dir: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="nbavl-kaggle-runner-test-") as temp_name:
        root = Path(temp_name)
        dataset = root / "dataset"
        dataset.mkdir()
        pd.DataFrame([{"not_odds": 1}]).to_csv(dataset / "invalid.csv", index=False)
        pd.DataFrame([
            {"Date": 1018, "Rot": 501, "VH": "V", "Team": "Philadelphia", "ML": 120},
            {"Date": 1018, "Rot": 502, "VH": "H", "Team": "Boston", "ML": -140},
            {"Date": 1019, "Rot": 503, "VH": "V", "Team": "Dallas", "ML": 110},
            {"Date": 1019, "Rot": 504, "VH": "H", "Team": "Phoenix", "ML": -130},
        ]).to_csv(dataset / "nbaodds2022.csv", index=False)
        predictions = root / "predictions.csv"
        pd.DataFrame([
            {"test_season": "2022-23", "game_id": "1", "game_date": "2022-10-18", "home_team_abbr": "BOS", "away_team_abbr": "PHI", "actual_home_win": 1, "predicted_home_win_probability": 0.62},
            {"test_season": "2022-23", "game_id": "2", "game_date": "2022-10-19", "home_team_abbr": "PHX", "away_team_abbr": "DAL", "actual_home_win": 0, "predicted_home_win_probability": 0.54},
        ]).to_csv(predictions, index=False)
        status = run(output_dir, "self_test_kaggle", predictions, dataset_root=dataset)
        assert status["benchmark_complete"] is True
        assert status["matched_games"] == 2
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
        print("Kaggle closing benchmark runner self-test passed")
        return
    if not args.predictions:
        parser.error("--predictions is required unless --self-test is used")
    status = run(
        args.output_dir,
        args.source_id,
        args.predictions,
        dataset_handle=args.dataset_handle,
        dataset_root=args.dataset_root,
    )
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
