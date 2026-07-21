# Historical Gold / Silver Coverage Reconciliation Implementation v1

更新日期：2026-07-21（Asia/Taipei）

## Trigger

Legacy Market Archive real-file audit retry `002` completed successfully at the workflow level and passed every frozen scientific gate, but its formal outcome remained blocked because the rebuilt five-season reference contained:

```text
Historical Silver games: 5,826
Historical Gold matchups: 5,824
Missing Gold for Silver: 2
```

The user-supplied candidate remains unchanged and does not need modification.

## Purpose

This implementation classifies why a Silver game has no corresponding Gold matchup. It does not repair, insert, delete, or override any source row.

Analyzer:

```text
scripts/analyze_historical_gold_silver_coverage_v1.py
```

## Inputs

The analyzer accepts local SQLite or gzip-compressed SQLite inputs:

```text
--silver-db historical-silver-multiseason.sqlite[.gz]
--gold-db historical-gold-multiseason.sqlite[.gz]
```

Frozen reference scope:

```text
2019-20
2020-21
2021-22
2022-23
2023-24
```

## Classification logic

For every Silver `games.game_id` missing from Gold `gold_matchup_features`, the analyzer checks:

1. Whether Silver has an exact home `team_game_features` row.
2. Whether Silver has an exact away `team_game_features` row.
3. Whether the Silver feature pair is exactly two rows with consistent home/away identity.
4. Whether both rows transferred to `gold_team_game_features`.
5. Whether both Gold team rows exist but `build_matchups` omitted the matchup.

Aggregate categories:

```text
missing_home_team_feature
missing_away_team_feature
missing_both_team_features
silver_feature_pair_identity_mismatch
gold_team_feature_transfer_mismatch
gold_matchup_builder_omission
silver_game_outside_gold_identity_contract
unclassified
```

## Output boundary

The output is one aggregate JSON only. It may include counts by season and reason category, but it never emits:

- game IDs;
- dates;
- team codes;
- row-level examples;
- hashes of row keys;
- Silver or Gold database files;
- source archives.

No fuzzy matching, manual override, or score-assisted identity repair is used.

## Synthetic validation

Pull-request CI uses five fixture games covering:

- one correctly covered game;
- missing home feature;
- missing away feature;
- Gold team-feature transfer mismatch;
- Gold matchup-builder omission.

The expected fixture result is `MIXED_CAUSES`. CI performs no network calls and reads no real reference database.

## Current state

```text
HISTORICAL_GOLD_SILVER_COVERAGE_RECONCILIATION_IMPLEMENTATION_READY_REAL_EXECUTION_DISABLED
```

The implementation does not authorize a real reference rebuild or diagnostic run. A separate reviewed execution request is required.

## Still blocked

- changing the Gold builder;
- treating the two missing games as expected exclusions;
- rerunning the Legacy Market Archive cross-source audit;
- replacing Historical Silver or Gold;
- Opening or Closing semantics;
- point-in-time market backtest;
- CLV, EV, ROI, Drawdown;
- model retraining;
- betting-edge claims;
- non-zero Stake.

## Exact next step

```text
HISTORICAL_GOLD_SILVER_COVERAGE_RECONCILIATION_REAL_REFERENCE_EXECUTION_REQUEST
```
