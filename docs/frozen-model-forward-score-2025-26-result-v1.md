# Frozen Model Forward Score 2025-26 Result v1

Updated: 2026-07-24  
Research position: Research Candidate / Pre-Market-Backtest  
Formal Stake: 0

## Result

```text
FROZEN_MODEL_FORWARD_SCORE_2025_26_PASS_RECORDED
```

The existing frozen `walk-forward-v2` classifier has now scored all 1,230 governed 2025-26 regular-season games without model retraining, refitting, calibration, or market-price features.

## Real execution

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

Private Artifact outputs:

```text
frozen-model-forward-score-2025-26-report-v1.json
frozen-model-forward-predictions-2025-26.csv
forward-gold-2025-26.sqlite.gz
```

Game-level predictions remain in the expiring private Artifact and are not committed to the public Repository.

## Frozen model contract

```text
model SHA-256:
007ce32cc5a80df3b87554d13847d388e2ca6cbf6122f00df2d4e87d5b49a343

version: walk-forward-v2
training seasons: 2019-20 through 2023-24
selected probability method: raw_logistic_elo
fit or refit calls: 0
calibration applied: false
```

The two late 2023-24 recovery games not present in the original frozen training population remained excluded from Elo-state reconstruction:

```text
22301177
22301195
```

## State construction

```text
original frozen-training Elo games: 5,824
2024-25 state-update games: 1,230
2025-26 forward-scored games: 1,230
```

Elo was reconstructed chronologically using the frozen settings:

```text
home-court advantage: 65
K factor: 20
offseason retention: 0.75
```

Every 2025-26 probability was generated before that game's result updated Elo.

## Forward Gold

```text
Gold team-game rows: 2,460
Gold matchup rows: 1,230
point-in-time violations: 0
same-day games excluded: true
season history reset: true
mature matchups with 20 prior games on both sides: 921
low-evidence matchups: 79
```

Gold database SHA-256:

```text
3a9bd07dac35ff2a6c9e880d3637d37ae5e18b5602e740dcfc7e3d3be413aead
```

## 2025-26 probability quality

| Metric | Frozen Logistic + Elo | Elo benchmark | Model minus Elo |
|---|---:|---:|---:|
| Log Loss | **0.600865** | 0.608236 | **-0.007371** |
| Brier Score | **0.206823** | 0.209715 | **-0.002892** |
| Accuracy | **68.374%** | 67.805% | **+0.569 pp** |
| ROC-AUC | **0.732718** | 0.725451 | **+0.007267** |

Calibration:

```text
ECE: 0.029773
MCE: 0.131528
```

The model improved all four aggregate metrics over Elo in this forward season.

## Paired bootstrap versus Elo

Five thousand paired game resamples were run with seed `20260724`.

```text
Log Loss difference, model minus Elo:
mean: -0.007388
95% interval: [-0.013974, -0.000927]
P(model better): 0.9884

Brier difference, model minus Elo:
mean: -0.002895
95% interval: [-0.005831, -0.000022]
P(model better): 0.9764

Accuracy difference, model minus Elo:
mean: +0.005737
95% interval: [-0.010569, +0.022764]
P(model better): 0.7362
```

The probability-quality improvements in Log Loss and Brier remain below zero across the paired 95% intervals. Accuracy improvement is directionally positive but its interval crosses zero.

## Confidence bands

| Minimum selected-side model probability | Games | Coverage | Historical accuracy |
|---:|---:|---:|---:|
| 50% | 1,230 | 100.00% | 68.37% |
| 55% | 1,016 | 82.60% | 71.56% |
| 60% | 795 | 64.63% | 73.96% |
| 65% | 596 | 48.46% | 76.68% |
| 70% | 424 | 34.47% | 80.19% |
| 75% | 250 | 20.33% | 83.60% |
| 80% | 140 | 11.38% | 86.43% |

These figures are model-only historical accuracy on completed games. They are not betting win rates, do not account for price, and do not prove positive expected value.

## What this unlocks

The private prediction CSV can now be joined to the already aligned private 2025-26 odds rows by the same game identity.

The approved next analysis is limited to explicit batch-time quality bands:

```text
T-60 candidate absolute error <= 5 minutes
T-60 candidate absolute error <= 15 minutes
T-60 candidate absolute error <= 30 minutes
T-60 candidate absolute error <= 60 minutes
```

The purpose is sensitivity analysis—checking how model-versus-market comparisons change as timing uncertainty widens.

## What remains locked

```text
exact provider-origin observed_at: unverified
strict T-60: not qualified
formal Point-in-Time market backtest: locked
CLV: locked
ROI / Drawdown: locked
betting-edge claim: locked
Formal Stake: 0
```

## Next unique sub-mainline

```text
JOIN_2025_26_FORWARD_PROBABILITIES_TO_PRIVATE_ALIGNED_ODDS_FOR_TIME_BANDED_SENSITIVITY_ONLY
```
