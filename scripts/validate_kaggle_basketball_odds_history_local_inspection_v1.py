#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "inspect_kaggle_basketball_odds_history_archive_v1.py"
spec = importlib.util.spec_from_file_location("kaggle_archive_inspector", MODULE_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def expect_error(fn, message: str) -> None:
    try:
        fn()
    except module.ArchiveInspectionError:
        return
    raise AssertionError(message)


def write_valid_archive(path: Path) -> None:
    detailed = (
        "event_id,observed_at,bookmaker,home_team,away_team,home_odds,away_odds\n"
        "evt-1,2026-01-01T00:00:00Z,book_a,Home A,Away A,1.80,2.10\n"
        "evt-1,2026-01-01T00:07:00Z,book_a,Home A,Away A,1.82,2.08\n"
    )
    main_lines = (
        "game_id,scrape_timestamp,provider,home,away,home_price,away_price\n"
        "evt-2,2026-01-02T00:00:00Z,book_b,Home B,Away B,1.70,2.20\n"
    )
    notebook = {"cells": [{"cell_type": "markdown", "source": ["synthetic contract"]}], "metadata": {}}
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("nba_detailed_odds.csv", detailed)
        archive.writestr("nba_main_lines.csv", main_lines)
        archive.writestr("__notebook__.ipynb", json.dumps(notebook))
        archive.writestr("wnba_main_lines.csv", "event_id,date,home,away,odds\n1,2026-01-01,A,B,1.5\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts" / "kaggle-basketball-odds-history-local-inspection-validation-v1.json",
    )
    args = parser.parse_args()
    tests = 0

    design = json.loads(
        (ROOT / "data" / "research" / "kaggle-basketball-odds-history-local-inspection-v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert design["source_id"] == "kaggle_zachht_basketball_odds_history"
    assert design["public_dataset_claims"]["license_label"] == "CC0: Public Domain"
    assert design["public_dataset_claims"]["scrape_attempt_interval_minutes"] == 7
    assert design["inspector"]["offline_only"] is True
    assert design["inspector"]["quote_rows_emitted"] == 0
    assert design["inspector"]["prices_emitted"] == 0
    assert design["inspector"]["network_client_included"] is False
    assert design["qualification_state"]["real_archive_inspected"] is False
    assert design["formal_stake"] == 0
    tests += 9

    with tempfile.TemporaryDirectory() as temp_dir:
        base = Path(temp_dir)
        archive_path = base / "basketball-odds-history.zip"
        write_valid_archive(archive_path)
        report = module.inspect_archive(archive_path)

        assert report["formal_state"] == "KAGGLE_BASKETBALL_ODDS_HISTORY_LOCAL_SCHEMA_CANDIDATE_FOUND"
        assert report["archive_file_count"] == 4
        assert report["csv_file_count"] == 3
        assert report["nba_csv_file_count"] == 2
        assert report["nba_csv_files_inspected"] == 2
        assert report["notebook_present"] is True
        assert report["schema_candidate"] is True
        assert report["field_presence"]["timestamp_file_count"] == 2
        assert report["field_presence"]["bookmaker_file_count"] == 2
        assert report["field_presence"]["event_file_count"] == 2
        assert report["field_presence"]["team_file_count"] == 2
        assert report["field_presence"]["price_file_count"] == 2
        assert report["quote_rows_emitted"] == 0
        assert report["prices_emitted"] == 0
        assert report["point_in_time_qualified"] is False
        assert report["historical_backfill_qualified"] is False
        assert report["market_metrics_executed"] is False
        assert report["formal_stake"] == 0
        tests += 18

        extracted = base / "extracted"
        extracted.mkdir()
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(extracted)
        directory_report = module.inspect_archive(extracted)
        assert directory_report["schema_candidate"] is True
        assert directory_report["nba_csv_file_count"] == 2
        tests += 2

        no_nba = base / "no-nba.zip"
        with zipfile.ZipFile(no_nba, "w") as archive:
            archive.writestr("wnba_main_lines.csv", "event_id,date,home,away,odds\n1,2026-01-01,A,B,1.5\n")
        no_nba_report = module.inspect_archive(no_nba)
        assert no_nba_report["schema_candidate"] is False
        assert no_nba_report["nba_csv_file_count"] == 0
        assert no_nba_report["next_unique_mainline"] == "OBTAIN_COMPLETE_KAGGLE_BASKETBALL_ODDS_HISTORY_ARCHIVE_AND_REINSPECT"
        tests += 3

        missing_timestamp = base / "missing-timestamp.zip"
        with zipfile.ZipFile(missing_timestamp, "w") as archive:
            archive.writestr(
                "nba_detailed_odds.csv",
                "event_id,bookmaker,home_team,away_team,home_odds,away_odds\n"
                "evt-1,book_a,Home A,Away A,1.80,2.10\n",
            )
        missing_report = module.inspect_archive(missing_timestamp)
        assert missing_report["schema_candidate"] is False
        assert missing_report["field_presence"]["timestamp_file_count"] == 0
        tests += 2

        unsafe = base / "unsafe.zip"
        with zipfile.ZipFile(unsafe, "w") as archive:
            archive.writestr("../nba.csv", "event_id,date,bookmaker,home,away,odds\n")
        expect_error(lambda: module.inspect_archive(unsafe), "unsafe archive member must fail")
        tests += 1

        empty = base / "empty.zip"
        with zipfile.ZipFile(empty, "w"):
            pass
        expect_error(lambda: module.inspect_archive(empty), "empty archive must fail")
        tests += 1

        expect_error(lambda: module.inspect_archive(ROOT), "repository path must be rejected")
        tests += 1

    assert tests == 37
    qa = {
        "schema_version": 1,
        "formal_state": "KAGGLE_BASKETBALL_ODDS_HISTORY_LOCAL_INSPECTOR_VALID",
        "offline_only": True,
        "manual_download_required": True,
        "source_archive_outside_repo_required": True,
        "aggregate_output_outside_repo_until_reviewed": True,
        "zip_and_directory_supported": True,
        "synthetic_contract_only": True,
        "real_archive_inspected": False,
        "quote_rows_emitted": 0,
        "prices_emitted": 0,
        "provider_requests_executed": 0,
        "timestamp_semantics_verified": False,
        "upstream_provenance_verified": False,
        "point_in_time_qualified": False,
        "historical_backfill_qualified": False,
        "formal_history_write_authorized": False,
        "market_metrics_executed": False,
        "contract_tests": tests,
        "formal_stake": 0,
        "next_unique_mainline": "AWAIT_MANUAL_KAGGLE_BASKETBALL_ODDS_HISTORY_ARCHIVE_FOR_LOCAL_INSPECTION",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
