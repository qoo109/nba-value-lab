# NBA Value Lab Handoff — Prior-Only Player Rotation Source 2025-26 v1

Date: 2026-07-24  
Repository: `qoo109/nba-value-lab`  
Research state: **Official Source Qualified / Feature Build Not Yet Executed**  
Formal Stake: **0**

## Source of Truth before milestone

```text
base main: 254e59a2fd8d15b3a226cc8d34ee9eddb45fe006
latest merged milestone: PR #183
binding design: PRIOR_ONLY_PLAYER_ROTATION_STATE_FEATURE_LAYER_V1_DESIGN_VALID
binding next mainline: QUALIFY_AND_BUILD_PRIOR_ONLY_PLAYER_ROTATION_STATE_SOURCE_V1_WITHOUT_MODEL_RETRAINING
open PRs before PR #185: none
recording PR: #185
```

A duplicate stale model-gap PR #184 was closed without merge after the newer PR #181 and PR #183 Source of Truth was identified. No PR #184 result is authoritative.

## Purpose

Build and qualify the official deidentified player minutes and starter source required for the already predeclared prior-only rotation-state feature design.

This milestone does not build the feature table, run a residual audit, retrain the model or execute a market backtest.

## Governed source chain

```text
governed 2025-26 Silver
  -> 1,230 game IDs / dates / teams / game duration
NBA Official LiveData final boxscore
  -> deterministic person ID / minutes / played / official starter
strict private source QA
  -> deidentified player-game source Artifact
```

The exact governed Silver Artifact is `8591673536`.

## Live source result

```text
requested games: 1,230
successful official games: 1,230
failed games: 0
team-game rows: 2,460
private deidentified player-game rows: 43,265
unique player IDs: 603
teams: 30
months: 7
```

Quality:

```text
duplicate game/player rows: 0
missing or unexpected team rows: 0
team mismatches: 0
invalid minutes: 0
starter without played state: 0
team-games without exactly five starters: 0
minute reconciliation errors: 0
maximum absolute team-minute error: 0.003333 minutes
```

## Official-to-official source reconciliation

The first live build was blocked by one team-minute discrepancy. It was not resolved by lowering tolerance.

Diagnosis:

```text
official game: 0022500093
team: HOU
LiveData deidentified subject minutes: 28:08.2
NBA.com official game box score: 36:48
missing amount: 8:39.8
team total before: 231:20
team total after: 240:00
```

A single bounded exception was predeclared in:

```text
data/research/prior-only-player-rotation-source-exceptions-2025-26-v1.json
```

The public manifest contains a SHA-256 deidentified subject key, not the raw player ID or name. It permits an exact minutes-only change when the game, team, subject hash and original LiveData value all match. Identity, played and starter changes remain prohibited.

```text
exceptions declared: 1
exceptions applied: 1
unmatched exceptions: 0
value mismatches: 0
```

## Point-in-time boundary

The source contract has no governed source-game end timestamp. The later feature builder must therefore apply the conservative approved fallback:

```text
source_game_date_et < target_game_date_et
```

Same-day, target-game and future rows remain prohibited. Missing early-season state remains null and flagged.

## Private / public boundary

Private Artifact:

```text
prior-only-player-rotation-source-2025-26-v1.csv
prior-only-player-rotation-source-index-2025-26-v1.csv
prior-only-player-rotation-source-2025-26-report-v1.json
```

Public repository:

```text
player rows: 0
game-level feature rows: 0
raw official JSON: 0
player names: 0
free-text not-playing descriptions: 0
```

## Live execution evidence

```text
source build head: 1cc53c6b898cf7c80fdf28649366f04ca9f636c3
workflow run: 30099845472
job: 89502852068
conclusion: success
Artifact: 8599159260
Artifact digest: sha256:5f83f1c21e4a73696fd4d5dca8faa7f98908373f0795c45c6637a149bd345ee9
Artifact inspected: true
```

## Qualification

```text
official source qualified for prior-only rotation v1: true
ready for rotation feature build: true
real feature build executed: false
residual audit executed: false
model training authorized: false
strict T-60 qualified: false
formal Point-in-Time Market Backtest allowed: false
EV / ROI / CLV / Drawdown: false
betting-edge claim: false
Formal Stake: 0
```

## Do Not Do

- Do not use target-game minutes, starters, participation or outcomes as features.
- Do not use same-day source rows under the date-only fallback.
- Do not infer missing players as inactive, traded or zero minutes.
- Do not add wildcard or fuzzy source corrections.
- Do not publish the private player-game source or source URL index.
- Do not retrain or refit the frozen model during source qualification or feature construction.
- Do not use market prices as rotation features.
- Do not calculate EV, ROI, CLV, Drawdown or betting selections.
- Do not increase Formal Stake.

## Next unique mainline

```text
BUILD_PRIOR_ONLY_PLAYER_ROTATION_STATE_FEATURES_2025_26_V1
WITHOUT_MODEL_RETRAINING
```

The next milestone must implement only the features already frozen by PR #183, enforce strict earlier-date source selection, produce team and matchup rows, and run coverage, missingness and source-time QA. Passing source coverage does not authorize model training.

## Aggregate result validation

To be bound after the final PR-head validation succeeds:

```text
final PR head: pending
validation run: pending
validation job: pending
validation Artifact: pending
validation Artifact digest: pending
contract tests: pending
formal validation state: PRIOR_ONLY_PLAYER_ROTATION_SOURCE_2025_26_RESULT_VALID
```
