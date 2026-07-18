# NBA Value Lab — Project Status

更新日期：2026-07-18  
定位：**Research Candidate / Pre-Market-Backtest**  
正式 Stake：**0**

最新 `main`、已合併 PR、Actions 與 Artifact QA 是正式 Source of Truth。

## Current Control Block

### Latest Main SHA at this snapshot

```text
5dfbe3318f2cf214f035e65806ae1c467cdefad8
```

最新完成：

```text
PR #65 — PAID_PILOT_NOT_APPROVED
PR #66 — No-cost Timestamped Odds Source Qualification v1 predeclaration
PR #67 — No-cost Timestamped Odds Metadata Census v1
```

### Currently open PRs

```text
No research execution PR.
```

### Next unique mainline

```text
PAUSE_MARKET_DATA_LINE_UNTIL_MATERIALLY_NEW_LAWFUL_SOURCE_OR_USER_FILE
```

不得重跑同一批候選，除非來源頁面、授權、schema 或可用資料有實質改變。

### Known blockers

- 使用者已明確不核准付費 Historical Odds pilot。
- 8 個零成本／既有候選中，合格 bookmaker-level point-in-time source 為 0。
- 尚無可稽核的同一 bookmaker、同一 snapshot、兩側 h2h prices 與可靠 `observed_at`。
- Production Backfill、PIT Odds Join、Market Backtest、CLV、EV、ROI、Drawdown 全部未解鎖。
- Historical model 仍明顯輸給 Closing Market。

### Do Not Do

- 不重新開啟付費路徑，除非使用者未來另行明確改變決定。
- 不建立帳號、訂閱、付款或呼叫付費歷史端點。
- 不繞過登入、付款、robots、流量限制或 access control。
- 不自動抓取 OddsPortal 或其他禁止自動化收集的來源。
- 不把 Kaggle uploader 的 CC0 標籤當成原始來源權利已釐清。
- 不把單一 game-level odds row、Opening／Closing label、first-seen 或 retrieval time 當成可靠 point-in-time snapshot。
- 不使用 fuzzy game、team、bookmaker 或 snapshot matching。
- 不用 future snapshot 補較早缺失 snapshot。
- 不混用不同 bookmaker 或不同 source snapshot 的兩側價格。
- 不降低固定 30-game sample、180 slots、coverage、PIT、identity、price 或 overround gates。
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
6. Point-in-time Odds Join and Market Backtest              Blocked
7. CLV / EV / ROI / Drawdown                                Blocked
8. Betting Decision Layer                                   Blocked
```

## Core Status

| Module | Status | Formal conclusion |
|---|---|---|
| Historical Gold | Completed | 5,824 matchup rows；strict PIT violations 0。 |
| Logistic + Elo Walk-forward v2 | Completed | 3,688 OOF；機率品質小幅優於 Elo。 |
| Closing Market Benchmark | Model lost | 模型明顯輸給 Closing Market。 |
| Expected Minutes Audit v3 | **ACCURACY_PASS** | 預先宣告的結構、樣本與數值 gates 全部通過。 |
| Injury Feature Holdout v1 | **VALID_NEGATIVE_RESULT** | Candidate 未達 promotion gates；後續使用 frozen baseline-only path。 |
| Frozen Odds Pilot Manifest | Completed / no-price | 30 games、180 exact timestamps、Opening labels 0。 |
| Paid Pilot Decision | **NOT APPROVED** | PR #65；付費、key 與 paid execution 均未授權。 |
| No-cost Source Policy | Completed | PR #66；42／42 checks；8 candidates frozen；0 quote downloads。 |
| No-cost Metadata Census | **NO_COST_METADATA_BLOCKED** | PR #67；20／20 checks；qualified candidates 0。 |
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

## No-cost Odds Evidence

PR #66 policy Artifact：

```text
workflow run: 29647265151
artifact id: 8430404837
digest: sha256:837945ddc7dde002e683391d1980a54c8e8c8e8466c38ac1381b68652ffac98b
checks: 42 / 42
candidates frozen: 8
quote downloads: 0
paid calls: 0
API keys read: 0
market metrics: false
formal stake: 0
```

PR #67 latest-head metadata census Artifact：

```text
workflow run: 29647570309
artifact id: 8430488984
digest: sha256:804bf265144a6324c67d8f130b48d8d33df2d99fd86c15cf54430ebec27bcd0e
checks: 20 / 20
formal state: NO_COST_METADATA_BLOCKED
candidate count: 8
qualified candidate count: 0
quote downloads: 0
paid calls: 0
API keys read: 0
market metrics: false
formal stake: 0
```

Latest-head regression：

```text
20 / 20 workflows successful
```

Candidate boundaries：

| Candidate | Formal boundary |
|---|---|
| Christopher Treasure | Closing benchmark only；reliable `observed_at` not established。 |
| Evan Hallmark | License unknown；provenance absent。 |
| Eric Qiu | CC0 label；original sources unnamed；bookmaker/timestamp unclear。 |
| cviaxmiwnptr | Single-row game odds；no bookmaker key or observed_at snapshots。 |
| SportsbookReviewOnline | Direct archive URLs 404。 |
| OddsPortal | Manual-only；automation prohibited。 |
| Public GitHub collectors | Code only；no reusable licensed quote asset found。 |
| User-supplied | File and rights statement not provided。 |

## Reopening Condition

Market-data research may reopen only when at least one of the following is true：

```text
1. a materially new lawful no-cost source appears;
2. an existing candidate publishes explicit rights, bookmaker and timestamp semantics;
3. the user supplies a file plus an explicit rights/provenance statement.
```

任何新候選仍必須使用 PR #66 的固定 30 場、180 slots 與原始 source-health gates。

## Important Recent PRs

```text
#52 Expanded Participation Census
#53 / #54 Expected Minutes Audit v3
#55 / #56 Injury Holdout v1
#57 Timestamped Odds Acquisition Policy v1
#59 Timestamped Odds Adapter v1
#60 Frozen Timestamped Odds Pilot Manifest v1
#63 Paid Pilot Approval Packet
#64 Paid Approval Gate Reconciliation
#65 Paid Pilot Rejection
#66 No-cost Source Qualification Predeclaration
#67 No-cost Metadata Census — merged
```
