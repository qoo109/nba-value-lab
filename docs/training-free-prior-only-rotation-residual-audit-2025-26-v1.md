# Training-free Prior-only Rotation Residual Audit 2025–26 v1

## Purpose

Predeclare the next diagnostic after PR #187. The audit asks whether the strictly-prior rotation-state feature layer is associated with frozen-model residuals and with paired model-minus-market error.

This is an audit design only. It does not execute the private join, fit a model, select production features, alter frozen probabilities, perform a formal Market Backtest or authorize betting use.

Formal state:

```text
TRAINING_FREE_PRIOR_ONLY_ROTATION_RESIDUAL_AUDIT_2025_26_V1_PREDECLARED
```

## Binding history

```text
Base main: 85821f7df6babce207dc5c39a24fbdcedd5ad165
Binding feature PR: #187
Binding feature result: PRIOR_ONLY_PLAYER_ROTATION_STATE_FEATURES_2025_26_RESULT_VALID
Binding prior decision: PRESERVE_FROZEN_BASELINE_AND_MARKET_BACKTEST_LOCK
```

PR #187 produced 1,230 private matchup rows, of which 1,075 independent games were feature-ready. The next step is permitted to inspect residual associations only; it is not a model-training step.

## Bound private inputs

### Rotation feature Artifact

```text
Artifact ID: 8603761824
Artifact SHA-256: sha256:e02cd15e9b3aa1d58d3cbee1f27f1caea461d7e2f8ec701389e6e5f969ba440a
Head: b1de9fa8616caff42f251d2db253e8ed2f80e42a
Matchup CSV SHA-256: sha256:3e8ef30f3a9801fda92fc95a490228b73fa53603093c914207e884a933b2de02
Feature-ready games: 1,075
```

### Frozen forward predictions

```text
Artifact ID: 8592208938
Artifact SHA-256: sha256:3f509beac4a897a86baf3bdfceb0d37100e65b334c60162ef98effee5064f518
Prediction CSV SHA-256: sha256:c3764faf6eb3703374b12a5d8668c6ef889cd8f54070a2c6cf135b55559ca725
Rows: 1,230
```

### Private market diagnostic join

```text
Private join CSV SHA-256: sha256:fbd5b0133cd0ad58f3fe4dada53e79b0fd2ea6021d8179f648f727c76a96735b
Private odds main CSV SHA-256: sha256:8ce1f53a39f9dc3a0adf65f3f91ba9eb6024fccfabd5282a50eea00a1292a0b3
Private odds bundle SHA-256: sha256:346e69f9f4ad559422d55add1b0d2b5c1a2dc38e22ef4575e1fc8ec87bf0df43
Valid two-sided pre-tip Moneyline games before the feature intersection: 1,110
```

All row-level inputs remain private. A missing or expired bound Artifact cannot be silently replaced by an ungoverned source.

## Identity and timing policy

The join uses exact governed `game_id` only.

Prohibited:

- fuzzy identity;
- team-name guessing;
- date-only fallback for the residual join;
- duplicate game keys;
- missing-side imputation;
- target-game feature reconstruction;
- replacing a bound input with a new unrecorded file.

Market timing remains:

```text
PRIVATE_ARCHIVE_BATCH_RELATIVE_DIAGNOSTIC_ONLY
```

The collector batch timestamp is not verified provider-origin `observed_at`. Nothing in this audit may be described as Strict T-60 or an executable market snapshot.

## Populations

### Primary model-residual population

All feature-ready independent games that join exactly to the frozen forward predictions.

```text
Expected rows: 1,075
Minimum valid rows: 1,000
One row per game: required
```

### Primary market-residual population

The exact intersection of:

- feature-ready rotation games;
- frozen forward predictions;
- private model-market join;
- nominal T-60 batch absolute error `<= 5` minutes.

```text
Minimum valid rows: 200
```

The market sensitivity populations are nested at `<=15`, `<=30` and `<=60` minutes. They cannot replace the primary population because one gives a more favorable result.

## Residual direction

The signed direction is fixed before execution:

```text
model_home_residual = actual_home_win - model_home_probability
market_home_residual = actual_home_win - market_home_probability_no_vig
```

Interpretation:

- positive signed residual: the home side performed better than forecast;
- negative signed residual: the home side performed worse than forecast.

Paired market-relative error:

```text
model_minus_market_log_loss_row
  = binary_log_loss(model_home_probability)
  - binary_log_loss(market_home_probability_no_vig)
```

A positive value means the frozen model was worse than the private no-vig market on that game.

Brier difference is a secondary sensitivity measure.

## Feature scope

