#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "g1_2_0_private_t60_bundle_preparation_v1.py"
spec = importlib.util.spec_from_file_location("bundle_prep", MODULE_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def expect_error(fn, message: str) -> None:
    try:
        fn()
    except module.BundlePreparationError:
        return
    raise AssertionError(message)


def real_input() -> dict:
    return {
        "contract_fixture_only": False,
        "schema_version": "g1-2-0-real-t60-input-v1",
        "data_mode": "real_governed",
        "slate_id": "private-2026-10-20-wave-1",
        "slate_date": "2026-10-20",
        "analysis_cutoff": "2026-10-20T23:00:00+00:00",
        "evaluation_stage": "T-60m",
        "target_bookmaker_id": "bookmaker_alpha",
        "market_id": "moneyline_ot_included",
        "includes_overtime": True,
        "data_version": "private_v1",
        "lock_window_minutes": {"min": 30, "max": 90},
        "season": "2026-27",
        "competition_type": "regular_season",
        "candidates": [{"private_contract_row": True}],
    }


def valid_evidence() -> dict:
    return {
        "evidence_schema_version": "g1-2-0-real-t60-source-evidence-v1",
        "contract_fixture_only": False,
        "source_id": "private_source_alpha",
        "source_url": "https://example.invalid/private-source",
        "source_rights_state": "private_research_allowed",
        "rights_review_reference": "user-reviewed-private-source-terms-2026-10-20",
        "rights_reviewed_by_user": True,
        "provider_timestamp_semantics_verified": True,
        "provider_timestamp_semantics_note": "Provider snapshot timestamp is documented as quote observation time.",
        "quote_time_authority": "provider_snapshot",
        "provider_observed_at_field": "snapshot.updated_at",
        "target_bookmaker_id": "bookmaker_alpha",
        "market_id": "moneyline_ot_included",
        "includes_overtime": True,
        "canonical_game_mapping_method": "exact",
        "normalized_input_sha256": "PENDING_SEAL",
        "raw_source_sha256": "PENDING_SEAL",
        "raw_source_retention_scope": "private_user_controlled",
        "public_redistribution_allowed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "g120-private-t60-bundle-preparation-validation-v1.json")
    args = parser.parse_args()
    tests = 0

    with tempfile.TemporaryDirectory() as temp:
        base = Path(temp)
        init_dir = base / "private-bundle"
        report = module.initialize_bundle(init_dir)
        assert report["formal_state"] == "G1_2_0_PRIVATE_T60_BUNDLE_TEMPLATE_INITIALIZED"
        assert (init_dir / "t60-input.template.json").is_file()
        assert (init_dir / "source-evidence.draft.json").is_file()
        assert (init_dir / "README_PRIVATE.txt").is_file()
        assert json.loads((init_dir / "t60-input.template.json").read_text())["template_only"] is True
        assert json.loads((init_dir / "source-evidence.draft.json").read_text())["rights_reviewed_by_user"] is False
        tests += 6

        expect_error(lambda: module.initialize_bundle(ROOT / "private-test"), "repository path must be rejected")
        tests += 1

        input_path = base / "real-input.json"
        evidence_path = base / "evidence-draft.json"
        raw_path = base / "raw-source.json"
        sealed_path = base / "sealed-evidence.json"
        input_path.write_text(json.dumps(real_input(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        evidence_path.write_text(json.dumps(valid_evidence(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        raw_path.write_text('{"private_raw_contract":"not_a_real_quote"}\n', encoding="utf-8")
        sealed_report = module.seal_evidence(input_path, evidence_path, raw_path, sealed_path)
        sealed = json.loads(sealed_path.read_text(encoding="utf-8"))
        assert sealed_report["formal_state"] == "G1_2_0_PRIVATE_T60_SOURCE_EVIDENCE_SEALED"
        assert sealed["normalized_input_sha256"].startswith("sha256:")
        assert sealed["raw_source_sha256"].startswith("sha256:")
        assert sealed_report["quote_rows_emitted"] == 0
        assert sealed_report["formal_stake"] == 0
        tests += 5

        mutations = [
            ("rights_reviewed_by_user", False, "bad-rights.json"),
            ("provider_timestamp_semantics_verified", False, "bad-time.json"),
            ("quote_time_authority", "collector_fetched_at", "bad-authority.json"),
            ("public_redistribution_allowed", True, "bad-public.json"),
        ]
        for key, value, filename in mutations:
            bad = valid_evidence()
            bad[key] = value
            evidence_path.write_text(json.dumps(bad), encoding="utf-8")
            expect_error(lambda f=filename: module.seal_evidence(input_path, evidence_path, raw_path, base / f), f"{key} mutation must fail")
            tests += 1

        bad_input = real_input()
        bad_input["target_bookmaker_id"] = "placeholder"
        input_path.write_text(json.dumps(bad_input), encoding="utf-8")
        evidence_path.write_text(json.dumps(valid_evidence()), encoding="utf-8")
        expect_error(lambda: module.seal_evidence(input_path, evidence_path, raw_path, base / "bad-book.json"), "placeholder bookmaker must fail")
        tests += 1

        templated = real_input()
        templated["template_only"] = True
        input_path.write_text(json.dumps(templated), encoding="utf-8")
        expect_error(lambda: module.seal_evidence(input_path, evidence_path, raw_path, base / "bad-template.json"), "template input must fail")
        tests += 1

    assert tests == 18
    qa = {
        "schema_version": 1,
        "formal_state": "G1_2_0_PRIVATE_T60_BUNDLE_PREPARATION_HELPER_VALID",
        "offline_only": True,
        "private_paths_outside_repository_required": True,
        "template_is_never_real_input": True,
        "rights_review_required": True,
        "provider_timestamp_semantics_required": True,
        "collector_fetched_at_substitution_allowed": False,
        "public_quote_rows_emitted": 0,
        "provider_requests_executed": 0,
        "formal_history_write_authorized": False,
        "market_metrics_executed": False,
        "contract_tests": tests,
        "formal_stake": 0,
        "next_unique_mainline": "AWAIT_REAL_GOVERNED_2026_27_T60_INPUT_AND_QUALIFIED_TIMESTAMPED_ODDS",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(qa, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
