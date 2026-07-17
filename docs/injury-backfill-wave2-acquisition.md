# Injury Backfill Wave 2 — Acquisition Audit

## Purpose

Wave 1 produced 91 independent selected games, nine short of the minimum Expected Minutes Accuracy Audit gate.

Wave 2 is not a hand-picked nine-game patch. It is a second calendar-fixed source sample that complements Wave 1:

```text
Wave 1: every other Monday beginning 2023-11-06
Wave 2: complementary Mondays beginning 2023-10-30
```

Both waves use the same official publication slots and acquisition thresholds.

## Fixed registry

```text
data/multi-report-injury-backfill-wave2-times.json
```

```text
season: 2023-24
weekday: Monday
cadence: every 14 days, complementary offset from Wave 1
slots: 08:30 / 13:30 / 17:30 ET
start: 2023-10-30
end: 2024-04-01
dates: 12
candidate reports: 36
requested-time overlap with Wave 1: 0
```

Christmas Day is retained because it belongs to the calendar rule. It was not removed after observing report availability or feature quality.

## Predeclared acquisition gate

```text
minimum single-report-ready player reports: 18
minimum successful team reports: 18
minimum ready overlap reports: 18
minimum unique ready overlap dates: 8
maximum failure rate per pipeline: 50%
```

Mandatory structural and privacy gates:

- all requested timestamps are unique;
- no requested timestamp overlaps Wave 1;
- all dates are Mondays separated by 14 days;
- all registered slots are 08:30／13:30／17:30 ET;
- successful timestamps belong to the registry;
- no duplicate source timestamps or URLs;
- team submission conflicts equal zero;
- aggregate reports agree with source indexes;
- normalized player rows and raw PDFs are deleted before Artifact upload;
- player reports with `ready=false` are excluded from downstream feature backfill.

## Parsed versus ready

The multi-report player importer records a report in its source index when the official PDF was downloaded and parsed. A separate `ready` field records whether that report passed the stricter single-report official PDF Gate.

Wave 2 therefore records two different counts:

```text
player parsed reports
player single-report-ready reports
```

Only `ready=true` player reports may enter the feature pipeline.

Script:

```text
scripts/audit_ready_injury_report_overlap.py
```

Outputs:

```text
ready-overlap-audit.json
ready-overlap-report-index.csv
ready-overlap-report-times.json
ready-player-source-index.csv
```

## Verified official result

Verified workflow run:

```text
29596148999
```

### Parsed acquisition coverage

| Item | Result |
|---|---:|
| Candidate reports | 36 |
| Calendar dates | 12 |
| Player parsed reports | 33 |
| Team successful reports | 31 |
| Parsed player/team overlap | 31 |
| Player parsed dates | 11 |
| Team successful dates | 11 |
| Parsed overlap dates | 11 |
| Player parse failure rate | 8.33% |
| Team failure rate | 13.89% |

### Single-report-ready coverage

| Item | Result |
|---|---:|
| Player parsed reports | 33 |
| Player `ready=true` | 31 |
| Player `ready=false` | 2 |
| Team successful reports | 31 |
| Ready player/team overlap | 31 |
| Ready overlap dates | 11 |

The 31-report ready overlap passed the predeclared gate.

### Ingestion coverage

```text
normalized player rows before deletion: 2,591
player ingestion games: 127
team submission rows: 862
team ingestion games: 153
```

Team submission status:

```text
481 SUBMITTED_WITH_PLAYER_ROWS
376 NOT_YET_SUBMITTED
5 UNKNOWN_NO_PLAYER_ROWS
0 submission conflicts
```

These are ingestion counts, not selected independent model samples.

## Fixed failures and not-ready reports

### Player download failures

```text
2024-02-19 08:30 ET — 403 Forbidden
2024-02-19 13:30 ET — 403 Forbidden
2024-02-19 17:30 ET — 403 Forbidden
```

These three fixed times failed both player and team pipelines and were not replaced.

### Player parsed but not single-report-ready

```text
2023-12-25 13:30 ET
2023-12-25 17:30 ET
```

Both PDFs were parseable, but they did not pass the stricter single-report Gate. They are excluded from the ready overlap and cannot enter the feature pipeline.

### Team pipeline failures

```text
2023-12-25 13:30 ET
2023-12-25 17:30 ET
2024-02-19 08:30 ET
2024-02-19 13:30 ET
2024-02-19 17:30 ET
```

The Christmas afternoon/evening reports contained team contexts whose scheduled games had already tipped before the publication time. Strict pre-tip QA rejected the full team reports rather than silently retaining mixed pregame/post-tip contexts.

## Quality and privacy result

```text
registry errors: 0
duplicate requested timestamps: 0
Wave 1 requested-time overlap: 0
duplicate player source times: 0
duplicate team source times: 0
duplicate player source URLs: 0
duplicate team source URLs: 0
unexpected successful timestamps: 0
team submission conflicts: 0
forbidden player-level files retained: 0
failed registry times replaced: false
outcomes or market prices used: false
```

## Decision

Generic parsed acquisition audit:

```text
ready_for_wave1_feature_backfill = true
```

This historical key is retained for backward compatibility and means only that the calendar-fixed acquisition passed the generic parsed-source Gate.

Authoritative Wave 2 downstream decision:

```text
ready_for_feature_backfill = true
ready_for_model_training = false
ready_for_probability_adjustment = false
ready_for_betting_edge_claim = false
```

The authoritative feature input is the 31-report `ready=true` player/team overlap, not all 33 parsed player reports.

## Artifact boundary

Artifact:

```text
injury-backfill-wave2-acquisition
```

Retained:

- aggregate player ingestion report;
- full player source index with `ready` state;
- aggregate team ingestion report;
- team source index;
- team-level submission panel;
- generic aggregate acquisition audit;
- single-report-ready overlap audit;
- ready player source index;
- ready overlap report index and timestamp registry.

Deleted:

- normalized player rows;
- player names and injury reasons;
- raw PDFs;
- identity maps;
- player-value rows;
- player boxscores.

## Next boundary

The Wave 2 feature PR must:

1. rebuild the official player panel from the fixed Wave 2 registry;
2. use `ready-player-source-index.csv` semantics so `ready=false` reports are excluded;
3. restrict to the 31 ready player/team overlap times;
4. build the full point-in-time feature chain;
5. apply the frozen T-60 policy;
6. combine Wave 1 and Wave 2 selected panels by `historical_game_id`;
7. deduplicate games appearing in both waves;
8. count the combined independent selected sample.

Only a deduplicated combined count of at least 100 may unlock Expected Minutes Accuracy Audit. Injury Holdout, model training, probability adjustment, and betting claims remain blocked.
