# Historical Silver 2023-24 Source-gap Exception Integration — Real-reference Validation Request Design v1

## Purpose

This design freezes the request contract for one future real-reference validation of the already validated synthetic transformer:

```text
scripts/integrate_historical_silver_source_gap_exception_v1.py
```

The future validation may read only committed aggregate JSON records. It may not rebuild or read databases, source archives, CSV files, Silver rows, Gold rows, or any row-level identifiers.

## Triggering state

```text
HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_IMPLEMENTATION_VALIDATED_SYNTHETIC_ONLY
```

The transformer has already passed synthetic and mutation testing. This design does not execute it against the committed real-reference aggregate report.

## Future request lifecycle

The future request must be a separate immutable record with:

```text
maximum execution count: 1
initial execution count: 0
workflow_dispatch only: true
explicit user approval required: true
automatic dispatch: false
request reuse after any execution attempt: false
```

Approval must be created separately and must bind the exact request ID, request SHA-256, and implementation module SHA-256.

## Allowed committed aggregate inputs

```text
data/research/historical-gold-silver-coverage-real-reference-result-v1.json
data/research/historical-silver-2023-24-source-gap-exception-manifest-v1.json
data/research/historical-silver-2023-24-source-gap-exception-integration-policy-v1.json
```

No network download or temporary database reconstruction is allowed.

## Expected aggregate result

A successful future validation is expected to preserve the raw report and add documented exception reporting:

```text
raw Silver games: 5,826
raw Gold matchups: 5,824
raw missing Gold for Silver: 2
documented source-gap exceptions: 2
unexplained missing after documentation: 0
covered or documented: 5,826
Gold dataset complete: false
recognition gate passed: true
exception code: SOURCE_ARCHIVE_PBPSTATS_GAME_ABSENT
```

These are validation expectations, not authorization to rewrite the raw Gold count or declare the Gold dataset complete.

## Output boundary

The future workflow may upload one aggregate JSON Artifact under 1 MiB. It must not include:

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
```

The output must include an aggregate validation receipt recording the request ID, run metadata, execution count, consumed state, real-reference validation flag, access boundaries, and Stake `0`.

## Failure behavior

- Structural or privacy failures stop before output.
- Request or approval binding failures stop before real-reference validation.
- Semantic mismatches may emit only a fail-closed aggregate result with zero recognized exceptions and the raw gap left unexplained.
- Any execution attempt consumes the request; repeat execution is prohibited.

## Not authorized

This design does not authorize or perform:

- creation of the real request record;
- explicit approval;
- an execution workflow;
- real-reference transformer execution;
- Analyzer replacement or modification;
- Silver or Gold builder changes;
- database writes or Historical Silver／Gold replacement;
- row patches, imputation, copied features, or manual insertion;
- cross-source audit reruns;
- market backtests, Opening／Closing semantics, CLV, EV, ROI, or Drawdown;
- model training or betting-edge claims;
- Stake above `0`.

## Next state after validation

```text
HISTORICAL_SILVER_2023_24_SOURCE_GAP_EXCEPTION_INTEGRATION_REAL_REFERENCE_VALIDATION_REQUEST_READY_FOR_DRAFT
```

The next PR may create the immutable request draft and its validator. It still may not grant approval or execute real-reference validation.
