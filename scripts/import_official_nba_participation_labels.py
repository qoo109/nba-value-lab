#!/usr/bin/env python3
"""Import deidentified player participation labels from NBA Official LiveData boxscores.

The official response includes player IDs, played flags, status, notPlayingReason and minutes.
Player names and free-text notPlayingDescription values are never written to output.
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
from typing import Any, Callable

VERSION = "official-player-participation-labels-v1"
SOURCE_PROVIDER = "NBA Official LiveData Boxscore"
DEFAULT_URL_TEMPLATE = (
    "https://cdn.nba.com/static/json/liveData/boxscore/"
    "boxscore_{official_game_id}.json"
)
LABELS = {
    "PLAYED",
    "EXPLICIT_DNP",
    "INACTIVE_OR_NOT_DRESSED",
    "UNKNOWN",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def normalize_official_game_id(value: Any) -> str:
    raw = re.sub(r"\.0$", "", str(value or "").strip())
    if not re.fullmatch(r"\d{8}|\d{10}", raw):
        raise ValueError(f"unsupported historical game ID: {value!r}")
    return raw.zfill(10)


def parse_iso_minutes(value: Any) -> float:
    text = str(value or "").strip()
    if not text:
        return 0.0
    numeric = re.fullmatch(r"\d+(?:\.\d+)?", text)
    if numeric:
        return float(text)
    match = re.fullmatch(
        r"P(?:\d+D)?T(?:(\d+(?:\.\d+)?)H)?(?:(\d+(?:\.\d+)?)M)?"
        r"(?:(\d+(?:\.\d+)?)S)?",
        text,
    )
    if not match:
        raise ValueError(f"unsupported official minutes format: {value!r}")
    hours = float(match.group(1) or 0)
    minutes = float(match.group(2) or 0)
    seconds = float(match.group(3) or 0)
    return round(hours * 60 + minutes + seconds / 60, 6)


def truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def classify_player(player: dict[str, Any]) -> tuple[str, float, int, int, str, str]:
    statistics = player.get("statistics") if isinstance(player.get("statistics"), dict) else {}
    minutes = parse_iso_minutes(statistics.get("minutes"))
    played = int(truthy(player.get("played")) or minutes > 0)
    starter = int(truthy(player.get("starter")) and played == 1)
    status = str(player.get("status") or "").strip().upper()
    reason = str(player.get("notPlayingReason") or "").strip().upper()

    if played:
        label = "PLAYED"
    elif reason.startswith("DNP"):
        label = "EXPLICIT_DNP"
    elif status == "INACTIVE" or reason.startswith(("INACTIVE", "DND", "NWT")):
        label = "INACTIVE_OR_NOT_DRESSED"
    else:
        label = "UNKNOWN"
    return label, minutes, played, starter, status, reason


def fetch_json(
    url: str,
    *,
    attempts: int = 3,
    timeout_seconds: int = 60,
) -> tuple[dict[str, Any], dict[str, Any]]:
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
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                payload = response.read()
                status = int(getattr(response, "status", 200))
            if status != 200:
                raise ValueError(f"unexpected HTTP status {status}")
            parsed = json.loads(payload.decode("utf-8"))
            if not isinstance(parsed, dict):
                raise ValueError("official JSON root is not an object")
            return parsed, {
                "retrieved_at": utc_now(),
                "source_bytes": len(payload),
                "source_sha256": hashlib.sha256(payload).hexdigest(),
                "http_status": status,
                "attempts": attempt,
            }
        except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(attempt)
    raise RuntimeError(f"official source fetch failed after {attempts} attempts: {last_error}")


def validate_game_payload(
    selected: dict[str, str],
    payload: dict[str, Any],
    official_game_id: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    game = payload.get("game") if isinstance(payload.get("game"), dict) else {}
    if str(meta.get("code", 200)) not in {"200", "200.0"}:
        raise ValueError(f"official meta code is not 200: {meta.get('code')!r}")
    if str(game.get("gameId") or "").strip() != official_game_id:
        raise ValueError(
            f"official game ID mismatch: expected={official_game_id} "
            f"actual={game.get('gameId')!r}"
        )
    if int(game.get("gameStatus") or 0) != 3:
        raise ValueError(f"official game is not final: status={game.get('gameStatus')!r}")

    expected_date = str(selected.get("game_date") or "").strip()
    game_code = str(game.get("gameCode") or "").strip()
    source_date = game_code[:8] if re.match(r"^\d{8}/", game_code) else ""
    if expected_date and source_date and source_date != expected_date.replace("-", ""):
        raise ValueError(
            f"official game date mismatch: expected={expected_date} source={source_date}"
        )

    home = game.get("homeTeam") if isinstance(game.get("homeTeam"), dict) else {}
    away = game.get("awayTeam") if isinstance(game.get("awayTeam"), dict) else {}
    expected_home = str(selected.get("home_team_abbr") or "").strip()
    expected_away = str(selected.get("away_team_abbr") or "").strip()
    source_home = str(home.get("teamTricode") or "").strip()
    source_away = str(away.get("teamTricode") or "").strip()
    if (source_home, source_away) != (expected_home, expected_away):
        raise ValueError(
            "official team mismatch: "
            f"expected={expected_away}@{expected_home} "
            f"source={source_away}@{source_home}"
        )

    player_rows: list[dict[str, Any]] = []
    for side, team in (("home", home), ("away", away)):
        team_abbr = str(team.get("teamTricode") or "").strip()
        players = team.get("players") if isinstance(team.get("players"), list) else []
        for player in players:
            if not isinstance(player, dict):
                continue
            player_id = str(player.get("personId") or "").strip()
            if not re.fullmatch(r"\d+", player_id):
                raise ValueError(
                    f"official player row has invalid personId for {official_game_id}: "
                    f"{player.get('personId')!r}"
                )
            label, minutes, played, starter, status, reason = classify_player(player)
            if label not in LABELS:
                raise ValueError(f"unrecognized participation label {label!r}")
            player_rows.append({
                "historical_game_id": str(selected.get("historical_game_id") or "").strip(),
                "official_game_id": official_game_id,
                "game_date": expected_date,
                "team_abbr": team_abbr,
                "home_away": side,
                "player_id": player_id,
                "participation_label": label,
                "actual_minutes": minutes,
                "actual_played": played,
                "actual_starter": starter,
                "official_status": status,
                "not_playing_reason_code": reason,
            })

    if not player_rows:
        raise ValueError("official final game contains no player rows")
    return game, player_rows


def run(
    selected_rows: list[dict[str, str]],
    output_dir: Path,
    *,
    url_template: str = DEFAULT_URL_TEMPLATE,
    fetcher: Callable[[str], tuple[dict[str, Any], dict[str, Any]]] = fetch_json,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    selected_by_id: dict[str, dict[str, str]] = {}
    duplicate_selected_games = 0
    invalid_selected_games = 0
    for row in selected_rows:
        historical_id = str(row.get("historical_game_id") or "").strip()
        if not historical_id:
            invalid_selected_games += 1
            continue
        if historical_id in selected_by_id:
            duplicate_selected_games += 1
        selected_by_id[historical_id] = row

    labels: list[dict[str, Any]] = []
    source_index: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    duplicate_game_player_rows = 0
    seen_game_players: set[tuple[str, str]] = set()
    team_mismatches = 0
    final_status_errors = 0
    invalid_player_rows = 0
    label_counts: Counter[str] = Counter()
    official_status_counts: Counter[str] = Counter()
    reason_counts: Counter[str] = Counter()

    for historical_id, selected in sorted(
        selected_by_id.items(),
        key=lambda item: (
            str(item[1].get("game_date") or ""),
            item[0],
        ),
    ):
        official_game_id = normalize_official_game_id(historical_id)
        source_url = url_template.format(official_game_id=official_game_id)
        index_row: dict[str, Any] = {
            "historical_game_id": historical_id,
            "official_game_id": official_game_id,
            "game_date": str(selected.get("game_date") or "").strip(),
            "home_team_abbr": str(selected.get("home_team_abbr") or "").strip(),
            "away_team_abbr": str(selected.get("away_team_abbr") or "").strip(),
            "source_provider": SOURCE_PROVIDER,
            "source_url": source_url,
            "source_success": 0,
            "source_http_status": "",
            "source_bytes": "",
            "source_sha256": "",
            "retrieved_at": "",
            "source_attempts": "",
            "official_player_rows": 0,
            "error_type": "",
            "error": "",
        }
        try:
            payload, source_meta = fetcher(source_url)
            game, game_rows = validate_game_payload(
                selected,
                payload,
                official_game_id,
            )
            index_row.update({
                "source_success": 1,
                "source_http_status": source_meta.get("http_status", 200),
                "source_bytes": source_meta.get("source_bytes", ""),
                "source_sha256": source_meta.get("source_sha256", ""),
                "retrieved_at": source_meta.get("retrieved_at", utc_now()),
                "source_attempts": source_meta.get("attempts", 1),
                "official_player_rows": len(game_rows),
            })
            for row in game_rows:
                key = (historical_id, str(row["player_id"]))
                if key in seen_game_players:
                    duplicate_game_player_rows += 1
                    continue
                seen_game_players.add(key)
                if row["team_abbr"] not in {
                    index_row["home_team_abbr"],
                    index_row["away_team_abbr"],
                }:
                    team_mismatches += 1
                if not re.fullmatch(r"\d+", str(row["player_id"])):
                    invalid_player_rows += 1
                row.update({
                    "source_provider": SOURCE_PROVIDER,
                    "source_url": source_url,
                    "source_sha256": index_row["source_sha256"],
                    "retrieved_at": index_row["retrieved_at"],
                    "label_version": VERSION,
                })
                labels.append(row)
                label_counts[str(row["participation_label"])] += 1
                official_status_counts[str(row["official_status"] or "BLANK")] += 1
                reason_counts[str(row["not_playing_reason_code"] or "BLANK")] += 1
            if int(game.get("gameStatus") or 0) != 3:
                final_status_errors += 1
        except Exception as exc:
            index_row["error_type"] = type(exc).__name__
            index_row["error"] = str(exc)
            failures.append({
                "historical_game_id": historical_id,
                "official_game_id": official_game_id,
                "source_url": source_url,
                "error_type": type(exc).__name__,
                "error": str(exc),
            })
        source_index.append(index_row)

    labels.sort(
        key=lambda row: (
            str(row["game_date"]),
            str(row["historical_game_id"]),
            str(row["team_abbr"]),
            str(row["player_id"]),
        )
    )
    source_index.sort(
        key=lambda row: (
            str(row["game_date"]),
            str(row["historical_game_id"]),
        )
    )
    successful_games = sum(int(row["source_success"]) for row in source_index)
    requested_games = len(selected_by_id)
    source_coverage = successful_games / requested_games if requested_games else 0.0
    unknown_rows = label_counts["UNKNOWN"]
    unknown_rate = unknown_rows / len(labels) if labels else 1.0
    structural_ready = (
        requested_games > 0
        and duplicate_selected_games == 0
        and invalid_selected_games == 0
        and successful_games == requested_games
        and duplicate_game_player_rows == 0
        and team_mismatches == 0
        and final_status_errors == 0
        and invalid_player_rows == 0
    )

    label_fields = [
        "historical_game_id",
        "official_game_id",
        "game_date",
        "team_abbr",
        "home_away",
        "player_id",
        "participation_label",
        "actual_minutes",
        "actual_played",
        "actual_starter",
        "official_status",
        "not_playing_reason_code",
        "source_provider",
        "source_url",
        "source_sha256",
        "retrieved_at",
        "label_version",
    ]
    source_fields = [
        "historical_game_id",
        "official_game_id",
        "game_date",
        "home_team_abbr",
        "away_team_abbr",
        "source_provider",
        "source_url",
        "source_success",
        "source_http_status",
        "source_bytes",
        "source_sha256",
        "retrieved_at",
        "source_attempts",
        "official_player_rows",
        "error_type",
        "error",
    ]
    write_csv(output_dir / "official-player-participation-labels.csv", labels, label_fields)
    write_csv(
        output_dir / "official-player-participation-source-index.csv",
        source_index,
        source_fields,
    )

    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "source": {
            "provider": SOURCE_PROVIDER,
            "url_template": url_template,
            "official_game_status_required": 3,
        },
        "coverage": {
            "requested_selected_games": requested_games,
            "successful_official_games": successful_games,
            "failed_official_games": len(failures),
            "official_game_source_coverage": round(source_coverage, 6),
            "official_player_rows": len(labels),
            "unique_player_ids": len({str(row["player_id"]) for row in labels}),
            "participation_label_counts": dict(sorted(label_counts.items())),
            "official_status_counts": dict(sorted(official_status_counts.items())),
            "not_playing_reason_code_counts": dict(sorted(reason_counts.items())),
            "unknown_player_rows": unknown_rows,
            "unknown_player_row_rate": round(unknown_rate, 6),
        },
        "quality": {
            "duplicate_selected_games": duplicate_selected_games,
            "invalid_selected_games": invalid_selected_games,
            "duplicate_official_game_player_rows": duplicate_game_player_rows,
            "team_mismatches": team_mismatches,
            "final_game_status_errors": final_status_errors,
            "invalid_player_rows": invalid_player_rows,
            "failed_game_examples": failures[:50],
            "player_names_retained": False,
            "not_playing_descriptions_retained": False,
            "raw_json_retained": False,
        },
        "decision": {
            "ready_for_player_participation_join": structural_ready,
            "ready_for_expected_minutes_accuracy_audit_v2": False,
            "ready_for_injury_feature_walk_forward_holdout": False,
            "ready_for_model_training": False,
            "ready_for_probability_adjustment": False,
            "ready_for_betting_edge_claim": False,
            "reason": (
                "All selected games were imported from the official final-game source "
                "without structural conflicts."
                if structural_ready
                else "The official participation source failed one or more game-level "
                "or structural gates."
            ),
        },
        "guardrails": {
            "missing_game_source_is_dnp": False,
            "missing_player_row_is_dnp": False,
            "unknown_player_state_is_zero_minutes": False,
            "target_game_labels_are_evaluation_only": True,
            "player_level_output_is_temporary": True,
        },
    }
    (output_dir / "official-player-participation-import-report.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def self_test(output_dir: Path) -> None:
    selected = [{
        "historical_game_id": "22300001",
        "game_date": "2023-10-24",
        "home_team_abbr": "AAA",
        "away_team_abbr": "BBB",
    }]
    payload = {
        "meta": {"code": 200},
        "game": {
            "gameId": "0022300001",
            "gameCode": "20231024/BBBAAA",
            "gameStatus": 3,
            "homeTeam": {
                "teamTricode": "AAA",
                "players": [
                    {
                        "personId": 1,
                        "status": "ACTIVE",
                        "played": "1",
                        "starter": "1",
                        "statistics": {"minutes": "PT31M30.00S"},
                    },
                    {
                        "personId": 2,
                        "status": "ACTIVE",
                        "played": "0",
                        "starter": "0",
                        "notPlayingReason": "DNP_COACH",
                        "statistics": {"minutes": "PT00M00.00S"},
                    },
                ],
            },
            "awayTeam": {
                "teamTricode": "BBB",
                "players": [
                    {
                        "personId": 3,
                        "status": "INACTIVE",
                        "played": "0",
                        "starter": "0",
                        "notPlayingReason": "INACTIVE_INJURY",
                        "statistics": {"minutes": "PT00M00.00S"},
                    },
                    {
                        "personId": 4,
                        "status": "ACTIVE",
                        "played": "0",
                        "starter": "0",
                        "statistics": {"minutes": "PT00M00.00S"},
                    },
                ],
            },
        },
    }

    def fake_fetcher(url: str):
        assert url.endswith("boxscore_0022300001.json")
        encoded = json.dumps(payload, sort_keys=True).encode()
        return payload, {
            "retrieved_at": "2026-07-18T00:00:00Z",
            "source_bytes": len(encoded),
            "source_sha256": hashlib.sha256(encoded).hexdigest(),
            "http_status": 200,
            "attempts": 1,
        }

    report = run(selected, output_dir, fetcher=fake_fetcher)
    assert report["decision"]["ready_for_player_participation_join"] is True, report
    assert report["coverage"]["participation_label_counts"] == {
        "EXPLICIT_DNP": 1,
        "INACTIVE_OR_NOT_DRESSED": 1,
        "PLAYED": 1,
        "UNKNOWN": 1,
    }, report
    rows = read_csv(output_dir / "official-player-participation-labels.csv")
    assert {row["participation_label"] for row in rows} == LABELS, rows
    assert all("name" not in key.lower() for key in rows[0]), rows[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selected-games", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--url-template", default=DEFAULT_URL_TEMPLATE)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test(args.output_dir)
        print("official player participation importer self-test passed")
        return
    if not args.selected_games:
        parser.error("--selected-games is required")
    report = run(
        read_csv(args.selected_games),
        args.output_dir,
        url_template=args.url_template,
    )
    print(json.dumps(report["decision"], indent=2))
    if not report["decision"]["ready_for_player_participation_join"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
