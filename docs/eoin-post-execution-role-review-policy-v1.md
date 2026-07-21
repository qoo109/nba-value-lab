# Eoin Post-execution Role Review Policy v1

## Purpose

This policy freezes the next research step after the completed one-time Eoin
full-adapter aggregate validation.

It does **not** promote the source by itself. It only defines whether a later,
separate evaluator may review the existing evidence for a more explicit
role-limited secondary QA designation.

## Current Role

```text
ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE
```

The current role remains unchanged until a later evaluation implementation is
predeclared, validated, reviewed, and merged.

## Evidence Anchors

### Cross-source audit

```text
workflow run: 29672984966
artifact id: 8437932113
artifact digest: sha256:96a87c6b52614ea6f7478e1bdbcc729c7c8eb2347490ca236475444ca5fcc63a
reference games: 1,230
matched games: 1,230
game identity match rate: 100%
final score match rate: 99.9187%
team boxscore coverage: 100%
team score match: 99.9187%
player candidate coverage: 100% coverage-only
PBP game coverage: 100%
```

### One-time aggregate execution

```text
formal state: ONE_TIME_FULL_ADAPTER_AGGREGATE_VALIDATION_PASS
workflow run: 29680729672
artifact id: 8440485189
artifact digest: sha256:e068940df05bfc51d8757aef500e9c6f812687bfa171b5fff8680ee3b59bb56c
request id: EOIN-FULL-ADAPTER-2026-07-19-001
request consumed: true
execution count: 1
games: 1,383
duplicate game_id groups: 0
raw rows emitted: 0
raw files emitted: false
```

## Allowed Review Domains

A later evaluator may review only:

- deterministic game identity QA;
- final score QA;
- team boxscore coverage and score QA;
- player boxscore candidate coverage-only;
- PBP game coverage QA;
- cross-source regression detection.

Player statistics remain **coverage-only**. The evidence does not establish
independent player-stat parity.

## Frozen Gates

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

## Candidate Later Outcomes

```text
ROLE_LIMITED_SECONDARY_QA_SOURCE_VALIDATED
RETAIN_ROLE_LIMITED_SECONDARY_SOURCE_ELIGIBLE
POST_EXECUTION_ROLE_REVIEW_BLOCKED
```

The maximum possible role under this policy is:

```text
ROLE_LIMITED_SECONDARY_QA_SOURCE_VALIDATED
```

This label would still mean a secondary QA/cross-check source only.

## Permanently Locked by This Policy

This policy does not allow:

- primary-source designation;
- Historical Silver replacement;
- Historical Gold replacement;
- independent player-stat parity claims;
- player feature import;
- model training or retraining;
- market backtest, CLV, EV, ROI, or Drawdown;
- betting decision activation or betting-edge claims;
- repeat execution of the consumed request;
- non-zero Stake.

## Validation Boundary

The policy validator:

- reads the policy JSON only;
- makes no network calls;
- does not download or execute the Eoin bundle;
- reads no raw Eoin rows;
- emits one small aggregate JSON report;
- leaves the current source role unchanged.

Expected policy validation state:

```text
EOIN_POST_EXECUTION_ROLE_REVIEW_POLICY_READY
```

A passing policy only unlocks design of a separate evaluation implementation.
It is not a source promotion result.
