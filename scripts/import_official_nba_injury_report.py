#!/usr/bin/env python3
"""Download, parse and validate one official NBA injury report PDF.

Raw PDF bytes and normalized player rows are temporary by default. Aggregate provenance and
QA reports are retained for auditability.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import re
import tempfile
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import httpx
import pandas as pd

from validate_injury_lineup_snapshots import validate

VERSION = "official-nba-injury-report-pdf-pilot-v1.2"
ET = ZoneInfo("America/New_York")
TEAM_NAME_TO_ABBR = {
    "Atlanta Hawks": "ATL", "Brooklyn Nets": "BKN", "Boston Celtics": "BOS",
    "Charlotte Hornets": "CHA", "Chicago Bulls": "CHI", "Cleveland Cavaliers": "CLE",
    "Dallas Mavericks": "DAL", "Denver Nuggets": "DEN", "Detroit Pistons": "DET",
    "Golden State Warriors": "GSW", "Houston Rockets": "HOU", "Indiana Pacers": "IND",
    "LA Clippers": "LAC", "Los Angeles Clippers": "LAC", "Los Angeles Lakers": "LAL",
    "Memphis Grizzlies": "MEM", "Miami Heat": "MIA", "Milwaukee Bucks": "MIL",
    "Minnesota Timberwolves": "MIN", "New Orleans Pelicans": "NOP", "New York Knicks": "NYK",
    "Oklahoma City Thunder": "OKC", "Orlando Magic": "ORL", "Philadelphia 76ers": "PHI",
    "Phoenix Suns": "PHX", "Portland Trail Blazers": "POR", "Sacramento Kings": "SAC",
    "San Antonio Spurs": "SAS", "Toronto Raptors": "TOR", "Utah Jazz": "UTA",
    "Washington Wizards": "WAS",
}
EXPECTED_COLUMNS = {
    "game_date", "game_time", "matchup", "team", "player_name", "current_status", "reason"
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_column(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def parse_report_time(value: str) -> datetime:
    text = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=ET)
    return parsed.astimezone(ET)


def report_url(report_time: datetime) -> str:
    local = report_time.astimezone(ET)
    # Official publication links encode the report hour and AM/PM only. For example, the
    # report published at 08:30 ET is stored as Injury-Report_YYYY-MM-DD_08AM.pdf.
    filename = local.strftime("Injury-Report_%Y-%m-%d_%I%p.pdf")
    return f"https://ak-static.cms.nba.com/referee/injury/{filename}"


def download_pdf(url: str, destination: Path) -> tuple[str, int]:
    # The official CDN currently rejects Python requests' default transport for these public
    # PDF objects. A standard httpx client works without authentication, cookies or bypasses.
    with httpx.Client(follow_redirects=True, timeout=45.0) as client:
        response = client.get(url=url)
    response.raise_for_status()
    payload = response.content
    if not payload.startswith(b"%PDF"):
        raise ValueError(
            f"official report response is not a PDF: content-type={response.headers.get('content-type')}"
        )
    destination.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest(), len(payload)


def parse_pdf(path: Path) -> pd.DataFrame:
    try:
        from nba_injury_report_pdf_to_df import pdf_to_df
    except ImportError as exc:
        raise RuntimeError("nba-injury-report-pdf-to-df==0.1.7 is required") from exc
    frame = pdf_to_df(str(path))
    if not isinstance(frame, pd.DataFrame):
        frame = pd.DataFrame(frame)
    frame = frame.rename(columns={column: normalize_column(column) for column in frame.columns})
    missing = sorted(EXPECTED_COLUMNS - set(frame.columns))
    if missing:
        raise ValueError(f"official PDF parser missing columns: {missing}; got={list(frame.columns)}")
    for column in ("game_date", "game_time", "matchup", "team"):
        frame[column] = frame[column].replace("", pd.NA).ffill()
    frame = frame.dropna(subset=["game_date", "game_time", "matchup", "team", "player_name"])
    return frame.reset_index(drop=True)


def parse_matchup(value: Any) -> tuple[str, str]:
    text = re.sub(r"\s+", "", str(value).upper())
    match = re.fullmatch(r"([A-Z]{3})@([A-Z]{3})", text)
    if not match:
        raise ValueError(f"unsupported matchup: {value!r}")
    return match.group(1), match.group(2)


def parse_game_time(game_date: Any, game_time: Any) -> datetime:
    day = datetime.strptime(str(game_date).strip(), "%m/%d/%Y").date()
    match = re.search(r"(\d{1,2}):(\d{2})", str(game_time))
    if not match:
        raise ValueError(f"unsupported game time: {game_time!r}")
    hour, minute = int(match.group(1)), int(match.group(2))
    # NBA reports use ET and omit AM/PM. Scheduled games are noon-or-later ET.
    if 1 <= hour <= 11:
        hour += 12
    if hour > 23 or minute > 59:
        raise ValueError(f"invalid game time: {game_time!r}")
    return datetime.combine(day, time(hour=hour, minute=minute), tzinfo=ET)


def source_rows(
    frame: pd.DataFrame,
    report_time: datetime,
    source_url: str,
    source_hash: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    rows, errors = [], []
    observed_at = iso_utc(report_time)
    for index, item in frame.iterrows():
        try:
            away, home = parse_matchup(item["matchup"])
            team_name = str(item["team"]).strip()
            team = TEAM_NAME_TO_ABBR[team_name]
            if team not in {away, home}:
                raise ValueError(f"team {team} does not belong to matchup {away}@{home}")
            opponent = home if team == away else away
            commence = parse_game_time(item["game_date"], item["game_time"])
            if report_time >= commence:
                raise ValueError("report timestamp is not before scheduled tip-off")
            game_id = f"official:{commence.date().isoformat()}:{away}@{home}"
            rows.append({
                "record_type": "INJURY_STATUS",
                "game_id": game_id,
                "commence_time": iso_utc(commence),
                "team_abbr": team,
                "opponent_abbr": opponent,
                "is_home": int(team == home),
                "player_id": "",
                "player_name": str(item["player_name"]).strip(),
                "source_status_raw": str(item["current_status"]).strip(),
                "source_reason_raw": str(item["reason"]).strip(),
                # For archived official reports, publication time is the earliest verifiable
                # public availability time. Retrieval time is stored separately below.
                "observed_at": observed_at,
                "source_report_time": observed_at,
                "source_provider": "NBA Official Injury Report",
                "source_url": source_url,
                "source_file_sha256": source_hash,
            })
        except Exception as exc:
            errors.append(f"parsed row {index + 2}: {type(exc).__name__}: {exc}")
    return rows, errors


def run(report_time_text: str, output_dir: Path, retain_normalized: bool = False) -> dict[str, Any]:
    report_time = parse_report_time(report_time_text)
    url = report_url(report_time)
    retrieved_at = utc_now()
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="nbavl-official-injury-") as temp_name:
        pdf_path = Path(temp_name) / "official-injury-report.pdf"
        source_hash, source_bytes = download_pdf(url, pdf_path)
        parsed = parse_pdf(pdf_path)
        raw_rows, conversion_errors = source_rows(parsed, report_time, url, source_hash)
        validation_dir = output_dir / "validation"
        validation = validate(raw_rows, validation_dir)
        normalized_path = validation_dir / "injury-lineup-snapshots-normalized.csv"
        if not retain_normalized and normalized_path.exists():
            normalized_path.unlink()

    status_counts = parsed["current_status"].astype(str).str.strip().value_counts().sort_index().to_dict()
    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "source": {
            "provider": "NBA Official Injury Report",
            "report_url": url,
            "report_time": iso_utc(report_time),
            "retrieved_at": retrieved_at,
            "source_file_sha256": source_hash,
            "source_size_bytes": source_bytes,
            "download_client": "httpx",
            "parser_package": "nba-injury-report-pdf-to-df",
            "parser_version": importlib.metadata.version("nba-injury-report-pdf-to-df"),
        },
        "coverage": {
            "pdf_parsed_rows": int(len(parsed)),
            "contract_input_rows": int(len(raw_rows)),
            "validated_rows": int(validation["normalized_rows"]),
            "games": int(validation["coverage"]["games"]),
            "teams": int(validation["coverage"]["teams"]),
            "players": int(validation["coverage"]["players"]),
            "raw_status_counts": status_counts,
        },
        "quality": {
            "conversion_errors": len(conversion_errors),
            "conversion_error_examples": conversion_errors[:50],
            "contract_errors": int(validation["quality"]["errors"]),
            "contract_warnings": int(validation["quality"]["warnings"]),
            "point_in_time_rule_passed": bool(validation["quality"]["point_in_time_rule_passed"]),
            "raw_pdf_deleted": True,
            "normalized_player_rows_retained": bool(retain_normalized),
        },
        "decision": {
            "ready_for_manual_official_pdf_pilot": bool(
                raw_rows
                and not conversion_errors
                and validation["decision"]["ready_for_point_in_time_feature_build"]
            ),
            "ready_for_automated_backfill": False,
            "ready_for_model_training": False,
            "ready_for_betting_edge_claim": False,
            "reason": "One-report parser pilot only; schedule/player mapping and multi-season coverage are not validated.",
        },
        "guardrails": {
            "official_publication_time_used_as_historical_observed_at": True,
            "actual_retrieval_time_stored_separately": True,
            "raw_pdf_committed_or_uploaded": False,
            "player_level_rows_uploaded_by_default": False,
            "third_party_injury_client_runtime_dependency": False,
        },
    }
    (output_dir / "official-injury-report-import-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def self_test(output_dir: Path) -> None:
    frame = pd.DataFrame([
        {
            "Game Date": "12/18/2023", "Game Time": "09:00 (ET)", "Matchup": "DAL@DEN",
            "Team": "Dallas Mavericks", "Player Name": "Lively II, Dereck",
            "Current Status": "Out", "Reason": "Injury/Illness - Left Ankle; Sprain",
        },
        {
            "Game Date": "12/18/2023", "Game Time": "09:00 (ET)", "Matchup": "DAL@DEN",
            "Team": "Denver Nuggets", "Player Name": "Gordon, Aaron",
            "Current Status": "Probable", "Reason": "Injury/Illness - Right Heel; Strain",
        },
    ]).rename(columns=lambda column: normalize_column(column))
    report_time = parse_report_time("2023-12-18T08:30:00-05:00")
    assert report_url(report_time).endswith("Injury-Report_2023-12-18_08AM.pdf")
    rows, errors = source_rows(frame, report_time, report_url(report_time), "a" * 64)
    assert not errors, errors
    validation = validate(rows, output_dir)
    assert validation["normalized_rows"] == 2, validation
    assert validation["decision"]["ready_for_point_in_time_feature_build"] is True, validation
    (output_dir / "official-import-self-test.json").write_text('{"passed":true}\n', encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-time", help="Official report timestamp; naive values are interpreted in America/New_York")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--retain-normalized", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("Official NBA injury report importer self-test passed")
        return
    if not args.report_time:
        parser.error("--report-time is required unless --self-test is used")
    report = run(args.report_time, args.output_dir, args.retain_normalized)
    print(json.dumps(report["decision"], indent=2))
    if not report["decision"]["ready_for_manual_official_pdf_pilot"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
