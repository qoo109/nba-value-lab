# NBA Value Lab Handoff — G1.2.0 Live Output Implementation

Date: 2026-07-24  
Formal Stake: `0`

## Latest main SHA before this milestone

```text
e78a26392dff5bc1c5d5eb16095518d60816d622
```

## Open PRs before this milestone

```text
none
```

## Completed

- G1.2.0 EV-primary executable decision function.
- Automatic 2026-27 regular-season activation resolver.
- G1.1.1 scheduled/control shadow preservation.
- T-60 and T-5 record fields for EV, PP guard and parallel comparison.
- V3.1.1 × G1.2.0 scheduled coordination v1.3.0.
- Frontend scheduled preview and active G1.2.0 routing.
- Prediction schema 1.4.0 and fail-closed tests.

## One unique next mainline

```text
VALIDATE_G1_2_0_END_TO_END_WITH_REAL_GOVERNED_2026_27_T60_INPUT
```

## Known blockers

- Governed bookmaker-level point-in-time odds are not yet acquired.
- The project remains Research Candidate / Pre-Market-Backtest.
- Formal injury holdout requirements are not yet met.
- Until a real eligible 2026-27 input exists, only fixtures can prove the activation path.

## Do Not Do

- Do not switch the offseason active Registry to G1.2.0 early.
- Do not omit `season` or `competition_type` and then infer activation from file dates.
- Do not let EV bypass hard data/risk Gates.
- Do not remove the 2pp PP guard or tune 5% / 7% / 10% thresholds after outcomes.
- Do not overwrite G1.1.1 control records.
- Do not use Closing-only prices as T-60 or T-5.
- Do not raise Stake above 0.
