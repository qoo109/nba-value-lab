# Historical Secondary Source Metadata Census v1

## Formal result

```text
METADATA_READY_DOWNLOAD_NOT_AUTHORIZED
```

Two candidates were reviewed under PR #69. Both have enough public metadata to justify a later file-level pilot, but neither is qualified as a full secondary source yet.

## Candidate results

### Eoin A Moore

Current metadata supports a future pilot for:

- game identity cross-check;
- team boxscore cross-check;
- player boxscore cross-check.

The advanced-stat and PBP roles remain blocked because the current page does not list the previously discussed extended-stat and PBP files as present assets. The page also states that a backend rebuild is in progress.

Formal outcome:

```text
METADATA_READY_DOWNLOAD_NOT_AUTHORIZED
```

### Wyatt Walsh

Current metadata supports a future pilot for:

- game identity cross-check;
- team and player boxscore cross-check;
- PBP coverage cross-check;
- SQLite schema reference.

Freshness remains blocked. The page claims daily updates, while visible Kaggle metadata is materially older. Freshness must be measured from database contents.

Formal outcome:

```text
METADATA_READY_DOWNLOAD_NOT_AUTHORIZED
```

## Why this is not a source qualification pass

The following have not yet been measured:

- exact downloaded file inventory;
- table and column schemas;
- row counts and duplicate counts;
- null key counts;
- date and season coverage;
- game/team identifier semantics;
- final-score agreement;
- 2023-24 overlap with Historical Gold;
- PBP event-order semantics;
- actual advanced-stat definitions.

Therefore:

```text
full secondary source qualified count: 0
existing Silver replacement: false
existing Gold replacement: false
```

## Next exact task

A new PR must run a temporary file-level pilot for the 2023-24 season. It must retain only aggregate QA reports and privacy-safe samples.

The first pilot remains frozen to:

```text
reference games >= 1,000
game identity match rate >= 98%
final score match rate >= 98%
team boxscore coverage >= 98%
player boxscore coverage >= 95%
PBP game coverage >= 95% when claimed
exact duplicate games = 0
```

No fuzzy matching and no replacement of the verified Silver path are allowed.

## Boundary

```text
downloads in this PR: 0
external data calls in workflow: 0
raw rows in Artifact: 0
model retraining: false
model metrics: false
market metrics: false
formal stake: 0
```
