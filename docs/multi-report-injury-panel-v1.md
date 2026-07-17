# Multi-report Injury Panel v1

## Purpose

Expand the official NBA injury-report pilot from one PDF into a reproducible panel of multiple dates and publication times.

This phase validates source availability, parser stability, publication timestamps, and aggregate coverage. It does not enable model training.

## Registered pilot timestamps

The pilot requests seven official reports:

```text
2023-12-18 08:30 ET
2023-12-18 13:30 ET
2023-12-18 17:30 ET
2024-01-15 08:30 ET
2024-02-12 08:30 ET
2024-03-18 08:30 ET
2024-04-08 08:30 ET
```

The first date tests intraday snapshots. The remaining dates test parser and source stability across the 2023–24 regular season.

The timestamp list is machine-readable in:

```text
data/multi-report-injury-pilot-times.json
```

## Official source

Each timestamp is converted to the official NBA injury-report URL pattern:

```text
https://ak-static.cms.nba.com/referee/injury/Injury-Report_YYYY-MM-DD_HHAP.pdf
```

The official publication time is stored separately from the actual retrieval time. Missing files are recorded as failed requests and are never converted into empty or healthy-team observations.

## Processing

For every successful report:

1. download the official PDF;
2. verify PDF bytes and SHA-256;
3. parse native PDF word coordinates;
4. validate point-in-time timestamps;
5. normalize statuses and teams;
6. retain a temporary player-level CSV for downstream in-workflow joins;
7. write aggregate report provenance and coverage.

The temporary combined panel is sorted by observation time, game, team, and snapshot ID.

## Retained outputs

The retained Artifact contains only:

- multi-report aggregate QA;
- source URL, timestamp, SHA-256 and size;
- per-report row, game, team and player counts;
- per-report validation reports;
- aggregate status counts.

Player names, injury reasons, and normalized player rows are deleted before Artifact upload.

## Ingestion gate

The registered pilot requires:

- at least four successful reports;
- at least three unique report dates;
- at least 300 normalized rows;
- no more than 50% failed requested reports;
- no duplicate snapshot IDs;
- no duplicate source URLs among successful reports;
- every successful report must pass the single-report gate.

A passed gate means the panel may proceed to player identity and prior-only value joins.

```text
ready_for_multi_report_identity_value_join: conditional
ready_for_model_training: false
ready_for_betting_edge_claim: false
```

## Guardrails

- raw PDFs are deleted;
- missing reports are explicit failures;
- a failed report never creates zero injury burden;
- publication timestamps remain point-in-time observations;
- player-level normalized rows are temporary;
- ingestion success alone cannot activate model features.

## Next phase

After the ingestion panel passes:

1. match all snapshots to Gold game IDs;
2. match player names to stable player IDs;
3. calculate prior-only expected minutes and impact at every report time;
4. build status transitions across intraday snapshots;
5. aggregate team injury burden by report time;
6. evaluate incremental value in season holdout folds.
