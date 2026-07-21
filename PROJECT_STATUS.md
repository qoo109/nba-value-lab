# NBA Value Lab — Project Status

狀態核對日期：2026-07-21  
研究定位：**Research Candidate / Pre-Market-Backtest**  
正式 Stake：**0**

最新 `main`、已合併 PR、GitHub Actions 與 Artifact QA 是正式 Source of Truth。

## Current Control Block

```text
latest main research merge: f53d76c8df58b951b84609477a566db1d525ac56
current work mode: OFFSEASON_DATA_CONSTRUCTION
live odds capture required now: false
formal Eoin source role: ROLE_LIMITED_SECONDARY_QA_SOURCE_VALIDATED
request consumed: true
repeat execution allowed: false
formal stake: 0
```

## Next Unique Mainline

```text
USER_SUPPLIED_LEGACY_MARKET_ARCHIVE_REAL_FILE_AUDIT_INPUTS_REQUIRED
```

PR #105 已凍結 Legacy Market Archive cross-source audit 規則；PR #106 已完成 deterministic runner、5,800 場 synthetic self-test 與 aggregate-only CI 驗證。

下一步是準備三項精確輸入：

```text
1. 原始 nba_2008-2026.csv
2. historical-gold-multiseason.sqlite 或 .sqlite.gz
3. 包含 games table 的 combined Historical Silver SQLite
```

## Legacy Market Archive

```text
source id: kaggle_cviaxmiwnptr_nba_betting_data_user_supplied
required file: nba_2008-2026.csv
bytes: 2,493,308
SHA-256: 729eb2ead85c14affbb81ae9a4c611fee9790b8dd3d1d7824e1ddba14410a8c4
rows: 24,440
columns: 27
provenance: user_confirmed
current role: ROLE_LIMITED_LEGACY_MARKET_ARCHIVE_ELIGIBLE
```

`nba_2008-2026_cleaned.csv` 是衍生檔，不能在 v1 中替代上述原始檔。

Frozen comparison contract：

```text
reference seasons: 2019-20 through 2023-24
candidate labels: 2020 through 2024
candidate filter: regular == true and playoffs == false
join key: game_date + home_team_abbr + away_team_abbr
fuzzy matching: false
manual key override: false
score-assisted identity repair: false
```

Frozen quality gates：

```text
reference games >= 5,700
eligible candidate games >= 5,700
reference match rate >= 98.5%
candidate match rate >= 98.5%
matched score-pair rate >= 99.0%
each-season reference match rate >= 97.0%
duplicate / ambiguous / unresolved / invalid / missing-score counts = 0
raw rows emitted = 0
raw files emitted = false
```

Implementation evidence：

```text
formal state: USER_SUPPLIED_LEGACY_MARKET_ARCHIVE_CROSS_SOURCE_AUDIT_IMPLEMENTATION_READY_BUT_REAL_FILE_EXECUTION_DISABLED
workflow run: 29798628467
artifact id: 8482916767
artifact digest: sha256:b6b7b9483b603dea278989c162ae0f3025e6df962f9f51571e465fbb26fe8c70
fixture games: 5,800
self-tests passed: 5 / 5
real candidate CSV read: false
real reference database read: false
network calls: false
real-file audit executed: false
raw rows emitted: 0
raw files emitted: false
source role changed: false
formal stake: 0
```

## Eoin Evidence Line

```text
formal execution result: ONE_TIME_FULL_ADAPTER_AGGREGATE_VALIDATION_PASS
formal Eoin source role: ROLE_LIMITED_SECONDARY_QA_SOURCE_VALIDATED
contract monitor: EOIN_SECONDARY_QA_CONTRACT_HEALTHY
integration mode: alert_only_evidence_contract_monitor
source data integration active: false
request consumed: true
repeat execution allowed: false
evidence review due: 2027-07-21
formal stake: 0
```

Eoin 只可作 deterministic QA 與 cross-source regression detection，不是主要資料來源，也不替換 Historical Silver／Gold。

## Current Research Position

- Historical Gold：Completed，5,824 matchup rows，strict PIT violations 0。
- Logistic + Elo Walk-forward v2：Completed，3,688 OOF。
- Closing Market Benchmark：模型明顯落後 Closing Market。
- Expected Minutes Audit v3：`ACCURACY_PASS`。
- Injury Feature Holdout v1：`VALID_NEGATIVE_RESULT`。
- Wyatt Real-file Audit：`STRUCTURAL_BLOCKED`。
- Eoin Secondary QA：`VALIDATED / HEALTHY / ALERT-ONLY`。
- Legacy Market Archive：`IMPLEMENTATION READY / REAL EXECUTION DISABLED`。

## Offseason Market State

```text
OFFSEASON_CAPTURE_SLEEP_MODE
```

尚未開季，因此目前不執行新的 live snapshot capture。Point-in-time join 與後續市場評估仍維持 blocked。

## Do Not Do

- 不以 cleaned／derived CSV 冒充 frozen exact candidate file。
- 不在缺少 Gold 或 Silver DB 時建立假的 real audit 結果。
- 不公開或 commit 原始大型 CSV、SQLite、Parquet 或第三方 archive。
- 不使用 fuzzy matching、人工覆寫或比分修補 game identity。
- 不把 Legacy Archive 標示為 point-in-time、Opening 或 Closing source。
- 不重複執行已消耗的 Eoin request。
- 正式 Stake 維持 0。

## Important Files

- `data/historical-odds-source-registry.json`
- `data/research/user-supplied-nba-betting-csv-provenance-current-status-v1.json`
- `data/research/user-supplied-legacy-market-archive-cross-source-audit-predeclaration-v1.json`
- `data/research/user-supplied-legacy-market-archive-cross-source-audit-implementation-v1.json`
- `scripts/run_user_supplied_legacy_market_archive_cross_source_audit_v1.py`

## Explicit Next Step

```text
Prepare exact original candidate file and reproducible Gold/Silver reference inputs.
Keep live odds capture asleep during the offseason.
```
