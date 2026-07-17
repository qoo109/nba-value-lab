# Probability Calibration v1

Probability Calibration v1 evaluates whether the five-season walk-forward probabilities should be recalibrated before market odds are joined.

## Inputs

The workflow reads `walk-forward-predictions.csv` from a completed `model-walk-forward-v2` artifact. It does not rebuild Silver, Gold or the predictive models.

## Candidates

- raw Logistic + Elo probability
- Platt scaling on the raw logit
- isotonic regression
- Elo benchmark

## Leakage rule

Calibration is evaluated in season order.

For each target season, its calibrator is fitted only on out-of-fold predictions from earlier completed test seasons. The target season is never used to fit its own calibrator.

With the current three OOF seasons:

- 2021–22 OOF predictions calibrate 2022–23
- 2021–22 and 2022–23 OOF predictions calibrate 2023–24

## Activation gate

A calibration candidate is activated only when it:

1. improves aggregate Log Loss by at least 0.0005; and
2. does not worsen aggregate Brier Score.

If neither candidate passes, the production choice remains the raw Logistic + Elo probability. This prevents unnecessary calibration from damaging already useful probabilities.

## Metrics

Each method is compared using:

- Log Loss
- Brier Score
- Accuracy
- ROC-AUC
- expected calibration error
- maximum calibration error
- ten-bin reliability table

The report also publishes the full-OOF Platt intercept and slope. Intercept near zero and slope near one indicate limited need for global recalibration.

## Workflow

Run `Calibrate walk-forward probabilities` and provide the workflow run ID that contains `model-walk-forward-v2`.

The workflow uses GitHub Actions artifact download, so the five historical seasons do not need to be rebuilt.

## Artifact

`probability-calibration-v1` contains:

- `probability-calibration-report.json`
- `calibrated-predictions.csv`
- `calibration-candidates.joblib`

The candidate model file is diagnostic. Consumers must obey `selected_probability_method` in the report and must not activate Platt or isotonic automatically.

## Market-data boundary

Completing calibration makes the probability layer ready for a point-in-time odds join. It does not prove a betting edge. Market backtesting remains blocked until timestamped moneyline snapshots and closing lines are available.
