# NBA Value Lab — Project Status

更新日期：2026-07-17  
目前定位：**Research Candidate／Pre-Market-Backtest**  
研究基準：以本文件「重要 PR」中最新已合併項目為準，不再用網站版本號判定研究成熟度。

本文件是研究管線的正式進度基準。根目錄 `README.md` 仍保留 V4.6／V3.1 × G1 FINAL 的 Legacy UI 與 Model Registry 說明；該版本號不代表目前模型是否可投注或能擊敗市場。

## 狀態定義

| 狀態 | 定義 |
|---|---|
| Completed | 已完成實作、QA 與指定驗證。 |
| Negative Result | 實驗已完成，但未通過 promotion gate；不得加入正式模型。 |
| Research Ready | 資料鏈或研究 proxy 可供下一階段實驗，但不可直接啟用模型、調整勝率或宣稱投注優勢。 |
| Blocked | 因缺少資料、授權、樣本、精確 timestamp 或正式 holdout 而無法啟用。 |

## 核心研究狀態

| 模組 | 狀態 | 目前結論 |
|---|---|---|
| Five-season Historical Gold | Completed | 5,824 matchup rows；strict point-in-time、same-day exclusion 與 season reset 通過。 |
| Logistic + Elo Walk-forward v2 | Completed | 3,688 場 OOF；相對 Elo 的 Log Loss 與 Brier 有小幅且跨 Fold 一致改善。 |
| Probability Calibration Gate | Completed | Platt／Isotonic 未穩定改善，因此保留 raw Logistic + Elo。 |
| Closing Market Benchmark | Completed / model lost to market | 1,894 場成功配對；模型明顯輸給 Closing Market。 |
| Market Residual Analysis v1 | Negative Result | 時間留存選擇 100% Closing Market、0% 模型殘差；不支持把模型加入 Closing Market。 |
| Rest／Travel／Schedule Context v1 | Negative Result | 已完成 2023–24 untouched holdout，未通過 promotion gate；基礎版本不得重做或加入正式模型。 |
| Official NBA Injury Importer | Completed | 官方 PDF、publication time、SHA-256、跨頁解析與時間戳 QA 已建立。 |
| Injury Snapshot → Gold Game ID | Completed | 官方 schedule key 可唯一對齊 Historical Gold；不使用 fuzzy team matching。 |
| Player Identity Layer | Completed | 單份 pilot 117/118；Multi-report pilot 649/654，0 ambiguous、0 fuzzy guessing。 |
| Expected Minutes | Research Ready / Research Proxy | prior-only 規則已建立；Multi-report coverage 606/654，但尚未完成 accuracy audit。 |
| Player Impact Proxy | Research Ready / Research Proxy | 透明 box-score proxy，不是 RAPM、EPM 或官方 metric。 |
| Team Injury Burden v1 | Research Ready | 單份 pilot 11 場、7 場 feature-ready；未啟用模型。 |
| Multi-report Injury Panel v1 | Research Ready | 6 份成功球員報告、4 個日期、654 列、41 場 player-ingestion coverage。 |
| Predeclared Snapshot Selection Policy | Completed | Primary policy 固定為 latest feature-ready snapshot at or before T-60m；不得看結果後改政策。 |
| Multi-report Injury Feature Backfill v1 | Research Ready | 63 個 long matchup snapshots、41 場獨立比賽；固定 T-60 選出 31 場。 |
| Injury Team Submission Status v1 | Research Ready | 7/7 官方報告、204 team rows、72 場；87 Not Yet Submitted、2 unknown synthetic；仍只選出 31 場。 |
| Injury Feature Residual Audit v1 | Research Ready | 7 場的殘差方向符合預期，但樣本不足；訓練、勝率調整與 betting edge 全部禁用。 |
| Odds schema／source registry／import boundary | Completed | 已建立 bookmaker、snapshot、去水機率、closing-only importer 與安全閘門。 |
| Real Timestamped Odds Data | Blocked | 尚未取得可稽核的 opening／intraday／closing observation timestamps 資料本體。 |
| Executable Market Backtest | Blocked | Closing label 不能當作可執行進場價；ROI、CLV、EV、Drawdown 尚不可計算。 |
| Production Betting Decision Layer | Blocked | 正式 stake 固定為 0；不得宣稱穩定 edge 或獲利能力。 |

## 重要市場基準

在成功配對的 1,894 場 Closing benchmark 中：

| 指標 | 模型 | Closing Market |
|---|---:|---:|
| Log Loss | 0.6421 | **0.6167** |
| Brier | 0.2250 | **0.2139** |
| Accuracy | 63.62% | **66.37%** |

正確結論：

> 模型目前能小幅擊敗 Elo，但沒有證據顯示它能擊敗或改善 NBA Closing Market。

Closing-only archive 沒有精確 observation timestamp，因此只能做 forecast benchmark，不能做 T-60m 進場模擬、ROI、CLV 或投注優勢宣稱。

## 已完成的負結果

### Rest／Travel／Schedule Context v1

已測試：

- rest days
- back-to-back
- 3-in-4、4-in-6、5-in-8
- previous-leg distance
- seven-day distance
- timezone direction
- altitude gain
- road-trip number
- same-venue streak

結果未通過 2023–24 untouched holdout，因此暫不加入正式模型。只有在新增更精細、真正不同的資料，例如實際城市行程、起飛時間、海拔暴露時數或球員級負荷後，才重新評估。

### Market Residual Analysis v1

時間留存混合測試選擇：

```text
Closing Market：100%
模型殘差：0%
```

這是已完成的負結果，不得為了追求複雜度而重新包裝成模型 edge。

## Injury 主線目前正式結果

