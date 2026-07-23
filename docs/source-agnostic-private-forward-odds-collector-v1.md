# Source-Agnostic Private Forward Odds Collector v1

更新日期：2026-07-24  
狀態：**Design validated / Offline implementation not started**  
Formal state：`SOURCE_AGNOSTIC_PRIVATE_FORWARD_ODDS_COLLECTOR_DESIGN_VALIDATED`  
Formal Stake：`0`

## 目的

目前 Historical Gold 已完成治理與語意凍結，但仍缺少合法、可稽核、bookmaker-level、具有可靠時間語意的真實盤口資料。BloomBet schema probe 已由使用者暫緩；HoopsAPI 免費層只能作為 forward-only 候選，不能回填既有歷史資料。

本設計建立一個**不綁定特定供應商、私人保存、只向前收集**的盤口收集契約。這一步只定義資料邊界、時間戳語意、Schema、去重、映射、儲存與 Artifact 規則，不建立帳號、不連接金鑰、不呼叫 API，也不保存真實盤口。

正式 machine-readable design：

```text
data/research/source-agnostic-private-forward-odds-collector-design-v1.json
```

Canonical private quote schema：

```text
schemas/private-forward-odds-quote-v1.schema.json
```

## 與既有層的關係

既有 `Point-in-time Odds Layer v1` 已定義研究端需要的 canonical 欄位，包括：

```text
game_id
commence_time_utc
observed_at_utc
bookmaker
market_key
snapshot_label
home_price_decimal
away_price_decimal
```

新的 collector 不取代該層。它只負責在私人儲存中累積可追溯的 forward observations。只有通過來源時間語意、事件映射與 point-in-time gate 的資料，之後才可轉換成既有 layer 所需的 canonical CSV。

## v1 範圍

```text
Sport: Basketball
League: NBA
Market: h2h / Moneyline
Odds format: Decimal
Direction: Forward only
Storage: Private only
Historical backfill: false
Opening inference: false
Market backtest: false
```

Spread、Total 與其他聯盟不屬於 v1。它們沒有對應目前 frozen baseline 的正式 estimand，也會擴大來源權利與資料品質風險。

## 四層架構

### 1. Target-time manifest

排程器只接受預先建立的目標時間清單，例如未來可能使用的 `T-60m`、`T-5m` 或 Closing target。這份設計不預設固定輪詢頻率，也不啟用 scheduler。

### 2. Provider adapter

每個供應商 adapter 只負責：

- 讀取該來源的 payload；
- 映射 event、bookmaker、market、prices 與來源時間欄位；
- 產生 canonical private quote record；
- 不推測缺失欄位；
- 不把 collector fetch time 偽裝成 provider observation time。

### 3. Private append-only store

建議預設位置：

```text
var/private/odds/forward-odds.sqlite
```

Repo 的 `.gitignore` 已排除 SQLite 類型檔案。Normalized quote rows、可能的 raw payload 與 quote prices 都只能存在私人儲存，不得放進 public repository 或 public Actions Artifact。

### 4. Qualification and export layer

之後獨立判斷：

- source rights 是否允許私人保存；
- provider timestamp 語意是否已文件化；
- event 是否 exact mapping；
- quote 是否嚴格在 tipoff 之前；
- 是否可轉成 point-in-time layer。

Collector 本身不能解鎖 Market Backtest。

## Timestamp contract

這是本設計最重要的治理邊界。

### `collector_fetched_at_utc`

必填，表示 NBA Value Lab 何時收到 payload。它只能證明收集時間。

```text
collector_fetched_at_utc ≠ provider observed_at
collector_fetched_at_utc NEVER substitutes quote_observed_at_utc
```

它永遠不能代替 `quote_observed_at_utc`。

### `provider_snapshot_at_utc`

可選。只有供應商明確文件化該欄位代表整體 snapshot 時間，並通過 source-specific qualification 後，才可成為 canonical observed time。

### `bookmaker_last_update_utc`

可選。只有供應商明確文件化該欄位代表該 bookmaker quote 的最後更新時間，才可成為 canonical observed time。

### `quote_observed_at_utc`

可為 `null`。允許的 authority：

```text
provider_snapshot
bookmaker_last_update
unverified
```

`unverified` 狀態必須符合：

```text
quote_observed_at_utc = null
point_in_time_eligible = false
```

即使 collector 在開賽前抓到一筆盤口，也不能因此宣稱該盤口是在 fetch time 才形成或更新。

