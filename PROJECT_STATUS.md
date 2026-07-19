# NBA Value Lab — Project Status

更新日期：2026-07-19
定位：**Research Candidate / Pre-Market-Backtest**  
正式 Stake：**0**

最新 `main`、已合併 PR、Actions 與 Artifact QA 是正式 Source of Truth。

## Current Control Block

### Latest Main SHA at this snapshot

```text
9ba38738ef26c8040897dd06d683da2bbb285a9d
```

最新完成：

```text
PR #69 — Historical Secondary Source Qualification v1 predeclaration
PR #70 — Historical Secondary Source Metadata Census v1
PR #71 — Wyatt SQLite File-level Pilot v1 predeclaration
PR #72 — Wyatt SQLite Census Runner v1 implementation
PR #74 — Wyatt SQLite operational size ceiling amendment to 3 GiB
PR #75 — Wyatt SQLite Aggregate Audit v1
Commit ce88b24 — Eoin data source automation
Commit 2654873 — Eoin cross-source audit workflow
Commit bf9db74 — Eoin cross-source audit result recorded
Commit 9ba3873 — Eoin role-limited adapter predeclaration
```

### Currently open research execution PRs

```text
None
```

### Next unique mainline

```text
EOIN_ROLE_LIMITED_ADAPTER_SELF_TEST_READY_FOR_CI_VALIDATION
```

使用者已提供真實 Wyatt Walsh `nba.sqlite`。檔案通過 SQLite header、唯讀開啟與 `integrity_check = ok`，但實際內容只有 16 tables、最晚到 2023-06-12、2023-24 pilot games 為 0，與上傳 metadata 所描述的 235-table current-season warehouse 不一致。

使用者也提供 Eoin A Moore Kaggle 檔案組，並已在 GitHub Actions 完成 census、internal qualification 與 2023-24 cross-source audit。Eoin 正式結果為 `ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE`，可做 game identity、final score、team boxscore 與 PBP coverage cross-check；player boxscore 目前只通過 coverage-only，不等於 player stat parity。

Eoin adapter predeclaration v1 已建立。此政策只授權後續實作 role-limited adapter self-test，不授權 adapter execution、raw row artifact、Silver／Gold replacement、model retraining 或 market backtest。

Eoin role-limited adapter v1 self-test implementation 已建立。本機 synthetic fixture self-test 通過；GitHub Actions 將跑含 Parquet fixture 的 CI self-test。完整 Eoin bundle execution 仍關閉。

### Parallel blocked line

```text
PAUSE_MARKET_DATA_LINE_UNTIL_MATERIALLY_NEW_LAWFUL_SOURCE_OR_USER_FILE
```

市場資料線仍暫停；使用者已不核准付費 Historical Odds pilot。

## Known blockers

- Wyatt 真實 SQLite 已完成 aggregate-only audit，正式結果為 `STRUCTURAL_BLOCKED`。
- 真實檔案只有 16 tables，並非 metadata 所描述的 235-table warehouse。
- `game` 最晚日期為 2023-06-12；2023-24 pilot games = 0，因此凍結的 1,000-game cross-source audit 無法執行。
- supplied schema 沒有 player game boxscore candidate table。
- `game` 有 56 個 duplicate `game_id` groups。
- `play_by_play` 有 7,360 個 duplicate `(game_id, eventnum)` groups。
- Wyatt 的完整次要來源合格數仍為 0。
- Eoin A Moore 已通過 role-limited secondary-source audit，但不是 Historical Silver／Gold replacement。
- Eoin adapter v1 目前只有 synthetic-fixture self-test；尚未允許 full Eoin bundle execution 或資料匯入。
- Eoin player boxscore 只通過 coverage-only；尚未有獨立 player-stat parity reference。
- 使用者已明確不核准付費 Historical Odds pilot。
- 8 個零成本／既有 odds 候選中，合格 bookmaker-level point-in-time source 為 0。
- Production Odds Backfill、PIT Odds Join、Market Backtest、CLV、EV、ROI、Drawdown 全部未解鎖。
- Historical model 仍明顯輸給 Closing Market。

## Do Not Do

- 不把 PR #72 synthetic SQLite self-test 或 PR #75 integrity pass 寫成 Wyatt source qualification pass。
- 不把 Eoin `ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE` 寫成完整 player stat parity、model promotion 或 Silver／Gold replacement。
- 不在 Eoin adapter self-test 中讀完整 Eoin bundle、輸出 derived tables 或執行 Silver／Gold replacement。
- 不公開或 commit 完整第三方 SQLite、原始 PBP、球員列或大量來源資料。
- 不以 fuzzy matching 連接 game、team、player 或 PBP。
- 不替換目前已驗證的 `shufinskiy/nba_data` Silver／Gold 主路徑。
- 不降低 PR #71 固定的 coverage、identity、score、duplicate 或 integrity gates。
- 不把 metadata 的 235-table 描述套用到實際只有 16 tables 的檔案。
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
8. Wyatt real file schema and 2023-24 cross-source audit     STRUCTURAL_BLOCKED
9. Eoin census, internal qualification, cross-source audit   ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE
10. Eoin adapter predeclaration                             Completed / implementation-ready
11. Eoin adapter self-test implementation                   Completed / CI validation pending
12. Eoin full adapter execution preflight                   Next after CI pass
13. Point-in-time Odds Join and Market Backtest              Blocked
14. CLV / EV / ROI / Drawdown                               Blocked
15. Betting Decision Layer                                  Blocked
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
| Wyatt SQLite Pilot Policy | Completed | PR #71；real-file gates 已凍結。 |
| Wyatt SQLite Census Runner | Completed / synthetic only | PR #72；唯讀 runner 已驗證。 |
| Wyatt SQLite Size Amendment | Completed | PR #74；operation ceiling 3 GiB，scientific gates 未改。 |
| Wyatt SQLite Real-file Audit | **STRUCTURAL_BLOCKED** | PR #75；16 tables、latest 2023-06-12、2023-24 games 0。 |
| Eoin Cross-source Audit v1 | **ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE** | Run 29672984966；1,230 / 1,230 games matched；score match 99.9187%；PBP coverage 100%。 |
| Eoin Adapter Predeclaration v1 | **ROLE_LIMITED_ADAPTER_READY_FOR_IMPLEMENTATION** | Policy-only；禁止 raw rows、Silver/Gold replacement、model retraining 與 market metrics。 |
| Eoin Role-limited Adapter v1 | **SELF_TEST_IMPLEMENTED** | Synthetic fixture only；full Eoin bundle execution disabled；CI validates Parquet fixture path。 |
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

