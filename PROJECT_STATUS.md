# NBA Value Lab — Project Status

狀態核對日期：2026-07-21  
研究定位：**Research Candidate / Pre-Market-Backtest**  
正式 Stake：**0**

最新 `main`、已合併 PR、GitHub Actions 與 Artifact QA 是正式 Source of Truth。若文件快照 SHA 與即時 Repository head 不同，以即時 `main` 為準。

## Current Control Block

```text
latest Eoin evaluation merge: ce0620cb46f5074ee9ab506cd300d5898014dbbf
formal Eoin execution result: ONE_TIME_FULL_ADAPTER_AGGREGATE_VALIDATION_PASS
post-execution policy state: EOIN_POST_EXECUTION_ROLE_REVIEW_POLICY_READY
formal Eoin source role: ROLE_LIMITED_SECONDARY_QA_SOURCE_VALIDATED
request id: EOIN-FULL-ADAPTER-2026-07-19-001
request consumed: true
repeat execution allowed: false
formal stake: 0
```

### Currently open research execution PRs

```text
None
```

### Next unique research step

```text
EOIN_SECONDARY_QA_INTEGRATION_POLICY — NOT_STARTED
```

下一步只能建立 **secondary QA integration policy**，定義 Eoin 如何在不替換任何資料層的前提下執行 deterministic cross-source QA。不得直接接入 Historical Silver、Historical Gold、player feature、模型訓練或市場回測。

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
```

## Eoin One-time Full Adapter Result

真實完整 Eoin bundle 已完成 **一次**、手動 `workflow_dispatch`、aggregate-only validation。該 request 已消耗，不得重複執行。

```text
formal state: ONE_TIME_FULL_ADAPTER_AGGREGATE_VALIDATION_PASS
workflow run: 29680729672
artifact id: 8440485189
artifact digest: sha256:e068940df05bfc51d8757aef500e9c6f812687bfa171b5fff8680ee3b59bb56c
execution count for request: 1
request consumed: true
all research gates passed: true
```

### Aggregate Results

```text
games: 1,383
team boxscore covered games: 1,383
team boxscore coverage rate: 1.000
team boxscore score match rate: 1.000
player boxscore candidate covered games: 1,383
player boxscore candidate coverage rate: 1.000
PBP covered games: 1,383
PBP game coverage rate: 1.000
duplicate game_id groups: 0
raw rows emitted: 0
raw files emitted: false
```

## Eoin Post-execution Role Review Policy

```text
formal state: EOIN_POST_EXECUTION_ROLE_REVIEW_POLICY_READY
workflow run: 29794965150
artifact id: 8481660306
artifact digest: sha256:1b309073ae19c23483225b1264ea982ef1f6d71f1d482cd124ad63fc0bfd77d0
checks: 24 / 24
checks failed: 0
network calls made: false
new bundle execution performed: false
raw Eoin rows read: false
raw rows emitted: 0
raw files emitted: false
formal stake: 0
```

## Eoin Post-execution Role Review Evaluation

PR #100 使用政策 JSON 中已凍結的 aggregate evidence 完成 evaluator。沒有重新下載 Artifact、沒有接觸 Kaggle、沒有執行 Eoin bundle，也沒有讀取 raw Eoin rows。

```text
formal outcome: ROLE_LIMITED_SECONDARY_QA_SOURCE_VALIDATED
workflow run: 29795498102
artifact id: 8481840798
artifact digest: sha256:f64248d5a3eaab52aa6a24fc36980144c5c962a31b91a4057834af1d36e42fd1
previous formal role: ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE
reviewed formal role: ROLE_LIMITED_SECONDARY_QA_SOURCE_VALIDATED
manifest failures: 0
failed scientific gates: 0
all scientific gates passed: true
policy structural validation: pass
```

### Validated QA Scope

Eoin 現在可作以下 **secondary QA／cross-source regression** 用途：

- deterministic game identity QA；
- final score QA；
- team boxscore coverage 與 score QA；
- player boxscore candidate coverage-only；
- PBP game coverage QA；
- cross-source regression detection。

Player statistics 仍是 coverage-only，不構成 independent player-stat parity。

### Evaluation Boundary

```text
network calls made: false
new bundle execution performed: false
external artifacts downloaded: false
raw Eoin rows read: false
raw rows emitted: 0
raw files emitted: false
derived tables emitted: false
primary source use: false
Historical Silver replacement: false
Historical Gold replacement: false
player-stat parity: false
player feature import: false
model retraining: false
market backtest: false
CLV / EV / ROI / Drawdown: false
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

