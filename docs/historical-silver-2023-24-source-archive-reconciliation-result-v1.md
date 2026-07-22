# Historical Silver 2023-24 Source Archive Reconciliation Result v1

更新日期：2026-07-22  
Repository：`qoo109/nba-value-lab`  
正式 Stake：`0`

## 正式結果

一次性、aggregate-only 的 Shufinskiy source archive reconciliation 已成功執行。

```text
request_id:
HISTORICAL-SILVER-2023-24-SOURCE-ARCHIVE-RECONCILIATION-2026-07-22-001

workflow run:
29901869841

artifact:
8522225397

artifact digest:
sha256:2b42dca052d331bf94e31568b24492092beb00fef352405601fd812a8603b334

formal state:
HISTORICAL_SILVER_2023_24_SOURCE_ARCHIVE_RECONCILIATION_AGGREGATE_VALIDATION_PASS

decision:
SOURCE_ARCHIVE_GAP_STABLE
```

## Aggregate coverage

```text
nbastats_2023 games: 1,230
pbpstats_2023 games: 1,228
overlap games: 1,228
nbastats only: 2
pbpstats only: 0
union games: 1,230
```

正式缺口分類：

```text
nbastats_game_present_pbpstats_game_absent = 2
```

因此，兩場沒有 possession-derived team features 的比賽是穩定的上游 archive coverage gap，不是 Silver builder 或 Gold builder 遺漏。

## Possession grouping QA

```text
possession_base:
  groups = 242,363
  inconsistent = 2
  usable = false

possession_with_score_context:
  groups = 242,364
  inconsistent = 1
  usable = false

possession_with_score_and_start_type:
  groups = 242,365
  inconsistent = 0
  usable = true
```

現行 `possession_with_score_and_start_type` normalization grouping 維持有效，不應替換成較簡化的 grouping。

## Execution receipt

```text
execution_count: 1 / 1
request_consumed: true
repeat_execution_allowed: false
network_download_performed: true
temporary_material_deleted_with_runner: true
```

這個 request 已消耗，不得重跑。

## 未解鎖事項

本結果不授權：

- Silver builder 修改或人工補列；
- Historical Silver／Gold replacement；
- Gold rebuild；
- cross-source audit rerun；
- Chris Munch 或 Eoin 資料執行；
- point-in-time market backtest；
- CLV、EV、ROI、Drawdown；
- 模型重訓或 betting-edge claim；
- Stake 高於 `0`。

## 下一步

依既有 reconciliation design 的 documented-exception lane，下一步是預先設計一份 source-gap exception manifest。該 manifest 必須保持 privacy-safe，不公開 game IDs、日期、隊伍代碼或逐列資料；在新 manifest 通過獨立驗證前，仍不得修改 Silver／Gold。
