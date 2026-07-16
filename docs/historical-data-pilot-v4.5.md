# NBA Value Lab V4.5 — 歷史資料來源試驗

更新日期：2026-07-16  
狀態：Pilot，不進正式模型、不進 GitHub Pages 公開資料目錄。

## 第一輪測試目標

先測試 `shufinskiy/nba_data` 的兩種 2023–24 歷史資料：

| source_key | 層級候選 | 用途 |
|---|---|---|
| `pbpstats_2023` | Bronze／Silver 候選 | Possession、回合起訖、事件摘要與進攻結果 |
| `nbastats_2023` | Bronze 候選 | 原始事件級 Play-by-Play |

第一輪自動執行 `pbpstats_2023`；`nbastats_2023` 可由 workflow 手動切換測試。

## 試驗檢查項目

- 壓縮檔下載是否成功。
- 檔案大小與 SHA-256。
- tar 路徑穿越與 symbolic link 防護。
- 壓縮檔內檔案數、格式與容量。
- CSV／JSON／JSONL／Parquet 欄位。
- 每個檔案最多 5,000 筆樣本的缺值率。
- GAME ID 樣本覆蓋。
- 候選主鍵是否完整與重複。
- 預期欄位是否存在。
- 是否具備進入下一輪 Silver 標準化的基本條件。

## 儲存政策

原始資料不會提交到此 repository：

```text
GitHub Actions 暫存下載
        ↓
安全解壓與樣本檢查
        ↓
產生 compact JSON audit report
        ↓
Actions artifact 保存 14 天
```

不提交：

- `.tar.xz` 原始壓縮檔
- 大型 CSV／JSON／Parquet
- 完整 PBP
- 完整 Possession 表

repository 只保存：

- 下載來源設定
- 稽核程式
- Schema 與品質規則
- 小型稽核報告（未來確認適合後才考慮）

## 下載與執行上限

- 預設下載硬上限：600MB。
- 單次工作時間上限：20 分鐘。
- 單次最多檢查 80 個資料檔。
- 每檔最多讀取 5,000 筆樣本。

超過上限不代表資料錯誤，而是代表它不適合目前免費、低成本的自動管線，需要改用分季、分月或外部物件儲存。

## 授權政策

`shufinskiy/nba_data` 的程式碼授權與上游資料使用權分開判斷。此試驗只進行私人研究品質驗證，不推定 NBA 原始資料可以公開再發布。

目前狀態：

```text
程式碼與下載工具：可研究使用
上游原始資料再發布：未取得明確授權，不提交公開 GitHub
衍生的精簡品質報告：可保存
```

## 通過標準

第一輪至少需要：

1. 壓縮檔可在上限內下載與解壓。
2. 至少成功解析一個支援格式的資料檔。
3. 預期核心欄位至少在一個檔案中完整出現。
4. 候選主鍵可檢查。
5. 不發生 archive traversal、格式損毀或全檔解析失敗。

通過後才進入下一階段：

- 比賽完整率比對
- 同一 game_id 的 PBP 與 Possession 對齊
- OffRtg／DefRtg／Pace／四要素重算
- Point-in-time rolling features
- Silver schema 設計
