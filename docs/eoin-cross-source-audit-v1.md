# Eoin Cross-Source Audit v1

## Purpose

Run a deterministic 2023-24 aggregate-only comparison between the Eoin A Moore
Kaggle dataset and the existing `shufinskiy/nba_data` 2023-24 event-level
reference.

This audit can qualify Eoin as a role-limited secondary source for game
identity, final score, team-score coverage, player-row availability, and PBP
availability. It does not approve replacement of Historical Silver or Gold.

Formal stake remains `0`.

## GitHub Actions

```text
Actions
-> Run Eoin cross-source audit v1
-> Run workflow
```

Default inputs:

```text
dataset_handle: eoinamoore/historical-nba-data-and-player-box-scores
max_download_mb: 600
```

The workflow downloads:

```text
Eoin Kaggle dataset into temporary Actions storage
shufinskiy/nba_data nbastats_2023.tar.xz into temporary Actions storage
```

It uploads only:

```text
eoin-cross-source-run-status.json
eoin_cross_source_audit_report.json
```

## Gates

```text
pilot season: 2023-24
reference games >= 1,000
game identity match rate >= 98%
final score match rate >= 98%
team boxscore coverage >= 98%
player boxscore candidate coverage >= 95%
PBP game coverage >= 95% when claimed
exact duplicate games = 0
fuzzy matching = false
```

## Important Limitation

`shufinskiy/nba_data` is an independent event-level reference, not a complete
independent player boxscore stat source. Therefore player boxscore status is
coverage-only in this audit. A later player-stat parity audit requires a
separate independent player boxscore reference.

## Outcomes

```text
ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE
SECONDARY_SOURCE_REJECTED
AUDIT_INCOMPLETE
```

`ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE` means the source can be used for the
validated roles under the stated limitation. It does not unlock model metrics,
market metrics, ROI, CLV, betting decisions, or Silver/Gold replacement.

`AUDIT_INCOMPLETE` means a required technical check, usually Parquet gameId
metadata access, could not be evaluated in the current runtime.

## Local Self-Test

```bash
python3 scripts/run_eoin_cross_source_audit_v1.py \
  --self-test \
  --output-dir out/eoin-cross-source-self-test
```
