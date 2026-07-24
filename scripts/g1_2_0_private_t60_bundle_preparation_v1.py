#!/usr/bin/env python3
"""Prepare and seal a private G1.2.0 real T-60 intake bundle.

This helper is offline-only. It performs no provider requests, writes no formal
history, and refuses to read or write private bundle files inside the public
repository tree.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VALID_TIME_AUTHORITY = {"provider_snapshot", "bookmaker_last_update"}
PLACEHOLDER_BOOKMAKERS = {"", "fixture_book", "fixture", "unknown", "placeholder", "synthetic", "__replace__"}


class BundlePreparationError(ValueError):
    """Raised when a private bundle preparation rule fails."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise BundlePreparationError(message)


def is_inside_repository(path: Path) -> bool:
    resolved = path.expanduser().resolve()
    root = ROOT.resolve()
    return resolved == root or root in resolved.parents


def require_private_path(path: Path, label: str) -> Path:
    resolved = path.expanduser().resolve()
    require(not is_inside_repository(resolved), f"{label} must remain outside the public repository")
    return resolved


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_bytes(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def initialize_bundle(output_dir: Path) -> dict[str, Any]:
    target = require_private_path(output_dir, "output directory")
    target.mkdir(parents=True, exist_ok=True)
    require(not any(target.iterdir()), "output directory must be empty")

    input_template = {
        "template_only": True,
        "contract_fixture_only": False,
        "schema_version": "g1-2-0-real-t60-input-v1",
        "data_mode": "REPLACE_WITH_real_governed",
        "slate_id": "REPLACE_WITH_PRIVATE_SLATE_ID",
        "slate_date": "YYYY-MM-DD",
        "analysis_cutoff": "YYYY-MM-DDTHH:MM:SS+00:00",
        "evaluation_stage": "T-60m",
        "target_bookmaker_id": "REPLACE_WITH_REAL_BOOKMAKER_ID",
        "market_id": "moneyline_ot_included",
        "includes_overtime": True,
        "data_version": "REPLACE_WITH_PRIVATE_DATA_VERSION",
        "lock_window_minutes": {"min": 30, "max": 90},
        "season": "2026-27",
        "competition_type": "regular_season",
        "candidates": [],
    }
    evidence_template = {
        "template_only": True,
        "evidence_schema_version": "g1-2-0-real-t60-source-evidence-v1",
        "contract_fixture_only": False,
        "source_id": "REPLACE_WITH_SOURCE_ID",
        "source_url": "https://REPLACE_WITH_SOURCE_URL",
        "source_rights_state": "UNREVIEWED",
        "rights_review_reference": "REPLACE_WITH_USER_REVIEW_REFERENCE",
        "rights_reviewed_by_user": False,
        "provider_timestamp_semantics_verified": False,
        "provider_timestamp_semantics_note": "REPLACE_WITH_AT_LEAST_20_CHARACTERS",
        "quote_time_authority": "REPLACE_WITH_provider_snapshot_OR_bookmaker_last_update",
        "provider_observed_at_field": "REPLACE_WITH_PROVIDER_FIELD",
        "target_bookmaker_id": "REPLACE_WITH_REAL_BOOKMAKER_ID",
        "market_id": "moneyline_ot_included",
        "includes_overtime": True,
        "canonical_game_mapping_method": "exact",
        "normalized_input_sha256": "PENDING_SEAL",
        "raw_source_sha256": "PENDING_SEAL",
        "raw_source_retention_scope": "private_user_controlled",
        "public_redistribution_allowed": False,
    }
    instructions = (
        "PRIVATE G1.2.0 T-60 BUNDLE\n"
        "\n"
        "1. Keep this directory outside the public repository.\n"
        "2. Replace every template marker in t60-input.template.json.\n"
        "3. Remove template_only before sealing.\n"
        "4. Review source rights and provider timestamp semantics personally.\n"
        "5. Save the untouched provider export privately.\n"
        "6. Complete source-evidence.draft.json and remove template_only.\n"
        "7. Run the seal command, then run the existing intake validator privately.\n"
        "8. Never commit raw quotes, prices, provider exports, API keys or sealed private files.\n"
    )
    write_json(target / "t60-input.template.json", input_template)
    write_json(target / "source-evidence.draft.json", evidence_template)
    (target / "README_PRIVATE.txt").write_text(instructions, encoding="utf-8")

    return {
        "formal_state": "G1_2_0_PRIVATE_T60_BUNDLE_TEMPLATE_INITIALIZED",
        "offline_only": True,
        "repository_write": False,
        "provider_requests_executed": 0,
        "formal_history_write_authorized": False,
        "market_metrics_executed": False,
        "formal_stake": 0,
        "files_created": 3,
    }


def _validate_real_input_identity(payload: dict[str, Any]) -> None:
    require(payload.get("template_only") is None, "remove template_only from normalized input before sealing")
    require(payload.get("contract_fixture_only") is False, "contract_fixture_only must be false")
    require(payload.get("data_mode") == "real_governed", "data_mode must be real_governed")
    require(payload.get("season") == "2026-27", "season must be 2026-27")
    require(payload.get("competition_type") == "regular_season", "competition_type must be regular_season")
    require(payload.get("evaluation_stage") == "T-60m", "evaluation_stage must be T-60m")
    require(payload.get("market_id") == "moneyline_ot_included", "market_id must be moneyline_ot_included")
    require(payload.get("includes_overtime") is True, "market must include overtime")
    bookmaker = str(payload.get("target_bookmaker_id", "")).strip()
    require(bookmaker.lower() not in PLACEHOLDER_BOOKMAKERS and "replace" not in bookmaker.lower(), "real bookmaker identity required")
    require(isinstance(payload.get("candidates"), list) and payload["candidates"], "normalized input candidates must be non-empty")


def _validate_evidence_draft(payload: dict[str, Any], evidence: dict[str, Any]) -> None:
    require(evidence.get("template_only") is None, "remove template_only from evidence draft before sealing")
    require(evidence.get("evidence_schema_version") == "g1-2-0-real-t60-source-evidence-v1", "invalid evidence schema")
    require(evidence.get("contract_fixture_only") is False, "evidence contract_fixture_only must be false")
    require(str(evidence.get("source_url", "")).startswith("https://"), "source_url must be HTTPS")
    require(evidence.get("source_rights_state") == "private_research_allowed", "source rights must allow private research")
    require(evidence.get("rights_reviewed_by_user") is True, "rights must be reviewed by user")
    require(bool(str(evidence.get("rights_review_reference", "")).strip()), "rights review reference required")
    require(evidence.get("provider_timestamp_semantics_verified") is True, "provider timestamp semantics must be verified")
    require(len(str(evidence.get("provider_timestamp_semantics_note", "")).strip()) >= 20, "timestamp semantics note is insufficient")
    require(evidence.get("quote_time_authority") in VALID_TIME_AUTHORITY, "invalid quote time authority")
    require(bool(str(evidence.get("provider_observed_at_field", "")).strip()), "provider observed_at field required")
    require(evidence.get("canonical_game_mapping_method") == "exact", "only exact game mapping is allowed")
    require(evidence.get("public_redistribution_allowed") is False, "public redistribution must remain disabled")
    require(evidence.get("raw_source_retention_scope") in {"private_ephemeral", "private_user_controlled"}, "raw source must remain private")
    require(evidence.get("target_bookmaker_id") == payload.get("target_bookmaker_id"), "bookmaker evidence mismatch")
    require(evidence.get("market_id") == payload.get("market_id"), "market evidence mismatch")
    require(evidence.get("includes_overtime") is payload.get("includes_overtime"), "overtime evidence mismatch")


def seal_evidence(input_path: Path, evidence_draft_path: Path, raw_source_path: Path, output_path: Path) -> dict[str, Any]:
    normalized = require_private_path(input_path, "normalized input")
    draft = require_private_path(evidence_draft_path, "evidence draft")
    raw = require_private_path(raw_source_path, "raw source")
    output = require_private_path(output_path, "sealed evidence output")
    require(normalized.is_file(), "normalized input file not found")
    require(draft.is_file(), "evidence draft file not found")
    require(raw.is_file(), "raw source file not found")
    require(output != draft, "sealed evidence output must be a new file")

    normalized_bytes = normalized.read_bytes()
    raw_bytes = raw.read_bytes()
    payload = json.loads(normalized_bytes.decode("utf-8"))
    evidence = json.loads(draft.read_text(encoding="utf-8"))
    _validate_real_input_identity(payload)
    _validate_evidence_draft(payload, evidence)

    sealed = dict(evidence)
    sealed["normalized_input_sha256"] = sha256_bytes(normalized_bytes)
    sealed["raw_source_sha256"] = sha256_bytes(raw_bytes)
    write_json(output, sealed)

    return {
        "formal_state": "G1_2_0_PRIVATE_T60_SOURCE_EVIDENCE_SEALED",
        "offline_only": True,
        "provider_requests_executed": 0,
        "normalized_input_sha256": sealed["normalized_input_sha256"],
        "raw_source_sha256": sealed["raw_source_sha256"],
        "quote_rows_emitted": 0,
        "formal_history_write_authorized": False,
        "market_metrics_executed": False,
        "formal_stake": 0,
        "next_unique_mainline": "RUN_PRIVATE_G1_2_0_REAL_T60_INTAKE_VALIDATOR",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="create an empty private bundle template")
    init.add_argument("--output-dir", required=True, type=Path)
    seal = sub.add_parser("seal", help="validate evidence assertions and bind SHA-256 values")
    seal.add_argument("--input", required=True, type=Path)
    seal.add_argument("--evidence-draft", required=True, type=Path)
    seal.add_argument("--raw-source", required=True, type=Path)
    seal.add_argument("--output-evidence", required=True, type=Path)
    args = parser.parse_args()

    if args.command == "init":
        report = initialize_bundle(args.output_dir)
    else:
        report = seal_evidence(args.input, args.evidence_draft, args.raw_source, args.output_evidence)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
