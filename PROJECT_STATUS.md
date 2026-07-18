# NBA Value Lab — Project Status

更新日期：2026-07-18  
目前定位：**Research Candidate／Pre-Market-Backtest**

本文件是研究管線的正式進度基準。根目錄 `README.md` 保留 V4.6／V3.1 × G1 FINAL 的 Legacy UI 與 Model Registry 說明；舊網站版本號不代表模型可投注、可獲利或能擊敗市場。

## 狀態定義

| 狀態 | 定義 |
|---|---|
| Completed | 實作、QA 與指定驗證已完成。 |
| Negative Result | 實驗完成但未通過 promotion gate；不得加入正式模型。 |
| Research Ready | 資料鏈可供下一階段研究；不可直接調整勝率或下注。 |
| Structural Blocked | 安全與 point-in-time 規則通過，但必要的 evaluation label／coverage 未達預先門檻。 |
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
| Expected Minutes | Research Proxy / Structural Blocked | v1 Accuracy Audit 已執行；數值門檻描述性通過，但 participation-label coverage 未達 6 個 frozen structural gates。 |
| Player Impact Proxy | Research Proxy | prior-only 透明 box-score proxy；不是 RAPM、EPM 或官方 metric。 |
| Team Injury Burden v1 | Research Ready | point-in-time long／matchup burden 已建立；未啟用模型。 |
| Frozen T-60 Snapshot Selection | Completed | Primary 固定為 latest feature-ready snapshot at or before T-60m。 |
| Injury Team Submission Status v1 | Research Ready | 缺報、NYS、unknown、synthetic side 不會補成健康。 |
| Wave 1 Acquisition | Completed | 36 固定時間；34 parsed player、33 team、31 overlap；12/12 日期。 |
| Wave 1 Features | Research Ready | frozen T-60 選出 91 場獨立比賽。 |
| Wave 2 Acquisition | Completed | 33 parsed player、31 player-ready、31 team、31 ready overlap；11 日期。 |
| Wave 2 Features | Research Ready | frozen T-60 選出 85 場獨立比賽。 |
| Combined Wave 1＋2 Selected Panel | Research Ready / 176 games | 0 跨 Wave 重複；176 場獨立比賽。 |
| Player Participation Label Layer | Blocked / Next | 需要完整區分 played、explicit DNP、inactive／not dressed、source missing。 |
| Injury Feature Walk-forward Holdout | Blocked | Expected Minutes v1 未通過 structural coverage；不得設計或執行 holdout。 |
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

```text
36 calendar-fixed candidate reports
34 parsed player reports
33 team reports
31 player/team overlap reports
12 overlap dates
filtered player rows: 2,657
identity matched: 2,634 / 2,657（99.1344%）
Expected Minutes／Impact rows: 2,465（92.7738%）
strict prior violations: 0
same-day rows excluded: 463
future rows excluded: 43,533
91 frozen T-60 selected games
```

固定排除：

```text
2024-01-01 17:30 ET — parsed but ready=false / team pre-tip QA failed
2024-01-15 13:30 ET — parsed but ready=false / team pre-tip QA failed
2024-01-15 17:30 ET — parsed but ready=false / team pre-tip QA failed
2024-04-08 08:30 ET — NYS-only / no player rows
2024-04-08 13:30 ET — NYS-only / no player rows
```

### Wave 2

```text
36 calendar-fixed candidate reports
33 player reports parsed
31 player reports single-report-ready
31 team reports successful
31 ready overlap reports
11 ready overlap dates
filtered player rows: 2,493
identity matched: 2,468 / 2,493（98.9972%）
Expected Minutes／Impact rows: 2,281（91.4962%）
strict prior violations: 0
same-day rows excluded: 371
future rows excluded: 42,104
85 frozen T-60 selected games
```

固定排除、不可替換：

```text
2023-12-25 13:30 ET — parsed but ready=false / team pre-tip QA failed
2023-12-25 17:30 ET — parsed but ready=false / team pre-tip QA failed
2024-02-19 08:30 ET — 403
2024-02-19 13:30 ET — 403
2024-02-19 17:30 ET — 403
```

### Combined Wave 1＋2

Deduplication key：`historical_game_id`

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

正式決定：

```text
ready_for_combined_selected_panel_research = true
ready_for_expected_minutes_accuracy_audit = true
ready_for_injury_feature_walk_forward_holdout = false
ready_for_model_training = false
ready_for_probability_adjustment = false
ready_for_betting_edge_claim = false
```

## Expected Minutes Accuracy Audit v1

正式狀態：

