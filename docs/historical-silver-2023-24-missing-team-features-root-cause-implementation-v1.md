# Historical Silver 2023-24 missing team features root-cause implementation v1

更新日期：2026-07-21（Asia/Taipei）

## Trigger

The completed aggregate-only Gold/Silver reconciliation produced:

```text
HISTORICAL_GOLD_SILVER_COVERAGE_RECONCILIATION_SOURCE_DATA_GAP_CONFIRMED
```

The five-season reference contained 5,826 Silver games and 5,824 Gold matchups. Both missing games were in `2023-24`, and both had zero Silver `team_game_features` rows. Gold transfer and matchup construction were not responsible.

## Purpose

This stage implements a narrower aggregate-only root-cause analyzer for the two 2023-24 Silver games with no team features. It does not modify the Silver or Gold builders and does not execute against real source data in pull-request CI.

## Analyzer

```text
scripts/analyze_historical_silver_missing_team_features_root_cause_v1.py
```

The analyzer inspects only these temporary Silver tables:

```text
games
possessions
team_game_features
```

It classifies zero-feature games into:

```text
nbastats_game_present_pbpstats_game_absent
no_event_or_possession_source_rows
pbpstats_possessions_all_offense_unresolved
pbpstats_single_expected_offense_team_coverage
pbpstats_offense_team_identity_mismatch
possession_metadata_count_mismatch
feature_aggregation_omission_after_valid_possessions
silver_game_identity_unresolved
unclassified
```

## Interpretation

- `nbastats_game_present_pbpstats_game_absent`: NBA Stats events exist but no pbpstats possession rows exist for the game.
- `no_event_or_possession_source_rows`: neither NBA Stats events nor pbpstats possession rows are represented.
- `pbpstats_possessions_all_offense_unresolved`: possession rows exist but every offensive team is unresolved.
- `pbpstats_single_expected_offense_team_coverage`: only one of the expected home/away teams appears as an offensive team.
- `pbpstats_offense_team_identity_mismatch`: resolved offensive teams do not equal the exact home/away pair.
- `possession_metadata_count_mismatch`: stored game possession count differs from the actual possession-row count.
- `feature_aggregation_omission_after_valid_possessions`: both expected offense teams exist, but no team features were produced.
- `silver_game_identity_unresolved`: the game does not have a valid home/away identity.

## Aggregate-only output

Allowed output:

- total games;
- games without team features;
- count by root-cause category;
- feature-count histogram;
- possession-row-count histogram;
- resolved-offense-team-count histogram;
- PBP-event presence counts;
- aggregate quality-flag counts;
- downstream readiness flags.

Forbidden output:

- game IDs;
- dates;
- team codes;
- raw possession rows;
- row hashes;
- source archives;
- SQLite databases;
- candidate CSV data.

## PR validation boundary

Pull-request CI uses synthetic SQLite fixtures only:

```text
network calls: false
real 2023-24 Silver rows read: false
real root-cause audit executed: false
raw rows emitted: 0
raw files emitted: false
formal Stake: 0
```

## Current permissions

Implementation validation does not authorize:

- real source download;
- Silver builder modification;
- Gold rebuild;
- cross-source audit rerun;
- Historical Silver or Gold replacement;
- Opening/Closing semantics;
- point-in-time market backtest;
- CLV, EV, ROI, or Drawdown;
- model retraining;
- betting-edge claims;
- non-zero Stake.

## Next step

After implementation CI passes, create a separate one-time real-execution request limited to rebuilding only the 2023-24 Silver reference in temporary storage and emitting one aggregate root-cause JSON report.
