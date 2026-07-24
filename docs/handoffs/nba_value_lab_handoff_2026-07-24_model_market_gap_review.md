# NBA Value Lab Handoff — Model / Market Gap Review 2025–26 v1

Updated: 2026-07-24  
Repository: `qoo109/nba-value-lab`  
Research state: **Research Candidate / Pre-Market-Backtest**  
Formal Stake: **0**

## Source of Truth

```text
prior main: d464bd0973974c9075e9a9bee9a14bb5fb2ac2d1
prior merged milestone: PR #180
recording PR: #181
working branch: research/model-market-gap-review-2025-26-v1
```

## Purpose

Use the private 1,110-game same-game model/market join and governed 1,230-game 2025–26 forward Gold only for an aggregate diagnostic of where the frozen model differs from the no-vig market.

No network or provider API request was executed. No game-level price row or joined row is committed.

## Primary population

```text
nearest valid pre-tip collector batch
absolute T-60 batch error <= 5 minutes
rows: 310
strict T-60 qualified: false
```

## Result

```text
Model Log Loss: 0.625383
Market Log Loss: 0.602416
Model Brier: 0.217402
Market Brier: 0.208598
Model Accuracy: 65.48%
Market Accuracy: 65.81%
Model AUC: 0.699519
Market AUC: 0.729216
```

The largest descriptive weakness occurs where the absolute model-market probability difference is at least 10 percentage points:

```text
rows: 92
model-minus-market Log Loss: +0.063125
model-minus-market Brier: +0.024684
```

This subgroup is not a betting filter and does not authorize post-hoc promotion.

## Binding prior result

The two-feature bounded injury candidate is already a `VALID_NEGATIVE_RESULT`. It must not be retuned on the same outcomes.

## Formal decision

```text
PRESERVE_FROZEN_BASELINE_AND_MARKET_BACKTEST_LOCK
```

## Next unique research design

```text
PREDECLARE_PRIOR_ONLY_PLAYER_ROTATION_STATE_FEATURE_LAYER_V1
```

The next candidate must add genuinely new prior-only player and rotation information. Market prices remain outside the independent win-probability model.

## Preserved locks

```text
model retraining authorized: false
injury candidate retuning authorized: false
market blend activation authorized: false
provider-origin observed_at verified: false
strict T-60: false
formal market backtest: false
EV / ROI / CLV / Drawdown: false
betting-edge claim: false
Formal Stake: 0
```

## Do Not Do

- Do not publish the private 1,110-game join.
- Do not treat the 10pp+ subgroup as a betting rule.
- Do not retune the rejected injury candidate.
- Do not use market prices as model features.
- Do not call collector batch timestamps exact provider-origin T-60.
- Do not calculate or claim EV, ROI, CLV, Drawdown or edge.

## Validation Evidence

Validated branch head before this evidence-binding commit:

```text
head: dcbb70681856aa103596ae88c28dd9e49bc8da79
PR: 181
run: 30086808895
job: 89460786105 — success
Artifact: 8594040269
digest: sha256:fc93aeb3b4cc762d33415881eef01f9f8bb1ef4d036743fa874b34cd9d4af8c4
contract tests: 87 / 87 PASS
synthetic checks: 4 / 4 PASS
Artifact inspected: true
formal state: MODEL_MARKET_GAP_REVIEW_2025_26_RESULT_VALID
```

A final branch-head validation is required after this handoff update before merge.
