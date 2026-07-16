#!/usr/bin/env python3
"""Audit a historical NBA archive without committing raw data.

The tool downloads one configured archive into a temporary directory, verifies
its size and hash, safely extracts it, samples supported files, and writes a
compact JSON report. It is intentionally read-only with respect to repository
data directories.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import tarfile
import tempfile
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "historical-source-pilot.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def download(url: str, destination: Path, max_bytes: int) -> tuple[int, str, str | None]:
    request = urllib.request.Request(url, headers={"User-Agent": "NBA-Value-Lab-V4.5-pilot/1.0"})
    digest = hashlib.sha256()
    total = 0
    content_type: str | None = None
    with urllib.request.urlopen(request, timeout=90) as response, destination.open("wb") as target:
        content_type = response.headers.get("Content-Type")
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise ValueError(f"download exceeded limit of {max_bytes} bytes")
            digest.update(chunk)
            target.write(chunk)
    return total, digest.hexdigest(), content_type


def safe_extract(archive: Path, destination: Path) -> list[tarfile.TarInfo]:
    destination = destination.resolve()
    with tarfile.open(archive, mode="r:xz") as handle:
        members = handle.getmembers()
        for member in members:
            member_path = (destination / member.name).resolve()
            if destination not in member_path.parents and member_path != destination:
                raise ValueError(f"unsafe archive path: {member.name}")
            if member.issym() or member.islnk():
                raise ValueError(f"links are not allowed in pilot archives: {member.name}")
        handle.extractall(destination, members=members, filter="data")
        return members


def normalize_record(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        for key in ("data", "rows", "events", "plays", "possessions", "result"):
            nested = value.get(key)
            rows = normalize_record(nested)
            if rows:
                return rows
        if value and all(not isinstance(item, (dict, list)) for item in value.values()):
            return [value]
    return []


def sample_csv(path: Path, row_limit: int) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = list(reader.fieldnames or [])
        for row in reader:
            rows.append(dict(row))
            if len(rows) >= row_limit:
                break
    return rows, columns


def sample_json(path: Path, row_limit: int) -> tuple[list[dict[str, Any]], list[str]]:
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        payload = json.load(handle)
    rows = normalize_record(payload)[:row_limit]
    columns = sorted({key for row in rows for key in row})
    return rows, columns


def sample_jsonl(path: Path, row_limit: int) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            value = json.loads(line)
            if isinstance(value, dict):
                rows.append(value)
            if len(rows) >= row_limit:
                break
    columns = sorted({key for row in rows for key in row})
    return rows, columns


def sample_parquet(path: Path, row_limit: int) -> tuple[list[dict[str, Any]], list[str]]:
    try:
        import pyarrow.parquet as pq  # type: ignore
    except ImportError as exc:
        raise RuntimeError("pyarrow is required to inspect parquet files") from exc
    table = pq.read_table(path)
    columns = list(table.column_names)
    sample = table.slice(0, row_limit).to_pylist()
    return [dict(row) for row in sample], columns


def supported(path: Path) -> bool:
    lower = path.name.lower()
    return lower.endswith((".csv", ".json", ".jsonl", ".ndjson", ".parquet"))


def sample_file(path: Path, row_limit: int) -> tuple[list[dict[str, Any]], list[str], str]:
    lower = path.name.lower()
    if lower.endswith(".csv"):
        rows, columns = sample_csv(path, row_limit)
        return rows, columns, "csv"
    if lower.endswith((".jsonl", ".ndjson")):
        rows, columns = sample_jsonl(path, row_limit)
        return rows, columns, "jsonl"
    if lower.endswith(".json"):
        rows, columns = sample_json(path, row_limit)
        return rows, columns, "json"
    if lower.endswith(".parquet"):
        rows, columns = sample_parquet(path, row_limit)
        return rows, columns, "parquet"
    raise ValueError(f"unsupported file: {path}")


def value_missing(value: Any) -> bool:
    return value is None or value == "" or str(value).strip().lower() in {"nan", "none", "null"}


def canonical_lookup(columns: Iterable[str]) -> dict[str, str]:
    return {column.upper(): column for column in columns}


def analyze_rows(
    rows: list[dict[str, Any]],
    columns: list[str],
    expected_fields: list[str],
    candidate_keys: list[list[str]],
) -> dict[str, Any]:
    lookup = canonical_lookup(columns)
    matched_expected = [field for field in expected_fields if field.upper() in lookup]
    missing_expected = [field for field in expected_fields if field.upper() not in lookup]
    missing_counts = {
        column: sum(value_missing(row.get(column)) for row in rows)
        for column in columns
        if rows
    }
    null_rates = {
        column: round(count / len(rows), 4)
        for column, count in missing_counts.items()
        if count
    }

    game_field = next((lookup[name] for name in ("GAME_ID", "GAMEID", "GAMEID") if name in lookup), None)
    distinct_games = len({str(row.get(game_field)) for row in rows if game_field and not value_missing(row.get(game_field))})

    key_checks: list[dict[str, Any]] = []
    for key in candidate_keys:
        resolved = [lookup.get(field.upper()) for field in key]
        if not all(resolved):
            key_checks.append({"fields": key, "available": False})
            continue
        seen: set[tuple[str, ...]] = set()
        duplicate_count = 0
        incomplete_count = 0
        for row in rows:
            values = tuple(str(row.get(field, "")) for field in resolved if field)
            if any(not value.strip() for value in values):
                incomplete_count += 1
                continue
            if values in seen:
                duplicate_count += 1
            seen.add(values)
        key_checks.append({
            "fields": key,
            "available": True,
            "sample_unique_keys": len(seen),
            "sample_duplicate_rows": duplicate_count,
            "sample_incomplete_rows": incomplete_count,
        })

    return {
        "sample_rows": len(rows),
        "column_count": len(columns),
        "columns": columns,
        "expected_fields_found": matched_expected,
        "expected_fields_missing": missing_expected,
        "sample_null_rates_nonzero": null_rates,
        "sample_distinct_games": distinct_games,
        "candidate_key_checks": key_checks,
    }


def audit(source_key: str, config_path: Path, output_path: Path, max_download_mb: int, max_files: int, sample_rows: int) -> dict[str, Any]:
    config = load_json(config_path)
    source = config["sources"].get(source_key)
    if not source:
        raise ValueError(f"unknown source_key: {source_key}")

    with tempfile.TemporaryDirectory(prefix="nbavl-history-pilot-") as temp_dir:
        temp = Path(temp_dir)
        archive = temp / f"{source_key}.tar.xz"
        extracted = temp / "extracted"
        extracted.mkdir()
        byte_limit = max_download_mb * 1024 * 1024
        archive_bytes, archive_sha256, content_type = download(source["url"], archive, byte_limit)
        members = safe_extract(archive, extracted)

        file_paths = sorted(path for path in extracted.rglob("*") if path.is_file())
        type_counts = Counter(path.suffix.lower() or "no_extension" for path in file_paths)
        sampled_files: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []
        aggregate_columns: Counter[str] = Counter()
        aggregate_games: set[str] = set()

        for path in [item for item in file_paths if supported(item)][:max_files]:
            relative = str(path.relative_to(extracted))
            try:
                rows, columns, file_format = sample_file(path, sample_rows)
                analysis = analyze_rows(
                    rows,
                    columns,
                    source.get("expected_fields_any", []),
                    source.get("candidate_primary_keys", []),
                )
                for column in columns:
                    aggregate_columns[column] += 1
                lookup = canonical_lookup(columns)
                game_field = next((lookup[name] for name in ("GAME_ID", "GAMEID") if name in lookup), None)
                if game_field:
                    aggregate_games.update(
                        str(row.get(game_field)) for row in rows if not value_missing(row.get(game_field))
                    )
                sampled_files.append({
                    "path": relative,
                    "format": file_format,
                    "bytes": path.stat().st_size,
                    **analysis,
                })
            except Exception as exc:  # report per-file errors without losing the whole audit
                errors.append({"path": relative, "error": f"{type(exc).__name__}: {exc}"})

        expected_found_any = sorted({
            field
            for item in sampled_files
            for field in item.get("expected_fields_found", [])
        })
        expected_missing_all = [
            field for field in source.get("expected_fields_any", [])
            if field not in expected_found_any
        ]
        report = {
            "schema_version": "1.0.0",
            "pilot_name": config.get("pilot_version"),
            "source_key": source_key,
            "provider": source.get("provider"),
            "source_role": source.get("source_role"),
            "season_label": source.get("season_label"),
            "source_url": source.get("url"),
            "license_status": source.get("license_status"),
            "archive": {
                "bytes": archive_bytes,
                "megabytes": round(archive_bytes / 1024 / 1024, 2),
                "sha256": archive_sha256,
                "content_type": content_type,
                "member_count": len(members),
                "file_count": len(file_paths),
                "file_types": dict(type_counts),
            },
            "inspection": {
                "max_files": max_files,
                "sample_rows_per_file": sample_rows,
                "sampled_file_count": len(sampled_files),
                "sampled_distinct_games_lower_bound": len(aggregate_games),
                "columns_seen_in_files": dict(aggregate_columns.most_common()),
                "expected_fields_found_any": expected_found_any,
                "expected_fields_missing_all": expected_missing_all,
                "files": sampled_files,
                "errors": errors,
            },
            "decision": {
                "schema_usable": bool(sampled_files) and not expected_missing_all,
                "raw_commit_allowed": False,
                "recommended_next_step": "compare game coverage and key uniqueness before Silver conversion",
            },
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return report


def self_test(output_path: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="nbavl-audit-selftest-") as temp_dir:
        temp = Path(temp_dir)
        source_dir = temp / "source"
        source_dir.mkdir()
        csv_path = source_dir / "possessions.csv"
        csv_path.write_text(
            "GAMEID,PERIOD,STARTTIME,ENDTIME,STARTTYPE,EVENTS\n"
            "001,1,12:00,11:42,StartOfPeriod,Made Shot\n"
            "001,1,11:42,11:18,OffMiss,Turnover\n",
            encoding="utf-8",
        )
        archive = temp / "fixture.tar.xz"
        with tarfile.open(archive, "w:xz") as handle:
            handle.add(csv_path, arcname="fixture/possessions.csv")
        rows, columns = sample_csv(csv_path, 10)
        analysis = analyze_rows(rows, columns, ["GAMEID", "PERIOD", "STARTTIME"], [["GAMEID", "PERIOD", "STARTTIME"]])
        payload = {"self_test": "passed", "archive_bytes": archive.stat().st_size, "analysis": analysis}
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="pbpstats_2023")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=Path("historical-source-audit.json"))
    parser.add_argument("--max-download-mb", type=int, default=600)
    parser.add_argument("--max-files", type=int, default=80)
    parser.add_argument("--sample-rows", type=int, default=5000)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test(args.output)
        print(f"self-test report: {args.output}")
        return 0

    report = audit(args.source, args.config, args.output, args.max_download_mb, args.max_files, args.sample_rows)
    print(json.dumps({
        "source": report["source_key"],
        "archive_mb": report["archive"]["megabytes"],
        "files": report["archive"]["file_count"],
        "sampled_files": report["inspection"]["sampled_file_count"],
        "schema_usable": report["decision"]["schema_usable"],
        "report": str(args.output),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
