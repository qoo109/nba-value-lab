# Eoin One-time Full Adapter Execution Request v1

更新日期：2026-07-19

## Purpose

建立一次性完整 Eoin aggregate validation 的申請封包，但保持：

```text
approval_granted: false
execution_enabled: false
full bundle executions: 0
raw Eoin rows read: false
formal stake: 0
```

本文件不是執行授權，也不會自動下載或讀取 Eoin bundle。

## Upstream Evidence

```text
Preflight run: 29677698906
Preflight artifact: 8439486695

Execution policy run: 29677971194
Execution policy artifact: 8439578942

Runner implementation run: 29679274470
Runner implementation artifact: 8440008401
```

三份 Artifact 均為 aggregate-only，且已人工檢查正式狀態與 raw-output 邊界。

## Frozen Request

```text
request id: EOIN-FULL-ADAPTER-2026-07-19-001
one-time only: true
workflow-dispatch only: true
pilot season: 2023-24
runtime ceiling: 45 minutes
concurrency: 1
required inputs:
  Games.csv
  TeamStatistics.csv
  PlayerStatistics.csv
  PlayByPlay.parquet
```

## Passing State

```text
ONE_TIME_EXECUTION_REQUEST_VALID_AWAITING_EXPLICIT_USER_APPROVAL
```

這只代表申請封包結構完整，下一步必須由使用者明確核准。

## Approval Text Template

```text
I approve request EOIN-FULL-ADAPTER-2026-07-19-001 for one one-time
aggregate-only Eoin full-adapter validation run. This does not authorize
raw-row artifacts, Historical Silver or Gold replacement, model retraining,
market backtest, betting edge claims, or non-zero Stake. Formal Stake remains 0.
```

未收到等義的明確核准前，不可把 `approval_granted` 或 `execution_enabled`
改成 `true`。

## Permanent Boundaries

即使未來核准一次性執行，仍只允許 aggregate validation：

```text
raw rows / raw files / archives / databases in Artifact: false
Historical Silver replacement: false
Historical Gold replacement: false
player-stat parity claim: false
model retraining: false
market backtest: false
CLV / EV / ROI / Drawdown: false
formal stake: 0
```
