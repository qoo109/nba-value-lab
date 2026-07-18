# Timestamped Odds Exact No-price Manifest v1

更新日期：2026-07-18  
Roadmap：Step 5  
狀態：**Implementation pending live official schedule QA**

## Purpose

在不呼叫付費 odds endpoint 的前提下，為 PR #57 凍結的 30 場 qualification sample 建立精確 scheduled tip-off 與 request timestamp 計畫。

Historical Gold／Silver 的正式表只保存 `game_date`，不能用固定晚間時間、猜測時區或事後手動填值。因此本層使用專案已採用的 **NBA Official LiveData Boxscore**，只抽取賽程身分 metadata：

```text
gameId
gameCode
gameTimeUTC
gameTimeLocal
gameEt
homeTeam.teamTricode
awayTeam.teamTricode
arena.arenaTimezone
```

不保存球員、比分或其他 boxscore 統計。

## Upstream locks

```text
policy PR: #57
adapter PR: #59
market model path: frozen baseline only
sample: 30 independent OOF games
snapshots: 6 per game
maximum game slots: 180
maximum paid quota ceiling: 1,800
Opening: not allowed
formal stake: 0
```

本層不修改來源候選、sample、snapshot、market、region、quota 或 bookmaker gates。

## Official schedule identity

每一場必須通過：

```text
official game ID = zero-padded frozen historical_game_id
game status = final
gameCode date = frozen game_date
home tricode = frozen home team
away tricode = frozen away team
gameEt local date = frozen game_date
gameTimeUTC = gameEt represented in UTC
optional gameTimeLocal / gameTimeHome / gameTimeAway represent the same instant
```

任何缺值、日期／隊伍／時間不一致都屬 structural blocker。失敗比賽不得被替換。

`gameTimeUTC` 在本層作為 `scheduled_tipoff_utc`。它是 NBA Official LiveData 保存的正式 game-time metadata，不是從比分、PBP 第一事件或比賽實際開始時間反推。

## Outputs

### 1. Schedule manifest — 30 rows

```text
timestamped-odds-schedule-manifest-v1.csv
```

包含 game ID、賽季、日期、主客隊、official scheduled tip-off、官方時間欄位、來源 URL、retrieved-at、bytes 與 SHA-256。

### 2. Game-slot manifest — 180 rows

```text
timestamped-odds-game-slot-manifest-v1.csv
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

每列只包含請求時間與 game identity；沒有 bookmaker 或 price。

### 3. Deduplicated request plan

```text
timestamped-odds-unique-request-plan-v1.csv
```

The Odds API Historical endpoint 以 requested timestamp 回傳該 sport 的事件集合，因此相同 `requested_at_utc` 只需要一個 future paid request。此計畫按 policy 的 dedup key `requested_at_utc` 去重並列出對應 target games／slots。

```text
exact planned requests = unique requested_at_utc
exact planned quota = unique requests × 10 credits
```

精確 quota 必須不高於 1,800。這只是離線成本計畫，不是付費授權。

## Structural gates

```text
official source successes = 30 / 30
schedule rows = 30
10 games per season
source hashes = 30 unique
schedule duplicate game IDs = 0
missing games = 0
date/team identity mismatches = 0
time consistency failures = 0
game-slot rows = 180
60 slots per season
duplicate game/snapshot keys = 0
Opening labels = 0
unique request-plan timestamps = unique
exact planned quota <= 1,800
```

## Privacy and usage boundary

公開 Artifact 允許保存 no-price schedule／request manifests，因其不含 odds provider data。NBA raw boxscore JSON 不寫入磁碟；只保存來源 URL、bytes、retrieved-at 與 SHA-256。

永久禁止：

```text
player rows retained: 0
score fields retained: 0
raw official JSON retained: 0
THE_ODDS_API_KEY read: false
paid odds endpoint called: false
real odds quotes downloaded: 0
market metrics calculated: false
```

## Formal decision

成功狀態：

```text
EXACT_MANIFEST_READY_ACCESS_NOT_PROVIDED
```

它只表示 30 場的 schedule identity、180 個 game slots 與去重 request／cost plan 已凍結。仍不允許：

```text
paid qualification execution
production backfill
Market Backtest
CLV / EV / ROI
betting-edge claim
nonzero stake
```

## Next exact task after merge

```text
revalidate provider pricing and terms
→ user explicitly approves maximum 1,800-credit qualification exposure
→ private THE_ODDS_API_KEY is configured
→ execute only the frozen qualification request plan
→ delete raw and quote-level temporary files
→ read aggregate source/bookmaker QA
```
