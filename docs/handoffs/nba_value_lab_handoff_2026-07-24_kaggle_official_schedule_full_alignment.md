# NBA Value Lab Handoff — Kaggle Full Official Schedule Alignment

Updated: 2026-07-24  
Formal Stake: 0

## Repository state before milestone

```text
main: 573d7782c270e4c7b5ffceb8ff1dd50c607b9c5b
latest merged PR: 173
open PRs before branch creation: none
recording PR: 174
```

## User request

Expand the successful 20-game pilot and fill the private Kaggle NBA odds archive with official game schedule information.

## Inputs

```text
private archive SHA-256:
sha256:36685fa53deaba112f93515fefffb971b02613f32f2f24d5a22dd0088863d419

main rows: 8,153
detailed rows: 149,752
source events: 1,199
```

The raw ZIP, quote rows and prices were not committed.

Official evidence:

- official NBA Communications 2025–26 day-by-day schedule-release PDF, versioned 2025-08-14 and marked subject to change;
- 38 bounded official NBA LiveData boxscore metadata records covering 30 NBA Cup-determined regular-season games, four known date adjustments and four known time adjustments;
- official NBA Cup Championship page for the non-standings Spurs–Knicks final.

## Milestone

```text
KAGGLE_OFFICIAL_SCHEDULE_FULL_ALIGNMENT_DIAGNOSTIC_VALID
```

## Reconciled schedule

```text
release rows retained: 1,192
NBA Cup-determined rows added: 30
date adjustments added: 4
time adjustments added: 4
final regular-season schedule rows: 1,230
unique schedule row IDs: 1,230
duplicate matchup/tipoff rows: 0
```

## Event classification

```text
MATCHED_HIGH_CONFIDENCE_REGULAR_SEASON: 1,102
MATCHED_SCHEDULE_ADJUSTED: 8
MATCHED_NEUTRAL_SITE_REGULAR_SEASON: 2
EXCLUDED_POSTSEASON_OR_PLAY_IN: 83
EXCLUDED_ALL_STAR: 3
EXCLUDED_NBA_CUP_CHAMPIONSHIP: 1
UNMATCHED_OR_AMBIGUOUS: 0
```

All 1,199 source events are classified. Regular-season events matched: 1,112.

## Official identity and tipoff coverage

```text
regular event/schedule one-to-one matches: 1,112
official published tipoff present: 1,112
stable official schedule row ID present: 1,112
true official NBA game ID present: 38
stable PDF-derived schedule row ID used: 1,074
```

The official release PDF does not contain NBA game IDs. Do not call PDF-derived stable schedule row IDs official NBA game IDs.

## Row enrichment

```text
regular main rows enriched: 7,713
regular detailed rows enriched: 144,034
detailed rows mapped to source event: 149,752 / 149,752
unmapped detailed rows: 0
```

## Batch-time diagnostic

```text
regular events with a pre-tip batch candidate: 1,111
regular events without one: 1
T-60 ±5m batch candidates: 315
T-60 ±15m batch candidates: 497
T-60 ±30m batch candidates: 616
T-60 ±60m batch candidates: 699
median absolute batch error: 23.5167m
regular events containing at/post-tip batches: 28
at/post-tip regular main rows: 34
```

The original `timestamp` is preserved. It remains a collector-created league-batch timestamp assumed UTC. It is not a provider-origin or row-level quote timestamp.

## Validation evidence

```text
workflow run: 30071992939
workflow job: 89414627564 — success
Artifact: 8588364774
digest:
sha256:99f48e85d931fd4b732b9c6d42d12c1b985f6a4b31e48bb60b6b3e6011dd0454
formal state:
KAGGLE_OFFICIAL_SCHEDULE_FULL_ALIGNMENT_RECORD_VALID
contract tests: 81 / 81 PASS
Artifact inspected: yes
```

The Artifact is aggregate-only. It confirms that no private archive or quote rows were committed and no market metrics were executed.

## Decision

```text
KEEP_PRIVATE_DIAGNOSTIC_ALIGNMENT
OFFICIAL_SCHEDULE_REPAIRED
QUOTE_TIME_UNRESOLVED
```

## Private outputs

```text
official_nba_2025_26_reconciled_schedule_v1.csv
kaggle_official_schedule_full_alignment_events_v1.csv
kaggle_nba_main_lines_officially_aligned_2025_26_v1.csv
kaggle_nba_detailed_odds_officially_aligned_2025_26_v1.csv
kaggle_official_schedule_full_alignment_summary_v1.json
kaggle_official_schedule_full_alignment_bundle_2025_26_v1.zip
```

These files remain private and must not be committed or redistributed.

## Preserved locks

```text
provider-origin quote time verified: false
quote-level exact observed_at verified: false
strict T-60 qualified: false
point-in-time qualified: false
historical backfill qualified: false
formal history write: false
G1.2.0 real input: false
Market Backtest: false
CLV / EV / ROI / Drawdown: false
betting edge claims: false
Formal Stake: 0
```

## Do not do

- Do not overwrite the original source timestamp.
- Do not label batch candidates exact T-60 quotes.
- Do not publish the enriched quote-level CSV files.
- Do not fabricate NBA game IDs for PDF-only schedule rows.
- Do not unlock market metrics or betting claims from this diagnostic alignment.

## Next unique mainline

```text
AWAIT_REAL_GOVERNED_2026_27_T60_INPUT_AND_QUALIFIED_TIMESTAMPED_ODDS
```
