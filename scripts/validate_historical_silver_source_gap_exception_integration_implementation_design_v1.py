#!/usr/bin/env python3
"""Validate the design-only Historical Silver source-gap integration implementation contract."""
from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DESIGN_PATH = Path(
    "data/research/historical-silver-2023-24-source-gap-exception-integration-implementation-design-v1.json"
)
STATUS_PATH = Path(
    "data/research/historical-silver-2023-24-source-gap-exception-integration-implementation-current-status-v1.json"
)
POLICY_PATH = Path(
    "data/research/historical-silver-2023-24-source-gap-exception-integration-policy-v1.json"
)
POLICY_STATUS_PATH = Path(
    "data/research/historical-silver-2023-24-source-gap-exception-integration-current-status-v1.json"
)
MANIFEST_PATH = Path(
    "data/research/historical-silver-2023-24-source-gap-exception-manifest-v1.json"
)
MANIFEST_STATUS_PATH = Path(
    "data/research/historical-silver-2023-24-source-gap-exception-current-status-v1.json"
)
DOC_PATH = Path(
    "docs/historical-silver-2023-24-source-gap-exception-integration-implementation-design-v1.md"
)
WORKFLOW_PATH = Path(
    ".github/workflows/validate-historical-silver-source-gap-exception-integration-implementation-design-v1.yml"
)