## Event mapping

資料進入私人 store 時，`canonical_game_id` 可以暫時為 `null`，但 mapping state 必須明確標記：

```text
unmapped
exact
quarantined
```

Exact mapping 同時要求：

1. 主隊 exact normalized identity；
2. 客隊 exact normalized identity；
3. scheduled tipoff 完全一致；
4. 只有一個 canonical game 候選。

禁止：

- fuzzy matching；
- nearest-date 或 nearest-time matching；
- 主客顛倒後自動修正；
- 推測 season；
- 推測 competition type。

只有 `mapping_state=exact` 才可能進入 point-in-time qualification。

## Quote contract

每筆 v1 quote 必須具有：

- stable `source_event_id`；
- stable `bookmaker_key`；
- exactly one `h2h` market；
- 同一 bookmaker 的 home 與 away 兩側價格；
- decimal odds 介於 `1.001` 與 `100.0`；
- scheduled tipoff；
- collector fetched time；
-明確 timestamp authority；
- deterministic row hash。

單邊 quote、混合兩家 bookmaker 的兩側價格、無 bookmaker key 或無 stable event id，全部 fail closed。

## Snapshot labels

Collector ingestion 不接受供應商自稱的 `Opening`、`T-60`、`T-5` 或 `Closing` 作為正式 snapshot label。

正式 label 必須在後續 qualification layer 中，依 predeclared target timestamp 從合格 rows 派生：

```text
eligible quote time <= target timestamp
```

不得使用 target 之後的 future quote，也不得用 Closing-only row 代替 T-60 或 T-5。

## Deduplication

Deterministic dedup key 包含：

```text
source_id
source_event_id
bookmaker_key
market_key
quote_time_authority
quote_observed_at_utc
collector_fetched_at_utc
home_price_decimal
away_price_decimal
```

相同 canonical key 的重複 row 不得靜默覆蓋。它必須計入 duplicate QA；append-only store 應保留 run provenance，但不得重複計算 coverage。

## Private storage boundary

### 可以私人保存

在 source rights 已審查的前提下：

- normalized quote records；
- collector run metadata；
- source response hash；
- event mapping state；
- quarantine reason；
- provider-specific adapter version。

### 預設不保存

```text
raw provider payload
```

Raw payload retention 必須逐來源確認 Terms、private retention 與安全政策。未知時預設 `false`。

### Public repository / Artifact 禁止

- API key、cookie 或 authorization header；
- raw provider payload；
- quote-level prices；
- quote-level event/team rows；
- 可下載 odds archive；
- model edge、EV、CLV、ROI、Drawdown；
- bet count 或 stake recommendation。

## Aggregate-only QA

Public Artifact 最多可包含：

- collector run count；
- request success/failure counts；
- source 與 adapter version；
- exact/unmapped/quarantined counts；
- timestamp authority counts；
- point-in-time eligible count；
- duplicate count；
- 不含價格的 coverage summary；
- response SHA-256。

## Fail-closed conditions

以下任一情況都不能成為 point-in-time eligible quote：

- source retention rights 未確認；
- stable source event identity 缺失；
- 主客隊或 scheduled tipoff 缺失／矛盾；
- bookmaker identity 缺失；
- 無法證明同 bookmaker 雙邊 h2h；
- decimal price 無效；
- provider timestamp 語意未驗證；
- observed time 在 tipoff 之後；
- fetched time 早於 provider-origin timestamp；
- duplicate canonical key；
- public output 將洩露 raw rows 或 prices。

## 本設計沒有授權的事項

```text
Account creation: false
Provider terms acceptance: false
API key connection: false
HTTP client: false
Network requests: false
Scheduler activation: false
Real quote ingestion: false
Historical backfill: false
Market Backtest: false
Model retraining: false
CLV / EV / ROI: false
Betting claim: false
Formal Stake: 0
```

## 下一條唯一主線

```text
IMPLEMENT_SOURCE_AGNOSTIC_PRIVATE_FORWARD_ODDS_COLLECTOR_OFFLINE_CORE_V1
```

該步只能建立：

- synthetic adapter；
- schema validator；
- deterministic hash / dedup；
- temporary private SQLite write；
- quarantine 與 aggregate-only QA；
- synthetic mutation tests。

不得加入 HTTP client、secret reader、scheduler 啟用、真實 provider payload 或任何市場績效計算。
