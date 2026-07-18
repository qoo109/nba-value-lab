# NBA Value Lab — Project Status

更新日期：2026-07-18  
定位：**Research Candidate / Pre-Market-Backtest**  
正式 Stake：**0**

最新 `main`、合併 PR、Actions 與 Artifact QA 是正式 Source of Truth；舊 handoff 與聊天紀錄只保留歷史脈絡。

## Current Control Block

### Latest Main SHA at this status snapshot

```text
70640f33f71f256433b7c36d256b2b99af441711
```

最新完成里程碑：

```text
PR #60 — Frozen Timestamped Odds Pilot Manifest v1
PR #63 — Timestamped Odds Paid Pilot Approval v1
PR #62 — PR #60 governance handoff sync（晚於 #63 合併，但未納入 #63，已由本狀態校正）
```

### Open PRs

```text
No research execution PR.
Current status/handoff reconciliation is documentation only.
```

### Next unique mainline

```text
WAIT_FOR_EXPLICIT_USER_APPROVAL
```

完整順序：

```text
等待使用者明確核准目前列價 US$30／月的 START 20K 方案
→ 承認每月續訂直到取消，以及可能另有未驗證的稅金／匯率／刷卡費
→ 最多授權 frozen 30-game qualification pilot 使用 1,800 API credits
→ 使用者在自動化之外完成帳號與訂閱
→ 只用 private GitHub Actions secret 連接 THE_ODDS_API_KEY
→ 再次確認方案／價格／quota／取消狀態
→ 才可另開 paid qualification execution PR
```

### Known blockers

- 尚未取得使用者對付費與最高 1,800 credits 的明確核准。
- 尚未確認／建立 Historical Odds paid subscription。
- `THE_ODDS_API_KEY` 尚未以 private secret 連接。
- 真實 bookmaker-level `observed_at` quotes 尚未取得。
- Production backfill 尚未獲授權，也尚未完成 rights review 與第二次 cost approval。
- Point-in-time Odds Join、Market Backtest、CLV、EV、ROI、Drawdown 尚未解鎖。
- Historical model 仍明顯輸給 Closing Market。

### Do Not Do

- 不自動建立帳號、訂閱、付款、購買 credits、取消或管理續訂。
- 未獲明確核准前，不呼叫 Historical paid endpoint。
- API key 不得寫入聊天、commit、log、Artifact、錯誤訊息或下載檔。
- 不繞過 401、403、429、登入、付款或 access control。
- 不替換 frozen 失敗比賽或手挑日期補 coverage。
- 不把 T-6h、T-24h 或 provider first-seen 冒充 true Opening。
- 不用 future snapshot 補較早缺失 snapshot。
- 不混用不同 bookmaker 或不同 provider snapshot 的兩側價格。
- Qualification pilot 不計算 edge、EV、ROI、CLV、Drawdown、bet count 或 profit ranking。
- Primary bookmaker 只按 coverage 與固定 key 排序，不按模型結果或價格選擇。
- Public repo／Artifact 不保留 raw odds JSON、quote-level rows、價格或可下載 odds archive。
- 已拒絕的 injury candidate 不得回到市場模型；只使用 frozen baseline-only path。
- 不重做 odds schema、bookmaker schema、no-vig boundary 或 source registry。
- Closing-only benchmark 不得當 executable market backtest。
- 未完成 PIT odds join 前，不宣稱 CLV、EV、ROI、Drawdown 或 betting edge。
- CI 綠燈只代表執行成功，必須讀 Artifact QA。
- 正式 Stake 維持 0。

## Canonical Roadmap

```text
1. Historical Gold and baseline model                       Completed
2. Official injury data and feature-ready matchups          Completed
3. Expected Minutes Accuracy Audit                          ACCURACY_PASS
4. Injury Feature Walk-forward Holdout                      VALID_NEGATIVE_RESULT
5. Real Timestamped Odds Acquisition                        Explicit paid-approval gate
6. Point-in-time Odds Join and Market Backtest              Blocked
7. CLV / EV / ROI / Drawdown                                Blocked
8. Betting Decision Layer                                   Blocked
```

