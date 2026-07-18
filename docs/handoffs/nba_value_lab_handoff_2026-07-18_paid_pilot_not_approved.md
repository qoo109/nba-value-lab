# NBA Value Lab Handoff — Paid Pilot Not Approved

更新日期：2026-07-18  
定位：**Research Candidate / Pre-Market-Backtest**  
正式 Stake：**0**

## Current Control Block

### Latest Main SHA at decision time

```text
29b3063c663544ccb4561c7dcd013ada0388abce
```

### Latest completed milestones

```text
PR #60 — Frozen Timestamped Odds Pilot Manifest v1
PR #63 — Timestamped Odds Paid Pilot Approval v1
PR #64 — Reconciled status and handoff at paid approval gate
```

### User decision

```text
PAID_PILOT_NOT_APPROVED
```

The user explicitly did not approve the currently listed paid Historical Odds path. This decision applies to the frozen 30-game / 180-request / maximum 1,800-credit qualification pilot.

### Formal consequences

```text
paid access authorized: false
account creation authorized: false
subscription or purchase authorized: false
THE_ODDS_API_KEY connection authorized: false
paid endpoint execution authorized: false
production backfill authorized: false
market backtest unlocked: false
CLV / EV / ROI / Drawdown unlocked: false
betting-edge claim authorized: false
formal stake: 0
```

No account, subscription, payment, secret connection, paid API call or real quote download occurred before this decision.

### Next unique mainline

```text
QUALIFY_NO_COST_OR_EXISTING_TIMESTAMPED_ODDS_SOURCES
```

This mainline is research-only. It may assess legal, free, existing or user-supplied sources, but it may not:

- bypass login, 401, 403, 429, paywalls or access controls;
- scrape sources whose terms prohibit automated collection;
- treat closing-only odds as executable point-in-time quotes;
- infer true Opening from T-6h, first-seen or closing data;
- publish raw quote-level provider data without explicit rights;
- unlock Market Backtest, CLV, EV, ROI or edge claims without valid timestamped quotes.

### Known blockers

- No approved paid historical odds source.
- No private `THE_ODDS_API_KEY` connection is authorized.
- No bookmaker-level point-in-time quotes with auditable `observed_at` have been acquired.
- Production Backfill, PIT Odds Join, Market Backtest, CLV, EV, ROI and Drawdown remain blocked.
- Historical model still loses to the Closing Market benchmark.

### Do Not Do

- Do not reopen the paid path without a new explicit user decision.
- Do not create an account, subscription, payment or paid request automatically.
- Do not introduce a paid client or secret-reading workflow while this decision is active.
- Do not lower identity, PIT, coverage or QA gates to accommodate a free source.
- Do not use fuzzy game, team, bookmaker or snapshot matching.
- Do not replace frozen failures with hand-selected games.
- Do not claim a betting edge; Stake remains 0.

## Preserved evidence

### Frozen pilot manifest

```text
30 games
180 exact request timestamps
maximum planned quota: 1,800 credits
Opening labels: 0
paid provider calls: 0
real quotes: 0
```

### Approval packet

```text
formal state before decision: APPROVAL_PACKET_VALID_AWAITING_USER_APPROVAL
checks: 23 / 23
failures: 0
```

The approval packet remains historical evidence of the proposed paid path. The new decision record supersedes its waiting state but does not rewrite or delete the packet.

## Source of Truth Order

1. Latest `main` and merged PRs.
2. GitHub Actions and Artifact QA.
3. This decision record and handoff.
4. Older handoffs and chat history.

## Next Exact Task

```text
Create a no-cost source qualification matrix from the existing source registry
→ verify availability, legality, timestamp semantics and bookmaker identity
→ reject any source that cannot provide auditable point-in-time two-sided h2h quotes
→ keep Market Backtest locked until a source passes all gates
```
