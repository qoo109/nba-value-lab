#!/usr/bin/env python3
"""Validate the Eoin full-adapter runner implementation without executing raw data."""
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

MANIFEST_SCHEMA = "eoin-full-adapter-runner-implementation-v1"
MANIFEST_STATE = "FULL_ADAPTER_RUNNER_IMPLEMENTED_EXECUTION_DISABLED"
READY_STATE = "FULL_ADAPTER_RUNNER_READY_FOR_ONE_TIME_EXECUTION_APPROVAL_BUT_DISABLED"
BLOCKED_STATE = "FULL_ADAPTER_RUNNER_VALIDATION_BLOCKED"
POLICY_READY_STATE = "FULL_ADAPTER_EXECUTION_POLICY_READY_FOR_IMPLEMENTATION_BUT_EXECUTION_DISABLED"
EXPECTED_FILES = ("Games.csv", "TeamStatistics.csv", "PlayerStatistics.csv", "PlayByPlay.parquet")


class RunnerBlocked(RuntimeError):
    """Raised before raw Eoin data is accessed when execution remains disabled."""


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_allowlisted_inventory(root: Path, limits: dict[str, Any]) -> dict[str, Any]:
    files = sorted(path for path in root.rglob("*") if path.is_file())
    names = [path.name for path in files]
    required = list(limits["required_input_files"])
    missing = sorted(name for name in required if name not in names)
    unexpected = sorted(name for name in names if name not in required)
    items = [
        {
            "name": path.name,
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in files
    ]
    total_bytes = sum(item["size_bytes"] for item in items)
    largest_bytes = max((item["size_bytes"] for item in items), default=0)
    checks = {
        "required_files_present": not missing,
        "unexpected_files_absent": not unexpected,
        "file_count_within_limit": len(files) <= int(limits["max_input_file_count"]),
        "total_bytes_within_limit": total_bytes <= int(limits["max_total_input_bytes"]),
        "largest_file_within_limit": largest_bytes <= int(limits["max_single_input_file_bytes"]),
    }
    return {
        "file_count": len(files),
        "total_bytes": total_bytes,
        "largest_file_bytes": largest_bytes,
        "missing_required_files": missing,
        "unexpected_files": unexpected,
        "files": items,
        "checks": checks,
        "all_checks_passed": all(checks.values()),
        "raw_rows_emitted": 0,
        "raw_files_emitted": False,
    }


def validate_manifest(manifest: dict[str, Any], policy: dict[str, Any]) -> list[str]:
    failures: list[str] = []

    def check(condition: bool, name: str) -> None:
        if not condition:
            failures.append(name)

    check(manifest.get("schema_version") == MANIFEST_SCHEMA, "manifest.schema_version")
    check(manifest.get("formal_state") == MANIFEST_STATE, "manifest.formal_state")
    check(manifest.get("source_id") == "kaggle_eoinamoore_historical_nba", "manifest.source_id")

    upstream = manifest.get("upstream_requirements", {})
    check(upstream.get("execution_policy") == "data/eoin-full-adapter-execution-policy-v1.json", "upstream.execution_policy")
    check(upstream.get("execution_policy_required_state") == POLICY_READY_STATE, "upstream.policy_state")
    check(upstream.get("execution_policy_validation_required") is True, "upstream.policy_validation_required")
    check(upstream.get("execution_policy_checks_failed_required") == 0, "upstream.policy_failures_zero")

    policy_next = policy.get("next_state_if_policy_validation_passes", {})
    check(policy_next.get("formal_state") == POLICY_READY_STATE, "policy.next_state")
    check(policy_next.get("ready_for_execution_implementation") is True, "policy.implementation_ready")
    check(policy_next.get("ready_for_full_adapter_execution") is False, "policy.execution_disabled")
    check(policy.get("activation_boundary", {}).get("full_bundle_execution_enabled") is False, "policy.full_bundle_disabled")

    limits = manifest.get("operational_limits", {})
    check(limits.get("max_runtime_minutes") == 45, "limits.runtime")
    check(limits.get("max_concurrent_runs") == 1, "limits.concurrency")
    check(limits.get("required_input_files") == list(EXPECTED_FILES), "limits.required_files")
    check(limits.get("max_input_file_count") == 4, "limits.file_count")
    check(isinstance(limits.get("max_total_input_bytes"), int) and limits["max_total_input_bytes"] > 0, "limits.total_bytes")
    check(isinstance(limits.get("max_single_input_file_bytes"), int) and limits["max_single_input_file_bytes"] > 0, "limits.single_bytes")

    switches = manifest.get("execution_switches", {})
    for key in ("full_bundle_execution_enabled", "network_download_enabled", "dataset_root_execution_enabled"):
        check(switches.get(key) is False, f"switches.{key}")
    check(switches.get("workflow_dispatch_only_when_later_enabled") is True, "switches.workflow_dispatch_only")
    check(switches.get("automatic_main_push_execution_allowed") is False, "switches.no_auto_push")
    check(switches.get("scheduled_execution_allowed") is False, "switches.no_schedule")
    check(switches.get("explicit_user_approval_required") is True, "switches.user_approval")
    check(switches.get("approval_record_required") is True, "switches.approval_record")

    forbidden = manifest.get("forbidden_promotions", {})
    for key in (
        "historical_silver_replacement_allowed",
        "historical_gold_replacement_allowed",
        "player_stat_parity_claim_allowed",
        "player_stat_feature_import_allowed",
        "model_training_input_allowed",
        "model_retraining_allowed",
        "market_backtest_allowed",
        "clv_ev_roi_drawdown_allowed",
        "betting_decision_layer_allowed",
        "betting_edge_claim_allowed",
    ):
        check(forbidden.get(key) is False, f"forbidden.{key}")
    check(forbidden.get("formal_stake") == 0, "forbidden.formal_stake")

    next_state = manifest.get("next_state_if_runner_validation_passes", {})
    check(next_state.get("formal_state") == READY_STATE, "next_state.formal_state")
    check(next_state.get("ready_for_one_time_execution_request_design") is True, "next_state.request_design_ready")
    for key in (
        "ready_for_full_bundle_execution",
        "ready_for_silver_replacement",
        "ready_for_gold_replacement",
        "ready_for_model_retraining",
        "ready_for_market_backtest",
        "ready_for_betting_edge_claim",
    ):
        check(next_state.get(key) is False, f"next_state.no_{key}")
    check(next_state.get("formal_stake") == 0, "next_state.formal_stake")
    return failures


def ensure_execution_allowed(manifest: dict[str, Any]) -> None:
    switches = manifest.get("execution_switches", {})
    if switches.get("full_bundle_execution_enabled") is not True:
        raise RunnerBlocked("full Eoin bundle execution remains disabled by implementation manifest")
    if switches.get("dataset_root_execution_enabled") is not True:
        raise RunnerBlocked("dataset-root execution remains disabled by implementation manifest")
    raise RunnerBlocked("one-time execution approval record is not implemented or supplied")


def write_fixture(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "Games.csv").write_text(
        "gameId,gameDateTimeEst,homeScore,awayScore\n22300001,2023-10-24 19:30:00,110,105\n",
        encoding="utf-8",
    )
    (root / "TeamStatistics.csv").write_text(
        "gameId,teamId,teamScore\n22300001,1,110\n22300001,2,105\n",
        encoding="utf-8",
    )
    (root / "PlayerStatistics.csv").write_text(
        "gameId,personId,points\n22300001,101,30\n",
        encoding="utf-8",
    )
    (root / "PlayByPlay.parquet").write_bytes(b"PAR1synthetic-runner-fixturePAR1")


def build_self_test_report(manifest: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    failures = validate_manifest(manifest, policy)
    with tempfile.TemporaryDirectory(prefix="nbavl-eoin-runner-") as temp_name:
        fixture = Path(temp_name)
        write_fixture(fixture)
        inventory = inspect_allowlisted_inventory(fixture, manifest["operational_limits"])

    blocked_before_data_access = False
    blocker_message = None
    try:
        ensure_execution_allowed(manifest)
    except RunnerBlocked as exc:
        blocked_before_data_access = True
        blocker_message = str(exc)

    if not inventory["all_checks_passed"]:
        failures.append("fixture.inventory")
    if not blocked_before_data_access:
        failures.append("execution.blocker")

    passed = not failures
    return {
        "schema_version": "eoin-full-adapter-runner-validation-v1",
        "formal_state": READY_STATE if passed else BLOCKED_STATE,
        "source_id": "kaggle_eoinamoore_historical_nba",
        "fixture_only": True,
        "manifest_state": manifest.get("formal_state"),
        "execution_policy_state": policy.get("next_state_if_policy_validation_passes", {}).get("formal_state"),
        "inventory": inventory,
        "quality": {
            "checks_failed": len(failures),
            "failed_checks": failures,
            "network_calls_made": False,
            "full_bundle_execution_performed": False,
            "raw_eoin_rows_read": False,
            "raw_rows_emitted": 0,
            "raw_files_emitted": False,
            "blocked_before_data_access": blocked_before_data_access,
            "blocker_message": blocker_message,
            "formal_stake": 0,
        },
        "decision": {
            "ready_for_one_time_execution_request_design": passed,
            "ready_for_full_bundle_execution": False,
            "ready_for_silver_replacement": False,
            "ready_for_gold_replacement": False,
            "ready_for_model_retraining": False,
            "ready_for_market_backtest": False,
            "ready_for_betting_edge_claim": False,
            "formal_stake": 0,
        },
    }


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("data/eoin-full-adapter-runner-implementation-v1.json"))
    parser.add_argument("--execution-policy", type=Path, default=Path("data/eoin-full-adapter-execution-policy-v1.json"))
    parser.add_argument("--dataset-root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    manifest = read_json(args.manifest)
    policy = read_json(args.execution_policy)

    if args.self_test:
        report = build_self_test_report(manifest, policy)
        write_report(args.output, report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["formal_state"] == READY_STATE else 1

    blocked = {
        "schema_version": "eoin-full-adapter-runner-validation-v1",
        "formal_state": "FULL_ADAPTER_EXECUTION_BLOCKED_BEFORE_DATA_ACCESS",
        "dataset_root_supplied": args.dataset_root is not None,
        "quality": {
            "network_calls_made": False,
            "full_bundle_execution_performed": False,
            "raw_eoin_rows_read": False,
            "raw_rows_emitted": 0,
            "raw_files_emitted": False,
            "formal_stake": 0,
        },
        "reason": "full Eoin bundle execution requires a later explicit approval and enablement change",
    }
    write_report(args.output, blocked)
    print(json.dumps(blocked, ensure_ascii=False, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