## Core Status

| Module | Status | Formal conclusion |
|---|---|---|
| Historical Gold | Completed | 5,824 matchup rows；strict PIT violations 0。 |
| Logistic + Elo Walk-forward v2 | Completed | 3,688 OOF；Log Loss／Brier 小幅且跨 Fold 優於 Elo。 |
| Calibration Gate | Completed | Platt／Isotonic 未穩定改善，保留 Raw。 |
| Closing Market Benchmark | Model lost | 模型明顯輸給 Closing Market。 |
| Market Residual v1 | Negative Result | 100% Closing Market、0% model residual。 |
| Rest／Travel v1 | Negative Result | Untouched holdout 未通過。 |
| Expected Minutes Audit v3 | **ACCURACY_PASS** | 所有預先宣告的結構、樣本與數值 gates 通過。 |
| Injury Feature Holdout v1 | **VALID_NEGATIVE_RESULT** | 結構通過；candidate 未達跨 Fold promotion gates。 |
| Injury candidate | Rejected | 市場研究只使用 frozen baseline-only path。 |
| Timestamped Odds Policy v1 | Completed | PR #57 鎖定 source、no-spend、quota、snapshots 與 storage contract。 |
| Timestamped Odds Adapter v1 | Completed／offline | PR #59；112／112 checks；`ACCESS_NOT_PROVIDED`。 |
| Exact Pilot Manifest v1 | **Completed** | PR #60；30 games、180 requests、exact 1,800-credit ceiling。 |
| Paid Pilot Approval Packet v1 | **Completed／Awaiting approval** | PR #63；23／23 checks；沒有帳號、付款、key 或 paid call。 |
| Paid qualification pilot | Blocked | 需要使用者核准、paid access 與 private secret。 |
| Production Backfill | Blocked | 需要 qualification pass、rights review 與另一次 cost approval。 |
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

## Expected Minutes Audit v3

```text
PR #53 — predeclaration
PR #54 — execution
Formal state: ACCURACY_PASS
```

```text
MAE: 5.120902 <= 6.5
RMSE: 6.693908 <= 9.0
Median AE: 4.093886 <= 5.5
Absolute bias: 0.668968 <= 2.0
Starter MAE: 4.663676 <= 6.5
Bench MAE: 5.792521 <= 7.5
10+ history MAE: 5.092724 <= 6.25
```

此結果只驗證 prior-only Expected Minutes proxy，不證明 injury feature 或投注價值。

## Injury Feature Holdout v1

```text
PR #55 — predeclaration
PR #56 — execution
Formal state: VALID_NEGATIVE_RESULT
Market path: frozen baseline-only
```

| Population | Baseline LL | Candidate LL | Gain |
|---|---:|---:|---:|
| Feb development — 65 | 0.657411 | 0.667960 | -0.010549 |
| Mar-Apr final — 104 | 0.589324 | 0.586426 | +0.002898 |
| Combined — 169 | 0.615511 | 0.617785 | -0.002274 |

Final fold 改善只保留為診斷，不推翻 combined negative decision。

## Timestamped Odds Acquisition Contract

```text
provider: The Odds API Historical v4
sport: basketball_nba
region: us
market: h2h only
odds format: decimal
snapshots: T-6h / T-3h / T-1h / T-30m / T-5m / Closing
Opening: not requested and may not be inferred
secret: THE_ODDS_API_KEY
```

Decision states：

```text
ACCESS_NOT_PROVIDED
SOURCE_QUALIFICATION_BLOCKED
NO_QUALIFIED_BOOKMAKER
QUALIFIED_FOR_PRODUCTION_MANIFEST
```

即使 qualified，也只允許建立 offline production manifest 與新的 cost preflight。

