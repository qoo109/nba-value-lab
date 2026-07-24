# NBA Value Lab Handoff — Frozen Model Forward Score 2025-26

Updated: 2026-07-24  
Formal Stake: 0

## Repository state before milestone

```text
main: c6ac3ef8e5d6b87f8504ac393687dcc997d0d9cc
latest merged PR: 178
open PRs before branch creation: none
recording PR: 179
```

## User-approved task

Continue the 2024-25 → 2025-26 feature chain and use the frozen existing model to generate 2025-26 win probabilities, filling missing source data with free legal public sources where necessary.

## Formal result

```text
FROZEN_MODEL_FORWARD_SCORE_2025_26_PASS_RECORDED
```

## Final real execution evidence

```text
branch head:
daacc74f5500f73b6816933af7e4fa8f3c9616f9

workflow run: 30081647871
job: 89444366089
Artifact: 8592067225
Artifact digest:
sha256:b366f12085208182845e96eeb9e6782415dd499ba2010146373ae23eb2278a9f
Artifact inspected: yes
```

## Frozen model integrity

```text
model file SHA-256:
007ce32cc5a80df3b87554d13847d388e2ca6cbf6122f00df2d4e87d5b49a343

version: walk-forward-v2
training seasons: 2019-20 through 2023-24
probability method: raw_logistic_elo
fit/refit calls: 0
calibration: false
```

## Population and state

```text
original frozen Elo-history games: 5,824
frozen historical exclusions: 22301177, 22301195
2024-25 state-update games: 1,230
2025-26 forward-scored games: 1,230
first date: 2025-10-21
last date: 2026-04-12
```

## Forward Gold

```text
team rows: 2,460
matchup rows: 1,230
PIT violations: 0
same-day games excluded: true
season reset: true
mature matchups prior 20: 921
low-evidence matchups: 79
```

## Probability-quality result

```text
Frozen Logistic + Elo:
Log Loss: 0.600865
Brier: 0.206823
Accuracy: 68.374%
ROC-AUC: 0.732718
ECE: 0.029773

Elo benchmark:
Log Loss: 0.608236
Brier: 0.209715
Accuracy: 67.805%
ROC-AUC: 0.725451
```

Paired bootstrap versus Elo:

```text
Log Loss 95% model-minus-Elo interval:
[-0.013974, -0.000927]

Brier 95% model-minus-Elo interval:
[-0.005831, -0.000022]

Accuracy 95% model-minus-Elo interval:
[-0.010569, +0.022764]
```

Model probability quality improved over Elo in the forward season. Accuracy difference is not statistically decisive under this paired interval.

## Confidence-band history

```text
>= 60%: 795 games / 73.96% accuracy
>= 65%: 596 games / 76.68% accuracy
>= 70%: 424 games / 80.19% accuracy
>= 75%: 250 games / 83.60% accuracy
>= 80%: 140 games / 86.43% accuracy
```

These are model-only historical accuracy figures, not betting win rates or profitability claims.

## Validation incident

The first workflow run `30081450119` successfully built and scored all 1,230 games, but the final database test incorrectly expected 60 team rows with `prior_games=0`. There are 30 NBA teams and exactly one first game per team, so the correct governed count is 30. Only the test assertion changed; model code and produced probabilities did not change.

The corrected final-head run `30081647871` passed every build, scoring, database and boundary check.

## Private outputs

```text
frozen-model-forward-predictions-2025-26.csv
SHA-256:
c3764faf6eb3703374b12a5d8668c6ef889cd8f54070a2c6cf135b55559ca725

forward-gold-2025-26.sqlite.gz
SHA-256:
3a9bd07dac35ff2a6c9e880d3637d37ae5e18b5602e740dcfc7e3d3be413aead
```

Game-level prediction rows remain private and are not committed publicly.

## Resolved blockers

```text
2024-25 governed state: resolved
2025-26 governed Silver: resolved
2025-26 pre-game Gold: resolved
frozen-model 2025-26 scoring: resolved
same-game model/odds season overlap: now available privately
```

## Preserved boundaries

```text
model retraining: false
model refitting: false
market data used as model feature: false
odds join: false in this milestone
strict T-60 qualified: false
Market Backtest: locked
CLV / ROI / Drawdown: locked
betting-edge claim: locked
Formal Stake: 0
```

## Do not do

- Do not retrain, refit, or recalibrate the frozen model during the odds sensitivity join.
- Do not publish game-level prediction rows or private price rows to GitHub Pages.
- Do not label collector-batch odds as exact provider-origin T-60.
- Do not describe confidence-band accuracy as a betting win rate.
- Do not select a timing band or edge threshold based on profitability.
- Do not report formal ROI, CLV, Drawdown or betting edge from this archive.

## Next unique diagnostic sub-mainline

```text
JOIN_2025_26_FORWARD_PROBABILITIES_TO_PRIVATE_ALIGNED_ODDS_FOR_TIME_BANDED_SENSITIVITY_ONLY
```

The formal project mainline remains governed by `PROJECT_STATUS.md`; this research milestone does not unlock G1.2.0 or change Stake.
