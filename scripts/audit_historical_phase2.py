#!/usr/bin/env python3
"""Compare two full historical archives and emit compact QA/Silver artifacts."""

import argparse
import json
import tarfile
import tempfile
from pathlib import Path

from historical_phase2_core import audit_source

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "historical-source-pilot.json"


def compare(first, second):
    a = set(first["scan"]["game_ids"])
    b = set(second["scan"]["game_ids"])
    overlap, union = a & b, a | b
    smaller = min(len(a), len(b))
    return {
        "first_source": first["source_key"],
        "second_source": second["source_key"],
        "first_game_count": len(a),
        "second_game_count": len(b),
        "overlap_game_count": len(overlap),
        "union_game_count": len(union),
        "overlap_ratio_of_smaller_source": round(len(overlap) / smaller, 6) if smaller else 0,
        "jaccard_ratio": round(len(overlap) / len(union), 6) if union else 0,
        "only_in_first_count": len(a - b),
        "only_in_second_count": len(b - a),
        "only_in_first_sample": sorted(a - b)[:25],
        "only_in_second_sample": sorted(b - a)[:25],
    }


def source_normalization_ready(item):
    scan = item["scan"]
    if scan["normalization_mode"] == "group_events_into_possessions":
        return any(
            check.get("usable_for_normalization")
            for check in scan.get("grouping_checks", [])
        )
    return any(
        check.get("unique_after_exact_dedupe")
        for check in scan.get("candidate_key_checks", [])
    )


def run(config_path, output, silver_output, max_mb, sample_limit):
    config = json.loads(config_path.read_text(encoding="utf-8"))
    keys = config["phase2_source_keys"]
    with tempfile.TemporaryDirectory(prefix="nbavl-history-phase2-") as temp:
        audits = [
            audit_source(key, config["sources"][key], Path(temp), max_mb, sample_limit)
            for key in keys
        ]

    coverage = compare(audits[0], audits[1])
    schema_pass = all(not item["scan"]["expected_fields_missing"] for item in audits)
    normalization_pass = all(source_normalization_ready(item) for item in audits)
    coverage_pass = coverage["overlap_ratio_of_smaller_source"] >= 0.98
    report = {
        "schema_version": "2.2.0",
        "pilot_name": config["pilot_name"],
        "follows_current_site_version": config["follows_current_site_version"],
        "sources": audits,
        "comparison": coverage,
        "decision": {
            "schema_pass": schema_pass,
            "source_normalization_pass": normalization_pass,
            "coverage_pass_98pct": coverage_pass,
            "ready_for_silver_pilot": schema_pass and normalization_pass and coverage_pass,
            "raw_commit_allowed": False,
            "dedupe_policy": "drop byte-equivalent normalized rows only; preserve conflicting rows",
            "pbpstats_policy": "group event rows into possession records, then assign event ordinal within each group",
            "next_step": (
                "build normalized possessions/events adapters and recompute team game features"
                if schema_pass and normalization_pass and coverage_pass
                else "resolve normalization or coverage differences before Silver conversion"
            ),
        },
    }

    silver_records = []
    for item in audits:
        for row in item["scan"]["silver_sample_rows"]:
            silver_records.append({
                "source_id": item["source_key"],
                "season_label": item["season_label"],
                "archive_sha256": item["archive"]["sha256"],
                **row,
            })
    silver = {
        "schema_version": "0.2.0-pilot",
        "follows_current_site_version": True,
        "raw_data_included": False,
        "dedupe_policy": "sample is pre-dedupe and traceable by source_row_number",
        "record_count": len(silver_records),
        "records": silver_records,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    silver_output.write_text(json.dumps(silver, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def self_test(output, silver_output):
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        config = {
            "pilot_name": "NBA Value Lab historical data pilot",
            "follows_current_site_version": True,
            "phase2_source_keys": ["a", "b"],
            "sources": {},
        }
        fixtures = {
            "a": (
                "GAMEID,PERIOD,STARTTIME,ENDTIME,OPPONENT,EVENTS,FG2A\n"
                "1,1,12:00,11:40,B,Shot and rebound,1\n"
                "1,1,12:00,11:40,B,Shot and rebound,1\n"
            ),
            "b": (
                "GAME_ID,EVENTNUM,PERIOD,PCTIMESTRING\n"
                "1,1,1,12:00\n"
                "1,1,1,12:00\n"
            ),
        }
        for key, text in fixtures.items():
            source = root / f"{key}.csv"
            source.write_text(text, encoding="utf-8")
            archive = root / f"{key}.tar.xz"
            with tarfile.open(archive, "w:xz") as handle:
                handle.add(source, arcname=source.name)
            if key == "a":
                fields = ["GAMEID", "PERIOD", "STARTTIME", "ENDTIME", "OPPONENT", "EVENTS"]
                keys = [["GAMEID", "PERIOD", "STARTTIME", "ENDTIME", "OPPONENT"]]
                game = ["GAMEID"]
                mode = "group_events_into_possessions"
                groups = [{
                    "name": "possession_group",
                    "fields": ["GAMEID", "PERIOD", "STARTTIME", "ENDTIME", "OPPONENT"],
                    "consistency_fields": ["EVENTS", "FG2A"],
                }]
            else:
                fields = ["GAME_ID", "EVENTNUM", "PERIOD", "PCTIMESTRING"]
                keys = [["GAME_ID", "EVENTNUM"]]
                game = ["GAME_ID"]
                mode = "event_rows"
                groups = []
            config["sources"][key] = {
                "provider": "fixture",
                "source_role": "fixture",
                "normalization_mode": mode,
                "season_label": "test",
                "url": archive.as_uri(),
                "game_id_fields": game,
                "expected_fields_any": fields,
                "candidate_primary_keys": keys,
                "grouping_rules": groups,
                "silver_sample_fields": fields,
                "license_status": "fixture",
            }
        config_path = root / "config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        report = run(config_path, output, silver_output, 10, 10)
        assert report["decision"]["ready_for_silver_pilot"]
        for source in report["sources"]:
            assert source["scan"]["exact_row_deduplication"]["exact_duplicate_rows"] == 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--silver-output", type=Path, required=True)
    parser.add_argument("--max-download-mb", type=int, default=600)
    parser.add_argument("--silver-limit-per-source", type=int, default=75)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test(args.output, args.silver_output)
        print("historical phase 2 normalization self-test passed")
        return

    report = run(
        args.config,
        args.output,
        args.silver_output,
        args.max_download_mb,
        args.silver_limit_per_source,
    )
    print(json.dumps({
        "sources": [{
            "source_key": item["source_key"],
            "normalization_mode": item["scan"]["normalization_mode"],
            "archive_mb": item["archive"]["megabytes"],
            "csv_mb": item["scan"]["file"]["megabytes"],
            "row_count": item["scan"]["rows"]["row_count"],
            "game_count": item["scan"]["rows"]["game_count"],
            "exact_dedupe": item["scan"]["exact_row_deduplication"],
            "key_checks": item["scan"]["candidate_key_checks"],
            "grouping_checks": item["scan"]["grouping_checks"],
        } for item in report["sources"]],
        "comparison": report["comparison"],
        "decision": report["decision"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
