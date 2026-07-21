# NBA Value Lab — Project Status

狀態核對日期：2026-07-21  
研究定位：**Research Candidate / Pre-Market-Backtest**  
正式 Stake：**0**

最新 `main`、已合併 PR、GitHub Actions 與 Artifact QA 是正式 Source of Truth。若聊天內容或舊文件與 Repository 衝突，以最新 Repository 為準。

## Current Control Block

```text
latest main research merge: f53d76c8df58b951b84609477a566db1d525ac56
current work mode: OFFSEASON_DATA_CONSTRUCTION
live odds capture required now: false
formal stake: 0
```

### Currently open research execution PRs

```text
None
```

### Next unique mainline

```text
USER_SUPPLIED_LEGACY_MARKET_ARCHIVE_REAL_FILE_AUDIT_INPUTS_REQUIRED
```

PR #105 已凍結使用者提供之 Legacy Market Archive 與五季 Historical Silver／Gold 的 deterministic cross-source audit 規則；PR #106 已完成 audit runner、5,800 場 synthetic self-test 與 aggregate-only CI 驗證。

目前不需要等 NBA 開季，也不需要啟動即時盤口擷取。下一步是準備或重建下列三項精確輸入，再另行建立 real-file execution request：

```text
1. 原始 nba_2008-2026.csv
2. historical-gold-multiseason.sqlite 或 .sqlite.gz
3. 包含 games table 的 combined Historical Silver SQLite
```

## Latest Completed Research Work

```text
PR #69  — Historical Secondary Source Qualification v1 predeclaration
PR #70  — Historical Secondary Source Metadata Census v1
PR #71  — Wyatt SQLite File-level Pilot v1 predeclaration
PR #72  — Wyatt SQLite Census Runner v1 implementation
PR #74  — Wyatt SQLite operational size ceiling amendment
PR #75  — Wyatt SQLite Aggregate Audit v1
PR #77  — Eoin preflight Artifact validation documentation
PR #78  — Eoin full adapter execution policy v1
PR #79  — Disabled Eoin full adapter runner guardrails v1
PR #80  — One-time Eoin full adapter execution request v1
PR #81  — Eoin request status and source-registry sync
PR #82  — Explicit Eoin approval record and manual one-time workflow
PR #83  — Approved Eoin manual-dispatch status sync
PR #96  — Reconciled Eoin post-execution status
PR #97  — Eoin post-execution role review policy v1
PR #98  — Eoin role review policy status sync
PR #100 — Eoin post-execution role review evaluation v1
PR #101 — Eoin secondary QA validation result sync
PR #102 — Eoin secondary QA integration policy v1
PR #103 — Eoin secondary QA contract monitor v1
PR #104 — Healthy Eoin secondary QA monitor status sync
PR #105 — User-supplied legacy market cross-source audit predeclaration v1
PR #106 — Legacy market cross-source audit implementation v1
```

## User-supplied Legacy Market Archive

### Candidate identity

```text
source id: kaggle_cviaxmiwnptr_nba_betting_data_user_supplied
dataset: cviaxmiwnptr/nba-betting-data-october-2007-to-june-2024
required file: nba_2008-2026.csv
bytes: 2,493,308
SHA-256: 729eb2ead85c14affbb81ae9a4c611fee9790b8dd3d1d7824e1ddba14410a8c4
rows: 24,440
columns: 27
provenance: user_confirmed
current formal role: ROLE_LIMITED_LEGACY_MARKET_ARCHIVE_ELIGIBLE
```

目前可找到的 `nba_2008-2026_cleaned.csv` 是衍生檔，欄位數已改變，不能在 v1 中冒充上述原始檔。若只保留 cleaned file，必須建立新版本政策，不能偷偷放寬檔案身分 gate。

### Frozen overlap scope

```text
reference seasons: 2019-20 through 2023-24
candidate labels: 2020 through 2024
candidate filter: regular == true and playoffs == false
join key: game_date + home_team_abbr + away_team_abbr
```

禁止 fuzzy matching、manual key override、many-to-many join，以及使用比分修補身份。比分只能驗證已配對的比賽。

### Frozen scientific gates

```text
reference games >= 5,700
eligible candidate games >= 5,700
reference match rate >= 98.5%
candidate match rate >= 98.5%
matched score-pair rate >= 99.0%
each-season reference match rate >= 97.0%
duplicate key groups = 0
ambiguous join keys = 0
unresolved team codes = 0
invalid dates = 0
missing in-scope scores = 0
raw rows emitted = 0
raw files emitted = false
```

