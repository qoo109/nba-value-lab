# NBA Value Lab — G1.2.0 Real T-60 Intake Validator Handoff

更新日期：2026-07-24

## Repository state before this milestone

```text
main: cff7e4e82d34420592a2f386775e55859397af26
latest merged PR: 167
open PRs before branch creation: none
Formal Stake：0
```

## User decision preserved

```text
HoopsAPI runtime path: DEFERRED_BY_USER_NO_EXECUTION
BloomBet schema probe: DEFERRED_BY_USER_NO_EXECUTION
paid odds path: NOT APPROVED
provider requests executed: 0
```

## Current milestone

```text
IMPLEMENT_G1_2_0_REAL_GOVERNED_T60_INPUT_INTAKE_VALIDATOR_V1
```

Implemented:

- `scripts/g1_2_0_real_t60_intake_validator_v1.py`
- documentation schema for normalized input and source evidence;
- separate normalized-input, evidence and raw-source contract fixtures;
- fail-closed contract validation;
- aggregate-only GitHub Actions QA;
- no network client, provider adapter, secret reader or formal history writer.

## Contract behavior

The production CLI accepts only:

```text
data_mode = real_governed
season = 2026-27
competition_type = regular_season
evaluation_stage = T-60m
```

Contract fixture only inputs are rejected by the production CLI.

Required source evidence includes private research rights, verified provider timestamp semantics, exact mapping, provider-origin observed_at authority, normalized input SHA-256 and raw source SHA-256.

`collector_fetched_at` cannot substitute for `observed_at`.

## Current execution state

```text
contract fixture only: true
real input validated: false
real G1.2.0 dry-run executed: false
qualified timestamped odds sources: none
formal history write authorized: false
provider requests executed: 0
raw quote rows emitted: 0
Market Backtest: false
Formal Stake：0
```

## Do not do

- Do not rename contract fixtures as `real_governed`.
- Do not use fixture, synthetic, Closing-only or future snapshots.
- Do not use collector receipt time as provider observation time.
- Do not retain raw provider payload in a public Artifact.
- Do not write formal history during intake validation.
- Do not activate G1.2.0 early.
- Do not run Market Backtest, CLV, EV, ROI or Drawdown.
- Do not raise Stake above 0.

## Next unique mainline

```text
AWAIT_REAL_GOVERNED_2026_27_T60_INPUT_AND_QUALIFIED_TIMESTAMPED_ODDS
```

When a lawful qualified source and one real governed T-60 bundle exist, run the validator privately and inspect aggregate-only QA. A passing intake does not itself authorize the real G1.2.0 dry-run; that remains a separate governed step.
