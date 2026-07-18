# Timestamped Odds Paid Pilot Approval v1

更新日期：2026-07-18  
正式狀態：`AWAITING_EXPLICIT_USER_APPROVAL`  
正式 Stake：`0`

## 目的

本文件只建立付費來源資格測試的核准邊界。它不建立帳號、不訂閱、不購買、不讀取 API key，也不呼叫 The Odds API Historical paid endpoint。

PR #60 已完成並合併 frozen no-price manifest：

```text
30 independent games
10 games per season: 2021-22 / 2022-23 / 2023-24
6 snapshot slots per game
180 unique historical requests
maximum pilot quota: 1,800 credits
formal state: PILOT_MANIFEST_READY_ACCESS_NOT_PROVIDED
```

## 官方資訊重新確認

查驗日期：2026-07-18。

官方來源：

- Pricing / plans: https://the-odds-api.com/
- Historical data: https://the-odds-api.com/historical-odds-data/
- V4 documentation: https://the-odds-api.com/liveapi/guides/v4/
- Terms: https://the-odds-api.com/terms-and-conditions.html
- Subscription management: https://the-odds-api.com/manage/upgrade-downgrade-cancel-a-subscription.html

查驗結果：

```text
Historical odds access: paid plans only
Historical featured markets: from 2020-06-06
Snapshots before September 2022: 10-minute intervals
Snapshots from September 2022: 5-minute intervals
Returned snapshot: closest equal to or earlier than requested timestamp
Historical quota: 10 credits × regions × markets
Empty historical response: does not count against quota
```

目前最低列出的含 Historical Odds 方案：

```text
Plan: START 20K
Base list price: USD 30 / month
Monthly credits: 20,000
Billing: charged immediately, then recurring monthly until cancelled
```

USD 30 是官方頁面列出的基礎方案價格；稅金、信用卡費、匯率或其他付款費用尚未驗證，不得把 USD 30 描述成最終刷卡金額。

## Exact Maximum Exposure

Frozen pilot 只有：

```text
region = us
market = h2h
historical cost = 10 credits per request
unique requests = 180
maximum pilot credits = 1,800
```

因此：

```text
1,800 / 20,000 = 9.0% of START 20K monthly quota
```

這不是按比例付費。若使用 START 20K，金錢曝險是整個訂閱方案目前列出的基礎月費 USD 30，而不是 1,800 credits 的比例價格。

## Terms / Storage Boundary

The Odds API Terms 禁止把資料重新包裝或作為獨立 raw-data product 轉售、再散布或提供下載。分析工具與 user-facing applications 可在符合條款、且原始資料不是主要商品的前提下使用。

本專案固定：

```text
public raw odds JSON: forbidden
public quote-level rows: forbidden
public price rows: forbidden
API key in commit/log/Artifact/chat: forbidden
standalone odds archive redistribution: forbidden
```

公開 repo／Artifact 只可保存：

- 程式碼、schema、manifest；
- aggregate coverage／source-health／QA；
- 無法重建 raw bookmaker quotes 的研究摘要；
- deidentified error classes。

Production backfill 前仍需另做正式 rights review 與第二次 cost approval。

## Required User Approval

在任何付費行為前，使用者必須明確承認：

1. 目前列出的 START 20K 基礎價格為 USD 30／月；
2. 可能另有尚未驗證的稅金、匯率或刷卡費；
3. 付費會立即開始，且每月自動續訂直到取消；
4. 本次 frozen pilot 最多使用 1,800 credits；
5. 本次核准不包含 production backfill、Market Backtest、CLV、EV、ROI、Drawdown 或下注；
6. `THE_ODDS_API_KEY` 只能以私密 secret 方式連接，不能貼入聊天或公開 repo。

核准文字模板：

```text
I approve the currently listed The Odds API START 20K subscription at a base price of USD 30 per month, acknowledge recurring monthly billing until cancelled and possible unverified taxes/FX/card fees, and authorize the frozen 30-game qualification pilot to use at most 1,800 API credits. This does not authorize production backfill, market metrics or betting execution.
```

## Current Execution State

```text
approval_state: AWAITING_EXPLICIT_USER_APPROVAL
account_created_by_automation: false
subscription_created_by_automation: false
payment_created_by_automation: false
api_key_read: false
paid_endpoint_calls: 0
real_quotes_downloaded: 0
ready_for_paid_qualification_execution: false
ready_for_production_backfill: false
ready_for_market_backtest: false
ready_for_clv_ev_roi: false
ready_for_betting_edge_claim: false
formal_stake: 0
```

收到明確核准後，也不能由自動化工具替使用者建立付款或訂閱；下一步只允許協助安全設定 private secret，並在正式執行前再次驗證方案、quota 與取消狀態。
