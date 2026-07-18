# Expected Minutes Accuracy Audit v2

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

Accuracy Audit v2 did not begin the Injury Feature Walk-forward Holdout and did not move the project to Timestamped Odds.

## Why v2 existed

Accuracy Audit v1 used a secondary player boxscore archive for target-game labels. It joined only 481 of 1,834 matched selected players and was formally:

```text
AUDIT_EXECUTED_STRUCTURAL_BLOCKED
```

Player Participation Label Layer v1 repaired that source gap using NBA Official LiveData final-game boxscores:

```text
176 / 176 official game sources
1,832 / 1,834 matched-player participation joins
99.8909% join rate
2.2901% UNKNOWN rate
0 source-missing games
```

Passing the participation layer made v2 inputs available. It did not retroactively convert v1 into a pass.

## Predeclaration order

The v2 policy was committed before implementation or any v2 accuracy result:

```text
data/expected-minutes-accuracy-audit-v2.json
initial policy commit: 4591c1d682f638cc7186a73f4707c01eea7e9b15
```

The policy preserved:

- every v1 primary numerical accuracy threshold;
- every v1 player-sample-size threshold;
- the frozen 176-game T-60 population;
- the same prior-only Expected Minutes proxy;
- the same naive prior-only baselines;
- the same non-activation boundary.

Only the target-game label source and its structural validation changed.

## Frozen population

```text
176 deduplicated independent games
selection: latest feature-ready snapshot at or before T-60m
waves: Wave 1 and Wave 2
population: players listed in the selected official injury snapshots
```

The selected games, publication times, identities, predictions and baselines were not changed after observing outcomes.

## Official participation labels

```text
PLAYED
EXPLICIT_DNP
INACTIVE_OR_NOT_DRESSED
SOURCE_MISSING
UNKNOWN
```

### Primary role-minutes estimand

Included only rows with:

- official label `PLAYED`;
- positive official actual minutes;
- matched deterministic identity;
- prior-only Expected Minutes available.

Excluded:

- `EXPLICIT_DNP`;
- `INACTIVE_OR_NOT_DRESSED`;
- `SOURCE_MISSING`;
- `UNKNOWN`;
- missing identity;
- missing Expected Minutes.

The primary estimand remained:

```text
conditional role minutes given actual appearance
```

### Secondary diagnostics

For classified labels:

- `PLAYED` used official actual minutes;
- `EXPLICIT_DNP` used explicit official zero minutes;
- `INACTIVE_OR_NOT_DRESSED` used explicit official zero minutes;
- `SOURCE_MISSING` and `UNKNOWN` remained missing.

Status-adjusted realized minutes and play-probability metrics were diagnostics only. They could not override primary or structural failure.

## Preserved structural gates

The v1 sample thresholds were not lowered:

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

Official-label gates:

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

Missing player rows, source failures and `UNKNOWN` labels were never converted to DNP or zero minutes.

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

## Official v2 result

Verified workflow run:

```text
29627677190
```

Artifact:

```text
expected-minutes-accuracy-audit-v2
artifact id: 8424436361
digest: sha256:7be8933b6d0aece1cf4dfa1c329dd2d82d75fb37db0f1ffe7f555af26aed1761
```

Formal decision:

```text
STRUCTURAL_BLOCKED
```

### Coverage

```text
combined selected games: 176
games with conditional role rows: 135
selected player snapshot rows: 1,840
identity match rate: 99.6739%
Expected Minutes coverage: 97.1739%
official source coverage: 100%
participation-label join rate: 99.8909%
UNKNOWN rate: 2.2901%
source-missing games: 0
conditional role rows: 313
starter rows: 186
bench rows: 127
explicit DNP rows: 28
inactive or not dressed rows: 1,450
long-history rows: 305
complete team-game groups: 278
complete team-game groups with played rows: 146
```

### Passed structural gates

- exact 176-game frozen population;
- minimum total player-snapshot rows;
- official source coverage;
- identity coverage;
- Expected Minutes coverage;
- participation-label join coverage;
- UNKNOWN-rate limit;
- zero source-missing games;
- starter sample minimum;
- complete team-game-group minimum;
- strict prior-date violations = 0;
- selected-game, audit-row and official game-player duplicates = 0;
- team mismatch and invalid label combinations = 0;
- target labels not used in prediction;
- secondary archive not used as target-game labels;
- missing actuals and missing Expected Minutes not imputed as zero;
- privacy deletion passed.

### Failed preserved structural gates

```text
evaluable games: 135 / 150
conditional role rows: 313 / 500
actual bench rows: 127 / 200
10+ prior-game rows: 305 / 400
```

These gates were known to be at risk before execution and were not lowered after the result.

## Descriptive primary accuracy

All preserved numerical accuracy gates passed on the available primary subset, but the metrics remain descriptive because structural sample gates failed.

```text
overall n: 313
overall MAE: 5.025591 minutes
overall RMSE: 6.631056 minutes
median absolute error: 4.064807 minutes
bias: +0.819810 minutes

starter n: 186
starter MAE: 4.756906 minutes
starter bias: -0.288442 minutes

bench n: 127
bench MAE: 5.419096 minutes
bench bias: +2.442919 minutes

10+ prior-game n: 305
10+ prior-game MAE: 5.033709 minutes

improvement vs last prior game: +1.676415 minutes
improvement vs recent-10 mean: +0.052660 minutes
improvement vs current-season mean: +0.183579 minutes

complete-team played-role groups: 146
team played-role aggregate MAE: 6.579170 minutes
team played-role aggregate bias: +1.970354 minutes
worst monitored subgroup absolute bias: 2.442919 minutes
```

## Secondary diagnostics

```text
classified realized-minutes rows: 1,748
status-adjusted realized-minutes MAE: 2.562937 minutes
status-adjusted realized-minutes RMSE: 5.849351 minutes
status-adjusted realized-minutes bias: -0.191191 minutes

play-probability rows: 1,792
play-probability Brier: 0.048751
play-probability Log Loss: 0.252880

complete-team realized groups: 278
team realized-minutes MAE: 7.893796 minutes
team realized-minutes bias: -0.682920 minutes
```

These results do not validate the status weights and are not promotion gates.

## Decision boundary

```text
expected_minutes_accuracy_audit_v2_passed = false
ready_for_injury_feature_walk_forward_holdout_design = false
ready_for_injury_feature_walk_forward_holdout = false
ready_for_model_training = false
ready_for_probability_adjustment = false
ready_for_betting_edge_claim = false
formal stake = 0
```

The official participation-label problem is repaired. The remaining blocker is independent-sample sufficiency for the preserved Expected Minutes audit population.

## Next canonical task

The frozen v2 policy requires exactly 176 games and is now a completed historical result. It may not be edited after observing the outcome.

The project remains inside Steps 1–3 of the 2026-07-17 roadmap:

```text
expand additional official injury snapshots
→ apply the same frozen T-60 selection policy
→ combine and deduplicate independent games
→ target approximately 280–300 selected games
→ predeclare a new expanded-sample Expected Minutes Accuracy Audit policy
→ rerun the audit
```

The approximate 280–300 target is driven by the preserved sample deficits, especially 313／500 conditional played rows and 127／200 bench rows. It is not a lowered threshold and does not replace the canonical roadmap.

Until a future expanded-sample audit passes:

```text
Injury Feature Walk-forward Holdout remains blocked
Timestamped Odds execution does not begin
Market Backtest does not begin
```
