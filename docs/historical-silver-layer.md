# NBA Value Lab 歷史資料 Silver Layer

狀態：Pilot。版本名稱跟隨網站目前正式版本，不綁定固定 UI 版本。

## 目的

將通過全檔稽核的 `pbpstats_2023` 與 `nbastats_2023` 轉成可查詢的 SQLite 資料庫，供私人研究、特徵工程與回測使用。

原始壓縮檔、完整 CSV 與完整 SQLite 不提交到公開 repository；建庫只在 GitHub Actions 暫存空間執行，壓縮資料庫以 14 天 artifact 保存。

## 資料表

### `games`

每場比賽一列，包含：

- game ID 與日期
- 主客隊 ID／縮寫
- 最終比分
- 最高節數與實際比賽分鐘
- PBP 事件數與 Possession 數
- 跨來源比分驗證結果
- 品質旗標

### `pbp_events`

由 `nbastats_2023` 正規化的事件級 Play-by-Play：

- 穩定 `event_id`
- event number、事件類型與 action type
- 節數、時間、主客側
- 描述、比分、球隊與球員 ID
- 精確重複列先移除；同鍵但內容不同的列保留並取得不同 ID

### `possessions`

由 `pbpstats_2023` 的多事件列分組建立。正式分組鍵：

```text
GAMEID
+ PERIOD
+ STARTTIME
+ ENDTIME
+ OPPONENT
+ STARTSCOREDIFFERENTIAL
+ STARTTYPE
```

欄位包含：

- 進攻方與防守方
- 回合起訖時間與起始類型
- 得分、二分／三分、罰球
- 進攻籃板與失誤
- 回合內事件數與事件文字
- 品質旗標

### `team_game_features`

每場每隊一列：

- Possessions
- Pace
- OffRtg／DefRtg／NetRtg
- eFG%
- TOV%（估計四要素分母）
- ORB%（以投籃未進次數估計）
- FTr
- 與官方最終比分的交叉驗證

## 指標定義

```text
Pace = 48 × (Team Poss + Opp Poss) / (2 × Game Minutes)
OffRtg = 100 × Team Points / Team Poss
DefRtg = 100 × Opp Points / Opp Poss
eFG% = (FGM + 0.5 × 3PM) / FGA
TOV% = TOV / (FGA + 0.44 × FTA + TOV)
FTr = FTA / FGA
ORB% estimate = ORB / Missed FG
```

`ORB% estimate` 不是正式 Box Score ORB%，因為目前來源沒有完整對手防守籃板欄位。它會保留明確名稱，不與正式 ORB% 混用。

## 得分重算

Possession 得分由下列資料計算：

```text
2 × FG2M + 3 × FG3M + made free throws parsed from EVENTS
```

再與 `nbastats` 最終比分比對。正式模型特徵管線要求至少 98% 已知比分比賽一致；不一致比賽保留，但會標記品質旗標，不能直接進訓練集。

## 產物

GitHub Actions artifact：

```text
historical-silver.sqlite.gz
silver-build-report.json
silver-sample.json
```

SQLite 解壓後可直接使用：

```bash
gzip -dk historical-silver.sqlite.gz
sqlite3 historical-silver.sqlite
```

常用查詢：

```sql
SELECT team_abbr, AVG(off_rtg), AVG(def_rtg), AVG(pace)
FROM team_game_features
GROUP BY team_abbr;
```

## 安全與使用限制

- 不推定上游 NBA 原始資料具有公開再發布權。
- 不把完整原始資料或完整 Silver database 推送到 GitHub Pages。
- 網站公開層只可使用經審核的精簡衍生摘要。
- 所有模型特徵必須遵守 `feature_time < game_start_time`，禁止使用當場或賽後資料預測同一場比賽。
