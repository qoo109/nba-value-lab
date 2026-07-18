# Expected Minutes Accuracy Audit v3 — Predeclaration

## Roadmap position

This task remains inside Step 3 of the canonical 2026-07-17 roadmap:

```text
Expanded Participation Census v1
→ Expected Minutes Accuracy Audit v3
→ Injury Feature Walk-forward Holdout
→ Timestamped Odds Acquisition
→ Market Backtest
→ CLV／EV／ROI
→ Betting Decision Layer
```

This predeclaration does not execute Accuracy Audit v3 and does not begin Injury Holdout, Timestamped Odds, Market Backtest, model activation, or betting decisions.

## Predeclaration order

The machine-readable policy was committed before any v3 implementation or accuracy result:

```text
data/expected-minutes-accuracy-audit-v3.json
predeclaration commit: 7f398b9b776a3be2478eed4ad2afc80d4e752e7e
```

No v3 MAE, RMSE, bias, subgroup accuracy, baseline comparison, or secondary diagnostic was inspected before this policy was frozen.

## Frozen upstream evidence

Merged census source:

```text
PR #52
merge commit: b2e07050e883cc62c35714406bdab606377d301c
workflow run: 29632917590
artifact: expanded-participation-census-v1
artifact id: 8426181763
digest: sha256:2acdf9c62fb16c19f649fdeffce1fa79261adfba3ee186cf707c77631d5d7ba0
formal state: CENSUS_READY_AUDIT_V3_ELIGIBLE
```

Latest-head validation also passed on run `29633290057`.

The census calculated no accuracy metrics.

## Frozen population

```text
combined independent games: 293
Wave 1: 91
Wave 2: 85
Wave 3: 117
selection: latest feature-ready snapshot at or before T-60m
fallback: none
deduplication key: historical_game_id
```

The selected games, publication timestamps, deterministic identities, prior-only Expected Minutes values, official participation labels, and roster-transition contract may not be changed after v3 accuracy results are observed.

## Frozen input counts

```text
successful official source games: 293
source-missing games: 0
official player rows: 10,309
selected player snapshot rows: 3,045
identity matched rows: 3,037
participation joins: 3,022
UNKNOWN rows: 103
evaluable games: 226
conditional PLAYED rows: 516
starter PLAYED rows: 307
bench PLAYED rows: 209
10+ prior-game PLAYED rows: 502
complete team-game groups: 450
recognized roster-transition rows: 1
unrecognized team mismatches: 0
```

A v3 execution must reproduce these exact input counts before calculating or promoting accuracy results. Any drift is structural blocking, not a reason to edit thresholds.

## Verified same-day roster transition

The frozen evaluation repair remains:

```text
transition id: 2024-02-08-gsw-ind-same-day-trade-v1
historical game: 22300733
date: 2024-02-08
pregame expected team: GSW
official final-roster team: IND
recognized rows: 1
```

The raw official labels are not modified. The exact opponent-team official row is excluded from the target-team evaluation join and is not counted as PLAYED, DNP, or zero minutes. Every other team mismatch remains fatal.

## Primary estimand

```text
conditional role minutes given official PLAYED label
```

Included rows must have:

- official participation label `PLAYED`;
- positive official target-game minutes;
- matched deterministic player identity;
- prior-only Expected Minutes available.

Excluded rows:

- `EXPLICIT_DNP`;
- `INACTIVE_OR_NOT_DRESSED`;
- `SOURCE_MISSING`;
- `UNKNOWN`;
- `IDENTITY_MISSING`;
- missing Expected Minutes;
- the recognized same-day roster-transition row.

Target-game participation, actual minutes, and actual starter／bench role are evaluation labels only. They may not update the prediction.

## Frozen prior-only baselines

```text
last prior-game minutes
recent-10 prior-game mean
current-season prior-game mean
```

Only the first two are promotion comparisons. Current-season mean remains descriptive.

## Preserved structural and sample gates

No v1／v2 sample gate was lowered:

```text
combined selected games: exactly 293
games with evaluable PLAYED rows: at least 150
selected player snapshot rows: at least 1,500
official source coverage: 100%
identity match rate: at least 95%
Expected Minutes coverage: at least 85%
participation join rate: at least 99%
UNKNOWN rate: at most 5%
source-missing games: 0
conditional PLAYED rows: at least 500
starter PLAYED rows: at least 150
bench PLAYED rows: at least 200
10+ prior-game PLAYED rows: at least 400
complete team-game groups: at least 100
recognized roster-transition rows: exactly 1
unrecognized team mismatches: 0
strict-prior violations: 0
ambiguous identities: 0
fuzzy identity: false
duplicate selected, accuracy, and official game-player rows: 0
invalid participation labels and minutes combinations: 0
forbidden player-level retained files: 0
```

The 99% participation-join gate preserves the stricter expanded census contract and is stronger than the 95% v2 minimum.

## Preserved primary accuracy gates

Every v1／v2 numerical gate is unchanged:

```text
overall MAE: at most 6.5 minutes
overall RMSE: at most 9.0 minutes
overall median absolute error: at most 5.5 minutes
absolute overall bias: at most 2.0 minutes
MAE improvement vs last prior game: at least 0.25 minutes
MAE improvement vs recent-10 mean: at least 0.0 minutes
starter MAE: at most 6.5 minutes
bench MAE: at most 7.5 minutes
10+ prior-game MAE: at most 6.25 minutes
complete-team played aggregate MAE: at most 18 minutes
absolute complete-team played aggregate bias: at most 7 minutes
monitored subgroup absolute bias: at most 4 minutes for groups with 50+ rows
```

## Required subgroups

```text
availability_status
participation_label
actual_role
expected_minutes_method
prior_game_count_band
expected_minutes_band
days_since_latest_prior_game_band
source_wave
```

Groups below 50 rows remain descriptive and do not create a monitored subgroup bias gate.

## Secondary diagnostics

Status-adjusted realized minutes and status play probability remain secondary diagnostics only. They cannot override structural failure or a primary accuracy failure and do not validate the research status weights.

## Formal decision states

```text
STRUCTURAL_BLOCKED
VALID_NEGATIVE_RESULT
ACCURACY_PASS
```

- `STRUCTURAL_BLOCKED`: any structural or frozen-input integrity gate fails. Numerical results, if produced, remain descriptive only.
- `VALID_NEGATIVE_RESULT`: all structural gates pass, but one or more primary accuracy gates fail.
- `ACCURACY_PASS`: all structural, frozen-input integrity, and primary accuracy gates pass.

A valid negative result is mergeable and must not trigger threshold edits.

## Promotion boundary

Even `ACCURACY_PASS` may only unlock a separate Injury Feature Walk-forward Holdout **design predeclaration**.

It does not directly enable:

```text
Injury Holdout execution
model training
probability adjustment
betting-edge claims
nonzero stake
```

Formal stake remains `0`.

## Next exact task after this predeclaration

```text
merge the v3 predeclaration
→ implement the audit against the exact frozen 293-game inputs
→ produce aggregate-only Artifact QA
→ record STRUCTURAL_BLOCKED, VALID_NEGATIVE_RESULT, or ACCURACY_PASS
```

No holdout or odds work may begin before the formal v3 decision.
