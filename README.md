# NBA Value Lab V2.6

NBA 賽前獨贏低賠熱門方的勝率、價格價值與模型驗證研究工具。

線上網站：<https://qoo109.github.io/nba-value-lab/>

## V2.6 重點

- 純 HTML、CSS、JavaScript，GitHub Pages 可直接執行
- 不需要 API 金鑰
- 不抓 10 家莊家每 5 分鐘全量盤口
- 目標莊家 1 家，市場比較來源 3～5 家
- 保存 Opening、T−24h、可選 T−6h、T−60m、T−5m、Closing
- T−60m 鎖定模型判斷；Closing 只用於 CLV
- ㄅ／ㄆ／ㄇ／模型不支持／資料不足分級
- 尚未完成歷史校準前，正式投注額固定為 0

## 檔案

- `index.html`：網站結構
- `styles.css`：響應式版面
- `script.js`：篩選、詳細分析、賠率試算與分頁
- `docs/NBA_Value_Analyzer_V2.6.md`：完整模型規格
- `docs/model-config-v2.6.json`：機器可讀規則
- `docs/NBA_Crawler_and_Storage_V2.6.md`：爬蟲與儲存規格

## GitHub Pages

此儲存庫採 `main` 分支根目錄發布。更新完成後，可在 Settings → Pages 查看部署狀態。

## 研究聲明

目前網站內比賽、賠率與勝率均為示範資料。模型尚未完成 walk-forward、機率校準、CLV 與一次性 holdout 驗證，不構成投注或獲利保證。
