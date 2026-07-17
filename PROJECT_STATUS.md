# NBA Value Lab — Project Status

更新日期：2026-07-17  
目前定位：**Research Candidate／Pre-Market-Backtest**  
目前 `main` 研究基準：PR #38，merge commit `0c07e27fd813caac3260e1fa49852f084c80a3eb`

本文件是研究管線的正式進度基準。根目錄 `README.md` 仍保留 V4.6／V3.1 × G1 FINAL 的舊網站與 Model Registry 說明，但舊網站版本號不代表目前研究成熟度。

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
| Injury Snapshot → Gold Game ID | Completed | 單份 pilot 的 11 場全部唯一對齊。 |
| Player Identity Layer | Completed | 單份 pilot 117/118 唯一精確匹配；不使用 fuzzy guessing。 |
| Expected Minutes | Research Ready / Research Proxy | prior-only 規則已建立，但尚未完成多日期、多賽季 accuracy audit。 |
| Player Impact Proxy | Research Ready / Research Proxy | 透明 box-score proxy，不是 RAPM、EPM 或官方 metric。 |
| Team Injury Burden v1 | Research Ready | 單份 pilot 11 場、7 場 feature-ready；未啟用模型。 |
| Multi-report Injury Panel v1 | Research Ready | PR #37 已合併；6 份成功報告、4 個日期、654 列、41 場 ingestion coverage。這不是 41 場 feature-ready matchup。 |
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

## Housekeeping — 優先文件任務

- [x] 新增 `PROJECT_STATUS.md`
- [x] README 首段連到本文件
- [x] 明確分離 Legacy UI 與 Research Pipeline
- [x] 建立 Completed／Negative Result／Research Ready／Blocked 狀態
- [ ] 後續每次重要 PR 合併後同步更新本文件
- [ ] 視需要關閉已被後續主線取代的早期草稿 PR，避免誤導

## 主線 A — Injury

已完成：

```text
Official Injury Importer
→ Single-report identity／value／team burden
→ Multi-report Injury Panel v1
```

下一步順序：

```text
1. Predeclared Snapshot Selection Policy
2. Multi-report Injury Feature Backfill v1
3. Long panel：每個 observed_at 一列
4. Selected panel：每場只保留預先定義的賽前快照
5. Expected Minutes Accuracy Audit
6. 至少 100 場獨立 feature-ready matchup
7. Injury Feature Walk-forward Holdout
8. Calibration／Residual 再驗證
```

### Snapshot Selection Policy 必須預先定義

可預先建立並比較多個固定政策，但不可看完結果後再選最有利的時間點：

- latest complete pre-tip
- T-60m 或之前最近完整報告
- T-180m 或之前最近完整報告
- 固定官方 publication slot
- 任一隊 `Not Yet Submitted` 時標記 incomplete，不補成健康

同一比賽的 08:30、13:30、T-60m、T-30m 等 snapshots 可以用於狀態變化與 snapshot-selection 研究，但在 holdout 中仍只能算 **1 場獨立比賽**。

樣本門檻：

```text
最低啟動：100 場獨立 feature-ready matchup
初步可靠：300 場以上
較理想：500 場以上，跨多個月份／賽季
```

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
- 缺報球隊不視為健康。
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
