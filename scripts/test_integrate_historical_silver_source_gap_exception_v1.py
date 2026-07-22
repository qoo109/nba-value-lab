#!/usr/bin/env python3
"""Synthetic-only tests for the source-gap exception transformer v1."""
from __future__ import annotations

import argparse
import copy
import json
import unittest
from pathlib import Path
from typing import Any

from integrate_historical_silver_source_gap_exception_v1 import (
    IntegrationValidationError,
    MAX_OUTPUT_BYTES,
    PROHIBITED_KEYS,
    integrate_documented_source_gap,
)

REASON_KEYS = (
    "missing_home_team_feature",
    "missing_away_team_feature",
    "missing_both_team_features",
    "silver_feature_pair_identity_mismatch",
    "gold_team_feature_transfer_mismatch",
    "gold_matchup_builder_omission",
    "silver_game_outside_gold_identity_contract",
    "unclassified",
)


def fixture_raw_report() -> dict[str, Any]:
    reasons = {key: 0 for key in REASON_KEYS}
    reasons["missing_both_team_features"] = 2
    return {
        "schema_version": "historical-gold-silver-coverage-reconciliation-report-v1",
        "generated_at": "synthetic",
        "formal_outcome": "HISTORICAL_GOLD_SILVER_COVERAGE_RECONCILIATION_SOURCE_DATA_GAP_CONFIRMED",
        "scope": {
            "season_labels": ["2019-20", "2020-21", "2021-22", "2022-23", "2023-24"],
            "silver_game_rows": 5826,
            "gold_matchup_rows": 5824,
            "gold_matchup_rows_outside_scope": 0,
        },
        "coverage": {
            "covered_games": 5824,
            "missing_gold_for_silver": 2,
            "classified_missing_games": 2,
            "unclassified_missing_games": 0,
            "covered_by_season": {"2023-24": 1228},
            "missing_by_season": {"2023-24": 2},
            "missing_by_reason": copy.deepcopy(reasons),
            "missing_by_season_and_reason": {"2023-24": copy.deepcopy(reasons)},
            "silver_feature_count_histogram": {"0": 2, "2": 5824},
            "gold_feature_count_histogram": {"0": 2, "2": 5824},
        },
        "decision": {
            "builder_repair_required": False,
            "source_data_reconciliation_required": True,
            "ready_for_followup_repair_design": True,
            "ready_for_cross_source_audit_rerun": False,
            "ready_for_market_backtest": False,
            "ready_for_model_retraining": False,
            "formal_stake": 0,
        },
        "boundaries": {
            "raw_rows_emitted": 0,
            "raw_files_emitted": False,
            "game_ids_emitted": False,
            "dates_emitted": False,
            "team_codes_emitted": False,
            "row_key_hashes_emitted": False,
            "historical_silver_replacement_allowed": False,
            "historical_gold_replacement_allowed": False,
            "opening_or_closing_labels_allowed": False,
            "point_in_time_market_backtest_allowed": False,
            "model_retraining_allowed": False,
            "betting_edge_claim_allowed": False,
            "formal_stake": 0,
        },
    }


def fixture_manifest() -> dict[str, Any]:
    return {
        "schema_version": "historical-silver-2023-24-source-gap-exception-manifest-v1",
        "formal_state": "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_MANIFEST_DESIGN_READY",
        "season_label": "2023-24",
        "aggregate_scope": {
            "source_gap_exception_games": 2,
            "unclassified_games": 0,
            "missing_reason": "nbastats_game_present_pbpstats_game_absent",
        },
        "exception_class": {
            "exception_code": "SOURCE_ARCHIVE_PBPSTATS_GAME_ABSENT",
            "upstream_gap_stable": True,
            "silver_builder_defect": False,
            "gold_builder_defect": False,
        },
        "public_evidence_policy": {
            "aggregate_only": True,
            "game_ids_allowed": False,
            "dates_allowed": False,
            "team_codes_allowed": False,
            "row_level_records_allowed": False,
        },
        "exception_handling_policy": {
            "mode": "DOCUMENTED_AGGREGATE_ONLY_NO_ROW_PATCH",
            "synthesize_team_feature_rows": False,
            "insert_manual_team_feature_rows": False,
        },
    }


