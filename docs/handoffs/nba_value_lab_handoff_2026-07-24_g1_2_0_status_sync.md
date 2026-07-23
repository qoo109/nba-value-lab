# NBA Value Lab Handoff — G1.2.0 Status Documentation Sync

Date: 2026-07-24  
Formal Stake: `0`

## Repository state before this documentation milestone

```text
main: bcb66ba5b207d6a86cf87b3aeed18f3f3c2c0115
latest merged PR: 153
open PRs before branch creation: none
```

## Completed evidence being synchronized

```text
G1.2.0 implementation PR: 153 / merged
formal state: G1_2_0_LIVE_OUTPUT_IMPLEMENTATION_VALID
validation run: 30025555150
validation artifact: 8571205516
validation artifact digest: sha256:0d5d4d65f8b50e9bc81057b1aaa96620d2f3b40c5a75df66357cbe58432b8ccb
```

The implementation, contract, executable fixtures, frontend routing, model registry and repository-hygiene boundaries passed. This milestone updates status documentation only; it does not execute a real 2026–27 input or market backtest.

## Active and scheduled versions

```text
Active V: V3.1.1-20260719
Active G: G1.1.1-20260719
Scheduled G: G1.2.0-20260723
Scheduled coordination: V3.1.1_X_G1.2.0-20260724
Formal Stake: 0
```

## One unique next mainline

```text
VALIDATE_G1_2_0_END_TO_END_WITH_REAL_GOVERNED_2026_27_T60_INPUT
```

Current status:

```text
BLOCKED — REAL GOVERNED INPUT NOT AVAILABLE
```

Necessary prerequisite:

```text
TIMESTAMPED_BOOKMAKER_ODDS_REAL_OBSERVED_AT_DATA_ACQUISITION_REQUIRED
```

## Do Not Do

- Do not redo or overwrite PR #153.
- Do not activate G1.2.0 before the explicit 2026–27 regular-season trigger and complete T-60 Gate.
- Do not infer season or competition type from file dates.
- Do not substitute fixture or Closing-only data for a real governed T-60 input.
- Do not bypass the 2pp PP Guard or any hard data/risk Gate.
- Do not retrain models, enable market backtesting, claim betting edge or raise Stake above 0.
