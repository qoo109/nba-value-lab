#!/usr/bin/env python3
"""Append one compact NBA Value Lab research record and rebuild the web index.

Usage:
    python scripts/append_research_record.py path/to/record.json

The tool never overwrites an existing price_evaluation_id. Records are stored in
monthly JSONL files and the web index contains only the latest 200 entries.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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
    for key in ("p_conservative", "p_neutral", "p_optimistic"):
        value = record[key]
        if value is not None and not 0 <= float(value) <= 1:
            raise ValueError(f"{key} must be 0..1 or null")
    values = [record.get("p_conservative"), record.get("p_neutral"), record.get("p_optimistic")]
    if all(value is not None for value in values) and not (values[0] <= values[1] <= values[2]):
        raise ValueError("probabilities must satisfy P_C <= P_N <= P_O")
    parse_time(record["predicted_at"])


def iter_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
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
        "schema_version": "1.0.0",
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
    INDEX_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append(record: dict[str, Any]) -> None:
    validate(record)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    current = iter_records()
    evaluation_id = record["price_evaluation_id"]
    if any(item["price_evaluation_id"] == evaluation_id for item in current):
        raise ValueError(f"price_evaluation_id already exists: {evaluation_id}")
    month = parse_time(record["predicted_at"]).strftime("%Y-%m")
    monthly_path = HISTORY_DIR / f"{month}.jsonl"
    with monthly_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    current.append(record)
    rebuild_index(current)
    print(f"Appended {evaluation_id} to {monthly_path.relative_to(ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("record", type=Path, help="UTF-8 JSON research record")
    args = parser.parse_args()
    append(load_json(args.record))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
