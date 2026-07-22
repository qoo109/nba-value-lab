#!/usr/bin/env python3
"""Validate the synthetic-only source-gap integration implementation v1."""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any

EXPECTED_DESIGN_STATE = "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_IMPLEMENTATION_DESIGN_READY"
EXPECTED_DESIGN_STATUS = "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_IMPLEMENTATION_DESIGN_VALIDATED"
EXPECTED_MODULE = "scripts/integrate_historical_silver_source_gap_exception_v1.py"
EXPECTED_TEST = "scripts/test_integrate_historical_silver_source_gap_exception_v1.py"
EXPECTED_FUNCTION = "integrate_documented_source_gap"
PASS_STATE = "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_IMPLEMENTATION_VALIDATION_PASS"
FORBIDDEN_IMPORT_ROOTS = {
    "sqlite3",
    "requests",
    "urllib",
    "http",
    "socket",
    "subprocess",
    "pandas",
    "numpy",
    "sqlalchemy",
}
FORBIDDEN_CALL_NAMES = {"open", "exec", "eval", "compile", "__import__"}


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def validate_module_source(path: Path) -> dict[str, Any]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    imported_roots: set[str] = set()
    called_names: set[str] = set()
    function_names: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            function_names.add(node.name)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            called_names.add(node.func.id)

    forbidden_imports = sorted(imported_roots & FORBIDDEN_IMPORT_ROOTS)
    forbidden_calls = sorted(called_names & FORBIDDEN_CALL_NAMES)
    if forbidden_imports:
        raise ValueError(f"forbidden implementation imports: {forbidden_imports}")
    if forbidden_calls:
        raise ValueError(f"forbidden implementation calls: {forbidden_calls}")
    if EXPECTED_FUNCTION not in function_names:
        raise ValueError(f"missing required transformer function: {EXPECTED_FUNCTION}")

    return {
        "parsed": True,
        "required_function_present": True,
        "forbidden_import_count": 0,
        "forbidden_call_count": 0,
    }


def validate(
    repo_root: Path,
    design_path: Path,
    design_status_path: Path,
    test_summary_path: Path,
) -> dict[str, Any]:
    design = load_json(design_path)
    design_status = load_json(design_status_path)
    test_summary = load_json(test_summary_path)

    if design.get("formal_state") != EXPECTED_DESIGN_STATE:
        raise ValueError("implementation design state mismatch")
    if design_status.get("formal_state") != EXPECTED_DESIGN_STATUS:
        raise ValueError("implementation design status mismatch")

    contract = design.get("future_module_contract", {})
    if contract.get("proposed_module") != EXPECTED_MODULE:
        raise ValueError("proposed module path mismatch")
    if contract.get("proposed_function") != f"{EXPECTED_FUNCTION}(raw_report, exception_manifest, integration_policy)":
        raise ValueError("proposed function signature mismatch")
    if contract.get("execution_model") != "PURE_IN_MEMORY_TRANSFORM":
        raise ValueError("execution model must remain pure in-memory")
    for field in (
        "database_access",
        "network_access",
        "source_archive_access",
        "row_level_input_allowed",
        "row_level_output_allowed",
        "existing_analyzer_modified_in_initial_implementation",
        "existing_builder_modified",
    ):
        if contract.get(field) is not False:
            raise ValueError(f"contract boundary changed: {field}")

    module_path = repo_root / EXPECTED_MODULE
    test_path = repo_root / EXPECTED_TEST
    if not module_path.is_file() or not test_path.is_file():
        raise ValueError("implementation module or synthetic test file is missing")
    module_validation = validate_module_source(module_path)

    if test_summary.get("successful") is not True:
        raise ValueError("synthetic test suite did not pass")
    tests_run = test_summary.get("tests_run")
    if isinstance(tests_run, bool) or not isinstance(tests_run, int) or tests_run < 12:
        raise ValueError("at least 12 synthetic tests are required")
    for field in ("real_data_read", "database_access", "network_access", "row_level_output"):
        if test_summary.get(field) is not False:
            raise ValueError(f"synthetic test boundary changed: {field}")
    if test_summary.get("formal_stake") != 0:
        raise ValueError("formal Stake must remain 0")

    return {
        "schema_version": "historical-silver-source-gap-exception-integration-implementation-validation-v1",
        "formal_state": PASS_STATE,
        "implementation_module": EXPECTED_MODULE,
        "synthetic_test_module": EXPECTED_TEST,
        "tests_run": tests_run,
        "all_tests_passed": True,
        "module_validation": module_validation,
        "execution_model": "PURE_IN_MEMORY_TRANSFORM",
        "aggregate_only": True,
        "raw_report_mutation_allowed": False,
        "database_access": False,
        "network_access": False,
        "source_archive_access": False,
        "real_rows_read": False,
        "row_level_input": False,
        "row_level_output": False,
        "coverage_analyzer_changed": False,
        "silver_builder_changed": False,
        "gold_builder_changed": False,
        "real_reference_validation_executed": False,
        "cross_source_audit_rerun": False,
        "market_backtest": False,
        "model_retraining": False,
        "betting_edge_claim": False,
        "next_research_step": "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_REAL_REFERENCE_VALIDATION_REQUEST_READY_FOR_DESIGN",
        "formal_stake": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument(
        "--design",
        type=Path,
        default=Path("data/research/historical-silver-2023-24-source-gap-exception-integration-implementation-design-v1.json"),
    )
    parser.add_argument(
        "--design-status",
        type=Path,
        default=Path("data/research/historical-silver-2023-24-source-gap-exception-integration-implementation-current-status-v1.json"),
    )
    parser.add_argument("--test-summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    result = validate(args.repo_root, args.design, args.design_status, args.test_summary)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "formal_state": result["formal_state"],
        "tests_run": result["tests_run"],
        "formal_stake": result["formal_stake"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
