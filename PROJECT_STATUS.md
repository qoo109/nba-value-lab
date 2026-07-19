# NBA Value Lab — Project Status

更新日期：2026-07-19  
定位：**Research Candidate / Pre-Market-Backtest**  
正式 Stake：**0**

最新 `main`、已合併 PR、GitHub Actions 與 Artifact QA 是正式 Source of Truth。

## Current Control Block

### Latest feature SHA before this status snapshot

```text
8bf32e20d40315d508f78ae50e6d919e591abdc7
```

即時 `main` SHA 以 GitHub repository head 為準；本欄記錄此次狀態快照所描述的最後功能 commit。

### 最新完成

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
Commit 2b871e8 — Eoin role-limited adapter self-test
Commit 2c23bb2 — Eoin lightweight adapter CI autorun
Commit 44467db — Eoin full adapter preflight gate
Commit cbdb002 — Eoin preflight website status sync
PR #77 — Eoin preflight Artifact validation documentation
PR #78 — Eoin full adapter execution policy v1
PR #79 — Disabled Eoin full adapter runner guardrails v1
PR #80 — One-time Eoin full adapter execution request v1
```

### Currently open research execution PRs

```text
None
```

### Next unique mainline

```text
ONE_TIME_EXECUTION_REQUEST_VALID_AWAITING_EXPLICIT_USER_APPROVAL
```

Request ID：

```text
EOIN-FULL-ADAPTER-2026-07-19-001
```

目前已完成 request packet 的結構與 Artifact 綁定驗證，但：

```text
approval_granted: false
execution_enabled: false
network calls made: 0
full bundle executions: 0
raw Eoin rows read: false
raw rows emitted: 0
formal stake: 0
```

沒有收到使用者對上述 request ID 的明確核准前，不得執行完整 Eoin bundle。

## Current Research Position

使用者提供的真實 Wyatt Walsh `nba.sqlite` 已通過 SQLite header、唯讀開啟與 `integrity_check = ok`，但實際內容只有 16 tables、最晚到 2023-06-12、2023-24 pilot games 為 0，與上傳 metadata 所描述的 235-table current-season warehouse 不一致。

Eoin A Moore Kaggle 檔案組已完成 census、internal qualification 與 2023-24 deterministic cross-source audit。正式結果為 `ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE`；可以作 game identity、final score、team boxscore、player candidate coverage 與 PBP coverage cross-check。Player 結果仍是 coverage-only，不等於 independent player-stat parity。

Eoin role-limited adapter self-test、full adapter preflight、separate execution policy、disabled runner guardrails 與 one-time execution request packet 都已建立並通過 aggregate-only CI。這些階段都沒有執行完整 bundle，也沒有匯入或公開 raw rows。

市場資料線仍暫停。使用者未核准付費 Historical Odds pilot；目前零成本或既有來源中，合格 bookmaker-level point-in-time odds source 仍為 0。

## Eoin Execution Chain

### 1. Cross-source Audit

```text
formal outcome: ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE
workflow run: 29672984966
artifact id: 8437932113
artifact digest: sha256:96a87c6b52614ea6f7478e1bdbcc729c7c8eb2347490ca236475444ca5fcc63a
```

### 2. Full Adapter Preflight

```text
formal state: FULL_ADAPTER_EXECUTION_PREFLIGHT_READY_BUT_DISABLED
workflow run: 29677698906
artifact id: 8439486695
artifact digest: sha256:39dd80ca107e2dc65f6bbba8012ba8b9ac40b60bd6a44db6f05cacb05a27d311
```

### 3. Separate Execution Policy

```text
formal state: FULL_ADAPTER_EXECUTION_POLICY_READY_FOR_IMPLEMENTATION_BUT_EXECUTION_DISABLED
workflow run: 29677971194
artifact id: 8439578942
artifact digest: sha256:9b81c9ef61f1f9d19453b9e04a8e42cd362700ac86e79a4377328f24fdfe25a2
```

### 4. Disabled Runner Guardrails

```text
formal state: FULL_ADAPTER_RUNNER_READY_FOR_ONE_TIME_EXECUTION_APPROVAL_BUT_DISABLED
workflow run: 29679274470
artifact id: 8440008401
artifact digest: sha256:15032709922439d062108994b08bfec76e815fb42443572c36e7d5db51d10331
blocked before data access: true
```

Frozen operational limits：

```text
runtime ceiling: 45 minutes
concurrency: 1
required files: Games.csv / TeamStatistics.csv / PlayerStatistics.csv / PlayByPlay.parquet
maximum input file count: 4
maximum total input size: 10 GiB
maximum single input file size: 8 GiB
maximum public output size: 10 MiB
maximum public artifact files: 6
```

### 5. One-time Execution Request

```text
request id: EOIN-FULL-ADAPTER-2026-07-19-001
formal state: ONE_TIME_EXECUTION_REQUEST_VALID_AWAITING_EXPLICIT_USER_APPROVAL
workflow run: 29679511515
artifact id: 8440091393
artifact digest: sha256:a1c4a76c3d09f38a40121bbdc71c93ddeb8d6076482b649acab105eef2c52a61
checks: 19 / 19
approval granted: false
execution enabled: false
ready for execution: false
```

## Known Blockers

- Wyatt real-file audit 正式結果為 `STRUCTURAL_BLOCKED`。
- Wyatt 檔案只有 16 tables，不是 metadata 所描述的 235-table warehouse。
- Wyatt `game` 最晚日期為 2023-06-12；2023-24 pilot games = 0。
- Wyatt supplied schema 沒有 player game boxscore candidate table。
- Wyatt `game` 有 56 個 duplicate `game_id` groups。
- Wyatt `play_by_play` 有 7,360 個 duplicate `(game_id, eventnum)` groups。
- Eoin player boxscore 仍只通過 coverage-only；尚無獨立 player-stat parity reference。
- Eoin one-time request 尚未取得使用者明確核准。
- 完整 Eoin bundle execution 尚未發生，執行次數仍為 0。
- 使用者未核准付費 Historical Odds pilot。
- 8 個零成本／既有 odds candidates 中，合格 point-in-time source 為 0。
- Production Odds Backfill、PIT Odds Join、Market Backtest、CLV、EV、ROI、Drawdown 全部未解鎖。
- Historical model 仍明顯輸給 Closing Market。

## Do Not Do

- 不把 Wyatt synthetic self-test 或 integrity pass 寫成 source qualification pass。
- 不把 Eoin `ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE` 寫成完整 player-stat parity、model promotion 或 Silver／Gold replacement。
- 不在沒有明確 approval record 時把 `approval_granted` 或 `execution_enabled` 改成 `true`。
- 不以 main push、schedule 或 concurrent job 執行完整 Eoin bundle。
- 不公開或 commit 完整第三方 SQLite、Kaggle archive、原始 PBP、球員列或大量來源資料。
- 不把 raw CSV、Parquet、SQLite、DuckDB 或 source archive 上傳成 Artifact。
- 不以 fuzzy matching 連接 game、team、player 或 PBP。
- 不替換目前已驗證的 `shufinskiy/nba_data` Silver／Gold 主路徑。
- 不降低既有 coverage、identity、score、duplicate、integrity 或 resource gates。
- 不將 Eoin player coverage-only 結果用作 player model feature import。
- 不重新開啟付費 odds 路徑，除非使用者未來另行明確改變決定。
- 不建立帳號、訂閱、付款或呼叫付費歷史 odds endpoint。
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
8. Wyatt real-file schema and cross-source audit             STRUCTURAL_BLOCKED
9. Eoin census and cross-source audit                        ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE
10. Eoin adapter predeclaration                              Completed
11. Eoin adapter self-test                                   Completed
12. Eoin full adapter preflight                              READY_BUT_DISABLED
13. Eoin separate execution policy                           READY_FOR_IMPLEMENTATION_BUT_DISABLED
14. Eoin disabled runner guardrails                          READY_FOR_APPROVAL_BUT_DISABLED
15. Eoin one-time execution request                          AWAITING_EXPLICIT_USER_APPROVAL
16. Eoin one-time full-bundle aggregate validation           NOT_STARTED
17. Point-in-time Odds Join and Market Backtest              Blocked
18. CLV / EV / ROI / Drawdown                                Blocked
19. Betting Decision Layer                                   Blocked
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
| Historical Secondary Source Policy | Completed | Eoin 與 Wyatt 兩候選、固定 gates。 |
| Wyatt SQLite Real-file Audit | **STRUCTURAL_BLOCKED** | 16 tables、latest 2023-06-12、2023-24 games 0。 |
| Eoin Cross-source Audit v1 | **ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE** | 1,230 / 1,230 matched；score 99.9187%；PBP 100%。 |
| Eoin Role-limited Adapter v1 | **SELF_TEST_IMPLEMENTED** | Synthetic fixture only。 |
| Eoin Full Adapter Preflight v1 | **READY_BUT_DISABLED** | Aggregate-only preflight passed。 |
| Eoin Execution Policy v1 | **READY_FOR_IMPLEMENTATION_BUT_DISABLED** | Separate policy passed；execution remains false。 |
| Eoin Runner Implementation v1 | **READY_FOR_APPROVAL_BUT_DISABLED** | Runner blocks before data access。 |
| Eoin One-time Request v1 | **AWAITING_EXPLICIT_USER_APPROVAL** | 19 / 19 checks；approval false；execution false。 |
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

## Reopening and Approval Conditions

Wyatt audit 只在 supplied bundle 實際包含 current schema、2023-24 games、player game boxscore table 與可驗證 provenance 時重新開啟；既有 gates 不得降低。

Eoin 下一步只在使用者明確核准 request ID `EOIN-FULL-ADAPTER-2026-07-19-001` 後才可設計／建立一次性 approval record。核准前不得執行。核准即使成立，也只授權一次 aggregate-only validation，不授權 raw artifacts、Silver／Gold replacement、player parity、model retraining、market backtest 或非 0 Stake。

市場資料研究只在以下條件之一成立時重新開啟：

```text
1. materially new lawful no-cost source appears;
2. an existing candidate publishes explicit rights, bookmaker and timestamp semantics;
3. the user supplies a timestamped odds file plus rights / provenance statement.
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
#77 Eoin preflight Artifact validation documentation
#78 Eoin full adapter execution policy v1
#79 Disabled Eoin full adapter runner guardrails v1
#80 One-time Eoin full adapter execution request v1
```
