# Real Timestamped Odds Acquisition / Backfill v1 — Predeclaration

## Purpose

This document freezes the source, population, timestamps, market, identity rules, privacy boundary, cost controls, source-health gates and future decision states **before** any paid historical odds request, raw response inspection, coverage result, odds join or market backtest.

The existing odds schema, source registry, proportional no-vig method, closing benchmark and point-in-time market layer are reused. This is not a new odds registry and does not calculate ROI, CLV, EV or betting edge.

## Roadmap position

```text
Injury Feature Holdout v1 — VALID_NEGATIVE_RESULT
→ this Real Timestamped Odds Acquisition / Backfill predeclaration
→ separate 90-game source-health pilot
→ explicit budget approval before full 3-season backfill
→ separate Point-in-time Odds Join / Market Backtest predeclaration
```

Formal stake remains `0`.

## Frozen upstream path

```text
main at predeclaration start:
95bf21a2b7dbe44cbd3eba09a9d72873c391fc70

PR #56:
Injury Feature Walk-forward Holdout v1
formal state: VALID_NEGATIVE_RESULT

market research model path:
frozen walk-forward-v2 raw Logistic + Elo baseline only

injury candidate:
rejected and excluded
```

The target prediction artifact is `model-walk-forward-v2`, workflow run `29551715399`, containing 3,688 out-of-fold games.

## Existing assets that must be reused

- `docs/point-in-time-odds-layer-v1.md`
- `scripts/build_point_in_time_odds.py`
- `data/templates/point-in-time-odds-template.csv`
- `data/historical-odds-source-registry.json`
- Existing proportional two-way no-vig definition
- Existing closing-only benchmark as a forecast benchmark only

No parallel odds schema or replacement source registry may be created.

## Frozen source

Primary source:

```text
source id: the_odds_api_historical_v4
provider: The Odds API Pty Ltd
API: https://api.the-odds-api.com/v4
historical endpoint: /historical/sports/{sport}/odds
sport key: basketball_nba
```

Source facts checked on 2026-07-18:

- Featured-market history is documented from 2020-06-06.
- Historical snapshots are documented at 10-minute intervals before 2022-09-18 and 5-minute intervals afterward.
- A historical query returns the closest snapshot at or before the requested ISO-8601 time.
- Historical access requires a paid plan.
- Historical odds cost 10 credits per region per market.

Terms boundary:

- API key must stay in `THE_ODDS_API_KEY` and must never appear in logs or artifacts.
- Raw or normalized bookmaker rows must not be committed to the public repository or published in a public Artifact.
- The provider data must not be resold, repackaged or redistributed as a standalone data product.
- Public outputs are limited to credential-free manifests, hashes, byte counts, request/quota totals, aggregate coverage QA and deidentified failure diagnostics.
- Raw and normalized rows require restricted user-controlled storage and must be deleted from workflow temporary storage.
- External or commercial deployment still requires a final usage-rights review.

No scraping fallback is allowed if the commercial source is unavailable.

## Frozen market and API request scope

```text
sport: basketball_nba
region: us
market: h2h only
odds format: decimal
date format: ISO-8601
bookmakers: all returned in the frozen region
include source IDs: true
include rotation numbers: true
include bookmaker links: false
```

Spread and total acquisition are outside v1. The current model predicts home-win probability, so the first executable market research layer is two-way NBA moneyline only.

## Frozen full target population

The population is the complete frozen walk-forward-v2 OOF set:

| Season | Games | Date range |
|---|---:|---|
| 2021-22 | 1,230 | 2021-10-19 through 2022-04-10 |
| 2022-23 | 1,230 | 2022-10-18 through 2023-04-09 |
| 2023-24 | 1,228 | 2023-10-24 through 2024-04-14 |
| **Total** | **3,688** | 3 chronological OOF seasons |

Each `game_id` is one independent game. Multiple bookmakers and snapshots are repeated observations of the same game, not additional model samples.

No game may be selected or replaced using outcomes, existing closing odds, model error, ROI or injury-candidate results.

## Frozen 90-game source-health pilot

Before full acquisition, a 90-game pilot must be generated from the frozen OOF file:

```text
30 games per season
hash = SHA-256("timestamped-odds-v1-pilot|" + game_id)
sort ascending within each season
take the first 30
```

The 90-game manifest must be written and hashed before the first paid API request. A failed date or game cannot be replaced with a handpicked alternative.

The pilot is source engineering only. It must not calculate model-versus-market performance.

## Event identity contract

A provider event is eligible only when all of the following are true:

1. Home team matches the frozen deterministic NBA full-name mapping.
2. Away team matches exactly after the same mapping.
3. Provider `commence_time`, converted to `America/New_York`, has the same local date as the Gold game date.
4. The match is unique.
5. Provider event ID and UTC commence time are present.

The event-discovery request is anchored at `00:00 America/New_York` on the Gold game date. The provider commence time from that response becomes the frozen acquisition anchor.

No fuzzy team matching, fuzzy schedule matching, nearest-date matching or manual identity override is allowed. Ambiguous matches are source failures.

