#!/usr/bin/env python3
"""Normalize closing-only NBA moneyline archives from CSV/XLSX.

This adapter is deliberately separate from the point-in-time odds layer. Archives that
only label a number as "closing" do not provide an auditable observation timestamp,
so they may be used to benchmark forecast quality against the closing market, but not
for CLV, entry-price ROI, or betting-edge claims.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

VERSION = "closing-odds-archive-v1"

TEAM_ALIASES = {
    "atlanta": "ATL", "atlanta hawks": "ATL", "atl": "ATL",
    "boston": "BOS", "boston celtics": "BOS", "bos": "BOS",
    "brooklyn": "BKN", "brooklyn nets": "BKN", "new jersey": "BKN", "new jersey nets": "BKN", "bkn": "BKN", "nj": "BKN",
    "charlotte": "CHA", "charlotte hornets": "CHA", "charlotte bobcats": "CHA", "cha": "CHA",
    "chicago": "CHI", "chicago bulls": "CHI", "chi": "CHI",
    "cleveland": "CLE", "cleveland cavaliers": "CLE", "cle": "CLE",
    "dallas": "DAL", "dallas mavericks": "DAL", "dal": "DAL",
    "denver": "DEN", "denver nuggets": "DEN", "den": "DEN",
    "detroit": "DET", "detroit pistons": "DET", "det": "DET",
    "golden state": "GSW", "golden state warriors": "GSW", "gs": "GSW", "gsw": "GSW",
    "houston": "HOU", "houston rockets": "HOU", "hou": "HOU",
    "indiana": "IND", "indiana pacers": "IND", "ind": "IND",
    "la clippers": "LAC", "l.a. clippers": "LAC", "los angeles clippers": "LAC", "lac": "LAC",
    "la lakers": "LAL", "l.a. lakers": "LAL", "los angeles lakers": "LAL", "lal": "LAL",
    "memphis": "MEM", "memphis grizzlies": "MEM", "mem": "MEM",
    "miami": "MIA", "miami heat": "MIA", "mia": "MIA",
    "milwaukee": "MIL", "milwaukee bucks": "MIL", "mil": "MIL",
    "minnesota": "MIN", "minnesota timberwolves": "MIN", "min": "MIN",
    "new orleans": "NOP", "new orleans pelicans": "NOP", "new orleans hornets": "NOP", "no": "NOP", "nop": "NOP",
    "new york": "NYK", "new york knicks": "NYK", "ny": "NYK", "nyk": "NYK",
    "oklahoma city": "OKC", "oklahoma city thunder": "OKC", "seattle": "OKC", "seattle supersonics": "OKC", "okc": "OKC",
    "orlando": "ORL", "orlando magic": "ORL", "orl": "ORL",
    "philadelphia": "PHI", "philadelphia 76ers": "PHI", "philadelphia sixers": "PHI", "phi": "PHI",
    "phoenix": "PHX", "phoenix suns": "PHX", "pho": "PHX", "phx": "PHX",
    "portland": "POR", "portland trail blazers": "POR", "portland trailblazers": "POR", "por": "POR",
    "sacramento": "SAC", "sacramento kings": "SAC", "sac": "SAC",
    "san antonio": "SAS", "san antonio spurs": "SAS", "sa": "SAS", "sas": "SAS",
    "toronto": "TOR", "toronto raptors": "TOR", "tor": "TOR",
    "utah": "UTA", "utah jazz": "UTA", "uta": "UTA", "uth": "UTA",
    "washington": "WAS", "washington wizards": "WAS", "washington bullets": "WAS", "was": "WAS",
}

COLUMN_ALIASES = {
    "date": ("date", "game_date", "gamedate"),
    "rotation": ("rot", "rotation", "rotation_number", "rotationnumber"),
    "vh": ("vh", "v_h", "visitor_home", "location", "site"),
    "team": ("team", "team_name", "teamname"),
    "moneyline": ("ml", "moneyline", "money_line", "close_ml", "closing_moneyline"),
    "home_team": ("home_team", "hometeam", "home"),
    "away_team": ("away_team", "awayteam", "visitor_team", "visitorteam", "away"),
    "home_ml": ("home_ml", "home_moneyline", "home_money_line", "ml_home"),
    "away_ml": ("away_ml", "away_moneyline", "away_money_line", "ml_away", "visitor_ml"),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def norm_col(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def resolve_columns(frame: pd.DataFrame) -> dict[str, str]:
    normalized = {norm_col(col): str(col) for col in frame.columns}
    resolved: dict[str, str] = {}
    for key, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if norm_col(alias) in normalized:
                resolved[key] = normalized[norm_col(alias)]
                break
    return resolved


def team_abbr(value: Any) -> str:
    raw = str(value or "").strip()
    key = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9. ]+", " ", raw.lower())).strip().replace(".", "")
    aliases = {k.replace(".", ""): v for k, v in TEAM_ALIASES.items()}
    if key in aliases:
        return aliases[key]
    compact = re.sub(r"[^A-Za-z]", "", raw).upper()
    if len(compact) == 3 and compact in set(TEAM_ALIASES.values()):
        return compact
    raise ValueError(f"unknown NBA team: {value!r}")


def parse_game_date(value: Any, season_start_year: int | None) -> str:
    text = str(value).strip()
    if not text or text.lower() == "nan":
        raise ValueError("blank game date")
    if re.fullmatch(r"\d{4}(?:\.0)?", text):
        if season_start_year is None:
            raise ValueError(f"MMDD date {text!r} requires --season-start-year")
        mmdd = str(int(float(text))).zfill(4)
        month, day = int(mmdd[:2]), int(mmdd[2:])
        year = season_start_year if month >= 7 else season_start_year + 1
        return datetime(year, month, day).date().isoformat()
    if re.fullmatch(r"\d{8}(?:\.0)?", text):
        return datetime.strptime(str(int(float(text))), "%Y%m%d").date().isoformat()
    parsed = pd.to_datetime(value, errors="raise")
    return parsed.date().isoformat()


def as_american(value: Any) -> int:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        raise ValueError("blank moneyline")
    text = str(value).strip().replace(",", "")
    if text.lower() in {"pk", "pick", "pickem", "pick'em"}:
        return 100
    if text.lower() in {"", "nan"}:
        raise ValueError("blank moneyline")
    number = int(round(float(text)))
    if number == 0 or abs(number) < 100 or abs(number) > 100000:
        raise ValueError(f"invalid American moneyline: {value!r}")
    return number


def american_to_decimal(value: int) -> float:
    return 1.0 + (value / 100.0 if value > 0 else 100.0 / abs(value))


def load_frame(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    raise ValueError("input must be CSV, XLSX, or XLS")


def wide_rows(frame: pd.DataFrame, cols: dict[str, str], season_start_year: int | None) -> tuple[list[dict[str, Any]], dict[str, int]]:
    required = {"date", "home_team", "away_team", "home_ml", "away_ml"}
    if not required.issubset(cols):
        return [], {}
    rows: list[dict[str, Any]] = []
    qa = {"unknown_team_rows": 0, "invalid_moneyline_rows": 0, "unpaired_rows": 0}
    for _, item in frame.iterrows():
        try:
            rows.append({
                "game_date": parse_game_date(item[cols["date"]], season_start_year),
                "home_team_abbr": team_abbr(item[cols["home_team"]]),
                "away_team_abbr": team_abbr(item[cols["away_team"]]),
                "home_moneyline_american": as_american(item[cols["home_ml"]]),
                "away_moneyline_american": as_american(item[cols["away_ml"]]),
            })
        except ValueError as exc:
            if "team" in str(exc):
                qa["unknown_team_rows"] += 1
            else:
                qa["invalid_moneyline_rows"] += 1
    return rows, qa


def long_rows(frame: pd.DataFrame, cols: dict[str, str], season_start_year: int | None) -> tuple[list[dict[str, Any]], dict[str, int]]:
    required = {"date", "vh", "team", "moneyline"}
    if not required.issubset(cols):
        missing = sorted(required - set(cols))
        raise ValueError(f"could not detect wide schema; long schema missing columns: {missing}")
    parsed: list[dict[str, Any]] = []
    qa = {"unknown_team_rows": 0, "invalid_moneyline_rows": 0, "unpaired_rows": 0}
    for source_order, (_, item) in enumerate(frame.iterrows()):
        try:
            parsed.append({
                "source_order": source_order,
                "game_date": parse_game_date(item[cols["date"]], season_start_year),
                "vh": str(item[cols["vh"]]).strip().upper()[:1],
                "team": team_abbr(item[cols["team"]]),
                "ml": as_american(item[cols["moneyline"]]),
                "rotation": str(item[cols["rotation"]]).strip() if "rotation" in cols else "",
            })
        except ValueError as exc:
            if "team" in str(exc):
                qa["unknown_team_rows"] += 1
            else:
                qa["invalid_moneyline_rows"] += 1
    rows: list[dict[str, Any]] = []
    by_date: dict[str, list[dict[str, Any]]] = {}
    for item in parsed:
        by_date.setdefault(item["game_date"], []).append(item)
    for date, items in sorted(by_date.items()):
        items.sort(key=lambda row: row["source_order"])
        for index in range(0, len(items), 2):
            pair = items[index:index + 2]
            if len(pair) != 2 or {row["vh"] for row in pair} != {"V", "H"}:
                qa["unpaired_rows"] += len(pair)
                continue
            home = next(row for row in pair if row["vh"] == "H")
            away = next(row for row in pair if row["vh"] == "V")
            rows.append({
                "game_date": date,
                "home_team_abbr": home["team"],
                "away_team_abbr": away["team"],
                "home_moneyline_american": home["ml"],
                "away_moneyline_american": away["ml"],
                "home_rotation": home["rotation"],
                "away_rotation": away["rotation"],
            })
    return rows, qa


def normalize(input_path: Path, output_dir: Path, source_id: str, season_start_year: int | None) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    frame = load_frame(input_path)
    cols = resolve_columns(frame)
    rows, qa = wide_rows(frame, cols, season_start_year)
    schema = "wide_game_rows"
    if not rows and not {"date", "home_team", "away_team", "home_ml", "away_ml"}.issubset(cols):
        rows, qa = long_rows(frame, cols, season_start_year)
        schema = "sbr_two_row_game"

    file_hash = hashlib.sha256(input_path.read_bytes()).hexdigest()
    seen: set[tuple[str, str, str]] = set()
    output: list[dict[str, Any]] = []
    duplicate_games = 0
    invalid_overround = 0
    for row in rows:
        key = (row["game_date"], row["home_team_abbr"], row["away_team_abbr"])
        if key in seen:
            duplicate_games += 1
            continue
        seen.add(key)
        home_decimal = american_to_decimal(row["home_moneyline_american"])
        away_decimal = american_to_decimal(row["away_moneyline_american"])
        home_implied = 1.0 / home_decimal
        away_implied = 1.0 / away_decimal
        total = home_implied + away_implied
        overround = total - 1.0
        flags: list[str] = ["closing_timestamp_unavailable"]
        if not -0.05 <= overround <= 0.30:
            flags.append("overround_outside_expected_range")
            invalid_overround += 1
        output.append({
            "game_date": row["game_date"],
            "home_team_abbr": row["home_team_abbr"],
            "away_team_abbr": row["away_team_abbr"],
            "home_moneyline_american": row["home_moneyline_american"],
            "away_moneyline_american": row["away_moneyline_american"],
            "home_price_decimal": round(home_decimal, 8),
            "away_price_decimal": round(away_decimal, 8),
            "home_implied_probability": round(home_implied, 10),
            "away_implied_probability": round(away_implied, 10),
            "overround": round(overround, 10),
            "fair_home_probability": round(home_implied / total, 10),
            "fair_away_probability": round(away_implied / total, 10),
            "snapshot_label": "Closing",
            "timestamp_quality": "closing_label_only",
            "source_id": source_id,
            "source_file_sha256": file_hash,
            "adapter_version": VERSION,
            "quality_flags": ",".join(flags),
        })
    output.sort(key=lambda row: (row["game_date"], row["home_team_abbr"], row["away_team_abbr"]))
    pd.DataFrame(output).to_csv(output_dir / "closing-moneyline-normalized.csv", index=False)
    seasons = sorted({int(row["game_date"][:4]) if int(row["game_date"][5:7]) >= 7 else int(row["game_date"][:4]) - 1 for row in output})
    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "source": {
            "source_id": source_id,
            "input_file": input_path.name,
            "input_sha256": file_hash,
            "detected_schema": schema,
            "detected_columns": cols,
            "season_start_year_argument": season_start_year,
        },
        "coverage": {
            "input_rows": int(len(frame)),
            "normalized_games": len(output),
            "season_start_years": seasons,
            "season_count": len(seasons),
        },
        "quality": {
            **qa,
            "duplicate_games_excluded": duplicate_games,
            "overround_outside_expected_range": invalid_overround,
            "exact_observation_timestamps_available": False,
            "same_bookmaker_open_to_close_history_available": False,
        },
        "decision": {
            "ready_for_closing_market_benchmark": len(output) >= 500 and len(seasons) >= 3,
            "ready_for_point_in_time_odds_layer": False,
            "ready_for_clv_analysis": False,
            "ready_for_entry_price_roi_backtest": False,
            "ready_for_betting_edge_claim": False,
        },
    }
    (output_dir / "closing-moneyline-import-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def self_test(output_dir: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="nbavl-closing-import-") as temp_name:
        source = Path(temp_name) / "nbaodds2023.csv"
        pd.DataFrame([
            {"Date": 1019, "Rot": 501, "VH": "V", "Team": "Brooklyn", "ML": 190},
            {"Date": 1019, "Rot": 502, "VH": "H", "Team": "Milwaukee", "ML": -220},
            {"Date": 1020, "Rot": 503, "VH": "V", "Team": "Golden State", "ML": -105},
            {"Date": 1020, "Rot": 504, "VH": "H", "Team": "LA Lakers", "ML": -115},
        ]).to_csv(source, index=False)
        report = normalize(source, output_dir, "self_test_sbr", 2021)
        assert report["coverage"]["normalized_games"] == 2, report
        assert report["source"]["detected_schema"] == "sbr_two_row_game", report
        assert report["decision"]["ready_for_clv_analysis"] is False
        (output_dir / "self-test.json").write_text('{"passed":true}\n', encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-id", default="manual_closing_archive")
    parser.add_argument("--season-start-year", type=int)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("closing odds archive importer self-test passed")
        return
    if not args.input:
        parser.error("--input is required unless --self-test is used")
    report = normalize(args.input, args.output_dir, args.source_id, args.season_start_year)
    print(json.dumps(report["decision"], indent=2))


if __name__ == "__main__":
    main()
