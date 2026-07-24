# Private Model/Market Gap Decomposition 2025-26 v1

Updated: 2026-07-24  
Research state: **Research Candidate / Pre-Market-Backtest**  
Formal Stake: **0**

## Purpose

Decompose why the frozen `walk-forward-v2` probability model trails the private no-vig Moneyline market without retraining the model, changing calibration, selecting bets or promoting a formal market backtest.

The diagnostic uses the already-governed private same-game join from PR #180 and enriches it with the governed 2025-26 forward Gold matchup features. It does not publish game-level prices or joined rows.

## Inputs

```text
private same-game model/market joins: 1,110
unique games: 1,110
Gold feature matches: 1,110
model: frozen walk-forward-v2 / raw_logistic_elo
fit/refit calls: 0
provider requests: 0
```

The market timestamp remains a collector-created league-batch timestamp assumed UTC. It is not provider-origin `observed_at`, so strict T-60 and formal Point-in-Time market backtesting remain unqualified.

## Predeclared design

Time-quality bands:

```text
±5 / ±15 / ±30 / ±60 minutes from T-60
```

Absolute model-versus-market probability-gap bins inside the ±60-minute population:

```text
< 2 percentage points
2 to <5 percentage points
5 to <10 percentage points
>=10 percentage points
```

Existing governed features are reviewed as a complete fixed list, not selected after seeing results:

- Net Rating differences over 5, 10 and 20 games
- Pace difference over 10 games
- eFG%, TOV%, ORB% and free-throw-rate differences over 10 games
- rest-days difference
- minimum prior-game count
- evidence coverage

No subgroup is promoted into a rule or betting threshold.

## Incremental-information diagnostic

Define:

```text
model-market delta = model home win probability - no-vig market home probability
market residual = actual home win - no-vig market home probability
```

A useful model deviation should have a stable positive relationship with the later market residual. The measured Spearman relationships were:

| T-60 batch-error band | Games | Delta vs market residual rho | Model/market side disagreements | Model-side win rate in disagreements |
|---:|---:|---:|---:|---:|
| ≤5 min | 310 | +0.0548 | 47 | 48.94% |
| ≤15 min | 493 | +0.0083 | 75 | 42.67% |
| ≤30 min | 612 | -0.0104 | 85 | 42.35% |
| ≤60 min | 697 | +0.0067 | 93 | 46.24% |

All four bootstrap 95% intervals for the correlation and covariance cross zero. In no band did the model side win a majority of games where model and market chose opposite sides.

## Probability-gap magnitude

Within the predeclared ±60-minute population:

| Absolute probability gap | Games | Model-minus-market Log Loss | Model-minus-market Brier |
|---:|---:|---:|---:|
| <2 pp | 119 | +0.003309 | +0.001091 |
| 2–<5 pp | 172 | +0.008426 | +0.003473 |
| 5–<10 pp | 208 | +0.025011 | +0.009859 |
| ≥10 pp | 198 | +0.051618 | +0.020069 |

The larger the frozen model's deviation from the market, the larger its Log Loss penalty in this population. This is descriptive evidence against using a larger model-market gap as an automatic value or bet-selection threshold.

## Existing Gold feature review

Several existing team-form features are associated with how the model deviates from the market, especially:

```text
ORB% last-10 difference       rho with model-market delta: -0.2666
Net Rating last-10 difference rho with model-market delta: -0.2284
Net Rating last-5 difference  rho with model-market delta: -0.2157
Net Rating last-20 difference rho with model-market delta: -0.1975
```

However, every predeclared existing feature has an absolute Spearman relationship below `0.06` with the later market residual in the ±60-minute population. This means the existing features can help explain *why* the model disagrees with the market, but this diagnostic does not show that those disagreements correct market errors.

This result does not prove any feature is harmful or causally over-weighted. It only blocks promotion based on the current diagnostic.

## Formal interpretation

```text
NO_INCREMENTAL_INFORMATION_SIGNAL_DEMONSTRATED
```

The frozen model remains a useful standalone probability model and is better than the Elo benchmark. But its deviations from this private no-vig market do not show stable incremental information. Increasing the probability-gap threshold would magnify, rather than repair, the observed forecasting penalty.

## Next research direction

The next work should add genuinely new point-in-time information that the current Gold layer does not contain:

1. point-in-time injury availability;
2. expected-minutes changes;
3. confirmed starting lineups;
4. rotation and player-role changes.

These are candidates, not validated features. The next diagnostic must first build coverage and residual evidence without fitting or modifying the frozen model.

Do not reopen:

- Rest/Travel v1 without materially different data;
- post-hoc model-market probability-gap threshold tuning;
- the prior Closing Market residual selection using the same design.

## Preserved locks

```text
model retraining: false
model refit: false
calibration change: false
market as model feature: false
strict T-60 qualified: false
formal Point-in-Time Market Backtest: false
EV / ROI / CLV / Drawdown: false
betting-edge claim: false
Formal Stake: 0
```

## Public/private boundary

Public repository contains only analyzer code, aggregate results, validation, documentation and handoff.

```text
public game-level rows: 0
public price rows: 0
raw odds archives: 0
private augmented rows retained locally: 1,110
```

## Next unique sub-mainline

```text
BUILD_2025_26_POINT_IN_TIME_INJURY_LINEUP_ROLE_FEATURE_DIAGNOSTIC
WITHOUT_MODEL_RETRAINING_OR_MARKET_BACKTEST_PROMOTION
```
