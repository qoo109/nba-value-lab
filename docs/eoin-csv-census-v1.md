# Eoin File Census v1

## Purpose

Run an aggregate-only file-level census for the Eoin A Moore Kaggle dataset after
the user supplies the downloaded files locally.

The first stage is not a source qualification pass. It only measures file
inventory, CSV columns, CSV row counts, key nulls, duplicate key groups, role
candidates, and Parquet file-level inventory.

The second stage is an internal aggregate readiness audit. It checks whether
`Games.csv`, `TeamStatistics.csv`, and `PlayerStatistics.csv` are coherent
enough to move to a later cross-source audit. It still does not approve source
replacement, model metrics, market metrics, or stake.

## Expected local files

```text
PlayerStatistics.csv
PlayerStatisticsExtended.csv
TeamStatistics.csv
TeamStatisticsExtended.csv
Games.csv
LeagueSchedule24_25.csv
LeagueSchedule25_26.csv
Players.csv
TeamHistories.csv
PlayByPlay.parquet
```

The first qualification-relevant roles are limited to:

```text
game identity cross-check
team boxscore cross-check
player boxscore cross-check
PBP availability check
```

Advanced stats are included when CSV files exist. Play-by-play Parquet is
inventoried by size and hash first; decoding rows requires a Parquet-capable
runtime such as `pyarrow`, `duckdb`, or GitHub Actions dependency expansion.

## Local command

```bash
python3 scripts/run_eoin_csv_census_v1.py \
  --input-dir /path/to/eoin-folder \
  --output-dir out/eoin-csv-census-v1
```

## GitHub Actions command

Use this when the goal is to run from GitHub instead of a local Mac:

```text
NBA Value Lab website
→ 明日分析
→ GITHUB WEBSITE RUNNER
→ 啟動 Eoin census
```

The website runner needs a fine-grained GitHub token for `qoo109/nba-value-lab`
with Actions read/write permission. It sends one workflow dispatch request from
the browser and clears the token input after a successful dispatch.

Fallback from the GitHub website:

```text
Actions
→ Run Eoin Kaggle CSV census v1
→ Run workflow
```

Default input:

```text
dataset_handle: eoinamoore/historical-nba-data-and-player-box-scores
```

The workflow first runs synthetic self-tests, then downloads the Kaggle dataset
inside GitHub Actions temporary storage and calls:

```bash
python scripts/run_eoin_kaggle_census_v1.py \
  --dataset-handle "$DATASET_HANDLE" \
  --output-dir /tmp/nbavl-eoin-kaggle-census
```

If Kaggle rejects anonymous access, add a free repository secret:

```text
KAGGLE_API_TOKEN
```

Do not commit Kaggle tokens, downloaded archives, extracted CSV files, or full
databases to the repository.

## Outputs

```text
aggregate_schema_report.json
aggregate_coverage_report.json
privacy_safe_schema_sample.json
download-inventory-report.json
eoin-kaggle-run-status.json
internal_qualification_report.json
```

The runner emits no raw rows and does not commit or copy downloaded source data.

## Internal qualification report

Read this file first after the GitHub run completes:

```text
internal_qualification_report.json
```

Important fields:

```text
outcome
all_internal_gates_passed
gate_results
games.unique_games
games.date_min / games.date_max
team_statistics.game_coverage_rate
team_statistics.score_match_rate
player_statistics.game_coverage_rate
optional_reports.PlayByPlay.parquet
```

Possible internal outcomes:

```text
INTERNAL_READY_FOR_CROSS_SOURCE_AUDIT
INTERNAL_BLOCKED
```

`INTERNAL_READY_FOR_CROSS_SOURCE_AUDIT` means the files are internally coherent
enough for the next deterministic comparison against an independent source. It
does not mean this source can replace Historical Silver or Gold yet.

## Frozen downstream gates

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
formal stake = 0
```
