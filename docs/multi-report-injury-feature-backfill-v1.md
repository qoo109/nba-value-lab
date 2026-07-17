# Multi-report Injury Feature Backfill v1

## Purpose

Convert the official multi-report injury ingestion panel into two point-in-time research tables without treating repeated publication times as independent games:

1. **Long panel** — one matchup row for every `(historical_game_id, observed_at)`.
2. **Selected panel** — at most one predeclared snapshot per independent game.

This phase does not train a model or adjust probabilities.

## Frozen primary policy

The primary policy is stored in:

```text
data/injury-snapshot-selection-policy-v1.json
```

It is frozen before any outcome or market join:

```text
latest feature-ready snapshot at or before T-60m
```

Requirements:

- both teams have snapshot rows;
- both teams meet expected-minutes feature coverage;
- observation is at least 60 minutes before tip-off;
- observation is strictly before tip-off;
- no fallback to an incomplete or later snapshot;
- latest eligible `observed_at` wins.

A missing team, `Not Yet Submitted`, missing feature coverage, or no eligible T-60 snapshot results in **no selection**. Missing is never converted to healthy or zero burden.

## Diagnostic policies

The configuration also reports coverage for:

- latest feature-ready pre-tip snapshot;
- latest feature-ready snapshot at or before T-180m.

These are diagnostics only. They may not replace the primary policy after outcomes are reviewed.

## Long panel

The long builder groups by:

```text
historical_game_id + observed_at + team_abbr
```

It reuses the existing deterministic identity and prior-only player-value layers, but does not modify the single-report Team Injury Burden v1 builder.

Outputs:

```text
multi-report-team-injury-burden-long.csv
multi-report-matchup-injury-burden-long.csv
multi-report-injury-feature-report.json
```

The long panel is suitable for publication-time transition research. It is not a holdout sample table.

## Selected panel

Outputs:

```text
selected-matchup-injury-burden.csv
snapshot-selection-audit.csv
snapshot-selection-report.json
```

`selected-matchup-injury-burden.csv` has at most one row per `historical_game_id`.

Multiple snapshots from the same game count as one independent game regardless of how many publication times exist.

## Sample-size gates

```text
minimum activation: 100 independent feature-ready games
initial reliability: 300 independent games
ideal target: 500 independent games across multiple months or seasons
```

Reaching 100 only permits a holdout experiment. It does not activate model training, probability adjustment, or betting claims.

## Verified live pilot

Workflow run:

```text
29590632622
```

Official source ingestion:

- requested reports: 7;
- successful reports: 6;
- failed reports: 1;
- unique report dates: 4;
- normalized player rows: 654;
- ingestion-covered games: 41;
- duplicate snapshot rows: 0.

The failed 2024-04-08 08:30 ET report contained 28 `Not Yet Submitted` team rows and no player status rows. It remained an explicit failed report and did not create healthy-team observations.

Gold and identity alignment:

- Gold game matches: 41 / 41;
- matched snapshot rows: 654 / 654;
- player IDs matched: 649 / 654, or 99.2355%;
- high-confidence player IDs: 649;
- ambiguous identities: 0;
- unmatched identities: 5, all with `OUT` status;
- fuzzy and nearest-name matching: 0.

Prior-only player values:

- expected-minutes rows: 606 / 654, or 92.6606%;
- player-impact rows: 606 / 654, or 92.6606%;
- players without prior history: 43;
- same-day source rows excluded: 131;
- future source rows excluded: 12,355;
- strict prior-date violations: 0;
- unknown values remained null.

Long panel:

- independent games: 41;
- long matchup snapshot rows: 63;
- long team snapshot rows: 126;
- complete matchup snapshots: 52;
- feature-ready matchup snapshots: 46;
- unique publication times: 6;
- non-pregame observations: 0;
- duplicate game-time snapshot rows: 0.

Frozen primary T-60 selection:

- independent games available: 41;
- independent games selected: 31;
- primary selection rate: 75.6098%;
- games without a primary selection: 10;
- incomplete snapshot rejections: 8 games;
- feature-unavailable rejections: 2 games;
- duplicate selected games: 0;
- fallback selections: 0.

The latest feature-ready pre-tip and T-180 diagnostic policies also selected 31 games in this pilot. This equality is a coverage observation, not permission to change the frozen primary policy.

The 100-independent-game minimum was **not met**. Injury Walk-forward holdout, model training, probability adjustment, and betting-edge claims remain disabled.

## Coverage limitation requiring another data layer

The current official PDF pipeline retains player status rows but does not yet retain an explicit team submission-completeness ledger. A team with no parsed player row is therefore conservatively treated as incomplete.

This prevents a missing or `Not Yet Submitted` team from being interpreted as healthy, but it also means the selected sample may overrepresent games where both teams listed at least one player.

Before a formal injury holdout, add a point-in-time team submission ledger that can distinguish:

- submitted with listed players;
- submitted with no injuries to report;
- `Not Yet Submitted`;
- parser/source missingness.

Until that distinction exists, `31 selected games` means a safe research panel, not a representative model-training sample.

## Live pilot workflow

```text
Validate multi-report injury feature backfill v1
```

The workflow:

1. rebuilds the official multi-report panel in temporary storage;
2. matches every snapshot to Gold game IDs;
3. imports Gold-validated player boxscores;
4. performs deterministic player identity matching;
5. builds expected minutes and impact using only earlier games;
6. builds the long team and matchup panel;
7. applies the frozen primary policy;
8. deletes player-level rows before Artifact upload;
9. uploads aggregate QA and game/team-level features only.

## Guardrails

- same-day and future boxscores remain excluded;
- observed time must be before tip-off;
- no fuzzy player identity;
- no missing value is filled with zero;
- no outcome or market price enters snapshot selection;
- repeated publication times are not independent samples;
- player names and injury reasons are not retained in the final Artifact;
- model training, probability adjustment, and betting-edge claims remain disabled.
