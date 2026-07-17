# Historical Gold Layer v1

NBA Value Lab Gold v1 將 2023–24 Silver SQLite 的每場 team-game 資料，轉成模型可直接使用的賽前特徵。

## Point-in-time 原則

Gold v1 的固定規則是：

```text
source_game_date < target_game_date
```

Silver 目前只有比賽日期，沒有精確開賽時間。因此同一天的任何比賽都不會互相使用，整個日期的 Gold 特徵全部產生後，才把當天結果加入歷史。這是刻意採用的保守防洩漏策略。

禁止使用：

- 當場結果、Box Score 或 PBP
- 同日較早比賽結果
- 含當場結果的 rolling average
- 賽季末統計回填
- 未來賽程結果或 Closing 資料

## 輸出資料表

### `gold_team_game_features`

每場、每隊一列，包含：

- 近 5／10／20 場 rolling averages
- Points、Opponent Points、Pace、OffRtg、DefRtg、NetRtg
- eFG%、TOV% 估計、ORB% 估計、FTr
- 勝率與平均分差
- 賽季截至當時的累積平均
- 主客場分開的歷史表現
- 休息天數、背靠背
- 最近 3／4／7 天的比賽數
- 對手截至賽前的平均 NetRtg
- 近 10 場 NetRtg 趨勢與波動
- 資料可信度與品質旗標

### `gold_matchup_features`

每場一列，將主隊減客隊的差值整理成模型輸入：

- Rest days difference
- Pace／OffRtg／DefRtg／NetRtg L10 difference
- Four Factors L10 difference
- Season NetRtg difference
- 簡易 opponent-adjusted NetRtg difference
- 雙方資料可信度

## 版本欄位

每筆資料保存：

- `source_version`
- `feature_version`
- `feature_generated_at`
- `quality_flags`
- `feature_cutoff_date`

Gold v1 的 feature version：

```text
gold-v1-rolling-schedule-opponent
```

## 建置方式

先準備 Silver SQLite 或 gzip：

```bash
python scripts/build_historical_gold.py \
  --silver-db /path/to/historical-silver.sqlite.gz \
  --output-dir /tmp/nbavl-historical-gold
```

自我測試：

```bash
python scripts/build_historical_gold.py \
  --self-test \
  --output-dir /tmp/nbavl-gold-self-test
```

## Artifact

GitHub Actions `Build historical Gold features` 會依序：

1. 重新建立 Silver SQLite
2. 建立 Gold SQLite
3. 執行 point-in-time 與覆蓋率 QA
4. 上傳 14 天 Artifact

Artifact 包含：

- `historical-gold.sqlite.gz`
- `gold-build-report.json`
- `gold-sample.json`

完整資料庫不提交公開 repository。

## Gold v1 的限制

- 目前只有 2023–24 單季
- Silver 尚無精確開賽時間，因此同日資料全部排除
- 旅行距離、跨時區、前場延長賽負荷尚未加入
- 傷病、先發與市場賠率尚未加入
- 對手強度校正目前是第一版簡化指標，後續可升級迭代式 schedule adjustment
- 尚未建立 Parquet 輸出與跨季 season reset 規則

## 下一步

Gold v1 通過後，建議依序進行：

1. 擴充 2022–23、2021–22
2. 加入精確 scheduled start time
3. 增加旅行與賽程負荷特徵
4. 建立 Logistic Regression／Elo baseline
5. Walk-forward validation
6. 機率校準與市場資料層
