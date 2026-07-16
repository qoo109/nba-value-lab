# NBA Value Lab V4.6

NBA 賽前獨贏的勝率、價格價值、資料 Gate 與模型驗證研究平台。

線上網站：<https://qoo109.github.io/nba-value-lab/>

## V4.6：V3.1 × G1 FINAL

目前啟用：

- V3.1：`V3.1-20260716`
- G1：`G1-FINAL-20260716`
- 協調層：`V3.1_X_G1-FINAL-20260716`

兩套引擎分開判定，不做未驗證的勝率平均或任意權重混合：

- V3.1 管理自己的核心、延伸、另行校準及範圍外政策。
- G1 管理六層雙向價格校準、第一資料 Gate、雙邊衝突與每批 0～1 場主要場次。
- 協調層只負責顯示 V 結論、G 結論與網站候選排序。
- 網站最多顯示 2 場「優先候選」，但這是 UI 排序，不是 G1 正式分級。

## Model Registry

- `spec.md`：人類可讀規格摘要與來源雜湊。
- `config.json`：網站可執行門檻。
- `models/manifest.json`：指定目前啟用版本與協調層。
- 舊版本保留，不直接覆寫。
- 更新模型設定後由 GitHub Actions 驗證。
- 歷史預測必須綁定當時的 V、G、協調層與資料版本。

目前路徑：

```text
models/
├─ manifest.json
├─ v3/
│  ├─ 3.0/
│  └─ 3.1/
├─ g1/
│  ├─ 1.0/
│  └─ 1.0-final-20260716/
└─ coordination/
   └─ v3.1-g1-final/
```

## V3.1 重點

- `prediction` 與 `price_evaluation` 分離。
- 單純價格變動新增 `price_evaluation_id`，不得改寫模型勝率或 `prediction_id`。
- Stage 0～2 安全邊際固定為 5pp。
- 核心區為 1.40～1.60。
- 1.30～1.39 與 1.61～1.75 未獨立驗證前最高為 ㄆ級・延伸研究。
- 1.76～1.99 為另行校準區。
- 人工覆核在鎖定前隱藏價格、EV、最低接受賠率與分級。

## G1 FINAL 重點

- 同場主客隊同時建立候選邊。
- 第一閘門先檢查資料、傷病、模型穩定性與市場可核對性。
- 核心研究價格區為 1.35～2.20，分成 5pp 與 6pp 兩個子層。
- 同場雙邊同時符合 ㄅ級數學條件時，標記雙邊價值衝突並阻止主要場次。
- 主要場次每批可以 0 場、最多 1 場。
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
- 同時間雙邊價格、價格層、V 結論與 G 結論
- G1 主要場次狀態與 UI 優先候選標記
- Closing、CLV、最終勝負與可選簡單比分

資料格式見 `schemas/prediction-record.schema.json`。

## 更新模型

1. 建立新的不可覆寫版本資料夾。
2. 放入 `spec.md` 與 `config.json`。
3. 若兩套引擎互動方式改變，建立新的 coordination config。
4. 更新 `models/manifest.json`。
5. 推送到 `main`。
6. Registry、JSON 與 JavaScript 驗證通過後，由 GitHub Pages 發布。

只修改門檻、價格層或 Gate 時不需要重做網站；增加新公式、資料物件、引擎或輸出欄位時，才同步新增前端協調模組。

## 主要檔案

- `index.html`：網站結構。
- `styles.css`／`readability.css`：響應式介面與深淺色模式。
- `js/v4-data.js`：示範 slate 與基礎 Registry 載入器。
- `js/v4-core.js`：共用市場數學。
- `js/v4-render.js`：總表、候選、詳情與試算器。
- `js/v4-6-model-coordination.js`：V3.1、G1 與協調層判定。
- `js/v4-init.js`：啟動時載入 V4.6 協調模組。
- `models/manifest.json`：啟用模型版本。
- `scripts/validate_model_registry.py`：Registry 驗證器。
- `data/current/`：當前賽程與來源健康度。
- `data/history/`：精簡歷史紀錄政策。

## GitHub Pages

專案包含 GitHub Actions Pages 部署 workflow。Repository 的 Settings → Pages → Source 需設為 GitHub Actions。

## 研究聲明

目前網站內勝率與候選仍包含示範資料。V3.1 與 G1 尚未完成完整 walk-forward、機率校準、CLV、final holdout 與鎖版前瞻測試，正式投注額固定為 0，不構成投注或獲利保證。
