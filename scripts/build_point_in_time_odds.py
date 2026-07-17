#!/usr/bin/env python3
"""Build a leakage-safe point-in-time NBA odds layer and research backtest."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ODDS_LAYER_VERSION = "point-in-time-odds-v1"
REQUIRED_PREDICTION_COLUMNS = {
    "game_id", "game_date", "target_season", "home_team_abbr", "away_team_abbr",
    "actual_home_win", "raw_probability",
}
REQUIRED_ODDS_COLUMNS = {
    "game_id", "commence_time_utc", "observed_at_utc", "bookmaker",
    "market_key", "snapshot_label", "home_price_decimal", "away_price_decimal",
}
OPTIONAL_ODDS_DEFAULTS = {
    "source_id": "user_odds",
    "source_event_id": "",
    "season_label": "",
    "home_team_abbr": "",
    "away_team_abbr": "",
    "fetched_at_utc": "",
    "raw_hash": "",
    "adapter_version": ODDS_LAYER_VERSION,
}
DEFAULT_THRESHOLDS = (0.0, 0.01, 0.02, 0.025, 0.03, 0.05)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_utc(value: str, field: str) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field} is required")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include a timezone: {value}")
    return parsed.astimezone(timezone.utc)


def iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def as_float(value: Any, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric: {value!r}") from exc
    if not math.isfinite(result):
        raise ValueError(f"{field} must be finite")
    return result


def clean_game_id(value: Any) -> str:
    text = str(value or "").strip()
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    return text


def read_csv_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        return [dict(row) for row in reader], fields


def load_predictions(path: Path) -> list[dict[str, Any]]:
    raw, fields = read_csv_rows(path)
    missing = sorted(REQUIRED_PREDICTION_COLUMNS - set(fields))
    if missing:
        raise ValueError(f"prediction file missing columns: {missing}")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw:
        game_id = clean_game_id(item["game_id"])
        if not game_id:
            raise ValueError("prediction game_id cannot be blank")
        if game_id in seen:
            raise ValueError(f"duplicate prediction game_id: {game_id}")
        seen.add(game_id)
        actual = int(float(item["actual_home_win"]))
        if actual not in (0, 1):
            raise ValueError(f"actual_home_win must be 0 or 1 for {game_id}")
        probability = as_float(item["raw_probability"], "raw_probability")
        if not 0 < probability < 1:
            raise ValueError(f"raw_probability must be between 0 and 1 for {game_id}")
        rows.append({
            **item,
            "game_id": game_id,
            "actual_home_win": actual,
            "raw_probability": probability,
            "home_team_abbr": str(item["home_team_abbr"]).strip().upper(),
            "away_team_abbr": str(item["away_team_abbr"]).strip().upper(),
        })
    rows.sort(key=lambda row: (str(row["game_date"]), row["game_id"]))
    return rows


def canonical_snapshot(value: Any) -> str:
    text = str(value or "").strip()
    lower = text.lower().replace(" ", "")
    aliases = {
        "closing": "Closing", "close": "Closing",
        "t-60": "T-60m", "t-60m": "T-60m", "60m": "T-60m",
        "t-5": "T-5m", "t-5m": "T-5m", "5m": "T-5m",
        "21:00": "21:00",
    }
    return aliases.get(lower, text)


def normalize_odds(path: Path, predictions: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    raw, fields = read_csv_rows(path)
    missing = sorted(REQUIRED_ODDS_COLUMNS - set(fields))
    if missing:
        raise ValueError(f"odds file missing columns: {missing}")
    prediction_map = {row["game_id"]: row for row in predictions}
    output: list[dict[str, Any]] = []
    duplicate_keys: set[tuple[str, str, str, str]] = set()
    duplicate_count = 0
    point_in_time_violations = 0
    team_mismatches = 0
    unknown_games = 0
    invalid_overround = 0

    for line_number, original in enumerate(raw, 2):
        item = {**OPTIONAL_ODDS_DEFAULTS, **original}
        game_id = clean_game_id(item["game_id"])
        prediction = prediction_map.get(game_id)
        if prediction is None:
            unknown_games += 1
            continue
        market = str(item["market_key"]).strip().lower()
        if market not in {"h2h", "moneyline"}:
            continue
        market = "h2h"
        bookmaker = str(item["bookmaker"]).strip()
        if not bookmaker:
            raise ValueError(f"bookmaker is blank at CSV line {line_number}")
        observed = parse_utc(item["observed_at_utc"], "observed_at_utc")
        commence = parse_utc(item["commence_time_utc"], "commence_time_utc")
        if observed >= commence:
            point_in_time_violations += 1
            continue
        fetched_text = str(item.get("fetched_at_utc") or "").strip()
        fetched = parse_utc(fetched_text, "fetched_at_utc") if fetched_text else observed
        flags: list[str] = []
        if fetched < observed:
            flags.append("fetched_before_observed")
        supplied_home = str(item.get("home_team_abbr") or "").strip().upper()
        supplied_away = str(item.get("away_team_abbr") or "").strip().upper()
        if supplied_home and supplied_home != prediction["home_team_abbr"]:
            flags.append("home_team_mismatch")
            team_mismatches += 1
        if supplied_away and supplied_away != prediction["away_team_abbr"]:
            flags.append("away_team_mismatch")
            team_mismatches += 1
        if "home_team_mismatch" in flags or "away_team_mismatch" in flags:
            continue
        home_price = as_float(item["home_price_decimal"], "home_price_decimal")
        away_price = as_float(item["away_price_decimal"], "away_price_decimal")
        if not (1.001 <= home_price <= 100 and 1.001 <= away_price <= 100):
            raise ValueError(f"decimal prices out of range for game {game_id}")
        home_implied = 1.0 / home_price
        away_implied = 1.0 / away_price
        total_implied = home_implied + away_implied
        overround = total_implied - 1.0
        if not (-0.05 <= overround <= 0.30):
            flags.append("overround_outside_expected_range")
            invalid_overround += 1
        fair_home = home_implied / total_implied
        fair_away = away_implied / total_implied
        snapshot = canonical_snapshot(item["snapshot_label"])
        key = (game_id, bookmaker.lower(), market, iso_z(observed))
        if key in duplicate_keys:
            duplicate_count += 1
            continue
        duplicate_keys.add(key)
        raw_hash = str(item.get("raw_hash") or "").strip()
        if not raw_hash:
            hash_payload = "\x1f".join([
                game_id, bookmaker, market, iso_z(observed),
                f"{home_price:.8f}", f"{away_price:.8f}",
            ])
            raw_hash = hashlib.sha256(hash_payload.encode()).hexdigest()
        output.append({
            "game_id": game_id,
            "season_label": str(item.get("season_label") or prediction["target_season"]).strip(),
            "game_date": prediction["game_date"],
            "home_team_abbr": prediction["home_team_abbr"],
            "away_team_abbr": prediction["away_team_abbr"],
            "commence_time_utc": iso_z(commence),
            "observed_at_utc": iso_z(observed),
            "fetched_at_utc": iso_z(fetched),
            "minutes_before_start": round((commence - observed).total_seconds() / 60.0, 3),
            "bookmaker": bookmaker,
            "market_key": market,
            "snapshot_label": snapshot,
            "home_price_decimal": round(home_price, 8),
            "away_price_decimal": round(away_price, 8),
            "home_implied_probability": round(home_implied, 10),
            "away_implied_probability": round(away_implied, 10),
            "overround": round(overround, 10),
            "fair_home_probability": round(fair_home, 10),
            "fair_away_probability": round(fair_away, 10),
            "source_id": str(item.get("source_id") or "user_odds").strip(),
            "source_event_id": str(item.get("source_event_id") or "").strip(),
            "raw_hash": raw_hash,
            "adapter_version": str(item.get("adapter_version") or ODDS_LAYER_VERSION).strip(),
            "quality_flags": ",".join(sorted(set(flags))),
        })

    output.sort(key=lambda row: (
        row["game_date"], row["game_id"], row["bookmaker"].lower(), row["observed_at_utc"]
    ))
    qa = {
        "input_rows": len(raw),
        "normalized_rows": len(output),
        "unknown_game_rows_excluded": unknown_games,
        "duplicate_quote_rows_excluded": duplicate_count,
        "point_in_time_violations": point_in_time_violations,
        "team_mismatches": team_mismatches,
        "overround_outside_expected_range": invalid_overround,
    }
    return output, qa


def choose_quotes(
    odds_rows: list[dict[str, Any]],
    entry_snapshot: str,
    bookmaker: str | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in odds_rows:
        if bookmaker and row["bookmaker"].lower() != bookmaker.lower():
            continue
        grouped[(row["game_id"], row["bookmaker"])].append(row)
    pairs: list[dict[str, Any]] = []
    entry_missing = closing_missing = 0
    for (game_id, book), rows in grouped.items():
        rows.sort(key=lambda row: row["observed_at_utc"])
        entries = [row for row in rows if canonical_snapshot(row["snapshot_label"]) == entry_snapshot]
        if not entries:
            entry_missing += 1
            continue
        entry = entries[-1]
        explicit_closing = [row for row in rows if canonical_snapshot(row["snapshot_label"]) == "Closing"]
        closing_candidates = explicit_closing or [
            row for row in rows
            if row["observed_at_utc"] >= entry["observed_at_utc"]
            and row["observed_at_utc"] < row["commence_time_utc"]
        ]
        closing = closing_candidates[-1] if closing_candidates else None
        if closing is None:
            closing_missing += 1
        pairs.append({"game_id": game_id, "bookmaker": book, "entry": entry, "closing": closing})
    return pairs, {
        "bookmaker_game_groups": len(grouped),
        "entry_snapshot": entry_snapshot,
        "entry_missing_groups": entry_missing,
        "closing_missing_groups": closing_missing,
    }


def binary_metrics(y: list[int], p: list[float]) -> dict[str, float | None]:
    if not y:
        return {"rows": 0, "log_loss": None, "brier_score": None, "accuracy": None}
    clipped = [min(max(value, 1e-9), 1 - 1e-9) for value in p]
    logloss = -sum(
        actual * math.log(probability) + (1 - actual) * math.log(1 - probability)
        for actual, probability in zip(y, clipped)
    ) / len(y)
    brier = sum((probability - actual) ** 2 for actual, probability in zip(y, clipped)) / len(y)
    accuracy = sum((probability >= 0.5) == bool(actual) for actual, probability in zip(y, clipped)) / len(y)
    return {
        "rows": len(y),
        "log_loss": round(logloss, 8),
        "brier_score": round(brier, 8),
        "accuracy": round(accuracy, 8),
    }


def maximum_drawdown(profits: Iterable[float]) -> float:
    cumulative = peak = 0.0
    max_drawdown = 0.0
    for profit in profits:
        cumulative += profit
        peak = max(peak, cumulative)
        max_drawdown = min(max_drawdown, cumulative - peak)
    return round(max_drawdown, 6)


def bootstrap_roi(records: list[dict[str, Any]], samples: int = 1000) -> list[float] | None:
    if len(records) < 30:
        return None
    rng = random.Random(42)
    rois = []
    for _ in range(samples):
        sample = [records[rng.randrange(len(records))]["profit_units"] for _ in records]
        rois.append(sum(sample) / len(sample))
    rois.sort()
    return [round(rois[int(samples * 0.025)], 6), round(rois[int(samples * 0.975)], 6)]


def summarize_bets(records: list[dict[str, Any]]) -> dict[str, Any]:
    if not records:
        return {
            "bets": 0, "profit_units": 0.0, "roi": None, "win_rate": None,
            "average_edge": None, "average_expected_value": None,
            "closing_line_coverage": 0.0, "average_clv_price": None,
            "positive_clv_rate": None, "maximum_drawdown_units": 0.0,
            "roi_bootstrap_95pct": None,
        }
    records = sorted(records, key=lambda row: (row["game_date"], row["game_id"], row["bookmaker"]))
    closing = [row for row in records if row["clv_price"] is not None]
    return {
        "bets": len(records),
        "profit_units": round(sum(row["profit_units"] for row in records), 6),
        "roi": round(sum(row["profit_units"] for row in records) / len(records), 8),
        "win_rate": round(sum(row["bet_won"] for row in records) / len(records), 8),
        "average_edge": round(sum(row["selected_edge"] for row in records) / len(records), 8),
        "average_expected_value": round(sum(row["expected_value"] for row in records) / len(records), 8),
        "closing_line_coverage": round(len(closing) / len(records), 8),
        "average_clv_price": (
            round(sum(row["clv_price"] for row in closing) / len(closing), 8) if closing else None
        ),
        "average_clv_probability": (
            round(sum(row["clv_probability"] for row in closing) / len(closing), 8) if closing else None
        ),
        "positive_clv_rate": (
            round(sum(row["clv_price"] > 0 for row in closing) / len(closing), 8) if closing else None
        ),
        "maximum_drawdown_units": maximum_drawdown(row["profit_units"] for row in records),
        "roi_bootstrap_95pct": bootstrap_roi(records),
    }


def build_market_records(
    predictions: list[dict[str, Any]],
    quote_pairs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    prediction_map = {row["game_id"]: row for row in predictions}
    output: list[dict[str, Any]] = []
    for pair in quote_pairs:
        prediction = prediction_map[pair["game_id"]]
        entry = pair["entry"]
        closing = pair["closing"]
        model_home = prediction["raw_probability"]
        home_edge = model_home - entry["fair_home_probability"]
        side = "home" if home_edge >= 0 else "away"
        model_side = model_home if side == "home" else 1.0 - model_home
        fair_side = entry["fair_home_probability"] if side == "home" else entry["fair_away_probability"]
        entry_price = entry["home_price_decimal"] if side == "home" else entry["away_price_decimal"]
        actual_home = prediction["actual_home_win"]
        won = int(actual_home == 1) if side == "home" else int(actual_home == 0)
        profit = entry_price - 1.0 if won else -1.0
        closing_price = None
        closing_fair = None
        if closing:
            closing_price = closing["home_price_decimal"] if side == "home" else closing["away_price_decimal"]
            closing_fair = closing["fair_home_probability"] if side == "home" else closing["fair_away_probability"]
        output.append({
            "game_id": pair["game_id"],
            "game_date": prediction["game_date"],
            "season_label": prediction["target_season"],
            "home_team_abbr": prediction["home_team_abbr"],
            "away_team_abbr": prediction["away_team_abbr"],
            "bookmaker": pair["bookmaker"],
            "entry_snapshot": entry["snapshot_label"],
            "entry_observed_at_utc": entry["observed_at_utc"],
            "closing_observed_at_utc": closing["observed_at_utc"] if closing else "",
            "actual_home_win": actual_home,
            "model_home_probability": round(model_home, 10),
            "market_fair_home_probability": entry["fair_home_probability"],
            "home_probability_edge": round(home_edge, 10),
            "selected_side": side,
            "selected_edge": round(abs(home_edge), 10),
            "model_selected_probability": round(model_side, 10),
            "entry_fair_probability": round(fair_side, 10),
            "entry_price_decimal": round(entry_price, 8),
            "expected_value": round(model_side * entry_price - 1.0, 10),
            "bet_won": won,
            "profit_units": round(profit, 8),
            "closing_price_decimal": round(closing_price, 8) if closing_price else None,
            "closing_fair_probability": round(closing_fair, 10) if closing_fair else None,
            "clv_price": round(entry_price / closing_price - 1.0, 10) if closing_price else None,
            "clv_probability": round(closing_fair - fair_side, 10) if closing_fair else None,
            "entry_overround": entry["overround"],
            "entry_source_id": entry["source_id"],
            "entry_raw_hash": entry["raw_hash"],
            "quality_flags": entry["quality_flags"],
        })
    output.sort(key=lambda row: (row["game_date"], row["game_id"], row["bookmaker"]))
    return output


def choose_primary_bookmaker(records: list[dict[str, Any]], requested: str | None) -> str | None:
    if requested:
        return requested
    counts: dict[str, set[str]] = defaultdict(set)
    for row in records:
        counts[row["bookmaker"]].add(row["game_id"])
    if not counts:
        return None
    return sorted(counts, key=lambda book: (-len(counts[book]), book.lower()))[0]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build(
    predictions_path: Path,
    odds_path: Path,
    output_dir: Path,
    entry_snapshot: str,
    bookmaker: str | None,
    minimum_edge: float,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    predictions = load_predictions(predictions_path)
    normalized, odds_qa = normalize_odds(odds_path, predictions)
    snapshot = canonical_snapshot(entry_snapshot)
    pairs, pairing_qa = choose_quotes(normalized, snapshot, bookmaker)
    records = build_market_records(predictions, pairs)
    primary_bookmaker = choose_primary_bookmaker(records, bookmaker)
    primary_records = [
        row for row in records
        if primary_bookmaker and row["bookmaker"].lower() == primary_bookmaker.lower()
    ]
    actual = [row["actual_home_win"] for row in primary_records]
    model_p = [row["model_home_probability"] for row in primary_records]
    market_p = [row["market_fair_home_probability"] for row in primary_records]
    threshold_grid = sorted(set((*DEFAULT_THRESHOLDS, minimum_edge)))
    backtests = {}
    for threshold in threshold_grid:
        selected = [
            row for row in primary_records
            if row["selected_edge"] >= threshold and row["expected_value"] > 0
        ]
        backtests[f"{threshold:.3f}"] = summarize_bets(selected)
    chosen_bets = [
        row for row in primary_records
        if row["selected_edge"] >= minimum_edge and row["expected_value"] > 0
    ]
    seasons = sorted({row["season_label"] for row in primary_records})
    source_ids = sorted({row["entry_source_id"] for row in primary_records})
    unique_games = len({row["game_id"] for row in primary_records})
    closing_coverage = (
        sum(row["clv_price"] is not None for row in primary_records) / len(primary_records)
        if primary_records else 0.0
    )
    leakage_pass = odds_qa["point_in_time_violations"] == 0
    source_is_real = bool(source_ids) and all(source != "synthetic_odds" for source in source_ids)
    research_ready = (
        source_is_real
        and leakage_pass
        and odds_qa["team_mismatches"] == 0
        and unique_games >= 500
        and len(seasons) >= 3
        and closing_coverage >= 0.80
        and primary_bookmaker is not None
    )
    report = {
        "odds_layer_version": ODDS_LAYER_VERSION,
        "generated_at": utc_now(),
        "source": {
            "prediction_file": str(predictions_path),
            "odds_file": str(odds_path),
            "prediction_rows": len(predictions),
            "source_ids": source_ids,
        },
        "configuration": {
            "entry_snapshot": snapshot,
            "requested_bookmaker": bookmaker,
            "primary_bookmaker": primary_bookmaker,
            "minimum_edge": minimum_edge,
            "selection_rule": "selected_edge >= minimum_edge and expected_value > 0",
            "stake_rule": "flat 1 unit",
        },
        "coverage": {
            "normalized_odds_rows": len(normalized),
            "bookmaker_game_pairs": len(records),
            "primary_bookmaker_games": unique_games,
            "primary_seasons": seasons,
            "prediction_match_rate": round(unique_games / len(predictions), 8) if predictions else 0.0,
            "closing_line_coverage": round(closing_coverage, 8),
        },
        "quality": {
            **odds_qa,
            **pairing_qa,
            "strict_observed_before_commence_required": True,
            "same_bookmaker_entry_and_closing": True,
            "decimal_price_range_enforced": True,
            "two_way_proportional_devig": True,
        },
        "probability_comparison": {
            "model_raw_logistic_elo": binary_metrics(actual, model_p),
            "market_no_vig": binary_metrics(actual, market_p),
        },
        "backtest": {
            "threshold_grid": backtests,
            "selected_threshold": f"{minimum_edge:.3f}",
            "selected_summary": summarize_bets(chosen_bets),
            "by_bookmaker_coverage": {
                book: len({row["game_id"] for row in records if row["bookmaker"] == book})
                for book in sorted({row["bookmaker"] for row in records})
            },
        },
        "guardrails": {
            "odds_observed_before_game_start": leakage_pass,
            "model_probability_method": "raw_logistic_elo",
            "odds_used_for_model_training": False,
            "closing_line_used_for_selection": False,
            "target_outcome_used_for_selection": False,
            "bookmaker_selected_by_coverage_not_performance": bookmaker is None,
            "public_betting_claims_allowed": False,
        },
        "decision": {
            "odds_layer_build_complete": True,
            "ready_for_research_market_backtest": research_ready,
            "ready_for_betting_edge_claim": False,
            "next_gate": (
                "run holdout and sensitivity analysis before any betting-edge claim"
                if research_ready else
                "supply at least 500 matched games across 3 seasons with >=80% same-book closing coverage"
            ),
        },
    }
    write_csv(output_dir / "normalized-odds.csv", normalized)
    write_csv(output_dir / "market-edge-records.csv", records)
    (output_dir / "point-in-time-odds-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def self_test(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    predictions = output_dir / "synthetic-predictions.csv"
    odds = output_dir / "synthetic-odds.csv"
    prediction_rows = []
    odds_rows = []
    for index in range(120):
        game_id = f"g{index:04d}"
        season = ("2021-22", "2022-23", "2023-24")[index // 40]
        date_text = f"202{1 + index // 40}-11-{1 + index % 28:02d}"
        actual = int(index % 3 != 0)
        model_p = 0.64 if actual else 0.52
        prediction_rows.append({
            "target_season": season,
            "calibration_seasons": "",
            "game_id": game_id,
            "game_date": date_text,
            "home_team_abbr": "AAA",
            "away_team_abbr": "BBB",
            "actual_home_win": actual,
            "raw_probability": model_p,
            "platt_probability": model_p,
            "isotonic_probability": model_p,
            "elo_probability": 0.60,
        })
        commence = datetime(2024, 1, 1 + (index % 20), 1, 0, tzinfo=timezone.utc)
        for label, minutes, home_price, away_price in (
            ("T-60m", 60, 1.80, 2.10),
            ("Closing", 5, 1.76, 2.18),
        ):
            observed = commence.timestamp() - minutes * 60
            odds_rows.append({
                "source_id": "synthetic_odds",
                "source_event_id": f"event-{game_id}",
                "game_id": game_id,
                "season_label": season,
                "home_team_abbr": "AAA",
                "away_team_abbr": "BBB",
                "commence_time_utc": iso_z(commence),
                "observed_at_utc": iso_z(datetime.fromtimestamp(observed, tz=timezone.utc)),
                "fetched_at_utc": iso_z(datetime.fromtimestamp(observed + 30, tz=timezone.utc)),
                "bookmaker": "FixtureBook",
                "market_key": "h2h",
                "snapshot_label": label,
                "home_price_decimal": home_price,
                "away_price_decimal": away_price,
                "raw_hash": "",
                "adapter_version": "fixture",
            })
    write_csv(predictions, prediction_rows)
    write_csv(odds, odds_rows)
    report = build(predictions, odds, output_dir / "result", "T-60m", None, 0.025)
    assert report["quality"]["point_in_time_violations"] == 0
    assert report["coverage"]["primary_bookmaker_games"] == 120
    assert report["coverage"]["closing_line_coverage"] == 1.0
    assert report["decision"]["odds_layer_build_complete"] is True
    assert report["decision"]["ready_for_research_market_backtest"] is False
    assert (output_dir / "result" / "normalized-odds.csv").exists()
    assert (output_dir / "result" / "market-edge-records.csv").exists()
    (output_dir / "self-test.json").write_text('{"passed":true}\n', encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--odds-csv", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--entry-snapshot", default="T-60m")
    parser.add_argument("--bookmaker")
    parser.add_argument("--minimum-edge", type=float, default=0.025)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("point-in-time odds layer self-test passed")
        return
    if not args.predictions or not args.odds_csv:
        parser.error("--predictions and --odds-csv are required unless --self-test is used")
    if not 0 <= args.minimum_edge <= 0.25:
        parser.error("--minimum-edge must be between 0 and 0.25")
    report = build(
        args.predictions,
        args.odds_csv,
        args.output_dir,
        args.entry_snapshot,
        args.bookmaker,
        args.minimum_edge,
    )
    print(json.dumps(report["decision"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
