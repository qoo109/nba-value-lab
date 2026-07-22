#!/usr/bin/env python3
"""Validate the vendored nba-odds-history-hub V0.19 archive contract."""

from __future__ import annotations

import hashlib
import json
import tarfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "data" / "odds-history-hub-integration-v1.json"
SOURCE_REGISTRY = ROOT / "data" / "source-registry.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def archive_files(archive_path: Path) -> list[Path]:
    return sorted(path for path in archive_path.rglob("*") if path.is_file())


def main() -> int:
    integration = load_json(INTEGRATION)
    registry = load_json(SOURCE_REGISTRY)

    require(integration.get("schema_version") == "odds-history-hub-integration-v1", "integration schema mismatch")

    canonical = integration.get("canonical_repository", {})
    require(canonical.get("full_name") == "qoo109/nba-value-lab", "NBA Value Lab must be canonical")
    require(canonical.get("role") == "single_active_workspace", "canonical repository role mismatch")

    origin = integration.get("historical_origin", {})
    require(origin.get("full_name") == "qoo109/nba-odds-history-hub", "unexpected historical origin")
    require(origin.get("default_branch") == "main", "historical origin default branch must be main")
    require(isinstance(origin.get("snapshot_commit"), str) and len(origin["snapshot_commit"]) == 40, "snapshot commit sha required")
    require(origin.get("recommended_repository_state") == "archived_read_only", "historical repository should be archived")

    archive = integration.get("archive", {})
    require(archive.get("mode") == "vendored_read_only_snapshot", "archive mode mismatch")
    archive_path = ROOT / archive.get("path", "")
    require(archive_path.is_dir(), "vendored archive directory missing")
    require((archive_path / "index.html").is_file(), "archived static website missing")
    require((archive_path / "ARCHIVE-NOTICE.md").is_file(), "archive notice missing")
    require(archive.get("active_development_enabled") is False, "archive development must remain disabled")
    require(archive.get("deployment_dependency") is False, "archive cannot be a deployment dependency")

    files = archive_files(archive_path)
    require(len(files) == archive.get("published_file_count") == 21, "published archive file count mismatch")

    source_archive = ROOT / archive.get("source_archive_path", "")
    require(source_archive.is_file(), "source archive missing")
    require(source_archive.stat().st_size == archive.get("source_archive_bytes"), "source archive byte count mismatch")
    digest = hashlib.sha256(source_archive.read_bytes()).hexdigest()
    require(digest == archive.get("source_archive_sha256"), "source archive sha256 mismatch")

    prefix = "nba-odds-history-hub-v0.19/"
    with tarfile.open(source_archive, "r:gz") as bundle:
        members = [member for member in bundle.getmembers() if member.isfile()]
        require(len(members) == archive.get("source_file_count") == 145, "source archive file count mismatch")
        require(all(member.name.startswith(prefix) for member in members), "source archive prefix mismatch")
        require(all(".." not in Path(member.name).parts for member in members), "source archive path traversal detected")
        require(all("/.git/" not in f"/{member.name}/" for member in members), "source archive must not contain .git")

        static_files = [
            path
            for path in files
            if path.name != "ARCHIVE-NOTICE.md" and path != source_archive
        ]
        for static_file in static_files:
            relative = static_file.relative_to(archive_path).as_posix()
            member = bundle.getmember(prefix + relative)
            archived_file = bundle.extractfile(member)
            require(archived_file is not None, f"cannot read archived static file: {relative}")
            require(archived_file.read() == static_file.read_bytes(), f"static file differs from source snapshot: {relative}")

    role = integration.get("role_in_nba_value_lab", {})
    require(role.get("mode") == "internal_archive_only", "archive role mismatch")
    for key in (
        "automatic_import_enabled",
        "cross_repository_write_enabled",
        "production_schedule_import_enabled",
        "production_database_access_enabled",
        "external_schedule_read_enabled",
    ):
        require(role.get(key) is False, f"{key} must remain false")
    require(role.get("formal_stake_fraction") == 0, "formal stake must remain zero")

    status = integration.get("snapshot_status", {})
    require(status.get("phase") == "V0.19", "snapshot phase mismatch")
    require(status.get("current_mode") == "archived_offseason_sleep", "snapshot must remain archived and asleep")
    require(status.get("checks_passed") == status.get("checks_total") == 31, "snapshot checks must be 31/31")
    require(status.get("owner_review_approval_granted") is False, "owner review approval must remain false")
    require(status.get("manual_schedule_execution_enabled") is False, "manual schedule execution must remain disabled")
    require(status.get("maximum_schedule_execution_count") == 0, "maximum execution count must remain zero")
    require(status.get("production_schedule_imported") is False, "production import must remain false")
    require(status.get("external_schedule_read") is False, "external schedule read must remain false")

    binding = integration.get("nba_value_lab_binding", {})
    require(binding.get("all_future_work_must_target_nba_value_lab") is True, "single-workspace binding required")

    sources = registry.get("sources", [])
    matches = [source for source in sources if source.get("source_id") == "nba_odds_history_hub_archive"]
    require(len(matches) == 1, "source registry must contain exactly one nba_odds_history_hub_archive entry")
    source = matches[0]
    require(source.get("status") == "archived_internal_snapshot", "source registry status mismatch")
    require(source.get("mode") == "vendored_read_only_snapshot", "source registry mode mismatch")
    require(source.get("archive_path") == archive.get("path"), "archive path mismatch")
    require(source.get("source_archive") == archive.get("source_archive_path"), "source archive path mismatch")
    require(source.get("source_archive_sha256") == archive.get("source_archive_sha256"), "source archive sha256 registry mismatch")
    require(source.get("snapshot_commit") == origin.get("snapshot_commit"), "snapshot commit mismatch")
    require(source.get("integration_manifest") == "data/odds-history-hub-integration-v1.json", "integration manifest path mismatch")
    require(source.get("documentation") == "docs/nba-odds-history-hub-integration-v1.md", "documentation path mismatch")

    boundary = source.get("safety_boundary", {})
    for key in (
        "automatic_import_enabled",
        "cross_repository_write_enabled",
        "production_schedule_import_enabled",
        "production_database_access_enabled",
        "external_schedule_read_enabled",
    ):
        require(boundary.get(key) is False, f"source boundary {key} must remain false")
    require(boundary.get("formal_stake") == 0, "source boundary formal stake must remain zero")

    print("Odds History Hub archive valid: V0.19, 21 published files, 145-file source bundle, NBA Value Lab canonical")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
