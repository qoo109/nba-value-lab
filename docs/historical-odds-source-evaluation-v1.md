# NBA Historical Odds Source Evaluation v1

更新日期：2026-07-17（Asia/Taipei）

目的：評估可用於 NBA Value Lab 的歷史賠率來源，區分「人工核對」、「收盤市場基準」與「真正 point-in-time 回測」。

## 結論摘要

| 來源 | 可否使用 | 建議用途 | 自動化政策 | 主要限制 |
|---|---|---|---|---|
| OddsPortal | 可以，但僅人工核對 | 查單場、跨莊家視覺比較、抽樣 QA | 禁止自動爬取 | 使用條款限制個人使用，禁止 scraping、aggregating 與 automated requests |
| SportsbookReviewOnline 舊 NBA archive | 原始入口目前不可用 | 僅作歷史來源線索與鏡像資料 provenance | 不直接抓取 | 指定舊網址於 2026-07-17 回傳 404；需改用保留鏡像並逐檔審查 |
| Covers Sports Odds History | 可以 | 奪冠、分區、勝場等 futures 歷史研究 | 人工查詢 | 不是逐場 moneyline／T-60／Closing 資料，不適合比賽級回測 |
| Kaggle | 可以，但需逐資料集判斷 | 下載研究用 CSV／SQLite，建立 closing-market benchmark | 只下載明確授權或經人工批准的資料集 | Kaggle 是平台，不是單一來源；授權、provenance、更新日期與欄位品質各自不同 |

## 1. OddsPortal

- NBA results 頁面目前可查看 1998-99 至今的賽季清單與歷史賠率。
- 適合人工打開單場，核對結果、開收盤與多家博彩公司差異。
- 不列入自動資料管線。OddsPortal 條款明確限制資料作個人使用，並禁止未經同意的 extraction、scraping、aggregating、recreating 以及 automated requests。
- 專案狀態：`manual_reference_only`。

來源：
- https://www.oddsportal.com/basketball/usa/nba/results/
- https://www.oddsportal.com/terms/

## 2. SportsbookReviewOnline / SBR archive

使用者提供的舊網址：

- https://sportsbookreviewsonline.com/scoresoddsarchives/nba/nbaoddsarchives.htm

於 2026-07-17 已無法直接取得並回傳 404，因此不能把它當成穩定的自動來源。

歷史上這套 archive 常見格式為每場兩列（Visitor／Home），包含日期、rotation、隊伍、比分與 moneyline 等欄位。現存 Kaggle 鏡像仍可作研究輸入，但必須：

1. 保存原始檔 SHA-256 與鏡像資料集版本。
2. 不假設 old archive 的 `ML` 一定具有精確收盤時間戳。
3. 不把 opening／closing 標籤當作 T-60m 或可稽核的 observed_at。
4. 未確認再發布權前，不把大型原始檔提交到公開 repository。

專案狀態：原站 `unavailable_legacy_reference`；鏡像資料可進 `closing_benchmark_pilot`。

## 3. Covers Sports Odds History

- Covers 的 Sports Odds History 明確定位為 archived futures lines。
- 適合研究 NBA 冠軍、分區冠軍、賽季勝場與其他 futures 的歷史變化。
- 不適合目前 game-level moneyline 模型的逐場市場回測。
- 可作未來的 `Futures Research Layer`，但不得混入單場勝率模型評估。

來源：
- https://www.covers.com/sportsoddshistory/
- https://www.covers.com/sportsoddshistory/nba-odds/

專案狀態：`manual_futures_reference`。

## 4. Kaggle

Kaggle 可使用，但必須把每個 dataset 當成獨立來源，而不是把「Kaggle」視為品質保證。

### 優先候選：Christopher Treasure — NBA Odds Data

- URL：https://www.kaggle.com/datasets/christophertreasure/nba-odds-data
- 公開描述：2008-2023 regular season，包含 moneyline、spread、total 與 second-half lines；2023 不完整。
- Provenance：描述指向舊 SportsbookReviewOnline archive。
- License：頁面標示 `Other (specified in description)`，不能視為 CC0。
- 建議：第一順位 `closing-market benchmark` 候選；下載後先做欄位、賽季、重複、隊名與 moneyline QA。

### 次級候選：Evan Hallmark — NBA Historical Stats and Betting Data

- URL：https://www.kaggle.com/datasets/ehallmar/nba-historical-stats-and-betting-data
- 包含 moneyline、spread、totals 等多個 CSV；頁面顯示資料集較舊。
- License：Unknown。
- 建議：只作交叉比對或人工研究，不進正式自動管線，直到 provenance 與授權明確。

### 次級候選：Eric Qiu — NBA Odds and Scores

- URL：https://www.kaggle.com/datasets/erichqiu/nba-odds-and-scores
- 頁面標示 CC0，包含多季 regular season／playoff odds 與 scores。
- 但來源描述僅稱由 various sources compiled，仍需驗證 bookmaker、開收盤定義、時間戳與欄位一致性。
- 建議：可作第二份交叉驗證資料，不可因 CC0 標籤就跳過 provenance QA。

### 不直接採用的例子

- 由 OddsPortal scraping 產生的 Kaggle dataset：即使檔案可下載，也需考慮原始網站條款及資料庫權利；不納入自動管線。
- License Unknown 的 dataset：只可人工研究，不公開再發布。

## 資料層級

### A. Point-in-time odds

必須有：

- exact `observed_at_utc`
- `commence_time_utc`
- bookmaker
- 同一時間的雙邊市場賠率
- T-60m／T-5m／Closing 快照

可計算：EV、ROI、CLV、最大回撤。

### B. Closing-label-only archive

只有 `Closing` 或一個最終 moneyline，沒有 exact observed timestamp。

可計算：

- closing no-vig probability
- model vs closing-market Log Loss
- model vs closing-market Brier Score
- 賽季級 forecast benchmark

不可計算或宣稱：

- T-60m entry ROI
- CLV
- 可交易 edge
- point-in-time betting backtest

## 新增工具

### 匯入 CSV / Excel

```bash
python scripts/import_closing_odds_archive.py \
  --input /path/to/nbaodds2022.xlsx \
  --season-start-year 2021 \
  --source-id kaggle_christophertreasure_nba_odds \
  --output-dir /tmp/nbavl-closing-odds
```

支援：

- SBR 常見兩列格式：`Date, Rot, VH, Team, ML`
- 一場一列 wide 格式：日期、主客隊、主客 moneyline
- CSV、XLSX、XLS
- 隊名 alias、American-to-decimal、去水機率、overround、重複與錯誤列 QA

### 與 Walk-forward 預測比較

```bash
python scripts/evaluate_closing_market_benchmark.py \
  --predictions walk-forward-predictions.csv \
  --closing-odds /tmp/nbavl-closing-odds/closing-moneyline-normalized.csv \
  --output-dir /tmp/nbavl-closing-benchmark
```

輸出：

- `closing-benchmark-report.json`
- `closing-benchmark-joined.csv`

## 接入優先順序

1. 先下載 Christopher Treasure Kaggle dataset，作 closing benchmark pilot。
2. 用 Eric Qiu CC0 dataset 做比分、主客隊與 moneyline 抽樣交叉驗證。
3. OddsPortal 僅人工抽樣核對，不自動爬取。
4. Covers 暫存為 futures research，不接 game-level pipeline。
5. 真正 ROI／CLV 仍等待有精確時間戳的合法 point-in-time odds。
