# NBA Value Lab — Project Status

更新日期：2026-07-18  
目前定位：**Research Candidate／Pre-Market-Backtest**

本文件是研究管線的正式進度基準。根目錄 `README.md` 保留 Legacy UI／Model Registry 說明；舊網站版本號不代表模型可投注、可獲利或能擊敗市場。

## 主線藍圖

後續固定以 `nba_value_lab_handoff_2026-07-17.md` 為主線。後續 handoff 只更新進度與阻塞，不得取代或重排：

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
Steps 1–3 — 擴充 Expected Minutes Audit 的獨立樣本
```

原因：Player Participation Label Layer v1 已修正 target-game label 缺口；Accuracy Audit v2 已執行，但保留的樣本量 gates 未達。下一步是擴充官方傷病快照與獨立 selected games，不是進 Holdout 或 Odds。

## 狀態定義

| 狀態 | 定義 |
|---|---|
| Completed | 實作、QA 與指定驗證完成。 |
| Negative Result | 實驗完成但未通過 promotion gate；不得加入正式模型。 |
| Research Ready | 資料鏈可供下一階段研究；不可直接調整勝率或下注。 |
| Structural Blocked | 安全、來源與 point-in-time 規則通過，但必要樣本或 evaluation coverage 未達預先門檻。 |
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
| Player Participation Label Layer v1 | Research Ready | 176／176 官方來源；1,832／1,834 matched-player joins；UNKNOWN 2.2901%。 |
| Expected Minutes Accuracy Audit v1 | Structural Blocked | target-game participation labels 不完整；描述性 accuracy 不可 promotion。 |
| Expected Minutes Accuracy Audit v2 | Structural Blocked | 官方 labels、來源與所有 numerical gates 通過，但 4 個 preserved sample gates 未達。 |
| Expected Minutes Expanded Sample | Next | 需要擴充到約 280–300 場獨立 frozen T-60 selected games，再預先宣告新 audit。 |
| Player Impact Proxy | Research Proxy | prior-only 透明 box-score proxy；不是 RAPM、EPM 或官方 metric。 |
| Team Injury Burden v1 | Research Ready | point-in-time long／matchup burden 已建立；未啟用模型。 |
| Frozen T-60 Snapshot Selection | Completed | Primary 固定為 latest feature-ready snapshot at or before T-60m。 |
| Injury Team Submission Status v1 | Research Ready | 缺報、NYS、unknown、synthetic side 不會補成健康。 |
| Wave 1 Features | Research Ready | frozen T-60 選出 91 場獨立比賽。 |
| Wave 2 Features | Research Ready | frozen T-60 選出 85 場獨立比賽。 |
| Combined Wave 1＋2 Panel | Research Ready / 176 games | 0 跨 Wave 重複；作為 Audit v1／v2 的 frozen population。 |
| Injury Feature Walk-forward Holdout | Blocked | 必須先通過 expanded-sample Expected Minutes Accuracy Audit。 |
| Odds schema／source registry／import boundary | Completed | bookmaker、snapshot、去水、closing importer 與安全閘門已完成。 |
| Real Timestamped Odds Data | Blocked | 依主線排在 Injury Feature Holdout 之後；目前尚未執行。 |
| Executable Market Backtest | Blocked | Closing label 不能當可執行進場價；CLV／EV／ROI／Drawdown 未解鎖。 |
| Production Betting Decision Layer | Blocked | 正式 stake 固定為 0。 |

## 市場基準

成功配對 1,894 場：

| 指標 | 模型 | Closing Market |
|---|---:|---:|
| Log Loss | 0.6421 | **0.6167** |
| Brier | 0.2250 | **0.2139** |
| Accuracy | 63.62% | **66.37%** |

> 模型目前能小幅擊敗 Elo，但沒有證據顯示能擊敗或改善 NBA Closing Market。

Closing-only archive 沒有精確 observation timestamp，只能做 forecast benchmark；不能做 T-60 進場模擬、CLV、EV、ROI 或投注優勢宣稱。

## 已完成的負結果

### Rest／Travel／Schedule Context v1

已測試 rest days、back-to-back、3-in-4、4-in-6、5-in-8、previous-leg distance、seven-day distance、timezone direction、altitude gain、road-trip number、same-venue streak。

2023–24 untouched holdout 未通過。除非新增真正不同的資料，例如實際城市行程、航班時間、海拔暴露或球員級負荷，否則不得重做。

### Market Residual Analysis v1

```text
Closing Market：100%
模型殘差：0%
```

不得重新包裝成模型 edge。

## Injury 樣本進度

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
2,657 filtered player rows
2,634 identity matched（99.1344%）
2,465 Expected Minutes／Impact rows（92.7738%）
strict prior violations: 0
frozen T-60 selected games: 91
```

### Wave 2

```text
36 candidate reports
33 parsed player reports
31 player reports single-report-ready
31 team reports
31 ready overlap reports
11 ready overlap dates
2,493 filtered player rows
2,468 identity matched（98.9972%）
2,281 Expected Minutes／Impact rows（91.4962%）
strict prior violations: 0
frozen T-60 selected games: 85
```

### Combined Wave 1＋2

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

