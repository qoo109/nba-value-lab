# Model / Market Gap Review 2025–26 v1

Updated: 2026-07-24  
Research state: **Research Candidate / Pre-Market-Backtest**  
Formal Stake: **0**

## Purpose

Review where the frozen `walk-forward-v2` model differs from the private no-vig Moneyline market after PR #180. This is an aggregate-only offline diagnostic. It does not publish game-level prices, retrain the model, calculate EV/ROI/CLV, or qualify strict T-60.

## Source boundary

```text
prior main: d464bd0973974c9075e9a9bee9a14bb5fb2ac2d1
private joined games: 1,110
forward Gold games: 1,230
network requests: 0
provider API requests: 0
public game-level rows: 0
public price rows: 0
```

Primary population:

```text
nearest valid pre-tip collector batch
absolute T-60 batch error <= 5 minutes
games: 310
provider-origin observed_at verified: false
strict T-60 qualified: false
```

## Primary result

| Metric | Frozen model | No-vig market | Model minus market |
|---|---:|---:|---:|
| Log Loss | 0.625383 | 0.602416 | +0.022966 |
| Brier Score | 0.217402 | 0.208598 | +0.008804 |
| Accuracy | 65.48% | 65.81% | -0.32 pp |
| ROC-AUC | 0.699519 | 0.729216 | -0.029697 |

Calibration:

| Metric | Frozen model | No-vig market |
|---|---:|---:|
| ECE, 10 equal-frequency bins | 0.065452 | 0.052566 |
| Calibration intercept | -0.066442 | -0.078223 |
| Calibration slope | 0.928389 | 0.910955 |

The market advantage is not explained only by winner classification. The market has better Log Loss, Brier and ROC-AUC, while the accuracy difference is only 0.32 percentage points.

## Fixed probability-gap slices

| Absolute model-market home-probability gap | Games | Model minus market Log Loss | Model minus market Brier | Accuracy difference |
|---|---:|---:|---:|---:|
| 0-2.5pp | 63 | +0.004093 | +0.001291 | +0.00 pp |
| 2.5-5pp | 59 | +0.019967 | +0.008189 | -3.39 pp |
| 5-10pp | 96 | -0.001289 | -0.001106 | +1.04 pp |
| 10pp+ | 92 | +0.063125 | +0.024684 | +0.00 pp |

The largest descriptive weakness is the `10pp+` group: 92 games and a model-minus-market Log Loss difference of +0.063125. This is diagnostic, not a post-hoc betting filter.

## Side agreement

| Model and market choose same side | Games | Model minus market Log Loss |
|---|---:|---:|
| No | 47 | +0.024971 |
| Yes | 263 | +0.022608 |

The market remains better both when the model agrees with it and when the two choose opposite sides. Disagreement alone is therefore not evidence of model edge.

## Existing Gold feature residual correlations

Target:

```text
market home no-vig probability - model home probability
```

| Existing frozen matchup feature | Rows | Spearman rho |
|---|---:|---:|
| `orb_pct_last_10_diff` | 306 | +0.256961 |
| `net_rtg_last_10_diff` | 306 | +0.255484 |
| `net_rtg_last_5_diff` | 306 | +0.213735 |
| `net_rtg_last_20_diff` | 306 | +0.204551 |
| `free_throw_rate_last_10_diff` | 306 | +0.138480 |
| `prior_games_min` | 310 | +0.123262 |
| `evidence_coverage` | 310 | +0.119218 |
| `rest_days_diff` | 306 | +0.061756 |
| `tov_pct_last_10_diff` | 306 | +0.035662 |
| `efg_pct_last_10_diff` | 306 | -0.021645 |
| `pace_last_10_diff` | 306 | +0.001687 |

These are existing model inputs, not newly discovered information. The correlations may indicate misweighting, nonlinearity, or omitted information correlated with existing team-strength indicators. They do not authorize retuning on the same outcomes.

## Prior negative result that remains binding

The predeclared injury candidate `bounded_injury_logit_offset_v1` already finished as `VALID_NEGATIVE_RESULT`. Its combined 169-game forward Log Loss and Brier did not pass the frozen promotion gates. It must not be repeatedly retuned on the same injury outcomes.

## Formal decision

```text
PRESERVE_FROZEN_BASELINE_AND_MARKET_BACKTEST_LOCK
```

Not authorized:

- model retraining on this result;
- retuning the rejected two-feature injury candidate;
- activating a model-market blend;
- treating collector batch time as provider-origin `observed_at`;
- EV, ROI, CLV, Drawdown or betting-edge claims;
- nonzero stake.

## Next research design

```text
PREDECLARE_PRIOR_ONLY_PLAYER_ROTATION_STATE_FEATURE_LAYER_V1
```

The next credible model experiment must add genuinely new pre-game information rather than reweighting the same aggregate Gold features or using market prices as prediction features.

Candidate data family, to be frozen before outcome review:

- prior-game player minutes and role concentration;
- rotation continuity over prior 5/10 games;
- projected available top-8 minutes using only information available before tipoff;
- starter/bench role continuity inferred only from prior games;
- roster-change and return-from-absence state;
- explicit missingness and source-time checks.

This is a design target only. It does not activate training or market backtesting.

## Preserved locks

```text
strict T-60: false
formal point-in-time market backtest: false
EV / ROI / CLV / Drawdown: false
betting-edge claim: false
Formal Stake: 0
```
