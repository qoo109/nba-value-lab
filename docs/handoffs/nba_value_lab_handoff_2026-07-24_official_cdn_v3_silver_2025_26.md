# NBA Value Lab Handoff — Official CDN + V3 Silver 2025-26

Updated: 2026-07-24  
Formal Stake: 0

## Repository state before milestone

```text
main: cde34f4620814aadf5a417f8986cafb2ff0b1097
latest merged PR: 177
open PRs before branch creation: none
recording PR: 178
```

## User-approved task

Use free public web sources to fill the missing 2025-26 feature data and continue toward frozen-model win-probability scoring without retraining.

## Formal result

```text
OFFICIAL_CDN_V3_SILVER_2025_26_BUILD_PASS_RECORDED
```

## Final execution evidence

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
SQLite integrity: ok
```

## Output

```text
games: 1,230
PBP events: 621,887
player aliases: 1,006
possessions: 249,957
team-game features: 2,460
exactly two team rows per game: 1,230 / 1,230
core feature null/non-finite rows: 0
```

Game-date range and rule:

```text
2025-10-21 through 2026-04-12
earliest CDN timeActual -> America/New_York date
```

## Source exception governance

Two immutable V3 terminal-score defects were diagnosed and recorded:

```text
0022500029 — CLE 148 at WAS 114
V3 terminal home score drifted to 115

0022500232 — DEN 123 at MIN 112
V3 period-end record reverted to halftime 60-55 after a documented courtside stats-system glitch
```

Exception diagnostic:

```text
run: 30079791244
job: 89438517519
Artifact: 8591318366
digest:
sha256:588faf8cec24bcceac2e3d5584b237b5e61a5303a4f37bab415f93fc18b0ad5c
```

Exception manifest:

```text
data/research/official-cdn-v3-terminal-score-exceptions-2025-26-v1.json
```

```text
documented exceptions: 2
unexplained mismatches: 0
wildcard exceptions: prohibited
V3 raw event rows modified: false
official final scores modified: false
```

## Resolved blockers

```text
2024-25 governed Silver: resolved by PR 177
2025-26 source availability: resolved by PR 177
2025-26 governed Silver: resolved by PR 178
```

## Remaining work

```text
continuous 2024-25 -> 2025-26 Gold state: pending
Elo carry through 2024-25 offseason: pending
frozen-model 2025-26 scoring: pending
same-game private odds sensitivity comparison: pending after scoring
```

## Preserved boundaries

```text
raw source archives committed: false
raw source rows committed: false
provider API requests: 0
model retraining: false
model scoring: false in this milestone
odds join: false
strict T-60 qualified: false
Market Backtest: locked
CLV / ROI / Drawdown: locked
betting-edge claim: locked
Formal Stake: 0
```

## Do not do

- Do not retrain or refit the frozen probability model.
- Do not use 2025-26 outcomes as input to the same game’s pre-game features.
- Do not let same-day games enter one another’s history.
- Do not remove or broaden the two-game exception manifest without a new version and fresh evidence.
- Do not commit the Silver SQLite or raw public archives to the Repository.
- Do not join private odds until same-game model prediction rows exist.
- Do not claim exact T-60, EV, ROI, CLV or betting edge.

## Next unique diagnostic sub-mainline

```text
BUILD_CONTINUOUS_2024_25_TO_2025_26_GOLD_AND_SCORE_FROZEN_MODEL
```

The formal project mainline remains governed by `PROJECT_STATUS.md`; this diagnostic milestone does not unlock G1.2.0 or change Stake.
