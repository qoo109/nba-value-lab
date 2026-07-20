#!/usr/bin/env python3
"""V4.10 history writer for registered V3.1 and G1 family records."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import append_research_record as base

_ORIGINAL_VALIDATE = base.validate


def validate(record: dict[str, Any]) -> None:
    _ORIGINAL_VALIDATE(record)


base.validate = validate
ROOT = base.ROOT
INDEX_PATH = base.INDEX_PATH
iter_records = base.iter_records


def evaluation_time(record: dict[str, Any]) -> str:
    return record.get("price_evaluated_at") or record.get("evaluation_cutoff") or record.get("observed_at") or record["predicted_at"]


def rebuild_index(records: list[dict[str, Any]]) -> None:
    ordered = sorted(records, key=evaluation_time, reverse=True)
    approximate_bytes = sum(len(json.dumps(item, ensure_ascii=False).encode("utf-8")) + 1 for item in records)
    manifest = json.loads((ROOT / "models" / "manifest.json").read_text(encoding="utf-8"))
    payload = {
        "schema_version": manifest["compatibility"]["prediction_record_schema"],
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "storage_policy": "compact_append_only",
        "active_models": {
            "V": str(manifest["active"]["V"]["version"]),
            "V_revision": manifest["active"]["V"]["revision_id"],
            "G": str(manifest["active"]["G"]["version"]),
            "G_revision": manifest["active"]["G"]["revision_id"],
            "coordination": manifest["coordination"]["coordination_id"],
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