176 場已超過最低 100 場啟動門檻，但最低啟動不等於足以通過每個 player-level sample gate。

## Player Participation Label Layer v1

Official source：NBA Official LiveData Boxscore  
Verified run：`29627052148`

```text
requested selected games: 176
successful official games: 176
source coverage: 100%
official player rows: 6,198
selected player snapshot rows: 1,840
identity matched rows: 1,834（99.6739%）
participation joins: 1,832 / 1,834（99.8909%）
source-missing games: 0
```

Selected matched-player labels：

```text
PLAYED: 314
EXPLICIT_DNP: 28
INACTIVE_OR_NOT_DRESSED: 1,450
UNKNOWN: 42
UNKNOWN rate: 2.2901%
```

正式決定：

```text
ready_for_expected_minutes_accuracy_audit_v2_inputs = true
ready_for_expected_minutes_accuracy_audit_v2 = false
ready_for_injury_feature_walk_forward_holdout = false
```

## Expected Minutes Accuracy Audit v2

Predeclared policy commit：

```text
4591c1d682f638cc7186a73f4707c01eea7e9b15
```

Verified workflow run：

```text
29627677190
```

Artifact：

```text
expected-minutes-accuracy-audit-v2
artifact id: 8424436361
digest: sha256:7be8933b6d0aece1cf4dfa1c329dd2d82d75fb37db0f1ffe7f555af26aed1761
```

正式狀態：

```text
STRUCTURAL_BLOCKED
```

Coverage：

```text
combined selected games: 176
games with conditional role rows: 135
selected player rows: 1,840
identity match rate: 99.6739%
Expected Minutes coverage: 97.1739%
official source coverage: 100%
participation join rate: 99.8909%
UNKNOWN rate: 2.2901%
source-missing games: 0
conditional role rows: 313
starter rows: 186
bench rows: 127
long-history rows: 305
complete team-game groups: 278
```

Failed preserved sample gates：

```text
evaluable games: 135 / 150
conditional role rows: 313 / 500
bench rows: 127 / 200
10+ prior-game rows: 305 / 400
```

Passed：

- official source／join／UNKNOWN／missing gates；
- identity／Expected Minutes coverage；
- starter minimum；
- complete team-game group minimum；
- strict prior-date、duplicate、team、label consistency、privacy gates；
- **所有 preserved numerical accuracy gates**。

Descriptive primary metrics：

```text
overall n: 313
MAE: 5.025591
RMSE: 6.631056
median AE: 4.064807
bias: +0.819810
starter MAE: 4.756906
bench MAE: 5.419096
10+ history MAE: 5.033709
improvement vs last game: +1.676415
improvement vs recent-10: +0.052660
team played-role aggregate MAE: 6.579170
```

這些數字仍是 descriptive only，因 structural sample gates 未通過。

正式決定：

```text
expected_minutes_accuracy_audit_v2_passed = false
ready_for_injury_feature_walk_forward_holdout_design = false
ready_for_injury_feature_walk_forward_holdout = false
ready_for_model_training = false
ready_for_probability_adjustment = false
ready_for_betting_edge_claim = false
```

## 下一個精確任務

v2 的 176-game policy 已凍結且完成，不能事後改成更多場。

後續仍沿 7/17 主線，在 Steps 1–3 補足樣本：

```text
1. Predeclare Wave 3 acquisition calendar and exclusion rules
2. 擴充更多日期與官方 publication times
3. 沿用 Team Submission Status 與 frozen T-60 selection
4. 與 Wave 1／2 依 historical_game_id 去重
5. 目標 combined selected 約 280–300 場
6. 重新預先宣告 expanded-sample Expected Minutes Accuracy Audit
7. 只有新 Audit pass 才進 Injury Feature Walk-forward Holdout
```

約 280–300 場是依目前 313／500 played rows 與 127／200 bench rows 的缺口估算，也符合原本 300+ 初步可靠度目標。它不是降低 gate，也不是改寫主線。

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

## Market 主線

只有 Injury Feature Holdout 通過後才繼續：

```text
Real Timestamped Odds Acquisition／Backfill
→ Opening／6h／3h／1h／30m／Close
→ Bookmaker-level normalization
→ Point-in-time Odds Join
→ Executable Market Backtest
→ CLV／EV／ROI／Drawdown
```

## 永久研究邊界

- 7/17 handoff 是主線；後續 handoff 只記錄進度。
- 不使用同日、賽後或未來資料建立賽前特徵。
- Target-game participation／minutes 只可作 evaluation labels。
- 缺失 player row 不等於 DNP 或 0 分鐘。
- `SOURCE_MISSING`／`UNKNOWN` 不得補成 0。
- 缺報、NYS、unknown、synthetic missing side 不視為健康。
- 只有明確 `SUBMITTED_NO_INJURIES` 才建立 explicit zero burden。
- 不使用 fuzzy identity 或 nearest-name guessing。
- 多個 snapshots 不可冒充多場獨立比賽。
- 不得事後降低 v1／v2 sample 或 numerical gates。
- Audit 未通過前，不進 Injury Holdout。
- Injury Holdout 未通過前，不執行 Timestamped Odds 主線。
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
- PR #49 — Expected Minutes Accuracy Audit v2 / Structural Blocked
