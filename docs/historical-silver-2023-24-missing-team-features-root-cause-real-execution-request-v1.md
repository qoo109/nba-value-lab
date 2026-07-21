# Historical Silver 2023-24 missing team features real-execution request v1

Request ID:

```text
HISTORICAL-SILVER-2023-24-MISSING-BOTH-TEAM-FEATURES-ROOT-CAUSE-2026-07-21-001
```

Current state:

```text
AWAITING_EXPLICIT_USER_APPROVAL
```

## Purpose

The completed Gold/Silver reconciliation confirmed that exactly two `2023-24` Silver games have no `team_game_features` rows. This request asks for one temporary rebuild of the 2023-24 Silver reference and one aggregate-only root-cause report.

## Frozen scope

```text
season: 2023-24
source path: shufinskiy/nba_data
expected Silver games: 1,230
expected zero-feature games: 2
candidate CSV: forbidden
Gold database/build: not required and forbidden
```

## Approved operations after explicit approval

A later approved workflow may run exactly once and may only:

1. download the 2023-24 pbpstats and NBA Stats source archives to temporary workflow storage;
2. rebuild the existing 2023-24 Historical Silver pipeline without code changes;
3. inspect temporary `games`, `possessions`, and `team_game_features` rows;
4. classify the two zero-feature games using the frozen categories;
5. delete archives and the Silver database;
6. upload one aggregate JSON report not larger than 1 MiB.

## Classification categories

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

## Forbidden output and actions

The workflow must not emit or upload:

- game IDs;
- dates;
- team codes;
- raw rows;
- row-key hashes;
- the Silver database;
- source archives;
- candidate CSV data.

The execution also must not:

- modify the Silver builder;
- run or modify the Gold builder;
- insert or override rows manually;
- use fuzzy matching;
- repair identity using scores;
- replace Historical Silver or Gold;
- rerun the cross-source audit automatically;
- unlock market evaluation or model retraining;
- change formal Stake from `0`.

## Approval boundary

Request validation does not enable execution. After CI passes, the repository owner must explicitly approve the exact request ID and the full aggregate-only boundary before an execution workflow may be added or dispatched.
