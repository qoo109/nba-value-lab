# Prior-only Player Rotation State Features 2025–26 v1

## Purpose

Build the predeclared private player-, team- and matchup-level rotation-state feature layer from the qualified 2025–26 NBA Official LiveData source.

This stage is feature construction and aggregate QA only. It does not train, refit, recalibrate or score a candidate model. It does not perform an odds join, formal Market Backtest, EV, ROI, CLV, Drawdown or betting selection.

## Bound source

The workflow is bound to the final PR #185 source Artifact:

```text
Artifact ID: 8599479933
Workflow run: 30100700645
Head SHA: 1d2f560024a58e75d7d0350b5917169deb8713e7
Artifact SHA-256: sha256:6a5c78b1d744731b90ff83ab9518b898b4b34878f22a001c82092250e2b2be7f
Source CSV SHA-256: sha256:5c56c1a9b0d714f7d41da8bd49a7ee7cf364eb2f40c9b6514223062e5be91507
Source index SHA-256: sha256:f4484c3b0d75c8cf693f87b2c4c3d00cfec32c1377935423f33ae3e601667bc7
```

The Artifact expires on 2026-08-07. If it expires, the workflow must not silently rebuild from an ungoverned source.

## Point-in-time rule

Every source row used for a target game must satisfy:

```text
source_game_date_et < target_game_date_et
```

Same-day, target-game and future rows are excluded. The official source does not provide a governed game-end timestamp, so the strict earlier Eastern date rule is the approved conservative fallback.

## Player feature population

For each target team-game, the private player output includes only players observed in that team's strictly-prior ten-game window. Target-game roster rows are never used to decide the player population.

A missing official source row is `unknown`, not zero. Window averages and rates use only explicit official rows and include sample-count fields. Early-season or insufficient-history values remain null.

## Player features

- `minutes_avg_prior_3`
- `minutes_avg_prior_5`
- `minutes_avg_prior_10`
- `minutes_trend_prior_3_vs_10`
- `start_rate_prior_5`
- `start_rate_prior_10`
- `appearance_rate_prior_10`
- `days_since_last_appearance`
- `recent_return_state`
- `role_rank_prior_5`

`recent_return_state` is defined only when the player has explicit official rows in the four most recent prior team games. It equals one when the latest prior game has positive minutes and the preceding three explicit rows have zero minutes.

## Team features

- `rotation_players_prior_5`
- `top5_minutes_share_prior_5`
- `top8_minutes_share_prior_5`
- `top8_minutes_share_prior_10`
- `rotation_entropy_prior_5`
- `rotation_entropy_prior_10`
- `top8_set_continuity_prior_5`
- `starter_set_continuity_prior_5`
- `minutes_allocation_volatility_prior_5`
- `role_change_magnitude_prior_3_vs_10`
- `recent_return_players_count`
- `new_team_rotation_players_prior_5`

### Explicit semantics

- Minute-share concentration and entropy use official player minutes aggregated over the named prior window.
- Top-eight and starter continuity use the mean Jaccard similarity of consecutive game sets.
- Minute-allocation volatility uses only explicit source rows for each player and requires at least two explicit observations. Missing rows are not imputed as zero.
- Role-change magnitude compares prior-three and prior-ten minute shares only for player IDs explicitly observed in both windows. It does not impute an absent player to zero.
- A new-team rotation player has fewer than five team-specific prior source rows and ranks in the current prior-five top eight.

## Matchup features

Each target game has home values, away values and `home - away` differences. If either side is null, the difference remains null.

## Feature readiness

A team row is feature-ready only when it has at least ten strictly-prior team games and all twelve predeclared team features are finite. A matchup is feature-ready only when both team rows are feature-ready.

### Rotation feature construction acceptance gates

```text
Feature-ready independent games >= 1,000
Feature-ready rate >= 80%
Teams with feature-ready rows = 30
Months with feature-ready games >= 5
Source-time violations = 0
Identity ambiguities = 0
Duplicate target keys = 0
Non-finite feature values = 0
Bounded feature violations = 0
Fuzzy identity rows = 0
Target-game source rows used = 0
Same-day source rows used = 0
Future source rows used = 0
Market feature rows used = 0
Missingness subgroup audit completed
```

Passing these gates means only:

```text
FEATURE_DATASET_ELIGIBLE_FOR_TRAINING_FREE_RESIDUAL_AUDIT
```

It does not authorize model training, model promotion, Strict T-60, formal Market Backtest, betting use or Stake above zero.

## Outputs

All row-level outputs remain in a short-lived private GitHub Actions Artifact:

- private player prior-state features;
- private team rotation features;
- private matchup rotation features;
- aggregate build report;
- aggregate validation report.

No player rows, names, source index, raw official JSON or game-level feature rows are committed to the public Repository.

## Next governed step

After a valid feature build and Artifact inspection, the next step is:

```text
PREDECLARE_TRAINING_FREE_PRIOR_ONLY_ROTATION_RESIDUAL_AUDIT_2025_26_V1
```

The residual audit must remain training-free and must describe nominal T-60 comparisons as private-archive batch-relative diagnostic sensitivity, not provider-origin Strict T-60.
