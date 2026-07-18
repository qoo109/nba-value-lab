# NBA Value Lab — Project Status

更新日期：2026-07-18  
目前定位：**Research Candidate／Pre-Market-Backtest**

本文件是研究管線的正式進度基準。根目錄 `README.md` 保留 Legacy UI／Model Registry 說明；舊網站版本號不代表模型可投注、可獲利或能擊敗市場。

## 主線藍圖

專案後續固定以 `nba_value_lab_handoff_2026-07-17.md` 的順序為準。後續日期的 handoff 只記錄進度與阻塞，不得取代或重排這條主線：

```text
1. 擴充多日期、多時間點官方傷病快照
2. 累積至少 100 場獨立 feature-ready matchup
3. Expected Minutes Accuracy Audit
4. Injury Feature Walk-forward Holdout
5. Timestamped Odds Acquisition
6. Market Backtest
7. CLV／EV／ROI
8. Betting Decision Layer
```

目前所在節點：

```text
Step 3 — Expected Minutes Accuracy Audit 修復階段
```

Player Participation Label Layer v1 是 Step 3 的補充資料層，不是新的專案方向。

## 狀態定義

| 狀態 | 定義 |
|---|---|
| Completed | 實作、QA 與指定驗證完成。 |
| Negative Result | 實驗完成但未通過 promotion gate；不得加入正式模型。 |
| Research Ready | 資料鏈可供下一階段研究；不可直接調整勝率或下注。 |
| Structural Blocked | 安全與 point-in-time 規則通過，但 evaluation label／coverage 未達預先門檻。 |
| Blocked | 缺資料、授權、樣本、timestamp 或正式 holdout。 |

## 核心研究狀態

