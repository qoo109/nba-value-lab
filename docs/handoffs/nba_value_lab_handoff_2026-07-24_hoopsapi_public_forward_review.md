# NBA Value Lab Handoff — HoopsAPI Public Forward Review

Date: 2026-07-24  
Formal Stake: `0`

## Project

Repository: `qoo109/nba-value-lab`  
Website: `https://qoo109.github.io/nba-value-lab/`

## Completed

- Preserved the user's decision to defer the BloomBet schema probe without execution.
- Reviewed HoopsAPI's official public site, documentation surface, pricing and Terms of Service.
- Confirmed the public free-tier claim of 10 requests per day, no card, all competitions/providers, and current moneyline, handicap and totals.
- Confirmed that public example fields include game ID, teams, scheduled start time, provider objects and same-provider two-sided moneyline.
- Confirmed that the public example does not provide quote-level observation or provider-update timestamps.
- Confirmed that full odds history and snapshots are paid Data-plan features, not free-tier features.
- Confirmed that raw odds resale, redistribution and sublicensing are prohibited by the public Terms.
- Did not create an account, connect a key, call an API, retain quotes or run market metrics.

## Formal states

```text
HoopsAPI review: HOOPSAPI_FREE_PUBLIC_REVIEW_FORWARD_ONLY_CANDIDATE
historical backfill: NOT QUALIFIED
existing frozen-Gold point-in-time join: NOT QUALIFIED
private forward collection: STRUCTURALLY PROMISING / NOT AUTHORIZED
provider requests executed: 0
market backtest: BLOCKED
formal Stake: 0
```

## Next unique mainline

```text
DESIGN_SOURCE_AGNOSTIC_PRIVATE_FORWARD_ODDS_COLLECTOR_V1
```

This is a provider-neutral design task. It requires no account or key and must not execute network requests. It should define the adapter boundary, collector-owned timestamps, private storage contract, fail-closed validation and later provider plug-in interface.

## Do Not Do

- Do not reactivate or execute the deferred BloomBet probe.
- Do not create a HoopsAPI account or accept its terms for the user.
- Do not connect API keys or execute provider requests.
- Do not infer provider timestamps from refresh-frequency marketing claims.
- Do not treat collector `fetched_at` as a provider-origin timestamp.
- Do not publish raw quote rows.
- Do not unlock market backtesting, CLV, EV, ROI, drawdown or betting claims.
- Do not raise Stake above 0.
