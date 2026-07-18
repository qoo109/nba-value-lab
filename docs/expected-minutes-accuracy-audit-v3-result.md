# Expected Minutes Accuracy Audit v3 — Official Result

更新日期：2026-07-18  
正式狀態：**ACCURACY_PASS**

## Evidence lock

```text
Predeclaration PR: #53
Policy commit: 7f398b9b776a3be2478eed4ad2afc80d4e752e7e
Predeclaration merge: 1f446ff5c503d852a94ccb29e1a519ba7149908a
Execution PR: #54
Verified workflow run: 29634963247
Artifact: expected-minutes-accuracy-audit-v3
Artifact id: 8426868417
Artifact digest: sha256:d550849409d00555d16c83fbfd85eacec65678d50ca651511e1e9d4394a4d66a
```

The v3 policy was frozen before execution and before any v3 accuracy result was observed. All v1/v2 numerical and sample gates were preserved.

## Frozen population and source QA

```text
combined selected games: 293
games with conditional-role rows: 226
selected player snapshot rows: 3,045
identity match rate: 99.7373%
Expected Minutes coverage: 97.4056%
official source coverage: 100%
participation join rate: 99.5061%
UNKNOWN rate: 3.3915%
source-missing games: 0
conditional PLAYED rows: 516
starter rows: 307
bench rows: 209
10+ prior-game rows: 502
complete team-game groups: 450
ambiguous identities: 0
fuzzy identity: false
strict-prior violations: 0
unrecognized team mismatches: 0
```

The observed counts reproduced the frozen census counts exactly.

## Primary estimand

```text
conditional role minutes given official PLAYED label
prediction: prior-only Expected Minutes
label: official target-game actual minutes
```

EXPLICIT_DNP, INACTIVE_OR_NOT_DRESSED, SOURCE_MISSING, UNKNOWN, IDENTITY_MISSING, missing predictions, and the recognized same-day roster transition row were excluded from the primary estimand. They were not imputed as zero.

## Primary accuracy result

| Gate | Result | Threshold | Pass |
|---|---:|---:|:---:|
| Overall MAE | 5.120902 | <= 6.5 | Yes |
| Overall RMSE | 6.693908 | <= 9.0 | Yes |
| Median absolute error | 4.093886 | <= 5.5 | Yes |
| Absolute bias | 0.668968 | <= 2.0 | Yes |
| Improvement vs last prior game | 1.201968 | >= 0.25 | Yes |
| Improvement vs recent-10 mean | 0.093054 | >= 0.0 | Yes |
| Starter MAE | 4.663676 | <= 6.5 | Yes |
| Bench MAE | 5.792521 | <= 7.5 | Yes |
| 10+ history MAE | 5.092724 | <= 6.25 | Yes |
| Complete-team aggregate MAE | 7.012663 | <= 18.0 | Yes |
| Complete-team aggregate absolute bias | 1.387791 | <= 7.0 | Yes |
| Worst monitored subgroup absolute bias | 2.642521 | <= 4.0 | Yes |

All structural, frozen-input integrity, sample, and primary numerical gates passed.

## Secondary diagnostics

Secondary metrics were retained for diagnosis only and were not allowed to override the primary decision.

```text
status-adjusted realized-minutes rows: 2,866
status-adjusted realized-minutes MAE: 2.601208
play-probability rows: 2,934
play-probability Brier: 0.050407
play-probability Log Loss: 0.281879
```

Status weights remain research assumptions; this audit does not validate them as learned probabilities.

## Privacy and leakage boundary

```text
temporary sensitive files deleted: 131
forbidden player-level files retained: 0
player names retained: false
injury reasons retained: false
target-game labels used in prediction: false
missing actual values imputed as zero: false
missing Expected Minutes imputed as zero: false
raw official labels modified: false
```

## Formal decision

```text
expected_minutes_accuracy_audit_v3_passed = true
ready_for_injury_feature_walk_forward_holdout_design_predeclaration = true
ready_for_injury_feature_walk_forward_holdout_execution = false
ready_for_model_training = false
ready_for_probability_adjustment = false
ready_for_betting_edge_claim = false
formal_stake = 0
```

`ACCURACY_PASS` only unlocks a separate Injury Feature Walk-forward Holdout design predeclaration. It does not authorize holdout execution, model activation, probability adjustment, market claims, or nonzero stake.

## Next exact task

```text
Predeclare Injury Feature Walk-forward Holdout
→ freeze baseline/candidate models, folds, features, missingness handling, metrics and promotion gates
→ merge the predeclaration before any holdout result is calculated
```
