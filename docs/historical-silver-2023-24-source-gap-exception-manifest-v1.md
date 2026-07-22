# Historical Silver 2023-24 Source Gap Exception Manifest v1

更新日期：2026-07-22  
Repository：`qoo109/nba-value-lab`  
正式 Stake：`0`

## 目的

本 manifest 落實 source archive reconciliation design 的 documented-exception lane。

一次性 reconciliation 已正式確認：

```text
SOURCE_ARCHIVE_GAP_STABLE
nbastats_game_present_pbpstats_game_absent = 2
```

這兩場比賽的 Silver game rows 存在，但 PBP Stats archive 沒有相應比賽覆蓋，因此無法產生 possession-derived team features。這是穩定的上游 archive coverage gap，不是 Silver builder、Gold builder 或 game identity 缺陷。

## Aggregate scope

```text
2023-24 Silver games: 1,230
games with two team-feature rows: 1,228
source-gap exception games: 2
unclassified games: 0

nbastats games: 1,230
pbpstats games: 1,228
overlap games: 1,228
nbastats only: 2
pbpstats only: 0
```

本公開 manifest 只保存 aggregate counts，不保存或輸出個別 game IDs、日期、隊伍代碼、source paths、source hashes 或逐列資料。

## Exception class

```text
exception_code:
SOURCE_ARCHIVE_PBPSTATS_GAME_ABSENT

handling_mode:
DOCUMENTED_AGGREGATE_ONLY_NO_ROW_PATCH
```

正式處理方式：

- 保留既有 Silver game rows；
- 不刪除比賽；
- 不合成、複製、補零或人工插入 team features；
- 不修改 Silver builder；
- 不以 secondary source 覆蓋正式 Silver／Gold；
- 不將兩場例外強制加入 Gold、模型或市場回測；
- runtime 可依既有 aggregate-confirmed 條件辨識例外，但不得把識別資訊持久化到公開 repo 或 Artifact。

## Fail-closed eligibility

對 source-gap exception games：

```text
Silver game identity retained: true
possession-derived team features available: false
Gold matchup eligible without new valid source rows: false
model training eligible: false
model evaluation eligible: false
market backtest reference eligible: false
manual override eligible: false
```

這份 manifest 只把已驗證的上游缺口正式文件化。它不會把缺失資料變成有效特徵，也不會解鎖任何 downstream research claim。

## Public evidence boundary

禁止公開：

- game IDs；
- 比賽日期；
- 主客隊或隊伍代碼；
- source file paths／hashes；
- raw rows／raw files；
- row-level records；
- row-key hashes。

公開輸出仍限制為不超過 `1 MiB` 的 aggregate-only evidence。

## 未授權事項

本 manifest 不授權：

- source archive reconciliation 重跑；
- Silver builder changes；
- source-gap row patch；
- Gold rebuild；
- Historical Silver／Gold replacement；
- cross-source audit rerun；
- Chris Munch 或 Eoin 資料執行；
- model retraining；
- point-in-time market backtest；
- CLV、EV、ROI、Drawdown；
- betting-edge claim；
- Stake 高於 `0`。

## 下一步

manifest 驗證通過後，下一個可設計節點是：

```text
HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_POLICY_READY_FOR_DESIGN
```

該 integration policy 只能規定現有 QA／coverage validator 如何接受並報告已文件化的 aggregate exception。它仍不得建立缺失 team features、修改 Silver／Gold，或直接重跑 cross-source audit。
