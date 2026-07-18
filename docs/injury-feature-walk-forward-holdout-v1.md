# Injury Feature Walk-forward Holdout v1 — Predeclaration

更新日期：2026-07-18  
Roadmap：Step 4  
執行狀態：**Not Executed**

## Purpose

This experiment asks one narrow question:

> Do the frozen point-in-time injury burden features add forward predictive value beyond the existing frozen Logistic＋Elo out-of-fold baseline?

It does not use market odds, does not tune after seeing holdout results, and does not activate a production model or betting layer.

## Predeclaration order

The machine-readable policy is committed before holdout implementation, candidate fitting, or holdout metrics:

```text
data/injury-feature-walk-forward-holdout-v1.json
predeclaration commit: 49560a26cf96b0aafa228416e84253de82e5ca80
```

No threshold, feature, split, candidate formula, penalty, or decision rule may be changed after the holdout result is observed.

## Frozen upstream evidence

### Expected Minutes Accuracy Audit v3

```text
PR #54
merge commit: 28866b168fc6194bea05353b01b120e649adcfd5
formal state: ACCURACY_PASS
official workflow: 29634963247
latest-head validation: 29635392094
```

### Injury panel

```text
PR #51
Wave 1 selected: 91
Wave 2 selected: 85
Wave 3 selected: 117
combined independent games: 293
selection: latest feature-ready at or before T-60m
fallback: none
```

### Frozen baseline predictions

```text
model: walk-forward-v2
workflow run: 29551715399
artifact: model-walk-forward-v2
OOF prediction rows: 3,688
```

Structural inspection before this predeclaration confirmed that all 293 injury-panel games uniquely join the existing 2023–24 OOF predictions with zero date or team mismatch. No candidate performance was calculated.

## Frozen population

```text
season: 2023-24
date range: 2023-10-30 through 2024-04-12
combined selected games: 293
complete snapshots: 293
feature-available games: 293
baseline OOF joins required: 293
```

Multiple publication snapshots for the same game remain one independent game. The deduplication key is `historical_game_id`.

## Chronological folds

No random shuffle is permitted.

### Fold 1 — development forward check

```text
train: 2023-10-30 through 2024-01-31 — 124 games
test:  2024-02-01 through 2024-02-29 — 65 games
```

### Fold 2 — final untouched holdout

```text
train: 2023-10-30 through 2024-02-29 — 189 games
test:  2024-03-01 through 2024-04-12 — 104 games
```

Combined forward test population:

```text
65 + 104 = 169 unique games
```

A test game may never enter its fold's scaler, optimizer, coefficients, thresholds, quartiles, or training metrics.

## Frozen baseline

Primary baseline:

```text
frozen predicted_home_win_probability
from the 2023-24 OOF fold of walk-forward-v2
```

Margin baseline:

```text
frozen predicted_home_margin
```

The prior calibration gate selected the raw Logistic＋Elo probability. No new Platt, Isotonic, intercept correction, or test-fold recalibration is allowed inside this experiment.

## Frozen primary candidate

Candidate name:

```text
bounded_injury_logit_offset_v1
```

Formula:

```text
logit(p_candidate)
= logit(p_baseline)
+ beta_1 × z(weighted unavailable minutes home-minus-away)
+ beta_2 × z(weighted positive absence impact home-minus-away)
```

Only two injury features are permitted:

```text
weighted_unavailable_minutes_home_minus_away
weighted_absence_impact_positive_home_minus_away
```

The deliberately small feature set limits multicollinearity and researcher degrees of freedom. The other existing burden fields remain diagnostic-only and may not be substituted after results are seen.

Positive feature values mean greater home-team burden. Therefore both candidate coefficients are constrained to be non-positive.

Frozen fit settings:

```text
training-fold standardization only
no intercept
baseline logit coefficient fixed at 1.0
L2 alpha: 0.05
coefficient bounds: -0.5 to 0.0
optimizer: L-BFGS-B
initial coefficients: 0.0, 0.0
max iterations: 2,000
tolerance: 1e-9
random seed: 20260718
hyperparameter tuning: none
```

No missing injury feature may be filled with zero. A missing or zero-variance feature structurally blocks the experiment.

