# Forward Feature Source Probe — 2024-25 / 2025-26 v1

Updated: 2026-07-24  
Research position: Research Candidate / Pre-Market-Backtest  
Formal Stake: 0

## Purpose

This execution closes the first source-availability question for forward-scoring the frozen NBA Value Lab probability model on the 2025-26 season.

It does not retrain the model or join market odds. It establishes whether enough free, public, NBA-derived source data exists to build the missing 2024-25 state and a governed 2025-26 pre-game feature chain.

## Execution

```text
workflow run: 30077376058
job: 89431003556
Artifact: 8590420908
Artifact digest:
sha256:b27b18cb5585a446007605a94865afc95b1a0685b54a81722e2e8a3247771f75
Artifact inspected: yes
```

Formal result:

```text
FORWARD_FEATURE_SOURCES_FOUND_2024_25_SILVER_VALID_2025_26_ADAPTER_READY
```

## 2024-25 governed Silver result

The existing historical adapters successfully built the complete 2024-25 regular-season Silver layer from the public `pbpstats_2024` and `nbastats_2024` archives.

```text
games: 1,230
pbp_events: 574,358
player_aliases: 983
possessions: 243,782
team_game_features: 2,460
team inference failures: 0
official score coverage: 100%
incomplete team games: 0
```

Source bindings:

```text
pbpstats_2024:
sha256:3e124793cc7fbc279627926e207b634fd593e5b56a69b8d0324f21460913c5c6

nbastats_2024:
sha256:8f370da00ad0a6d4157921bd161d56ea32647a165d906516f2b36384a6a4989a
```

The possession-score reconstruction QA matched 1,029 games and mismatched 201 games, for a match rate of `0.836585`. This does not replace official final scores: the governed pipeline continues to use NBA Stats official final scores for ratings, while reconstructed possession points remain QA-only.

The derived database is retained only as an expiring private Artifact:

```text
silver-2024-25/historical-silver.sqlite.gz
```

It is not approved for public repository commit.

## 2025-26 source coverage

Three available public archives were inspected:

```text
cdnnba_2025
nbastatsv3_2025
matchups_2025
```

Every source contains exactly 1,230 game IDs, and the all-three intersection is also 1,230.

### Official CDN play-by-play

```text
rows: 708,268
columns: 57
games: 1,230
team tricodes: 30
terminal-score candidates: 1,230
```

Required adapter fields are present:

```text
gameId
period
actionType
scoreHome
scoreAway
teamId
teamTricode
possession
```

### NBA Stats PlayByPlayV3

```text
rows: 621,887
columns: 24
games: 1,230
team tricodes: 30
terminal-score candidates: 1,230
```

The V3 source supplies cross-source event, score, team and player identity evidence. It does not expose the CDN `possession` field, so it is not sufficient alone for the current possession feature contract.

### Matchup context

```text
rows: 240,839
columns: 48
games: 1,230
```

The matchup archive supplies stable game IDs and home/away team IDs, plus player-matchup context. It is not used as a substitute for event or final-score data.

## Approved source composition for implementation

```text
matchups_2025
    -> stable home/away identity candidate

cdnnba_2025
    -> official score progression
    -> possession identity
    -> shooting, turnover, rebound and free-throw reconstruction
    -> event actual timestamps

nbastatsv3_2025
    -> event and player identity
    -> cross-source team/score validation
```

The implementation must fail closed when the three sources disagree on game identity, team identity or terminal score.

## Game-date rule

The future Gold pipeline uses date-level exclusion. To avoid UTC-date splits for evening NBA games, the implementation must derive the governed game date from the earliest official CDN `timeActual` converted to `America/New_York`, then verify it against available official schedule metadata.

No same-day game may become historical input to another game when only date precision is governed.

## Execution boundaries

```text
provider API requests: 0
raw archives committed: false
raw rows emitted: 0
model retraining: false
model scoring: false
odds join: false
strict T-60 qualification: false
Market Backtest: locked
CLV / ROI / Drawdown: locked
betting-edge claim: locked
Formal Stake: 0
```

## Decision

```text
IMPLEMENT_OFFICIAL_CDN_V3_2025_26_SILVER_ADAPTER_AND_CONTINUOUS_GOLD_STATE
```

The next implementation must preserve the frozen model contract, carry Elo through 2024-25, build strictly pre-game 2025-26 Gold rows, and only then score 2025-26 without retraining.
