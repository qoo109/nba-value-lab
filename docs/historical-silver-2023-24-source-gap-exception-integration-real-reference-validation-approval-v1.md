# Historical Silver 2023-24 Source-gap Exception Integration — Real-reference Validation Approval v1

## Approval

The repository owner explicitly affirmed the immediately preceding approval request in the ChatGPT project conversation with:

```text
好的繼續
```

The immediately preceding request was:

```text
我批准 Request 001 依已驗證的 Request SHA-256 與 Transformer SHA-256，建立單次 aggregate-only real-reference validation 執行流程；最大執行次數 1，Stake 維持 0。
```

This approval is therefore recorded as an explicit affirmation of that exact scope. It does not authorize any broader activity.

## Immutable bindings

```text
request id:
HISTORICAL-SILVER-2023-24-SOURCE-GAP-EXCEPTION-INTEGRATION-REAL-REFERENCE-VALIDATION-2026-07-22-001

request file SHA-256:
sha256:192a06862fe830027686d149d36572b4ad76ea609f489c6a3d540b7ea4b27e97

transformer SHA-256:
sha256:c4bd7ccb05bcf78747a7210e0eefad083d599de2ca8b0d44c9c455006f084cbc

request validation run: 29913352533
request validation artifact: 8526880141
artifact digest:
sha256:63f5ca853727d2530cff9bc9bf1b6eb92b3a1841f90668ecdcfb0a01018b9200
```

The approval validator recomputes both file hashes from the repository and fails closed if either binding changes.

## Authorized next action

This approval authorizes creation of a separately validated one-time `workflow_dispatch` execution workflow. It does not itself create or execute that workflow.

```text
maximum execution count: 1
execution count before approval: 0
workflow_dispatch only: true
automatic dispatch: false
approved ref: refs/heads/main
repeat execution allowed: false
```

## Allowed committed inputs

Only these committed aggregate JSON records may be read by the future executor:

```text
data/research/historical-gold-silver-coverage-real-reference-result-v1.json
data/research/historical-silver-2023-24-source-gap-exception-manifest-v1.json
data/research/historical-silver-2023-24-source-gap-exception-integration-policy-v1.json
```

No additional paths, database files, source archives, CSV files, raw rows, network downloads, or temporary reference rebuilds are allowed.

## Expected aggregate result

```text
raw Silver games: 5,826
raw Gold matchups: 5,824
raw missing Gold for Silver: 2
documented exceptions: 2
unexplained missing after documentation: 0
covered or documented: 5,826
Gold dataset complete: false
recognition gate passed: true
```

The future validation must preserve the raw report without mutation and fail closed on any semantic mismatch.

## Output boundary

Only one aggregate JSON Artifact may be emitted, with a maximum size of 1 MiB. It may not contain game IDs, dates, team abbreviations, source paths, source hashes, row-level records, or row-key hashes.

## Not authorized

This approval does not authorize:

- Analyzer or transformer modification;
- Silver or Gold builder changes;
- Silver or Gold database writes or replacement;
- row patches, manual insertion, or imputation;
- cross-source audit reruns;
- Opening／Closing semantics or market backtests;
- CLV, EV, ROI, Drawdown;
- model training or retraining;
- betting-edge claims;
- Stake above `0`.

## State after approval validation

```text
HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_REAL_REFERENCE_VALIDATION_ONE_TIME_EXECUTION_WORKFLOW_READY_FOR_IMPLEMENTATION
```

Real-reference validation remains unexecuted until a separate executor and manual workflow pass validation and are dispatched exactly once.
