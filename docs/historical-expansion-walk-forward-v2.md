# Historical Expansion and Walk-Forward Model v2

This phase expands NBA Value Lab from a one-season modeling pilot to a five-season, season-ordered evaluation pipeline.

## Default seasons

The manual workflow builds these regular seasons in parallel:

- 2019–20
- 2020–21
- 2021–22
- 2022–23
- 2023–24

Each season is independently downloaded, normalized, audited and uploaded as a temporary one-day Actions artifact. The combine job then merges the audited Silver databases without committing raw NBA data to the public repository.

## Why seasons build independently

Parallel season jobs reduce total runtime and preserve a separate QA boundary for every source pair. One failed or structurally different season is visible before the databases are combined.

The merged Silver report validates:

- distinct game and feature keys
- season count and per-season game counts
- source archive hashes
- table totals
- source IDs rewritten to the correct season

The large combined Silver database is temporary. The retained artifact contains the compact Silver report, the multi-season Gold database and the model outputs.

## Gold season policy

Gold rolling features follow two boundaries:

```text
same season
and source_game_date < target_game_date
```

L5, L10, L20, venue splits, rest and schedule-load histories reset at every season boundary. This avoids treating the previous April as an immediate prior observation for the next October.

Same-day games remain excluded from one another because the historical source currently provides date precision rather than one unified scheduled tip-off timestamp.

## Elo season policy

Elo is point-in-time and updates only after a completed game. Unlike rolling box-score features, team strength carries across seasons with regression toward league average:

```text
new_rating = 1500 + 0.75 × (old_rating - 1500)
```

Default parameters:

- home-court advantage: 65 Elo points
- K factor: 20
- offseason retention: 0.75

Pregame Elo rating difference and Elo win probability become explicit Logistic/Ridge input features. Elo also remains an independent benchmark, so the report can measure whether Gold features add value beyond Elo itself.

## Walk-forward evaluation

No random split is allowed.

The first two seasons establish training history. Every following season is evaluated as a separate out-of-sample fold:

```text
2019–20 + 2020–21 → test 2021–22
2019–20 through 2021–22 → test 2022–23
2019–20 through 2022–23 → test 2023–24
```

The report publishes each fold and an aggregate out-of-fold evaluation.

Win probability metrics:

- Log Loss
- Brier Score
- Accuracy
- ROC-AUC
- calibration bins
- Log Loss gain versus Elo

Margin metrics:

- MAE
- RMSE
- correlation

## Artifacts

`historical-gold-multiseason` contains:

- `historical-gold-multiseason.sqlite.gz`
- `multiseason-silver-report.json`
- `multiseason-silver-sample.json`
- `multiseason-gold-report.json`
- `multiseason-gold-sample.json`

`model-walk-forward-v2` contains:

- `home-win-logistic-elo-v2.joblib`
- `home-margin-ridge-elo-v2.joblib`
- `walk-forward-report.json`
- `walk-forward-predictions.csv`

Artifacts are retained for 14 days. Temporary per-season Silver artifacts are retained for one day.

## Interpretation boundary

Five-season walk-forward testing is strong enough to begin calibration research. It is not yet a betting backtest.

The pipeline deliberately keeps `ready_for_market_odds_backtest` false until point-in-time market prices are joined with timestamps that prove each price existed before the prediction cutoff.
