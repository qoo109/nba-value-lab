# Public / Private Odds Usage v1

Updated: 2026-07-24  
Formal Stake: 0

## Purpose

The 2025-26 Kaggle odds archive has been aligned to official NBA schedule metadata, but its timestamp remains a collector-created league-batch timestamp. The project therefore separates the public website layer from the private price layer.

## Public website layer

Public files:

```text
odds-alignment.html
js/v4-odds-alignment-public.js
data/public/odds-alignment-summary-2025-26-v1.json
```

The public layer may display:

- official schedule alignment totals;
- classification totals;
- snapshot coverage;
- T-60 batch-candidate quality counts;
- timestamp and qualification warnings.

It must not contain:

- decimal odds or prices;
- quote rows;
- Pinnacle links;
- source event IDs;
- collector timestamps;
- exact T-60 claims;
- Market Backtest, CLV, ROI or betting-edge claims.

## Private price layer

Private files remain outside the public repository:

```text
kaggle_nba_main_lines_officially_aligned_2025_26_v1.csv
kaggle_nba_detailed_odds_officially_aligned_2025_26_v1.csv
kaggle_official_schedule_full_alignment_events_v1.csv
```

Use the local query utility:

```bash
python scripts/query_private_aligned_odds_v1.py \
  --main-csv /PRIVATE/PATH/kaggle_nba_main_lines_officially_aligned_2025_26_v1.csv \
  --official-schedule-row-id <ROW_ID> \
  --target-minutes-before-tip 60 \
  --output /PRIVATE/PATH/selected-odds.json
```

Alternative selectors:

```bash
--official-game-id 0022500001
```

or:

```bash
--away-team "Houston Rockets" \
--home-team "Oklahoma City Thunder" \
--scheduled-tipoff-utc "2025-10-21T23:30:00+00:00"
```

Join-key preference:

```text
1. official_schedule_row_id
2. official_game_id, when a true NBA game ID exists
3. official away/home teams + scheduled_tipoff_utc
```

The utility selects the nearest available pre-tip collector batch to the requested target. It does not create or infer a provider-origin quote timestamp.

## Using detailed markets

After selecting a main-line batch locally, filter the detailed CSV with:

```text
official_schedule_row_id
+ collector batch timestamp
```

Then use `Market`, `Selection` and `Odds` to obtain the relevant Moneyline, Spread or Total rows. Keep this operation private.

## Model probability versus market price

The model and market layers must stay separate:

```text
governed pre-game features
        ↓
model win probability

private aligned odds
        ↓
raw implied probability
        ↓
no-vig market probability
```

The current odds archive can support exploratory sensitivity comparisons by time-quality band:

```text
T-60 candidate error <= 5 minutes
T-60 candidate error <= 15 minutes
T-60 candidate error <= 30 minutes
T-60 candidate error <= 60 minutes
```

It cannot support a formal point-in-time market backtest because provider-origin quote time and row-level exact `observed_at` remain unverified.

Do not silently feed these prices into the independent win-probability model. Doing so would make the model-versus-market comparison circular unless a separately governed market-feature model is explicitly designed and validated.

## Current qualification

```text
website display: allowed
private local price query: allowed for diagnostic research
model-only probability analysis: allowed with governed pre-game features and OOF predictions
exploratory model-versus-market sensitivity: allowed with explicit timestamp uncertainty
formal Market Backtest: locked
CLV / ROI / Drawdown: locked
betting-edge claim: locked
Formal Stake: 0
```
