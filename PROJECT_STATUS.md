# NBA Value Lab — Project Status

更新日期：2026-07-18  
定位：**Research Candidate / Pre-Market-Backtest**  
正式 Stake：**0**

本文件是研究管線的正式狀態基準。最新 main、合併 PR、Actions 與 Artifact QA 優先於舊 handoff、聊天紀錄與規格文件。

## Current Control Block

### Latest Main SHA

```text
95bf21a2b7dbe44cbd3eba09a9d72873c391fc70
```

最新已合併里程碑：

```text
PR #56 — Injury Feature Walk-forward Holdout v1 — VALID_NEGATIVE_RESULT
```

### Open PR

| PR | 狀態 | 正式內容 |
|---|---|---|
| #57 — Predeclare Real Timestamped Odds Acquisition v1 | Draft | 只鎖定來源資格、付費邊界、30 場 pilot、quota、bookmaker coverage、provenance 與 storage gates；不呼叫付費端點。 |

### Next unique mainline

```text
完成 PR #57 policy-only validation 並合併
→ 另開 adapter / synthetic self-test PR
→ 不使用 API key、不呼叫 paid endpoint
→ 只有使用者明確核准費用並提供 THE_ODDS_API_KEY 後，才可執行 frozen 30-game qualification pilot
```

### Known blockers

- PR #57 尚未合併，Timestamped Odds acquisition contract 尚未成為 main 正式規則。
- The Odds API historical access 需要付費方案；目前未取得使用者付費核准。
- `THE_ODDS_API_KEY` 尚未提供或連接。
- 正式執行前必須重新確認當時價格、Terms、quota 與資料使用邊界。
- 真實 bookmaker-level `observed_at` odds data 尚未取得。
- Point-in-time Odds Join、Market Backtest、CLV、EV、ROI、Drawdown 尚未解鎖。
- Historical model 仍明顯輸給 Closing Market。

### Do Not Do

- 不得自動建立帳號、訂閱方案、購買 credits 或產生任何費用。
- 不得在未獲使用者明確核准前呼叫 Historical paid endpoint。
- 不得把 API key 寫入 commit、log、Artifact、error message 或下載檔。
- 不得繞過 401、403、429、登入、付款或 access control。
- 不得把 T-6h、T-24h 或 provider first-seen quote 冒充 true bookmaker Opening。
- 不得用 future snapshot 補較早缺失 snapshot。
- 不得混用不同 bookmaker 或不同 snapshot 的兩側價格。
- 不得在 qualification pilot 計算 model edge、EV、ROI、CLV、Drawdown、bet count 或 bookmaker profit ranking。
- 不得按 ROI、模型表現或價格高低選擇 primary bookmaker；只能按 coverage 與固定 key 排序。
- 不得在 public repo 或 public Artifact 保留 raw JSON、quote-level rows、價格資料或可下載 odds archive。
- 不得把已拒絕的 injury candidate 放回市場模型；使用 frozen baseline-only path。
- 不重做 odds schema、bookmaker schema、no-vig boundary 或 source registry。
- Closing-only benchmark 不得當 executable market backtest。
- 未完成 point-in-time odds join 前，不宣稱 CLV、EV、ROI、Drawdown 或 betting edge。
- CI 綠燈只代表流程執行成功，必須讀 Artifact QA。
- 正式 Stake 維持 0。

## Canonical Roadmap

```text
1. Historical Gold and baseline model
2. Official injury data and feature-ready matchups
3. Expected Minutes Accuracy Audit
4. Injury Feature Walk-forward Holdout
5. Real Timestamped Odds Acquisition
6. Point-in-time Odds Join and Market Backtest
7. CLV / EV / ROI / Drawdown
8. Betting Decision Layer
```

目前節點：

```text
Step 5 — Real Timestamped Odds Acquisition v1 predeclaration
```

Holdout v1 已產生 structurally valid negative result。市場研究只保留 frozen baseline-only path；目前只允許來源與取得政策預先宣告，尚未允許付費 qualification、production backfill、Market Backtest 或投注。

## Core Status

| Module | Status | Formal conclusion |
|---|---|---|
| Historical Gold | Completed | 5,824 matchup rows；strict PIT violations 0。 |
| Logistic + Elo Walk-forward v2 | Completed | 3,688 OOF；Log Loss / Brier 小幅且跨 Fold 優於 Elo。 |
| Calibration Gate | Completed | Platt / Isotonic 未穩定改善，保留 Raw。 |
| Closing Market Benchmark | Model lost | 模型明顯輸給 Closing Market。 |
| Market Residual v1 | Negative Result | 100% Closing Market、0% model residual。 |
| Rest / Travel v1 | Negative Result | Untouched holdout 未通過。 |
| Wave 1 / 2 / 3 Injury Features | Research Ready | 91 + 85 + 117 = 293 independent games。 |
| Expanded Participation Census v1 | Completed | 226 evaluable games；516 PLAYED；209 bench；502 long-history。 |
| Expected Minutes Audit v3 | **ACCURACY_PASS** | 所有預先宣告的結構、樣本與數值 gates 通過。 |
| Injury Feature Holdout v1 | **VALID_NEGATIVE_RESULT** | 結構通過；固定兩特徵 candidate 未達跨 Fold promotion gates。 |
| Injury candidate | Rejected | 不進入後續市場模型。 |
| Timestamped Odds Acquisition v1 | Predeclaration in progress | PR #57 Draft；尚未讀 key、呼叫 paid endpoint 或下載 quote。 |
| Paid qualification pilot | Blocked | 需要 PR #57 合併、顯式費用核准與 `THE_ODDS_API_KEY`。 |
| Production Backfill | Blocked | 需要 pilot 通過、offline manifest 與另一次明確 cost approval。 |
| Market Backtest | Blocked | 尚無 executable point-in-time odds join。 |
| Betting Decision Layer | Blocked | Stake = 0。 |

