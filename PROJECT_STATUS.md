# NBA Value Lab — Project Status

更新日期：2026-07-18  
目前定位：**Research Candidate／Pre-Market-Backtest**  
正式 Stake：**0**

本文件是研究管線的正式狀態基準。判定順序：最新 `main`／合併 PR／Actions／Artifact QA，高於舊 handoff、聊天紀錄與設計規格。

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
Step 4 — Injury Feature Walk-forward Holdout design predeclaration
```

Expected Minutes Accuracy Audit v3 已正式通過。現在只解鎖 **Holdout 設計的預先宣告**；尚未允許 Holdout execution、Timestamped Odds、Market Backtest、模型啟用或投注。

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
| Wave 1 Features | Research Ready | frozen T-60 selected 91 場。 |
| Wave 2 Features | Research Ready | frozen T-60 selected 85 場。 |
| Wave 3 Features | Research Ready | frozen T-60 selected 117 場。 |
| Combined Wave 1＋2＋3 | Research Ready / 293 games | 0 跨 Wave 重複、0 identity／selection-policy conflict。 |
| Expanded Participation Census v1 | Completed / Eligible | 226 evaluable games；516 conditional PLAYED；209 bench；502 long-history。 |
| Expected Minutes Accuracy Audit v2 | Structural Blocked | 數值門檻通過，但舊 176 場樣本門檻不足。 |
| Expected Minutes Accuracy Audit v3 | **ACCURACY_PASS** | 所有預先宣告的結構、固定輸入、樣本與數值門檻通過。 |
| Injury Feature Walk-forward Holdout | Design predeclaration unlocked | 必須先獨立預先宣告，尚未執行。 |
| Timestamped Odds | Blocked | 依主線排在 Injury Holdout 之後。 |
| Market Backtest | Blocked | 尚無可執行 point-in-time odds join。 |
| Betting Decision Layer | Blocked | 正式 stake = 0。 |

## 市場基準

| 指標 | 模型 | Closing Market |
|---|---:|---:|
| Log Loss | 0.6421 | **0.6167** |
| Brier | 0.2250 | **0.2139** |
| Accuracy | 63.62% | **66.37%** |

模型能小幅改善 Elo 的機率品質，但目前沒有證據顯示能擊敗或改善 NBA Closing Market。

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

這是機率預測的小幅、一致增益，不是獲利證據。

## Injury／Expected Minutes population

### Wave 1

```text
ready overlap reports: 31
filtered player rows: 2,657
identity matched: 2,634（99.1344%）
Expected Minutes／Impact rows: 2,465
frozen T-60 selected games: 91
```

### Wave 2

```text
ready overlap reports: 31
filtered player rows: 2,493
identity matched: 2,468（98.9972%）
Expected Minutes／Impact rows: 2,281
frozen T-60 selected games: 85
```

### Wave 3

```text
ready overlap reports: 44
filtered player rows: 2,918
identity matched: 2,905（99.5545%）
Expected Minutes／Impact rows: 2,818（96.5730%）
strict-prior violations: 0
same-day rows excluded: 513
future rows excluded: 25,940
frozen T-60 selected games: 117
```

Gold-domain correction only excluded two team-only contexts outside Historical Gold and without player rows:

```text
2024-01-19 DAL@GSW
2024-04-12 LAL@MEM
excluded rows: 12
unmatched player-backed games: 0
excluded player-backed games: 0
```

### Combined Wave 1＋2＋3

```text
Wave 1: 91
Wave 2: 85
Wave 3: 117
combined independent games: 293
cross-wave duplicate games: 0
game identity conflicts: 0
selection policy conflicts: 0
duplicate output games: 0
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

Official source and join QA:

```text
combined selected games: 293
successful official source games: 293
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

Preserved sample gates:

```text
evaluable games: 226 / 150 — pass
conditional PLAYED rows: 516 / 500 — pass
starter rows: 307
bench rows: 209 / 200 — pass
10+ prior-game rows: 502 / 400 — pass
complete team-game groups: 450 / 100 — pass
```

固定的同日 roster transition：

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

## Expected Minutes Accuracy Audit v2

正式狀態：

```text
STRUCTURAL_BLOCKED
```

舊 176 場 frozen population 未達四個 preserved sample gates：

```text
evaluable games: 135 / 150
conditional PLAYED rows: 313 / 500
bench rows: 127 / 200
10+ prior-game rows: 305 / 400
```

當時數值只能描述，不得重分類為 pass。

## Expected Minutes Accuracy Audit v3

Evidence lock：

```text
Predeclaration PR: #53
Policy commit: 7f398b9b776a3be2478eed4ad2afc80d4e752e7e
Predeclaration merge: 1f446ff5c503d852a94ccb29e1a519ba7149908a
Execution PR: #54
Verified workflow: 29634963247
Artifact: expected-minutes-accuracy-audit-v3
Artifact id: 8426868417
Digest: sha256:d550849409d00555d16c83fbfd85eacec65678d50ca651511e1e9d4394a4d66a
Formal state: ACCURACY_PASS
```

Primary estimand：

```text
conditional role minutes given official PLAYED label
prediction: prior-only Expected Minutes
label: official target-game actual minutes
```

Primary results：

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

Privacy and leakage QA：

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

Formal permissions：

```text
ready_for_injury_feature_walk_forward_holdout_design_predeclaration = true
ready_for_injury_feature_walk_forward_holdout_execution = false
ready_for_model_training = false
ready_for_probability_adjustment = false
ready_for_betting_edge_claim = false
formal_stake = 0
```

Audit v3 通過只證明目前 prior-only Expected Minutes proxy 達到預先宣告的準確度門檻；它不證明 injury features 能改善賽前勝率，也不證明投注價值。

## 下一個精確任務

```text
Predeclare Injury Feature Walk-forward Holdout
→ freeze Baseline and Candidate models
→ freeze chronological folds and untouched holdout
→ freeze injury feature list and missingness handling
→ freeze Log Loss／Brier／AUC／calibration／margin metrics
→ freeze promotion, valid-negative-result and structural-block paths
→ merge predeclaration before any holdout result is calculated
```

## 已知阻塞

- Injury Holdout 尚未預先宣告或執行。
- Timestamped Odds 的真實 bookmaker-level `observed_at` 資料仍缺失。
- Point-in-time Odds Join、Executable Market Backtest、CLV／EV／ROI／Drawdown 仍未解鎖。
- 模型目前仍輸給 Closing Market。

## Do Not Do

- 不得在 Holdout 預先宣告前查看或選擇正式 Holdout 結果。
- 不降低既有 sample、numerical、join 或 leakage gates。
- 不使用 fuzzy identity、nearest-name guessing 或 fuzzy schedule matching。
- 不把 target-game participation／minutes 放入賽前特徵。
- 不把 missing、NYS、UNKNOWN、SOURCE_MISSING 補成健康、DNP 或 0。
- 不把多個 publication snapshots 當成多場獨立比賽。
- 不重做 Rest／Travel v1，除非取得實質不同的行程／負荷資料。
- 不強制 Platt／Isotonic；Raw 已由 calibration gate 選中。
- 不把 Closing benchmark 當成 executable market backtest。
- 不重做 odds schema／source registry；真正缺的是 timestamped odds data。
- Injury Holdout 未通過前，不執行 Timestamped Odds 主線。
- 未完成 timestamped odds join 前，不宣稱 CLV、EV、ROI、Drawdown 或 betting edge。
- CI 綠燈只代表流程執行成功，必須讀 Artifact QA。
- 正式 Stake 維持 0。

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
- PR #54 — Accuracy Audit v3 Execution
