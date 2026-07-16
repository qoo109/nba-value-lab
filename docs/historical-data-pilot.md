# NBA Value Lab — 歷史資料來源試驗

更新日期：2026-07-16  
版本政策：永遠跟隨網站目前正式版本，不在資料管線名稱中固定 UI 版本。  
狀態：Pilot，不進正式模型，也不把大型原始資料提交到 GitHub Pages repository。

## 目前測試來源

| source_key | 層級候選 | 用途 |
|---|---|---|
| `pbpstats_2023` | Bronze／Silver 候選 | Possession、回合起訖、事件摘要、投籃與進攻結果 |
| `nbastats_2023` | Bronze 候選 | 原始事件級 Play-by-Play |

## 第二階段檢查

第二階段不再只讀取 5,000 筆樣本，而是完整掃描兩份 CSV：

1. 完整列數與完整 GAME ID 數量。
2. 每場事件／Possession 數量的最小值、中位數、P95 與最大值。
3. `GAMEID + PERIOD + STARTTIME + ENDTIME` 的重複狀況。
4. 加入 `OPPONENT` 後的 Possession 候選主鍵唯一性。
5. `GAME_ID + EVENTNUM` 的事件主鍵唯一性。
6. 兩來源 GAME ID 的交集、聯集與缺場清單。
7. 核心欄位缺值率與 Schema 差異。
8. 產生最多 150 列的 compact Silver 樣本供後續 adapter 開發。

## 儲存政策

```text
GitHub Actions 暫存下載
        ↓
安全解壓與全檔掃描
        ↓
產生 QA report + compact Silver sample
        ↓
Actions artifact 保存 14 天
```

不提交：

- `.tar.xz` 原始壓縮檔
- 解壓後的大型 CSV／JSON／Parquet
- 完整 Play-by-Play
- 完整 Possession 表

repository 只保存：

- 來源設定與 Schema 規則
- 稽核及轉換程式
- GitHub Actions workflow
- 文件

## 第二階段通過標準

- 兩來源核心欄位皆完整。
- 每個來源至少有一組可用且唯一的候選主鍵。
- 較小來源的 GAME ID 至少 98% 能在另一來源找到。
- 全檔掃描可在 GitHub Actions 時間與容量限制內完成。
- 原始資料仍不進 repository。

全部通過後，下一步才會建立正式的標準化 adapter，並重算：

- OffRtg／DefRtg／NetRtg
- Pace
- eFG%
- TOV%
- ORB%
- FTr
- Point-in-time rolling features

## 授權界線

此試驗只做私人研究與品質驗證。程式碼授權與上游 NBA 原始資料的保存／再發布權分開判斷；未取得明確權利前，不公開重製完整原始資料。
