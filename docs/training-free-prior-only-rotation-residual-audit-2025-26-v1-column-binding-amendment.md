# Training-free Prior-only Rotation Residual Audit 2025–26 v1 — Column Binding Amendment

## Purpose

Bind the twelve conceptual feature names in PR #188 to the exact physical columns in the private matchup CSV produced by PR #187.

Formal state:

```text
TRAINING_FREE_PRIOR_ONLY_ROTATION_RESIDUAL_AUDIT_2025_26_V1_COLUMN_BINDING_AMENDMENT_PREDECLARED
```

## Why this amendment is required

A static schema check performed before any private residual execution found a naming-shape mismatch:

```text
PR #188 conceptual name:
rotation_players_prior_5_diff

PR #187 physical CSV column:
diff_rotation_players_prior_5
```

The same suffix-versus-prefix difference applies to all twelve matchup differences.

This is a column-binding correction only. At the time it was declared:

```text
Private residual join executed: false
Residual statistics computed: false
Outcomes inspected for amendment: false
Market results inspected for amendment: false
Feature set changed: false
Hypotheses changed: false
Population gates changed: false
Decision policy changed: false
```

No post-outcome feature selection or threshold change occurred.

## Bound source

```text
Feature PR: #187
Feature Artifact: 8603761824
Feature Artifact SHA-256: sha256:e02cd15e9b3aa1d58d3cbee1f27f1caea461d7e2f8ec701389e6e5f969ba440a
Matchup CSV SHA-256: sha256:3e8ef30f3a9801fda92fc95a490228b73fa53603093c914207e884a933b2de02
Header SHA-256: sha256:81bbe7ab22a5e7892207b4eb765a084dc88c059407664532672ea93d9f51146d
```

## Exact canonical-to-physical mapping

| Canonical audit name | Physical CSV column |
|---|---|
| `rotation_players_prior_5_diff` | `diff_rotation_players_prior_5` |
| `top5_minutes_share_prior_5_diff` | `diff_top5_minutes_share_prior_5` |
| `top8_minutes_share_prior_5_diff` | `diff_top8_minutes_share_prior_5` |
| `top8_minutes_share_prior_10_diff` | `diff_top8_minutes_share_prior_10` |
| `rotation_entropy_prior_5_diff` | `diff_rotation_entropy_prior_5` |
| `rotation_entropy_prior_10_diff` | `diff_rotation_entropy_prior_10` |
| `top8_set_continuity_prior_5_diff` | `diff_top8_set_continuity_prior_5` |
| `starter_set_continuity_prior_5_diff` | `diff_starter_set_continuity_prior_5` |
| `minutes_allocation_volatility_prior_5_diff` | `diff_minutes_allocation_volatility_prior_5` |
| `role_change_magnitude_prior_3_vs_10_diff` | `diff_role_change_magnitude_prior_3_vs_10` |
| `recent_return_players_count_diff` | `diff_recent_return_players_count` |
| `new_team_rotation_players_prior_5_diff` | `diff_new_team_rotation_players_prior_5` |

Identity and readiness columns are also bound exactly:

```text
game_id -> target_game_id
game_date_et -> target_game_date_et
home_team -> home_team_abbr
away_team -> away_team_abbr
feature_ready_game -> feature_ready_game
```

## Runtime policy

The execution tool must use this explicit dictionary. It may not infer columns from prefixes, suffixes, case-folding, approximate spelling or positional order.

```text
Mapping cardinality: ONE_TO_ONE
Canonical features: 12
Physical columns: 12
Duplicate canonical names: 0
Duplicate physical names: 0
Unmapped primary features allowed: 0
Extra primary physical columns allowed: 0
Runtime guessing: prohibited
Fuzzy column matching: prohibited
```

## Rotation-stress index binding

The seven stress-index components retain the PR #188 signs and now bind to physical columns:

- `diff_rotation_players_prior_5`: `+1`
- `diff_top8_set_continuity_prior_5`: `-1`
- `diff_starter_set_continuity_prior_5`: `-1`
- `diff_minutes_allocation_volatility_prior_5`: `+1`
- `diff_role_change_magnitude_prior_3_vs_10`: `+1`
- `diff_recent_return_players_count`: `+1`
- `diff_new_team_rotation_players_prior_5`: `+1`

The index definition, outcome-free median/IQR scaling, minimum five components and hypothesis directions are unchanged.

## Preserved design

```text
Primary model expected rows: 1,075
Primary model minimum rows: 1,000
Primary market minimum rows: 200
Sensitivity bands: 15 / 30 / 60 minutes
Bootstrap resamples: 5,000
Bootstrap seed: 20260725
H1 direction: negative
H2 direction: positive
Multiple testing: Benjamini-Hochberg q <= 0.10
Public output: aggregate only
```

## Preserved locks

```text
Model training authorized: false
Model promotion authorized: false
Strict T-60 qualified: false
Formal Market Backtest allowed: false
Betting-edge claim allowed: false
Formal Stake: 0
```

## Next unique mainline after validation

```text
IMPLEMENT_AND_EXECUTE_TRAINING_FREE_PRIOR_ONLY_ROTATION_RESIDUAL_AUDIT_2025_26_V1_USING_EXACT_COLUMN_BINDING
```

Execution remains dependent on the bound private model-market join or its exact governed source archive. The amendment does not authorize a replacement input.
