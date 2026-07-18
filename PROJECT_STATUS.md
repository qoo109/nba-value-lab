# NBA Value Lab — Project Status

更新日期：2026-07-18  
定位：**Research Candidate / Pre-Market-Backtest**  
正式 Stake：**0**

最新 `main`、已合併 PR、Actions 與 Artifact QA 是正式 Source of Truth。

## Current Control Block

### Latest Main SHA at this snapshot

```text
29b3063c663544ccb4561c7dcd013ada0388abce
```

### Open PR

| PR | 狀態 | 用途 |
|---|---|---|
| #65 — Record Paid Pilot Rejection and Freeze Paid Path | Draft / governance only | 記錄使用者不核准付費方案並切換至免費來源研究。 |

### Formal user decision

```text
PAID_PILOT_NOT_APPROVED
```

適用範圍：原先凍結的 30 場、180 個請求時間點、最高 1,800 credits 的來源資格測試。

正式後果：

```text
paid access authorized: false
account or subscription authorized: false
paid execution authorized: false
production backfill authorized: false
market backtest unlocked: false
CLV / EV / ROI / Drawdown unlocked: false
betting-edge claim authorized: false
formal stake: 0
```

### Next unique mainline

```text
合併 PR #65
→ QUALIFY_NO_COST_OR_EXISTING_TIMESTAMPED_ODDS_SOURCES
```

只允許研究合法、免費、既有或使用者提供的資料來源。

### Known blockers

- 使用者已明確不核准目前的付費歷史賠率方案。
- 尚無合格的免費 bookmaker-level point-in-time quotes。
- Production Backfill、PIT Odds Join、Market Backtest、CLV、EV、ROI、Drawdown 均未解鎖。
- Historical model 仍明顯輸給 Closing Market。

### Do Not Do

- 不重新開啟付費路徑，除非使用者未來另行明確改變決定。
- 不建立帳號、訂閱、付款或呼叫付費歷史端點。
- 不繞過登入、付款、流量限制或 access control。
- 不對禁止自動化收集的來源進行抓取。
- 不使用 fuzzy game、team、bookmaker、player 或 snapshot matching。
- 不把 T-6h、first-seen 或 Closing 冒充 true Opening。
- 不用 future snapshot 補較早缺失 snapshot。
- 不混用不同 bookmaker 或不同 provider snapshot 的兩側價格。
- Closing-only benchmark 不得當 executable market backtest。
- 不降低 PIT、identity、coverage 或 QA gates。
- 未完成合格 PIT odds join 前，不宣稱 CLV、EV、ROI、Drawdown 或 betting edge。
- 正式 Stake 維持 0。

## Canonical Roadmap

```text
1. Historical Gold and baseline model                       Completed
2. Official injury data and feature-ready matchups          Completed
3. Expected Minutes Accuracy Audit                          ACCURACY_PASS
4. Injury Feature Walk-forward Holdout                      VALID_NEGATIVE_RESULT
5. Real Timestamped Odds Acquisition                        Paid path rejected / free-source research only
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
| Expected Minutes Audit v3 | **ACCURACY_PASS** | 預先宣告 gates 全部通過。 |
| Injury Feature Holdout v1 | **VALID_NEGATIVE_RESULT** | Candidate 未達 promotion gates。 |
| Injury candidate | Rejected | 後續只使用 frozen baseline-only path。 |
| Exact Pilot Manifest v1 | Completed | PR #60；30 games、180 exact timestamps。 |
| Paid Pilot Approval Packet v1 | Historical proposal only | PR #63；23／23 checks，未執行付費請求。 |
| User paid-pilot decision | **NOT APPROVED** | PR #65 記錄並鎖定決定。 |
| No-cost source qualification | Next research step | 尚未有來源通過。 |
| Market Backtest | Blocked | 尚無 executable PIT odds join。 |
| Betting Decision Layer | Blocked | Stake = 0。 |

## Historical Model Evidence

```text
Walk-forward OOF games: 3,688
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

## Preserved Research Evidence

### Expected Minutes Audit v3

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

### Injury Feature Holdout v1

| Population | Baseline LL | Candidate LL | Gain |
|---|---:|---:|---:|
| Feb development — 65 | 0.657411 | 0.667960 | -0.010549 |
| Mar-Apr final — 104 | 0.589324 | 0.586426 | +0.002898 |
| Combined — 169 | 0.615511 | 0.617785 | -0.002274 |

Formal state: `VALID_NEGATIVE_RESULT`。

### Frozen Timestamped Odds Manifest

```text
30 exact games
180 exact request timestamps
Opening labels: 0
paid provider calls: 0
real quotes: 0
market metrics: false
```

### Paid Proposal Packet

```text
formal state before user decision: APPROVAL_PACKET_VALID_AWAITING_USER_APPROVAL
checks: 23 / 23
failures: 0
```

PR #65 的 `PAID_PILOT_NOT_APPROVED` 決定取代等待狀態，但不刪除或改寫既有研究證據。

## No-cost Source Qualification Requirements

候選來源必須具備：

```text
historical game identity
bookmaker identity
same-book two-sided h2h prices
scheduled tipoff
provider snapshot timestamp
bookmaker update or observed timestamp
stable source identifier
retrieval provenance and content hash
clear Terms and redistribution boundary
```

最低 Snapshot 需求仍為：

```text
T-6h / T-3h / T-1h / T-30m / T-5m / Closing
```

Opening 不屬於 v1，也不得推定。缺少可稽核 timestamp、bookmaker identity、同書兩側價格或合法使用邊界的來源，一律淘汰，不降低 Gate。

## Next Exact Task

```text
Merge PR #65
→ build a no-cost source qualification matrix from the existing source registry
→ verify availability, Terms, timestamp semantics, bookmaker identity and historical coverage
→ reject sources that cannot provide auditable PIT two-sided h2h quotes
→ keep Market Backtest locked until one source passes every gate
```

## Important Recent PRs

```text
#52 Expanded Participation Census
#53 / #54 Expected Minutes Audit v3
#55 / #56 Injury Holdout v1
#57 Timestamped Odds Acquisition Policy v1
#59 Timestamped Odds Adapter v1
#60 Frozen Timestamped Odds Pilot Manifest v1
#61 duplicate manifest PR — closed
#62 PR #60 governance handoff sync
#63 Timestamped Odds Paid Pilot Approval v1
#64 Reconcile Status at Paid Approval Gate
#65 Record Paid Pilot Rejection and Freeze Paid Path — Draft
```
