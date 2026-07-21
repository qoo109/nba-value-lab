# Eoin Secondary QA Integration Policy v1

## Purpose

This policy defines the only integration path unlocked by the reviewed Eoin
role:

```text
ROLE_LIMITED_SECONDARY_QA_SOURCE_VALIDATED
```

The integration is an **alert-only evidence-contract monitor**. It does not
read Eoin source rows, download Kaggle data, execute the consumed full-adapter
request, or mutate any NBA Value Lab data or model output.

## Pinned Evidence

The contract pins four reviewed evidence groups:

1. Eoin cross-source audit:
   - run `29672984966`;
   - Artifact `8437932113`;
   - digest `sha256:96a87c6b52614ea6f7478e1bdbcc729c7c8eb2347490ca236475444ca5fcc63a`.
2. One-time aggregate execution:
   - run `29680729672`;
   - Artifact `8440485189`;
   - digest `sha256:e068940df05bfc51d8757aef500e9c6f812687bfa171b5fff8680ee3b59bb56c`;
   - request consumed after one execution.
3. Post-execution role review policy:
   - run `29794965150`;
   - Artifact `8481660306`;
   - digest `sha256:1b309073ae19c23483225b1264ea982ef1f6d71f1d482cd124ad63fc0bfd77d0`.
4. Role review evaluation:
   - run `29795498102`;
   - Artifact `8481840798`;
   - digest `sha256:f64248d5a3eaab52aa6a24fc36980144c5c962a31b91a4057834af1d36e42fd1`.

Unreviewed evidence substitution is forbidden.

## Allowed Integration Functions

A later contract monitor may perform only:

- contract integrity checks;
- pinned Artifact identity and digest checks;
- formal-role consistency checks;
- forbidden-permission regression checks;
- evidence-freshness checks;
- deterministic QA-domain registry checks;
- alert-summary generation.

Allowed QA domains remain:

```text
game_identity_qa
final_score_qa
team_boxscore_qa
player_boxscore_candidate_coverage_only
pbp_game_coverage_qa
cross_source_regression_detection
```

## Alert-only Targets

The integration may update only research alert metadata, source-registry alert
metadata, and QA dashboard metadata.

It may not become a gate or input for:

- Historical Silver builds;
- Historical Gold builds;
- player feature pipelines;
- model training or retraining;
- market backtests;
- betting decisions.

## Fail-closed Behaviour

```text
contract mismatch              -> alert and disable QA integration
Artifact identity mismatch     -> alert and disable QA integration
formal-role drift              -> alert and disable QA integration
forbidden permission enabled   -> blocked
stale evidence                 -> alert and disable QA integration
missing required evidence      -> blocked
```

An alert must never mutate primary data, derived tables, model outputs, market
outputs, or Stake.

## Freshness Policy

```text
evidence as of: 2026-07-21
review interval: 365 days
review due: 2027-07-21
stale behaviour: ALERT_AND_DISABLE_QA_INTEGRATION
automatic source re-execution: false
```

Any new source execution requires a separate policy and explicit approval. The
consumed request cannot be reused.

## Output Boundary

A later monitor may emit one aggregate JSON report no larger than 1 MiB.

It must emit:

```text
raw rows: 0
raw files: false
derived tables: false
archives or databases: false
```

## Permanently Locked

This policy does not authorize:

- primary-source designation;
- Historical Silver or Gold replacement;
- independent player-stat parity;
- player feature import;
- model training or retraining;
- market backtest, CLV, EV, ROI, or Drawdown;
- betting-decision activation or betting-edge claims;
- repeat full-bundle execution;
- non-zero Stake.

## Expected Validation State

```text
EOIN_SECONDARY_QA_INTEGRATION_POLICY_READY_FOR_IMPLEMENTATION
```

A passing policy only allows creation of a separate contract-monitor
implementation. The integration remains inactive until that implementation is
reviewed and merged.
