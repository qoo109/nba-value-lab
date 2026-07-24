# NBA Value Lab Handoff — The Odds API Free Forward Review v1

更新日期：2026-07-24  
Formal Stake：0

## Repository state before milestone

```text
main: d8b7d9fc0cf46cd9b04dd8cf91338dca46b4fa1b
latest merged PR: 169
open PRs before branch creation: none
```

## Preserved user decisions

```text
HoopsAPI runtime path: DEFERRED_BY_USER_NO_EXECUTION
BloomBet schema probe: DEFERRED_BY_USER_NO_EXECUTION
paid historical odds path: NOT APPROVED
free/legal sources only: required
provider requests executed before milestone: 0
```

## Milestone

```text
PR #170 — Review The Odds API free forward candidate v1
THE_ODDS_API_FREE_FORWARD_PUBLIC_REVIEW_AND_SYNTHETIC_ADAPTER_VALID
```

Created:

- official public plan/schema/Terms review;
- provider-specific source record;
- synthetic-only adapter shell for v4-shaped NBA h2h events;
- fail-closed contract tests;
- aggregate-only Actions QA;
- current status v12.

## Public review result

```text
free current odds: 500 credits/month
historical odds on free plan: false
NBA sport key: basketball_nba
bookmaker identity: publicly documented
bookmaker last_update: publicly documented
provider snapshot timestamp: not publicly established
standalone raw-data redistribution: prohibited
API key privacy: required
```

Decision:

```text
PROMISING_ZERO_COST_FORWARD_CANDIDATE_REQUIRES_USER_TERMS_REVIEW_AND_CAPPED_RUNTIME_PREFLIGHT
```

## Dedicated validation and Artifact QA

```text
workflow run: 30064853297
job: 89393705197 / success
artifact: 8585859838
artifact digest: sha256:2da201ee26d0883949b47358d0d2c90683ef89a2a923f30f63009a09ba10e69a
artifact formal state: THE_ODDS_API_FREE_FORWARD_PUBLIC_REVIEW_AND_SYNTHETIC_ADAPTER_VALID
contract tests: 29 / 29 PASS
artifact inspected: true
```

Aggregate-only QA confirms:

```text
public review only: true
zero-cost forward candidate: true
historical backfill eligible: false
synthetic adapter only: true
public schema has bookmaker last_update: true
runtime provider timestamp semantics verified: false
provider requests executed: 0
real quotes retained: 0
public quote rows emitted: 0
formal history write authorized: false
market metrics executed: false
Formal Stake: 0
```

## No execution claims

```text
account created: false
API key connected: false
provider requests executed: 0
real quotes retained: 0
runtime timestamp semantics verified: false
point-in-time qualified: false
real 2026-27 T-60 input qualified: false
formal history write authorized: false
Market Backtest: false
Formal Stake: 0
```

## Proposed capped preflight

```text
request id: THE-ODDS-API-FREE-FORWARD-PREFLIGHT-2026-07-24-001
maximum requests: 2
execution enabled: false
```

Prerequisites:

1. User personally reviews and accepts provider Terms.
2. User confirms the free account does not create paid/card obligations.
3. User creates the account and privately stores the API Key.
4. User separately approves the exact request id.
5. The NBA 2026-27 market must actually exist before the one odds request.

## Do not do

- Do not paste the API Key into chat, repo, issue, log or Artifact.
- Do not call the paid Historical API.
- Do not infer provider snapshot time from collector receipt time.
- Do not publish team IDs, prices, raw response or quote rows.
- Do not move production collection/history storage into NBA Value Lab; use `qoo109/nba-odds-history-hub` after qualification.
- Do not run G1.2.0, Market Backtest, CLV, EV, ROI or Drawdown.
- Do not raise Stake above 0.

## Next unique mainline

```text
AWAIT_USER_TERMS_REVIEW_AND_CAPPED_THE_ODDS_API_FREE_FORWARD_PREFLIGHT_APPROVAL
```
