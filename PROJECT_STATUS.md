# NBA Value Lab — Project Status

更新日期：2026-07-18  
定位：**Research Candidate / Pre-Market-Backtest**  
正式 Stake：**0**

本文件是研究管線的正式狀態基準。最新 main、合併 PR、Actions 與 Artifact QA 優先於舊 handoff、聊天紀錄與規格文件。

## Current Control Block

### Latest Main SHA

```text
8c3c45b9e77a0e9de40b82057ba2ac06be6068ac
```

最新已合併里程碑：

```text
PR #55 — Predeclare Injury Feature Walk-forward Holdout v1
```

### Open PR

| PR | 狀態 | 正式內容 |
|---|---|---|
| #56 — Run Injury Feature Walk-forward Holdout v1 | Draft | Artifact 結果為 `VALID_NEGATIVE_RESULT`，等待結果文件與回歸驗證後合併。 |

### Next unique mainline

```text
合併 PR #56 的正式負結果
→ 預先宣告 Real Timestamped Odds Acquisition / Backfill
→ 後續市場研究只使用 frozen baseline-only path
```

### Known blockers

- PR #56 尚未合併到 main。
- 真實 bookmaker-level `observed_at` odds data 尚未取得。
- Timestamped Odds source、usage boundary 與 acquisition gates 尚未另行預先宣告。
- Point-in-time Odds Join、Market Backtest、CLV、EV、ROI、Drawdown 尚未解鎖。
- Historical model 仍明顯輸給 Closing Market。

### Do Not Do

- 不得用相同 293 場結果重新選 feature、fold、penalty、bounds、bootstrap 或 promotion gates。
- 不得因 Final holdout 單獨改善，就把整體 `VALID_NEGATIVE_RESULT` 改寫成通過。
- 被拒絕的 injury candidate 不得進入 baseline-only 市場路徑。
- 不使用 random split、fuzzy identity 或 fuzzy schedule matching。
- Target-game participation 與 minutes 不得進入賽前 feature。
- Missing、NYS、UNKNOWN、SOURCE_MISSING 不得補成健康、DNP 或 0。
- 同一場的多個 publication snapshots 不得當成多場獨立比賽。
- 不重做 Rest / Travel v1，除非取得實質不同的行程或負荷資料。
- 不強制 Platt / Isotonic；Raw 已由既有 calibration gate 選中。
- Closing-only benchmark 不得當 executable market backtest。
- 不重做 odds schema / source registry；真正缺的是 timestamped odds data。
- Timestamped Odds predeclaration 合併前，不執行 acquisition 或價格回測。
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
Step 5 — Real Timestamped Odds Acquisition / Backfill predeclaration unlocked
```

Holdout v1 已產生 structurally valid negative result。後續只保留 frozen baseline-only market path；尚未允許 Timestamped Odds execution、Market Backtest、模型啟用或投注。

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
| Expected Minutes Audit v2 | Structural Blocked | 舊 176 場樣本不足。 |
| Expected Minutes Audit v3 | **ACCURACY_PASS** | 所有預先宣告的結構、樣本與數值 gates 通過。 |
| Injury Feature Holdout v1 | **VALID_NEGATIVE_RESULT** | 結構通過；固定兩特徵 candidate 未達跨 Fold promotion gates。 |
| Injury candidate | Rejected | 不進入後續市場模型。 |
| Timestamped Odds | Predeclaration unlocked / Data blocked | 可設計 acquisition contract；尚無真實 observed_at data。 |
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

## Injury Population

```text
Wave 1: 91
Wave 2: 85
Wave 3: 117
Combined independent games: 293
Cross-wave duplicates: 0
Selection-policy conflicts: 0
Primary snapshot: latest feature-ready at or before T-60m
Fallback: none
```

Wave 3 QA：

```text
filtered player rows: 2,918
identity matched: 2,905 / 2,918 = 99.5545%
Expected Minutes / Impact coverage: 96.5730%
strict-prior violations: 0
```

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
Predeclaration merge: 8c3c45b9e77a0e9de40b82057ba2ac06be6068ac
Policy commit: 49560a26cf96b0aafa228416e84253de82e5ca80
Execution PR: #56
Workflow run: 29636667921
Artifact id: 8427322134
Digest: sha256:f5a00bf4c5034b40d5692306459611012e176092e54ab4f647c6c23b0c3e40a0
Formal state: VALID_NEGATIVE_RESULT
```

### Structural QA

```text
population games: 293
baseline OOF joins: 293
complete snapshots: 293
missing feature rows: 0
duplicate games: 0
date/team mismatch: 0
fallback rows: 0
strict PIT violations: 0
fold overlap: 0
test rows used for training: 0
structural blockers: 0
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

Combined Accuracy rose from 62.13% to 64.50%, but Accuracy cannot override worse Log Loss / Brier.

### Bootstrap

```text
10,000 paired game-level replicates
combined P(Log Loss gain > 0): 0.4023 / required 0.70 — fail
final P(Log Loss gain > 0): 0.6549 / required 0.55 — pass
```

### Failed promotion gates

```text
combined Log Loss gain: -0.002274 / required >= +0.002000
development Log Loss gain: -0.010549 / required >= -0.005000
combined Brier gain: -0.000010 / required >= +0.000500
combined bootstrap P(gain > 0): 0.4023 / required >= 0.7000
```

### Passed safety gates

```text
average probability shift: 0.037843 <= 0.05
maximum single-game shift: 0.155311 <= 0.20
worst monitored subgroup degradation: 0.015943 <= 0.03
all probability coefficients non-positive: true
```

### Formal permissions

```text
injury_candidate_research_ready = false
market_research_model_path = frozen_baseline_only
ready_for_timestamped_odds_predeclaration = true
ready_for_timestamped_odds_execution = false
ready_for_production_model_training = false
ready_for_probability_adjustment = false
ready_for_betting_edge_claim = false
formal_stake = 0
```

Final fold 的改善保留為診斷，但不可推翻 combined negative decision。這個 exact candidate 不得再用相同結果反覆調整直到通過。

## Next Exact Task

```text
Predeclare Real Timestamped Odds Acquisition / Backfill
→ freeze legal source and usage boundary
→ freeze bookmaker, market, observed_at and scheduled_tipoff requirements
→ target snapshots: Opening, T-6h, T-3h, T-1h, T-30m, Closing
→ freeze provenance, source-health, normalization and missingness gates
→ use frozen baseline-only model path
→ merge predeclaration before acquiring or evaluating executable prices
```

Odds schema、bookmaker schema、snapshot schema、no-vig boundary 與 Closing benchmark 已完成；不得重建另一套 registry。

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
- PR #56 — Injury Holdout `VALID_NEGATIVE_RESULT` (Draft)
