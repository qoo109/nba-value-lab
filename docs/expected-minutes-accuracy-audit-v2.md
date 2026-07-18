# Expected Minutes Accuracy Audit v2 — Predeclared Design

## Roadmap position

This audit remains inside Step 3 of the canonical 2026-07-17 roadmap:

```text
Official injury snapshot backfill
→ 100+ independent feature-ready matchups
→ Expected Minutes Accuracy Audit
→ Injury Feature Walk-forward Holdout
→ Timestamped Odds Acquisition
→ Market Backtest
→ CLV／EV／ROI
→ Betting Decision Layer
```

Accuracy Audit v2 does not begin the Injury Feature Walk-forward Holdout and does not move the project to Timestamped Odds.

## Why v2 exists

Accuracy Audit v1 used a secondary player boxscore archive for target-game labels. It joined only 481 of 1,834 matched selected players, so the v1 result was formally:

```text
AUDIT_EXECUTED_STRUCTURAL_BLOCKED
```

Player Participation Label Layer v1 repaired that label-source gap using NBA Official LiveData final-game boxscores:

```text
176 / 176 official game sources
1,832 / 1,834 matched-player participation joins
99.8909% join rate
2.2901% UNKNOWN rate
0 source-missing games
```

Passing the participation layer made v2 inputs available. It did not make Expected Minutes accurate and did not retroactively convert v1 into a pass.

## Predeclaration order

The v2 policy file was committed before implementation or any v2 accuracy result:

```text
data/expected-minutes-accuracy-audit-v2.json
initial policy commit: 4591c1d682f638cc7186a73f4707c01eea7e9b15
```

The policy preserves:

- every v1 primary numerical accuracy threshold;
- every v1 player-sample-size threshold;
- the frozen 176-game T-60 population;
- the same prior-only Expected Minutes proxy;
- the same naive prior-only baselines;
- the same non-activation boundary.

Only the target-game label source and its structural validation are replaced by the official participation layer.

## Frozen population

```text
176 deduplicated independent games
selection: latest feature-ready snapshot at or before T-60m
waves: Wave 1 and Wave 2
population: players listed in the selected official injury snapshots
```

The selected games, selected publication times, identities, predictions and baselines may not be changed after observing v2 outcomes.

## Official participation labels

```text
PLAYED
EXPLICIT_DNP
INACTIVE_OR_NOT_DRESSED
SOURCE_MISSING
UNKNOWN
```

### Primary role-minutes estimand

Include only rows with:

- official label `PLAYED`;
- positive official actual minutes;
- matched deterministic player identity;
- prior-only Expected Minutes available.

Exclude:

- `EXPLICIT_DNP`;
- `INACTIVE_OR_NOT_DRESSED`;
- `SOURCE_MISSING`;
- `UNKNOWN`;
- missing identity;
- missing Expected Minutes.

This preserves the original estimand:

```text
conditional role minutes given actual appearance
```

### Secondary realized-minutes diagnostic

For classified official labels:

- `PLAYED` uses official actual minutes;
- `EXPLICIT_DNP` uses explicit official zero minutes;
- `INACTIVE_OR_NOT_DRESSED` uses explicit official zero minutes;
- `SOURCE_MISSING` and `UNKNOWN` remain missing.

Status-adjusted realized minutes and play-probability metrics remain diagnostics. They cannot override a structural or primary accuracy failure.

## Preserved structural sample gates

The v1 sample thresholds are not lowered after seeing the v1 or participation-layer results:

```text
combined selected games: exactly 176
games with evaluable played rows: at least 150
selected player snapshot rows: at least 1,500
identity match rate: at least 95%
Expected Minutes coverage: at least 85%
conditional PLAYED rows: at least 500
actual starter rows: at least 150
actual bench rows: at least 200
10+ prior-game rows: at least 400
complete team-game groups: at least 100
```

The current participation layer contains 314 `PLAYED` labels before Expected Minutes and baseline filtering. Therefore the frozen 176-game v2 population may still fail the preserved 500-row primary sample gate.

That possibility is accepted in advance. The gate will not be lowered to manufacture a pass.

## New official-label structural gates

```text
official game-source coverage: 100%
participation-label join rate among matched IDs: at least 95%
UNKNOWN rate among matched IDs: at most 5%
source-missing games: 0
duplicate official game-player rows: 0
team mismatches: 0
invalid participation labels: 0
invalid minutes/label combinations: 0
```

Missing player rows, source failures and `UNKNOWN` labels are never converted to DNP or zero minutes.

## Preserved primary accuracy gates

```text
overall MAE: at most 6.5 minutes
overall RMSE: at most 9.0 minutes
overall median absolute error: at most 5.5 minutes
absolute overall bias: at most 2.0 minutes
MAE improvement vs last prior game: at least 0.25 minutes
MAE improvement vs recent-10 mean: at least 0.0 minutes
actual starter MAE: at most 6.5 minutes
actual bench MAE: at most 7.5 minutes
10+ prior-game MAE: at most 6.25 minutes
complete-team played-role aggregate MAE: at most 18 minutes
absolute complete-team aggregate bias: at most 7 minutes
monitored subgroup absolute bias: at most 4 minutes for groups with 50+ rows
```

## Required reporting

The audit reports:

- overall conditional role-minutes MAE, RMSE, median absolute error and bias;
- starter and bench role metrics;
- 10+ prior-game metrics;
- paired last-game, recent-10 and current-season baselines;
- complete team-game played-role aggregation;
- availability status;
- participation label;
- Expected Minutes method;
- prior-game count band;
- Expected Minutes band;
- days since latest prior game;
- source wave;
- status-adjusted realized-minutes diagnostics;
- status play-probability Brier and Log Loss.

## Decision states

### STRUCTURAL_BLOCKED

One or more point-in-time, source, coverage, sample, duplicate, missingness or privacy gates fail.

Accuracy metrics may be reported descriptively but cannot promote the proxy.

### VALID_NEGATIVE_RESULT

Every structural gate passes, but one or more primary accuracy gates fail.

Expected Minutes remains a research proxy and Injury Holdout design stays blocked.

### ACCURACY_PASS

Every structural and primary accuracy gate passes.

This only unlocks a separate, predeclared Injury Feature Walk-forward Holdout design. It does not execute that holdout and does not activate the model.

## Non-activation boundary

Regardless of the v2 result:

```text
ready_for_injury_feature_walk_forward_holdout = false
ready_for_model_training = false
ready_for_probability_adjustment = false
ready_for_betting_edge_claim = false
formal stake = 0
```

Only an `ACCURACY_PASS` may set:

```text
ready_for_injury_feature_walk_forward_holdout_design = true
```

The next canonical roadmap stage remains blocked until that decision is earned.
