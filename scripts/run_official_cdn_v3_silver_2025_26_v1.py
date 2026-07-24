#!/usr/bin/env python3
"""Compatibility runner for the 2025-26 official CDN/V3 Silver builder.

The public PlayByPlayV3 archive contains edited actions whose source
`actionNumber` is not a reliable terminal-order key for every game. Before the
core builder ingests V3 rows, this runner creates a temporary private copy with
a deterministic per-game archive-row sequence in the action-number field.

This changes no score, team, player, clock or action content. It only gives the
cross-source terminal-score validator an ordering key that matches archive row
order. The temporary normalized CSV is deleted automatically and never emitted.
"""
from __future__ import annotations

import csv
import tempfile
from collections import defaultdict
from pathlib import Path

import build_official_cdn_v3_silver_2025_26_v1 as builder

_ORIGINAL_NORMALIZE_V3_EVENTS = builder.normalize_v3_events


def _canonical(name: str) -> str:
    return str(name or "").strip().lower().replace("_", "")


def _normalize_v3_events_by_archive_order(csv_path, db, games, batch_size=5000):
    with tempfile.TemporaryDirectory(prefix="nbavl-v3-row-order-") as temp_name:
        normalized = Path(temp_name) / "nbastatsv3_2025_row_order.csv"
        counters = defaultdict(int)
        with Path(csv_path).open("r", encoding="utf-8-sig", errors="replace", newline="") as source:
            reader = csv.DictReader(source)
            fieldnames = list(reader.fieldnames or [])
            lookup = {_canonical(name): name for name in fieldnames}
            game_field = lookup.get("gameid")
            action_field = lookup.get("actionnumber")
            if not game_field or not action_field:
                raise RuntimeError("V3 row-order normalization requires gameId and actionNumber")
            with normalized.open("w", encoding="utf-8", newline="") as destination:
                writer = csv.DictWriter(destination, fieldnames=fieldnames)
                writer.writeheader()
                for row in reader:
                    game_key = str(row.get(game_field, "")).strip()
                    counters[game_key] += 1
                    row[action_field] = str(counters[game_key])
                    writer.writerow(row)
        return _ORIGINAL_NORMALIZE_V3_EVENTS(normalized, db, games, batch_size)


builder.normalize_v3_events = _normalize_v3_events_by_archive_order


if __name__ == "__main__":
    raise SystemExit(builder.main())
