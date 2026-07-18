#!/usr/bin/env python3
"""Build the frozen no-price odds pilot manifest from NBA official season schedules.

This adapter performs exactly one low-frequency request per frozen season to the
legacy NBA schedule JSON. It reads no odds API key and calls no paid odds endpoint.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_timestamped_odds_pilot_manifest_v1 import (
    GAME_SLOT_FIELDS,
    REQUEST_PLAN_FIELDS,
    build_unique_request_plan,
    load_gold_sample,
    write_csv,
)
from qualify_timestamped_odds_v1 import build_request_manifest, read_json, utc_now

VERSION = "timestamped-odds-pilot-legacy-schedule-v1"
SOURCE_PROVIDER = "NBA Official Legacy Season Schedule"
URL_TEMPLATE = (
    "https://data.nba.com/data/10s/v2015/json/mobile_teams/"
    "nba/{season_start}/league/00_full_schedule.json"
)
READY_STATE = "PILOT_MANIFEST_READY_ACCESS_NOT_PROVIDED"
BLOCKED_STATE = "PILOT_MANIFEST_STRUCTURAL_BLOCKED"

SCHEDULE_FIELDS = [
    "historical_game_id",
    "official_game_id",
    "season",
    "game_date",
    "away_team_abbr",
    "home_team_abbr",
    "scheduled_tipoff_utc",
    "official_game_time_et",
    "official_game_time_local",
    "arena_timezone",
    "source_url",
    "source_retrieved_at",
    "source_bytes",
    "source_sha256",
]


def fetch_json(url: str, attempts: int = 3) -> tuple[dict[str, Any], dict[str, Any]]:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "NBA-Value-Lab-Research/1.0",
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read()
                status = int(getattr(response, "status", 200))
            if status != 200:
                raise ValueError(f"unexpected HTTP status {status}")
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("official schedule JSON root is not an object")
            return payload, {
                "retrieved_at": utc_now(),
                "http_status": status,
                "source_bytes": len(raw),
                "source_sha256": hashlib.sha256(raw).hexdigest(),
                "attempts": attempt,
            }
        except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(attempt)
    raise RuntimeError(f"official season schedule fetch failed after {attempts} attempts: {last_error}")


def normalize_gid(value: Any) -> str:
    raw = re.sub(r"\.0$", "", str(value or "").strip())
    if not re.fullmatch(r"\d{8}|\d{10}", raw):
        raise ValueError(f"unsupported official schedule game ID: {value!r}")
    return raw.zfill(10)


def flatten_schedule(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for month in payload.get("lscd") or []:
        if not isinstance(month, dict):
            continue
        month_schedule = month.get("mscd") if isinstance(month.get("mscd"), dict) else {}
        for game in month_schedule.get("g") or []:
            if isinstance(game, dict):
                rows.append(game)
    return rows


def parse_tipoff_utc(game: dict[str, Any]) -> str:
    utc_date = str(game.get("gdtutc") or "").strip()
    utc_time = str(game.get("utctm") or "").strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", utc_date):
        raise ValueError(f"invalid gdtutc: {utc_date!r}")
    if not re.fullmatch(r"\d{2}:\d{2}(?::\d{2})?", utc_time):
        raise ValueError(f"invalid utctm: {utc_time!r}")
    if len(utc_time) == 5:
        utc_time += ":00"
    parsed = datetime.fromisoformat(f"{utc_date}T{utc_time}+00:00")
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def team_abbr(game: dict[str, Any], side: str) -> str:
    team = game.get(side) if isinstance(game.get(side), dict) else {}
    return str(team.get("ta") or "").strip().upper()


def run(policy_path: Path, gold_path: Path, output_dir: Path) -> dict[str, Any]:
    policy = read_json(policy_path)
    sample = list(policy["qualification_pilot"]["sample"])
    gold_rows, gold_qa = load_gold_sample(gold_path, sample)
    output_dir.mkdir(parents=True, exist_ok=True)

    source_failures: list[dict[str, str]] = []
    season_payloads: dict[str, tuple[dict[str, Any], dict[str, Any], str]] = {}
    for season in sorted({str(row["season"]) for row in gold_rows}):
        season_start = season.split("-", 1)[0]
        url = URL_TEMPLATE.format(season_start=season_start)
        try:
            payload, meta = fetch_json(url)
            season_payloads[season] = (payload, meta, url)
        except Exception as exc:
            source_failures.append({
                "season": season,
                "error_type": type(exc).__name__,
                "error": str(exc)[:300],
                "source_url": url,
            })

    schedule_rows: list[dict[str, Any]] = []
    game_failures: list[dict[str, str]] = []
    source_hashes: set[str] = set()
    for selected in gold_rows:
        season = selected["season"]
        source = season_payloads.get(season)
        if source is None:
            game_failures.append({
                "historical_game_id": selected["historical_game_id"],
                "error_type": "SourceMissing",
                "error": f"official season schedule unavailable for {season}",
            })
            continue
        payload, meta, source_url = source
        wanted = normalize_gid(selected["historical_game_id"])
        candidates = [game for game in flatten_schedule(payload) if normalize_gid(game.get("gid")) == wanted]
        if len(candidates) != 1:
            game_failures.append({
                "historical_game_id": selected["historical_game_id"],
                "error_type": "GameMatchError",
                "error": f"official schedule candidates={len(candidates)}",
            })
            continue
        game = candidates[0]
        source_date = str(game.get("gdte") or "").strip()
        source_home = team_abbr(game, "h")
        source_away = team_abbr(game, "v")
        if (
            source_date != selected["game_date"]
            or source_home != selected["home_team_abbr"]
            or source_away != selected["away_team_abbr"]
        ):
            game_failures.append({
                "historical_game_id": selected["historical_game_id"],
                "error_type": "IdentityMismatch",
                "error": (
                    f"expected={selected['game_date']} {selected['away_team_abbr']}@{selected['home_team_abbr']} "
                    f"source={source_date} {source_away}@{source_home}"
                ),
            })
            continue
        try:
            tipoff = parse_tipoff_utc(game)
        except Exception as exc:
            game_failures.append({
                "historical_game_id": selected["historical_game_id"],
                "error_type": type(exc).__name__,
                "error": str(exc)[:300],
            })
            continue
        source_sha = str(meta["source_sha256"])
        source_hashes.add(source_sha)
        schedule_rows.append({
            **selected,
            "official_game_id": wanted,
            "scheduled_tipoff_utc": tipoff,
            "official_game_time_et": str(game.get("etm") or "").strip(),
            "official_game_time_local": str(game.get("htm") or "").strip(),
            "arena_timezone": "",
            "source_url": source_url,
            "source_retrieved_at": str(meta["retrieved_at"]),
            "source_bytes": int(meta["source_bytes"]),
            "source_sha256": source_sha,
        })

    schedule_rows.sort(key=lambda row: (row["season"], row["game_date"], row["historical_game_id"]))
    game_slots, base_report = build_request_manifest(policy, schedule_rows)
    request_plan, plan_qa = build_unique_request_plan(policy, game_slots)
    schedule_by_season = Counter(row["season"] for row in schedule_rows)
    slots_by_season = Counter(row["season"] for row in game_slots)
    duplicate_schedule_games = len(schedule_rows) - len({row["historical_game_id"] for row in schedule_rows})
    duplicate_game_slots = len(game_slots) - len({(row["historical_game_id"], row["snapshot_label"]) for row in game_slots})
    opening_labels = sum(str(row["snapshot_label"]).lower().startswith("opening") for row in game_slots)

    expected_games = int(policy["qualification_pilot"]["games"])
    expected_slots = int(policy["qualification_pilot"]["maximum_requested_snapshot_slots"])
    maximum_credits = int(policy["qualification_pilot"]["maximum_paid_quota_credits"])
    blockers: list[str] = []
    if gold_qa["duplicate_gold_rows"]: blockers.append("duplicate_gold_rows")
    if gold_qa["missing_gold_games"]: blockers.append("missing_gold_games")
    if gold_qa["gold_identity_mismatches"]: blockers.append("gold_identity_mismatches")
    if source_failures: blockers.append("official_season_source_failures")
    if game_failures: blockers.append("official_game_schedule_failures")
    if len(schedule_rows) != expected_games: blockers.append("schedule_game_count")
    if sorted(schedule_by_season.values()) != [10, 10, 10]: blockers.append("schedule_games_per_season")
    if duplicate_schedule_games: blockers.append("duplicate_schedule_games")
    if len(source_hashes) != 3: blockers.append("official_season_source_hash_count")
    if not base_report["decision"]["manifest_structurally_ready"]: blockers.append("base_manifest_structural_gate")
    if len(game_slots) != expected_slots: blockers.append("game_slot_count")
    if sorted(slots_by_season.values()) != [60, 60, 60]: blockers.append("game_slots_per_season")
    if duplicate_game_slots: blockers.append("duplicate_game_slot_keys")
    if opening_labels: blockers.append("opening_labels")
    if plan_qa["duplicate_request_plan_timestamps"]: blockers.append("duplicate_request_plan_timestamps")
    if plan_qa["exact_planned_quota_credits"] > maximum_credits: blockers.append("quota_credit_cap")

    write_csv(output_dir / "timestamped-odds-pilot-exact-schedule-v1.csv", schedule_rows, SCHEDULE_FIELDS)
    write_csv(output_dir / "timestamped-odds-pilot-game-slot-manifest-v1.csv", game_slots, GAME_SLOT_FIELDS)
    write_csv(output_dir / "timestamped-odds-pilot-unique-request-plan-v1.csv", request_plan, REQUEST_PLAN_FIELDS)
    failures = {"season_source_failures": source_failures, "game_schedule_failures": game_failures}
    (output_dir / "timestamped-odds-pilot-schedule-failures-v1.json").write_text(
        json.dumps(failures, indent=2) + "\n", encoding="utf-8"
    )

    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "formal_state": READY_STATE if not blockers else BLOCKED_STATE,
        "coverage": {
            **gold_qa,
            "official_season_schedule_requests": 3,
            "official_season_schedule_sources": len(season_payloads),
            "official_schedule_games": len(schedule_rows),
            "official_source_failures": len(source_failures),
            "official_game_failures": len(game_failures),
            "schedule_games_by_season": dict(sorted(schedule_by_season.items())),
            "game_slot_rows": len(game_slots),
            "game_slots_by_season": dict(sorted(slots_by_season.items())),
            **plan_qa,
        },
        "quality": {
            "source_failures": source_failures,
            "game_failures": game_failures,
            "official_source_hashes": len(source_hashes),
            "raw_official_json_files_retained": 0,
            "duplicate_schedule_games": duplicate_schedule_games,
            "duplicate_game_slot_keys": duplicate_game_slots,
            "opening_labels": opening_labels,
            "prices_in_manifests": False,
            "bookmaker_fields_in_manifests": False,
            "player_fields_retained": 0,
            "score_fields_retained": 0,
            "odds_api_key_read": False,
            "network_calls_to_paid_odds_provider": 0,
            "paid_odds_endpoint_called": False,
            "real_odds_quotes_downloaded": 0,
            "subscription_or_purchase_created": False,
            "market_metrics_calculated": False,
            "structural_blockers": sorted(blockers),
        },
        "decision": {
            "manifest_structurally_ready": not blockers,
            "access_state": "ACCESS_NOT_PROVIDED",
            "ready_for_paid_qualification_execution": False,
            "paid_execution_requires_explicit_user_approval": True,
            "paid_execution_requires_private_secret": True,
            "ready_for_production_backfill": False,
            "ready_for_market_backtest": False,
            "ready_for_clv_ev_roi": False,
            "ready_for_betting_edge_claim": False,
            "formal_stake": 0,
        },
        "source": {
            "gold_artifact_run": 29551715399,
            "official_provider": SOURCE_PROVIDER,
            "official_url_template": URL_TEMPLATE,
        },
        "upstream": {
            "policy_pr": 57,
            "adapter_pr": 59,
            "policy_schema_version": policy["schema_version"],
            "model_path": policy["upstream_evidence"]["injury_holdout"]["market_research_model_path"],
        },
    }
    (output_dir / "timestamped-odds-pilot-manifest-v1.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.policy, args.gold, args.output_dir)
    print(json.dumps({
        "formal_state": report["formal_state"],
        "coverage": report["coverage"],
        "structural_blockers": report["quality"]["structural_blockers"],
    }, indent=2))


if __name__ == "__main__":
    main()
