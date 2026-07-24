# NBA Value Lab — Handoff after PR #187

## Repository

```text
qoo109/nba-value-lab
```

## Latest merged milestone

```text
PR #187
Build prior-only player rotation state features 2025-26 v1
Merge commit: 85821f7df6babce207dc5c39a24fbdcedd5ad165
```

Formal aggregate feature result:

```text
PRIOR_ONLY_PLAYER_ROTATION_STATE_FEATURES_2025_26_RESULT_VALID
```

Coverage:

```text
Private player feature rows: 44,196
Private team feature rows: 2,460
Private matchup feature rows: 1,230
Feature-ready independent games: 1,075
Feature-ready rate: 87.398374%
Teams: 30
Feature-ready months: 6
Validation: 38 / 38 PASS
Recorded-result validation: 51 / 51 PASS
```

All source-time, identity, duplicate, finite-value, bounded-value and privacy gates passed with zero violations.

## Current design PR

The next governed step is being predeclared on:

```text
design/training-free-prior-only-rotation-residual-audit-2025-26-v1
```

Mainline:

```text
PREDECLARE_TRAINING_FREE_PRIOR_ONLY_ROTATION_RESIDUAL_AUDIT_2025_26_V1
```

The design freezes:

- exact private input Artifacts and SHA-256 values;
- exact `game_id` joins;
- model and market residual direction;
- 1,075-game model-residual population;
- nominal T-60 batch-relative `<=5` minute market population;
- nested `<=15 / <=30 / <=60` sensitivity populations;
- one outcome-free rotation-stress index;
- two directional primary hypotheses;
- twelve fixed feature-difference secondary tests;
- Benjamini–Hochberg FDR `q <= 0.10`;
- 5,000 independent-game bootstrap resamples;
- chronological-half and monthly sign checks;
- aggregate-only public output.

## Boundaries

The design does not execute the residual audit and does not authorize:

- model fit, refit or retraining;
- model promotion or feature selection;
- calibration changes;
- Strict T-60 qualification;
- formal Market Backtest;
- EV, ROI, CLV or Drawdown;
- betting-edge claims;
- Stake above `0`.

## Next after design validation and merge

```text
EXECUTE_TRAINING_FREE_PRIOR_ONLY_ROTATION_RESIDUAL_AUDIT_2025_26_V1_ON_BOUND_PRIVATE_ARTIFACTS
```

Execution must use the bound private feature, frozen prediction and private model-market inputs. No expired Artifact may be replaced silently by an ungoverned source.
