# Point-in-time Odds Layer v1

## Purpose

This layer joins the selected `raw_logistic_elo` probability to timestamped two-way NBA moneyline quotes without allowing market data to leak into model training.

It produces:

- normalized decimal prices
- implied and proportional no-vig probabilities
- model-versus-market probability comparisons
- flat-stake threshold backtests
- same-book closing-line value
- ROI, win rate, maximum drawdown and bootstrap ROI intervals
- strict research-readiness gates

The output remains research data. It does not create a betting-edge claim.

## Canonical CSV schema

Start from `data/templates/point-in-time-odds-template.csv`.

Required fields:

| field | rule |
|---|---|
| `game_id` | must match `calibrated-predictions.csv` |
| `commence_time_utc` | ISO-8601 with timezone |
| `observed_at_utc` | ISO-8601 with timezone and strictly before commence time |
| `bookmaker` | stable bookmaker name or key |
| `market_key` | `h2h` or `moneyline` |
| `snapshot_label` | normally `21:00`, `T-60m`, `T-5m` or `Closing` |
| `home_price_decimal` | decimal odds greater than 1 |
| `away_price_decimal` | decimal odds greater than 1 |

Recommended provenance fields:

- `source_id`
- `source_event_id`
- `season_label`
- `home_team_abbr`
- `away_team_abbr`
- `fetched_at_utc`
- `raw_hash`
- `adapter_version`

Rows with an unknown game, a team mismatch, a duplicate quote key, or `observed_at_utc >= commence_time_utc` are excluded and reported.

## No-vig probability

For decimal prices `O_home` and `O_away`:

```text
q_home = 1 / O_home
q_away = 1 / O_away
overround = q_home + q_away - 1

fair_home = q_home / (q_home + q_away)
fair_away = q_away / (q_home + q_away)
```

Version 1 deliberately uses the transparent proportional method. More complex power or Shin methods can be compared later, but they must not replace this baseline silently.

## Entry and closing quotes

The entry quote is the latest row with the requested `snapshot_label`, normally `T-60m`.

Closing is:

1. the latest same-book row labeled `Closing`, or
2. if no explicit label exists, the latest same-book quote after entry and before start.

Closing prices are used only for CLV analysis. They are never used to select a bet.

## Selection rule

The model probability is the calibration decision from v1:

```text
raw_logistic_elo
```

For the home side:

```text
home_edge = model_home_probability - fair_home_probability
```

The selected side is whichever side has positive edge. A research bet requires:

```text
selected_edge >= minimum_edge
and
expected_value > 0
```

Default minimum edge:

```text
0.025
```

All results use one flat unit per bet. No Kelly sizing is used in v1.

## CLV

Same-book closing-line value is reported two ways:

```text
clv_price = entry_decimal_odds / closing_decimal_odds - 1
clv_probability = closing_fair_probability - entry_fair_probability
```

Positive values mean the entry price beat the same-book close.

## Outputs

- `normalized-odds.csv`
- `market-edge-records.csv`
- `point-in-time-odds-report.json`

The report includes model and market Log Loss/Brier comparisons, threshold sensitivity, ROI, maximum drawdown, closing coverage and source QA.

## Research readiness gate

`ready_for_research_market_backtest` requires:

- a non-synthetic source
- zero point-in-time violations
- zero team mismatches
- at least 500 matched games
- at least 3 seasons
- at least 80% same-book closing coverage
- one primary bookmaker selected by explicit request or coverage, never by ROI

Even after the gate passes:

```text
ready_for_betting_edge_claim = false
```

A separate untouched holdout, source-rights review, transaction-cost assumptions, and sensitivity analysis are still required.

## Local usage

```bash
python scripts/build_point_in_time_odds.py \
  --predictions /path/calibrated-predictions.csv \
  --odds-csv /path/point-in-time-odds.csv \
  --output-dir /tmp/nbavl-point-in-time-odds \
  --entry-snapshot T-60m \
  --minimum-edge 0.025
```

Optional single-book filter:

```bash
--bookmaker Pinnacle
```

## GitHub Actions

`Validate point-in-time Odds Layer v1` can read:

- `probability-calibration-v1` from a prior workflow run, and
- an odds CSV from another artifact run or a repository path.

The full odds archive should not be committed publicly unless its source rights explicitly allow redistribution.

## Source strategy

The current active source remains `user_odds`: manual, same-book, two-sided timestamped snapshots.

An optional commercial adapter may use The Odds API historical endpoint. Its official documentation states that featured-market history begins in June 2020, snapshots are 10 minutes until September 2022 and 5 minutes afterward, and historical access requires a paid plan. API keys must be stored as GitHub Secrets and raw responses must stay in temporary workflow storage or restricted artifacts.

Unknown websites must not be scraped merely to fill coverage.