If provider commence time changes by more than 30 minutes across snapshots, the game is excluded and reported; it is not silently re-anchored after prices are seen.

## Frozen snapshot contract

Fixed snapshots:

```text
T-6h
T-3h
T-1h
T-30m
Closing = anchor commence time minus 1 second
```

The returned source snapshot must be at or before the requested time and no more than 15 minutes older than the target.

Opening is deliberately defined as a reproducible proxy, not as a claim about a bookmaker's true first-posted price:

```text
Opening grid:
T-14d, T-10d, T-7d, T-5d, T-3d, T-48h, T-24h, T-12h, T-6h

OpeningGridProxy:
the earliest valid two-sided bookmaker quote found on this fixed grid
```

Public outputs must retain the label `OpeningGridProxy`. They must not call it a true bookmaker opening timestamp.

For every quote:

- source snapshot timestamp must be preserved;
- bookmaker `last_update` must be at or before the source snapshot and before tip-off;
- Closing `last_update` may be at most 60 minutes old;
- later-snapshot fallback is forbidden;
- cross-book, cross-time and cross-game filling are forbidden.

## Quote normalization contract

Primary market is exactly `h2h` with exactly two outcomes: frozen home team and frozen away team.

Requirements:

- decimal price strictly greater than 1.0;
- no draw outcome;
- provider bookmaker key and title preserved;
- provider event ID preserved;
- source IDs preserved when available;
- source snapshot timestamp and bookmaker last-update preserved;
- retrieval timestamp, raw SHA-256 and adapter version required;
- unique key: `(game_id, snapshot_label, bookmaker_key, market_key)`;
- duplicate keys allowed: 0;
- missing prices or bookmakers remain missing;
- American odds are not the canonical stored format.

No-vig, edge, ROI, CLV and market scoring are not calculated during acquisition.

## Cost and request guardrails

A dry-run request plan is mandatory before network access. It must report request counts by endpoint and estimated provider credits.

Pilot hard cap:

```text
20,000 credits
```

The workflow must abort before any paid request when the estimate exceeds the cap.

Every response must record:

- `x-requests-remaining`
- `x-requests-used`
- `x-requests-last`

HTTP 401/403 must not be bypassed. HTTP 429 permits at most three bounded retries with backoff; concurrency must not be increased to defeat the limit.

This predeclaration does **not** authorize the full 3,688-game paid backfill. Full execution requires a separate explicit user budget approval after the pilot reports its real request plan and coverage.

## Pilot source-health gates

All are frozen before source access:

```text
planned games = 90
exact event match rate >= 95%
exact event match rate in each season >= 90%
ambiguous events = 0
team identity mismatches = 0
successful request rate >= 95%
snapshot timestamp compliance = 100%
fixed-snapshot freshness >= 99%
games with 2+ books at T-1h >= 80%
games with a same-book T-1h / Closing pair >= 80%
secret exposures = 0
public raw or normalized quote rows = 0
post-tip quotes = 0
later-snapshot fallbacks = 0
fuzzy matches = 0
```

A pilot pass unlocks only explicit-budget full backfill. It does not unlock an odds join or market backtest.

## Full-backfill gates

```text
target games = 3,688
matched independent games >= 3,000
matched games in every season >= 900
seasons = 3
T-1h two-sided coverage >= 80%
same-book T-1h / Closing paired coverage >= 80%
point-in-time violations = 0
team identity mismatches = 0
duplicate quote keys = 0
public raw or normalized quote rows = 0
```

Primary bookmaker selection is coverage-only:

```text
1. Keep books with overall T-1h / Closing paired coverage >= 80%.
2. Require paired coverage >= 70% in each season.
3. Select the highest paired coverage.
4. Resolve exact ties by bookmaker key ascending.
```

Outcomes, model error, edge, ROI or CLV may not influence bookmaker selection.

## Future formal decision states

```text
SOURCE_ACCESS_BLOCKED
SOURCE_STRUCTURAL_BLOCKED
PILOT_READY_FOR_FULL_BACKFILL
FULL_BACKFILL_READY_FOR_ODDS_JOIN_PREDECLARATION
```

`SOURCE_ACCESS_BLOCKED` means the paid plan, API secret, restricted storage or explicit pilot budget permission is absent. It is not a source-quality result.

`SOURCE_STRUCTURAL_BLOCKED` means access existed but one or more frozen source, identity, timestamp, quote, cost or privacy gates failed.

`PILOT_READY_FOR_FULL_BACKFILL` permits only a separately approved full acquisition.

`FULL_BACKFILL_READY_FOR_ODDS_JOIN_PREDECLARATION` permits only a new, separate point-in-time odds join and market-backtest predeclaration using the frozen baseline-only model path.

None of these states directly enables:

```text
point-in-time odds join execution
market backtest
CLV / EV / ROI / Drawdown
production probability adjustment
betting edge claim
nonzero stake
```

## Permanent non-activation boundary

```text
paid API request performed in this PR: false
raw odds inspected in this PR: false
coverage measured in this PR: false
market performance calculated in this PR: false
injury candidate used: false
odds used for model training: false
closing used to select entry: false
stake: 0
```
