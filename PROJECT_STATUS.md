# NBA Value Lab — Project Status

狀態核對日期：2026-07-21  
研究定位：**Research Candidate / Pre-Market-Backtest**  
正式 Stake：**0**

最新 `main`、已合併 PR、GitHub Actions 與 Artifact QA 是正式 Source of Truth。若文件快照 SHA 與即時 Repository head 不同，以即時 `main` 為準。

## Current Control Block

```text
latest Eoin monitor merge: 8e52036f4bd7bc5f89fb4af3e2ea7187d6dcaf5f
formal Eoin execution result: ONE_TIME_FULL_ADAPTER_AGGREGATE_VALIDATION_PASS
formal Eoin source role: ROLE_LIMITED_SECONDARY_QA_SOURCE_VALIDATED
integration policy: EOIN_SECONDARY_QA_INTEGRATION_POLICY_READY_FOR_IMPLEMENTATION
contract monitor: EOIN_SECONDARY_QA_CONTRACT_HEALTHY
integration mode: alert_only_evidence_contract_monitor
source data integration active: false
request consumed: true
repeat execution allowed: false
formal stake: 0
```

### Currently open research execution PRs

```text
None
```

### Next unique mainline

```text
PAUSE_EOIN_EXPANSION_UNTIL_NEW_INDEPENDENT_PLAYER_REFERENCE_OR_NEW_APPROVAL
```

Eoin 已完成目前核准範圍內的 census、cross-source audit、一次性 aggregate validation、role review、integration policy 與 alert-only contract monitor。現階段不再擴充 Eoin 資料線。

只有以下條件之一成立才重新開啟：

1. 出現 independent player-stat parity reference；
2. 需要更新超過 freshness deadline 的 evidence contract；
3. 使用者對新的 bundle execution request 給予明確核准；
4. 出現 materially new lawful source 或新 supplied file。

