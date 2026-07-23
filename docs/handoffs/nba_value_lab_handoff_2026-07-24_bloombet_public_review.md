# NBA Value Lab Handoff — BloomBet Public Review

Date: 2026-07-24  
Formal Stake: `0`

## Project

Repository: `qoo109/nba-value-lab`  
Website: `https://qoo109.github.io/nba-value-lab/`

## Completed

- Reviewed BloomBet official public homepage, API documentation landing page and About page.
- Confirmed only public marketing claims for a USD 0, 500-request-per-month, no-card tier with NBA/NFL, live/historical and 15+ provider coverage.
- Recorded that schema, timestamp semantics, historical coverage, terms and retention rights remain unverified.
- Created a fail-closed maximum-three-request schema-probe design.
- Did not create an account, connect a key, call the API, retain quotes or run market metrics.

## Formal states

```text
public review: BLOOMBET_FREE_API_PUBLIC_REVIEW_BLOCKED
schema probe request: VALID / AWAITING EXPLICIT USER APPROVAL
execution count: 0 / 1
maximum API requests: 3
market backtest: BLOCKED
formal Stake: 0
```

## One unique next prerequisite line

```text
BLOOMBET_FREE_API_ZERO_COST_SCHEMA_PROBE_AWAITING_EXPLICIT_USER_APPROVAL
```

## Required user action

The user must explicitly approve or decline a user-created BloomBet free account, private `BLOOMBET_API_KEY` setup and at most three schema requests. The key must not be pasted into chat.

## Do Not Do

- Do not create an account on the user's behalf.
- Do not accept provider terms on the user's behalf.
- Do not place the API key in repository files, chat, logs or Artifacts.
- Do not exceed three requests.
- Do not retain or publish raw quote-level rows.
- Do not unlock market backtesting, CLV, EV, ROI, drawdown or betting claims.
- Do not raise Stake above 0.
