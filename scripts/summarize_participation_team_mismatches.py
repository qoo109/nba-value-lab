#!/usr/bin/env python3
"""Summarize participation team mismatches without retaining player-level identifiers."""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "participation-team-mismatch-summary-v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def summarize(
    audit_rows: list[dict[str, str]],
    official_rows: list[dict[str, str]],
    output_dir: Path,
) -> dict[str, Any]:
    official_index = {
        (
            str(row.get("historical_game_id") or "").strip(),
            str(row.get("player_id") or "").strip(),
        ): row
        for row in official_rows
        if str(row.get("historical_game_id") or "").strip()
        and str(row.get("player_id") or "").strip()
    }
    mismatches = []
    pair_counts: Counter[tuple[str, str]] = Counter()
    game_counts: Counter[str] = Counter()
    rows_without_official_match = 0
    for row in audit_rows:
        game_id = str(row.get("historical_game_id") or "").strip()
        player_id = str(row.get("player_id") or "").strip()
        expected = str(row.get("team_abbr") or "").strip()
        official_row = official_index.get((game_id, player_id)) if player_id else None
        if official_row is None:
            rows_without_official_match += 1
            continue
        official = str(official_row.get("team_abbr") or "").strip()
        if not official or expected == official:
            continue
        pair_counts[(expected, official)] += 1
        game_counts[game_id] += 1
        mismatches.append({
            "historical_game_id": game_id,
            "game_date": str(row.get("game_date") or "").strip(),
            "source_wave": str(row.get("source_wave") or "").strip(),
            "expected_team_abbr": expected,
            "official_team_abbr": official,
        })
    unique_examples = []
    seen = set()
    for item in sorted(
        mismatches,
        key=lambda x: (
            x["game_date"], x["historical_game_id"],
            x["expected_team_abbr"], x["official_team_abbr"],
        ),
    ):
        key = tuple(item.values())
        if key not in seen:
            seen.add(key)
            unique_examples.append(item)
    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "coverage": {
            "audit_rows_scanned": len(audit_rows),
            "official_rows_indexed": len(official_index),
            "audit_rows_without_official_match": rows_without_official_match,
            "team_mismatch_rows": len(mismatches),
            "team_mismatch_games": len(game_counts),
            "team_mismatch_pair_counts": {
                f"{expected}->{official}": count
                for (expected, official), count in sorted(pair_counts.items())
            },
            "team_mismatch_game_counts": dict(sorted(game_counts.items())),
        },
        "examples": unique_examples[:20],
        "quality": {
            "player_names_retained": False,
            "player_ids_retained": False,
            "injury_reasons_retained": False,
            "actual_minutes_retained": False,
        },
        "decision": {
            "team_consistency_gate_passed": len(mismatches) == 0,
            "requires_source_or_identity_review": len(mismatches) > 0,
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "participation-team-mismatch-summary.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def self_test(output_dir: Path) -> None:
    audit = [
        {
            "historical_game_id": "g1",
            "game_date": "2024-01-01",
            "source_wave": "wave1",
            "team_abbr": "AAA",
            "player_id": "secret",
        },
        {
            "historical_game_id": "g2",
            "team_abbr": "CCC",
            "player_id": "same",
        },
    ]
    official = [
        {"historical_game_id": "g1", "player_id": "secret", "team_abbr": "BBB"},
        {"historical_game_id": "g2", "player_id": "same", "team_abbr": "CCC"},
    ]
    report = summarize(audit, official, output_dir)
    assert report["coverage"]["team_mismatch_rows"] == 1
    assert report["examples"][0]["expected_team_abbr"] == "AAA"
    assert report["examples"][0]["official_team_abbr"] == "BBB"
    assert "player_id" not in report["examples"][0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-rows", type=Path)
    parser.add_argument("--official-labels", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("participation team mismatch summary self-test passed")
        return
    if args.audit_rows is None or args.official_labels is None:
        parser.error("--audit-rows and --official-labels are required")
    report = summarize(
        read_csv(args.audit_rows),
        read_csv(args.official_labels),
        args.output_dir,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
