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

## GitHub Run Result — 2026-07-19

```text
workflow run: 29672984966
workflow URL: https://github.com/qoo109/nba-value-lab/actions/runs/29672984966
commit SHA: 2654873d9e823a1e392da55b4b08f0c702abf799
artifact id: 8437932113
artifact digest: sha256:96a87c6b52614ea6f7478e1bdbcc729c7c8eb2347490ca236475444ca5fcc63a
formal outcome: ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE
all core gates passed: true
formal stake: 0
raw rows emitted: 0
raw files emitted: false
```

Observed aggregate comparison:

```text
reference games: 1,230
matched games: 1,230
game identity match rate: 100%
final score match rate: 99.9187%
team boxscore coverage: 100%
team boxscore score match rate: 99.9187%
player boxscore candidate coverage: 100% coverage-only
PBP game coverage: 100%
Eoin pilot games: 1,383
Eoin PBP rows: 18,727,295
```

This run qualifies Eoin for role-limited secondary source use only. It does not
approve player-stat parity, model promotion, market metrics, betting decisions,
or Historical Silver/Gold replacement.

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
