# Historical Secondary Source Qualification v1

## Purpose

This policy evaluates two secondary historical NBA datasets as possible cross-check sources for the existing Bronze/Silver/Gold pipeline.

It does **not** replace the verified `shufinskiy/nba_data` path and does not download either candidate in this PR.

## Frozen candidates

### Eoin A Moore — NBA Database (1947 - Present)

Dataset page:

`https://www.kaggle.com/datasets/eoinamoore/historical-nba-data-and-player-box-scores`

Metadata observed on 2026-07-18:

- license label: `CC0: Public Domain`;
- currently listed files include `PlayerStatistics.csv`, `TeamStatistics.csv`, `Games.csv`, `LeagueSchedule24_25.csv`, `Players.csv`, and `TeamHistories.csv`;
- the page states that the backend is being rebuilt;
- advanced-stat and full play-by-play assets are goals and are not presumed to be present.

Possible roles are limited to game, team-boxscore, player-boxscore, optional advanced-stat, and optional PBP cross-checks.

### Wyatt Walsh — NBA Database

Dataset page:

`https://www.kaggle.com/datasets/wyattowalsh/basketball`

Metadata observed on 2026-07-18:

- license label: `CC BY-SA 4.0`;
- advertised as a normalized SQLite database;
- page claims 65,000+ games and 13M+ PBP rows;
- the page text claims daily updating, while the visible Kaggle metadata is materially older.

Freshness must therefore be measured from the downloaded database contents rather than from the page description.

## Phase A — metadata-only predeclaration

This PR freezes:

- exactly two candidates;
- source URLs and displayed license labels;
- current file or asset claims;
- known metadata risks;
- future download, schema, coverage, and cross-source gates.

No candidate is presumed qualified.

## Phase B — future download pilot

A separate PR is mandatory before any file is downloaded.

That PR must record:

- source URL;
- retrieval time;
- content length;
- SHA-256;
- safe extraction result;
- exact file inventory;
- aggregate-only QA outputs.

Raw archives, extracted raw data, and full databases must not be committed to the repository. Full inputs may exist only temporarily during a workflow. Only aggregate reports and privacy-safe samples may be uploaded.

## Phase C — schema census

For each candidate, record:

- exact tables/files and columns;
- row counts;
- duplicate counts;
- null key counts;
- date and season coverage;
- game/team identifier semantics;
- PBP event ordering semantics when PBP is claimed;
- definitions of advanced metrics when those metrics are claimed.

Marketing text and page descriptions are not accepted as schema evidence.

## Phase D — 2023-24 cross-source audit

The first pilot season is frozen to `2023-24` and must compare against the existing verified Historical Gold/Silver path.

Deterministic matching only:

```text
official_game_id
or
game_date + home_team + away_team + final_score
```

No fuzzy matching is allowed.

Frozen minimum gates:

```text
reference games >= 1,000
game identity match rate >= 98%
final score match rate >= 98%
team boxscore coverage >= 98%
player boxscore coverage >= 95%
PBP game coverage >= 95% when PBP is claimed
exact duplicate games = 0
```

A candidate may qualify for a limited role without qualifying as a PBP or advanced-stat source. It may not replace the verified Silver source in v1.

## Formal outcomes

```text
METADATA_BLOCKED
METADATA_READY_DOWNLOAD_NOT_AUTHORIZED
DOWNLOAD_PILOT_ELIGIBLE
ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE
SECONDARY_SOURCE_REJECTED
```

## Permanent boundary

```text
downloads in this PR: 0
external data calls in this PR: 0
secrets read in this PR: 0
raw rows in Artifact: 0
model retraining: false
model metrics: false
market metrics: false
existing Silver replacement: false
existing Gold replacement: false
formal stake: 0
```
