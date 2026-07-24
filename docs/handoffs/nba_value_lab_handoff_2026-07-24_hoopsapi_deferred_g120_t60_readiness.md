# NBA Value Lab — HoopsAPI Deferred / G1.2.0 T-60 Readiness Handoff

更新日期：2026-07-24

## Repository state before this milestone

```text
main: 13cc8c13c90626a7a03916f9530f179387255fbb
latest merged PR: 166
open PRs before branch creation: none
Formal Stake：0
```

## User decision

```text
HoopsAPI runtime path: DEFERRED_BY_USER_NO_EXECUTION
request id: HOOPSAPI-PRIVATE-RUNTIME-PREFLIGHT-2026-07-24-001
account creation authorized: false
Terms acceptance authorized: false
API key connection authorized: false
execution enabled: false
execution count: 0 / 1
provider requests executed: 0
```

PR #166 的 preflight design 保留在 repo 作為未來選項，但目前不繼續 HoopsAPI account／key／network path。

## Current milestone

```text
DESIGN_G1_2_0_REAL_GOVERNED_T60_INPUT_READINESS_GATE_V1
```

正式 Gate：

```text
gate id: G1-2-0-REAL-GOVERNED-T60-INPUT-READINESS-GATE-2026-07-24-001
formal state: G1_2_0_REAL_GOVERNED_T60_INPUT_READINESS_GATE_DESIGN_VALIDATED
design only: true
real input available: false
real validation executed: false
```

## Frozen readiness conditions

- `season=2026-27` 必須明確提供。
- `competition_type=regular_season` 必須明確提供。
- `data_mode=real_governed`；fixture／synthetic／closing-only 均不合格。
- `evaluation_stage=T-60m`。
- `30 <= minutes_to_tip <= 90`。
- 真實 bookmaker identity，不接受 fixture／placeholder。
- 同一 bookmaker 的雙邊 h2h prices。
- 兩邊共用相同 provider-origin `observed_at`。
- `observed_at <= analysis_cutoff < tipoff`。
- provider timestamp semantics、source rights、source ID／URL、raw SHA-256 必須完整。
- `collector_fetched_at` 不得替代 `observed_at`，也不得冒充 provider-origin observation time。
- Closing-only 不得冒充 T-60。
- Fixture 不得寫入 formal history。

## Current blockers

```text
qualified timestamped odds sources: none
HoopsAPI: deferred
BloomBet schema probe: deferred
ZachHT Kaggle archive: research blocked
real governed 2026-27 T-60 input: unavailable
Market Backtest: blocked
CLV / EV / ROI / Drawdown: blocked
Formal Stake：0
```

## Next unique mainline

```text
AWAIT_REAL_GOVERNED_2026_27_T60_INPUT_AND_QUALIFIED_TIMESTAMPED_ODDS
```

下一次接續時，先核對最新 main、Open PR、Actions 與 Artifact QA。除非使用者另行選定合法來源或提供真實 governed input，不要回頭執行 HoopsAPI request，也不要用 fixture／Closing-only 代替 prerequisite。