## PR #60 — Exact No-price Pilot Manifest

Latest merged-head evidence：

```text
merge SHA: 332d199122ad61815503d1165c81a696c28dbfee
workflow run: 29639270948
artifact id: 8428103801
digest: sha256:31aa2acafe9834a09720486c96413d8da863f35623de78ef8ef1da8b6432a2a4
formal state: PILOT_MANIFEST_READY_ACCESS_NOT_PROVIDED
```

QA：

```text
Gold matches: 30 / 30
Official season files: 3 / 3
Exact schedule games: 30 / 30
Games per season: 10 / 10 / 10
Game slots: 180
Unique request timestamps: 180
Exact planned quota: 1,800 credits
Opening labels: 0
Raw official JSON retained: 0
Player / score / bookmaker / price fields retained: 0
Paid provider calls: 0
API key read: false
Real quotes: 0
Market metrics: false
```

先前 NBA LiveData per-game schedule 路徑的 30／30 HTTP 403 已保留；未繞過、未替換 frozen games。正式 schedule 使用三份低頻 NBA Official season files。

## PR #63 — Paid Pilot Approval Packet

Official facts revalidated on 2026-07-18：

```text
Historical access: paid plan only
Historical quota: 10 credits × regions × markets
Historical featured markets: from 2020-06-06
Snapshot interval: 10 minutes before Sep 2022; 5 minutes from Sep 2022
Returned snapshot: closest equal to or before requested timestamp
Lowest currently listed historical-enabled plan: START 20K
Base listed price: US$30 / month
Monthly quota: 20,000 credits
Billing: immediate and recurring monthly until cancelled
Frozen pilot maximum: 1,800 credits = 9.0% of quota
```

US$30 是官方列出的基礎方案價，不是已驗證的最終刷卡金額；稅金、匯率與刷卡費可能另計。

Artifact：

```text
merge SHA: 78f09865360b5f4cc1c16a766a9fd803c1e5ae80
workflow run: 29639804815
artifact id: 8428253271
digest: sha256:45d47c9dc12eaf39ebac8c9ac7ed01af7600cc56a1153dd3b628162f4a33486e
formal state: APPROVAL_PACKET_VALID_AWAITING_USER_APPROVAL
checks: 23 / 23
failures: 0
```

Execution boundary：

```text
approval_state: AWAITING_EXPLICIT_USER_APPROVAL
automatic purchase or subscription: false
account / subscription / payment created by automation: false
api_key_read: false
paid_endpoint_calls: 0
real_quotes_downloaded: 0
maximum_pilot_credits: 1,800
ready_for_paid_qualification_execution: false
ready_for_production_backfill: false
ready_for_market_backtest: false
ready_for_clv_ev_roi: false
ready_for_betting_edge_claim: false
formal_stake: 0
```

Terms／Storage boundary：

```text
standalone raw-data resale or redistribution: forbidden
public raw responses / quote-level rows / price rows: forbidden
API key in public files or chat: forbidden
public output: aggregate QA and non-reconstructable research summaries only
production backfill: separate rights review and cost approval required
```

## Required Explicit Approval

任何 paid action 前，使用者必須明確核准：

1. START 20K 目前列出的基礎價格為 US$30／月；
2. 方案立即開始計費，並每月續訂直到取消；
3. 可能另有尚未驗證的稅金、匯率或刷卡費；
4. Frozen 30-game qualification pilot 最多使用 1,800 API credits；
5. 此核准不包含 production backfill、Market Backtest、CLV、EV、ROI、Drawdown 或下注；
6. `THE_ODDS_API_KEY` 只能透過 private secret 連接。

## Next Exact Task

```text
WAIT_FOR_EXPLICIT_USER_APPROVAL
```

收到核准後仍須先重新驗證方案／價格／quota／取消狀態，再由使用者於自動化之外完成訂閱，最後才建立有硬性 1,800-credit ceiling 的 execution PR。

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
```
