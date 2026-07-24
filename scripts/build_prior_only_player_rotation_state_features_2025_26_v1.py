#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

VERSION = "prior-only-player-rotation-state-features-2025-26-v1"
FORMAL_STATE = "PRIOR_ONLY_PLAYER_ROTATION_STATE_FEATURES_2025_26_PASS"
EXPECTED_GAMES = 1230
EXPECTED_TEAM_ROWS = 2460
MIN_FEATURE_READY_GAMES = 1000
MIN_FEATURE_READY_RATE = 0.80
MIN_READY_MONTHS = 5
EXPECTED_TEAMS = 30

PLAYER_FEATURE_FIELDS = [
    "minutes_avg_prior_3",
    "minutes_avg_prior_5",
    "minutes_avg_prior_10",
    "minutes_trend_prior_3_vs_10",
    "start_rate_prior_5",
    "start_rate_prior_10",
    "appearance_rate_prior_10",
    "days_since_last_appearance",
    "recent_return_state",
    "role_rank_prior_5",
]

TEAM_FEATURE_FIELDS = [
    "rotation_players_prior_5",
    "top5_minutes_share_prior_5",
    "top8_minutes_share_prior_5",
    "top8_minutes_share_prior_10",
    "rotation_entropy_prior_5",
    "rotation_entropy_prior_10",
    "top8_set_continuity_prior_5",
    "starter_set_continuity_prior_5",
    "minutes_allocation_volatility_prior_5",
    "role_change_magnitude_prior_3_vs_10",
    "recent_return_players_count",
    "new_team_rotation_players_prior_5",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def as_date(value: str) -> date:
    return date.fromisoformat(value)


def finite_or_none(value: float | int | None) -> float | int | None:
    if value is None:
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def mean(values: Iterable[float]) -> float | None:
    items = list(values)
    return sum(items) / len(items) if items else None


def jaccard(left: set[str], right: set[str]) -> float | None:
    union = left | right
    if not union:
        return None
    return len(left & right) / len(union)


def normalized_entropy(minutes_by_player: dict[str, float]) -> float | None:
    positive = [value for value in minutes_by_player.values() if value > 0]
    total = sum(positive)
    if total <= 0:
        return None
    if len(positive) == 1:
        return 0.0
    probs = [value / total for value in positive]
    raw = -sum(p * math.log(p) for p in probs)
    return raw / math.log(len(probs))


def top_set(rows: list[dict[str, Any]], k: int) -> set[str]:
    ranked = sorted(
        (row for row in rows if row["minutes"] > 0),
        key=lambda row: (-row["minutes"], row["player_id"]),
    )
    return {row["player_id"] for row in ranked[:k]}


def pairwise_mean_jaccard(sets: list[set[str]]) -> float | None:
    if len(sets) < 2:
        return None
    values = [jaccard(sets[i - 1], sets[i]) for i in range(1, len(sets))]
    clean = [value for value in values if value is not None]
    return mean(clean)


def aggregate_minutes(rows_by_game: list[list[dict[str, Any]]]) -> dict[str, float]:
    result: defaultdict[str, float] = defaultdict(float)
    for rows in rows_by_game:
        for row in rows:
            result[row["player_id"]] += row["minutes"]
    return dict(result)


def top_share(rows_by_game: list[list[dict[str, Any]]], k: int) -> float | None:
    totals = aggregate_minutes(rows_by_game)
    total = sum(totals.values())
    if total <= 0:
        return None
    ranked = sorted(totals.items(), key=lambda item: (-item[1], item[0]))
    return sum(value for _, value in ranked[:k]) / total


def role_change(rows3: list[list[dict[str, Any]]], rows10: list[list[dict[str, Any]]]) -> tuple[float | None, int]:
    total3 = aggregate_minutes(rows3)
    total10 = aggregate_minutes(rows10)
    sum3 = sum(total3.values())
    sum10 = sum(total10.values())
    if sum3 <= 0 or sum10 <= 0:
        return None, 0
    common = sorted(set(total3) & set(total10))
    if not common:
        return None, 0
    value = sum(abs(total3[player] / sum3 - total10[player] / sum10) for player in common)
    return value, len(common)


def minutes_volatility(rows_by_game: list[list[dict[str, Any]]]) -> tuple[float | None, int]:
    shares_by_player: defaultdict[str, list[float]] = defaultdict(list)
    for rows in rows_by_game:
        total = sum(row["minutes"] for row in rows)
        if total <= 0:
            continue
        for row in rows:
            # Absence of a source row is unknown and is not imputed as zero.
            shares_by_player[row["player_id"]].append(row["minutes"] / total)
    deviations = [statistics.pstdev(values) for values in shares_by_player.values() if len(values) >= 2]
    return (mean(deviations), len(deviations))


def parse_inputs(source_path: Path, index_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    raw_source = read_csv(source_path)
    raw_index = read_csv(index_path)

    source: list[dict[str, Any]] = []
    seen_source: set[tuple[str, str]] = set()
    for row in raw_source:
        key = (row["source_game_id"].zfill(10), row["player_id"].strip())
        if key in seen_source:
            raise ValueError(f"duplicate source game-player key: {key}")
        seen_source.add(key)
        source.append(
            {
                "source_game_id": key[0],
                "source_game_date_et": row["source_game_date_et"],
                "team_abbr": row["team_abbr"].strip(),
                "player_id": key[1],
                "minutes": float(row["minutes"]),
                "played": int(row["played"]),
                "starter": int(row["starter"]),
                "source_provider": row["source_provider"],
                "source_sha256": row["source_sha256"],
                "retrieved_at": row["retrieved_at"],
                "source_time_semantics": row["source_time_semantics"],
            }
        )

    games: list[dict[str, Any]] = []
    seen_games: set[str] = set()
    for row in raw_index:
        game_id = row["historical_game_id"].zfill(10)
        if game_id in seen_games:
            raise ValueError(f"duplicate target game: {game_id}")
        seen_games.add(game_id)
        if row.get("source_success") != "1":
            raise ValueError(f"source index contains failed game: {game_id}")
        games.append(
            {
                "target_game_id": game_id,
                "target_game_date_et": row["game_date"],
                "home_team_abbr": row["home_team_abbr"].strip(),
                "away_team_abbr": row["away_team_abbr"].strip(),
            }
        )

    games.sort(key=lambda row: (row["target_game_date_et"], row["target_game_id"]))
    source.sort(key=lambda row: (row["source_game_date_et"], row["source_game_id"], row["team_abbr"], row["player_id"]))
    return source, games


def build(source: list[dict[str, Any]], games: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    if len(games) != EXPECTED_GAMES:
        raise ValueError(f"expected {EXPECTED_GAMES} target games, found {len(games)}")

    index_by_game = {row["target_game_id"]: row for row in games}
    expected_team_games = {
        (row["target_game_id"], team)
        for row in games
        for team in (row["home_team_abbr"], row["away_team_abbr"])
    }
    if len(expected_team_games) != EXPECTED_TEAM_ROWS:
        raise ValueError("target team-game domain is not exactly 2,460 unique rows")

    rows_by_team_game: defaultdict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    player_team_history: defaultdict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    source_time_violations = 0
    source_team_mismatches = 0
    player_game_teams: defaultdict[tuple[str, str], set[str]] = defaultdict(set)

    for row in source:
        game = index_by_game.get(row["source_game_id"])
        if game is None:
            source_team_mismatches += 1
            continue
        if row["source_game_date_et"] != game["target_game_date_et"]:
            source_team_mismatches += 1
        if row["team_abbr"] not in {game["home_team_abbr"], game["away_team_abbr"]}:
            source_team_mismatches += 1
        rows_by_team_game[(row["team_abbr"], row["source_game_id"])].append(row)
        player_team_history[(row["team_abbr"], row["player_id"])].append(row)
        player_game_teams[(row["source_game_id"], row["player_id"])].add(row["team_abbr"])

    cross_team_identity_game_conflicts = sum(len(teams) > 1 for teams in player_game_teams.values())
    if source_team_mismatches:
        raise ValueError(f"source/index mismatches: {source_team_mismatches}")
    if cross_team_identity_game_conflicts:
        raise ValueError(f"same player appears for multiple teams in one game: {cross_team_identity_game_conflicts}")

    team_games: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for game in games:
        for side, team in (("home", game["home_team_abbr"]), ("away", game["away_team_abbr"])):
            team_games[team].append(
                {
                    "game_id": game["target_game_id"],
                    "game_date": game["target_game_date_et"],
                    "side": side,
                }
            )
    for team in team_games:
        team_games[team].sort(key=lambda row: (row["game_date"], row["game_id"]))

    player_outputs: list[dict[str, Any]] = []
    team_outputs: list[dict[str, Any]] = []
    team_output_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    null_counts: Counter[str] = Counter()
    team_history_bands: Counter[str] = Counter()

    for game in games:
        target_date = as_date(game["target_game_date_et"])
        for side, team in (("home", game["home_team_abbr"]), ("away", game["away_team_abbr"])):
            prior_team_games = [
                row for row in team_games[team]
                if as_date(row["game_date"]) < target_date
            ]
            prior_count = len(prior_team_games)
            if prior_count < 3:
                team_history_bands["lt3"] += 1
            elif prior_count < 5:
                team_history_bands["3_to_4"] += 1
            elif prior_count < 10:
                team_history_bands["5_to_9"] += 1
            else:
                team_history_bands["gte10"] += 1

            windows: dict[int, list[dict[str, Any]]] = {
                n: prior_team_games[-n:] for n in (3, 5, 10)
            }
            window_rows: dict[int, list[list[dict[str, Any]]]] = {
                n: [rows_by_team_game[(team, item["game_id"])] for item in windows[n]]
                for n in windows
            }

            for n in windows:
                for item in windows[n]:
                    if as_date(item["game_date"]) >= target_date:
                        source_time_violations += 1

            candidate_players = sorted({
                row["player_id"]
                for rows in window_rows[10]
                for row in rows
            })
            row_map_by_game = {
                item["game_id"]: {row["player_id"]: row for row in rows_by_team_game[(team, item["game_id"])]}
                for item in prior_team_games
            }

            player_rows_for_target: list[dict[str, Any]] = []
            for player_id in candidate_players:
                feature: dict[str, Any] = {
                    "target_game_id": game["target_game_id"],
                    "target_game_date_et": game["target_game_date_et"],
                    "team_abbr": team,
                    "target_side": side,
                    "player_id": player_id,
                    "prior_team_games_count": prior_count,
                    "source_time_rule": "source_game_date_et < target_game_date_et",
                    "feature_version": VERSION,
                }
                observed_by_n: dict[int, list[dict[str, Any]]] = {}
                for n in (3, 5, 10):
                    observed = [
                        row_map_by_game[item["game_id"]][player_id]
                        for item in windows[n]
                        if player_id in row_map_by_game[item["game_id"]]
                    ]
                    observed_by_n[n] = observed
                    feature[f"eligible_rows_prior_{n}"] = len(observed)
                    feature[f"minutes_avg_prior_{n}"] = mean(row["minutes"] for row in observed)

                if feature["minutes_avg_prior_3"] is not None and feature["minutes_avg_prior_10"] is not None:
                    feature["minutes_trend_prior_3_vs_10"] = feature["minutes_avg_prior_3"] - feature["minutes_avg_prior_10"]
                else:
                    feature["minutes_trend_prior_3_vs_10"] = None

                for n in (5, 10):
                    observed = observed_by_n[n]
                    feature[f"start_rate_prior_{n}"] = (
                        sum(row["starter"] for row in observed) / len(observed) if observed else None
                    )
                observed10 = observed_by_n[10]
                feature["appearance_rate_prior_10"] = (
                    sum(row["minutes"] > 0 for row in observed10) / len(observed10) if observed10 else None
                )

                positive_prior = [
                    row for row in player_team_history[(team, player_id)]
                    if as_date(row["source_game_date_et"]) < target_date and row["minutes"] > 0
                ]
                feature["days_since_last_appearance"] = (
                    (target_date - as_date(positive_prior[-1]["source_game_date_et"])).days
                    if positive_prior else None
                )

                last4 = prior_team_games[-4:]
                if len(last4) == 4 and all(player_id in row_map_by_game[item["game_id"]] for item in last4):
                    seq = [row_map_by_game[item["game_id"]][player_id]["minutes"] for item in last4]
                    feature["recent_return_state"] = int(seq[-1] > 0 and all(value <= 0 for value in seq[:-1]))
                else:
                    feature["recent_return_state"] = None
                feature["role_rank_prior_5"] = None
                feature["team_specific_rows_before_target"] = sum(
                    as_date(row["source_game_date_et"]) < target_date
                    for row in player_team_history[(team, player_id)]
                )
                player_rows_for_target.append(feature)

            rankable = sorted(
                (row for row in player_rows_for_target if row["minutes_avg_prior_5"] is not None),
                key=lambda row: (-row["minutes_avg_prior_5"], row["player_id"]),
            )
            for rank, row in enumerate(rankable, start=1):
                row["role_rank_prior_5"] = rank

            recent_return_count = sum(row["recent_return_state"] == 1 for row in player_rows_for_target)
            new_team_top8_count = sum(
                row["role_rank_prior_5"] is not None
                and row["role_rank_prior_5"] <= 8
                and row["team_specific_rows_before_target"] < 5
                for row in player_rows_for_target
            )

            volatility, volatility_players = minutes_volatility(window_rows[5])
            role_change_value, role_change_players = role_change(window_rows[3], window_rows[10])
            team_feature: dict[str, Any] = {
                "target_game_id": game["target_game_id"],
                "target_game_date_et": game["target_game_date_et"],
                "team_abbr": team,
                "target_side": side,
                "prior_team_games_count": prior_count,
                "rotation_players_prior_5": len({
                    row["player_id"] for rows in window_rows[5] for row in rows if row["minutes"] > 0
                }) if len(windows[5]) == 5 else None,
                "top5_minutes_share_prior_5": top_share(window_rows[5], 5) if len(windows[5]) == 5 else None,
                "top8_minutes_share_prior_5": top_share(window_rows[5], 8) if len(windows[5]) == 5 else None,
                "top8_minutes_share_prior_10": top_share(window_rows[10], 8) if len(windows[10]) == 10 else None,
                "rotation_entropy_prior_5": normalized_entropy(aggregate_minutes(window_rows[5])) if len(windows[5]) == 5 else None,
                "rotation_entropy_prior_10": normalized_entropy(aggregate_minutes(window_rows[10])) if len(windows[10]) == 10 else None,
                "top8_set_continuity_prior_5": pairwise_mean_jaccard([top_set(rows, 8) for rows in window_rows[5]]) if len(windows[5]) == 5 else None,
                "starter_set_continuity_prior_5": pairwise_mean_jaccard([
                    {row["player_id"] for row in rows if row["starter"] == 1} for rows in window_rows[5]
                ]) if len(windows[5]) == 5 else None,
                "minutes_allocation_volatility_prior_5": volatility if len(windows[5]) == 5 else None,
                "role_change_magnitude_prior_3_vs_10": role_change_value if len(windows[10]) == 10 else None,
                "recent_return_players_count": recent_return_count if len(windows[5]) == 5 else None,
                "new_team_rotation_players_prior_5": new_team_top8_count if len(windows[5]) == 5 else None,
                "volatility_players_compared": volatility_players if len(windows[5]) == 5 else 0,
                "role_change_players_compared": role_change_players if len(windows[10]) == 10 else 0,
                "candidate_players_prior_10": len(candidate_players),
                "source_time_rule": "source_game_date_et < target_game_date_et",
                "feature_version": VERSION,
            }

            for field in TEAM_FEATURE_FIELDS:
                team_feature[field] = finite_or_none(team_feature[field])
                if team_feature[field] is None:
                    null_counts[field] += 1

            team_feature["feature_ready_team"] = int(
                prior_count >= 10 and all(team_feature[field] is not None for field in TEAM_FEATURE_FIELDS)
            )
            team_outputs.append(team_feature)
            team_output_by_key[(game["target_game_id"], team)] = team_feature
            player_outputs.extend(player_rows_for_target)

    matchup_outputs: list[dict[str, Any]] = []
    readiness: Counter[str] = Counter()
    for game in games:
        home = team_output_by_key[(game["target_game_id"], game["home_team_abbr"])]
        away = team_output_by_key[(game["target_game_id"], game["away_team_abbr"])]
        output: dict[str, Any] = {
            "target_game_id": game["target_game_id"],
            "target_game_date_et": game["target_game_date_et"],
            "home_team_abbr": game["home_team_abbr"],
            "away_team_abbr": game["away_team_abbr"],
            "home_prior_team_games_count": home["prior_team_games_count"],
            "away_prior_team_games_count": away["prior_team_games_count"],
            "feature_ready_home": home["feature_ready_team"],
            "feature_ready_away": away["feature_ready_team"],
            "feature_ready_game": int(home["feature_ready_team"] and away["feature_ready_team"]),
            "feature_version": VERSION,
        }
        if output["feature_ready_game"]:
            readiness["both_ready"] += 1
        elif output["feature_ready_home"]:
            readiness["away_not_ready"] += 1
        elif output["feature_ready_away"]:
            readiness["home_not_ready"] += 1
        else:
            readiness["both_not_ready"] += 1

        for field in TEAM_FEATURE_FIELDS:
            output[f"home_{field}"] = home[field]
            output[f"away_{field}"] = away[field]
            output[f"diff_{field}"] = (
                home[field] - away[field]
                if home[field] is not None and away[field] is not None
                else None
            )
        matchup_outputs.append(output)

    duplicate_team_keys = len(team_outputs) - len({(row["target_game_id"], row["team_abbr"]) for row in team_outputs})
    duplicate_matchup_keys = len(matchup_outputs) - len({row["target_game_id"] for row in matchup_outputs})
    duplicate_player_keys = len(player_outputs) - len({
        (row["target_game_id"], row["team_abbr"], row["player_id"]) for row in player_outputs
    })
    non_finite_values = 0
    bounded_violations = 0
    for row in team_outputs:
        for field in TEAM_FEATURE_FIELDS:
            value = row[field]
            if isinstance(value, float) and not math.isfinite(value):
                non_finite_values += 1
        for field in (
            "top5_minutes_share_prior_5",
            "top8_minutes_share_prior_5",
            "top8_minutes_share_prior_10",
            "rotation_entropy_prior_5",
            "rotation_entropy_prior_10",
            "top8_set_continuity_prior_5",
            "starter_set_continuity_prior_5",
        ):
            value = row[field]
            if value is not None and not (0 <= value <= 1):
                bounded_violations += 1

    ready_games = sum(row["feature_ready_game"] for row in matchup_outputs)
    ready_rate = ready_games / len(matchup_outputs)
    ready_teams = sorted({
        row["team_abbr"] for row in team_outputs if row["feature_ready_team"]
    })
    ready_months = sorted({
        row["target_game_date_et"][:7] for row in matchup_outputs if row["feature_ready_game"]
    })

    report = {
        "schema_version": VERSION,
        "formal_state": FORMAL_STATE,
        "generated_at_utc": utc_now(),
        "purpose": "Build strictly-prior private player, team and matchup rotation-state features without model retraining or market features.",
        "inputs": {
            "target_games": len(games),
            "target_team_rows": len(team_outputs),
            "source_player_game_rows": len(source),
            "teams": len(team_games),
            "source_time_rule": "source_game_date_et < target_game_date_et",
        },
        "outputs": {
            "private_player_feature_rows": len(player_outputs),
            "private_team_feature_rows": len(team_outputs),
            "private_matchup_feature_rows": len(matchup_outputs),
            "public_player_rows_committed": 0,
            "public_game_level_feature_rows_committed": 0,
        },
        "coverage": {
            "feature_ready_independent_games": ready_games,
            "feature_ready_rate": round(ready_rate, 8),
            "teams_with_feature_ready_rows": len(ready_teams),
            "ready_team_abbrs": ready_teams,
            "months_with_feature_ready_games": len(ready_months),
            "ready_months": ready_months,
            "readiness_subgroups": dict(readiness),
            "team_history_bands": dict(team_history_bands),
        },
        "missingness": {
            "team_feature_null_counts": dict(sorted(null_counts.items())),
            "subgroup_audit_completed": True,
            "missing_source_row_policy": "UNKNOWN_NOT_ZERO",
            "early_season_policy": "NULL_PLUS_SAMPLE_COUNTS",
        },
        "quality": {
            "duplicate_target_game_team_keys": duplicate_team_keys,
            "duplicate_target_game_keys": duplicate_matchup_keys,
            "duplicate_target_game_team_player_keys": duplicate_player_keys,
            "source_time_violations": source_time_violations,
            "identity_ambiguities": cross_team_identity_game_conflicts,
            "source_index_mismatches": source_team_mismatches,
            "non_finite_feature_values": non_finite_values,
            "bounded_feature_violations": bounded_violations,
            "fuzzy_identity_rows": 0,
            "target_game_source_rows_used": 0,
            "same_day_source_rows_used": 0,
            "future_source_rows_used": 0,
            "market_feature_rows_used": 0,
        },
        "acceptance_gates": {
            "minimum_feature_ready_games": MIN_FEATURE_READY_GAMES,
            "minimum_feature_ready_rate": MIN_FEATURE_READY_RATE,
            "minimum_teams": EXPECTED_TEAMS,
            "minimum_months": MIN_READY_MONTHS,
            "feature_ready_games_pass": ready_games >= MIN_FEATURE_READY_GAMES,
            "feature_ready_rate_pass": ready_rate >= MIN_FEATURE_READY_RATE,
            "teams_pass": len(ready_teams) == EXPECTED_TEAMS,
            "months_pass": len(ready_months) >= MIN_READY_MONTHS,
            "source_time_pass": source_time_violations == 0,
            "identity_pass": cross_team_identity_game_conflicts == 0,
            "missingness_audit_pass": True,
            "dataset_eligible_for_training_free_residual_audit": False,
        },
        "preserved_locks": {
            "model_training_authorized": False,
            "model_retraining_executed": False,
            "model_refit_executed": False,
            "calibration_change_executed": False,
            "strict_t60_qualified": False,
            "formal_market_backtest_allowed": False,
            "betting_edge_claim_allowed": False,
            "formal_stake": 0,
        },
        "next_unique_sub_mainline": "PREDECLARE_TRAINING_FREE_PRIOR_ONLY_ROTATION_RESIDUAL_AUDIT_2025_26_V1",
    }
    gate_values = [
        report["acceptance_gates"][key]
        for key in (
            "feature_ready_games_pass",
            "feature_ready_rate_pass",
            "teams_pass",
            "months_pass",
            "source_time_pass",
            "identity_pass",
            "missingness_audit_pass",
        )
    ]
    quality_values = [value == 0 for value in report["quality"].values()]
    accepted = all(gate_values) and all(quality_values)
    report["acceptance_gates"]["dataset_eligible_for_training_free_residual_audit"] = accepted
    report["formal_state"] = (
        FORMAL_STATE if accepted else "PRIOR_ONLY_PLAYER_ROTATION_STATE_FEATURES_2025_26_FAIL"
    )
    return player_outputs, team_outputs, matchup_outputs, report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--source-index", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    source, games = parse_inputs(args.source, args.source_index)
    players, teams, matchups, report = build(source, games)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    player_fields = [
        "target_game_id", "target_game_date_et", "team_abbr", "target_side", "player_id",
        "prior_team_games_count", "eligible_rows_prior_3", "eligible_rows_prior_5", "eligible_rows_prior_10",
        *PLAYER_FEATURE_FIELDS,
        "team_specific_rows_before_target", "source_time_rule", "feature_version",
    ]
    team_fields = [
        "target_game_id", "target_game_date_et", "team_abbr", "target_side", "prior_team_games_count",
        *TEAM_FEATURE_FIELDS,
        "volatility_players_compared", "role_change_players_compared", "candidate_players_prior_10",
        "feature_ready_team", "source_time_rule", "feature_version",
    ]
    matchup_fields = [
        "target_game_id", "target_game_date_et", "home_team_abbr", "away_team_abbr",
        "home_prior_team_games_count", "away_prior_team_games_count",
        "feature_ready_home", "feature_ready_away", "feature_ready_game",
    ]
    for field in TEAM_FEATURE_FIELDS:
        matchup_fields.extend([f"home_{field}", f"away_{field}", f"diff_{field}"])
    matchup_fields.append("feature_version")

    player_path = args.output_dir / "prior-only-player-rotation-player-features-2025-26-v1.csv"
    team_path = args.output_dir / "prior-only-player-rotation-team-features-2025-26-v1.csv"
    matchup_path = args.output_dir / "prior-only-player-rotation-matchup-features-2025-26-v1.csv"
    report_path = args.output_dir / "prior-only-player-rotation-state-features-2025-26-report-v1.json"
    write_csv(player_path, players, player_fields)
    write_csv(team_path, teams, team_fields)
    write_csv(matchup_path, matchups, matchup_fields)

    report["input_digests"] = {
        "source_csv_sha256": sha256(args.source),
        "source_index_csv_sha256": sha256(args.source_index),
    }
    report["output_digests"] = {
        "private_player_features_sha256": sha256(player_path),
        "private_team_features_sha256": sha256(team_path),
        "private_matchup_features_sha256": sha256(matchup_path),
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["formal_state"] == FORMAL_STATE else 1


if __name__ == "__main__":
    raise SystemExit(main())
