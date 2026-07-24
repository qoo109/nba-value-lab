# Kaggle Basketball-odds-history Local Inspection v1

更新日期：2026-07-24  
研究定位：Research Candidate / Pre-Market-Backtest  
Formal Stake：0

## Purpose

The Odds API free runtime path is deferred by user with no execution. The next no-cost path is a manual, local inspection of the Kaggle dataset:

```text
https://www.kaggle.com/datasets/zachht/wnba-odds-history
```

The public dataset page currently describes global, NBA, college and WNBA basketball odds, decimal/euro-style prices, a collection start of 2025-08-24 and scrape attempts every seven minutes. The dataset page carries a CC0 label and currently lists roughly 550 files.

These public claims are not sufficient to qualify the source. The exact NBA filenames, columns, timestamp meaning, bookmaker identity, upstream scrape source and upstream terms remain unverified.

## Milestone

```text
IMPLEMENT_KAGGLE_BASKETBALL_ODDS_HISTORY_LOCAL_INSPECTOR_V1
```

Added:

```text
scripts/inspect_kaggle_basketball_odds_history_archive_v1.py
```

The helper accepts a manually downloaded ZIP or extracted directory and emits aggregate-only schema/provenance readiness metadata.

## Safety boundaries

The downloaded archive and generated inspection JSON must remain outside the public repository until separately reviewed.

The inspector performs no:

- Kaggle login or API calls;
- network requests;
- credential reads;
- provider requests;
- quote-level public output;
- price output;
- formal history writes;
- Market Backtest, CLV, EV, ROI or Drawdown.

## What it inspects

For NBA-named CSV files only:

- filenames;
- file sizes and SHA-256 hashes;
- row counts;
- normalized column names;
- possible timestamp columns;
- possible bookmaker/provider columns;
- possible event/game columns;
- possible team columns;
- possible odds/price columns.

For a notebook, it records only filename, JSON validity, cell count and SHA-256.

The output never contains CSV rows or bookmaker prices.

## Local usage

After manually downloading the Kaggle ZIP to a private local folder:

```bash
python scripts/inspect_kaggle_basketball_odds_history_archive_v1.py \
  --source /private/path/basketball-odds-history.zip \
  --output /private/path/kaggle-local-inspection-v1.json
```

An extracted directory is also accepted.

## Interpretation

A result of:

```text
KAGGLE_BASKETBALL_ODDS_HISTORY_LOCAL_SCHEMA_CANDIDATE_FOUND
```

means only that at least one NBA CSV appears to contain timestamp, bookmaker, event, team and price-like columns.

It does **not** establish:

- that timestamps are true observation times;
- that bookmaker identities are stable or real;
- that both sides come from the same bookmaker snapshot;
- that upstream scraping rights are compatible with private research;
- that game mapping is exact;
- that the source is point-in-time qualified;
- that historical backfill or G1.2.0 is authorized.

## Qualification gates after a real archive is inspected

1. Identify exact NBA filenames and schema.
2. Determine whether timestamp columns represent scrape observation time, provider update time or later export time.
3. Confirm explicit bookmaker identity and same-book two-sided h2h prices.
4. Inspect notebook/source code for upstream source and collection behavior.
5. Review upstream terms independently from the Kaggle CC0 label.
6. Confirm deterministic game/team mapping.
7. Keep raw data private and emit only aggregate QA.

## Current state

```text
manual archive downloaded: false
real archive inspected: false
schema candidate found: false
timestamp semantics verified: false
bookmaker identity semantics verified: false
upstream provenance verified: false
source rights verified: false
point-in-time qualified: false
historical backfill qualified: false
Market Backtest: false
Formal Stake: 0
```

## Next unique mainline

```text
AWAIT_MANUAL_KAGGLE_BASKETBALL_ODDS_HISTORY_ARCHIVE_FOR_LOCAL_INSPECTION
```
