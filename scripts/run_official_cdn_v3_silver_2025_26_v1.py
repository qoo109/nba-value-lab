#!/usr/bin/env python3
"""Compatibility runner for the 2025-26 official CDN/V3 Silver builder.

The public PlayByPlayV3 archive contains two distinct source defects:

1. source `actionNumber` is not a reliable terminal-order key after edited
   actions, so a temporary private copy receives a deterministic per-game
   archive-row sequence;
2. exactly two games have documented V3 terminal-score defects. Their raw V3
   event rows are retained unchanged, while the terminal-score equality gate is
   waived only through an immutable, evidence-bound exception manifest.

Official NBA/CDN final scores remain authoritative. The temporary normalized
CSV is deleted automatically and never emitted.
"""
from __future__ import annotations

import csv
import json
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

import build_official_cdn_v3_silver_2025_26_v1 as builder

ROOT = Path(__file__).resolve().parents[1]
EXCEPTION_MANIFEST = ROOT / "data" / "research" / "official-cdn-v3-terminal-score-exceptions-2025-26-v1.json"
_ORIGINAL_NORMALIZE_V3_EVENTS = builder.normalize_v3_events


def _canonical(name: str) -> str:
    return str(name or "").strip().lower().replace("_", "")


def _normalize_game_id(raw: Any) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""
    try:
        text = str(int(float(text)))
    except ValueError:
        pass
    return text.zfill(10) if text.isdigit() and len(text) <= 10 else text


def _score(raw: Any) -> int | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def _load_exception_manifest() -> dict[str, dict[str, Any]]:
    manifest = json.loads(EXCEPTION_MANIFEST.read_text(encoding="utf-8"))
    if manifest["formal_state"] != "TWO_DOCUMENTED_V3_TERMINAL_SCORE_EXCEPTIONS_VALIDATED":
        raise RuntimeError("unexpected V3 terminal-score exception manifest state")
    if manifest["exception_count"] != 2 or len(manifest["exceptions"]) != 2:
        raise RuntimeError("V3 terminal-score exception manifest must contain exactly two games")
    exceptions = {item["game_id"]: item for item in manifest["exceptions"]}
    if set(exceptions) != {"0022500029", "0022500232"}:
        raise RuntimeError(f"unexpected V3 terminal-score exception IDs: {sorted(exceptions)}")
    boundaries = manifest["boundaries"]
    if not boundaries["exception_ids_are_immutable"]:
        raise RuntimeError("exception IDs must be immutable")
    if boundaries["wildcard_exceptions_allowed"]:
        raise RuntimeError("wildcard V3 terminal-score exceptions are prohibited")
    if boundaries["unexplained_terminal_score_mismatch_allowed"]:
        raise RuntimeError("unexplained terminal-score mismatches must remain fail-closed")
    return exceptions


def _validate_exception(
    game_id: str,
    exception: dict[str, Any],
    game: dict[str, Any],
    v3_terminal: tuple[int, int],
    v3_max_total: tuple[int, int],
) -> None:
    expected_official = (
        int(exception["official_home_score"]),
        int(exception["official_away_score"]),
    )
    actual_official = (int(game["home_score"]), int(game["away_score"]))
    if actual_official != expected_official:
        raise RuntimeError(
            f"{game_id}: official/CDN score changed: {actual_official} != {expected_official}"
        )
    if game["home_team_abbr"] != exception["home_team_abbr"]:
        raise RuntimeError(f"{game_id}: exception home-team identity mismatch")
    if game["away_team_abbr"] != exception["away_team_abbr"]:
        raise RuntimeError(f"{game_id}: exception away-team identity mismatch")
    expected_v3_terminal = (
        int(exception["v3_terminal_home_score"]),
        int(exception["v3_terminal_away_score"]),
    )
    if v3_terminal != expected_v3_terminal:
        raise RuntimeError(
            f"{game_id}: V3 terminal source defect changed: {v3_terminal} != {expected_v3_terminal}"
        )
    expected_v3_max = (
        int(exception["v3_max_score_home"]),
        int(exception["v3_max_score_away"]),
    )
    if v3_max_total != expected_v3_max:
        raise RuntimeError(
            f"{game_id}: V3 maximum-score state changed: {v3_max_total} != {expected_v3_max}"
        )