## Latest Completed Research Work

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
PR #83 — Approved Eoin manual-dispatch status sync
Commit 587112d — Eoin one-time execution result and consumed-request status recorded
PR #96 — Reconciled post-execution PROJECT_STATUS
PR #97 — Eoin post-execution role review policy v1
PR #98 — Eoin role review policy status and registry sync
PR #100 — Eoin post-execution role review evaluation v1
PR #101 — Eoin secondary QA validation result sync
PR #102 — Eoin secondary QA integration policy v1
PR #103 — Eoin secondary QA contract monitor v1
```

## Eoin Evidence Chain

### 1. Cross-source Audit

```text
formal outcome: ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE
workflow run: 29672984966
artifact id: 8437932113
artifact digest: sha256:96a87c6b52614ea6f7478e1bdbcc729c7c8eb2347490ca236475444ca5fcc63a
reference games: 1,230
matched games: 1,230
game identity match: 100%
final score match: 99.9187%
team boxscore coverage: 100%
player candidate coverage: 100% coverage-only
PBP game coverage: 100%
```

### 2. One-time Full Adapter Aggregate Validation

```text
formal state: ONE_TIME_FULL_ADAPTER_AGGREGATE_VALIDATION_PASS
workflow run: 29680729672
artifact id: 8440485189
artifact digest: sha256:e068940df05bfc51d8757aef500e9c6f812687bfa171b5fff8680ee3b59bb56c
request id: EOIN-FULL-ADAPTER-2026-07-19-001
execution count: 1
request consumed: true
all research gates passed: true
games: 1,383
duplicate game_id groups: 0
raw rows emitted: 0
raw files emitted: false
```

### 3. Post-execution Role Review Policy

```text
formal state: EOIN_POST_EXECUTION_ROLE_REVIEW_POLICY_READY
workflow run: 29794965150
artifact id: 8481660306
artifact digest: sha256:1b309073ae19c23483225b1264ea982ef1f6d71f1d482cd124ad63fc0bfd77d0
checks: 24 / 24
checks failed: 0
```

### 4. Post-execution Role Review Evaluation

```text
formal outcome: ROLE_LIMITED_SECONDARY_QA_SOURCE_VALIDATED
workflow run: 29795498102
artifact id: 8481840798
artifact digest: sha256:f64248d5a3eaab52aa6a24fc36980144c5c962a31b91a4057834af1d36e42fd1
failed scientific gates: 0
all scientific gates passed: true
```

Validated scope is limited to:

- deterministic game identity QA；
- final score QA；
- team boxscore coverage／score QA；
- player boxscore candidate coverage-only；
- PBP game coverage QA；
- cross-source regression detection。

Player statistics remain coverage-only and do not establish independent player-stat parity.

### 5. Secondary QA Integration Policy

```text
formal state: EOIN_SECONDARY_QA_INTEGRATION_POLICY_READY_FOR_IMPLEMENTATION
workflow run: 29795934068
artifact id: 8481986433
artifact digest: sha256:ea9e3306c397ee2e150eb091d57171f8c17748e756984d89d288b8b5cc5b5638
checks: 26 / 26
checks failed: 0
integration active: false
alert only: true
```

The policy pins the reviewed evidence, enforces version／Artifact identity, defines a 365-day review window, and fail-closes on role drift, Artifact drift, stale evidence, missing evidence, or forbidden permission activation.

### 6. Secondary QA Contract Monitor

```text
formal state: EOIN_SECONDARY_QA_CONTRACT_HEALTHY
workflow run: 29796165352
artifact id: 8482057613
artifact digest: sha256:813e78b4ff070641f85c5b49a6e46eb3c65c324bb9d25c9b6491b57e694ff0e8
alerts: 0
blocking failures: 0
all contract checks passed: true
evidence review due: 2027-07-21
evidence stale: false
integration active for alerts only: true
source data integration active: false
```

The monitor checks `PROJECT_STATUS.md`, `data/source-registry.json`, pinned evidence identity, request consumption, role consistency, forbidden permissions, approved QA domains and evidence freshness.

## Eoin Runtime Boundary

```text
network calls by role evaluator / policy / monitor: false
external Artifact downloads by monitor: false
new bundle execution by monitor: false
raw Eoin rows read by monitor: false
raw rows emitted: 0
raw files emitted: false
derived tables emitted: false
data or model mutation: false
primary source use: false
Historical Silver replacement: false
Historical Gold replacement: false
player-stat parity: false
player feature import: false
model retraining: false
market backtest: false
CLV / EV / ROI / Drawdown: false
betting decision activation: false
betting edge claim: false
repeat full-bundle execution: false
formal stake: 0
```

## Current Research Position

### Historical Model

- Historical Gold：Completed，5,824 matchup rows，strict PIT violations 0。
- Logistic + Elo Walk-forward v2：Completed，3,688 OOF；機率品質小幅優於 Elo。
- Closing Market Benchmark：模型明顯輸給 Closing Market。
- Expected Minutes Audit v3：`ACCURACY_PASS`。
- Injury Feature Holdout v1：`VALID_NEGATIVE_RESULT`；保留 baseline-only path。

### Eoin A Moore

正式角色：

```text
ROLE_LIMITED_SECONDARY_QA_SOURCE_VALIDATED
```

這不是 primary source，也不是 Historical Silver／Gold replacement。它只可作受限的 deterministic QA、cross-source validation 與 alert-only regression detection。

### Wyatt Walsh SQLite

正式結果仍是 `STRUCTURAL_BLOCKED`。實際檔案只有 16 tables、最晚 game date 為 2023-06-12、2023-24 pilot games 為 0，且沒有 player game boxscore candidate table。

### Market Data

```text
PAUSE_MARKET_DATA_LINE_UNTIL_MATERIALLY_NEW_LAWFUL_SOURCE_OR_USER_FILE
```

使用者未核准付費 Historical Odds pilot。8 個零成本／既有 odds candidates 中，合格 bookmaker-level point-in-time source 仍為 0。

## Known Blockers

- Eoin player boxscore 仍是 coverage-only，沒有 independent player-stat parity reference。
- Eoin 一次性 request 已使用，不能重複執行同一 request ID。
- Eoin evidence review due date 為 2027-07-21；逾期後 monitor 必須回傳 alert-disabled，不能自動重跑來源。
- Wyatt 真實檔案為 `STRUCTURAL_BLOCKED`。
- 真實 bookmaker-level point-in-time odds source 合格數仍為 0。
- Production Odds Backfill、PIT Odds Join、Market Backtest、CLV、EV、ROI、Drawdown 全部未解鎖。
- Historical model 仍明顯輸給 Closing Market。

## Do Not Do

- 不重複執行 `EOIN-FULL-ADAPTER-2026-07-19-001`。
- 不以 main push、schedule 或 concurrent job 執行完整 Eoin bundle。
- 不公開或 commit Kaggle archive、完整第三方資料庫、原始 PBP、球員列或大量來源資料。
- 不把 raw CSV、Parquet、SQLite、DuckDB 或 source archive 上傳成 Artifact。
- 不以 fuzzy matching 連接 game、team、player 或 PBP。
- 不把 `ROLE_LIMITED_SECONDARY_QA_SOURCE_VALIDATED` 解讀成 primary source 或 production data source。
- 不把 Eoin coverage pass 寫成 independent player-stat parity。
- 不替換目前已驗證的 `shufinskiy/nba_data` Historical Silver／Gold 主路徑。
- 不將 Eoin player coverage-only 結果用作 player model feature import。
- 不把 contract monitor 的 healthy state 當作模型 promotion 或資料匯入授權。
- 不把 Wyatt integrity pass 寫成 source qualification pass。
- 不重新開啟付費 odds 路徑，除非使用者未來另行明確改變決定。
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
6. Historical Secondary Source Metadata Review              Completed
7. Wyatt SQLite read-only census runner                     Completed / synthetic only
8. Wyatt real-file schema and cross-source audit             STRUCTURAL_BLOCKED
9. Eoin census and cross-source audit                        Completed / role-limited
10. Eoin one-time full-bundle aggregate validation          PASS / REQUEST CONSUMED
11. Eoin post-execution role review                         ROLE_LIMITED_SECONDARY_QA_SOURCE_VALIDATED
12. Eoin secondary QA integration policy                    READY_FOR_IMPLEMENTATION
13. Eoin secondary QA contract monitor                      EOIN_SECONDARY_QA_CONTRACT_HEALTHY
14. Eoin source-data expansion                              PAUSED
15. Point-in-time Odds Join and Market Backtest             Blocked
16. CLV / EV / ROI / Drawdown                               Blocked
17. Betting Decision Layer                                  Blocked
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
| Eoin Aggregate Validation | **PASS / REQUEST CONSUMED** | 1,383 games；all frozen aggregate gates passed；raw output 0。 |
| Eoin Role Review | **ROLE_LIMITED_SECONDARY_QA_SOURCE_VALIDATED** | Secondary QA only；player coverage-only。 |
| Eoin Integration Policy | **READY_FOR_IMPLEMENTATION** | 26 / 26 checks；alert-only，source integration inactive。 |
| Eoin Contract Monitor | **HEALTHY** | 0 alerts；0 blockers；review due 2027-07-21。 |
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

## Important Files

- `PROJECT_STATUS.md`：正式專案狀態與唯一 Roadmap。
- `README.md`：專案入口與研究定位。
- `data/source-registry.json`：來源角色、證據、workflow／Artifact 與執行邊界。
- `data/eoin-secondary-qa-integration-policy-v1.json`：alert-only integration policy。
- `scripts/validate_eoin_secondary_qa_integration_policy_v1.py`：policy／evidence contract validator。
- `data/eoin-secondary-qa-contract-monitor-v1.json`：contract monitor manifest。
- `scripts/run_eoin_secondary_qa_contract_monitor_v1.py`：contract monitor。
- `.github/workflows/run-eoin-secondary-qa-contract-monitor-v1.yml`：monitor workflow。

## Explicit Next Step

目前 Eoin 線沒有新的自動擴充工作。維持 contract monitor，並將研究資源轉回尚未解鎖的核心阻塞：

```text
1. materially new lawful point-in-time odds source；或
2. 使用者提供 timestamped odds file 加 rights / provenance；或
3. independent player-stat parity reference。
```

在上述條件未成立前，不新增 Eoin bundle execution、模型整合或市場回測工作。
