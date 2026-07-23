# NBA Value Lab Handoff — Private Forward Collector Offline Core

## Formal state

```text
SOURCE_AGNOSTIC_PRIVATE_FORWARD_ODDS_COLLECTOR_OFFLINE_CORE_VALIDATED
```

## Completed

- Provider-neutral synthetic adapter and normalizer.
- `collector_fetched_at_utc NEVER substitutes quote_observed_at_utc`.
- Exact mapping and timestamp eligibility gates.
- Deterministic hash, same-run and cross-run duplicate handling, and quarantine.
- Temporary private SQLite append-only storage.
- Aggregate-only QA with no quote prices or quote-level identities.
- Twelve synthetic contract tests.

## Boundaries

```text
Account creation: false
API key connection: false
HTTP client: false
Scheduler: false
Provider requests executed: 0
Real quotes retained: 0
Market metrics: false
Formal Stake: 0
```

## Key files

```text
scripts/private_forward_odds_collector_v1.py
data/fixtures/private-forward-odds-synthetic-v1.json
data/research/source-agnostic-private-forward-odds-collector-offline-core-v1.json
data/research/no-cost-timestamped-odds-source-qualification-current-status-v6.json
docs/source-agnostic-private-forward-odds-collector-offline-core-v1.md
```

## Next unique mainline

```text
DESIGN_FIRST_PROVIDER_PRIVATE_FORWARD_ADAPTER_QUALIFICATION_GATE_V1
```

The next step is design-only. It must not create a provider account, accept provider terms, connect a secret, execute a request or ingest a real quote without a separate explicit approval gate.
