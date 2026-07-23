#!/usr/bin/env python3
"""Execute the approved Historical Gold 5,826 semantic freeze exactly once."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

REQUEST_ID = "HISTORICAL-GOLD-5826-FREEZE-MANIFEST-REAL-ARTIFACT-EXECUTION-2026-07-23-001"
APPROVAL_SCHEMA = "historical-gold-5826-freeze-manifest-real-artifact-execution-approval-v1"
APPROVAL_STATE = "EXPLICIT_USER_APPROVAL_GRANTED"
SOURCE_RUN_ID = 29976204693
SOURCE_ARTIFACT_ID = 8551587005
SOURCE_ARTIFACT_NAME = "historical-silver-gold-two-game-official-cdn-recovery-v2"
SOURCE_ARTIFACT_DIGEST = "sha256:3ed2d28da3af58b8b72d805860a144541ac5f38106653cfbda593e16bbaa8e8d"
ARTIFACT_EXPIRY = "2026-08-06T03:14:00Z"
EXPECTED_FILES = {
    "historical-silver-multiseason-recovered-v1.sqlite.gz": (369318173, "sha256:48c032339402d5f75e43d7aaf8e977784aee9eceff74c9e7da952af8e1680eb8"),
    "historical-gold-multiseason-recovered-v1.sqlite.gz": (5268851, "sha256:a4e94fab1681b53817f305d08c196995d406fa0566ab70d6083aa5cebfc52085"),
    "two-game-official-cdn-pbp-recovery-result-v2.json": (3751, "sha256:97d292d56f6ee8b6f0a2d4e4471990f7c953cca7c324eb64c129066695df7c30"),
}
BINDINGS = {
    "request_file_sha256": "sha256:2f8d209b3a7c5031c338b3add108e534ff69ec0d08d62bbb93f7b20963865990",
    "request_design_file_sha256": "sha256:33e5a5789430092d8ccf6f3831c89424683b4726dd6dacdc876695dba287d57e",
    "implementation_file_sha256": "sha256:ca4c21316711897121f480165227cea6f6059db808706f4084c853e428418a21",
    "synthetic_result_file_sha256": "sha256:24a8ea75116a179c34942f9d301c9cc9a3422d583b4d6cc69935f26ce2ccbcd5",
    "policy_file_sha256": "sha256:50e36245b712d934cfc26e443be2fb15c2087c1819dea583914b364049da2eda",
    "recovery_status_file_sha256": "sha256:bea4deeccf6c23d6bd66108a3c567ad2a10be4fe56b2b20fa3710d9196ccb741",
}
PATHS = {
    "request_file_sha256": Path("data/research/historical-gold-5826-freeze-manifest-real-artifact-execution-request-v1.json"),
    "request_design_file_sha256": Path("data/research/historical-gold-5826-freeze-manifest-real-artifact-execution-request-design-v1.json"),
    "implementation_file_sha256": Path("scripts/build_historical_gold_5826_complete_corpus_freeze_manifest_v1.py"),
    "synthetic_result_file_sha256": Path("data/research/historical-gold-5826-complete-corpus-freeze-manifest-synthetic-implementation-result-v1.json"),
    "policy_file_sha256": Path("data/research/historical-gold-5826-complete-corpus-freeze-policy-v1.json"),
    "recovery_status_file_sha256": Path("data/research/historical-silver-2023-24-two-game-official-cdn-pbp-recovery-current-status-v1.json"),
}
PROHIBITED = {
    "game_id", "game_date", "home_team_abbr", "away_team_abbr", "team_code",
    "feature_id", "matchup_feature_id", "raw_row", "sample_row",
    "row_level_hash", "individual_feature_value", "player_information", "market_price",
}

class ExecutionBlocked(RuntimeError):
    pass

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()

def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ExecutionBlocked(f"{path} must contain an object")
    return value

def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

def has_prohibited(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(str(key) in PROHIBITED or has_prohibited(child) for key, child in value.items())
    if isinstance(value, list):
        return any(has_prohibited(child) for child in value)
    return False

def require(condition: bool, message: str) -> None:
    if not condition:
        raise ExecutionBlocked(message)

def validate_approval(approval: Mapping[str, Any], args: argparse.Namespace) -> None:
    require(approval.get("schema_version") == APPROVAL_SCHEMA, "approval schema mismatch")
    require(approval.get("request_id") == REQUEST_ID, "approval request mismatch")
    require(approval.get("approval_state") == APPROVAL_STATE, "approval not granted")
    require(approval.get("approved_by") == "qoo109", "approver mismatch")
    require(approval.get("formal_stake") == 0, "Stake must remain 0")
    auth = approval.get("execution_authorization", {})
    require(auth.get("one_time_only") is True, "one-time authorization missing")
    require(auth.get("maximum_execution_count") == 1, "maximum execution count mismatch")
    require(auth.get("executions_recorded_before_approval") == 0, "prior execution recorded")
    require(auth.get("request_consumed_before_approval") is False, "request already consumed")
    require(auth.get("workflow_dispatch_only") is True, "workflow dispatch required")
    require(auth.get("automatic_dispatch_allowed") is False, "automatic dispatch prohibited")
    require(auth.get("approved_ref") == "refs/heads/main", "approved ref mismatch")
    require(auth.get("approved_to_dispatch_exactly_once") is True, "dispatch not approved")
    require(auth.get("workflow_rerun_allowed") is False, "reruns prohibited")
    binding = approval.get("exact_artifact_binding", {})
    require(binding.get("source_workflow_run_id") == SOURCE_RUN_ID, "source run mismatch")
    require(binding.get("artifact_id") == SOURCE_ARTIFACT_ID, "artifact id mismatch")
    require(binding.get("artifact_name") == SOURCE_ARTIFACT_NAME, "artifact name mismatch")
    require(binding.get("artifact_archive_digest") == SOURCE_ARTIFACT_DIGEST, "artifact digest mismatch")
    require(binding.get("artifact_expires_at") == ARTIFACT_EXPIRY, "artifact expiry mismatch")
    declared = approval.get("immutable_bindings", {})
    for key, expected in BINDINGS.items():
        require(declared.get(key) == expected, f"approval binding mismatch: {key}")
        require(sha256_file(PATHS[key]) == expected, f"committed file mismatch: {key}")
    require(args.confirmation_request_id == REQUEST_ID, "confirmation request id mismatch")
    require(args.workflow_event == "workflow_dispatch", "workflow_dispatch required")
    require(args.workflow_ref == "refs/heads/main", "main branch required")
    require(args.run_attempt == 1, "workflow rerun prohibited")
    require(args.execution_count_before == 0, "request execution count is not zero")
    require(datetime.now(timezone.utc) < parse_utc(ARTIFACT_EXPIRY), "bound Artifact expired")

def validate_artifact(root: Path) -> None:
    files = sorted(path.name for path in root.iterdir() if path.is_file())
    require(files == sorted(EXPECTED_FILES), f"exact Artifact file set mismatch: {files}")
    for name, (size, digest) in EXPECTED_FILES.items():
        path = root / name
        require(path.stat().st_size == size, f"size mismatch: {name}")
        require(sha256_file(path) == digest, f"sha256 mismatch: {name}")

def validate_manifest(manifest: Mapping[str, Any]) -> None:
    require(manifest.get("schema_version") == "historical-gold-5826-complete-corpus-freeze-manifest-v1", "manifest schema mismatch")
    require(manifest.get("formal_state") == "HISTORICAL_GOLD_SEMANTIC_CORPUS_MANIFEST_VALID", "manifest state mismatch")
    require(manifest.get("formal_stake") == 0, "manifest Stake mismatch")
    require(manifest.get("season_labels") == ["2019-20", "2020-21", "2021-22", "2022-23", "2023-24"], "season mismatch")
    tables = manifest.get("tables", {})
    require(tables.get("gold_matchup_features", {}).get("row_count") == 5826, "matchup count mismatch")
    require(tables.get("gold_team_game_features", {}).get("row_count") == 11652, "team row count mismatch")
    privacy = manifest.get("privacy_boundaries", {})
    require(privacy.get("aggregate_only") is True, "aggregate-only boundary failed")
    require(privacy.get("row_level_values_emitted") is False, "row values emitted")
    require(privacy.get("row_level_hashes_emitted") is False, "row hashes emitted")
    require(not has_prohibited(manifest), "prohibited field in manifest")

def execute(args: argparse.Namespace) -> None:
    approval = read_json(args.approval)
    validate_approval(approval, args)
    if args.validate_only:
        print(json.dumps({"approval_valid": True, "ready_for_one_time_manual_dispatch": True, "formal_stake": 0}, indent=2))
        return
    validate_artifact(args.artifact_dir)
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    require(not any(output.iterdir()), "output directory must be empty")
    recovery = args.artifact_dir / "two-game-official-cdn-pbp-recovery-result-v2.json"
    committed_recovery = Path("data/research/historical-silver-2023-24-two-game-official-cdn-pbp-recovery-result-v2.json")
    require(sha256_file(recovery) == sha256_file(committed_recovery), "recovery result differs from committed copy")
    gold_gzip = args.artifact_dir / "historical-gold-multiseason-recovered-v1.sqlite.gz"
    sqlite_path = args.temp_dir / "historical-gold-multiseason-recovered-v1.sqlite"
    args.temp_dir.mkdir(parents=True, exist_ok=True)
    with gzip.open(gold_gzip, "rb") as source, sqlite_path.open("wb") as target:
        shutil.copyfileobj(source, target)
    sqlite_before = sha256_file(sqlite_path)
    manifest_path = output / "historical-gold-5826-complete-corpus-freeze-manifest-v1.json"
    subprocess.run(
        [sys.executable, str(PATHS["implementation_file_sha256"]), "--gold-sqlite", str(sqlite_path),
         "--policy", str(PATHS["policy_file_sha256"]), "--output", str(manifest_path)],
        check=True,
    )
    sqlite_after = sha256_file(sqlite_path)
    require(sqlite_before == sqlite_after, "Gold SQLite changed during processing")
    manifest = read_json(manifest_path)
    validate_manifest(manifest)
    receipt = {
        "schema_version": "historical-gold-5826-freeze-manifest-real-artifact-execution-receipt-v1",
        "formal_outcome": "HISTORICAL_GOLD_5826_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_PASS_CONSUMED",
        "request_id": REQUEST_ID,
        "workflow_run_id": args.workflow_run_id,
        "workflow_run_attempt": args.run_attempt,
        "workflow_ref": args.workflow_ref,
        "github_sha": args.github_sha,
        "execution_count_for_request": 1,
        "maximum_execution_count_for_request": 1,
        "request_consumed": True,
        "repeat_execution_allowed": False,
        "source_workflow_run_id": SOURCE_RUN_ID,
        "source_artifact_id": SOURCE_ARTIFACT_ID,
        "source_artifact_name": SOURCE_ARTIFACT_NAME,
        "source_artifact_archive_digest": SOURCE_ARTIFACT_DIGEST,
        "gold_gzip_sha256": sha256_file(gold_gzip),
        "gold_gzip_size_bytes": gold_gzip.stat().st_size,
        "decompressed_gold_sqlite_sha256": sqlite_before,
        "manifest_sha256": sha256_file(manifest_path),
        "manifest_size_bytes": manifest_path.stat().st_size,
        "real_artifact_read": True,
        "gold_sqlite_read_only": True,
        "database_modified": False,
        "raw_rows_emitted": 0,
        "formal_stake": 0,
    }
    require(not has_prohibited(receipt), "prohibited field in receipt")
    receipt_path = output / "historical-gold-5826-freeze-manifest-real-artifact-execution-receipt-v1.json"
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    files = sorted(path.name for path in output.iterdir() if path.is_file())
    require(files == sorted([manifest_path.name, receipt_path.name]), "output file set mismatch")
    require(sum(path.stat().st_size for path in output.iterdir() if path.is_file()) <= 1048576, "output exceeds 1 MiB")

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--approval", required=True, type=Path)
    parser.add_argument("--artifact-dir", type=Path, default=Path("/tmp/nbavl-gold-5826-input"))
    parser.add_argument("--output-dir", type=Path, default=Path("/tmp/nbavl-gold-5826-output"))
    parser.add_argument("--temp-dir", type=Path, default=Path("/tmp/nbavl-gold-5826-temp"))
    parser.add_argument("--confirmation-request-id", required=True)
    parser.add_argument("--workflow-event", required=True)
    parser.add_argument("--workflow-ref", required=True)
    parser.add_argument("--workflow-run-id", type=int, default=0)
    parser.add_argument("--run-attempt", type=int, required=True)
    parser.add_argument("--github-sha", default="")
    parser.add_argument("--execution-count-before", type=int, required=True)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    execute(args)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
