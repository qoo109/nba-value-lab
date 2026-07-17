# NBA Value Lab — Project Status

更新日期：2026-07-17  
目前定位：**Research Candidate／Pre-Market-Backtest**

本文件是研究管線的正式進度基準。根目錄 `README.md` 保留 V4.6／V3.1 × G1 FINAL 的 Legacy UI 與 Model Registry 說明；舊網站版本號不代表模型可投注、可獲利或能擊敗市場。

## 狀態定義

| 狀態 | 定義 |
|---|---|
| Completed | 實作、QA 與指定驗證已完成。 |
| Negative Result | 實驗完成但未通過 promotion gate；不得加入正式模型。 |
| Research Ready | 資料鏈可供下一階段研究；不可直接調整勝率或下注。 |
| Blocked | 缺資料、授權、樣本、timestamp 或正式 holdout。 |

## 核心研究狀態

| 模組 | 狀態 | 正式結論 |
|---|---|---|
| Five-season Historical Gold | Completed | 5,824 matchup rows；strict point-in-time、same-day exclusion、season reset 通過。 |
| Logistic + Elo Walk-forward v2 | Completed | 3,688 場 OOF；相對 Elo 的 Log Loss／Brier 有小幅且跨 Fold 一致改善。 |
| Probability Calibration Gate | Completed | Platt／Isotonic 未穩定改善，保留 raw Logistic + Elo。 |
| Closing Market Benchmark | Completed / model lost | 1,894 場成功配對；模型明顯輸給 Closing Market。 |
| Market Residual Analysis v1 | Negative Result | 時間留存選擇 100% Closing Market、0% 模型殘差。 |
| Rest／Travel／Schedule Context v1 | Negative Result | 2023–24 untouched holdout 未通過，不加入正式模型。 |
| Official NBA Injury Importer | Completed | 官方 PDF、publication time、SHA-256、跨頁解析與時間 QA 已建立。 |
| Injury Snapshot → Gold Game ID | Completed | 日期＋客隊＋主隊唯一對齊；不使用 fuzzy team matching。 |
| Player Identity Layer | Completed | Wave 1 99.1344%；Wave 2 98.9972%；0 ambiguous、0 fuzzy。 |
| Expected Minutes | Accuracy Audit Unlocked | Wave 1 coverage 92.7738%；Wave 2 coverage 91.4962%；176 場已解鎖 Accuracy Audit，但尚未驗證準確度。 |
| Player Impact Proxy | Research Proxy | prior-only 透明 box-score proxy；不是 RAPM、EPM 或官方 metric。 |
| Team Injury Burden v1 | Research Ready | point-in-time long／matchup burden 已建立；未啟用模型。 |
| Predeclared Snapshot Selection | Completed | Primary 固定為 latest feature-ready snapshot at or before T-60m。 |
| Injury Team Submission Status v1 | Research Ready | 缺報、NYS、unknown、synthetic side 不會補成健康。 |
| Wave 1 Acquisition | Completed | 36 固定時間；34 parsed player、33 team、31 overlap；12/12 日期。 |
| Wave 1 Features | Research Ready | frozen T-60 選出 91 場獨立比賽。 |
| Wave 2 Acquisition | Completed | 33 parsed player、31 player-ready、31 team、31 ready overlap；11 日期。 |
| Wave 2 Features | Research Ready | frozen T-60 選出 85 場獨立比賽。 |
| Combined Wave 1＋2 Selected Panel | Research Ready / 176 games | 0 跨 Wave 重複；176 場獨立比賽；Expected Minutes Accuracy Audit 已解鎖。 |
| Injury Feature Walk-forward Holdout | Blocked | 必須先完成並通過 Expected Minutes Accuracy Audit。 |
| Odds schema／source registry／import boundary | Completed | bookmaker、snapshot、去水、closing importer 與安全閘門已完成。 |
| Real Timestamped Odds Data | Blocked | 缺 opening／intraday／closing observation timestamp 資料本體。 |
| Executable Market Backtest | Blocked | Closing label 不能當可執行進場價；CLV／EV／ROI／Drawdown 未解鎖。 |
| Production Betting Decision Layer | Blocked | 正式 stake 固定為 0。 |

## 市場基準

成功配對的 1,894 場 Closing benchmark：

| 指標 | 模型 | Closing Market |
|---|---:|---:|
| Log Loss | 0.6421 | **0.6167** |
| Brier | 0.2250 | **0.2139** |
| Accuracy | 63.62% | **66.37%** |

