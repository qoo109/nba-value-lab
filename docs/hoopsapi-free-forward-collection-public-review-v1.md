# HoopsAPI Free — Public Forward-Collection Review v1

Date: 2026-07-24  
Formal Stake: `0`

## Objective

Review only HoopsAPI's public website, documentation surface, pricing and Terms of Service. Do not create an account, connect an API key, execute requests, retain quote rows or run market metrics.

## Public findings

The official site publicly advertises a free tier with 10 requests per day, no card requirement, all competitions and providers, and moneyline, handicap and over/under markets. It states that provider odds refresh every five minutes and canonical game data every fifteen minutes.

The public response example for `GET /v1/games?competition=NBA` includes a stable-looking `game_id`, competition, home and away teams, scheduled `start_time`, provider objects, and two-sided moneyline values within each provider object.

The public example does not include a quote-level `observed_at`, provider update timestamp or bookmaker last-update field. Therefore a future private collector would have to generate its own retrieval timestamp (`fetched_at`) and preserve it as the observation time without pretending it is a provider-origin timestamp.

## Historical boundary

Full odds history and snapshots are advertised only on the paid Data plan at EUR 249 per month. The free tier cannot backfill the frozen 2019-20 through 2023-24 Gold population and cannot unlock the existing market backtest.

## Terms boundary

The Terms of Service require an account and API key. They prohibit resale, redistribution and sublicensing of raw odds data, constructing a competing odds aggregation service, and bypassing rate limits or access controls. Any future use must therefore remain private and purpose-limited; raw quote rows must not be committed or uploaded as public artifacts.

## Formal decision

```text
HOOPSAPI_FREE_PUBLIC_REVIEW_FORWARD_ONLY_CANDIDATE
```

HoopsAPI is structurally promising for a future private forward collector, but it is not qualified for historical backfill, the existing frozen-Gold point-in-time join or market backtesting. No account, key or provider request is authorized.

## Next unique mainline

```text
DESIGN_SOURCE_AGNOSTIC_PRIVATE_FORWARD_ODDS_COLLECTOR_V1
```

This next step is design-only and requires no provider account or API key. The design must:

- record collector-generated `fetched_at` as `observed_at` while keeping its provenance explicit;
- preserve source, provider, event ID, teams and scheduled tipoff;
- reject future snapshots, fuzzy matches and missing two-sided prices;
- keep secrets and raw quote rows out of repository files, logs and public artifacts;
- perform no provider request until a separate approval and execution PR exists;
- leave market backtesting, CLV, EV, ROI and betting claims disabled.
