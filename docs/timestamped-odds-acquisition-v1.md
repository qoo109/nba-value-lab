# Real Timestamped Odds Acquisition v1 — Predeclaration

更新日期：2026-07-18  
Roadmap：Step 5  
執行狀態：**Policy only / Paid access not provided**

## Purpose

本階段不是重建 Odds schema，也不是直接開始 ROI 回測。現有 repo 已有：

- `data/templates/point-in-time-odds-template.csv`
- `scripts/build_point_in_time_odds.py`
- `docs/point-in-time-odds-layer-v1.md`
- `data/historical-odds-source-registry.json`
- Closing-only benchmark 與 proportional no-vig 邊界

真正缺少的是：

> 合法、可稽核、bookmaker-level、帶可靠 `observed_at` 的歷史 NBA Moneyline 報價資料。

## Upstream decision

```text
PR #56 — Injury Feature Walk-forward Holdout v1
Formal state: VALID_NEGATIVE_RESULT
Market research model path: frozen baseline-only
Injury candidate research-ready: false
```

因此後續市場資料不得把被拒絕的 injury candidate 重新放回模型路徑。

## Predeclaration lock

Machine-readable policy：

```text
data/timestamped-odds-acquisition-v1.json
predeclaration commit: 454ed78a800bfe5fec7a02a203721b196154f94a
```

這份政策在以下行為之前完成：

- 建立或使用付費 API key
- 購買任何方案
- 呼叫歷史 Odds endpoint
- 下載真實 quote
- 查看 bookmaker coverage
- 計算 model edge、EV、ROI、CLV 或 Drawdown

任何付費存取仍需要使用者另外明確同意。本 PR 不會自動建立帳號或購買方案。

## Candidate source

Primary qualification candidate：

```text
The Odds API Historical API v4
sport: basketball_nba
region: us
market: h2h
odds format: decimal
```

截至 2026-07-18 的官方文件查驗：

- Featured-market historical snapshots 自 2020-06-06 起提供。
- 2022 年 9 月以前約每 10 分鐘一個 snapshot，之後約每 5 分鐘。
- 指定歷史時間時，API 回傳「小於或等於 requested date 的最近 snapshot」。
- Historical endpoint 只在付費方案提供。
- 一個 region × 一個 market 的 historical request 成本為 10 credits。
- Terms 允許資料用於分析工具，但禁止把 raw data 重新包裝成獨立資料產品散布。

官方來源：

- `https://the-odds-api.com/liveapi/guides/v4/`
- `https://the-odds-api.com/historical-odds-data/`
- `https://the-odds-api.com/terms-and-conditions.html`
- `https://the-odds-api.com/`

正式使用前仍須重新檢查價格、Terms 與 account plan；本文件是工程使用邊界，不是法律意見。

## v1 market scope

```text
NBA
US region
h2h / moneyline only
decimal odds
all returned US-region bookmaker keys
```

Spread 與 Total 不屬於 v1，因為 frozen baseline 是勝負機率模型。擴張市場會增加付費 quota 且沒有對應的正式模型 estimand。

## Snapshot targets

```text
T-6h
T-3h
T-1h
T-30m
T-5m
Closing = query at scheduled tip-off minus one second
```

`observed_at` 固定使用 provider historical response 的 snapshot timestamp。`bookmaker_last_update` 另欄保存，不可拿 retrieval time 或推測時間代替。

### Opening boundary

The Odds API historical endpoint沒有明確宣告 bookmaker true opening。v1 因此：

```text
Opening required: false
T-6h may be called Opening: false
T-24h may be called Opening: false
Provider first-seen may be called true bookmaker opening: false
```

只有來源日後明確提供並可稽核的 opening 定義，才可另外預先宣告。

## Frozen qualification pilot

Pilot 只測 source、timestamp、bookmaker、coverage、quota 與 storage boundary，不看模型或投注結果。

```text
30 games
10 games per OOF season
2021-22 / 2022-23 / 2023-24
6 requested snapshots per game
maximum request slots: 180
maximum quota: 1,800 credits
```

30 場已在 machine-readable policy 固定。抽樣規則是每季依 `game_date, game_id` 排序後，使用 10 個等距索引；不得在看到來源 coverage 後換場。