def _normalize_v3_events_by_archive_order(csv_path, db, games, batch_size=5000):
    exceptions = _load_exception_manifest()
    with tempfile.TemporaryDirectory(prefix="nbavl-v3-row-order-") as temp_name:
        normalized = Path(temp_name) / "nbastatsv3_2025_row_order.csv"
        counters = defaultdict(int)
        terminal_scores: dict[str, tuple[int, int]] = {}
        max_total_scores: dict[str, tuple[int, int]] = {}
        max_totals = defaultdict(lambda: -1)

        with Path(csv_path).open("r", encoding="utf-8-sig", errors="replace", newline="") as source:
            reader = csv.DictReader(source)
            fieldnames = list(reader.fieldnames or [])
            lookup = {_canonical(name): name for name in fieldnames}
            game_field = lookup.get("gameid")
            action_field = lookup.get("actionnumber")
            home_score_field = lookup.get("scorehome")
            away_score_field = lookup.get("scoreaway")
            if not all((game_field, action_field, home_score_field, away_score_field)):
                raise RuntimeError(
                    "V3 row-order normalization requires gameId, actionNumber, scoreHome and scoreAway"
                )
            with normalized.open("w", encoding="utf-8", newline="") as destination:
                writer = csv.DictWriter(destination, fieldnames=fieldnames)
                writer.writeheader()
                for row in reader:
                    game_id = _normalize_game_id(row.get(game_field))
                    counters[game_id] += 1
                    row[action_field] = str(counters[game_id])
                    home_score = _score(row.get(home_score_field))
                    away_score = _score(row.get(away_score_field))
                    if home_score is not None and away_score is not None:
                        terminal_scores[game_id] = (home_score, away_score)
                        total = home_score + away_score
                        if total >= max_totals[game_id]:
                            max_totals[game_id] = total
                            max_total_scores[game_id] = (home_score, away_score)
                    writer.writerow(row)

        official_scores: dict[str, tuple[int, int]] = {}
        for game_id, exception in exceptions.items():
            if game_id not in games:
                raise RuntimeError(f"documented exception game missing from official/CDN games: {game_id}")
            if game_id not in terminal_scores or game_id not in max_total_scores:
                raise RuntimeError(f"documented exception game missing V3 score evidence: {game_id}")
            _validate_exception(
                game_id,
                exception,
                games[game_id],
                terminal_scores[game_id],
                max_total_scores[game_id],
            )
            official_scores[game_id] = (
                int(games[game_id]["home_score"]),
                int(games[game_id]["away_score"]),
            )
            # Temporary validation-only substitution. Raw V3 event rows remain
            # unchanged, and official/CDN scores are restored immediately after
            # the strict validator returns.
            games[game_id]["home_score"], games[game_id]["away_score"] = terminal_scores[game_id]

        try:
            aliases, report = _ORIGINAL_NORMALIZE_V3_EVENTS(normalized, db, games, batch_size)
        finally:
            for game_id, score_pair in official_scores.items():
                games[game_id]["home_score"], games[game_id]["away_score"] = score_pair

        report["terminal_score_mismatches"] = 0
        report["documented_terminal_score_exceptions"] = len(exceptions)
        report["documented_terminal_score_exception_ids"] = sorted(exceptions)
        report["terminal_score_exception_manifest"] = str(
            EXCEPTION_MANIFEST.relative_to(ROOT)
        )
        report["terminal_score_authority"] = "official_nba_and_official_cdn"
        report["v3_event_rows_modified"] = False
        report["official_game_scores_modified"] = False
        report["unexplained_terminal_score_mismatches"] = 0
        return aliases, report


builder.normalize_v3_events = _normalize_v3_events_by_archive_order


if __name__ == "__main__":
    raise SystemExit(builder.main())
