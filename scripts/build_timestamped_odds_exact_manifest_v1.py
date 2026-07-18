#!/usr/bin/env python3
"""Build the frozen 30-game no-price Timestamped Odds request manifest.

The script fetches only NBA Official LiveData boxscore metadata to recover
``gameTimeUTC``. It never reads an odds API key, never calls an odds provider,
never retains player/score rows and never calculates market performance.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from import_official_nba_participation_labels import (
    DEFAULT_URL_TEMPLATE,
    fetch_json,
    normalize_official_game_id,
)
from qualify_timestamped_odds_v1 import (
    build_request_manifest,
    iso_utc,
    parse_utc,
    read_json,
    utc_now,
)

VERSION = "timestamped-odds-exact-manifest-v1"
SOURCE_PROVIDER = "NBA Official LiveData Boxscore"
FORMAL_STATE = "EXACT_MANIFEST_READY_ACCESS_NOT_PROVIDED"
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
GAME_SLOT_FIELDS = [
    "request_id",
    "source_id",
    "endpoint",
    "sport_key",
    "region",
    "market",
    "odds_format",
    "historical_game_id",
    "season",
    "game_date",
    "away_team_abbr",
    "home_team_abbr",
    "scheduled_tipoff_utc",
    "snapshot_label",
    "seconds_before_tipoff",
    "requested_at_utc",
]
REQUEST_PLAN_FIELDS = [
    "request_plan_id",
    "source_id",
    "endpoint",
    "sport_key",
    "region",
    "market",
    "odds_format",
    "requested_at_utc",
    "target_game_count",
    "target_slot_count",
    "target_game_ids",
    "target_snapshot_labels",
]


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def parse_aware(value: Any, field: str) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"blank {field}")
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"{field} lacks timezone: {value!r}")
    return parsed


def same_instant(left: datetime, right: datetime) -> bool:
    return left.astimezone(timezone.utc) == right.astimezone(timezone.utc)


def validate_official_schedule_payload(
    expected: dict[str, Any],
    payload: dict[str, Any],
    official_game_id: str,
) -> tuple[dict[str, Any], dict[str, int]]:
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    game = payload.get("game") if isinstance(payload.get("game"), dict) else {}
    if str(meta.get("code", 200)) not in {"200", "200.0"}:
        raise ValueError(f"official meta code is not 200: {meta.get('code')!r}")
    if str(game.get("gameId") or "").strip() != official_game_id:
        raise ValueError(
            f"official game ID mismatch: expected={official_game_id} actual={game.get('gameId')!r}"
        )
    if int(game.get("gameStatus") or 0) != 3:
        raise ValueError(f"official game is not final: {game.get('gameStatus')!r}")

    expected_date = str(expected["game_date"])
    game_code = str(game.get("gameCode") or "").strip()
    source_date = game_code[:8] if re.match(r"^\d{8}/", game_code) else ""
    if source_date != expected_date.replace("-", ""):
        raise ValueError(
            f"official game date mismatch: expected={expected_date} source={source_date or '<blank>'}"
        )

    home = game.get("homeTeam") if isinstance(game.get("homeTeam"), dict) else {}
    away = game.get("awayTeam") if isinstance(game.get("awayTeam"), dict) else {}
    source_home = str(home.get("teamTricode") or "").strip()
    source_away = str(away.get("teamTricode") or "").strip()
    if (source_home, source_away) != (str(expected["home"]), str(expected["away"])):
        raise ValueError(
            "official team mismatch: "
            f"expected={expected['away']}@{expected['home']} "
            f"source={source_away}@{source_home}"
        )

    game_time_utc = parse_aware(game.get("gameTimeUTC"), "gameTimeUTC")
    if game_time_utc.utcoffset() != timedelta(0):
        raise ValueError(f"gameTimeUTC is not UTC: {game.get('gameTimeUTC')!r}")
    game_time_et = parse_aware(game.get("gameEt"), "gameEt")
    if game_time_et.date().isoformat() != expected_date:
        raise ValueError(
            f"gameEt date mismatch: expected={expected_date} actual={game_time_et.date()}"
        )
    if not same_instant(game_time_utc, game_time_et):
        raise ValueError("gameTimeUTC and gameEt represent different instants")

    optional_fields = ["gameTimeLocal", "gameTimeHome", "gameTimeAway"]
    present_optional = 0
    for field in optional_fields:
        value = str(game.get(field) or "").strip()
        if not value:
            continue
        present_optional += 1
        parsed = parse_aware(value, field)
        if not same_instant(game_time_utc, parsed):
            raise ValueError(f"{field} does not equal gameTimeUTC")

    arena = game.get("arena") if isinstance(game.get("arena"), dict) else {}
    arena_timezone = str(arena.get("arenaTimezone") or "").strip()
    return (
        {
            "historical_game_id": str(expected["game_id"]),
            "official_game_id": official_game_id,
            "season": str(expected["season"]),
            "game_date": expected_date,
            "away_team_abbr": str(expected["away"]),
            "home_team_abbr": str(expected["home"]),
            "scheduled_tipoff_utc": iso_utc(game_time_utc),
            "official_game_time_et": str(game.get("gameEt") or "").strip(),
            "official_game_time_local": str(game.get("gameTimeLocal") or "").strip(),
            "arena_timezone": arena_timezone,
        },
        {
            "optional_time_fields_present": present_optional,
            "time_instant_mismatches": 0,
        },
    )


def build_unique_request_plan(
    policy: dict[str, Any],
    game_slots: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in game_slots:
        grouped[str(row["requested_at_utc"])].append(row)

    plan: list[dict[str, Any]] = []
    for requested_at in sorted(grouped):
        rows = grouped[requested_at]
        template = rows[0]
        game_ids = sorted({str(row["historical_game_id"]) for row in rows})
        labels = sorted({str(row["snapshot_label"]) for row in rows})
        plan.append({
            "request_plan_id": hashlib.sha256(
                f"{policy['source_candidate']['source_id']}|{requested_at}".encode("utf-8")
            ).hexdigest()[:24],
            "source_id": template["source_id"],
            "endpoint": template["endpoint"],
            "sport_key": template["sport_key"],
            "region": template["region"],
            "market": template["market"],
            "odds_format": template["odds_format"],
            "requested_at_utc": requested_at,
            "target_game_count": len(game_ids),
            "target_slot_count": len(rows),
            "target_game_ids": ";".join(game_ids),
            "target_snapshot_labels": ";".join(labels),
        })

    source = policy["source_candidate"]
    cost_per_request = int(source["quota_cost_per_region_per_market_per_request"])
    report = {
        "unique_request_timestamps": len(plan),
        "game_slot_rows": len(game_slots),
        "deduplicated_request_savings": len(game_slots) - len(plan),
        "exact_planned_quota_credits": len(plan) * cost_per_request,
        "maximum_paid_quota_credits": int(policy["qualification_pilot"]["maximum_paid_quota_credits"]),
        "duplicate_request_plan_timestamps": len(plan)
        - len({row["requested_at_utc"] for row in plan}),
    }
    return plan, report


def run(
    policy: dict[str, Any],
    output_dir: Path,
    *,
    fetcher: Callable[[str], tuple[dict[str, Any], dict[str, Any]]] = fetch_json,
    url_template: str = DEFAULT_URL_TEMPLATE,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    sample = list(policy["qualification_pilot"]["sample"])
    schedule_rows: list[dict[str, Any]] = []
    source_failures: list[dict[str, str]] = []
    source_hashes: set[str] = set()
    optional_time_fields_present = 0
    raw_files_written = 0
    player_fields_retained = 0
    score_fields_retained = 0

    for expected in sample:
        historical_game_id = str(expected["game_id"])
        official_game_id = normalize_official_game_id(historical_game_id)
        source_url = url_template.format(official_game_id=official_game_id)
        try:
            payload, source_meta = fetcher(source_url)
            schedule, qa = validate_official_schedule_payload(
                expected, payload, official_game_id
            )
            source_sha = str(source_meta.get("source_sha256") or "").strip()
            if not re.fullmatch(r"[0-9a-f]{64}", source_sha):
                raise ValueError("official source SHA-256 is missing or invalid")
            source_hashes.add(source_sha)
            optional_time_fields_present += int(qa["optional_time_fields_present"])
            schedule.update({
                "source_url": source_url,
                "source_retrieved_at": str(source_meta.get("retrieved_at") or "").strip(),
                "source_bytes": int(source_meta.get("source_bytes") or 0),
                "source_sha256": source_sha,
            })
            schedule_rows.append(schedule)
        except Exception as exc:  # preserve a deidentified source failure, never replace a game
            source_failures.append({
                "historical_game_id": historical_game_id,
                "failure_type": type(exc).__name__,
                "failure_message": str(exc)[:300],
            })

    schedule_rows.sort(key=lambda row: (row["season"], row["game_date"], row["historical_game_id"]))
    game_slots, manifest_report = build_request_manifest(policy, schedule_rows)
    unique_plan, request_plan_report = build_unique_request_plan(policy, game_slots)

    duplicate_schedule_game_ids = len(schedule_rows) - len(
        {row["historical_game_id"] for row in schedule_rows}
    )
    duplicate_tipoff_game_pairs = len(schedule_rows) - len({
        (row["historical_game_id"], row["scheduled_tipoff_utc"])
        for row in schedule_rows
    })
    duplicate_game_slot_keys = len(game_slots) - len({
        (row["historical_game_id"], row["snapshot_label"])
        for row in game_slots
    })
    opening_labels = sum(str(row["snapshot_label"]).lower() == "opening" for row in game_slots)
    season_schedule_counts = Counter(str(row["season"]) for row in schedule_rows)
    season_slot_counts = Counter(str(row["season"]) for row in game_slots)

    expected_games = int(policy["qualification_pilot"]["games"])
    expected_slots = int(policy["qualification_pilot"]["maximum_requested_snapshot_slots"])
    max_credits = int(policy["qualification_pilot"]["maximum_paid_quota_credits"])
    structural_blockers: list[str] = []
    if source_failures:
        structural_blockers.append("official_source_failures")
    if len(schedule_rows) != expected_games:
        structural_blockers.append("schedule_game_count")
    if duplicate_schedule_game_ids:
        structural_blockers.append("duplicate_schedule_game_ids")
    if duplicate_tipoff_game_pairs:
        structural_blockers.append("duplicate_game_tipoff_pairs")
    if len(source_hashes) != len(schedule_rows):
        structural_blockers.append("duplicate_or_missing_source_hashes")
    if not manifest_report["decision"]["manifest_structurally_ready"]:
        structural_blockers.append("base_manifest_structural_gate")
    if len(game_slots) != expected_slots:
        structural_blockers.append("game_slot_count")
    if duplicate_game_slot_keys:
        structural_blockers.append("duplicate_game_slot_keys")
    if opening_labels:
        structural_blockers.append("opening_labels")
    if request_plan_report["duplicate_request_plan_timestamps"]:
        structural_blockers.append("duplicate_request_plan_timestamps")
    if request_plan_report["exact_planned_quota_credits"] > max_credits:
        structural_blockers.append("quota_credit_cap")
    if sorted(season_schedule_counts.values()) != [10, 10, 10]:
        structural_blockers.append("schedule_games_per_season")
    if sorted(season_slot_counts.values()) != [60, 60, 60]:
        structural_blockers.append("slots_per_season")

    write_csv(output_dir / "timestamped-odds-schedule-manifest-v1.csv", schedule_rows, SCHEDULE_FIELDS)
    write_csv(output_dir / "timestamped-odds-game-slot-manifest-v1.csv", game_slots, GAME_SLOT_FIELDS)
    write_csv(output_dir / "timestamped-odds-unique-request-plan-v1.csv", unique_plan, REQUEST_PLAN_FIELDS)
    (output_dir / "timestamped-odds-schedule-source-failures-v1.json").write_text(
        json.dumps(source_failures, indent=2) + "\n", encoding="utf-8"
    )

    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "formal_state": FORMAL_STATE if not structural_blockers else "SCHEDULE_MANIFEST_STRUCTURAL_BLOCKED",
        "source": {
            "provider": SOURCE_PROVIDER,
            "url_template": url_template,
            "official_source_requests": len(sample),
            "official_source_successes": len(schedule_rows),
            "official_source_failures": len(source_failures),
            "source_hashes": len(source_hashes),
            "raw_source_files_retained": raw_files_written,
        },
        "coverage": {
            "frozen_sample_games": expected_games,
            "schedule_rows": len(schedule_rows),
            "schedule_games_by_season": dict(sorted(season_schedule_counts.items())),
            "game_slot_rows": len(game_slots),
            "game_slots_by_season": dict(sorted(season_slot_counts.items())),
            **request_plan_report,
        },
        "quality": {
            "duplicate_schedule_game_ids": duplicate_schedule_game_ids,
            "duplicate_game_tipoff_pairs": duplicate_tipoff_game_pairs,
            "duplicate_game_slot_keys": duplicate_game_slot_keys,
            "opening_labels": opening_labels,
            "optional_official_time_fields_present": optional_time_fields_present,
            "game_date_team_identity_mismatches": len(manifest_report["quality"]["identity_mismatches"]),
            "missing_schedule_games": len(manifest_report["quality"]["missing_schedule_games"]),
            "prices_in_manifests": False,
            "bookmaker_fields_in_manifests": False,
            "player_fields_retained": player_fields_retained,
            "score_fields_retained": score_fields_retained,
            "odds_api_key_read": False,
            "paid_odds_endpoint_called": False,
            "real_odds_quotes_downloaded": 0,
            "market_metrics_calculated": False,
            "structural_blockers": sorted(structural_blockers),
        },
        "decision": {
            "exact_no_price_manifest_ready": not structural_blockers,
            "access_state": "ACCESS_NOT_PROVIDED",
            "ready_for_paid_qualification_execution": False,
            "ready_for_production_backfill": False,
            "ready_for_market_backtest": False,
            "ready_for_clv_ev_roi": False,
            "ready_for_betting_edge_claim": False,
            "formal_stake": 0,
        },
        "upstream": {
            "policy_pr": 57,
            "adapter_pr": 59,
            "policy_schema_version": policy["schema_version"],
            "model_path": policy["upstream_evidence"]["injury_holdout"]["market_research_model_path"],
        },
    }
    (output_dir / "timestamped-odds-exact-manifest-v1-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def synthetic_fetcher(policy: dict[str, Any]) -> Callable[[str], tuple[dict[str, Any], dict[str, Any]]]:
    sample_by_official = {
        normalize_official_game_id(row["game_id"]): row
        for row in policy["qualification_pilot"]["sample"]
    }

    def fetch(url: str) -> tuple[dict[str, Any], dict[str, Any]]:
        match = re.search(r"boxscore_(\d{10})\.json$", url)
        if not match or match.group(1) not in sample_by_official:
            raise ValueError(f"unexpected synthetic URL: {url}")
        official_game_id = match.group(1)
        row = sample_by_official[official_game_id]
        game_day = date.fromisoformat(str(row["game_date"]))
        game_time = datetime.combine(game_day, time(23, 0), tzinfo=timezone.utc)
        payload = {
            "meta": {"code": 200},
            "game": {
                "gameId": official_game_id,
                "gameTimeUTC": iso_utc(game_time),
                "gameTimeLocal": iso_utc(game_time),
                "gameTimeHome": iso_utc(game_time),
                "gameTimeAway": iso_utc(game_time),
                "gameEt": iso_utc(game_time),
                "gameCode": f"{game_day.strftime('%Y%m%d')}/{row['away']}{row['home']}",
                "gameStatus": 3,
                "homeTeam": {"teamTricode": row["home"], "score": 100, "players": []},
                "awayTeam": {"teamTricode": row["away"], "score": 90, "players": []},
                "arena": {"arenaTimezone": "Synthetic/UTC"},
            },
        }
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        return payload, {
            "retrieved_at": "2026-07-18T09:00:00Z",
            "source_bytes": len(encoded),
            "source_sha256": hashlib.sha256(encoded).hexdigest(),
            "http_status": 200,
            "attempts": 1,
        }

    return fetch


def self_test(policy: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    report = run(policy, output_dir, fetcher=synthetic_fetcher(policy))
    assert report["formal_state"] == FORMAL_STATE, report
    assert report["coverage"]["schedule_rows"] == 30, report
    assert report["coverage"]["game_slot_rows"] == 180, report
    assert report["coverage"]["exact_planned_quota_credits"] <= 1800, report
    assert report["quality"]["opening_labels"] == 0, report
    assert report["quality"]["player_fields_retained"] == 0, report
    assert report["quality"]["score_fields_retained"] == 0, report
    assert report["quality"]["paid_odds_endpoint_called"] is False, report
    assert report["decision"]["ready_for_paid_qualification_execution"] is False, report

    bad_fetch = synthetic_fetcher(policy)

    def wrong_time_fetch(url: str) -> tuple[dict[str, Any], dict[str, Any]]:
        payload, meta = bad_fetch(url)
        if payload["game"]["gameId"] == "0022100001":
            payload["game"]["gameEt"] = "2021-10-19T22:00:00Z"
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        meta["source_bytes"] = len(encoded)
        meta["source_sha256"] = hashlib.sha256(encoded).hexdigest()
        return payload, meta

    blocked = run(policy, output_dir / "negative-time", fetcher=wrong_time_fetch)
    assert blocked["formal_state"] == "SCHEDULE_MANIFEST_STRUCTURAL_BLOCKED", blocked
    assert blocked["source"]["official_source_failures"] == 1, blocked

    summary = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "checks": {
            "synthetic_schedule_games": report["coverage"]["schedule_rows"],
            "synthetic_game_slots": report["coverage"]["game_slot_rows"],
            "synthetic_unique_request_timestamps": report["coverage"]["unique_request_timestamps"],
            "synthetic_exact_quota": report["coverage"]["exact_planned_quota_credits"],
            "opening_labels": report["quality"]["opening_labels"],
            "wrong_time_consistency_rejected": True,
            "no_player_or_score_fields_retained": True,
            "no_paid_odds_access": True,
        },
        "execution_boundary": {
            "official_live_requests": 0,
            "odds_provider_requests": 0,
            "odds_api_key_read": False,
            "real_odds_quotes_downloaded": 0,
            "market_metrics_calculated": False,
            "formal_stake": 0,
        },
    }
    (output_dir / "timestamped-odds-exact-manifest-v1-self-test.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    if args.self_test == args.live:
        parser.error("choose exactly one of --self-test or --live")

    policy = read_json(args.policy)
    if args.self_test:
        report = self_test(policy, args.output_dir)
    else:
        report = run(policy, args.output_dir)
    print(json.dumps(report, indent=2))
    formal_state = report.get("formal_state")
    if args.live and formal_state != FORMAL_STATE:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
