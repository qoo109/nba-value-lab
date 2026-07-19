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

### 2. NBA Free Data Refresh

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

### 3. Model and UI Validation

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

### 4. Closing Market Benchmark

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

1. Run `Run Eoin Kaggle CSV census v1`.
2. Review `internal_qualification_report.json`.
3. If internal gates pass and 2023-24 coverage looks viable, create a separate
   deterministic cross-source audit.
4. Keep Wyatt blocked unless a materially new dataset bundle appears.
