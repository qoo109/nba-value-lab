#!/usr/bin/env python3
"""Append compact NBA Value Lab research records and rebuild the web index.

Usage:
    python scripts/append_research_record.py path/to/record.json
    python scripts/append_research_record.py path/to/records.json --validate-only

The input may be one JSON object or an array. The tool never overwrites an
existing price_evaluation_id. Batch writes are validated before any history
file is changed and are committed through temporary files.
"""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
HISTORY_DIR = ROOT / "data" / "history"
INDEX_PATH = HISTORY_DIR / "index.json"
REQUIRED = {
    "prediction_id",
    "price_evaluation_id",
    "game_id",
    "selection_team_id",
    "predicted_at",
    "evaluation_stage",
    "model_v",
    "model_g",
    "p_conservative",
    "p_neutral",
    "p_optimistic",
    "v_grade",
    "g_grade",
}
VALID_GRADES = {"ㄅ", "ㄆ", "ㄇ", "不支持", "資料不足"}
VALID_STAGES = {"Opening", "T-24h", "21:00", "T-6h", "T-60m", "T-5m", "event", "Closing"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_input(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        return [payload]
    if isinstance(payload, list) and all(isinstance(item, dict) for item in payload):
        return payload
    raise ValueError("input must be one JSON object or an array of objects")


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("predicted_at must include a timezone")
    return parsed


def validate(record: dict[str, Any]) -> None:
    missing = sorted(REQUIRED - record.keys())
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")
    if str(record["model_v"]) != "3.1":
        raise ValueError("model_v must be 3.1 for the active compact schema")
    if str(record["model_g"]) != "1.0":
        raise ValueError("model_g must be 1.0 for the active compact schema")
    if record["evaluation_stage"] not in VALID_STAGES:
        raise ValueError("invalid evaluation_stage")
    if record["v_grade"] not in VALID_GRADES or record["g_grade"] not in VALID_GRADES:
        raise ValueError("invalid V or G grade")
    for key in ("prediction_id", "price_evaluation_id", "game_id", "selection_team_id"):
        if not isinstance(record[key], str) or not record[key].strip():
            raise ValueError(f"{key} must be a non-empty string")
    for key in ("p_conservative", "p_neutral", "p_optimistic"):
        value = record[key]
        if value is not None and not 0 <= float(value) <= 1:
            raise ValueError(f"{key} must be 0..1 or null")
    values = [record.get("p_conservative"), record.get("p_neutral"), record.get("p_optimistic")]
    if all(value is not None for value in values) and not (values[0] <= values[1] <= values[2]):
        raise ValueError("probabilities must satisfy P_C <= P_N <= P_O")
    for key in ("target_odds", "opponent_odds", "closing_odds"):
        value = record.get(key)
        if value is not None and float(value) <= 1:
            raise ValueError(f"{key} must be greater than 1")
    parse_time(record["predicted_at"])


def iter_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not HISTORY_DIR.exists():
        return records
    for path in sorted(HISTORY_DIR.glob("????-??.jsonl")):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                validate(record)
                records.append(record)
            except (json.JSONDecodeError, ValueError) as exc:
                raise SystemExit(f"Invalid history record {path.name}:{line_number}: {exc}") from exc
    return records


def rebuild_index(records: list[dict[str, Any]]) -> None:
    ordered = sorted(records, key=lambda item: item["predicted_at"], reverse=True)
    approximate_bytes = sum(len(json.dumps(item, ensure_ascii=False).encode("utf-8")) + 1 for item in records)
    payload = {
        "schema_version": "1.1.0",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "storage_policy": "compact_append_only",
        "active_models": {
            "V": "3.1",
            "G": "1.0",
            "G_revision": "G1-FINAL-20260716",
            "coordination": "V3.1_X_G1-FINAL-20260716",
        },
        "record_count": len({item["prediction_id"] for item in records}),
        "price_evaluation_count": len({item["price_evaluation_id"] for item in records}),
        "outcome_count": sum(item.get("won") is not None for item in records),
        "approximate_bytes": approximate_bytes,
        "latest_record_at": ordered[0]["predicted_at"] if ordered else None,
        "records": ordered[:200],
    }
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp = INDEX_PATH.with_suffix(".json.tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, INDEX_PATH)


def append_many(records: Iterable[dict[str, Any]], *, validate_only: bool = False) -> list[Path]:
    new_records = list(records)
    if not new_records:
        raise ValueError("no records supplied")
    for record in new_records:
        validate(record)

    existing = iter_records()
    existing_ids = {item["price_evaluation_id"] for item in existing}
    batch_ids = [item["price_evaluation_id"] for item in new_records]
    if len(batch_ids) != len(set(batch_ids)):
        raise ValueError("duplicate price_evaluation_id inside batch")
    collisions = sorted(existing_ids.intersection(batch_ids))
    if collisions:
        raise ValueError(f"price_evaluation_id already exists: {', '.join(collisions)}")

    if validate_only:
        return []

    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in new_records:
        grouped[parse_time(record["predicted_at"]).strftime("%Y-%m")].append(record)

    prepared: list[tuple[Path, Path]] = []
    for month, month_records in grouped.items():
        target = HISTORY_DIR / f"{month}.jsonl"
        temp = target.with_suffix(".jsonl.tmp")
        prior = target.read_text(encoding="utf-8") if target.exists() else ""
        new_lines = "".join(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n" for item in month_records)
        temp.write_text(prior + new_lines, encoding="utf-8")
        prepared.append((temp, target))

    try:
        for temp, target in prepared:
            os.replace(temp, target)
        rebuild_index(existing + new_records)
    finally:
        for temp, _ in prepared:
            if temp.exists():
                temp.unlink()

    return [target for _, target in prepared]


def append(record: dict[str, Any]) -> None:
    paths = append_many([record])
    print(f"Appended {record['price_evaluation_id']} to {paths[0].relative_to(ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("record", type=Path, help="UTF-8 JSON record or array of records")
    parser.add_argument("--validate-only", action="store_true", help="validate without writing history")
    args = parser.parse_args()
    records = normalize_input(load_json(args.record))
    paths = append_many(records, validate_only=args.validate_only)
    if args.validate_only:
        print(f"Validated {len(records)} research record(s)")
    else:
        joined = ", ".join(str(path.relative_to(ROOT)) for path in paths)
        print(f"Appended {len(records)} record(s) to {joined}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