Primary individual-feature tests use only the twelve predeclared `home - away` matchup differences:

- `rotation_players_prior_5_diff`
- `top5_minutes_share_prior_5_diff`
- `top8_minutes_share_prior_5_diff`
- `top8_minutes_share_prior_10_diff`
- `rotation_entropy_prior_5_diff`
- `rotation_entropy_prior_10_diff`
- `top8_set_continuity_prior_5_diff`
- `starter_set_continuity_prior_5_diff`
- `minutes_allocation_volatility_prior_5_diff`
- `role_change_magnitude_prior_3_vs_10_diff`
- `recent_return_players_count_diff`
- `new_team_rotation_players_prior_5_diff`

Raw home and away values may be summarized descriptively but are not an additional primary test family.

No feature may be added, removed, transformed or thresholded after outcome inspection.

## Predeclared rotation-stress index

The audit also uses one outcome-free, equal-weight diagnostic index. Components are median/IQR scaled on the feature-ready audit population.

Positive stress components:

- more rotation players;
- greater minute-allocation volatility;
- greater role-change magnitude;
- more recent-return players;
- more new-team rotation players.

Negative-signed components:

- top-eight continuity;
- starter continuity.

The signed index is home stress minus away stress. Positive means greater home-side rotation stress. At least five of seven components must be present.

The absolute index is the stress-gap magnitude.

This scaling is audit-only. It is not a point-in-time production transform and cannot be inserted into a model without a later walk-forward predeclaration.

## Primary hypotheses

### H1 — Signed frozen-model residual

```text
Spearman(signed rotation stress, model_home_residual) < 0
```

Greater home-relative rotation stress is expected to be associated with home underperformance versus the frozen model.

### H2 — Market-relative error

```text
Spearman(rotation stress gap magnitude,
         model_minus_market_log_loss_row) > 0
```

Larger rotation-state imbalance is expected to identify games where the frozen model trails the private no-vig market by more.

These directions are frozen before private outcome execution.

## Secondary diagnostics

- two-sided Spearman correlations for all twelve fixed feature differences;
- top-versus-bottom quartile mean residual contrasts;
- market-relative Brier difference;
- raw home and away descriptive summaries.

The twelve-feature families use Benjamini–Hochberg FDR at `q <= 0.10`, separately for model-residual and market-relative tests.

Secondary results cannot independently promote a feature or authorize training.

## Uncertainty and robustness

```text
Bootstrap resamples: 5,000
Seed: 20260725
Bootstrap unit: independent game
Confidence interval: 95%
```

Robustness checks:

- chronological first-half and second-half sign consistency;
- same direction in at least four of six feature-ready months;
- nested market sensitivity at `<=15`, `<=30` and `<=60` minutes;
- no best-band selection;
- no post-hoc threshold tuning.

## Decision policy

Possible formal outcomes:

```text
AUDIT_INVALID_OR_UNDERPOWERED
VALID_NO_PRIOR_ONLY_ROTATION_RESIDUAL_SIGNAL
VALID_INCONCLUSIVE_PRIOR_ONLY_ROTATION_RESIDUAL_DIAGNOSTIC
VALID_DIAGNOSTIC_PRIOR_ONLY_ROTATION_RESIDUAL_SIGNAL
```

A valid diagnostic signal requires all of the following:

1. H1 has the predeclared negative sign and its 95% bootstrap interval excludes zero.
2. H2 has the predeclared positive sign and its 95% bootstrap interval excludes zero.
3. Both signs are consistent in both chronological halves.
4. Both signs appear in at least four feature-ready months.
5. Every validity and privacy gate passes.

Even the strongest diagnostic result does not authorize model training, feature selection, model promotion, Strict T-60, formal Market Backtest or betting use.

## Public/private boundary

Public outputs are aggregate only:

- population counts;
- aggregate correlations and confidence intervals;
- FDR-adjusted aggregate tables;
- chronological and monthly aggregate sign checks;
- formal decision;
- preserved locks.

Public repository counts remain:

```text
Public game-level joined rows: 0
Public player rows: 0
Public price rows: 0
Raw private Artifacts committed: 0
```

## Preserved locks

```text
Model training authorized: false
Model promotion authorized: false
Strict T-60 qualified: false
Formal Market Backtest allowed: false
Betting-edge claim allowed: false
Formal Stake: 0
```

## Next unique mainline after design validation

```text
EXECUTE_TRAINING_FREE_PRIOR_ONLY_ROTATION_RESIDUAL_AUDIT_2025_26_V1_ON_BOUND_PRIVATE_ARTIFACTS
```

Execution must occur in a later governed step after this design passes CI and is merged.
