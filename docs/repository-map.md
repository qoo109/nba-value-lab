# NBA Value Lab Repository Map

## 先看這三個入口

1. `README.md`：專案用途、啟動方式與主要功能。
2. `PROJECT_STATUS.md`：目前正式研究狀態、阻塞項目與 Stake 0 邊界。
3. `models/manifest.json`：目前啟用的 V、G 與 coordination 版本。

## 目錄分工

| 路徑 | 用途 | 維護規則 |
|---|---|---|
| `.github/workflows/` | 排程、驗證、一次性核准工作與 Pages 部署 | GitHub Actions 只辨識這一層的 workflow；不要為了視覺整理搬進子目錄 |
| `backups/` | 已停止開發的網站與來源封存 | 唯讀；靜態網站可展開，完整原始碼優先收成有 SHA-256 的封包 |
| `config/` | 網站與研究共用設定 | 不放執行輸出 |
| `css/` | V5 元件、頁面與響應式樣式 | 根目錄只保留目前入口直接載入的 CSS |
| `data/current/` | 網站目前讀取的賽程與來源健康度 | 可由排程更新，不作歷史真值 |
| `data/history/` | 精簡研究紀錄與 index | 不放完整原始資料庫 |
| `data/locks/` | T-60、T-5 等鎖定紀錄 | 不覆寫既有 snapshot |
| `data/research/` | 正式研究狀態、核准、結果與機器可讀證據 | 與 `PROJECT_STATUS.md` 保持一致 |
| `data/templates/` | 人工輸入與 workflow 範本 | 只放不含秘密的範例 |
| `docs/` | 研究規格、runbook、結果與架構文件 | 舊版展示移到 `docs/legacy/` |
| `js/` | 目前網站 JavaScript | 依 V4 compatibility 與 V5 modules 維持現有邊界 |
| `models/` | 不可覆寫的模型版本、協調層與完整 release | 新門檻建立新版本，不改寫舊資料夾 |
| `schemas/` | 正式輸出 JSON Schema | schema 變更需同步 validator |
| `scripts/` | builder、importer、audit、runner、validator 與測試 | workflow 大量使用固定路徑；未做全引用遷移前維持單層 |
| `out/` | 本機暫存與 aggregate 測試輸出 | 已由 Git 忽略，可隨時重建 |

## 根目錄規則

根目錄只保留網站啟動與專案導覽需要的檔案：

```text
index.html
styles.css
readability.css
README.md
PROJECT_STATUS.md
.nojekyll
.gitignore
```

舊展示頁或未被目前 `index.html` 載入的舊前端檔案放進 `docs/legacy/`。新的研究文件放 `docs/`，新的機器可讀狀態放 `data/research/`，不要再增加根目錄入口。

## 命名與清理規則

- 使用小寫 kebab-case 文件名與版本尾碼，例如 `point-in-time-odds-layer-v1.md`。
- 已發布的研究證據與模型版本不改名、不覆寫；新增 superseding 版本。
- `.DS_Store`、`.pytest_cache`、資料庫、ZIP 與本機 `out/` 不提交。
- 備份封包必須記錄來源 commit、檔案數、bytes 與 SHA-256。
- 刪除 workflow、核准紀錄或研究結果前，先確認 `PROJECT_STATUS.md` 與所有引用。
