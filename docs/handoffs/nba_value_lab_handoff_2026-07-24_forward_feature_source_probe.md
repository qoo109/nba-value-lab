# NBA Value Lab Handoff — Forward Feature Source Probe

Updated: 2026-07-24  
Formal Stake: 0

## Repository state before milestone

```text
main: d4221bdd34020594d72ba761f5a41501a8310509
latest merged PR: 176
open PRs before branch creation: none
recording PR: 177
```

## User-approved task

Begin the 2024-25 and 2025-26 feature-chain work, using free public web sources to fill missing data where necessary.

## Formal result

```text
FORWARD_FEATURE_SOURCES_FOUND_2024_25_SILVER_VALID_2025_26_ADAPTER_READY
```

## Real execution evidence

```text
branch head at real execution:
bfd26126112d1a7036782db1dc0f1d608f07f02a

workflow run: 30077376058
job: 89431003556
Artifact: 8590420908
Artifact digest:
sha256:b27b18cb5585a446007605a94865afc95b1a0685b54a81722e2e8a3247771f75
Artifact inspected: yes
```

## 2024-25 result

```text
games: 1,230
pbp events: 574,358
player aliases: 983
possessions: 243,782
team-game features: 2,460
team inference pass: true
official score coverage: 100%
incomplete team games: 0
```

The 2024-25 Silver database was created successfully and is retained only in the expiring private Artifact.

Possession score reconstruction:

```text
matched games: 1,029
mismatched games: 201
match rate: 0.836585
```

This is QA-only. Official NBA Stats final scores remain the rating-points source.

## 2025-26 result

Public source archives found:

```text
cdnnba_2025
nbastatsv3_2025
matchups_2025
```

Coverage:

```text
cdnnba game IDs: 1,230
nbastatsv3 game IDs: 1,230
matchups game IDs: 1,230
all-three intersection: 1,230
union: 1,230
```

The CDN source exposes all fields needed for a fail-closed possession reconstruction adapter. NBA Stats V3 supplies independent event/team/player identity validation, and the matchup source supplies stable home/away team identity context.

## Important implementation decision

Use:

```text
matchups -> home/away identity
cdnnba -> possessions, score progression, event timestamp and action statistics
nbastatsv3 -> event/player identity and cross-source QA
```

Derive the governed game date by converting the earliest official CDN `timeActual` to `America/New_York`. Verify against official schedule metadata. Do not use raw UTC calendar date as the Gold season date.

## Blockers

```text
source availability blocker: resolved
2024-25 Silver blocker: resolved
2025-26 adapter implementation: pending
continuous 2024-25 -> 2025-26 Gold state: pending
frozen-model 2025-26 scoring: pending
same-game private odds comparison: pending after scoring
```

## Preserved boundaries

```text
raw source archives committed: false
raw rows committed: false
provider API requests: 0
model retraining: false
model scoring: false
odds join: false
strict T-60 qualified: false
Market Backtest: locked
CLV / ROI / Drawdown: locked
betting-edge claim: locked
Formal Stake: 0
```

## Do not do

- Do not retrain or refit the frozen model during the forward-scoring chain.
- Do not use 2025-26 game outcomes to create pre-game features for the same game.
- Do not allow a same-day game to become historical input when only date precision is governed.
- Do not use market prices as independent-model training features.
- Do not commit the 2024-25 Silver database or raw source archives to the public repository.
- Do not label batch odds as exact T-60.
- Do not claim EV, ROI, CLV or betting edge.

## Next unique diagnostic sub-mainline

```text
IMPLEMENT_OFFICIAL_CDN_V3_2025_26_SILVER_ADAPTER_AND_CONTINUOUS_GOLD_STATE
```

The formal project mainline remains governed by `PROJECT_STATUS.md`; this sub-mainline does not unlock G1.2.0 or change Stake.
