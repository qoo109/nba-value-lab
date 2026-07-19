# Eoin Full Adapter Execution Policy v1

更新日期：2026-07-19

## Purpose

預先宣告完整 Eoin bundle role-limited execution 的執行政策與安全邊界。

這仍是 **policy validation**，不是完整 bundle execution。它不下載或讀取真實 Eoin bundle、不輸出 raw rows、不替換 Silver／Gold、不重訓模型、不執行市場回測，正式 Stake 維持 `0`。

## Required Upstream State

必須先由 `Validate Eoin full adapter preflight v1` 產生正式狀態：

```text
FULL_ADAPTER_EXECUTION_PREFLIGHT_READY_BUT_DISABLED
```

並確認：

```text
checks_failed = 0
raw_rows_read = false
raw_rows_emitted = 0
raw_files_emitted = false
ready_for_full_adapter_execution_policy = true
ready_for_full_adapter_execution = false
formal_stake = 0
```

## Policy Scope

未來若另行實作 execution runner，只允許：

```text
Games.csv
TeamStatistics.csv
PlayerStatistics.csv
PlayByPlay.parquet
```

運行範圍只包含檔案 inventory、hash／size、schema／Parquet metadata、aggregate row counts、duplicate groups、deterministic game identity、final score、team boxscore、player candidate coverage-only 與 PBP game coverage。

## Runtime Boundaries

```text
full bundle execution enabled now: false
future explicit user approval required: true
separate implementation PR required: true
workflow_dispatch only when later enabled: true
automatic main-push execution: false
scheduled execution: false
concurrent execution: false
read-only source access: true
temporary Actions storage only: true
safe extract required: true
deterministic matching only: true
fuzzy matching: false
```

未來 implementation PR 之前，必須另外凍結檔案大小、解壓大小、timeout、磁碟空間與失敗清理門檻。

## Artifact Boundary

允許公開：

- aggregate JSON reports
- schema metadata
- row／duplicate counts
- coverage rates
- hashes and file sizes
- source health status

禁止公開：

- raw game／team／player／PBP rows
- derived game ID lists
- full CSV／Parquet
- SQLite／DuckDB
- downloaded archives

## Passing State

```text
FULL_ADAPTER_EXECUTION_POLICY_READY_FOR_IMPLEMENTATION_BUT_EXECUTION_DISABLED
```

這只表示下一步可以另外設計 execution runner implementation。它仍不授權完整 Eoin bundle execution、Silver／Gold replacement、player-stat parity、model retraining、market backtest、CLV／EV／ROI／Drawdown、betting edge 或非 0 Stake。
