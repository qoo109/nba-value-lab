# Historical Silver source-gap exception real-reference validation — admission incident v1

Date: 2026-07-22  
Request: `HISTORICAL-SILVER-2023-24-SOURCE-GAP-EXCEPTION-INTEGRATION-REAL-REFERENCE-VALIDATION-2026-07-22-001`

## Observed failure

The first manual `workflow_dispatch` run failed in approximately 15 seconds. The user-provided GitHub Actions screenshot showed:

```text
workflow run number: 1
job: execute-once
status: Failure
process exit code: 2
execution result Artifact path: missing
```

The exact GitHub run ID was not available in the screenshot and is therefore intentionally not guessed.

## Root cause

The failure occurred in the validate-only admission step before any governed aggregate input was read.

The v1 runner required this approval status:

```text
HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_REAL_REFERENCE_VALIDATION_APPROVAL_VALID
```

The immutable committed approval current-status record correctly remained in this lifecycle state:

```text
HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_REAL_REFERENCE_VALIDATION_APPROVAL_VALID_PENDING_EXECUTION_WORKFLOW_IMPLEMENTATION
```

The approval itself was valid. The mismatch was only between the runner's admission constant and the committed lifecycle status record.

## Consumption decision

The failed run did not pass validate-only admission and did not reach the non-validate-only execution step. Therefore:

```text
execution count: 0 / 1
request consumed: false
real-reference inputs read: false
transformer executed: false
execution receipt created: false
result Artifact created: false
```

The request remains eligible for one controlled manual retry after the fix is merged. This is not a repeat execution because the governed execution step was never attempted.

## Fix

A compatibility wrapper binds the unchanged v1 runner's admission gate to the exact committed approval current-status lifecycle state:

```text
scripts/run_historical_silver_source_gap_exception_integration_real_reference_validation_once_v2.py
```

The wrapper does not modify:

- the approved Request ID;
- Request SHA-256;
- Transformer SHA-256;
- the core v1 execution logic;
- the three approved committed aggregate inputs;
- aggregate-only output restrictions;
- one-time consumption semantics;
- Stake `0`.

A dedicated validator executes the real admission gate against the committed Request, approval and approval-status records without reading the three governed aggregate inputs. It also runs fail-closed mutation tests for status, hashes, owner, dispatch event, branch, execution count, automatic dispatch and Stake.

## Boundaries preserved

```text
network access: false
database access: false
source archive access: false
raw CSV access: false
raw rows read: false
Silver or Gold write: false
cross-source audit rerun: false
market backtest: false
model retraining: false
betting-edge claim: false
formal Stake: 0
```
