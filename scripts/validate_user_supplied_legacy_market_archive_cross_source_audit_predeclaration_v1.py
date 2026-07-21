#!/usr/bin/env python3
"""Validate the user-supplied legacy market archive cross-source audit policy.

The validator is policy-only. It must not read the real candidate CSV, read the
Historical Silver/Gold databases, make network calls, or emit row-level data.
"""
from __future__ import annotations

import argparse
import copy
import json
import tempfile
from pathlib import Path
from typing import Any

SCHEMA_VERSION = (
    "user-supplied-legacy-market-archive-cross-source-audit-predeclaration-v1"
)
READY_STATE = (
    "USER_SUPPLIED_LEGACY_MARKET_ARCHIVE_CROSS_SOURCE_AUDIT_"
    "PREDECLARATION_READY"
)
BLOCKED_STATE = (
    "USER_SUPPLIED_LEGACY_MARKET_ARCHIVE_CROSS_SOURCE_AUDIT_"
    "PREDECLARATION_BLOCKED"
)
CURRENT_ROLE = "ROLE_LIMITED_LEGACY_MARKET_ARCHIVE_ELIGIBLE"
MAXIMUM_ROLE = "ROLE_LIMITED_LEGACY_MARKET_ARCHIVE_CROSS_SOURCE_VALIDATED"
EXPECTED_FILE_SHA256 = (
    "729eb2ead85c14affbb81ae9a4c611fee9790b8dd3d1d7824e1ddba14410a8c4"
)
EXPECTED_TEAM_MAPPING = {
    "atl": "ATL", "bkn": "BKN", "bos": "BOS", "cha": "CHA",
    "chi": "CHI", "cle": "CLE", "dal": "DAL", "den": "DEN",
    "det": "DET", "gs": "GSW", "hou": "HOU", "ind": "IND",
    "lac": "LAC", "lal": "LAL", "mem": "MEM", "mia": "MIA",
    "mil": "MIL", "min": "MIN", "no": "NOP", "ny": "NYK",
    "okc": "OKC", "orl": "ORL", "phi": "PHI", "phx": "PHX",
    "por": "POR", "sa": "SAS", "sac": "SAC", "tor": "TOR",
    "utah": "UTA", "wsh": "WAS",
}
EXPECTED_SEASON_MAPPING = {
    "2020": "2019-20",
    "2021": "2020-21",
    "2022": "2021-22",
    "2023": "2022-23",
    "2024": "2023-24",
}
EXPECTED_OUTCOMES = [
    "ROLE_LIMITED_LEGACY_MARKET_ARCHIVE_CROSS_SOURCE_VALIDATED",
    "RETAIN_ROLE_LIMITED_LEGACY_MARKET_ARCHIVE_ELIGIBLE",
    "USER_SUPPLIED_LEGACY_MARKET_ARCHIVE_CROSS_SOURCE_AUDIT_RESEARCH_BLOCKED",
]


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("policy root must be a JSON object")
    return value


def get_path(value: dict[str, Any], dotted_path: str) -> Any:
    current: Any = value
    for component in dotted_path.split("."):
        if not isinstance(current, dict) or component not in current:
            return None
        current = current[component]
    return current


