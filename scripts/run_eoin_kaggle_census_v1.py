#!/usr/bin/env python3
"""Download the Eoin Kaggle dataset and run aggregate-only CSV census.

Raw Kaggle files remain in temporary storage. Only aggregate reports, hashes,
coverage placeholders, and run status are written to the output directory.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any

import run_eoin_csv_census_v1 as census
import run_eoin_internal_qualification_v1 as qualification

VERSION = "eoin-kaggle-census-v1"
DEFAULT_DATASET_HANDLE = "eoinamoore/historical-nba-data-and-player-box-scores"


def download_dataset(handle: str, destination: Path) -> Path:
    try:
        import kagglehub
    except ImportError as exc:
        raise RuntimeError("kagglehub is required for Kaggle dataset download") from exc

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


def file_inventory(root: Path) -> dict[str, Any]:
    files = [path for path in root.rglob("*") if path.is_file()]
    suffix_counts: dict[str, int] = {}
    total_bytes = 0
    expected: dict[str, dict[str, Any]] = {}
    for path in files:
        suffix = path.suffix.lower() or "<none>"
        suffix_counts[suffix] = suffix_counts.get(suffix, 0) + 1
        total_bytes += path.stat().st_size
        if path.name in census.EXPECTED_FILES:
            expected[path.name] = {
                "relative_path": str(path.relative_to(root)),
                "size_bytes": path.stat().st_size,
                "sha256": census.sha256_file(path),
            }
    return {
        "file_count": len(files),
        "total_bytes": total_bytes,
        "suffix_counts": dict(sorted(suffix_counts.items())),
        "expected_files": census.EXPECTED_FILES,
        "present_expected_files": sorted(expected),
        "missing_expected_files": [name for name in census.EXPECTED_FILES if name not in expected],
        "expected_file_inventory": expected,
        "raw_rows_emitted": 0,
    }


def validate_boundaries(output_dir: Path) -> dict[str, Any]:
    schema = json.loads((output_dir / "aggregate_schema_report.json").read_text())
    coverage = json.loads((output_dir / "aggregate_coverage_report.json").read_text())
    sample = json.loads((output_dir / "privacy_safe_schema_sample.json").read_text())
    internal = json.loads((output_dir / "internal_qualification_report.json").read_text())
    checks = {
        "schema_raw_rows_zero": schema["aggregate"]["raw_rows_emitted"] == 0,
        "schema_raw_files_not_emitted": schema["aggregate"]["raw_files_emitted"] is False,
        "coverage_raw_rows_zero": coverage["raw_rows_emitted"] == 0,
        "sample_raw_rows_zero": sample["raw_rows_emitted"] == 0,
        "internal_raw_rows_zero": internal["boundaries"]["raw_rows_emitted"] == 0,
        "internal_raw_files_not_emitted": internal["boundaries"]["raw_files_emitted"] is False,
        "formal_cross_source_not_executed": internal["formal_cross_source_qualification_executed"] is False,
        "formal_replacement_not_approved": internal["formal_source_replacement_approved"] is False,
        "qualification_not_evaluated": schema["qualification_evaluated"] is False,
        "cross_source_not_executed": schema["cross_source_audit_executed"] is False,
        "formal_stake_zero": schema["boundaries"]["formal_stake"] == 0,
        "internal_formal_stake_zero": internal["formal_stake"] == 0,
    }
    return {
        "checks": checks,
        "all_passed": all(checks.values()),
        "raw_rows_in_artifact": 0,
        "raw_files_in_artifact": False,
        "formal_stake": 0,
    }


def run(
    output_dir: Path,
    dataset_handle: str | None = None,
    dataset_root: Path | None = None,
) -> dict[str, Any]:
    if bool(dataset_handle) == bool(dataset_root):
        raise ValueError("Provide exactly one of dataset_handle or dataset_root")

    output_dir.mkdir(parents=True, exist_ok=True)
    status: dict[str, Any] = {
        "schema_version": VERSION,
        "source_id": "kaggle_eoinamoore_historical_nba",
        "dataset_handle": dataset_handle,
        "anonymous_download_attempted": bool(dataset_handle) and not bool(os.environ.get("KAGGLE_API_TOKEN")),
        "kaggle_api_token_present": bool(os.environ.get("KAGGLE_API_TOKEN")),
        "raw_files_committed": False,
        "raw_files_uploaded_as_artifact": False,
        "raw_rows_uploaded_as_artifact": False,
    }

    with tempfile.TemporaryDirectory(prefix="nbavl-eoin-kaggle-") as temp_name:
        temp = Path(temp_name)
        try:
            root = download_dataset(dataset_handle, temp / "download") if dataset_handle else Path(dataset_root)
            status["download_complete"] = bool(dataset_handle)
            status["dataset_root_inspected"] = True
            inventory = file_inventory(root)
            (output_dir / "download-inventory-report.json").write_text(
                json.dumps(inventory, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            census_report = census.inspect_directory(root)
            census.write_reports(census_report, output_dir)
            status["census_complete"] = True
            qualification_report = qualification.run(root, output_dir)
            status["internal_qualification_complete"] = True
            status["internal_qualification_outcome"] = qualification_report["outcome"]
            status["internal_gates_passed"] = qualification_report["all_internal_gates_passed"]
            status["file_count"] = census_report["aggregate"]["file_count"]
            status["total_rows"] = census_report["aggregate"]["total_rows"]
            status["missing_expected_files"] = census_report["input"]["missing_expected_files"]
            status["role_candidates"] = census_report["role_candidates"]
            status["boundary_validation"] = validate_boundaries(output_dir)
            if not status["boundary_validation"]["all_passed"]:
                raise RuntimeError("aggregate-only boundary validation failed")
        except Exception as exc:
            status["error"] = f"{type(exc).__name__}: {exc}"
            (output_dir / "eoin-kaggle-run-status.json").write_text(
                json.dumps(status, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            raise

    status["temporary_raw_files_deleted"] = bool(dataset_handle)
    (output_dir / "eoin-kaggle-run-status.json").write_text(
        json.dumps(status, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return status


def self_test(output_dir: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="nbavl-eoin-kaggle-self-test-") as temp_name:
        root = Path(temp_name)
        nested = root / "nested"
        nested.mkdir()
        (nested / "Games.csv").write_text(
            "game_id,game_date,home_team_id,away_team_id,home_pts,away_pts\n"
            "0022300001,2023-10-24,1,2,110,105\n",
            encoding="utf-8",
        )
        (nested / "TeamStatistics.csv").write_text(
            "game_id,team_id,pts\n0022300001,1,110\n0022300001,2,105\n",
            encoding="utf-8",
        )
        (nested / "PlayerStatistics.csv").write_text(
            "game_id,player_id,team_id,pts\n0022300001,101,1,30\n",
            encoding="utf-8",
        )
        status = run(output_dir, dataset_root=root)
        assert status["census_complete"] is True, status
        assert status["internal_qualification_complete"] is True, status
        assert status["file_count"] == 3, status
        assert status["boundary_validation"]["all_passed"] is True, status
        assert status["temporary_raw_files_deleted"] is False, status
        (output_dir / "self-test.json").write_text('{"passed":true}\n', encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-handle", default=DEFAULT_DATASET_HANDLE)
    parser.add_argument("--dataset-root", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test(args.output_dir)
        print("eoin kaggle census self-test passed")
        return 0

    status = run(
        args.output_dir,
        dataset_handle=None if args.dataset_root else args.dataset_handle,
        dataset_root=args.dataset_root,
    )
    print(json.dumps(status, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
