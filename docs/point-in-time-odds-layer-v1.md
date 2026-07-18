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

## Current execution boundary

The layer and schema already exist, but executable historical odds have not yet been acquired. The frozen acquisition contract is:

```text
data/real-timestamped-odds-acquisition-policy-v1.json
```

Until that policy is merged and its separately approved acquisition passes, this document remains an implementation specification only. It does not authorize paid API requests, odds joins, market backtests, CLV, EV, ROI, Drawdown or nonzero stake.

## Canonical CSV schema

Start from `data/templates/point-in-time-odds-template.csv`.

Required fields:

| field | rule |
|---|---|
| `game_id` | must match the frozen OOF prediction population |
| `commence_time_utc` | ISO-8601 with timezone |
| `observed_at_utc` | source snapshot time, ISO-8601 with timezone and strictly before commence time |
| `bookmaker` | stable bookmaker name or key |
| `market_key` | `h2h` or `moneyline` |
| `snapshot_label` | acquisition v1 freezes `OpeningGridProxy`, `T-6h`, `T-3h`, `T-1h`, `T-30m` and `Closing` |
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
- provider bookmaker key and title
- provider bookmaker `last_update`
- provider outcome source IDs when available

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

No-vig, edge or performance metrics are forbidden during the acquisition stage. They belong only to a later, separately predeclared odds-join and market-backtest stage.

## Entry and closing quotes

The first future executable-entry study is frozen at `T-1h`; other fixed snapshots are retained for movement and sensitivity analysis. No entry rule is active during acquisition.

Closing is the same-book two-sided quote associated with the frozen `Closing` request and passing the source timestamp and bookmaker last-update freshness gates. It may not be selected after outcomes or ROI are observed.

Closing prices are used only for later CLV analysis. They are never used to select a bet.

## Opening proxy

Acquisition v1 does not claim to recover each bookmaker's true first-posted opening line. It uses a frozen request grid and labels the earliest valid two-sided quote:

```text
OpeningGridProxy
```

The proxy label must remain visible in every downstream output.

## Selection rule

The only model path allowed for future market research is the calibration decision retained after the injury holdout:

```text
frozen raw_logistic_elo baseline only
```

The exact injury candidate from Holdout v1 was formally rejected and must not enter this layer.

For the home side in a future market-backtest PR:

```text
home_edge = model_home_probability - fair_home_probability
```

Any threshold, expected-value rule, transaction-cost assumption or bet-selection policy must be frozen in a separate future predeclaration. The earlier example threshold in this implementation is not activated by acquisition.

## CLV

A future same-book closing-line value may be reported two ways:

```text
clv_price = entry_decimal_odds / closing_decimal_odds - 1
clv_probability = closing_fair_probability - entry_fair_probability
```

Positive values mean the entry price beat the same-book close. No CLV is calculated in the acquisition PR.

## Outputs of the later market layer

- `normalized-odds.csv`
- `market-edge-records.csv`
- `point-in-time-odds-report.json`

These outputs are not public by default. Provider usage rights and restricted-storage boundaries control whether quote-level data may leave private storage.

## Research readiness gate

The generic layer requires:

- a non-synthetic source
- zero point-in-time violations
- zero team mismatches
- at least 500 matched games
- at least 3 seasons
- at least 80% same-book closing coverage
- one primary bookmaker selected by coverage, never by ROI

The frozen Real Timestamped Odds Acquisition v1 contract is stricter for the planned full backfill:

```text
matched independent games >= 3,000
matched games in every season >= 900
T-1h two-sided coverage >= 80%
same-book T-1h / Closing paired coverage >= 80%
```

The stricter acquisition contract governs this project milestone.

Even after acquisition passes:

```text
ready_for_betting_edge_claim = false
```

A separate odds-join and market-backtest predeclaration, an untouched evaluation, usage-rights review, transaction-cost assumptions and sensitivity analysis are still required.

## Local usage

This command is retained only for a future restricted-input market study:

```bash
python scripts/build_point_in_time_odds.py \
  --predictions /path/calibrated-predictions.csv \
  --odds-csv /restricted/path/point-in-time-odds.csv \
  --output-dir /restricted/path/nbavl-point-in-time-odds \
  --entry-snapshot T-1h \
  --minimum-edge 0.025
```

It must not be run as part of the acquisition predeclaration or source-health pilot.

## GitHub Actions and storage

The public repository may contain:

- adapter and validation code
- credential-free source manifests
- schema and policy files
- hashes, byte counts and request/quota totals
- aggregate source-health QA
- deidentified failure diagnostics

It must not contain API credentials or raw/normalized bookmaker quote rows. The Odds API data must stay in restricted user-controlled storage; temporary workflow copies must be deleted. Public Artifacts remain aggregate-only.

## Source strategy

The selected planned source is `the_odds_api_historical_v4`, governed by `data/real-timestamped-odds-acquisition-policy-v1.json` and the existing `data/historical-odds-source-registry.json`.

Historical access is commercial and remains blocked until all of the following exist:

```text
merged predeclaration
paid historical access
THE_ODDS_API_KEY configured privately
restricted raw/normalized storage
explicit 90-game pilot budget approval
```

A successful 90-game source-health pilot may only unlock a separately approved full backfill. The full 3,688-game acquisition is not automatically authorized.

`user_odds` remains a manual schema-compatible reference path, not an automatic replacement source. Unknown websites, manual-reference sites and sources that prohibit automated extraction must not be scraped to fill coverage.