EXPECTED_PROHIBITED_FIELDS = {
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


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def require_false(mapping: dict[str, Any], keys: list[str], prefix: str) -> None:
    for key in keys:
        require(mapping.get(key) is False, f"{prefix}.{key} must be false")


def validate_design(
    design: dict[str, Any],
    status: dict[str, Any],
    policy: dict[str, Any],
    policy_status: dict[str, Any],
    manifest: dict[str, Any],
    manifest_status: dict[str, Any],
) -> None:
    require(
        design.get("schema_version")
        == "historical-silver-2023-24-source-gap-exception-integration-implementation-design-v1",
        "unexpected design schema",
    )
    require(
        design.get("formal_state")
        == "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_IMPLEMENTATION_DESIGN_READY",
        "unexpected design formal state",
    )
    require(
        design.get("design_role") == "PURE_AGGREGATE_REPORT_TRANSFORMER_CONTRACT",
        "design role must remain pure aggregate transformer contract",
    )
    require(
        design.get("triggering_state")
        == "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_POLICY_VALIDATED",
        "unexpected triggering state",
    )

    inputs = design.get("inputs", {})
    require(inputs.get("coverage_analyzer") == "scripts/analyze_historical_gold_silver_coverage_v1.py", "coverage analyzer path changed")
    require(inputs.get("exception_manifest") == str(MANIFEST_PATH), "manifest path mismatch")
    require(inputs.get("exception_manifest_status") == str(MANIFEST_STATUS_PATH), "manifest status path mismatch")
    require(inputs.get("integration_policy") == str(POLICY_PATH), "policy path mismatch")
    require(inputs.get("integration_policy_status") == str(POLICY_STATUS_PATH), "policy status path mismatch")

    require(
        policy.get("formal_state")
        == "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_POLICY_DESIGN_READY",
        "policy design state mismatch",
    )
    require(
        policy_status.get("formal_state")
        == "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_POLICY_VALIDATED",
        "policy status is not validated",
    )
    require(
        manifest.get("formal_state")
        == "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_MANIFEST_DESIGN_READY",
        "manifest design state mismatch",
    )
    require(
        manifest_status.get("formal_state")
        == "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_MANIFEST_VALIDATED",
        "manifest status is not validated",
    )

    manifest_code = manifest.get("exception_class", {}).get("exception_code")
    manifest_count = manifest.get("aggregate_scope", {}).get("source_gap_exception_games")
    manifest_unclassified = manifest.get("aggregate_scope", {}).get("unclassified_games")
    require(manifest_code == "SOURCE_ARCHIVE_PBPSTATS_GAME_ABSENT", "exception code mismatch")
    require(manifest_count == 2, "exception count must remain 2")
    require(manifest_unclassified == 0, "manifest unclassified count must remain 0")

    module = design.get("future_module_contract", {})
    require(module.get("proposed_module") == "scripts/integrate_historical_silver_source_gap_exception_v1.py", "proposed module path mismatch")
    require(module.get("proposed_function") == "integrate_documented_source_gap(raw_report, exception_manifest, integration_policy)", "proposed function mismatch")
    require(module.get("execution_model") == "PURE_IN_MEMORY_TRANSFORM", "execution model must remain pure")
    require_false(
        module,
        [
            "database_access",
            "network_access",
            "source_archive_access",
            "row_level_input_allowed",
            "row_level_output_allowed",
            "existing_analyzer_modified_in_initial_implementation",
            "existing_builder_modified",
        ],
        "future_module_contract",
    )

    validation = design.get("input_validation_contract", {})
    require(validation.get("required_exception_code") == manifest_code, "validation exception code drift")
    require(validation.get("required_exception_count") == manifest_count, "validation exception count drift")
    require(validation.get("required_season_label") == "2023-24", "season must remain 2023-24")
    require(validation.get("structural_failure_mode") == "RAISE_VALIDATION_ERROR_BEFORE_OUTPUT", "structural failure mode changed")
    require(validation.get("semantic_mismatch_mode") == "EMIT_FAIL_CLOSED_AGGREGATE_REPORT", "semantic mismatch mode changed")
    require(len(validation.get("required_raw_report_fields", [])) >= 15, "raw report requirements are incomplete")

    algorithm = design.get("recognition_algorithm", {})
    require(algorithm.get("all_conditions_required") is True, "all recognition conditions must be required")
    require(algorithm.get("partial_recognition_allowed") is False, "partial recognition must remain prohibited")
    require(len(algorithm.get("conditions", [])) >= 14, "recognition conditions are incomplete")
    require(algorithm.get("on_full_match", {}).get("documented_source_gap_exception_count") == 2, "full-match exception count changed")
    require(algorithm.get("on_full_match", {}).get("unexplained_missing_count_after_documentation") == 0, "full-match unexplained count changed")
    require(algorithm.get("on_any_semantic_mismatch", {}).get("documented_source_gap_exception_count") == 0, "fail-closed exception count must be 0")

    output = design.get("output_contract", {})
    require(output.get("schema_version") == "historical-gold-silver-coverage-with-documented-exceptions-v1", "output schema mismatch")
    require(output.get("preserve_raw_report_without_mutation") is True, "raw report mutation is prohibited")
    require(output.get("preserve_raw_formal_outcome") is True, "raw formal outcome must remain visible")
    require(output.get("additive_top_level_section") == "documented_exception_reporting", "additive section mismatch")
    require(output.get("gold_dataset_complete") is False, "Gold must not be declared complete")
    require(output.get("maximum_output_bytes") == 1048576, "output limit must remain 1 MiB")
    require(set(output.get("prohibited_fields", [])) == EXPECTED_PROHIBITED_FIELDS, "prohibited field contract changed")
    require(len(output.get("required_additive_fields", [])) == 9, "required additive fields changed")

    derived = design.get("derived_metric_rules", {})
    require(derived.get("gold_coverage_rewritten_as_complete") is False, "Gold coverage rewrite is prohibited")
    require(derived.get("negative_derived_counts_allowed") is False, "negative derived counts must be prohibited")
    require(derived.get("automatic_raw_count_adjustment_allowed") is False, "raw count adjustment is prohibited")

    tests = design.get("synthetic_test_matrix", [])
    require(isinstance(tests, list) and len(tests) >= 12, "synthetic test matrix is incomplete")

    boundaries = design.get("boundaries", {})
    require(boundaries.get("design_only") is True, "design must remain design-only")
    require_false(
        boundaries,
        [
            "production_module_created",
            "coverage_analyzer_changed",
            "database_read_or_write",
            "network_calls_made",
            "source_archives_read",
            "real_rows_read",
            "raw_files_emitted",
            "silver_builder_change",
            "gold_builder_change",
            "historical_silver_replacement",
            "historical_gold_replacement",
            "cross_source_audit_rerun",
            "market_backtest",
            "model_training_or_retraining",
            "betting_edge_claim",
        ],
        "boundaries",
    )
    require(boundaries.get("raw_rows_emitted") == 0, "raw rows must remain 0")
    require(boundaries.get("formal_stake") == 0, "formal Stake must remain 0")

    next_state = design.get("next_state_if_valid", {})
    require(
        next_state.get("formal_state")
        == "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_IMPLEMENTATION_DESIGN_VALIDATED",
        "next formal state mismatch",
    )
    require(
        next_state.get("next_research_step")
        == "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_IMPLEMENTATION_READY_FOR_IMPLEMENTATION",
        "next research step mismatch",
    )
    require(next_state.get("ready_for_synthetic_implementation") is True, "synthetic implementation should be ready")
    require_false(
        next_state,
        [
            "ready_for_real_data_execution",
            "ready_for_analyzer_replacement",
            "ready_for_silver_builder_change",
            "ready_for_gold_rebuild",
            "ready_for_cross_source_audit_rerun",
            "ready_for_market_backtest",
        ],
        "next_state_if_valid",
    )
    require(next_state.get("formal_stake") == 0, "next-state Stake must remain 0")

    require(
        status.get("formal_state")
        == "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_IMPLEMENTATION_DESIGN_VALIDATED",
        "status formal state mismatch",
    )
    require(status.get("design") == str(DESIGN_PATH), "status design path mismatch")
    require(status.get("documentation") == str(DOC_PATH), "status documentation path mismatch")
    require(status.get("workflow") == str(WORKFLOW_PATH), "status workflow path mismatch")
    require(status.get("ready_for_synthetic_implementation") is True, "status must permit synthetic implementation")
    require(status.get("production_module_created") is False, "status must not claim a production module")
    require(status.get("coverage_analyzer_changed") is False, "status must not claim analyzer changes")
    require(status.get("formal_stake") == 0, "status Stake must remain 0")


def run_mutation_tests(
    design: dict[str, Any],
    status: dict[str, Any],
    policy: dict[str, Any],
    policy_status: dict[str, Any],
    manifest: dict[str, Any],
    manifest_status: dict[str, Any],
) -> int:
    mutations: list[tuple[str, Any]] = [
        ("enable_database_access", lambda d: d["future_module_contract"].__setitem__("database_access", True)),
        ("allow_partial_recognition", lambda d: d["recognition_algorithm"].__setitem__("partial_recognition_allowed", True)),
        ("rewrite_gold_complete", lambda d: d["output_contract"].__setitem__("gold_dataset_complete", True)),
        ("raise_stake", lambda d: d["boundaries"].__setitem__("formal_stake", 1)),
        ("change_exception_count", lambda d: d["input_validation_contract"].__setitem__("required_exception_count", 1)),
        ("drop_prohibited_field", lambda d: d["output_contract"].__setitem__("prohibited_fields", d["output_contract"]["prohibited_fields"][:-1])),
        ("allow_real_execution", lambda d: d["next_state_if_valid"].__setitem__("ready_for_real_data_execution", True)),
        ("claim_module_created", lambda d: d["boundaries"].__setitem__("production_module_created", True)),
    ]
    passed = 0
    for name, mutate in mutations:
        candidate = copy.deepcopy(design)
        mutate(candidate)
        try:
            validate_design(candidate, status, policy, policy_status, manifest, manifest_status)
        except ValueError:
            passed += 1
        else:
            raise AssertionError(f"mutation was not rejected: {name}")
    return passed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    for path in (
        DESIGN_PATH,
        STATUS_PATH,
        POLICY_PATH,
        POLICY_STATUS_PATH,
        MANIFEST_PATH,
        MANIFEST_STATUS_PATH,
        DOC_PATH,
        WORKFLOW_PATH,
    ):
        require(path.exists(), f"missing required file: {path}")

    design = load_json(DESIGN_PATH)
    status = load_json(STATUS_PATH)
    policy = load_json(POLICY_PATH)
    policy_status = load_json(POLICY_STATUS_PATH)
    manifest = load_json(MANIFEST_PATH)
    manifest_status = load_json(MANIFEST_STATUS_PATH)

    validate_design(design, status, policy, policy_status, manifest, manifest_status)
    mutation_tests_passed = run_mutation_tests(
        design, status, policy, policy_status, manifest, manifest_status
    )

    report = {
        "schema_version": "historical-silver-source-gap-exception-integration-implementation-design-validation-v1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "formal_state": "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_IMPLEMENTATION_DESIGN_VALIDATED",
        "design_role": design["design_role"],
        "proposed_module": design["future_module_contract"]["proposed_module"],
        "proposed_output_schema": design["output_contract"]["schema_version"],
        "synthetic_test_cases_required": len(design["synthetic_test_matrix"]),
        "mutation_tests_passed": mutation_tests_passed,
        "design_only": True,
        "production_module_created": False,
        "coverage_analyzer_changed": False,
        "database_read_or_write": False,
        "network_calls_made": False,
        "real_rows_read": False,
        "raw_rows_emitted": 0,
        "ready_for_synthetic_implementation": True,
        "ready_for_real_data_execution": False,
        "ready_for_cross_source_audit_rerun": False,
        "ready_for_market_backtest": False,
        "formal_stake": 0,
        "next_research_step": design["next_state_if_valid"]["next_research_step"],
    }
    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    require(len(payload.encode("utf-8")) <= 1048576, "validation report exceeds 1 MiB")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
