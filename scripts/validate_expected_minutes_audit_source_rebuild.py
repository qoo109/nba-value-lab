#!/usr/bin/env python3
"""Validate that an Expected Minutes audit source rebuild matches the frozen acquisition wave.

The multi-report player importer intentionally exits non-zero when any successfully parsed report
fails its single-report readiness gate. That is expected for the frozen Wave 1 and Wave 2 samples.
This validator permits the pipeline to continue only when the exact predeclared success, readiness,
and fixed-failure pattern is reproduced.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

EXPECTED: dict[str, dict[str, Any]] = {
    "wave1": {
        "requested": 36,
        "successful": 34,
        "failed": 2,
        "ready_true": 31,
        "ready_false": 3,
        "failed_times": {
            "2024-04-08T08:30:00-04:00",
            "2024-04-08T13:30:00-04:00",
        },
        "not_ready_times": {
            "2024-01-01T17:30:00-05:00",
            "2024-01-15T13:30:00-05:00",
            "2024-01-15T17:30:00-05:00",
        },
    },
    "wave2": {
        "requested": 36,
        "successful": 33,
        "failed": 3,
        "ready_true": 31,
        "ready_false": 2,
        "failed_times": {
            "2024-02-19T08:30:00-05:00",
            "2024-02-19T13:30:00-05:00",
            "2024-02-19T17:30:00-05:00",
        },
        "not_ready_times": {
            "2023-12-25T13:30:00-05:00",
            "2023-12-25T17:30:00-05:00",
        },
    },
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def as_bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes"}


def validate(wave: str, report_path: Path, index_path: Path, importer_exit: int) -> dict[str, Any]:
    expected = EXPECTED[wave]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    rows = read_csv(index_path)
    coverage = report.get("coverage", {})
    failed_examples = report.get("quality", {}).get("failed_report_examples", [])

    ready_true = {row["requested_report_time"] for row in rows if as_bool(row.get("ready"))}
    ready_false = {row["requested_report_time"] for row in rows if not as_bool(row.get("ready"))}
    failed_times = {str(row.get("requested_report_time", "")) for row in failed_examples}

    checks = {
        "importer_exit_is_expected_gate_exit": importer_exit == 2,
        "requested_reports": int(coverage.get("requested_reports", -1)) == expected["requested"],
        "successful_reports": int(coverage.get("successful_reports", -1)) == expected["successful"],
        "failed_reports": int(coverage.get("failed_reports", -1)) == expected["failed"],
        "source_index_rows": len(rows) == expected["successful"],
        "ready_true_count": len(ready_true) == expected["ready_true"],
        "ready_false_count": len(ready_false) == expected["ready_false"],
        "fixed_failed_times": failed_times == expected["failed_times"],
        "fixed_not_ready_times": ready_false == expected["not_ready_times"],
        "duplicate_requested_times": len(rows) == len({row["requested_report_time"] for row in rows}),
        "duplicate_source_urls": len(rows) == len({row["source_url"] for row in rows}),
        "normalized_rows_positive": int(coverage.get("normalized_player_rows", 0)) > 0,
        "identity_join_not_directly_enabled": report.get("decision", {}).get(
            "ready_for_multi_report_identity_value_join"
        ) is False,
    }
    passed = all(checks.values())
    result = {
        "wave": wave,
        "passed": passed,
        "checks": checks,
        "coverage": coverage,
        "ready_true": len(ready_true),
        "ready_false_times": sorted(ready_false),
        "failed_times": sorted(failed_times),
        "guardrail": "Only ready=true rows may enter the downstream overlap audit.",
    }
    if not passed:
        raise AssertionError(json.dumps(result, indent=2))
    return result


def self_test() -> None:
    assert EXPECTED["wave1"]["ready_true"] == 31
    assert EXPECTED["wave2"]["ready_true"] == 31
    assert EXPECTED["wave1"]["failed_times"].isdisjoint(EXPECTED["wave1"]["not_ready_times"])
    assert EXPECTED["wave2"]["failed_times"].isdisjoint(EXPECTED["wave2"]["not_ready_times"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wave", choices=sorted(EXPECTED))
    parser.add_argument("--report", type=Path)
    parser.add_argument("--source-index", type=Path)
    parser.add_argument("--importer-exit", type=int)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        print("source rebuild validator self-test passed")
        return
    if args.wave is None or args.report is None or args.source_index is None or args.importer_exit is None:
        parser.error("--wave, --report, --source-index and --importer-exit are required")
    print(json.dumps(validate(args.wave, args.report, args.source_index, args.importer_exit), indent=2))


if __name__ == "__main__":
    main()