這不是 primary source，也不是 Historical Silver／Gold replacement。它只允許在明確受限的 QA domains 內，使用 deterministic cross-source evidence 做驗證與 regression detection。

### Wyatt Walsh SQLite

正式結果仍是 `STRUCTURAL_BLOCKED`。實際檔案只有 16 tables、最晚 game date 為 2023-06-12、2023-24 pilot games 為 0，且沒有 player game boxscore candidate table。

### Market Data

```text
PAUSE_MARKET_DATA_LINE_UNTIL_MATERIALLY_NEW_LAWFUL_SOURCE_OR_USER_FILE
```

使用者未核准付費 Historical Odds pilot。8 個零成本／既有 odds candidates 中，合格 bookmaker-level point-in-time source 仍為 0。

## Known Blockers

- Eoin secondary QA integration policy 尚未建立；目前尚無正式自動化接入規格。
- Eoin player boxscore 仍是 coverage-only，沒有 independent player-stat parity reference。
- Eoin 一次性 request 已使用，不能重複執行同一 request ID。
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
9. Eoin census and cross-source audit                        ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE
10. Eoin adapter predeclaration                             Completed
11. Eoin adapter self-test                                  Completed
12. Eoin full adapter preflight                             Completed / execution gated
13. Eoin separate execution policy                          Completed
14. Eoin disabled runner guardrails                         Completed
15. Eoin one-time execution request                         Completed / consumed
16. Eoin one-time full-bundle aggregate validation          ONE_TIME_FULL_ADAPTER_AGGREGATE_VALIDATION_PASS
17. Eoin post-execution role review policy                  EOIN_POST_EXECUTION_ROLE_REVIEW_POLICY_READY
18. Eoin post-execution role review evaluation              ROLE_LIMITED_SECONDARY_QA_SOURCE_VALIDATED
19. Eoin secondary QA integration policy                    NOT_STARTED
20. Point-in-time Odds Join and Market Backtest             Blocked
21. CLV / EV / ROI / Drawdown                               Blocked
22. Betting Decision Layer                                  Blocked
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
| Eoin Full Adapter Aggregate Validation | **PASS / REQUEST CONSUMED** | 1,383 games；all frozen aggregate gates passed；raw output 0。 |
| Eoin Post-execution Role Review Policy | **READY** | 24 / 24 checks；no data execution。 |
| Eoin Role Review Evaluation | **ROLE_LIMITED_SECONDARY_QA_SOURCE_VALIDATED** | All frozen scientific gates passed；secondary QA only。 |
| Eoin Player Statistics | **COVERAGE-ONLY** | 不構成 independent player-stat parity。 |
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
- `data/eoin-post-execution-role-review-policy-v1.json`：post-execution review policy。
- `data/eoin-post-execution-role-review-evaluation-v1.json`：evaluation manifest。
- `scripts/evaluate_eoin_post_execution_role_review_v1.py`：aggregate-only evaluator。
- `docs/eoin-post-execution-role-review-evaluation-v1.md`：outcome 與 role boundary。
- `.github/workflows/evaluate-eoin-post-execution-role-review-v1.yml`：evaluation CI。

## Explicit Next Step

建立 `Eoin Secondary QA Integration Policy v1`：

1. 只允許 deterministic QA 與 regression alerts；
2. 不重新下載或執行完整 Eoin bundle；
3. 不建立或替換 Silver／Gold tables；
4. 不匯入 player features；
5. 定義 fail-closed、版本 pinning、evidence freshness 與 alert-only outputs；
6. 所有 QA 結果都不得影響模型、market backtest 或 Stake 0。
