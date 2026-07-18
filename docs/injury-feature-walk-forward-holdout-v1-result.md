# Injury Feature Walk-forward Holdout v1 — Official Result

更新日期：2026-07-18  
正式狀態：**VALID_NEGATIVE_RESULT**

## Evidence lock

```text
Predeclaration PR: #55
Predeclaration merge: 8c3c45b9e77a0e9de40b82057ba2ac06be6068ac
Policy commit: 49560a26cf96b0aafa228416e84253de82e5ca80
Execution PR: #56
Verified workflow run: 29636667921
Artifact: injury-feature-walk-forward-holdout-v1
Artifact id: 8427322134
Artifact digest: sha256:f5a00bf4c5034b40d5692306459611012e176092e54ab4f647c6c23b0c3e40a0
```

The population, folds, baseline, candidate formula, features, regularization, coefficient bounds, bootstrap, subgroup definitions, and promotion gates were frozen before this result was calculated.

## Frozen population and structural QA

```text
injury-panel games: 293
unique injury games: 293
baseline OOF rows: 3,688
exact baseline joins: 293
Wave 1: 91
Wave 2: 85
Wave 3: 117
complete snapshots: 293
feature-available games: 293
missing injury feature rows: 0
duplicate injury games: 0
duplicate baseline games: 0
date/team identity mismatches: 0
selection-policy mismatches: 0
fallback rows: 0
before-T-60 violations: 0
timestamp parse errors: 0
strict point-in-time violations: 0
fold overlap games: 0
test rows used for training: 0
```

All structural gates passed. The result is therefore a valid forward research result rather than a structural block.

## Frozen candidate

```text
bounded_injury_logit_offset_v1

logit(p_candidate)
= logit(p_baseline)
+ beta_1 × z(weighted unavailable minutes home-minus-away)
+ beta_2 × z(weighted positive absence impact home-minus-away)
```

Only the two predeclared injury features were used. Scaling was learned inside each training fold. No intercept, market odds, target-game participation labels, post-result feature selection, or hyperparameter search was used.

## Fold 1 — Development forward check

```text
train: 2023-10-30 → 2024-01-31 — 124 games
test:  2024-02-01 → 2024-02-29 — 65 games
```

| Metric | Baseline | Candidate | Gain |
|---|---:|---:|---:|
| Log Loss | 0.657411 | 0.667960 | **-0.010549** |
| Brier | 0.233483 | 0.235695 | **-0.002212** |
| Accuracy | 60.00% | 63.08% | +3.08 pp |
| AUC | 0.688447 | 0.673295 | -0.015152 |
| Margin MAE | 11.556817 | 11.569429 | -0.012612 |

Probability coefficients:

```text
weighted unavailable minutes: -0.240480
positive absence impact:      -0.008085
```

The primary probability metrics worsened. The development Log Loss degradation exceeded the permitted `-0.005` floor.

## Fold 2 — Final untouched holdout

```text
train: 2023-10-30 → 2024-02-29 — 189 games
test:  2024-03-01 → 2024-04-12 — 104 games
```

| Metric | Baseline | Candidate | Gain |
|---|---:|---:|---:|
| Log Loss | 0.589324 | 0.586426 | **+0.002898** |
| Brier | 0.202537 | 0.201171 | **+0.001366** |
| Accuracy | 63.46% | 65.38% | +1.92 pp |
| AUC | 0.744483 | 0.749129 | +0.004646 |
| Margin MAE | 10.365402 | 10.464249 | -0.098847 |

Probability coefficients:

```text
weighted unavailable minutes: -0.066604
positive absence impact:      -0.111723
```

The final untouched probability metrics improved, but a single positive final fold cannot override the failed combined and development gates.

## Combined forward result

Combined forward test population:

```text
65 + 104 = 169 independent games
```

| Metric | Baseline | Candidate | Gain |
|---|---:|---:|---:|
| Log Loss | 0.615511 | 0.617785 | **-0.002274** |
| Brier | 0.214439 | 0.214450 | **-0.000010** |
| Accuracy | 62.13% | 64.50% | +2.37 pp |
| AUC | 0.709760 | 0.710616 | +0.000856 |

Primary interpretation:

- Accuracy improved, but the project promotes probability quality using Log Loss and Brier—not hit rate alone.
- Combined Log Loss worsened instead of improving by the required `0.002`.
- Combined Brier was effectively flat but slightly worse, rather than improving by the required `0.0005`.

## Paired bootstrap

10,000 paired game-level replicates, seed `20260718`:

| Population | P(Log Loss gain > 0) | Required | 95% gain interval |
|---|---:|---:|---:|
| Combined 169 games | **0.4023** | >= 0.70 | -0.019655 to +0.014665 |
| Final 104 games | **0.6549** | >= 0.55 | -0.012533 to +0.018326 |

The final fold passed its bootstrap probability threshold, but the combined population did not.

## Promotion gates

Failed gates:

```text
combined_forward_log_loss_gain
  observed: -0.002274
  required: >= +0.002000

development_fold_log_loss_gain
  observed: -0.010549
  required: >= -0.005000

combined_forward_brier_gain
  observed: -0.000010
  required: >= +0.000500

combined_bootstrap_probability_log_loss_gain_positive
  observed: 0.4023
  required: >= 0.7000
```

Passed safety and final-fold gates:

```text
final holdout Log Loss gain: +0.002898 — pass
final holdout Brier gain: +0.001366 — pass
final bootstrap P(gain > 0): 0.6549 — pass
average absolute probability shift: 0.037843 <= 0.05 — pass
maximum single-game shift: 0.155311 <= 0.20 — pass
worst monitored subgroup degradation: 0.015943 <= 0.03 — pass
all fitted probability coefficients non-positive — pass
```

## Formal interpretation

```text
decision_state = VALID_NEGATIVE_RESULT
injury_candidate_research_ready = false
market_research_model_path = frozen_baseline_only
ready_for_timestamped_odds_predeclaration = true
ready_for_timestamped_odds_execution = false
ready_for_production_model_training = false
ready_for_probability_adjustment = false
ready_for_betting_edge_claim = false
formal_stake = 0
```

This result does **not** prove that all injury information is useless. It establishes that this exact predeclared, bounded two-feature adjustment did not produce sufficiently stable forward probability improvement across the frozen 293-game panel.

The positive final fold is retained as a diagnostic observation, not used to overturn the negative combined decision. The candidate must not be retuned repeatedly on the same outcomes until it passes.

## Privacy and leakage boundary

```text
game-level temporary prediction rows retained: 0
model joblib files retained: 0
player-level files retained: 0
target-game participation used as feature: false
target-game minutes used as feature: false
market odds used: false
random shuffle used: false
missing injury values imputed as zero: false
post-result feature selection performed: false
hyperparameter search performed: false
```

## Next exact task

The structurally valid negative result unlocks a separately predeclared market-data stage using the frozen baseline-only path:

```text
Predeclare Real Timestamped Odds Acquisition／Backfill
→ freeze legal source, bookmaker, market and observed_at requirements
→ freeze source-health, provenance, normalization and missingness gates
→ merge the predeclaration before acquiring or evaluating executable prices
```

The odds schema and source registry already exist. The missing asset is real bookmaker-level data with reliable `observed_at`, not another registry design.
