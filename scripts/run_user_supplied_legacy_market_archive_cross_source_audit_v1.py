#!/usr/bin/env python3
"""Deterministic aggregate-only audit for the user-supplied legacy NBA market archive."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import shutil
import sqlite3
import tempfile
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

MANIFEST_SCHEMA = "user-supplied-legacy-market-archive-cross-source-audit-implementation-v1"
MANIFEST_STATE = "USER_SUPPLIED_LEGACY_MARKET_ARCHIVE_CROSS_SOURCE_AUDIT_IMPLEMENTATION_PREDECLARED"
POLICY_SCHEMA = "user-supplied-legacy-market-archive-cross-source-audit-predeclaration-v1"
POLICY_READY_STATE = "USER_SUPPLIED_LEGACY_MARKET_ARCHIVE_CROSS_SOURCE_AUDIT_PREDECLARATION_READY"
IMPLEMENTATION_READY = "USER_SUPPLIED_LEGACY_MARKET_ARCHIVE_CROSS_SOURCE_AUDIT_IMPLEMENTATION_READY_BUT_REAL_FILE_EXECUTION_DISABLED"
VALIDATED = "ROLE_LIMITED_LEGACY_MARKET_ARCHIVE_CROSS_SOURCE_VALIDATED"
RETAIN = "RETAIN_ROLE_LIMITED_LEGACY_MARKET_ARCHIVE_ELIGIBLE"
BLOCKED = "USER_SUPPLIED_LEGACY_MARKET_ARCHIVE_CROSS_SOURCE_AUDIT_RESEARCH_BLOCKED"
SOURCE_ID = "kaggle_cviaxmiwnptr_nba_betting_data_user_supplied"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain one JSON object")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_bool(value: Any) -> bool | None:
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return None


def parse_int(value: Any) -> int | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def parse_iso_date(value: Any) -> str | None:
    text = str(value).strip()
    try:
        return date.fromisoformat(text).isoformat()
    except (TypeError, ValueError):
        return None


def duplicate_group_count(keys: Iterable[tuple[str, ...]]) -> int:
    counts = Counter(keys)
    return sum(1 for count in counts.values() if count > 1)


def rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 9) if denominator else 0.0


def table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")}


def has_table(connection: sqlite3.Connection, table: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def open_sqlite(path: Path, temp_dir: Path, label: str) -> tuple[sqlite3.Connection, Path]:
    if not path.exists():
        raise FileNotFoundError(path)
    resolved = path
    if path.suffix == ".gz":
        resolved = temp_dir / f"{label}.sqlite"
        with gzip.open(path, "rb") as source, resolved.open("wb") as target:
            shutil.copyfileobj(source, target, length=1024 * 1024)
    connection = sqlite3.connect(resolved)
    connection.row_factory = sqlite3.Row
    return connection, resolved


def validate_manifest(manifest: dict[str, Any], policy: dict[str, Any]) -> dict[str, bool]:
    candidate = manifest.get("candidate_input") or {}
    references = manifest.get("reference_inputs") or {}
    audit = manifest.get("audit_contract") or {}
    validation = manifest.get("validation_mode") or {}
    output = manifest.get("output_boundary") or {}
    permissions = manifest.get("downstream_permissions") or {}
    next_state = manifest.get("next_state_if_validation_passes") or {}
    policy_next = policy.get("next_state_if_validation_passes") or {}

    false_permissions = (
        "ready_for_real_file_audit_execution",
        "ready_for_opening_label",
        "ready_for_closing_label",
        "ready_for_point_in_time_join",
        "ready_for_market_backtest",
        "ready_for_clv",
        "ready_for_ev",
        "ready_for_roi",
        "ready_for_drawdown",
        "ready_for_historical_silver_replacement",
        "ready_for_historical_gold_replacement",
        "ready_for_model_retraining",
        "ready_for_betting_edge_claim",
    )

    return {
        "manifest_schema": manifest.get("schema_version") == MANIFEST_SCHEMA,
        "manifest_state": manifest.get("formal_state") == MANIFEST_STATE,
        "source_id": manifest.get("source_id") == SOURCE_ID,
        "policy_schema": policy.get("schema_version") == POLICY_SCHEMA,
        "policy_binding": manifest.get("policy")
        == "data/research/user-supplied-legacy-market-archive-cross-source-audit-predeclaration-v1.json",
        "policy_ready": (
            manifest.get("policy_required_state") == POLICY_READY_STATE
            and policy_next.get("formal_state") == POLICY_READY_STATE
        ),
        "candidate_identity": (
            candidate.get("file_name") == policy.get("candidate_source", {}).get("file_name")
            and candidate.get("file_bytes") == policy.get("candidate_source", {}).get("file_bytes")
            and candidate.get("file_sha256") == policy.get("candidate_source", {}).get("file_sha256")
            and candidate.get("row_count") == policy.get("candidate_source", {}).get("row_count")
            and candidate.get("column_count") == policy.get("candidate_source", {}).get("column_count")
            and candidate.get("real_mode_exact_identity_required") is True
            and candidate.get("cleaned_or_derived_file_substitution_allowed") is False
            and candidate.get("network_download_allowed") is False
        ),
        "reference_contract": (
            references.get("gold_database", {}).get("required_table") == "gold_matchup_features"
            and references.get("silver_database", {}).get("required_table") == "games"
            and references.get("real_mode_reference_rebuild_allowed_in_validation_workflow") is False
            and references.get("network_download_allowed") is False
        ),
        "deterministic_join": (
            audit.get("join_key") == ["game_date", "home_team_abbr", "away_team_abbr"]
            and audit.get("gold_to_silver_join_key") == ["game_id"]
            and audit.get("score_validation_only") is True
            and audit.get("score_used_to_repair_identity") is False
            and audit.get("fuzzy_matching_allowed") is False
            and audit.get("manual_key_overrides_allowed") is False
            and audit.get("many_to_many_join_allowed") is False
        ),
        "validation_boundary": (
            validation.get("synthetic_fixture_only") is True
            and validation.get("real_candidate_csv_read") is False
            and validation.get("real_reference_database_read") is False
            and validation.get("network_calls") is False
            and validation.get("external_artifact_downloads") is False
            and validation.get("real_file_audit_executed") is False
        ),
        "output_boundary": (
            output.get("aggregate_report_only") is True
            and output.get("maximum_output_files") == 1
            and output.get("maximum_output_bytes") == 1048576
            and output.get("raw_rows_emitted") == 0
            and output.get("raw_files_emitted") is False
            and output.get("row_level_unmatched_examples_emitted") is False
            and output.get("candidate_csv_emitted") is False
            and output.get("reference_database_emitted") is False
            and output.get("derived_tables_emitted") is False
        ),
        "downstream_permissions": (
            all(permissions.get(key) is False for key in false_permissions)
            and permissions.get("formal_stake") == 0
        ),
        "next_state": (
            next_state.get("formal_state") == IMPLEMENTATION_READY
            and next_state.get("ready_for_separate_real_file_execution_request") is True
            and next_state.get("real_file_audit_executed") is False
            and next_state.get("source_role_changed") is False
            and next_state.get("formal_stake") == 0
        ),
    }


def load_candidate(
    path: Path,
    policy: dict[str, Any],
    manifest: dict[str, Any],
    fixture_mode: bool,
) -> dict[str, Any]:
    expected = manifest["candidate_input"]
    file_size = path.stat().st_size
    file_hash = sha256_file(path)
    mapping = policy["deterministic_join_contract"]["team_mapping"]
    season_mapping = {int(key): value for key, value in policy["overlap_scope"]["season_mapping"].items()}

    normalized: list[dict[str, Any]] = []
    rows_total = 0
    eligible_rows = 0
    excluded_non_overlap = 0
    excluded_non_regular = 0
    excluded_playoffs = 0
    invalid_dates = 0
    missing_scores = 0
    unresolved_occurrences = 0
    unresolved_codes: set[str] = set()

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        required = set(expected["required_columns"])
        missing_columns = sorted(required - set(fields))
        for row_number, row in enumerate(reader, start=2):
            rows_total += 1
            season = parse_int(row.get("season"))
            if season not in season_mapping:
                excluded_non_overlap += 1
                continue
            regular = parse_bool(row.get("regular"))
            playoffs = parse_bool(row.get("playoffs"))
            if regular is not True:
                excluded_non_regular += 1
                continue
            if playoffs is not False:
                excluded_playoffs += 1
                continue
            eligible_rows += 1

            game_date = parse_iso_date(row.get("date"))
            if game_date is None:
                invalid_dates += 1

            away_raw = str(row.get("away", "")).strip().lower()
            home_raw = str(row.get("home", "")).strip().lower()
            away = mapping.get(away_raw)
            home = mapping.get(home_raw)
            if away is None:
                unresolved_occurrences += 1
                unresolved_codes.add(away_raw or "<blank>")
            if home is None:
                unresolved_occurrences += 1
                unresolved_codes.add(home_raw or "<blank>")

            away_score = parse_int(row.get("score_away"))
            home_score = parse_int(row.get("score_home"))
            if away_score is None or home_score is None:
                missing_scores += 1

            if game_date is None or away is None or home is None:
                continue
            normalized.append({
                "row_number": row_number,
                "season_label": season_mapping[season],
                "game_date": game_date,
                "home_team_abbr": home,
                "away_team_abbr": away,
                "home_score": home_score,
                "away_score": away_score,
                "key": (game_date, home, away),
            })

    identity_checks = {
        "file_name": path.name == expected["file_name"],
        "file_bytes": file_size == expected["file_bytes"],
        "file_sha256": file_hash == expected["file_sha256"],
        "row_count": rows_total == expected["row_count"],
        "column_count": len(fields) == expected["column_count"],
        "required_columns": not missing_columns,
    }
    if fixture_mode:
        identity_checks = {key: True for key in identity_checks}

    key_counts = Counter(row["key"] for row in normalized)
    return {
        "rows": normalized,
        "identity": {
            "file_name": path.name,
            "file_bytes": file_size,
            "file_sha256": file_hash,
            "row_count": rows_total,
            "column_count": len(fields),
            "missing_required_columns": missing_columns,
            "checks": identity_checks,
            "all_checks_passed": all(identity_checks.values()),
            "fixture_identity_bypass": fixture_mode,
        },
        "counts": {
            "rows_total": rows_total,
            "eligible_rows": eligible_rows,
            "normalized_rows": len(normalized),
            "excluded_non_overlap": excluded_non_overlap,
            "excluded_non_regular": excluded_non_regular,
            "excluded_playoffs": excluded_playoffs,
            "invalid_dates": invalid_dates,
            "missing_scores": missing_scores,
            "unresolved_team_code_occurrences": unresolved_occurrences,
            "unresolved_team_codes_unique": len(unresolved_codes),
            "duplicate_key_groups": sum(1 for count in key_counts.values() if count > 1),
        },
    }


def load_reference(
    gold_path: Path,
    silver_path: Path,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    references = manifest["reference_inputs"]
    required_gold = set(references["gold_database"]["required_columns"])
    required_silver = set(references["silver_database"]["required_columns"])
    scope = set(manifest["audit_contract"]["reference_seasons"])

    with tempfile.TemporaryDirectory(prefix="nbavl-legacy-market-reference-") as temp_name:
        temp = Path(temp_name)
        gold, _ = open_sqlite(gold_path, temp, "gold")
        silver, _ = open_sqlite(silver_path, temp, "silver")
        try:
            gold_table = references["gold_database"]["required_table"]
            silver_table = references["silver_database"]["required_table"]
            gold_table_present = has_table(gold, gold_table)
            silver_table_present = has_table(silver, silver_table)
            gold_columns = table_columns(gold, gold_table) if gold_table_present else set()
            silver_columns = table_columns(silver, silver_table) if silver_table_present else set()
            missing_gold_columns = sorted(required_gold - gold_columns)
            missing_silver_columns = sorted(required_silver - silver_columns)
            schema_valid = (
                gold_table_present
                and silver_table_present
                and not missing_gold_columns
                and not missing_silver_columns
            )
            if not schema_valid:
                return {
                    "rows": [],
                    "schema": {
                        "gold_table_present": gold_table_present,
                        "silver_table_present": silver_table_present,
                        "missing_gold_columns": missing_gold_columns,
                        "missing_silver_columns": missing_silver_columns,
                        "valid": False,
                    },
                    "counts": {},
                }

            gold_rows = [dict(row) for row in gold.execute(
                "SELECT game_id, game_date, home_team_abbr, away_team_abbr FROM gold_matchup_features"
            )]
            silver_rows = [dict(row) for row in silver.execute(
                "SELECT game_id, game_date, season_label, home_team_abbr, away_team_abbr, home_score, away_score "
                "FROM games WHERE season_label IN (?,?,?,?,?)",
                tuple(sorted(scope)),
            )]
        finally:
            gold.close()
            silver.close()

    gold_id_counts = Counter(str(row["game_id"]) for row in gold_rows)
    silver_id_counts = Counter(str(row["game_id"]) for row in silver_rows)
    duplicate_gold_game_ids = sum(1 for count in gold_id_counts.values() if count > 1)
    duplicate_silver_game_ids = sum(1 for count in silver_id_counts.values() if count > 1)
    gold_by_id = {str(row["game_id"]): row for row in gold_rows if gold_id_counts[str(row["game_id"])] == 1}
    silver_by_id = {str(row["game_id"]): row for row in silver_rows if silver_id_counts[str(row["game_id"])] == 1}

    rows: list[dict[str, Any]] = []
    identity_mismatches = 0
    invalid_dates = 0
    missing_scores = 0
    missing_gold_for_silver = 0
    for game_id, silver_row in silver_by_id.items():
        gold_row = gold_by_id.get(game_id)
        if gold_row is None:
            missing_gold_for_silver += 1
            continue
        game_date = parse_iso_date(gold_row.get("game_date"))
        silver_date = parse_iso_date(silver_row.get("game_date"))
        if game_date is None or silver_date is None:
            invalid_dates += 1
            continue
        gold_identity = (
            game_date,
            str(gold_row.get("home_team_abbr", "")).strip(),
            str(gold_row.get("away_team_abbr", "")).strip(),
        )
        silver_identity = (
            silver_date,
            str(silver_row.get("home_team_abbr", "")).strip(),
            str(silver_row.get("away_team_abbr", "")).strip(),
        )
        if gold_identity != silver_identity:
            identity_mismatches += 1
            continue
        home_score = parse_int(silver_row.get("home_score"))
        away_score = parse_int(silver_row.get("away_score"))
        if home_score is None or away_score is None:
            missing_scores += 1
        rows.append({
            "game_id": game_id,
            "season_label": str(silver_row["season_label"]),
            "game_date": game_date,
            "home_team_abbr": gold_identity[1],
            "away_team_abbr": gold_identity[2],
            "home_score": home_score,
            "away_score": away_score,
            "key": gold_identity,
        })

    gold_in_scope_ids = set(gold_by_id) & set(silver_by_id)
    missing_silver_for_gold = len(set(gold_by_id) - set(silver_by_id))
    key_counts = Counter(row["key"] for row in rows)
    return {
        "rows": rows,
        "schema": {
            "gold_table_present": True,
            "silver_table_present": True,
            "missing_gold_columns": [],
            "missing_silver_columns": [],
            "valid": True,
        },
        "counts": {
            "gold_rows": len(gold_rows),
            "silver_rows_in_scope": len(silver_rows),
            "gold_silver_intersection_ids": len(gold_in_scope_ids),
            "reference_rows": len(rows),
            "duplicate_gold_game_ids": duplicate_gold_game_ids,
            "duplicate_silver_game_ids": duplicate_silver_game_ids,
            "duplicate_reference_key_groups": sum(1 for count in key_counts.values() if count > 1),
            "gold_silver_identity_mismatches": identity_mismatches,
            "missing_gold_for_silver": missing_gold_for_silver,
            "missing_silver_for_gold": missing_silver_for_gold,
            "invalid_dates": invalid_dates,
            "missing_scores": missing_scores,
        },
    }


def run_audit(
    manifest: dict[str, Any],
    policy: dict[str, Any],
    candidate_path: Path,
    gold_path: Path,
    silver_path: Path,
    fixture_mode: bool,
) -> dict[str, Any]:
    manifest_checks = validate_manifest(manifest, policy)
    manifest_failures = sorted(name for name, passed in manifest_checks.items() if not passed)

    candidate = load_candidate(candidate_path, policy, manifest, fixture_mode)
    reference = load_reference(gold_path, silver_path, manifest)
    boundary_failures = list(manifest_failures)
    if not candidate["identity"]["all_checks_passed"]:
        boundary_failures.append("candidate_exact_file_identity")
    if not reference["schema"].get("valid"):
        boundary_failures.append("reference_schema")

    ref_counts = reference.get("counts") or {}
    for key in (
        "duplicate_gold_game_ids",
        "duplicate_silver_game_ids",
        "gold_silver_identity_mismatches",
        "missing_gold_for_silver",
    ):
        if ref_counts.get(key, 0) != 0:
            boundary_failures.append(f"reference_{key}")

    candidate_rows = candidate["rows"]
    reference_rows = reference["rows"]
    candidate_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    reference_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    candidate_key_counts = Counter(row["key"] for row in candidate_rows)
    reference_key_counts = Counter(row["key"] for row in reference_rows)
    for row in candidate_rows:
        if candidate_key_counts[row["key"]] == 1:
            candidate_by_key[row["key"]] = row
    for row in reference_rows:
        if reference_key_counts[row["key"]] == 1:
            reference_by_key[row["key"]] = row

    ambiguous_keys = len({key for key, count in candidate_key_counts.items() if count > 1})
    ambiguous_keys += len({key for key, count in reference_key_counts.items() if count > 1})
    matched_keys = set(candidate_by_key) & set(reference_by_key)
    candidate_only = set(candidate_by_key) - set(reference_by_key)
    reference_only = set(reference_by_key) - set(candidate_by_key)

    score_comparable = 0
    score_matches = 0
    matched_by_season: dict[str, int] = defaultdict(int)
    reference_by_season: dict[str, int] = defaultdict(int)
    for row in reference_rows:
        reference_by_season[row["season_label"]] += 1
    for key in matched_keys:
        candidate_row = candidate_by_key[key]
        reference_row = reference_by_key[key]
        matched_by_season[reference_row["season_label"]] += 1
        scores = (
            candidate_row["home_score"],
            candidate_row["away_score"],
            reference_row["home_score"],
            reference_row["away_score"],
        )
        if all(value is not None for value in scores):
            score_comparable += 1
            if scores[0] == scores[2] and scores[1] == scores[3]:
                score_matches += 1

    gates_cfg = policy["frozen_execution_gates"]
    reference_total = ref_counts.get("silver_rows_in_scope", len(reference_rows))
    candidate_total = candidate["counts"]["eligible_rows"]
    reference_match_rate = rate(len(matched_keys), reference_total)
    candidate_match_rate = rate(len(matched_keys), candidate_total)
    score_pair_rate = rate(score_matches, score_comparable)
    each_season_rates = {
        season: rate(matched_by_season.get(season, 0), reference_by_season.get(season, 0))
        for season in manifest["audit_contract"]["reference_seasons"]
    }

    gate_results = {
        "minimum_reference_games": reference_total >= gates_cfg["minimum_reference_games"],
        "minimum_candidate_eligible_games": candidate_total >= gates_cfg["minimum_candidate_eligible_games"],
        "minimum_reference_match_rate": reference_match_rate >= gates_cfg["minimum_reference_match_rate"],
        "minimum_candidate_match_rate": candidate_match_rate >= gates_cfg["minimum_candidate_match_rate"],
        "minimum_matched_score_pair_rate": score_pair_rate >= gates_cfg["minimum_matched_score_pair_rate"],
        "minimum_each_season_reference_match_rate": all(
            value >= gates_cfg["minimum_each_season_reference_match_rate"]
            for value in each_season_rates.values()
        ),
        "maximum_candidate_duplicate_key_groups": candidate["counts"]["duplicate_key_groups"]
        <= gates_cfg["maximum_candidate_duplicate_key_groups"],
        "maximum_reference_duplicate_key_groups": ref_counts.get("duplicate_reference_key_groups", 0)
        <= gates_cfg["maximum_reference_duplicate_key_groups"],
        "maximum_ambiguous_join_keys": ambiguous_keys <= gates_cfg["maximum_ambiguous_join_keys"],
        "maximum_unresolved_team_codes": candidate["counts"]["unresolved_team_code_occurrences"]
        <= gates_cfg["maximum_unresolved_team_codes"],
        "maximum_invalid_candidate_dates": candidate["counts"]["invalid_dates"]
        <= gates_cfg["maximum_invalid_candidate_dates"],
        "maximum_invalid_reference_dates": ref_counts.get("invalid_dates", 0)
        <= gates_cfg["maximum_invalid_reference_dates"],
        "maximum_missing_candidate_scores_in_scope": candidate["counts"]["missing_scores"]
        <= gates_cfg["maximum_missing_candidate_scores_in_scope"],
        "maximum_missing_reference_scores_in_scope": ref_counts.get("missing_scores", 0)
        <= gates_cfg["maximum_missing_reference_scores_in_scope"],
        "maximum_raw_rows_emitted": 0 <= gates_cfg["maximum_raw_rows_emitted"],
        "raw_files_emitted_allowed": gates_cfg["raw_files_emitted_allowed"] is False,
    }
    failed_gates = sorted(name for name, passed in gate_results.items() if not passed)
    boundary_failures = sorted(set(boundary_failures))
    if boundary_failures:
        outcome = BLOCKED
    elif failed_gates:
        outcome = RETAIN
    else:
        outcome = VALIDATED

    report = {
        "schema_version": "user-supplied-legacy-market-archive-cross-source-audit-report-v1",
        "evaluated_at": utc_now(),
        "source_id": SOURCE_ID,
        "fixture_mode": fixture_mode,
        "real_file_audit_executed": not fixture_mode,
        "formal_outcome": outcome,
        "previous_formal_role": "ROLE_LIMITED_LEGACY_MARKET_ARCHIVE_ELIGIBLE",
        "reviewed_formal_role": VALIDATED if outcome == VALIDATED else "ROLE_LIMITED_LEGACY_MARKET_ARCHIVE_ELIGIBLE",
        "manifest_checks": manifest_checks,
        "manifest_failures": manifest_failures,
        "boundary_failures": boundary_failures,
        "candidate_file_identity": candidate["identity"],
        "candidate_counts": candidate["counts"],
        "reference_schema": reference["schema"],
        "reference_counts": ref_counts,
        "comparison": {
            "matched_games": len(matched_keys),
            "candidate_only_games": len(candidate_only),
            "reference_only_games": len(reference_only),
            "candidate_match_rate": candidate_match_rate,
            "reference_match_rate": reference_match_rate,
            "score_comparable_games": score_comparable,
            "score_pair_matches": score_matches,
            "score_pair_match_rate": score_pair_rate,
            "ambiguous_join_keys": ambiguous_keys,
            "reference_match_rate_by_season": each_season_rates,
            "unmatched_reason_counts": {
                "candidate_key_not_in_reference": len(candidate_only),
                "reference_key_not_in_candidate": len(reference_only),
                "candidate_invalid_date": candidate["counts"]["invalid_dates"],
                "candidate_unresolved_team_code": candidate["counts"]["unresolved_team_code_occurrences"],
                "candidate_duplicate_key_group": candidate["counts"]["duplicate_key_groups"],
                "reference_duplicate_key_group": ref_counts.get("duplicate_reference_key_groups", 0),
            },
        },
        "scientific_gates": gate_results,
        "failed_scientific_gates": failed_gates,
        "all_scientific_gates_passed": not failed_gates,
        "quality": {
            "network_calls_made": False,
            "external_artifacts_downloaded": False,
            "fuzzy_matching_used": False,
            "manual_key_overrides_used": False,
            "scores_used_to_repair_identity": False,
            "raw_rows_emitted": 0,
            "raw_files_emitted": False,
            "row_level_unmatched_examples_emitted": False,
            "derived_tables_emitted": False,
            "formal_stake": 0,
        },
        "downstream_permissions": {
            "ready_for_opening_label": False,
            "ready_for_closing_label": False,
            "ready_for_point_in_time_join": False,
            "ready_for_market_backtest": False,
            "ready_for_clv": False,
            "ready_for_ev": False,
            "ready_for_roi": False,
            "ready_for_drawdown": False,
            "ready_for_historical_silver_replacement": False,
            "ready_for_historical_gold_replacement": False,
            "ready_for_model_retraining": False,
            "ready_for_betting_edge_claim": False,
            "formal_stake": 0,
        },
    }
    return report


def create_fixture(root: Path, policy: dict[str, Any], games_per_season: int = 1160) -> tuple[Path, Path, Path]:
    root.mkdir(parents=True, exist_ok=True)
    candidate_path = root / "fixture_candidate.csv"
    gold_path = root / "fixture_gold.sqlite"
    silver_path = root / "fixture_silver.sqlite"
    mapping = policy["deterministic_join_contract"]["team_mapping"]
    candidate_codes = list(mapping)
    reference_codes = [mapping[code] for code in candidate_codes]
    season_mapping = {int(key): value for key, value in policy["overlap_scope"]["season_mapping"].items()}
    fields = [
        "season", "date", "regular", "playoffs", "away", "home",
        "score_away", "score_home", "q1_away", "q2_away", "q3_away", "q4_away",
        "ot_away", "q1_home", "q2_home", "q3_home", "q4_home", "ot_home",
        "whos_favored", "spread", "total", "moneyline_away", "moneyline_home",
        "h2_spread", "h2_total", "id_spread", "id_total",
    ]

    gold = sqlite3.connect(gold_path)
    silver = sqlite3.connect(silver_path)
    gold.execute(
        "CREATE TABLE gold_matchup_features (game_id TEXT PRIMARY KEY, game_date TEXT, home_team_abbr TEXT, away_team_abbr TEXT)"
    )
    silver.execute(
        "CREATE TABLE games (game_id TEXT PRIMARY KEY, game_date TEXT, season_label TEXT, home_team_abbr TEXT, away_team_abbr TEXT, home_score INTEGER, away_score INTEGER)"
    )

    with candidate_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for season_number, season_label in season_mapping.items():
            season_start = season_number - 1
            start = date(season_start, 10, 1)
            for game_index in range(games_per_season):
                day_index = game_index // 15
                slot = game_index % 15
                rotation = day_index % 29
                rotated_candidate = candidate_codes[:1] + candidate_codes[1 + rotation:] + candidate_codes[1:1 + rotation]
                rotated_reference = reference_codes[:1] + reference_codes[1 + rotation:] + reference_codes[1:1 + rotation]
                home_raw = rotated_candidate[slot]
                away_raw = rotated_candidate[29 - slot]
                home_ref = rotated_reference[slot]
                away_ref = rotated_reference[29 - slot]
                game_date = (start + timedelta(days=day_index)).isoformat()
                game_id = f"{season_label}-fixture-{game_index:04d}"
                home_score = 95 + (game_index % 24)
                away_score = 88 + ((game_index * 5) % 27)
                if home_score == away_score:
                    home_score += 1
                writer.writerow({
                    "season": season_number,
                    "date": game_date,
                    "regular": True,
                    "playoffs": False,
                    "away": away_raw,
                    "home": home_raw,
                    "score_away": away_score,
                    "score_home": home_score,
                    "q1_away": 20,
                    "q2_away": 22,
                    "q3_away": 23,
                    "q4_away": away_score - 65,
                    "ot_away": 0,
                    "q1_home": 24,
                    "q2_home": 24,
                    "q3_home": 24,
                    "q4_home": home_score - 72,
                    "ot_home": 0,
                    "whos_favored": "home",
                    "spread": 3.5,
                    "total": 210.5,
                    "moneyline_away": 140,
                    "moneyline_home": -160,
                    "h2_spread": 2.0,
                    "h2_total": 105.5,
                    "id_spread": 1,
                    "id_total": 0,
                })
                gold.execute(
                    "INSERT INTO gold_matchup_features VALUES (?,?,?,?)",
                    (game_id, game_date, home_ref, away_ref),
                )
                silver.execute(
                    "INSERT INTO games VALUES (?,?,?,?,?,?,?)",
                    (game_id, game_date, season_label, home_ref, away_ref, home_score, away_score),
                )
    gold.commit()
    silver.commit()
    gold.close()
    silver.close()
    return candidate_path, gold_path, silver_path


def mutate_candidate_team(source: Path, destination: Path) -> None:
    with source.open("r", encoding="utf-8", newline="") as input_handle:
        rows = list(csv.DictReader(input_handle))
        fields = list(rows[0])
    rows[0]["home"] = "unknown"
    with destination.open("w", encoding="utf-8", newline="") as output_handle:
        writer = csv.DictWriter(output_handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def mutate_candidate_scores(source: Path, destination: Path, count: int = 100) -> None:
    with source.open("r", encoding="utf-8", newline="") as input_handle:
        rows = list(csv.DictReader(input_handle))
        fields = list(rows[0])
    for row in rows[:count]:
        row["score_home"] = str(int(row["score_home"]) + 7)
    with destination.open("w", encoding="utf-8", newline="") as output_handle:
        writer = csv.DictWriter(output_handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def self_test(manifest: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="nbavl-legacy-market-audit-self-test-") as temp_name:
        root = Path(temp_name)
        candidate, gold, silver = create_fixture(root / "pass", policy)
        passing = run_audit(manifest, policy, candidate, gold, silver, fixture_mode=True)
        assert passing["formal_outcome"] == VALIDATED, passing
        assert passing["all_scientific_gates_passed"] is True, passing
        assert passing["comparison"]["matched_games"] == 5800, passing

        bad_team_path = root / "bad-team.csv"
        mutate_candidate_team(candidate, bad_team_path)
        bad_team = run_audit(manifest, policy, bad_team_path, gold, silver, fixture_mode=True)
        assert bad_team["formal_outcome"] == RETAIN, bad_team
        assert "maximum_unresolved_team_codes" in bad_team["failed_scientific_gates"], bad_team

        bad_score_path = root / "bad-score.csv"
        mutate_candidate_scores(candidate, bad_score_path)
        bad_score = run_audit(manifest, policy, bad_score_path, gold, silver, fixture_mode=True)
        assert bad_score["formal_outcome"] == RETAIN, bad_score
        assert "minimum_matched_score_pair_rate" in bad_score["failed_scientific_gates"], bad_score

        drifted = json.loads(json.dumps(manifest))
        drifted["downstream_permissions"]["ready_for_betting_edge_claim"] = True
        blocked = run_audit(drifted, policy, candidate, gold, silver, fixture_mode=True)
        assert blocked["formal_outcome"] == BLOCKED, blocked
        assert "downstream_permissions" in blocked["boundary_failures"], blocked

        real_identity_blocked = run_audit(manifest, policy, candidate, gold, silver, fixture_mode=False)
        assert real_identity_blocked["formal_outcome"] == BLOCKED, real_identity_blocked
        assert "candidate_exact_file_identity" in real_identity_blocked["boundary_failures"], real_identity_blocked

    return {
        "schema_version": "user-supplied-legacy-market-archive-cross-source-audit-implementation-validation-report-v1",
        "validated_at": utc_now(),
        "formal_state": IMPLEMENTATION_READY,
        "source_id": SOURCE_ID,
        "fixture_mode": True,
        "self_tests": {
            "full_frozen_gate_pass": True,
            "unresolved_team_fail_closed": True,
            "score_agreement_gate": True,
            "forbidden_permission_fail_closed": True,
            "real_file_identity_fail_closed": True,
        },
        "fixture_games": 5800,
        "real_candidate_csv_read": False,
        "real_reference_database_read": False,
        "network_calls_made": False,
        "external_artifacts_downloaded": False,
        "real_file_audit_executed": False,
        "raw_rows_emitted": 0,
        "raw_files_emitted": False,
        "ready_for_separate_real_file_execution_request": True,
        "source_role_changed": False,
        "market_backtest_ready": False,
        "betting_edge_claim_allowed": False,
        "formal_stake": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/research/user-supplied-legacy-market-archive-cross-source-audit-implementation-v1.json"),
    )
    parser.add_argument(
        "--policy",
        type=Path,
        default=Path("data/research/user-supplied-legacy-market-archive-cross-source-audit-predeclaration-v1.json"),
    )
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--reference-gold", type=Path)
    parser.add_argument("--reference-silver", type=Path)
    parser.add_argument("--fixture-mode", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = load_json(args.manifest)
    policy = load_json(args.policy)
    if args.self_test:
        report = self_test(manifest, policy)
    else:
        if not (args.candidate and args.reference_gold and args.reference_silver):
            parser.error("--candidate, --reference-gold and --reference-silver are required without --self-test")
        report = run_audit(
            manifest,
            policy,
            args.candidate,
            args.reference_gold,
            args.reference_silver,
            fixture_mode=args.fixture_mode,
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if len(payload.encode("utf-8")) > 1048576:
        raise RuntimeError("aggregate output exceeds 1 MiB boundary")
    args.output.write_text(payload, encoding="utf-8")
    print(json.dumps({
        "formal_state": report.get("formal_state"),
        "formal_outcome": report.get("formal_outcome"),
        "real_file_audit_executed": report.get("real_file_audit_executed"),
        "raw_rows_emitted": report.get("raw_rows_emitted", report.get("quality", {}).get("raw_rows_emitted")),
        "formal_stake": report.get("formal_stake", report.get("quality", {}).get("formal_stake")),
    }, indent=2))
    if report.get("formal_outcome") == BLOCKED:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
