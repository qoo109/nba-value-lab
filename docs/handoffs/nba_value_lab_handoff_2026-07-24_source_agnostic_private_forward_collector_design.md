# NBA Value Lab Handoff — Source-Agnostic Private Forward Odds Collector Design

Date: 2026-07-24  
Formal Stake: `0`

## Project

Repository: `qoo109/nba-value-lab`

## Completed

- Preserved the BloomBet schema probe as deferred with zero execution.
- Preserved HoopsAPI as an unauthorized forward-only candidate, not a historical source.
- Designed a provider-neutral private forward NBA Moneyline collector.
- Added the canonical private quote JSON Schema.
- Separated `collector_fetched_at_utc` from provider-origin quote timestamps.
- Required exact team and scheduled-tipoff mapping for point-in-time eligibility.
- Prohibited Closing-only substitution for T-60 or T-5.
- Defined deterministic deduplication and quarantine rules.
- Defined private SQLite storage and aggregate-only public Artifact boundaries.
- Did not create an account, connect a key, make a network request, retain a real quote or run market metrics.

## Formal state

```text
SOURCE_AGNOSTIC_PRIVATE_FORWARD_ODDS_COLLECTOR_DESIGN_VALIDATED
```

## Key files

```text
data/research/source-agnostic-private-forward-odds-collector-design-v1.json
schemas/private-forward-odds-quote-v1.schema.json
docs/source-agnostic-private-forward-odds-collector-v1.md
data/research/no-cost-timestamped-odds-source-qualification-current-status-v5.json
```

## Timestamp rule

```text
collector_fetched_at_utc NEVER substitutes quote_observed_at_utc
```

Rows with no verified provider-origin timestamp may be stored privately as forward observations, but remain:

```text
point_in_time_eligible = false
```

## Current boundaries

```text
Account creation: false
API key connection: false
Network requests: false
Scheduler activation: false
Real quote ingestion: false
Raw quote publication: false
Historical backfill: false
Market Backtest: false
CLV / EV / ROI: false
Formal Stake: 0
```

## One unique next mainline

```text
IMPLEMENT_SOURCE_AGNOSTIC_PRIVATE_FORWARD_ODDS_COLLECTOR_OFFLINE_CORE_V1
```

## Next implementation boundary

The next step may use only synthetic inputs to implement schema checks, deterministic hashes, deduplication, quarantine, private temporary SQLite writes and aggregate-only QA. It must not include an HTTP client, secret reader, active scheduler, provider account, real payload or market performance calculation.

## Do not redo

- Do not rerun the BloomBet schema probe unless the user later gives explicit approval.
- Do not treat HoopsAPI free data as historical backfill.
- Do not infer `observed_at` from collector fetch time.
- Do not infer Opening from first seen, T-6h or T-24h.
- Do not use Closing-only rows as T-60 or T-5.
- Do not unlock Market Backtest or raise Stake above 0.