## Eoin Cross-source Evidence

GitHub Actions aggregate-only audit：

```text
workflow run: 29672984966
workflow URL: https://github.com/qoo109/nba-value-lab/actions/runs/29672984966
commit SHA: 2654873d9e823a1e392da55b4b08f0c702abf799
artifact id: 8437932113
digest: sha256:96a87c6b52614ea6f7478e1bdbcc729c7c8eb2347490ca236475444ca5fcc63a
formal outcome: ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE
all core gates passed: true
raw rows in Artifact: 0
raw files in Artifact: false
formal stake: 0
```

2023-24 deterministic comparison against `shufinskiy/nba_data`：

```text
reference games: 1,230
matched games: 1,230
game identity match rate: 100%
final score match rate: 99.9187% (1,229 / 1,230)
team boxscore coverage: 100%
team boxscore score match rate: 99.9187%
player boxscore candidate coverage: 100% coverage-only
PBP game coverage: 100%
Eoin pilot games: 1,383
extra Eoin pilot games: 153
Eoin PBP rows: 18,727,295
Eoin PBP unique games: 39,164
```

限制：

```text
shufinskiy reference 是 event-level source，不是完整獨立 player boxscore stat reference。
player boxscore 結果只代表 candidate row coverage，不代表 player stat parity。
此結果不解鎖 model metrics、market metrics、CLV、EV、ROI、Drawdown 或投注決策。
```

## Wyatt Real-file Evidence

PR #74 policy amendment：

```text
archive: nba.sqlite.zip
archive size: 434,150,473 bytes
SQLite member size: 2,349,588,480 bytes
operational maximum: 3,221,225,472 bytes
scientific gates changed: false
```

PR #75 aggregate audit：

```text
workflow run: 29657039708
artifact id: 8433179663
digest: sha256:875a24b0c24cb8f9e62ee85b89d7c415bb563669e4f56169d948d33b963bde9c
checks: 27 / 27
formal state: STRUCTURAL_BLOCKED
SQLite integrity_check: ok
actual tables: 16
metadata-described tables: 235
total table rows: 14,060,690
actual latest game date: 2023-06-12
2023-24 pilot games: 0
PBP rows: 13,592,899
duplicate game_id groups: 56
duplicate PBP event-key groups: 7,360
player game boxscore candidate: none
raw rows in Artifact: 0
secondary source qualified: false
```

## Wyatt Real-file Gates

```text
accepted extensions: .sqlite / .sqlite3 / .db
size: 1 MiB to 3 GiB
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

Wyatt file-level audit 只在以下條件成立時重新開啟：

```text
1. a supplied SQLite or DuckDB bundle actually contains the advertised current schema;
2. the actual file includes 2023-24 games and a player game boxscore table;
3. provenance ties the file to the published dataset version;
4. filename, size, SHA-256, read-only integrity, schema and date coverage are revalidated;
5. all original identity, score, coverage and duplicate gates remain unchanged.
```

目前這份 16-table legacy file 可保留為 1946–2022-23 exploratory cross-check candidate，但不得升格為正式次要來源。

Eoin 下一步只可開啟 adapter predeclaration：

```text
1. define role-limited Eoin adapter scope;
2. map deterministic game/team/PBP identifiers only;
3. keep player-stat parity out of scope until an independent boxscore reference exists;
4. keep existing Silver and Gold unchanged;
5. emit only aggregate validation reports and small derived schema metadata.
```

Eoin adapter predeclaration v1 已完成後，adapter self-test implementation 已建立：

```text
1. synthetic-fixture adapter self-test implemented;
2. local self-test reads only temporary fixture rows;
3. CI self-test validates Parquet fixture metadata path;
4. aggregate adapter report only;
5. raw Eoin files, Silver, Gold, model and market lines remain unchanged.
```

Eoin 下一步只可開啟 full adapter execution preflight，且必須先等 GitHub CI 通過：

```text
1. inspect CI artifact from Validate Eoin role-limited adapter v1;
2. keep full Eoin bundle execution disabled until a separate preflight policy;
3. preserve raw-row and raw-file artifact ban;
4. preserve player-stat parity block;
5. preserve Stake 0.
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
#74 Wyatt SQLite operational size ceiling amendment
#75 Wyatt SQLite Aggregate Audit v1
ce88b24 Eoin data source automation
2654873 Eoin cross-source audit workflow
bf9db74 Eoin cross-source audit result recorded
9ba3873 Eoin role-limited adapter predeclaration
```
