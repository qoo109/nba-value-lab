# NBA Value Lab — Project Status

更新日期：2026-07-19  
定位：**Research Candidate / Pre-Market-Backtest**  
正式 Stake：**0**

最新 `main`、已合併 PR、GitHub Actions 與 Artifact QA 是正式 Source of Truth。

## Current Control Block

### Latest feature SHA before this status snapshot

```text
b29f9213c52ac641b9365decc67d202d716a826b
```

### 最新完成

```text
PR #69 — Historical Secondary Source Qualification v1 predeclaration
PR #70 — Historical Secondary Source Metadata Census v1
PR #71 — Wyatt SQLite File-level Pilot v1 predeclaration
PR #72 — Wyatt SQLite Census Runner v1 implementation
PR #74 — Wyatt SQLite operational size ceiling amendment to 3 GiB
PR #75 — Wyatt SQLite Aggregate Audit v1
PR #77 — Eoin preflight Artifact validation documentation
PR #78 — Eoin full adapter execution policy v1
PR #79 — Disabled Eoin full adapter runner guardrails v1
PR #80 — One-time Eoin full adapter execution request v1
PR #81 — Eoin request status and source-registry sync
PR #82 — Explicit approval record and manual one-time execution workflow
```

### Currently open research execution PRs

```text
None
```

### Next unique mainline

```text
ONE_TIME_EXECUTION_APPROVAL_VALID_READY_FOR_MANUAL_DISPATCH
```

Request ID：

```text
EOIN-FULL-ADAPTER-2026-07-19-001
```

目前正式控制狀態：

```text
approval granted: true
manual dispatch ready: true
execution workflow: Run approved Eoin full adapter once v1
full bundle execution count: 0
network download performed: false
raw Eoin rows read: false
raw rows emitted: 0
raw files emitted: false
Historical Silver replacement: false
Historical Gold replacement: false
model retraining: false
market backtest: false
formal stake: 0
```

使用者已在 2026-07-19 明確核准上述 request ID。核准只涵蓋一次、手動 `workflow_dispatch`、aggregate-only 的 Eoin full-adapter validation。

尚未執行真實完整 bundle。下一步是手動執行：

```text
GitHub
→ Actions
→ Run approved Eoin full adapter once v1
→ Run workflow
→ Branch: main
→ request_id: EOIN-FULL-ADAPTER-2026-07-19-001
```

不能只看 workflow 綠勾；執行後必須下載並檢查 Artifact。

## Current Research Position

使用者提供的真實 Wyatt Walsh `nba.sqlite` 已通過 SQLite header、唯讀開啟與 `integrity_check = ok`，但實際內容只有 16 tables、最晚到 2023-06-12、2023-24 pilot games 為 0，與上傳 metadata 所描述的 235-table current-season warehouse 不一致。

Eoin A Moore Kaggle 檔案組已完成 census、internal qualification 與 2023-24 deterministic cross-source audit。正式結果為 `ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE`；可作 game identity、final score、team boxscore、player candidate coverage 與 PBP coverage cross-check。Player 結果仍是 coverage-only，不等於 independent player-stat parity。

Eoin role-limited adapter self-test、full adapter preflight、separate execution policy、disabled runner guardrails、one-time execution request 與 explicit approval record 都已建立並通過 aggregate-only CI。

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

### 5. One-time Execution Request

```text
request id: EOIN-FULL-ADAPTER-2026-07-19-001
formal state: ONE_TIME_EXECUTION_REQUEST_VALID_AWAITING_EXPLICIT_USER_APPROVAL
workflow run: 29679511515
artifact id: 8440091393
artifact digest: sha256:a1c4a76c3d09f38a40121bbdc71c93ddeb8d6076482b649acab105eef2c52a61
checks: 19 / 19
```

### 6. Explicit Approval and Executor Self-test

```text
formal state: ONE_TIME_EXECUTION_APPROVAL_VALID_READY_FOR_MANUAL_DISPATCH
executor self-test: ONE_TIME_EXECUTION_EXECUTOR_SELF_TEST_PASS
workflow run: 29680234472
artifact id: 8440335771
artifact digest: sha256:06b850edbad49ac55136ead2572b117743da4b0521d98ae2786fa6bbaaedbeeb
approval checks failed: 0
ready for repeat execution: false
formal stake: 0
```

### Frozen operational limits