def fixture_policy() -> dict[str, Any]:
    return {
        "schema_version": "historical-silver-2023-24-source-gap-exception-integration-policy-v1",
        "formal_state": "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_POLICY_DESIGN_READY",
        "recognition_gate": {
            "all_conditions_required": True,
            "on_any_mismatch": "FAIL_CLOSED_UNEXPLAINED_COVERAGE_GAP",
            "partial_recognition_allowed": False,
            "automatic_count_adjustment_allowed": False,
        },
        "reporting_contract": {
            "preserve_raw_metrics": True,
            "gold_coverage_rewritten_as_complete": False,
        },
        "decision_semantics": {
            "gold_dataset_complete": False,
            "formal_stake": 0,
        },
    }


def recursively_contains_prohibited_key(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            key in PROHIBITED_KEYS or recursively_contains_prohibited_key(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(recursively_contains_prohibited_key(item) for item in value)
    return False


class SourceGapIntegrationTests(unittest.TestCase):
    def run_transform(
        self,
        raw: dict[str, Any] | None = None,
        manifest: dict[str, Any] | None = None,
        policy: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return integrate_documented_source_gap(
            raw if raw is not None else fixture_raw_report(),
            manifest if manifest is not None else fixture_manifest(),
            policy if policy is not None else fixture_policy(),
        )

    def test_valid_fixture_recognizes_exactly_two(self) -> None:
        output = self.run_transform()
        reporting = output["documented_exception_reporting"]
        self.assertTrue(reporting["recognition_gate_passed"])
        self.assertEqual(reporting["documented_source_gap_exception_count"], 2)
        self.assertEqual(reporting["unexplained_missing_count_after_documentation"], 0)
        self.assertEqual(reporting["covered_or_documented_count"], 5826)

    def test_raw_missing_three_fails_closed(self) -> None:
        raw = fixture_raw_report()
        raw["coverage"]["missing_gold_for_silver"] = 3
        output = self.run_transform(raw=raw)
        reporting = output["documented_exception_reporting"]
        self.assertFalse(reporting["recognition_gate_passed"])
        self.assertEqual(reporting["documented_source_gap_exception_count"], 0)
        self.assertEqual(reporting["unexplained_missing_count_after_documentation"], 3)

    def test_wrong_missing_reason_fails_closed(self) -> None:
        raw = fixture_raw_report()
        raw["coverage"]["missing_by_reason"]["missing_both_team_features"] = 0
        raw["coverage"]["missing_by_reason"]["missing_home_team_feature"] = 2
        output = self.run_transform(raw=raw)
        self.assertFalse(output["documented_exception_reporting"]["recognition_gate_passed"])

    def test_builder_repair_true_fails_closed(self) -> None:
        raw = fixture_raw_report()
        raw["decision"]["builder_repair_required"] = True
        output = self.run_transform(raw=raw)
        self.assertIn(
            "BUILDER_REPAIR_REQUIRED",
            output["documented_exception_reporting"]["recognition_failure_reasons"],
        )

    def test_unclassified_missing_fails_closed(self) -> None:
        raw = fixture_raw_report()
        raw["coverage"]["unclassified_missing_games"] = 1
        output = self.run_transform(raw=raw)
        self.assertFalse(output["documented_exception_reporting"]["recognition_gate_passed"])

    def test_manifest_count_mutation_fails_closed(self) -> None:
        manifest = fixture_manifest()
        manifest["aggregate_scope"]["source_gap_exception_games"] = 3
        output = self.run_transform(manifest=manifest)
        self.assertIn(
            "MANIFEST_EXCEPTION_COUNT_MISMATCH",
            output["documented_exception_reporting"]["recognition_failure_reasons"],
        )

    def test_exception_code_mutation_fails_closed(self) -> None:
        manifest = fixture_manifest()
        manifest["exception_class"]["exception_code"] = "OTHER"
        output = self.run_transform(manifest=manifest)
        self.assertIn(
            "EXCEPTION_CODE_MISMATCH",
            output["documented_exception_reporting"]["recognition_failure_reasons"],
        )

    def test_nonzero_stake_fails_closed(self) -> None:
        raw = fixture_raw_report()
        raw["decision"]["formal_stake"] = 1
        output = self.run_transform(raw=raw)
        self.assertIn(
            "RAW_FORMAL_STAKE_NONZERO",
            output["documented_exception_reporting"]["recognition_failure_reasons"],
        )

    def test_identifier_boundary_mutation_fails_closed(self) -> None:
        raw = fixture_raw_report()
        raw["boundaries"]["game_ids_emitted"] = True
        output = self.run_transform(raw=raw)
        self.assertIn(
            "RAW_IDENTIFIER_BOUNDARY_VIOLATION",
            output["documented_exception_reporting"]["recognition_failure_reasons"],
        )

    def test_prohibited_identifier_key_raises_before_output(self) -> None:
        raw = fixture_raw_report()
        raw["coverage"]["game_id"] = "synthetic-do-not-persist"
        with self.assertRaises(IntegrationValidationError):
            self.run_transform(raw=raw)

    def test_structurally_incomplete_input_raises_before_output(self) -> None:
        raw = fixture_raw_report()
        del raw["coverage"]["missing_by_season"]
        with self.assertRaises(IntegrationValidationError):
            self.run_transform(raw=raw)

    def test_inputs_remain_byte_equivalent(self) -> None:
        raw = fixture_raw_report()
        manifest = fixture_manifest()
        policy = fixture_policy()
        before = json.dumps([raw, manifest, policy], sort_keys=True, separators=(",", ":"))
        self.run_transform(raw, manifest, policy)
        after = json.dumps([raw, manifest, policy], sort_keys=True, separators=(",", ":"))
        self.assertEqual(before, after)

    def test_output_is_aggregate_only_and_below_limit(self) -> None:
        output = self.run_transform()
        payload = json.dumps(output, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self.assertLess(len(payload), MAX_OUTPUT_BYTES)
        self.assertFalse(recursively_contains_prohibited_key(output))
        self.assertFalse(output["documented_exception_reporting"]["gold_dataset_complete"])

    def test_partial_recognition_policy_mutation_fails_closed(self) -> None:
        policy = fixture_policy()
        policy["recognition_gate"]["partial_recognition_allowed"] = True
        output = self.run_transform(policy=policy)
        self.assertIn(
            "POLICY_PARTIAL_RECOGNITION_ENABLED",
            output["documented_exception_reporting"]["recognition_failure_reasons"],
        )

    def test_policy_fail_closed_mode_mutation_fails_closed(self) -> None:
        policy = fixture_policy()
        policy["recognition_gate"]["on_any_mismatch"] = "ALLOW"
        output = self.run_transform(policy=policy)
        self.assertIn(
            "POLICY_FAIL_CLOSED_MODE_MISMATCH",
            output["documented_exception_reporting"]["recognition_failure_reasons"],
        )

    def test_missing_season_fails_closed(self) -> None:
        raw = fixture_raw_report()
        raw["scope"]["season_labels"].remove("2023-24")
        output = self.run_transform(raw=raw)
        self.assertIn(
            "SEASON_SCOPE_MISMATCH",
            output["documented_exception_reporting"]["recognition_failure_reasons"],
        )

    def test_wrong_formal_outcome_fails_closed(self) -> None:
        raw = fixture_raw_report()
        raw["formal_outcome"] = "OTHER"
        output = self.run_transform(raw=raw)
        self.assertIn(
            "RAW_FORMAL_OUTCOME_MISMATCH",
            output["documented_exception_reporting"]["recognition_failure_reasons"],
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SourceGapIntegrationTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    summary = {
        "schema_version": "historical-silver-source-gap-exception-integration-synthetic-test-summary-v1",
        "formal_state": (
            "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_SYNTHETIC_TESTS_PASS"
            if result.wasSuccessful()
            else "HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_SYNTHETIC_TESTS_FAIL"
        ),
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "successful": result.wasSuccessful(),
        "real_data_read": False,
        "database_access": False,
        "network_access": False,
        "row_level_output": False,
        "formal_stake": 0,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