| 模組 | 狀態 | 正式結論 |
|---|---|---|
| Five-season Historical Gold | Completed | 5,824 matchup rows；strict point-in-time、same-day exclusion、season reset 通過。 |
| Logistic + Elo Walk-forward v2 | Completed | 3,688 場 OOF；相較 Elo 有小幅、跨 Fold 一致改善。 |
| Probability Calibration Gate | Completed | Platt／Isotonic 未穩定改善，保留 raw Logistic + Elo。 |
| Closing Market Benchmark | Completed / model lost | 1,894 場配對；模型明顯輸給 Closing Market。 |
| Market Residual Analysis v1 | Negative Result | 時間留存選擇 100% Closing Market、0% 模型殘差。 |
| Rest／Travel／Schedule Context v1 | Negative Result | 2023–24 untouched holdout 未通過。 |
| Official NBA Injury Importer | Completed | 官方 PDF、publication time、SHA-256、跨頁解析與時間 QA 已建立。 |
| Injury Snapshot → Gold Game ID | Completed | 日期＋客隊＋主隊唯一對齊；不使用 fuzzy team matching。 |
| Player Identity Layer | Completed | Wave 1 99.1344%；Wave 2 98.9972%；0 ambiguous、0 fuzzy。 |
| Expected Minutes | Research Proxy / Audit v1 Structural Blocked | v1 已執行；描述性數值門檻通過，但原 participation labels 不完整。 |
| Player Participation Label Layer v1 | Research Ready | 176／176 官方來源；1,832／1,834 matched-player joins；UNKNOWN 2.2901%；v2 inputs ready。 |
| Player Impact Proxy | Research Proxy | prior-only 透明 box-score proxy；不是 RAPM、EPM 或官方 metric。 |
| Team Injury Burden v1 | Research Ready | point-in-time long／matchup burden 已建立；未啟用模型。 |
| Frozen T-60 Snapshot Selection | Completed | Primary 固定為 latest feature-ready snapshot at or before T-60m。 |
| Injury Team Submission Status v1 | Research Ready | 缺報、NYS、unknown、synthetic side 不會補成健康。 |
| Wave 1 Acquisition | Completed | 36 固定時間；34 parsed player、33 team、31 overlap；12 日期。 |
| Wave 1 Features | Research Ready | frozen T-60 選出 91 場獨立比賽。 |
| Wave 2 Acquisition | Completed | 33 parsed player、31 player-ready、31 team、31 ready overlap；11 日期。 |
| Wave 2 Features | Research Ready | frozen T-60 選出 85 場獨立比賽。 |
| Combined Wave 1＋2 Selected Panel | Research Ready / 176 games | 0 跨 Wave 重複；176 場獨立比賽。 |
| Expected Minutes Accuracy Audit v2 | Next / Not Executed | 必須先預先宣告 v2 policy，再使用官方 participation labels 重跑。 |
| Injury Feature Walk-forward Holdout | Blocked | 必須先通過 Expected Minutes Accuracy Audit v2。 |
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
36 candidate reports
34 parsed player reports
33 team reports
31 ready overlap reports
12 overlap dates
filtered player rows: 2,657
identity matched: 2,634 / 2,657（99.1344%）
Expected Minutes／Impact rows: 2,465（92.7738%）
strict prior violations: 0
same-day rows excluded: 463
future rows excluded: 43,533
frozen T-60 selected games: 91
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
36 candidate reports
33 parsed player reports
31 player reports single-report-ready
31 team reports
31 ready overlap reports
11 ready overlap dates
filtered player rows: 2,493
identity matched: 2,468 / 2,493（98.9972%）
Expected Minutes／Impact rows: 2,281（91.4962%）
strict prior violations: 0
same-day rows excluded: 371
future rows excluded: 42,104
frozen T-60 selected games: 85
```

固定排除：

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

176 場代表 Steps 1–2 已達最低 Accuracy Audit 啟動門檻；不代表 Expected Minutes、Injury Feature 或 betting edge 已通過。

## Expected Minutes Accuracy Audit v1

正式狀態：

```text
AUDIT_EXECUTED_STRUCTURAL_BLOCKED
```

Frozen population：

```text
176 independent games
1,840 selected player snapshot rows
1,834 identity matched rows（99.6739%）
1,788 Expected Minutes rows（97.1739%）
481 target-game boxscore joins（26.2268%）
314 actual played rows
167 explicit DNP rows
1,359 missing target-game rows
```

描述性 subset（313 rows）：

```text
overall MAE: 5.0258 minutes
RMSE: 6.6313
median absolute error: 4.0650
bias: +0.8198
starter MAE: 4.7569
bench MAE: 5.4196
10+ prior-game MAE: 5.0339
improvement vs last prior game: +1.6768
improvement vs recent-10 mean: +0.0528
```

這些數字只能描述，不可寫成 Accuracy Audit pass。

## Player Participation Label Layer v1

Roadmap parent：

```text
Step 3 — Expected Minutes Accuracy Audit
```

Official source：

```text
NBA Official LiveData Boxscore
```

Verified workflow run：

```text
29626746364
```

正式 QA：

```text
requested selected games: 176
successful official games: 176
source coverage: 100%
official player rows: 6,198
selected player snapshot rows: 1,840
identity matched rows: 1,834（99.6739%）
participation label joins: 1,832 / 1,834（99.8909%）
source-missing games: 0
complete team-game groups: 345
```

Selected matched-player labels：

```text
PLAYED: 314
EXPLICIT_DNP: 28
INACTIVE_OR_NOT_DRESSED: 1,450
UNKNOWN: 42
UNKNOWN rate: 2.2901%
```

所有 frozen source／join／unknown／duplicate／team gates 通過。

正式決定：

```text
ready_for_expected_minutes_accuracy_audit_v2_inputs = true
ready_for_expected_minutes_accuracy_audit_v2 = false
ready_for_injury_feature_walk_forward_holdout_design = false
ready_for_injury_feature_walk_forward_holdout = false
ready_for_model_training = false
ready_for_probability_adjustment = false
ready_for_betting_edge_claim = false
```

## 下一個精確任務

仍在 7/17 主線 Step 3：

```text
1. Predeclare Expected Minutes Accuracy Audit v2 policy
2. 固定使用原 176 場 T-60 population
3. 使用 Player Participation Label Layer v1 作 target-game labels
4. Target labels 只可用於 evaluation，不得回流 prediction
5. 重跑 structural、overall、starter／bench、history、team-level accuracy gates
6. 只有 v2 pass 才可進 Injury Feature Walk-forward Holdout
```

目前不得提前進入 Timestamped Odds 或 Market Backtest；它們仍排在 Injury Feature Holdout 之後。

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
- 多個 publication times 只算一場獨立比賽。

Diagnostic policies 不得在看 outcome 後取代 Primary。

## Market 主線 Roadmap

在 Injury Feature Holdout 完成後才繼續：

```text
Real Timestamped Odds Acquisition／Backfill
→ Opening／6h／3h／1h／30m／Close
→ Bookmaker-level normalization
→ Point-in-time Odds Join
→ Executable Market Backtest
→ CLV／EV／ROI／Drawdown
```

真正缺的是合法、可稽核且帶 observation timestamp 的 odds 資料本體，不是再建立 registry 或 schema。

## 永久研究邊界

- 不使用同日、賽後或未來資料建立賽前特徵。
- Target-game participation／minutes 只可作 evaluation labels。
- 缺失 player row 不等於 DNP 或 0 分鐘。
- `SOURCE_MISSING`／`UNKNOWN` 不得補成 0。
- 缺報、Not Yet Submitted、unknown、synthetic missing side 不視為健康。
- 只有明確 `SUBMITTED_NO_INJURIES` 才能建立 explicit zero burden。
- 不使用 fuzzy identity 或 nearest-name guessing。
- 多個 snapshots 不可冒充多場獨立比賽。
- parsed 不等於 single-report-ready；`ready=false` 不得進 feature pipeline。
- 固定 acquisition 失敗時間不可用手挑日期替換。
- Accuracy Audit v2 未通過前，不進 Injury Holdout。
- Injury Holdout 未通過前，不進 Timestamped Odds 主線執行。
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
- PR #47 — Expected Minutes Accuracy Audit v1 / Structural Blocked
- PR #48 — Player Participation Label Layer v1
