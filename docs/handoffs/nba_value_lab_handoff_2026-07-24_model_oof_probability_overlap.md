# NBA Value Lab Handoff — Model OOF Probability / Odds Overlap

Updated: 2026-07-24  
Formal Stake: 0

## Repository state before milestone

```text
main: 9e5aa099f9def4f9af92c68e2540d00feea9a11c
latest merged PR: 175
open PRs before branch creation: none
recording PR: 176
```

## User-approved task

Continue from the public/private odds split and begin the model probability analysis without silently treating 2025-26 odds as model probabilities.

## Real execution input

```text
workflow run: 29551715399
Artifact: model-walk-forward-v2
Artifact ID: 8396002523
Artifact digest:
sha256:6063adac9851b47d339a93e35935115008b736a16925548d36a8c54a0353b41b
OOF prediction rows: 3,688
OOF seasons: 2021-22, 2022-23, 2023-24
selected probability method: raw_logistic_elo
```

Private odds input:

```text
season: 2025-26
main-line rows: 8,153
regular-season events: 1,112
raw prices committed: false
```

## Formal result

```text
MODEL_OOF_PROBABILITY_DIAGNOSTIC_VALID_MARKET_JOIN_BLOCKED_NO_SEASON_OVERLAP
```

## Model-only findings

```text
Log Loss: 0.631306
Brier Score: 0.220567
Accuracy: 63.856%
ROC-AUC: 0.687099
ECE: 0.014239
```

Compared with Elo:

```text
Log Loss improvement: 0.002996
Brier improvement: 0.001383
Accuracy difference: -0.217 percentage points
AUC improvement: 0.002645
```

Confidence-band history:

```text
>= 60% selected-side probability: 2,260 games / 70.00% accuracy
>= 65% selected-side probability: 1,643 games / 73.04% accuracy
>= 70% selected-side probability: 1,091 games / 77.27% accuracy
>= 75% selected-side probability: 640 games / 79.53% accuracy
>= 80% selected-side probability: 281 games / 82.56% accuracy
```

These are OOF probability-quality diagnostics. They are not betting win rates and do not prove positive EV.

## Bootstrap interpretation

Five thousand paired game resamples show directionally better Log Loss and Brier than Elo, but both 95% intervals cross zero. The result is a small research improvement, not decisive superiority.

## Market overlap gate

```text
prediction seasons: 2021-22 through 2023-24
odds season: 2025-26
overlap seasons: none
market sensitivity executed: false
```

The historical OOF predictions cannot be joined directly to the 2025-26 prices because they describe different games.

## 2025-26 forward scoring blockers

```text
MISSING_GOVERNED_2024_25_SEASON_STATE
MISSING_GOVERNED_2025_26_PRE_GAME_GOLD_FEATURES
MISSING_2025_26_MODEL_PREDICTION_ROWS
```

The 2024-25 state is necessary because Elo carries across seasons. The 2025-26 feature rows must be built using only information available before each game.

## Final branch-head validation

Latest validated branch head before binding this immutable handoff evidence:

```text
head: 03a3941ac8d1aacb176ed7875e3e01e21123e622
workflow run: 30076240742
job: 89427480538
Artifact: 8589957641
Artifact digest:
sha256:afa4396f29850e98b58a1455e2279b5c3bbf56c6c7168a6e7bca7a4d79a4d08f
formal state: MODEL_OOF_PROBABILITY_MARKET_OVERLAP_DIAGNOSTIC_VALID
contract tests: 58 / 58 PASS
Artifact inspected: yes
```

## Preserved boundaries

```text
model retraining executed: false
raw prediction rows committed: false
raw odds committed: false
same-game model-versus-market comparison: false
strict T-60 qualified: false
Market Backtest: locked
CLV / ROI / Drawdown: locked
betting-edge claim: locked
Formal Stake: 0
```

## Do not do

- Do not join 2021-24 prediction rows to 2025-26 odds by team name alone.
- Do not call confidence-band accuracy a betting win rate.
- Do not select or promote a threshold based on profitability.
- Do not retrain the model during the forward feature-chain step.
- Do not skip the 2024-25 Elo state.

## Next unique diagnostic sub-mainline

```text
BUILD_GOVERNED_2024_25_AND_2025_26_PRE_GAME_FEATURE_CHAIN_WITHOUT_RETRAINING_THEN_SCORE_2025_26_FORWARD
```

The formal project mainline remains governed by `PROJECT_STATUS.md`; this diagnostic does not unlock G1.2.0, Market Backtest or Stake.