```text
AUDIT_EXECUTED_STRUCTURAL_BLOCKED
```

Verified Workflow run：`29624463032`

### Frozen population

```text
176 deduplicated independent games
selection: latest feature-ready snapshot at or before T-60m
selected player snapshot rows: 1,840
```

### Dataset coverage

```text
selected games with accuracy rows: 176
identity matched rows: 1,834 / 1,840（99.6739%）
Expected Minutes rows: 1,788 / 1,840（97.1739%）
target-game boxscore join rows: 481 / 1,834（26.2268%）
actual played rows: 314
explicit DNP rows: 167
missing target-game boxscore rows: 1,359
```

通過的安全與 point-in-time gates：

- exactly 176 selected games；
- selected player rows ≥ 1,500；
- identity match rate；
- Expected Minutes coverage；
- starter sample minimum；
- strict prior-date violations = 0；
- duplicate selected games = 0；
- duplicate accuracy rows = 0；
- target-game labels 未進入 prediction；
- missing actual／Expected Minutes 未補 0；
- final Artifact 不保留 player names、reasons、identity maps、player values、boxscores、raw PDFs 或 player-level accuracy rows。

未通過的 frozen structural coverage gates：

```text
minimum evaluable games: 135 / 150
actual boxscore join rate: 26.2268% / 90%
conditional role rows: 313 / 500
actual bench rows: 127 / 200
long-history rows: 305 / 400
complete team-game groups: 5 / 100
```

目前 secondary boxscore archive 無法替所有 injury-listed players 提供完整的 target-game participation label。缺 row 不可推定為 DNP，也不可補成 0。

### 描述性 accuracy，不可 promotion

313 個有 matched target-game appearance label 的 rows：

```text
overall MAE: 5.0258 minutes
RMSE: 6.6313 minutes
median absolute error: 4.0650 minutes
bias: +0.8198 minutes
starter MAE: 4.7569 minutes
bench MAE: 5.4196 minutes
10+ prior-game MAE: 5.0339 minutes
MAE improvement vs last prior game: +1.6768 minutes
MAE improvement vs recent-10 mean: +0.0528 minutes
```

所有 numerical accuracy thresholds 在目前可評估 subset 內均通過，但因 structural label coverage 不完整，這些數字只能作描述，不構成 Accuracy Audit pass。

正式決定：

```text
expected_minutes_accuracy_audit_passed = false
ready_for_injury_feature_walk_forward_holdout_design = false
ready_for_injury_feature_walk_forward_holdout = false
ready_for_model_training = false
ready_for_probability_adjustment = false
ready_for_betting_edge_claim = false
```

v1 的 frozen gates 不因看見結果而放寬。

## Frozen Snapshot Selection

Primary：

```text
latest feature-ready snapshot at or before T-60m
```

固定規則：

- both teams snapshot complete；
- both teams feature-ready；
- observed_at 至少早於 tip-off 60 分鐘；
- latest eligible observed_at wins；
- no fallback；
- Not Yet Submitted／unknown／missing → no selection；
- 多個 publication times 只算 1 場獨立比賽。

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
→ Expected Minutes Accuracy Audit v1（Structural Blocked）
```

下一步：

```text
1. Predeclare Player Participation Label Layer v1 source and status contract
2. Acquire complete target-game labels: played／explicit DNP／inactive／not dressed／source missing
3. Gold-validate game, team, player identity and target-game timing
4. Keep missing source coverage separate from DNP and zero minutes
5. Predeclare Expected Minutes Accuracy Audit v2 before reading new accuracy results
6. Re-run on the same frozen 176-game population or a separately frozen expansion
7. Only if v2 structural + accuracy gates pass, design Injury Feature Walk-forward Holdout
```

不得從描述性 MAE 直接跳到 holdout、模型啟用或下注。

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
- Target-game labels 只作 evaluation，不得回流 prediction。
- 缺失值不隨意補成 0。
- Missing participation row 不可推定為 DNP／inactive／zero minutes。
- 缺報、Not Yet Submitted、unknown、synthetic missing side 不視為健康。
- 只有明確 `SUBMITTED_NO_INJURIES` 才能建立 explicit zero burden。
- 不使用 fuzzy identity 或 nearest-name guessing。
- 多個 snapshots 不可冒充多場獨立比賽。
- parsed 不等於 single-report-ready；`ready=false` 不得進 feature pipeline。
- 固定 acquisition 失敗時間不可用手挑日期替換。
- Audit numerical subset 通過不等於 structural audit 通過。
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
- PR #47 — Expected Minutes Accuracy Audit v1（Structural Blocked）
