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

Only publication times that succeeded in both pipelines entered the feature chain.

Script:

```text
scripts/filter_injury_panels_to_acquisition_overlap.py
```

The filter verifies that player and team observed timestamps agree and writes:

```text
overlap-player-injury-panel.csv       temporary player-level data
overlap-team-submission-panel.csv     team-level data
overlap-report-index.csv              report provenance
overlap-filter-report.json            aggregate QA
```

Player-only or team-only successful reports were excluded. Failed registry times were not replaced.

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

- overlap reports and dates meet the acquisition minimum;
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
- team submission reconciliation has no missing-ledger, side, or structural errors;
- frozen selection has at most one row per independent game;
- outcomes and market prices are absent from selection;
- player-level files are deleted before Artifact upload.

## Verified official result

Verified workflow run:

```text
29594902839
```

### Successful overlap

| Item | Result |
|---|---:|
| Overlap reports | 31 |
| Overlap dates | 12 |
| Filtered player rows | 2,657 |
| Filtered team rows | 832 |
| Player-ingestion games | 127 |
| Team-ledger games | 162 |
| Observed-at mismatches | 0 |
| Rows outside overlap | 0 |

The player and team panels were restricted to exactly the same 31 publication times.

### Historical Gold mapping

| Item | Player panel | Team panel |
|---|---:|---:|
| Games | 127 | 162 |
| Matched games | 127 | 162 |
| Match rate | 100% | 100% |
| Unmatched games | 0 | 0 |
| Duplicate Gold keys | 0 | 0 |

No fuzzy team matching was used.

### Player identity

```text
snapshot rows: 2,657
matched player rows: 2,634
high-confidence rows: 2,634
match rate: 99.1344%
high-confidence rate: 99.1344%
unmatched rows: 23
ambiguous rows: 0
fuzzy matches: 0
```

The 23 unmatched rows remained blocked rather than guessed.

### Prior-only Expected Minutes and impact

```text
feature rows: 2,634
Expected Minutes rows: 2,465
Player Impact rows: 2,465
Expected Minutes coverage: 92.7738%
Player Impact coverage: 92.7738%
players without prior history: 169
strict prior-date violations: 0
same-day rows excluded: 463
future rows excluded: 43,533
```

Unknown values remained null and were not imputed as zero.

### Long feature panel

```text
127 independent player-derived games
286 long matchup snapshots
572 long team snapshots
236 complete matchup snapshots
191 feature-ready matchup snapshots
31 unique publication times
0 duplicate snapshot rows
0 non-pregame observations
```

The long panel is for publication-time transition research. Its 286 snapshots are not 286 independent samples.

### Team submission reconciliation

```text
832 reconciled team rows
416 reconciled matchup snapshots
162 independent games represented
236 complete matchup snapshots
191 feature-ready matchup snapshots
260 submission-only team rows added
305 NOT_YET_SUBMITTED
522 SUBMITTED_WITH_PLAYER_ROWS
5 UNKNOWN_NO_PLAYER_ROWS
0 reconciliation errors
0 missing team ledgers
0 matchup side errors
0 nonpregame rows
```

The Wave 1 source contained no explicit `SUBMITTED_NO_INJURIES` team, so the pipeline created no new explicit zero-burden team.

### Frozen T-60 selection

Primary policy remained:

```text
latest feature-ready snapshot at or before T-60m
```

Result:

```text
independent games represented: 162
selected independent games: 91
games without primary selection: 71
selection rate: 56.1728%
rejected incomplete: 56
rejected feature unavailable: 15
duplicate selected games: 0
```

Diagnostic coverage:

```text
latest feature-ready pre-tip: 91
latest feature-ready at or before T-180m: 88
```

Diagnostics may not replace the Primary policy after outcome review.

## Sample-size decision

```text
minimum activation gate: 100 independent selected games
Wave 1 selected: 91
shortfall: 9
initial reliability: 300
ideal target: 500
```

Wave 1 did **not** reach the minimum gate.

```text
ready_for_wave1_selected_panel_research = true
ready_for_expected_minutes_accuracy_audit = false
ready_for_injury_feature_walk_forward_holdout = false
ready_for_model_training = false
ready_for_probability_adjustment = false
ready_for_betting_edge_claim = false
```

The correct next step is another calendar-fixed acquisition wave. It is not valid to lower the 100-game gate, count repeated snapshots as new games, promote the diagnostic policy, or hand-pick replacement dates.

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

Final privacy check:

```text
forbidden player-level files retained: 0
```

## Decision boundary

The structural research panel is reproducible and safe for selected-panel research. Expected Minutes Accuracy Audit remains blocked at 91/100 independent games, and all downstream model or betting activation remains disabled.
