# User-supplied Legacy Market Archive Cross-source Audit Implementation v1

更新日期：2026-07-21（Asia/Taipei）

## Purpose

本階段實作 PR #105 已合併的 deterministic、aggregate-only cross-source audit。實作完成後，才允許在另一個明確的 `workflow_dispatch` 執行真實檔案比對。

本階段不改變來源角色，也不宣稱真實稽核已經完成。

## Repository state checked first

開始前已確認：

- `PROJECT_STATUS.md`
- `README.md`
- `docs/source-intake-sop-v1.md`
- `docs/historical-gold-layer.md`
- `docs/historical-expansion-walk-forward-v2.md`
- PR #95：本機 CSV aggregate audit
- PR #99：使用者來源確認
- PR #105：cross-source audit predeclaration
- 現行 Historical Gold／Silver schema
- Eoin 線已完成並暫停，不重複任何 Eoin 工作

## Current source state

```text
ROLE_LIMITED_LEGACY_MARKET_ARCHIVE_ELIGIBLE
```

Implementation ready 不等於 cross-source validation pass。

## Implemented runner

```text
scripts/run_user_supplied_legacy_market_archive_cross_source_audit_v1.py
```

Runner 可接受：

```text
--candidate-csv <local exact file>
或
--dataset-handle cviaxmiwnptr/nba-betting-data-october-2007-to-june-2024

--gold-db historical-gold-multiseason.sqlite[.gz]
--silver-db historical-silver-multiseason.sqlite[.gz]
--predeclaration data/research/user-supplied-legacy-market-archive-cross-source-audit-predeclaration-v1.json
--output-dir <aggregate output directory>
```

Kaggle 模式不是「抓到名字相同就使用」。Runner 必須找到唯一一個同時符合：

```text
bytes: 2,493,308
SHA-256: 729eb2ead85c14affbb81ae9a4c611fee9790b8dd3d1d7824e1ddba14410a8c4
```

的檔案，否則 fail closed。

## Reference contract

Identity 來自：

```text
gold_matchup_features
+ gold_team_game_features（season_label）
```

Final score 驗證來自：

```text
Historical Silver games
```

使用 Gold 的 `home_feature_id` 連到 season label，再以相同 `game_id` 讀取 Silver final scores。Gold 或 Silver 缺表、缺欄位、缺 score game ID 都會阻擋稽核。

## Deterministic join

唯一 join key：

```text
game_date + home_team_abbr + away_team_abbr
```

固定規則：

- candidate 只取 season 2020～2024；
- `regular == true and playoffs == false`；
- 固定 30 隊代碼映射；
- fuzzy matching = false；
- manual key override = false；
- many-to-many join = false；
- score 只能驗證 identity，不能修補 identity。

## Aggregate-only outputs

Runner 只輸出：

```text
user-supplied-legacy-market-archive-cross-source-audit-report.json
user-supplied-legacy-market-archive-cross-source-run-status.json
```

內容可包含：

- candidate／reference SHA-256 與 bytes；
- eligible counts；
- season aggregate counts；
- matched／unmatched counts；
- match rates；
- score-pair match rate；
- duplicate／ambiguous／invalid aggregate counts；
- failed gate names；
- formal outcome；
- unchanged guardrails。

永遠不得輸出：

- 原始 CSV rows；
- 原始 Silver／Gold rows；
- unmatched keys；
- individual game IDs；
- 個別不一致比賽清單；
- 原始資料庫或 source archives。

## Synthetic tests

Pull request CI 只執行 synthetic tests：

1. 完整 deterministic match → `ROLE_LIMITED_LEGACY_MARKET_ARCHIVE_CROSS_SOURCE_VALIDATED`
2. identity 相同但一筆 score mismatch → `RETAIN_ROLE_LIMITED_LEGACY_MARKET_ARCHIVE_ELIGIBLE`
3. duplicate deterministic key → `USER_SUPPLIED_LEGACY_MARKET_ARCHIVE_CROSS_SOURCE_AUDIT_RESEARCH_BLOCKED`

Synthetic CI 不讀真實 candidate CSV，也不讀真實 Historical databases。

## Real execution workflow

```text
.github/workflows/run-user-supplied-legacy-market-archive-cross-source-audit-v1.yml
```

真實 job 只會在：

```text
workflow_dispatch
execute_real_audit = true
```

時執行。

Workflow 會在同一個 temporary runner workspace：

1. 重新建立五季 audited Silver；
2. 合併 multiseason Silver；
3. 建立 season-aware Gold；
4. 下載 confirmed Kaggle dataset；
5. 以 exact bytes + SHA-256 選取 candidate；
6. 執行 frozen deterministic audit；
7. 刪除 candidate、Silver、Gold 與 source temporary files；
8. 只上傳兩份 aggregate JSON。

不使用中間 raw database Artifact 傳遞，因此不會把 Silver、Gold、CSV、PBP 或來源 archives 上傳成 Artifact。

## Frozen reference evidence anchor

Implementation 記錄既有已驗證 evidence：

```text
workflow run: 29551715399
head SHA: c9ad2281c04b35a551acb617fcc255ce36af7a29
historical-gold-multiseason artifact id: 8396002371
artifact digest: sha256:c831e2fc1b03b99319e2847a015a0e94744574bfa6ebff49e43da3f3ed201538
Gold matchup rows: 5,824
```

真實執行仍會重新建立 Silver／Gold，以取得 policy 要求的完整 `games` score table；不會把過期的一日 Silver Artifact 當作仍可用。

## Candidate execution outcomes

Runner 只能輸出：

```text
ROLE_LIMITED_LEGACY_MARKET_ARCHIVE_CROSS_SOURCE_VALIDATED
RETAIN_ROLE_LIMITED_LEGACY_MARKET_ARCHIVE_ELIGIBLE
USER_SUPPLIED_LEGACY_MARKET_ARCHIVE_CROSS_SOURCE_AUDIT_RESEARCH_BLOCKED
```

Implementation 本身不選擇任何真實 outcome。

## Still blocked

無論後續 cross-source audit 結果為何，本實作都不解鎖：

- Opening／Closing 語意；
- bookmaker identity；
- exact `observed_at`；
- Point-in-time odds join；
- T-60m／T-5m entry backtest；
- CLV、entry-price ROI、Drawdown；
- betting edge；
- Historical Silver／Gold replacement；
- model retraining；
- 非 0 Stake。

## Exact next step

```text
USER_SUPPLIED_LEGACY_MARKET_ARCHIVE_CROSS_SOURCE_AUDIT_EXECUTION
```

必須先合併並通過本 Implementation CI，再由明確的 `workflow_dispatch` 執行。執行後只根據 frozen gates 與 aggregate Artifact 記錄正式 outcome。
