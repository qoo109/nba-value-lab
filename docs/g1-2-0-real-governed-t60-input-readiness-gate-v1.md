# G1.2.0 Real Governed T-60 Input Readiness Gate v1

更新日期：2026-07-24  
Formal Stake：0

## Purpose

HoopsAPI runtime path 已依使用者決定暫時跳過，不建立帳號、不接受 Terms、不連接 API Key，也不執行 preflight。

```text
HoopsAPI request:
HOOPSAPI-PRIVATE-RUNTIME-PREFLIGHT-2026-07-24-001

status:
DEFERRED_BY_USER_NO_EXECUTION

execution enabled: false
execution count: 0 / 1
provider requests executed: 0
```

下一個非 provider-specific 工作，是固定第一份真實 2026-27 例行賽 T-60 input 在進入 G1.2.0 前必須滿足的 readiness gate。

本里程碑只設計 Gate，不會執行真實輸入，也不會把 fixture 或 Closing-only odds 冒充真實 T-60 資料。

## Formal state

```text
G1_2_0_REAL_GOVERNED_T60_INPUT_READINESS_GATE_DESIGN_VALIDATED
```

## Activation identity

G1.2.0 只有以下 metadata 明確存在時才可進入 activation path：

```text
season: 2026-27
competition_type: regular_season
evaluation_stage: T-60m
data_mode: real_governed
includes_overtime: true
```

禁止：

- 依日期推測 season；
- 省略 competition type；
- offseason 提前把 G1.2.0 設為 primary；
- 用 `active_only` 繞過 scheduled／control shadow；
- 用 fixture 通過 real-input gate。

## Required top-level fields

```text
schema_version
data_mode
slate_id
slate_date
analysis_cutoff
evaluation_stage
target_bookmaker_id
market_id
includes_overtime
data_version
lock_window_minutes
candidates
season
competition_type
```

`target_bookmaker_id` 不得是 `fixture_book`、`unknown`、`placeholder` 或空值。

T-60 lock window 固定維持：

```text
30 <= minutes_to_tip <= 90
```

## Required candidate fields

每一個 game 必須同時有 home 與 away 兩邊，而且是同一 bookmaker、同一 snapshot：

```text
game_id
scheduled_at
candidate_side
selection_team_id
opponent_team_id
target_odds
opponent_odds
observed_at
p_conservative
p_neutral
p_optimistic
coverage_pct
confidence
news_risk_level
analysis_gate_status
comparison_sources
injury_confirmed
starters_confirmed
minutes_limit_confirmed
source_lineage_complete
market_rules_complete
price_timestamp_valid
out_of_distribution
reverse_path_resolved
stale_warning
model_market_gap_pp
independent_evidence_count
data_age_minutes
```

必要一致性：

- exactly two sides per game；
- home／away team mapping 必須精確互補；
- target／opponent odds 必須是同 snapshot 的雙邊價格；
- home 與 away 的 `observed_at` 必須完全相同；
- `P_C <= P_N <= P_O`；
- 兩邊 neutral probability 必須互補；
- home P_C＋away P_O＝1；
- home P_O＋away P_C＝1；
- 禁止 fuzzy mapping 或 nearest-time mapping。

## Odds provenance gate

真實 T-60 input 必須提供可稽核的 bookmaker-level provenance：

```text
bookmaker identity: required
same-book two-sided h2h: required
provider-origin observed_at: required
observed_at timezone: required
observed_at <= analysis_cutoff < tipoff
source URL or source ID: required
source rights state: private_research_allowed
raw source SHA-256: required
provider timestamp semantics: verified
```

`collector_fetched_at` 不得替代 `observed_at`。

```text
collector_fetched_at substitution: false
Closing-only substitution for T-60: false
future snapshot fill: false
Opening inference: false
```

沒有 provider-origin timestamp 時必須 fail closed：

```text
price_timestamp_valid: false
real input ready: false
G1.2.0 end-to-end validation: blocked
```

## Injury and information boundary

- Missing／Unknown／NYS 不得補成健康或 0 burden。
- Target-game participation 與 minutes 不得回流 prediction features。
- Main gate 仍要求 injury、starters 與 minutes-limit confirmation。
- EV 不得繞過資料、傷病、來源或風險 Gate。
- 2pp PP Guard 與 5%／7%／10% EV thresholds 不變。

## Current readiness decision

```text
qualified timestamped odds source: none
real governed 2026-27 T-60 input available: false
fixture eligible as real input: false
Closing-only eligible as T-60: false
real G1.2.0 validation executed: false
Market Backtest: false
CLV / EV / ROI / Drawdown: false
betting edge claims: false
Formal Stake：0
```

## Next unique mainline

```text
AWAIT_REAL_GOVERNED_2026_27_T60_INPUT_AND_QUALIFIED_TIMESTAMPED_ODDS
```

當兩項 prerequisite 都存在時，只先執行一次 dry-run／aggregate-only readiness validation；不得直接寫入 formal history、啟用 market metrics 或提高 Stake。
