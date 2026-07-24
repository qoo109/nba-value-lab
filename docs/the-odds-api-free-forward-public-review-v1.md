# The Odds API Free Forward Public Review v1

更新日期：2026-07-24  
研究定位：Research Candidate / Pre-Market-Backtest  
Formal Stake：0

## Purpose

本里程碑審查 The Odds API 的免費 current-odds 方案是否值得成為 2026-27 NBA 正規賽的 forward-only T-60 候選來源。

它不重啟已拒絕的付費 Historical API 路線，不建立帳號、不接受條款、不讀取 API Key、不發送 provider request，也不保存真實 quote。

## Official public evidence

查驗來源：

- `https://the-odds-api.com/`
- `https://the-odds-api.com/liveapi/guides/v4/`
- `https://the-odds-api.com/terms-and-conditions.html`

截至本次審查，官方網站公開顯示：

- 免費 Starter 方案每月 500 credits；
- 免費方案包含 current odds，但不包含 Historical Odds；
- v4 current odds endpoint 支援 `basketball_nba`、`us` region、`h2h` 與 decimal odds；
- event response 含 `id`、`commence_time`、`home_team`、`away_team`；
- bookmaker response 含 `key` 與 `last_update`；
- h2h outcomes 可提供同一 bookmaker 的兩邊價格；
- Terms 支援網站、dashboard 與 analytical tools，但禁止把 raw data 重新包裝成獨立資料產品或 API；
- API Key 必須保持私人。

官方公開頁面沒有確認免費註冊是否完全不需要付款卡，因此該欄維持 `unverified`，不得自行推定。

## Formal decision

```text
PROMISING_ZERO_COST_FORWARD_CANDIDATE_REQUIRES_USER_TERMS_REVIEW_AND_CAPPED_RUNTIME_PREFLIGHT
```

理由：

1. 免費 current API 的 quota 足以研究低頻、單一 region、單一 market 的 T-60 forward snapshot。
2. 公開 schema 已出現明確 bookmaker identity、兩邊 h2h prices 與 bookmaker `last_update`。
3. Historical Odds 仍是付費功能，因此本來源不可補回過去 3,688 場 OOF 歷史。
4. `last_update` 的實際 runtime 欄位、涵義、NBA coverage 與 plan/card 條件仍須由使用者親自確認並做受限 preflight。

## Synthetic adapter shell

新增：

```text
scripts/the_odds_api_free_forward_adapter_v1.py
```

只處理 synthetic payload，沒有：

- HTTP client；
- secret reader；
- scheduler；
- account workflow；
- formal history writer；
- Market Backtest 或市場指標。

Adapter 只接受：

- `sport_key = basketball_nba`；
- 同一 bookmaker；
- `market.key = h2h`；
- exactly two outcomes；
- outcome team names 精確等於 home/away；
- decimal price > 1；
- provider-origin `market.last_update` 或 `bookmaker.last_update`。

`collector_fetched_at_utc` 永遠不能代替 bookmaker `last_update`。

Synthetic adapter 雖可輸出 `quote_time_authority=bookmaker_last_update`，但 source rights 仍是 `unreviewed`、mapping 仍是 `unmapped`，不代表 point-in-time qualification 已完成。

## Capped runtime preflight boundary

預先保留 request id：

```text
THE-ODDS-API-FREE-FORWARD-PREFLIGHT-2026-07-24-001
```

只有在使用者親自完成以下事項後，才能另行設計／執行：

1. 閱讀並接受 The Odds API Terms；
2. 確認免費方案不產生付費或付款卡義務；
3. 建立帳號並取得 API Key；
4. 將 Key 放入使用者控制的私人 secret store，不貼到聊天或 repo；
5. 明確批准上述 request id；
6. 等待 2026-27 NBA regular-season markets 實際存在。

最多兩個 provider requests：

1. `/v4/sports?all=true`：只確認 sport key 與 schema；
2. `/v4/sports/basketball_nba/odds?regions=us&markets=h2h&oddsFormat=decimal`：只在 NBA markets 已存在時執行一次。

Preflight 只可輸出 aggregate-only QA：欄位存在、bookmaker count、game count、timestamp presence、quota headers 與 hash。禁止公開 team、price、raw payload、API Key 或 quote rows。

## Current boundaries

```text
account created: false
API key connected: false
provider requests executed: 0
real quotes retained: 0
provider timestamp semantics runtime verified: false
point-in-time qualified: false
historical backfill eligible: false
Market Backtest: false
CLV / EV / ROI / Drawdown: false
Formal Stake: 0
```

## Next unique mainline

```text
AWAIT_USER_TERMS_REVIEW_AND_CAPPED_THE_ODDS_API_FREE_FORWARD_PREFLIGHT_APPROVAL
```

實際 forward collection 與歷史資料庫仍應放在 `qoo109/nba-odds-history-hub`；NBA Value Lab 只保存 provider qualification、schema、aggregate QA 與 intake contract，不成為公開 raw odds 來源。
