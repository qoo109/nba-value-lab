# Timestamped Odds Qualification Adapter v1

更新日期：2026-07-18  
Roadmap：Step 5  
狀態：**Offline implementation / ACCESS_NOT_PROVIDED**

## Scope

本模組實作 PR #57 已合併的取得契約，但不執行付費 API：

```text
scripts/qualify_timestamped_odds_v1.py
```

目前能力：

1. 依 frozen 30-game sample 與外部 schedule 建立無價格 request manifest。
2. 解析已提供的 The Odds API Historical v4 response payload。
3. 使用 deterministic exact NBA team alias 對齊事件。
4. 驗證 provider snapshot `<= requested_at` 與最大 lag。
5. 分開保存 provider snapshot、bookmaker last_update 與 fetched_at。
6. 只解析同 bookmaker、同 snapshot 的 two-way h2h 價格。
7. 驗證 decimal price、two-way overround、duplicate key、future snapshot 與 tip-off identity。
8. 依 coverage-only 規則彙總 bookmaker qualification。
9. 在沒有付費核准與 secret 時輸出 `ACCESS_NOT_PROVIDED`。

## Explicit non-capabilities

本 PR 沒有 HTTP client，也不會：

- 讀取 `THE_ODDS_API_KEY`
- 呼叫 The Odds API
- 建立帳號或訂閱
- 產生任何 API quota 或費用
- 下載真實 quote
- 計算 model edge、EV、ROI、CLV 或 Drawdown
- 寫入 public quote-level Artifact

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

輸出只包含 request metadata，不包含 bookmaker 或價格。

Manifest 必須：

```text
exactly 30 games
exactly 180 request rows
0 schedule duplicates
0 missing schedule games
0 game-date/team identity mismatch
estimated quota <= 1,800 credits
```

## Historical payload parser

預期 payload 結構符合 Historical v4：

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

Parser 的 team mapping 重用既有 `import_closing_odds_archive.py` deterministic aliases；不使用 fuzzy matching。

事件只有在下列條件成立時才匹配：

```text
exact home team
exact away team
exactly one matching event
```

多個相同 matchup event 會被視為 ambiguous 並拒絕，不靠最近時間猜測。

## Point-in-time checks

```text
provider_snapshot_at <= requested_at < scheduled_tipoff
```

最大接受 lag：

```text
requested_at before 2022-09-01: 15 minutes
requested_at from 2022-09-01: 10 minutes
```

Future snapshot 永遠拒絕。`fetched_at` 不得代替 `observed_at`。

## Quote normalization

每個 bookmaker 只接受唯一一個 `h2h` market，且 outcomes 必須正好是該場 home/away 兩隊。

Temporary normalized row 包含：

```text
request_id
source_event_id
historical_game_id
snapshot_label
requested_at_utc
provider_snapshot_at_utc
scheduled_tipoff_utc
bookmaker_key
bookmaker_last_update_utc
market_key
home_team_abbr
away_team_abbr
home_price_decimal
away_price_decimal
two_way_overround
```

這些 quote rows 只允許存在於受限 temporary workflow storage，正式 Artifact 前必須刪除。

## Synthetic tests

Self-test 固定驗證：

- 正常 Lakers @ Nuggets payload 可以精確解析。
- 兩側價格由同 bookmaker／同 h2h market 取得。
- overround 計算正確。
- provider future snapshot 被拒絕。
- 同 matchup 出現兩個 event 時拒絕 ambiguous match。
- `ACCESS_NOT_PROVIDED` 狀態為 0 network、0 key、0 paid call、0 purchase。

Synthetic payload 不含任何真實 provider quote，亦不觸發網路。

## Qualification aggregation

Paid pilot 日後執行時，adapter 可彙總：

- request success
- mapped games and per-season counts
- snapshot lag / PIT errors
- bookmaker coverage
- T-60 + Closing completeness
- all-target-snapshot coverage
- quote validity and overround
- duplicates and team errors

Primary bookmaker 只依 coverage ranking：

```text
complete T-60 + Closing count desc
all-target coverage desc
minimum per-season complete count desc
bookmaker key asc
```

不讀模型預測，不以 ROI、edge 或價格高低選 bookmaker。

## Current formal state

```text
ACCESS_NOT_PROVIDED
network requests made = 0
API key read = false
paid endpoint called = false
quotes downloaded = 0
subscription or purchase created = false
market metrics calculated = false
ready_for_production_manifest = false
ready_for_production_backfill = false
ready_for_market_backtest = false
ready_for_clv_ev_roi = false
ready_for_betting_edge_claim = false
formal_stake = 0
```

## Next exact task after merge

```text
build the exact 30-game schedule manifest from Historical Gold without paid calls
→ calculate and freeze exact request timestamps and 1,800-credit ceiling
→ stop before network execution
→ request explicit user approval and THE_ODDS_API_KEY only when pilot is ready
```
