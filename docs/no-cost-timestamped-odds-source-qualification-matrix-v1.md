# No-cost Timestamped Odds Source Qualification Matrix v1

Updated: 2026-07-23  
Project state: Research Candidate / Pre-Market-Backtest  
Formal Stake: 0

## Purpose

The repository owner declined the paid historical-odds route. This document records the first no-cost source qualification pass without lowering any existing point-in-time, identity, provenance, privacy or research gates.

This is a source-qualification result only. It does not download quote-level data, create a market backtest, calculate CLV/EV/ROI, retrain a model or authorize betting.

## Required gates

A source can unlock a historical or forward point-in-time pilot only when it can provide:

- zero-dollar access without a paid trial or card requirement;
- real observation timestamps rather than retrieval-time guesses;
- explicit bookmaker identity;
- two-sided NBA h2h prices from the same bookmaker;
- strictly pre-tip snapshots;
- deterministic game and team mapping;
- acceptable terms and storage boundaries;
- no login, paywall, 401, 403, 429 or technical-control bypass.

Opening may not be inferred from T-6h, first-seen or Closing. Closing-only archives remain forecast benchmarks rather than executable entry-price histories.

## Initial result

No source is qualified for production historical backfill yet.

### 1. BloomBet Free API — most promising API candidate

Official page checked: `https://getbloombet.com/`

The official page states:

- Free plan: 500 requests per month.
- NBA and NFL coverage.
- Live and historical moneyline data.
- More than 15 providers.
- The API documentation page states the free key requires no credit card.

Still unverified:

- exact historical endpoint and response schema;
- whether each row includes a provider snapshot timestamp;
- coverage years and update cadence;
- explicit Opening and Closing semantics;
- data retention and research-output rights.

Decision:

```text
PROMISING_NEEDS_ZERO_COST_SCHEMA_AND_TERMS_PILOT
```

No account or API key has been created or read. A later pilot must be limited to metadata/schema calls and must not calculate market performance.

### 2. Kaggle Basketball-odds-history — most promising existing archive candidate

Dataset checked: `https://www.kaggle.com/datasets/zachht/wnba-odds-history`

The Kaggle card states:

- CC0 license on the dataset page;
- collection began 2025-08-24;
- scraping attempted every seven minutes;
- global, NBA, college and WNBA coverage;
- approximately 95.79 MB and 550 files at the time of review.

Still unverified:

- exact NBA file names and columns;
- real observation timestamp column;
- bookmaker identity and same-book two-sided quotes;
- the scraper's upstream source and its terms;
- whether timestamps represent observations or later publication/export times.

Decision:

```text
PROMISING_NEEDS_FILE_SCHEMA_AND_PROVENANCE_REVIEW
```

The next safe action is a manual dataset download followed by local inspection of only the NBA files and notebook. A CC0 label on Kaggle does not by itself prove upstream extraction rights or point-in-time semantics.

### 3. HoopsAPI Free — forward-only possibility

Official pages checked:

- `https://hoopsapi.com/`
- `https://hoopsapi.com/legal/terms`

The free plan provides 10 current-data requests per day. Full odds history and snapshots are listed under the paid Data plan. Terms prohibit resale or redistribution of raw odds data.

Decision:

```text
FORWARD_COLLECTION_CANDIDATE_ONLY_NOT_HISTORICAL_BACKFILL
```

A separately governed future collector could potentially record its own lawful fetch timestamps while keeping quote-level data private. This is not approved or implemented by this matrix.

## Rejected or role-limited sources

| Source | Result | Reason |
|---|---|---|
| BALLDONTLIE NBA odds | Reject no-cost historical gate | Betting odds and historical opening endpoints require the paid GOAT tier. |
| The Odds API historical v4 | Paid route remains rejected | Historical snapshots are paid-only and the owner declined the paid path. |
| Christopher Treasure Kaggle NBA Odds | Keep Closing benchmark only | No auditable observed_at, bookmaker identity or multi-snapshot semantics. |
| cviaxmiwnptr Kaggle NBA Betting Data | Keep legacy QA role only | No bookmaker, observed_at or verified Opening/Closing identity. |
| OddsPortal | Manual QA only | Existing registry and terms review block automated extraction. |
| Covers Sports Odds History | Futures reference only | NBA scope is futures, season totals and playoff series rather than game-level timestamped h2h. |
| OddsCrowd | Manual current reference pending review | Current comparison pages are visible, but historical archive, timestamp semantics and automation rights are unverified. |

## Current formal boundary

```text
qualified historical sources: 0
market backtest unlocked: false
CLV / EV / ROI unlocked: false
betting edge claim allowed: false
formal Stake: 0
```

## Next exact task

```text
A. Manually download Kaggle Basketball-odds-history
   → inspect NBA files, notebook, schema, timestamps, bookmaker identity and provenance

B. Review BloomBet free API endpoint schema and terms
   → only if still zero-cost and no card is required
   → later run at most three metadata/schema requests with a private key

C. Reject both sources unless all immutable qualification gates pass
```

No source should be selected by model performance, ROI or favorable prices.
