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
Steps 1–3 — Wave 3 feature backfill and expanded-sample construction
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
| Player Identity Waves 1–2 | Completed | 99% 左右；0 ambiguous、0 fuzzy。 |
| Player Participation Labels v1 | Research Ready | 176／176 官方來源；99.8909% join；UNKNOWN 2.2901%。 |
| Expected Minutes Audit v2 | Structural Blocked | 所有 numerical gates 通過，但 4 個 preserved sample gates 未達。 |
| Wave 1 Features | Research Ready | frozen T-60 selected 91 場。 |
| Wave 2 Features | Research Ready | frozen T-60 selected 85 場。 |
| Combined Wave 1＋2 | Research Ready / 176 games | 0 跨 Wave 重複；Audit v1／v2 frozen population。 |
| Wave 3 Acquisition | Research Ready | 45 player、44 team、44 ready overlap、15 dates。 |
| Wave 3 Features | Next | 尚未執行 identity、values、T-60 selection 與跨 Wave 去重。 |
| Expanded Accuracy Audit | Blocked | 等 Wave 3 features 與 combined sample 完成後另行預先宣告。 |
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

### Combined Wave 1＋2

```text
selected games: 176
cross-wave duplicates: 0
identity conflicts: 0
policy conflicts: 0
```

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

Predeclaration commits：

```text
061f5af060890666d9fc7ca9de865fe129ce3a51
cda6ab1a70d3ac4a19893782c3bf180a7af2d56e
```

Verified workflow：

```text
29628847808
```

Artifact：

```text
injury-backfill-wave3-acquisition
artifact id: 8424782891
digest: sha256:4c974008f9f5055a78e1b57649feca0dcc189a262050abec5439035360db61af
```

Official QA：

```text
requested reports: 45
player successful reports: 45
team successful reports: 44
ready overlap reports: 44
ready overlap dates: 15
normalized player rows: 3,008
player unique games: 167
team submission rows: 1,306
team unique games: 223
submission conflicts: 0
```

Team submission states：

```text
NOT_YET_SUBMITTED: 725
SUBMITTED_WITH_PLAYER_ROWS: 572
UNKNOWN_NO_PLAYER_ROWS: 9
```

固定排除：

```text
2024-01-11 17:30 ET
```

原因：player PDF parsed，但 `single_report_ready=false`；team pre-tip QA failed。不得替換該 timestamp。

Formal decision：

```text
ready_for_feature_backfill = true
ready_for_model_training = false
ready_for_probability_adjustment = false
ready_for_betting_edge_claim = false
```

Wave 1／2 acquisition regressions 均通過。舊 registry 沒有 `cadence_days` 時仍使用 backward-compatible 14-day default。

## 下一個精確任務

```text
1. Filter Wave 3 panels to 44 ready overlaps
2. Gold schedule matching
3. Deterministic player identity
4. Prior-only Expected Minutes／Impact
5. Team submission reconciliation
6. Long and matchup injury burden
7. Frozen latest feature-ready at or before T-60
8. Deduplicate against Waves 1／2 by historical_game_id
9. Measure combined selected games and official participation-label sample counts
```

只有 expanded sample 確認足夠後，才可另外預先宣告 Expected Minutes Accuracy Audit v3。

## 永久邊界

- missing player row ≠ DNP／0 minutes。
- `SOURCE_MISSING`／`UNKNOWN` 不得補成 0。
- NYS、unknown、synthetic missing side 不視為健康。
- 只有明確 `SUBMITTED_NO_INJURIES` 才可建立 zero burden。
- 不使用 fuzzy identity。
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
