# Eoin Full Adapter Runner Implementation v1

更新日期：2026-07-19

## Purpose

建立完整 Eoin bundle 的執行器邊界、輸入 allowlist、資源上限與
blocked-before-data-access 行為。

本階段只實作 runner admission／guardrail self-test，不執行完整 Eoin
bundle，不下載 Kaggle raw archive，也不讀真實 raw Eoin rows。

## Frozen Operational Limits

```text
runtime: 45 minutes
concurrency: 1
required files: Games.csv / TeamStatistics.csv / PlayerStatistics.csv / PlayByPlay.parquet
maximum input file count: 4
maximum total input bytes: 10 GiB
maximum single input file bytes: 8 GiB
maximum public output bytes: 10 MiB
maximum public artifact files: 6
```

這些是操作安全上限，不是研究 promotion gates。

## Current Switches

```text
full bundle execution: false
network download: false
dataset-root execution: false
automatic main-push execution: false
scheduled execution: false
explicit future user approval required: true
approval record required: true
```

## CI Self-test

Workflow：

```text
Validate Eoin full adapter runner implementation v1
```

CI 只會：

```text
rebuild aggregate-only upstream policy reports
create a tiny synthetic four-file inventory
validate filenames, sizes and SHA-256 generation
prove the non-self-test execution path blocks before data access
upload aggregate JSON reports only
```

## Passing State

```text
FULL_ADAPTER_RUNNER_READY_FOR_ONE_TIME_EXECUTION_APPROVAL_BUT_DISABLED
```

這代表可以再設計「一次性 execution request／approval record」，仍不代表
完整資料匯入已獲准。

## Still Forbidden

```text
raw rows or raw files in Artifact
Historical Silver / Gold replacement
player-stat parity or player feature import
model retraining
market backtest
CLV / EV / ROI / Drawdown
betting decision layer
formal stake above 0
```
