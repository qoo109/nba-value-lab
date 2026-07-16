# NBA Value Lab V4.3 — 免費資料來源登錄

更新日期：2026-07-16  
資料策略：全免費優先、低頻、可追溯、point-in-time、來源失敗不靜默降級。

## 狀態定義

- `active`：目前可直接使用。
- `pilot`：已確認可取得，正在建立 adapter 與 schema 驗證。
- `manual`：只作人工核對或小量匯入。
- `disabled`：暫不啟用。

## 第一批來源

| source_id | 來源 | 狀態 | 主要用途 | 取得模式 | 重要限制 |
|---|---|---|---|---|---|
| `user_odds` | 使用者手動雙邊盤口 | active | 21:00／T-60m／T-5m／Closing 價格快照 | manual | 必須同一莊家、同一市場、同一時間 |
| `derived_schedule` | 自行計算賽程衍生特徵 | active | 休息差、背靠背、旅行、時區、賽程密度 | derived | 依賽程與場館座標重建 |
| `nba_injury_official` | NBA Official Injury Reports | pilot | 傷病、疾病、休息與報告修訂 | crawler | PDF schema 變動時停止發布 |
| `nba_live_cdn` | NBA Live Data CDN | pilot | 賽程、比數、狀態、Box Score、PBP | api | 無商業 SLA，必須驗證 schema |
| `nba_api` | swar/nba_api | pilot | NBA.com Stats 與 Live Data client | api | client 為 MIT；NBA endpoint 可能變動 |
| `basketball_reference` | Basketball-Reference | manual | 歷史核對與小量回填 | import/manual | 自動化前先審查條款、robots 與保存權 |

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

## 暫不啟用

- 每五分鐘自動盤口。
- 付費商業 API。
- 未完成條款審查的公開網站大量爬蟲。
- 將大型原始 PDF、HTML、PBP 或多年資料直接放入 GitHub Pages repository。
