# Eoin Post-execution Role Review Evaluation v1

## Purpose

This evaluator applies the frozen post-execution role review policy to the
aggregate evidence already embedded in the policy JSON.

It does not download an Artifact, contact Kaggle, execute the Eoin bundle, or
read raw Eoin rows.

## Inputs

```text
data/eoin-post-execution-role-review-policy-v1.json
data/eoin-post-execution-role-review-evaluation-v1.json
```

The policy contains the reviewed evidence anchors for:

- cross-source audit run `29672984966`;
- one-time aggregate execution run `29680729672`;
- the consumed request `EOIN-FULL-ADAPTER-2026-07-19-001`.

No external files are fetched during evaluation.

## Outcome Logic

The evaluator can produce exactly three outcomes:

```text
ROLE_LIMITED_SECONDARY_QA_SOURCE_VALIDATED
RETAIN_ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE
POST_EXECUTION_ROLE_REVIEW_BLOCKED
```

Rules:

1. A manifest, policy-structure, or safety-boundary failure produces
   `POST_EXECUTION_ROLE_REVIEW_BLOCKED`.
2. A structurally valid policy with one or more scientific gate failures
   produces `RETAIN_ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE`.
3. A structurally valid policy with every frozen scientific gate passing
   produces `ROLE_LIMITED_SECONDARY_QA_SOURCE_VALIDATED`.

Scientific evidence failures are evaluated separately from policy-structure
failures. This prevents a below-threshold scientific result from being
misclassified as an infrastructure or safety-policy error.

## Frozen Scientific Gates

```text
cross-source matched games >= 1,000
game identity match rate >= 98%
final score match rate >= 98%
team boxscore coverage >= 98%
team boxscore score match >= 98%
player candidate coverage >= 95%
PBP game coverage >= 95%
full-bundle aggregate games >= 1,000
duplicate game_id groups = 0
request consumed = true
execution count <= 1
raw rows emitted = 0
raw files emitted = false
```

## Expected Frozen-evidence Result

The evidence currently frozen in the policy is expected to produce:

```text
ROLE_LIMITED_SECONDARY_QA_SOURCE_VALIDATED
```

This role means only that Eoin may be used as a role-limited secondary QA and
cross-source regression-check source for the approved domains.

It does not establish a primary or production data role.

## Allowed QA Scope

A validated role may cover:

- deterministic game identity QA;
- final score QA;
- team boxscore coverage and score QA;
- player boxscore candidate coverage-only;
- PBP game coverage QA;
- cross-source regression detection.

Player statistics remain coverage-only and do not establish independent
player-stat parity.

## Permanently Locked

Regardless of evaluation outcome, the evaluator does not allow:

- primary-source designation;
- Historical Silver or Historical Gold replacement;
- independent player-stat parity claims;
- player feature import;
- model training or retraining;
- market backtest, CLV, EV, ROI, or Drawdown;
- betting-decision activation or betting-edge claims;
- repeat execution of the consumed request;
- non-zero Stake.

## Runtime Boundary

The evaluation workflow:

- uses no network calls;
- performs no new bundle execution;
- downloads no external Artifacts;
- reads no raw Eoin rows;
- emits one aggregate JSON report only;
- emits no raw rows, raw files, archives, or derived tables.

A green workflow is not sufficient by itself. The generated Artifact must be
inspected before the result is merged into `PROJECT_STATUS.md` or
`data/source-registry.json`.
