#!/usr/bin/env python3
"""Validate the one-time Historical Gold freeze-manifest real-Artifact request design."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

DESIGN_STATE = "HISTORICAL_GOLD_5826_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_REQUEST_DESIGN_READY"
STATUS_STATE = "HISTORICAL_GOLD_5826_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_REQUEST_DESIGN_READY_FOR_VALIDATION"
IMPLEMENTATION_STATE = (
    "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_IMPLEMENTATION_"
    "SYNTHETIC_VALIDATED_READY_FOR_REAL_ARTIFACT_EXECUTION_REQUEST_DESIGN"
)
SYNTHETIC_STATE = "HISTORICAL_GOLD_5826_FREEZE_MANIFEST_IMPLEMENTATION_SYNTHETIC_VALID"
POLICY_STATE = "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_POLICY_DESIGN_VALIDATED"
RECOVERY_STATE = "HISTORICAL_SILVER_2023_24_TWO_GAME_OFFICIAL_CDN_PBP_RECOVERY_PASS_ARTIFACT_ADOPTED"
NEXT = "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_REQUEST_READY_FOR_DRAFT"
REQUEST_PREFIX = "HISTORICAL-GOLD-5826-FREEZE-MANIFEST-REAL-ARTIFACT-EXECUTION"
BUILDER_BLOB = "ebec2d9582961531eb72297ffac922bd38bb1382"
RESULT_BLOB = "e96874e04dfbdb107ef379280c2404bf6be8bd80"
IMPLEMENTATION_STATUS_BLOB = "a2d51597262399f94b3557d341b759b84d1602f1"
ARTIFACT_DIGEST = "sha256:3ed2d28da3af58b8b72d805860a144541ac5f38106653cfbda593e16bbaa8e8d"
GOLD_SHA = "sha256:a4e94fab1681b53817f305d08c196995d406fa0566ab70d6083aa5cebfc52085"
SILVER_SHA = "sha256:48c032339402d5f75e43d7aaf8e977784aee9eceff74c9e7da952af8e1680eb8"
RECOVERY_RESULT_SHA = "sha256:97d292d56f6ee8b6f0a2d4e4471990f7c953cca7c324eb64c129066695df7c30"
EXPECTED_SEASONS = ["2019-20", "2020-21", "2021-22", "2022-23", "2023-24"]
ALLOWED_ACTIONS = [
    "actions/checkout@v4",
    "actions/setup-python@v5",
    "actions/download-artifact@v4",
    "actions/upload-artifact@v4",
]
EXPECTED_INPUT_FILES = {
    "historical-silver-multiseason-recovered-v1.sqlite.gz": (369318173, SILVER_SHA, False),
    "historical-gold-multiseason-recovered-v1.sqlite.gz": (5268851, GOLD_SHA, True),
    "two-game-official-cdn-pbp-recovery-result-v2.json": (3751, RECOVERY_RESULT_SHA, True),
}
EXPECTED_OUTPUT_FILES = {
    "historical-gold-5826-complete-corpus-freeze-manifest-v1.json",
    "historical-gold-5826-freeze-manifest-real-artifact-execution-receipt-v1.json",
}
EXPECTED_PROHIBITED_FIELDS = {
    "game_id",
    "game_date",
    "home_team_abbr",
    "away_team_abbr",
    "team_code",
    "feature_id",
    "matchup_feature_id",
    "raw_row",
    "sample_row",
    "row_level_hash",
    "individual_feature_value",
    "player_information",
    "market_price",
}
EXPECTED_RECEIPT_FIELDS = {
    "schema_version",
    "formal_outcome",
    "request_id",
    "workflow_run_id",
    "workflow_run_attempt",
    "workflow_ref",
    "github_sha",
    "execution_count_for_request",
    "maximum_execution_count_for_request",
    "request_consumed",
    "repeat_execution_allowed",
    "source_workflow_run_id",
    "source_artifact_id",
    "source_artifact_name",
    "source_artifact_archive_digest",
    "gold_gzip_sha256",
    "gold_gzip_size_bytes",
    "decompressed_gold_sqlite_sha256",
    "manifest_sha256",
    "manifest_size_bytes",
    "real_artifact_read",
    "gold_sqlite_read_only",
    "database_modified",
    "raw_rows_emitted",
    "formal_stake",
}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def _add(checks: dict[str, bool], name: str, condition: Any) -> None:
    checks[name] = bool(condition)


def synthetic_request_fixture(design: Mapping[str, Any]) -> dict[str, Any]:
    artifact = design["exact_artifact_binding"]
    return {
        "schema_version": design["future_request_contract"]["request_schema_version"],
        "request_id": f"{REQUEST_PREFIX}-2026-07-23-001",
        "formal_state": "DRAFT_FIXTURE_NOT_APPROVED_NOT_EXECUTABLE",
        "maximum_execution_count": 1,
        "execution_count": 0,
        "request_consumed": False,
        "repeat_execution_allowed": False,
        "workflow_dispatch_only": True,
        "manual_dispatch_branch": "main",
        "explicit_user_approval_required": True,
        "approval_granted": False,
        "execution_enabled": False,
        "automatic_dispatch_allowed": False,
        "source_workflow_run_id": artifact["source_workflow_run_id"],
        "source_artifact_id": artifact["artifact_id"],
        "source_artifact_name": artifact["artifact_name"],
        "source_artifact_archive_digest": artifact["artifact_archive_digest"],
        "source_artifact_expires_at": artifact["artifact_expires_at"],
        "builder_git_blob_sha": design["implementation_git_blob_sha"],
        "real_artifact_downloaded": False,
        "real_artifact_read": False,
        "semantic_manifest_created": False,
        "corpus_frozen": False,
        "formal_stake": 0,
    }


def validate_request_fixture(fixture: Mapping[str, Any], design: Mapping[str, Any]) -> bool:
    artifact = design["exact_artifact_binding"]
    prefix_ok = isinstance(fixture.get("request_id"), str) and fixture["request_id"].startswith(REQUEST_PREFIX + "-")
    return all(
        (
            fixture.get("schema_version") == "historical-gold-5826-freeze-manifest-real-artifact-execution-request-v1",
            prefix_ok,
            fixture.get("maximum_execution_count") == 1,
            fixture.get("execution_count") == 0,
            fixture.get("request_consumed") is False,
            fixture.get("repeat_execution_allowed") is False,
            fixture.get("workflow_dispatch_only") is True,
            fixture.get("manual_dispatch_branch") == "main",
            fixture.get("explicit_user_approval_required") is True,
            fixture.get("approval_granted") is False,
            fixture.get("execution_enabled") is False,
            fixture.get("automatic_dispatch_allowed") is False,
            fixture.get("source_workflow_run_id") == 29976204693,
            fixture.get("source_artifact_id") == 8551587005,
            fixture.get("source_artifact_name") == "historical-silver-gold-two-game-official-cdn-recovery-v2",
            fixture.get("source_artifact_archive_digest") == ARTIFACT_DIGEST,
            fixture.get("source_artifact_expires_at") == "2026-08-06T03:14:00Z",
            fixture.get("builder_git_blob_sha") == BUILDER_BLOB,
            fixture.get("real_artifact_downloaded") is False,
            fixture.get("real_artifact_read") is False,
            fixture.get("semantic_manifest_created") is False,
            fixture.get("corpus_frozen") is False,
            fixture.get("formal_stake") == 0,
            artifact.get("artifact_id") == fixture.get("source_artifact_id"),
        )
    )


def validate(
    design: dict[str, Any],
    status: dict[str, Any],
    implementation_status: dict[str, Any],
    synthetic_result: dict[str, Any],
    recovery_status: dict[str, Any],
    policy: dict[str, Any],
    builder_path: Path,
    implementation_status_path: Path,
    synthetic_result_path: Path,
) -> dict[str, Any]:
    checks: dict[str, bool] = {}

    _add(checks, "design_schema", design.get("schema_version") == "historical-gold-5826-freeze-manifest-real-artifact-execution-request-design-v1")
    _add(checks, "design_state", design.get("formal_state") == DESIGN_STATE)
    _add(checks, "design_role", design.get("design_role") == "ONE_TIME_EXACT_GITHUB_ARTIFACT_READ_ONLY_SEMANTIC_FREEZE_REQUEST_CONTRACT")
    _add(checks, "trigger_state", design.get("triggering_state") == IMPLEMENTATION_STATE)
    _add(checks, "builder_path", design.get("implementation_module") == str(builder_path))
    _add(checks, "builder_declared_blob", design.get("implementation_git_blob_sha") == BUILDER_BLOB)
    _add(checks, "builder_actual_blob", git_blob_sha(builder_path) == BUILDER_BLOB)
    _add(checks, "implementation_status_actual_blob", git_blob_sha(implementation_status_path) == IMPLEMENTATION_STATUS_BLOB)
    _add(checks, "synthetic_result_actual_blob", git_blob_sha(synthetic_result_path) == RESULT_BLOB)

    contract = design.get("future_request_contract", {})
    _add(checks, "request_prefix", contract.get("request_id_prefix") == REQUEST_PREFIX)
    _add(checks, "request_schema", contract.get("request_schema_version") == "historical-gold-5826-freeze-manifest-real-artifact-execution-request-v1")
    _add(checks, "one_execution", contract.get("maximum_execution_count") == 1 and contract.get("initial_execution_count") == 0)
    for key in (
        "workflow_dispatch_only",
        "explicit_user_approval_required",
        "approval_must_be_separate_from_request",
        "approval_must_bind_exact_request_id",
        "approval_must_bind_exact_request_file_sha256",
        "approval_must_bind_exact_implementation_file_sha256",
        "approval_must_bind_exact_synthetic_result_file_sha256",
        "approval_must_bind_exact_policy_file_sha256",
        "approval_must_bind_exact_source_recovery_status_file_sha256",
        "request_consumed_after_any_execution_attempt",
        "approval_before_artifact_expiry_required",
        "execution_before_artifact_expiry_required",
    ):
        _add(checks, f"contract_{key}", contract.get(key) is True)
    for key in (
        "request_reuse_after_any_execution_attempt",
        "workflow_rerun_allowed",
        "automatic_dispatch_allowed",
    ):
        _add(checks, f"contract_{key}", contract.get(key) is False)
    _add(checks, "main_only", contract.get("manual_dispatch_branch") == "main")

    artifact = design.get("exact_artifact_binding", {})
    expected_artifact = {
        "repository": "qoo109/nba-value-lab",
        "source_workflow_run_id": 29976204693,
        "source_workflow_job_id": 89108363564,
        "artifact_id": 8551587005,
        "artifact_name": "historical-silver-gold-two-game-official-cdn-recovery-v2",
        "artifact_archive_size_bytes": 374591375,
        "artifact_archive_digest": ARTIFACT_DIGEST,
        "artifact_created_at": "2026-07-23T03:14:03Z",
        "artifact_expires_at": "2026-08-06T03:14:00Z",
        "artifact_expiry_policy": "FAIL_CLOSED_NO_SILENT_REBUILD_OR_SUBSTITUTION",
    }
    for key, value in expected_artifact.items():
        _add(checks, f"artifact_{key}", artifact.get(key) == value)
    selector = artifact.get("download_selector", {})
    _add(checks, "selector_action", selector.get("action") == "actions/download-artifact@v4")
    _add(checks, "selector_repository", selector.get("repository") == "qoo109/nba-value-lab")
    _add(checks, "selector_run", selector.get("run_id") == 29976204693)
    _add(checks, "selector_name", selector.get("artifact_name") == "historical-silver-gold-two-game-official-cdn-recovery-v2")
    _add(checks, "selector_token", selector.get("github_token_required") is True)

    file_set = design.get("required_artifact_file_set", {})
    _add(checks, "input_file_count", file_set.get("exact_file_count") == 3)
    _add(checks, "no_extra_input_files", file_set.get("additional_files_allowed") is False)
    files = file_set.get("files", [])
    by_name = {item.get("filename"): item for item in files if isinstance(item, dict)}
    _add(checks, "input_names", set(by_name) == set(EXPECTED_INPUT_FILES))
    for name, (size, sha, read_allowed) in EXPECTED_INPUT_FILES.items():
        item = by_name.get(name, {})
        _add(checks, f"input_{name}_size", item.get("size_bytes") == size)
        _add(checks, f"input_{name}_sha", item.get("sha256") == sha)
        _add(checks, f"input_{name}_read", item.get("read_allowed") is read_allowed)
    _add(checks, "silver_evidence_only", by_name.get("historical-silver-multiseason-recovered-v1.sqlite.gz", {}).get("reason") == "SILVER_IS_BOUND_EVIDENCE_ONLY_NOT_NEEDED_FOR_MANIFEST_EXECUTION")
    _add(checks, "gold_temp_only", by_name.get("historical-gold-multiseason-recovered-v1.sqlite.gz", {}).get("decompress_to_temporary_sqlite_only") is True)
    _add(checks, "recovery_committed_copy", by_name.get("two-game-official-cdn-pbp-recovery-result-v2.json", {}).get("committed_copy_sha256_must_match") is True)

    steps = design.get("allowed_execution_steps", {})
    for key in (
        "checkout_exact_main_commit",
        "setup_python_3_12",
        "read_github_artifact_metadata",
        "download_exact_bound_artifact",
        "verify_artifact_not_expired",
        "verify_exact_file_set",
        "verify_all_file_sizes_and_sha256",
        "read_only_decompress_gold_gzip",
        "execute_validated_manifest_builder_once",
        "validate_aggregate_manifest",
        "create_aggregate_execution_receipt",
        "upload_exactly_one_output_artifact",
        "temporary_files_must_be_deleted_by_runner_cleanup",
    ):
        _add(checks, f"step_{key}", steps.get(key) is True)

    network = design.get("network_and_permissions_policy", {})
    _add(checks, "permissions", network.get("github_actions_permissions") == {"contents": "read", "actions": "read"})
    _add(checks, "allowed_actions", network.get("allowed_external_actions") == ALLOWED_ACTIONS)
    _add(checks, "artifact_transport_only", network.get("github_artifact_transport_only") is True)
    for key in (
        "external_network_allowed",
        "generic_http_client_allowed",
        "curl_allowed",
        "wget_allowed",
        "package_install_allowed",
        "source_archive_download_allowed",
        "odds_or_injury_download_allowed",
    ):
        _add(checks, f"network_{key}", network.get(key) is False)

    scope = design.get("read_only_execution_scope", {})
    _add(checks, "gold_read_allowed", scope.get("gold_gzip_read_allowed") is True and scope.get("gold_sqlite_read_allowed") is True)
    for key in (
        "silver_gzip_read_allowed",
        "repository_database_write_allowed",
        "artifact_file_write_allowed",
        "sqlite_write_allowed",
        "raw_row_export_allowed",
        "row_level_hash_output_allowed",
        "database_rebuild_allowed",
        "source_recovery_rerun_allowed",
        "builder_modification_allowed",
        "policy_modification_allowed",
        "synthetic_result_modification_allowed",
    ):
        _add(checks, f"scope_{key}", scope.get(key) is False)

    manifest = design.get("manifest_validation_scope", {})
    _add(checks, "manifest_schema", manifest.get("expected_manifest_schema") == "historical-gold-5826-complete-corpus-freeze-manifest-v1")
    _add(checks, "manifest_policy", manifest.get("expected_policy_id") == "HISTORICAL-GOLD-5826-COMPLETE-CORPUS-FREEZE-POLICY-2026-07-23-001")
    _add(checks, "manifest_design", manifest.get("expected_implementation_design_id") == "HISTORICAL-GOLD-5826-COMPLETE-CORPUS-FREEZE-MANIFEST-IMPLEMENTATION-DESIGN-2026-07-23-001")
    _add(checks, "manifest_counts", manifest.get("expected_gold_matchup_rows") == 5826 and manifest.get("expected_gold_team_rows") == 11652)
    _add(checks, "manifest_seasons", manifest.get("expected_seasons") == EXPECTED_SEASONS)
    _add(checks, "manifest_zero_violations", manifest.get("expected_remaining_source_exceptions") == 0 and manifest.get("expected_point_in_time_violations") == 0 and manifest.get("expected_duplicate_violations") == 0)
    _add(checks, "manifest_gates", manifest.get("expected_aggregate_validation_passed") is True and manifest.get("expected_privacy_boundaries_passed") is True)
    _add(checks, "manifest_size", manifest.get("maximum_manifest_bytes") == 1048576)
    _add(checks, "manifest_fail_closed", manifest.get("fail_closed_on_any_mismatch") is True and manifest.get("partial_manifest_allowed") is False)

    output = design.get("allowed_output_artifact", {})
    _add(checks, "output_name", output.get("artifact_name") == "historical-gold-5826-complete-corpus-freeze-manifest-real-artifact-execution-v1")
    _add(checks, "output_count", output.get("exact_file_count") == 2 and output.get("additional_files_allowed") is False)
    _add(checks, "output_size", output.get("maximum_total_uncompressed_bytes") == 1048576)
    _add(checks, "output_files", {item.get("filename") for item in output.get("files", [])} == EXPECTED_OUTPUT_FILES)
    _add(checks, "receipt_fields", set(output.get("receipt_required_fields", [])) == EXPECTED_RECEIPT_FIELDS)
    _add(checks, "prohibited_fields", set(output.get("prohibited_fields", [])) == EXPECTED_PROHIBITED_FIELDS)

    separation = design.get("approval_and_execution_separation", {})
    for key in (
        "this_design_creates_request",
        "this_design_grants_approval",
        "this_design_creates_execution_workflow",
        "this_design_enables_execution",
        "future_request_grants_approval",
        "future_request_enables_execution",
        "manual_dispatch_before_valid_request_and_approval",
        "manual_dispatch_after_artifact_expiry",
    ):
        _add(checks, f"separation_{key}", separation.get(key) is False)
    _add(checks, "future_one_dispatch", separation.get("future_approval_may_enable_exactly_one_manual_dispatch") is True)

    failure = design.get("failure_semantics", {})
    _add(checks, "failure_expiry", failure.get("artifact_expired_or_missing") == "BLOCK_BEFORE_DOWNLOAD_OR_READ_AND_REQUIRE_NEW_GOVERNED_REBUILD_LANE")
    _add(checks, "failure_approval", failure.get("request_or_approval_binding_failure") == "BLOCK_BEFORE_ARTIFACT_DOWNLOAD")
    _add(checks, "failure_manifest", failure.get("manifest_validation_failure") == "EMIT_AGGREGATE_FAIL_CLOSED_RECEIPT_NO_CANONICAL_FREEZE_CLAIM")
    _add(checks, "failure_privacy", failure.get("privacy_boundary_failure") == "BLOCK_OUTPUT_ARTIFACT")
    _add(checks, "failure_rerun", failure.get("workflow_rerun_attempt") == "BLOCK_AS_REQUEST_CONSUMED_OR_REPEAT_DISALLOWED")
    _add(checks, "failure_no_claim", failure.get("scientific_claim_on_failure") is False)

    nonauth = design.get("non_authorizations", {})
    for key, value in nonauth.items():
        _add(checks, f"nonauth_{key}", value is False)

    requirements = design.get("design_validation_requirements", {})
    _add(checks, "minimum_mutations", requirements.get("minimum_mutation_test_count", 0) >= 15)
    for key in (
        "synthetic_request_fixture_tests_required",
        "mutation_tests_required",
        "validate_no_request_record_created",
        "validate_no_approval_record_created",
        "validate_no_execution_workflow_created",
        "validate_no_artifact_downloaded_or_read",
        "validate_exact_artifact_and_file_bindings",
        "validate_expiry_fail_closed",
        "validate_one_time_consumption",
        "validate_aggregate_only_output",
        "validate_formal_stake_zero",
    ):
        _add(checks, f"requirement_{key}", requirements.get(key) is True)

    next_state = design.get("next_state_if_valid", {})
    _add(checks, "next_state", next_state.get("formal_state") == "HISTORICAL_GOLD_5826_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_REQUEST_DESIGN_VALIDATED")
    _add(checks, "next_step", next_state.get("next_research_step") == NEXT)
    _add(checks, "ready_draft", next_state.get("ready_for_request_draft") is True)
    for key in (
        "ready_for_explicit_user_approval",
        "ready_for_real_artifact_execution",
        "ready_for_corpus_freeze_claim",
        "ready_for_market_backtest",
        "ready_for_model_retraining",
    ):
        _add(checks, f"next_{key}", next_state.get(key) is False)
    _add(checks, "next_stake", next_state.get("formal_stake") == 0)

    _add(checks, "status_schema", status.get("schema_version") == "historical-gold-5826-freeze-manifest-real-artifact-execution-request-design-current-status-v1")
    _add(checks, "status_state", status.get("formal_state") == STATUS_STATE)
    evidence = status.get("triggering_evidence", {})
    _add(checks, "status_result_blob", evidence.get("synthetic_result_git_blob_sha") == RESULT_BLOB)
    _add(checks, "status_implementation_blob", evidence.get("implementation_status_git_blob_sha") == IMPLEMENTATION_STATUS_BLOB)
    _add(checks, "status_builder_blob", evidence.get("builder_git_blob_sha") == BUILDER_BLOB)
    _add(checks, "status_synthetic_tests", (evidence.get("synthetic_tests_total"), evidence.get("synthetic_tests_passed"), evidence.get("synthetic_tests_failed")) == (20, 20, 0))
    lifecycle = status.get("request_lifecycle", {})
    _add(checks, "status_design_created", lifecycle.get("request_design_created") is True)
    _add(checks, "status_max_one", lifecycle.get("maximum_execution_count") == 1 and lifecycle.get("execution_count") == 0)
    for key in (
        "request_design_validated",
        "request_draft_created",
        "request_validated",
        "approval_record_created",
        "approval_validated",
        "execution_workflow_created",
        "execution_enabled",
        "request_consumed",
        "repeat_execution_allowed",
        "automatic_dispatch_allowed",
        "real_artifact_downloaded",
        "real_artifact_read",
        "semantic_manifest_created",
        "corpus_frozen",
    ):
        _add(checks, f"status_{key}", lifecycle.get(key) is False)
    _add(checks, "status_next", status.get("next_research_step_if_valid") == NEXT)
    for key in (
        "ready_for_request_draft",
        "ready_for_explicit_user_approval",
        "ready_for_real_artifact_execution",
        "ready_for_corpus_freeze_claim",
        "ready_for_market_backtest",
        "ready_for_model_retraining",
    ):
        _add(checks, f"status_{key}", status.get(key) is False)
    _add(checks, "status_stake", status.get("formal_stake") == 0)

    _add(checks, "implementation_state", implementation_status.get("formal_state") == IMPLEMENTATION_STATE)
    impl_lifecycle = implementation_status.get("implementation_state", {})
    _add(checks, "implementation_passed", impl_lifecycle.get("implementation_module_created") is True and impl_lifecycle.get("synthetic_sqlite_tests_passed") is True)
    _add(checks, "implementation_execution_zero", impl_lifecycle.get("real_artifact_execution_count") == 0)
    _add(checks, "implementation_not_frozen", impl_lifecycle.get("corpus_frozen") is False)
    _add(checks, "implementation_ready_design", implementation_status.get("ready_for_real_artifact_execution_request_design") is True)
    _add(checks, "implementation_stake", implementation_status.get("formal_stake") == 0)

    _add(checks, "synthetic_state", synthetic_result.get("formal_state") == SYNTHETIC_STATE)
    synthetic = synthetic_result.get("synthetic_validation", {})
    _add(checks, "synthetic_20", (synthetic.get("tests_total"), synthetic.get("tests_passed"), synthetic.get("tests_failed")) == (20, 20, 0))
    _add(checks, "synthetic_no_real_read", synthetic_result.get("real_artifact_boundary", {}).get("real_artifact_read") is False)
    _add(checks, "synthetic_stake", synthetic_result.get("formal_stake") == 0)

    _add(checks, "recovery_state", recovery_status.get("formal_state") == RECOVERY_STATE)
    rec_evidence = recovery_status.get("execution_evidence", {})
    _add(checks, "recovery_artifact", rec_evidence.get("artifact_id") == 8551587005 and rec_evidence.get("artifact_archive_digest") == ARTIFACT_DIGEST)
    rec_files = recovery_status.get("artifact_files", {})
    _add(checks, "recovery_gold", rec_files.get("historical_gold", {}).get("sha256") == GOLD_SHA and rec_files.get("historical_gold", {}).get("matchup_features") == 5826)
    _add(checks, "recovery_silver", rec_files.get("historical_silver", {}).get("sha256") == SILVER_SHA)
    _add(checks, "recovery_result", rec_files.get("aggregate_result", {}).get("sha256") == RECOVERY_RESULT_SHA)
    _add(checks, "recovery_stake", recovery_status.get("formal_stake") == 0)

    _add(checks, "policy_state", policy.get("formal_state") == POLICY_STATE)
    policy_scope = policy.get("governed_scope", {})
    _add(checks, "policy_counts", policy_scope.get("gold_matchup_features") == 5826 and policy_scope.get("gold_team_game_features") == 11652)
    _add(checks, "policy_complete", policy_scope.get("documented_source_exceptions_remaining") == 0 and policy_scope.get("gold_point_in_time_violations") == 0)
    _add(checks, "policy_stake", policy.get("decision", {}).get("formal_stake") == 0)

    fixture = synthetic_request_fixture(design)
    _add(checks, "synthetic_request_fixture", validate_request_fixture(fixture, design))

    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "schema_version": "historical-gold-5826-freeze-manifest-real-artifact-request-design-validation-report-v1",
        "validated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "formal_state": "HISTORICAL_GOLD_5826_FREEZE_MANIFEST_REAL_ARTIFACT_REQUEST_DESIGN_VALID" if not failed else "HISTORICAL_GOLD_5826_FREEZE_MANIFEST_REAL_ARTIFACT_REQUEST_DESIGN_INVALID",
        "checks": checks,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "checks_failed": len(failed),
        "failed_checks": failed,
        "artifact_id": 8551587005 if not failed else None,
        "artifact_expires_at": "2026-08-06T03:14:00Z" if not failed else None,
        "synthetic_tests_passed": 20 if not failed else None,
        "request_design_validated": not failed,
        "request_draft_created": False,
        "approval_created": False,
        "execution_workflow_created": False,
        "real_artifact_downloaded": False,
        "real_artifact_read": False,
        "ready_for_request_draft": not failed,
        "ready_for_explicit_user_approval": False,
        "ready_for_real_artifact_execution": False,
        "ready_for_corpus_freeze_claim": False,
        "ready_for_market_backtest": False,
        "ready_for_model_retraining": False,
        "formal_stake": 0,
    }


def self_test(
    design: dict[str, Any],
    status: dict[str, Any],
    implementation_status: dict[str, Any],
    synthetic_result: dict[str, Any],
    recovery_status: dict[str, Any],
    policy: dict[str, Any],
    builder_path: Path,
    implementation_status_path: Path,
    synthetic_result_path: Path,
) -> dict[str, bool]:
    baseline = validate(
        design,
        status,
        implementation_status,
        synthetic_result,
        recovery_status,
        policy,
        builder_path,
        implementation_status_path,
        synthetic_result_path,
    )
    assert baseline["checks_failed"] == 0, baseline
    output: dict[str, bool] = {"baseline_passes": True}

    mutations: dict[str, tuple[str, tuple[str, ...], Any]] = {
        "wrong_artifact_id_blocks": ("design", ("exact_artifact_binding", "artifact_id"), 1),
        "wrong_artifact_digest_blocks": ("design", ("exact_artifact_binding", "artifact_archive_digest"), "sha256:bad"),
        "expired_substitution_policy_blocks": ("design", ("exact_artifact_binding", "artifact_expiry_policy"), "ALLOW_REBUILD"),
        "automatic_dispatch_blocks": ("design", ("future_request_contract", "automatic_dispatch_allowed"), True),
        "rerun_blocks": ("design", ("future_request_contract", "workflow_rerun_allowed"), True),
        "two_executions_blocks": ("design", ("future_request_contract", "maximum_execution_count"), 2),
        "approval_separation_blocks": ("design", ("future_request_contract", "approval_must_be_separate_from_request"), False),
        "wrong_branch_blocks": ("design", ("future_request_contract", "manual_dispatch_branch"), "dev"),
        "silver_read_blocks": ("design", ("read_only_execution_scope", "silver_gzip_read_allowed"), True),
        "sqlite_write_blocks": ("design", ("read_only_execution_scope", "sqlite_write_allowed"), True),
        "external_network_blocks": ("design", ("network_and_permissions_policy", "external_network_allowed"), True),
        "curl_blocks": ("design", ("network_and_permissions_policy", "curl_allowed"), True),
        "extra_action_blocks": ("design", ("network_and_permissions_policy", "allowed_external_actions"), ALLOWED_ACTIONS + ["third-party/action@v1"]),
        "wrong_gold_hash_blocks": ("design", ("required_artifact_file_set", "files", "1", "sha256"), "sha256:bad"),
        "extra_output_blocks": ("design", ("allowed_output_artifact", "exact_file_count"), 3),
        "privacy_field_missing_blocks": ("design", ("allowed_output_artifact", "prohibited_fields"), []),
        "partial_manifest_blocks": ("design", ("manifest_validation_scope", "partial_manifest_allowed"), True),
        "request_created_blocks": ("status", ("request_lifecycle", "request_draft_created"), True),
        "approval_created_blocks": ("status", ("request_lifecycle", "approval_record_created"), True),
        "execution_enabled_blocks": ("status", ("request_lifecycle", "execution_enabled"), True),
        "artifact_read_blocks": ("status", ("request_lifecycle", "real_artifact_read"), True),
        "synthetic_failure_blocks": ("synthetic", ("synthetic_validation", "tests_failed"), 1),
        "recovery_hash_blocks": ("recovery", ("artifact_files", "historical_gold", "sha256"), "sha256:bad"),
        "policy_gap_blocks": ("policy", ("governed_scope", "documented_source_exceptions_remaining"), 1),
        "nonzero_stake_blocks": ("status", ("formal_stake",), 1),
    }

    for name, (target, path, replacement) in mutations.items():
        d = copy.deepcopy(design)
        s = copy.deepcopy(status)
        i = copy.deepcopy(implementation_status)
        y = copy.deepcopy(synthetic_result)
        r = copy.deepcopy(recovery_status)
        p = copy.deepcopy(policy)
        obj = {"design": d, "status": s, "implementation": i, "synthetic": y, "recovery": r, "policy": p}[target]
        cursor: Any = obj
        for key in path[:-1]:
            if isinstance(cursor, list):
                cursor = cursor[int(key)]
            else:
                cursor = cursor[key]
        last = path[-1]
        if isinstance(cursor, list):
            cursor[int(last)] = replacement
        else:
            cursor[last] = replacement
        report = validate(d, s, i, y, r, p, builder_path, implementation_status_path, synthetic_result_path)
        output[name] = report["checks_failed"] > 0
        assert output[name], (name, report)

    fixture = synthetic_request_fixture(design)
    fixture_mutations = {
        "fixture_preapproved_blocks": ("approval_granted", True),
        "fixture_execution_enabled_blocks": ("execution_enabled", True),
        "fixture_consumed_blocks": ("request_consumed", True),
        "fixture_wrong_artifact_blocks": ("source_artifact_id", 1),
        "fixture_real_read_blocks": ("real_artifact_read", True),
        "fixture_nonzero_stake_blocks": ("formal_stake", 1),
    }
    for name, (key, value) in fixture_mutations.items():
        mutated = copy.deepcopy(fixture)
        mutated[key] = value
        output[name] = not validate_request_fixture(mutated, design)
        assert output[name], name

    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--design", required=True, type=Path)
    parser.add_argument("--current-status", required=True, type=Path)
    parser.add_argument("--implementation-status", required=True, type=Path)
    parser.add_argument("--synthetic-result", required=True, type=Path)
    parser.add_argument("--recovery-status", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--builder", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    design = load_json(args.design)
    status = load_json(args.current_status)
    implementation_status = load_json(args.implementation_status)
    synthetic_result = load_json(args.synthetic_result)
    recovery_status = load_json(args.recovery_status)
    policy = load_json(args.policy)
    report = validate(
        design,
        status,
        implementation_status,
        synthetic_result,
        recovery_status,
        policy,
        args.builder,
        args.implementation_status,
        args.synthetic_result,
    )
    if args.self_test:
        report["self_test"] = self_test(
            design,
            status,
            implementation_status,
            synthetic_result,
            recovery_status,
            policy,
            args.builder,
            args.implementation_status,
            args.synthetic_result,
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report["checks_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
