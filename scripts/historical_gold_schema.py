#!/usr/bin/env python3
"""SQLite schema and shared helpers for NBA Value Lab historical Gold v1."""

from __future__ import annotations

import gzip
import shutil
import sqlite3
from pathlib import Path

GOLD_SCHEMA_VERSION = "1.0.0"
FEATURE_VERSION = "gold-v1-rolling-schedule-opponent"
WINDOWS = (5, 10, 20)
METRICS = (
    "points",
    "opponent_points",
    "pace",
    "off_rtg",
    "def_rtg",
    "net_rtg",
    "efg_pct",
    "tov_pct_estimated",
    "orb_pct_fg_miss_estimate",
    "free_throw_rate",
    "win",
    "margin",
)


def safe_mean(values: list[float | int | None]) -> float | None:
    clean = [float(value) for value in values if value is not None]
    return round(sum(clean) / len(clean), 6) if clean else None


def create_gold_schema(connection: sqlite3.Connection) -> None:
    rolling_columns = []
    for window in WINDOWS:
        rolling_columns.extend(f"{metric}_l{window} REAL" for metric in METRICS)

    connection.executescript(
        f"""
        PRAGMA journal_mode=OFF;
        PRAGMA synchronous=OFF;
        PRAGMA temp_store=MEMORY;
        PRAGMA foreign_keys=OFF;

        CREATE TABLE gold_metadata (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL
        );

        CREATE TABLE gold_team_game_features (
          game_id TEXT NOT NULL,
          game_date TEXT NOT NULL,
          season_label TEXT NOT NULL,
          team_abbr TEXT NOT NULL,
          opponent_abbr TEXT NOT NULL,
          is_home INTEGER NOT NULL,
          feature_cutoff_date TEXT NOT NULL,
          prior_games INTEGER NOT NULL,
          rest_days INTEGER,
          is_back_to_back INTEGER NOT NULL,
          games_last_3_days INTEGER NOT NULL,
          games_last_4_days INTEGER NOT NULL,
          games_last_7_days INTEGER NOT NULL,
          home_games_prior INTEGER NOT NULL,
          away_games_prior INTEGER NOT NULL,
          home_off_rtg_prior REAL,
          home_def_rtg_prior REAL,
          home_net_rtg_prior REAL,
          home_win_pct_prior REAL,
          away_off_rtg_prior REAL,
          away_def_rtg_prior REAL,
          away_net_rtg_prior REAL,
          away_win_pct_prior REAL,
          season_off_rtg_prior REAL,
          season_def_rtg_prior REAL,
          season_net_rtg_prior REAL,
          season_pace_prior REAL,
          season_win_pct_prior REAL,
          opponent_strength_net_rtg_prior REAL,
          net_rtg_trend_l10 REAL,
          net_rtg_std_l10 REAL,
          data_confidence REAL,
          {", ".join(rolling_columns)},
          source_version TEXT NOT NULL,
          feature_version TEXT NOT NULL,
          feature_generated_at TEXT NOT NULL,
          quality_flags TEXT NOT NULL,
          PRIMARY KEY(game_id, team_abbr)
        );

        CREATE TABLE gold_matchup_features (
          game_id TEXT PRIMARY KEY,
          game_date TEXT NOT NULL,
          season_label TEXT NOT NULL,
          home_team_abbr TEXT NOT NULL,
          away_team_abbr TEXT NOT NULL,
          feature_cutoff_date TEXT NOT NULL,
          home_prior_games INTEGER NOT NULL,
          away_prior_games INTEGER NOT NULL,
          rest_days_diff REAL,
          pace_l10_diff REAL,
          off_rtg_l10_diff REAL,
          def_rtg_l10_diff REAL,
          net_rtg_l10_diff REAL,
          efg_pct_l10_diff REAL,
          tov_pct_l10_diff REAL,
          orb_pct_l10_diff REAL,
          free_throw_rate_l10_diff REAL,
          season_net_rtg_diff REAL,
          opponent_adjusted_net_rtg_diff REAL,
          home_data_confidence REAL,
          away_data_confidence REAL,
          source_version TEXT NOT NULL,
          feature_version TEXT NOT NULL,
          feature_generated_at TEXT NOT NULL,
          quality_flags TEXT NOT NULL
        );

        CREATE INDEX idx_gold_team_date ON gold_team_game_features(team_abbr, game_date);
        CREATE INDEX idx_gold_matchup_date ON gold_matchup_features(game_date);
        """
    )


def gunzip_to(source: Path, destination: Path) -> None:
    with gzip.open(source, "rb") as src, destination.open("wb") as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)


def gzip_file(source: Path, destination: Path) -> None:
    with source.open("rb") as src, gzip.open(destination, "wb", compresslevel=6) as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)
