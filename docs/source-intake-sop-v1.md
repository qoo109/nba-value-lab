# Source Intake SOP v1

## Purpose

Keep historical data-source pilots consistent while the project remains a
research candidate. Every incoming source must be measured before it can support
cross-source validation, market backtests, or any betting decision layer.

Formal stake remains `0`.

## Intake Classes

### Class A: Local User-Supplied File

Examples:

```text
SQLite / DuckDB bundle
CSV folder
ZIP archive containing source files
```

Required intake checks:

```text
source URL or provenance note
retrieved_at if known
file inventory
content length / size bytes
SHA-256 for each accepted file
safe extraction result when zipped
schema or column inventory
row counts
date or season coverage
duplicate key groups
null key counts
raw rows emitted = 0
```

### Class B: Metadata-Only Candidate

Metadata is enough to justify a later pilot, but never enough to qualify a
source. Page descriptions, table catalogs, and marketing copy must be treated as
claims until the actual files are inspected.

### Class C: Rejected or Blocked Candidate

A candidate is blocked when the actual file contents fail the frozen contract.
Do not keep retrying the same file unless the user supplies materially new
content.

## Current Source Queue

```text
1. Wyatt Walsh SQLite/DuckDB      STRUCTURAL_BLOCKED
2. Eoin A Moore file bundle       INTERNAL_QUALIFICATION_READY
3. Market point-in-time odds      PAUSED_UNTIL_LAWFUL_SOURCE_OR_USER_FILE
```

## Wyatt Boundary

Do not rerun the same Wyatt files:

```text
nba.sqlite: 16 tables, latest game date 2023-06-12
nba.duckdb: 12 KB empty shell
2023-24 pilot games: 0
player game boxscore table: missing
```

A Wyatt audit may only reopen if a materially new bundle contains the advertised
current schema and season coverage.

## Eoin Next Step

Observed local files:

```text
Games.csv
LeagueSchedule24_25.csv
LeagueSchedule25_26.csv
PlayerStatistics.csv
PlayerStatisticsExtended.csv
Players.csv
PlayByPlay.parquet
TeamStatistics.csv
TeamHistories.csv
TeamStatisticsExtended.csv
```

GitHub website execution:

```text
Actions -> Run Eoin Kaggle CSV census v1 -> Run workflow
```

This downloads the selected Kaggle dataset into Actions temporary storage and
uploads only aggregate reports plus an internal qualification report. If Kaggle
requires authentication, use the repository secret `KAGGLE_API_TOKEN`.

Run:

```bash
python3 scripts/run_eoin_csv_census_v1.py \
  --input-dir /path/to/eoin-folder \
  --output-dir out/eoin-csv-census-v1

python3 scripts/run_eoin_internal_qualification_v1.py \
  --input-dir /path/to/eoin-folder \
  --output-dir out/eoin-internal-qualification-v1
```

The internal qualification pass still does not replace Silver or Gold. If it
passes, the next step is a separate 2023-24 deterministic cross-source audit.

## Frozen Gates

```text
pilot season: 2023-24
reference games >= 1,000
game identity match rate >= 98%
final score match rate >= 98%
team boxscore coverage >= 98%
player boxscore coverage >= 95%
PBP game coverage >= 95% when claimed
exact duplicate games = 0
fuzzy matching = false
existing Silver replacement = false
existing Gold replacement = false
formal stake = 0
```

## Output Policy

Allowed:

```text
aggregate reports
privacy-safe schema samples
counts, hashes, date ranges, duplicate counts
```

Not allowed:

```text
raw archives committed to Git
extracted raw rows committed to Git
full databases committed to Git
raw player or PBP rows in artifacts
market, CLV, ROI, or stake claims before PIT odds join
```
