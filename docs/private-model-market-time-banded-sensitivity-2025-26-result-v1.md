# Private Model / Market Time-Banded Sensitivity 2025-26 v1

Updated: 2026-07-24  
Research position: Research Candidate / Pre-Market-Backtest  
Formal Stake: 0

## Result

```text
PRIVATE_MODEL_MARKET_TIME_BANDED_SENSITIVITY_2025_26_VALID_RECORDED
```

The frozen 2025-26 model probabilities were joined privately to the officially aligned two-way moneyline archive. The comparison uses four predeclared nested timing-quality bands based on the absolute error between the selected collector batch and T-60:

```text
<= 5 minutes
<= 15 minutes
<= 30 minutes
<= 60 minutes
```

This is a sensitivity diagnostic. The archive timestamp is a collector-created league-batch timestamp assumed UTC, not a verified provider-origin quote timestamp.

## Private execution

```text
execution mode: local private offline
network requests: 0
provider API requests: 0
```

Input bindings:

```text
frozen-model predictions CSV SHA-256:
c3764faf6eb3703374b12a5d8668c6ef889cd8f54070a2c6cf135b55559ca725

aligned odds main CSV SHA-256:
8ce1f53a39f9dc3a0adf65f3f91ba9eb6024fccfabd5282a50eea00a1292a0b3

private odds bundle SHA-256:
346e69f9f4ad559422d55add1b0d2b5c1a2dc38e22ef4575e1fc8ec87bf0df43
```

Private output bindings:

```text
aggregate report SHA-256:
efa1327200d3fafee38978d882f3f736891587afe3460d211008c90cefa549ce

private joined CSV SHA-256:
fbd5b0133cd0ad58f3fe4dada53e79b0fd2ea6021d8179f648f727c76a96735b

private bundle SHA-256:
1bc637e6f5a5d50a8390ce969646abec6e1d20200979fc813e6365a139758732
```

No game-level prices, collector timestamps, or joined rows were committed publicly.

## Exact same-game join

```text
2025-26 prediction rows: 1,230
aligned regular-season odds events: 1,112
exact same-game matches before moneyline filter: 1,111
valid two-way pre-tip moneyline matches: 1,110
orientation mismatches: 0
duplicate join keys: 0
```

Join methods:

```text
official ordered away/home + Eastern date: 1,108
neutral-site team1/team2 + Eastern date: 2
```

Two records were excluded:

1. Orlando at Phoenix on 2026-02-21 had no valid two-way pre-tip moneyline.
2. Miami at Chicago on the published 2026-01-08 schedule row had no exact completed game on that ordered-team/date key. It was not fuzzily attached to another date.

## Market probability rule

For two decimal prices `O_home` and `O_away`:

```text
q_home = 1 / O_home
q_away = 1 / O_away

market_home_no_vig = q_home / (q_home + q_away)
market_away_no_vig = q_away / (q_home + q_away)
```

The selected row is the nearest valid pre-tip collector batch to T-60. No profitability-based timing-band selection was performed.

## Results by timing-quality band

| Maximum T-60 batch error | Games | Model Log Loss | Market Log Loss | Model Brier | Market Brier | Model Accuracy | Market Accuracy |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 min | 310 | 0.625383 | **0.602416** | 0.217402 | **0.208598** | 65.48% | **65.81%** |
| 15 min | 493 | 0.603332 | **0.576019** | 0.207676 | **0.196791** | 66.94% | **69.17%** |
| 30 min | 612 | 0.600365 | **0.570928** | 0.206647 | **0.194875** | 67.16% | **69.28%** |
| 60 min | 697 | 0.602119 | **0.577348** | 0.207430 | **0.197743** | 67.72% | **68.72%** |

ROC-AUC also favored the no-vig market in every band:

```text
<= 5 min:  model 0.6995 / market 0.7292
<= 15 min: model 0.7276 / market 0.7577
<= 30 min: model 0.7306 / market 0.7620
<= 60 min: model 0.7315 / market 0.7573
```

## Paired bootstrap interpretation

Each timing band used 5,000 paired game resamples. Positive model-minus-market Log Loss and Brier values mean the model was worse.

### T-60 error <= 5 minutes

```text
Log Loss difference 95% interval:
[+0.000241, +0.046153]

Brier difference 95% interval:
[-0.001278, +0.018990]

Accuracy difference 95% interval:
[-0.045161, +0.041935]
```

### T-60 error <= 15 minutes

```text
Log Loss difference 95% interval:
[+0.009116, +0.044748]

Brier difference 95% interval:
[+0.002911, +0.018695]

Accuracy difference 95% interval:
[-0.056795, +0.012170]
```

### T-60 error <= 30 minutes

```text
Log Loss difference 95% interval:
[+0.013716, +0.045402]

Brier difference 95% interval:
[+0.004780, +0.018973]

Accuracy difference 95% interval:
[-0.050654, +0.008170]
```

### T-60 error <= 60 minutes

```text
Log Loss difference 95% interval:
[+0.009757, +0.040017]

Brier difference 95% interval:
[+0.003073, +0.016398]

Accuracy difference 95% interval:
[-0.037303, +0.017217]
```

The no-vig market had lower Log Loss and Brier in all four predeclared timing bands. The evidence does not show the frozen model beating the market on this private archive.

## Side agreement

Model and market chose the same side in roughly 85–87% of the games:

```text
<= 5 min: 84.84%
<= 15 min: 84.79%
<= 30 min: 86.11%
<= 60 min: 86.66%
```

When they disagreed, the model-selected side did not exceed 50% accuracy in any band. This is diagnostic context only; it is not a predeclared betting strategy.

## Interpretation

The frozen model is meaningfully better than its pure Elo benchmark on the complete forward season, but the market is a stronger probability baseline on the matched private moneyline population.

This means the current model can estimate game win probability, but it has not demonstrated incremental market information sufficient to support a betting-edge claim.

A future model revision should focus on information not already efficiently reflected in the market—such as governed injury timing, lineup availability, rest/travel effects, matchup-specific player context, or market-independent uncertainty—while preserving an untouched forward holdout.

## Preserved locks

```text
provider-origin observed_at verified: false
strict T-60 qualified: false
formal Point-in-Time market backtest: locked
EV calculated: false
ROI calculated: false
CLV calculated: false
Drawdown calculated: false
bet selection executed: false
betting-edge claim: locked
Formal Stake: 0
```

## Next unique sub-mainline

```text
REVIEW_MODEL_MARKET_GAP_AND_PRESERVE_MARKET_BACKTEST_LOCK_WHILE_AWAITING_EXACT_PROVIDER_OBSERVED_AT
```
