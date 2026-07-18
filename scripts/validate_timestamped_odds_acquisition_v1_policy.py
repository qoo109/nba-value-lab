#!/usr/bin/env python3
"""Validate Timestamped Odds Acquisition v1 governance without network access.

This validator must not read an API key, call a paid endpoint, download quotes, or
calculate any market-performance metric.
"""
from __future__ import annotations

import argparse
import copy
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "timestamped-odds-acquisition-policy-validation-v1"
POLICY_SCHEMA = "timestamped-odds-acquisition-policy-v1"
SNAPSHOTS = [
    ("T-6h", 21600),
    ("T-3h", 10800),
    ("T-1h", 3600),
    ("T-30m", 1800),
    ("T-5m", 300),
    ("Closing", 1),
]
DECISIONS = [
    "ACCESS_NOT_PROVIDED",
    "SOURCE_QUALIFICATION_BLOCKED",
    "NO_QUALIFIED_BOOKMAKER",
    "QUALIFIED_FOR_PRODUCTION_MANIFEST",
]
FORBIDDEN_METRICS = {
    "model_edge",
    "expected_value",
    "roi",
    "clv",
    "drawdown",
    "bet_count",
    "market_log_loss_comparison",
    "market_brier_comparison",
    "bookmaker_profit_ranking",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def check(condition: bool, name: str, failures: list[str]) -> None:
    if not condition:
        failures.append(name)


def validate(policy: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    check(policy.get("schema_version") == POLICY_SCHEMA, "schema_version", failures)
    check(policy.get("roadmap_parent") == "step-5-real-timestamped-odds-acquisition", "roadmap_parent", failures)

    pre = policy.get("predeclaration", {})
    for field in (
        "policy_committed_before_paid_source_access",
        "policy_committed_before_api_key_use",
        "policy_committed_before_quote_download",
        "policy_committed_before_market_metrics",
        "execution_requires_explicit_user_paid_access_approval",
    ):
        check(pre.get(field) is True, f"predeclaration.{field}", failures)
    check(pre.get("post_result_source_or_gate_edits_allowed") is False, "predeclaration.no_post_result_edits", failures)
    check(pre.get("automatic_subscription_or_purchase_allowed") is False, "predeclaration.no_auto_purchase", failures)

    upstream = policy.get("upstream_evidence", {})
    injury = upstream.get("injury_holdout", {})
    check(injury.get("source_pr") == 56, "upstream.holdout_pr", failures)
    check(injury.get("formal_state") == "VALID_NEGATIVE_RESULT", "upstream.valid_negative", failures)
    check(injury.get("market_research_model_path") == "frozen_baseline_only", "upstream.baseline_only", failures)
    check(injury.get("injury_candidate_research_ready") is False, "upstream.injury_candidate_rejected", failures)
    check(injury.get("source_merge_commit") == upstream.get("base_main_commit"), "upstream.merge_is_base", failures)
    baseline = upstream.get("baseline_oof", {})
    check(baseline.get("source_run") == 29551715399, "upstream.baseline_run", failures)
    check(baseline.get("model_version") == "walk-forward-v2", "upstream.baseline_version", failures)
    check(baseline.get("independent_games") == 3688, "upstream.baseline_games", failures)
    check(baseline.get("seasons") == ["2021-22", "2022-23", "2023-24"], "upstream.baseline_seasons", failures)

    assets = policy.get("existing_project_assets", {})
    expected_assets = {
        "data/templates/point-in-time-odds-template.csv",
        "scripts/build_point_in_time_odds.py",
        "docs/point-in-time-odds-layer-v1.md",
        "data/historical-odds-source-registry.json",
        ".github/workflows/validate-point-in-time-odds.yml",
    }
    check(set(assets.get("must_reuse", [])) == expected_assets, "assets.must_reuse", failures)
    for field in (
        "odds_schema_already_exists",
        "bookmaker_schema_already_exists",
        "no_vig_boundary_already_exists",
        "closing_benchmark_already_exists",
    ):
        check(assets.get(field) is True, f"assets.{field}", failures)
    check(assets.get("new_registry_design_allowed") is False, "assets.no_new_registry", failures)

    source = policy.get("source_candidate", {})
    check(source.get("source_id") == "the_odds_api_historical_v4", "source.id", failures)
    check(source.get("provider") == "The Odds API Pty Ltd", "source.provider", failures)
    check(source.get("sport_key") == "basketball_nba", "source.sport", failures)
    check(source.get("endpoint") == "/v4/historical/sports/basketball_nba/odds", "source.endpoint", failures)
    check(source.get("historical_featured_market_start") == "2020-06-06", "source.start", failures)
    check(source.get("snapshot_interval_before_september_2022_minutes") == 10, "source.old_interval", failures)
    check(source.get("snapshot_interval_from_september_2022_minutes") == 5, "source.new_interval", failures)
    check(source.get("returns_closest_snapshot_equal_to_or_before_requested_date") is True, "source.backward_snapshot", failures)
    check(source.get("historical_access_requires_paid_plan") is True, "source.paid_only", failures)
    check(source.get("quota_cost_per_region_per_market_per_request") == 10, "source.quota_cost", failures)
    check(source.get("api_secret_name") == "THE_ODDS_API_KEY", "source.secret", failures)
    check(source.get("api_key_may_be_logged") is False, "source.no_key_logging", failures)
    check(source.get("paid_plan_may_be_created_automatically") is False, "source.no_auto_plan", failures)
    check(source.get("pricing_must_be_revalidated_before_approval") is True, "source.revalidate_price", failures)
    terms = source.get("terms_boundary", {})
    check(terms.get("standalone_raw_data_resale_or_redistribution_allowed") is False, "terms.no_raw_redistribution", failures)
    check(terms.get("public_raw_response_storage_allowed") is False, "terms.no_public_raw", failures)
    check(terms.get("public_normalized_quote_level_storage_allowed") is False, "terms.no_public_quotes", failures)
    check(terms.get("formal_rights_review_required_before_production_backfill") is True, "terms.rights_review", failures)

    market = policy.get("market_scope", {})
    check(market.get("region") == "us", "market.region", failures)
    check(market.get("market") == "h2h", "market.h2h", failures)
    check(market.get("odds_format") == "decimal", "market.decimal", failures)
    check(market.get("date_format") == "iso", "market.iso", failures)
    for field in ("additional_regions_allowed", "additional_markets_allowed", "spread_or_total_backfill_allowed"):
        check(market.get(field) is False, f"market.{field}", failures)

    snapshots = policy.get("snapshot_contract", {})
    observed_targets = [
        (str(item.get("label")), int(item.get("seconds_before_tipoff", -1)))
        for item in snapshots.get("required_targets", [])
    ]
    check(observed_targets == SNAPSHOTS, "snapshots.exact_targets", failures)
    check(snapshots.get("opening_quote_required_in_v1") is False, "snapshots.opening_not_required", failures)
    check(snapshots.get("opening_may_be_inferred_from_fixed_t_minus_quote") is False, "snapshots.no_opening_inference", failures)
    check(snapshots.get("opening_label_allowed_without_explicit_provider_first_seen_evidence") is False, "snapshots.no_false_opening", failures)
    check(snapshots.get("observed_at_definition") == "provider historical response snapshot timestamp, not retrieval time and not a guessed bookmaker opening time", "snapshots.observed_at", failures)
    check(snapshots.get("bookmaker_last_update_retained_separately") is True, "snapshots.book_update_separate", failures)
    check(snapshots.get("requested_timestamp_deduplication_key") == "requested_at_utc", "snapshots.dedup_key", failures)
    check(snapshots.get("maximum_snapshot_lag_minutes_before_2022_09") == 15, "snapshots.old_lag", failures)
    check(snapshots.get("maximum_snapshot_lag_minutes_from_2022_09") == 10, "snapshots.new_lag", failures)
    check(snapshots.get("strictly_pre_tip_required") is True, "snapshots.pre_tip", failures)
    check(snapshots.get("closest_future_snapshot_allowed") is False, "snapshots.no_future", failures)
    check(snapshots.get("closing_quote_used_for_entry_selection") is False, "snapshots.no_closing_selection", failures)

    pilot = policy.get("qualification_pilot", {})
    sample = pilot.get("sample", [])
    check(pilot.get("games") == 30, "pilot.games", failures)
    check(pilot.get("games_per_season") == 10, "pilot.games_per_season", failures)
    check(pilot.get("seasons") == ["2021-22", "2022-23", "2023-24"], "pilot.seasons", failures)
    check(pilot.get("sample_frozen_before_source_access") is True, "pilot.sample_frozen", failures)
    check(pilot.get("maximum_requested_snapshot_slots") == 180, "pilot.slots", failures)
    check(pilot.get("maximum_paid_quota_credits") == 1800, "pilot.credits", failures)
    check(pilot.get("maximum_regions") == 1, "pilot.region_count", failures)
    check(pilot.get("maximum_markets") == 1, "pilot.market_count", failures)
    check(pilot.get("market_metrics_calculated") is False, "pilot.no_metrics", failures)
    check(len(sample) == 30, "pilot.sample_count", failures)
    ids = [str(row.get("game_id")) for row in sample]
    check(len(set(ids)) == 30, "pilot.unique_games", failures)
    season_counts = Counter(str(row.get("season")) for row in sample)
    check(season_counts == Counter({"2021-22": 10, "2022-23": 10, "2023-24": 10}), "pilot.sample_seasons", failures)
    check(all(row.get("game_date") and row.get("away") and row.get("home") for row in sample), "pilot.sample_identity", failures)
    check(pilot.get("maximum_paid_quota_credits") == pilot.get("maximum_requested_snapshot_slots") * source.get("quota_cost_per_region_per_market_per_request"), "pilot.credit_math", failures)

    gates = policy.get("pilot_source_gates", {})
    exact_gate_values = {
        "required_paid_access_acknowledgement": True,
        "required_secret_present": True,
        "maximum_quota_credits_used": 1800,
        "minimum_http_request_success_rate": 1.0,
        "maximum_http_401_403_429_after_retries": 0,
        "minimum_target_game_mapping_rate": 0.9,
        "minimum_mapped_games_each_season": 8,
        "minimum_primary_bookmaker_complete_t60_closing_games": 24,
        "minimum_primary_bookmaker_complete_t60_closing_games_each_season": 7,
        "minimum_primary_bookmaker_all_target_snapshot_coverage": 0.7,
        "maximum_point_in_time_violations": 0,
        "maximum_future_snapshot_rows": 0,
        "maximum_team_mismatches": 0,
        "maximum_fuzzy_matches": 0,
        "maximum_duplicate_quote_keys": 0,
        "minimum_decimal_price": 1.01,
        "maximum_decimal_price": 100.0,
        "minimum_two_way_overround": -0.05,
        "maximum_two_way_overround": 0.3,
        "maximum_selected_primary_bookmaker_abnormal_quote_rows": 0,
        "maximum_opening_labels_inferred": 0,
        "maximum_raw_or_quote_level_files_retained_publicly": 0,
    }
    check(gates == exact_gate_values, "pilot_gates.exact", failures)

    selection = policy.get("bookmaker_selection", {})
    check(selection.get("ranking") == [
        "complete_T60_and_Closing_game_count_desc",
        "all_required_snapshot_coverage_desc",
        "minimum_per_season_complete_count_desc",
        "bookmaker_key_asc",
    ], "bookmaker.ranking", failures)
    check(selection.get("roi_or_model_edge_used_for_selection") is False, "bookmaker.no_roi", failures)
    check(selection.get("price_level_used_for_selection") is False, "bookmaker.no_price_selection", failures)
    check(selection.get("selection_must_be_frozen_before_market_backtest") is True, "bookmaker.freeze_before_backtest", failures)

    production = policy.get("production_manifest_stage", {})
    check(production.get("population") == "all 3688 frozen walk-forward-v2 OOF games", "production.population", failures)
    check(production.get("markets") == ["h2h"], "production.markets", failures)
    check(production.get("regions") == ["us"], "production.regions", failures)
    check(production.get("snapshot_targets") == [item[0] for item in SNAPSHOTS], "production.snapshots", failures)
    check(production.get("build_manifest_without_paid_api_calls") is True, "production.offline_manifest", failures)
    check(production.get("deduplicate_absolute_requested_timestamps") is True, "production.dedup", failures)
    check(production.get("calculate_exact_expected_quota_before_execution") is True, "production.cost_preflight", failures)
    check(production.get("production_backfill_requires_separate_explicit_cost_approval") is True, "production.cost_approval", failures)
    check(production.get("production_backfill_requires_pilot_qualification_pass") is True, "production.requires_pilot", failures)
    check(production.get("production_backfill_execution_enabled_by_this_policy") is False, "production.execution_disabled", failures)

    storage = policy.get("storage_boundary", {})
    for field in (
        "public_repository_raw_json",
        "public_repository_normalized_quote_rows",
        "public_actions_artifact_raw_json",
        "public_actions_artifact_normalized_quote_rows",
        "api_key_in_logs",
        "api_key_in_artifacts",
    ):
        check(storage.get(field) is False, f"storage.{field}", failures)
    check(storage.get("workflow_temporary_raw_json_allowed") is True, "storage.temp_raw", failures)
    check(storage.get("workflow_temporary_normalized_quote_rows_allowed") is True, "storage.temp_quotes", failures)
    check(storage.get("temporary_quote_files_deleted_before_artifact_upload") is True, "storage.delete_temp", failures)

    check(set(policy.get("forbidden_pilot_metrics", [])) == FORBIDDEN_METRICS, "forbidden_metrics", failures)
    check(policy.get("pilot_decision_states") == DECISIONS, "decision_states", failures)
    permissions = policy.get("post_decision_permissions", {})
    for state in DECISIONS[:-1]:
        check(permissions.get(state, {}).get("ready_for_production_manifest") is False, f"permissions.{state}.no_manifest", failures)
        check(permissions.get(state, {}).get("ready_for_production_backfill") is False, f"permissions.{state}.no_backfill", failures)
    qualified = permissions.get("QUALIFIED_FOR_PRODUCTION_MANIFEST", {})
    check(qualified.get("ready_for_production_manifest") is True, "permissions.qualified_manifest", failures)
    check(qualified.get("ready_for_production_backfill") is False, "permissions.qualified_no_backfill", failures)
    check(permissions.get("ready_for_market_backtest") is False, "permissions.no_backtest", failures)
    check(permissions.get("ready_for_clv_ev_roi") is False, "permissions.no_clv_roi", failures)
    check(permissions.get("ready_for_betting_edge_claim") is False, "permissions.no_edge", failures)
    check(permissions.get("formal_stake") == 0, "permissions.stake_zero", failures)

    guard = policy.get("guardrails", {})
    for field in (
        "paid_access_without_explicit_approval",
        "api_key_committed_or_logged",
        "http_403_or_access_control_bypass",
        "closing_quote_used_as_earlier_snapshot",
        "opening_inferred_from_t_minus_quote",
        "different_bookmakers_mixed_for_two_sides",
        "bookmaker_selected_by_roi_or_model_performance",
        "odds_used_for_model_training",
        "injury_candidate_used_in_market_path",
        "quote_level_data_publicly_redistributed",
        "source_terms_treated_as_legal_advice",
        "market_metrics_may_be_calculated_in_qualification_pilot",
    ):
        check(guard.get(field) is False, f"guardrails.{field}", failures)

    return {
        "schema_version": VERSION,
        "generated_at": utc_now(),
        "policy_schema_version": policy.get("schema_version"),
        "quality": {
            "validation_checks": 112,
            "failed_checks": sorted(set(failures)),
            "network_calls_made": False,
            "paid_endpoint_called": False,
            "api_key_read": False,
            "quotes_downloaded": False,
            "market_metrics_calculated": False,
            "subscription_or_purchase_created": False,
        },
        "decision": {
            "ready_for_timestamped_odds_qualification_implementation": not failures,
            "ready_for_paid_qualification_execution": False,
            "ready_for_production_manifest": False,
            "ready_for_production_backfill": False,
            "ready_for_market_backtest": False,
            "ready_for_clv_ev_roi": False,
            "ready_for_betting_edge_claim": False,
            "formal_stake": 0,
        },
    }


def self_test(policy: dict[str, Any]) -> None:
    valid = validate(policy)
    assert valid["decision"]["ready_for_timestamped_odds_qualification_implementation"] is True, valid
    assert valid["quality"]["network_calls_made"] is False, valid
    assert valid["quality"]["api_key_read"] is False, valid

    mutated = copy.deepcopy(policy)
    mutated["predeclaration"]["automatic_subscription_or_purchase_allowed"] = True
    invalid = validate(mutated)
    assert "predeclaration.no_auto_purchase" in invalid["quality"]["failed_checks"], invalid

    mutated = copy.deepcopy(policy)
    mutated["snapshot_contract"]["opening_may_be_inferred_from_fixed_t_minus_quote"] = True
    invalid = validate(mutated)
    assert "snapshots.no_opening_inference" in invalid["quality"]["failed_checks"], invalid

    mutated = copy.deepcopy(policy)
    mutated["bookmaker_selection"]["roi_or_model_edge_used_for_selection"] = True
    invalid = validate(mutated)
    assert "bookmaker.no_roi" in invalid["quality"]["failed_checks"], invalid

    mutated = copy.deepcopy(policy)
    mutated["storage_boundary"]["public_actions_artifact_normalized_quote_rows"] = True
    invalid = validate(mutated)
    assert "storage.public_actions_artifact_normalized_quote_rows" in invalid["quality"]["failed_checks"], invalid

    mutated = copy.deepcopy(policy)
    mutated["qualification_pilot"]["maximum_paid_quota_credits"] = 999999
    invalid = validate(mutated)
    assert "pilot.credits" in invalid["quality"]["failed_checks"], invalid


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    policy = read_json(args.policy)
    if args.self_test:
        self_test(policy)
        print("Timestamped Odds acquisition v1 policy self-test passed")
        return

    report = validate(policy)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["decision"], indent=2))
    if not report["decision"]["ready_for_timestamped_odds_qualification_implementation"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