> 模型目前能小幅擊敗 Elo，但沒有證據顯示它能擊敗或改善 NBA Closing Market。

Closing-only archive 沒有精確 observation timestamp，只能做 forecast benchmark；不能做 T-60 進場模擬、CLV、EV、ROI 或投注優勢宣稱。

## 已完成的負結果

### Rest／Travel／Schedule Context v1

已測試 rest days、back-to-back、3-in-4、4-in-6、5-in-8、previous-leg distance、seven-day distance、timezone direction、altitude gain、road-trip number、same-venue streak。

結果未通過 2023–24 untouched holdout。只有新增真正不同的資料，例如實際城市行程、航班時間、海拔暴露或球員級負荷，才重新評估。

### Market Residual Analysis v1

```text
Closing Market：100%
模型殘差：0%
```

不得把此負結果重新包裝成模型 edge。

## Injury 主線正式結果

### Pilot

```text
654 player snapshot rows
63 matchup snapshots
41 independent games
31 selected T-60 independent games
```

### Wave 1

Acquisition：

```text
36 calendar-fixed candidate reports
34 parsed player reports
33 team reports
31 player/team overlap reports
12 overlap dates
```

Full features：

```text
filtered player rows: 2,657
identity matched: 2,634 / 2,657
identity rate: 99.1344%
Expected Minutes／Impact rows: 2,465
coverage: 92.7738%
strict prior violations: 0
same-day rows excluded: 463
future rows excluded: 43,533
127 player-derived games
286 long matchup snapshots
162 reconciled games
91 frozen T-60 selected games
```

Wave 1 正式決定：

```text
ready_for_wave1_selected_panel_research = true
ready_for_expected_minutes_accuracy_audit = false
```

### Wave 2

Calendar registry：

```text
12 complementary Mondays
08:30 / 13:30 / 17:30 ET
36 candidate reports
0 requested-time overlap with Wave 1
```

Acquisition：

```text
33 player reports parsed
31 player reports single-report-ready
31 team reports successful
31 ready overlap reports
11 ready overlap dates
```

固定排除、不可替換：

```text
2023-12-25 13:30 ET — parsed but ready=false / team pre-tip QA failed
2023-12-25 17:30 ET — parsed but ready=false / team pre-tip QA failed
2024-02-19 08:30 ET — 403
2024-02-19 13:30 ET — 403
2024-02-19 17:30 ET — 403
```

Full features：

```text
filtered player rows: 2,493
filtered team rows: 862
player Gold match: 122 / 122
team Gold match: 153 / 153
identity matched: 2,468 / 2,493
identity rate: 98.9972%
Expected Minutes／Impact rows: 2,281
coverage: 91.4962%
strict prior violations: 0
same-day rows excluded: 371
future rows excluded: 42,104
122 player-derived games
269 long matchup snapshots
153 reconciled games
85 frozen T-60 selected games
```

Wave 2 selection：

```text
153 independent games represented
85 selected independent games
68 without selection
54 incomplete
14 feature unavailable
0 duplicate selected games
```

### Combined Wave 1＋2

Deduplication key：

```text
historical_game_id
```

Predeclared duplicate policy：

```text
matching date／teams／commence／frozen policy required
retain later eligible observed_at
identity or policy conflict blocks the game
```

Verified combined result：

```text
Wave 1 selected: 91
Wave 2 selected: 85
raw selected rows: 176
cross-wave duplicate games: 0
identity conflicts: 0
policy conflicts: 0
duplicate output games: 0
combined independent games: 176
```

Formal decision：

```text
ready_for_combined_selected_panel_research = true
ready_for_expected_minutes_accuracy_audit = true
ready_for_injury_feature_walk_forward_holdout = false
ready_for_model_training = false
ready_for_probability_adjustment = false
ready_for_betting_edge_claim = false
```

176 場只代表樣本量足以開始 Expected Minutes Accuracy Audit。它不代表 Expected Minutes 已準確，也不代表 Injury Feature 有效。

## Sample Gates

```text
combined selected independent games: 176
Expected Minutes Accuracy Audit gate: 100 — met
initial reliability target: 300 — not met
ideal target: 500 — not met
```

流程邊界：

