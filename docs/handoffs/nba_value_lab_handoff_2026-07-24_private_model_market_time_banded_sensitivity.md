# NBA Value Lab Handoff — Private Model/Market Time-Banded Sensitivity 2025-26

日期：2026-07-24  
Repository：`qoo109/nba-value-lab`  
研究定位：**Research Candidate / Pre-Market-Backtest**  
Formal Stake：**0**

## Source of Truth

- Prior `main`: `a11e3800cbb718c3b1bd002b142e2887f6ee3ab4`
- Prior merged milestone: PR #179 — frozen `walk-forward-v2` forward score on governed 2025-26 data
- Working branch: `research/private-odds-time-banded-sensitivity-2025-26-v1`
- This handoff records an aggregate-only private diagnostic. It does not publish game-level prices or joined prediction rows.

## Purpose

Join the frozen model's 1,230 forward probabilities to the private aligned 2025-26 archive for a time-quality sensitivity study only. The analysis selects the nearest valid pre-tip collector batch to T-60 and evaluates four predeclared nested timing-error bands: ±5, ±15, ±30 and ±60 minutes.

The collector timestamp is batch-created and assumed UTC. It is not verified provider-origin quote time and therefore cannot qualify strict T-60 or a formal point-in-time market backtest.

## Governed Inputs

- Frozen forward prediction rows: `1,230`
- Frozen forward Artifact: `8592208938`
- Prediction CSV SHA-256: `c3764faf6eb3703374b12a5d8668c6ef889cd8f54070a2c6cf135b55559ca725`
- Private odds rows: `8,153`
- Regular-season aligned private events: `1,112`
- Exact same-game matches before valid-moneyline filtering: `1,111`
- Valid two-way pre-tip Moneyline matches: `1,110`
- Orientation mismatches: `0`
- Duplicate join keys: `0`

## Selection Policy

```text
market: two-way Moneyline
snapshot: nearest valid pre-tip collector batch to T-60
tie breaker: earliest assumed-UTC collector batch timestamp
market probability: proportional no-vig
bands: ±5 / ±15 / ±30 / ±60 minutes
bands nested: true
profitability-based band selection: false
```

## Aggregate Results

| Maximum T-60 batch error | Rows | Model Log Loss | Market Log Loss | Model Brier | Market Brier | Model Accuracy | Market Accuracy |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 min | 310 | 0.625383 | 0.602416 | 0.217402 | 0.208598 | 65.484% | 65.806% |
| 15 min | 493 | 0.603332 | 0.576019 | 0.207676 | 0.196791 | 66.937% | 69.168% |
| 30 min | 612 | 0.600365 | 0.570928 | 0.206647 | 0.194875 | 67.157% | 69.281% |
| 60 min | 697 | 0.602119 | 0.577348 | 0.207430 | 0.197743 | 67.719% | 68.723% |

Paired 5,000-resample diagnostics:

- Model-minus-market Log Loss CI excludes zero on the worse-than-market side in all four bands.
- Model-minus-market Brier CI excludes zero in the 15, 30 and 60-minute bands; the 5-minute interval crosses zero.
- Model accuracy does not exceed market accuracy in any band.

Formal interpretation:

> Across every predeclared timing-quality band, the no-vig market probability outperformed the frozen model on Log Loss and Brier. This diagnostic provides no evidence that the frozen model beats the market on this private archive.

## Public / Private Boundary

Public repository contains only:

- offline analyzer source;
- aggregate result record;
- aggregate result document;
- aggregate-only validator and synthetic self-test workflow;
- this handoff.

Public repository contains:

- game-level joined rows: `0`
- bookmaker price rows: `0`
- raw odds archives: `0`

Private local output contains `1,110` joined rows and remains outside the public repository.

## Preserved Locks

- model retraining: `false`
- model refit: `false`
- calibration change: `false`
- market data used as model feature: `false`
- strict T-60 qualified: `false`
- formal point-in-time market backtest allowed: `false`
- EV calculated: `false`
- ROI calculated: `false`
- CLV calculated: `false`
- Drawdown calculated: `false`
- betting-edge claim allowed: `false`
- Formal Stake: `0`

## Do Not Do

- Do not relabel collector batch timestamps as provider-origin `observed_at`.
- Do not call this an executable T-60 backtest.
- Do not calculate or publish EV, ROI, CLV, Drawdown or betting selections from this milestone.
- Do not publish the private joined CSV or raw price rows.
- Do not tune timing bands after seeing profitability or forecast metrics.
- Do not retrain the frozen model in this milestone.
- Do not promote G1.2.0 or increase Formal Stake.

## Next Unique Sub-Mainline

```text
REVIEW_MODEL_MARKET_GAP_AND_PRESERVE_MARKET_BACKTEST_LOCK_WHILE_AWAITING_EXACT_PROVIDER_OBSERVED_AT
```

The research conclusion is a negative market-comparison result, not a pipeline failure. The next model work must focus on genuinely new pre-game information or a predeclared market-residual design. Formal market backtesting remains blocked until an exact provider-origin `observed_at` source is legally and technically qualified.

## Validation Evidence

To be completed after the branch-head workflow succeeds:

- PR: `pending`
- final branch head: `pending`
- validation run: `pending`
- validation job: `pending`
- validation Artifact: `pending`
- validation Artifact digest: `pending`
- formal validation state: `PRIVATE_MODEL_MARKET_TIME_BANDED_SENSITIVITY_2025_26_RESULT_VALID`
