# NBA Value Lab — Project Status

更新日期：2026-07-18  
目前定位：**Research Candidate／Pre-Market-Backtest**  
正式 Stake：**0**

本文件是研究管線的正式狀態基準。證據優先順序：最新 `main`／合併 PR／Actions／Artifact QA，高於舊 handoff、聊天紀錄與設計規格。

## Current Control Block

### Latest Git Commit／Main SHA

```text
28866b168fc6194bea05353b01b120e649adcfd5
```

Merged milestone：

```text
PR #54 — Expected Minutes Accuracy Audit v3 — ACCURACY_PASS
```

### Currently open PRs

| PR | 狀態 | 用途 |
|---|---|---|
| #55 — Predeclare Injury Feature Walk-forward Holdout v1 | Draft | 只鎖定 population、fold、candidate、metrics 與 promotion gates；不執行 Holdout。 |

### Next unique mainline

```text
完成並合併 PR #55 的 policy-only validation
→ 另開 PR 實作完全相同的 two-fold Injury Feature Holdout
→ 產生 STRUCTURAL_BLOCKED、VALID_NEGATIVE_RESULT 或 HOLDOUT_RESEARCH_PASS
```

### Known blockers

- PR #55 尚未合併，Holdout execution 不得開始。
- Injury Feature Walk-forward Holdout 尚未產生正式結果。
- 真實 bookmaker-level `observed_at` Timestamped Odds 資料仍缺失。
- Point-in-time Odds Join、Executable Market Backtest、CLV／EV／ROI／Drawdown 尚未解鎖。
- Historical model 目前仍明顯輸給 Closing Market。

### Do Not Do

- 不得在 PR #55 合併前計算或查看 Injury Holdout 表現。
- 不得在結果出現後更換 feature、fold、penalty、coefficient bounds、bootstrap 或 promotion gates。
- 不使用 random split、fuzzy identity、nearest-name guessing 或 fuzzy schedule matching。
- 不把 target-game participation／minutes 放入賽前特徵。
- 不把 missing、NYS、UNKNOWN、SOURCE_MISSING 補成健康、DNP 或 0。
- 不把同一場的多個 publication snapshots 當成多場獨立比賽。
- 不把 market odds 用於 Holdout 訓練或 feature selection。
- 不重做 Rest／Travel v1，除非取得實質不同的行程／負荷資料。
- 不強制 Platt／Isotonic；Raw 已由既有 calibration gate 選中。
- 不把 Closing benchmark 當 executable market backtest。
- 不重做 odds schema／source registry；真正缺的是 timestamped odds data。
- 未完成 timestamped odds join 前，不宣稱 CLV、EV、ROI、Drawdown 或 betting edge。
- CI 綠燈只代表流程成功，必須讀 Artifact QA。
- 正式 Stake 維持 0。

## 固定主線

```text
1. 擴充官方傷病快照
2. 建立足夠的獨立 feature-ready matchup
3. Expected Minutes Accuracy Audit
4. Injury Feature Walk-forward Holdout
5. Timestamped Odds Acquisition
6. Market Backtest
7. CLV／EV／ROI
8. Betting Decision Layer
```

目前節點：

```text
Step 4 — Injury Feature Walk-forward Holdout v1 predeclaration
```

Expected Minutes Accuracy Audit v3 已正式通過。目前只允許預先宣告 Holdout；尚未允許 Holdout execution、Timestamped Odds、Market Backtest、模型啟用或投注。

## 核心狀態

