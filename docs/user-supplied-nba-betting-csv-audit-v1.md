# User-supplied NBA Betting CSV Audit v1

更新日期：2026-07-21（Asia/Taipei）

## Purpose

本次處理使用者提供的 `nba_2008-2026.csv`，依 `Source Intake SOP v1` 執行 Class A 本機檔案的 aggregate-only file audit。

本次沒有把原始 CSV、原始資料列或大型衍生表提交到 GitHub。Repository 只保存稽核程式、SHA-256、schema、coverage、缺失統計、結構一致性與正式研究 Gate。

## Repository source of truth checked first

開始前已確認：

- `PROJECT_STATUS.md`
- `README.md`
- `docs/source-intake-sop-v1.md`
- `docs/historical-odds-source-evaluation-v1.md`
- `data/historical-odds-source-registry.json`
- `scripts/import_closing_odds_archive.py`

現有 Closing importer 與 market benchmark 不重做。本次新增的是針對這份 27 欄 wide CSV 的 file-level qualification，並保留未知盤口時間語意。

## File identity

```text
file: nba_2008-2026.csv
bytes: 2,493,308
sha256: 729eb2ead85c14affbb81ae9a4c611fee9790b8dd3d1d7824e1ddba14410a8c4
rows: 24,440
columns: 27
date range: 2007-10-30 through 2026-06-13
season labels: 2008 through 2026
```

## Provenance status

檔案欄位與 Kaggle dataset `cviaxmiwnptr/nba-betting-data-october-2007-to-june-2024` 的公開 schema 完整吻合；該頁面標示 CC0，並描述 2007-10-30 至 2023-01-16 來自 Sportsbook Reviews Online、2023-01-17 起改用 ESPN。

但使用者尚未明確確認這份本機檔案就是從該網址下載，因此目前正式 provenance 狀態是：

```text
pending_user_confirmation
```

不得把 schema match 寫成已由使用者確認的來源證明。

## Aggregate audit result

```text
30 team codes
19 season labels
exact date+away+home duplicate groups: 0
invalid dates: 0
quarter+OT versus final-score mismatches: 0
id_spread result mismatches: 0
id_total result mismatches: 0
invalid complete moneyline values: 0
moneyline overround outside -5% to 30%: 0
```

Game type counts：

```text
regular: 22,808
playoffs: 1,592
other_or_play_in: 40
invalid regular=true and playoffs=true: 0
```

Market availability：

```text
spread non-null: 24,437
total non-null: 24,440
complete moneyline pairs: 19,810
missing moneyline pairs: 4,630
partial moneyline pairs: 0
h2_spread missing: 4,618
h2_total missing: 4,623
```

2024、2025、2026 season labels 的 moneyline 與 second-half lines 全部缺失。缺失值不得填 0，也不得當成 unchanged quote。

## Formal outcome

```text
ROLE_LIMITED_LEGACY_MARKET_ARCHIVE_ELIGIBLE_PROVENANCE_PENDING
```

允許：

- game identity 與 final score deterministic cross-check
- spread／total descriptive research
- 具有完整雙邊 moneyline 的 forecast benchmark pilot
- 與 Historical Gold 進行預先宣告、確定性 key 的交叉稽核

仍禁止：

- 把盤口稱為 Opening 或 Closing
- Point-in-time odds join
- T-60m／T-5m entry backtest
- CLV、entry-price ROI、Drawdown
- betting edge 或非 0 Stake
- 取代既有 Historical Silver／Gold
- 未經 Gate 的模型重訓

## Why it is not a second timestamped odds snapshot

檔案沒有：

```text
bookmaker
observed_at
opening_at
closing_at
same-book open/close history
```

因此它是 legacy market archive，不是 Odds History Hub 的第二份快照，也不會解鎖 market backtest。

## Reproduce

```bash
python scripts/audit_user_supplied_nba_betting_csv_v1.py \
  --input /path/to/nba_2008-2026.csv \
  --output /tmp/user-supplied-nba-betting-csv-audit-v1.json \
  --source-id kaggle_cviaxmiwnptr_nba_betting_data_user_supplied \
  --source-url https://www.kaggle.com/datasets/cviaxmiwnptr/nba-betting-data-october-2007-to-june-2024 \
  --supplied-at 2026-07-21T09:48:48+08:00 \
  --provenance-status pending_user_confirmation
```

## Exact next step

建立獨立 PR，預先宣告 deterministic cross-source audit：

```text
pilot seasons: overlap with verified Historical Gold only
join key: game_date + home_team + away_team
score used as validation field, not fuzzy key repair
fuzzy matching: false
raw CSV committed: false
Silver/Gold replacement: false
model retraining: false
market backtest: false
formal Stake: 0
```

在 cross-source audit 通過前，不把這份 CSV 升格為正式模型輸入。
