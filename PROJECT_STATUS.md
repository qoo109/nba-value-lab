# NBA Value Lab — Project Status

更新日期：2026-07-18  
定位：**Research Candidate / Pre-Market-Backtest**  
正式 Stake：**0**

最新 `main`、已合併 PR、Actions 與 Artifact QA 是正式 Source of Truth。

## Current Control Block

### Latest Main SHA at this snapshot

```text
7b60dd9b7a35e4dcc2ab2e04ade7409ee6538afe
```

最新完成：

```text
PR #69 — Historical Secondary Source Qualification v1 predeclaration
PR #70 — Historical Secondary Source Metadata Census v1
PR #71 — Wyatt SQLite File-level Pilot v1 predeclaration
PR #72 — Wyatt SQLite Census Runner v1 implementation
```

### Currently open research execution PRs

```text
None
```

### Next unique mainline

```text
INPUT_FILE_REQUIRED
```

下一個正式執行只在使用者提供 Wyatt Walsh `.sqlite`／`.sqlite3`／`.db` 檔後開始。不得把 synthetic runner success 寫成真實來源已通過。

### Parallel blocked line

```text
PAUSE_MARKET_DATA_LINE_UNTIL_MATERIALLY_NEW_LAWFUL_SOURCE_OR_USER_FILE
```

市場資料線仍暫停；使用者已不核准付費 Historical Odds pilot。

## Known blockers

- Wyatt Walsh 真實 SQLite 尚未提供，因此 schema census 與 2023-24 cross-source audit 尚未執行。
- Eoin A Moore 與 Wyatt Walsh 目前都只有 metadata-ready，完整次要來源合格數仍為 0。
- 使用者已明確不核准付費 Historical Odds pilot。
- 8 個零成本／既有 odds 候選中，合格 bookmaker-level point-in-time source 為 0。
- Production Odds Backfill、PIT Odds Join、Market Backtest、CLV、EV、ROI、Drawdown 全部未解鎖。
- Historical model 仍明顯輸給 Closing Market。

## Do Not Do

- 不把 PR #72 synthetic SQLite 自測當成 Wyatt 真實資料驗證。
- 不公開或 commit 完整第三方 SQLite、原始 PBP、球員列或大量來源資料。
- 不以 fuzzy matching 連接 game、team、player 或 PBP。
- 不替換目前已驗證的 `shufinskiy/nba_data` Silver／Gold 主路徑。
- 不降低 PR #71 固定的 coverage、identity、score、duplicate 或 integrity gates。
- 不重新開啟付費 odds 路徑，除非使用者未來另行明確改變決定。
- 不建立帳號、訂閱、付款或呼叫付費歷史端點。
- Closing-only benchmark 不得當 executable market backtest。
- 未完成合格 PIT odds join 前，不宣稱 CLV、EV、ROI、Drawdown 或 betting edge。
- 正式 Stake 維持 0。

## Canonical Roadmap

```text
1. Historical Gold and baseline model                       Completed
2. Official injury data and feature-ready matchups          Completed
3. Expected Minutes Accuracy Audit                          ACCURACY_PASS
4. Injury Feature Walk-forward Holdout                      VALID_NEGATIVE_RESULT
5. Real Timestamped Odds Acquisition                        NO_COST_METADATA_BLOCKED
6. Historical Secondary Source Metadata Review              METADATA_READY_DOWNLOAD_NOT_AUTHORIZED
7. Wyatt SQLite read-only census runner                     Completed / synthetic only
8. Wyatt real file schema and 2023-24 cross-source audit     INPUT_FILE_REQUIRED
9. Point-in-time Odds Join and Market Backtest              Blocked
10. CLV / EV / ROI / Drawdown                               Blocked
11. Betting Decision Layer                                  Blocked
```

## Core Status

| Module | Status | Formal conclusion |
|---|---|---|
| Historical Gold | Completed | 5,824 matchup rows；strict PIT violations 0。 |
| Logistic + Elo Walk-forward v2 | Completed | 3,688 OOF；機率品質小幅優於 Elo。 |
| Closing Market Benchmark | Model lost | 模型明顯輸給 Closing Market。 |
| Expected Minutes Audit v3 | **ACCURACY_PASS** | 預先宣告的結構、樣本與數值 gates 全部通過。 |
| Injury Feature Holdout v1 | **VALID_NEGATIVE_RESULT** | Candidate 未達 promotion gates；保留 baseline-only path。 |
| Frozen Odds Pilot Manifest | Completed / no-price | 30 games、180 exact timestamps、Opening labels 0。 |
| Paid Pilot Decision | **NOT APPROVED** | 付費、key 與 paid execution 均未授權。 |
| No-cost Odds Metadata Census | **NO_COST_METADATA_BLOCKED** | 8 candidates；qualified 0。 |
| Historical Secondary Source Policy | Completed | PR #69；Eoin 與 Wyatt 兩候選、固定 2023-24 gates。 |
| Historical Secondary Source Metadata Census | **METADATA_READY_DOWNLOAD_NOT_AUTHORIZED** | PR #70；metadata-ready 2、full-qualified 0。 |
| Wyatt SQLite Pilot Policy | **INPUT_FILE_REQUIRED** | PR #71；真實 SQLite 未提供。 |
| Wyatt SQLite Census Runner | Completed / synthetic only | PR #72；唯讀 runner 已驗證，不代表來源通過。 |
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

