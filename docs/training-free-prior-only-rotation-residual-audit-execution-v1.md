# Training-free Prior-only Rotation Residual Audit 2025–26 v1 — Execution

## Current state

The design and exact physical-column binding are already merged through PR #188 and PR #189.

This execution layer implements the frozen audit contract but does not publish row-level inputs or outputs.

Current mainline:

```text
IMPLEMENT_AND_EXECUTE_TRAINING_FREE_PRIOR_ONLY_ROTATION_RESIDUAL_AUDIT_2025_26_V1_USING_EXACT_COLUMN_BINDING
```

## Bound private inputs

The executor refuses any input whose SHA-256 differs from the predeclared values:

```text
Rotation matchup features:
sha256:3e8ef30f3a9801fda92fc95a490228b73fa53603093c914207e884a933b2de02

Frozen forward predictions:
sha256:c3764faf6eb3703374b12a5d8668c6ef889cd8f54070a2c6cf135b55559ca725

Private model-market join:
sha256:fbd5b0133cd0ad58f3fe4dada53e79b0fd2ea6021d8179f648f727c76a96735b
```

Expected row counts:

```text
Rotation matchup rows: 1,230
Feature-ready model rows: 1,075
Frozen prediction rows: 1,230
Private model-market join rows: 1,110
```

The market join remains a private archive diagnostic. Its collector batch timestamps are not provider-origin `observed_at` and do not qualify Strict T-60.

## Exact identity and feature binding

Game identity uses the official numeric NBA game ID serialized as a ten-character string. Restoring serialization-lost leading zeroes is allowed; team/date fallback and fuzzy matching are prohibited.

The twelve conceptual feature names are bound one-to-one to the physical PR #187 `diff_...` columns recorded by PR #189. Runtime prefix/suffix inference and approximate column matching are prohibited.

## Primary tests

### H1 — frozen-model signed residual

```text
model_home_residual = actual_home_win - model_home_probability
Spearman(signed rotation stress, model_home_residual) < 0
```

Population: all 1,075 feature-ready games with an exact frozen-prediction join.

### H2 — private-market relative error

```text
model_minus_market_log_loss_row
  = log_loss(model_home_probability)
  - log_loss(market_home_probability_no_vig)

Spearman(rotation stress gap magnitude,
         model_minus_market_log_loss_row) > 0
```

Primary market population: exact feature-ready intersection with nominal T-60 collector-batch absolute error `<= 5` minutes.

Nested sensitivity populations remain `<=15`, `<=30`, and `<=60` minutes. No band may replace the primary population because its result is more favorable.

## Secondary tests

- twelve fixed feature-difference correlations against model residual;
- twelve fixed feature-difference correlations against model-minus-market Log Loss;
- Brier-difference sensitivity;
- outcome-free quartile contrasts;
- Benjamini–Hochberg FDR `q <= 0.10` within each fixed twelve-feature family.

Secondary results are diagnostic only and cannot independently authorize feature selection or model training.

## Uncertainty and robustness

```text
Bootstrap resamples: 5,000
Seed: 20260725
Bootstrap unit: independent game
Confidence interval: 95%
```

The six primary decision checks remain:

1. H1 has the predeclared negative sign and its bootstrap interval excludes zero.
2. H2 has the predeclared positive sign and its bootstrap interval excludes zero.
3. H1 has the same sign in both chronological halves.
4. H2 has the same sign in both chronological halves.
5. H1 has the expected sign in at least four feature-ready months.
6. H2 has the expected sign in at least four feature-ready months.

## Formal outcomes

```text
AUDIT_INVALID_OR_UNDERPOWERED
VALID_NO_PRIOR_ONLY_ROTATION_RESIDUAL_SIGNAL
VALID_INCONCLUSIVE_PRIOR_ONLY_ROTATION_RESIDUAL_DIAGNOSTIC
VALID_DIAGNOSTIC_PRIOR_ONLY_ROTATION_RESIDUAL_SIGNAL
```

Even `VALID_DIAGNOSTIC_PRIOR_ONLY_ROTATION_RESIDUAL_SIGNAL` does not authorize model training, feature promotion, Strict T-60, formal Market Backtest, EV, ROI, CLV, Drawdown, betting selections, or Stake above `0`.

## Private execution command

```bash
python scripts/analyze_training_free_prior_only_rotation_residual_audit_2025_26_v1.py \
  --features /private/prior-only-player-rotation-matchup-features-2025-26-v1.csv \
  --predictions /private/frozen-model-forward-predictions-2025-26.csv \
  --market-join /private/private-model-market-time-banded-join-2025-26-v1.csv \
  --output /private/training-free-prior-only-rotation-residual-audit-2025-26-report-v1.json \
  --bootstrap-resamples 5000 \
  --seed 20260725
```

Only the aggregate report may later be recorded in the public Repository. The three input CSV files and any game-level joined output must remain private.

## Current execution blocker

The feature and frozen-prediction inputs are available in governed short-lived Artifacts. The exact private model-market join is stored in the user's File Library but is not mounted in the active execution environment.

Until the exact CSV is attached to the active conversation or otherwise supplied through an approved private execution path:

```text
EXECUTOR IMPLEMENTED
SYNTHETIC CONTRACT VALIDATION PENDING / IN PROGRESS
REAL THREE-WAY PRIVATE AUDIT NOT YET EXECUTED
```

No substitute, reconstructed approximation, public row-level commit, or different digest is allowed.
