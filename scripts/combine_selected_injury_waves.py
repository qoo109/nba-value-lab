#!/usr/bin/env python3
"""Combine independently selected injury-feature waves into one deduplicated game panel.

Each input must already apply the same frozen latest-feature-ready-at-or-before-T-60 policy.
If a game appears in multiple waves, the later eligible observed_at is retained. Mismatched game
identity, teams, dates, policy, or eligibility blocks readiness rather than silently choosing a row.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "combined-selected-injury-waves-v1"
PRIMARY_POLICY = "latest_feature_ready_at_or_before_t60"


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


def parse_timestamp(value: Any) -> datetime:
    text = str(value or "").strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"timestamp must include timezone: {value!r}")
    return parsed.astimezone(timezone.utc)


def as_int(value: Any, default: int = 0) -> int:
    text = str(value or "").strip()
    return default if not text else int(float(text))


def validate_wave(
    name: str,
    rows: list[dict[str, str]],
    audit: dict[str, Any],
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    decision = audit.get("decision", {})
    coverage = audit.get("coverage", {})
    quality = audit.get("quality", {})
    if decision.get("ready_for_wave1_selected_panel_research") is not True:
        errors.append(f"{name} upstream selected-panel audit is not ready")
    if decision.get("ready_for_model_training") is not False:
        errors.append(f"{name} unexpectedly reports model-training readiness")
    if decision.get("ready_for_betting_edge_claim") is not False:
        errors.append(f"{name} unexpectedly reports betting-edge readiness")
    expected_rows = as_int(coverage.get("selected_independent_games"), -1)
    if expected_rows != len(rows):
        errors.append(f"{name} selected CSV rows={len(rows)} but audit={expected_rows}")

    ids = [str(row.get("historical_game_id", "")).strip() for row in rows]
    if any(not value for value in ids):
        errors.append(f"{name} has blank historical_game_id")
    duplicate_ids = len(ids) - len(set(ids))
    if duplicate_ids:
        errors.append(f"{name} has {duplicate_ids} duplicate historical_game_id rows")
    if as_int(quality.get("duplicate_selected_games")) != 0:
        errors.append(f"{name} audit reports duplicate selected games")

    for index, row in enumerate(rows, 2):
        if str(row.get("selection_policy", "")).strip() != PRIMARY_POLICY:
            errors.append(f"{name} row {index} selection policy differs from frozen primary")
        if as_int(row.get("selection_minimum_minutes_before_tip"), -1) != 60:
            errors.append(f"{name} row {index} T-60 threshold mismatch")
        if as_int(row.get("selection_fallback_used"), -1) != 0:
            errors.append(f"{name} row {index} used fallback")
        if as_int(row.get("matchup_snapshot_complete"), -1) != 1:
            errors.append(f"{name} row {index} snapshot incomplete")
        if as_int(row.get("matchup_feature_available"), -1) != 1:
            errors.append(f"{name} row {index} feature unavailable")
        try:
            observed = parse_timestamp(row.get("observed_at"))
            commence = parse_timestamp(row.get("commence_time"))
            if observed >= commence:
                errors.append(f"{name} row {index} is not pregame")
            minutes = (commence - observed).total_seconds() / 60.0
            if minutes < 60.0:
                errors.append(f"{name} row {index} is inside T-60")
        except ValueError as exc:
            errors.append(f"{name} row {index}: {exc}")

    if as_int(audit.get("sample_size", {}).get("minimum_activation_independent_games"), 100) != 100:
        warnings.append(f"{name} upstream minimum sample gate is not 100")
    return errors, warnings


def combine(
    waves: list[tuple[str, list[dict[str, str]], dict[str, Any]]],
    output_dir: Path,
) -> dict[str, Any]:
    if not waves:
        raise ValueError("at least one wave is required")
    all_errors: list[str] = []
    all_warnings: list[str] = []
    grouped: dict[str, list[tuple[str, dict[str, str]]]] = defaultdict(list)
    input_counts: dict[str, int] = {}

    for name, rows, audit in waves:
        errors, warnings = validate_wave(name, rows, audit)
        all_errors.extend(errors)
        all_warnings.extend(warnings)
        input_counts[name] = len(rows)
        for row in rows:
            game_id = str(row.get("historical_game_id", "")).strip()
            if game_id:
                grouped[game_id].append((name, row))

    combined_rows: list[dict[str, Any]] = []
    duplicate_games = 0
    duplicate_candidate_rows = 0
    identity_conflicts = 0
    policy_conflicts = 0
    selection_audit: list[dict[str, Any]] = []
    selected_source_counts: Counter[str] = Counter()

    for game_id, candidates in sorted(
        grouped.items(),
        key=lambda item: (
            min(str(row.get("game_date", "")) for _, row in item[1]),
            item[0],
        ),
    ):
        duplicate_candidate_rows += max(len(candidates) - 1, 0)
        duplicate_games += int(len(candidates) > 1)
        identities = {
            (
                str(row.get("game_date", "")).strip(),
                str(row.get("home_team_abbr", "")).strip(),
                str(row.get("away_team_abbr", "")).strip(),
                str(row.get("commence_time", "")).strip(),
            )
            for _, row in candidates
        }
        policies = {
            (
                str(row.get("selection_policy", "")).strip(),
                as_int(row.get("selection_minimum_minutes_before_tip"), -1),
                as_int(row.get("selection_fallback_used"), -1),
            )
            for _, row in candidates
        }
        if len(identities) != 1:
            identity_conflicts += 1
            all_errors.append(f"game {game_id} has conflicting date/team/commence identity across waves")
            continue
        if policies != {(PRIMARY_POLICY, 60, 0)}:
            policy_conflicts += 1
            all_errors.append(f"game {game_id} has conflicting or invalid selection policy across waves")
            continue

        ordered = sorted(
            candidates,
            key=lambda item: (parse_timestamp(item[1]["observed_at"]), item[0]),
        )
        source_wave, selected = ordered[-1]
        output = dict(selected)
        output["source_wave"] = source_wave
        output["candidate_wave_count"] = len(candidates)
        output["combined_selection_version"] = VERSION
        combined_rows.append(output)
        selected_source_counts[source_wave] += 1
        selection_audit.append({
            "historical_game_id": game_id,
            "candidate_waves": ",".join(name for name, _ in ordered),
            "candidate_count": len(candidates),
            "selected_wave": source_wave,
            "selected_observed_at": str(selected.get("observed_at", "")),
            "tie_break_rule": "latest_eligible_observed_at_then_wave_name",
        })

    combined_ids = [str(row["historical_game_id"]) for row in combined_rows]
    duplicate_output_games = len(combined_ids) - len(set(combined_ids))
    combined_rows.sort(key=lambda row: (str(row.get("game_date", "")), str(row.get("historical_game_id", ""))))
    minimum_gate = 100
    reliability_gate = 300
    ideal_gate = 500
    structural_ready = (
        not all_errors
        and bool(combined_rows)
        and duplicate_output_games == 0
        and identity_conflicts == 0
        and policy_conflicts == 0
    )
    minimum_met = structural_ready and len(combined_rows) >= minimum_gate

    output_dir.mkdir(parents=True, exist_ok=True)
    fields = list(combined_rows[0]) if combined_rows else []
    write_csv(output_dir / "combined-selected-matchup-injury-burden.csv", combined_rows, fields)
    write_csv(
        output_dir / "combined-selected-wave-audit.csv",
        selection_audit,
        list(selection_audit[0]) if selection_audit else [],
    )
    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "input_waves": input_counts,
        "coverage": {
            "raw_selected_rows": sum(input_counts.values()),
            "unique_games_before_conflict_exclusion": len(grouped),
            "duplicate_games_across_waves": duplicate_games,
            "duplicate_candidate_rows": duplicate_candidate_rows,
            "combined_independent_games": len(combined_rows),
            "selected_source_wave_counts": dict(sorted(selected_source_counts.items())),
        },
        "quality": {
            "validation_errors": len(all_errors),
            "validation_error_examples": all_errors[:50],
            "validation_warnings": len(all_warnings),
            "validation_warning_examples": all_warnings[:50],
            "game_identity_conflicts": identity_conflicts,
            "selection_policy_conflicts": policy_conflicts,
            "duplicate_output_games": duplicate_output_games,
            "outcomes_or_market_prices_used": False,
            "latest_eligible_observed_at_tie_break_predeclared": True,
        },
        "sample_size": {
            "minimum_expected_minutes_accuracy_audit_games": minimum_gate,
            "initial_reliability_games": reliability_gate,
            "ideal_games": ideal_gate,
            "minimum_gate_met": minimum_met,
            "initial_reliability_met": structural_ready and len(combined_rows) >= reliability_gate,
            "ideal_gate_met": structural_ready and len(combined_rows) >= ideal_gate,
        },
        "decision": {
            "ready_for_combined_selected_panel_research": structural_ready,
            "ready_for_expected_minutes_accuracy_audit": minimum_met,
            "ready_for_injury_feature_walk_forward_holdout": False,
            "ready_for_model_training": False,
            "ready_for_probability_adjustment": False,
            "ready_for_betting_edge_claim": False,
            "reason": (
                "The deduplicated combined selected panel passed structural QA and reached the Expected Minutes Accuracy Audit gate."
                if minimum_met
                else "The combined panel passed structural QA but did not reach the Expected Minutes Accuracy Audit gate."
                if structural_ready
                else "The combined selected panel failed one or more structural gates."
            ),
        },
        "guardrails": {
            "deduplication_key": "historical_game_id",
            "duplicate_game_selection": "latest eligible observed_at, then wave name",
            "multiple_publication_times_are_independent_games": False,
            "minimum_gate_directly_enables_holdout": False,
            "expected_minutes_accuracy_audit_required_before_holdout": True,
        },
    }
    (output_dir / "combined-selected-injury-waves-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def self_test(output_dir: Path) -> None:
    base = {
        "game_date": "2024-01-01",
        "commence_time": "2024-01-02T00:00:00Z",
        "home_team_abbr": "AAA",
        "away_team_abbr": "BBB",
        "matchup_snapshot_complete": "1",
        "matchup_feature_available": "1",
        "selection_policy": PRIMARY_POLICY,
        "selection_minimum_minutes_before_tip": "60",
        "selection_fallback_used": "0",
    }
    wave1 = [
        {**base, "historical_game_id": "g1", "observed_at": "2024-01-01T20:00:00Z"},
        {**base, "historical_game_id": "g2", "observed_at": "2024-01-01T19:00:00Z"},
    ]
    wave2 = [
        {**base, "historical_game_id": "g2", "observed_at": "2024-01-01T21:00:00Z"},
        {**base, "historical_game_id": "g3", "observed_at": "2024-01-01T18:00:00Z"},
    ]
    def audit_for(rows):
        return {
            "coverage": {"selected_independent_games": len(rows)},
            "quality": {"duplicate_selected_games": 0},
            "sample_size": {"minimum_activation_independent_games": 100},
            "decision": {
                "ready_for_wave1_selected_panel_research": True,
                "ready_for_model_training": False,
                "ready_for_betting_edge_claim": False,
            },
        }
    report = combine(
        [("wave1", wave1, audit_for(wave1)), ("wave2", wave2, audit_for(wave2))],
        output_dir,
    )
    assert report["decision"]["ready_for_combined_selected_panel_research"] is True, report
    assert report["coverage"]["combined_independent_games"] == 3, report
    assert report["coverage"]["duplicate_games_across_waves"] == 1, report
    rows = read_csv(output_dir / "combined-selected-matchup-injury-burden.csv")
    g2 = next(row for row in rows if row["historical_game_id"] == "g2")
    assert g2["source_wave"] == "wave2", g2


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wave", action="append", nargs=3, metavar=("NAME", "SELECTED_CSV", "AUDIT_JSON"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("combined selected injury waves self-test passed")
        return
    if not args.wave or len(args.wave) < 2:
        parser.error("at least two --wave NAME SELECTED_CSV AUDIT_JSON groups are required")
    waves = [
        (name, read_csv(Path(csv_path)), read_json(Path(audit_path)))
        for name, csv_path, audit_path in args.wave
    ]
    report = combine(waves, args.output_dir)
    print(json.dumps(report["decision"], indent=2))
    if not report["decision"]["ready_for_combined_selected_panel_research"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
