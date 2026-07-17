# Point-in-time Injury & Lineup Snapshot v1

## Goal

Create a provider-neutral contract for pregame injury and lineup information before any source-specific parser is allowed into the model pipeline.

The contract exists to prevent three common research errors:

1. using an injury update published after tip-off;
2. treating a late confirmed lineup as if it were known at an earlier decision time;
3. attaching current player-value estimates to historical snapshots.

## Primary injury source pilot

The first approved primary source is the NBA Official seasonal Injury Report page:

- <https://official.nba.com/nba-injury-report-2025-26-season/>

The official page publishes timestamped reports throughout the day. Raw PDFs must remain outside the public repository. The public repo may keep only source URL, report time, retrieval time, SHA-256, normalized records, and QA summaries.

Automatic PDF extraction remains disabled until parser quality and source terms are reviewed.

## Record types

### `INJURY_STATUS`

Required raw fields include:

- game and team identity
- player identity
- raw source status and reason
- `source_report_time`
- `observed_at`
- scheduled `commence_time`
- source URL and SHA-256

Normalized availability values:

- `AVAILABLE`
- `PROBABLE`
- `QUESTIONABLE`
- `DOUBTFUL`
- `OUT`
- `INACTIVE`
- `SUSPENDED`
- `UNKNOWN`

### `LINEUP_STATUS`

Normalized lineup roles:

- `CONFIRMED_STARTER`
- `PROJECTED_STARTER`
- `ROTATION`
- `BENCH`
- `INACTIVE`
- `UNKNOWN`

No pregame lineup provider is approved yet. Postgame box scores must not be backfilled as pregame knowledge.

## Time rules

Every accepted row must satisfy:

```text
source_report_time <= observed_at < commence_time
```

Optional player-value fields must also satisfy:

```text
player_value_asof <= observed_at
```

Rows that fail these rules are excluded and the file is not ready for feature construction.

## Player-value fields

The schema supports optional point-in-time player values:

- `prior_expected_minutes`
- `prior_impact_estimate`
- `player_value_asof`
- `player_value_version`

These fields must be produced only from information available before the snapshot. The validator does not create player values; it only verifies bounds and timestamps.

## Conflict handling

Within the same source file, game, team, player, and record type, contradictory normalized values are a hard failure.

Exact duplicate rows are removed and counted.

A confirmed lineup snapshot should contain exactly five confirmed starters per team. Other counts produce warnings because partial reports may exist, but they cannot be treated as complete confirmed lineups.

## Files

- JSON Schema: `schemas/injury-lineup-snapshot-v1.schema.json`
- CSV template: `data/templates/injury-lineup-snapshot-v1.csv`
- Source registry: `data/injury-lineup-source-registry.json`
- Validator: `scripts/validate_injury_lineup_snapshots.py`

## Usage

```bash
python scripts/validate_injury_lineup_snapshots.py \
  --input injury-lineup-snapshots.csv \
  --output-dir out/injury-lineup-v1
```

Outputs:

- `injury-lineup-snapshots-normalized.csv`
- `injury-lineup-validation-report.json`

## Activation gates

Passing schema validation means only that the file is safe for point-in-time feature construction.

It does **not** mean:

- historical coverage is sufficient;
- the source is approved for automated collection;
- player-value estimates are valid;
- the records are ready for model training;
- a betting edge exists.

The next implementation step is a manual official-PDF pilot covering a small set of game days, followed by player and game matching QA.
