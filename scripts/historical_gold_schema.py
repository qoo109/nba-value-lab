#!/usr/bin/env python3
"""SQLite schema and helpers for the NBA Value Lab historical Gold layer."""

from __future__ import annotations

import hashlib
import sqlite3
from typing import Any

GOLD_SCHEMA_VERSION = "1.0.0"
GOLD_FEATURE_VERSION = "gold-team-game-v1"
ROLLING_WINDOWS = (5, 10, 20)
BASE_METRICS = (
    "pace",
    "off_rtg",
    "def_rtg",
    "net_rtg",
    "efg_pct",
    "tov_pct_estimated",
    "orb_pct_fg_miss_estimate",
    "free_throw_rate",
    "points",
    "opponent_points",
    "margin",
    "win",
)


def stable_id(*parts: Any) -> str:
    payload = "\x1f".join("" if part is None else str(part).strip() for part in parts)
    return hashlib.sha1(payload.encode("utf-8", errors="replace")).hexdigest()


def create_gold_schema(connection: sqlite3.Connection) -> None:
    rolling_columns = []
    for window in ROLLING_WINDOWS:
        for metric in BASE_METRICS:
            rolling_columns.append(f"{metric}_last_{window} REAL")
        rolling_columns.append(f"net_rtg_std_last_{window} REAL")
        rolling_columns.append(f"sample_size_last_{window} INTEGER NOT NULL")

    connection.executescript(
        f"""
        PRAGMA journal_mode=OFF;
        PRAGMA synchronous=OFF;
        PRAGMA temp_store=MEMORY;

        CREATE TABLE gold_metadata (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL
        );

        CREATE TABLE gold_team_game_features (
          feature_id TEXT PRIMARY KEY,
          game_id TEXT NOT NULL,
          game_date TEXT NOT NULL,
          season_label TEXT NOT NULL,
          team_abbr TEXT NOT NULL,
          opponent_abbr TEXT NOT NULL,
          is_home INTEGER NOT NULL,
          feature_cutoff_time TEXT NOT NULL,
          prior_games INTEGER NOT NULL,
          prior_home_games INTEGER NOT NULL,
          prior_away_games INTEGER NOT NULL,
          days_rest INTEGER,
          is_back_to_back INTEGER NOT NULL,
          games_last_3_days INTEGER NOT NULL,
          games_last_7_days INTEGER NOT NULL,
          home_off_rtg_prior REAL,
          home_def_rtg_prior REAL,
          home_net_rtg_prior REAL,
          home_win_rate_prior REAL,
          away_off_rtg_prior REAL,
          away_def_rtg_prior REAL,
          away_net_rtg_prior REAL,
          away_win_rate_prior REAL,
          opponent_strength_net_rtg_last_10 REAL,
          opponent_adjusted_net_rtg_last_10 REAL,
          trend_net_rtg_last_5_vs_10 REAL,
          {", ".join(rolling_columns)},
          source_version TEXT NOT NULL,
          feature_version TEXT NOT NULL,
          feature_generated_at TEXT NOT NULL,
          quality_flags TEXT NOT NULL,
          UNIQUE(game_id, team_abbr)
        );

        CREATE TABLE gold_matchup_features (
          matchup_feature_id TEXT PRIMARY KEY,
          game_id TEXT NOT NULL UNIQUE,
          game_date TEXT NOT NULL,
          home_team_abbr TEXT NOT NULL,
          away_team_abbr TEXT NOT NULL,
          home_feature_id TEXT NOT NULL,
          away_feature_id TEXT NOT NULL,
          net_rtg_last_5_diff REAL,
          net_rtg_last_10_diff REAL,
          net_rtg_last_20_diff REAL,
          pace_last_10_diff REAL,
          efg_pct_last_10_diff REAL,
          tov_pct_last_10_diff REAL,
          orb_pct_last_10_diff REAL,
          free_throw_rate_last_10_diff REAL,
          rest_days_diff REAL,
          prior_games_min INTEGER NOT NULL,
          evidence_coverage REAL NOT NULL,
          source_version TEXT NOT NULL,
          feature_version TEXT NOT NULL,
          feature_generated_at TEXT NOT NULL,
          quality_flags TEXT NOT NULL
        );

        CREATE INDEX idx_gold_team_date ON gold_team_game_features(team_abbr, game_date);
        CREATE INDEX idx_gold_game ON gold_team_game_features(game_id);
        CREATE INDEX idx_gold_matchup_date ON gold_matchup_features(game_date);
        """
    )
