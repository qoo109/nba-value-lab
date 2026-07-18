# Wyatt SQLite Real File Audit v1

## Formal outcome

```text
STRUCTURAL_BLOCKED
```

The supplied SQLite file passed the header and integrity checks, but it does not satisfy the frozen 2023-24 qualification contract.

## Aggregate findings

```text
integrity_check: ok
tables: 16
views: 0
total table rows: 14,060,690
latest game date: 2023-06-12
2023-24 games: 0
```

The accompanying metadata describes 235 cataloged outputs and current-season coverage. The inspected SQLite contains 16 tables and ends after the 2022-23 season.

Available legacy roles:

- game identity and team boxscore: `game`, `game_summary`, `line_score`;
- play-by-play: `play_by_play`;
- inactive-player records: `inactive_players`.

No player game boxscore table is present.

## Duplicate diagnostics

```text
game rows: 65,698
distinct game IDs: 65,642
duplicate game_id groups: 56

PBP rows: 13,592,899
distinct PBP game IDs: 29,818
duplicate (game_id, eventnum) groups: 7,360
```

## Gate result

The minimum 1,000-game 2023-24 population is not present. Therefore identity, score, team-boxscore, player-boxscore, and PBP match-rate gates cannot be promoted.

```text
secondary source qualified: false
existing Silver replacement: false
existing Gold replacement: false
formal stake: 0
```

A new audit requires a bundle whose actual schema and season coverage match its published metadata. The current file can remain only as a legacy exploratory cross-check candidate.
