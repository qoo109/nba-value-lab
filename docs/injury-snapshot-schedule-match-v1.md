# Injury Snapshot Schedule Match v1

## Purpose

Map normalized official NBA injury-report game keys to the historical NBA Value Lab `game_id` used by Gold and Silver.

The official injury importer creates a deterministic temporary key:

```text
official:YYYY-MM-DD:AWAY@HOME
```

The schedule matcher joins this key to `gold_matchup_features` using:

```text
game_date + away_team_abbr + home_team_abbr
```

The historical Gold game ID originates from the audited Silver schedule and is therefore the identifier required for later feature construction.

## Exact matching only

The pilot does not use fuzzy dates, team-name similarity, timezone shifts or nearest-game guesses.

A report is ready for the historical game-ID join only when:

- every official game key is syntactically valid;
- every player row agrees with the home/away sides encoded by the official key;
- every unique official game has exactly one historical schedule match;
- no Gold schedule key is duplicated;
- every snapshot row belongs to a matched game.

Any unmatched or duplicated key is a hard failure.

## Inputs

### Normalized injury snapshot CSV

Produced by:

```bash
PYTHONPATH=scripts python scripts/import_official_nba_injury_report.py \
  --report-time 2023-12-18T08:30:00-05:00 \
  --retain-normalized \
  --output-dir out/injury-import
```

### Historical Gold database

The workflow consumes the `historical-gold-multiseason` Artifact and reads only:

- `game_id`
- `game_date`
- `home_team_abbr`
- `away_team_abbr`

from `gold_matchup_features`.

## Validated historical fixture

The official 2023-12-18 08:30 ET report was matched against the five-season Gold schedule.

Verified result:

- 118 normalized injury rows
- 11 unique games with player status rows
- 11 historical game IDs matched
- 118 player rows assigned to matched games
- 100% exact game match rate
- 0 unmatched games
- 0 duplicated Gold schedule keys
- 0 home/away side errors
- 5,824 Gold schedule rows available to the matcher

Matched games:

| Official key | Historical game ID |
|---|---:|
| `official:2023-12-18:BKN@UTA` | `22300357` |
| `official:2023-12-18:CHA@TOR` | `22300354` |
| `official:2023-12-18:CHI@PHI` | `22300351` |
| `official:2023-12-18:DAL@DEN` | `22300356` |
| `official:2023-12-18:DET@ATL` | `22300352` |
| `official:2023-12-18:HOU@CLE` | `22300349` |
| `official:2023-12-18:LAC@IND` | `22300350` |
| `official:2023-12-18:MEM@OKC` | `22300355` |
| `official:2023-12-18:MIN@MIA` | `22300353` |
| `official:2023-12-18:NYK@LAL` | `22300359` |
| `official:2023-12-18:WAS@SAC` | `22300358` |

This fixture is ready for the historical game-ID join. It is not yet ready for player identity joining or model training.

## Usage

```bash
python scripts/validate_injury_snapshot_schedule_match.py \
  --snapshot-csv out/injury-import/validation/injury-lineup-snapshots-normalized.csv \
  --gold historical-gold-multiseason.sqlite.gz \
  --output-dir out/injury-schedule-match
```

Outputs:

- `injury-snapshot-schedule-match-report.json`
- `injury-snapshot-game-id-map.csv`

The game mapping contains no player names or injury reasons.

## Artifact controls

The live workflow temporarily retains normalized player rows only long enough to perform the schedule join. It deletes the player-level CSV before Artifact upload.

The Artifact contains:

- aggregate official import report;
- aggregate snapshot-contract validation report;
- aggregate schedule-match report;
- game-level official-to-historical ID mapping.

## Activation boundary

A perfect game-ID match does not establish player identity quality or model readiness.

The next required QA layers are:

1. player-name normalization and historical player-ID matching;
2. multiple official reports across different dates and publication times;
3. cross-season PDF layout sampling;
4. status-change sequencing within the same game;
5. point-in-time player-value joins.
