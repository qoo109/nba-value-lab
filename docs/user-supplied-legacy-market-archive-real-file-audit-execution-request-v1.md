# Legacy Market Archive Real-file Audit Execution Request v1

更新日期：2026-07-21（Asia/Taipei）

## Purpose

本文件建立一次性的真實檔案 cross-source audit 執行請求：

```text
LEGACY-MARKET-ARCHIVE-AUDIT-2026-07-21-001
```

目前狀態：

```text
AWAITING_EXPLICIT_USER_APPROVAL
```

此階段只建立並驗證 request，不會下載資料、不會重建 Silver／Gold，也不會執行真實稽核。

## Why a separate request is required

PR #105 已凍結科學規則；PR #106 已完成 deterministic runner 與 5,800 場 synthetic validation；PR #107 已記錄 implementation evidence。Implementation 的正式狀態仍是：

```text
USER_SUPPLIED_LEGACY_MARKET_ARCHIVE_CROSS_SOURCE_AUDIT_IMPLEMENTATION_READY_BUT_REAL_FILE_EXECUTION_DISABLED
```

因此下一步不能直接啟動網路下載或讀取真實資料，必須先取得一次性、明確的使用者核准。

## Exact candidate

唯一可接受 candidate：

```text
dataset handle: cviaxmiwnptr/nba-betting-data-october-2007-to-june-2024
file: nba_2008-2026.csv
bytes: 2,493,308
SHA-256: 729eb2ead85c14affbb81ae9a4c611fee9790b8dd3d1d7824e1ddba14410a8c4
rows: 24,440
columns: 27
```

Cleaned、renamed 或 derived 檔案不能替代。Approved workflow 在暫存空間下載 Kaggle dataset 後，只能用 exact bytes + SHA-256 選取檔案；找不到唯一符合者就 fail closed。

## Reference reconstruction

真實稽核需要：

```text
Historical Silver combined SQLite with games table
Historical Gold multiseason SQLite with gold_matchup_features
```

因既有單季 Silver artifacts 已到期，approved workflow 必須在同一個 temporary runner workspace 重建：

```text
2019-20
2020-21
2021-22
2022-23
2023-24
```

流程只使用既有、已驗證的 `shufinskiy/nba_data` builder 路徑，不替換正式 Silver／Gold。

## One-time approved operations

明確核准後，一次性 workflow 才可：

1. 在暫存空間下載 confirmed Kaggle candidate；
2. exact bytes／SHA-256 驗證；
3. 下載五季 reference archives 到暫存空間；
4. 建立 audited per-season Silver；
5. 合併 Silver 並建立 Gold；
6. 執行 frozen deterministic audit；
7. 刪除 candidate、archives、Silver、Gold 與暫存 rows；
8. 只上傳一份不超過 1 MiB 的 aggregate JSON。

## Prohibited output

不得上傳：

- 原始 candidate CSV；
- 原始或合併 Silver／Gold database；
- PBP、Parquet 或 source archives；
- raw rows；
- unmatched keys；
- game IDs；
- 個別比分不一致清單；
- derived row-level tables。

## Frozen audit rules

```text
candidate filter: season 2020..2024 and regular == true and playoffs == false
join key: game_date + home_team_abbr + away_team_abbr
Gold ↔ Silver: exact game_id
fuzzy matching: false
manual override: false
many-to-many: false
score identity repair: false
```

Frozen gates 仍由：

```text
data/research/user-supplied-legacy-market-archive-cross-source-audit-predeclaration-v1.json
```

控制，不得在 request 或執行階段降低。

## Approval boundary

Request validation 通過後的狀態只能是：

```text
LEGACY_MARKET_ARCHIVE_REAL_FILE_AUDIT_REQUEST_VALID_AWAITING_EXPLICIT_USER_APPROVAL
```

它不等於 execution enabled。使用者必須明確核准完整 request ID 與邊界，之後才能建立 approval record 與單次 workflow。

建議核准文字：

> 我核准 request LEGACY-MARKET-ARCHIVE-AUDIT-2026-07-21-001 執行一次 workflow_dispatch 的 aggregate-only Legacy Market Archive 真實檔案 cross-source audit。核准範圍包含在暫存空間下載已確認的 Kaggle candidate、重建五季 Historical Silver／Gold、讀取暫存資料列並依 frozen deterministic gates 稽核；不得上傳原始 CSV、資料庫、來源 archive 或逐場資料，不得解鎖 Opening／Closing、PIT market backtest、CLV、EV、ROI、Drawdown、模型重訓、betting edge 或非 0 Stake。

## Unchanged blocks

即使後續真實 audit 通過，也不會解鎖：

- bookmaker／observed_at；
- Opening／Closing；
- point-in-time odds join；
- T-60／T-5 entry backtest；
- CLV、EV、ROI、Drawdown；
- Historical Silver／Gold replacement；
- model retraining；
- betting-edge claim；
- 非 0 Stake。

## Exact next step

Request CI 通過並合併後，等待使用者提供上述明確核准文字。未核准前不得建立或啟動真實 execution workflow。
