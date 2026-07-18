# NBA Value Lab — Handoff After PR #72

更新日期：2026-07-18（Asia/Taipei）  
Repository：`qoo109/nba-value-lab`  
定位：**Research Candidate / Pre-Market-Backtest**  
正式 Stake：**0**

## Latest verified main before this status sync

```text
7b60dd9b7a35e4dcc2ab2e04ade7409ee6538afe
```

## Latest completed PRs

```text
PR #69 — Historical Secondary Source Qualification v1
PR #70 — Historical Secondary Source Metadata Census v1
PR #71 — Wyatt SQLite File-level Pilot v1 predeclaration
PR #72 — Wyatt SQLite Census Runner v1 implementation
```

## Formal current state

```text
INPUT_FILE_REQUIRED
```

PR #72 completed only the runner implementation and synthetic validation. It did not open or inspect the real Wyatt Walsh SQLite database.

## PR #72 evidence

```text
workflow run: 29651474770
artifact id: 8431589455
digest: sha256:7b11a7847b1085e3ee4f3f9ed69c803321efbc1d9c058671035d58ee1938019b
synthetic table count: 4
SQLite integrity_check: ok
opened read-only: true
input modified: false
raw rows emitted: 0
cross-source audit executed: false
qualification evaluated: false
```

## Runner capabilities

The merged runner now supports:

- `.sqlite`, `.sqlite3`, and `.db` validation;
- frozen 1 MiB–2 GiB size gate;
- SQLite header and SHA-256 checks;
- URI read-only open with `mode=ro` and `immutable=1`;
- `query_only`, `trusted_schema = OFF`, and `integrity_check`;
- aggregate table, column, PK, index, foreign-key, row-count, date-range, and season census;
- heuristic candidate-table detection for games, team boxscores, player boxscores, and PBP;
- aggregate-only output without source rows.

## Next exact execution

The next execution starts only after the user supplies the Wyatt Walsh SQLite file and identifies its provenance.

The real-file audit must preserve the PR #71 gates:

```text
2023-24 reference games >= 1,000
game identity match >= 98%
final score match >= 98%
team boxscore coverage >= 98%
player boxscore coverage >= 95%
PBP game coverage >= 95% when claimed
exact duplicate games = 0
SQLite integrity_check = ok
fuzzy matching = false
```

## Permanent boundary

```text
full SQLite committed to Repository: false
full SQLite uploaded as Artifact: false
raw PBP/player rows in Artifact: 0
existing Silver replacement: false
existing Gold replacement: false
model metrics: false
market metrics: false
formal stake: 0
```

The separate Timestamped Odds line remains paused at `NO_COST_METADATA_BLOCKED`; paid historical odds remain not approved.
