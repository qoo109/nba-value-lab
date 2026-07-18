# NBA Value Lab — Formal Handoff

更新日期：2026-07-18（Asia/Taipei）  
Repository：`qoo109/nba-value-lab`  
定位：**Research Candidate / Pre-Market-Backtest**  
正式 Stake：**0**

> 正式 Source of Truth：GitHub main、合併 PR、Actions、Artifact QA。舊 handoff 與聊天紀錄只保留歷史脈絡。

## Current Control Block

### Latest Main SHA at handoff snapshot

```text
70640f33f71f256433b7c36d256b2b99af441711
```

### Latest merged milestones

```text
PR #60 — Frozen Timestamped Odds Pilot Manifest v1
PR #63 — Timestamped Odds Paid Pilot Approval v1
PR #62 — PR #60 governance sync, merged after #63 but based before #63
```

本 handoff 的目的，是把 PR #63 的正式證據補回最新治理狀態。

### Currently open PRs

```text
No research execution PR.
Only documentation/status reconciliation may be open.
```

### Next unique mainline

```text
WAIT_FOR_EXPLICIT_USER_APPROVAL
```

### Known blockers

- 使用者尚未核准目前列價 US$30／月與最高 1,800 credits。
- Paid historical subscription 尚未由使用者完成。
- `THE_ODDS_API_KEY` 尚未以 private secret 連接。
- 真實 bookmaker-level `observed_at` quotes 尚未取得。
- Production backfill、PIT odds join、Market Backtest、CLV、EV、ROI、Drawdown 全部未解鎖。
- Historical model 仍輸給 Closing Market。

### Do Not Do

- 不自動建立帳號、訂閱、付款或管理續訂。
- 未核准前不呼叫 paid endpoint。
- API key 不得進聊天、commit、log 或 Artifact。
- 不繞過 401／403／429、登入、付款或 access control。
- 不替換 frozen games，不手挑日期補 coverage。
- 不推定 Opening，不以 future snapshot 補過去 snapshot。
- 不混用 bookmaker／snapshot 的兩側價格。
- Qualification pilot 不計算 edge／EV／ROI／CLV／Drawdown／profit ranking。
- Public repo／Artifact 不留 raw odds、quote-level rows 或價格。
- Injury candidate 已拒絕；市場研究只走 frozen baseline-only。
- Stake 維持 0。

## Executive Summary

正式研究狀態：

```text
Expected Minutes Audit v3: ACCURACY_PASS
Injury Feature Holdout v1: VALID_NEGATIVE_RESULT
Injury candidate: rejected
Market model path: frozen baseline only
Exact Odds Manifest: PILOT_MANIFEST_READY_ACCESS_NOT_PROVIDED
Paid Approval Packet: APPROVAL_PACKET_VALID_AWAITING_USER_APPROVAL
```

目前不能宣稱模型有投注優勢，也不能計算或宣稱 executable CLV／EV／ROI／Drawdown。

## Historical Model Evidence

```text
OOF games: 3,688
Logistic + Elo Log Loss: 0.631306
Elo Log Loss: 0.634301
Logistic + Elo Brier: 0.220567
Elo Brier: 0.221949
```

Closing benchmark（1,894 games）：

| Metric | Model | Closing |
|---|---:|---:|
| Log Loss | 0.6421 | **0.6167** |
| Brier | 0.2250 | **0.2139** |
| Accuracy | 63.62% | **66.37%** |

正式結論：模型明顯輸給 Closing Market。

## Expected Minutes Audit v3

```text
PR #53 — policy
PR #54 — execution
Formal state: ACCURACY_PASS
MAE: 5.120902
RMSE: 6.693908
Median AE: 4.093886
Absolute bias: 0.668968
Starter MAE: 4.663676
Bench MAE: 5.792521
10+ history MAE: 5.092724
```

此 pass 只驗證 prior-only Expected Minutes proxy，不證明 injury feature 或市場價值。

## Injury Feature Holdout v1

```text
PR #55 — policy
PR #56 — execution
Formal state: VALID_NEGATIVE_RESULT
```

| Population | Baseline LL | Candidate LL | Gain |
|---|---:|---:|---:|
| Feb development — 65 | 0.657411 | 0.667960 | -0.010549 |
| Mar-Apr final — 104 | 0.589324 | 0.586426 | +0.002898 |
| Combined — 169 | 0.615511 | 0.617785 | -0.002274 |

Candidate 未通過跨 Fold gates，因此拒絕。

## PR #60 — Exact No-price Pilot Manifest

```text
merge SHA: 332d199122ad61815503d1165c81a696c28dbfee
workflow run: 29639270948
artifact id: 8428103801
digest: sha256:31aa2acafe9834a09720486c96413d8da863f35623de78ef8ef1da8b6432a2a4
formal state: PILOT_MANIFEST_READY_ACCESS_NOT_PROVIDED
```

```text
Gold matches: 30 / 30
Official season files: 3 / 3
Exact schedule games: 30 / 30
Game slots: 180
Unique requested timestamps: 180
Exact quota ceiling: 1,800 credits
Opening labels: 0
Paid calls: 0
API key read: false
Real quotes: 0
Market metrics: false
```

先前 per-game NBA LiveData schedule 路徑 30／30 HTTP 403 已保留；沒有繞過或替換樣本。

## PR #63 — Paid Pilot Approval Packet

官方資訊於 2026-07-18 重新確認：

```text
Historical access: paid plan only
Quota: 10 credits × regions × markets
Featured market history: from 2020-06-06
Snapshot interval: 10 minutes before Sep 2022; 5 minutes after
Response snapshot: closest equal to or earlier than requested time
Lowest currently listed historical-enabled plan: START 20K
Base listed price: US$30 / month
Monthly credits: 20,000
Billing: immediate and recurring monthly until cancelled
Frozen pilot: 1,800 credits maximum = 9.0% of quota
```

US$30 是基礎列價，不保證等於最終刷卡金額；稅金、匯率與刷卡費可能另計。

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

No-spend boundary：

```text
account / subscription / payment by automation: false
api_key_read: false
paid_endpoint_calls: 0
real_quotes_downloaded: 0
ready_for_paid_qualification_execution: false
ready_for_market_backtest: false
formal_stake: 0
```

## Required Explicit Approval

任何 paid action 前，使用者必須明確承認：

1. START 20K 目前列出的基礎價格為 US$30／月；
2. 方案立即開始計費，並每月續訂直到取消；
3. 可能另有未驗證的稅金、匯率或刷卡費；
4. Frozen 30-game qualification pilot 最多使用 1,800 credits；
5. 不授權 production backfill、Market Backtest、CLV、EV、ROI、Drawdown 或下注；
6. API key 只能使用 private secret。

## Sequence After Approval

```text
revalidate plan / price / quota / cancellation state
→ user completes account and subscription outside automation
→ connect THE_ODDS_API_KEY as private secret
→ create execution PR with hard 180-request / 1,800-credit ceiling
→ run frozen 30-game source qualification only
→ read aggregate Artifact QA
```

Possible outcomes：

```text
SOURCE_QUALIFICATION_BLOCKED
NO_QUALIFIED_BOOKMAKER
QUALIFIED_FOR_PRODUCTION_MANIFEST
```

即使 qualified，也不能直接執行 production backfill；仍需 rights review、production manifest 與第二次 cost approval。

— Handoff end —
