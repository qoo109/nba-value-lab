# Historical Silver 2023-24 Source-gap Exception Integration — Real-reference Validation Request v1

## Request

```text
HISTORICAL-SILVER-2023-24-SOURCE-GAP-EXCEPTION-INTEGRATION-REAL-REFERENCE-VALIDATION-2026-07-22-001
```

This record requests one future validation of the already synthetic-validated pure aggregate transformer against committed aggregate reference records.

It does **not** grant approval and does **not** enable execution.

## Requested action

```text
VALIDATE_AGGREGATE_TRANSFORMER_AGAINST_COMMITTED_REAL_REFERENCE_RECORDS_ONCE
```

The transformer is:

```text
scripts/integrate_historical_silver_source_gap_exception_v1.py
```

The request validator must compute and publish SHA-256 values for both this request file and the implementation module. A later approval record must bind both exact digests and the exact request ID.

## Allowed committed inputs

Only these repository records may be read by a future approved validation:

```text
data/research/historical-gold-silver-coverage-real-reference-result-v1.json
data/research/historical-silver-2023-24-source-gap-exception-manifest-v1.json
data/research/historical-silver-2023-24-source-gap-exception-integration-policy-v1.json
```

No additional paths are authorized.

The future validation may not read or rebuild databases, source archives, raw CSV files, Silver rows, Gold rows, or network resources.

## One-time lifecycle

```text
maximum execution count: 1
current execution count: 0
request consumed: false
repeat execution allowed: false
workflow_dispatch only: true
automatic dispatch allowed: false
explicit user approval required: true
approval granted: false
execution enabled: false
```

Any future execution attempt consumes this request, including a blocked or failed attempt. The request may never be reused afterward.

## Separate approval requirement

A later approval must be a different immutable record and must bind:

```text
exact request ID
request file SHA-256 from request validation Artifact
implementation module SHA-256 from request validation Artifact
repository owner identity
maximum execution count = 1
```

The approval may not broaden the allowed input paths, introduce network access, or enable automatic dispatch.

## Expected aggregate result

When every frozen recognition condition matches, the expected result is:

```text
raw Silver games: 5,826
raw Gold matchups: 5,824
raw missing Gold for Silver: 2
documented source-gap exceptions: 2
unexplained missing after documentation: 0
covered or documented: 5,826
Gold dataset complete: false
recognition gate passed: true
```

These fields are reporting annotations only. The raw Gold count stays `5,824`; the dataset is not rewritten as complete.

On a semantic mismatch, the transformer must fail closed and report zero documented exceptions while preserving the raw gap as unexplained.

## Privacy and output boundary

A future approved run may emit one aggregate JSON Artifact under 1 MiB. It may not emit:

```text
game_id
game_date
home_team_abbr
away_team_abbr
team_code
source_file_path
source_file_hash
row_level_record
row_key_hash
raw rows
raw files
```

## This request does not authorize

- an approval record;
- an execution workflow;
- real-reference validation in this PR;
- Analyzer modification or replacement;
- Silver or Gold builder changes;
- database writes, replacements, or row patches;
- manual row insertion;
- cross-source audit reruns;
- Opening／Closing semantics;
- market backtests, CLV, EV, ROI, or Drawdown;
- model training or retraining;
- betting-edge claims;
- formal Stake above `0`.

## State after request validation

```text
HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_REAL_REFERENCE_VALIDATION_REQUEST_VALID_AWAITING_EXPLICIT_USER_APPROVAL
```

The next controlled step is a separate explicit approval record. Until that record is reviewed and validated, no real-reference execution is allowed.
