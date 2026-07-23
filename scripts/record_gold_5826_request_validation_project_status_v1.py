#!/usr/bin/env python3
"""Record the validated Gold 5,826 real Artifact request in PROJECT_STATUS.md."""
from pathlib import Path

PATH = Path("PROJECT_STATUS.md")
text = PATH.read_text(encoding="utf-8")

old_control = """real Artifact execution request design validated: true
real Artifact execution request created: false
real Artifact freeze workflow created: false
real Artifact execution approved: false
real Artifact execution count: 0
semantic freeze manifest created: false
corpus freeze executed: false
"""
new_control = """real Artifact execution request design validated: true
real Artifact execution request created: true
real Artifact execution request validation: PASS / AWAITING EXPLICIT USER APPROVAL
real Artifact execution request validation PR: 144
real Artifact execution request validation merge: 0ac67d836a6380c56565d9d8ac12465f260db65d
real Artifact execution request validation run: 29992891138
real Artifact execution request validation job: 89159516469
real Artifact execution request validation artifact: 8557702959
real Artifact execution request validation digest: sha256:bbea63ba827b29f10b14f76290eb67d47e9d3cb219f2b97219470616a1d24508
real Artifact execution request synthetic tests: 20 / 20 PASS
real Artifact execution request mutation tests: 35 / PASS
real Artifact freeze workflow created: false
real Artifact execution approved: false
real Artifact execution count: 0
semantic freeze manifest created: false
corpus freeze executed: false
"""
if text.count(old_control) != 1:
    raise SystemExit(f"expected one control block target, found {text.count(old_control)}")
text = text.replace(old_control, new_control, 1)

old_next = """## Next Unique Mainline

```text
HISTORICAL_GOLD_5826_COMPLETE_CORPUS_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_REQUEST_READY_FOR_DRAFT
```

The one-time exact GitHub Artifact request design is validated. The next controlled lane may create the governed request draft, but it may not grant approval, create or dispatch the execution workflow, download Artifact `8551587005`, read the real Gold database, create the canonical manifest, or freeze the corpus. Market backtesting, injury-model activation, model retraining, betting-edge claims and Stake above `0` remain unauthorized.
"""
new_next = """## Next Unique Mainline

```text
HISTORICAL_GOLD_5826_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_EXPLICIT_USER_APPROVAL_REQUIRED
```

The governed request is validated and bound to the exact adopted Artifact and computed SHA-256 approval evidence. The next controlled lane requires separate explicit user approval. Until that approval is recorded, no approval evidence, execution workflow, Artifact download/read, semantic manifest or corpus freeze may be created. Market backtesting, injury-model activation, model retraining, betting-edge claims and Stake above `0` remain unauthorized.
"""
if text.count(old_next) != 1:
    raise SystemExit(f"expected one next-mainline target, found {text.count(old_next)}")
text = text.replace(old_next, new_next, 1)

marker = "### Historical Gold 5,826 real Artifact execution request design"
if text.count(marker) != 1:
    raise SystemExit(f"expected one completed-evidence marker, found {text.count(marker)}")
section = """### Historical Gold 5,826 real Artifact execution request validation

```text
formal state: HISTORICAL_GOLD_5826_FREEZE_MANIFEST_REAL_ARTIFACT_EXECUTION_REQUEST_VALID_AWAITING_EXPLICIT_USER_APPROVAL
request ID: HISTORICAL-GOLD-5826-FREEZE-MANIFEST-REAL-ARTIFACT-EXECUTION-2026-07-23-001
request valid: true
synthetic tests: 20 / 20 PASS
mutation tests: 35 / PASS
maximum execution count: 1
execution count: 0
request consumed: false
approval granted: false
execution enabled: false
execution workflow created: false
real Artifact downloaded: false
real Artifact read: false
semantic manifest created: false
corpus frozen: false
formal Stake: 0
```

Validation evidence:

```text
validation PR: 144
validation merge: 0ac67d836a6380c56565d9d8ac12465f260db65d
validated head: b0225215301e71b0f411810e8c1719ea5ea8d531
workflow run: 29992891138
job: 89159516469 / validate-request / success
Artifact: 8557702959
Artifact digest: sha256:bbea63ba827b29f10b14f76290eb67d47e9d3cb219f2b97219470616a1d24508
Artifact expiry: 2026-08-06T08:53:06Z
```

The request validator confirmed the exact Artifact binding, upstream evidence, expiry, aggregate-only privacy boundary and fail-closed mutations. It computed the approval SHA-256 bindings without downloading or reading the real Gold Artifact. Separate explicit user approval remains required before any executor may be created.

Formal records:

- `data/research/historical-gold-5826-freeze-manifest-real-artifact-execution-request-v1.json`
- `data/research/historical-gold-5826-freeze-manifest-real-artifact-execution-request-current-status-v1.json`
- `data/research/historical-gold-5826-freeze-manifest-real-artifact-execution-request-validation-result-v1.json`
- `docs/historical-gold-5826-freeze-manifest-real-artifact-execution-request-validation-result-v1.md`


"""
text = text.replace(marker, section + marker, 1)
PATH.write_text(text, encoding="utf-8")
