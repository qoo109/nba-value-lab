# Injury Backfill Wave 1 — Acquisition Audit

## Purpose

Wave 1 expands the official injury-report source coverage without selecting dates from outcomes, market prices, injury severity, or feature availability.

This stage answers only:

> Can a fixed calendar sample of historical official NBA injury reports be acquired, parsed, and audited with enough provenance coverage to justify a full feature backfill?

It does not build a trainable sample, run a holdout, change probabilities, or claim betting value.

## Calendar-fixed registry

Registry:

```text
data/multi-report-injury-backfill-wave1-times.json
```

The registry was fixed before inspecting Wave 1 results:

```text
season: 2023-24
weekday: Monday
cadence: every 14 days
slots: 08:30 / 13:30 / 17:30 ET
start: 2023-11-06
end: 2024-04-08
dates: 12
candidate reports: 36
```

Unavailable or structurally rejected official PDFs remain failed observations. They may not be replaced by dates selected after seeing data quality, outcomes, market prices, or feature coverage.

## Predeclared acquisition gate

```text
minimum successful player reports: 18
minimum successful team reports: 18
minimum overlapping successful reports: 18
minimum unique overlapping dates: 8
maximum failure rate per pipeline: 50%
```

Additional mandatory gates:

- requested timestamps are unique;
- registered calendar policy is internally consistent;
- successful source timestamps are a subset of the registry;
- provenance source URLs are not duplicated;
- team submission conflicts equal zero;
- aggregate reports agree with source indexes;
- player-level normalized rows are deleted before Artifact upload.

These thresholds were not changed after seeing the Wave 1 results.

## Acquisition pipelines

Two official-source pipelines run independently against the same registry:

1. **Player report pipeline**
   - official PDF download;
   - native coordinate parser;
   - normalized player status rows in temporary storage;
   - aggregate source index and QA report.

2. **Team submission pipeline**
   - official PDF download;
   - game/team submission context;
   - `SUBMITTED_WITH_PLAYER_ROWS`;
   - `SUBMITTED_NO_INJURIES`;
   - `NOT_YET_SUBMITTED`;
   - `UNKNOWN_NO_PLAYER_ROWS`.

Independent ingestion is intentional. The audit measures whether the two pipelines agree on report availability and publication-time coverage.

## Aggregate audit

Script:

```text
scripts/audit_injury_backfill_wave.py
```

Outputs:

```text
injury-backfill-wave-audit.json
injury-backfill-wave-report-index.csv
```

The report index contains only report-level provenance and success/failure states. It does not contain player names or injury reasons.

The audit records:

- player successful reports and dates;
- team successful reports and dates;
- overlapping successful reports and dates;
- failure rates;
- normalized row and independent game coverage;
- team submission status counts;
- missing report timestamps;
- source-index duplicates;
- structural conflicts;
- sensitive file deletion status.

## Verified official result

Verified workflow run:

```text
29594037731
```

### Report availability

| Item | Result |
|---|---:|
| Candidate reports | 36 |
| Calendar dates | 12 |
| Player pipeline successes | 34 |
| Team pipeline successes | 33 |
| Overlapping successes | 31 |
| Player successful dates | 12 |
| Team successful dates | 12 |
| Overlapping successful dates | 12 |
| Player failure rate | 5.56% |
| Team failure rate | 8.33% |

Every predeclared acquisition threshold passed.

### Source coverage

| Item | Result |
|---|---:|
| Temporary normalized player rows | 2,942 |
| Player-report unique games | 131 |
| Team submission rows | 888 |
| Team-ledger unique games | 162 |
| `SUBMITTED_WITH_PLAYER_ROWS` | 522 |
| `NOT_YET_SUBMITTED` | 361 |
| `UNKNOWN_NO_PLAYER_ROWS` | 5 |
| Team submission conflicts | 0 |

The player and team game counts are ingestion coverage, not selected independent model samples.

### Fixed failed report times

Player pipeline failures:

```text
2024-04-08T08:30:00-04:00
2024-04-08T13:30:00-04:00
```

Both official reports contained only `NOT YET SUBMITTED` team contexts and no player status rows. They remain failed player observations; the team submission pipeline retains the unsubmitted states.

Team pipeline failures:

```text
2024-01-01T17:30:00-05:00
2024-01-15T13:30:00-05:00
2024-01-15T17:30:00-05:00
```

These reports failed the team parser's strict pre-tip context QA. They remain fixed failures and were not replaced. The full feature backfill may use only publication times that passed both pipelines unless a separate parser-improvement PR revalidates the same fixed registry.

### Quality and privacy gates

```text
duplicate requested timestamps: 0
duplicate player source times: 0
duplicate team source times: 0
duplicate player source URLs: 0
duplicate team source URLs: 0
unexpected successful timestamps: 0
team submission conflicts: 0
forbidden player-level files retained: 0
registry errors: 0
aggregate/source-index crosscheck failures: 0
```

The latest Artifact reproduced the first run's core coverage values.

## Artifact boundary

Artifact:

```text
injury-backfill-wave1-acquisition
```

Retained:

- aggregate player ingestion report;
- player source index;
- aggregate team ingestion report;
- team source index;
- team-level submission panel;
- acquisition audit JSON;
- report-level acquisition index.

Deleted before audit and Artifact upload:

- normalized player rows;
- per-report player status CSVs;
- player identity maps;
- player value rows;
- player boxscores;
- raw PDFs.

## Decision boundary

Wave 1 passed:

```text
ready_for_wave1_feature_backfill = true
```

It remains false for:

```text
ready_for_model_training
ready_for_probability_adjustment
ready_for_betting_edge_claim
```

The next phase must use the fixed successful overlap and separately rebuild:

- Gold game mapping;
- deterministic player identity;
- prior-only expected minutes;
- player impact proxy;
- team injury burden;
- team submission reconciliation;
- the already frozen T-60 selected panel.

The independent-game sample gate remains:

```text
minimum holdout start: 100 selected feature-ready games
initial reliability: 300 games
ideal target: 500 games across months or seasons
```

Passing acquisition does not establish how many of the 131 player-ingestion games will survive identity, expected-minutes, completeness, and frozen T-60 selection gates.
