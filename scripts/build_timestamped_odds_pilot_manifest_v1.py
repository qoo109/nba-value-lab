#!/usr/bin/env python3
"""Build the frozen 30-game exact no-price Timestamped Odds pilot manifest.

Historical Gold is the authoritative game identity layer. NBA Official LiveData
is used only to recover exact scheduled-tipoff metadata. This module never reads
THE_ODDS_API_KEY, never calls a paid odds endpoint, never retains player/score
rows and never calculates market performance.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import re
import shutil
import sqlite3
import tempfile
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

VERSION = "timestamped-odds-pilot-manifest-v1"
SOURCE_PROVIDER = "NBA Official LiveData Boxscore"
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def open_gold(path: Path) -> tuple[sqlite3.Connection, Path | None]:
    if path.suffix != ".gz":
        return sqlite3.connect(path), None
    temp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
    temp.close()
    temp_path = Path(temp.name)
    with gzip.open(path, "rb") as source, temp_path.open("wb") as destination:
        shutil.copyfileobj(source, destination, length=1024 * 1024)
    return sqlite3.connect(temp_path), temp_path


def load_gold_sample(
    gold_path: Path,
    sample: list[dict[str, Any]],
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    connection, temporary_path = open_gold(gold_path)
    try:
        table_exists = connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='gold_matchup_features'"
        ).fetchone()[0]
        if int(table_exists) != 1:
            raise ValueError("Historical Gold lacks gold_matchup_features")
        ids = [str(item["game_id"]) for item in sample]
        placeholders = ",".join("?" for _ in ids)
        values = connection.execute(
            "SELECT game_id, game_date, home_team_abbr, away_team_abbr "
            f"FROM gold_matchup_features WHERE game_id IN ({placeholders})",
            ids,
        ).fetchall()
    finally:
        connection.close()
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    duplicate_gold_rows = len(values) - len({str(row[0]) for row in values})
    by_id = {
        str(row[0]): {
            "historical_game_id": str(row[0]),
            "game_date": str(row[1]),
            "home_team_abbr": str(row[2]),
            "away_team_abbr": str(row[3]),
        }
        for row in values
    }
    missing: list[str] = []
    mismatches: list[str] = []
    matched: list[dict[str, str]] = []
    for frozen in sample:
        game_id = str(frozen["game_id"])
        row = by_id.get(game_id)
        if row is None:
            missing.append(game_id)
            continue
        expected = (
            str(frozen["game_date"]),
            str(frozen["home"]),
            str(frozen["away"]),
        )
        actual = (
            row["game_date"],
            row["home_team_abbr"],
            row["away_team_abbr"],
        )
        if actual != expected:
            mismatches.append(game_id)
            continue
        matched.append({
            **row,
            "season": str(frozen["season"]),
        })

    matched.sort(key=lambda row: (row["season"], row["game_date"], row["historical_game_id"]))
    return matched, {
        "gold_query_rows": len(values),
        "matched_sample_games": len(matched),
        "duplicate_gold_rows": duplicate_gold_rows,
        "missing_gold_games": sorted(missing),
        "gold_identity_mismatches": sorted(mismatches),
        "gold_input_sha256": sha256_file(gold_path),
    }


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
    selected: dict[str, str],
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

    game_code = str(game.get("gameCode") or "").strip()
    source_date = game_code[:8] if re.match(r"^\d{8}/", game_code) else ""
    expected_date = selected["game_date"]
    if not source_date or source_date != expected_date.replace("-", ""):
        raise ValueError(
            f"official game date mismatch: expected={expected_date} source={source_date or '<blank>'}"
        )

    home = game.get("homeTeam") if isinstance(game.get("homeTeam"), dict) else {}
    away = game.get("awayTeam") if isinstance(game.get("awayTeam"), dict) else {}
    source_home = str(home.get("teamTricode") or "").strip()
    source_away = str(away.get("teamTricode") or "").strip()
    expected_teams = (selected["home_team_abbr"], selected["away_team_abbr"])
    if (source_home, source_away) != expected_teams:
        raise ValueError(
            "official team mismatch: "
            f"expected={selected['away_team_abbr']}@{selected['home_team_abbr']} "
            f"source={source_away}@{source_home}"
        )

    game_time_utc = parse_aware(game.get("gameTimeUTC"), "gameTimeUTC")
    if game_time_utc.utcoffset() != timedelta(0):
        raise ValueError(f"gameTimeUTC is not expressed in UTC: {game.get('gameTimeUTC')!r}")
    game_time_et = parse_aware(game.get("gameEt"), "gameEt")
    if game_time_et.date().isoformat() != expected_date:
        raise ValueError(
            f"gameEt date mismatch: expected={expected_date} actual={game_time_et.date()}"
        )
    if not same_instant(game_time_utc, game_time_et):
        raise ValueError("gameTimeUTC and gameEt represent different instants")

    optional_time_fields_present = 0
    for field in ("gameTimeLocal", "gameTimeHome", "gameTimeAway"):
        text = str(game.get(field) or "").strip()
        if not text:
            continue
        optional_time_fields_present += 1
        if not same_instant(game_time_utc, parse_aware(text, field)):
            raise ValueError(f"{field} does not equal gameTimeUTC")

    arena = game.get("arena") if isinstance(game.get("arena"), dict) else {}
    return (
        {
            **selected,
            "official_game_id": official_game_id,
            "scheduled_tipoff_utc": iso_utc(game_time_utc),
            "official_game_time_et": str(game.get("gameEt") or "").strip(),
            "official_game_time_local": str(game.get("gameTimeLocal") or "").strip(),
            "arena_timezone": str(arena.get("arenaTimezone") or "").strip(),
        },
        {
            "optional_time_fields_present": optional_time_fields_present,
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

    cost_per_request = int(
        policy["source_candidate"]["quota_cost_per_region_per_market_per_request"]
    )
    return plan, {
        "unique_request_timestamps": len(plan),
        "game_slot_rows": len(game_slots),
        "deduplicated_request_savings": len(game_slots) - len(plan),
        "exact_planned_quota_credits": len(plan) * cost_per_request,
        "maximum_paid_quota_credits": int(
            policy["qualification_pilot"]["maximum_paid_quota_credits"]
        ),
        "duplicate_request_plan_timestamps": len(plan)
        - len({row["requested_at_utc"] for row in plan}),
    }


def run(
    policy_path: Path,
    gold_path: Path,
    output_dir: Path,
    *,
    fetcher: Callable[[str], tuple[dict[str, Any], dict[str, Any]]] = fetch_json,
    url_template: str = DEFAULT_URL_TEMPLATE,
) -> dict[str, Any]:
    policy = read_json(policy_path)
    sample = list(policy["qualification_pilot"]["sample"])
    gold_rows, gold_qa = load_gold_sample(gold_path, sample)
    output_dir.mkdir(parents=True, exist_ok=True)

    schedule_rows: list[dict[str, Any]] = []
    official_failures: list[dict[str, str]] = []
    source_hashes: set[str] = set()
    optional_time_fields_present = 0

    for selected in gold_rows:
        historical_game_id = selected["historical_game_id"]
        official_game_id = normalize_official_game_id(historical_game_id)
        source_url = url_template.format(official_game_id=official_game_id)
        try:
            payload, source_meta = fetcher(source_url)
            schedule, time_qa = validate_official_schedule_payload(
                selected, payload, official_game_id
            )
            source_sha = str(source_meta.get("source_sha256") or "").strip()
            if not re.fullmatch(r"[0-9a-f]{64}", source_sha):
                raise ValueError("official source SHA-256 is missing or invalid")
            source_hashes.add(source_sha)
            optional_time_fields_present += int(time_qa["optional_time_fields_present"])
            schedule.update({
                "source_url": source_url,
                "source_retrieved_at": str(source_meta.get("retrieved_at") or "").strip(),
                "source_bytes": int(source_meta.get("source_bytes") or 0),
                "source_sha256": source_sha,
            })
            schedule_rows.append(schedule)
        except Exception as exc:
            official_failures.append({
                "historical_game_id": historical_game_id,
                "error_type": type(exc).__name__,
                "error": str(exc)[:300],
            })

    schedule_rows.sort(
        key=lambda row: (row["season"], row["game_date"], row["historical_game_id"])
    )
    game_slots, base_manifest_report = build_request_manifest(policy, schedule_rows)
    request_plan, request_plan_qa = build_unique_request_plan(policy, game_slots)

    schedule_by_season = Counter(str(row["season"]) for row in schedule_rows)
    slots_by_season = Counter(str(row["season"]) for row in game_slots)
    duplicate_schedule_games = len(schedule_rows) - len({
        row["historical_game_id"] for row in schedule_rows
    })
    duplicate_game_tipoff_pairs = len(schedule_rows) - len({
        (row["historical_game_id"], row["scheduled_tipoff_utc"])
        for row in schedule_rows
    })
    duplicate_game_slot_keys = len(game_slots) - len({
        (row["historical_game_id"], row["snapshot_label"])
        for row in game_slots
    })
    opening_labels = sum(
        str(row["snapshot_label"]).strip().lower().startswith("opening")
        for row in game_slots
    )

    expected_games = int(policy["qualification_pilot"]["games"])
    expected_slots = int(policy["qualification_pilot"]["maximum_requested_snapshot_slots"])
    maximum_credits = int(policy["qualification_pilot"]["maximum_paid_quota_credits"])
    structural_blockers: list[str] = []
    if gold_qa["duplicate_gold_rows"]:
        structural_blockers.append("duplicate_gold_rows")
    if gold_qa["missing_gold_games"]:
        structural_blockers.append("missing_gold_games")
    if gold_qa["gold_identity_mismatches"]:
        structural_blockers.append("gold_identity_mismatches")
    if official_failures:
        structural_blockers.append("official_source_failures")
    if len(schedule_rows) != expected_games:
        structural_blockers.append("schedule_game_count")
    if duplicate_schedule_games:
        structural_blockers.append("duplicate_schedule_games")
    if duplicate_game_tipoff_pairs:
        structural_blockers.append("duplicate_game_tipoff_pairs")
    if len(source_hashes) != len(schedule_rows):
        structural_blockers.append("duplicate_or_missing_official_source_hashes")
    if not base_manifest_report["decision"]["manifest_structurally_ready"]:
        structural_blockers.append("base_manifest_structural_gate")
    if len(game_slots) != expected_slots:
        structural_blockers.append("game_slot_count")
    if duplicate_game_slot_keys:
        structural_blockers.append("duplicate_game_slot_keys")
    if opening_labels:
        structural_blockers.append("opening_labels")
    if request_plan_qa["duplicate_request_plan_timestamps"]:
        structural_blockers.append("duplicate_request_plan_timestamps")
    if request_plan_qa["exact_planned_quota_credits"] > maximum_credits:
        structural_blockers.append("quota_credit_cap")
    if sorted(schedule_by_season.values()) != [10, 10, 10]:
        structural_blockers.append("schedule_games_per_season")
    if sorted(slots_by_season.values()) != [60, 60, 60]:
        structural_blockers.append("game_slots_per_season")

    write_csv(
        output_dir / "timestamped-odds-pilot-exact-schedule-v1.csv",
        schedule_rows,
        SCHEDULE_FIELDS,
    )
    write_csv(
        output_dir / "timestamped-odds-pilot-game-slot-manifest-v1.csv",
        game_slots,
        GAME_SLOT_FIELDS,
    )
    write_csv(
        output_dir / "timestamped-odds-pilot-unique-request-plan-v1.csv",
        request_plan,
        REQUEST_PLAN_FIELDS,
    )
    (output_dir / "timestamped-odds-pilot-schedule-failures-v1.json").write_text(
        json.dumps(official_failures, indent=2) + "\n",
        encoding="utf-8",
    )

    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "formal_state": READY_STATE if not structural_blockers else BLOCKED_STATE,
        "coverage": {
            **gold_qa,
            "official_schedule_requests": len(gold_rows),
            "official_schedule_games": len(schedule_rows),
            "official_source_failures": len(official_failures),
            "schedule_games_by_season": dict(sorted(schedule_by_season.items())),
            "game_slot_rows": len(game_slots),
            "game_slots_by_season": dict(sorted(slots_by_season.items())),
            **request_plan_qa,
        },
        "quality": {
            "official_failures": official_failures,
            "official_source_hashes": len(source_hashes),
            "raw_official_json_files_retained": 0,
            "duplicate_schedule_games": duplicate_schedule_games,
            "duplicate_game_tipoff_pairs": duplicate_game_tipoff_pairs,
            "duplicate_game_slot_keys": duplicate_game_slot_keys,
            "missing_schedule_games": len(
                base_manifest_report["quality"]["missing_schedule_games"]
            ),
            "manifest_identity_mismatches": len(
                base_manifest_report["quality"]["identity_mismatches"]
            ),
            "opening_labels": opening_labels,
            "optional_official_time_fields_present": optional_time_fields_present,
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
            "structural_blockers": sorted(structural_blockers),
        },
        "decision": {
            "manifest_structurally_ready": not structural_blockers,
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
            "official_url_template": url_template,
        },
        "upstream": {
            "policy_pr": 57,
            "adapter_pr": 59,
            "policy_schema_version": policy["schema_version"],
            "model_path": policy["upstream_evidence"]["injury_holdout"][
                "market_research_model_path"
            ],
        },
    }
    (output_dir / "timestamped-odds-pilot-manifest-v1.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def create_synthetic_gold(path: Path, sample: list[dict[str, Any]]) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "CREATE TABLE gold_matchup_features ("
            "game_id TEXT PRIMARY KEY, game_date TEXT NOT NULL, "
            "home_team_abbr TEXT NOT NULL, away_team_abbr TEXT NOT NULL)"
        )
        connection.executemany(
            "INSERT INTO gold_matchup_features VALUES (?, ?, ?, ?)",
            [
                (
                    str(row["game_id"]),
                    str(row["game_date"]),
                    str(row["home"]),
                    str(row["away"]),
                )
                for row in sample
            ],
        )
        connection.commit()
    finally:
        connection.close()


def synthetic_fetcher(
    policy: dict[str, Any],
) -> Callable[[str], tuple[dict[str, Any], dict[str, Any]]]:
    by_official_id = {
        normalize_official_game_id(row["game_id"]): row
        for row in policy["qualification_pilot"]["sample"]
    }

    def fetch(url: str) -> tuple[dict[str, Any], dict[str, Any]]:
        match = re.search(r"boxscore_(\d{10})\.json$", url)
        if not match or match.group(1) not in by_official_id:
            raise ValueError(f"unexpected synthetic source URL: {url}")
        official_game_id = match.group(1)
        row = by_official_id[official_game_id]
        game_day = date.fromisoformat(str(row["game_date"]))
        game_time = datetime.combine(game_day, time(23, 0), tzinfo=timezone.utc)
        payload = {
            "meta": {"code": 200},
            "game": {
                "gameId": official_game_id,
                "gameStatus": 3,
                "gameCode": f"{game_day.strftime('%Y%m%d')}/{row['away']}{row['home']}",
                "gameTimeUTC": iso_utc(game_time),
                "gameEt": iso_utc(game_time),
                "gameTimeLocal": iso_utc(game_time),
                "gameTimeHome": iso_utc(game_time),
                "gameTimeAway": iso_utc(game_time),
                "homeTeam": {
                    "teamTricode": row["home"],
                    "score": 100,
                    "players": [],
                },
                "awayTeam": {
                    "teamTricode": row["away"],
                    "score": 90,
                    "players": [],
                },
                "arena": {"arenaTimezone": "Synthetic/UTC"},
            },
        }
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        return payload, {
            "retrieved_at": "2026-07-18T09:00:00Z",
            "http_status": 200,
            "source_bytes": len(encoded),
            "source_sha256": hashlib.sha256(encoded).hexdigest(),
            "attempts": 1,
        }

    return fetch


def self_test(policy_path: Path, output_dir: Path) -> dict[str, Any]:
    policy = read_json(policy_path)
    sample = list(policy["qualification_pilot"]["sample"])
    output_dir.mkdir(parents=True, exist_ok=True)
    gold_path = output_dir / "synthetic-gold.sqlite"
    create_synthetic_gold(gold_path, sample)

    result_dir = output_dir / "valid"
    report = run(
        policy_path,
        gold_path,
        result_dir,
        fetcher=synthetic_fetcher(policy),
    )
    assert report["formal_state"] == READY_STATE, report
    assert report["coverage"]["matched_sample_games"] == 30, report
    assert report["coverage"]["official_schedule_games"] == 30, report
    assert report["coverage"]["game_slot_rows"] == 180, report
    assert report["coverage"]["exact_planned_quota_credits"] <= 1800, report
    assert report["quality"]["opening_labels"] == 0, report
    assert report["quality"]["player_fields_retained"] == 0, report
    assert report["quality"]["score_fields_retained"] == 0, report
    assert report["quality"]["paid_odds_endpoint_called"] is False, report

    valid_fetcher = synthetic_fetcher(policy)

    def wrong_time_fetch(url: str) -> tuple[dict[str, Any], dict[str, Any]]:
        payload, meta = valid_fetcher(url)
        if payload["game"]["gameId"] == "0022100001":
            payload["game"]["gameEt"] = "2021-10-19T22:00:00Z"
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        meta["source_bytes"] = len(encoded)
        meta["source_sha256"] = hashlib.sha256(encoded).hexdigest()
        return payload, meta

    blocked = run(
        policy_path,
        gold_path,
        output_dir / "negative-time",
        fetcher=wrong_time_fetch,
    )
    assert blocked["formal_state"] == BLOCKED_STATE, blocked
    assert blocked["coverage"]["official_source_failures"] == 1, blocked

    summary = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "checks": {
            "gold_matches": report["coverage"]["matched_sample_games"],
            "schedule_games": report["coverage"]["official_schedule_games"],
            "game_slots": report["coverage"]["game_slot_rows"],
            "unique_request_timestamps": report["coverage"]["unique_request_timestamps"],
            "exact_planned_quota_credits": report["coverage"][
                "exact_planned_quota_credits"
            ],
            "opening_labels": report["quality"]["opening_labels"],
            "wrong_time_consistency_rejected": True,
            "gold_identity_enforced": True,
            "no_player_score_price_or_bookmaker_fields": True,
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
    (output_dir / "timestamped-odds-pilot-manifest-v1-self-test.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )
    gold_path.unlink(missing_ok=True)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--gold", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        report = self_test(args.policy, args.output_dir)
    else:
        if args.gold is None:
            parser.error("--gold is required for live manifest construction")
        report = run(args.policy, args.gold, args.output_dir)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
