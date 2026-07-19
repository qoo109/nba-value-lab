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
2. Eoin A Moore file bundle       ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE
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

## Eoin Status and Next Step

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

The internal qualification pass does not replace Silver or Gold.

GitHub cross-source execution:

```text
Actions -> Run Eoin cross-source audit v1 -> Run workflow
```

This compares Eoin against the existing `shufinskiy/nba_data` 2023-24
event-level reference. It can produce a role-limited secondary-source outcome
for game identity, final score, team-score coverage, player-row availability,
and PBP availability. It still does not approve Historical Silver or Gold
replacement.

Latest completed cross-source result:

```text
workflow run: 29672984966
artifact id: 8437932113
formal outcome: ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE
reference games: 1,230
matched games: 1,230
final score match rate: 99.9187%
team boxscore coverage: 100%
PBP game coverage: 100%
player boxscore candidate coverage: 100% coverage-only
```

Next step:

```text
Validate Eoin adapter predeclaration before importing derived data.
Keep player-stat parity out of scope until an independent player boxscore
reference exists.
Keep existing Silver and Gold unchanged.
```

Adapter predeclaration:

```text
data/eoin-adapter-predeclaration-v1.json
docs/eoin-adapter-predeclaration-v1.md
scripts/validate_eoin_adapter_predeclaration_v1.py
```

Passing state:

```text
ROLE_LIMITED_ADAPTER_READY_FOR_IMPLEMENTATION
```

This state authorizes adapter implementation only. It does not authorize
adapter execution against the full Eoin bundle, raw-row artifacts, Silver/Gold
replacement, model retraining, market metrics or betting decisions.

Adapter self-test implementation:

```text
scripts/run_eoin_role_limited_adapter_v1.py
docs/eoin-role-limited-adapter-v1.md
.github/workflows/validate-eoin-role-limited-adapter-v1.yml
```

Passing state:

```text
ROLE_LIMITED_ADAPTER_SELF_TEST_PASS
```

The self-test is fixture-only. It does not execute against the full Eoin bundle,
does not read raw Eoin rows and does not permit public derived tables.

Full adapter execution preflight:

```text
data/eoin-full-adapter-preflight-v1.json
docs/eoin-full-adapter-execution-preflight-v1.md
scripts/validate_eoin_full_adapter_preflight_v1.py
.github/workflows/validate-eoin-full-adapter-preflight-v1.yml
```

Passing state:

```text
FULL_ADAPTER_EXECUTION_PREFLIGHT_READY_BUT_DISABLED
```

This confirms the execution boundary only. It still does not authorize direct
full Eoin bundle execution, raw-row artifacts, Silver/Gold replacement, model
retraining, market metrics or betting decisions.

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
