# Model Baseline v1

Model Baseline v1 is the first auditable prediction layer built on the point-in-time Gold database.

## Targets

- `home_win`: binary home-team win outcome
- `home_margin`: final home score minus away score

## Models

- Logistic Regression for home win probability
- Ridge Regression for expected home margin
- Sequential Elo as a traditional probability benchmark
- Dummy prior/mean models as minimum comparison baselines

## Features

The model uses only pre-game Gold matchup features:

- Net Rating differences over 5, 10, and 20 games
- Pace, effective field-goal percentage, turnover percentage, offensive-rebound percentage, and free-throw-rate differences
- Rest-day difference
- Evidence coverage
- Minimum prior-game sample size

No betting odds are used in training.

## Leakage controls

Rows are sorted by `game_date, game_id` and split chronologically:

- first 70%: training
- next 15%: validation
- final 15%: test

The dataset is never randomly shuffled. Gold features already enforce `source_game_date < target_game_date`, so same-day and future games cannot enter a feature row.

## Metrics

Win probability:

- Log Loss
- Brier Score
- Accuracy
- ROC-AUC
- 10-bin calibration table

Margin:

- MAE
- RMSE
- prediction/actual correlation

## Outputs

The manual GitHub Actions build uploads `model-baseline-v1` containing:

- `home-win-logistic.joblib`
- `home-margin-ridge.joblib`
- `baseline-report.json`
- `baseline-predictions.csv`

## Interpretation rule

A successful single-season run proves the pipeline works; it does not prove a durable betting edge. Betting backtesting should remain blocked until multiple seasons and point-in-time market odds are available.
