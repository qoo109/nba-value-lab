# Wyatt SQLite Census Runner v1

## Purpose

This runner prepares the file-level inspection step predeclared in PR #71. It can inspect a supplied `.sqlite`, `.sqlite3`, or `.db` file without modifying it and without emitting source rows.

It does not download the Kaggle dataset and does not qualify the source by itself.

## Read-only controls

The runner:

- checks the accepted extension;
- checks the frozen size range;
- verifies the `SQLite format 3` header;
- records the filename, size, and SHA-256;
- opens the database with SQLite URI `mode=ro` and `immutable=1`;
- enables `PRAGMA query_only`;
- runs `PRAGMA integrity_check`;
- compares the file hash before and after the synthetic self-test.

## Aggregate schema census

For each non-internal table it records only aggregate or structural information:

- row count;
- column names and declared types;
- primary-key columns;
- primary-key null and duplicate-group counts;
- indexes;
- foreign keys;
- candidate date ranges;
- candidate season counts and a small set of distinct season labels;
- heuristic role scores for games, team boxscores, player boxscores, and PBP.

No source row values are emitted. The small season-label list is metadata, not game, player, or PBP content.

## Outputs

A real input run writes:

```text
aggregate_schema_report.json
aggregate_coverage_report.json
privacy_safe_schema_sample.json
```

`aggregate_coverage_report.json` remains explicitly incomplete until the deterministic 2023-24 cross-source join is executed. The runner therefore never issues a formal source-qualification outcome.

## Synthetic validation

GitHub Actions creates a temporary four-table synthetic SQLite database and verifies:

- read-only operation;
- integrity check;
- table, column, key, index, foreign-key, date, and season inventory;
- role detection;
- zero raw rows in output;
- zero model or market metrics;
- no Silver or Gold replacement.

The synthetic database is not uploaded. Only aggregate synthetic reports are retained for 14 days.

## Current formal state

Until the real Wyatt Walsh SQLite file is supplied:

```text
INPUT_FILE_REQUIRED
```

The frozen PR #71 qualification gates remain unchanged:

```text
2023-24 reference games >= 1,000
game identity match >= 98%
final score match >= 98%
team boxscore coverage >= 98%
player boxscore coverage >= 95%
PBP game coverage >= 95% when claimed
exact duplicate games = 0
SQLite integrity check = ok
```

## Boundaries

```text
external downloads: 0
real database opened in this PR: false
raw source rows in Artifact: 0
raw SQLite in Artifact: false
existing Silver replacement: false
existing Gold replacement: false
model metrics: false
market metrics: false
formal stake: 0
```
