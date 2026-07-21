# Eoin Secondary QA Contract Monitor v1

## Purpose

The contract monitor activates only the alert layer allowed by the Eoin
secondary QA integration policy.

It verifies that the reviewed evidence, source role, request-consumption state,
forbidden permissions, freshness deadline, `PROJECT_STATUS.md`, and
`data/source-registry.json` remain consistent.

It does not access the Eoin dataset.

## Healthy State

```text
EOIN_SECONDARY_QA_CONTRACT_HEALTHY
```

A healthy state means the evidence contract remains internally consistent and
alert metadata may be published.

It does not mean source data is integrated into Historical Silver, Historical
Gold, features, models, market backtests, or betting decisions.

## Other States

```text
EOIN_SECONDARY_QA_CONTRACT_ALERT_DISABLED
EOIN_SECONDARY_QA_CONTRACT_BLOCKED
```

`ALERT_DISABLED` is used for reviewed-contract drift or stale evidence. The
secondary QA alert integration is disabled, but no primary data is changed.

`BLOCKED` is used for structural safety failures such as missing required
source records, invalid integration policy, or an enabled forbidden
permission.

## Monitored Contract

The monitor reads only committed project metadata:

- `PROJECT_STATUS.md`;
- `data/source-registry.json`;
- `data/eoin-cross-source-audit-v1.json`;
- `data/eoin-post-execution-role-review-policy-v1.json`;
- `data/eoin-post-execution-role-review-evaluation-v1.json`;
- `data/eoin-secondary-qa-integration-policy-v1.json`.

It validates:

- integration-policy structure;
- formal-role consistency;
- source-registry role and evaluation evidence;
- consumed request and disabled repeat execution;
- pinned Artifact IDs and digests;
- forbidden-permission regressions;
- evidence freshness;
- approved deterministic QA domains.

## Current Freshness Window

```text
evidence as of: 2026-07-21
review due: 2027-07-21
```

After the due date, the monitor must return
`EOIN_SECONDARY_QA_CONTRACT_ALERT_DISABLED` until a separately reviewed policy
refreshes the evidence contract.

It must not automatically re-execute the Eoin bundle.

## Runtime Boundary

The monitor:

- performs no network calls;
- downloads no external Artifacts;
- executes no Eoin bundle;
- reads no raw Eoin rows, archives, or databases;
- performs no fuzzy matching;
- mutates no data, feature, model, market, or betting output;
- emits one aggregate JSON report only.

## Permanent Permissions Boundary

Even when healthy:

```text
primary source use: false
Historical Silver replacement: false
Historical Gold replacement: false
player-stat parity: false
player feature import: false
model training or retraining: false
market backtest: false
CLV / EV / ROI / Drawdown: false
betting decision layer: false
betting-edge claim: false
repeat full-bundle execution: false
formal Stake: 0
```

## Self-tests

The implementation includes deterministic tests for:

- current healthy contract;
- stale evidence producing alert-disabled;
- registry-role drift producing alert-disabled;
- forbidden model permission producing blocked;
- missing Eoin registry record producing blocked.

## Artifact Review

The workflow uploads only:

```text
eoin-secondary-qa-contract-monitor-v1-report.json
```

A green workflow must still be followed by Artifact inspection before the
monitor is recorded as implemented and active for alerts.
