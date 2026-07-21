# User-supplied Legacy Market Archive Cross-source Audit Implementation v1

## Purpose

This offseason implementation converts the frozen PR #105 policy into a deterministic audit runner. Pull-request validation uses synthetic data only and does not read the real user CSV or real Historical Silver/Gold databases.

Expected validation state:

```text
USER_SUPPLIED_LEGACY_MARKET_ARCHIVE_CROSS_SOURCE_AUDIT_IMPLEMENTATION_READY_BUT_REAL_FILE_EXECUTION_DISABLED
```

## Bound policy

```text
data/research/user-supplied-legacy-market-archive-cross-source-audit-predeclaration-v1.json
```

No frozen threshold may be reduced by this implementation.

## Real inputs required later

```text
nba_2008-2026.csv
historical-gold-multiseason.sqlite or .sqlite.gz
combined Historical Silver SQLite containing the games table
```

The candidate CSV must exactly match:

```text
file name: nba_2008-2026.csv
bytes: 2,493,308
SHA-256: 729eb2ead85c14affbb81ae9a4c611fee9790b8dd3d1d7824e1ddba14410a8c4
rows: 24,440
columns: 27
```

A cleaned, enriched or renamed derivative is not accepted under v1. A different file requires a new versioned policy.

## Reference contract

Gold provides matchup identity from `gold_matchup_features`:

```text
game_id
game_date
home_team_abbr
away_team_abbr
```

Silver provides identity and final scores from `games`:

```text
game_id
game_date
season_label
home_team_abbr
away_team_abbr
home_score
away_score
```

Gold and Silver first join by exact `game_id`. Missing or conflicting in-scope reference identity blocks the audit.

## Candidate scope and join

Only rows meeting all conditions enter the comparison:

```text
season in 2020..2024
regular == true
playoffs == false
```

The only candidate-to-reference key is:

```text
game_date + home_team_abbr + away_team_abbr
```

The exact 30-team mapping is inherited from the policy. Fuzzy matching, manual key overrides, many-to-many matching and score-assisted identity repair are prohibited.

## Aggregate output only

The runner emits one compact JSON report with file identity, game counts, match rates, score agreement, season coverage, duplicate counts, team/date errors, gate results and the formal outcome.

It never emits raw candidate rows, raw reference rows, row-level unmatched examples, CSV files, databases or derived tables.

## Outcome rules

```text
invalid policy, manifest, candidate identity or reference structure
  -> USER_SUPPLIED_LEGACY_MARKET_ARCHIVE_CROSS_SOURCE_AUDIT_RESEARCH_BLOCKED

valid inputs with any frozen scientific gate failure
  -> RETAIN_ROLE_LIMITED_LEGACY_MARKET_ARCHIVE_ELIGIBLE

valid inputs with every frozen gate passed
  -> ROLE_LIMITED_LEGACY_MARKET_ARCHIVE_CROSS_SOURCE_VALIDATED
```

The maximum outcome remains a limited historical QA role, not a point-in-time market source.

## Synthetic validation

The workflow generates 5,800 five-season fixture games and verifies:

1. every frozen gate can pass with deterministic matching;
2. an unknown team code fails closed;
3. score agreement below 99% fails its gate;
4. forbidden downstream permission drift blocks execution;
5. a non-matching real file identity blocks execution.

Validation makes no network calls, downloads no external Artifact and reads no real source file.

## Unchanged boundaries

A separate reviewed request is required before real-file execution. Opening/Closing labels, bookmaker or observation-time inference, point-in-time joins, market backtesting, performance metrics, data-layer replacement, model retraining and any non-zero formal Stake remain disabled.