| 模組 | 狀態 | 正式結論 |
|---|---|---|
| Historical Gold | Completed | 5,824 matchup rows；strict point-in-time 與 season reset 通過。 |
| Logistic + Elo Walk-forward v2 | Completed | 3,688 場 OOF；Log Loss／Brier 小幅且跨 Fold 一致優於 Elo。 |
| Calibration Gate | Completed | Platt／Isotonic 未穩定改善，保留 Raw Logistic＋Elo。 |
| Closing Market Benchmark | Model lost | 1,894 場；模型明顯輸給 Closing Market。 |
| Market Residual Analysis v1 | Negative Result | 100% Closing Market、0% 模型殘差。 |
| Rest／Travel Context v1 | Negative Result | 2023–24 untouched holdout 未通過。 |
| Official Injury Importer | Completed | PDF、publication time、SHA-256、跨頁與時間 QA 已建立。 |
| Wave 1 Features | Research Ready | Frozen T-60 selected 91 場。 |
| Wave 2 Features | Research Ready | Frozen T-60 selected 85 場。 |
| Wave 3 Features | Research Ready | Frozen T-60 selected 117 場。 |
| Combined Wave 1＋2＋3 | Research Ready / 293 games | 0 跨 Wave 重複、0 identity／selection-policy conflict。 |
| Expanded Participation Census v1 | Completed / Eligible | 226 evaluable games；516 PLAYED；209 bench；502 long-history。 |
| Expected Minutes Accuracy Audit v2 | Structural Blocked | 數值門檻通過，但舊 176 場樣本門檻不足。 |
| Expected Minutes Accuracy Audit v3 | **ACCURACY_PASS** | 所有預先宣告的結構、固定輸入、樣本與數值門檻通過。 |
| Injury Feature Walk-forward Holdout v1 | Predeclaration in progress | PR #55 Draft；尚未 fit、尚未執行、尚無結果。 |
| Timestamped Odds | Blocked | 須先取得 structurally valid Holdout result。 |
| Market Backtest | Blocked | 尚無可執行 point-in-time odds join。 |
| Betting Decision Layer | Blocked | 正式 stake = 0。 |

## Historical Model

### Five-season Walk-forward v2

```text
OOF games: 3,688
Logistic + Elo Log Loss: 0.631306
Elo Log Loss: 0.634301
Logistic + Elo Brier: 0.220567
Elo Brier: 0.221949
Logistic + Elo Accuracy: 63.856%
Elo Accuracy: 64.073%
Logistic + Elo AUC: 0.687099
Elo AUC: 0.684454
```

這是機率品質的小幅、一致增益，不是獲利證據。

### Closing Market Benchmark

| 指標 | 模型 | Closing Market |
|---|---:|---:|
| Log Loss | 0.6421 | **0.6167** |
| Brier | 0.2250 | **0.2139** |
| Accuracy | 63.62% | **66.37%** |

## Injury／Expected Minutes population

```text
Wave 1: 91 selected games
Wave 2: 85 selected games
Wave 3: 117 selected games
combined independent games: 293
cross-wave duplicate games: 0
game identity conflicts: 0
selection policy conflicts: 0
selection: latest feature-ready snapshot at or before T-60m
fallback: none
```

Wave 3 QA：

```text
ready overlap reports: 44
filtered player rows: 2,918
identity matched: 2,905 / 2,918 = 99.5545%
Expected Minutes／Impact rows: 2,818 = 96.5730%
strict-prior violations: 0
same-day rows excluded: 513
future rows excluded: 25,940
```

Gold-domain correction only excluded two team-only contexts outside Historical Gold and without player rows：

```text
2024-01-19 DAL@GSW
2024-04-12 LAL@MEM
excluded rows: 12
unmatched player-backed games: 0
excluded player-backed games: 0
```

293 場達到 Accuracy Audit 的研究啟動需求，但不可寫成 300+ reliability pass。

## Expanded Participation Census v1

```text
Predeclaration commit: 8d5d3e56a8d4fe7e54070860695715b3f71f0f05
Workflow run: 29632917590
Artifact: expanded-participation-census-v1
Artifact id: 8426181763
Digest: sha256:2acdf9c62fb16c19f649fdeffce1fa79261adfba3ee186cf707c77631d5d7ba0
Formal state: CENSUS_READY_AUDIT_V3_ELIGIBLE
```

```text
successful official source games: 293 / 293
source-missing games: 0
official player rows: 10,309
selected player snapshot rows: 3,045
identity matched: 3,037 / 3,045 = 99.7373%
participation joins: 3,022 / 3,037 = 99.5061%
UNKNOWN: 103 / 3,037 = 3.3915%
strict-prior violations: 0
ambiguous identities: 0
fuzzy identity: false
unrecognized team mismatches: 0
```

```text
evaluable games: 226 / 150 — pass
conditional PLAYED rows: 516 / 500 — pass
starter rows: 307
bench rows: 209 / 200 — pass
10+ prior-game rows: 502 / 400 — pass
complete team-game groups: 450 / 100 — pass
```

固定同日 roster transition：

```text
historical game: 22300733
matchup: GSW@IND
snapshot date: 2024-02-08
recognized rows: 1
raw official labels modified: false
counted as PLAYED: false
counted as DNP: false
imputed as zero: false
all other team mismatches: hard failure
```

## Expected Minutes Accuracy Audit v3

Evidence lock：

