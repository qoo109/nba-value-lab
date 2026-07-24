# Training-free Prior-only Rotation Residual Audit Executor v1

## Status

```text
EXECUTOR_READY
REAL_PRIVATE_RESIDUAL_AUDIT_NOT_EXECUTED
EXACT_PRIVATE_MODEL_MARKET_JOIN_NOT_AVAILABLE
```

This implementation provides the governed executor and synthetic contract test for the design merged in PR #188 and the exact column binding merged in PR #189.

It does not record or imply a real residual result.

## Bound inputs

```text
Rotation feature Artifact: 8603761824
Rotation matchup CSV SHA-256:
sha256:3e8ef30f3a9801fda92fc95a490228b73fa53603093c914207e884a933b2de02

Frozen prediction Artifact: 8592208938
Frozen prediction CSV SHA-256:
sha256:c3764faf6eb3703374b12a5d8668c6ef889cd8f54070a2c6cf135b55559ca725

Required private model-market join SHA-256:
sha256:fbd5b0133cd0ad58f3fe4dada53e79b0fd2ea6021d8179f648f727c76a96735b
```

The executor validates all three row-level input SHA-256 values before reading or computing results.

No substituted, reconstructed, newly scraped or approximately matching market file is accepted.

## Exact joins and physical columns

- feature and prediction identity: exact governed `game_id`;
- feature and private market identity: exact governed `game_id`;
- game date, home team and away team must agree exactly;
- duplicate keys are fatal;
- frozen model probability and outcome must match between prediction and private market rows;
- the twelve physical `diff_...` columns are read only through the PR #189 one-to-one mapping;
- no prefix/suffix inference, fuzzy column selection or positional fallback is used.

## Primary populations

```text
Model residual population:
expected 1,075 feature-ready exact joins
minimum 1,000

Market residual population:
feature-ready exact intersection
nominal T-60 collector batch absolute error <= 5 minutes
minimum 200

Sensitivity:
<= 15 / <= 30 / <= 60 minutes
```

Nominal T-60 remains a private archive batch-relative diagnostic. It is not provider-origin `observed_at`, Strict T-60 or an executable market snapshot.

## Statistical implementation

The executor implements the frozen PR #188 design:

- signed rotation-stress index using outcome-free median/IQR scaling;
- minimum five available components;
- H1 Spearman correlation with signed frozen-model residual;
- H2 Spearman correlation with paired model-minus-market per-game Log Loss difference;
- 5,000 independent-game bootstrap resamples with seed `20260725`;
- chronological first/second-half signs;
- monthly signs, requiring at least 10 rows for a reported monthly correlation;
- twelve fixed feature-difference secondary Spearman tests;
- Benjamini–Hochberg FDR `q <= 0.10` separately by family;
- top-versus-bottom quartile contrasts;
- Brier-difference sensitivity;
- nested 15/30/60-minute market timing sensitivity.

No best-band selection or post-hoc threshold tuning is allowed.

## Formal decisions

The executor can emit only one predeclared decision:

```text
AUDIT_INVALID_OR_UNDERPOWERED
VALID_NO_PRIOR_ONLY_ROTATION_RESIDUAL_SIGNAL
VALID_INCONCLUSIVE_PRIOR_ONLY_ROTATION_RESIDUAL_DIAGNOSTIC
VALID_DIAGNOSTIC_PRIOR_ONLY_ROTATION_RESIDUAL_SIGNAL
```

A diagnostic signal still does not authorize training, feature promotion or betting use.

## Public/private boundary

Only one aggregate JSON report may be published or committed.

The executor does not write:

- joined game rows;
- player rows;
- market quote rows;
- prediction rows;
- feature rows;
- selected games;
- betting recommendations.

```text
Public game-level rows: 0
Public player rows: 0
Public price rows: 0
Raw private Artifacts committed: 0
```

## Synthetic validation only

The CI workflow runs `--self-test` with generated synthetic arrays. The synthetic test checks:

- negative H1 behavior;
- positive H2 behavior;
- bootstrap confidence intervals;
- Benjamini–Hochberg adjustment;
- no model fitting API;
- all research locks.

It does not load the real feature, prediction or private market files.

## Current blocker

The exact private model-market join from PR #180 is not in the public Repository and is not present in the current governed Actions Artifact set.

Required identity:

```text
filename:
private-model-market-time-banded-join-2025-26-v1.csv

SHA-256:
sha256:fbd5b0133cd0ad58f3fe4dada53e79b0fd2ea6021d8179f648f727c76a96735b
```

Until that exact file, or the exact governed private archive capable of reproducing it under the frozen PR #180 analyzer, is restored, real execution remains blocked.

The blocker must not be bypassed by:

- downloading a different Kaggle copy;
- scraping Pinnacle or another bookmaker;
- rebuilding from an unverified archive;
- changing the expected digest;
- using the aggregate PR #180 result as row-level input;
- executing only H1 while H2 input is absent.

## Preserved locks

```text
Real private residual audit executed: false
Model fit/refit/retraining: false
Calibration change: false
Feature selection: false
Model promotion authorized: false
Strict T-60 qualified: false
Formal Market Backtest allowed: false
EV / ROI / CLV / Drawdown calculated: false
Betting-edge claim allowed: false
Formal Stake: 0
```

## Next unique mainline

```text
RESTORE_EXACT_PRIVATE_MODEL_MARKET_JOIN_AND_EXECUTE_BOUND_TRAINING_FREE_ROTATION_RESIDUAL_AUDIT
```
