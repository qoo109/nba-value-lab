# Injury Backfill Wave 2 — Full Features and Combined Panel

## Purpose

Wave 2 converts the 31-report single-report-ready player/team overlap into the full point-in-time injury feature chain, applies the unchanged frozen T-60 selection policy, and combines the resulting game-level panel with Wave 1.

The primary objective is not to add nine hand-picked games. It is to determine the deduplicated independent-game count from two calendar-fixed waves.

## Authoritative Wave 2 source input

Wave 2 acquisition produced:

```text
33 player reports parsed
31 player reports single-report-ready
31 team reports successful
31 ready player/team overlap reports
11 ready overlap dates
```

Only the 31 `ready=true` overlap times enter the feature chain. The two Christmas afternoon/evening reports with `ready=false`, and the three 2/19 download failures, remain excluded without replacement.

## Wave 2 feature chain

```text
fixed Wave 2 registry
→ single-report-ready player/team overlap
→ Historical Gold game mapping
→ deterministic player identity
→ prior-only Expected Minutes and impact
→ long injury burden panel
→ team submission reconciliation
→ frozen latest-feature-ready-at-or-before-T-60 selection
→ Wave 2 aggregate feature audit
```

## Wave 1 provenance

The combined Workflow downloads the verified Wave 1 feature Artifact from workflow run:

```text
29595409025
```

It requires the Wave 1 final audit to report:

```text
ready_for_wave1_selected_panel_research = true
selected independent games = 91
ready_for_expected_minutes_accuracy_audit = false
```

Wave 1 is not rebuilt or modified by the Wave 2 feature calculation.

## Combined game policy

Script:

```text
scripts/combine_selected_injury_waves.py
```

Deduplication key:

```text
historical_game_id
```

If a game appears in multiple waves:

1. game date, home team, away team, and commence time must agree;
2. both rows must use the frozen Primary policy;
3. both rows must be complete, feature-ready, pregame, and at least T-60;
4. the later eligible `observed_at` is retained;
5. an exact observed-time tie uses wave name only as a deterministic final tie-break;
6. identity or policy conflicts block the combined panel.

This rule is frozen before viewing the combined sample count.

## Combined sample gate

```text
minimum Expected Minutes Accuracy Audit gate: 100 independent games
initial reliability target: 300
ideal target: 500
```

A combined count of at least 100 may unlock only:

```text
ready_for_expected_minutes_accuracy_audit = true
```

It does not unlock:

```text
ready_for_injury_feature_walk_forward_holdout
ready_for_model_training
ready_for_probability_adjustment
ready_for_betting_edge_claim
```

Expected Minutes Accuracy Audit must still pass before an injury-feature holdout can be designed.

## Workflow

```text
Validate injury backfill wave 2 features
```

The Workflow:

1. downloads Historical Gold;
2. downloads the verified Wave 1 selected Artifact;
3. rebuilds Wave 2 from the fixed registry;
4. filters to the single-report-ready player/team overlap;
5. builds Wave 2 point-in-time features;
6. deletes all player-level data;
7. audits Wave 2 structural readiness;
8. combines Wave 1 and Wave 2 by historical game;
9. uploads Wave 2 and combined aggregate outputs.

## Artifact boundary

Artifact:

```text
injury-backfill-wave2-features
```

Retained:

- ready overlap reports and indexes;
- Historical Gold game maps;
- aggregate identity and player-value QA;
- reconciled team/matchup features;
- Wave 2 selected game-level panel;
- Wave 2 aggregate feature audit;
- combined selected game-level panel;
- combined deduplication audit and decision report.

Deleted:

- player names and injury reasons;
- source player panels;
- player identity maps;
- player-value rows;
- player boxscores;
- raw PDFs.

The final Artifact must be read before deciding whether the 100-game Accuracy Audit gate was reached.
