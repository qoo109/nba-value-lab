# NBA Value Lab Handoff — Gold 5,826 Real Artifact Request Design v1

## Repository

```text
qoo109/nba-value-lab
```

## Completed upstream state

```text
Historical Gold matchups: 5,826
Gold team-game rows: 11,652
remaining source exceptions: 0
point-in-time violations: 0
freeze-manifest builder synthetic tests: 20 / 20 PASS
formal Stake: 0
```

## This lane

A design-only contract defines how a future one-time request may bind and read the exact adopted GitHub Actions Artifact.

Primary records:

```text
data/research/historical-gold-5826-freeze-manifest-real-artifact-execution-request-design-v1.json
data/research/historical-gold-5826-freeze-manifest-real-artifact-execution-request-design-current-status-v1.json
docs/historical-gold-5826-freeze-manifest-real-artifact-execution-request-design-v1.md
scripts/validate_historical_gold_5826_freeze_manifest_real_artifact_execution_request_design_v1.py
.github/workflows/validate-historical-gold-5826-freeze-manifest-real-artifact-execution-request-design-v1.yml
```

## Exact future input

```text
source run: 29976204693
source job: 89108363564
Artifact ID: 8551587005
Artifact name: historical-silver-gold-two-game-official-cdn-recovery-v2
archive digest: sha256:3ed2d28da3af58b8b72d805860a144541ac5f38106653cfbda593e16bbaa8e8d
expiry: 2026-08-06T03:14:00Z
Gold gzip SHA-256: sha256:a4e94fab1681b53817f305d08c196995d406fa0566ab70d6083aa5cebfc52085
```

## Governance decisions

- Exactly one manual execution attempt maximum.
- A separate explicit user approval must bind the exact request and implementation evidence.
- Any execution attempt consumes the request.
- Rerun and automatic dispatch are prohibited.
- GitHub Actions Artifact transport is the only future network path.
- Silver is evidence-only and may not be read.
- Gold may be decompressed only to temporary runner storage and opened read-only.
- Output is exactly one Artifact with two aggregate JSON files under 1 MiB.
- Artifact expiry or identity mismatch blocks before real Gold read.

## Still not created or executed

```text
request draft: false
approval record: false
execution workflow: false
Artifact download: false
real Gold read: false
canonical semantic manifest: false
corpus frozen: false
market backtest: false
model retraining: false
formal Stake: 0
```

## Next lane after validation

```text
HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_REQUEST_READY_FOR_DRAFT
```

The next lane may create the governed request record only. It must not grant approval, create or dispatch the execution workflow, download the Artifact, or read the real database.