```text
100+ selected games
→ Expected Minutes Accuracy Audit
→ Audit 通過
→ 才可設計 Injury Feature Walk-forward Holdout
→ Holdout 通過
→ 才可評估 Calibration／Residual promotion
```

不得從 176 場直接跳到模型啟用或下注。

## Frozen Snapshot Selection

Primary：

```text
latest feature-ready snapshot at or before T-60m
```

固定規則：

- both teams snapshot complete
- both teams feature-ready
- observed_at 至少早於 tip-off 60 分鐘
- latest eligible observed_at wins
- no fallback
- Not Yet Submitted／unknown／missing → no selection
- 多個 publication times 只算 1 場獨立比賽

Diagnostic policies 可比較 coverage，但不得在看 outcome 後取代 Primary。

## Injury 主線 Roadmap

已完成：

```text
Official Injury Importer
→ deterministic identity／prior-only values／team burden
→ Frozen T-60 Snapshot Selection
→ Team Submission Status
→ Wave 1 acquisition + full features
→ Wave 2 acquisition + full features
→ Wave 1＋2 deduplicated selected panel（176 games）
```

下一步：

```text
1. Predeclare Expected Minutes Accuracy Audit v1 gates
2. Rebuild player-level predictions for the selected 176 games
3. Join actual target-game minutes from Gold-validated boxscores
4. Evaluate overall and subgroup MAE／RMSE／median AE
5. Evaluate starter／bench／rookie／return-from-injury／status groups
6. Evaluate missingness, no-appearance and team-level error
7. Only if Audit passes, design Injury Walk-forward Holdout
```

## Expected Minutes Accuracy Audit — 必要邊界

尚未執行。至少必須：

- 僅使用 frozen selected 176 個獨立 game IDs；
- 每個 player prediction 必須在 target game 前產生；
- target-game actual minutes 只能作 label，不得回流到 prediction；
- starter、bench、rookie／no-history、復出球員分組；
- availability status 分組；
- actual DNP／inactive／未出場必須明確分類，不可一律當作 0 分鐘 prediction success；
- 報告 MAE、RMSE、median absolute error、bias 與 coverage；
- team-level minutes/burden aggregation error；
- 缺失值不得補 0；
- Audit 通過也不直接啟用模型，只解鎖 holdout 設計。

## Market 主線 Roadmap

已完成：

```text
Odds schema／source registry／import boundary
→ Closing-only benchmark
→ Market residual experiment
```

下一步：

```text
1. Real Timestamped Odds Acquisition／Backfill
2. Opening／6h／3h／1h／30m／Close
3. Bookmaker-level normalization
4. Point-in-time Odds Join
5. Executable Market Backtest
6. CLV／EV／ROI／Drawdown
```

真正缺的是合法、可稽核且帶 observation timestamp 的 odds 資料本體，不是再建立 registry 或 schema。

## 永久研究邊界

- 不使用同日、賽後或未來資料建立賽前特徵。
- 缺失值不隨意補成 0。
- 缺報、Not Yet Submitted、unknown、synthetic missing side 不視為健康。
- 只有明確 `SUBMITTED_NO_INJURIES` 才能建立 explicit zero burden。
- 不使用 fuzzy identity 或 nearest-name guessing。
- 多個 snapshots 不可冒充多場獨立比賽。
- parsed 不等於 single-report-ready；`ready=false` 不得進 feature pipeline。
- 固定 acquisition 失敗時間不可用手挑日期替換。
- 未完成 timestamped odds join 前，不宣稱 CLV、EV、ROI 或 executable edge。
- CI 綠燈只代表流程完成；必須讀 Artifact QA。
- 模型目前輸給 Closing Market，正式投注額維持 0。

## 重要 PR

- PR #28 — Closing benchmark correction
- PR #29 — Market Residual Analysis v1
- PR #30 — Rest／Travel context negative result
- PR #35 — Player Value & Expected Minutes v1
- PR #36 — Team Injury Burden v1
- PR #37 — Multi-report Injury Panel v1
- PR #38 — Injury Feature Residual Audit v1
- PR #39 — Research status／README correction
- PR #40 — Multi-report Injury Feature Backfill v1
- PR #41 — Injury Team Submission Status v1
- PR #42 — Wave 1 Acquisition Audit
- PR #43 — Wave 1 Full Features
- PR #44 — Wave 2 Acquisition + Ready Overlap Audit
- PR #45 — Wave 2 Full Features + Combined 176-game Panel
