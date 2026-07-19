# Eoin Role-limited Adapter v1

更新日期：2026-07-19

## Purpose

Implement the first adapter step allowed by Eoin Adapter Predeclaration v1:
an offline synthetic-fixture self-test for role-limited secondary-source
mapping.

This step does not execute against the full Eoin Kaggle bundle.

Formal stake remains `0`.

## Inputs

The self-test creates temporary fixture files only:

```text
Games.csv
TeamStatistics.csv
PlayerStatistics.csv
PlayByPlay.parquet when pyarrow is available
```

The adapter validates:

```text
deterministic gameId normalization
game duplicate detection
team boxscore coverage
team score consistency
player boxscore candidate coverage
PBP game coverage by Parquet metadata when available
policy guardrails from data/eoin-adapter-predeclaration-v1.json
```

## Outputs

Aggregate-only artifacts:

```text
eoin-role-limited-secondary-adapter-v1-report.json
eoin-role-limited-secondary-adapter-v1-status.json
```

The report may contain counts, rates, gate results and policy status. It must
not contain raw rows, raw game lists, raw player rows, raw PBP rows, full CSVs,
Parquet files, SQLite files or DuckDB files.

## Explicit Boundary

```text
full Eoin bundle execution: false
raw Eoin rows read: false
raw rows emitted: 0
raw files emitted: false
Historical Silver replacement: false
Historical Gold replacement: false
model retraining: false
market metrics: false
betting decision layer: false
formal stake: 0
```

Player boxscore remains coverage-only. Player-stat parity still requires a
separate independent player boxscore reference and a separate predeclared audit.

## Local Command

Local self-test without Parquet dependency:

```bash
python3 scripts/run_eoin_role_limited_adapter_v1.py \
  --self-test \
  --output-dir out/eoin-role-limited-adapter-v1
```

CI self-test with Parquet fixture:

```bash
python3 scripts/run_eoin_role_limited_adapter_v1.py \
  --self-test \
  --require-parquet-fixture \
  --output-dir out/eoin-role-limited-adapter-v1
```

## GitHub Actions

```text
Actions -> Validate Eoin role-limited adapter v1
```

Passing state:

```text
ROLE_LIMITED_ADAPTER_SELF_TEST_PASS
```

That state still does not authorize full adapter execution, Silver/Gold
replacement, model retraining, market backtest, betting claims or nonzero stake.
