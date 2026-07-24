# Kaggle NBA Odds — Full 2025–26 Official Schedule Alignment v1

Updated: 2026-07-24  
Formal Stake: 0

## Purpose

Repair the private Kaggle `Basketball-odds-history` NBA archive with governed official schedule metadata while preserving the archive's time uncertainty.

This pass adds or verifies:

- stable official schedule row identity;
- official away/home orientation where declared;
- published scheduled tipoff in UTC;
- regular-season, neutral-site, NBA Cup Championship, All-Star and postseason/play-in separation;
- known schedule-date and schedule-time reconciliation;
- batch-time distance from published tipoff.

It does **not** create provider-origin quote timestamps or exact T-60 quotes.

## Private input

```text
archive SHA-256:
sha256:36685fa53deaba112f93515fefffb971b02613f32f2f24d5a22dd0088863d419

nba_main_lines.csv: 8,153 rows
nba_detailed_odds.csv: 149,752 rows
source events: 1,199
```

The ZIP, quote rows and prices remain private and are not committed.

## Official schedule evidence

### Schedule release

The official NBA Communications 2025–26 day-by-day schedule-release PDF was used as the versioned base schedule.

```text
version date: 2025-08-14
published rows: 1,200
team appearances: 80 per team
neutral-site rows: 3
subject to change: yes
payload SHA-256:
sha256:98a06493d0a107cc410853ad230e67d48858777a2baf76ac77d089cbeaf2435d
```

The release contains 80 defined games per team. Thirty Dec. 9–15 regular-season games were left to be determined after NBA Cup group play.

### Official LiveData reconciliation subset

A bounded official NBA LiveData pass fetched 38 game metadata records:

```text
30 NBA Cup-determined regular-season games
4 known date adjustments
4 known time adjustments
returned: 38 / 38
```

Only metadata was fetched: official NBA game ID, teams, `gameTimeUTC`, status and arena fields. No odds were requested.

### Reconciled regular-season schedule

```text
base release rows retained: 1,192
NBA Cup-determined rows added: 30
date-adjustment rows added: 4
time-adjustment rows added: 4
final schedule rows: 1,230
unique schedule row IDs: 1,230
duplicate matchup/tipoff rows: 0
```

## Full archive result

All 1,199 source events received a deterministic classification:

| Classification | Events |
|---|---:|
| `MATCHED_HIGH_CONFIDENCE_REGULAR_SEASON` | 1,102 |
| `MATCHED_SCHEDULE_ADJUSTED` | 8 |
| `MATCHED_NEUTRAL_SITE_REGULAR_SEASON` | 2 |
| `EXCLUDED_POSTSEASON_OR_PLAY_IN` | 83 |
| `EXCLUDED_ALL_STAR` | 3 |
| `EXCLUDED_NBA_CUP_CHAMPIONSHIP` | 1 |
| `UNMATCHED_OR_AMBIGUOUS` | 0 |

Regular-season matches:

```text
regular events matched: 1,112
one-to-one event/schedule matches: 1,112
official published tipoff present: 1,112
stable official schedule row ID present: 1,112
true official NBA game ID present: 38
stable PDF schedule row ID used: 1,074
archive coverage of 1,230-game schedule: 90.4065%
```

The PDF itself does not provide NBA game IDs. Therefore the 1,074 release-only matches receive a deterministic `official_schedule_row_id`, not a fabricated `official_game_id`.

## Row enrichment

```text
regular main rows enriched: 7,713
regular detailed rows enriched: 144,034
all detailed rows mapped to a main event: 149,752 / 149,752
unmapped detailed rows: 0
```

The original source `timestamp` remains unchanged. New fields distinguish it from official schedule time:

```text
collector_batch_timestamp_utc_assumed
scheduled_tipoff_utc
batch_minutes_before_published_tipoff
batch_pre_tip_by_assumed_utc
t60_absolute_error_minutes
t60_batch_candidate
collector_timestamp_semantics
quote_observation_time_semantics
```

## Batch T-60 diagnostic

For each matched regular-season event, the nearest positive batch timestamp to published T-60 was selected.

```text
regular events with a pre-tip candidate: 1,111
regular events without a pre-tip candidate: 1
within T-60 ±5 minutes: 315
within T-60 ±15 minutes: 497
within T-60 ±30 minutes: 616
within T-60 ±60 minutes: 699
median absolute batch error: 23.5167 minutes
regular events containing at/post-tip batches: 28
at/post-tip regular main rows: 34
```

These are named **batch candidates**, not exact quote observations. The notebook creates a league-batch timestamp and then reads detailed pages sequentially, so an individual quote can occur later than the shared timestamp.

## Official time repaired; quote time unresolved

The alignment successfully repairs:

- game identity at schedule-row level;
- away/home orientation;
- official published tipoff;
- competition bucket;
- schedule changes represented in the bounded LiveData subset.

It does not verify:

- provider-origin quote time;
- exact row-level `observed_at`;
- strict pre-tip status for each quote;
- exact T-60 quote identity.

## Decision

```text
KEEP_PRIVATE_DIAGNOSTIC_ALIGNMENT
OFFICIAL_SCHEDULE_REPAIRED
QUOTE_TIME_UNRESOLVED
```

## Preserved locks

```text
point-in-time qualified: false
historical backfill qualified: false
formal history write: false
G1.2.0 real input: false
Market Backtest: false
CLV / EV / ROI / Drawdown: false
betting edge claims: false
Formal Stake: 0
```

## Private deliverables

The local bundle contains:

```text
official_nba_2025_26_reconciled_schedule_v1.csv
kaggle_official_schedule_full_alignment_events_v1.csv
kaggle_nba_main_lines_officially_aligned_2025_26_v1.csv
kaggle_nba_detailed_odds_officially_aligned_2025_26_v1.csv
kaggle_official_schedule_full_alignment_summary_v1.json
```

Do not commit or publicly redistribute these enriched quote files.

## Next unique mainline

```text
AWAIT_REAL_GOVERNED_2026_27_T60_INPUT_AND_QUALIFIED_TIMESTAMPED_ODDS
```
