# Injury Backfill Wave 1 — Full Feature Backfill

## Purpose

This phase converts the calendar-fixed Wave 1 acquisition into the same point-in-time injury feature chain validated by the pilot.

It does not change the acquisition registry or the frozen snapshot-selection policy.

## Source intersection

Wave 1 acquisition produced:

```text
34 successful player reports
33 successful team reports
31 successful overlap reports
12 overlap dates
```

Only publication times that succeeded in both pipelines may enter the feature chain.

Script:

```text
scripts/filter_injury_panels_to_acquisition_overlap.py
```

The filter verifies that player and team observed timestamps agree and writes:

```text
overlap-player-injury-panel.csv       temporary player-level data
overlap-team-submission-panel.csv     team-level data
overlap-report-index.csv              report provenance
overlap-filter-report.json             aggregate QA
```

Player-only or team-only successful reports are excluded from this phase. Failed registry times are not replaced.

## Feature chain

```text
fixed acquisition overlap
→ Historical Gold schedule mapping
→ deterministic player identity
→ prior-only expected minutes
→ prior-only player impact proxy
→ long team and matchup injury burden
→ team submission reconciliation
→ frozen T-60 selection
→ final aggregate audit
```

## Structural gates

The final audit requires:

- all overlap reports and dates meet the acquisition minimum;
- player and team games match Historical Gold at 100%;
- no unmatched games or duplicate Gold schedule keys;
- player identity match rate at least 95%;
- high-confidence identity rate at least 90%;
- ambiguous identity rows equal zero;
- fuzzy edit-distance matching remains disabled;
- Expected Minutes and impact coverage at least 85%;
- strict prior-date violations equal zero;
- same-day and future rows remain excluded;
- feature observations are strictly pregame;
- team submission reconciliation has no missing ledger, side, or structural errors;
- frozen selection has at most one row per independent game;
- outcomes and market prices are absent from selection;
- player-level files are deleted before Artifact upload.

## Sample-size decisions

```text
minimum activation gate: 100 independent selected games
initial reliability: 300
ideal target: 500
```

If Wave 1 reaches 100 selected games, it unlocks only:

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

Expected Minutes Accuracy Audit remains a required upstream gate before an injury holdout.

## Artifact boundary

Artifact:

```text
injury-backfill-wave1-features
```

Retained:

- aggregate source and overlap reports;
- report-level provenance indexes;
- Gold game maps;
- aggregate identity and player-value QA;
- team/matchup long features;
- team submission reconciliation QA;
- frozen selected game-level panel;
- final aggregate audit.

Deleted:

- player names and injury reasons;
- overlap player panel;
- normalized source player rows;
- player identity map;
- player-value rows;
- player boxscores;
- raw PDFs.

## Decision boundary

A green workflow means the structural research panel is reproducible. The final Artifact must still be read to determine the selected independent-game count and which next gate, if any, is unlocked.