### Pilot is allowed to report

- API request success/failure
- provider snapshot lag
- target-game mapping
- bookmaker/snapshot/season coverage
- two-sided price validity
- overround range
- quota headers and total credits
- duplicate/team/timestamp errors
- response SHA-256

### Pilot must not report

```text
model edge
expected value
ROI
CLV
drawdown
bet count
model-vs-market Log Loss or Brier
bookmaker ranking by profit
```

## Qualification gates

Access gates：

```text
explicit paid-access acknowledgement required
THE_ODDS_API_KEY secret required
no automatic purchase
quota <= 1,800 credits
HTTP request success = 100%
no unresolved 401 / 403 / 429
```

Source and mapping gates：

```text
target-game mapping >= 90%
at least 8 / 10 games mapped in every season
point-in-time violations = 0
future snapshots = 0
team mismatches = 0
fuzzy matches = 0
duplicate quote keys = 0
Opening inferred = 0
```

Bookmaker qualification：

```text
at least one bookmaker has T-60 + Closing for >= 24 / 30 games
at least 7 complete games in every season
all-target-snapshot coverage >= 70%
selected bookmaker abnormal quote rows = 0
```

Primary bookmaker ranking is coverage-only：

1. Complete T-60＋Closing game count, descending
2. All-required-snapshot coverage, descending
3. Minimum per-season complete count, descending
4. Stable bookmaker key, ascending

ROI、model edge 或市場賠率高低不得參與 bookmaker 選擇。

## Point-in-time rules

- Provider snapshot must be equal to or earlier than requested timestamp.
- Quote must remain strictly before scheduled tip-off.
- Before September 2022, maximum accepted provider lag is 15 minutes.
- From September 2022, maximum accepted provider lag is 10 minutes.
- A future snapshot may never be substituted for a missing earlier snapshot.
- Closing may be used later for CLV only; it cannot select the entry bet.
- Two sides of one quote must come from the same bookmaker and same provider snapshot.

## Provenance

Per request：

```text
source_id
endpoint_version
requested_at_utc
provider_snapshot_at_utc
fetched_at_utc
HTTP status
response bytes
response SHA-256
x-requests-last / used / remaining
adapter version
```

Per quote, in temporary restricted storage only：

```text
source_event_id
historical_game_id
scheduled_tipoff_utc
provider_snapshot_at_utc
bookmaker key
bookmaker last_update
market key
home / away decimal prices
```

Team mapping only accepts deterministic exact aliases. No fuzzy matching.

## Storage and Terms boundary

The public repo and public Actions Artifact may not retain：

- API key
- raw historical response JSON
- normalized quote-level rows
- quote prices
- downloadable odds archive

Workflow temporary storage may hold raw/normalized rows only during execution, and they must be deleted before Artifact upload.

Publicly retained outputs are limited to aggregate QA, request/hash manifests without prices, quota summary, coverage tables, and deidentified failure diagnostics.

## Production manifest stage

Only `QUALIFIED_FOR_PRODUCTION_MANIFEST` can unlock a later manifest step：

```text
population: all 3,688 frozen Walk-forward v2 OOF games
seasons: 2021-22 through 2023-24
market: h2h
region: us
snapshots: T-6h / T-3h / T-1h / T-30m / T-5m / Closing
```

The manifest must be built without paid calls, deduplicate identical absolute requested timestamps, and calculate exact expected credits before production backfill.

Production backfill requires another explicit cost approval. This policy does not enable full backfill execution.

## Pilot decision states

```text
ACCESS_NOT_PROVIDED
SOURCE_QUALIFICATION_BLOCKED
NO_QUALIFIED_BOOKMAKER
QUALIFIED_FOR_PRODUCTION_MANIFEST
```

Even the final state only allows a separate production manifest. It does not enable：

```text
production backfill
Market Backtest
CLV / EV / ROI / Drawdown
betting-edge claims
nonzero stake
```

## Next exact task after this policy is merged

```text
implement policy-only validator and source adapter self-tests
→ do not call paid endpoint without explicit approval and THE_ODDS_API_KEY
→ when access is approved, run only the frozen 30-game qualification pilot
→ read aggregate Artifact QA
```
