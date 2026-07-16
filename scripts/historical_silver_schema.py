#!/usr/bin/env python3
"""Shared helpers and SQLite schema for historical Silver adapters."""

from __future__ import annotations

import gzip
import hashlib
import re
import shutil
import sqlite3
from pathlib import Path
from typing import Any, Iterable

FREE_THROW_RE = re.compile(r"\bFree Throw\b", re.IGNORECASE)
MISSED_FREE_THROW_RE = re.compile(r"^\s*MISS\b.*\bFree Throw\b", re.IGNORECASE)


def missing(value: Any) -> bool:
    return value is None or str(value).strip().lower() in {"", "nan", "none", "null"}


def clean(value: Any) -> str | None:
    return None if missing(value) else str(value).strip()


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return default


def safe_div(numerator: float, denominator: float) -> float | None:
    if not denominator:
        return None
    return round(numerator / denominator, 6)


def stable_id(*parts: Any) -> str:
    payload = "\x1f".join("" if part is None else str(part).strip() for part in parts)
    return hashlib.sha1(payload.encode("utf-8", errors="replace")).hexdigest()


def row_fingerprint(row: dict[str, Any], columns: Iterable[str]) -> str:
    return stable_id(*(row.get(column, "") for column in columns))


def parse_score(value: Any) -> tuple[int | None, int | None]:
    """NBA stats SCORE is formatted as away - home."""
    text = clean(value)
    if not text or "-" not in text:
        return None, None
    left, right = text.split("-", 1)
    try:
        return int(left.strip()), int(right.strip())
    except ValueError:
        return None, None


def parse_free_throws(events_text: str | None) -> tuple[int, int]:
    attempts = makes = 0
    for line in (events_text or "").splitlines():
        if not FREE_THROW_RE.search(line):
            continue
        attempts += 1
        if not MISSED_FREE_THROW_RE.search(line):
            makes += 1
    return attempts, makes


def create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA journal_mode=OFF;
        PRAGMA synchronous=OFF;
        PRAGMA temp_store=MEMORY;
        PRAGMA foreign_keys=OFF;

        CREATE TABLE metadata (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL
        );

        CREATE TABLE games (
          game_id TEXT PRIMARY KEY,
          game_date TEXT,
          season_label TEXT NOT NULL,
          home_team_id TEXT,
          home_team_abbr TEXT,
          away_team_id TEXT,
          away_team_abbr TEXT,
          home_score INTEGER,
          away_score INTEGER,
          max_period INTEGER,
          game_minutes REAL,
          pbp_event_count INTEGER NOT NULL,
          possession_count INTEGER NOT NULL,
          score_match INTEGER,
          quality_flags TEXT NOT NULL
        );

        CREATE TABLE pbp_events (
          event_id TEXT PRIMARY KEY,
          game_id TEXT NOT NULL,
          event_num INTEGER,
          event_type INTEGER,
          action_type INTEGER,
          period INTEGER,
          clock TEXT,
          side TEXT,
          description TEXT,
          neutral_description TEXT,
          away_score INTEGER,
          home_score INTEGER,
          score_margin TEXT,
          team_id TEXT,
          team_abbr TEXT,
          player1_id TEXT,
          player2_id TEXT,
          player3_id TEXT,
          video_available INTEGER,
          source_id TEXT NOT NULL,
          source_row_number INTEGER NOT NULL
        );

        CREATE TABLE possessions (
          possession_id TEXT PRIMARY KEY,
          game_id TEXT NOT NULL,
          game_date TEXT,
          period INTEGER,
          start_clock TEXT,
          end_clock TEXT,
          offense_team_abbr TEXT,
          defense_team_abbr TEXT,
          start_score_differential INTEGER,
          start_type TEXT,
          points_scored INTEGER NOT NULL,
          fg2a INTEGER NOT NULL,
          fg2m INTEGER NOT NULL,
          fg3a INTEGER NOT NULL,
          fg3m INTEGER NOT NULL,
          fta INTEGER NOT NULL,
          ftm INTEGER NOT NULL,
          offensive_rebounds INTEGER NOT NULL,
          turnovers INTEGER NOT NULL,
          shooting_fouls_drawn INTEGER NOT NULL,
          nonshooting_fouls_resulting_in_fts INTEGER NOT NULL,
          event_rows INTEGER NOT NULL,
          events_text TEXT,
          source_id TEXT NOT NULL,
          quality_flags TEXT NOT NULL
        );

        CREATE TABLE team_game_features (
          game_id TEXT NOT NULL,
          team_abbr TEXT NOT NULL,
          opponent_abbr TEXT,
          is_home INTEGER,
          points INTEGER NOT NULL,
          opponent_points INTEGER NOT NULL,
          possessions INTEGER NOT NULL,
          opponent_possessions INTEGER NOT NULL,
          pace REAL,
          off_rtg REAL,
          def_rtg REAL,
          net_rtg REAL,
          fga INTEGER NOT NULL,
          fgm INTEGER NOT NULL,
          fg3a INTEGER NOT NULL,
          fg3m INTEGER NOT NULL,
          fta INTEGER NOT NULL,
          ftm INTEGER NOT NULL,
          offensive_rebounds INTEGER NOT NULL,
          turnovers INTEGER NOT NULL,
          efg_pct REAL,
          tov_pct_estimated REAL,
          orb_pct_fg_miss_estimate REAL,
          free_throw_rate REAL,
          source_points_match INTEGER,
          quality_flags TEXT NOT NULL,
          PRIMARY KEY(game_id, team_abbr)
        );

        CREATE INDEX idx_pbp_events_game ON pbp_events(game_id, period, event_num);
        CREATE INDEX idx_possessions_game ON possessions(game_id, period, start_clock);
        CREATE INDEX idx_possessions_offense ON possessions(offense_team_abbr, game_id);
        CREATE INDEX idx_features_team ON team_game_features(team_abbr, game_id);
        """
    )


def gzip_file(source: Path, destination: Path) -> None:
    with source.open("rb") as source_handle, gzip.open(destination, "wb", compresslevel=6) as target:
        shutil.copyfileobj(source_handle, target, length=1024 * 1024)
