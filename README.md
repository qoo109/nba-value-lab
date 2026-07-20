# NBA Value Lab

NBA 賽前獨贏的勝率、市場賠率價值、資料 Gate 與模型驗證研究平台。

> **目前研究定位：Research Candidate／Pre-Market-Backtest**  
> 最新研究管線、已完成負結果、阻塞項目與下一步，請以 [`PROJECT_STATUS.md`](./PROJECT_STATUS.md) 為正式基準。  
> 下方 V4.6／V3.1 × G1 FINAL 內容是保留中的 Legacy UI／Model Registry 說明，不代表目前研究成熟度。

線上網站：<https://qoo109.github.io/nba-value-lab/>

## Research Pipeline 摘要

目前已完成五季 Historical Gold、Logistic + Elo Walk-forward v2、Calibration Gate、Closing Market Benchmark、Market Residual Analysis、Rest／Travel holdout、官方傷病報告 importer、Player Identity、Expected Minutes research proxy、Team Injury Burden、Multi-report Injury Panel 與 Injury Residual Audit。

目前最重要的限制：

- 模型能小幅擊敗 Elo，但在 1,894 場 Closing benchmark 中明顯輸給 Closing Market。
- Rest／Travel／Schedule Context v1 已完成，但未通過 promotion gate。
- Multi-report Injury Panel 已可研究，但 ingestion coverage 不等於 feature-ready matchup。
- Odds schema／source registry 已完成；真正缺少的是有 observation timestamp 的真實 opening／intraday／closing odds 資料。
- Executable Market Backtest、CLV、EV、ROI、Drawdown 與正式投注決策層仍未解鎖。
- 正式投注額固定為 0。

## Legacy UI／Registry：V3.1.1 × G1.1.1

目前啟用：

- V3.1.1：`V3.1.1-20260719`
- G1.1.1：`G1.1.1-20260719`
- 協調層：`V3.1.1_X_G1.1.1-20260719`

兩套引擎分開判定，不做未驗證的勝率平均或任意權重混合：

- V3.1.1 管理自己的核心、延伸、另行校準及範圍外政策。
- G1.1.1 管理六層雙向市場賠率校準、第一資料 Gate、雙邊衝突與每批目標 2 場、最多 3 場主要場次。
- 協調層保存 V、G 與 coordination 三個獨立 grade；只有 V 核心與 G 同時通過才能標示雙引擎 ㄅ級。
- 網站最多顯示 2 場「優先候選」，但這是 UI 排序，不是 G1 正式分級。

## Model Registry

- `spec.md`：可獨立重建公式、分級與 Gate 的人類可讀規格。
- `config.json`：網站可執行門檻。
- `spec_integrity`：對 spec 的 UTF-8 精確檔案位元組計算 SHA-256，不做正規化。
- `models/manifest.json`：指定目前啟用版本與協調層。
- `models/releases/v3.1.1-g1.1.1-complete/spec.md`：網站下載用的完整統整規則，集中說明 active V、G、協調層、公式、Gate 與研究限制。
- 舊版本保留，不直接覆寫。
- 更新模型設定後由 GitHub Actions 驗證。
- 歷史預測必須綁定當時的 V、G、協調層與資料版本。

目前路徑：

```text
models/
├─ manifest.json
├─ v3/
│  ├─ 3.0/
│  ├─ 3.1/
│  └─ 3.1.1/
├─ g1/
│  ├─ 1.0/
│  ├─ 1.0-final-20260716/
│  ├─ 1.1-main-2-max-3/
│  └─ 1.1.1/
├─ coordination/
│  └─ v3.1.1-g1.1.1/
└─ releases/
   └─ v3.1.1-g1.1.1-complete/
```

## V3.1.1 重點