```text
runtime ceiling: 45 minutes
concurrency: 1
required files: Games.csv / TeamStatistics.csv / PlayerStatistics.csv / PlayByPlay.parquet
maximum input file count: 4
maximum total input size: 10 GiB
maximum single input file size: 8 GiB
maximum public output size: 10 MiB
manual workflow_dispatch only
public Artifact: one aggregate JSON report
```

## Known Blockers

- Wyatt real-file audit 正式結果為 `STRUCTURAL_BLOCKED`。
- Wyatt 檔案只有 16 tables，不是 metadata 所描述的 235-table warehouse。
- Wyatt `game` 最晚日期為 2023-06-12；2023-24 pilot games = 0。
- Wyatt supplied schema 沒有 player game boxscore candidate table。
- Wyatt `game` 有 56 個 duplicate `game_id` groups。
- Wyatt `play_by_play` 有 7,360 個 duplicate `(game_id, eventnum)` groups。
- Eoin player boxscore 仍只通過 coverage-only；尚無獨立 player-stat parity reference。
- Eoin one-time full-bundle aggregate validation 尚未手動 dispatch，執行次數仍為 0。
- 使用者未核准付費 Historical Odds pilot。
- 8 個零成本／既有 odds candidates 中，合格 point-in-time source 為 0。
- Production Odds Backfill、PIT Odds Join、Market Backtest、CLV、EV、ROI、Drawdown 全部未解鎖。
- Historical model 仍明顯輸給 Closing Market。

## Do Not Do

- 不把 Wyatt synthetic self-test 或 integrity pass 寫成 source qualification pass。
- 不把 Eoin `ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE` 寫成完整 player-stat parity、model promotion 或 Silver／Gold replacement。
- 不以 main push、schedule 或 concurrent job 執行完整 Eoin bundle。
- 不使用錯誤 request ID 或非 `main` ref 執行。
- 不重複執行已消耗的一次性 approval；執行後必須先記錄結果並標記 consumed。
- 不公開或 commit 完整第三方 SQLite、Kaggle archive、原始 PBP、球員列或大量來源資料。
- 不把 raw CSV、Parquet、SQLite、DuckDB 或 source archive 上傳成 Artifact。
- 不以 fuzzy matching 連接 game、team、player 或 PBP。
- 不替換目前已驗證的 `shufinskiy/nba_data` Silver／Gold 主路徑。
- 不降低既有 coverage、identity、score、duplicate、integrity 或 resource gates。
- 不將 Eoin player coverage-only 結果用作 player model feature import。
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
15. Eoin one-time execution request                          APPROVED_READY_FOR_MANUAL_DISPATCH
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
| Paid Pilot Decision | **NOT APPROVED** | 付費、key 與 paid execution 均未授權。 |
| No-cost Odds Metadata Census | **NO_COST_METADATA_BLOCKED** | 8 candidates；qualified 0。 |
| Wyatt SQLite Real-file Audit | **STRUCTURAL_BLOCKED** | 16 tables、latest 2023-06-12、2023-24 games 0。 |
| Eoin Cross-source Audit v1 | **ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE** | 1,230 / 1,230 matched；score 99.9187%；PBP 100%。 |
| Eoin Full Adapter Preflight v1 | **READY_BUT_DISABLED** | Aggregate-only preflight passed。 |
| Eoin Execution Policy v1 | **READY_FOR_IMPLEMENTATION_BUT_DISABLED** | Separate policy passed。 |
| Eoin Runner Implementation v1 | **READY_FOR_APPROVAL_BUT_DISABLED** | Runner blocks before data access。 |
| Eoin One-time Request v1 | **APPROVED_READY_FOR_MANUAL_DISPATCH** | Explicit approval valid；true execution count remains 0。 |
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

限制：player boxscore 結果只代表 candidate row coverage，不代表 player stat parity；此結果不解鎖 model metrics、market metrics、CLV、EV、ROI、Drawdown 或投注決策。

## After the Approved Run

執行後只接受以下兩種完成狀態：

```text
ONE_TIME_FULL_ADAPTER_AGGREGATE_VALIDATION_PASS
ONE_TIME_FULL_ADAPTER_AGGREGATE_VALIDATION_RESEARCH_BLOCKED
```

必須記錄：workflow run ID、Artifact ID、digest、formal state、每個 frozen gate、raw output boundary，以及 request consumed 狀態。未完成這些記錄前，不得進行第二次執行或任何資料升格。
