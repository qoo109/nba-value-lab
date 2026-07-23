# Historical Gold 5,826 Freeze Manifest Real Artifact Execution Request Design v1

## Purpose

Define the governance contract for a future one-time request to read the exact adopted Historical Gold GitHub Actions Artifact and generate an aggregate semantic freeze manifest.

This stage is design-only. It does not create the request, approval, execution workflow, canonical manifest, or corpus freeze.

## Triggering evidence

```text
synthetic builder validation: 20 / 20 PASS
implementation PR: 139
result recording PR: 140
result recording merge: 7f603a92790166238476e76f50b8b112af731eec
builder Git blob SHA: ebec2d9582961531eb72297ffac922bd38bb1382
formal Stake: 0
```

## Exact Artifact binding

The future request may bind only this Artifact:

```text
repository: qoo109/nba-value-lab
source workflow run: 29976204693
source job: 89108363564
Artifact ID: 8551587005
Artifact name: historical-silver-gold-two-game-official-cdn-recovery-v2
archive size: 374,591,375 bytes
archive digest: sha256:3ed2d28da3af58b8b72d805860a144541ac5f38106653cfbda593e16bbaa8e8d
expiry: 2026-08-06T03:14:00Z
```

The future workflow must fail closed if the Artifact is missing, expired, renamed, replaced, or does not match the exact metadata.

No silent rebuild or substitute Artifact is allowed. After expiry, a new governed rebuild lane with complete source-hash evidence is required.

## Exact file set

The downloaded Artifact must contain exactly three files and no extras:

```text
historical-silver-multiseason-recovered-v1.sqlite.gz
historical-gold-multiseason-recovered-v1.sqlite.gz
two-game-official-cdn-pbp-recovery-result-v2.json
```

The Silver database is evidence-only and must not be decompressed or read. The Gold database is the only database input permitted. The aggregate recovery result may be read only to verify its committed-copy binding.

## Request lifecycle

The future request must:

- have a unique request ID using the declared prefix;
- start at execution count `0` with maximum `1`;
- require a separate explicit user approval;
- bind the exact request, builder, policy, synthetic-result, and recovery-status file hashes;
- permit manual `workflow_dispatch` from `main` only;
- prohibit automatic dispatch and reruns;
- become consumed after any execution attempt, whether successful or failed;
- require approval and execution before the Artifact expires.

The request itself grants neither approval nor execution authority.

## Future workflow permissions and transport

Only these GitHub Actions are permitted:

```text
actions/checkout@v4
actions/setup-python@v5
actions/download-artifact@v4
actions/upload-artifact@v4
```

Permissions:

```text
contents: read
actions: read
```

The only permitted network transport is GitHub Actions Artifact transport. Generic HTTP clients, `curl`, `wget`, package installation, source-archive downloads, and odds or injury downloads are prohibited.

## Read-only execution boundary

The future workflow may:

1. verify the request and approval bindings;
2. verify the Artifact is unexpired;
3. download the exact Artifact by repository, run ID, and name;
4. verify the exact three-file set, sizes, and SHA-256 values;
5. decompress the Gold gzip to temporary runner storage;
6. execute the already validated builder once against the decompressed Gold SQLite;
7. validate the aggregate manifest;
8. emit one aggregate execution receipt;
9. upload one output Artifact containing exactly two JSON files.

It may not read Silver, write to SQLite, rebuild data, rerun recovery, modify the builder or policy, export rows, or write any database to the repository.

## Output contract

The future output Artifact may contain exactly:

```text
historical-gold-5826-complete-corpus-freeze-manifest-v1.json
historical-gold-5826-freeze-manifest-real-artifact-execution-receipt-v1.json
```

Combined uncompressed size must not exceed 1 MiB.

The receipt records request consumption, source Artifact binding, Gold gzip identity, decompressed SQLite identity, manifest identity, read-only controls, and Stake. It must not contain game IDs, dates, team codes, feature IDs, raw/sample rows, row-level hashes, individual feature values, player data, or market prices.

## Failure semantics

```text
expired or missing Artifact -> block before download/read; require new governed rebuild lane
metadata mismatch -> block before Gold read
file-set/hash/size mismatch -> block before Gold read
request/approval mismatch -> block before Artifact download
manifest mismatch -> aggregate fail-closed receipt; no canonical freeze claim
privacy failure -> block output Artifact
rerun attempt -> block as consumed/repeat-disallowed
```

A failed execution attempt still consumes the one-time request.

## Current boundaries

```text
request design created: true
request design validated: pending CI
request draft created: false
approval record created: false
execution workflow created: false
Artifact downloaded: false
real Gold database read: false
canonical manifest created: false
corpus frozen: false
market backtest: false
model retraining: false
formal Stake: 0
```

## Next controlled lane after validation

```text
HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_REQUEST_READY_FOR_DRAFT
```
