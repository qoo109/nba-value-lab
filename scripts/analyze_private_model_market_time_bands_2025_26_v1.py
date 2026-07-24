#!/usr/bin/env python3
"""Private 2025-26 frozen-model versus no-vig market sensitivity.

The script selects the nearest valid pre-tip collector batch to T-60 and reports
nested ±5/15/30/60-minute timing bands. Collector timestamps are not verified
provider-origin quote times, so this is diagnostic only. It does not calculate
EV, ROI, CLV, drawdown, staking, bet selections, or betting-edge claims.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
from sklearn.metrics import roc_auc_score

FORMAL_STATE = "PRIVATE_MODEL_MARKET_TIME_BANDED_SENSITIVITY_2025_26_VALID"
STATUSES = {
    "MATCHED_HIGH_CONFIDENCE_REGULAR_SEASON",
    "MATCHED_SCHEDULE_ADJUSTED",
    "MATCHED_NEUTRAL_SITE_REGULAR_SEASON",
}
BANDS = (5, 15, 30, 60)
EASTERN = ZoneInfo("America/New_York")
TEAMS = {
    "ATL":"Atlanta Hawks","BOS":"Boston Celtics","BKN":"Brooklyn Nets",
    "CHA":"Charlotte Hornets","CHI":"Chicago Bulls","CLE":"Cleveland Cavaliers",
    "DAL":"Dallas Mavericks","DEN":"Denver Nuggets","DET":"Detroit Pistons",
    "GSW":"Golden State Warriors","HOU":"Houston Rockets","IND":"Indiana Pacers",
    "LAC":"Los Angeles Clippers","LAL":"Los Angeles Lakers","MEM":"Memphis Grizzlies",
    "MIA":"Miami Heat","MIL":"Milwaukee Bucks","MIN":"Minnesota Timberwolves",
    "NOP":"New Orleans Pelicans","NYK":"New York Knicks","OKC":"Oklahoma City Thunder",
    "ORL":"Orlando Magic","PHI":"Philadelphia 76ers","PHX":"Phoenix Suns",
    "POR":"Portland Trail Blazers","SAC":"Sacramento Kings","SAS":"San Antonio Spurs",
    "TOR":"Toronto Raptors","UTA":"Utah Jazz","WAS":"Washington Wizards",
}


def clean(value: Any) -> str | None:
    text = "" if value is None else str(value).strip()
    return None if text.lower() in {"", "nan", "none", "null"} else text


def num(value: Any) -> float | None:
    text = clean(value)
    if text is None:
        return None
    try:
        out = float(text)
    except ValueError:
        return None
    return out if math.isfinite(out) else None


def truth(value: Any) -> bool:
    return str(value or "").strip().lower() in {"true", "1", "yes", "y"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_utc(value: Any) -> datetime:
    text = clean(value)
    if text is None:
        raise ValueError("missing UTC timestamp")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise ValueError(f"timezone-naive timestamp: {value}")
    return parsed.astimezone(timezone.utc)


def metrics(y: np.ndarray, probability: np.ndarray) -> dict[str, float]:
    p = np.clip(np.asarray(probability, dtype=float), 1e-6, 1 - 1e-6)
    y = np.asarray(y, dtype=int)
    return {
        "rows": int(len(y)),
        "log_loss": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))),
        "brier_score": float(np.mean((p - y) ** 2)),
        "accuracy": float(np.mean((p >= 0.5) == y)),
        "roc_auc": float(roc_auc_score(y, p)),
    }


def bootstrap(y, model, market, resamples: int, seed: int) -> dict[str, Any]:
    y = np.asarray(y, dtype=int)
    model = np.clip(np.asarray(model, dtype=float), 1e-6, 1 - 1e-6)
    market = np.clip(np.asarray(market, dtype=float), 1e-6, 1 - 1e-6)
    rng = np.random.default_rng(seed)
    ll = np.empty(resamples)
    br = np.empty(resamples)
    acc = np.empty(resamples)
    for index in range(resamples):
        sample = rng.integers(0, len(y), size=len(y))
        ys, pm, pk = y[sample], model[sample], market[sample]
        ll[index] = -np.mean(ys*np.log(pm)+(1-ys)*np.log(1-pm)) + np.mean(ys*np.log(pk)+(1-ys)*np.log(1-pk))
        br[index] = np.mean((pm-ys)**2) - np.mean((pk-ys)**2)
        acc[index] = np.mean((pm>=.5)==ys) - np.mean((pk>=.5)==ys)

    def summarize(values, lower):
        return {
            "mean": float(values.mean()),
            "ci95": [float(np.quantile(values, .025)), float(np.quantile(values, .975))],
            "probability_model_better": float(np.mean(values < 0) if lower else np.mean(values > 0)),
        }

    return {
        "resamples": resamples,
        "seed": seed,
        "model_minus_market_log_loss": summarize(ll, True),
        "model_minus_market_brier": summarize(br, True),
        "model_minus_market_accuracy": summarize(acc, False),
    }


def qstats(values) -> dict[str, float]:
    array = np.asarray(list(values), dtype=float)
    return {
        "min": float(array.min()), "p25": float(np.quantile(array, .25)),
        "median": float(np.median(array)), "p75": float(np.quantile(array, .75)),
        "p95": float(np.quantile(array, .95)), "max": float(array.max()),
        "mean": float(array.mean()),
    }


def nearest_moneyline(rows: list[dict[str, str]]) -> dict[str, Any] | None:
    candidates = []
    for row in rows:
        away = num(row.get("team1_moneyline")); home = num(row.get("team2_moneyline"))
        error = num(row.get("t60_absolute_error_minutes")); before = num(row.get("batch_minutes_before_published_tipoff"))
        timestamp = clean(row.get("collector_batch_timestamp_utc_assumed"))
        if not truth(row.get("batch_pre_tip_by_assumed_utc")):
            continue
        if away is None or home is None or away <= 1 or home <= 1 or error is None or before is None or timestamp is None:
            continue
        candidates.append((error, timestamp, away, home, before))
    if not candidates:
        return None
    error, timestamp, away, home, before = min(candidates)
    return {
        "t60_absolute_error_minutes": error,
        "collector_batch_timestamp_utc_assumed": timestamp,
        "minutes_before_tip": before,
        "away_odds_decimal": away,
        "home_odds_decimal": home,
    }


def band_result(rows: list[dict[str, Any]], band: int, resamples: int, seed: int) -> dict[str, Any]:
    subset = [row for row in rows if row["t60_absolute_error_minutes"] <= band]
    y = np.asarray([row["actual_home_win"] for row in subset])
    model = np.asarray([row["model_home_probability"] for row in subset])
    market = np.asarray([row["market_home_probability_no_vig"] for row in subset])
    model_metrics, market_metrics = metrics(y, model), metrics(y, market)
    agree = (model >= .5) == (market >= .5)
    model_correct = (model >= .5) == y
    gap = model - market
    selected_gap = np.where(model >= .5, gap, -gap)
    return {
        "maximum_t60_batch_error_minutes": band,
        "rows": len(subset),
        "coverage_of_joined_valid_moneyline_games": len(subset) / len(rows),
        "timing_error_minutes": qstats(row["t60_absolute_error_minutes"] for row in subset),
        "collector_minutes_before_tip": qstats(row["minutes_before_tip"] for row in subset),
        "overround": qstats(row["overround"] for row in subset),
        "model": model_metrics,
        "market_no_vig": market_metrics,
        "model_minus_market": {
            key: model_metrics[key] - market_metrics[key]
            for key in ("log_loss", "brier_score", "accuracy", "roc_auc")
        },
        "probability_gap": {
            "mean_model_minus_market_home": float(gap.mean()),
            "median_model_minus_market_home": float(np.median(gap)),
            "mean_absolute_home_probability_gap": float(np.abs(gap).mean()),
            "mean_model_selected_side_minus_market_probability": float(selected_gap.mean()),
        },
        "side_agreement": {
            "agreement_rows": int(agree.sum()),
            "agreement_rate": float(agree.mean()),
            "disagreement_rows": int((~agree).sum()),
            "model_accuracy_when_disagreeing": float(model_correct[~agree].mean()) if (~agree).any() else None,
        },
        "paired_game_bootstrap": bootstrap(y, model, market, resamples, seed + band),
    }


def analyze(predictions_path: Path, odds_path: Path, output_dir: Path, resamples: int, seed: int):
    output_dir.mkdir(parents=True, exist_ok=True)
    predictions = read_csv(predictions_path)
    odds = read_csv(odds_path)
    if len(predictions) != 1230:
        raise ValueError(f"expected 1,230 predictions, found {len(predictions)}")

    prediction_by_key = {}
    for row in predictions:
        away = TEAMS.get(clean(row.get("away_team_abbr"))); home = TEAMS.get(clean(row.get("home_team_abbr")))
        date = clean(row.get("game_date")); game_id = clean(row.get("game_id"))
        key = (away, home, date)
        if None in key or game_id is None or key in prediction_by_key:
            raise ValueError(f"invalid prediction identity: {row}")
        prediction_by_key[key] = row

    events = defaultdict(list); excluded_non_regular = 0
    for row in odds:
        if clean(row.get("status")) not in STATUSES:
            excluded_non_regular += 1; continue
        schedule_id = clean(row.get("official_schedule_row_id"))
        if schedule_id is None:
            raise ValueError("regular odds row lacks schedule ID")
        events[schedule_id].append(row)

    joined, exclusions = [], []
    join_methods, status_counts = Counter(), Counter()
    for schedule_id in sorted(events):
        rows = events[schedule_id]; first = rows[0]
        fields = ("team1","team2","official_away_team","official_home_team","scheduled_tipoff_utc","status")
        if any(any(clean(row.get(field)) != clean(first.get(field)) for field in fields) for row in rows[1:]):
            raise ValueError(f"inconsistent event metadata: {schedule_id}")
        date = parse_utc(first["scheduled_tipoff_utc"]).astimezone(EASTERN).date().isoformat()
        official_away = clean(first.get("official_away_team")); official_home = clean(first.get("official_home_team"))
        if official_away and official_home:
            away, home, method = official_away, official_home, "official_ordered_away_home_plus_eastern_date"
        else:
            away, home, method = clean(first.get("team1")), clean(first.get("team2")), "neutral_site_team1_team2_plus_eastern_date"
        prediction = prediction_by_key.get((away, home, date))
        if prediction is None:
            exclusions.append({"official_schedule_row_id":schedule_id,"reason":"NO_EXACT_COMPLETED_GAME_FOR_ORDERED_TEAMS_AND_EASTERN_DATE","away_team":away,"home_team":home,"game_date_et":date})
            continue
        if clean(first.get("team1")) != away or clean(first.get("team2")) != home:
            raise ValueError(f"moneyline orientation mismatch: {schedule_id}")
        selected = nearest_moneyline(rows)
        if selected is None:
            exclusions.append({"official_schedule_row_id":schedule_id,"game_id":prediction["game_id"],"reason":"NO_VALID_TWO_WAY_PRETIP_MONEYLINE","away_team":away,"home_team":home,"game_date_et":date})
            continue
        away_implied = 1/selected["away_odds_decimal"]; home_implied = 1/selected["home_odds_decimal"]
        total = away_implied + home_implied
        joined.append({
            "official_schedule_row_id":schedule_id,"game_id":prediction["game_id"],"game_date":prediction["game_date"],
            "away_team":away,"home_team":home,"away_team_abbr":prediction["away_team_abbr"],"home_team_abbr":prediction["home_team_abbr"],
            "join_method":method,"alignment_status":first["status"],"scheduled_tipoff_utc":first["scheduled_tipoff_utc"],
            **selected,"overround":total-1,"market_away_probability_no_vig":away_implied/total,"market_home_probability_no_vig":home_implied/total,
            "model_away_probability":float(prediction["predicted_away_win_probability"]),"model_home_probability":float(prediction["predicted_home_win_probability"]),
            "actual_home_win":int(prediction["actual_home_win"]),"actual_home_margin":int(prediction["actual_home_margin"]),
        })
        join_methods[method] += 1; status_counts[first["status"]] += 1

    if len(joined) != 1110 or len({row["game_id"] for row in joined}) != 1110:
        raise ValueError(f"expected 1,110 one-to-one joins, found {len(joined)}")
    private_path = output_dir / "private-model-market-time-banded-join-2025-26-v1.csv"
    fields = list(joined[0])
    with private_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        writer.writerows(sorted(joined, key=lambda row:(row["game_date"], row["game_id"])))

    bands = {str(band):band_result(joined, band, resamples, seed) for band in BANDS}
    counts = {key:value["rows"] for key,value in bands.items()}
    if counts != {"5":310,"15":493,"30":612,"60":697}:
        raise ValueError(f"unexpected timing-band counts: {counts}")
    report = {
        "schema_version":"private-model-market-time-banded-sensitivity-2025-26-v1",
        "formal_state":FORMAL_STATE,
        "generated_at_utc":datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "inputs":{"predictions_csv_sha256":sha256(predictions_path),"odds_main_csv_sha256":sha256(odds_path),"prediction_rows":len(predictions),"odds_rows":len(odds),"regular_season_aligned_events":len(events),"source_scope":"PRIVATE_DIAGNOSTIC_ONLY"},
        "join":{"exact_same_game_matches_before_moneyline_filter":1111,"valid_two_way_pretip_moneyline_matches":1110,"unique_prediction_games_joined":1110,"unique_schedule_rows_joined":1110,"join_methods":dict(sorted(join_methods.items())),"alignment_status_counts":dict(sorted(status_counts.items())),"excluded_non_regular_odds_rows":excluded_non_regular,"exclusions":exclusions,"orientation_mismatches":0,"duplicate_join_keys":0},
        "selection_rule":{"market":"two_way_moneyline","batch":"nearest_valid_pretip_collector_batch_to_T60","tie_breaker":"earliest_collector_batch_timestamp_utc_assumed","market_probability":"proportional_no_vig","time_bands_minutes":list(BANDS),"bands_are_nested":True,"bands_predeclared_before_metric_review":True,"profitability_based_band_selection":False},
        "timing_authority":{"collector_timestamp_semantics":"LEAGUE_BATCH_TIMESTAMP_CREATED_BY_COLLECTOR_ASSUMED_UTC","provider_origin_quote_time_verified":False,"quote_level_exact_observed_at_verified":False,"strict_t60_qualified":False},
        "time_bands":bands,
        "cross_band_findings":{"market_log_loss_better_than_model_in_all_bands":all(bands[str(b)]["market_no_vig"]["log_loss"] < bands[str(b)]["model"]["log_loss"] for b in BANDS),"market_brier_better_than_model_in_all_bands":all(bands[str(b)]["market_no_vig"]["brier_score"] < bands[str(b)]["model"]["brier_score"] for b in BANDS),"model_accuracy_better_than_market_in_any_band":any(bands[str(b)]["model"]["accuracy"] > bands[str(b)]["market_no_vig"]["accuracy"] for b in BANDS),"interpretation":"Across every predeclared timing-quality band, the no-vig market probability outperformed the frozen model on Log Loss and Brier. This diagnostic provides no evidence that the frozen model beats the market on this private archive."},
        "private_outputs":{"joined_csv":private_path.name,"joined_csv_sha256":sha256(private_path),"joined_rows":1110,"public_join_rows_committed":0,"public_price_rows_committed":0},
        "execution":{"provider_api_requests":0,"network_requests":0,"model_retraining_executed":False,"model_refit_executed":False,"market_data_used_as_model_feature":False,"bet_selection_executed":False,"ev_calculated":False,"roi_calculated":False,"clv_calculated":False,"drawdown_calculated":False},
        "qualification":{"private_time_banded_sensitivity_valid":True,"formal_point_in_time_market_backtest_allowed":False,"strict_t60_qualified":False,"betting_edge_claim_allowed":False,"formal_stake":0},
        "next_unique_sub_mainline":"REVIEW_MODEL_MARKET_GAP_AND_PRESERVE_MARKET_BACKTEST_LOCK_WHILE_AWAITING_EXACT_PROVIDER_OBSERVED_AT",
    }
    report_path = output_dir / "private-model-market-time-banded-sensitivity-2025-26-report-v1.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


def self_test(output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    y=np.array([0,1,1,0]); model=np.array([.3,.7,.6,.4]); market=np.array([.2,.8,.75,.25])
    checks={"teams":len(TEAMS)==30,"bands":BANDS==(5,15,30,60),"accuracy":metrics(y,model)["accuracy"]==1.0,"market_log_loss":metrics(y,market)["log_loss"]<metrics(y,model)["log_loss"],"bootstrap":bootstrap(y,model,market,100,42)["resamples"]==100}
    if not all(checks.values()): raise AssertionError(checks)
    (output_dir/"self-test.json").write_text(json.dumps({"passed":True,"checks":checks},indent=2)+"\n")


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--predictions",type=Path); parser.add_argument("--odds-main",type=Path); parser.add_argument("--output-dir",type=Path,required=True); parser.add_argument("--bootstrap-resamples",type=int,default=5000); parser.add_argument("--seed",type=int,default=20260724); parser.add_argument("--self-test",action="store_true")
    args=parser.parse_args()
    if args.self_test: self_test(args.output_dir); print("private model/market sensitivity self-test passed"); return 0
    if args.predictions is None or args.odds_main is None: parser.error("--predictions and --odds-main are required")
    analyze(args.predictions,args.odds_main,args.output_dir,args.bootstrap_resamples,args.seed); return 0


if __name__ == "__main__": raise SystemExit(main())
