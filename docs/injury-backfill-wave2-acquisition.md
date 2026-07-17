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

Christmas Day is retained because it belongs to the calendar rule. It may not be removed after observing report availability or feature quality.

## Predeclared acquisition gate

```text
minimum successful player reports: 18
minimum successful team reports: 18
minimum overlapping successful reports: 18
minimum unique overlapping dates: 8
maximum failure rate per pipeline: 50%
```

Mandatory structural and privacy gates:

- all requested timestamps are unique;
- no requested timestamp overlaps Wave 1;
- all dates are Mondays separated by 14 days;
- all registered slots are 08:30／13:30／17:30 ET;
- successful timestamps must belong to the registry;
- no duplicate source timestamps or URLs;
- team submission conflicts equal zero;
- aggregate reports agree with source indexes;
- normalized player rows and raw PDFs are deleted before Artifact upload.

## Workflow

```text
Validate injury backfill wave 2 acquisition
```

The Workflow runs the official player and team-submission pipelines independently against the same 36-report registry, deletes player-level source rows, and then runs the reusable aggregate acquisition audit.

The reusable audit retains the historical JSON decision key:

```text
ready_for_wave1_feature_backfill
```

For Wave 2 this key means only that the current fixed acquisition wave passed the generic feature-backfill gate. It does not merge Wave 1 and Wave 2 and does not activate any model.

## Artifact boundary

Artifact:

```text
injury-backfill-wave2-acquisition
```

Retained:

- aggregate player ingestion report;
- player source index;
- aggregate team ingestion report;
- team source index;
- team-level submission panel;
- aggregate acquisition audit;
- report-level success/failure index.

Deleted:

- normalized player rows;
- player names and injury reasons;
- raw PDFs;
- identity maps;
- player-value rows;
- player boxscores.

## Next boundary

If Wave 2 acquisition passes, a separate feature PR must:

1. restrict to Wave 2 player/team overlap;
2. build the full point-in-time feature chain;
3. apply the frozen T-60 policy;
4. combine Wave 1 and Wave 2 selected panels by `historical_game_id`;
5. deduplicate games appearing in both waves;
6. count the combined independent selected sample.

Only a deduplicated combined count of at least 100 may unlock Expected Minutes Accuracy Audit. Injury Holdout, model training, probability adjustment, and betting claims remain blocked.
