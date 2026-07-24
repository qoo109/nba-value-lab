# NBA Value Lab Handoff — Prior-Only Player Rotation State Feature Layer v1

Date: 2026-07-24  
Repository: `qoo109/nba-value-lab`  
Research state: **Design Predeclared / Not Executed**  
Formal Stake: **0**

## Source of Truth

```text
base main: d572632a798e2453ea577318af34f811847c8f28
latest merged research milestone: PR #181
binding decision: PRESERVE_FROZEN_BASELINE_AND_MARKET_BACKTEST_LOCK
binding next design: PREDECLARE_PRIOR_ONLY_PLAYER_ROTATION_STATE_FEATURE_LAYER_V1
open PRs before branch creation: none
```

A duplicate PR #182 was closed without merge after the newer PR #181 Source of Truth was discovered. No result from PR #182 is authoritative.

## Milestone purpose

Freeze the specification for genuinely new player-level rotation and role-state information before any source build, outcome review or model fitting.

This milestone performs no network acquisition, no feature build, no residual audit, no model training and no market backtest.

## Primary point-in-time rule

```text
source_game_end_time_utc < target_analysis_cutoff_utc < target_tipoff_utc
```

Target-game boxscore, starter, minutes, participation and outcome rows are prohibited. Unknown source end times are excluded. Date-only fallback requires a strictly earlier Eastern game date.

## Frozen design

Player features: `10`

- prior 3/5/10 minutes;
- prior 3-versus-10 minutes trend;
- prior 5/10 start rate;
- prior 10 appearance rate;
- days since last appearance;
- prior-only recent return state;
- prior-5 team role rank.

Team features: `12`

- rotation player count;
- top-5/top-8 minute concentration;
- rotation entropy;
- top-eight continuity;
- official starter continuity;
- minutes allocation volatility;
- role-change magnitude;
- recent return count;
- new-team rotation count.

Primary features use current-season completed games only and require at least three prior games. Early-season values remain null with flags. Prior-season carryover is not mixed into primary v1.

## Source qualification boundary

- governed Silver controls game identity and schedule;
- deterministic official player IDs only;
- official completed-game boxscore is preferred for prior minutes and starters;
- a secondary source requires separate provenance, license and schema qualification;
- no fuzzy matching or nearest-name guessing;
- no bypass of 403, authentication or access controls;
- public player rows and public game-level feature rows remain zero.

## Activation gates

Before a later model experiment can be designed:

```text
feature-ready independent games >= 1,000
feature-ready rate >= 80%
months covered >= 5
teams represented = 30
source-time violations = 0
identity ambiguities = 0
missingness subgroup audit = required
residual direction = predeclared
```

Passing coverage does not authorize model training.

## Diagnostic sequence

1. Source, identity, timestamp, coverage and distribution QA.
2. Training-free residual audit against the frozen model and market residual.
3. Separately predeclare a walk-forward candidate only after a formal promotion decision.

Primary residual population remains the private same-game market join with T-60 batch error at most five minutes. Wider bands are sensitivity checks only.

## Preserved locks

```text
real feature build executed: false
residual audit executed: false
model training authorized: false
market prices as features: false
strict T-60 qualified: false
formal Market Backtest allowed: false
EV / ROI / CLV / Drawdown: false
betting-edge claim: false
Formal Stake: 0
```

## Do Not Do

- Do not use target-game boxscore or participation data as a pregame feature.
- Do not infer missing players as inactive, traded or zero minutes.
- Do not use a minutes-based starter proxy as a confirmed lineup.
- Do not retune the rejected injury offset on the same outcomes.
- Do not reopen Rest/Travel v1 without materially different data.
- Do not use model-market gap thresholds as betting filters.
- Do not train or refit the frozen model in this milestone.

## Next unique mainline

```text
QUALIFY_AND_BUILD_PRIOR_ONLY_PLAYER_ROTATION_STATE_SOURCE_V1
WITHOUT_MODEL_RETRAINING
```

## Validation evidence

Initial validated branch head before evidence-binding commit:

```text
head: 0d2c9fac8b425a5910d38c418c718f149f04319b
workflow run: 30092846352
job: 89479813158
conclusion: success
Artifact: 8596349633
Artifact digest: sha256:ce607cc1f4f7ad42d1ede5af1a4b41b402dabda2ae41cbcccb87bc4113654b78
formal state: PRIOR_ONLY_PLAYER_ROTATION_STATE_FEATURE_LAYER_V1_DESIGN_VALID
contract tests: 116 / 116 PASS
Artifact inspected: true
```

A final branch-head validation must also pass after this evidence-binding commit before merge.
