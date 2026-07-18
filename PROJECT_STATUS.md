# NBA Value Lab — Project Status

更新日期：2026-07-18  
目前定位：**Research Candidate／Pre-Market-Backtest**

本文件是研究管線的正式進度基準。`nba_value_lab_handoff_2026-07-17.md` 是唯一主線；後續 handoff 只更新進度與阻塞，不得取代或重排。

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
Step 3 — Expanded participation-label census before Accuracy Audit v3 design
```

尚未進入 Injury Holdout、Timestamped Odds 或 Market Backtest。

## 核心狀態

| 模組 | 狀態 | 正式結論 |
|---|---|---|
| Historical Gold | Completed | 5,824 matchup rows；strict point-in-time 與 season reset 通過。 |
| Logistic + Elo Walk-forward v2 | Completed | 3,688 場 OOF；小幅優於 Elo。 |
| Closing Market Benchmark | Model lost | 1,894 場；模型輸給 Closing Market。 |
| Market Residual Analysis v1 | Negative Result | 100% Closing Market、0% 模型殘差。 |
| Rest／Travel Context v1 | Negative Result | 2023–24 untouched holdout 未通過。 |
| Official Injury Importer | Completed | PDF、publication time、SHA-256、跨頁與時間 QA 已建立。 |
| Player Participation Labels v1 | Research Ready | frozen 176-game panel：99.8909% join；UNKNOWN 2.2901%。 |
| Expected Minutes Audit v2 | Structural Blocked | 所有 numerical gates 通過，但 4 個 preserved sample gates 未達。 |
| Wave 1 Features | Research Ready | frozen T-60 selected 91 場。 |
| Wave 2 Features | Research Ready | frozen T-60 selected 85 場。 |
| Wave 3 Acquisition | Research Ready | 45 player、44 team、44 ready overlap、15 dates。 |
| Wave 3 Features | Research Ready | identity 99.5545%；Expected Minutes／Impact 96.573%；T-60 selected 117 場。 |
| Combined Wave 1＋2＋3 | Research Ready / 293 games | 0 跨 Wave 重複、0 identity／policy conflict。 |
| Expanded Participation Census | Next | 必須先量測 293-game panel 的 PLAYED／bench／10+ history 等樣本。 |
| Expected Minutes Accuracy Audit v3 | Blocked | 等 expanded participation counts 固定後才可預先宣告。 |
| Injury Holdout | Blocked | 必須先通過 expanded Accuracy Audit。 |
| Timestamped Odds | Blocked | 依主線排在 Injury Holdout 之後。 |
| Betting Decision Layer | Blocked | 正式 stake = 0。 |

## 市場基準

| 指標 | 模型 | Closing Market |
|---|---:|---:|
| Log Loss | 0.6421 | **0.6167** |
| Brier | 0.2250 | **0.2139** |
| Accuracy | 63.62% | **66.37%** |

模型目前能小幅擊敗 Elo，但沒有證據顯示能擊敗或改善 NBA Closing Market。

## Injury 樣本

### Wave 1

```text
36 candidate reports
31 ready overlap reports
2,657 filtered player rows
2,634 identity matched（99.1344%）
2,465 Expected Minutes／Impact rows
frozen T-60 selected games: 91
```

### Wave 2

```text
36 candidate reports
31 ready overlap reports
2,493 filtered player rows
2,468 identity matched（98.9972%）
2,281 Expected Minutes／Impact rows
frozen T-60 selected games: 85
```

### Wave 3

```text
45 candidate reports
44 ready overlap reports
2,918 filtered player rows
2,905 identity matched（99.5545%）
2,818 Expected Minutes／Impact rows（96.5730%）
strict-prior violations: 0
same-day rows excluded: 513
future rows excluded: 25,940
frozen T-60 selected games: 117
```

Gold-domain team correction：

```text
input team games: 223
Gold-matched team games: 221
excluded team-only games: 2
excluded team-only rows: 12
unmatched player-backed games: 0
excluded player-backed games: 0
```

固定排除的 team-only contexts：

```text
2024-01-19 DAL@GSW
2024-04-12 LAL@MEM
```

這兩場不在 Historical Gold，且不在 player map；不得建立特徵。任何 player-backed unmatched game 仍是 hard failure。

### Combined Wave 1＋2＋3

```text
Wave 1 selected: 91
Wave 2 selected: 85
Wave 3 selected: 117
raw selected rows: 293
cross-wave duplicate games: 0
combined independent games: 293
game identity conflicts: 0
selection policy conflicts: 0
duplicate output games: 0
```

Sample status：

```text
minimum Accuracy Audit game gate 100: met
initial reliability gate 300: not met
ideal gate 500: not met
```

293 場落在 Wave 3 前規劃的 280–300 範圍內，但不可把 293 寫成 300+ reliability pass。

## Expected Minutes Accuracy Audit v2

Predeclared policy commit：

```text
4591c1d682f638cc7186a73f4707c01eea7e9b15
```

正式狀態：

```text
STRUCTURAL_BLOCKED
```

Failed preserved sample gates：

```text
evaluable games: 135 / 150
conditional PLAYED rows: 313 / 500
bench rows: 127 / 200
10+ prior-game rows: 305 / 400
```

Descriptive metrics：

```text
MAE: 5.025591
RMSE: 6.631056
median AE: 4.064807
bias: +0.819810
starter MAE: 4.756906
bench MAE: 5.419096
10+ history MAE: 5.033709
```

這些數字仍是 descriptive only；不可寫成 Audit Pass。

## Wave 3 Acquisition

Predeclared calendar：

```text
2024-01-04 → 2024-04-11
15 consecutive Thursdays
08:30／13:30／17:30 ET
45 candidate reports
cadence_days: 7
```

Verified acquisition workflow：

```text
29629052936
```

Official acquisition QA：

```text
player successful reports: 45
team successful reports: 44
ready overlap reports: 44
ready overlap dates: 15
normalized player rows: 3,008
team submission rows: 1,306
submission conflicts: 0
```

固定排除：

```text
2024-01-11 17:30 ET
```

原因：player PDF parsed，但 `single_report_ready=false`；team pre-tip QA failed。不得替換該 timestamp。

## Wave 3 Feature Result

Predeclared design commit：

```text
e60e0bf342f60948e5e7a7fb1fc1830e5e9b1440
```

Verified workflow：

```text
29629748942
```

Artifact：

```text
injury-backfill-wave3-features
artifact id: 8425081360
digest: sha256:5f600148ce07f2388173b2151ba31e5ec822a31e1774377e15fda40a0d393d6e
```

Frozen T-60 selection：

```text
available independent games: 221
selected games: 117
games without primary selection: 104
selection rate: 52.9412%
feature unavailable: 4
incomplete snapshot: 100
duplicate selected games: 0
```

Formal decision：

```text
Wave 3 selected panel: Research Ready
combined Wave 1/2/3 panel: Research Ready
ready_for_expected_minutes_accuracy_audit = true
ready_for_injury_feature_walk_forward_holdout = false
ready_for_model_training = false
ready_for_probability_adjustment = false
ready_for_betting_edge_claim = false
```

`ready_for_expected_minutes_accuracy_audit` 只表示 game-level minimum 已達；不代表 player-level preserved sample gates 已達，也不代表可以跳過新的 predeclaration。

## 下一個精確任務

```text
1. Rebuild selected player snapshots for Waves 1, 2, and 3
2. Join NBA Official LiveData participation labels to the combined 293-game panel
3. Freeze source, identity, join, UNKNOWN, duplicate, team, and privacy QA
4. Measure evaluable games
5. Measure conditional PLAYED rows
6. Measure starter and bench rows
7. Measure 10+ prior-game rows
8. Decide whether expanded Accuracy Audit v3 can be predeclared
```

這一步只是 expanded participation census，不計算或查看新的 accuracy metrics。

## 永久邊界

- missing player row ≠ DNP／0 minutes。
- `SOURCE_MISSING`／`UNKNOWN` 不得補成 0。
- NYS、unknown、synthetic missing side 不視為健康。
- 只有明確 `SUBMITTED_NO_INJURIES` 才可建立 zero burden。
- 不使用 fuzzy identity 或 fuzzy schedule matching。
- multiple snapshots 不可冒充 multiple independent games。
- 不得降低 v1／v2 sample 或 numerical gates。
- Expanded Accuracy Audit 未通過前，不進 Injury Holdout。
- Injury Holdout 未通過前，不執行 Timestamped Odds。
- 未完成 timestamped odds join 前，不宣稱 CLV、EV、ROI 或 executable edge。
- CI 綠燈只代表流程完成；必須讀 Artifact QA。
- 正式投注額維持 0。

## 重要 PR

- PR #28 — Closing benchmark
- PR #29 — Market Residual v1
- PR #30 — Rest／Travel negative result
- PR #40 — Multi-report Injury Feature Backfill
- PR #41 — Team Submission Status
- PR #42／#43 — Wave 1
- PR #44／#45 — Wave 2
- PR #47 — Accuracy Audit v1
- PR #48 — Participation Labels
- PR #49 — Accuracy Audit v2
- PR #50 — Wave 3 Acquisition
- PR #51 — Wave 3 Features
