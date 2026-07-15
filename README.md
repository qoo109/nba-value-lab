# NBA Value Lab — GitHub Pages 靜態版

這是一個可直接上傳到 GitHub 的純靜態網站版本，不需要 Node.js、不需要 build，也不需要後端。

## 檔案內容

- `index.html`：網站主頁
- `styles.css`：完整 UI 樣式
- `script.js`：分頁、篩選、詳細分析彈窗、賠率即時試算
- `.nojekyll`：避免 GitHub Pages 對靜態檔案做 Jekyll 處理

## 上傳到 GitHub Pages

1. 建立一個 GitHub repository。
2. 把這個資料夾裡的所有檔案上傳到 repo 根目錄。
3. 到 repo 的 `Settings` → `Pages`。
4. Source 選 `Deploy from a branch`。
5. Branch 選 `main`，資料夾選 `/root`。
6. 儲存後等待 GitHub Pages 產生網址。

## 重要提醒

目前這包是靜態展示版，裡面的比賽、賠率與勝率是示範資料，不是真實即時盤。

若要接上真實資料，建議下一版改成：

- 賽程：NBA 官方賽程
- 傷病：NBA 官方傷情報告
- 盤口：The Odds API 或其他合法賠率 API
- 下注前價格：保留手動輸入莊家賠率覆蓋

## 修改資料

示範資料在 `script.js` 的 `games` 陣列中。你可以直接改：

- 比賽名稱
- 熱門方
- 賠率
- 保守／中性／樂觀勝率
- 分級
- 支持證據與主要風險

改完後直接重新上傳檔案即可。
