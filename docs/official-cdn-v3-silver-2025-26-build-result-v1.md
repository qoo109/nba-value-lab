# Official CDN + Stats V3 Silver 2025-26 Build Result v1

Updated: 2026-07-24  
Research position: Research Candidate / Pre-Market-Backtest  
Formal Stake: 0

## Result

```text
OFFICIAL_CDN_V3_SILVER_2025_26_BUILD_PASS_RECORDED
```

The missing 2025-26 governed Silver layer is now built from free public NBA-derived archives without retraining the model or joining market prices.

## Final real execution

```text
branch head:
85477bb0f39188f48360fbc51d52ac58b423d190

workflow run: 30080247460
job: 89439929496
Artifact: 8591518327
Artifact digest:
sha256:880a3e9688a0035a7c6c8a5e934f32f6011ba44417ae5659c21b9d65fe00db6a
Artifact inspected: yes

build report SHA-256:
sha256:9de72ae0ffc4056b405a9c8caf569cfb2eed2596390055c8542d6fc92ad52911

Silver SQLite gzip SHA-256:
sha256:f0027956f6d0a1061955f2b00572d3295a8cfc4ef00de431290c38c80847a59a
Silver SQLite gzip bytes: 84,333,787
SQLite integrity check: ok
```

## Source composition

```text
matchups_2025
    -> stable home / away team identity

cdnnba_2025
    -> official event timestamps
    -> score progression and final score
    -> possession identity
    -> shooting, turnover, rebound and free-throw features

nbastatsv3_2025
    -> normalized PBP events
    -> player identity
    -> independent team and score QA
```

No source archive or extracted raw CSV is committed to the public Repository.

## Output tables

```text
games: 1,230
pbp_events: 621,887
player_aliases: 1,006
possessions: 249,957
team_game_features: 2,460
```

Coverage:

```text
games with exactly two team-feature rows: 1,230 / 1,230
games with official terminal score: 1,230 / 1,230
team-identity mismatches: 0
duplicate team-feature keys: 0
core null/non-finite feature rows: 0
minimum possession segments per game: 167
maximum possession segments per game: 259
```

## Governed date rule

The Gold pipeline is date-ordered. The builder therefore derives each game date from the earliest official CDN `timeActual`, converts it to `America/New_York`, and uses the resulting Eastern calendar date.

```text
minimum game date: 2025-10-21
maximum game date: 2026-04-12
```

This prevents an evening NBA game from being assigned to the following day simply because its UTC timestamp crosses midnight.

## Two documented V3 score exceptions

The first strict execution found two PlayByPlayV3 terminal-score defects. They were not silently suppressed. A focused real-source diagnostic was executed:

```text
workflow run: 30079791244
job: 89438517519
Artifact: 8591318366
Artifact digest:
sha256:588faf8cec24bcceac2e3d5584b237b5e61a5303a4f37bab415f93fc18b0ad5c
```

The immutable exception manifest is:

```text
data/research/official-cdn-v3-terminal-score-exceptions-2025-26-v1.json
```

### `0022500029` — Cleveland at Washington

Official NBA LiveData and the NBA Cup live-updates page give the final score as:

```text
Cleveland 148
Washington 114
```

The V3 archive reports Washington as 115 at period end. Official NBA/CDN score remains authoritative; raw V3 events remain unchanged.

### `0022500232` — Denver at Minnesota

Official NBA records give the final score as:

```text
Denver 123
Minnesota 112
```

The V3 final scoring action reaches the correct `112–123`, but its later period-end record falls back to the halftime score `60–55`. The NBA game recap reports that the courtside statistics system froze late in the third quarter and that final statistics became available several hours later.

This is therefore a documented source defect, not a game result ambiguity.

Final exception state:

```text
documented V3 terminal-score exceptions: 2
unexplained terminal-score mismatches: 0
wildcard exceptions: prohibited
V3 event rows modified: false
official game scores modified: false
```

## What this unlocks

The project now has:

```text
2019-20 through 2023-24 frozen historical corpus
2024-25 governed Silver state
2025-26 governed Silver state
frozen existing win-probability model Artifact
```

The next research step can build continuous 2024-25 → 2025-26 Gold state, carry Elo through the offseason, and score 2025-26 using the frozen model without retraining.

## What remains locked

```text
model retraining: not executed
2025-26 model scoring: not executed in this milestone
private odds join: not executed
strict T-60: not qualified
Market Backtest: locked
CLV / ROI / Drawdown: locked
betting-edge claim: locked
Formal Stake: 0
```

## Next unique sub-mainline

```text
BUILD_CONTINUOUS_2024_25_TO_2025_26_GOLD_AND_SCORE_FROZEN_MODEL
```
