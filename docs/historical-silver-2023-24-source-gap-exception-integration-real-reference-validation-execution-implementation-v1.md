# Historical Silver 2023-24 Source Gap Exception Integration — Real-reference Validation Execution Implementation v1

## Status

```text
formal state:
HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_REAL_REFERENCE_VALIDATION_ONE_TIME_EXECUTION_WORKFLOW_IMPLEMENTATION_VALIDATED_NOT_EXECUTED

request id:
HISTORICAL-SILVER-2023-24-SOURCE-GAP-EXCEPTION-INTEGRATION-REAL-REFERENCE-VALIDATION-2026-07-22-001

execution count: 0 / 1
request consumed: false
real-reference validation executed: false
formal Stake: 0
```

## Purpose

This stage creates the separately approved one-time execution path for validating the existing pure aggregate transformer against committed aggregate reference records.

It does **not** dispatch the workflow. The implementation validation workflow uses synthetic fixtures and static contract checks only.

## Immutable bindings

```text
Request SHA-256:
sha256:192a06862fe830027686d149d36572b4ad76ea609f489c6a3d540b7ea4b27e97

Transformer SHA-256:
sha256:c4bd7ccb05bcf78747a7210e0eefad083d599de2ca8b0d44c9c455006f084cbc
```

The manual runner recomputes both digests before reading any committed real-reference input.

## Allowed committed inputs

Only these three JSON files may be supplied:

```text
data/research/historical-gold-silver-coverage-real-reference-result-v1.json
data/research/historical-silver-2023-24-source-gap-exception-manifest-v1.json
data/research/historical-silver-2023-24-source-gap-exception-integration-policy-v1.json
```

The flattened coverage result is converted in memory into the frozen aggregate transformer input schema. No row-level source material is created or read.

## Runner

```text
scripts/run_historical_silver_source_gap_exception_integration_real_reference_validation_once_v1.py
```

The runner:

- revalidates the request, approval, approval status, exact Request SHA-256 and exact Transformer SHA-256;
- requires `workflow_dispatch`, `refs/heads/main`, the exact Request ID and execution count `0`;
- rejects any input path outside the three approved committed aggregate JSON files;
- adapts only aggregate coverage counts in memory;
- invokes `integrate_documented_source_gap` without modifying the transformer;
- emits one aggregate JSON result smaller than 1 MiB;
- records execution count `1`, request consumed `true`, and repeat execution `false` after an execution attempt;
- fails closed on admission, structural, semantic or privacy-boundary mismatches.

## Manual workflow

```text
.github/workflows/run-approved-historical-silver-source-gap-exception-integration-real-reference-validation-once-v1.yml
```

The workflow has only a `workflow_dispatch` trigger. It is additionally gated by:

```text
github.ref == refs/heads/main
github.run_attempt == 1
exact request_id input
```

It uploads exactly one aggregate result Artifact. It does not download network data, build a database, read a source archive or run a cross-source audit.

## Implementation validation

```text
scripts/validate_historical_silver_source_gap_exception_integration_real_reference_validation_execution_implementation_v1.py
.github/workflows/validate-historical-silver-source-gap-exception-integration-real-reference-validation-execution-implementation-v1.yml
```

Implementation validation performs:

- Python compilation;
- static runner and workflow contract checks;
- at least 20 fail-closed mutation tests;
- at least 15 synthetic transformer/adapter tests;
- confirmation that governed inputs, the analyzer and the transformer are unchanged;
- confirmation that no committed real-reference input is read during implementation validation.

## Expected aggregate result

A successful future manual run must preserve:

```text
raw Silver games: 5,826
raw Gold matchups: 5,824
raw missing Gold for Silver: 2
documented source gap exceptions: 2
unexplained missing after documentation: 0
covered or documented: 5,826
Gold dataset complete: false
recognition gate passed: true
formal Stake: 0
```

## Prohibited activity

This implementation does not authorize:

- database, source archive, CSV or network access;
- raw row reads or row-level output;
- identifiers, dates, team codes, file paths or row-key hashes in output;
- Silver or Gold writes or replacement;
- analyzer or transformer modification;
- source-gap row patches or manual row insertion;
- cross-source audit reruns;
- Opening／Closing or point-in-time market semantics;
- CLV, EV, ROI or Drawdown;
- model training or retraining;
- betting-edge claims;
- Stake above `0`.

## Next controlled state

After implementation CI succeeds and the PR is merged:

```text
HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_REAL_REFERENCE_VALIDATION_READY_FOR_MANUAL_DISPATCH
```

The one-time workflow still requires a deliberate manual dispatch from `main` with the exact Request ID.
