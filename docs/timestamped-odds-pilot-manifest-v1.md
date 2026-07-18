# Frozen Timestamped Odds Pilot Manifest v1

更新日期：2026-07-18  
Roadmap：Step 5  
狀態：**Official schedule / no-price manifest validation**

## Purpose

在不呼叫付費 odds endpoint 的前提下，為 PR #57 凍結的 30 場 qualification sample 建立：

1. Historical Gold 驗證的 exact game identity；
2. NBA Official LiveData 提供的 exact scheduled tip-off；
3. 每場 6 個 frozen game/snapshot slots；
4. 依 `requested_at_utc` 去重後的 exact request／quota plan。

Historical Gold 正式表只有 `game_date`，不能猜測固定開賽時間。NBA Official LiveData 只用於 schedule metadata；球員、比分與 raw JSON 不留存。

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

本層不修改 source、sample、market、region、snapshots、quota cap 或 bookmaker gates。

## Historical Gold identity

從 `historical-gold-multiseason` 只讀：

```text
game_id
game_date
home_team_abbr
away_team_abbr
```

30 場必須全部唯一存在，且日期與主客隊完全符合 frozen policy。Missing 或 mismatch 不得以其他比賽替換。

## Official schedule metadata

來源：

```text
https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{official_game_id}.json
```

只保留：

```text
gameId
gameCode
gameTimeUTC
gameTimeLocal
gameEt
homeTeam.teamTricode
awayTeam.teamTricode
arena.arenaTimezone
source URL / retrieved_at / bytes / SHA-256
```

每場必須通過：

```text
official game ID = zero-padded Historical Gold game ID
gameStatus = final
gameCode date = frozen game_date
home / away tricode = frozen teams
gameEt date = frozen game_date
gameTimeUTC and gameEt = same instant
optional gameTimeLocal / gameTimeHome / gameTimeAway = same instant
```

`gameTimeUTC` 成為 `scheduled_tipoff_utc`。不得從 PBP 第一事件、比分或人工常識反推。

## Frozen outputs

### Schedule manifest — 30 rows

```text
timestamped-odds-pilot-exact-schedule-v1.csv
```

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

Historical endpoint 以 absolute requested timestamp 查詢整個 NBA sport snapshot，因此相同 `requested_at_utc` 只規劃一次未來請求：

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
official schedule success = 30 / 30
official source SHA-256 = 30 unique
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
- deidentified source failures。

禁止 Artifact：

```text
raw NBA JSON
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
