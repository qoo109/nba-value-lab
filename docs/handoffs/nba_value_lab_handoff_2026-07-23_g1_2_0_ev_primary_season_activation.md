# NBA Value Lab Handoff — G1.2.0 EV-Primary Season Activation

Date: 2026-07-23  
Formal Stake: `0`

## Latest main SHA before this milestone

```text
0dcc4cd74a36f92479628ff42db8a992d8afe2e2
```

## Open PRs before this milestone

```text
none
```

## Decision recorded

```text
G1_2_0_EV_PRIMARY_USER_APPROVED_FOR_2026_27_SEASON
```

The user approved EV-primary as the primary G-system rule set for the next NBA regular season. The canonical new version is `G1.2.0-20260723`; it cannot be named G1.1 because immutable `G1.1.1-20260719` already exists.

## Version roles

```text
Offseason active G: G1.1.1-20260719
Scheduled primary G from 2026-27 trigger: G1.2.0-20260723
Post-trigger control: G1.1.1-20260719 / parallel control shadow
V engine: V3.1.1-20260719 / unchanged
Formal Stake: 0
```

Activation trigger:

```text
first_2026_27_regular_season_game_with_complete_T60_data_gate
```

## Frozen G1.2.0 thresholds

```text
ConservativeEV = P_C × decimal odds − 1
candidate minimum EV = 5%
ㄇ級 minimum EV = 5%
ㄆ級 minimum EV = 7%
ㄅ級 minimum EV = 10%
PP Edge safety floor = 2pp
post-result threshold tuning = forbidden
```

## Preserved hard gates

- Coverage at least 85% for core selection.
- Injury and rotation confirmation.
- High confidence and interval-width gate.
- News risk no higher than 1.
- At least three comparison sources.
- Same bookmaker, market and observed-at two-sided price.
- OOD, stale-price and unmodeled reverse-path blockers.
- Dual-side conflict blocks main selection.
- T-60 prediction lock, T-5 reselection, Closing validation only.
- Main target 2, maximum 3, zero selections allowed.

## One unique next mainline

```text
IMPLEMENT_AND_VALIDATE_G1_2_0_LIVE_DECISION_OUTPUT_BEFORE_2026_27_SEASON_TRIGGER
```

This means implementing the actual EV-based grade/output fields and frontend display before the first eligible regular-season T-60 run. It does not authorize bypassing the timestamped-odds data gate.

## Known blockers

- Real governed bookmaker-level point-in-time odds are still not acquired.
- Current project remains Research Candidate / Pre-Market-Backtest.
- G1.2.0 cannot produce a valid live main selection when its T-60 data gates are incomplete.
- Formal injury activation remains below its governed holdout requirement.

## Do Not Do

- Do not overwrite or delete G1.1.1.
- Do not call the new version G1.1 in the registry.
- Do not activate real-money Stake; Stake remains 0.
- Do not use Closing-only odds as T-60 or T-5 executable prices.
- Do not remove the 2pp PP safety floor.
- Do not tune 5% / 7% / 10% EV thresholds after seeing results without a new version.
- Do not let high EV bypass Coverage, injury, news, source, OOD or stale-price gates.
- Do not blend V and G probabilities.
- Do not claim profitability from the informal proxy test.
