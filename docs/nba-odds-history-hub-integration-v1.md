# NBA Odds History Hub Archive v1

## 決策

`qoo109/nba-value-lab` 是唯一繼續開發、更新資料、執行驗證與發布網站的主專案。

`qoo109/nba-odds-history-hub` 不再是外部執行依賴。其 V0.19 完整受控檔案快照已放進：

```text
backups/nba-odds-history-hub-v0.19/
```

快照來源固定為：

```text
repository: qoo109/nba-odds-history-hub
commit: 5d2659efb2fee1cf28816ebfc65ddac929d75d6a
phase: V0.19
tracked files: 145
```

## 備份網站

主站發布後，靜態備份入口為：

```text
https://qoo109.github.io/nba-value-lab/backups/nba-odds-history-hub-v0.19/
```

這個入口只展開舊版網站需要的靜態 HTML 與 `data/public`。完整 145 檔原始碼、文件、規格、測試與 workflow 已收進：

```text
backups/nba-odds-history-hub-v0.19/nba-odds-history-hub-v0.19-source.tar.gz
bytes: 117257
sha256: 654eeda2229e99b051ab5ad6088983e79b212e9c8fd7e46247bae3e02ef98deb
```

這樣 Pages 仍可直接瀏覽備份網站，GitHub 檔案列表則不需要展開整個舊 repository。封存包內的 `.github/workflows` 不會被主專案執行。

## Repository 處理方式

原 GitHub repository 建議設為 Archive，而不是 Delete。Archive 會保留完整 commit、branch、PR、issue 與 release 歷史；主專案內的快照則提供可直接瀏覽的檔案備份。

只有在以下條件都確認後才考慮刪除原 repository：

1. `nba-value-lab` 主分支已包含完整快照；
2. GitHub Pages 備份網址可正常開啟；
3. 已另行保存完整 Git bundle 或確認不需要原 PR／issue 歷史。

## 執行邊界

- 所有新功能與新資料工作只進 `qoo109/nba-value-lab`。
- 封存快照唯讀，不在其中繼續開發。
- 不從原 repository 自動匯入或跨 repo 寫入。
- 不自動讀取外部 schedule，不碰 production database。
- 不因封存而解鎖 market backtest、CLV、EV、ROI、Drawdown 或正式投注決策。
- 正式投注額固定為 0。

機器可讀決策位於 `data/odds-history-hub-integration-v1.json`。