```text
Predeclaration PR: #53
Policy commit: 7f398b9b776a3be2478eed4ad2afc80d4e752e7e
Predeclaration merge: 1f446ff5c503d852a94ccb29e1a519ba7149908a
Execution PR: #54
Merge commit: 28866b168fc6194bea05353b01b120e649adcfd5
Official workflow: 29634963247
Final-head validation: 29635392094
Official Artifact id: 8426868417
Final-head Artifact id: 8427003917
Formal state: ACCURACY_PASS
```

Primary estimand：

```text
conditional role minutes given official PLAYED label
prediction: prior-only Expected Minutes
label: official target-game actual minutes
```

| Gate | Result | Threshold | Pass |
|---|---:|---:|:---:|
| Overall MAE | 5.120902 | <= 6.5 | Yes |
| Overall RMSE | 6.693908 | <= 9.0 | Yes |
| Median AE | 4.093886 | <= 5.5 | Yes |
| Absolute bias | 0.668968 | <= 2.0 | Yes |
| Improvement vs last prior game | 1.201968 | >= 0.25 | Yes |
| Improvement vs recent-10 mean | 0.093054 | >= 0.0 | Yes |
| Starter MAE | 4.663676 | <= 6.5 | Yes |
| Bench MAE | 5.792521 | <= 7.5 | Yes |
| 10+ history MAE | 5.092724 | <= 6.25 | Yes |
| Complete-team aggregate MAE | 7.012663 | <= 18.0 | Yes |
| Complete-team aggregate absolute bias | 1.387791 | <= 7.0 | Yes |
| Worst monitored subgroup absolute bias | 2.642521 | <= 4.0 | Yes |

```text
all structural gates passed: true
all frozen-input integrity gates passed: true
all primary accuracy gates passed: true
structural blockers: 0
accuracy blockers: 0
temporary sensitive files deleted: 131
forbidden player-level files retained: 0
target-game labels used in prediction: false
missing actual imputed as zero: false
missing Expected Minutes imputed as zero: false
raw official labels modified: false
```

Audit v3 通過只證明 prior-only Expected Minutes proxy 達到預先宣告門檻；不證明 injury features 能改善比賽機率，也不證明投注價值。

## Injury Feature Walk-forward Holdout v1 — Frozen PR #55 Contract

### Population and folds

```text
population: exact 293 games
baseline OOF joins required: 293
season: 2023-24
date range: 2023-10-30 → 2024-04-12

Fold 1
train: through 2024-01-31 — 124 games
test: February 2024 — 65 games

Final untouched holdout
train: through 2024-02-29 — 189 games
test: 2024-03-01 → 2024-04-12 — 104 games

combined forward tests: 169 games
```

### Frozen candidate

```text
bounded_injury_logit_offset_v1
baseline: frozen Walk-forward v2 OOF probability
features:
- weighted_unavailable_minutes_home_minus_away
- weighted_absence_impact_positive_home_minus_away
training-fold standardization only
no intercept
baseline logit coefficient fixed at 1.0
L2 alpha: 0.05
coefficient bounds: -0.5 to 0.0
optimizer: L-BFGS-B
hyperparameter tuning: none
```

### Formal future decisions

```text
STRUCTURAL_BLOCKED
VALID_NEGATIVE_RESULT
HOLDOUT_RESEARCH_PASS
```

`VALID_NEGATIVE_RESULT` 是完整研究結果：拒絕 injury candidate，保留 frozen baseline-only market path，不得反覆調參直到變正。

`HOLDOUT_RESEARCH_PASS` 只讓 candidate 成為後續市場比較的 Research Ready 路徑，不直接啟用模型、機率調整或投注。

## 重要 PR

- PR #28 — Closing Market Benchmark
- PR #29 — Market Residual v1
- PR #30 — Rest／Travel Negative Result
- PR #35 — Player Value／Expected Minutes v1
- PR #36 — Team Injury Burden v1
- PR #37 — Multi-report Injury Panel
- PR #38 — Injury Residual Audit
- PR #40 — Frozen T-60 Backfill
- PR #41 — Team Submission Status
- PR #42／#43 — Wave 1
- PR #44／#45 — Wave 2
- PR #47 — Accuracy Audit v1
- PR #48 — Participation Labels
- PR #49 — Accuracy Audit v2
- PR #50 — Wave 3 Acquisition
- PR #51 — Wave 3 Features
- PR #52 — Expanded Participation Census v1
- PR #53 — Accuracy Audit v3 Predeclaration
- PR #54 — Accuracy Audit v3 Execution / ACCURACY_PASS
- PR #55 — Injury Feature Holdout v1 Predeclaration（Draft）