def validate_policy(policy: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool, observed: Any = None) -> None:
        checks.append({
            "name": name,
            "passed": bool(condition),
            "observed": observed,
        })

    check("schema_version", policy.get("schema_version") == SCHEMA_VERSION,
          policy.get("schema_version"))
    check("candidate_source_id",
          get_path(policy, "candidate_source.source_id") ==
          "kaggle_cviaxmiwnptr_nba_betting_data_user_supplied",
          get_path(policy, "candidate_source.source_id"))
    check("candidate_provenance_user_confirmed",
          get_path(policy, "candidate_source.provenance_status") == "user_confirmed",
          get_path(policy, "candidate_source.provenance_status"))
    check("candidate_current_role",
          get_path(policy, "candidate_source.current_formal_outcome") == CURRENT_ROLE,
          get_path(policy, "candidate_source.current_formal_outcome"))
    check("candidate_file_sha256",
          get_path(policy, "candidate_source.file_sha256") == EXPECTED_FILE_SHA256,
          get_path(policy, "candidate_source.file_sha256"))
    check("candidate_file_bytes",
          get_path(policy, "candidate_source.file_bytes") == 2493308,
          get_path(policy, "candidate_source.file_bytes"))
    check("candidate_row_count",
          get_path(policy, "candidate_source.row_count") == 24440,
          get_path(policy, "candidate_source.row_count"))
    check("candidate_column_count",
          get_path(policy, "candidate_source.column_count") == 27,
          get_path(policy, "candidate_source.column_count"))

    check("reference_source_path",
          get_path(policy, "reference_source.primary_source_path") ==
          "shufinskiy/nba_data",
          get_path(policy, "reference_source.primary_source_path"))
    check("reference_gold_rows",
          get_path(policy, "reference_source.historical_gold_matchup_rows") == 5824,
          get_path(policy, "reference_source.historical_gold_matchup_rows"))
    check("reference_pit_violations_zero",
          get_path(policy, "reference_source.strict_point_in_time_violations") == 0,
          get_path(policy, "reference_source.strict_point_in_time_violations"))
    check("reference_identity_table",
          get_path(policy, "reference_source.identity_table") ==
          "gold_matchup_features",
          get_path(policy, "reference_source.identity_table"))
    check("reference_score_table",
          get_path(policy, "reference_source.score_validation_table") == "games",
          get_path(policy, "reference_source.score_validation_table"))

    check("season_mapping_exact",
          get_path(policy, "overlap_scope.season_mapping") == EXPECTED_SEASON_MAPPING,
          get_path(policy, "overlap_scope.season_mapping"))
    check("regular_only_filter",
          get_path(policy, "overlap_scope.candidate_game_filter") ==
          "regular == true and playoffs == false",
          get_path(policy, "overlap_scope.candidate_game_filter"))
    check("playoffs_out_of_scope",
          get_path(policy, "overlap_scope.playoffs_in_scope") is False,
          get_path(policy, "overlap_scope.playoffs_in_scope"))
    check("moneyline_not_required",
          get_path(policy, "overlap_scope.moneyline_required_for_identity_audit") is False,
          get_path(policy, "overlap_scope.moneyline_required_for_identity_audit"))

    contract = policy.get("deterministic_join_contract", {})
    check("join_key_exact",
          contract.get("join_key") == [
              "game_date", "home_team_abbr", "away_team_abbr"
          ], contract.get("join_key"))
    check("team_mapping_exact",
          contract.get("team_mapping") == EXPECTED_TEAM_MAPPING,
          len(contract.get("team_mapping", {})))
    check("fuzzy_matching_disabled",
          contract.get("fuzzy_matching_allowed") is False,
          contract.get("fuzzy_matching_allowed"))
    check("score_is_validation_only",
          contract.get("score_validation_only") is True and
          contract.get("score_used_to_repair_identity") is False,
          {
              "validation_only": contract.get("score_validation_only"),
              "repair_identity": contract.get("score_used_to_repair_identity"),
          })
    check("many_to_many_disabled",
          contract.get("many_to_many_join_allowed") is False,
          contract.get("many_to_many_join_allowed"))
    check("manual_overrides_disabled",
          contract.get("manual_key_overrides_allowed") is False,
          contract.get("manual_key_overrides_allowed"))

    gates = policy.get("frozen_execution_gates", {})
    expected_gates = {
        "minimum_reference_games": 5700,
        "minimum_candidate_eligible_games": 5700,
        "minimum_reference_match_rate": 0.985,
        "minimum_candidate_match_rate": 0.985,
        "minimum_matched_score_pair_rate": 0.99,
        "minimum_each_season_reference_match_rate": 0.97,
        "maximum_candidate_duplicate_key_groups": 0,
        "maximum_reference_duplicate_key_groups": 0,
        "maximum_ambiguous_join_keys": 0,
        "maximum_unresolved_team_codes": 0,
        "maximum_invalid_candidate_dates": 0,
        "maximum_invalid_reference_dates": 0,
        "maximum_missing_candidate_scores_in_scope": 0,
        "maximum_missing_reference_scores_in_scope": 0,
        "maximum_raw_rows_emitted": 0,
        "raw_files_emitted_allowed": False,
    }
    check("frozen_gates_exact", gates == expected_gates, gates)

    check("candidate_outcomes_exact",
          policy.get("candidate_execution_outcomes") == EXPECTED_OUTCOMES,
          policy.get("candidate_execution_outcomes"))
    check("maximum_role_frozen",
          policy.get("maximum_role_if_later_audit_passes") == MAXIMUM_ROLE,
          policy.get("maximum_role_if_later_audit_passes"))

    forbidden = policy.get("forbidden_actions", {})
    forbidden_false_keys = [
        "network_calls_in_predeclaration_validation",
        "real_candidate_csv_read_in_predeclaration_validation",
        "real_reference_database_read_in_predeclaration_validation",
        "raw_candidate_csv_committed",
        "raw_reference_database_committed",
        "raw_rows_in_artifact",
        "fuzzy_matching",
        "opening_label_allowed",
        "closing_label_allowed",
        "point_in_time_join_allowed",
        "entry_price_roi_allowed",
        "clv_allowed",
        "drawdown_allowed",
        "betting_edge_claim_allowed",
        "historical_silver_replacement_allowed",
        "historical_gold_replacement_allowed",
        "model_retraining_allowed",
    ]
    check("all_forbidden_actions_disabled",
          all(forbidden.get(key) is False for key in forbidden_false_keys),
          {key: forbidden.get(key) for key in forbidden_false_keys})
    check("formal_stake_zero", forbidden.get("formal_stake") == 0,
          forbidden.get("formal_stake"))

    next_state = policy.get("next_state_if_validation_passes", {})
    check("next_state_ready",
          next_state.get("formal_state") == READY_STATE,
          next_state.get("formal_state"))
    check("implementation_only",
          next_state.get("ready_for_separate_audit_implementation") is True and
          next_state.get("real_file_audit_executed") is False and
          next_state.get("source_role_changed") is False,
          next_state)
    check("market_model_still_blocked",
          next_state.get("market_backtest_ready") is False and
          next_state.get("model_retraining_authorized") is False and
          next_state.get("formal_stake") == 0,
          next_state)

    failed = [item for item in checks if not item["passed"]]
    state = READY_STATE if not failed else BLOCKED_STATE
    return {
        "schema_version": SCHEMA_VERSION,
        "formal_state": state,
        "checks_total": len(checks),
        "checks_passed": len(checks) - len(failed),
        "checks_failed": len(failed),
        "checks": checks,
        "quality": {
            "network_calls_made": False,
            "real_candidate_csv_read": False,
            "real_reference_database_read": False,
            "raw_rows_emitted": 0,
            "raw_files_emitted": False,
        },
        "decision": {
            "ready_for_separate_audit_implementation": not failed,
            "real_file_audit_executed": False,
            "source_role_changed": False,
            "current_source_role": CURRENT_ROLE,
            "maximum_possible_later_role": MAXIMUM_ROLE,
            "ready_for_point_in_time_market_backtest": False,
            "ready_for_clv_analysis": False,
            "ready_for_entry_price_roi_backtest": False,
            "ready_for_model_retraining": False,
            "ready_for_betting_edge_claim": False,
            "formal_stake": 0,
        },
    }


