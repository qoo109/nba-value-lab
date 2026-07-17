# Historical Gold Layer v1

## Purpose

Gold v1 converts the audited 2023–24 Silver team-game data into reproducible pregame features for baseline model research.

The output is research data. It is not a validated betting model and does not create website performance claims.

## Point-in-time rule

Every feature row follows:

```text
source_game_date < target_game_date
```

Games played on the same calendar date are excluded from one another. The current historical source has a game date but no reliable unified tip-off timestamp, so this conservative rule prevents accidental same-day ordering leakage.

The full workflow must pass an independent prior-game-count audit before the Gold artifact is accepted.

## Output tables

### `gold_team_game_features`

One row per team and target game.

Includes:

- rolling windows for the previous 5, 10 and 20 games
- Pace, OffRtg, DefRtg and NetRtg
- eFG%, estimated TOV%, estimated ORB% and FTr
- points, opponent points, margin and win rate
- NetRtg volatility
- prior home and away splits
- rest days and back-to-back flag
- games played in the prior 3 and 7 days
- opponent NetRtg strength over its prior 10 games
- simple opponent-adjusted NetRtg
- recent NetRtg trend
- source, schema and feature versions
- generation time and quality flags

### `gold_matchup_features`

One row per game, joining the home and away point-in-time team rows.

Includes:

- home minus away rolling NetRtg differences
- Pace and four-factor differences
- rest-day difference
- minimum prior-game sample
- evidence coverage
- quality flags and immutable feature IDs

## Early-season missing values

Gold v1 does not backfill early-season rows with future season averages.

Rows with fewer than 5, 10 or 20 prior games remain in the database and receive explicit quality flags. Rolling fields use the available prior sample and publish their exact sample size.

This allows later model stages to choose one of the following without changing the historical feature truth:

- exclude immature rows
- add missing-value indicators
- train a separate early-season model
- use prior-season features after cross-season support is added

## Opponent adjustment

The first version uses a deliberately simple and inspectable feature:

```text
opponent_adjusted_net_rtg_last_10
  = team_net_rtg_last_10 - opponent_net_rtg_last_10
```

This is a baseline feature, not the final strength-of-schedule algorithm. Iterative or ridge-based opponent adjustment should be added only after multiple seasons are available.

## Artifacts

Manual workflow runs produce:

- `historical-gold.sqlite.gz`
- `gold-build-report.json`
- `gold-sample.json`

Artifacts are retained for 14 days. The full database is not committed to the public repository.

## Workflow

`build-historical-gold.yml` has two stages:

1. Synthetic self-test on pull requests and manual runs.
2. Manual full build that recreates the audited Silver database in temporary storage and then creates Gold.

Rebuilding Silver in the same workflow guarantees that the Gold artifact records the exact Silver source hashes used for generation.

## Acceptance gates

A live build must satisfy:

- at least 2,400 team-game rows
- at least 1,200 matchup rows
- zero duplicate team-game keys
- zero duplicate game matchup keys
- zero point-in-time violations
- at least one matchup where both teams have 20 prior games
- valid compressed SQLite and JSON outputs

## Current limitations

Gold v1 is intentionally limited to the audited 2023–24 season.

It does not yet include:

- prior-season carryover
- multiple-season training data
- tip-off-time ordering within the same date
- travel distance or time-zone changes
- player injuries, starters or rotation load
- market odds or closing lines
- advanced iterative strength-of-schedule adjustment
- trained or calibrated probability models

The report therefore keeps `cross_season_training_ready` set to `false` even when the single-season build passes.

## Next phase after validation

1. Run the full Gold workflow and inspect coverage and null reports.
2. Add 2022–23 and 2021–22 Silver seasons.
3. define cross-season carryover and offseason reset rules.
4. Build interpretable baselines: Elo, logistic regression and simple Net Rating.
5. Use walk-forward validation only.
