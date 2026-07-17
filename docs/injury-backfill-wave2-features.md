# Injury Backfill Wave 2 — Full Features and Combined Panel

## Purpose

Wave 2 converts the 31-report single-report-ready player/team overlap into the full point-in-time injury feature chain, applies the unchanged frozen T-60 selection policy, and combines the resulting game-level panel with Wave 1.

The objective was not to add nine hand-picked games. It was to determine the deduplicated independent-game count from two calendar-fixed waves.

## Authoritative Wave 2 source input

```text
33 player reports parsed
31 player reports single-report-ready
31 team reports successful
31 ready player/team overlap reports
11 ready overlap dates
```

Only the 31 `ready=true` overlap times entered the feature chain. The two Christmas afternoon/evening reports with `ready=false`, and the three 2/19 download failures, remained excluded without replacement.

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

The combined Workflow used the verified Wave 1 feature Artifact from workflow run:

```text
29595409025
```

Required Wave 1 state:

```text
ready_for_wave1_selected_panel_research = true
selected independent games = 91
ready_for_expected_minutes_accuracy_audit = false
```

Wave 1 was not rebuilt or modified by the Wave 2 feature calculation.

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

This rule was frozen before viewing the combined sample count.

## Verified official result

Verified workflow run:

```text
29596726831
```

### Ready source overlap

```text
player parsed reports: 33
player single-report-ready: 31
team successful reports: 31
ready overlap reports: 31
ready overlap dates: 11
player not-ready reports: 2
```

No player-only or team-only ready times entered the feature chain.

### Historical Gold mapping

| Item | Player panel | Team panel |
|---|---:|---:|
| Games | 122 | 153 |
| Matched games | 122 | 153 |
| Match rate | 100% | 100% |
| Unmatched games | 0 | 0 |
| Duplicate Gold keys | 0 | 0 |

### Player identity

```text
snapshot rows: 2,493
matched player rows: 2,468
high-confidence rows: 2,468
match rate: 98.9972%
high-confidence rate: 98.9972%
unmatched rows: 25
ambiguous rows: 0
fuzzy matches: 0
```

The 25 unmatched rows remained blocked rather than guessed.

### Prior-only Expected Minutes and impact

```text
Expected Minutes rows: 2,281
Player Impact rows: 2,281
Expected Minutes coverage: 91.4962%
Player Impact coverage: 91.4962%
players without prior history: 187
strict prior-date violations: 0
same-day rows excluded: 371
future rows excluded: 42,104
```

Unknown values remained null.

### Long feature panel

```text
122 player-derived independent games
269 long matchup snapshots
538 long team snapshots
212 complete matchup snapshots
163 feature-ready matchup snapshots
31 unique publication times
0 duplicate snapshot rows
0 nonpregame observations
```

The 269 snapshots are longitudinal observations, not independent games.

### Team submission reconciliation

```text
862 reconciled team rows
431 reconciled matchup snapshots
153 independent games represented
212 complete matchup snapshots
163 feature-ready matchup snapshots
324 submission-only team rows added
376 NOT_YET_SUBMITTED
481 SUBMITTED_WITH_PLAYER_ROWS
5 UNKNOWN_NO_PLAYER_ROWS
0 reconciliation errors
0 missing ledgers
0 side errors
0 nonpregame rows
```

No explicit `SUBMITTED_NO_INJURIES` team appeared, so no new explicit zero-burden team was manufactured.

### Frozen Wave 2 T-60 selection

```text
independent games represented: 153
selected independent games: 85
games without selection: 68
selection rate: 55.5556%
incomplete snapshots: 54
feature unavailable: 14
duplicate selected games: 0
```

Diagnostic policies:

```text
latest feature-ready pre-tip: 85
latest feature-ready at or before T-180m: 80
```

Diagnostics remain research-only.

## Combined Wave 1 + Wave 2 result

```text
Wave 1 selected rows: 91
Wave 2 selected rows: 85
raw selected rows: 176
cross-wave duplicate games: 0
identity conflicts: 0
policy conflicts: 0
combined independent games: 176
```

Selected source counts:

```text
wave1: 91
wave2: 85
```

The combined panel contains exactly one row for each of 176 historical games.

## Combined sample decision

```text
minimum Expected Minutes Accuracy Audit gate: 100
combined independent games: 176
minimum gate met: true
initial reliability target: 300 — not met
ideal target: 500 — not met
```

Formal decision:

```text
ready_for_combined_selected_panel_research = true
ready_for_expected_minutes_accuracy_audit = true
ready_for_injury_feature_walk_forward_holdout = false
ready_for_model_training = false
ready_for_probability_adjustment = false
ready_for_betting_edge_claim = false
```

Crossing 100 unlocks only the Expected Minutes Accuracy Audit. It does not validate Expected Minutes, activate injury features, or establish a market edge.

## Quality and privacy

```text
combined validation errors: 0
combined validation warnings: 0
game identity conflicts: 0
selection policy conflicts: 0
duplicate output games: 0
outcomes or market prices used: false
forbidden player-level files retained: 0
```

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

## Next boundary

The next research task is **Expected Minutes Accuracy Audit v1** using the 176-game deduplicated selected sample.

It must evaluate actual target-game minutes with strict point-in-time grouping and must not turn a passing sample-size gate into automatic model activation. Injury-feature holdout remains blocked until the accuracy audit passes its own predeclared gates.
