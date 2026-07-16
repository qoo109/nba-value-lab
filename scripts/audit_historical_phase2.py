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
    key_pass = all(
        any(check.get("unique") for check in item["scan"]["candidate_key_checks"])
        for item in audits
    )
    coverage_pass = coverage["overlap_ratio_of_smaller_source"] >= 0.98
    report = {
        "schema_version": "2.0.0",
        "pilot_name": config["pilot_name"],
        "follows_current_site_version": config["follows_current_site_version"],
        "sources": audits,
        "comparison": coverage,
        "decision": {
            "schema_pass": schema_pass,
            "candidate_key_pass": key_pass,
            "coverage_pass_98pct": coverage_pass,
            "ready_for_silver_pilot": schema_pass and key_pass and coverage_pass,
            "raw_commit_allowed": False,
            "next_step": (
                "build normalized adapters and recompute team game features"
                if schema_pass and key_pass and coverage_pass
                else "resolve key or coverage differences before Silver conversion"
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
        "schema_version": "0.1.0-pilot",
        "follows_current_site_version": True,
        "raw_data_included": False,
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
            "a": "GAMEID,PERIOD,STARTTIME,ENDTIME,OPPONENT,EVENTS\n1,1,12:00,11:40,B,Shot\n",
            "b": "GAME_ID,EVENTNUM,PERIOD,PCTIMESTRING\n1,1,1,12:00\n",
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
            else:
                fields = ["GAME_ID", "EVENTNUM", "PERIOD", "PCTIMESTRING"]
                keys = [["GAME_ID", "EVENTNUM"]]
                game = ["GAME_ID"]
            config["sources"][key] = {
                "provider": "fixture",
                "source_role": "fixture",
                "season_label": "test",
                "url": archive.as_uri(),
                "game_id_fields": game,
                "expected_fields_any": fields,
                "candidate_primary_keys": keys,
                "silver_sample_fields": fields,
                "license_status": "fixture",
            }
        config_path = root / "config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        report = run(config_path, output, silver_output, 10, 10)
        assert report["decision"]["ready_for_silver_pilot"]


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
        print("historical phase 2 self-test passed")
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
            "archive_mb": item["archive"]["megabytes"],
            "csv_mb": item["scan"]["file"]["megabytes"],
            "row_count": item["scan"]["rows"]["row_count"],
            "game_count": item["scan"]["rows"]["game_count"],
            "key_checks": item["scan"]["candidate_key_checks"],
        } for item in report["sources"]],
        "comparison": report["comparison"],
        "decision": report["decision"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
