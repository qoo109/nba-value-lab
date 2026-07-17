#!/usr/bin/env python3
"""Validate and normalize point-in-time NBA injury and lineup snapshots."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pandas as pd

VERSION = "injury-lineup-snapshot-v1"
TEAMS = {
    "ATL","BKN","BOS","CHA","CHI","CLE","DAL","DEN","DET","GSW","HOU","IND","LAC","LAL",
    "MEM","MIA","MIL","MIN","NOP","NYK","OKC","ORL","PHI","PHX","POR","SAC","SAS","TOR","UTA","WAS",
}
RECORD_TYPES = {"INJURY_STATUS", "LINEUP_STATUS"}
STATUS_MAP = {
    "available":"AVAILABLE", "active":"AVAILABLE", "probable":"PROBABLE",
    "questionable":"QUESTIONABLE", "doubtful":"DOUBTFUL", "out":"OUT",
    "inactive":"INACTIVE", "suspended":"SUSPENDED", "not with team":"OUT",
    "not_with_team":"OUT", "unknown":"UNKNOWN", "":"UNKNOWN",
}
LINEUP_MAP = {
    "confirmed starter":"CONFIRMED_STARTER", "confirmed_starter":"CONFIRMED_STARTER",
    "starter":"CONFIRMED_STARTER", "projected starter":"PROJECTED_STARTER",
    "projected_starter":"PROJECTED_STARTER", "rotation":"ROTATION", "bench":"BENCH",
    "inactive":"INACTIVE", "unknown":"UNKNOWN", "":"UNKNOWN",
}
REASON_PATTERNS = [
    ("REST", re.compile(r"\b(rest|load management)\b", re.I)),
    ("ILLNESS", re.compile(r"\b(illness|sick|flu|covid)\b", re.I)),
    ("PERSONAL", re.compile(r"\b(personal|family|bereavement)\b", re.I)),
    ("SUSPENSION", re.compile(r"\b(suspend|disciplin)\b", re.I)),
    ("G_LEAGUE", re.compile(r"\b(g league|assignment|two-way)\b", re.I)),
    ("INJURY", re.compile(r"\b(knee|ankle|foot|leg|hamstring|groin|hip|back|shoulder|wrist|hand|finger|elbow|neck|calf|achilles|concussion|injury|surgery|fracture|sprain|strain|soreness|contusion)\b", re.I)),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def norm_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", norm(value).lower()).strip("_")


def parse_timestamp(value: Any, field: str) -> datetime:
    text = norm(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{field} must be ISO-8601: {value!r}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone: {value!r}")
    return parsed.astimezone(timezone.utc)


def iso_utc(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def status_from_raw(value: Any) -> str:
    return STATUS_MAP.get(norm(value).lower().replace("-", " "), "UNKNOWN")


def lineup_from_raw(value: Any) -> str:
    return LINEUP_MAP.get(norm(value).lower().replace("-", " "), "UNKNOWN")


def reason_category(value: Any) -> str:
    text = norm(value)
    for category, pattern in REASON_PATTERNS:
        if pattern.search(text):
            return category
    return "OTHER" if text else "UNSPECIFIED"


def valid_https(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def player_key(row: dict[str, Any]) -> str:
    player_id = norm(row.get("player_id"))
    return f"id:{player_id}" if player_id else f"name:{norm_key(row.get('player_name'))}"


def stable_id(*parts: Any) -> str:
    payload = "\x1f".join(norm(part) for part in parts)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def read_input(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path, dtype=str, keep_default_na=False).to_dict(orient="records")
    if suffix in {".jsonl", ".ndjson"}:
        rows = []
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON on line {number}") from exc
        return rows
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("JSON input must be an array of records")
        return payload
    raise ValueError("input must be CSV, JSON, JSONL or NDJSON")


def normalize_row(raw: dict[str, Any], row_number: int) -> tuple[dict[str, Any] | None, list[str], list[str]]:
    row = {norm_key(key): value for key, value in raw.items()}
    errors, warnings = [], []
    record_type = norm(row.get("record_type")).upper()
    if record_type not in RECORD_TYPES:
        errors.append(f"record_type must be one of {sorted(RECORD_TYPES)}")
    team, opponent = norm(row.get("team_abbr")).upper(), norm(row.get("opponent_abbr")).upper()
    if team not in TEAMS:
        errors.append("team_abbr is invalid")
    if opponent and opponent not in TEAMS:
        errors.append("opponent_abbr is invalid")
    if team and opponent and team == opponent:
        errors.append("team_abbr and opponent_abbr cannot match")
    game_id, player_name = norm(row.get("game_id")), norm(row.get("player_name"))
    if not game_id:
        errors.append("game_id is required")
    if not player_name and not norm(row.get("player_id")):
        errors.append("player_name or player_id is required")

    times: dict[str, datetime] = {}
    for field in ("commence_time", "observed_at", "source_report_time"):
        try:
            times[field] = parse_timestamp(row.get(field), field)
        except ValueError as exc:
            errors.append(str(exc))
    if len(times) == 3:
        if times["source_report_time"] > times["observed_at"]:
            errors.append("source_report_time cannot be after observed_at")
        if times["observed_at"] >= times["commence_time"]:
            errors.append("observed_at must be before commence_time")
        if times["source_report_time"] >= times["commence_time"]:
            errors.append("source_report_time must be before commence_time")
        if (times["observed_at"] - times["source_report_time"]).total_seconds() / 60 > 180:
            warnings.append("source report was captured more than 180 minutes after publication")

    source_provider = norm(row.get("source_provider"))
    source_url = norm(row.get("source_url"))
    source_hash = norm(row.get("source_file_sha256")).lower()
    if not source_provider:
        errors.append("source_provider is required")
    if not valid_https(source_url):
        errors.append("source_url must be an HTTPS URL")
    if not re.fullmatch(r"[0-9a-f]{64}", source_hash):
        errors.append("source_file_sha256 must be 64 lowercase hex characters")

    raw_status = norm(row.get("source_status_raw") or row.get("availability_status"))
    raw_role = norm(row.get("source_lineup_role_raw") or row.get("lineup_role"))
    availability, lineup_role = status_from_raw(raw_status), lineup_from_raw(raw_role)
    if record_type == "INJURY_STATUS" and availability == "UNKNOWN":
        warnings.append("injury status could not be normalized")
    if record_type == "LINEUP_STATUS" and lineup_role == "UNKNOWN":
        warnings.append("lineup role could not be normalized")

    prior_expected_minutes = norm(row.get("prior_expected_minutes"))
    prior_impact = norm(row.get("prior_impact_estimate"))
    for field, value, low, high in (
        ("prior_expected_minutes", prior_expected_minutes, 0.0, 48.0),
        ("prior_impact_estimate", prior_impact, -20.0, 20.0),
    ):
        if not value:
            continue
        try:
            number = float(value)
            if not low <= number <= high:
                errors.append(f"{field} outside [{low}, {high}]")
        except ValueError:
            errors.append(f"{field} must be numeric")
    asof = None
    if prior_expected_minutes or prior_impact:
        try:
            asof = parse_timestamp(row.get("player_value_asof"), "player_value_asof")
            if "observed_at" in times and asof > times["observed_at"]:
                errors.append("player_value_asof cannot be after observed_at")
        except ValueError as exc:
            errors.append(str(exc))

    if errors:
        return None, [f"row {row_number}: {message}" for message in errors], [f"row {row_number}: {message}" for message in warnings]
    normalized = {
        "snapshot_record_id": stable_id(source_hash, game_id, team, player_key(row), record_type, raw_status, raw_role, iso_utc(times["observed_at"])),
        "record_type": record_type,
        "game_id": game_id,
        "commence_time": iso_utc(times["commence_time"]),
        "team_abbr": team,
        "opponent_abbr": opponent,
        "is_home": int(norm(row.get("is_home")).lower() in {"1", "true", "yes", "home"}),
        "player_id": norm(row.get("player_id")),
        "player_name": player_name,
        "availability_status": availability if record_type == "INJURY_STATUS" else "UNKNOWN",
        "lineup_role": lineup_role if record_type == "LINEUP_STATUS" else "UNKNOWN",
        "reason_category": reason_category(row.get("source_reason_raw") or row.get("reason")),
        "reason_text": norm(row.get("source_reason_raw") or row.get("reason")),
        "observed_at": iso_utc(times["observed_at"]),
        "source_report_time": iso_utc(times["source_report_time"]),
        "source_provider": source_provider,
        "source_url": source_url,
        "source_file_sha256": source_hash,
        "source_status_raw": raw_status,
        "source_lineup_role_raw": raw_role,
        "prior_expected_minutes": float(prior_expected_minutes) if prior_expected_minutes else None,
        "prior_impact_estimate": float(prior_impact) if prior_impact else None,
        "player_value_asof": iso_utc(asof) if asof else "",
        "player_value_version": norm(row.get("player_value_version")),
    }
    return normalized, [], [f"row {row_number}: {message}" for message in warnings]


def validate(rows: list[dict[str, Any]], output_dir: Path) -> dict[str, Any]:
    normalized, errors, warnings = [], [], []
    for number, raw in enumerate(rows, 2):
        item, item_errors, item_warnings = normalize_row(raw, number)
        errors.extend(item_errors)
        warnings.extend(item_warnings)
        if item:
            normalized.append(item)

    exact_duplicates, seen_ids, unique_rows = 0, set(), []
    for row in normalized:
        key = row["snapshot_record_id"]
        if key in seen_ids:
            exact_duplicates += 1
            continue
        seen_ids.add(key)
        unique_rows.append(row)
    normalized = unique_rows

    grouped: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = {}
    for row in normalized:
        key = (
            row["source_file_sha256"], row["game_id"], row["team_abbr"],
            row["player_id"] or norm_key(row["player_name"]), row["record_type"],
        )
        grouped.setdefault(key, []).append(row)
    conflicts = []
    for key, items in grouped.items():
        values = {(item["availability_status"], item["lineup_role"]) for item in items}
        if len(values) > 1:
            conflicts.append({"key": key, "values": sorted(values)})

    frame = pd.DataFrame(normalized)
    starter_counts = []
    if not frame.empty:
        starters = frame[(frame["record_type"] == "LINEUP_STATUS") & (frame["lineup_role"] == "CONFIRMED_STARTER")]
        for key, group in starters.groupby(["source_file_sha256", "game_id", "team_abbr"]):
            starter_counts.append({"snapshot_team_key": list(key), "confirmed_starters": int(len(group))})
            if len(group) != 5:
                warnings.append(f"confirmed lineup count is {len(group)}, expected 5 for {key}")

    point_in_time_passed = not any("must be before commence_time" in message for message in errors)
    ready = bool(normalized) and not errors and not conflicts and point_in_time_passed
    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "input_rows": len(rows),
        "normalized_rows": len(normalized),
        "excluded_rows": len(rows) - len(normalized),
        "quality": {
            "errors": len(errors), "warnings": len(warnings),
            "error_examples": errors[:50], "warning_examples": warnings[:50],
            "exact_duplicates_removed": exact_duplicates,
            "conflicting_snapshot_records": len(conflicts), "conflict_examples": conflicts[:20],
            "point_in_time_rule_passed": point_in_time_passed,
            "confirmed_starter_counts": starter_counts[:50],
        },
        "coverage": {
            "games": int(frame["game_id"].nunique()) if normalized else 0,
            "teams": int(frame["team_abbr"].nunique()) if normalized else 0,
            "players": int(frame[["player_id", "player_name"]].astype(str).agg("|".join, axis=1).nunique()) if normalized else 0,
            "availability_status_counts": frame["availability_status"].value_counts().sort_index().to_dict() if normalized else {},
            "lineup_role_counts": frame["lineup_role"].value_counts().sort_index().to_dict() if normalized else {},
        },
        "decision": {
            "ready_for_point_in_time_feature_build": ready,
            "ready_for_model_training": False,
            "ready_for_betting_edge_claim": False,
            "reason": "Schema and QA readiness only; historical coverage and player-value joins are still required.",
        },
        "guardrails": {
            "observed_at_strictly_before_commence_time": True,
            "source_report_time_not_after_observed_at": True,
            "player_value_asof_not_after_observed_at": True,
            "raw_source_files_committed": False,
            "late_updates_allowed_for_training": False,
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(normalized).to_csv(output_dir / "injury-lineup-snapshots-normalized.csv", index=False)
    (output_dir / "injury-lineup-validation-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def self_test(output_dir: Path) -> None:
    source_hash = "a" * 64
    valid = [
        {
            "record_type":"INJURY_STATUS", "game_id":"g1", "commence_time":"2026-01-02T00:00:00Z",
            "team_abbr":"BOS", "opponent_abbr":"NYK", "is_home":"1", "player_id":"p1", "player_name":"Player One",
            "source_status_raw":"Questionable", "source_reason_raw":"Left ankle soreness",
            "observed_at":"2026-01-01T20:15:00Z", "source_report_time":"2026-01-01T20:00:00Z",
            "source_provider":"NBA Official Injury Report", "source_url":"https://official.nba.com/example.pdf",
            "source_file_sha256":source_hash, "prior_expected_minutes":"31.5", "prior_impact_estimate":"2.1",
            "player_value_asof":"2026-01-01T19:00:00Z", "player_value_version":"prior-20-v1",
        },
        {
            "record_type":"LINEUP_STATUS", "game_id":"g1", "commence_time":"2026-01-02T00:00:00Z",
            "team_abbr":"BOS", "opponent_abbr":"NYK", "is_home":"1", "player_id":"p1", "player_name":"Player One",
            "source_lineup_role_raw":"Projected Starter", "observed_at":"2026-01-01T20:15:00Z",
            "source_report_time":"2026-01-01T20:00:00Z", "source_provider":"manual_test",
            "source_url":"https://example.com/lineup", "source_file_sha256":source_hash,
        },
    ]
    report = validate(valid, output_dir)
    assert report["normalized_rows"] == 2
    assert report["decision"]["ready_for_point_in_time_feature_build"] is True
    invalid = dict(valid[0])
    invalid["observed_at"] = "2026-01-02T00:01:00Z"
    bad = validate([invalid], output_dir / "invalid")
    assert bad["decision"]["ready_for_point_in_time_feature_build"] is False
    assert bad["quality"]["errors"] >= 1
    (output_dir / "self-test.json").write_text('{"passed":true}\n', encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("Injury/lineup snapshot validator self-test passed")
        return
    if not args.input:
        parser.error("--input is required unless --self-test is used")
    report = validate(read_input(args.input), args.output_dir)
    print(json.dumps(report["decision"], indent=2))
    if not report["decision"]["ready_for_point_in_time_feature_build"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
