# Historical Gold 5,826 real Artifact execution approval v1

## Explicit user decision

The repository owner explicitly approved the exact request in the ChatGPT project conversation on 2026-07-23:

> 我批准 Request HISTORICAL-GOLD-5826-FREEZE-MANIFEST-REAL-ARTIFACT-EXECUTION-2026-07-23-001 的一次性真實 Artifact 執行。

```text
request ID:
HISTORICAL-GOLD-5826-FREEZE-MANIFEST-REAL-ARTIFACT-EXECUTION-2026-07-23-001

approval state: EXPLICIT_USER_APPROVAL_GRANTED
maximum execution count: 1
execution count before approval: 0
request consumed before approval: false
workflow_dispatch only: true
automatic dispatch allowed: false
workflow rerun allowed: false
repeat execution allowed: false
formal Stake: 0
```

## Immutable approval bindings

The approval binds the exact SHA-256 values produced by request validation run `29992891138`, job `89159516469`, Artifact `8557702959`:

```text
request:
sha256:2f8d209b3a7c5031c338b3add108e534ff69ec0d08d62bbb93f7b20963865990

request design:
sha256:33e5a5789430092d8ccf6f3831c89424683b4726dd6dacdc876695dba287d57e

manifest builder:
sha256:ca4c21316711897121f480165227cea6f6059db808706f4084c853e428418a21

synthetic result:
sha256:24a8ea75116a179c34942f9d301c9cc9a3422d583b4d6cc69935f26ce2ccbcd5

freeze policy:
sha256:50e36245b712d934cfc26e443be2fb15c2087c1819dea583914b364049da2eda

recovery current status:
sha256:bea4deeccf6c23d6bd66108a3c567ad2a10be4fe56b2b20fa3710d9196ccb741
```

The approved source remains Artifact `8551587005`, source run `29976204693`, archive digest `sha256:3ed2d28da3af58b8b72d805860a144541ac5f38106653cfbda593e16bbaa8e8d`, expiring `2026-08-06T03:14:00Z`.

## Authorized execution

The approval authorizes creation of one manual `workflow_dispatch` executor on `main`. The executor may download only the exact bound GitHub Actions Artifact, verify its exact three-file set and hashes, decompress only the Gold gzip into temporary runner storage, open the Gold SQLite read-only through the validated builder, and upload exactly two aggregate JSON files under 1 MiB.

Any execution attempt consumes the request. A workflow rerun or second dispatch is prohibited.

## Not authorized

This approval does not authorize Silver semantic database reads, repository database writes, SQLite writes, source recovery reruns, Gold rebuilds, market backtests, model retraining, injury activation, betting-edge claims, or Stake above `0`.

## State after merge

```text
HISTORICAL_GOLD_5826_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_APPROVED_READY_FOR_ONE_TIME_MANUAL_DISPATCH
```
