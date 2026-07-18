#!/usr/bin/env python3
"""Create an evaluation-safe participation label file by excluding verified roster transitions.

Raw official labels remain authoritative source evidence. A row is excluded only when a frozen,
deidentified transition contract matches its game/player token, official team, label, played flag,
and an upstream deterministic identity row confirms the expected pregame team.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "recognized-roster-transition-filter-v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def player_token(game_id: str, player_id: str) -> str:
    return hashlib.sha256(f"{game_id}|{player_id}".encode("utf-8")).hexdigest()


def run(
    official_rows: list[dict[str, str]],
    identity_inputs: list[tuple[str, list[dict[str, str]]]],
    policy: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    rules = list(policy.get("recognized_roster_transitions", []))
    configured_tokens = {
        str(rule.get("player_token_sha256") or "").strip()
        for rule in rules
        if str(rule.get("player_token_sha256") or "").strip()
    }
    duplicate_rule_tokens = len(configured_tokens) != len(rules)

    identity_matches: dict[tuple[str, str], list[dict[str, str]]] = {}
    for wave, rows in identity_inputs:
        for row in rows:
            game_id = str(row.get("historical_game_id") or "").strip()
            player_id = str(row.get("player_id") or "").strip()
            if not game_id or not player_id:
                continue
            token = player_token(game_id, player_id)
            identity_matches.setdefault((game_id, token), []).append({
                "source_wave": wave,
                "team_abbr": str(row.get("team_abbr") or "").strip(),
            })

    excluded_keys: set[tuple[str, str]] = set()
    rule_results: list[dict[str, Any]] = []
    validation_errors: list[str] = []
    for rule in rules:
        transition_id = str(rule.get("transition_id") or "").strip()
        game_id = str(rule.get("historical_game_id") or "").strip()
        game_date = str(rule.get("game_date") or "").strip()
        expected_team = str(rule.get("expected_team_abbr") or "").strip()
        official_team = str(rule.get("official_team_abbr") or "").strip()
        token = str(rule.get("player_token_sha256") or "").strip()
        required_label = str(rule.get("required_participation_label") or "").strip()
        required_played = int(rule.get("required_actual_played", 0))
        expected_rows = int(rule.get("expected_rows", 0))
        matching_official = []
        for row in official_rows:
            row_game = str(row.get("historical_game_id") or "").strip()
            row_player = str(row.get("player_id") or "").strip()
            if row_game == game_id and row_player and player_token(row_game, row_player) == token:
                matching_official.append(row)
        matching_identity = identity_matches.get((game_id, token), [])
        official_checks = {
            "transition_id_present": bool(transition_id),
            "game_date_present": bool(game_date),
            "token_is_sha256": len(token) == 64 and all(c in "0123456789abcdef" for c in token),
            "official_row_count_exact": len(matching_official) == expected_rows,
            "official_team_exact": bool(matching_official) and all(
                str(row.get("team_abbr") or "").strip() == official_team
                for row in matching_official
            ),
            "official_label_exact": bool(matching_official) and all(
                str(row.get("participation_label") or "").strip() == required_label
                for row in matching_official
            ),
            "official_played_exact": bool(matching_official) and all(
                int(float(str(row.get("actual_played") or "0"))) == required_played
                for row in matching_official
            ),
            "official_game_date_exact": bool(matching_official) and all(
                str(row.get("game_date") or "").strip() == game_date
                for row in matching_official
            ),
            "expected_identity_team_present": any(
                row["team_abbr"] == expected_team for row in matching_identity
            ),
            "expected_identity_wave_present": any(
                row["source_wave"] == str(rule.get("source_wave") or row["source_wave"])
                and row["team_abbr"] == expected_team
                for row in matching_identity
            ),
            "opponent_team_transition": expected_team != official_team,
            "handling_is_exclusion": str(rule.get("handling") or "").strip()
            == "exclude_official_opponent_team_row_from_target_team_evaluation_join",
            "evidence_present": len(rule.get("evidence", [])) >= 1,
        }
        passed = all(official_checks.values())
        if passed:
            for row in matching_official:
                excluded_keys.add((
                    str(row.get("historical_game_id") or "").strip(),
                    str(row.get("player_id") or "").strip(),
                ))
        else:
            validation_errors.append(transition_id or f"rule-{len(rule_results)+1}")
        rule_results.append({
            "transition_id": transition_id,
            "historical_game_id": game_id,
            "game_date": game_date,
            "expected_team_abbr": expected_team,
            "official_team_abbr": official_team,
            "expected_rows": expected_rows,
            "matched_official_rows": len(matching_official),
            "matching_identity_rows": len(matching_identity),
            "checks": official_checks,
            "passed": passed,
        })

    evaluation_rows = [
        row for row in official_rows
        if (
            str(row.get("historical_game_id") or "").strip(),
            str(row.get("player_id") or "").strip(),
        ) not in excluded_keys
    ]
    recognized_rows = len(official_rows) - len(evaluation_rows)
    required_recognized_rows = int(
        policy.get("structural_gates", {}).get("recognized_roster_transition_rows", 0)
    )
    ready = (
        not duplicate_rule_tokens
        and not validation_errors
        and recognized_rows == required_recognized_rows
        and recognized_rows == sum(int(rule.get("expected_rows", 0)) for rule in rules)
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    fields = list(official_rows[0]) if official_rows else []
    write_csv(
        output_dir / "evaluation-player-participation-labels.csv",
        evaluation_rows,
        fields,
    )
    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "coverage": {
            "raw_official_label_rows": len(official_rows),
            "evaluation_label_rows": len(evaluation_rows),
            "configured_transition_contracts": len(rules),
            "recognized_roster_transition_rows": recognized_rows,
            "required_recognized_roster_transition_rows": required_recognized_rows,
        },
        "quality": {
            "duplicate_rule_tokens": duplicate_rule_tokens,
            "validation_errors": validation_errors,
            "rule_results": rule_results,
            "player_names_retained": False,
            "player_ids_retained_in_report": False,
            "accuracy_metrics_used": False,
            "sample_thresholds_changed": False,
            "unrecognized_team_mismatches_allowed": False,
        },
        "decision": {
            "ready_for_exact_team_evaluation_join": ready,
            "ready_for_accuracy_audit_execution": False,
            "ready_for_injury_holdout": False,
            "ready_for_model_training": False,
            "ready_for_betting_edge_claim": False,
        },
        "guardrails": {
            "raw_official_source_is_modified": False,
            "recognized_rows_are_excluded_from_evaluation_join": True,
            "recognized_rows_are_counted_as_played": False,
            "recognized_rows_are_counted_as_dnp": False,
            "recognized_rows_are_counted_as_zero_minutes": False,
            "all_other_team_mismatches_remain_fatal": True,
        },
    }
    (output_dir / "recognized-roster-transition-filter-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def self_test(output_dir: Path) -> None:
    game_id = "g1"
    player_id = "p1"
    token = player_token(game_id, player_id)
    labels = [{
        "historical_game_id": game_id,
        "game_date": "2024-01-01",
        "team_abbr": "BBB",
        "player_id": player_id,
        "participation_label": "INACTIVE_OR_NOT_DRESSED",
        "actual_played": "0",
    }, {
        "historical_game_id": game_id,
        "game_date": "2024-01-01",
        "team_abbr": "AAA",
        "player_id": "p2",
        "participation_label": "PLAYED",
        "actual_played": "1",
    }]
    identities = [("wave1", [{
        "historical_game_id": game_id,
        "team_abbr": "AAA",
        "player_id": player_id,
    }])]
    policy = {
        "structural_gates": {"recognized_roster_transition_rows": 1},
        "recognized_roster_transitions": [{
            "transition_id": "t1",
            "historical_game_id": game_id,
            "game_date": "2024-01-01",
            "source_wave": "wave1",
            "expected_team_abbr": "AAA",
            "official_team_abbr": "BBB",
            "player_token_sha256": token,
            "required_participation_label": "INACTIVE_OR_NOT_DRESSED",
            "required_actual_played": 0,
            "expected_rows": 1,
            "handling": "exclude_official_opponent_team_row_from_target_team_evaluation_join",
            "evidence": [{"provider": "official", "url": "https://example.invalid"}],
        }],
    }
    report = run(labels, identities, policy, output_dir)
    assert report["decision"]["ready_for_exact_team_evaluation_join"] is True, report
    assert report["coverage"]["recognized_roster_transition_rows"] == 1, report
    remaining = read_csv(output_dir / "evaluation-player-participation-labels.csv")
    assert len(remaining) == 1 and remaining[0]["player_id"] == "p2", remaining


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--official-labels", type=Path)
    parser.add_argument("--identity-map", nargs=2, action="append", metavar=("WAVE", "CSV"))
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("recognized roster transition filter self-test passed")
        return
    if args.official_labels is None or not args.identity_map or args.policy is None:
        parser.error("--official-labels, --identity-map and --policy are required")
    report = run(
        read_csv(args.official_labels),
        [(wave, read_csv(Path(path))) for wave, path in args.identity_map],
        read_json(args.policy),
        args.output_dir,
    )
    print(json.dumps(report, indent=2))
    if not report["decision"]["ready_for_exact_team_evaluation_join"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
