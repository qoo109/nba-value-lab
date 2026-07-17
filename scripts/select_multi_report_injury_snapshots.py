#!/usr/bin/env python3
"""Apply a predeclared, outcome-blind snapshot-selection policy.

The primary output contains at most one row per historical game. Multiple publication
snapshots from one game remain diagnostic observations and never become independent
holdout samples.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "injury-snapshot-selection-v1"


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


def as_bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes"}


def as_float(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    return float(text)


def parse_timestamp(value: Any) -> datetime:
    text = str(value or "").strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"timestamp must include timezone: {value!r}")
    return parsed.astimezone(timezone.utc)


def load_policy(path: Path) -> dict[str, Any]:
    policy = json.loads(path.read_text(encoding="utf-8"))
    if policy.get("schema_version") != "injury-snapshot-selection-policy-v1":
        raise ValueError("unsupported snapshot-selection policy schema")
    primary = policy.get("primary_policy")
    if not isinstance(primary, dict):
        raise ValueError("primary_policy is required")
    required = {
        "name", "minimum_minutes_before_tip", "require_matchup_snapshot_complete",
        "require_matchup_feature_available", "fallback", "tie_breaker",
    }
    missing = sorted(required - set(primary))
    if missing:
        raise ValueError(f"primary_policy missing keys: {missing}")
    if primary["fallback"] != "no_selection":
        raise ValueError("v1 only permits fallback=no_selection")
    if primary["tie_breaker"] != "latest_observed_at":
        raise ValueError("v1 only permits tie_breaker=latest_observed_at")
    return policy


def eligible(row: dict[str, str], rule: dict[str, Any]) -> tuple[bool, str]:
    minutes = as_float(row.get("minutes_before_tip"))
    if minutes is None:
        return False, "missing_minutes_before_tip"
    if minutes < float(rule["minimum_minutes_before_tip"]):
        return False, "inside_cutoff_window"
    if bool(rule["require_matchup_snapshot_complete"]) and not as_bool(row.get("matchup_snapshot_complete")):
        return False, "incomplete_snapshot"
    if bool(rule["require_matchup_feature_available"]) and not as_bool(row.get("matchup_feature_available")):
        return False, "feature_unavailable"
    observed = parse_timestamp(row.get("observed_at"))
    commence = parse_timestamp(row.get("commence_time"))
    if observed >= commence:
        return False, "not_pregame"
    return True, "eligible"


def select(
    long_rows: list[dict[str, str]],
    policy: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    primary = policy["primary_policy"]
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    duplicate_game_observed_rows = 0
    seen: set[tuple[str, str]] = set()
    invalid_rows = 0
    for row in long_rows:
        game_id = str(row.get("historical_game_id", "")).strip()
        observed = str(row.get("observed_at", "")).strip()
        if not game_id or not observed:
            invalid_rows += 1
            continue
        key = (game_id, observed)
        if key in seen:
            duplicate_game_observed_rows += 1
        seen.add(key)
        groups[game_id].append(row)

    selected: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    rejection_counts: Counter[str] = Counter()
    games_without_selection = 0

    for game_id, rows in sorted(groups.items()):
        candidates: list[dict[str, str]] = []
        row_reasons: dict[str, str] = {}
        for row in rows:
            try:
                is_eligible, reason = eligible(row, primary)
            except (ValueError, TypeError):
                is_eligible, reason = False, "invalid_timestamp_or_numeric"
            row_reasons[str(row.get("observed_at", ""))] = reason
            if is_eligible:
                candidates.append(row)
        chosen: dict[str, str] | None = None
        if candidates:
            chosen = max(candidates, key=lambda row: parse_timestamp(row["observed_at"]))
            output = dict(chosen)
            output["selection_policy"] = primary["name"]
            output["selection_minimum_minutes_before_tip"] = primary["minimum_minutes_before_tip"]
            output["selection_fallback_used"] = 0
            selected.append(output)
        else:
            games_without_selection += 1
            reasons = Counter(row_reasons.values())
            rejection_counts[reasons.most_common(1)[0][0] if reasons else "no_rows"] += 1

        chosen_observed = str(chosen.get("observed_at", "")) if chosen else ""
        for row in sorted(rows, key=lambda item: str(item.get("observed_at", ""))):
            reason = row_reasons.get(str(row.get("observed_at", "")), "not_evaluated")
            audit.append({
                "historical_game_id": game_id,
                "game_date": row.get("game_date", ""),
                "observed_at": row.get("observed_at", ""),
                "commence_time": row.get("commence_time", ""),
                "minutes_before_tip": row.get("minutes_before_tip", ""),
                "matchup_snapshot_complete": row.get("matchup_snapshot_complete", ""),
                "matchup_feature_available": row.get("matchup_feature_available", ""),
                "primary_eligible": int(reason == "eligible"),
                "primary_rejection_reason": "" if reason == "eligible" else reason,
                "selected_primary_snapshot": int(str(row.get("observed_at", "")) == chosen_observed),
                "selection_policy": primary["name"],
            })

    diagnostic_results = {}
    for rule in policy.get("diagnostic_policies", []):
        selected_games = 0
        for rows in groups.values():
            qualifying = []
            for row in rows:
                try:
                    if eligible(row, rule)[0]:
                        qualifying.append(row)
                except (ValueError, TypeError):
                    continue
            selected_games += int(bool(qualifying))
        diagnostic_results[str(rule["name"])] = {
            "independent_games_selected": selected_games,
            "research_only": True,
            "may_not_replace_primary_policy_after_outcome_review": True,
        }

    output_dir.mkdir(parents=True, exist_ok=True)
    selected_fields = list(selected[0]) if selected else (
        list(long_rows[0]) + [
            "selection_policy", "selection_minimum_minutes_before_tip", "selection_fallback_used"
        ] if long_rows else []
    )
    audit_fields = list(audit[0]) if audit else []
    write_csv(output_dir / "selected-matchup-injury-burden.csv", selected, selected_fields)
    write_csv(output_dir / "snapshot-selection-audit.csv", audit, audit_fields)

    selected_game_ids = [str(row["historical_game_id"]) for row in selected]
    duplicate_selected_games = len(selected_game_ids) - len(set(selected_game_ids))
    selected_count = len(set(selected_game_ids))
    minimum_activation = int(policy["sample_size_gates"]["minimum_independent_games"])
    initial_reliability = int(policy["sample_size_gates"]["initial_reliability_independent_games"])
    ideal = int(policy["sample_size_gates"]["ideal_independent_games"])
    quality_ok = duplicate_game_observed_rows == 0 and duplicate_selected_games == 0 and invalid_rows == 0
    report = {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "policy": policy,
        "coverage": {
            "long_snapshot_rows": len(long_rows),
            "independent_games_available": len(groups),
            "independent_games_selected": selected_count,
            "games_without_primary_selection": games_without_selection,
            "primary_selection_rate": round(selected_count / len(groups), 6) if groups else 0.0,
            "rejection_reason_counts": dict(sorted(rejection_counts.items())),
            "diagnostic_policy_results": diagnostic_results,
        },
        "quality": {
            "invalid_long_rows": invalid_rows,
            "duplicate_game_observed_rows": duplicate_game_observed_rows,
            "duplicate_selected_independent_games": duplicate_selected_games,
            "selected_rows_equal_independent_games": len(selected) == selected_count,
            "outcomes_or_market_prices_used_for_selection": False,
            "multiple_snapshots_counted_as_independent_games": False,
            "incomplete_snapshots_imputed_as_healthy": False,
            "post_outcome_policy_selection_allowed": False,
        },
        "sample_size": {
            "minimum_activation_independent_games": minimum_activation,
            "initial_reliability_independent_games": initial_reliability,
            "ideal_independent_games": ideal,
            "minimum_activation_met": selected_count >= minimum_activation,
            "initial_reliability_met": selected_count >= initial_reliability,
            "ideal_sample_met": selected_count >= ideal,
        },
        "decision": {
            "ready_for_selected_panel_research": bool(selected) and quality_ok,
            "ready_for_injury_feature_walk_forward_holdout": (
                selected_count >= minimum_activation and quality_ok
            ),
            "ready_for_model_training": False,
            "ready_for_probability_adjustment": False,
            "ready_for_betting_edge_claim": False,
            "reason": (
                "Primary policy produced one outcome-blind row per independent game. "
                "Holdout remains blocked until the independent-game gate and upstream audits pass."
            ),
        },
        "guardrails": {
            "primary_policy_predeclared": True,
            "primary_policy_fallback": "no_selection",
            "selection_key": "historical_game_id",
            "selected_rows_per_game_maximum": 1,
            "diagnostic_policies_cannot_be_promoted_after_viewing_outcomes": True,
        },
    }
    (output_dir / "snapshot-selection-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def self_test(output_dir: Path) -> None:
    policy = {
        "schema_version": "injury-snapshot-selection-policy-v1",
        "frozen_before_outcome_join": True,
        "primary_policy": {
            "name": "latest_feature_ready_at_or_before_t60",
            "minimum_minutes_before_tip": 60,
            "require_matchup_snapshot_complete": True,
            "require_matchup_feature_available": True,
            "fallback": "no_selection",
            "tie_breaker": "latest_observed_at",
        },
        "diagnostic_policies": [{
            "name": "latest_complete_pre_tip",
            "minimum_minutes_before_tip": 0,
            "require_matchup_snapshot_complete": True,
            "require_matchup_feature_available": True,
            "fallback": "no_selection",
            "tie_breaker": "latest_observed_at",
        }],
        "sample_size_gates": {
            "minimum_independent_games": 100,
            "initial_reliability_independent_games": 300,
            "ideal_independent_games": 500,
        },
    }
    rows = [
        {"historical_game_id":"g1","game_date":"2024-01-01","observed_at":"2024-01-01T20:00:00Z","commence_time":"2024-01-02T00:00:00Z","minutes_before_tip":"240","matchup_snapshot_complete":"1","matchup_feature_available":"1"},
        {"historical_game_id":"g1","game_date":"2024-01-01","observed_at":"2024-01-01T23:00:00Z","commence_time":"2024-01-02T00:00:00Z","minutes_before_tip":"60","matchup_snapshot_complete":"0","matchup_feature_available":"0"},
        {"historical_game_id":"g1","game_date":"2024-01-01","observed_at":"2024-01-01T23:30:00Z","commence_time":"2024-01-02T00:00:00Z","minutes_before_tip":"30","matchup_snapshot_complete":"1","matchup_feature_available":"1"},
        {"historical_game_id":"g2","game_date":"2024-01-02","observed_at":"2024-01-02T21:30:00Z","commence_time":"2024-01-02T23:00:00Z","minutes_before_tip":"90","matchup_snapshot_complete":"1","matchup_feature_available":"1"},
        {"historical_game_id":"g2","game_date":"2024-01-02","observed_at":"2024-01-02T21:50:00Z","commence_time":"2024-01-02T23:00:00Z","minutes_before_tip":"70","matchup_snapshot_complete":"1","matchup_feature_available":"1"},
    ]
    report = select(rows, policy, output_dir)
    selected = read_csv(output_dir / "selected-matchup-injury-burden.csv")
    assert report["coverage"]["independent_games_selected"] == 2, report
    assert len(selected) == 2, selected
    assert next(row for row in selected if row["historical_game_id"] == "g1")["observed_at"] == "2024-01-01T20:00:00Z"
    assert next(row for row in selected if row["historical_game_id"] == "g2")["observed_at"] == "2024-01-02T21:50:00Z"
    assert report["quality"]["multiple_snapshots_counted_as_independent_games"] is False
    assert report["decision"]["ready_for_injury_feature_walk_forward_holdout"] is False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--long-matchups", type=Path)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test(args.output_dir)
        print("injury snapshot selection self-test passed")
        return
    if not args.long_matchups or not args.policy:
        parser.error("--long-matchups and --policy are required")
    report = select(read_csv(args.long_matchups), load_policy(args.policy), args.output_dir)
    print(json.dumps(report["decision"], indent=2))
    if not report["decision"]["ready_for_selected_panel_research"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
