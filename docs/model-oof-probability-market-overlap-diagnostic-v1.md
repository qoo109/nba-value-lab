# Model OOF Probability / Market Overlap Diagnostic v1

Updated: 2026-07-24  
Position: Research Candidate / Pre-Market-Backtest  
Formal Stake: 0

## Purpose

This diagnostic answers two separate questions without retraining the model:

1. How well does the current selected probability method behave on its historical out-of-fold games?
2. Can those model predictions be joined to the newly aligned 2025-26 private odds archive?

The analysis uses the real `model-walk-forward-v2` Artifact from workflow run `29551715399` and the private aligned 2025-26 main-lines CSV. Raw predictions and raw prices remain outside the repository.

## Frozen input evidence

```text
model workflow run: 29551715399
model Artifact: 8396002523
model Artifact digest:
sha256:6063adac9851b47d339a93e35935115008b736a16925548d36a8c54a0353b41b
OOF rows: 3,688
OOF seasons: 2021-22, 2022-23, 2023-24
private odds rows: 8,153
private odds regular events: 1,112
private odds season: 2025-26
```

## Model-only OOF result

Selected probability method:

```text
raw_logistic_elo
```

Aggregate result:

| Metric | Logistic + Elo | Elo benchmark | Model minus Elo |
|---|---:|---:|---:|
| Log Loss | 0.631306 | 0.634301 | -0.002996 |
| Brier Score | 0.220567 | 0.221949 | -0.001383 |
| Accuracy | 63.856% | 64.073% | -0.217 pp |
| ROC-AUC | 0.687099 | 0.684454 | +0.002645 |

The model improves probability-sensitive metrics slightly while its hard 50% classification accuracy is slightly lower than Elo. This is consistent with the project objective: probability quality matters more than a small difference in raw winner-picking accuracy.

## Calibration

Equal-width ten-bin reliability:

```text
ECE: 0.014239
MCE: 0.162346
```

The large MCE comes from the `0.90-1.00` bin, which contains only four games. It must not be interpreted as a broad 16.2 percentage-point calibration failure. The weighted ECE of about 1.42 percentage points is the more representative aggregate summary.

## Historical confidence bands

The table selects whichever side the model gives at least the stated probability. It reports historical OOF accuracy, not value, EV or profitability.

| Minimum selected-side probability | Games | Coverage | Historical accuracy | Mean model probability |
|---:|---:|---:|---:|---:|
| 50% | 3,688 | 100.0% | 63.86% | 64.56% |
| 55% | 2,961 | 80.29% | 67.31% | 67.52% |
| 60% | 2,260 | 61.28% | 70.00% | 70.61% |
| 65% | 1,643 | 44.55% | 73.04% | 73.69% |
| 70% | 1,091 | 29.58% | 77.27% | 76.87% |
| 75% | 640 | 17.35% | 79.53% | 79.99% |
| 80% | 281 | 7.62% | 82.56% | 83.30% |

These results show sensible monotonic behavior: higher model confidence corresponds to higher historical accuracy and lower coverage. They do not establish that any threshold is profitable because no same-game, point-in-time market price is present in these OOF seasons.

## Paired bootstrap versus Elo

Five thousand paired game resamples were used with seed `20260724`.

```text
Log Loss difference, model - Elo:
mean -0.003007
95% interval [-0.006914, +0.001056]
model better in 92.86% of resamples

Brier difference, model - Elo:
mean -0.001389
95% interval [-0.003090, +0.000383]
model better in 93.58% of resamples

Accuracy difference, model - Elo:
mean -0.002047
95% interval [-0.012209, +0.007863]
model better in 34.22% of resamples
```

Probability improvement is directionally consistent but the 95% intervals still cross zero. The correct interpretation is **small research value over Elo, not decisive superiority**.

## Market overlap gate

```text
model OOF seasons: 2021-22 through 2023-24
private odds season: 2025-26
overlap seasons: none
market sensitivity executed: false
```

Joining the current historical OOF prediction rows directly to the 2025-26 odds would be scientifically invalid. The games are not the same population.

Formal state:

```text
MODEL_OOF_PROBABILITY_DIAGNOSTIC_VALID_MARKET_JOIN_BLOCKED_NO_SEASON_OVERLAP
```

## What is needed for 2025-26 model probability

The trained artifact exists, but strict forward scoring remains blocked by:

```text
MISSING_GOVERNED_2024_25_SEASON_STATE
MISSING_GOVERNED_2025_26_PRE_GAME_GOLD_FEATURES
MISSING_2025_26_MODEL_PREDICTION_ROWS
```

The 2024-25 season cannot simply be skipped because the model's point-in-time Elo state carries across seasons with offseason regression. The 2025-26 Gold rows must also be constructed using only information available before each target game.

## Preserved boundaries

```text
model retraining performed: false
raw predictions committed: false
raw odds committed: false
same-game model-versus-market comparison: false
strict T-60 qualified: false
Market Backtest: locked
CLV: locked
ROI: locked
betting-edge claim: locked
Formal Stake: 0
```

## Decision

```text
KEEP_RAW_LOGISTIC_ELO_AS_RESEARCH_PROBABILITY_BASELINE_AND_BUILD_2024_25_TO_2025_26_GOVERNED_FORWARD_FEATURE_CHAIN_BEFORE_ODDS_JOIN
```

Next diagnostic sub-mainline:

```text
BUILD_GOVERNED_2024_25_AND_2025_26_PRE_GAME_FEATURE_CHAIN_WITHOUT_RETRAINING_THEN_SCORE_2025_26_FORWARD
```
