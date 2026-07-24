# NBA Value Lab Handoff — Public Odds Dashboard / Private Query

Updated: 2026-07-24  
Formal Stake: 0

## Repository state before milestone

```text
main: 3a2841f5513c2787c115245838c2474bf0effa70
latest merged PR: 174
open PRs before branch creation: none
recording PR: 175
```

## User request

Create a website-safe public version of the official schedule alignment, explain how private odds can later be pulled for analysis, and determine whether the current model can now perform win-probability analysis.

## Milestone

```text
PUBLIC_ODDS_ALIGNMENT_WEB_EXPORT_VALID
```

## Public website layer

```text
odds-alignment.html
js/v4-odds-alignment-public.js
data/public/odds-alignment-summary-2025-26-v1.json
```

Public scope:

```text
AGGREGATE_ONLY_NO_PRICES
price fields: 0
quote rows: 0
source event IDs: 0
collector timestamps: 0
```

The page displays official schedule-alignment and batch-time quality totals. It does not expose private prices.

## Private odds access

```text
scripts/query_private_aligned_odds_v1.py
```

The local utility supports:

- `official_schedule_row_id`;
- true `official_game_id` when available;
- away/home teams plus scheduled tipoff fallback;
- nearest available pre-tip collector batch to a requested target such as T-60.

It returns private prices with explicit diagnostic-only warnings. It does not infer or fabricate provider-origin quote time.

## Model interpretation

Model-only win-probability analysis is possible only from governed pre-game feature rows and out-of-fold or strictly forward predictions. The odds archive does not create model probability.

Correct separation:

```text
governed pre-game features -> model probability
private odds -> implied / no-vig market probability
model probability vs market probability -> exploratory sensitivity comparison
```

The current aligned odds can be compared in explicit timestamp-quality bands, but cannot unlock a formal Point-in-Time market backtest.

## Validation

Latest validated branch head at handoff recording time:

```text
head: 50eb8002aa68c76a52d2ed336be4e8a3d0da1855
workflow run: 30074523573
job: 89422267703
Artifact: 8589313990
Artifact digest: sha256:e390c34e5a2612f15bfe504fd2c3dca525780476161caeec63b586fad3a78a17
formal state: PUBLIC_ODDS_ALIGNMENT_WEB_EXPORT_VALID
contract tests: 52 / 52 PASS
Artifact inspected: yes
```

## Preserved locks

```text
provider-origin quote time verified: false
quote-level exact observed_at verified: false
strict T-60 qualified: false
point-in-time qualified: false
historical backfill qualified: false
formal Market Backtest: false
CLV / ROI / Drawdown: false
betting-edge claim: false
Formal Stake: 0
```

## Do not do

- Do not upload the private aligned CSVs or original archive to GitHub Pages.
- Do not label the nearest collector batch as an exact T-60 quote.
- Do not feed market prices into the independent win-probability model without a separately governed market-feature specification.
- Do not claim ROI, CLV or betting edge from this archive.

## Next unique mainline

```text
RUN_2025_26_MODEL_ONLY_OOF_WIN_PROBABILITY_DIAGNOSTIC_THEN_OPTIONAL_MARKET_SENSITIVITY_BANDS
```

This next step requires a governed 2025-26 feature table, final game outcomes and model prediction rows that can be joined to the aligned odds through the official schedule key. It remains diagnostic-only until exact quote-time qualification exists.
