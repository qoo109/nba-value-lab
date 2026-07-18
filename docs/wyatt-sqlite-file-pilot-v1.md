# Wyatt SQLite File-level Pilot v1

## Purpose

Evaluate the Wyatt Walsh NBA SQLite database as a **secondary historical cross-check source** for the existing Bronze/Silver/Gold pipeline.

This policy does not replace `shufinskiy/nba_data`, Historical Silver, or Historical Gold.

## Current formal state

```text
INPUT_FILE_REQUIRED
```

No SQLite file is present in this PR, so no database inspection or coverage result is claimed.

## Accepted input

A future execution PR may use one local SQLite-compatible file with one of these extensions:

```text
.sqlite
.sqlite3
.db
```

The execution must record:

- source filename;
- file size;
- SHA-256;
- SQLite header validation;
- read-only open result;
- SQLite integrity check result.

The raw database must not be committed or uploaded as an Artifact.

## Frozen schema census

The file-level pilot must report only aggregate structure and QA:

- tables and columns;
- primary keys, indexes, and foreign keys;
- row counts;
- null key counts;
- exact duplicate counts;
- date and season coverage;
- game/team identifier semantics;
- PBP event ordering semantics.

## Frozen 2023-24 cross-source audit

Reference source:

```text
existing verified Historical Gold and Silver
```

Matching must be deterministic:

```text
official_game_id
or
game_date + home_team + away_team + final_score
```

No fuzzy matching is allowed.

Qualification gates:

```text
reference games >= 1,000
game identity match rate >= 98%
final score match rate >= 98%
team boxscore coverage >= 98%
player boxscore coverage >= 95%
PBP game coverage >= 95% when PBP is claimed
exact duplicate games = 0
SQLite integrity check = ok
```

## Allowed outputs

```text
aggregate_schema_report.json
aggregate_coverage_report.json
privacy_safe_schema_sample.json
```

Forbidden outputs include the full SQLite database, raw PBP rows, raw player rows, and public republication of source data.

## Formal outcomes

```text
INPUT_FILE_REQUIRED
STRUCTURAL_BLOCKED
ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE
SECONDARY_SOURCE_REJECTED
```

## Current boundary

```text
input file present: false
database opened: false
raw rows in Artifact: 0
existing Silver replacement: false
existing Gold replacement: false
model retraining: false
model metrics: false
market metrics: false
formal stake: 0
```
