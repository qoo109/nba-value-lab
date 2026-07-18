# Timestamped Odds Qualification Adapter v1

更新日期：2026-07-18  
Roadmap：Step 5  
狀態：**Offline implementation / ACCESS_NOT_PROVIDED**

## Scope

本模組實作 PR #57 已合併的取得契約，但不執行付費 API。

```text
scripts/qualify_timestamped_odds_v1.py
scripts/run_timestamped_odds_qualification_v1.py
```

`qualify_timestamped_odds_v1.py` 提供基礎 manifest／payload utility；`run_timestamped_odds_qualification_v1.py` 是正式 hardened validation runner。

目前能力：

1. 依 frozen 30-game sample 與 exact schedule rows 建立無價格 request manifest。
2. 解析已提供的 The Odds API Historical v4 response payload。
3. 使用 deterministic NBA aliases，要求 home、away、scheduled tip-off 三者完全一致。
4. 驗證 provider snapshot `<= requested_at` 與 frozen maximum lag。
5. 驗證 bookmaker `last_update <= provider_snapshot < tipoff`。
6. 分開保存 provider snapshot、bookmaker last-update 與 fetched-at。
7. 只解析同 bookmaker、同 snapshot、唯一 h2h market 的兩側價格。
8. 驗證 decimal price、two-way overround、duplicate keys、quota provenance 與 PIT。
9. 按 coverage-only 規則彙總 bookmaker qualification。
10. 在沒有付費核准與 secret 時輸出 `ACCESS_NOT_PROVIDED`。

## Explicit non-capabilities

本 PR 沒有 HTTP client，也不會：

- 讀取 `THE_ODDS_API_KEY`
- 呼叫 The Odds API
- 建立帳號、訂閱或購買 credits
- 產生 API quota 或費用
- 下載真實 quote
- 計算 model edge、EV、ROI、CLV、Drawdown 或 model-vs-market score
- 寫入 public quote-level Artifact

## Frozen policy

正式 Source of Truth：

```text
data/timestamped-odds-acquisition-v1.json
PR #57
merge: 926fd8355602935f51a5fe38f82ba2fa37c825fb
```

本 PR 不修改：

```text
source
30-game sample
market / region
snapshot labels
1,800-credit ceiling
bookmaker ranking
decision states
storage boundary
```

## Request manifest

Manifest builder 需要 frozen sample 對應的 schedule rows：

```text
historical_game_id
game_date
away_team_abbr
home_team_abbr
scheduled_tipoff_utc
```

每場固定產生：

```text
T-6h
T-3h
T-1h
T-30m
T-5m
Closing = tip-off minus one second
```

Opening 不屬於 v1，也不得從 T-minus 或 provider first-seen 推定。

Manifest 必須：

```text
exactly 30 games
exactly 180 request rows
0 schedule duplicates
0 missing schedule games
0 game-date/team identity mismatch
estimated quota <= 1,800 credits
0 price fields
0 API key
```

Manifest 本身不等於 paid execution authorization。

## Historical payload parser

預期 Historical v4 payload：

```text
timestamp
previous_timestamp
next_timestamp
data[]
  id
  commence_time
  home_team
  away_team
  bookmakers[]
    key
    last_update
    markets[]
      key = h2h
      outcomes[]
```

### Strict event identity

事件必須同時符合：

```text
exact normalized home team
exact normalized away team
exact scheduled_tipoff_utc
exactly one matching event
nonblank provider event id
```

以下狀態全部拒絕：

- 相同隊伍但不同 tip-off
- 主客顛倒
- 多個完全相同候選事件
- 無法辨識的 target identity
- fuzzy／nearest-time／nearest-date 配對

不能因 provider event 看起來「最接近」就手動選擇。

## Point-in-time checks

```text
provider_snapshot_at <= requested_at < scheduled_tipoff
bookmaker_last_update <= provider_snapshot_at
bookmaker_last_update < scheduled_tipoff
```

最大 provider lag：

```text
requested_at before 2022-09-01: 15 minutes
requested_at from 2022-09-01: 10 minutes
```

Future snapshot 永遠拒絕。`fetched_at` 不得替代 `observed_at`。

## Quote normalization

每個 bookmaker 只接受：

- nonblank stable key;
- unique bookmaker block per event;
- valid pre-snapshot `last_update`;
- exactly one `h2h` market;
- exactly home and away outcomes;
- no duplicate or unknown outcome;
- finite decimal prices;
- frozen price and overround ranges.

Temporary normalized rows只允許存在於受限 temporary storage，正式 Artifact 前必須刪除。

## Qualification aggregation

Source-level structural blockers：

- manifest／source-index 不完整或重複;
- HTTP success 未達 100%;
- unresolved 401／403／429;
- mapping 或 per-season mapping 未達 gate;
- future snapshot／PIT／tip-off／team／ambiguous／fuzzy error;
- duplicate quote key;
- inferred Opening;
- missing request hash or quota header;
- total quota above 1,800.

Bookmaker qualification仍完全依 frozen coverage ranking：

```text
complete T-1h + Closing count desc
all-target coverage desc
minimum per-season complete count desc
bookmaker key asc
```

Abnormal quote gate 只套用於 candidate selected bookmaker。非候選 bookmaker 的異常不會把另一個完整、合法、符合 coverage gate 的 bookmaker 一起判為 source-level blocked。

ROI、model edge、價格高低或賽果不得參與排序。

## Synthetic validation

兩層 self-tests 固定驗證：

```text
180 no-price manifest rows
estimated quota = 1,800
Opening labels = 0
valid Lakers @ Nuggets parse
exact scheduled tip-off identity
wrong tip-off rejected
future provider snapshot rejected
ambiguous event rejected
bookmaker update after provider snapshot rejected
same-book two-sided h2h retained
coverage-only stable-key tie-break
nonselected abnormal bookmaker does not block a qualified bookmaker
global PIT violation blocks qualification
quota headers required
```

Synthetic price 只在 process memory 中測試 parser，公開 Artifact 不保存 quote rows 或價格。

## Aggregate-only Artifact

允許上傳：

- policy validation report;
- base synthetic self-test summary;
- hardened self-test summary;
- `ACCESS_NOT_PROVIDED` report.

禁止上傳：

```text
API key
raw provider response
request manifest CSV
normalized quote rows
real or synthetic prices
downloadable odds archive
market performance metrics
```

## Current formal state

```text
ACCESS_NOT_PROVIDED
network requests made = 0
API key read = false
paid endpoint called = false
real quotes downloaded = 0
subscription or purchase created = false
market metrics calculated = false
quote-level rows retained = 0
ready_for_paid_qualification_execution = false
ready_for_production_manifest = false
ready_for_production_backfill = false
ready_for_market_backtest = false
ready_for_clv_ev_roi = false
ready_for_betting_edge_claim = false
formal_stake = 0
```

## Next exact task after merge

```text
obtain authoritative exact scheduled tipoffs for the frozen 30 games without paid odds calls
→ build and freeze the 180-row no-price request manifest
→ verify exact quota ceiling = 1,800 credits
→ read structural manifest QA
→ stop before network execution
```

只有使用者另行明確核准付費 access，並以 private secret 連接 `THE_ODDS_API_KEY` 後，才可執行 frozen qualification pilot。
