# No-cost Timestamped Odds Source Qualification v1

## Position

```text
PR #65 — PAID_PILOT_NOT_APPROVED
→ this predeclaration
→ metadata and schema qualification only
→ separate frozen source-health execution PR only if a candidate passes
```

This stage does not download historical quotes, create accounts, use API keys, run a market backtest, or calculate betting performance.

## Why this stage exists

The project still lacks the core market asset: lawful bookmaker-level NBA historical moneyline quotes with a reliable observation timestamp strictly before tipoff. Public datasets often provide one game-level odds row, an opening/closing label without a timestamp, or unclear source provenance. Those assets may support a manual cross-check or closing benchmark, but they cannot impersonate executable point-in-time prices.

## Frozen scope

The existing 30-game qualification sample and six snapshot labels are reused without changes:

```text
T-6h / T-3h / T-1h / T-30m / T-5m / Closing
30 games
10 games per season
2021-22 / 2022-23 / 2023-24
180 requested snapshot slots
```

No candidate may replace games after its coverage is observed.

## Frozen candidate roster

| Candidate | Current metadata state | Initial action |
|---|---|---|
| Christopher Treasure NBA Odds | Existing closing benchmark; timestamp unknown/closing-only | Reuse aggregate evidence only |
| Evan Hallmark NBA Historical Betting | License unknown; no usable provenance description | Metadata review only |
| Eric Qiu NBA Odds and Scores | Kaggle CC0 label; description says scraped from unspecified sources | Metadata/schema review only |
| cviaxmiwnptr NBA Betting Data | Kaggle CC0 label; derived from SBR and ESPN; one game-level odds row | Metadata/schema review only |
| SportsbookReviewOnline legacy archive | Direct archive URL returns 404 | Availability record only |
| OddsPortal | Project registry prohibits automation | Manual spot checks only |
| Public GitHub odds collectors | Code does not establish data rights or included historical data | License and included-data inventory only |
| Future user-supplied file | Not provided | Same rights, schema and PIT gates apply |

## Metadata gate

A candidate is blocked before download or import unless all relevant facts are explicit:

- license or permission;
- automated research use boundary;
- original source provenance and terms;
- bookmaker definition;
- moneyline semantics;
- timestamp semantics;
- scheduled tipoff availability;
- no paid plan, secret, account or access-control bypass.

A CC0 label on a derived dataset is not sufficient by itself when the original source and collection rights are unclear.

## Schema gate

A source that passes metadata review must still provide:

```text
same bookmaker
same source snapshot
two-sided h2h prices
bookmaker key
provider_snapshot_at or observed_at
scheduled_tipoff_utc
home / away identity
stable source event key
file version / retrieval provenance
```

Missing rows are not zero and a closing row is not a T-60 or opening row. Fuzzy matching and future-snapshot substitution remain forbidden.

## Source-health gates

The original strict qualification thresholds are retained:

```text
target-game mapping >= 90%
>= 8 mapped games per season
primary bookmaker complete T-60 + Closing games >= 24
>= 7 complete T-60 + Closing games per season
all-target snapshot coverage >= 70%
PIT violations = 0
future snapshot rows = 0
team mismatches = 0
fuzzy matches = 0
duplicate quote keys = 0
inferred Opening labels = 0
```

Price range and two-way overround checks also remain unchanged.

## Decision states

```text
NO_COST_METADATA_BLOCKED
NO_COST_SCHEMA_REVIEW_REQUIRED
NO_COST_SOURCE_STRUCTURAL_BLOCKED
NO_COST_SOURCE_QUALIFIED_FOR_FROZEN_PILOT
```

Even the final state only permits a separate frozen source-health pilot PR. It does not unlock the production backfill or any market-performance calculation.

## Permanent boundary

```text
paid access: false
account / subscription: false
API key or secret: false
restricted scraping: false
market backtest: false
CLV / EV / ROI / Drawdown: false
betting-edge claim: false
formal stake: 0
```
