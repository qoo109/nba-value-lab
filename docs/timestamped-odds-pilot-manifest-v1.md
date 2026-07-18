# Frozen Timestamped Odds Pilot Manifest v1

更新日期：2026-07-18  
Roadmap：Step 5  
狀態：**Official season schedule / no-price manifest validation**

## Purpose

在不呼叫付費 odds endpoint 的前提下，為 PR #57 凍結的 30 場 qualification sample 建立：

1. Historical Gold 驗證的 exact game identity；
2. NBA Official season schedule 提供的 exact UTC tip-off；
3. 每場 6 個 frozen game/snapshot slots；
4. 依 `requested_at_utc` 去重後的 exact request／quota plan。

Historical Gold 正式表只有 `game_date`，不能猜測固定開賽時間或從 PBP 第一事件反推。

## Recorded source correction

最初嘗試使用單場 NBA Official LiveData Boxscore：

```text
workflow run: 29638960721
Gold matches: 30 / 30
single-game official requests: 30
HTTP 403: 30 / 30
paid odds-provider calls: 0
```

此結果只證明 GitHub runner 的單場 CDN 路徑不可用；沒有繞過 403、沒有替換比賽、沒有降低 Gate。

正式 schedule metadata 路徑改為同樣屬 NBA 官方網域的低頻 season schedule files：

```text
https://data.nba.com/data/10s/v2015/json/mobile_teams/
nba/{season_start}/league/00_full_schedule.json
```

每個 frozen season 只請求一份檔案，共 3 份。這是 schedule metadata source correction，不是 odds source、sample 或 snapshot policy 的事後替換。

## Frozen upstream controls

```text
policy PR: #57
adapter PR: #59
Historical Gold run: 29551715399
sample: 30 games / 10 per OOF season
snapshots: 6 per game
maximum game slots: 180
maximum paid quota ceiling: 1,800
Opening: forbidden
market path: frozen baseline only
formal stake: 0
```

本層不修改 odds source、sample、market、region、snapshots、quota cap 或 bookmaker gates。

## Historical Gold identity

從 `historical-gold-multiseason` 只讀：

```text
game_id
game_date
home_team_abbr
away_team_abbr
```

30 場必須全部唯一存在，且日期與主客隊完全符合 frozen policy。Missing 或 mismatch 不得以其他比賽替換。

## NBA Official season schedule fields

每份 season schedule 只使用：

```text
gid      official game ID
gdte     Eastern game date
gdtutc   UTC date
utctm    UTC time
etm      Eastern display time
htm      home-local display time
h.ta     home team abbreviation
v.ta     away team abbreviation
```

每場必須通過：

```text
normalized gid = zero-padded Historical Gold game ID
gid candidate count = exactly 1
gdte = frozen game_date
h.ta = frozen home team
v.ta = frozen away team
gdtutc = valid ISO date
utctm = valid UTC clock time
scheduled_tipoff_utc = gdtutc + utctm + Z
```

不使用 nearest date、fuzzy schedule matching 或人工覆寫。

## Frozen outputs

### Schedule manifest — 30 rows

```text
timestamped-odds-pilot-exact-schedule-v1.csv
```

每列保存 Gold identity、official game ID、scheduled UTC、官方 season source URL、retrieved-at、bytes 與 SHA-256。

### Game-slot manifest — 180 rows

```text
timestamped-odds-pilot-game-slot-manifest-v1.csv
```

每場固定：

```text
T-6h
T-3h
T-1h
T-30m
T-5m
Closing = scheduled_tipoff_utc - 1 second
```

### Deduplicated request plan

```text
timestamped-odds-pilot-unique-request-plan-v1.csv
```

未來 Historical Odds endpoint 以 absolute requested timestamp 查詢 NBA sport snapshot，因此相同 `requested_at_utc` 只規劃一次請求：

```text
exact requests = unique requested_at_utc
exact quota = unique requests × 10 credits
```

Game slots 仍保持 180；去重只降低未來 request count，不改變每場 snapshot contract。

## Structural gates

```text
Historical Gold matches = 30 / 30
Gold duplicates = 0
Gold missing / identity mismatch = 0
official season source requests = 3
official season source success = 3 / 3
official source SHA-256 = 3 unique
official schedule games = 30 / 30
official game candidate / identity / UTC errors = 0
schedule games each season = 10 / 10 / 10
game slots = 180
game slots each season = 60 / 60 / 60
duplicate game/snapshot keys = 0
Opening labels = 0
request-plan timestamps unique
exact planned quota <= 1,800
```

## Retention boundary

允許 Artifact：

- no-price schedule manifest；
- no-price game-slot manifest；
- no-price unique request plan；
- aggregate QA；
- deidentified season-source／game failures。

禁止 Artifact：

```text
raw NBA season JSON
player rows
scores
bookmaker fields
price / outcome rows
THE_ODDS_API_KEY
Odds API response
edge / EV / ROI / CLV / Drawdown
```

## Formal state

成功結果：

```text
PILOT_MANIFEST_READY_ACCESS_NOT_PROVIDED
```

它只證明 schedule identity、180 game slots 與 exact request/cost plan 可重現。仍然：

```text
ready_for_paid_qualification_execution = false
ready_for_production_backfill = false
ready_for_market_backtest = false
ready_for_clv_ev_roi = false
ready_for_betting_edge_claim = false
formal_stake = 0
```

## Next exact task

```text
read official live Artifact QA
→ freeze validated manifest evidence
→ revalidate provider pricing / Terms / quota
→ request explicit user approval for the exact maximum paid exposure
→ configure THE_ODDS_API_KEY privately
→ only then execute the frozen source-qualification pilot
```
