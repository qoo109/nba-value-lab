#!/usr/bin/env python3
"""Deterministic aggregate-only audit for the user-supplied legacy NBA market archive.

The runner compares the owner-confirmed candidate CSV with the verified five-season
Historical Gold identity layer and Historical Silver final scores. It never emits
raw rows, unmatched keys, game identifiers, or source databases.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

VERSION = "user-supplied-legacy-market-archive-cross-source-audit-implementation-v1"
REPORT_NAME = "user-supplied-legacy-market-archive-cross-source-audit-report.json"
STATUS_NAME = "user-supplied-legacy-market-archive-cross-source-run-status.json"

PASS_OUTCOME = "ROLE_LIMITED_LEGACY_MARKET_ARCHIVE_CROSS_SOURCE_VALIDATED"
RETAIN_OUTCOME = "RETAIN_ROLE_LIMITED_LEGACY_MARKET_ARCHIVE_ELIGIBLE"
BLOCKED_OUTCOME = "USER_SUPPLIED_LEGACY_MARKET_ARCHIVE_CROSS_SOURCE_AUDIT_RESEARCH_BLOCKED"

REQUIRED_CANDIDATE_COLUMNS = {
    "season", "date", "regular", "playoffs", "home", "away",
    "score_home", "score_away",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_bool(value: Any) -> bool | None:
    text = "" if value is None else str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return None


def parse_int(value: Any) -> int | None:
    text = "" if value is None else str(value).strip()
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    if not number.is_integer():
        return None
    return int(number)


def normalize_date(value: Any) -> str | None:
    text = "" if value is None else str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        return None


def safe_rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 9) if denominator else 0.0


def duplicate_group_count(keys: Iterable[tuple[str, str, str]]) -> int:
    counts = Counter(keys)
    return sum(1 for count in counts.values() if count > 1)


def table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")}


@contextmanager
def materialized_sqlite(path: Path) -> Iterator[Path]:
    """Yield a plain SQLite path for .sqlite or .gz input and delete temp copies."""
    if path.suffix.lower() != ".gz":
        yield path
        return
    with tempfile.TemporaryDirectory(prefix="nbavl-legacy-audit-db-") as temp_name:
        target = Path(temp_name) / path.with_suffix("").name
        with gzip.open(path, "rb") as source, target.open("wb") as destination:
            shutil.copyfileobj(source, destination, length=1024 * 1024)
        yield target


def load_policy(path: Path) -> dict[str, Any]:
    policy = json.loads(path.read_text(encoding="utf-8"))
    expected = "user-supplied-legacy-market-archive-cross-source-audit-predeclaration-v1"
    if policy.get("schema_version") != expected:
        raise ValueError("unexpected predeclaration schema version")
    if policy.get("next_state_if_validation_passes", {}).get(
        "formal_state"
    ) != "USER_SUPPLIED_LEGACY_MARKET_ARCHIVE_CROSS_SOURCE_AUDIT_PREDECLARATION_READY":
        raise ValueError("predeclaration is not in the ready state")
    contract = policy["deterministic_join_contract"]
    if contract.get("fuzzy_matching_allowed") is not False:
        raise ValueError("fuzzy matching must remain disabled")
    if contract.get("score_used_to_repair_identity") is not False:
        raise ValueError("scores must not repair identity")
    if contract.get("many_to_many_join_allowed") is not False:
        raise ValueError("many-to-many joins must remain disabled")
    if contract.get("manual_key_overrides_allowed") is not False:
        raise ValueError("manual key overrides must remain disabled")
    return policy


def locate_confirmed_candidate(dataset_root: Path, policy: dict[str, Any]) -> Path:
    expected = policy["candidate_source"]
    expected_sha = expected["file_sha256"]
    expected_bytes = int(expected["file_bytes"])
    candidates = [path for path in dataset_root.rglob("*") if path.is_file()]
    matches = []
    for path in candidates:
        if path.stat().st_size != expected_bytes:
            continue
        if file_sha256(path) == expected_sha:
            matches.append(path)
    if len(matches) != 1:
        raise ValueError(
            f"expected exactly one candidate file matching confirmed size/hash; found {len(matches)}"
        )
    return matches[0]


def download_dataset(handle: str, destination: Path) -> Path:
    try:
        import kagglehub
    except ImportError as exc:
        raise RuntimeError("kagglehub is required for live dataset download") from exc
    destination.mkdir(parents=True, exist_ok=True)
    try:
        resolved = kagglehub.dataset_download(
            handle,
            force_download=True,
            output_dir=str(destination),
        )
    except Exception as exc:
        raise RuntimeError(
            "Kaggle download failed. Public access is attempted first; if Kaggle "
            "requires authentication, configure the free KAGGLE_API_TOKEN secret. "
            f"Original error: {type(exc).__name__}: {exc}"
        ) from exc
    return Path(resolved)


def load_candidate(path: Path, policy: dict[str, Any]) -> dict[str, Any]:
    expected = policy["candidate_source"]
    actual_sha = file_sha256(path)
    actual_bytes = path.stat().st_size
    file_identity_pass = (
        actual_sha == expected["file_sha256"]
        and actual_bytes == int(expected["file_bytes"])
    )

    scope = policy["overlap_scope"]
    allowed_seasons = {int(value) for value in scope["candidate_season_labels"]}
    season_mapping = {int(key): value for key, value in scope["season_mapping"].items()}
    team_mapping = policy["deterministic_join_contract"]["team_mapping"]

    all_rows = 0
    eligible_rows = 0
    invalid_dates = 0
    unresolved_team_rows = 0
    missing_scores = 0
    invalid_boolean_rows = 0
    invalid_season_rows = 0
    rows_by_season: Counter[str] = Counter()
    records: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing_columns = sorted(REQUIRED_CANDIDATE_COLUMNS - columns)
        if missing_columns:
            raise ValueError(f"candidate CSV missing required columns: {missing_columns}")

        for row in reader:
            all_rows += 1
            season = parse_int(row.get("season"))
            regular = parse_bool(row.get("regular"))
            playoffs = parse_bool(row.get("playoffs"))
            if season is None:
                invalid_season_rows += 1
                continue
            if regular is None or playoffs is None:
                invalid_boolean_rows += 1
                continue
            if season not in allowed_seasons or not regular or playoffs:
                continue

            eligible_rows += 1
            season_label = season_mapping[season]
            rows_by_season[season_label] += 1
            game_date = normalize_date(row.get("date"))
            if game_date is None:
                invalid_dates += 1

            home_raw = str(row.get("home", "")).strip().lower()
            away_raw = str(row.get("away", "")).strip().lower()
            home = team_mapping.get(home_raw)
            away = team_mapping.get(away_raw)
            if home is None or away is None:
                unresolved_team_rows += 1

            home_score = parse_int(row.get("score_home"))
            away_score = parse_int(row.get("score_away"))
            if home_score is None or away_score is None:
                missing_scores += 1

            if game_date and home and away:
                records.append({
                    "key": (game_date, home, away),
                    "season_label": season_label,
                    "home_score": home_score,
                    "away_score": away_score,
                })

    keys = [record["key"] for record in records]
    return {
        "file": {
            "name": path.name,
            "bytes": actual_bytes,
            "sha256": actual_sha,
            "expected_name": expected["file_name"],
            "expected_bytes": int(expected["file_bytes"]),
            "expected_sha256": expected["file_sha256"],
            "identity_pass": file_identity_pass,
        },
        "all_rows": all_rows,
        "eligible_rows": eligible_rows,
        "eligible_rows_by_season": dict(sorted(rows_by_season.items())),
        "invalid_dates": invalid_dates,
        "unresolved_team_rows": unresolved_team_rows,
        "missing_scores": missing_scores,
        "invalid_boolean_rows": invalid_boolean_rows,
        "invalid_season_rows": invalid_season_rows,
        "duplicate_key_groups": duplicate_group_count(keys),
        "records": records,
    }


def load_reference(gold_path: Path, silver_path: Path, policy: dict[str, Any]) -> dict[str, Any]:
    reference_seasons = set(policy["overlap_scope"]["reference_seasons"])
    with materialized_sqlite(gold_path) as gold_db, materialized_sqlite(silver_path) as silver_db:
        gold_connection = sqlite3.connect(gold_db)
        silver_connection = sqlite3.connect(silver_db)
        try:
            required_gold_tables = {"gold_matchup_features", "gold_team_game_features"}
            present_gold_tables = {
                row[0] for row in gold_connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            if not required_gold_tables.issubset(present_gold_tables):
                raise ValueError("Gold database is missing required identity tables")
            if "games" not in {
                row[0] for row in silver_connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }:
                raise ValueError("Silver database is missing games table")

            required_matchup = {
                "game_id", "game_date", "home_team_abbr", "away_team_abbr", "home_feature_id"
            }
            required_team = {"feature_id", "season_label", "is_home"}
            required_games = {"game_id", "home_score", "away_score"}
            if not required_matchup.issubset(table_columns(gold_connection, "gold_matchup_features")):
                raise ValueError("Gold matchup table has an unexpected schema")
            if not required_team.issubset(table_columns(gold_connection, "gold_team_game_features")):
                raise ValueError("Gold team feature table has an unexpected schema")
            if not required_games.issubset(table_columns(silver_connection, "games")):
                raise ValueError("Silver games table has an unexpected schema")

            score_by_game = {
                str(game_id): (parse_int(home_score), parse_int(away_score))
                for game_id, home_score, away_score in silver_connection.execute(
                    "SELECT game_id, home_score, away_score FROM games"
                )
            }

            records: list[dict[str, Any]] = []
            rows_by_season: Counter[str] = Counter()
            invalid_dates = 0
            missing_scores = 0
            missing_score_game_ids = 0
            invalid_home_feature_rows = 0

            query = """
                SELECT
                    m.game_id,
                    m.game_date,
                    m.home_team_abbr,
                    m.away_team_abbr,
                    t.season_label,
                    t.is_home
                FROM gold_matchup_features AS m
                JOIN gold_team_game_features AS t
                  ON t.feature_id = m.home_feature_id
            """
            for game_id, game_date_raw, home_raw, away_raw, season_label, is_home in gold_connection.execute(query):
                season_label = str(season_label)
                if season_label not in reference_seasons:
                    continue
                if int(is_home) != 1:
                    invalid_home_feature_rows += 1
                rows_by_season[season_label] += 1
                game_date = normalize_date(game_date_raw)
                if game_date is None:
                    invalid_dates += 1
                scores = score_by_game.get(str(game_id))
                if scores is None:
                    missing_score_game_ids += 1
                    home_score = away_score = None
                else:
                    home_score, away_score = scores
                if home_score is None or away_score is None:
                    missing_scores += 1
                home = str(home_raw).strip().upper()
                away = str(away_raw).strip().upper()
                if game_date:
                    records.append({
                        "key": (game_date, home, away),
                        "season_label": season_label,
                        "home_score": home_score,
                        "away_score": away_score,
                    })

            keys = [record["key"] for record in records]
            return {
                "gold_file": {
                    "name": gold_path.name,
                    "bytes": gold_path.stat().st_size,
                    "sha256": file_sha256(gold_path),
                },
                "silver_file": {
                    "name": silver_path.name,
                    "bytes": silver_path.stat().st_size,
                    "sha256": file_sha256(silver_path),
                },
                "reference_rows": len(records),
                "reference_rows_by_season": dict(sorted(rows_by_season.items())),
                "invalid_dates": invalid_dates,
                "missing_scores": missing_scores,
                "missing_score_game_ids": missing_score_game_ids,
                "invalid_home_feature_rows": invalid_home_feature_rows,
                "duplicate_key_groups": duplicate_group_count(keys),
                "records": records,
            }
        finally:
            gold_connection.close()
            silver_connection.close()


def compare(candidate: dict[str, Any], reference: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    candidate_groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    reference_groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in candidate["records"]:
        candidate_groups[record["key"]].append(record)
    for record in reference["records"]:
        reference_groups[record["key"]].append(record)

    ambiguous_keys = {
        key for key, rows in candidate_groups.items() if len(rows) != 1
    } | {
        key for key, rows in reference_groups.items() if len(rows) != 1
    }
    candidate_keys = set(candidate_groups) - ambiguous_keys
    reference_keys = set(reference_groups) - ambiguous_keys
    matched_keys = candidate_keys & reference_keys
    candidate_only = candidate_keys - reference_keys
    reference_only = reference_keys - candidate_keys

    score_pair_matches = 0
    score_pair_compared = 0
    matched_by_season: Counter[str] = Counter()
    candidate_unmatched_by_season: Counter[str] = Counter()
    reference_unmatched_by_season: Counter[str] = Counter()

    for key in matched_keys:
        candidate_row = candidate_groups[key][0]
        reference_row = reference_groups[key][0]
        matched_by_season[reference_row["season_label"]] += 1
        if None not in (
            candidate_row["home_score"], candidate_row["away_score"],
            reference_row["home_score"], reference_row["away_score"],
        ):
            score_pair_compared += 1
            if (
                candidate_row["home_score"] == reference_row["home_score"]
                and candidate_row["away_score"] == reference_row["away_score"]
            ):
                score_pair_matches += 1

    for key in candidate_only:
        candidate_unmatched_by_season[candidate_groups[key][0]["season_label"]] += 1
    for key in reference_only:
        reference_unmatched_by_season[reference_groups[key][0]["season_label"]] += 1

    candidate_count = int(candidate["eligible_rows"])
    reference_count = int(reference["reference_rows"])
    matched_count = len(matched_keys)
    per_season = {}
    all_seasons = policy["overlap_scope"]["reference_seasons"]
    for season in all_seasons:
        ref_total = int(reference["reference_rows_by_season"].get(season, 0))
        cand_total = int(candidate["eligible_rows_by_season"].get(season, 0))
        matched = int(matched_by_season.get(season, 0))
        per_season[season] = {
            "reference_games": ref_total,
            "candidate_eligible_games": cand_total,
            "matched_games": matched,
            "reference_match_rate": safe_rate(matched, ref_total),
            "candidate_match_rate": safe_rate(matched, cand_total),
            "candidate_unmatched_games": int(candidate_unmatched_by_season.get(season, 0)),
            "reference_unmatched_games": int(reference_unmatched_by_season.get(season, 0)),
        }

    return {
        "matched_games": matched_count,
        "candidate_unmatched_games": len(candidate_only),
        "reference_unmatched_games": len(reference_only),
        "ambiguous_join_keys": len(ambiguous_keys),
        "candidate_match_rate": safe_rate(matched_count, candidate_count),
        "reference_match_rate": safe_rate(matched_count, reference_count),
        "score_pair_compared_games": score_pair_compared,
        "score_pair_match_games": score_pair_matches,
        "score_pair_mismatch_games": score_pair_compared - score_pair_matches,
        "matched_score_pair_rate": safe_rate(score_pair_matches, score_pair_compared),
        "by_season": per_season,
        "aggregate_unmatched_reason_counts": {
            "candidate_key_not_in_reference": len(candidate_only),
            "reference_key_not_in_candidate": len(reference_only),
            "ambiguous_or_duplicate_join_key": len(ambiguous_keys),
        },
    }


def evaluate_gates(
    candidate: dict[str, Any],
    reference: dict[str, Any],
    comparison: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    frozen = policy["frozen_execution_gates"]
    gates = {
        "candidate_file_identity": candidate["file"]["identity_pass"],
        "minimum_reference_games": reference["reference_rows"] >= frozen["minimum_reference_games"],
        "minimum_candidate_eligible_games": candidate["eligible_rows"] >= frozen["minimum_candidate_eligible_games"],
        "minimum_reference_match_rate": comparison["reference_match_rate"] >= frozen["minimum_reference_match_rate"],
        "minimum_candidate_match_rate": comparison["candidate_match_rate"] >= frozen["minimum_candidate_match_rate"],
        "minimum_matched_score_pair_rate": comparison["matched_score_pair_rate"] >= frozen["minimum_matched_score_pair_rate"],
        "minimum_each_season_reference_match_rate": all(
            item["reference_match_rate"] >= frozen["minimum_each_season_reference_match_rate"]
            for item in comparison["by_season"].values()
        ),
        "maximum_candidate_duplicate_key_groups": candidate["duplicate_key_groups"] <= frozen["maximum_candidate_duplicate_key_groups"],
        "maximum_reference_duplicate_key_groups": reference["duplicate_key_groups"] <= frozen["maximum_reference_duplicate_key_groups"],
        "maximum_ambiguous_join_keys": comparison["ambiguous_join_keys"] <= frozen["maximum_ambiguous_join_keys"],
        "maximum_unresolved_team_codes": candidate["unresolved_team_rows"] <= frozen["maximum_unresolved_team_codes"],
        "maximum_invalid_candidate_dates": candidate["invalid_dates"] <= frozen["maximum_invalid_candidate_dates"],
        "maximum_invalid_reference_dates": reference["invalid_dates"] <= frozen["maximum_invalid_reference_dates"],
        "maximum_missing_candidate_scores_in_scope": candidate["missing_scores"] <= frozen["maximum_missing_candidate_scores_in_scope"],
        "maximum_missing_reference_scores_in_scope": reference["missing_scores"] <= frozen["maximum_missing_reference_scores_in_scope"],
        "reference_home_feature_identity": reference["invalid_home_feature_rows"] == 0,
        "candidate_boolean_and_season_parse": (
            candidate["invalid_boolean_rows"] == 0 and candidate["invalid_season_rows"] == 0
        ),
        "raw_rows_emitted": 0 <= frozen["maximum_raw_rows_emitted"],
        "raw_files_emitted": frozen["raw_files_emitted_allowed"] is False,
    }
    failed = sorted(name for name, passed in gates.items() if not passed)
    return {
        "checks": gates,
        "checks_total": len(gates),
        "checks_passed": len(gates) - len(failed),
        "checks_failed": len(failed),
        "failed_gates": failed,
        "all_frozen_gates_passed": not failed,
    }


def sanitized_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in candidate.items() if key != "records"}


def sanitized_reference(reference: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in reference.items() if key != "records"}


def run_audit(
    candidate_path: Path,
    gold_path: Path,
    silver_path: Path,
    policy_path: Path,
    output_dir: Path,
    *,
    execution_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    policy = load_policy(policy_path)
    status: dict[str, Any] = {
        "schema_version": VERSION,
        "started_at": utc_now(),
        "candidate_source_id": policy["candidate_source"]["source_id"],
        "reference_source_id": policy["reference_source"]["source_id"],
        "execution_context": execution_context or {},
        "deterministic_matching_only": True,
        "fuzzy_matching": False,
        "raw_candidate_csv_committed": False,
        "raw_reference_database_committed": False,
        "raw_files_uploaded_as_artifact": False,
        "raw_rows_uploaded_as_artifact": False,
        "formal_stake": 0,
    }
    status_path = output_dir / STATUS_NAME
    try:
        candidate = load_candidate(candidate_path, policy)
        reference = load_reference(gold_path, silver_path, policy)
        comparison = compare(candidate, reference, policy)
        gate_result = evaluate_gates(candidate, reference, comparison, policy)
        all_passed = gate_result["all_frozen_gates_passed"]

        structural_block = (
            not candidate["file"]["identity_pass"]
            or candidate["invalid_dates"] > 0
            or candidate["unresolved_team_rows"] > 0
            or candidate["duplicate_key_groups"] > 0
            or reference["invalid_dates"] > 0
            or reference["duplicate_key_groups"] > 0
            or reference["missing_score_game_ids"] > 0
            or comparison["ambiguous_join_keys"] > 0
        )
        formal_outcome = (
            PASS_OUTCOME if all_passed
            else BLOCKED_OUTCOME if structural_block
            else RETAIN_OUTCOME
        )

        report = {
            "schema_version": VERSION,
            "generated_at": utc_now(),
            "formal_outcome": formal_outcome,
            "predeclaration": {
                "path": str(policy_path),
                "schema_version": policy["schema_version"],
                "ready_state": policy["next_state_if_validation_passes"]["formal_state"],
            },
            "candidate": sanitized_candidate(candidate),
            "reference": sanitized_reference(reference),
            "comparison": comparison,
            "gates": gate_result,
            "scientific_interpretation": {
                "source_role_before_audit": policy["candidate_source"]["current_formal_outcome"],
                "maximum_role_if_passed": policy["maximum_role_if_later_audit_passes"],
                "source_role_changed_by_runner": False,
                "scores_used_for_identity_repair": False,
                "fuzzy_matching_used": False,
                "manual_key_overrides_used": False,
                "many_to_many_join_used": False,
            },
            "boundaries": {
                "raw_rows_emitted": 0,
                "raw_files_emitted": False,
                "unmatched_keys_emitted": False,
                "game_ids_emitted": False,
                "candidate_csv_committed": False,
                "reference_database_committed": False,
                "opening_label_allowed": False,
                "closing_label_allowed": False,
                "point_in_time_join_allowed": False,
                "entry_price_roi_allowed": False,
                "clv_allowed": False,
                "drawdown_allowed": False,
                "betting_edge_claim_allowed": False,
                "historical_silver_replacement_allowed": False,
                "historical_gold_replacement_allowed": False,
                "model_retraining_allowed": False,
                "formal_stake": 0,
            },
            "decision": {
                "cross_source_validation_passed": all_passed,
                "ready_for_role_result_sync": all_passed,
                "ready_for_point_in_time_market_backtest": False,
                "ready_for_model_retraining": False,
                "formal_stake": 0,
            },
        }
        (output_dir / REPORT_NAME).write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        status.update({
            "completed_at": utc_now(),
            "cross_source_audit_complete": True,
            "formal_outcome": formal_outcome,
            "all_frozen_gates_passed": all_passed,
            "aggregate_report": REPORT_NAME,
            "runner_created_raw_files": False,
            "external_input_cleanup_performed_by_runner": False,
        })
        status_path.write_text(
            json.dumps(status, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return report
    except Exception as exc:
        status.update({
            "completed_at": utc_now(),
            "cross_source_audit_complete": False,
            "error": f"{type(exc).__name__}: {exc}",
            "runner_created_raw_files": False,
            "external_input_cleanup_performed_by_runner": False,
        })
        status_path.write_text(
            json.dumps(status, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        raise


def create_fixture_policy(base_policy: dict[str, Any], candidate_path: Path, seasons: list[str]) -> dict[str, Any]:
    policy = json.loads(json.dumps(base_policy))
    policy["candidate_source"]["file_name"] = candidate_path.name
    policy["candidate_source"]["file_bytes"] = candidate_path.stat().st_size
    policy["candidate_source"]["file_sha256"] = file_sha256(candidate_path)
    policy["overlap_scope"]["reference_seasons"] = seasons
    policy["overlap_scope"]["candidate_season_labels"] = [2023, 2024]
    policy["overlap_scope"]["season_mapping"] = {"2023": seasons[0], "2024": seasons[1]}
    gates = policy["frozen_execution_gates"]
    gates["minimum_reference_games"] = 4
    gates["minimum_candidate_eligible_games"] = 4
    gates["minimum_reference_match_rate"] = 1.0
    gates["minimum_candidate_match_rate"] = 1.0
    gates["minimum_matched_score_pair_rate"] = 1.0
    gates["minimum_each_season_reference_match_rate"] = 1.0
    return policy


def write_fixture_databases(gold_path: Path, silver_path: Path, rows: list[dict[str, Any]]) -> None:
    gold = sqlite3.connect(gold_path)
    silver = sqlite3.connect(silver_path)
    try:
        gold.executescript(
            """
            CREATE TABLE gold_matchup_features (
              game_id TEXT PRIMARY KEY,
              game_date TEXT NOT NULL,
              home_team_abbr TEXT NOT NULL,
              away_team_abbr TEXT NOT NULL,
              home_feature_id TEXT NOT NULL
            );
            CREATE TABLE gold_team_game_features (
              feature_id TEXT PRIMARY KEY,
              season_label TEXT NOT NULL,
              is_home INTEGER NOT NULL
            );
            """
        )
        silver.execute(
            "CREATE TABLE games (game_id TEXT PRIMARY KEY, home_score INTEGER, away_score INTEGER)"
        )
        for index, row in enumerate(rows, 1):
            game_id = f"G{index}"
            feature_id = f"H{index}"
            gold.execute(
                "INSERT INTO gold_matchup_features VALUES (?, ?, ?, ?, ?)",
                (game_id, row["date"], row["home"], row["away"], feature_id),
            )
            gold.execute(
                "INSERT INTO gold_team_game_features VALUES (?, ?, 1)",
                (feature_id, row["season_label"]),
            )
            silver.execute(
                "INSERT INTO games VALUES (?, ?, ?)",
                (game_id, row["score_home"], row["score_away"]),
            )
        gold.commit()
        silver.commit()
    finally:
        gold.close()
        silver.close()


def self_test(output_dir: Path, policy_path: Path) -> None:
    base_policy = load_policy(policy_path)
    with tempfile.TemporaryDirectory(prefix="nbavl-legacy-cross-source-self-test-") as temp_name:
        root = Path(temp_name)
        candidate_path = root / "fixture.csv"
        rows = [
            {"season": 2023, "date": "2022-10-18", "regular": "True", "playoffs": "False", "home": "bos", "away": "phi", "score_home": 126, "score_away": 117, "season_label": "2022-23"},
            {"season": 2023, "date": "2022-10-19", "regular": "True", "playoffs": "False", "home": "phx", "away": "dal", "score_home": 107, "score_away": 105, "season_label": "2022-23"},
            {"season": 2024, "date": "2023-10-24", "regular": "True", "playoffs": "False", "home": "den", "away": "lal", "score_home": 119, "score_away": 107, "season_label": "2023-24"},
            {"season": 2024, "date": "2023-10-25", "regular": "True", "playoffs": "False", "home": "ny", "away": "bos", "score_home": 104, "score_away": 108, "season_label": "2023-24"},
        ]
        with candidate_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["season", "date", "regular", "playoffs", "home", "away", "score_home", "score_away"],
            )
            writer.writeheader()
            for row in rows:
                writer.writerow({key: row[key] for key in writer.fieldnames})

        fixture_policy = create_fixture_policy(
            base_policy, candidate_path, ["2022-23", "2023-24"]
        )
        fixture_policy_path = root / "policy.json"
        fixture_policy_path.write_text(
            json.dumps(fixture_policy, indent=2) + "\n", encoding="utf-8"
        )
        gold_path = root / "gold.sqlite"
        silver_path = root / "silver.sqlite"
        write_fixture_databases(
            gold_path,
            silver_path,
            [
                {
                    "date": row["date"],
                    "home": fixture_policy["deterministic_join_contract"]["team_mapping"][row["home"]],
                    "away": fixture_policy["deterministic_join_contract"]["team_mapping"][row["away"]],
                    "score_home": row["score_home"],
                    "score_away": row["score_away"],
                    "season_label": row["season_label"],
                }
                for row in rows
            ],
        )
        report = run_audit(
            candidate_path,
            gold_path,
            silver_path,
            fixture_policy_path,
            output_dir,
            execution_context={"mode": "synthetic_self_test"},
        )
        assert report["formal_outcome"] == PASS_OUTCOME, report
        assert report["comparison"]["matched_games"] == 4, report
        assert report["comparison"]["matched_score_pair_rate"] == 1.0, report
        assert report["gates"]["all_frozen_gates_passed"] is True, report
        assert report["boundaries"]["raw_rows_emitted"] == 0, report
        assert report["boundaries"]["raw_files_emitted"] is False, report

        mismatch_silver = root / "silver-score-mismatch.sqlite"
        shutil.copy2(silver_path, mismatch_silver)
        connection = sqlite3.connect(mismatch_silver)
        try:
            connection.execute("UPDATE games SET home_score = home_score + 1 WHERE game_id = 'G1'")
            connection.commit()
        finally:
            connection.close()
        mismatch_report = run_audit(
            candidate_path,
            gold_path,
            mismatch_silver,
            fixture_policy_path,
            root / "negative-score-output",
            execution_context={"mode": "synthetic_negative_score_test"},
        )
        assert mismatch_report["formal_outcome"] == RETAIN_OUTCOME, mismatch_report
        assert (
            "minimum_matched_score_pair_rate"
            in mismatch_report["gates"]["failed_gates"]
        ), mismatch_report

        duplicate_candidate = root / "duplicate-fixture.csv"
        duplicate_rows = rows + [dict(rows[0])]
        with duplicate_candidate.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["season", "date", "regular", "playoffs", "home", "away", "score_home", "score_away"],
            )
            writer.writeheader()
            for row in duplicate_rows:
                writer.writerow({key: row[key] for key in writer.fieldnames})
        duplicate_policy = create_fixture_policy(
            base_policy, duplicate_candidate, ["2022-23", "2023-24"]
        )
        duplicate_policy["frozen_execution_gates"]["minimum_candidate_eligible_games"] = 4
        duplicate_policy_path = root / "duplicate-policy.json"
        duplicate_policy_path.write_text(
            json.dumps(duplicate_policy, indent=2) + "\n", encoding="utf-8"
        )
        duplicate_report = run_audit(
            duplicate_candidate,
            gold_path,
            silver_path,
            duplicate_policy_path,
            root / "negative-duplicate-output",
            execution_context={"mode": "synthetic_negative_duplicate_test"},
        )
        assert duplicate_report["formal_outcome"] == BLOCKED_OUTCOME, duplicate_report
        assert duplicate_report["candidate"]["duplicate_key_groups"] == 1, duplicate_report
        assert duplicate_report["boundaries"]["raw_rows_emitted"] == 0, duplicate_report
        assert duplicate_report["boundaries"]["raw_files_emitted"] is False, duplicate_report

        (output_dir / "self-test.json").write_text(
            json.dumps({
                "passed": True,
                "schema_version": VERSION,
                "positive_case": PASS_OUTCOME,
                "score_mismatch_case": RETAIN_OUTCOME,
                "duplicate_key_case": BLOCKED_OUTCOME,
            }, indent=2) + "\n",
            encoding="utf-8",
        )


def resolve_candidate(
    policy: dict[str, Any],
    candidate_csv: Path | None,
    dataset_handle: str | None,
    temp_root: Path,
) -> Path:
    if bool(candidate_csv) == bool(dataset_handle):
        raise ValueError("provide exactly one of --candidate-csv or --dataset-handle")
    if candidate_csv:
        return candidate_csv
    dataset_root = download_dataset(str(dataset_handle), temp_root / "kaggle-download")
    return locate_confirmed_candidate(dataset_root, policy)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-csv", type=Path)
    parser.add_argument("--dataset-handle")
    parser.add_argument("--gold-db", type=Path)
    parser.add_argument("--silver-db", type=Path)
    parser.add_argument("--predeclaration", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--reference-workflow-run-id")
    parser.add_argument("--reference-artifact-id")
    parser.add_argument("--reference-artifact-digest")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        self_test(args.output_dir, args.predeclaration)
        print("user-supplied legacy market cross-source audit self-test passed")
        return
    if not args.gold_db or not args.silver_db:
        parser.error("--gold-db and --silver-db are required unless --self-test is used")

    policy = load_policy(args.predeclaration)
    with tempfile.TemporaryDirectory(prefix="nbavl-legacy-cross-source-run-") as temp_name:
        candidate_path = resolve_candidate(
            policy, args.candidate_csv, args.dataset_handle, Path(temp_name)
        )
        report = run_audit(
            candidate_path,
            args.gold_db,
            args.silver_db,
            args.predeclaration,
            args.output_dir,
            execution_context={
                "mode": "real_file_audit",
                "reference_workflow_run_id": args.reference_workflow_run_id,
                "reference_artifact_id": args.reference_artifact_id,
                "reference_artifact_digest": args.reference_artifact_digest,
                "dataset_handle": args.dataset_handle,
                "kaggle_api_token_present": bool(os.environ.get("KAGGLE_API_TOKEN")),
            },
        )
    status_path = args.output_dir / STATUS_NAME
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["candidate_download_temp_deleted"] = bool(args.dataset_handle)
    status["external_gold_and_silver_inputs_deleted_by_runner"] = False
    status_path.write_text(
        json.dumps(status, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "formal_outcome": report["formal_outcome"],
        "all_frozen_gates_passed": report["gates"]["all_frozen_gates_passed"],
        "matched_games": report["comparison"]["matched_games"],
        "reference_match_rate": report["comparison"]["reference_match_rate"],
        "candidate_match_rate": report["comparison"]["candidate_match_rate"],
        "matched_score_pair_rate": report["comparison"]["matched_score_pair_rate"],
        "formal_stake": report["boundaries"]["formal_stake"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
