#!/usr/bin/env python3
"""Aggregate-only audit for the user-supplied NBA betting CSV schema.

This tool never emits raw rows. It records file identity, schema, coverage,
structural consistency, and research-use gates for a legacy line archive whose
exact observation timestamps and bookmaker semantics are unavailable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

VERSION = "user-supplied-nba-betting-csv-audit-v1"
REQUIRED_COLUMNS = [
    "season", "date", "regular", "playoffs", "away", "home",
    "score_away", "score_home",
    "q1_away", "q2_away", "q3_away", "q4_away", "ot_away",
    "q1_home", "q2_home", "q3_home", "q4_home", "ot_home",
    "whos_favored", "spread", "total",
    "moneyline_away", "moneyline_home", "h2_spread", "h2_total",
    "id_spread", "id_total",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def american_implied(series: pd.Series) -> pd.Series:
    values = series.astype(float)
    return pd.Series(
        np.where(values > 0, 100.0 / (values + 100.0), (-values) / ((-values) + 100.0)),
        index=series.index,
    )


def finite(value: Any) -> float | None:
    number = float(value)
    return number if math.isfinite(number) else None


def audit(
    input_path: Path,
    *,
    source_id: str,
    source_url: str | None,
    supplied_at: str | None,
    provenance_status: str,
    minimum_games: int = 1000,
    expected_team_count: int = 30,
) -> dict[str, Any]:
    frame = pd.read_csv(input_path)
    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
    extra_columns = sorted(set(frame.columns) - set(REQUIRED_COLUMNS))
    if missing_columns:
        raise ValueError(f"missing required columns: {missing_columns}")

    dates = pd.to_datetime(frame["date"], errors="coerce")
    invalid_dates = int(dates.isna().sum())
    duplicate_game_keys = int(frame.duplicated(["date", "away", "home"]).sum())
    team_values = sorted(set(frame["away"].dropna().astype(str)) | set(frame["home"].dropna().astype(str)))

    away_score_sum = frame[["q1_away", "q2_away", "q3_away", "q4_away", "ot_away"]].sum(axis=1)
    home_score_sum = frame[["q1_home", "q2_home", "q3_home", "q4_home", "ot_home"]].sum(axis=1)
    away_score_mismatches = int((away_score_sum != frame["score_away"]).sum())
    home_score_mismatches = int((home_score_sum != frame["score_home"]).sum())

    total_mask = frame["total"].notna() & frame["id_total"].notna()
    actual_total = frame["score_away"] + frame["score_home"]
    expected_total = np.where(
        actual_total > frame["total"], 1, np.where(actual_total < frame["total"], 0, 2)
    )
    total_result_mismatches = int(
        (expected_total[total_mask.to_numpy()] != frame.loc[total_mask, "id_total"].to_numpy()).sum()
    )

    spread_mask = (
        frame["spread"].notna()
        & frame["id_spread"].notna()
        & frame["whos_favored"].isin(["home", "away"])
    )
    favorite_margin = np.where(
        frame["whos_favored"].eq("home"),
        frame["score_home"] - frame["score_away"],
        frame["score_away"] - frame["score_home"],
    )
    expected_spread = np.where(
        favorite_margin > frame["spread"], 1, np.where(favorite_margin < frame["spread"], 0, 2)
    )
    spread_result_mismatches = int(
        (expected_spread[spread_mask.to_numpy()] != frame.loc[spread_mask, "id_spread"].to_numpy()).sum()
    )

    moneyline_complete = frame["moneyline_home"].notna() & frame["moneyline_away"].notna()
    moneyline_partial = frame["moneyline_home"].notna() ^ frame["moneyline_away"].notna()
    moneyline_values = frame.loc[moneyline_complete, ["moneyline_home", "moneyline_away"]]
    invalid_moneyline_values = int(
        (((moneyline_values.abs() < 100) | (moneyline_values == 0))).sum().sum()
    )
    overround = (
        american_implied(frame.loc[moneyline_complete, "moneyline_home"])
        + american_implied(frame.loc[moneyline_complete, "moneyline_away"])
        - 1.0
    )
    overround_outside_range = int(((overround < -0.05) | (overround > 0.30)).sum())
    overround_summary = {
        "count": int(overround.count()),
        "mean": finite(overround.mean()) if len(overround) else None,
        "min": finite(overround.min()) if len(overround) else None,
        "p01": finite(overround.quantile(0.01)) if len(overround) else None,
        "p50": finite(overround.quantile(0.50)) if len(overround) else None,
        "p99": finite(overround.quantile(0.99)) if len(overround) else None,
        "max": finite(overround.max()) if len(overround) else None,
    }

    market_columns = [
        "spread", "total", "moneyline_away", "moneyline_home", "h2_spread", "h2_total"
    ]
    coverage_by_season: dict[str, dict[str, int]] = {}
    for season, group in frame.groupby("season", dropna=False):
        coverage_by_season[str(int(season))] = {
            column: int(group[column].notna().sum()) for column in market_columns
        } | {"games": int(len(group))}

    game_type_counts = {
        "regular": int((frame["regular"] & ~frame["playoffs"]).sum()),
        "playoffs": int((~frame["regular"] & frame["playoffs"]).sum()),
        "other_or_play_in": int((~frame["regular"] & ~frame["playoffs"]).sum()),
        "invalid_both_true": int((frame["regular"] & frame["playoffs"]).sum()),
    }

    null_counts = {column: int(count) for column, count in frame.isna().sum().items()}
    structural_pass = all([
        invalid_dates == 0,
        duplicate_game_keys == 0,
        away_score_mismatches == 0,
        home_score_mismatches == 0,
        total_result_mismatches == 0,
        spread_result_mismatches == 0,
        invalid_moneyline_values == 0,
        overround_outside_range == 0,
        game_type_counts["invalid_both_true"] == 0,
        len(frame) >= minimum_games,
        len(team_values) == expected_team_count,
    ])

    provenance_pending = provenance_status != "user_confirmed"
    formal_outcome = (
        "ROLE_LIMITED_LEGACY_MARKET_ARCHIVE_ELIGIBLE_PROVENANCE_PENDING"
        if structural_pass and provenance_pending
        else "ROLE_LIMITED_LEGACY_MARKET_ARCHIVE_ELIGIBLE"
        if structural_pass
        else "STRUCTURAL_RESEARCH_BLOCKED"
    )

    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "source": {
            "source_id": source_id,
            "source_url": source_url,
            "input_file": input_path.name,
            "input_bytes": int(input_path.stat().st_size),
            "input_sha256": file_sha256(input_path),
            "supplied_at": supplied_at,
            "provenance_status": provenance_status,
            "provenance_note": (
                "User supplied the local file. Exact source identity remains pending "
                "unless the user confirms the dataset URL."
            ),
            "raw_rows_emitted": 0,
            "raw_file_committed": False,
        },
        "schema": {
            "row_count": int(len(frame)),
            "column_count": int(len(frame.columns)),
            "columns": list(frame.columns),
            "required_columns_present": True,
            "extra_columns": extra_columns,
        },
        "coverage": {
            "date_min": None if invalid_dates == len(frame) else dates.min().date().isoformat(),
            "date_max": None if invalid_dates == len(frame) else dates.max().date().isoformat(),
            "season_min": int(frame["season"].min()),
            "season_max": int(frame["season"].max()),
            "season_count": int(frame["season"].nunique()),
            "team_count": len(team_values),
            "team_codes": team_values,
            "game_type_counts": game_type_counts,
            "market_non_null_by_season": coverage_by_season,
            "moneyline_complete_games": int(moneyline_complete.sum()),
            "moneyline_missing_games": int((~moneyline_complete).sum()),
            "moneyline_partial_pair_games": int(moneyline_partial.sum()),
        },
        "quality": {
            "null_counts": null_counts,
            "invalid_date_rows": invalid_dates,
            "duplicate_game_key_groups": duplicate_game_keys,
            "away_score_component_mismatches": away_score_mismatches,
            "home_score_component_mismatches": home_score_mismatches,
            "id_total_mismatches": total_result_mismatches,
            "id_spread_mismatches": spread_result_mismatches,
            "invalid_moneyline_values": invalid_moneyline_values,
            "moneyline_overround": overround_summary,
            "overround_outside_minus5_to_30_pct": overround_outside_range,
            "all_structural_gates_pass": structural_pass,
        },
        "semantics": {
            "bookmaker_available": False,
            "exact_observed_at_available": False,
            "opening_closing_classified": False,
            "point_in_time_join_ready": False,
            "missing_moneyline_rows_treated_as_zero": False,
            "other_or_play_in_rows_require_explicit_game_type": True,
        },
        "decision": {
            "formal_outcome": formal_outcome,
            "ready_for_game_identity_and_score_crosscheck": structural_pass,
            "ready_for_spread_total_descriptive_research": structural_pass,
            "ready_for_moneyline_forecast_benchmark_pilot": structural_pass and int(moneyline_complete.sum()) >= 500,
            "ready_for_closing_market_benchmark": False,
            "ready_for_point_in_time_odds_layer": False,
            "ready_for_clv_analysis": False,
            "ready_for_entry_price_roi_backtest": False,
            "ready_for_betting_edge_claim": False,
            "existing_silver_replacement": False,
            "existing_gold_replacement": False,
            "model_retraining_authorized": False,
            "formal_stake": 0,
        },
    }
    return report


def write_report(report: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def self_test(output_path: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="nbavl-user-csv-audit-") as temp_name:
        source = Path(temp_name) / "fixture.csv"
        rows = [
            {
                "season": 2025, "date": "2024-10-22", "regular": True, "playoffs": False,
                "away": "ny", "home": "bos", "score_away": 109, "score_home": 132,
                "q1_away": 24, "q2_away": 31, "q3_away": 32, "q4_away": 22, "ot_away": 0,
                "q1_home": 43, "q2_home": 31, "q3_home": 39, "q4_home": 19, "ot_home": 0,
                "whos_favored": "home", "spread": 5.5, "total": 222.5,
                "moneyline_away": 180, "moneyline_home": -210,
                "h2_spread": 2.5, "h2_total": 110.5, "id_spread": 1, "id_total": 1,
            }
        ]
        pd.DataFrame(rows, columns=REQUIRED_COLUMNS).to_csv(source, index=False)
        report = audit(
            source,
            source_id="fixture",
            source_url=None,
            supplied_at="2026-07-21T09:48:48+08:00",
            provenance_status="pending_user_confirmation",
            minimum_games=1,
            expected_team_count=2,
        )
        assert report["quality"]["all_structural_gates_pass"] is True
        assert report["decision"]["ready_for_point_in_time_odds_layer"] is False
        assert report["decision"]["ready_for_clv_analysis"] is False
        assert report["source"]["raw_rows_emitted"] == 0
        write_report(report, output_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-id", default="user_supplied_nba_betting_csv")
    parser.add_argument("--source-url")
    parser.add_argument("--supplied-at")
    parser.add_argument(
        "--provenance-status",
        choices=("pending_user_confirmation", "user_confirmed"),
        default="pending_user_confirmation",
    )
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output)
        print("user-supplied NBA betting CSV audit self-test passed")
        return
    if not args.input:
        parser.error("--input is required unless --self-test is used")
    report = audit(
        args.input,
        source_id=args.source_id,
        source_url=args.source_url,
        supplied_at=args.supplied_at,
        provenance_status=args.provenance_status,
    )
    write_report(report, args.output)
    print(json.dumps(report["decision"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