## Historical Benchmarks

### Walk-forward v2

```text
OOF games: 3,688
Logistic + Elo Log Loss: 0.631306
Elo Log Loss: 0.634301
Logistic + Elo Brier: 0.220567
Elo Brier: 0.221949
Logistic + Elo Accuracy: 63.856%
Elo Accuracy: 64.073%
```

### Closing Market

| Metric | Model | Closing Market |
|---|---:|---:|
| Log Loss | 0.6421 | **0.6167** |
| Brier | 0.2250 | **0.2139** |
| Accuracy | 63.62% | **66.37%** |

## Expected Minutes Accuracy Audit v3

```text
PR #53 — predeclaration
PR #54 — execution
Merge: 28866b168fc6194bea05353b01b120e649adcfd5
Formal state: ACCURACY_PASS
```

| Gate | Result | Threshold |
|---|---:|---:|
| Overall MAE | 5.120902 | <= 6.5 |
| Overall RMSE | 6.693908 | <= 9.0 |
| Median AE | 4.093886 | <= 5.5 |
| Absolute bias | 0.668968 | <= 2.0 |
| Starter MAE | 4.663676 | <= 6.5 |
| Bench MAE | 5.792521 | <= 7.5 |
| 10+ history MAE | 5.092724 | <= 6.25 |

Audit v3 只證明 prior-only Expected Minutes proxy 達標，不證明 injury feature 能改善勝率或產生投注價值。

## Injury Feature Walk-forward Holdout v1

### Evidence

```text
Predeclaration PR: #55
Execution PR: #56
Merge: 95bf21a2b7dbe44cbd3eba09a9d72873c391fc70
Formal state: VALID_NEGATIVE_RESULT
```

### Probability results

| Population | Baseline Log Loss | Candidate Log Loss | Gain |
|---|---:|---:|---:|
| Feb development — 65 games | 0.657411 | 0.667960 | **-0.010549** |
| Mar-Apr final — 104 games | 0.589324 | 0.586426 | **+0.002898** |
| Combined forward — 169 games | 0.615511 | 0.617785 | **-0.002274** |

| Population | Baseline Brier | Candidate Brier | Gain |
|---|---:|---:|---:|
| Feb development | 0.233483 | 0.235695 | **-0.002212** |
| Mar-Apr final | 0.202537 | 0.201171 | **+0.001366** |
| Combined forward | 0.214439 | 0.214450 | **-0.000010** |

Final fold 的改善保留為診斷，但不可推翻 combined negative decision。後續 market path 固定為 baseline-only。

## Timestamped Odds Acquisition v1 — PR #57 Frozen Contract

### Existing assets to reuse

```text
data/templates/point-in-time-odds-template.csv
scripts/build_point_in_time_odds.py
docs/point-in-time-odds-layer-v1.md
data/historical-odds-source-registry.json
.github/workflows/validate-point-in-time-odds.yml
Closing-only benchmark
proportional no-vig boundary
```

True missing asset：

```text
licensed bookmaker-level historical quotes with reliable observed_at
```

### Candidate source scope

```text
provider: The Odds API Historical API v4
sport: basketball_nba
region: us
market: h2h only
odds format: decimal
paid historical access required
secret name: THE_ODDS_API_KEY
```

### Frozen snapshot targets

```text
T-6h
T-3h
T-1h
T-30m
T-5m
Closing = scheduled tip-off minus one second query
```

Opening is not part of v1 and may not be inferred from fixed T-minus snapshots or provider first-seen rows.

### Frozen qualification pilot

```text
30 deterministic games
10 games per season: 2021-22 / 2022-23 / 2023-24
6 snapshot requests per game
maximum request slots: 180
maximum paid quota: 1,800 credits
market metrics calculated: false
```

### Qualification decisions

```text
ACCESS_NOT_PROVIDED
SOURCE_QUALIFICATION_BLOCKED
NO_QUALIFIED_BOOKMAKER
QUALIFIED_FOR_PRODUCTION_MANIFEST
```

Even `QUALIFIED_FOR_PRODUCTION_MANIFEST` only permits an offline production manifest and exact cost preflight. It does not permit full backfill, Market Backtest, CLV / EV / ROI, betting-edge claims or nonzero stake.

## Next Exact Task

```text
Validate and merge PR #57 policy-only predeclaration
→ implement source adapter and synthetic tests without API key or network call
→ stop before paid pilot
→ request explicit spend approval and THE_ODDS_API_KEY only when the frozen 30-game pilot is ready
```

## Important PRs

- PR #28 — Closing Market Benchmark
- PR #29 — Market Residual Negative Result
- PR #30 — Rest / Travel Negative Result
- PR #35 — Expected Minutes v1
- PR #36 — Team Injury Burden
- PR #37 — Multi-report Injury Panel
- PR #38 — Injury Residual Audit
- PR #40 — Frozen T-60
- PR #41 — Team Submission Status
- PR #42 / #43 — Wave 1
- PR #44 / #45 — Wave 2
- PR #47 — Accuracy Audit v1
- PR #48 — Participation Labels
- PR #49 — Accuracy Audit v2
- PR #50 — Wave 3 Acquisition
- PR #51 — Wave 3 Features
- PR #52 — Expanded Participation Census
- PR #53 / #54 — Accuracy Audit v3
- PR #55 — Injury Holdout Predeclaration
- PR #56 — Injury Holdout VALID_NEGATIVE_RESULT
- PR #57 — Timestamped Odds Acquisition v1 Predeclaration (Draft)
