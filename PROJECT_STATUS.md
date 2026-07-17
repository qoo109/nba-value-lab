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
| Player Identity Layer | Completed | Wave 1：2,634/2,657 high-confidence，99.1344%；0 ambiguous、0 fuzzy。 |
| Expected Minutes | Research Proxy / Blocked Audit | Wave 1 prior-only coverage 92.7738%；Accuracy Audit 尚未解鎖。 |
| Player Impact Proxy | Research Proxy | Wave 1 coverage 92.7738%；透明 box-score proxy，不是 RAPM、EPM 或官方 metric。 |
| Team Injury Burden v1 | Research Ready | point-in-time long／matchup burden 已建立；未啟用模型。 |
| Predeclared Snapshot Selection | Completed | Primary 固定為 latest feature-ready snapshot at or before T-60m。 |
| Multi-report Injury Feature Pilot | Research Ready | Pilot：63 long snapshots、41 場獨立比賽、31 場 selected。 |
| Injury Team Submission Status v1 | Research Ready | 缺報、NYS、unknown 與 synthetic side 不會補成健康。 |
| Injury Backfill Wave 1 Acquisition | Completed | 36 固定時間；34 player、33 team、31 overlap；12/12 日期。 |
| Injury Backfill Wave 1 Features | Research Ready / 91 of 100 | 結構 QA 全通過；frozen T-60 選出 91 場，未達 Accuracy Audit 門檻。 |
| Injury Feature Residual Audit v1 | Research Ready | 7 場方向符合預期，但樣本不足。 |
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
52 complete matchup snapshots
46 feature-ready matchup snapshots
31 selected T-60 independent games
```

### Team submission pilot

```text
7 / 7 official reports
204 team submission rows
72 independent games represented
115 SUBMITTED_WITH_PLAYER_ROWS
87 NOT_YET_SUBMITTED
2 UNKNOWN_NO_PLAYER_ROWS synthetic sides
0 conflicts
31 selected T-60 independent games
```

Team ledger 提升來源完整度，沒有灌大 trainable sample。`NOT_YET_SUBMITTED`、unknown、synthetic missing side 與缺失資料均未補成健康或零負擔。

### Wave 1 calendar-fixed acquisition

Registry：

```text
2023-24 Mondays every 14 days
12 dates
08:30 / 13:30 / 17:30 ET
36 candidate reports
```

Acquisition：

```text
player successes: 34 / 36
team successes: 33 / 36
overlap successes: 31 / 36
overlap dates: 12 / 12
player normalized rows before deletion: 2,942
player ingestion games: 131
team submission rows: 888
team ingestion games: 162
```

固定失敗時間不可用手挑日期替換：

```text
Player failures
- 2024-04-08 08:30 ET
- 2024-04-08 13:30 ET

