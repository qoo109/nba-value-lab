#!/usr/bin/env python3
"""Validate the one-time Historical Gold real Artifact execution request.

The validator is governance-only. It never downloads or reads the bound GitHub
Actions Artifact and never executes the manifest builder. It validates exact
committed evidence, computes file digests for the later separate approval, and
runs fail-closed mutations.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

REQUEST_SCHEMA = "historical-gold-5826-freeze-manifest-real-artifact-execution-request-v1"
REQUEST_STATE = "HISTORICAL_GOLD_5826_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_REQUEST_DRAFT_READY_FOR_VALIDATION"
REQUEST_ID = "HISTORICAL-GOLD-5826-FREEZE-MANIFEST-REAL-ARTIFACT-EXECUTION-2026-07-23-001"
REQUEST_ROLE = "ONE_TIME_EXACT_GITHUB_ARTIFACT_READ_ONLY_SEMANTIC_FREEZE_REQUEST"
REQUEST_ACTION = "READ_EXACT_ADOPTED_GITHUB_ARTIFACT_AND_BUILD_AGGREGATE_SEMANTIC_FREEZE_MANIFEST_ONCE"
REQUEST_BASE = "734d2ab88265b1fb1fad6036e220df2581be9860"
REQUEST_STATUS_SCHEMA = "historical-gold-5826-freeze-manifest-real-artifact-execution-request-current-status-v1"
DESIGN_STATUS_STATE = "HISTORICAL_GOLD_5826_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_REQUEST_DESIGN_VALIDATED_READY_FOR_REQUEST_DRAFT"
IMPLEMENTATION_STATUS_STATE = "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_IMPLEMENTATION_SYNTHETIC_VALIDATED_READY_FOR_REAL_ARTIFACT_EXECUTION_REQUEST_DESIGN"
SYNTHETIC_STATE = "HISTORICAL_GOLD_5826_FREEZE_MANIFEST_IMPLEMENTATION_SYNTHETIC_VALID"
POLICY_STATE = "HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_POLICY_DESIGN_VALIDATED"
RECOVERY_STATE = "HISTORICAL_SILVER_2023_24_TWO_GAME_OFFICIAL_CDN_PBP_RECOVERY_PASS_ARTIFACT_ADOPTED"
NEXT_STATE = "HISTORICAL_GOLD_5826_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_REQUEST_VALID_AWAITING_EXPLICIT_USER_APPROVAL"
NEXT_STEP = "HISTORICAL_GOLD_5826_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_EXPLICIT_USER_APPROVAL_REQUIRED"

BUILDER_PATH = "scripts/build_historical_gold_5826_complete_corpus_freeze_manifest_v1.py"
DESIGN_PATH = "data/research/historical-gold-5826-freeze-manifest-real-artifact-execution-request-design-v1.json"
SYNTHETIC_PATH = "data/research/historical-gold-5826-complete-corpus-freeze-manifest-synthetic-implementation-result-v1.json"
POLICY_PATH = "data/research/historical-gold-5826-complete-corpus-freeze-policy-v1.json"
RECOVERY_PATH = "data/research/historical-silver-2023-24-two-game-official-cdn-pbp-recovery-current-status-v1.json"
IMPLEMENTATION_STATUS_PATH = "data/research/historical-gold-5826-complete-corpus-freeze-manifest-implementation-current-status-v1.json"

ARTIFACT_ID = 8551587005
ARTIFACT_NAME = "historical-silver-gold-two-game-official-cdn-recovery-v2"
ARTIFACT_DIGEST = "sha256:3ed2d28da3af58b8b72d805860a144541ac5f38106653cfbda593e16bbaa8e8d"
ARTIFACT_EXPIRY = "2026-08-06T03:14:00Z"
GOLD_SHA = "sha256:a4e94fab1681b53817f305d08c196995d406fa0566ab70d6083aa5cebfc52085"
SEASONS = ["2019-20", "2020-21", "2021-22", "2022-23", "2023-24"]

EXPECTED_BLOBS = {
    "implementation": "ebec2d9582961531eb72297ffac922bd38bb1382",
    "synthetic": "e96874e04dfbdb107ef379280c2404bf6be8bd80",
    "policy": "748941805f1da0c88c8f9140adc66055a8e27130",
    "recovery": "92ac9a23e620a27116b60d925a00f9ae7fc636fc",
    "design": "d299225a79ffd5d1149f4537e08b5fa600cf1a18",
}

PROHIBITED_OUTPUT = {
    "game_id", "game_date", "home_team_abbr", "away_team_abbr", "team_code",
    "feature_id", "matchup_feature_id", "raw_row", "sample_row",
    "row_level_hash", "individual_feature_value", "player_information",
    "market_price",
}
PROHIBITED_REQUEST_KEYS = {
    "game_ids", "game_dates", "team_codes", "feature_ids", "raw_rows",
    "sample_rows", "row_level_hashes", "individual_feature_values",
    "player_information", "market_prices",
}


class RequestValidationError(ValueError):
    pass


def mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RequestValidationError(f"{name} must be an object")
    return value


def get_path(payload: Mapping[str, Any], dotted: str) -> Any:
    current: Any = payload
    for part in dotted.split("."):
        if not isinstance(current, Mapping) or part not in current:
            raise RequestValidationError(f"missing field: {dotted}")
        current = current[part]
    return current


def expect(payload: Mapping[str, Any], dotted: str, expected: Any) -> None:
    actual = get_path(payload, dotted)
    if actual != expected:
        raise RequestValidationError(f"{dotted}: expected {expected!r}, got {actual!r}")


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def parse_utc(value: Any) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise RequestValidationError("timestamp must be RFC3339 UTC")
    return datetime.fromisoformat(value[:-1] + "+00:00")


def has_prohibited_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            str(key) in PROHIBITED_REQUEST_KEYS or has_prohibited_key(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(has_prohibited_key(child) for child in value)
    return False


def validate_request(
    request: Mapping[str, Any],
    request_status: Mapping[str, Any],
    design_status: Mapping[str, Any],
    implementation_status: Mapping[str, Any],
    synthetic: Mapping[str, Any],
    policy: Mapping[str, Any],
    recovery: Mapping[str, Any],
    *,
    implementation_bytes: bytes,
    synthetic_bytes: bytes,
    policy_bytes: bytes,
    recovery_bytes: bytes,
    design_bytes: bytes,
) -> None:
    request = mapping(request, "request")
    request_status = mapping(request_status, "request_status")
    design_status = mapping(design_status, "design_status")
    implementation_status = mapping(implementation_status, "implementation_status")
    synthetic = mapping(synthetic, "synthetic")
    policy = mapping(policy, "policy")
    recovery = mapping(recovery, "recovery")
    if has_prohibited_key(request):
        raise RequestValidationError("request contains prohibited row-level keys")

    for dotted, expected in {
        "schema_version": REQUEST_SCHEMA,
        "formal_state": REQUEST_STATE,
        "request_id": REQUEST_ID,
        "request_role": REQUEST_ROLE,
        "requested_action": REQUEST_ACTION,
        "request_creation_base_commit": REQUEST_BASE,
        "triggering_design": DESIGN_PATH,
        "triggering_implementation_status": IMPLEMENTATION_STATUS_PATH,
        "triggering_synthetic_result": SYNTHETIC_PATH,
        "implementation_binding.module_path": BUILDER_PATH,
        "implementation_binding.implementation_recording_pr": 139,
        "implementation_binding.implementation_recording_merge_commit": "b561c941b5fc27a0bda3fa790244ff92c35b5c0b",
        "implementation_binding.implementation_validated_head_sha": "04fdbe44f642af85bc287a02a2f978f12bf62cb0",
        "implementation_binding.implementation_git_blob_sha": EXPECTED_BLOBS["implementation"],
        "implementation_binding.implementation_file_sha256_must_be_computed_by_request_validator": True,
        "implementation_binding.approval_must_bind_computed_implementation_file_sha256": True,
        "implementation_binding.builder_modification_allowed_after_request_validation": False,
    }.items():
        expect(request, dotted, expected)

    governance = {
        "request_design_recording_pr": 141,
        "request_design_recording_merge_commit": "5c6431110b7085dec1663cf6303df5393fd4dd97",
        "request_design_validated_head_sha": "f84a217b0f4b2d144c58032f5edc793a2b92553b",
        "request_design_git_blob_sha": EXPECTED_BLOBS["design"],
        "request_design_validation_run_id": 29986783982,
        "request_design_validation_job_id": 89140319716,
        "request_design_validation_artifact_id": 8555320565,
        "request_design_validation_artifact_digest": "sha256:a4c0dce31c951fc0913bffc084411a9353928468fe1baafc0a412e050283c3e9",
        "synthetic_result_git_blob_sha": EXPECTED_BLOBS["synthetic"],
        "synthetic_validation_run_id": 29984329419,
        "synthetic_validation_job_id": 89132779309,
        "synthetic_validation_artifact_id": 8554394051,
        "synthetic_validation_artifact_digest": "sha256:1ecf4862ff87c3eb23ccb8d6b1c9860a229b54b8c76c469930dd2723da213f6f",
        "synthetic_tests_total": 20,
        "synthetic_tests_passed": 20,
        "synthetic_tests_failed": 0,
        "policy_path": POLICY_PATH,
        "policy_git_blob_sha": EXPECTED_BLOBS["policy"],
        "recovery_status_path": RECOVERY_PATH,
        "recovery_status_git_blob_sha": EXPECTED_BLOBS["recovery"],
        "implementation_status_path": IMPLEMENTATION_STATUS_PATH,
        "implementation_status_git_blob_sha": "a2d51597262399f94b3557d341b759b84d1602f1",
    }
    for field, expected in governance.items():
        expect(request, f"governance_evidence_binding.{field}", expected)

    artifact = {
        "repository": "qoo109/nba-value-lab",
        "source_workflow_run_id": 29976204693,
        "source_workflow_job_id": 89108363564,
        "artifact_id": ARTIFACT_ID,
        "artifact_name": ARTIFACT_NAME,
        "artifact_archive_size_bytes": 374591375,
        "artifact_archive_digest": ARTIFACT_DIGEST,
        "artifact_created_at": "2026-07-23T03:14:03Z",
        "artifact_expires_at": ARTIFACT_EXPIRY,
        "artifact_expiry_policy": "FAIL_CLOSED_NO_SILENT_REBUILD_OR_SUBSTITUTION",
        "download_transport": "GITHUB_ACTIONS_DOWNLOAD_ARTIFACT_V4_ONLY",
        "download_repository": "qoo109/nba-value-lab",
        "download_run_id": 29976204693,
        "github_token_required": True,
    }
    for field, expected in artifact.items():
        expect(request, f"exact_artifact_binding.{field}", expected)
    if parse_utc(get_path(request, "exact_artifact_binding.artifact_expires_at")) <= datetime.now(timezone.utc):
        raise RequestValidationError("bound Artifact has expired")

    expect(request, "required_artifact_file_set.exact_file_count", 3)
    expect(request, "required_artifact_file_set.additional_files_allowed", False)
    expected_input_files = [
        {
            "role": "HISTORICAL_SILVER_REFERENCE",
            "filename": "historical-silver-multiseason-recovered-v1.sqlite.gz",
            "size_bytes": 369318173,
            "sha256": "sha256:48c032339402d5f75e43d7aaf8e977784aee9eceff74c9e7da952af8e1680eb8",
            "read_allowed": False,
        },
        {
            "role": "HISTORICAL_GOLD_EXECUTION_INPUT",
            "filename": "historical-gold-multiseason-recovered-v1.sqlite.gz",
            "size_bytes": 5268851,
            "sha256": GOLD_SHA,
            "read_allowed": True,
            "decompress_to_temporary_sqlite_only": True,
        },
        {
            "role": "AGGREGATE_RECOVERY_RESULT",
            "filename": "two-game-official-cdn-pbp-recovery-result-v2.json",
            "size_bytes": 3751,
            "sha256": "sha256:97d292d56f6ee8b6f0a2d4e4471990f7c953cca7c324eb64c129066695df7c30",
            "read_allowed": True,
            "committed_copy": "data/research/historical-silver-2023-24-two-game-official-cdn-pbp-recovery-result-v2.json",
            "committed_copy_sha256_must_match": True,
        },
    ]
    if get_path(request, "required_artifact_file_set.files") != expected_input_files:
        raise RequestValidationError("exact Artifact file set mismatch")

    controls = {
        "maximum_execution_count": 1,
        "execution_count": 0,
        "request_consumed": False,
        "request_consumed_after_any_execution_attempt": True,
        "repeat_execution_allowed": False,
        "workflow_rerun_allowed": False,
        "workflow_dispatch_only": True,
        "manual_dispatch_branch": "main",
        "automatic_dispatch_allowed": False,
        "explicit_user_approval_required": True,
        "approval_granted": False,
        "execution_enabled": False,
        "execution_workflow_created": False,
        "real_artifact_downloaded": False,
        "real_artifact_read": False,
        "semantic_manifest_created": False,
        "corpus_frozen": False,
    }
    for field, expected in controls.items():
        expect(request, f"execution_control.{field}", expected)

    approval_flags = (
        "approval_record_must_be_separate",
        "approval_must_bind_exact_request_id",
        "approval_must_bind_request_file_sha256_from_validation_artifact",
        "approval_must_bind_implementation_file_sha256_from_validation_artifact",
        "approval_must_bind_synthetic_result_file_sha256_from_validation_artifact",
        "approval_must_bind_policy_file_sha256_from_validation_artifact",
        "approval_must_bind_recovery_status_file_sha256_from_validation_artifact",
        "approval_must_bind_request_design_file_sha256_from_validation_artifact",
        "approval_must_bind_exact_artifact_id_and_digest",
        "approval_must_name_repository_owner",
        "approval_may_not_expand_artifact_file_set",
        "approval_may_not_expand_allowed_output",
        "approval_may_not_enable_automatic_dispatch",
        "approval_may_not_allow_rerun",
        "approval_must_be_recorded_before_artifact_expiry",
    )
    for field in approval_flags:
        expect(request, f"approval_binding_requirements.{field}", True)
    expect(request, "approval_binding_requirements.approval_must_preserve_maximum_execution_count", 1)

    future = mapping(get_path(request, "allowed_future_execution"), "allowed_future_execution")
    true_fields = {
        "checkout_exact_main_commit", "setup_python_3_12", "read_github_artifact_metadata",
        "download_exact_bound_artifact", "verify_artifact_not_expired", "verify_exact_file_set",
        "verify_all_file_sizes_and_sha256", "read_only_decompress_gold_gzip",
        "execute_validated_manifest_builder_once", "validate_aggregate_manifest",
        "create_aggregate_execution_receipt", "upload_exactly_one_output_artifact",
    }
    false_fields = {
        "external_network_allowed", "generic_http_client_allowed", "curl_allowed",
        "wget_allowed", "package_install_allowed", "source_archive_download_allowed",
        "odds_or_injury_download_allowed", "silver_database_read_allowed",
        "repository_database_write_allowed", "sqlite_write_allowed", "raw_row_export_allowed",
        "row_level_hash_output_allowed", "database_rebuild_allowed", "source_recovery_rerun_allowed",
        "builder_modification_allowed", "policy_modification_allowed", "synthetic_result_modification_allowed",
    }
    for field in true_fields:
        if future.get(field) is not True:
            raise RequestValidationError(f"allowed_future_execution.{field} must be true")
    for field in false_fields:
        if future.get(field) is not False:
            raise RequestValidationError(f"allowed_future_execution.{field} must be false")
    expect(request, "allowed_future_execution.github_actions_permissions_contents", "read")
    expect(request, "allowed_future_execution.github_actions_permissions_actions", "read")

    expected_manifest = {
        "manifest_schema": "historical-gold-5826-complete-corpus-freeze-manifest-v1",
        "policy_id": "HISTORICAL-GOLD-5826-COMPLETE-CORPUS-FREEZE-POLICY-2026-07-23-001",
        "implementation_design_id": "HISTORICAL-GOLD-5826-COMPLETE-CORPUS-FREEZE-MANIFEST-IMPLEMENTATION-DESIGN-2026-07-23-001",
        "gold_matchup_rows": 5826,
        "gold_team_rows": 11652,
        "seasons": SEASONS,
        "remaining_source_exceptions": 0,
        "point_in_time_violations": 0,
        "duplicate_violations": 0,
        "aggregate_validation_passed": True,
        "privacy_boundaries_passed": True,
        "maximum_manifest_bytes": 1048576,
        "fail_closed_on_any_mismatch": True,
        "partial_manifest_allowed": False,
    }
    for field, expected in expected_manifest.items():
        expect(request, f"expected_manifest_result.{field}", expected)

    for dotted, expected in {
        "allowed_future_output.single_artifact_only": True,
        "allowed_future_output.artifact_name": "historical-gold-5826-complete-corpus-freeze-manifest-real-artifact-execution-v1",
        "allowed_future_output.exact_file_count": 2,
        "allowed_future_output.additional_files_allowed": False,
        "allowed_future_output.maximum_total_uncompressed_bytes": 1048576,
    }.items():
        expect(request, dotted, expected)
    expected_output_files = [
        {
            "filename": "historical-gold-5826-complete-corpus-freeze-manifest-v1.json",
            "role": "CANONICAL_AGGREGATE_SEMANTIC_MANIFEST",
        },
        {
            "filename": "historical-gold-5826-freeze-manifest-real-artifact-execution-receipt-v1.json",
            "role": "ONE_TIME_EXECUTION_RECEIPT",
        },
    ]
    if get_path(request, "allowed_future_output.files") != expected_output_files:
        raise RequestValidationError("allowed output file set mismatch")
    if set(get_path(request, "allowed_future_output.prohibited_fields")) != PROHIBITED_OUTPUT:
        raise RequestValidationError("prohibited output field set mismatch")

    non_auth = mapping(get_path(request, "non_authorizations"), "non_authorizations")
    if not non_auth or any(value is not False for value in non_auth.values()):
        raise RequestValidationError("all non_authorizations must remain false")

    requirements = mapping(get_path(request, "request_validation_requirements"), "request_validation_requirements")
    required_flags = {
        "compute_request_file_sha256", "compute_implementation_file_sha256",
        "compute_synthetic_result_file_sha256", "compute_policy_file_sha256",
        "compute_recovery_status_file_sha256", "compute_request_design_file_sha256",
        "validate_exact_request_id", "validate_artifact_not_expired",
        "validate_exact_artifact_and_file_bindings", "validate_execution_count_zero",
        "validate_request_not_consumed", "validate_approval_not_granted",
        "validate_execution_disabled", "validate_no_execution_workflow_created",
        "validate_no_approval_record_created", "validate_no_artifact_downloaded_or_read",
        "validate_aggregate_only_output", "mutation_tests_required", "validate_formal_stake_zero",
    }
    for field in required_flags:
        if requirements.get(field) is not True:
            raise RequestValidationError(f"request_validation_requirements.{field} must be true")
    if type(requirements.get("minimum_mutation_test_count")) is not int or requirements["minimum_mutation_test_count"] < 20:
        raise RequestValidationError("minimum mutation count must be at least 20")

    expect(request, "next_state_if_valid.formal_state", NEXT_STATE)
    expect(request, "next_state_if_valid.next_research_step", NEXT_STEP)
    expect(request, "next_state_if_valid.ready_for_explicit_user_approval", True)
    for field in (
        "ready_for_real_artifact_execution", "ready_for_execution_workflow_implementation",
        "ready_for_corpus_freeze_claim", "ready_for_market_backtest", "ready_for_model_retraining",
    ):
        expect(request, f"next_state_if_valid.{field}", False)
    expect(request, "next_state_if_valid.formal_stake", 0)
    expect(request, "formal_stake", 0)

    # Request status must describe the pre-validation state only.
    expect(request_status, "schema_version", REQUEST_STATUS_SCHEMA)
    expect(request_status, "formal_state", REQUEST_STATE)
    expect(request_status, "request_id", REQUEST_ID)
    expect(request_status, "validation_state.request_created", True)
    expect(request_status, "validation_state.request_validated", False)
    for field, expected in {
        "maximum_execution_count": 1, "execution_count": 0, "request_consumed": False,
        "repeat_execution_allowed": False, "workflow_dispatch_only": True,
        "automatic_dispatch_allowed": False, "explicit_user_approval_required": True,
        "approval_granted": False, "execution_enabled": False,
        "execution_workflow_created": False, "real_artifact_downloaded": False,
        "real_artifact_read": False, "semantic_manifest_created": False, "corpus_frozen": False,
    }.items():
        expect(request_status, f"execution_control.{field}", expected)
    expect(request_status, "ready_for_explicit_user_approval", False)
    expect(request_status, "ready_for_real_artifact_execution", False)
    expect(request_status, "formal_stake", 0)

    # Canonical upstream evidence.
    expect(design_status, "formal_state", DESIGN_STATUS_STATE)
    expect(design_status, "design_validation_evidence.workflow_run_id", 29986783982)
    expect(design_status, "design_validation_evidence.workflow_job_id", 89140319716)
    expect(design_status, "design_validation_evidence.validation_artifact_id", 8555320565)
    expect(design_status, "design_validation_evidence.validation_artifact_digest", "sha256:a4c0dce31c951fc0913bffc084411a9353928468fe1baafc0a412e050283c3e9")
    expect(design_status, "request_lifecycle.request_design_validated", True)
    expect(design_status, "request_lifecycle.request_draft_created", False)
    expect(design_status, "request_lifecycle.execution_count", 0)
    expect(design_status, "request_lifecycle.request_consumed", False)
    expect(design_status, "request_lifecycle.real_artifact_downloaded", False)
    expect(design_status, "request_lifecycle.real_artifact_read", False)
    expect(design_status, "ready_for_request_draft", True)
    expect(design_status, "ready_for_explicit_user_approval", False)
    expect(design_status, "ready_for_real_artifact_execution", False)
    expect(design_status, "formal_stake", 0)

    expect(implementation_status, "formal_state", IMPLEMENTATION_STATUS_STATE)
    expect(implementation_status, "implementation_state.implementation_module_created", True)
    expect(implementation_status, "implementation_state.synthetic_sqlite_tests_executed", True)
    expect(implementation_status, "implementation_state.synthetic_tests_passed", 20)
    expect(implementation_status, "implementation_state.real_artifact_execution_workflow_created", False)
    expect(implementation_status, "implementation_state.real_artifact_execution_approved", False)
    expect(implementation_status, "implementation_state.real_artifact_execution_count", 0)
    expect(implementation_status, "implementation_state.semantic_manifest_created", False)
    expect(implementation_status, "implementation_state.corpus_frozen", False)
    expect(implementation_status, "ready_for_real_artifact_execution_request_design", True)
    expect(implementation_status, "ready_for_real_artifact_execution", False)
    expect(implementation_status, "formal_stake", 0)

    expect(synthetic, "formal_state", SYNTHETIC_STATE)
    expect(synthetic, "synthetic_validation.tests_total", 20)
    expect(synthetic, "synthetic_validation.tests_passed", 20)
    expect(synthetic, "synthetic_validation.tests_failed", 0)
    expect(synthetic, "real_artifact_boundary.preferred_artifact_id", ARTIFACT_ID)
    expect(synthetic, "real_artifact_boundary.preferred_artifact_digest", ARTIFACT_DIGEST)
    expect(synthetic, "real_artifact_boundary.preferred_artifact_expires_at", ARTIFACT_EXPIRY)
    for field in (
        "real_artifact_downloaded", "real_artifact_read", "real_execution_workflow_created",
        "real_execution_approved", "semantic_manifest_created", "corpus_frozen",
    ):
        expect(synthetic, f"real_artifact_boundary.{field}", False)
    expect(synthetic, "real_artifact_boundary.real_execution_count", 0)
    expect(synthetic, "formal_stake", 0)

    expect(policy, "formal_state", POLICY_STATE)
    expect(policy, "policy_id", "HISTORICAL-GOLD-5826-COMPLETE-CORPUS-FREEZE-POLICY-2026-07-23-001")
    expect(policy, "governed_scope.gold_matchup_features", 5826)
    expect(policy, "governed_scope.gold_team_game_features", 11652)
    expect(policy, "governed_scope.documented_source_exceptions_remaining", 0)
    expect(policy, "governed_scope.gold_point_in_time_violations", 0)
    expect(policy, "immutable_evidence_bindings.adopted_artifact_id", ARTIFACT_ID)
    expect(policy, "immutable_evidence_bindings.adopted_artifact_digest", ARTIFACT_DIGEST)
    expect(policy, "immutable_evidence_bindings.historical_gold_sha256", GOLD_SHA)
    expect(policy, "decision.formal_stake", 0)

    expect(recovery, "formal_state", RECOVERY_STATE)
    expect(recovery, "source_exception_state.remaining_documented_exception_count", 0)
    expect(recovery, "adoption.new_gold_matchup_reference_count", 5826)
    expect(recovery, "execution_evidence.artifact_id", ARTIFACT_ID)
    expect(recovery, "execution_evidence.artifact_archive_digest", ARTIFACT_DIGEST)
    expect(recovery, "artifact_files.historical_gold.sha256", GOLD_SHA)
    expect(recovery, "formal_stake", 0)

    actual_blobs = {
        "implementation": git_blob_sha(implementation_bytes),
        "synthetic": git_blob_sha(synthetic_bytes),
        "policy": git_blob_sha(policy_bytes),
        "recovery": git_blob_sha(recovery_bytes),
        "design": git_blob_sha(design_bytes),
    }
    if actual_blobs != EXPECTED_BLOBS:
        raise RequestValidationError(f"upstream Git blob mismatch: {actual_blobs}")


def mutation_tests(
    request: Mapping[str, Any], request_status: Mapping[str, Any],
    design_status: Mapping[str, Any], implementation_status: Mapping[str, Any],
    synthetic: Mapping[str, Any], policy: Mapping[str, Any], recovery: Mapping[str, Any],
    **bytes_inputs: bytes,
) -> int:
    mutations = [
        ("request_id", "OTHER"),
        ("formal_state", "OTHER"),
        ("request_creation_base_commit", "OTHER"),
        ("implementation_binding.implementation_git_blob_sha", "OTHER"),
        ("governance_evidence_binding.request_design_validation_run_id", 1),
        ("governance_evidence_binding.synthetic_tests_passed", 19),
        ("exact_artifact_binding.artifact_id", 1),
        ("exact_artifact_binding.artifact_archive_digest", "sha256:wrong"),
        ("exact_artifact_binding.artifact_expires_at", "2026-07-01T00:00:00Z"),
        ("required_artifact_file_set.exact_file_count", 2),
        ("execution_control.maximum_execution_count", 2),
        ("execution_control.execution_count", 1),
        ("execution_control.request_consumed", True),
        ("execution_control.repeat_execution_allowed", True),
        ("execution_control.workflow_rerun_allowed", True),
        ("execution_control.automatic_dispatch_allowed", True),
        ("execution_control.approval_granted", True),
        ("execution_control.execution_enabled", True),
        ("execution_control.execution_workflow_created", True),
        ("execution_control.real_artifact_downloaded", True),
        ("execution_control.real_artifact_read", True),
        ("allowed_future_execution.silver_database_read_allowed", True),
        ("allowed_future_execution.package_install_allowed", True),
        ("allowed_future_execution.repository_database_write_allowed", True),
        ("expected_manifest_result.gold_matchup_rows", 5824),
        ("expected_manifest_result.remaining_source_exceptions", 2),
        ("allowed_future_output.exact_file_count", 3),
        ("next_state_if_valid.ready_for_real_artifact_execution", True),
        ("non_authorizations.market_backtest", True),
        ("formal_stake", 1),
    ]
    passed = 0
    for dotted, replacement in mutations:
        candidate = copy.deepcopy(request)
        current: Any = candidate
        parts = dotted.split(".")
        for part in parts[:-1]:
            current = current[part]
        current[parts[-1]] = replacement
        try:
            validate_request(candidate, request_status, design_status, implementation_status, synthetic, policy, recovery, **bytes_inputs)
        except RequestValidationError:
            passed += 1
        else:
            raise RequestValidationError(f"mutation not rejected: {dotted}")

    extra_cases: list[tuple[str, Mapping[str, Any], Mapping[str, Any], Mapping[str, Any], Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]] = []
    privacy = copy.deepcopy(request)
    privacy["raw_rows"] = [{"synthetic": True}]
    extra_cases.append(("privacy", privacy, request_status, design_status, implementation_status, synthetic, recovery))

    bad_status = copy.deepcopy(request_status)
    bad_status["execution_control"]["approval_granted"] = True
    extra_cases.append(("request_status", request, bad_status, design_status, implementation_status, synthetic, recovery))

    bad_design = copy.deepcopy(design_status)
    bad_design["request_lifecycle"]["request_draft_created"] = True
    extra_cases.append(("design", request, request_status, bad_design, implementation_status, synthetic, recovery))

    bad_synthetic = copy.deepcopy(synthetic)
    bad_synthetic["synthetic_validation"]["tests_failed"] = 1
    extra_cases.append(("synthetic", request, request_status, design_status, implementation_status, bad_synthetic, recovery))

    bad_recovery = copy.deepcopy(recovery)
    bad_recovery["source_exception_state"]["remaining_documented_exception_count"] = 2
    extra_cases.append(("recovery", request, request_status, design_status, implementation_status, synthetic, bad_recovery))

    for name, req, req_status, d_status, i_status, synth, rec in extra_cases:
        try:
            validate_request(req, req_status, d_status, i_status, synth, policy, rec, **bytes_inputs)
        except RequestValidationError:
            passed += 1
        else:
            raise RequestValidationError(f"upstream mutation not rejected: {name}")
    return passed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--request-status", type=Path, required=True)
    parser.add_argument("--design-status", type=Path, required=True)
    parser.add_argument("--implementation-status", type=Path, required=True)
    parser.add_argument("--synthetic-result", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--recovery-status", type=Path, required=True)
    parser.add_argument("--implementation", type=Path, required=True)
    parser.add_argument("--request-design", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    paths = {
        "request": args.request,
        "request_status": args.request_status,
        "design_status": args.design_status,
        "implementation_status": args.implementation_status,
        "synthetic": args.synthetic_result,
        "policy": args.policy,
        "recovery": args.recovery_status,
        "implementation": args.implementation,
        "design": args.request_design,
    }
    raw = {name: path.read_bytes() for name, path in paths.items()}
    values = {
        name: json.loads(data)
        for name, data in raw.items()
        if name not in {"implementation", "design"}
    }
    byte_inputs = {
        "implementation_bytes": raw["implementation"],
        "synthetic_bytes": raw["synthetic"],
        "policy_bytes": raw["policy"],
        "recovery_bytes": raw["recovery"],
        "design_bytes": raw["design"],
    }
    validate_request(
        values["request"], values["request_status"], values["design_status"],
        values["implementation_status"], values["synthetic"], values["policy"],
        values["recovery"], **byte_inputs,
    )
    mutation_count = mutation_tests(
        values["request"], values["request_status"], values["design_status"],
        values["implementation_status"], values["synthetic"], values["policy"],
        values["recovery"], **byte_inputs,
    )

    report = {
        "schema_version": "historical-gold-5826-freeze-manifest-real-artifact-execution-request-validation-v1",
        "formal_state": NEXT_STATE,
        "request_id": REQUEST_ID,
        "request_file": str(args.request),
        "request_file_sha256": sha256_bytes(raw["request"]),
        "request_status_file_sha256": sha256_bytes(raw["request_status"]),
        "request_design_file_sha256": sha256_bytes(raw["design"]),
        "request_design_git_blob_sha": git_blob_sha(raw["design"]),
        "implementation_file_sha256": sha256_bytes(raw["implementation"]),
        "implementation_git_blob_sha": git_blob_sha(raw["implementation"]),
        "synthetic_result_file_sha256": sha256_bytes(raw["synthetic"]),
        "synthetic_result_git_blob_sha": git_blob_sha(raw["synthetic"]),
        "policy_file_sha256": sha256_bytes(raw["policy"]),
        "policy_git_blob_sha": git_blob_sha(raw["policy"]),
        "recovery_status_file_sha256": sha256_bytes(raw["recovery"]),
        "recovery_status_git_blob_sha": git_blob_sha(raw["recovery"]),
        "design_status_file_sha256": sha256_bytes(raw["design_status"]),
        "implementation_status_file_sha256": sha256_bytes(raw["implementation_status"]),
        "artifact_id": ARTIFACT_ID,
        "artifact_name": ARTIFACT_NAME,
        "artifact_archive_digest": ARTIFACT_DIGEST,
        "artifact_expires_at": ARTIFACT_EXPIRY,
        "gold_gzip_sha256": GOLD_SHA,
        "synthetic_tests_passed": 20,
        "mutation_tests_passed": mutation_count,
        "request_valid": True,
        "ready_for_explicit_user_approval": True,
        "approval_granted": False,
        "execution_enabled": False,
        "execution_workflow_created": False,
        "real_artifact_downloaded": False,
        "real_artifact_read": False,
        "semantic_manifest_created": False,
        "corpus_frozen": False,
        "execution_count": 0,
        "maximum_execution_count": 1,
        "request_consumed": False,
        "repeat_execution_allowed": False,
        "automatic_dispatch_allowed": False,
        "aggregate_only": True,
        "raw_rows_read": False,
        "raw_rows_emitted": 0,
        "ready_for_real_artifact_execution": False,
        "ready_for_execution_workflow_implementation": False,
        "ready_for_corpus_freeze_claim": False,
        "ready_for_market_backtest": False,
        "ready_for_model_retraining": False,
        "formal_stake": 0,
        "next_research_step": NEXT_STEP,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
