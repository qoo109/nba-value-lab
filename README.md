# NBA Value Lab V4.5

NBA 賽前獨贏的勝率、價格價值、資料 Gate 與模型驗證研究平台。

線上網站：<https://qoo109.github.io/nba-value-lab/>

## V4.5 Model Registry

- V、G 模型規格與網站程式分離
- `spec.md` 提供人類可讀規格
- `config.json` 提供網站可執行門檻
- `models/manifest.json` 指定目前啟用的 V、G 版本
- 更新設定後由 GitHub Actions 自動驗證
- 舊模型版本保留，不直接覆寫
- 歷史預測綁定當時的 V、G 版本

目前登錄：

- V3.0：價格價值、EV 與最低接受賠率
- G1.0：雙向價格層、資料 Gate 與優先序

## 免費資料層

- GitHub Actions 每日以台灣時間 08:05、12:05、17:05、21:05 更新
- 保存來源、抓取時間、觀察時間、hash、Adapter 版本與 stale 狀態
- 不使用付費 API
- 不抓每五分鐘全量盤口

## 精簡歷史紀錄

專案不保存完整 Box Score 或 Play-by-play。歷史資料只保留模型驗證所需欄位：

- game_id、目標邊與預測時間
- 21:00／T−60m／T−5m 階段
- V、G 模型版本
- 保守／中性／樂觀勝率
- 當時賠率、Closing、分級與候選層級
- 最終勝負與可選的簡單比分

資料格式見 `schemas/prediction-record.schema.json`。

## 更新模型

1. 建立新版本資料夾，例如 `models/v3/3.1/`。
2. 放入 `spec.md` 與 `config.json`。
3. 更新 `models/manifest.json`。
4. 推送到 `main`。
5. 驗證成功後由 GitHub Pages 自動發布。

若只是修改門檻、價格層或 Gate，不需要重做網站；若新增全新公式、輸入欄位或引擎結構，才需要同步更新 JavaScript。

## 主要檔案

- `index.html`：網站結構
- `styles.css`／`readability.css`：響應式介面與深淺色模式
- `js/v4-data.js`：示範 slate 與 Model Registry 載入器
- `js/v4-core.js`：V、G 共用價格與 Gate 邏輯
- `js/v4-render.js`：總表、候選、詳情與試算器
- `models/manifest.json`：啟用模型版本
- `models/v3/`、`models/g1/`：版本化模型規格與設定
- `scripts/validate_model_registry.py`：Registry 驗證器
- `data/current/`：當前賽程與來源健康度
- `data/history/`：精簡歷史紀錄政策

## GitHub Pages

專案已包含 GitHub Actions Pages 部署 workflow。Repository 的 Settings → Pages → Source 需設為 GitHub Actions。

## 研究聲明

目前網站內勝率與候選仍包含示範資料。模型尚未完成完整 walk-forward、機率校準、CLV 與一次性 holdout 驗證，不構成投注或獲利保證。