Team failures
- 2024-01-01 17:30 ET
- 2024-01-15 13:30 ET
- 2024-01-15 17:30 ET
```

### Wave 1 full feature backfill

只有 player／team 同時成功的 31 個 publication times 進入 feature chain。

Overlap：

```text
filtered player rows: 2,657
filtered team rows: 832
player-ingestion games: 127
team-ledger games: 162
observed-at mismatches: 0
rows outside overlap: 0
```

Gold mapping：

```text
player games matched: 127 / 127
team games matched: 162 / 162
unmatched games: 0
duplicate Gold keys: 0
```

Identity：

```text
matched: 2,634 / 2,657
match rate: 99.1344%
high-confidence rate: 99.1344%
unmatched: 23
ambiguous: 0
fuzzy matches: 0
```

Prior-only values：

```text
Expected Minutes rows: 2,465
Player Impact rows: 2,465
coverage: 92.7738%
players without prior history: 169
strict prior violations: 0
same-day rows excluded: 463
future rows excluded: 43,533
```

Long panel：

```text
127 player-derived independent games
286 long matchup snapshots
236 complete snapshots
191 feature-ready snapshots
0 nonpregame observations
0 duplicate snapshots
```

Team reconciliation：

```text
832 team rows
416 matchup snapshots
162 independent games represented
236 complete snapshots
191 feature-ready snapshots
305 NOT_YET_SUBMITTED
522 SUBMITTED_WITH_PLAYER_ROWS
5 UNKNOWN_NO_PLAYER_ROWS
0 reconciliation errors
0 missing ledgers
0 side errors
```

Frozen T-60 selection：

```text
independent games represented: 162
selected independent games: 91
games without selection: 71
selection rate: 56.1728%
incomplete: 56
feature unavailable: 15
duplicate selected games: 0
```

Diagnostic policies：

```text
latest feature-ready pre-tip: 91
latest feature-ready at or before T-180m: 88
```

Diagnostics 不得在看過 outcome 後取代 Primary。

## Sample Gates

```text
Wave 1 selected: 91
minimum Expected Minutes Accuracy Audit gate: 100
shortfall: 9
initial reliability: 300
ideal target: 500
```

目前正式判定：

```text
ready_for_wave1_selected_panel_research = true
ready_for_expected_minutes_accuracy_audit = false
ready_for_injury_feature_walk_forward_holdout = false
ready_for_model_training = false
ready_for_probability_adjustment = false
ready_for_betting_edge_claim = false
```

100 場只解鎖 **Expected Minutes Accuracy Audit**，不會直接解鎖 Injury Holdout。Expected Minutes Audit 通過後，才可建立 holdout promotion gate。

## Injury 主線 Roadmap

已完成：

```text
Official Injury Importer
→ Single-report identity／value／team burden
→ Multi-report Injury Panel v1
→ Frozen T-60 Snapshot Selection
→ Team Submission Status v1
→ Wave 1 calendar-fixed acquisition
→ Wave 1 full feature backfill
```

下一步：

```text
1. Wave 2 calendar-fixed acquisition（不可手挑補 9 場）
2. Wave 2 full feature backfill
3. 合併 Wave 1＋Wave 2，依 game_id 去重
4. frozen T-60 selected panel
5. 達 100 場才執行 Expected Minutes Accuracy Audit
6. Accuracy Audit 通過後才設計 Injury Walk-forward Holdout
7. Holdout 通過後才評估 Calibration／Residual
```

不得降低 100 場門檻、把 repeated snapshots 當新比賽、把 diagnostic policy 升為 Primary，或挑選最有利日期補齊 9 場。

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

## 兩條主線匯合

```text
Point-in-time Model
＋ Selected Point-in-time Injury
＋ Executable Point-in-time Odds
→ True Market Backtest
→ Holdout EV／CLV／ROI
```

## 後續候選，不是目前主線

- Lineup Continuity
- Usage Redistribution
- Rotation Stability
- Referee Tendency：僅限授權清楚、歷史完整、可 point-in-time 驗證的來源
- 更精細的球員級旅行與負荷資料

## 永久研究邊界

- 不使用同日、賽後或未來資料建立賽前特徵。
- 缺失值不隨意補成 0。
- 缺報、Not Yet Submitted、unknown、synthetic missing side 不視為健康。
- 只有明確 `SUBMITTED_NO_INJURIES` 才能建立 explicit zero burden。
- 不使用 fuzzy identity 或 nearest-name guessing。
- 多個 snapshots 不可冒充多場獨立比賽。
- 固定 acquisition 失敗時間不可用手挑日期替換。
- 未完成 timestamped odds join 前，不宣稱 CLV、EV、ROI 或 executable edge。
- CI 綠燈只代表流程完成；必須讀 Artifact QA。
- 模型目前輸給 Closing Market，正式投注額維持 0。

## Housekeeping

- [x] `PROJECT_STATUS.md` 作為正式基準
- [x] README 分離 Legacy UI 與 Research Pipeline
- [x] Completed／Negative Result／Research Ready／Blocked 分區
- [x] 重要 PR 同步正式 QA 數字
- [ ] 視需要關閉被後續主線取代的早期草稿 PR

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
- PR #42 — Injury Backfill Wave 1 Acquisition Audit
- PR #43 — Injury Backfill Wave 1 Full Features
