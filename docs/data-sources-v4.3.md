# NBA Value Lab V4.3 — 免費資料來源登錄

更新日期：2026-07-17  
資料策略：全免費優先、低頻、可追溯、point-in-time、來源失敗不靜默降級。

## 狀態定義

- `active`：目前可直接使用。
- `pilot`：已確認可取得，正在建立 adapter 與 schema 驗證。
- `manual`：只作人工核對或小量匯入。
- `disabled`：暫不啟用。
- `paid_api_optional`：只有在使用者主動提供付費方案與 Secret 後才可啟用。

## 第一批來源

| source_id | 來源 | 狀態 | 主要用途 | 取得模式 | 重要限制 |
|---|---|---|---|---|---|
| `user_odds` | 使用者手動雙邊盤口 | active | 21:00／T-60m／T-5m／Closing 市場賠率快照 | manual | 必須同一莊家、同一市場、同一時間 |
| `the_odds_api_historical` | The Odds API historical snapshots | disabled | 2020 年後 moneyline／spread／total 歷史快照 | paid API | 歷史端點需付費；API key 僅放 GitHub Secret；原始 JSON 不公開提交 |
| `kaggle_christophertreasure_nba_odds` | Kaggle NBA Odds Data | pilot | 2008-2023 closing-market benchmark | manual download/import | 2023 不完整；授權為 Other；沒有精確 observed timestamp |
| `kaggle_erichqiu_nba_odds_scores` | Kaggle NBA Odds and Scores | pilot | 比分與 moneyline 交叉驗證 | manual download/import | 須驗證 various sources provenance 與開收盤定義 |
| `oddsportal_nba_results` | OddsPortal NBA historical results | manual | 單場與跨莊家人工核對 | browser/manual | 條款禁止未經同意的 scraping、aggregation 與 automated requests |
| `covers_nba_sports_odds_history` | Covers NBA Sports Odds History | manual | 冠軍／分區／勝場 futures 研究 | browser/manual | 不屬於逐場 moneyline 或 CLV 資料 |
| `derived_schedule` | 自行計算賽程衍生特徵 | active | 休息差、背靠背、旅行、時區、賽程密度 | derived | 依賽程與場館座標重建 |
| `nba_injury_official` | NBA Official Injury Reports | pilot | 傷病、疾病、休息與報告修訂 | crawler | PDF schema 變動時停止發布 |
| `nba_live_cdn` | NBA Live Data CDN | pilot | 賽程、比數、狀態、Box Score、PBP | api | 無商業 SLA，必須驗證 schema |
| `nba_api` | swar/nba_api | pilot | NBA.com Stats 與 Live Data client | api | client 為 MIT；NBA endpoint 可能變動 |
| `basketball_reference` | Basketball-Reference | manual | 歷史核對與小量回填 | import/manual | 自動化前先審查條款、robots 與保存權 |

完整歷史賠率來源審查與分級：

- `docs/historical-odds-source-evaluation-v1.md`
- `data/historical-odds-source-registry.json`

## 每筆資料最低品質欄位

```text
source_id
published_at
observed_at
fetched_at
raw_hash
adapter_version
stale
fallback
```

## 賠率資料的額外最低欄位

```text
game_id
commence_time_utc
observed_at_utc
bookmaker
market_key
snapshot_label
home_price_decimal
away_price_decimal
```

固定規則：

- `observed_at_utc < commence_time_utc`
- 同一列必須是同莊家、同市場、同時間的雙邊市場賠率
- Closing 只能做 CLV，不可回頭參與下注選擇
- 賠率不得成為勝率模型的訓練特徵
- 完整歷史賠率若無再發布權，不提交公開 repository

## 接入順序

### Phase A — 賽程與結果

1. game_id、主客隊、開賽時間與台灣時區。
2. 比賽狀態與最終結果。
3. Box Score 與球員分鐘。
4. PBP、回合數、垃圾時間與節奏衍生欄位。

### Phase B — 傷病與輪替

1. 官方狀態與報告時間。
2. 21:00、T-60m、T-5m 三個快照。
3. minutes limit 與預計先發先保留人工欄位。
4. 以情境方式表示出賽、限時與缺陣，不自行捏造狀態機率。

### Phase C — 歷史與驗證

1. 依日期重建當時可見的球隊統計。
2. 保存模型版本、資料版本與 prediction id。
3. 分開驗證 V3、G1、核心主推與優先候選。
4. 報告 Brier、Log Loss、Calibration、CLV、ROI 與最大回撤。

### Phase D — Point-in-time Odds Layer

1. 以 canonical CSV 匯入同莊家雙邊 moneyline。
2. 驗證 observed time、commence time、game/team mapping 與 raw hash。
3. 計算 overround 與 proportional no-vig probability。
4. 將 T-60m entry 與同莊家 Closing 配對。
5. 報告 model-versus-market、EV、CLV、ROI、最大回撤與門檻敏感度。
6. 在 500 場、3 季、80% Closing 覆蓋前不開啟正式市場回測判定。

### Phase E — Closing-only Historical Benchmark

1. 匯入 SBR／Kaggle 常見 CSV、XLSX 或 XLS 歷史檔。
2. 支援一場兩列的 `Date, Rot, VH, Team, ML` 與一場一列 wide schema。
3. 將 American moneyline 轉為 decimal、overround 與 no-vig probability。
4. 與 Walk-forward OOF 預測依日期及主客隊配對。
5. 只比較 Log Loss、Brier 與 accuracy，不計算 ROI 或 CLV。
6. 沒有 exact observed timestamp 的資料永遠不得升級為 point-in-time backtest。

## 暫不啟用

- 每五分鐘自動盤口。
- 未由使用者主動啟用的付費商業 API。
- 未完成條款審查的公開網站大量爬蟲。
- OddsPortal 或其他明確禁止 automated requests 的網站爬蟲。
- 將大型原始 PDF、HTML、PBP 或多年賠率直接放入 GitHub Pages repository。
