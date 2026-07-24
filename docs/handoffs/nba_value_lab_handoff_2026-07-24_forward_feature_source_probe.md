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

## Final branch-head real execution evidence

```text
branch head:
849cd83d83d3e955414e806e4771ab2c2019bf59

workflow run: 30078039872
job: 89433051409
Artifact: 8590667307
Artifact digest:
sha256:1d3a271b148e2abd5f2d5ed0ef75ed2a6107363a3985cd05ad2d475e61eaa4ed
Artifact inspected: yes
```

Record validator at the same branch head:

```text
workflow run: 30078039896
job: 89433051513
Artifact: 8590635291
Artifact digest:
sha256:565ab5d4753b0b9b12670c1b51bd04e61a5df5f7d2e6613d53400b2d18b72b1b
result: PASS
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
