# GitHub Automation Runbook v1

## Purpose

Run research-safe automation from the GitHub website without committing raw
datasets, API secrets, full databases, or betting records.

Formal stake remains `0`.

## Ready Workflows

### 1. Eoin File Census + Internal Qualification

Website launcher:

```text
NBA Value Lab website
-> 明日分析
-> GITHUB WEBSITE RUNNER
-> paste fine-grained GitHub token
-> 啟動 Eoin census
```

The website launcher calls GitHub's workflow dispatch REST API from the user's
browser. The token is not committed, embedded in the site, or sent to a custom
server. Use a fine-grained token limited to this repository with Actions
read/write permission.

GitHub website fallback:

```text
Actions -> Run Eoin Kaggle CSV census v1 -> Run workflow
```

Default input:

```text
dataset_handle: eoinamoore/historical-nba-data-and-player-box-scores
```

What it does:

```text
downloads the public Kaggle dataset into temporary Actions storage
checks expected CSV inventory
counts rows, columns, null keys, duplicate key groups
checks internal Games / TeamStatistics / PlayerStatistics consistency
reads PlayByPlay.parquet metadata when the workflow dependency is available
uploads aggregate-only JSON reports
does not upload raw CSV rows or raw Parquet rows
does not execute formal cross-source qualification by itself
```

Optional secret if Kaggle requires authentication:

```text
KAGGLE_API_TOKEN
```

### 2. Eoin Cross-Source Audit

```text
Actions -> Run Eoin cross-source audit v1 -> Run workflow
```

What it does:

```text
downloads Eoin Kaggle data into temporary Actions storage
downloads shufinskiy/nba_data nbastats_2023 reference into temporary Actions storage
compares 2023-24 game identity, final scores, team-score coverage, player-row availability, and PBP availability
uploads aggregate-only JSON reports
does not upload raw source rows, archives, Parquet files, or databases
does not approve Silver/Gold replacement
formal stake remains 0
```

First file to inspect:

```text
eoin_cross_source_audit_report.json
```

Possible outcomes:

```text
ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE
SECONDARY_SOURCE_REJECTED
```

`ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE` remains role-limited because
`shufinskiy/nba_data` is not a complete independent player boxscore stat
reference.

### 3. Eoin Adapter Predeclaration

```text
Actions -> Validate Eoin adapter predeclaration v1 -> Run workflow
```

What it does:

```text
automatically runs on main pushes that touch the Eoin adapter policy surface
validates data/eoin-adapter-predeclaration-v1.json
requires the completed cross-source evidence file
allows only role-limited adapter implementation
does not execute the adapter
does not read raw Eoin rows
does not approve Silver/Gold replacement
does not unlock model retraining or market backtest
formal stake remains 0
```

Passing state:

```text
ROLE_LIMITED_ADAPTER_READY_FOR_IMPLEMENTATION
```

### 4. Eoin Role-limited Adapter Self-test

```text
Actions -> Validate Eoin role-limited adapter v1 -> Run workflow
```

What it does:

```text
automatically runs on main pushes that touch the Eoin adapter self-test surface
runs only synthetic fixtures
validates deterministic gameId normalization
validates team score and player candidate coverage aggregates
validates PBP Parquet metadata path in CI
uploads aggregate-only self-test reports
does not execute against the full Eoin bundle
does not approve Silver/Gold replacement
does not unlock model retraining or market backtest
formal stake remains 0
```

Passing state:

```text
ROLE_LIMITED_ADAPTER_SELF_TEST_PASS
```

### 5. NBA Free Data Refresh

```text
Actions -> Update NBA free data -> Run workflow
```

What it does:

```text
refreshes current schedule / source health
uses public no-key endpoints and fallbacks
commits only data/current snapshots when changed
does not create model predictions
does not unlock market backtest
```

### 6. Model and UI Validation

```text
Actions -> Validate model registry -> Run workflow
```

What it does:

```text
validates active model registry
tests G1.1 multi-main policy
checks V5 UI module limits
checks JavaScript syntax
```

### 7. Closing Market Benchmark

```text
Actions -> Build Kaggle closing market benchmark -> Run workflow
```

What it does:

```text
downloads an approved closing-label Kaggle odds source
compares model probability quality against closing market
uploads reports only
does not compute ROI or CLV
does not prove executable betting edge
```

This is useful, but it is not a point-in-time odds backtest.

## Optional API Secrets

### GitHub Website Launcher

The static GitHub Pages site cannot safely store a permanent GitHub token.

Allowed:

```text
paste a short-lived fine-grained token into the website launcher
limit token access to qoo109/nba-value-lab
grant Actions read/write only
delete or rotate the token when finished
```

Blocked:

```text
hard-code a GitHub token in JavaScript
commit a token to the repository
store a shared personal token in GitHub Pages
make unauthenticated public buttons that run workflows
```

### Kaggle

Use only as a GitHub repository secret:

```text
KAGGLE_API_TOKEN
```

Never commit `kaggle.json`, usernames, keys, downloaded archives, or extracted
raw files.

### The Odds API

The free tier can be used only for current or upcoming NBA moneyline snapshots.
It is not enough for historical PIT odds.

Allowed:

```text
live/current h2h moneyline smoke tests
request quota and schema checks
manual comparison with user-observed prices
```

Blocked:

```text
historical odds backfill
CLV
ROI
drawdown
betting decision layer
```

Historical odds remain blocked unless a lawful paid source is explicitly
approved or the user supplies a timestamped odds file with provenance.

## Artifact Policy

Allowed artifacts:

```text
aggregate_schema_report.json
aggregate_coverage_report.json
privacy_safe_schema_sample.json
download-inventory-report.json
internal_qualification_report.json
run-status.json
summary metrics
hashes and file sizes
```

Disallowed artifacts:

```text
raw CSV rows
full SQLite / DuckDB databases
Kaggle archives
raw player rows
raw play-by-play rows
bookmaker quote-level rows before PIT policy approval
API secrets
```

## Current Priority

1. Keep the completed Eoin census and cross-source reports as aggregate-only evidence.
2. Treat Eoin as `ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE`.
3. Validate `Eoin Adapter Predeclaration v1`.
4. Run `Validate Eoin role-limited adapter v1`.
5. Inspect the aggregate-only CI artifact before any full adapter execution preflight.
6. Keep player-stat parity out of scope until an independent player boxscore reference exists.
7. Keep Wyatt blocked unless a materially new dataset bundle appears.