def write_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def self_test(policy: dict[str, Any]) -> None:
    good = validate_policy(policy)
    assert good["formal_state"] == READY_STATE, good
    assert good["checks_failed"] == 0, good

    mutated = copy.deepcopy(policy)
    mutated["deterministic_join_contract"]["fuzzy_matching_allowed"] = True
    bad = validate_policy(mutated)
    assert bad["formal_state"] == BLOCKED_STATE, bad
    assert bad["checks_failed"] >= 1, bad

    mutated = copy.deepcopy(policy)
    mutated["frozen_execution_gates"]["minimum_reference_match_rate"] = 0.90
    bad = validate_policy(mutated)
    assert bad["formal_state"] == BLOCKED_STATE, bad

    mutated = copy.deepcopy(policy)
    mutated["forbidden_actions"]["model_retraining_allowed"] = True
    bad = validate_policy(mutated)
    assert bad["formal_state"] == BLOCKED_STATE, bad

    with tempfile.TemporaryDirectory(prefix="nbavl-legacy-cross-source-policy-") as name:
        path = Path(name) / "report.json"
        write_report(good, path)
        assert json.loads(path.read_text(encoding="utf-8"))["formal_state"] == READY_STATE


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    policy = read_json(args.policy)
    if args.self_test:
        self_test(policy)
    report = validate_policy(policy)
    write_report(report, args.output)
    print(json.dumps({
        "formal_state": report["formal_state"],
        "checks_failed": report["checks_failed"],
    }, indent=2))
    raise SystemExit(0 if report["formal_state"] == READY_STATE else 2)


if __name__ == "__main__":
    main()
