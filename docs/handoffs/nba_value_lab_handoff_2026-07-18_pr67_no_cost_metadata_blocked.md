# NBA Value Lab Handoff — PR #67 No-cost Metadata Blocked

更新日期：2026-07-18  
定位：**Research Candidate / Pre-Market-Backtest**  
正式 Stake：**0**

## Current Control Block

### Latest Git Commit / Main SHA

此交接建立時的最新已驗證 `main`：

```text
4006ffdd01e57b6bf8bdd2e14e11bb1e2672c6e3
```

最新已合併研究里程碑：

```text
PR #65 — PAID_PILOT_NOT_APPROVED
PR #66 — No-cost Timestamped Odds Source Qualification v1 predeclaration
```

### Currently open PRs

| PR | 狀態 | 用途 |
|---|---|---|
| #67 — No-cost Timestamped Odds Metadata Census v1 | Draft / validated negative result | 審查 8 個固定候選的授權、原始來源、bookmaker 與 timestamp 語意。 |

### Next unique mainline

```text
驗證並合併 PR #67
→ PAUSE_MARKET_DATA_LINE_UNTIL_MATERIALLY_NEW_LAWFUL_SOURCE_OR_USER_FILE
```

這不是降低標準後繼續抓資料。只有出現實質新來源或使用者提供合法資料檔時，才可依 PR #66 的相同 Gate 重新開啟。

### Known blockers

- 使用者已明確不核准付費 Historical Odds pilot。
- 8 個固定的免費、既有或潛在候選中，通過 metadata Gate 的來源為 0。
- 尚無來源同時具備明確權利、bookmaker identity、同書兩側 h2h prices、scheduled tipoff 與可靠 `observed_at`／snapshot timestamp。
- Production Backfill、PIT Odds Join、Market Backtest、CLV、EV、ROI、Drawdown 均未解鎖。
- Historical model 仍明顯輸給 Closing Market。

### Do Not Do

- 不重新開啟付費路徑，除非使用者未來另行明確改變決定。
- 不建立帳號、訂閱、付款、讀取 API key 或呼叫付費端點。
- 不繞過登入、robots、付款、流量限制或 access control。
- 不自動抓取 OddsPortal 或其他禁止自動化收集的來源。
- 不把 Kaggle uploader 的 CC0 標籤當成原始來源權利已釐清。
- 不把單一 game-level odds row、Opening／Closing label、provider first-seen 或 retrieval time 冒充 point-in-time `observed_at`。
- 不使用 fuzzy game、team、bookmaker 或 snapshot matching。
- 不用 future snapshot 補較早缺失 snapshot。
- 不混用不同 bookmaker 或不同 source snapshot 的兩側價格。
- 不降低固定 30 場、180 slots、coverage、PIT、identity、price 或 overround Gates。
- Closing-only benchmark 不得當 executable market backtest。
- 未完成合格 PIT odds join 前，不宣稱 CLV、EV、ROI、Drawdown 或 betting edge。
- 正式 Stake 維持 0。

## Formal Decision Trail

### PR #65 — Paid path rejected

```text
formal state: PAID_PILOT_NOT_APPROVED
paid access authorized: false
account / subscription authorized: false
paid execution authorized: false
production backfill authorized: false
formal stake: 0
```

### PR #66 — No-cost source policy frozen

```text
merge SHA: 4006ffdd01e57b6bf8bdd2e14e11bb1e2672c6e3
workflow run: 29647265151
artifact: no-cost-timestamped-odds-source-qualification-v1-policy
artifact id: 8430404837
digest: sha256:837945ddc7dde002e683391d1980a54c8e8c8e8466c38ac1381b68652ffac98b
checks: 42 / 42
candidate count: 8
quote downloads: 0
paid calls: 0
API keys read: 0
market metrics: false
formal stake: 0
```

PR #66 沿用既有固定樣本與 Gate：

```text
30 games
10 games per season
2021-22 / 2022-23 / 2023-24
T-6h / T-3h / T-1h / T-30m / T-5m / Closing
180 snapshot slots
```

Coverage 與 PIT 門檻未降低。

## PR #67 — Metadata Census Result

正式狀態：

```text
NO_COST_METADATA_BLOCKED
```

Latest validated Artifact：

```text
workflow run: 29647433614
artifact: no-cost-timestamped-odds-metadata-census-v1
artifact id: 8430453513
digest: sha256:37c4df2d4be62267c1f7bcd4b3b87d769be950a5c4abbe84f7387f32306ed111
checks: 20 / 20
candidate count: 8
qualified candidate count: 0
quote downloads: 0
paid calls: 0
API keys read: 0
market metrics: false
formal stake: 0
```

## Frozen Candidate Outcomes

| Candidate | 結論 | 允許用途 |
|---|---|---|
| Christopher Treasure NBA Odds | Reliable `observed_at` 與 bookmaker-level snapshot history 未建立 | Closing benchmark only |
| Evan Hallmark historical betting data | License unknown；描述與原始來源 provenance 不足 | Metadata reference only |
| Eric Qiu odds and scores | CC0 label，但原始來源未具名，bookmaker／timestamp 語意不清楚 | Manual metadata/schema research only |
| cviaxmiwnptr NBA betting data | 單一 game-level odds；無 bookmaker key、`observed_at` 或多時間點 snapshots | Single-row cross-check only |
| SportsbookReviewOnline legacy archive | Direct archive URLs 404 | Legacy provenance note only |
| OddsPortal | 自動化被專案 registry／Terms boundary 禁止 | Manual spot checks only |
| Public GitHub collectors | 找到 collector code，但沒有權利清楚的可重用歷史 quote asset | Code-pattern research only |
| User-supplied timestamped odds | 未提供檔案與 rights statement | None |

## Research State Preserved

Expected Minutes Audit v3：

```text
formal state: ACCURACY_PASS
MAE: 5.120902
RMSE: 6.693908
Median AE: 4.093886
Absolute bias: 0.668968
Starter MAE: 4.663676
Bench MAE: 5.792521
10+ history MAE: 5.092724
```

Injury Feature Holdout v1：

```text
formal state: VALID_NEGATIVE_RESULT
combined baseline Log Loss: 0.615511
combined candidate Log Loss: 0.617785
combined gain: -0.002274
market path: frozen baseline-only
```

Closing Market benchmark：

```text
model Log Loss: 0.6421
closing Log Loss: 0.6167
model Brier: 0.2250
closing Brier: 0.2139
model accuracy: 63.62%
closing accuracy: 66.37%
```

正式結論仍為：模型輸給 Closing Market，沒有 betting-edge 證據。

## Reopening Conditions

Market-data line 只有在以下任一條件成立時才可重啟：

```text
1. 出現實質新的合法零成本來源；
2. 既有候選公布明確的 rights、bookmaker 與 timestamp semantics；
3. 使用者提供資料檔及明確 rights / provenance statement。
```

重啟後仍必須使用 PR #66 的固定樣本與 Gate；不得因 coverage 不足更換比賽、降低門檻或改寫負結果。
