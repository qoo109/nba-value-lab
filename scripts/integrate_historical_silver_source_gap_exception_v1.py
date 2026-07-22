#!/usr/bin/env python3
"""Pure aggregate transformer for documented Historical Silver source gaps.

This module accepts only already-aggregated dictionaries. It performs no file,
database, network, source-archive, Silver, or Gold access. The input objects are
never mutated.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

RAW_SCHEMA_VERSION = "historical-gold-silver-coverage-reconciliation-report-v1"
OUTPUT_SCHEMA_VERSION = "historical-gold-silver-coverage-with-documented-exceptions-v1"
REQUIRED_POLICY_STATE = "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_POLICY_DESIGN_READY"
REQUIRED_MANIFEST_STATE = "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_MANIFEST_DESIGN_READY"
REQUIRED_FORMAL_OUTCOME = "HISTORICAL_GOLD_SILVER_COVERAGE_RECONCILIATION_SOURCE_DATA_GAP_CONFIRMED"
REQUIRED_EXCEPTION_CODE = "SOURCE_ARCHIVE_PBPSTATS_GAME_ABSENT"
REQUIRED_SEASON = "2023-24"
REQUIRED_EXCEPTION_COUNT = 2
RECOGNIZED_STATE = "HISTORICAL_GOLD_SILVER_COVERAGE_DOCUMENTED_SOURCE_EXCEPTION_RECOGNIZED"
FAIL_CLOSED_STATE = "FAIL_CLOSED_UNEXPLAINED_COVERAGE_GAP"
POLICY_VERSION = "historical-silver-2023-24-source-gap-exception-integration-policy-v1"
MAX_OUTPUT_BYTES = 1_048_576

PROHIBITED_KEYS = {
    "game_id",
    "game_date",
    "home_team_abbr",
    "away_team_abbr",
    "team_code",
    "source_file_path",
    "source_file_hash",
    "row_level_record",
    "row_key_hash",
}

REQUIRED_RAW_PATHS = (
    "schema_version",
    "formal_outcome",
    "scope.season_labels",
    "scope.silver_game_rows",
    "scope.gold_matchup_rows",
    "coverage.missing_gold_for_silver",
    "coverage.unclassified_missing_games",
    "coverage.missing_by_season",
    "coverage.missing_by_reason",
    "coverage.missing_by_season_and_reason",
    "decision.builder_repair_required",
    "decision.formal_stake",
    "boundaries.game_ids_emitted",
    "boundaries.dates_emitted",
    "boundaries.team_codes_emitted",
    "boundaries.row_key_hashes_emitted",
)


class IntegrationValidationError(ValueError):
    """Raised when the aggregate input structure is incomplete or invalid."""


def _require_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise IntegrationValidationError(f"{name} must be a mapping")
    return value


def _get_path(payload: Mapping[str, Any], path: str) -> Any:
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            raise IntegrationValidationError(f"missing required field: {path}")
        current = current[part]
    return current


def _require_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise IntegrationValidationError(f"{name} must be an integer")
    if value < 0:
        raise IntegrationValidationError(f"{name} must be non-negative")
    return value


def _require_bool(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise IntegrationValidationError(f"{name} must be a boolean")
    return value


def _mapping_contains_prohibited_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) in PROHIBITED_KEYS:
                return True
            if _mapping_contains_prohibited_key(child):
                return True
    elif isinstance(value, list):
        return any(_mapping_contains_prohibited_key(item) for item in value)
    return False


def _validate_structure(
    raw_report: Mapping[str, Any],
    exception_manifest: Mapping[str, Any],
    integration_policy: Mapping[str, Any],
) -> None:
    for path in REQUIRED_RAW_PATHS:
        _get_path(raw_report, path)

    seasons = _get_path(raw_report, "scope.season_labels")
    if not isinstance(seasons, list) or not all(isinstance(item, str) for item in seasons):
        raise IntegrationValidationError("scope.season_labels must be a string list")

    for path in (
        "scope.silver_game_rows",
        "scope.gold_matchup_rows",
        "coverage.missing_gold_for_silver",
        "coverage.unclassified_missing_games",
        "decision.formal_stake",
    ):
        _require_int(_get_path(raw_report, path), path)

    for path in (
        "decision.builder_repair_required",
        "boundaries.game_ids_emitted",
        "boundaries.dates_emitted",
        "boundaries.team_codes_emitted",
        "boundaries.row_key_hashes_emitted",
    ):
        _require_bool(_get_path(raw_report, path), path)

    _require_mapping(_get_path(raw_report, "coverage.missing_by_season"), "coverage.missing_by_season")
    _require_mapping(_get_path(raw_report, "coverage.missing_by_reason"), "coverage.missing_by_reason")
    _require_mapping(
        _get_path(raw_report, "coverage.missing_by_season_and_reason"),
        "coverage.missing_by_season_and_reason",
    )

    for path in (
        "formal_state",
        "aggregate_scope.source_gap_exception_games",
        "aggregate_scope.unclassified_games",
        "exception_class.exception_code",
        "public_evidence_policy.aggregate_only",
        "exception_handling_policy.mode",
    ):
        _get_path(exception_manifest, path)
    _require_int(
        _get_path(exception_manifest, "aggregate_scope.source_gap_exception_games"),
        "manifest aggregate exception count",
    )
    _require_int(
        _get_path(exception_manifest, "aggregate_scope.unclassified_games"),
        "manifest unclassified count",
    )
    _require_bool(
        _get_path(exception_manifest, "public_evidence_policy.aggregate_only"),
        "manifest aggregate_only",
    )

    for path in (
        "schema_version",
        "formal_state",
        "recognition_gate.on_any_mismatch",
        "recognition_gate.partial_recognition_allowed",
        "recognition_gate.automatic_count_adjustment_allowed",
        "reporting_contract.preserve_raw_metrics",
        "reporting_contract.gold_coverage_rewritten_as_complete",
        "decision_semantics.formal_stake",
    ):
        _get_path(integration_policy, path)
    _require_bool(
        _get_path(integration_policy, "recognition_gate.partial_recognition_allowed"),
        "policy partial_recognition_allowed",
    )
    _require_bool(
        _get_path(integration_policy, "recognition_gate.automatic_count_adjustment_allowed"),
        "policy automatic_count_adjustment_allowed",
    )
    _require_bool(
        _get_path(integration_policy, "reporting_contract.preserve_raw_metrics"),
        "policy preserve_raw_metrics",
    )
    _require_bool(
        _get_path(integration_policy, "reporting_contract.gold_coverage_rewritten_as_complete"),
        "policy gold_coverage_rewritten_as_complete",
    )
    _require_int(
        _get_path(integration_policy, "decision_semantics.formal_stake"),
        "policy formal_stake",
    )


def _semantic_failure_reasons(
    raw_report: Mapping[str, Any],
    exception_manifest: Mapping[str, Any],
    integration_policy: Mapping[str, Any],
) -> list[str]:
    reasons: list[str] = []

    if raw_report["schema_version"] != RAW_SCHEMA_VERSION:
        reasons.append("RAW_SCHEMA_MISMATCH")
    if REQUIRED_SEASON not in raw_report["scope"]["season_labels"]:
        reasons.append("SEASON_SCOPE_MISMATCH")
    if raw_report["formal_outcome"] != REQUIRED_FORMAL_OUTCOME:
        reasons.append("RAW_FORMAL_OUTCOME_MISMATCH")

    raw_missing = raw_report["coverage"]["missing_gold_for_silver"]
    if raw_missing != REQUIRED_EXCEPTION_COUNT:
        reasons.append("RAW_MISSING_COUNT_MISMATCH")

    missing_by_season = raw_report["coverage"]["missing_by_season"]
    if missing_by_season.get(REQUIRED_SEASON) != REQUIRED_EXCEPTION_COUNT:
        reasons.append("SEASON_MISSING_COUNT_MISMATCH")

    season_reasons = raw_report["coverage"]["missing_by_season_and_reason"].get(REQUIRED_SEASON)
    if not isinstance(season_reasons, Mapping):
        reasons.append("SEASON_REASON_MAP_MISMATCH")
    elif season_reasons.get("missing_both_team_features") != REQUIRED_EXCEPTION_COUNT:
        reasons.append("SEASON_MISSING_REASON_MISMATCH")

    missing_reasons = raw_report["coverage"]["missing_by_reason"]
    if missing_reasons.get("missing_both_team_features") != REQUIRED_EXCEPTION_COUNT:
        reasons.append("TOTAL_MISSING_REASON_MISMATCH")
    if any(
        _require_int(value, f"coverage.missing_by_reason.{key}") != 0
        for key, value in missing_reasons.items()
        if key != "missing_both_team_features"
    ):
        reasons.append("OTHER_MISSING_REASONS_PRESENT")

    if raw_report["coverage"]["unclassified_missing_games"] != 0:
        reasons.append("UNCLASSIFIED_MISSING_PRESENT")
    if raw_report["decision"]["builder_repair_required"] is not False:
        reasons.append("BUILDER_REPAIR_REQUIRED")

    if exception_manifest["formal_state"] != REQUIRED_MANIFEST_STATE:
        reasons.append("MANIFEST_STATE_MISMATCH")
    if exception_manifest["exception_class"]["exception_code"] != REQUIRED_EXCEPTION_CODE:
        reasons.append("EXCEPTION_CODE_MISMATCH")
    if exception_manifest["aggregate_scope"]["source_gap_exception_games"] != REQUIRED_EXCEPTION_COUNT:
        reasons.append("MANIFEST_EXCEPTION_COUNT_MISMATCH")
    if exception_manifest["aggregate_scope"]["unclassified_games"] != 0:
        reasons.append("MANIFEST_UNCLASSIFIED_PRESENT")
    if exception_manifest["public_evidence_policy"]["aggregate_only"] is not True:
        reasons.append("MANIFEST_NOT_AGGREGATE_ONLY")
    if exception_manifest["exception_handling_policy"]["mode"] != "DOCUMENTED_AGGREGATE_ONLY_NO_ROW_PATCH":
        reasons.append("MANIFEST_HANDLING_MODE_MISMATCH")

    if integration_policy["schema_version"] != POLICY_VERSION:
        reasons.append("POLICY_VERSION_MISMATCH")
    if integration_policy["formal_state"] != REQUIRED_POLICY_STATE:
        reasons.append("POLICY_STATE_MISMATCH")
    if integration_policy["recognition_gate"]["on_any_mismatch"] != "FAIL_CLOSED_UNEXPLAINED_COVERAGE_GAP":
        reasons.append("POLICY_FAIL_CLOSED_MODE_MISMATCH")
    if integration_policy["recognition_gate"]["partial_recognition_allowed"] is not False:
        reasons.append("POLICY_PARTIAL_RECOGNITION_ENABLED")
    if integration_policy["recognition_gate"]["automatic_count_adjustment_allowed"] is not False:
        reasons.append("POLICY_AUTOMATIC_COUNT_ADJUSTMENT_ENABLED")
    if integration_policy["reporting_contract"]["preserve_raw_metrics"] is not True:
        reasons.append("POLICY_RAW_METRIC_PRESERVATION_DISABLED")
    if integration_policy["reporting_contract"]["gold_coverage_rewritten_as_complete"] is not False:
        reasons.append("POLICY_REWRITES_GOLD_COMPLETE")

    if any(
        raw_report["boundaries"][field] is not False
        for field in ("game_ids_emitted", "dates_emitted", "team_codes_emitted", "row_key_hashes_emitted")
    ):
        reasons.append("RAW_IDENTIFIER_BOUNDARY_VIOLATION")
    if _mapping_contains_prohibited_key(raw_report):
        reasons.append("RAW_PROHIBITED_IDENTIFIER_PRESENT")
    if _mapping_contains_prohibited_key(exception_manifest):
        reasons.append("MANIFEST_PROHIBITED_IDENTIFIER_PRESENT")

    if raw_report["decision"]["formal_stake"] != 0:
        reasons.append("RAW_FORMAL_STAKE_NONZERO")
    if integration_policy["decision_semantics"]["formal_stake"] != 0:
        reasons.append("POLICY_FORMAL_STAKE_NONZERO")

    return reasons


def integrate_documented_source_gap(
    raw_report: Mapping[str, Any],
    exception_manifest: Mapping[str, Any],
    integration_policy: Mapping[str, Any],
) -> dict[str, Any]:
    """Return a fail-closed aggregate report without mutating any input object."""

    raw_report = _require_mapping(raw_report, "raw_report")
    exception_manifest = _require_mapping(exception_manifest, "exception_manifest")
    integration_policy = _require_mapping(integration_policy, "integration_policy")
    _validate_structure(raw_report, exception_manifest, integration_policy)

    reasons = _semantic_failure_reasons(raw_report, exception_manifest, integration_policy)
    recognition_gate_passed = not reasons
    documented_count = REQUIRED_EXCEPTION_COUNT if recognition_gate_passed else 0
    raw_missing = _require_int(
        raw_report["coverage"]["missing_gold_for_silver"],
        "coverage.missing_gold_for_silver",
    )

    raw_covered_value = raw_report["coverage"].get("covered_games")
    if raw_covered_value is None:
        raw_covered = _require_int(raw_report["scope"]["silver_game_rows"], "scope.silver_game_rows") - raw_missing
        if raw_covered < 0:
            raise IntegrationValidationError("derived covered_games would be negative")
    else:
        raw_covered = _require_int(raw_covered_value, "coverage.covered_games")

    unexplained = raw_missing - documented_count
    if unexplained < 0:
        raise IntegrationValidationError("derived unexplained missing count would be negative")

    reporting = {
        "exception_policy_version": POLICY_VERSION,
        "exception_policy_state": integration_policy["formal_state"],
        "documented_source_gap_exception_code": REQUIRED_EXCEPTION_CODE,
        "documented_source_gap_exception_count": documented_count,
        "unexplained_missing_count_after_documentation": unexplained,
        "covered_or_documented_count": raw_covered + documented_count,
        "gold_matchup_count_after_documentation": raw_report["scope"]["gold_matchup_rows"],
        "gold_dataset_complete": False,
        "recognition_gate_passed": recognition_gate_passed,
        "recognition_failure_reasons": reasons,
        "documented_exception_state": RECOGNIZED_STATE if recognition_gate_passed else FAIL_CLOSED_STATE,
    }

    return {
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "raw_coverage_report": deepcopy(raw_report),
        "documented_exception_reporting": reporting,
    }


__all__ = [
    "IntegrationValidationError",
    "integrate_documented_source_gap",
    "MAX_OUTPUT_BYTES",
    "OUTPUT_SCHEMA_VERSION",
    "PROHIBITED_KEYS",
]