Expected Minutes Audit v3：

```text
MAE: 5.120902
RMSE: 6.693908
Median AE: 4.093886
Absolute bias: 0.668968
Starter MAE: 4.663676
Bench MAE: 5.792521
10+ history MAE: 5.092724
Formal state: ACCURACY_PASS
```

Injury Feature Holdout v1：

| Population | Baseline LL | Candidate LL | Gain |
|---|---:|---:|---:|
| Feb development — 65 | 0.657411 | 0.667960 | -0.010549 |
| Mar-Apr final — 104 | 0.589324 | 0.586426 | +0.002898 |
| Combined — 169 | 0.615511 | 0.617785 | -0.002274 |

Formal state：`VALID_NEGATIVE_RESULT`。

## Secondary Historical Source Evidence

PR #69 policy Artifact：

```text
workflow run: 29649382555
artifact id: 8431003217
digest: sha256:4327c92f5e90255cc41d7b5afdca7efc094d7aacc0bf4084e1249b8a3c1183ee
candidate count: 2
downloads: 0
existing Silver replacement: false
formal stake: 0
```

PR #70 metadata census Artifact：

```text
workflow run: 29649555363
artifact id: 8431049131
digest: sha256:4ee249a9cb873365424a1bda55b9e295ae9d52834c18d50020da71fccd573e55
formal state: METADATA_READY_DOWNLOAD_NOT_AUTHORIZED
metadata-ready candidates: 2
full-qualified candidates: 0
downloads: 0
```

PR #71 policy Artifact：

```text
workflow run: 29650340574
artifact id: 8431271984
digest: sha256:f97dfcee7a3beae2e049d50a17837101b4bd3ba870028749ec23be0162125fda
formal state: INPUT_FILE_REQUIRED
database opened: false
raw rows: 0
```

PR #72 synthetic runner Artifact：

```text
workflow run: 29651474770
artifact id: 8431589455
digest: sha256:7b11a7847b1085e3ee4f3f9ed69c803321efbc1d9c058671035d58ee1938019b
synthetic tables: 4
SQLite integrity_check: ok
opened read-only: true
input modified: false
raw rows emitted: 0
cross-source audit executed: false
qualification evaluated: false
```

## Wyatt Real-file Gates

```text
accepted extensions: .sqlite / .sqlite3 / .db
size: 1 MiB to 2 GiB
SQLite header required
read-only open required
integrity_check = ok
2023-24 reference games >= 1,000
game identity match >= 98%
final score match >= 98%
team boxscore coverage >= 98%
player boxscore coverage >= 95%
PBP game coverage >= 95% when claimed
exact duplicate games = 0
fuzzy matching = false
```

真實檔案只可暫時處理；Repository 與 Artifact 不得保存完整 SQLite 或原始 rows。

## Reopening Conditions

Wyatt file-level audit 可在以下條件成立時開始：

```text
1. the user supplies the Wyatt SQLite file;
2. the file extension and size satisfy PR #71;
3. provenance identifies it as the Wyatt Walsh Kaggle dataset;
4. the runner records filename, size, SHA-256 and read-only integrity evidence.
```

市場資料研究只在以下條件之一成立時重新開啟：

```text
1. a materially new lawful no-cost source appears;
2. an existing candidate publishes explicit rights, bookmaker and timestamp semantics;
3. the user supplies a file plus an explicit rights/provenance statement.
```

## Important Recent PRs

```text
#52 Expanded Participation Census
#53 / #54 Expected Minutes Audit v3
#55 / #56 Injury Holdout v1
#60 Frozen Timestamped Odds Pilot Manifest v1
#63 Paid Pilot Approval Packet
#65 Paid Pilot Rejection
#66 / #67 No-cost Odds Source Qualification and Census
#69 Historical Secondary Source Qualification v1
#70 Historical Secondary Source Metadata Census v1
#71 Wyatt SQLite File-level Pilot v1 predeclaration
#72 Wyatt SQLite Census Runner v1 implementation
```