### Implementation validation evidence

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
external Artifact downloads: false
real-file audit executed: false
raw rows emitted: 0
raw files emitted: false
source role changed: false
formal stake: 0
```

Synthetic validation covers：完整 gate pass、未知隊伍代碼 fail-closed、比分一致率 gate、禁止權限漂移 fail-closed、錯誤真實檔案身分 fail-closed。

### Real-file execution state

```text
real-file audit executed: false
real-file execution authorized: false
source role promoted: false
```

在 exact original candidate、Gold DB 與 Silver DB 同時可用前，不建立虛假的 audit 結果。

## Eoin Evidence Line

```text
formal execution result: ONE_TIME_FULL_ADAPTER_AGGREGATE_VALIDATION_PASS
formal source role: ROLE_LIMITED_SECONDARY_QA_SOURCE_VALIDATED
contract monitor: EOIN_SECONDARY_QA_CONTRACT_HEALTHY
integration mode: alert_only_evidence_contract_monitor
source-data integration active: false
request consumed: true
repeat execution allowed: false
evidence review due: 2027-07-21
```

Eoin 只可作 deterministic game identity、final score、team boxscore、player candidate coverage-only、PBP coverage 與 cross-source regression QA。不是 primary source，不是 Silver／Gold replacement，也沒有 independent player-stat parity。

## Current Research Position

### Historical Model

- Historical Gold：Completed，5,824 matchup rows，strict PIT violations 0。
- Logistic + Elo Walk-forward v2：Completed，3,688 OOF；機率品質小幅優於 Elo。
- Closing Market Benchmark：模型明顯輸給 Closing Market。
- Expected Minutes Audit v3：`ACCURACY_PASS`。
- Injury Feature Holdout v1：`VALID_NEGATIVE_RESULT`；維持 baseline-only path。

### Wyatt Walsh SQLite

```text
STRUCTURAL_BLOCKED
```

真實檔案只有 16 tables、最晚 game date 2023-06-12、2023-24 pilot games 0，且沒有 player game boxscore candidate table。

### Live / Point-in-time Market Data

```text
OFFSEASON_CAPTURE_SLEEP_MODE
```

尚未開季，因此暫不核准或執行新的 live snapshot capture。真實 bookmaker-level PIT source 合格數仍為 0；Production Odds Backfill、PIT Odds Join、Market Backtest、CLV、EV、ROI 與 Drawdown 保持 blocked。

## Core Status

| Module | Status | Formal conclusion |
|---|---|---|
| Historical Gold | Completed | 5,824 matchup rows；strict PIT violations 0。 |
| Logistic + Elo Walk-forward v2 | Completed | 3,688 OOF；機率品質小幅優於 Elo。 |
| Closing Market Benchmark | Model lost | 模型明顯輸給 Closing Market。 |
| Expected Minutes Audit v3 | **ACCURACY_PASS** | Frozen gates 全部通過。 |
| Injury Feature Holdout v1 | **VALID_NEGATIVE_RESULT** | 未達 promotion gates。 |
| Paid Historical Odds Pilot | **NOT APPROVED** | 付費與 paid execution 未授權。 |
| No-cost PIT Odds Census | **NO_COST_METADATA_BLOCKED** | 8 candidates；qualified 0。 |
| Wyatt Real-file Audit | **STRUCTURAL_BLOCKED** | 不符合目前研究需求。 |
| Eoin Secondary QA | **VALIDATED / HEALTHY** | Alert-only deterministic QA。 |
| Legacy Market Archive | **IMPLEMENTATION READY / REAL EXECUTION DISABLED** | 等待 exact candidate + Gold + Silver。 |
| Market Backtest | Blocked | 尚無 executable PIT odds join。 |
| Betting Decision Layer | Blocked | Stake = 0。 |

## Preserved Model Evidence

Historical OOF：

```text
Games: 3,688
Logistic + Elo Log Loss: 0.631306
Elo Log Loss: 0.634301
Logistic + Elo Brier: 0.220567
Elo Brier: 0.221949
```

Closing benchmark（1,894 matched games）：

| Metric | Model | Closing |
|---|---:|---:|
| Log Loss | 0.6421 | **0.6167** |
| Brier | 0.2250 | **0.2139** |
| Accuracy | 63.62% | **66.37%** |

正式結論：模型目前輸給 Closing Market；不得宣稱 betting edge。

## Do Not Do

- 不以 cleaned／derived CSV 冒充 frozen exact candidate file。
- 不在缺少 Gold 或 Silver DB 時捏造 cross-source audit 結果。
- 不公開或 commit 原始大型 CSV、SQLite、Parquet、PBP 或第三方 archive。
- 不把 raw source files 上傳成公開 Artifact。
- 不使用 fuzzy matching、人工覆寫或比分修補 game identity。
- 不把 legacy archive 寫成 point-in-time、Opening 或 Closing source。
- 不重複執行已消耗的 Eoin request。
- 不把 Eoin QA role 寫成 primary source 或 player-stat parity。
- 不替換已驗證的 Historical Silver／Gold 主路徑。
- 不重新開啟付費 odds 路徑，除非使用者未來另行明確改變決定。
- 未完成合格 PIT odds join 前，不宣稱 CLV、EV、ROI、Drawdown 或 betting edge。
- 正式 Stake 維持 0。

## Important Files

- `PROJECT_STATUS.md`
- `README.md`
- `data/historical-odds-source-registry.json`
- `data/research/user-supplied-nba-betting-csv-provenance-current-status-v1.json`
- `data/research/user-supplied-legacy-market-archive-cross-source-audit-predeclaration-v1.json`
- `data/research/user-supplied-legacy-market-archive-cross-source-audit-implementation-v1.json`
- `scripts/run_user_supplied_legacy_market_archive_cross_source_audit_v1.py`
- `.github/workflows/validate-user-supplied-legacy-market-archive-cross-source-audit-implementation-v1.yml`

## Explicit Next Step

```text
Prepare exact original candidate file and reproducible Gold/Silver reference inputs.
Do not activate live odds capture during the offseason.
```

收到完整三項輸入後，下一個變更只能是 separate real-file execution request；它仍不得解鎖 PIT market backtest 或非零 Stake。
