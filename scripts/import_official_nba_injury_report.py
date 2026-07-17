#!/usr/bin/env python3
"""Download, parse and validate one official NBA injury report PDF.

Raw PDF bytes and normalized player rows are temporary by default. Aggregate provenance and
QA reports are retained for auditability.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import httpx
import pandas as pd
import pymupdf

from validate_injury_lineup_snapshots import validate

VERSION = "official-nba-injury-report-pdf-pilot-v1.5"
LAYOUT_VERSION = "official-landscape-seven-column-2023-v1"
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
ALLOWED_STATUSES = {"Available", "Probable", "Questionable", "Doubtful", "Out"}
OUTPUT_COLUMNS = [
    "game_date", "game_time", "matchup", "team", "player_name", "current_status", "reason"
]
COLUMN_BOUNDS = (
    ("game_date", 0.0, 100.0),
    ("game_time", 100.0, 190.0),
    ("matchup", 190.0, 255.0),
    ("team", 255.0, 415.0),
    ("player_name", 415.0, 575.0),
    ("current_status", 575.0, 655.0),
    ("reason", 655.0, 900.0),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def parse_report_time(value: str) -> datetime:
    text = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=ET)
    return parsed.astimezone(ET)


def report_url(report_time: datetime) -> str:
    local = report_time.astimezone(ET)
    filename = local.strftime("Injury-Report_%Y-%m-%d_%I%p.pdf")
    return f"https://ak-static.cms.nba.com/referee/injury/{filename}"


def download_pdf(url: str, destination: Path) -> tuple[str, int]:
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


def word_column(x0: float) -> str | None:
    for name, left, right in COLUMN_BOUNDS:
        if left <= x0 < right:
            return name
    return None


def join_words(words: list[dict[str, Any]]) -> str:
    ordered = sorted(words, key=lambda item: (item["center_y"], item["x0"]))
    return normalize_space(" ".join(item["text"] for item in ordered))


def group_physical_lines(words: list[dict[str, Any]], tolerance: float = 2.5) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    for word in sorted(words, key=lambda item: (item["center_y"], item["x0"])):
        target = None
        for line in reversed(lines[-4:]):
            if abs(line["center_y"] - word["center_y"]) <= tolerance:
                target = line
                break
        if target is None:
            target = {"center_y": word["center_y"], "words": []}
            lines.append(target)
        target["words"].append(word)
        target["center_y"] = sum(item["center_y"] for item in target["words"]) / len(target["words"])
    for line in lines:
        line["words"].sort(key=lambda item: item["x0"])
        cells = {name: [] for name, _, _ in COLUMN_BOUNDS}
        for word in line["words"]:
            column = word_column(word["x0"])
            if column:
                cells[column].append(word)
        line["cells"] = {name: join_words(items) for name, items in cells.items()}
    return lines


def page_words(page: pymupdf.Page) -> list[dict[str, Any]]:
    words = []
    for x0, y0, x1, y1, text, block, line, word in page.get_text("words", sort=True):
        center_y = (float(y0) + float(y1)) / 2.0
        if center_y < 40.0 or center_y > 530.0:
            continue
        words.append({
            "x0": float(x0), "y0": float(y0), "x1": float(x1), "y1": float(y1),
            "center_y": center_y, "text": str(text),
            "block": int(block), "line": int(line), "word": int(word),
        })
    return words


def is_header_line(line: dict[str, Any]) -> bool:
    if line["center_y"] >= 125.0:
        return False
    combined = " ".join(item["text"] for item in line["words"])
    return "Game Date" in combined and "Player Name" in combined and "Current Status" in combined


def valid_context_value(field: str, value: str) -> bool:
    if field == "game_date":
        return bool(re.fullmatch(r"\d{2}/\d{2}/\d{4}", value))
    if field == "game_time":
        return bool(re.fullmatch(r"\d{2}:\d{2}(?: \(ET\))?", value))
    if field == "matchup":
        return bool(re.fullmatch(r"[A-Z]{3}@[A-Z]{3}", value))
    if field == "team":
        return value in TEAM_NAME_TO_ABBR
    return False


def has_context(cells: dict[str, str]) -> bool:
    return any(
        valid_context_value(field, normalize_space(cells.get(field)))
        for field in ("game_date", "game_time", "matchup", "team")
    )


def update_context(state: dict[str, str], cells: dict[str, str]) -> None:
    for field in ("game_date", "game_time", "matchup", "team"):
        value = normalize_space(cells.get(field))
        if value and valid_context_value(field, value):
            state[field] = value


def parse_pdf(path: Path) -> tuple[pd.DataFrame, dict[str, Any]]:
    document = pymupdf.open(path)
    state = {"game_date": "", "game_time": "", "matchup": "", "team": ""}
    records: list[dict[str, str]] = []
    parse_errors: list[str] = []
    submission_rows = 0
    page_summaries = []

    for page_index, page in enumerate(document):
        all_words = page_words(page)
        all_lines = group_physical_lines(all_words)
        lines = [line for line in all_lines if not is_header_line(line)]
        body_words = [word for line in lines for word in line["words"]]
        context_events = []
        anchors = []
        for line in lines:
            cells = line["cells"]
            if has_context(cells):
                context_events.append(line)
            status = normalize_space(cells["current_status"])
            if status in ALLOWED_STATUSES:
                anchors.append(line["center_y"])
            if "NOT YET SUBMITTED" in normalize_space(cells["reason"]).upper():
                submission_rows += 1

        anchors = sorted({round(value, 3) for value in anchors})
        context_events.sort(key=lambda item: item["center_y"])
        event_index = 0
        page_records = 0

        for anchor_index, anchor in enumerate(anchors):
            while event_index < len(context_events) and context_events[event_index]["center_y"] <= anchor + 2.5:
                update_context(state, context_events[event_index]["cells"])
                event_index += 1

            lower = 40.0 if anchor_index == 0 else (anchors[anchor_index - 1] + anchor) / 2.0
            upper = 530.0 if anchor_index + 1 == len(anchors) else (anchor + anchors[anchor_index + 1]) / 2.0
            band = [word for word in body_words if lower <= word["center_y"] < upper]
            player_words = [
                word for word in band
                if word_column(word["x0"]) == "player_name" and abs(word["center_y"] - anchor) <= 3.5
            ]
            status_words = [
                word for word in band
                if word_column(word["x0"]) == "current_status" and abs(word["center_y"] - anchor) <= 3.5
            ]
            reason_words = [word for word in band if word_column(word["x0"]) == "reason"]
            player = join_words(player_words)
            status = join_words(status_words)
            reason = join_words(reason_words)

            row_errors = []
            if not player:
                row_errors.append("missing player name")
            if status not in ALLOWED_STATUSES:
                row_errors.append(f"invalid status {status!r}")
            for field in ("game_date", "game_time", "matchup", "team"):
                if not state[field]:
                    row_errors.append(f"missing carried {field}")
            if row_errors:
                parse_errors.append(
                    f"page {page_index + 1} anchor {anchor:.2f}: " + "; ".join(row_errors)
                )
                continue

            records.append({
                "game_date": state["game_date"],
                "game_time": state["game_time"],
                "matchup": state["matchup"],
                "team": state["team"],
                "player_name": player,
                "current_status": status,
                "reason": reason,
            })
            page_records += 1

        while event_index < len(context_events):
            update_context(state, context_events[event_index]["cells"])
            event_index += 1

        page_summaries.append({
            "page": page_index + 1,
            "physical_lines": len(lines),
            "status_anchors": len(anchors),
            "parsed_player_rows": page_records,
        })

    frame = pd.DataFrame(records, columns=OUTPUT_COLUMNS)
    qa = {
        "layout_version": LAYOUT_VERSION,
        "page_count": len(document),
        "parsed_player_rows": int(len(frame)),
        "not_yet_submitted_team_rows": int(submission_rows),
        "parse_errors": len(parse_errors),
        "parse_error_examples": parse_errors[:50],
        "page_summaries": page_summaries,
    }
    if frame.empty:
        raise ValueError(f"native PDF parser produced no player rows: {qa}")
    return frame, qa


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
            team_name = normalize_space(item["team"])
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
                "player_name": normalize_space(item["player_name"]),
                "source_status_raw": normalize_space(item["current_status"]),
                "source_reason_raw": normalize_space(item["reason"]),
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
        parsed, parser_qa = parse_pdf(pdf_path)
        raw_rows, conversion_errors = source_rows(parsed, report_time, url, source_hash)
        validation_dir = output_dir / "validation"
        validation = validate(raw_rows, validation_dir)
        normalized_path = validation_dir / "injury-lineup-snapshots-normalized.csv"
        if not retain_normalized and normalized_path.exists():
            normalized_path.unlink()

    status_counts = parsed["current_status"].astype(str).str.strip().value_counts().sort_index().to_dict()
    all_conversion_errors = parser_qa["parse_error_examples"] + conversion_errors
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
            "parser_engine": "PyMuPDF native word coordinates",
            "parser_version": pymupdf.VersionBind,
            "layout_version": LAYOUT_VERSION,
        },
        "coverage": {
            "pdf_parsed_rows": int(len(parsed)),
            "contract_input_rows": int(len(raw_rows)),
            "validated_rows": int(validation["normalized_rows"]),
            "games": int(validation["coverage"]["games"]),
            "teams": int(validation["coverage"]["teams"]),
            "players": int(validation["coverage"]["players"]),
            "not_yet_submitted_team_rows": int(parser_qa["not_yet_submitted_team_rows"]),
            "raw_status_counts": status_counts,
        },
        "quality": {
            "conversion_errors": len(all_conversion_errors),
            "conversion_error_examples": all_conversion_errors[:50],
            "contract_errors": int(validation["quality"]["errors"]),
            "contract_warnings": int(validation["quality"]["warnings"]),
            "point_in_time_rule_passed": bool(validation["quality"]["point_in_time_rule_passed"]),
            "raw_pdf_deleted": True,
            "normalized_player_rows_retained": bool(retain_normalized),
            "parser_qa": parser_qa,
        },
        "decision": {
            "ready_for_manual_official_pdf_pilot": bool(
                raw_rows
                and not all_conversion_errors
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
            "third_party_pdf_parser_runtime_dependency": False,
        },
    }
    (output_dir / "official-injury-report-import-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def self_test(output_dir: Path) -> None:
    report_time = parse_report_time("2023-12-18T08:30:00-05:00")
    assert report_url(report_time).endswith("Injury-Report_2023-12-18_08AM.pdf")
    synthetic = pd.DataFrame([
        {
            "game_date": "12/18/2023", "game_time": "09:00 (ET)", "matchup": "DAL@DEN",
            "team": "Dallas Mavericks", "player_name": "Lively II, Dereck",
            "current_status": "Out", "reason": "Injury/Illness - Left Ankle; Sprain",
        },
        {
            "game_date": "12/18/2023", "game_time": "09:00 (ET)", "matchup": "DAL@DEN",
            "team": "Denver Nuggets", "player_name": "Gordon, Aaron",
            "current_status": "Probable", "reason": "Injury/Illness - Right Heel; Strain",
        },
    ])
    rows, errors = source_rows(synthetic, report_time, report_url(report_time), "a" * 64)
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
