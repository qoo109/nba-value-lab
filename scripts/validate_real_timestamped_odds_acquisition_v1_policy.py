#!/usr/bin/env python3
"""Validate the frozen Real Timestamped Odds Acquisition v1 predeclaration.

Policy-only: no network access, no API secret, no odds rows, no outcomes, no fitting,
and no market-performance calculations.
"""
from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "real-timestamped-odds-acquisition-policy-v1"
EXPECTED_MAIN = "95bf21a2b7dbe44cbd3eba09a9d72873c391fc70"
EXPECTED_SOURCE = "the_odds_api_historical_v4"
EXPECTED_SEASON_COUNTS = {"2021-22": 1230, "2022-23": 1230, "2023-24": 1228}
EXPECTED_FIXED_SNAPSHOTS = {
    "T-6h": 21600,
    "T-3h": 10800,
    "T-1h": 3600,
    "T-30m": 1800,
    "Closing": 1,
}
EXPECTED_OPENING_GRID = {
    "T-14d": 1209600,
    "T-10d": 864000,
    "T-7d": 604800,
    "T-5d": 432000,
    "T-3d": 259200,
    "T-48h": 172800,
    "T-24h": 86400,
    "T-12h": 43200,
    "T-6h": 21600,
}
EXPECTED_DECISIONS = [
    "SOURCE_ACCESS_BLOCKED",
    "SOURCE_STRUCTURAL_BLOCKED",
    "PILOT_READY_FOR_FULL_BACKFILL",
    "FULL_BACKFILL_READY_FOR_ODDS_JOIN_PREDECLARATION",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def as_label_map(rows: Any, field: str = "label") -> dict[str, int]:
    if not isinstance(rows, list):
        return {}
    result: dict[str, int] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        label = row.get(field)
        seconds = row.get("seconds_before_anchor_commence")
        if isinstance(label, str) and isinstance(seconds, int):
            result[label] = seconds
    return result


def validate_policy(policy: dict[str, Any]) -> tuple[list[str], int]:
    errors: list[str] = []
    checks = 0

    def check(condition: bool, message: str) -> None:
        nonlocal checks
        checks += 1
        require(condition, message, errors)

    check(policy.get("schema_version") == SCHEMA_VERSION, "schema_version changed")
    check(policy.get("roadmap_parent") == "step-5-real-timestamped-odds-acquisition", "roadmap parent changed")

    pre = policy.get("predeclaration", {})
    for key in (
        "policy_committed_before_paid_api_request",
        "policy_committed_before_raw_historical_odds_inspection",
        "policy_committed_before_coverage_results",
        "policy_committed_before_market_backtest",
    ):
        check(pre.get(key) is True, f"predeclaration flag {key} must be true")
    for key in (
        "post_result_source_substitution_allowed",
        "post_result_population_substitution_allowed",
        "post_result_snapshot_substitution_allowed",
        "outcome_or_roi_based_bookmaker_selection_allowed",
    ):
        check(pre.get(key) is False, f"forbidden predeclaration flag {key} must be false")

    upstream = policy.get("upstream_evidence", {})
    check(upstream.get("base_main_commit") == EXPECTED_MAIN, "base main commit changed")
    holdout = upstream.get("injury_holdout", {})
    check(holdout.get("source_pr") == 56, "holdout source PR must remain 56")
    check(holdout.get("formal_state") == "VALID_NEGATIVE_RESULT", "holdout decision changed")
    check(holdout.get("market_research_model_path") == "frozen_baseline_only", "market path must remain baseline-only")
    baseline = upstream.get("baseline_oof", {})
    check(baseline.get("source_run") == 29551715399, "baseline OOF run changed")
    check(baseline.get("artifact_name") == "model-walk-forward-v2", "baseline artifact changed")
    check(baseline.get("model_version") == "walk-forward-v2", "baseline model version changed")
    check(baseline.get("calibration_decision") == "raw_logistic_elo", "calibration decision changed")

    reused = policy.get("existing_assets_reused", {})
    check(reused.get("rebuild_schema_or_registry") is False, "odds schema/registry must not be rebuilt")
    for key in ("point_in_time_odds_layer", "odds_builder", "odds_template", "source_registry"):
        check(bool(reused.get(key)), f"existing asset {key} must be referenced")

    source = policy.get("source_contract", {})
    check(source.get("primary_source_id") == EXPECTED_SOURCE, "primary source changed")
    check(source.get("historical_access") == "paid_plan_only", "paid historical access boundary changed")
    check(source.get("api_secret_name") == "THE_ODDS_API_KEY", "API secret name changed")
    check(source.get("api_key_must_remain_secret") is True, "API key secrecy disabled")
    check(source.get("api_key_in_logs_or_artifacts") is False, "API key exposure enabled")
    check(source.get("standalone_data_resale_or_redistribution") is False, "standalone redistribution enabled")
    check(source.get("public_raw_or_normalized_odds_rows") is False, "public odds-row publication enabled")
    check(source.get("restricted_storage_required_for_raw_and_normalized_rows") is True, "restricted storage requirement removed")
    check(source.get("workflow_temporary_raw_files_deleted") is True, "temporary raw deletion disabled")
    documented = source.get("documented_source_properties", {})
    check(documented.get("featured_market_history_start") == "2020-06-06", "source history start changed")
    check(documented.get("snapshot_interval_before_2022_09_18_minutes") == 10, "pre-2022 snapshot interval changed")
    check(documented.get("snapshot_interval_from_2022_09_18_minutes") == 5, "post-2022 snapshot interval changed")
    check(documented.get("historical_query_returns_closest_snapshot_at_or_before_requested_time") is True, "snapshot selection semantics changed")
    check(documented.get("historical_endpoint_credit_cost_per_region_per_market") == 10, "historical credit rule changed")

    population = policy.get("full_target_population", {})
    check(population.get("independent_games") == 3688, "full target population changed")
    check(population.get("deduplication_key") == "game_id", "game-level dedup key changed")
    check(population.get("model_path") == "frozen_baseline_only", "full target model path changed")
    check(population.get("injury_candidate_included") is False, "rejected injury candidate reintroduced")
    check(population.get("game_outcomes_used_for_acquisition_selection") is False, "outcomes allowed in acquisition selection")
    check(population.get("closing_market_results_used_for_acquisition_selection") is False, "closing results allowed in acquisition selection")
    season_counts = {
        row.get("season_label"): row.get("games")
        for row in population.get("seasons", [])
        if isinstance(row, dict)
    }
    check(season_counts == EXPECTED_SEASON_COUNTS, "season counts changed")
    check(sum(season_counts.values()) == 3688, "season counts no longer sum to 3,688")

    pilot = policy.get("pilot_population", {})
    check(pilot.get("independent_games") == 90, "pilot game count changed")
    check(pilot.get("games_per_season") == 30, "pilot per-season count changed")
    check(pilot.get("selection_salt") == "timestamped-odds-v1-pilot", "pilot selection salt changed")
    check(pilot.get("selection_uses_outcomes_or_existing_odds") is False, "pilot may not use outcomes or odds")
    check(pilot.get("pilot_manifest_must_be_frozen_before_api_requests") is True, "pilot manifest freeze removed")
    check(pilot.get("date_or_game_replacement_after_failure") is False, "failed pilot rows may not be replaced")

    query = policy.get("api_query_contract", {})
    check(query.get("sport_key") == "basketball_nba", "sport key changed")
    check(query.get("region") == "us", "region changed")
    check(query.get("markets") == ["h2h"], "v1 market must remain h2h only")
    check(query.get("odds_format") == "decimal", "canonical odds format changed")
    check(query.get("date_format") == "iso", "date format changed")
    check(query.get("include_sids") is True, "source ID capture disabled")
    check(query.get("include_links") is False, "bookmaker links unexpectedly enabled")
    check(query.get("bookmakers_parameter") is None, "bookmaker list must not be outcome-selected")
    check(query.get("spread_and_total_acquisition_in_v1") is False, "spread/total scope creep detected")

    identity = policy.get("event_identity_contract", {})
    check(identity.get("home_team_exact_after_normalization") is True, "exact home identity disabled")
    check(identity.get("away_team_exact_after_normalization") is True, "exact away identity disabled")
    check(identity.get("provider_commence_local_date_timezone") == "America/New_York", "identity timezone changed")
    check(identity.get("provider_commence_local_date_must_equal_gold_game_date") is True, "date identity gate disabled")
    check(identity.get("fuzzy_team_matching") is False, "fuzzy team matching enabled")
    check(identity.get("fuzzy_schedule_matching") is False, "fuzzy schedule matching enabled")
    check(identity.get("nearest_date_matching") is False, "nearest-date matching enabled")
    check(identity.get("ambiguous_event_matches_allowed") == 0, "ambiguous event matches allowed")
    check(identity.get("maximum_commence_time_drift_minutes_across_snapshots") == 30, "commence drift gate changed")

    snapshots = policy.get("snapshot_contract", {})
    check(as_label_map(snapshots.get("fixed_snapshots")) == EXPECTED_FIXED_SNAPSHOTS, "fixed snapshot contract changed")
    check(as_label_map(snapshots.get("opening_grid")) == EXPECTED_OPENING_GRID, "opening grid changed")
    check(snapshots.get("opening_public_label") == "OpeningGridProxy", "opening proxy label changed")
    check(snapshots.get("opening_must_not_be_described_as_true_first_posted_bookmaker_open") is True, "opening proxy disclosure removed")
    check(snapshots.get("source_snapshot_must_be_at_or_before_requested_time") is True, "future snapshot allowed")
    check(snapshots.get("maximum_source_snapshot_age_minutes") == 15, "snapshot freshness gate changed")
    check(snapshots.get("closing_bookmaker_last_update_max_age_minutes") == 60, "closing staleness gate changed")
    check(snapshots.get("later_snapshot_fallback") is False, "later snapshot fallback enabled")
    check(snapshots.get("cross_book_fill") is False, "cross-book fill enabled")
    check(snapshots.get("cross_game_fill") is False, "cross-game fill enabled")

    quote = policy.get("quote_normalization_contract", {})
    check(quote.get("market_key") == "h2h", "quote market changed")
    check(quote.get("required_outcomes") == ["home_team", "away_team"], "required outcomes changed")
    check(quote.get("draw_outcome_allowed") is False, "draw outcome enabled")
    check(quote.get("decimal_price_strictly_greater_than") == 1.0, "decimal price boundary changed")
    check(quote.get("unique_quote_key") == ["game_id", "snapshot_label", "bookmaker_key", "market_key"], "unique quote key changed")
    check(quote.get("duplicate_quote_keys_allowed") == 0, "duplicate quote keys allowed")
    check(quote.get("missing_prices_imputed") is False, "missing prices imputed")
    check(quote.get("missing_bookmakers_imputed") is False, "missing bookmakers imputed")
    check(quote.get("no_vig_method") == "proportional_two_way", "no-vig baseline changed")
    check(quote.get("no_vig_or_edge_calculated_during_acquisition") is False, "acquisition stage calculates market performance")

    cost = policy.get("request_and_cost_guardrails", {})
    check(cost.get("dry_run_request_plan_required") is True, "dry-run request plan removed")
    check(cost.get("pilot_credit_hard_cap") == 20000, "pilot credit cap changed")
    check(cost.get("abort_before_request_if_pilot_estimate_exceeds_cap") is True, "credit-cap abort removed")
    check(cost.get("http_401_or_403_bypass_allowed") is False, "access-control bypass enabled")
    check(cost.get("maximum_retry_attempts_per_request") == 3, "retry cap changed")
    check(cost.get("full_backfill_requires_separate_explicit_user_budget_approval") is True, "full-backfill approval removed")
    check(cost.get("full_backfill_execution_allowed_by_this_predeclaration_alone") is False, "full backfill improperly authorized")

    pilot_gates = policy.get("pilot_source_health_gates", {})
    expected_pilot = {
        "planned_games": 90,
        "minimum_exact_event_match_rate": 0.95,
        "minimum_exact_event_match_rate_each_season": 0.9,
        "maximum_ambiguous_event_matches": 0,
        "maximum_team_identity_mismatches": 0,
        "minimum_successful_request_rate": 0.95,
        "minimum_snapshot_timestamp_compliance_rate": 1.0,
        "minimum_fixed_snapshot_freshness_rate": 0.99,
        "minimum_games_with_two_or_more_bookmakers_at_t1h": 0.8,
        "minimum_games_with_same_book_t1h_and_closing_pair": 0.8,
        "maximum_secret_exposures": 0,
        "maximum_public_raw_or_normalized_quote_rows": 0,
        "maximum_post_tip_quotes": 0,
        "maximum_later_snapshot_fallbacks": 0,
        "maximum_fuzzy_matches": 0,
    }
    for key, value in expected_pilot.items():
        check(pilot_gates.get(key) == value, f"pilot source-health gate {key} changed")

    full = policy.get("full_backfill_gates", {})
    expected_full = {
        "target_independent_games": 3688,
        "minimum_matched_independent_games": 3000,
        "minimum_matched_games_each_season": 900,
        "minimum_seasons": 3,
        "minimum_t1h_two_sided_quote_coverage": 0.8,
        "minimum_same_book_t1h_and_closing_pair_coverage": 0.8,
        "primary_bookmaker_minimum_overall_pair_coverage": 0.8,
        "primary_bookmaker_minimum_pair_coverage_each_season": 0.7,
        "bookmaker_selection_uses_roi_or_outcomes": False,
        "maximum_point_in_time_violations": 0,
        "maximum_team_identity_mismatches": 0,
        "maximum_duplicate_quote_keys": 0,
        "maximum_public_raw_or_normalized_quote_rows": 0,
    }
    for key, value in expected_full.items():
        check(full.get(key) == value, f"full-backfill gate {key} changed")
    check("highest same-book" in str(full.get("primary_bookmaker_selection", "")), "coverage-only bookmaker rule missing")

    check(policy.get("decision_states") == EXPECTED_DECISIONS, "decision states changed")
    permissions = policy.get("post_decision_permissions", {})
    check(permissions.get("ready_for_point_in_time_odds_join_execution") is False, "odds join execution enabled")
    check(permissions.get("ready_for_market_backtest") is False, "market backtest enabled")
    check(permissions.get("ready_for_clv_ev_roi_drawdown") is False, "CLV/EV/ROI enabled")
    check(permissions.get("ready_for_betting_edge_claim") is False, "betting edge claim enabled")
    check(permissions.get("formal_stake") == 0, "formal stake changed")

    guards = policy.get("guardrails", {})
    check(guards.get("injury_candidate_used") is False, "rejected injury candidate used")
    check(guards.get("odds_used_for_model_training") is False, "odds used for model training")
    check(guards.get("closing_used_to_select_entry") is False, "closing used to select entry")
    check(guards.get("same_game_snapshots_count_as_independent_games") is False, "snapshots counted as independent games")
    check(guards.get("missing_quote_means_no_quote") is True, "missing quote semantics changed")
    check(guards.get("missing_quote_imputed_from_other_book_or_time") is False, "missing quote imputation enabled")
    check(guards.get("source_failures_replaced_with_handpicked_dates") is False, "source failures may be hand replaced")
    check(guards.get("raw_data_committed_to_public_repo") is False, "public raw commit enabled")
    check(guards.get("raw_data_distributed_as_standalone_product") is False, "standalone raw distribution enabled")
    check(guards.get("market_performance_metrics_calculated_in_acquisition_stage") is False, "market metrics enabled in acquisition")
    check(guards.get("stake_nonzero") is False, "nonzero stake enabled")

    return errors, checks


def build_report(policy: dict[str, Any], errors: list[str], checks: int) -> dict[str, Any]:
    return {
        "schema_version": "real-timestamped-odds-acquisition-policy-validation-v1",
        "generated_at": utc_now(),
        "policy_schema_version": policy.get("schema_version"),
        "checks_run": checks,
        "checks_passed": checks - len(errors),
        "errors": errors,
        "decision": "POLICY_VALID" if not errors else "POLICY_INVALID",
        "execution_boundary": {
            "network_requests_performed": False,
            "api_secret_read": False,
            "raw_odds_read": False,
            "coverage_measured": False,
            "market_performance_calculated": False,
            "full_backfill_authorized": False,
            "ready_for_betting_edge_claim": False,
            "formal_stake": 0,
        },
    }


def run_self_tests(policy: dict[str, Any]) -> None:
    errors, _ = validate_policy(policy)
    assert not errors, errors

    mutations: list[tuple[str, Any]] = []

    changed = copy.deepcopy(policy)
    changed["source_contract"]["primary_source_id"] = "other_source"
    mutations.append(("source mutation", changed))

    changed = copy.deepcopy(policy)
    changed["full_target_population"]["independent_games"] = 3687
    mutations.append(("population mutation", changed))

    changed = copy.deepcopy(policy)
    changed["api_query_contract"]["markets"] = ["h2h", "spreads"]
    mutations.append(("market mutation", changed))

    changed = copy.deepcopy(policy)
    changed["snapshot_contract"]["fixed_snapshots"][2]["seconds_before_anchor_commence"] = 1800
    mutations.append(("snapshot mutation", changed))

    changed = copy.deepcopy(policy)
    changed["source_contract"]["public_raw_or_normalized_odds_rows"] = True
    mutations.append(("privacy mutation", changed))

    changed = copy.deepcopy(policy)
    changed["request_and_cost_guardrails"]["pilot_credit_hard_cap"] = 50000
    mutations.append(("cost mutation", changed))

    changed = copy.deepcopy(policy)
    changed["full_target_population"]["injury_candidate_included"] = True
    mutations.append(("rejected candidate mutation", changed))

    changed = copy.deepcopy(policy)
    changed["post_decision_permissions"]["ready_for_market_backtest"] = True
    mutations.append(("activation mutation", changed))

    for name, mutation in mutations:
        mutation_errors, _ = validate_policy(mutation)
        assert mutation_errors, f"negative self-test failed: {name} was accepted"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    policy = json.loads(args.policy.read_text(encoding="utf-8"))
    if args.self_test:
        run_self_tests(policy)

    errors, checks = validate_policy(policy)
    report = build_report(policy, errors, checks)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "real-timestamped-odds-acquisition-policy-validation.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
