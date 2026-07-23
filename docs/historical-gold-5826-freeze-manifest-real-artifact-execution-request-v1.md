# Historical Gold 5,826 freeze-manifest real Artifact execution request v1

## Purpose

Create the immutable request record for one future, separately approved, manual GitHub Actions execution that may read the exact adopted Historical Gold Artifact and produce an aggregate semantic freeze manifest.

This request does **not** grant approval, enable execution, create an execution workflow, download or read the Artifact, create the canonical manifest, or freeze the corpus.

## Request identity

```text
request ID:
HISTORICAL-GOLD-5826-FREEZE-MANIFEST-REAL-ARTIFACT-EXECUTION-2026-07-23-001

maximum execution attempts: 1
current execution count: 0
request consumed: false
repeat allowed: false
workflow dispatch only: true
automatic dispatch: false
formal Stake: 0
```

## Exact source binding

```text
source workflow run: 29976204693
source workflow job: 89108363564
Artifact ID: 8551587005
Artifact name: historical-silver-gold-two-game-official-cdn-recovery-v2
Artifact archive size: 374,591,375 bytes
Artifact archive digest:
sha256:3ed2d28da3af58b8b72d805860a144541ac5f38106653cfbda593e16bbaa8e8d
Artifact expiry: 2026-08-06T03:14:00Z
```

No silent rebuild or substitution is allowed. Missing, expired, renamed, resized, or mismatched Artifact evidence blocks execution.

## Exact Artifact file set

The Artifact must contain exactly three files:

```text
historical-silver-multiseason-recovered-v1.sqlite.gz
historical-gold-multiseason-recovered-v1.sqlite.gz
two-game-official-cdn-pbp-recovery-result-v2.json
```

Silver is evidence-only and must not be read. Gold may be decompressed only into temporary runner storage and opened read-only. The aggregate recovery result must match its committed copy.

## Upstream scientific bindings

The request validator computes SHA-256 values for:

```text
request file
validated manifest builder
synthetic implementation result
freeze policy
recovery current-status record
request-design file
```

A later approval must bind every computed value. Approval may not replace or modify the builder, policy, synthetic result, recovery state, Artifact identity, file set, output contract, or execution count.

The approval must be a new, explicit user decision made after this request has passed validation. Generic continuation wording used to create this request does not grant execution approval.

## Future execution boundary

A later approved workflow may use only:

```text
actions/checkout@v4
actions/setup-python@v5
actions/download-artifact@v4
actions/upload-artifact@v4
Python 3.12 standard library
GitHub Actions Artifact transport
```

It may not use generic HTTP, curl, wget, package installation, source archives, odds data, injury data, Silver reads, SQLite writes, database rebuilds, or source-recovery reruns.

## Expected aggregate result

```text
Gold matchup rows: 5,826
Gold team-game rows: 11,652
seasons: 2019-20 through 2023-24
remaining source exceptions: 0
point-in-time violations: 0
duplicate violations: 0
aggregate validation: PASS
privacy boundaries: PASS
```

## Output contract

Exactly one output Artifact may contain exactly two aggregate JSON files:

```text
historical-gold-5826-complete-corpus-freeze-manifest-v1.json
historical-gold-5826-freeze-manifest-real-artifact-execution-receipt-v1.json
```

The total uncompressed output must remain below 1 MiB. Game IDs, dates, team codes, feature IDs, raw/sample rows, row-level hashes, individual feature values, player information, and market prices are prohibited.

## Consumption rule

Any real execution attempt consumes the request, whether it passes or fails. Workflow reruns and repeat dispatch are prohibited.

## Current state

```text
request created: true
request validated: pending
approval granted: false
execution workflow created: false
execution enabled: false
Artifact downloaded/read: false
semantic manifest created: false
corpus frozen: false
formal Stake: 0
```

## Next state after successful request validation

```text
HISTORICAL_GOLD_5826_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_EXPLICIT_USER_APPROVAL_REQUIRED
```