## Secondary margin diagnostic

A bounded residual margin candidate may be fit with the same two standardized injury features:

```text
candidate margin = frozen baseline margin + X × gamma
coefficient bounds: -6.0 to 0.0
L2 alpha: 0.05
```

Margin results are diagnostic and cannot override a failed probability promotion gate.

## Metrics

Primary:

```text
Log Loss
Brier Score
```

Secondary:

```text
AUC
Accuracy
Calibration intercept
Calibration slope
10-bin equal-frequency ECE
Average and maximum absolute probability shift
Margin MAE
Margin RMSE
```

Paired game-level bootstrap:

```text
10,000 replicates
seed: 20260718
80% and 95% intervals
unit: historical_game_id
```

## Promotion gates

A `HOLDOUT_RESEARCH_PASS` requires all structural gates and every rule below:

```text
combined forward Log Loss gain >= 0.002
final untouched holdout Log Loss gain > 0
Fold 1 Log Loss gain >= -0.005
combined forward Brier gain >= 0.0005
final untouched holdout Brier gain >= -0.001
combined bootstrap probability(Log Loss gain > 0) >= 0.70
final bootstrap probability(Log Loss gain > 0) >= 0.55
average absolute probability shift <= 0.05
maximum single-game probability shift <= 0.20
monitored subgroup Log Loss degradation <= 0.03 for groups with at least 30 rows
both fitted injury coefficients non-positive
```

`gain` always means baseline metric minus candidate metric, so positive is better.

## Monitored subgroups

```text
source_wave
test_fold
minimum Expected Minutes coverage band
minutes-before-tip band
training-fold absolute injury-burden quartile
```

All subgroup thresholds and quartiles must be learned from training data only. Subgroups cannot rescue a failed primary result.

## Structural gates

The execution is structurally valid only if:

```text
population games = 293
baseline joins = 293
unique game IDs = 293
combined forward tests = 169
final holdout = 104
fold overlap = 0
identity mismatch = 0
feature missing rows = 0
snapshot-before-T-60 violations = 0
strict point-in-time violations = 0
target-game labels used as features = false
market odds used = false
random shuffle used = false
fuzzy identity or schedule matching = false
```

## Formal decision states

```text
STRUCTURAL_BLOCKED
VALID_NEGATIVE_RESULT
HOLDOUT_RESEARCH_PASS
```

Interpretation:

- `STRUCTURAL_BLOCKED`: the population, join, fold, point-in-time, missingness, or implementation contract failed. Any performance values are descriptive only.
- `VALID_NEGATIVE_RESULT`: the structure passed but one or more promotion gates failed. The injury candidate is rejected; the frozen baseline-only path remains valid.
- `HOLDOUT_RESEARCH_PASS`: every structural and promotion gate passed. The candidate becomes research-ready for later market comparison, but is not activated.

A valid negative result is a completed research result and must not be repeatedly tuned until it becomes positive.

## Post-decision permissions

Both structurally valid outcomes may unlock a separately predeclared Timestamped Odds acquisition stage:

```text
VALID_NEGATIVE_RESULT
→ proceed with frozen baseline-only market research

HOLDOUT_RESEARCH_PASS
→ preserve baseline and injury candidate as separate market-research paths
```

Neither outcome directly authorizes:

```text
production model training
probability adjustment in live decisions
betting-edge claims
nonzero stake
```

## Permanent boundaries

- No market odds enter training or feature selection.
- Target-game participation and minutes remain evaluation-only and are not candidate features.
- Missing injury data is not zero, healthy, DNP, or inactive.
- No fuzzy identity, fuzzy schedule matching, or nearest-name guessing.
- No random split or same-game snapshot duplication.
- No post-result feature substitution, hyperparameter search, threshold reduction, or calibration choice.
- Secondary metrics and subgroups cannot override primary failure.
- Formal stake remains `0`.

## Next exact task after this predeclaration is merged

```text
implement the exact frozen two-fold holdout
→ produce aggregate-only Artifact QA
→ record STRUCTURAL_BLOCKED, VALID_NEGATIVE_RESULT, or HOLDOUT_RESEARCH_PASS
```
