# Prior-only Player Rotation State Features 2025–26 v1 — Result

## Formal result

```text
PRIOR_ONLY_PLAYER_ROTATION_STATE_FEATURES_2025_26_RESULT_VALID
```

The governed GitHub Actions feature build completed successfully from the final PR #185 private source Artifact. The generated row-level features remain in a short-lived private Artifact; only aggregate evidence is recorded in the Repository.

## Execution evidence

```text
Workflow run: 30110090746
Job: 89537194548
Head: 0634c67d7b3a46598ba70acc5b6b9495755302f9
Artifact: 8603174927
Artifact SHA-256: sha256:e164912d2330e9f915e27095d4ec7aa3ff0efe917c6dd406a697f7ce16f3ea0c
Expires: 2026-08-07T16:43:00Z
Artifact inspected: true
```

## Bound source

```text
Source Artifact: 8599479933
Source Artifact SHA-256: sha256:6a5c78b1d744731b90ff83ab9518b898b4b34878f22a001c82092250e2b2be7f
Source player-game rows: 43,265
Point-in-time rule: source_game_date_et < target_game_date_et
```

## Private outputs

```text
Player feature rows: 44,196
Team feature rows: 2,460
Matchup feature rows: 1,230
Public player rows: 0
Public game-level feature rows: 0
```

Output digests:

```text
Player: sha256:03a5300f5a8f415a00ce9e77ca7c682ad6fb792922bd775b63353c166259d1a5
Team: sha256:3196d4920149aa8929f8098960276086692f4a37fb62ffcddbfdc78ba82c98a8
Matchup: sha256:3e8ef30f3a9801fda92fc95a490228b73fa53603093c914207e884a933b2de02
```

## Coverage

```text
Feature-ready independent games: 1,075 / 1,230
Feature-ready rate: 87.398374%
Teams with feature-ready rows: 30
Months with feature-ready games: 6
```

Readiness subgroups:

```text
Both ready: 1,075
Both not ready: 145
Home not ready only: 6
Away not ready only: 4
```

The feature-ready sample exceeds the predeclared minimum of 1,000 independent games and 80% coverage.

## Missingness

Early-season missingness is structural and expected:

- prior-five features are null for the first five team-game contexts;
- prior-ten features are null for the first ten team-game contexts;
- missing source rows remain unknown and are never imputed as zero;
- sample-count fields are preserved;
- the missingness subgroup audit completed.

## Quality

```text
Validation: 38 / 38 PASS
Duplicate target keys: 0
Source-time violations: 0
Identity ambiguities: 0
Source/index mismatches: 0
Non-finite values: 0
Bounded-feature violations: 0
Fuzzy identity rows: 0
Target-game source rows used: 0
Same-day source rows used: 0
Future source rows used: 0
Market feature rows used: 0
Player-name fields found: 0
```

## Interpretation

The result qualifies the feature dataset only for a separately predeclared, training-free residual audit.

It does not authorize:

- model fit, refit or retraining;
- calibration change;
- model promotion;
- Strict T-60 qualification;
- formal Market Backtest;
- EV, ROI, CLV or Drawdown;
- betting-edge claims;
- Formal Stake above zero.

## Next unique mainline

```text
PREDECLARE_TRAINING_FREE_PRIOR_ONLY_ROTATION_RESIDUAL_AUDIT_2025_26_V1
```

The future residual audit must define its population, direction and sensitivity bands before inspecting outcomes. Nominal T-60 comparisons remain private-archive batch-relative diagnostics and are not provider-origin Strict T-60.
