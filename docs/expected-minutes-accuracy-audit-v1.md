# Expected Minutes Accuracy Audit v1

## Purpose

The combined Wave 1＋Wave 2 selected panel contains 176 independent games and therefore meets the minimum sample gate for an Expected Minutes Accuracy Audit.

This audit asks:

> Does the prior-only Expected Minutes proxy estimate the role minutes of listed injury-report players accurately enough to justify designing an injury-feature holdout?

It does not test whether the injury feature improves win probabilities, beats Closing Market, or produces betting value.

## Frozen evaluation population

```text
176 deduplicated independent games
selection policy: latest feature-ready snapshot at or before T-60m
source waves: Wave 1 and Wave 2
population: players listed in each selected official injury snapshot
```

Target-game actual minutes are labels only. They may not update Expected Minutes, player identity, source selection, or any point-in-time feature.

## Primary estimand

```text
conditional role minutes given actual appearance
```

Include:

- player identity matched;
- prior-only Expected Minutes available;
- target-game boxscore row found;
- actual minutes greater than zero.

Exclude from the primary metric:

- explicit target-game DNP rows;
- missing target-game boxscore rows;
- missing player identity;
- missing Expected Minutes.

DNP and missing rows are not silently imputed as zero.

## Secondary diagnostics

### Status-adjusted realized minutes

```text
Expected Minutes × (1 - status unavailability weight)
```

Compared with actual target-game minutes, including explicit DNP zero rows.

### Status play probability

```text
1 - status unavailability weight
```

Compared with the actual played／DNP label using Brier and Log Loss.

Status weights remain research assumptions. Secondary diagnostics cannot override failure of the primary Expected Minutes gates.

## Naive prior-only baselines

All baselines use games strictly before the target date:

- last prior played game minutes;
- recent 10 played-game mean;
- current-season played-game mean.

The Expected Minutes proxy must improve MAE by at least 0.25 minutes over last-game minutes and must not be worse than the recent-10 mean on paired rows.

## Predeclared structural gates

```text
combined selected games: exactly 176
minimum games with evaluable player rows: 150
minimum selected player snapshot rows: 1,500
identity match rate: at least 95%
Expected Minutes coverage: at least 85%
actual boxscore join rate among matched IDs: at least 90%
conditional role rows: at least 500
actual starter rows: at least 150
actual bench rows: at least 200
long-history rows (10+ prior games): at least 400
complete team-game groups: at least 100
strict prior violations: 0
duplicate selected games: 0
duplicate accuracy rows: 0
```

## Predeclared primary accuracy gates

```text
overall MAE: at most 6.5 minutes
overall RMSE: at most 9.0 minutes
overall median absolute error: at most 5.5 minutes
absolute overall bias: at most 2.0 minutes
MAE improvement vs last game: at least 0.25 minutes
MAE improvement vs recent-10 mean: at least 0.0 minutes
actual starter MAE: at most 6.5 minutes
actual bench MAE: at most 7.5 minutes
10+ prior-game MAE: at most 6.25 minutes
complete team played-role aggregate MAE: at most 18 minutes
absolute complete-team aggregate bias: at most 7 minutes
monitored subgroup absolute bias: at most 4 minutes for groups with 50+ rows
```

These gates were fixed before the official audit result.

## Required subgroup reporting

- availability status;
- actual starter／bench role;
- Expected Minutes method;
- prior-game count band;
- Expected Minutes band;
- days since latest prior game;
- source wave.

Actual starter／bench and actual target minutes are evaluation-side labels, not prediction inputs.

A 14+ day gap is a schedule-based return candidate, not proof that the player returned from injury.

## Team-level evaluation

For team-game groups where every listed row has:

- matched identity;
- Expected Minutes;
- target-game boxscore row;

the audit reports:

- sum of Expected Minutes for listed players who actually played versus their actual minutes;
- status-adjusted realized minutes versus actual listed-player minutes.

Only the conditional played-role team aggregate belongs to the primary gate. Status-adjusted realized minutes remain diagnostic.

## Temporary data and privacy

The Workflow temporarily rebuilds:

