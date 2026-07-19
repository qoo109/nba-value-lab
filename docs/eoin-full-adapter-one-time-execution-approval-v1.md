# Eoin Full Adapter One-time Execution Approval v1

## Approval

The repository owner explicitly approved request:

```text
EOIN-FULL-ADAPTER-2026-07-19-001
```

Approval was given on 2026-07-19 in direct response to the frozen request scope.
The stored response is:

```text
好 我核准
```

The normalized authorization is one one-time aggregate-only Eoin full-adapter
validation run.

## What is authorized

- one manual `workflow_dispatch` run on `main`;
- temporary download of `eoinamoore/historical-nba-data-and-player-box-scores`;
- temporary reading of exactly:
  - `Games.csv`
  - `TeamStatistics.csv`
  - `PlayerStatistics.csv`
  - `PlayByPlay.parquet`
- 2023-24 aggregate row counts, duplicate groups, deterministic coverage, score
  agreement, file sizes, and hashes;
- one aggregate JSON Artifact retained for 14 days.

## What remains forbidden

- raw rows, raw files, downloaded archives, CSV, Parquet, SQLite, or DuckDB in
  public Artifacts;
- Historical Silver or Historical Gold replacement;
- player-stat parity claims or player feature import;
- model training or retraining;
- market backtest, CLV, EV, ROI, or Drawdown;
- betting edge claims or betting decision activation;
- non-zero Stake.

## Admission validation

The approval and executor self-test workflow is:

```text
Validate Eoin one-time execution approval v1
```

Expected state:

```text
ONE_TIME_EXECUTION_APPROVAL_VALID_READY_FOR_MANUAL_DISPATCH
```

The self-test uses synthetic temporary fixtures only and performs no Kaggle
network download.

## Approved execution workflow

The execution workflow is intentionally manual-only:

```text
Run approved Eoin full adapter once v1
```

Run it from:

```text
GitHub
→ Actions
→ Run approved Eoin full adapter once v1
→ Run workflow
→ Branch: main
→ request_id: EOIN-FULL-ADAPTER-2026-07-19-001
```

The workflow has no push, pull-request, or schedule trigger. It revalidates the
approval before network access, runs with concurrency 1 and a 45-minute limit,
and uploads only:

```text
eoin-full-adapter-one-time-execution-report.json
```

## Artifact review

Do not treat a green workflow alone as the research result. Download and inspect
the Artifact first.

Possible completed research states:

```text
ONE_TIME_FULL_ADAPTER_AGGREGATE_VALIDATION_PASS
ONE_TIME_FULL_ADAPTER_AGGREGATE_VALIDATION_RESEARCH_BLOCKED
```

Both states mean the approved execution completed. The second means one or more
frozen research gates did not pass; it is not a workflow infrastructure error.

Required boundary fields remain:

```text
raw_rows_emitted: 0
raw_files_emitted: false
historical_silver_replacement: false
historical_gold_replacement: false
model_training_or_retraining: false
market_backtest: false
betting_edge_claim: false
formal_stake: 0
```

After the Artifact is reviewed, record the workflow run ID, Artifact ID, digest,
formal state, and mark the request consumed before any future execution is
discussed.
