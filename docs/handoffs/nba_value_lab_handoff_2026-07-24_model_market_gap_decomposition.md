# NBA Value Lab Handoff — Model/Market Gap Decomposition 2025-26

Date: 2026-07-24  
Repository: `qoo109/nba-value-lab`  
Research state: **Research Candidate / Pre-Market-Backtest**  
Formal Stake: **0**

## Source of Truth before milestone

```text
prior main: d464bd0973974c9075e9a9bee9a14bb5fb2ac2d1
prior merged milestone: PR #180
open PRs before branch creation: none
working branch: research/model-market-gap-decomposition-2025-26-v1
```

## Purpose

Review the 2025-26 frozen model-versus-market gap while preserving all market-backtest and betting locks. The milestone uses the 1,110-row private same-game join and the 2025-26 governed forward Gold matchup features.

No new provider request, model fit, calibration change, price publication or bet selection is executed.

## Governed population

```text
private model/market rows: 1,110
unique games: 1,110
Gold feature joins: 1,110
primary feature diagnostic band: T-60 batch error <=60 minutes
primary band rows: 697
```

## Main findings

Across the predeclared ±5, ±15, ±30 and ±60-minute bands, the correlation between model-market probability delta and later market residual stays between `-0.0104` and `+0.0548`. Every bootstrap interval crosses zero.

Where model and market select opposite sides, model-side win rates are:

```text
±5:  48.94%
±15: 42.67%
±30: 42.35%
±60: 46.24%
```

The model does not win a majority of disagreements in any band.

Within the ±60-minute population, model-minus-market Log Loss grows monotonically with the absolute probability gap:

```text
<2 pp:    +0.003309
2-<5 pp:  +0.008426
5-<10 pp: +0.025011
>=10 pp:  +0.051618
```

Formal finding:

```text
NO_INCREMENTAL_INFORMATION_SIGNAL_DEMONSTRATED
```

## Existing-feature interpretation

Existing Net Rating and ORB% features are associated with the direction of model-market disagreement, but none of the fixed existing Gold features has an absolute correlation of `0.06` or more with later market residuals. This does not promote, remove or reweight any feature.

## Next research direction

```text
BUILD_2025_26_POINT_IN_TIME_INJURY_LINEUP_ROLE_FEATURE_DIAGNOSTIC
WITHOUT_MODEL_RETRAINING_OR_MARKET_BACKTEST_PROMOTION
```

Candidate information layers:

- point-in-time injury availability;
- expected-minutes changes;
- confirmed starting lineups;
- rotation and role changes.

They remain unvalidated until coverage and residual evidence are produced.

## Public/private boundary

```text
public game-level join rows: 0
public price rows: 0
raw odds archives: 0
private augmented rows: 1,110 / local only
```

## Preserved locks

```text
strict provider-origin T-60: false
formal Point-in-Time Market Backtest: false
model retraining/refit: false
calibration change: false
EV / ROI / CLV / Drawdown: false
betting-edge claim: false
Formal Stake: 0
```

## Do Not Do

- Do not turn a larger model-market probability gap into a betting threshold.
- Do not call collector batch timestamps exact provider `observed_at`.
- Do not retrain the frozen model in this milestone.
- Do not reopen Rest/Travel v1 without materially different data.
- Do not publish the private augmented CSV or prices.
- Do not promote G1.2.0 or increase Formal Stake.

## Validation evidence

Pending branch-head GitHub Actions execution. Bind final head, run, job, Artifact and digest before merge.
