# User-supplied NBA Betting CSV Provenance Confirmation v1

更新日期：2026-07-21（Asia/Taipei）

## Confirmation

Repository owner explicitly confirmed that the supplied local file:

```text
nba_2008-2026.csv
```

came from:

```text
https://www.kaggle.com/datasets/cviaxmiwnptr/nba-betting-data-october-2007-to-june-2024
```

Dataset handle:

```text
cviaxmiwnptr/nba-betting-data-october-2007-to-june-2024
```

The confirmation applies to the exact file identity already audited in PR #95:

```text
bytes: 2,493,308
sha256: 729eb2ead85c14affbb81ae9a4c611fee9790b8dd3d1d7824e1ddba14410a8c4
rows: 24,440
columns: 27
date range: 2007-10-30 through 2026-06-13
season labels: 2008 through 2026
```

## Provenance Resolution

The immutable file-level audit was originally recorded as:

```text
ROLE_LIMITED_LEGACY_MARKET_ARCHIVE_ELIGIBLE_PROVENANCE_PENDING
```

The separate confirmation record now resolves only the provenance gate. The current formal source outcome becomes:

```text
ROLE_LIMITED_LEGACY_MARKET_ARCHIVE_ELIGIBLE
```

Evidence record:

```text
data/research/user-supplied-nba-betting-csv-provenance-confirmation-v1.json
```

The original aggregate audit remains preserved as the evidence captured before user confirmation:

```text
data/research/user-supplied-nba-betting-csv-audit-v1.json
```

## Allowed Role

The confirmed source may support:

- deterministic game identity cross-check;
- final score cross-check;
- spread and total descriptive research;
- a moneyline forecast benchmark pilot using complete paired moneylines;
- a separately predeclared deterministic overlap audit against verified Historical Gold.

## What Confirmation Does Not Establish

Source confirmation does not create missing market semantics. The file still has no verified:

```text
bookmaker
observed_at
opening_at
closing_at
same-book opening-to-closing history
```

Therefore confirmation does not permit:

- calling the lines Opening or Closing;
- point-in-time odds joins;
- T-60m or T-5m entry backtests;
- CLV, entry-price ROI, or Drawdown claims;
- betting-edge claims;
- Historical Silver or Gold replacement;
- model retraining;
- non-zero Stake.

## Data Boundary

```text
raw CSV committed: false
raw rows emitted: 0
raw file Artifact allowed: false
formal Stake: 0
```

## Exact Next Step

Create a separate predeclaration for a deterministic cross-source audit:

```text
reference: verified Historical Gold
scope: seasons overlapping Historical Gold only
join key: game_date + home_team + away_team
score: validation field only
fuzzy matching: false
raw CSV committed: false
Silver replacement: false
Gold replacement: false
model retraining: false
market backtest: false
formal Stake: 0
```

No derived-data promotion is allowed before that audit is implemented, validated, reviewed, and merged.
