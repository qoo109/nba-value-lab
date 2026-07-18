# No-cost Timestamped Odds Metadata Census v1

## Formal result

```text
NO_COST_METADATA_BLOCKED
```

Eight frozen candidate classes were reviewed under PR #66. None passed every license, provenance, bookmaker-definition and timestamp-semantics gate required to begin the frozen 30-game source-health pilot.

## Important boundary

This census used public metadata, existing repository evidence and availability checks only.

```text
quote downloads: 0
paid calls: 0
accounts created: 0
API keys read: 0
market metrics calculated: false
formal stake: 0
```

## Candidate conclusions

| Candidate | Result | Allowed boundary |
|---|---|---|
| Christopher Treasure NBA Odds | Reliable `observed_at` and bookmaker-level snapshot history not established | Existing closing benchmark only |
| Evan Hallmark historical betting data | Kaggle license unknown; no description/provenance | Metadata reference only |
| Eric Qiu odds and scores | CC0 label, but original sources are unnamed and timestamp/bookmaker semantics are unclear | Manual metadata/schema research only |
| cviaxmiwnptr NBA betting data | Game-level odds columns, but no bookmaker key, `observed_at`, or multiple pre-tip snapshots | Single-row odds cross-check only |
| SportsbookReviewOnline legacy archive | Both direct archive URLs returned HTTP 404 | Legacy provenance note only |
| OddsPortal | Automation remains prohibited by the project registry and source terms boundary | Manual spot checks only |
| Public GitHub collectors | Client/collector code exists, but no reusable historical quote asset with clear rights was found | Code-pattern research only |
| User-supplied data | No file or rights statement was supplied | None |

## Why CC0 was not enough

A dataset uploader's CC0 label does not automatically resolve rights or provenance for material collected from unnamed or third-party sources. It also does not create missing bookmaker identities or actual observation timestamps.

## Why opening/closing rows are not enough

The project requires a quote to be tied to:

```text
one bookmaker
one source snapshot
two sides of the same h2h market
observed_at / provider_snapshot_at
scheduled_tipoff_utc
strictly pre-tip timing
```

A single game-level row, a generic closing label, or an opening/closing pair without observation timestamps cannot represent T-6h, T-3h, T-1h, T-30m or T-5m.

## Decision boundary

```text
ready_for_frozen_source_health_pilot: false
ready_for_production_backfill: false
ready_for_point_in_time_odds_join: false
ready_for_market_backtest: false
ready_for_clv_ev_roi_drawdown: false
ready_for_betting_edge_claim: false
formal stake: 0
```

## Next allowed path

The market-data line pauses until one of these occurs:

1. a materially new lawful no-cost source appears; or
2. the user supplies a data file plus an explicit rights/provenance statement.

Any new candidate must pass the same PR #66 gates. Games, coverage thresholds, PIT rules and bookmaker requirements may not be relaxed.
