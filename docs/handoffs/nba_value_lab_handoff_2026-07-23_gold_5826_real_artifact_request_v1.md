# NBA Value Lab Handoff — Gold 5,826 Real Artifact Request v1

## Repository

```text
qoo109/nba-value-lab
```

## Governed corpus

```text
Gold matchups: 5,826
Gold team-game rows: 11,652
remaining source exceptions: 0
point-in-time violations: 0
formal Stake: 0
```

## Current lane

A one-time request draft binds the exact adopted GitHub Actions Artifact and the validated offline manifest builder.

```text
request ID:
HISTORICAL-GOLD-5826-FREEZE-MANIFEST-REAL-ARTIFACT-EXECUTION-2026-07-23-001

maximum execution attempts: 1
execution count: 0
request consumed: false
approval granted: false
execution enabled: false
```

## Exact Artifact

```text
source run: 29976204693
source job: 89108363564
Artifact: 8551587005
archive digest: sha256:3ed2d28da3af58b8b72d805860a144541ac5f38106653cfbda593e16bbaa8e8d
expiry: 2026-08-06T03:14:00Z
Gold gzip SHA-256: sha256:a4e94fab1681b53817f305d08c196995d406fa0566ab70d6083aa5cebfc52085
```

## Request files

```text
data/research/historical-gold-5826-freeze-manifest-real-artifact-execution-request-v1.json
data/research/historical-gold-5826-freeze-manifest-real-artifact-execution-request-current-status-v1.json
docs/historical-gold-5826-freeze-manifest-real-artifact-execution-request-v1.md
scripts/validate_historical_gold_5826_freeze_manifest_real_artifact_execution_request_v1.py
.github/workflows/validate-historical-gold-5826-freeze-manifest-real-artifact-execution-request-v1.yml
```

## Validation behavior

The request validator computes SHA-256 bindings for the request, request design, builder, synthetic result, freeze policy, and recovery status. A later separate approval must bind every computed digest.

The validator does not download/read the Artifact and does not execute the manifest builder.

## Still prohibited

```text
approval creation without a new explicit user decision
execution workflow implementation
manual or automatic dispatch
Artifact download/read
Silver database read
SQLite/database writes
canonical manifest creation
corpus freeze claim
market backtest
model retraining
injury candidate activation
betting-edge claim
Stake above 0
```

## Next state after request validation

```text
HISTORICAL_GOLD_5826_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_EXPLICIT_USER_APPROVAL_REQUIRED
```