### Player-derived long panel

```text
654 player snapshot rows
63 matchup snapshots
41 independent games
52 complete matchup snapshots
46 feature-ready matchup snapshots
31 selected T-60 independent games
```

同一場比賽的多個 publication times 只能作狀態轉換研究，不能冒充多個 holdout 樣本。

### Team submission ledger

```text
7 / 7 requested official reports succeeded
204 team submission rows
72 independent games represented
115 SUBMITTED_WITH_PLAYER_ROWS
87 NOT_YET_SUBMITTED
2 UNKNOWN_NO_PLAYER_ROWS synthetic missing sides
0 submission conflicts
```

所有 204 team rows 與 72 場比賽均唯一對齊 Historical Gold。

Reconciliation 後：

```text
102 matchup snapshots
72 independent games represented
52 complete matchup snapshots
46 feature-ready matchup snapshots
31 selected T-60 independent games
```

Team ledger 增加了可稽核的來源覆蓋，但沒有增加 feature-ready selected 樣本。這是正確結果：`NOT_YET_SUBMITTED`、unknown、synthetic missing side 與缺失資料均未被補成健康或零負擔。

目前 pilot 沒有明確 `SUBMITTED_NO_INJURIES` 團隊，因此沒有新增任何 explicit zero-burden team。

## Housekeeping

- [x] 新增 `PROJECT_STATUS.md`
- [x] README 首段連到本文件
- [x] 明確分離 Legacy UI 與 Research Pipeline
- [x] 建立 Completed／Negative Result／Research Ready／Blocked 狀態
- [x] 不再硬編碼網站版本號作為研究成熟度
- [ ] 每次重要研究 PR 合併時同步更新本文件
- [ ] 視需要關閉已被後續主線取代的早期草稿 PR，避免誤導

## 主線 A — Injury

已完成：

```text
Official Injury Importer
→ Single-report identity／value／team burden
→ Multi-report Injury Panel v1
→ Predeclared T-60 Snapshot Selection Policy
→ Multi-report Injury Feature Backfill v1
→ Team Submission Status v1
→ Long panel + selected game-level panel
```

下一步順序：

```text
1. 擴充更多官方 publication times 與日期
2. 至少累積 100 場獨立 selected feature-ready matchup
3. Expected Minutes Accuracy Audit
4. 先發／替補／新秀／復出球員分組
5. Injury Feature Walk-forward Holdout
6. Calibration／Residual 再驗證
```

### 樣本門檻

```text
目前：31 場獨立 selected games
最低啟動：100 場獨立 selected feature-ready matchup
初步可靠：300 場以上
較理想：500 場以上，跨多個月份／賽季
```

達到 100 只代表可以開始 holdout 實驗，不代表可以啟用模型或下注。

### Snapshot Selection Policy

Primary policy 已預先固定：

```text
latest feature-ready snapshot at or before T-60m
```

固定規則：

- both teams snapshot complete
- both teams feature-ready
- observed_at 至少早於 tip-off 60 分鐘
- no fallback
- latest eligible observed_at wins
- Not Yet Submitted／unknown／missing team → no selection

Diagnostic policies 可以比較 coverage，但不可在看過 outcome 後升級為 primary policy。

## 主線 B — Market

已完成：

```text
Odds schema／source registry／import boundary
→ Closing-only benchmark
→ Market residual experiment
```

下一步順序：

```text
1. Real Timestamped Odds Acquisition／Backfill
2. Opening／6h／3h／1h／30m／Close
3. Bookmaker-level normalization
4. Point-in-time Odds Join
5. Executable Market Backtest
6. CLV／EV／ROI／Drawdown
```

真正缺少的是有 observation timestamp 的合法、可稽核資料本體，不是再建立一套 registry 或基本 schema。

## 兩條主線匯合

```text
Point-in-time Model
＋ Selected Point-in-time Injury
＋ Executable Point-in-time Odds
→ True Market Backtest
→ Holdout EV／CLV／ROI
```

## 暫不列入目前主線

以下可作後續 Feature Expansion 候選，但不應取代 Injury 與 Market 兩條主線：

- Lineup Continuity
- Usage Redistribution
- Rotation Stability
- Referee Tendency：僅限授權清楚、歷史覆蓋完整且可 point-in-time 驗證的資料來源
- 更精細的球員級旅行與負荷資料

## 永久研究邊界

- 不使用同日、賽後或未來資料建立賽前特徵。
- 缺失值不隨意補成 0。
- 缺報、Not Yet Submitted、unknown 或 synthetic missing side 球隊不視為健康。
- 只有明確 `SUBMITTED_NO_INJURIES` 才能建立 explicit zero burden。
- 不使用 fuzzy player identity 或 nearest-name guessing。
- 多個 snapshots 不可冒充多場獨立比賽。
- 未完成 timestamped odds join 前，不宣稱 ROI、EV、CLV 或可執行投注 edge。
- CI 綠燈只代表流程通過；必須讀正式 Artifact QA 數字後才能判定資料有效。
- 模型目前輸給 Closing Market，正式投注額維持為 0。

## 重要 PR

- PR #28 — Fix Christopher Treasure Kaggle closing benchmark
- PR #29 — Market Residual Analysis v1
- PR #30 — Feature Expansion v3 context pilot（Rest／Travel 負結果）
- PR #35 — Player Value & Expected Minutes v1
- PR #36 — Team Injury Burden v1
- PR #37 — Multi-report Injury Panel v1
- PR #38 — Injury Feature Residual Audit v1
- PR #39 — Research status and README correction
- PR #40 — Multi-report Injury Feature Backfill v1
- PR #41 — Injury Team Submission Status v1