- Wave 1 and Wave 2 player snapshots;
- deterministic identity maps;
- prior-only player-value rows;
- Gold-validated player boxscores;
- deidentified player-level accuracy rows.

Before Artifact upload it deletes:

- player names and injury reasons;
- player snapshot rows;
- identity maps;
- player-value rows;
- player boxscores;
- deidentified player-level accuracy rows;
- raw PDFs.

The retained Artifact contains only aggregate reports and subgroup summaries.

## Official v1 result

Verified workflow run:

```text
29624112057
```

The fixed Wave 1 and Wave 2 source patterns, Gold joins, identity layer, prior-only values, privacy deletion, and deidentified dataset build completed successfully.

### Dataset coverage

```text
combined independent games: 176
selected player snapshot rows: 1,840
identity matched rows: 1,834
identity match rate: 99.6739%
Expected Minutes rows: 1,788
Expected Minutes coverage: 97.1739%
target-game boxscore join rows: 481
boxscore join rate among matched IDs: 26.2268%
actual played rows: 314
explicit DNP rows: 167
missing target-game boxscore rows: 1,359
```

No player name, injury reason, identity map, player-value row, raw boxscore row, or deidentified player-level accuracy row was retained in the final Artifact.

### Structural gates that passed

- exactly 176 selected independent games;
- at least 1,500 player snapshot rows;
- identity match rate;
- Expected Minutes coverage;
- starter sample minimum;
- strict prior-date rule;
- duplicate selected-game rule;
- duplicate accuracy-row rule;
- target-game labels not used in prediction;
- missing actual minutes not imputed as zero;
- missing Expected Minutes not imputed as zero.

### Structural coverage blockers

The following predeclared gates did not pass:

```text
minimum evaluable games: 135 / 150
actual boxscore join rate: 26.2268% / 90%
conditional role rows: 313 / 500
actual bench rows: 127 / 200
long-history rows: 305 / 400
complete team-game groups: 5 / 100
```

The current open player boxscore archive contains many played and explicit DNP rows, but it does not provide complete target-game participation labels for all players listed in the selected official injury snapshots. A missing target-game row cannot safely be converted to DNP or zero minutes.

### Descriptive accuracy only

Among the 313 rows with a matched target-game appearance label, all numerical accuracy thresholds were within the frozen limits:

```text
overall MAE: 5.0258 minutes
overall RMSE: 6.6313 minutes
median absolute error: 4.0650 minutes
bias: +0.8198 minutes
starter MAE: 4.7569 minutes
bench MAE: 5.4196 minutes
10+ prior-game MAE: 5.0339 minutes
MAE improvement vs last prior game: +1.6768 minutes
MAE improvement vs recent-10 mean: +0.0528 minutes
```

These values are **descriptive only**. They may not be promoted into a formal Expected Minutes pass because the structural coverage population is incomplete.

### Decision

```text
status: AUDIT_EXECUTED_STRUCTURAL_BLOCKED
Expected Minutes Accuracy Audit passed: false
ready for Injury Feature Walk-forward Holdout design: false
ready for Injury Feature Walk-forward Holdout: false
ready for model training: false
ready for probability adjustment: false
ready for betting-edge claim: false
```

The next requirement is a complete, point-in-time-compatible player participation label layer that distinguishes:

- played;
- explicit DNP;
- inactive／not dressed;
- missing source coverage.

The v1 gates are not loosened after observing the result.

## Decision boundary

The audit can produce four outcomes:

1. **Pipeline or safety failure** — point-in-time, duplicate, privacy, identity, or source integrity failed; result is invalid.
2. **Structural coverage block** — safety rules passed, but the evaluable label population did not meet the frozen minimums; descriptive metrics are retained but cannot promote the proxy. This is the official v1 outcome.
3. **Valid negative result** — all structural gates passed but one or more accuracy gates failed; Expected Minutes remains a research proxy.
4. **Accuracy pass** — all structural and primary accuracy gates passed; a separate Injury Feature Walk-forward Holdout design may proceed.

Even an accuracy pass does not directly enable:

```text
Injury Feature Walk-forward Holdout execution
model training
probability adjustment
betting-edge claim
```

A separate, predeclared holdout promotion gate remains mandatory.