- `prediction` 與 `price_evaluation` 分離。
- 單純市場賠率變動新增 `price_evaluation_id`，不得改寫模型勝率或 `prediction_id`。
- Stage 0～2 安全邊際固定為 5pp。
- 核心區為 1.40～1.60。
- `core_odds_scope` 只表示可取得 V ㄅ級的核心區；完整分類仍讀取 `price_segments`。
- 1.30～1.39 與 1.61～1.75 未獨立驗證前最高為 ㄆ級・延伸研究。
- 1.76～1.99 為另行校準區。
- ThresholdDistance ≥ 0 為ㄅ級、−3～0pp 為ㄆ級、低於 −3pp 且仍有正優勢為ㄇ級。
- 人工覆核在鎖定前隱藏市場賠率、EV、最低接受賠率與分級。

## G1.1.1 重點

- 同場主客隊同時建立候選邊。
- 第一閘門先檢查資料、傷病、模型穩定性與市場可核對性。
- 核心研究市場賠率區為 1.35～2.20，分成 5pp 與 6pp 兩個子層。
- 同場雙邊同時符合 ㄅ級數學條件時，標記雙邊價值衝突並阻止主要場次。
- 主要場次一般目標 2 場、硬上限 3 場；允許 0 或 1 場，第三場需通過額外嚴格 Gate。
- 主要場次還需要 Coverage、區間、比較來源、模型市場差、傷病與 stale 等硬性 Gate。
- T-60m 只能產生「主要場次待 T-5m 確認」；T-5m 再鎖定最終結果。

## 免費資料層

- GitHub Actions 每日以台灣時間 08:05、12:05、17:05、21:05 更新。
- 保存來源、抓取時間、觀察時間、hash、Adapter 版本與 stale 狀態。
- 不使用付費 API。
- 不抓每五分鐘全量盤口。

## 精簡歷史紀錄

專案不保存完整 Box Score 或 Play-by-play，只保留模型驗證需要的最小資料：

- `prediction_id` 與 `price_evaluation_id`
- game_id、選擇方與分析截止時間
- V、G 與協調層版本
- 保守／中性／樂觀勝率
- 同時間雙邊市場賠率、市場賠率層、V 結論與 G 結論
- G1 主要場次狀態與 UI 優先候選標記
- Closing、CLV、最終勝負與可選簡單比分

資料格式見 `schemas/prediction-record.schema.json`。

## 更新模型

1. 建立新的不可覆寫版本資料夾。
2. 放入 `spec.md` 與 `config.json`。
3. 若兩套引擎互動方式改變，建立新的 coordination `spec.md` 與 `config.json`。
4. 更新 `models/manifest.json`。
5. 推送到 `main`。
6. Registry、JSON 與 JavaScript 驗證通過後，由 GitHub Pages 發布。

只修改門檻、市場賠率層或 Gate 時不需要重做網站；增加新公式、資料物件、引擎或輸出欄位時，才同步新增前端協調模組。

## 主要檔案

- `PROJECT_STATUS.md`：目前研究管線的正式進度、負結果、阻塞項目與 Roadmap。
- `index.html`：網站結構。
- `styles.css`／`readability.css`：響應式介面與深淺色模式。
- `js/v4-data.js`：示範 slate 與基礎 Registry 載入器。
- `js/v4-core.js`：共用市場數學。
- `js/v4-render.js`：總表、候選、詳情與試算器。
- `js/v4-6-model-coordination.js`：V、G 與協調層設定驅動判定。
- `js/v4-init.js`：啟動時載入 V4.6 協調模組。
- `models/manifest.json`：啟用模型版本。
- `scripts/validate_model_registry.py`：Registry 驗證器。
- `data/current/`：當前賽程與來源健康度。
- `data/history/`：精簡歷史紀錄政策。

## GitHub Pages

專案包含 GitHub Actions Pages 部署 workflow。Repository 的 Settings → Pages → Source 需設為 GitHub Actions。

## 研究聲明

Legacy UI 內的勝率與候選仍可能包含示範資料。正式研究管線已完成 Walk-forward、Calibration Gate、Closing Market Benchmark 與多個 holdout／殘差實驗，但尚未完成 real timestamped odds backfill、executable market backtest、CLV、EV、ROI、Drawdown 與正式鎖版前瞻測試。

目前沒有證據支持模型能改善 Closing Market，也沒有穩定投注優勢或獲利證據；正式投注額固定為 0，不構成投注或獲利保證。
