#!/usr/bin/env python3
"""V4.9 history wrapper with evaluation-time ordering.

The base append tool remains the single writer. This wrapper rebuilds the web
index using the latest price evaluation time so a price-only T-5m record is
shown after its immutable T-60m prediction.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import append_research_record as base

ROOT = base.ROOT
INDEX_PATH = base.INDEX_PATH
iter_records = base.iter_records


def evaluation_time(record: dict[str, Any]) -> str:
    return (
        record.get("price_evaluated_at")
        or record.get("evaluation_cutoff")
        or record.get("observed_at")
        or record["predicted_at"]
    )


def rebuild_index(records: list[dict[str, Any]]) -> None:
    ordered = sorted(records, key=evaluation_time, reverse=True)
    approximate_bytes = sum(len(json.dumps(item, ensure_ascii=False).encode("utf-8")) + 1 for item in records)
    payload = {
        "schema_version": "1.2.0",
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
        "latest_record_at": evaluation_time(ordered[0]) if ordered else None,
        "records": ordered[:200],
    }
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp = INDEX_PATH.with_suffix(".json.tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, INDEX_PATH)


def append_many(records: Iterable[dict[str, Any]], *, validate_only: bool = False) -> list[Path]:
    new_records = list(records)
    paths = base.append_many(new_records, validate_only=validate_only)
    if not validate_only:
        rebuild_index(base.iter_records())
    return paths
