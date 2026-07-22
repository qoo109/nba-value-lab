# Historical Silver missing-team-features root-cause incident — Run 29888939524

日期：2026-07-22

## Result

Run `29888939524` reached the approved root-cause workflow but stopped before producing a scientific root-cause result.

Formal state:

```text
HISTORICAL_SILVER_2023_24_MISSING_TEAM_FEATURES_ROOT_CAUSE_BLOCKED_BEFORE_RESULT
```

## Root Cause

The executor read the rebuilt Historical Silver report with the wrong field path:

```text
report["quality"]["team_inference_failures"]
```

The actual field lives under:

```text
report["sources"]["pbpstats_2023"]["team_inference_failures"]
```

This caused:

```text
KeyError: 'team_inference_failures'
```

## Completed Before The Failure

- Approval validation passed: `80 / 80`.
- Workflow event and `main` branch binding passed.
- The executor entered the approved one-time path.
- One aggregate-only JSON artifact was uploaded.

## Not Completed

- No formal root-cause classification was produced.
- No Silver builder repair was authorized or performed.
- No Historical Silver or Gold replacement was authorized or performed.
- No cross-source audit rerun, market backtest, CLV, EV, ROI, Drawdown, model retraining, betting edge claim, or non-zero Stake was authorized.

## Output Boundary

Artifact `8517546804` contained one aggregate JSON report only.

No Candidate CSV, Gold database, source archive, raw row, Silver database, game ID, date, team code, row-level record, or row-key hash was uploaded.

## Request Consumption

Request `HISTORICAL-SILVER-2023-24-MISSING-BOTH-TEAM-FEATURES-ROOT-CAUSE-2026-07-21-001` recorded one execution attempt and must not be reused.

A repaired retry requires a new explicit request and a fresh user approval.

## Repair

The repair changes the executor to read `team_inference_failures` from the `pbpstats_2023` source report and adds a self-test for the rebuild summary shape.

The approved diagnostic scope, aggregate-only output boundary, and formal Stake `0` remain unchanged.
